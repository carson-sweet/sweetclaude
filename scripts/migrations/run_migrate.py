#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Step 2 helper for skill-library/configure/_migrate/SKILL.md.

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
    if len(argv) < 2:
        print(json.dumps({"error": "usage: run_migrate.py <runner_path> [project_dir]"}))
        return 1

    runner_path = argv[1]
    project_dir = str(Path(argv[2]).resolve()) if len(argv) > 2 else "."

    try:
        runner_mod = _import_runner(runner_path)
        MigrationRunner = runner_mod.MigrationRunner
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
