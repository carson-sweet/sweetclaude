#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate the optional-feature onboarding ledger (.sweetclaude/state/skills.yaml).

Creates the v2 stub init normally writes. Idempotent: an existing file is
never touched. Feature skills populate entries as features are onboarded.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STUB = (
    "# .sweetclaude/state/skills.yaml\n"
    "# SweetClaude skills state — schema version 2\n"
    "schema_version: 2\n"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create the skills.yaml v2 stub if missing",
    )
    parser.add_argument("--project-dir", default=".", help="Project directory")
    args = parser.parse_args(argv)

    project = Path(args.project_dir).expanduser().resolve()
    state_dir = project / ".sweetclaude" / "state"
    skills_path = state_dir / "skills.yaml"

    if skills_path.exists():
        print(json.dumps({
            "status": "exists",
            "path": str(skills_path),
            "detail": "skills.yaml already present — not modified.",
        }))
        return 0

    if not state_dir.is_dir():
        print(json.dumps({
            "status": "error",
            "path": str(skills_path),
            "detail": (
                "state directory missing — this project is not initialized; "
                "run /sweetclaude:configure init"
            ),
        }), file=sys.stderr)
        return 1

    tmp = skills_path.with_suffix(".tmp")
    tmp.write_text(STUB, encoding="utf-8")
    tmp.replace(skills_path)
    print(json.dumps({
        "status": "created",
        "path": str(skills_path),
        "schema_version": 2,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
