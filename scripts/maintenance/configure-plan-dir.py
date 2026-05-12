#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Step 7c helper for skills/update/SKILL.md — configure .sweetclaude/plans
as the project's plansDirectory in both Claude Code settings files.

Replaces an inline `if [ -d ".sweetclaude" ]; then python3 - << 'PY' ... PY fi`
heredoc in the SKILL. That pattern is fragile under agent re-typing: `fi`
can end up inside the Python body. Extracted to a helper file the SKILL
just invokes by path.

Usage:
    python3 configure-plan-dir.py [project-dir]

No-op (exit 0) if `<project-dir>/.sweetclaude` does not exist. The SKILL
can call this unconditionally; the helper handles the conditional itself.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile


def main(argv: list[str]) -> int:
    project = argv[1] if len(argv) > 1 else "."
    sweetclaude = os.path.join(project, ".sweetclaude")
    if not os.path.isdir(sweetclaude):
        print("configure-plan-dir: no .sweetclaude/ in project — skipping")
        return 0

    plans_dir = ".sweetclaude/plans"
    os.makedirs(os.path.join(project, plans_dir), exist_ok=True)

    claude_dir = os.path.join(project, ".claude")
    os.makedirs(claude_dir, exist_ok=True)

    changed = []
    for path in (
        os.path.join(claude_dir, "settings.json"),
        os.path.join(claude_dir, "settings.local.json"),
    ):
        try:
            with open(path) as f:
                d = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            d = {}
        if d.get("plansDirectory") == plans_dir:
            continue
        d["plansDirectory"] = plans_dir
        parent = os.path.dirname(path) or "."
        with tempfile.NamedTemporaryFile(
            "w", dir=parent, suffix=".tmp", delete=False
        ) as tmp:
            json.dump(d, tmp, indent=2)
            tmp_name = tmp.name
        try:
            os.replace(tmp_name, path)
        except OSError as e:
            print(f"configure-plan-dir: could not write {path}: {e}")
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            continue
        changed.append(path)

    if changed:
        print(f"configure-plan-dir: set plansDirectory in {len(changed)} file(s)")
    else:
        print("configure-plan-dir: plansDirectory already configured")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
