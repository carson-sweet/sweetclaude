#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Step 6 helper for skills/bootstrap/SKILL.md.

When the user declines a minor/patch update ("Not now"), write
`framework.update.declined = <available-version>` to sweetclaude.yaml so
the version-aware decline rule silences the offer for the rest of this
installed major.

Usage:
    python3 write-decline.py <project-dir>

Reads the yaml file, writes declined = available-version (or null if no
available version is set). Exits 0 in all normal cases.

Extracted out of the SKILL because inline heredocs are brittle when the
agent re-types the bash.
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
        print("write-decline: no sweetclaude.yaml — skipping")
        return 0

    try:
        with open(path) as f:
            d = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"write-decline: could not parse sweetclaude.yaml: {e}")
        return 0

    available = (d.get("framework") or {}).get("update", {}).get("available")
    d.setdefault("framework", {}).setdefault("update", {})["declined"] = available

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

    print(f"write-decline: declined set to {available!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
