#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Own the TDD phase marker (ISSUE-282).

`hooks/test-guardian.sh` and `hooks/auto-test-runner.sh` have always gated on
`tdd_phase: implementing`. Nothing ever wrote it. An exhaustive search found
the value in exactly two places: the hooks that read it, and test fixtures
that hand-wrote it to check the hooks' logic.

So `rules/tdd-levels.md` — "test files are immutable during implementation" —
described something that had never once happened.

This script is the writer. `skill-library/build/code-tdd/SKILL.md` calls it at the points
its own process already names: after RED is verified and the tests are
committed, test files are frozen; when the cycle returns to writing tests,
they are not.

The marker lives at `work.active.tdd_phase` in sweetclaude.yaml, alongside the
rest of the active-work state. phase.yaml is mirrored only when it already
exists, because the story controllers maintain it and onboarding never creates
it.

Usage:
    python3 scripts/tdd_phase.py set --phase implementing --project-dir .
    python3 scripts/tdd_phase.py get --project-dir .
    python3 scripts/tdd_phase.py clear --project-dir .
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import yaml

WRITING_TESTS = "writing_tests"
IMPLEMENTING = "implementing"
REFACTORING = "refactoring"

# `implementing` is the one the guardian blocks on. The others exist so the
# marker says what is happening rather than only whether tests are frozen.
VALID = (WRITING_TESTS, IMPLEMENTING, REFACTORING)


def _state_paths(project_dir: Path) -> tuple[Path, Path]:
    state = project_dir / ".sweetclaude" / "state"
    return state / "sweetclaude.yaml", state / "phase.yaml"


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=str(path.parent), suffix=".tmp",
                                     delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(data, tmp, default_flow_style=False, sort_keys=False,
                       allow_unicode=True)
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def get_phase(project_dir: Path) -> str | None:
    """Canonical first, mirror only as a fallback for mid-migration projects."""
    sc_path, phase_path = _state_paths(project_dir)
    sc = _load(sc_path)
    phase = ((sc.get("work") or {}).get("active") or {}).get("tdd_phase")
    if phase:
        return phase
    return _load(phase_path).get("tdd_phase") or None


def set_phase(project_dir: Path, phase: str) -> dict:
    if phase not in VALID:
        raise ValueError(f"tdd_phase must be one of {', '.join(VALID)} (got {phase!r})")

    sc_path, phase_path = _state_paths(project_dir)
    if not sc_path.is_file():
        raise FileNotFoundError(
            f"no sweetclaude.yaml at {sc_path} — the project is not configured")

    sc = _load(sc_path)
    active = (sc.setdefault("work", {}).setdefault("active", {}) or {})
    if not isinstance(active, dict):
        active = {}
        sc["work"]["active"] = active
    active["tdd_phase"] = phase
    _atomic_write(sc_path, sc)

    # The story controllers keep phase.yaml in step when a workflow is running.
    # Mirror only if it already exists; creating it would resurrect the file
    # every v4 consumer stopped reading (ISSUE-251).
    mirrored = False
    if phase_path.is_file():
        mirror = _load(phase_path)
        mirror["tdd_phase"] = phase
        _atomic_write(phase_path, mirror)
        mirrored = True

    return {"ok": True, "tdd_phase": phase, "mirrored_to_phase_yaml": mirrored,
            "tests_frozen": phase == IMPLEMENTING}


def clear_phase(project_dir: Path) -> dict:
    sc_path, phase_path = _state_paths(project_dir)
    sc = _load(sc_path)
    active = (sc.get("work") or {}).get("active")
    if isinstance(active, dict) and "tdd_phase" in active:
        active.pop("tdd_phase")
        _atomic_write(sc_path, sc)
    if phase_path.is_file():
        mirror = _load(phase_path)
        if "tdd_phase" in mirror:
            mirror.pop("tdd_phase")
            _atomic_write(phase_path, mirror)
    return {"ok": True, "tdd_phase": None, "tests_frozen": False}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Read and write the TDD phase marker.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("set")
    s.add_argument("--phase", required=True, choices=list(VALID))
    s.add_argument("--project-dir", type=Path, default=Path("."))

    g = sub.add_parser("get")
    g.add_argument("--project-dir", type=Path, default=Path("."))

    c = sub.add_parser("clear")
    c.add_argument("--project-dir", type=Path, default=Path("."))

    args = p.parse_args(argv)
    project = args.project_dir.resolve()

    try:
        if args.cmd == "set":
            print(json.dumps(set_phase(project, args.phase)))
        elif args.cmd == "clear":
            print(json.dumps(clear_phase(project)))
        else:
            phase = get_phase(project)
            print(json.dumps({"ok": True, "tdd_phase": phase,
                              "tests_frozen": phase == IMPLEMENTING}))
    except (ValueError, FileNotFoundError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
