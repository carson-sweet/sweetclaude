"""R-237: every code-tdd level's RED-commit step invokes hooks/git-checkpoint.sh."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
SKILL = REPO_ROOT / "skill-library" / "build" / "code-tdd" / "SKILL.md"
INVOCATION = "${CLAUDE_PLUGIN_ROOT}/hooks/git-checkpoint.sh"


def _level(n: int) -> str:
    text = SKILL.read_text(encoding="utf-8")
    match = re.search(rf"^## Level {n}:.*?(?=^## )", text, re.S | re.M)
    assert match, f"Level {n} section not found"
    return match.group(0)


class TestR237CodeTddLevelsInvokeGitCheckpoint:
    @pytest.mark.parametrize("level", [1, 2, 3])
    def test_level_invokes_git_checkpoint_via_plugin_root(self, level):
        assert INVOCATION in _level(level)

    @pytest.mark.parametrize("level", [1, 2, 3])
    def test_level_checkpoint_message_is_a_red_commit(self, level):
        section = _level(level)
        invocations = [ln for ln in section.splitlines() if "git-checkpoint.sh" in ln]

        assert invocations, "no git-checkpoint.sh invocation"
        assert any("test: RED" in ln for ln in invocations)
