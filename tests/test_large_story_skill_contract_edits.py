"""R-218: the large-story skill describes contract edits as denied, not prompted."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
SKILL = REPO_ROOT / "skill-library" / "build" / "large-story" / "SKILL.md"


def _text() -> str:
    return re.sub(r"\s+", " ", SKILL.read_text(encoding="utf-8")).lower()


class TestR218LargeStorySkillContractEditsAreDenied:
    def test_no_approval_prompt_wording(self):
        assert "approval prompt" not in _text()

    def test_contract_edits_are_described_as_denied(self):
        assert "denied" in _text()

    def test_human_run_approve_amendment_command_is_named(self):
        assert "approve-amendment" in _text()

    def test_human_run_amend_contract_command_is_named(self):
        assert "amend-contract" in _text()
