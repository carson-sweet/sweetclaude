#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Step 0 helper for skills/update/SKILL.md.

Running `/sweetclaude:update` is the user explicitly saying "I want updates
again." Clear `framework.update.declined` if it's a legacy boolean or a
prior version-string decline so the rest of the update flow doesn't
silently no-op.

Usage:
    python3 clear-decline.py <project-dir>

No-op if the project has no `.sweetclaude/state/sweetclaude.yaml` (skill
can be invoked from any directory). Exits 0 in all normal cases.

Extracted out of the SKILL because nested heredocs (`if ...; then python3 - << 'PY'
... PY fi`) are brittle when the agent re-types the bash — `fi` can end up
inside the Python heredoc and crash the step silently.
"""

from __future__ import annotations

import os
import sys
import tempfile

import yaml


def main(argv: list[str]) -> int:
    project_dir = argv[1] if len(argv) > 1 else "."
    path = os.path.join(project_dir, ".sweetclaude/state/sweetclaude.yaml")
    if not os.path.exists(path):
        print("clear-decline: no sweetclaude.yaml — skipping")
        return 0

    try:
        with open(path) as f:
            d = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"clear-decline: could not parse sweetclaude.yaml: {e}")
        return 0

    upd = d.setdefault("framework", {}).setdefault("update", {})
    current = upd.get("declined")
    if current in (None, False):
        print("clear-decline: no declined flag set — no change")
        return 0

    upd["declined"] = None
    parent = os.path.dirname(path)
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=parent, suffix=".tmp", delete=False
        ) as tmp:
            yaml.safe_dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
            tmp_name = tmp.name
        os.replace(tmp_name, path)
        tmp_name = None
    finally:
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
    print(f"clear-decline: cleared declined={current!r} → null")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
