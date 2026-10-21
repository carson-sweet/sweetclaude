"""R-223: the work-item-artifacts skill resolves the backfill script under the plugin."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
LIBRARY = REPO_ROOT / "skill-library"
SKILL = LIBRARY / "configure" / "work-item-artifacts" / "SKILL.md"
SCRIPT_NAME = "backfill_work_item_artifacts.py"
INVOCATION = re.compile(r"(\S*)" + re.escape(SCRIPT_NAME))
ANCHORS = ("${CLAUDE_PLUGIN_ROOT}/", "{skill base directory}/")


class TestR223BackfillInvocationsResolveUnderPlugin:
    def test_every_invocation_is_anchored_to_the_plugin_or_skill_directory(self):
        text = SKILL.read_text(encoding="utf-8")
        found = list(INVOCATION.finditer(text))
        unanchored = [
            m.group(0) for m in found
            if not m.group(1).lstrip("\"'").startswith(ANCHORS)
        ]

        assert found, "skill no longer invokes the backfill script"
        assert unanchored == []

    def test_no_bare_project_relative_invocation_anywhere_in_skill_library(self):
        offenders = []
        for path in LIBRARY.rglob("*.md"):
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"(?<![\w/}])scripts/" + re.escape(SCRIPT_NAME), line):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{n}")

        assert offenders == []
