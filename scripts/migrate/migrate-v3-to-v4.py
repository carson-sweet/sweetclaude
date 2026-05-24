#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
v3 -> v4 backlog migration core.

Pure, deterministic operations extracted from skills/migrate/SKILL.md so the
migration can be tested end-to-end without an LLM in the loop. The skill
remains responsible for: lock/backup (Step 1), user prompts (Step 3 done-
item choice, Step 4 preview confirmation, Step 8 delete prompt), and the
overall flow orchestration. This script provides the operations the skill
delegates to.

CLI subcommands:
  resolve-base       --project-dir DIR
  scan-orphans       --project-dir DIR
  validate           --project-dir DIR
  plan               --project-dir DIR [--include-done]
  execute            --project-dir DIR [--include-done]
  verify             --project-dir DIR --created-paths-file FILE
  finalize           --project-dir DIR

All commands emit JSON on stdout. Errors emit on stderr; exit 1 on failure.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys

import yaml


V3_VALID_STATUSES = {"backlog", "in_progress", "done", "cancelled", "blocked", "abandoned", "deferred"}
VALID_TYPES = {"story", "bug", "debt", "chore"}
TERMINAL_STATUSES = {"done", "abandoned"}

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


_WORK_ITEM_PATTERNS = ["BL-*.md", "STORY-*.md", "BUG-*.md", "DEBT-*.md", "CHORE-*.md", "ISSUE-*.md"]
_TYPED_SUBDIRS = ["stories", "bugs", "debt", "chores"]


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


def scan_orphans(project_dir: pathlib.Path) -> dict:
    """Scan all known SweetClaude locations for orphaned work item files.

    Returns categorized findings so the skill can present them to the user.
    """
    product_base = resolve_product_base(project_dir)
    backlog_path = product_base / "backlog"
    primary_bl_files = {str(p) for p in backlog_path.glob("BL-*.md")} if backlog_path.exists() else set()

    findings: list[dict] = []
    seen: set[str] = set()

    def _add(path: pathlib.Path, category: str, detail: str) -> None:
        key = str(path.resolve())
        if key in seen or str(path) in primary_bl_files:
            return
        seen.add(key)
        fm = _sniff_frontmatter(path)
        findings.append({
            "file": str(path),
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

    # 2. Work-item-patterned files anywhere under search roots (not already in primary set)
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in _WORK_ITEM_PATTERNS:
            for p in root.rglob(pattern):
                if "done/" in str(p) or "archived/" in str(p):
                    _add(p, "archived", "in done/ or archived/ directory")
                else:
                    _add(p, "stray-file", f"matches {pattern} outside expected location")

    # 3. BL-*.md in unexpected locations (wrong base path, nested)
    for root in search_roots:
        if not root.exists():
            continue
        for p in root.rglob("BL-*.md"):
            if str(p) not in primary_bl_files:
                _add(p, "bl-wrong-location", "BL file outside primary backlog directory")

    # 4. scratch/ — markdown files that look like work items
    scratch_dir = project_dir / "scratch"
    if scratch_dir.is_dir():
        for p in scratch_dir.rglob("*.md"):
            fm = _sniff_frontmatter(p)
            if fm is not None:
                _add(p, "scratch", "work item found in scratch/")

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


def build_plan(project_dir: pathlib.Path, include_done: bool) -> dict:
    """Compute the migration plan without writing. Same logic as execute() but no I/O."""
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

    return {
        "product_base": str(product_base),
        "counter": counter,
        "skipped_done": skipped_done,
        "plan_items": plan_items,
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

    If installed_version is already 4.x AND ISSUE-*.md files exist in
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
    if not installed.startswith("4."):
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


def execute(project_dir: pathlib.Path, include_done: bool) -> dict:
    """Write all migrated files. Return {created_paths, migration_map, counters}."""
    guard = _check_already_migrated(project_dir)
    if guard:
        return guard
    plan = build_plan(project_dir, include_done)
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

    return {
        "product_base": plan["product_base"],
        "counter": plan["counter"],
        "skipped_done": plan["skipped_done"],
        "created_paths": created_paths,
        "migration_map": migration_map,
        "rewritten_milestones": rewritten_milestones,
    }


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
    Bootstrap then sees PLUGIN_IS_V4 && !PROJECT_NOT_V4 — no hard-stop fires.
    The user can re-run cleanup-v3-files to finish. This is strictly safer
    than the previous order, where a crash between writes produced
    privacy=new + installed_version=old → bootstrap hard-stop loop that
    a re-run would not detect (V3_FILES at new product_base = 0).
    """
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
        "artifact_privacy_base_path": ".sweetclaude/product",
        "installed_version": "4.1.0",
    }


def cleanup_v3_files(project_dir: pathlib.Path) -> dict:
    """Remove v3 BL-*.md files from all known backlog locations.

    Called by the skill only after backup verification passes. Keeping v3 files
    after a completed migration creates a "stuck migration" state in bootstrap
    (V3_FILES > 0 triggers the hard-stop loop).
    """
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
    _add("scan-orphans")
    _add("validate")
    p_plan = _add("plan")
    p_plan.add_argument("--include-done", action="store_true")
    p_exec = _add("execute")
    p_exec.add_argument("--include-done", action="store_true")
    p_verify = _add("verify")
    p_verify.add_argument("--created-paths-file", required=True, type=pathlib.Path)
    _add("finalize")
    _add("cleanup-v3-files")

    args = parser.parse_args(argv)
    project_dir = args.project_dir.resolve()

    if args.cmd == "resolve-base":
        _emit({"product_base": str(resolve_product_base(project_dir))})
    elif args.cmd == "scan-orphans":
        _emit(scan_orphans(project_dir))
    elif args.cmd == "validate":
        _emit(validate(project_dir))
    elif args.cmd == "plan":
        _emit(build_plan(project_dir, args.include_done))
    elif args.cmd == "execute":
        result = execute(project_dir, args.include_done)
        _emit(result)
        if result.get("error"):
            return 1
    elif args.cmd == "verify":
        paths = json.loads(args.created_paths_file.read_text())
        _emit(verify(project_dir, paths))
    elif args.cmd == "finalize":
        _emit(finalize(project_dir))
    elif args.cmd == "cleanup-v3-files":
        _emit(cleanup_v3_files(project_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
