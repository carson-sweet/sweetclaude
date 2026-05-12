#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Step 4b helper for skills/_migrate/SKILL.md.

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


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("ROLLBACK_FAIL|usage: run_rollback.py <runner_path> <snapshot_json> [project_dir]")
        return 1

    runner_path = argv[1]
    snapshot_json = argv[2]
    project_dir = str(Path(argv[3]).resolve()) if len(argv) > 3 else "."

    sys.path.insert(0, str(Path(runner_path).parent))
    try:
        from runner import MigrationRunner, SnapshotInfo  # type: ignore[import]
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
