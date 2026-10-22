"""R-022: /sweetclaude:go offers reactivation when .sweetclaude/disabled exists."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
GO_SKILL = REPO_ROOT / "skills" / "go" / "SKILL.md"
FLAG = ".sweetclaude/disabled"
REMOVE = re.compile(r"rm\s+(-f\s+)?[^\n]*\.sweetclaude/disabled")


def _text() -> str:
    return GO_SKILL.read_text(encoding="utf-8")


def _flag_sections() -> list[str]:
    return [s for s in re.split(r"(?m)^## ", _text()) if FLAG in s]


class TestR022GoReactivatesDisabledProject:
    def test_go_checks_disabled_flag_before_routing(self) -> None:
        text = _text()
        assert FLAG in text, "go skill never references .sweetclaude/disabled"
        assert text.index(FLAG) < text.index("find-skill"), "disabled check must precede routing"

    def test_go_asks_user_before_reactivating(self) -> None:
        assert any(
            re.search(r"(?i)\b(ask|confirm|offer)\b", s) and re.search(r"(?i)reactivat", s)
            for s in _flag_sections()
        ), "no go step offers reactivation"

    def test_go_removes_flag_on_confirmation(self) -> None:
        assert any(REMOVE.search(s) for s in _flag_sections()), (
            "no concrete removal of .sweetclaude/disabled"
        )

    def test_removal_is_conditioned_on_yes(self) -> None:
        assert any(
            re.search(r"(?i)\b(yes|confirms|confirmed|approves)\b", s) and REMOVE.search(s)
            for s in _flag_sections()
        )
