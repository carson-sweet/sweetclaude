#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Step 4b helper for skill-library/configure/_migrate/SKILL.md.

Executes a migration rollback from a SnapshotInfo JSON string and removes
the pending-migration-snapshot.json marker on success.

Usage:
    python3 run_rollback.py <runner_path> <snapshot_json> [project_dir]

Outputs one line:
    ROLLBACK_OK|<msg>    — success
    ROLLBACK_FAIL|<msg>  — failure; caller should surface the reason
"""

from __future__ import annotations

import json
import sys
from pathlib import Path



def _import_runner(runner_path: str):
    """Import the migration runner, honouring the path the caller passed.

    Loads runner_path by explicit file location when it exists, so a caller
    that points at a specific install gets that install's runner. Falls back
    to the module sitting beside this script when the given path is missing or
    empty — that fallback is what kept migrations working while the argument
    was silently ignored, and dropping it would turn a stale $RUNNER into a
    hard failure. Raises ImportError when neither is available. (ISSUE-267)
    """
    import importlib.util

    candidates = []
    if runner_path:
        candidates.append(Path(runner_path))
    candidates.append(Path(__file__).resolve().parent / "runner.py")

    for candidate in candidates:
        if not candidate.is_file():
            continue
        spec = importlib.util.spec_from_file_location("sweetclaude_migration_runner", candidate)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("sweetclaude_migration_runner", module)
        spec.loader.exec_module(module)
        return module

    raise ImportError(
        f"no runner module found at {runner_path!r} or beside {Path(__file__).name}"
    )


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("ROLLBACK_FAIL|usage: run_rollback.py <runner_path> <snapshot_json> [project_dir]")
        return 1

    runner_path = argv[1]
    snapshot_json = argv[2]
    project_dir = str(Path(argv[3]).resolve()) if len(argv) > 3 else "."

    try:
        runner_mod = _import_runner(runner_path)
        MigrationRunner = runner_mod.MigrationRunner
        SnapshotInfo = runner_mod.SnapshotInfo
    except ImportError as e:
        print(f"ROLLBACK_FAIL|cannot import runner: {e}")
        return 1

    try:
        snap_data = json.loads(snapshot_json)
        snap = SnapshotInfo(**snap_data)
    except Exception as e:
        print(f"ROLLBACK_FAIL|invalid snapshot JSON: {e}")
        return 1

    runner = MigrationRunner(project_dir=project_dir)
    ok, reason = runner.rollback(snap)

    if ok:
        marker = Path(project_dir) / ".sweetclaude" / "state" / "pending-migration-snapshot.json"
        try:
            marker.unlink(missing_ok=True)
        except OSError:
            pass
        print(f"ROLLBACK_OK|{reason or ''}")
        return 0
    else:
        print(f"ROLLBACK_FAIL|{reason or 'unknown error'}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
