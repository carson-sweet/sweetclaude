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


V3_VALID_STATUSES = {"backlog", "in_progress", "done", "cancelled", "blocked", "abandoned"}
VALID_TYPES = {"story", "bug", "debt", "chore"}
TYPE_PREFIX = {"story": "STORY", "bug": "BUG", "debt": "DEBT", "chore": "CHORE"}
TYPE_DIR = {"story": "stories", "bug": "bugs", "debt": "debt", "chore": "chores"}
TERMINAL_STATUSES = {"done", "abandoned"}

# Status remapping from v3 to v4 vocabulary.
STATUS_REMAP = {
    "backlog": "new",
    "cancelled": "abandoned",
    "in_progress": "active",
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


def _read_v3_file(path: pathlib.Path) -> tuple[dict, str] | tuple[None, str]:
    """Return (frontmatter_dict, body_text) or (None, error_reason)."""
    raw = path.read_bytes()
    if raw[:3] == b"\xef\xbb\xbf":
        raw = raw[3:]
    text = raw.decode("utf-8").replace("\r\n", "\n")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "no-frontmatter-delimiter"
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return None, f"frontmatter-parse-error:{e}"
    if not isinstance(fm, dict):
        return None, f"frontmatter-not-a-dict:{type(fm).__name__}"
    return fm, parts[2]


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
        for field in ("id", "type", "title", "status"):
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

    counters = {"story": 0, "bug": 0, "debt": 0, "chore": 0}
    plan_items: list[dict] = []
    skipped_done = 0

    for path in files:
        fm_or_err = _read_v3_file(path)
        if fm_or_err[0] is None:
            # Validation should have caught this — but in case caller skipped validate, be defensive.
            continue
        fm, _ = fm_or_err

        typ = (fm.get("type") or "story").lower()
        if typ not in counters:
            typ = "story"

        v3_status = fm.get("status", "backlog")
        v4_status = STATUS_REMAP.get(v3_status, v3_status)
        is_terminal = v4_status in TERMINAL_STATUSES

        if is_terminal and not include_done:
            skipped_done += 1
            continue

        counters[typ] += 1
        new_id = f"{TYPE_PREFIX[typ]}-{counters[typ]:03d}"
        slug = _make_slug(fm.get("title", ""))

        subdir = f"{TYPE_DIR[typ]}/done" if is_terminal else TYPE_DIR[typ]
        dest = project_dir / "docs" / "product" / "backlog" / subdir / f"{new_id}-{slug}.md"

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
        "counters": counters,
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
        "priority": fm.get("priority", "soon"),
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
    """Idempotency guard (BUG-005): refuse to overwrite a populated v4 state.

    If installed_version is already 4.x AND docs/product/backlog/INDEX.md has
    non-zero counters, re-running execute would clobber the INDEX with a
    new empty one (because counters start at 0 each run). That's the
    half-state recovery hazard. Refuse and direct the user to the right tool.
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
    index_path = project_dir / "docs" / "product" / "backlog" / "INDEX.md"
    if not index_path.exists():
        return None
    raw = index_path.read_text()
    if "---" not in raw:
        return None
    try:
        fm = yaml.safe_load(raw.split("---", 2)[1]) or {}
    except yaml.YAMLError:
        return None
    counters = fm.get("counters") or {}
    total = sum(v for v in counters.values() if isinstance(v, int))
    if total <= 0:
        return None
    return {
        "error": "already-migrated",
        "installed_version": installed,
        "index_counter_sum": total,
        "message": (
            f"Project is already at installed_version={installed} with a populated "
            f"INDEX.md ({total} entries). Re-running execute would overwrite the "
            f"existing INDEX with empty counters. If a previous migration was "
            f"interrupted and you need to clean up residual v3 BL files, run "
            f"`migrate-v3-to-v4.py cleanup-v3-files` instead."
        ),
    }


def execute(project_dir: pathlib.Path, include_done: bool) -> dict:
    """Write all migrated files. Return {created_paths, migration_map, counters}."""
    guard = _check_already_migrated(project_dir)
    if guard:
        return guard
    plan = build_plan(project_dir, include_done)
    today = datetime.date.today().isoformat()

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

    # Regenerate INDEX.md and MIGRATION-MAP.md
    _write_index_and_map(project_dir, plan["counters"], migration_map, created_paths, today)

    return {
        "product_base": plan["product_base"],
        "counters": plan["counters"],
        "skipped_done": plan["skipped_done"],
        "created_paths": created_paths,
        "migration_map": migration_map,
    }


def _make_table(items: list[dict]) -> str:
    header = "| ID | Title | Status | Priority | Effort | Tags |\n|---|---|---|---|---|---|"
    if not items:
        return header
    lines = [header]
    for fm in items:
        tags = ", ".join(fm.get("tags", []) or [])
        lines.append(
            f"| {fm['id']} | {fm['title']} | {fm['status']} | "
            f"{fm.get('priority', '')} | {fm.get('effort', '')} | {tags} |"
        )
    return "\n".join(lines)


def _write_index_and_map(
    project_dir: pathlib.Path,
    counters: dict[str, int],
    migration_map: list[dict],
    created_paths: list[str],
    today: str,
) -> None:
    index_path = project_dir / "docs" / "product" / "backlog" / "INDEX.md"
    rows: dict[str, list[dict]] = {"story": [], "bug": [], "debt": [], "chore": []}

    for dest_str in created_paths:
        if "/done/" in dest_str:
            continue
        dest = pathlib.Path(dest_str)
        raw = dest.read_text(encoding="utf-8")
        parts = raw.split("---", 2)
        if len(parts) < 3:
            continue
        fm = yaml.safe_load(parts[1]) or {}
        typ = fm.get("type", "story")
        if typ in rows:
            rows[typ].append(fm)

    index_content = (
        f"---\n"
        f"counters:\n"
        f"  story: {counters['story']}\n"
        f"  bug: {counters['bug']}\n"
        f"  debt: {counters['debt']}\n"
        f"  chore: {counters['chore']}\n"
        f"updated: {today}\n"
        f"---\n\n"
        f"# Backlog INDEX\n\n"
        f"This file is the source of truth for backlog counter state and the visible table of unscheduled work.\n\n"
        f"## Stories\n{_make_table(rows['story'])}\n\n"
        f"## Bugs\n{_make_table(rows['bug'])}\n\n"
        f"## Debt\n{_make_table(rows['debt'])}\n\n"
        f"## Chores\n{_make_table(rows['chore'])}\n"
    )
    index_path.write_text(index_content, encoding="utf-8")

    map_path = project_dir / "docs" / "product" / "backlog" / "MIGRATION-MAP.md"
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
    sc.setdefault("framework", {})["installed_version"] = "4.0.0"
    sc_path.write_text(yaml.safe_dump(sc, default_flow_style=False, sort_keys=False))

    # 2. artifact-privacy.yaml second — the layout switch
    privacy_path = project_dir / ".sweetclaude" / "artifact-privacy.yaml"
    if privacy_path.exists():
        d = yaml.safe_load(privacy_path.read_text()) or {}
    else:
        d = {}
    d.setdefault("categories", {}).setdefault("product", {})["base_path"] = "docs/product"
    privacy_path.write_text(yaml.safe_dump(d, default_flow_style=False, sort_keys=False))

    return {
        "artifact_privacy_base_path": "docs/product",
        "installed_version": "4.0.0",
    }


def cleanup_v3_files(project_dir: pathlib.Path) -> dict:
    """Remove v3 BL-*.md files from the (pre-finalize) product_base/backlog directory.

    Called by the skill only after backup verification passes. Keeping v3 files
    after a completed migration creates a "stuck migration" state in bootstrap
    (V3_FILES > 0 + installed_version: 4.0.0 triggers the hard-stop loop).
    """
    # After finalize, product_base in artifact-privacy.yaml is `docs/product`.
    # But the v3 files we want to remove may live at the OLD product_base
    # (`.sweetclaude/product`) if that was the v3 layout. We need to clean both
    # potential locations: the OLD .sweetclaude/product/backlog AND the current
    # docs/product/backlog. The docs/product/backlog now contains v4 output —
    # so we only target files matching BL-*.md, never STORY-/BUG-/DEBT-/CHORE-.
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
