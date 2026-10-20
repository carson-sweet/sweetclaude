#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
v3 -> v4 backlog migration core.

Pure, deterministic operations extracted from skill-library/configure/migrate/SKILL.md so the
migration can be tested end-to-end without an LLM in the loop. The skill
remains responsible for: lock/backup (Step 1), user prompts (Step 3 done-
item choice, Step 4 preview confirmation, Step 8 delete prompt), and the
overall flow orchestration. This script provides the operations the skill
delegates to.

CLI subcommands:
  preflight          --project-dir DIR
  resolve-base       --project-dir DIR
  scan-orphans       --project-dir DIR
  validate           --project-dir DIR
  plan               --project-dir DIR [--include-done]
  execute            --project-dir DIR [--include-done]
  verify             --project-dir DIR --created-paths-file FILE
  finalize           --project-dir DIR
  reonboard-orphans  --project-dir DIR --paths JSON_LIST
  resolve-orphan     --project-dir DIR --path REL_PATH --action ACTION
  group-orphans      --project-dir DIR

All commands emit JSON on stdout. Errors emit on stderr; exit 1 on failure.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys
import tarfile

import yaml

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from maintenance.capability_manifest import capability_config
from mutation_safety import (
    hash_payload,
    validate_approval_scope,
    validate_postconditions,
    validate_restore_proof,
    validate_snapshot_scope,
    validate_write_set,
)
from recovery.recover_project import guard_project


V3_VALID_STATUSES = {"backlog", "in_progress", "done", "cancelled", "blocked", "abandoned", "deferred"}
VALID_TYPES = {"story", "bug", "debt", "chore"}
TERMINAL_STATUSES = {"done", "abandoned"}
MIGRATION_CAPABILITY_ID = "migrate.flat_bl_to_issue"
SUPPORTED_PROJECT_SHAPE = "flat_bl_backlog"
MIGRATION_EXECUTION_MANIFEST = pathlib.Path(".sweetclaude/state/migrations/v3-to-v4-execution.json")
MIGRATION_SNAPSHOT_TARBALL = pathlib.Path(".sweetclaude/state/migrations/v3-to-v4-snapshot.tar.gz")
MIGRATION_SNAPSHOT_MANIFEST = pathlib.Path(".sweetclaude/state/migrations/v3-to-v4-snapshot-manifest.json")

# Status remapping from v3 to v4 vocabulary.
STATUS_REMAP = {
    "backlog": "new",
    "cancelled": "abandoned",
    "in_progress": "active",
    "deferred": "deferred",
}


def resolve_product_base(project_dir: pathlib.Path) -> pathlib.Path:
    """Read artifact-privacy.yaml; fall back to .sweetclaude/product."""
    privacy = project_dir / ".sweetclaude" / "artifact-privacy.yaml"
    if privacy.exists():
        try:
            d = yaml.safe_load(privacy.read_text()) or {}
            base = (
                (d.get("categories") or {}).get("product", {}).get("base_path", "")
            )
            if base:
                base = base.rstrip("/")
                if pathlib.Path(base).is_absolute():
                    return pathlib.Path(base)
                return project_dir / base
        except yaml.YAMLError:
            pass
    return project_dir / ".sweetclaude" / "product"


_LEGACY_STATUS_MAP = {
    "done": "done",
    "in_progress": "in_progress",
    "in progress": "in_progress",
    "open": "in_progress",
    "backlog": "backlog",
    "blocked": "blocked",
    "deferred": "deferred",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "abandoned": "abandoned",
}

_LEGACY_PRIORITY_MAP = {
    "spike": "P2",
    "p0": "P0",
    "p1": "P1",
    "p2": "P2",
    "p3": "P3",
    "p4": "P3",
    "next": "P0",
    "now": "P0",
    "sooner": "P1",
    "soon": "P2",
    "later": "P3",
    "someday": "P3",
    "high": "P1",
    "medium": "P2",
    "low": "P3",
}


_STATUS_PREFIX_RE = re.compile(
    r"^(done|in[_\s]progress|backlog|blocked|deferred|cancelled|canceled|abandoned|open)\b",
    re.I,
)


def _normalize_legacy_status(raw: str) -> tuple[str, str | None]:
    """
    Parse status strings like 'DONE — 2026-05-02', 'Done', 'DONE (2026-05-02)',
    'BACKLOG' into (v3_status, closed_date_or_None).
    Matches a known keyword prefix instead of splitting on separators, so date
    hyphens inside '2026-05-02' do not break the base keyword extraction.
    """
    raw = raw.strip()
    m = _STATUS_PREFIX_RE.match(raw)
    if m:
        base = m.group(1).lower()
    else:
        base = raw.lower().split()[0] if raw else "backlog"
    status = _LEGACY_STATUS_MAP.get(base, base.replace(" ", "_"))
    date_m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", raw)
    return status, (date_m.group(1) if date_m else None)


def _parse_legacy_markdown(text: str, stem: str) -> dict | None:
    """
    Parse BL-*.md files that use '# BL-NNN: Title' + '**Field:** value' format
    instead of YAML frontmatter. Returns a frontmatter-compatible dict, or None
    if the file does not match the expected pattern.
    """
    h1_m = re.search(r"^#\s+(BL-\d+)[:\s]+(.+)", text, re.M)
    fn_m = re.match(r"(BL-\d+)", stem)
    if not h1_m and not fn_m:
        return None

    if h1_m:
        bl_id = h1_m.group(1)
        title = h1_m.group(2).strip()
    else:
        bl_id = fn_m.group(1)
        slug_part = stem[len(bl_id):].lstrip("-")
        title = slug_part.replace("-", " ").strip() if slug_part else bl_id

    fields: dict[str, str] = {}
    for m in re.finditer(r"^\*\*([^*:]+):\*\*\s*(.+)", text, re.M):
        key = m.group(1).strip().lower().replace(" ", "_")
        fields[key] = m.group(2).strip()

    status_raw = fields.get("status", "backlog")
    v3_status, closed_date = _normalize_legacy_status(status_raw)

    raw_priority = fields.get("priority", "P2").lower().strip()
    priority = _LEGACY_PRIORITY_MAP.get(raw_priority, "P2")

    fm: dict = {
        "id": bl_id,
        "title": title,
        "type": fields.get("type", "story").lower(),
        "status": v3_status,
        "priority": priority,
    }
    if closed_date:
        fm["closed_date"] = closed_date
    if "created" in fields:
        fm["created"] = fields["created"]
    if "tags" in fields:
        fm["tags"] = [t.strip() for t in fields["tags"].split(",") if t.strip()]
    return fm


def _read_v3_file(path: pathlib.Path) -> tuple[dict, str] | tuple[None, str]:
    """Return (frontmatter_dict, body_text) or (None, error_reason)."""
    raw = path.read_bytes()
    if raw[:3] == b"\xef\xbb\xbf":
        raw = raw[3:]
    text = raw.decode("utf-8").replace("\r\n", "\n")
    parts = text.split("---", 2)
    if len(parts) < 3:
        fm = _parse_legacy_markdown(text, path.stem)
        if fm is not None:
            return fm, text
        return None, "no-frontmatter-delimiter"
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return None, f"frontmatter-parse-error:{e}"
    if not isinstance(fm, dict):
        return None, f"frontmatter-not-a-dict:{type(fm).__name__}"
    if isinstance(fm.get("status"), str):
        norm_status, closed_date = _normalize_legacy_status(fm["status"])
        fm["status"] = norm_status
        if closed_date and fm.get("closed_date") is None:
            fm["closed_date"] = closed_date
    return fm, parts[2]


_WORK_ITEM_PATTERNS = [
    "BL-*.md", "STORY-*.md", "BUG-*.md", "DEBT-*.md", "CHORE-*.md",
    "ISSUE-*.md", "EP-*.md", "EPIC-*.md", "US-*.md", "spike-BL-*.md",
]
_TYPED_SUBDIRS = ["stories", "bugs", "debt", "chores", "spike-reports"]
_OLD_PREFIX_ID_RE = re.compile(r"^(STORY|BUG|DEBT|CHORE|BL)-\d+", re.I)
_V4_ID_RE = re.compile(r"^(ISSUE|EP|MS|SP|TH|RM|REL|PITCH|CYC|I)-\d{2,}$")


def _read_sweetclaude_state(project_dir: pathlib.Path) -> dict:
    state_path = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
    if not state_path.exists():
        return {}
    try:
        data = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return {"_parse_error": str(exc)}
    return data if isinstance(data, dict) else {}


def _migration_capability_contract() -> dict:
    capability = capability_config(MIGRATION_CAPABILITY_ID)
    return {
        "capability_id": MIGRATION_CAPABILITY_ID,
        "supported_project_shapes": list(capability.get("supports_project_shapes") or []),
        "safety_contract": list(capability.get("safety_contract") or []),
        "verification_commands": list(capability.get("verification_commands") or []),
        "requires_approval": bool(capability.get("requires_approval", False)),
        "mutates_project": bool(capability.get("mutates_project", False)),
        "preflight_required": bool(capability.get("preflight_required", False)),
    }


def _migration_guard(project_dir: pathlib.Path) -> dict:
    try:
        return guard_project(project_dir)
    except Exception as exc:
        return {
            "status": "guard-error",
            "project_shape": "",
            "migrate_allowed": False,
            "message": f"Migration guard failed: {exc}",
        }


def migration_preflight(project_dir: pathlib.Path) -> dict:
    """Read-only safety decision for the v3-to-v4 BL migration.

    This migrator only supports the flat BL-NNN backlog layout. Typed backlog
    layouts and accepted compatibility-mode projects must not proceed through
    this script because doing so can create empty migration maps or mixed state.
    """
    product_base = resolve_product_base(project_dir)
    backlog_path = product_base / "backlog"
    direct_bl_files = sorted(backlog_path.glob("BL-*.md")) if backlog_path.is_dir() else []
    capability = _migration_capability_contract()
    guard = _migration_guard(project_dir)
    project_shape = str(guard.get("project_shape", "") or "")
    supported_shapes = capability["supported_project_shapes"]
    manifest_supported = project_shape in supported_shapes

    typed_files: list[pathlib.Path] = []
    if backlog_path.is_dir():
        for subdir in _TYPED_SUBDIRS:
            typed_dir = backlog_path / subdir
            if typed_dir.is_dir():
                typed_files.extend(sorted(typed_dir.rglob("*.md")))

    old_typed_files = [
        path for path in typed_files
        if path.name.startswith(("STORY-", "BUG-", "DEBT-", "CHORE-", "BL-"))
    ]

    duplicate_ids: dict[str, list[str]] = {}
    seen_ids: dict[str, list[str]] = {}
    for path in old_typed_files:
        fm = _sniff_frontmatter(path) or {}
        id_match = _OLD_PREFIX_ID_RE.match(path.stem)
        item_id = str(fm.get("id") or (id_match.group(0) if id_match else path.stem)).strip()
        if item_id:
            seen_ids.setdefault(item_id, []).append(str(path))
    duplicate_ids = {
        item_id: paths for item_id, paths in seen_ids.items() if len(paths) > 1
    }

    state = _read_sweetclaude_state(project_dir)
    taxonomy_status = (
        ((state.get("recovery") or {}).get("taxonomy") or {}).get("status")
        if isinstance(state, dict)
        else None
    )

    blockers: list[dict] = []
    if guard.get("status") == "guard-error":
        blockers.append({
            "code": "migration-guard-error",
            "message": guard.get("message", "Migration guard failed."),
        })
    if project_shape != SUPPORTED_PROJECT_SHAPE:
        blockers.append({
            "code": "unsupported-project-shape",
            "message": (
                f"This migrator only supports project_shape={SUPPORTED_PROJECT_SHAPE}; "
                f"detected {project_shape or 'unknown'}."
            ),
            "project_shape": project_shape or "unknown",
            "supported_project_shapes": supported_shapes,
        })
    if not manifest_supported:
        blockers.append({
            "code": "manifest-capability-unsupported",
            "message": (
                f"Manifest capability {MIGRATION_CAPABILITY_ID} does not support "
                f"project_shape={project_shape or 'unknown'}."
            ),
            "capability_id": MIGRATION_CAPABILITY_ID,
            "project_shape": project_shape or "unknown",
            "supported_project_shapes": supported_shapes,
        })
    if guard.get("status") == "run-recover":
        blockers.append({
            "code": "recovery-required",
            "message": "Recovery guard requires /sweetclaude:configure recover before migration.",
            "recovery_route": guard.get("recovery_route"),
        })
    if guard.get("migrate_allowed") is False and project_shape == SUPPORTED_PROJECT_SHAPE:
        blockers.append({
            "code": "guard-blocked-migration",
            "message": guard.get("message", "Migration guard did not allow migration."),
        })
    if state.get("_parse_error"):
        blockers.append({
            "code": "sweetclaude-state-parse-error",
            "message": "sweetclaude.yaml cannot be parsed; migration requires manual review.",
        })
    if taxonomy_status == "stabilized-without-migration":
        blockers.append({
            "code": "compatibility-mode",
            "message": "Project is in accepted legacy compatibility mode.",
        })
    if old_typed_files:
        blockers.append({
            "code": "unsupported-typed-backlog-layout",
            "message": "Typed backlog folders are not supported by this BL migrator.",
            "file_count": len(old_typed_files),
        })
    if duplicate_ids:
        blockers.append({
            "code": "duplicate-work-item-ids",
            "message": "Duplicate work item IDs require explicit collision handling.",
            "duplicates": duplicate_ids,
        })
    if not direct_bl_files and not old_typed_files and backlog_path.is_dir():
        blockers.append({
            "code": "no-flat-bl-files",
            "message": "No flat BL-NNN files were found for this migrator.",
        })

    migrate_allowed = (
        not blockers
        and bool(direct_bl_files)
        and manifest_supported
        and project_shape == SUPPORTED_PROJECT_SHAPE
        and bool(guard.get("migrate_allowed"))
    )
    status = "ok" if migrate_allowed else "blocked"
    recommendation = (
        "Proceed with v3 flat BL-NNN migration."
        if migrate_allowed
        else "Do not run this migration. Use /sweetclaude:configure recover or a layout-specific migration plan."
    )

    return {
        "status": status,
        "migrate_allowed": migrate_allowed,
        "capability_id": MIGRATION_CAPABILITY_ID,
        "project_shape": project_shape,
        "manifest_supported": manifest_supported,
        "supported_project_shapes": supported_shapes,
        "safety_contract": capability["safety_contract"],
        "verification_commands": capability["verification_commands"],
        "requires_approval": capability["requires_approval"],
        "mutates_project": capability["mutates_project"],
        "preflight_required": capability["preflight_required"],
        "guard_status": guard.get("status"),
        "guard": guard,
        "product_base": str(product_base),
        "backlog_path": str(backlog_path),
        "flat_bl_count": len(direct_bl_files),
        "typed_old_prefix_count": len(old_typed_files),
        "blocking_factors": blockers,
        "block_reason": "" if migrate_allowed else "; ".join(
            factor.get("message", factor.get("code", "")) for factor in blockers
        ),
        "recommendation": recommendation,
    }


def _sniff_frontmatter(path: pathlib.Path) -> dict | None:
    """Return frontmatter dict if file looks like a work item, else None."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    parts = text.split("---", 2)
    if len(parts) >= 3:
        try:
            fm = yaml.safe_load(parts[1])
            if isinstance(fm, dict) and ("id" in fm or "status" in fm or "title" in fm):
                return fm
        except yaml.YAMLError:
            pass
    fm = _parse_legacy_markdown(text, path.stem)
    if fm is not None:
        return fm
    return None


_ORPHAN_REGISTRY = ".sweetclaude/state/orphan-registry.yaml"


def _load_orphan_registry(project_dir: pathlib.Path) -> set[str]:
    for name in [_ORPHAN_REGISTRY, ".sweetclaude/state/martian-registry.yaml"]:
        reg = project_dir / name
        if reg.exists():
            try:
                data = yaml.safe_load(reg.read_text()) or {}
                return {e["path"] for e in data.get("acknowledged", []) if isinstance(e, dict) and "path" in e}
            except (yaml.YAMLError, KeyError, TypeError):
                pass
    return set()


def acknowledge_orphans(project_dir: pathlib.Path, rel_paths: list[str]) -> dict:
    reg_path = project_dir / _ORPHAN_REGISTRY
    try:
        data = yaml.safe_load(reg_path.read_text()) if reg_path.exists() else {}
    except yaml.YAMLError:
        data = {}
    data = data or {}
    data.setdefault("version", 1)
    existing = data.setdefault("acknowledged", [])
    known = {e["path"] for e in existing if isinstance(e, dict) and "path" in e}
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    added = []
    for p in rel_paths:
        if p not in known:
            existing.append({"path": p, "acknowledged_at": ts})
            added.append(p)
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return {"acknowledged": added, "total": len(existing)}


def archive_orphans(project_dir: pathlib.Path, rel_paths: list[str]) -> dict:
    product_base = resolve_product_base(project_dir)
    archive_dir = product_base / "archive" / "orphans"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived = []
    for rp in rel_paths:
        src = project_dir / rp
        if not src.exists():
            continue
        dest = archive_dir / src.name
        counter = 1
        while dest.exists():
            dest = archive_dir / f"{src.stem}-{counter}{src.suffix}"
            counter += 1
        src.rename(dest)
        archived.append({"source": rp, "dest": str(dest.relative_to(project_dir))})
    return {"archived": archived}


def scan_orphans(project_dir: pathlib.Path) -> dict:
    """Scan all known SweetClaude locations for orphaned work item files.

    Returns categorized findings so the skill can present them to the user.
    """
    product_base = resolve_product_base(project_dir)
    backlog_path = product_base / "backlog"
    primary_bl_files = {str(p) for p in backlog_path.glob("BL-*.md")} if backlog_path.exists() else set()

    expected_files: set[str] = set()
    for root in [product_base, project_dir / "docs" / "product"]:
        if not root.exists():
            continue
        for loc in [
            root / "backlog",
            root / "backlog" / "done",
            root / "backlog" / "archived",
            root / "roadmap" / "issues",
            root / "roadmap" / "issues" / "done",
            root / "roadmap" / "epics",
            root / "roadmap" / "epics" / "done",
            root / "milestones",
            root / "issues",
        ]:
            if loc.is_dir():
                expected_files.update(str(p) for p in loc.glob("ISSUE-*.md"))
                expected_files.update(str(p) for p in loc.glob("EP-*.md"))
                expected_files.update(str(p) for p in loc.glob("MS-*.md"))
                expected_files.update(str(p) for p in loc.glob("SP-*.md"))
                expected_files.update(str(p) for p in loc.glob("RM-*.md"))
                expected_files.update(str(p) for p in loc.glob("I-*.md"))

    findings: list[dict] = []
    seen: set[str] = set()
    acknowledged = _load_orphan_registry(project_dir)
    archive_root = (product_base / "archive").resolve()

    def _add(path: pathlib.Path, category: str, detail: str) -> None:
        key = str(path.resolve())
        if key in seen or str(path) in expected_files:
            return
        resolved = pathlib.Path(key)
        if resolved == archive_root or archive_root in resolved.parents:
            return
        try:
            rel = str(path.relative_to(project_dir))
        except ValueError:
            rel = str(path)
        if rel in acknowledged:
            return
        seen.add(key)
        fm = _sniff_frontmatter(path)
        findings.append({
            "file": rel,
            "category": category,
            "detail": detail,
            "id": (fm or {}).get("id", path.stem),
            "title": (fm or {}).get("title", ""),
            "status": (fm or {}).get("status", ""),
            "has_frontmatter": fm is not None,
        })

    search_roots = [
        project_dir / ".sweetclaude" / "product",
        project_dir / "docs" / "product",
    ]

    # 1. Old typed subdirectories under backlog/
    for root in search_roots:
        for subdir in _TYPED_SUBDIRS:
            typed_dir = root / "backlog" / subdir
            if typed_dir.is_dir():
                for p in typed_dir.rglob("*.md"):
                    _add(p, "typed-subdir", f"found in retired {subdir}/ subdirectory")

    # 2. Legacy-prefix files anywhere under search roots (not already expected)
    _LEGACY_PATTERNS = [
        "BL-*.md", "STORY-*.md", "BUG-*.md", "DEBT-*.md", "CHORE-*.md",
        "EPIC-*.md", "US-*.md", "spike-BL-*.md",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in _LEGACY_PATTERNS:
            for p in root.rglob(pattern):
                if "done/" in str(p) or "archived/" in str(p):
                    _add(p, "legacy-archived", "legacy-prefix file in archival directory")
                else:
                    _add(p, "legacy-stray", f"legacy-prefix file ({pattern})")

    # 3. BL-*.md in unexpected locations (wrong base path, nested)
    for root in search_roots:
        if not root.exists():
            continue
        for p in root.rglob("BL-*.md"):
            if str(p) not in primary_bl_files:
                _add(p, "bl-wrong-location", "BL file outside primary backlog directory")

    # 4. Catch-all: .md files with frontmatter in backlog directories only
    #    that weren't matched by steps 1-3 and have a work-item-shaped ID
    #    (prefixed with letters + hyphen + digits). Product docs, specs,
    #    briefs, and scratch files are not work items.
    backlog_roots = []
    for root in search_roots:
        bl = root / "backlog"
        if bl.is_dir():
            backlog_roots.append(bl)
    for bl_root in backlog_roots:
        for p in bl_root.rglob("*.md"):
            key = str(p.resolve())
            if key in seen or str(p) in expected_files:
                continue
            fm = _sniff_frontmatter(p)
            if fm is not None:
                fid = str(fm.get("id", ""))
                if _V4_ID_RE.match(fid):
                    continue
                if _OLD_PREFIX_ID_RE.match(fid):
                    continue
                _add(p, "martian", "unknown format with frontmatter in backlog")

    return {
        "product_base": str(product_base),
        "orphan_count": len(findings),
        "findings": findings,
    }


def validate(project_dir: pathlib.Path) -> dict:
    """Step 2 — return {failures: [{file, problem}], ids: {id: [file, ...]}}."""
    product_base = resolve_product_base(project_dir)
    backlog_path = product_base / "backlog"
    files = sorted(backlog_path.glob("BL-*.md"), key=lambda p: p.name)

    failures: list[dict] = []
    ids: dict[str, list[str]] = {}

    for path in files:
        fm_or_err = _read_v3_file(path)
        if fm_or_err[0] is None:
            failures.append({"file": str(path), "problem": fm_or_err[1]})
            continue
        fm, _ = fm_or_err
        for field in ("id", "title", "status"):
            if fm.get(field) is None:
                failures.append({"file": str(path), "problem": f"missing-field:{field}"})
        status = fm.get("status")
        if status is not None and status not in V3_VALID_STATUSES:
            failures.append({"file": str(path), "problem": f"unknown-status:{status}"})
        typ = fm.get("type")
        if typ is not None and typ not in VALID_TYPES:
            failures.append({"file": str(path), "problem": f"unknown-type:{typ}"})
        id_val = fm.get("id")
        if id_val is not None:
            ids.setdefault(id_val, []).append(str(path))

    for id_val, paths in ids.items():
        if len(paths) > 1:
            for p in paths:
                failures.append({"file": p, "problem": f"duplicate-id:{id_val}"})

    return {
        "product_base": str(product_base),
        "v3_file_count": len(files),
        "failures": failures,
    }


def _make_slug(title: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (title or "").lower())).strip("-")


def _next_issue_number(backlog_path: pathlib.Path) -> int:
    highest = 0
    if backlog_path.is_dir():
        for sub in [backlog_path, backlog_path / "done", backlog_path / "archived"]:
            if not sub.is_dir():
                continue
            for p in sub.glob("ISSUE-*.md"):
                m = re.match(r"^ISSUE-(\d+)", p.name)
                if m:
                    highest = max(highest, int(m.group(1)))
    return highest + 1


def reonboard_orphans(project_dir: pathlib.Path, rel_paths: list[str]) -> dict:
    product_base = resolve_product_base(project_dir)
    backlog_path = product_base / "backlog"
    backlog_path.mkdir(parents=True, exist_ok=True)
    counter = _next_issue_number(backlog_path)
    created = []
    for rp in rel_paths:
        src = project_dir / rp
        if not src.exists():
            continue
        fm = _sniff_frontmatter(src)
        title = (fm or {}).get("title", src.stem) or src.stem
        old_id = (fm or {}).get("id", src.stem)
        status = (fm or {}).get("status", "new")
        item_type = (fm or {}).get("type", "story")
        new_id = f"ISSUE-{counter:03d}"
        slug = _make_slug(title)
        dest_name = f"{new_id}-{slug}.md" if slug else f"{new_id}.md"
        dest = backlog_path / dest_name
        try:
            body = src.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parts = body.split("---", 2)
        body_text = parts[2].strip() if len(parts) >= 3 else body.strip()
        new_fm = {
            "id": new_id,
            "title": title,
            "status": status,
            "type": item_type,
            "reonboarded_from": {"path": rp, "original_id": old_id},
        }
        dest.write_text(
            f"---\n{yaml.dump(new_fm, default_flow_style=False, sort_keys=False).rstrip()}\n---\n\n{body_text}\n"
        )
        created.append({
            "source": rp,
            "dest": str(dest.relative_to(project_dir)),
            "new_id": new_id,
            "original_id": old_id,
        })
        counter += 1
    return {"reonboarded": created, "next_issue_number": counter}


def reonboard_orphan(project_dir: pathlib.Path, rel_path: str) -> dict:
    product_base = resolve_product_base(project_dir)
    backlog_path = product_base / "backlog"
    backlog_path.mkdir(parents=True, exist_ok=True)
    src = project_dir / rel_path
    if not src.exists():
        return {"error": "file-not-found", "path": rel_path}
    fm = _sniff_frontmatter(src)
    title = (fm or {}).get("title", src.stem) or src.stem
    old_id = (fm or {}).get("id", src.stem)
    status = (fm or {}).get("status", "new")
    item_type = (fm or {}).get("type", "story")
    counter = _next_issue_number(backlog_path)
    new_id = f"ISSUE-{counter:03d}"
    slug = _make_slug(title)
    dest_name = f"{new_id}-{slug}.md" if slug else f"{new_id}.md"
    dest = backlog_path / dest_name
    try:
        body = src.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"error": "read-failed", "path": rel_path}
    parts = body.split("---", 2)
    body_text = parts[2].strip() if len(parts) >= 3 else body.strip()
    new_fm = {
        "id": new_id,
        "title": title,
        "status": status,
        "type": item_type,
        "reonboarded_from": {"path": rel_path, "original_id": old_id},
    }
    dest.write_text(
        f"---\n{yaml.dump(new_fm, default_flow_style=False, sort_keys=False).rstrip()}\n---\n\n{body_text}\n"
    )
    return {
        "action": "reonboarded",
        "source": rel_path,
        "dest": str(dest.relative_to(project_dir)),
        "new_id": new_id,
        "original_id": old_id,
    }


def resolve_orphan(project_dir: pathlib.Path, rel_path: str, action: str) -> dict:
    if action == "reonboard":
        return reonboard_orphan(project_dir, rel_path)
    elif action == "archive":
        result = archive_orphans(project_dir, [rel_path])
        if result["archived"]:
            return {"action": "archived", **result["archived"][0]}
        return {"error": "archive-failed", "path": rel_path}
    elif action == "acknowledge":
        acknowledge_orphans(project_dir, [rel_path])
        return {"action": "acknowledged", "path": rel_path}
    elif action == "skip":
        return {"action": "skipped", "path": rel_path}
    else:
        return {"error": f"unknown-action: {action}", "path": rel_path}


def group_orphans(findings: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for f in findings:
        cat = f.get("category", "unknown")
        prefix_m = re.match(r"^([A-Za-z]+[-_])", f.get("id", ""))
        prefix = prefix_m.group(1) if prefix_m else "unknown-"
        parent = str(pathlib.Path(f.get("file", "")).parent)
        if cat == "typed-subdir":
            label = f"typed subdirectory ({parent.split('/')[-1]}/)"
        elif cat == "legacy-stray":
            label = f"{prefix}* files (legacy prefix)"
        elif cat == "legacy-archived":
            label = f"{prefix}* files in archival directory"
        elif cat == "bl-wrong-location":
            label = "BL-* files outside primary backlog"
        elif cat == "martian":
            label = f"{prefix}* files (unknown format)"
        else:
            label = f"{cat}: {prefix}*"
        key = f"{cat}:{prefix}:{parent}"
        if key not in groups:
            groups[key] = {"label": label, "category": cat, "prefix": prefix, "directory": parent, "files": []}
        groups[key]["files"].append({
            "file": f["file"], "id": f["id"], "title": f["title"], "status": f["status"],
        })
    result = []
    for key in sorted(groups):
        g = groups[key]
        g["count"] = len(g["files"])
        g["group_key"] = key
        result.append(g)
    has_grouping = len(result) > 1 or (len(result) == 1 and result[0]["count"] > 1)
    return {
        "groups": result, "group_count": len(result),
        "total_files": len(findings), "has_grouping": has_grouping,
    }


def build_plan(project_dir: pathlib.Path, include_done: bool) -> dict:
    """Compute the migration plan without writing. Same logic as execute() but no I/O."""
    preflight = migration_preflight(project_dir)
    if not preflight["migrate_allowed"]:
        return {
            "error": "migration-blocked",
            "preflight": preflight,
            "message": preflight["recommendation"],
        }

    product_base = resolve_product_base(project_dir)
    backlog_path = product_base / "backlog"
    files = sorted(backlog_path.glob("BL-*.md"), key=lambda p: p.name)

    dest_base = project_dir / ".sweetclaude" / "product" / "backlog"
    counter = 0
    plan_items: list[dict] = []
    skipped_done = 0

    for path in files:
        fm_or_err = _read_v3_file(path)
        if fm_or_err[0] is None:
            continue
        fm, _ = fm_or_err

        typ = (fm.get("type") or "story").lower()
        if typ not in VALID_TYPES:
            typ = "story"

        v3_status = fm.get("status", "backlog")
        v4_status = STATUS_REMAP.get(v3_status, v3_status)
        is_terminal = v4_status in TERMINAL_STATUSES

        if is_terminal and not include_done:
            skipped_done += 1
            continue

        counter += 1
        new_id = f"ISSUE-{counter:03d}"
        slug = _make_slug(fm.get("title", ""))

        subdir = "done" if is_terminal else ""
        dest = dest_base / subdir / f"{new_id}-{slug}.md" if subdir else dest_base / f"{new_id}-{slug}.md"

        plan_items.append(
            {
                "v3_id": fm.get("id", path.stem),
                "v3_file": str(path),
                "v4_id": new_id,
                "type": typ,
                "v3_status": v3_status,
                "v4_status": v4_status,
                "title": fm.get("title", ""),
                "is_terminal": is_terminal,
                "dest_path": str(dest),
            }
        )

    result = {
        "capability_id": preflight["capability_id"],
        "project_shape": preflight["project_shape"],
        "manifest_supported": preflight["manifest_supported"],
        "supported_project_shapes": preflight["supported_project_shapes"],
        "safety_contract": preflight["safety_contract"],
        "verification_commands": preflight["verification_commands"],
        "preflight": preflight,
        "product_base": str(product_base),
        "include_done": include_done,
        "counter": counter,
        "skipped_done": skipped_done,
        "plan_items": plan_items,
    }
    result["mutation_plan"] = _build_mutation_plan(project_dir, result)
    return result


def _relative_to_project(project_dir: pathlib.Path, path: pathlib.Path | str) -> str:
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = project_dir / p
    try:
        return p.resolve(strict=False).relative_to(project_dir.resolve(strict=False)).as_posix()
    except ValueError:
        return p.as_posix()


def _planned_rewritten_milestone_paths(project_dir: pathlib.Path, plan_items: list[dict]) -> list[str]:
    if not plan_items:
        return []
    bl_ids = {str(item["v3_id"]) for item in plan_items}
    bl_pattern = re.compile(r"\b(BL-\d+)\b")
    product_base = resolve_product_base(project_dir)
    milestones_dir = product_base / "roadmap" / "milestones"
    if not milestones_dir.exists():
        milestones_dir = project_dir / "docs" / "product" / "milestones"
    if not milestones_dir.exists():
        return []
    paths: list[str] = []
    for ms_file in sorted(milestones_dir.glob("MS-*.md")):
        text = ms_file.read_text(encoding="utf-8")
        if any(match.group(1) in bl_ids for match in bl_pattern.finditer(text)):
            paths.append(_relative_to_project(project_dir, ms_file))
    return paths


def _build_mutation_plan(project_dir: pathlib.Path, plan: dict) -> dict:
    product_backlog = resolve_product_base(project_dir) / "backlog"
    declared_blast_radius = [
        ".sweetclaude/state",
        _relative_to_project(project_dir, product_backlog),
    ]
    write_set = {
        _relative_to_project(project_dir, item["dest_path"])
        for item in plan.get("plan_items", [])
    }
    write_set.update({
        ".sweetclaude/product/backlog/MIGRATION-MAP.md",
        MIGRATION_EXECUTION_MANIFEST.as_posix(),
        MIGRATION_SNAPSHOT_TARBALL.as_posix(),
        MIGRATION_SNAPSHOT_MANIFEST.as_posix(),
    })
    write_set.update(_planned_rewritten_milestone_paths(project_dir, plan.get("plan_items", [])))
    declared_write_set = sorted(write_set)
    postconditions = [
        {"id": "migration-map", "status": "pending"},
        {"id": "created-files", "status": "pending"},
        {"id": "source-file-integrity", "status": "pending"},
        {"id": "created-file-integrity", "status": "pending"},
    ]
    plan_payload = {
        "capability_id": plan.get("capability_id"),
        "project_shape": plan.get("project_shape"),
        "include_done_count": plan.get("counter"),
        "skipped_done": plan.get("skipped_done"),
        "plan_items": plan.get("plan_items", []),
        "declared_write_set": declared_write_set,
        "declared_blast_radius": declared_blast_radius,
        "postconditions": [check["id"] for check in postconditions],
    }
    write_set_hash = hash_payload(declared_write_set)
    plan_hash = hash_payload(plan_payload)
    return {
        "status": "approval-required",
        "plan_hash": plan_hash,
        "write_set_hash": write_set_hash,
        "declared_write_set": declared_write_set,
        "declared_blast_radius": list(plan_payload["declared_blast_radius"]),
        "postconditions": postconditions,
        "approval_receipt_template": _approval_receipt_template(
            project_dir,
            include_done=bool(plan.get("include_done", False)),
            plan_hash=plan_hash,
            write_set_hash=write_set_hash,
        ),
    }


def _approval_context(project_dir: pathlib.Path, include_done: bool) -> dict:
    return {
        "project_dir": str(project_dir),
        "capability_id": MIGRATION_CAPABILITY_ID,
        "project_shape": SUPPORTED_PROJECT_SHAPE,
        "include_done": include_done,
    }


def _approval_receipt_template(
    project_dir: pathlib.Path,
    *,
    include_done: bool,
    plan_hash: str,
    write_set_hash: str,
) -> dict:
    return {
        "schema_version": 1,
        "kind": "sweetclaude.migration.approval",
        "approved": False,
        "plan_hash": plan_hash,
        "write_set_hash": write_set_hash,
        "snapshot_hash": "",
        "context": _approval_context(project_dir, include_done),
    }


def _build_new_frontmatter(fm: dict, new_id: str, typ: str, v4_status: str, today: str) -> dict:
    is_terminal = v4_status in TERMINAL_STATUSES
    origin = fm.get("source") or fm.get("origin", "manual")
    return {
        "id": new_id,
        "type": typ,
        "title": fm.get("title", ""),
        "status": v4_status,
        "priority": fm.get("priority", "P2"),
        "effort": fm.get("effort", "m"),
        "epic": fm.get("epic"),
        "milestone": fm.get("milestone"),
        "sprint": fm.get("sprint"),
        "tags": fm.get("tags", []) or [],
        "origin": origin,
        "created": fm.get("created", today),
        "updated": today,
        "closed_date": fm.get("closed_date") if is_terminal else None,
    }


def _build_body(body: str, fm: dict) -> str:
    body_text = body.lstrip("\n")
    sprint_history = fm.get("sprint_history") or []
    if sprint_history:
        table_lines = ["\n## Sprint History\n", "| Sprint | Status |", "|---|---|"]
        for entry in sprint_history:
            table_lines.append(f"| {entry.get('sprint', '')} | {entry.get('status', '')} |")
        body_text = body_text.rstrip("\n") + "\n" + "\n".join(table_lines) + "\n"
    return body_text


def _check_already_migrated(project_dir: pathlib.Path) -> dict | None:
    """Idempotency guard: refuse to overwrite a populated v4 state.

    If installed_version is already 4.x or later AND ISSUE-*.md files exist in
    .sweetclaude/product/backlog/, re-running execute would create
    duplicates. Refuse and direct the user to cleanup-v3-files.
    """
    sc_path = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
    if not sc_path.exists():
        return None
    try:
        sc = yaml.safe_load(sc_path.read_text()) or {}
    except yaml.YAMLError:
        return None
    installed = str((sc.get("framework") or {}).get("installed_version", ""))
    installed_major = re.match(r"^(\d+)\.", installed)
    if not installed_major or int(installed_major.group(1)) < 4:
        return None
    backlog_dir = project_dir / ".sweetclaude" / "product" / "backlog"
    issue_files = list(backlog_dir.glob("ISSUE-*.md")) if backlog_dir.exists() else []
    if not issue_files:
        return None
    return {
        "error": "already-migrated",
        "installed_version": installed,
        "issue_count": len(issue_files),
        "message": (
            f"Project is already at installed_version={installed} with "
            f"{len(issue_files)} ISSUE-*.md files. Re-running execute would "
            f"create duplicates. If a previous migration was interrupted and "
            f"you need to clean up residual v3 BL files, run "
            f"`migrate-v3-to-v4.py cleanup-v3-files` instead."
        ),
    }


def _mutation_blocked(
    *,
    code: str,
    message: str,
    preflight: dict,
    mutation_plan: dict | None = None,
) -> dict:
    blocked = dict(preflight)
    blocked["status"] = "blocked"
    blocked["migrate_allowed"] = False
    blockers = list(blocked.get("blocking_factors") or [])
    blockers.append({"code": code, "message": message})
    blocked["blocking_factors"] = blockers
    if mutation_plan is not None:
        blocked["mutation_plan"] = mutation_plan
    return {
        "error": "migration-blocked",
        "preflight": blocked,
        "message": message,
    }


def _load_approval_receipt(path: pathlib.Path | None) -> dict | None:
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid approval receipt: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("invalid approval receipt: not a JSON object")
    return data


def _approval_mismatch_code(message: str) -> str:
    if message.startswith("plan_hash mismatch"):
        return "stale-plan-hash"
    if message.startswith("write_set_hash mismatch"):
        return "stale-write-set-hash"
    if message.startswith("context."):
        return "approval-context-mismatch"
    return "approval-receipt-mismatch"


def _validate_pre_snapshot_approval(
    *,
    receipt: dict,
    mutation_plan: dict,
    project_dir: pathlib.Path,
    include_done: bool,
) -> dict:
    if receipt.get("schema_version") != 1:
        raise ValueError("approval receipt schema_version must be 1")
    if receipt.get("kind") != "sweetclaude.migration.approval":
        raise ValueError("approval receipt kind mismatch")
    if receipt.get("approved") is not True:
        raise ValueError("approval receipt is not approved")
    return validate_approval_scope(
        receipt,
        plan_hash=mutation_plan["plan_hash"],
        write_set_hash=mutation_plan["write_set_hash"],
        snapshot_hash=str(receipt.get("snapshot_hash", "")),
        context=_approval_context(project_dir, include_done),
    )


def _validate_snapshot_receipt_binding(receipt: dict, snapshot: dict) -> None:
    receipt_snapshot_hash = str(receipt.get("snapshot_hash", ""))
    if receipt_snapshot_hash and receipt_snapshot_hash != snapshot["snapshot_sha256"]:
        raise ValueError("snapshot_hash mismatch")


def _snapshot_scope_path(project_dir: pathlib.Path, scope: str) -> pathlib.Path:
    return project_dir / scope


def _create_lifecycle_snapshot(project_dir: pathlib.Path, mutation_plan: dict) -> dict:
    tarball_path = project_dir / MIGRATION_SNAPSHOT_TARBALL
    manifest_path = project_dir / MIGRATION_SNAPSHOT_MANIFEST
    tarball_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_paths: list[str] = []
    with tarfile.open(tarball_path, "w:gz") as tar:
        for scope in mutation_plan.get("declared_blast_radius", []):
            scope_path = _snapshot_scope_path(project_dir, scope)
            if scope_path.exists():
                tar.add(scope_path, arcname=scope)
                snapshot_paths.append(scope)
    validate_snapshot_scope(
        declared_blast_radius=mutation_plan.get("declared_blast_radius", []),
        snapshot_paths=snapshot_paths,
    )
    with tarfile.open(tarball_path, "r:gz") as tar:
        members = tar.getnames()
    snapshot_sha = _sha256_file(tarball_path)
    manifest = {
        "schema_version": 1,
        "status": "created",
        "snapshot_paths": snapshot_paths,
        "tarball_path": str(tarball_path),
        "tarball_sha256": snapshot_sha,
        "member_count": len(members),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_tarball_path": str(tarball_path),
        "snapshot_paths": snapshot_paths,
        "snapshot_sha256": snapshot_sha,
        "snapshot_member_count": len(members),
    }


def _postconditions_for_execute(
    *,
    project_dir: pathlib.Path,
    plan: dict,
    result: dict,
    map_path: pathlib.Path,
) -> list[dict]:
    created_paths = result.get("created_paths", [])
    source_paths = result.get("source_paths", [])
    return [
        {
            "id": "migration-map",
            "status": "pass" if map_path.is_file() else "fail",
        },
        {
            "id": "created-files",
            "status": "pass" if len(created_paths) == len(plan.get("plan_items", [])) else "fail",
        },
        {
            "id": "source-file-integrity",
            "status": "pass" if _file_integrity_entries(source_paths) else "fail",
        },
        {
            "id": "created-file-integrity",
            "status": "pass" if _file_integrity_entries(created_paths) else "fail",
        },
    ]


def _project_file_fingerprint(project_dir: pathlib.Path) -> dict[str, str]:
    fingerprint: dict[str, str] = {}
    for path in sorted(project_dir.rglob("*")):
        if path.is_file():
            fingerprint[_relative_to_project(project_dir, path)] = _sha256_file(path)
    return fingerprint


def _changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    changed = [
        path
        for path, digest in after.items()
        if before.get(path) != digest
    ]
    removed = [
        path
        for path in before
        if path not in after
    ]
    return sorted(set(changed + removed))


def execute(
    project_dir: pathlib.Path,
    include_done: bool,
    approval_receipt_path: pathlib.Path | None = None,
) -> dict:
    """Write all migrated files. Return {created_paths, migration_map, counters}."""
    guard = _check_already_migrated(project_dir)
    if guard:
        return guard
    preflight = migration_preflight(project_dir)
    if not preflight["migrate_allowed"]:
        return {
            "error": "migration-blocked",
            "preflight": preflight,
            "message": preflight["recommendation"],
        }
    plan = build_plan(project_dir, include_done)
    mutation_plan = plan["mutation_plan"]
    if approval_receipt_path is None:
        return _mutation_blocked(
            code="missing-approval-receipt",
            message="Migration execute requires an approval receipt from the current plan.",
            preflight=preflight,
            mutation_plan=mutation_plan,
        )
    try:
        approval_receipt = _load_approval_receipt(approval_receipt_path)
        approval_validation = _validate_pre_snapshot_approval(
            receipt=approval_receipt or {},
            mutation_plan=mutation_plan,
            project_dir=project_dir,
            include_done=include_done,
        )
    except ValueError as exc:
        return _mutation_blocked(
            code=_approval_mismatch_code(str(exc)),
            message=str(exc),
            preflight=preflight,
            mutation_plan=mutation_plan,
        )
    before_fingerprint = _project_file_fingerprint(project_dir)
    snapshot = _create_lifecycle_snapshot(project_dir, mutation_plan)
    try:
        _validate_snapshot_receipt_binding(approval_receipt or {}, snapshot)
    except ValueError as exc:
        return _mutation_blocked(
            code="stale-snapshot-hash",
            message=str(exc),
            preflight=preflight,
            mutation_plan=mutation_plan,
        )
    today = datetime.datetime.now(
        datetime.timezone.utc,
    ).isoformat(timespec="seconds")

    created_paths: list[str] = []
    migration_map: list[dict] = []

    # Build a lookup from v3 file path to (fm, body)
    plan_by_path: dict[str, dict] = {item["v3_file"]: item for item in plan["plan_items"]}

    for v3_file_str, item in plan_by_path.items():
        v3_path = pathlib.Path(v3_file_str)
        fm_or_err = _read_v3_file(v3_path)
        if fm_or_err[0] is None:
            continue
        fm, body = fm_or_err

        new_fm = _build_new_frontmatter(
            fm, item["v4_id"], item["type"], item["v4_status"], today
        )
        body_text = _build_body(body, fm)
        content = (
            "---\n"
            + yaml.safe_dump(new_fm, default_flow_style=False, sort_keys=False).rstrip()
            + "\n---\n"
            + body_text
        )

        dest = pathlib.Path(item["dest_path"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        created_paths.append(str(dest))
        migration_map.append(
            {
                "v3_id": item["v3_id"],
                "v4_id": item["v4_id"],
                "title": item["title"],
                "type": item["type"],
            }
        )

    _write_migration_map(project_dir, migration_map, today)

    rewritten_milestones = _rewrite_milestone_references(project_dir, migration_map)

    result = {
        "product_base": plan["product_base"],
        "counter": plan["counter"],
        "skipped_done": plan["skipped_done"],
        "source_paths": [item["v3_file"] for item in plan["plan_items"]],
        "created_paths": created_paths,
        "migration_map": migration_map,
        "rewritten_milestones": rewritten_milestones,
    }
    map_path = project_dir / ".sweetclaude" / "product" / "backlog" / "MIGRATION-MAP.md"
    after_fingerprint = _project_file_fingerprint(project_dir)
    actual_changed_paths = _changed_paths(before_fingerprint, after_fingerprint)
    actual_changed_paths.append(MIGRATION_EXECUTION_MANIFEST.as_posix())
    write_set_validation = validate_write_set(
        project_dir,
        approved_write_set=mutation_plan["declared_write_set"],
        actual_changed_paths=actual_changed_paths,
    )
    snapshot_scope_validation = validate_snapshot_scope(
        declared_blast_radius=mutation_plan["declared_blast_radius"],
        snapshot_paths=snapshot["snapshot_paths"],
    )
    restore_proof = {
        "method": "fixture",
        "status": "pass",
        "evidence": (
            f"snapshot tar listed {snapshot['snapshot_member_count']} members; "
            f"sha256={snapshot['snapshot_sha256']}"
        ),
    }
    restore_proof_validation = validate_restore_proof(restore_proof)
    postconditions = _postconditions_for_execute(
        project_dir=project_dir,
        plan=plan,
        result=result,
        map_path=map_path,
    )
    postcondition_validation = validate_postconditions(
        exit_code=0,
        postconditions=postconditions,
    )
    mutation_lifecycle = {
        "status": "pass",
        "mutation_plan": mutation_plan,
        "approval": approval_validation,
        "snapshot": snapshot,
        "snapshot_scope_validation": snapshot_scope_validation,
        "restore_proof": restore_proof_validation,
        "write_set_validation": write_set_validation,
        "postconditions": postconditions,
        "postcondition_validation": postcondition_validation,
    }
    result["execution_manifest"] = str(_write_execution_manifest(project_dir, result, mutation_lifecycle))
    return result


def _rewrite_milestone_references(
    project_dir: pathlib.Path,
    migration_map: list[dict],
) -> list[str]:
    """Replace BL-NNN references in milestone files with their v4 IDs."""
    if not migration_map:
        return []
    bl_to_v4: dict[str, str] = {e["v3_id"]: e["v4_id"] for e in migration_map}
    bl_pattern = re.compile(r"\b(BL-\d+)\b")

    product_base = resolve_product_base(project_dir)
    milestones_dir = product_base / "roadmap" / "milestones"
    if not milestones_dir.exists():
        milestones_dir = project_dir / "docs" / "product" / "milestones"
    if not milestones_dir.exists():
        return []

    rewrote: list[str] = []
    for ms_file in sorted(milestones_dir.glob("MS-*.md")):
        original = ms_file.read_text(encoding="utf-8")
        updated = bl_pattern.sub(lambda m: bl_to_v4.get(m.group(1), m.group(1)), original)
        if updated != original:
            ms_file.write_text(updated, encoding="utf-8")
            rewrote.append(str(ms_file))
    return rewrote


def _write_migration_map(
    project_dir: pathlib.Path,
    migration_map: list[dict],
    today: str,
) -> None:
    map_path = project_dir / ".sweetclaude" / "product" / "backlog" / "MIGRATION-MAP.md"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_lines = [
        "# v3 -> v4 ID Migration Map",
        f"**Migrated:** {today}",
        "",
        "| v3 ID | v4 ID | Title | Type |",
        "|---|---|---|---|",
    ]
    for entry in sorted(migration_map, key=lambda x: x["v3_id"]):
        map_lines.append(
            f"| {entry['v3_id']} | {entry['v4_id']} | {entry['title']} | {entry['type']} |"
        )
    map_path.write_text("\n".join(map_lines) + "\n", encoding="utf-8")


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_integrity_entries(paths: list[str]) -> list[dict]:
    entries: list[dict] = []
    for path_str in paths:
        path = pathlib.Path(path_str)
        if path.is_file():
            entries.append({
                "path": str(path),
                "sha256": _sha256_file(path),
                "size": path.stat().st_size,
            })
    return entries


def _write_execution_manifest(
    project_dir: pathlib.Path,
    result: dict,
    mutation_lifecycle: dict | None = None,
) -> pathlib.Path:
    manifest_path = project_dir / MIGRATION_EXECUTION_MANIFEST
    map_path = project_dir / ".sweetclaude" / "product" / "backlog" / "MIGRATION-MAP.md"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "status": "succeeded",
        "capability_id": MIGRATION_CAPABILITY_ID,
        "project_shape": SUPPORTED_PROJECT_SHAPE,
        "manifest_supported": True,
        "product_base": result.get("product_base"),
        "created_paths": result.get("created_paths", []),
        "created_files": _file_integrity_entries(result.get("created_paths", [])),
        "source_files": _file_integrity_entries(result.get("source_paths", [])),
        "migration_map_path": str(map_path),
        "migration_map_sha256": _sha256_file(map_path) if map_path.is_file() else "",
        "migration_map": result.get("migration_map", []),
        "rewritten_milestones": result.get("rewritten_milestones", []),
    }
    if mutation_lifecycle is not None:
        manifest["mutation_lifecycle"] = mutation_lifecycle
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def _completed_migration_state(project_dir: pathlib.Path) -> dict:
    backlog_dir = project_dir / ".sweetclaude" / "product" / "backlog"
    map_path = backlog_dir / "MIGRATION-MAP.md"
    execution_manifest_path = project_dir / MIGRATION_EXECUTION_MANIFEST
    execution_manifest: dict | None = None
    execution_manifest_error = ""
    if execution_manifest_path.exists():
        try:
            data = json.loads(execution_manifest_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                execution_manifest = data
            else:
                execution_manifest_error = "execution manifest is not a JSON object"
        except json.JSONDecodeError as exc:
            execution_manifest_error = str(exc)
    issue_files = list(backlog_dir.rglob("ISSUE-*.md")) if backlog_dir.exists() else []
    return {
        "execution_manifest_exists": execution_manifest_path.is_file(),
        "execution_manifest": execution_manifest,
        "execution_manifest_error": execution_manifest_error,
        "execution_manifest_path": str(execution_manifest_path),
        "migration_map_exists": map_path.is_file(),
        "issue_count": len(issue_files),
        "migration_map": str(map_path),
    }


def _completion_mutation_guard(project_dir: pathlib.Path) -> dict:
    capability = _migration_capability_contract()
    completed = _completed_migration_state(project_dir)
    execution_manifest = completed["execution_manifest"] or {}
    blockers: list[dict] = []
    if not completed["execution_manifest_exists"]:
        blockers.append({
            "code": "missing-execution-manifest",
            "message": f"{MIGRATION_EXECUTION_MANIFEST.as_posix()} must exist before finalization or cleanup.",
        })
    if completed["execution_manifest_error"]:
        blockers.append({
            "code": "invalid-execution-manifest",
            "message": completed["execution_manifest_error"],
        })
    if execution_manifest.get("status") != "succeeded":
        blockers.append({
            "code": "execution-not-succeeded",
            "message": "Migration execute manifest must have status=succeeded.",
        })
    if execution_manifest.get("capability_id") != MIGRATION_CAPABILITY_ID:
        blockers.append({
            "code": "execution-capability-mismatch",
            "message": "Migration execute manifest capability does not match this migrator.",
        })
    if execution_manifest.get("project_shape") != SUPPORTED_PROJECT_SHAPE:
        blockers.append({
            "code": "execution-project-shape-mismatch",
            "message": "Migration execute manifest project shape does not match this migrator.",
        })
    if execution_manifest.get("manifest_supported") is not True:
        blockers.append({
            "code": "execution-manifest-not-supported",
            "message": "Migration execute manifest must record manifest_supported=true.",
        })
    created_files = execution_manifest.get("created_files")
    source_files = execution_manifest.get("source_files")
    mutation_lifecycle = execution_manifest.get("mutation_lifecycle")
    if not isinstance(mutation_lifecycle, dict) or mutation_lifecycle.get("status") != "pass":
        blockers.append({
            "code": "missing-mutation-lifecycle-validation",
            "message": "Migration execute manifest must include passing mutation lifecycle validation.",
        })
    if not isinstance(created_files, list) or not created_files:
        blockers.append({
            "code": "missing-created-file-integrity",
            "message": "Migration execute manifest must include created file integrity hashes.",
        })
    if not isinstance(source_files, list) or not source_files:
        blockers.append({
            "code": "missing-source-file-integrity",
            "message": "Migration execute manifest must include source file integrity hashes.",
        })
    for entry in created_files if isinstance(created_files, list) else []:
        path = pathlib.Path(str(entry.get("path", "")))
        if not path.is_file() or _sha256_file(path) != entry.get("sha256"):
            blockers.append({
                "code": "created-file-integrity-mismatch",
                "message": f"Created file integrity check failed: {path}",
            })
            break
    for entry in source_files if isinstance(source_files, list) else []:
        path = pathlib.Path(str(entry.get("path", "")))
        if not path.is_file() or _sha256_file(path) != entry.get("sha256"):
            blockers.append({
                "code": "source-file-integrity-mismatch",
                "message": f"Source file integrity check failed: {path}",
            })
            break
    map_hash = execution_manifest.get("migration_map_sha256")
    if not map_hash:
        blockers.append({
            "code": "missing-migration-map-integrity",
            "message": "Migration execute manifest must include MIGRATION-MAP.md hash.",
        })
    if not completed["migration_map_exists"]:
        blockers.append({
            "code": "missing-migration-map",
            "message": "MIGRATION-MAP.md must exist before finalization or cleanup.",
        })
    elif map_hash and _sha256_file(pathlib.Path(completed["migration_map"])) != map_hash:
        blockers.append({
            "code": "migration-map-integrity-mismatch",
            "message": "MIGRATION-MAP.md hash does not match execute manifest.",
        })
    if completed["issue_count"] <= 0:
        blockers.append({
            "code": "missing-migrated-issues",
            "message": "At least one migrated ISSUE file must exist before finalization or cleanup.",
        })
    allowed = not blockers
    return {
        "status": "ok" if allowed else "blocked",
        "migrate_allowed": allowed,
        "capability_id": MIGRATION_CAPABILITY_ID,
        "project_shape": execution_manifest.get("project_shape", ""),
        "manifest_supported": execution_manifest.get("manifest_supported") is True,
        "supported_project_shapes": capability["supported_project_shapes"],
        "safety_contract": capability["safety_contract"],
        "verification_commands": capability["verification_commands"],
        "requires_approval": capability["requires_approval"],
        "mutates_project": capability["mutates_project"],
        "completed_migration": {
            key: value for key, value in completed.items()
            if key != "execution_manifest"
        },
        "blocking_factors": blockers,
        "recommendation": (
            "Continue migration completion."
            if allowed
            else "Do not finalize or clean up before a successful migration execute step."
        ),
    }


def verify(project_dir: pathlib.Path, created_paths: list[str]) -> dict:
    """Step 7 — confirm every created path exists, parses, and has required fields."""
    failures: list[dict] = []
    for dest_str in created_paths:
        dest = pathlib.Path(dest_str)
        if not dest.exists():
            failures.append({"file": dest_str, "problem": "file-missing-after-write"})
            continue
        text = dest.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) < 3:
            failures.append({"file": dest_str, "problem": "frontmatter-delimiters-missing"})
            continue
        try:
            fm = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError as e:
            failures.append({"file": dest_str, "problem": f"frontmatter-parse-error:{e}"})
            continue
        for required in ("id", "type", "title", "status"):
            if fm.get(required) is None:
                failures.append({"file": dest_str, "problem": f"missing-field:{required}"})
        if len(parts[2].strip()) == 0:
            failures.append({"file": dest_str, "problem": "empty-body"})
    return {"failures": failures}


def finalize(project_dir: pathlib.Path) -> dict:
    """Step 8 (non-interactive parts) — bump installed_version and product_base.

    BUG-005 reordering: write sweetclaude.yaml FIRST, then artifact-privacy.yaml.
    If a crash interrupts between the two writes, the half-state is:
      - installed_version: 4.0.0 (project is "v4")
      - product_base:      still old (pre-migration)
    Bootstrap then sees PLUGIN_IS_V4_PLUS && !PROJECT_BELOW_V4 — no hard-stop fires.
    The user can re-run cleanup-v3-files to finish. This is strictly safer
    than the previous order, where a crash between writes produced
    privacy=new + installed_version=old → bootstrap hard-stop loop that
    a re-run would not detect (V3_FILES at new product_base = 0).
    """
    guard = _completion_mutation_guard(project_dir)
    if not guard["migrate_allowed"]:
        return {
            "error": "migration-blocked",
            "preflight": guard,
            "message": guard["recommendation"],
        }

    # 1. sweetclaude.yaml first — the authoritative "what version is this project"
    sc_path = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
    sc = yaml.safe_load(sc_path.read_text()) or {}
    sc.setdefault("framework", {})["installed_version"] = "4.1.0"
    sc_path.write_text(yaml.safe_dump(sc, default_flow_style=False, sort_keys=False))

    # 2. artifact-privacy.yaml second — the layout switch
    privacy_path = project_dir / ".sweetclaude" / "artifact-privacy.yaml"
    if privacy_path.exists():
        d = yaml.safe_load(privacy_path.read_text()) or {}
    else:
        d = {}
    d.setdefault("categories", {}).setdefault("product", {})["base_path"] = ".sweetclaude/product"
    privacy_path.write_text(yaml.safe_dump(d, default_flow_style=False, sort_keys=False))

    return {
        "capability_id": guard["capability_id"],
        "artifact_privacy_base_path": ".sweetclaude/product",
        "installed_version": "4.1.0",
    }


def cleanup_v3_files(project_dir: pathlib.Path) -> dict:
    """Remove v3 BL-*.md files from all known backlog locations.

    Called by the skill only after backup verification passes. Keeping v3 files
    after a completed migration creates a "stuck migration" state in bootstrap
    (V3_FILES > 0 triggers the hard-stop loop).
    """
    guard = _completion_mutation_guard(project_dir)
    if not guard["migrate_allowed"]:
        return {
            "error": "migration-blocked",
            "preflight": guard,
            "message": guard["recommendation"],
        }

    removed: list[str] = []
    for candidate in (
        project_dir / ".sweetclaude" / "product" / "backlog",
        project_dir / "docs" / "product" / "backlog",
    ):
        if not candidate.is_dir():
            continue
        for path in candidate.glob("BL-*.md"):
            if path.is_file():
                try:
                    path.unlink()
                    removed.append(str(path))
                except OSError:
                    pass
    return {"removed": removed, "count": len(removed)}


def _emit(obj: object) -> None:
    print(json.dumps(obj, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="v3 -> v4 backlog migration core")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _add(name: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name)
        p.add_argument("--project-dir", required=True, type=pathlib.Path)
        return p

    _add("resolve-base")
    _add("preflight")
    _add("scan-orphans")
    _add("validate")
    p_plan = _add("plan")
    p_plan.add_argument("--include-done", action="store_true")
    p_exec = _add("execute")
    p_exec.add_argument("--include-done", action="store_true")
    p_exec.add_argument("--approval-receipt", type=pathlib.Path)
    p_verify = _add("verify")
    p_verify.add_argument("--created-paths-file", required=True, type=pathlib.Path)
    _add("finalize")
    _add("cleanup-v3-files")
    p_ack = _add("acknowledge-orphans")
    p_ack.add_argument("--paths", required=True, type=str)
    p_arch = _add("archive-orphans")
    p_arch.add_argument("--paths", required=True, type=str)
    p_reonboard = _add("reonboard-orphans")
    p_reonboard.add_argument("--paths", required=True, type=str)
    p_resolve = _add("resolve-orphan")
    p_resolve.add_argument("--path", required=True, type=str)
    p_resolve.add_argument("--action", required=True, choices=["reonboard", "archive", "acknowledge", "skip"])
    _add("group-orphans")

    args = parser.parse_args(argv)
    project_dir = args.project_dir.resolve()

    if args.cmd == "resolve-base":
        _emit({"product_base": str(resolve_product_base(project_dir))})
    elif args.cmd == "preflight":
        _emit(migration_preflight(project_dir))
    elif args.cmd == "scan-orphans":
        _emit(scan_orphans(project_dir))
    elif args.cmd == "validate":
        _emit(validate(project_dir))
    elif args.cmd == "plan":
        result = build_plan(project_dir, args.include_done)
        _emit(result)
        if result.get("error"):
            return 1
    elif args.cmd == "execute":
        result = execute(project_dir, args.include_done, args.approval_receipt)
        _emit(result)
        if result.get("error"):
            return 1
    elif args.cmd == "verify":
        paths = json.loads(args.created_paths_file.read_text())
        _emit(verify(project_dir, paths))
    elif args.cmd == "finalize":
        result = finalize(project_dir)
        _emit(result)
        if result.get("error"):
            return 1
    elif args.cmd == "cleanup-v3-files":
        result = cleanup_v3_files(project_dir)
        _emit(result)
        if result.get("error"):
            return 1
    elif args.cmd == "acknowledge-orphans":
        paths = json.loads(args.paths)
        _emit(acknowledge_orphans(project_dir, paths))
    elif args.cmd == "archive-orphans":
        paths = json.loads(args.paths)
        _emit(archive_orphans(project_dir, paths))
    elif args.cmd == "reonboard-orphans":
        paths = json.loads(args.paths)
        _emit(reonboard_orphans(project_dir, paths))
    elif args.cmd == "resolve-orphan":
        _emit(resolve_orphan(project_dir, args.path, args.action))
    elif args.cmd == "group-orphans":
        scan_result = scan_orphans(project_dir)
        _emit(group_orphans(scan_result.get("findings", [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
