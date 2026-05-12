#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Step 2 helper for skills/_migrate/SKILL.md.

Runs the migration and prints the results as JSON.

Usage:
    python3 run_migrate.py <runner_path> [project_dir]

Outputs a JSON array of migration result objects. Each object has:
    file_key, success, failure_mode, failure_details,
    on_disk_version_before, on_disk_version_after, target_version, recovery_menu
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(json.dumps({"error": "usage: run_migrate.py <runner_path> [project_dir]"}))
        return 1

    runner_path = argv[1]
    project_dir = str(Path(argv[2]).resolve()) if len(argv) > 2 else "."

    sys.path.insert(0, str(Path(runner_path).parent))
    try:
        from runner import MigrationRunner  # type: ignore[import]
    except ImportError as e:
        print(json.dumps({"error": f"cannot import runner: {e}"}))
        return 1

    runner = MigrationRunner(project_dir=project_dir)
    results = runner.run()
    out = [
        {
            "file_key": r.file_key,
            "success": r.success,
            "failure_mode": r.failure_mode,
            "failure_details": r.failure_details,
            "on_disk_version_before": r.on_disk_version_before,
            "on_disk_version_after": r.on_disk_version_after,
            "target_version": r.target_version,
            "recovery_menu": r.recovery_menu,
        }
        for r in results
    ]
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
