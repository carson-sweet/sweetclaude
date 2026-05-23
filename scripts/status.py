#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
SweetClaude status module — canonical work-item status lifecycle.

Public API:
  CANONICAL_STATUSES  frozenset of 11 valid status values
  TERMINAL_STATUSES   frozenset of 4 terminal status values
  validate(value)     bool
  assert_valid(value) raises ValueError if not canonical
  validate_transition(old, new, entity_type, reopen=False)
  write_status(filepath, new_status, actor, project_dir=None)
  set_terminal(filepath, status, actor, project_dir=None)
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required: pip install pyyaml")

CANONICAL_STATUSES: frozenset[str] = frozenset({
    "new", "ready", "active", "in-review", "blocked",
    "on-hold", "deferred", "done", "declined", "abandoned", "superseded",
})

TERMINAL_STATUSES: frozenset[str] = frozenset({
    "done", "declined", "abandoned", "superseded",
})


def validate(value) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        return False
    return value in CANONICAL_STATUSES


def assert_valid(value) -> None:
    if not validate(value):
        valid_list = sorted(CANONICAL_STATUSES)
        raise ValueError(
            f"Invalid status {value!r}. Valid statuses: {valid_list}"
        )


def validate_transition(old: str, new: str, entity_type: str, reopen: bool = False) -> bool:
    if old not in CANONICAL_STATUSES:
        raise ValueError(f"Invalid status {old!r}. Valid statuses: {sorted(CANONICAL_STATUSES)}")
    if new not in CANONICAL_STATUSES:
        raise ValueError(f"Invalid status {new!r}. Valid statuses: {sorted(CANONICAL_STATUSES)}")
    if old == new:
        return True
    if old in TERMINAL_STATUSES and new not in TERMINAL_STATUSES:
        if not reopen:
            raise ValueError(
                f"Cannot transition from terminal status {old!r} to {new!r} without reopen=True"
            )
    return True


def _parse_frontmatter(raw: str) -> tuple[dict, str, str]:
    normalized = raw.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    parts = normalized.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Missing frontmatter delimiters (---)")
    fm_text = parts[1]
    body = parts[2]
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError as e:
        raise ValueError(f"frontmatter YAML parse error: {e}")
    if fm is None or not isinstance(fm, dict):
        raise ValueError("frontmatter is empty or missing status key")
    return fm, fm_text, body


def _resolve_project_dir(filepath: str, project_dir: str | None) -> Path:
    if project_dir:
        return Path(project_dir)
    return Path(filepath).resolve().parent


def _audit_log_path(project_dir: Path) -> Path:
    return project_dir / ".sweetclaude" / "metrics" / "status-audit.jsonl"


def _append_audit(project_dir: Path, actor: str, entity: str, file_rel: str, old: str, new: str) -> None:
    log_path = _audit_log_path(project_dir)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actor": actor,
        "entity": entity,
        "file": file_rel,
        "old": old,
        "new": new,
    }
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _normalize_status_field(value: str) -> str:
    from schema import normalize_status
    return normalize_status(value)


def _trigger_cache_rebuild(project_dir: Path) -> None:
    try:
        _scripts_dir = Path(__file__).resolve().parent
        if str(_scripts_dir) not in sys.path:
            sys.path.insert(0, str(_scripts_dir))
        from cache import rebuild as _rebuild
        _rebuild(str(project_dir))
    except Exception as e:
        print(f"WARNING: cache rebuild failed after status change: {e}", file=sys.stderr)


def _atomic_write_frontmatter(filepath: Path, fm: dict, body: str) -> None:
    fm_text = yaml.safe_dump(fm, default_flow_style=False, allow_unicode=True)
    new_content = f"---\n{fm_text}---\n{body}"
    fd, tmp = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp")
    try:
        os.write(fd, new_content.encode("utf-8"))
    finally:
        os.close(fd)
    try:
        os.replace(tmp, str(filepath))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_status(filepath: str, new_status: str, actor: str, project_dir: str | None = None, reopen: bool = False) -> None:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    assert_valid(new_status)

    if new_status in TERMINAL_STATUSES:
        raise ValueError(
            f"Cannot use write_status() to set terminal status {new_status!r}. "
            f"Use set_terminal() instead."
        )

    parts = path.parts
    if "done" in parts[:-1]:
        if new_status not in TERMINAL_STATUSES:
            raise ValueError(
                f"File is in a done/ directory; cannot set non-terminal status {new_status!r}"
            )

    raw = path.read_text(encoding="utf-8-sig")
    fm, _fm_text, body = _parse_frontmatter(raw)

    if "status" not in fm:
        raise ValueError(f"frontmatter is missing status key in {filepath}")

    from schema import validate_frontmatter
    fm_check = dict(fm)
    fm_check["status"] = _normalize_status_field(fm_check.get("status", ""))
    violations = validate_frontmatter(fm_check)
    if violations:
        raise ValueError(
            f"Cannot write status to structurally invalid file {filepath}: "
            + "; ".join(violations)
        )

    old_status = fm_check["status"]

    if old_status == new_status:
        return

    validate_transition(old_status, new_status, "issue", reopen=reopen)

    fm["status"] = new_status
    fm["updated"] = datetime.date.today().isoformat()
    _atomic_write_frontmatter(path, fm, body)

    pd = _resolve_project_dir(filepath, project_dir)
    entity = fm.get("id", path.stem)
    try:
        file_rel = str(path.relative_to(pd))
    except ValueError:
        file_rel = str(path)

    _append_audit(pd, actor, entity, file_rel, old_status, new_status)
    _trigger_cache_rebuild(pd)


def _check_completion_criteria(fm: dict, filepath: str) -> None:
    criteria = fm.get("completion_criteria")
    if not criteria or not isinstance(criteria, list):
        return
    valid = [c for c in criteria if isinstance(c, dict)]
    if not valid:
        return
    total = len(valid)
    done = sum(1 for c in valid if c.get("done", False))
    if done < total:
        unmet = [
            c.get("description", f"criterion #{i}")
            for i, c in enumerate(valid)
            if not c.get("done", False)
        ]
        raise ValueError(
            f"Cannot mark epic done: {done} of {total} completion criteria met. "
            f"Unmet criteria in {filepath}:\n"
            + "\n".join(f"  - {d}" for d in unmet)
        )


def _dest_dir_for_terminal(filepath: Path) -> Path:
    parts = filepath.parts
    parent = filepath.parent
    parent_name = parent.name
    if parent_name == "backlog":
        return parent / "archived"
    return parent / "done"


def set_terminal(filepath: str, status: str, actor: str, project_dir: str | None = None) -> None:
    if status not in TERMINAL_STATUSES:
        raise ValueError(
            f"set_terminal() requires a terminal status; {status!r} is not terminal. "
            f"Terminal statuses: {sorted(TERMINAL_STATUSES)}"
        )

    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    raw = path.read_text(encoding="utf-8-sig")
    fm, _fm_text, body = _parse_frontmatter(raw)

    if "status" not in fm:
        raise ValueError(f"frontmatter is missing status key in {filepath}")

    from schema import validate_frontmatter
    fm_check = dict(fm)
    fm_check["status"] = _normalize_status_field(fm_check.get("status", ""))
    violations = validate_frontmatter(fm_check)
    if violations:
        raise ValueError(
            f"Cannot set terminal status on structurally invalid file {filepath}: "
            + "; ".join(violations)
        )

    old_status = fm_check["status"]
    validate_transition(old_status, status, "issue")

    if fm.get("type") == "epic" and status == "done":
        _check_completion_criteria(fm, filepath)

    dest_dir = _dest_dir_for_terminal(path)
    dest_path = dest_dir / path.name

    if dest_path.exists():
        raise FileExistsError(
            f"Destination already exists: {dest_path}"
        )

    dest_dir.mkdir(parents=True, exist_ok=True)

    fm["status"] = status
    fm["closed_date"] = datetime.date.today().isoformat()
    fm["updated"] = datetime.date.today().isoformat()
    updated_content = "---\n" + yaml.safe_dump(fm, default_flow_style=False, allow_unicode=True) + "---\n" + body

    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, updated_content.encode("utf-8"))
    finally:
        os.close(fd)

    try:
        os.replace(tmp, str(dest_path))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

    try:
        path.unlink()
    except OSError as e:
        try:
            dest_path.unlink()
        except OSError:
            pass
        raise RuntimeError(f"Move failed; rolled back: {e}") from e

    pd = _resolve_project_dir(filepath, project_dir)
    entity = fm.get("id", path.stem)
    try:
        file_rel = str(dest_path.relative_to(pd))
    except ValueError:
        file_rel = str(dest_path)

    _append_audit(pd, actor, entity, file_rel, old_status, status)
    _trigger_cache_rebuild(pd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SweetClaude status CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set")
    p_set.add_argument("--file", required=True)
    p_set.add_argument("--status", required=True)
    p_set.add_argument("--actor", default=None)
    p_set.add_argument("--project-dir", default=None)
    p_set.add_argument("--reopen", action="store_true", default=False)

    p_terminal = sub.add_parser("set-terminal")
    p_terminal.add_argument("--file", required=True)
    p_terminal.add_argument("--status", required=True)
    p_terminal.add_argument("--actor", default=None)
    p_terminal.add_argument("--project-dir", default=None)

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("--status", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        if validate(args.status):
            return 0
        return 1

    if args.actor is None:
        print(json.dumps({"error": "actor is required"}))
        return 1

    if args.cmd == "set":
        try:
            write_status(args.file, args.status, args.actor, project_dir=args.project_dir, reopen=args.reopen)
            print(json.dumps({"status": args.status, "file": args.file}))
            return 0
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            return 1

    if args.cmd == "set-terminal":
        try:
            set_terminal(args.file, args.status, args.actor, project_dir=args.project_dir)
            print(json.dumps({"status": args.status, "file": args.file}))
            return 0
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
