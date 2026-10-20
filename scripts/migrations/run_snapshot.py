#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Step 1 helper for skill-library/configure/_migrate/SKILL.md.

Creates a pre-migration safety snapshot (tarball + git tag). Idempotent:
if a prior snapshot is recorded in .sweetclaude/state/pending-migration-snapshot.json
and both the tarball and git tag are still present, returns the existing snapshot
rather than creating a duplicate.

Usage:
    python3 run_snapshot.py <runner_path> <project_dir>

Outputs one line:
    SNAPSHOT_OK|<json>     — snapshot created or reused
    SNAPSHOT_FAILED|<msg>  — fatal; caller should abort migration
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _check_existing(project_dir: Path) -> dict | None:
    """Return the stored snapshot dict if still valid on disk, else None."""
    marker = project_dir / ".sweetclaude" / "state" / "pending-migration-snapshot.json"
    if not marker.exists():
        return None
    try:
        snap = json.loads(marker.read_text())
    except Exception:
        return None

    tarball = snap.get("tarball_path", "")
    git_tag = snap.get("git_tag", "")

    if not Path(tarball).exists():
        return None

    if git_tag:
        rc = subprocess.run(
            ["git", "rev-parse", "--verify", git_tag],
            capture_output=True,
            text=True,
            cwd=str(project_dir),
        ).returncode
        if rc != 0:
            return None

    return snap


def _save_snapshot(project_dir: Path, snap_dict: dict) -> None:
    import tempfile

    marker = project_dir / ".sweetclaude" / "state" / "pending-migration-snapshot.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=str(marker.parent), suffix=".tmp", delete=False
        ) as tmp:
            json.dump(snap_dict, tmp)
            tmp_name = tmp.name
        os.replace(tmp_name, str(marker))
        tmp_name = None
    finally:
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass



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
        print("SNAPSHOT_FAILED|usage: run_snapshot.py <runner_path> [project_dir]")
        return 1

    runner_path = argv[1]
    project_dir = Path(argv[2]).resolve() if len(argv) > 2 else Path(".").resolve()

    existing = _check_existing(project_dir)
    if existing:
        print(f"SNAPSHOT_OK|{json.dumps(existing)}")
        return 0

    try:
        runner_mod = _import_runner(runner_path)
        MigrationRunner = runner_mod.MigrationRunner
    except ImportError as e:
        print(f"SNAPSHOT_FAILED|cannot import runner: {e}")
        return 1

    runner = MigrationRunner(project_dir=str(project_dir))
    try:
        snap = runner.create_snapshot()
    except RuntimeError as e:
        print(f"SNAPSHOT_FAILED|{e}")
        return 1

    snap_dict = snap.to_dict()
    _save_snapshot(project_dir, snap_dict)
    print(f"SNAPSHOT_OK|{json.dumps(snap_dict)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
