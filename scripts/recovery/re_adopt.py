#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Re-adopt: the universal, no-data-loss terminal fallback.

When no other doctor route resolves a project's state — including layouts with
no validated migrator — re-adopt archives the SweetClaude state directory aside
(reversibly) so the project can be re-onboarded fresh against its existing,
untouched source and artifacts.

Guarantees:
- No data loss: `.sweetclaude/` is MOVED (not deleted) into a timestamped
  `.sweetclaude.legacy/<ts>/` archive; every file is preserved.
- Reversible: reverse_re_adopt moves it back.
- Non-destructive to the rest of the project: source code and relocated
  artifact bases (e.g. docs/product) are left exactly where they are, so a
  re-onboarding pass adopts the existing project rather than losing it.

This module is human-gated by design: it is invoked deliberately (doctor names
it as the terminal fallback), never as an automatic fix recipe.
"""
from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path
from typing import Any


def _timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def plan_re_adopt(project_dir: str | Path) -> dict[str, Any]:
    """Read-only: describe exactly what execute_re_adopt would do."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    sc = project / ".sweetclaude"
    if not sc.exists():
        return {
            "ok": False,
            "reason": "No .sweetclaude/ state to archive; nothing to re-adopt.",
        }
    file_count = sum(1 for f in sc.rglob("*") if f.is_file())
    return {
        "ok": True,
        "archives": [".sweetclaude"],
        "legacy_root": ".sweetclaude.legacy/<timestamp>/",
        "files_to_archive": file_count,
        "preserves_untouched": ["project source", "relocated artifact bases (per artifact-privacy)"],
        "no_data_loss": True,
        "reversible": True,
        "next_step": (
            "After archiving, re-onboard: run /sweetclaude:configure init (or /sweetclaude:go "
            "and describe the project) to adopt the existing project. The archived "
            "state remains at the legacy path for manual reference/port."
        ),
    }


def execute_re_adopt(project_dir: str | Path) -> dict[str, Any]:
    """Snapshot-first, reversible archive of .sweetclaude/. No data loss."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    sc = project / ".sweetclaude"
    if not sc.exists():
        return {
            "ok": False,
            "reason": "No .sweetclaude/ state to archive; nothing to re-adopt.",
        }
    legacy_root = project / ".sweetclaude.legacy" / _timestamp()
    legacy_root.mkdir(parents=True, exist_ok=True)
    dest = legacy_root / ".sweetclaude"
    # move preserves every file and clears the root for a fresh re-onboard
    shutil.move(str(sc), str(dest))
    return {
        "ok": True,
        "legacy_path": str(legacy_root),
        "archived": str(dest),
        "reversible": True,
        "next_step": (
            "Re-onboard with /sweetclaude:configure init (or /sweetclaude:go). Existing "
            "source and relocated artifacts are untouched. Archived state is at "
            f"{legacy_root}."
        ),
    }


def reverse_re_adopt(project_dir: str | Path, legacy_path: str | Path) -> dict[str, Any]:
    """Undo execute_re_adopt: restore the archived .sweetclaude/."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    legacy = Path(legacy_path)
    archived = legacy / ".sweetclaude"
    sc = project / ".sweetclaude"
    if not archived.exists():
        return {"ok": False, "reason": f"No archived state at {archived}."}
    if sc.exists():
        return {"ok": False, "reason": f"{sc} already exists; refusing to overwrite."}
    shutil.move(str(archived), str(sc))
    return {"ok": True, "restored": str(sc)}


def main(argv: list[str] | None = None) -> int:
    """CLI so doctor can drive the re-onboard archive through a script call
    rather than a skill-side mv. Reuses the functions above — no reimplementation
    of the archiving. JSON to stdout; non-zero exit when the operation fails so
    callers can detect it."""
    parser = argparse.ArgumentParser(
        description="Re-adopt: archive .sweetclaude/ aside (reversible) and "
        "re-onboard via sweetclaude:library-load init.")
    subparsers = parser.add_subparsers(dest="command")

    plan_parser = subparsers.add_parser(
        "plan", help="Read-only: describe what execute would archive.")
    plan_parser.add_argument("--project-dir", default=".", help="Project directory")
    plan_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    execute_parser = subparsers.add_parser(
        "execute",
        help="Archive .sweetclaude/ to .sweetclaude.legacy/<ts>/ (reversible).")
    execute_parser.add_argument("--project-dir", default=".", help="Project directory")
    execute_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    args = parser.parse_args(argv)

    if args.command == "plan":
        result = plan_re_adopt(args.project_dir)
    elif args.command == "execute":
        result = execute_re_adopt(args.project_dir)
    else:
        parser.error("a command is required: plan | execute")
        return 2  # unreachable — parser.error exits

    pretty = bool(getattr(args, "pretty", False))
    print(json.dumps(result, indent=2 if pretty else None, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
