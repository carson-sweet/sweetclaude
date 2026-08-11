#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Every redirect skill points at a skill that exists (ISSUE-261).

Five skills exist only to send the user somewhere else. A redirect naming a
target that does not resolve is the exact defect ISSUE-252 was, and it is
invisible from the redirect's own text — the sentence reads fine either way.
"""
from __future__ import annotations

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]


def redirect_targets() -> dict[str, str]:
    found = {}
    for path in sorted((REPO / "skills").glob("*/SKILL.md")):
        header = re.match(r"^---\n(.*?)\n---", path.read_text(encoding="utf-8"), re.S)
        if not header:
            continue
        desc = re.search(r"^description:\s*(.+?)(?=\n[a-z-]+:|\Z)", header.group(1),
                         re.S | re.M)
        text = " ".join(desc.group(1).split()) if desc else ""
        target = re.search(r"(?:Redirects to|use)\s+/?(?:sweetclaude:)([\w-]+)", text)
        if target and re.search(r"DEPRECATED|Redirects", text, re.I):
            found[path.parent.name] = target.group(1)
    return found


def main() -> int:
    targets = redirect_targets()
    broken = {s: t for s, t in targets.items()
              if not (REPO / "skills" / t / "SKILL.md").is_file()}
    print(f"{len(targets)} redirect skills, {len(targets) - len(broken)} resolving")
    for skill, target in sorted(broken.items()):
        print(f"  {skill} -> sweetclaude:{target} does not exist")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
