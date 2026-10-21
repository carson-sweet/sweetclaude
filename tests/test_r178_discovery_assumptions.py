"""R-178: product-discovery appends ASM-NNN entries to the assumption register."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
DISCOVERY = REPO_ROOT / "skill-library" / "plan" / "product-discovery" / "SKILL.md"
WRITERS = [
    REPO_ROOT / "skill-library" / "design" / "design-ux-review" / "SKILL.md",
    REPO_ROOT / "skill-library" / "plan" / "product-user-focus-group" / "SKILL.md",
]
REGISTER = ".sweetclaude/state/assumption-register.md"


def _sections() -> list[str]:
    return re.split(r"(?m)^#{2,3} ", DISCOVERY.read_text(encoding="utf-8"))


class TestR178DiscoveryWritesAssumptionRegister:
    def test_register_path_matches_existing_writers(self) -> None:
        for writer in WRITERS:
            assert REGISTER in writer.read_text(encoding="utf-8")
        assert REGISTER in DISCOVERY.read_text(encoding="utf-8")

    def test_append_step_names_path_and_action_together(self) -> None:
        assert any(
            REGISTER in s and re.search(r"(?i)\bappend", s) for s in _sections()
        ), "no discovery step appends to the assumption register"

    def test_step_uses_asm_nnn_ids(self) -> None:
        assert any(
            REGISTER in s and re.search(r"ASM-(NNN|\d{3})", s) for s in _sections()
        ), "register step does not use ASM-NNN ids"

    def test_step_is_triggered_by_an_answer_recorded_as_assumption(self) -> None:
        assert any(
            REGISTER in s
            and re.search(r"(?i)answer", s)
            and re.search(r"(?i)assum", s)
            and re.search(r"(?i)\b(when|if|whenever)\b", s)
            for s in _sections()
        )
