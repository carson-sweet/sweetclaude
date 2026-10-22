"""R-034: setup Branch A and B write a CLAUDE.md SweetClaude section that passes master Step 2."""

from __future__ import annotations

import re

import pytest

from setup_skill_sections import MASTER_SKILL, branch_section

HEADING = re.compile(r"^#{1,6}\s+.*sweetclaude", re.IGNORECASE | re.MULTILINE)
WRITE_VERB = re.compile(r"(?i)(write|create|append|add|generate)")


def master_requires_sweetclaude_section() -> bool:
    text = MASTER_SKILL.read_text()
    step2 = text.split("**Step 2:", 1)[1].split("**Step 3:", 1)[0]
    return bool(re.search(r"CLAUDE\.md.*exist.*SweetClaude section", step2))


def written_section_blocks(section: str) -> list[str]:
    blocks = re.findall(r"```[a-z]*\n(.*?)```", section, re.DOTALL)
    return [b for b in blocks if HEADING.search(b)]


class TestR034ClaudeMdSection:
    @pytest.mark.parametrize("letter", ["A", "B"])
    def test_branch_has_step_writing_claude_md(self, letter):
        section = branch_section(letter)
        lines = [l for l in section.splitlines() if "CLAUDE.md" in l]
        assert any(WRITE_VERB.search(l) for l in lines), (
            f"Branch {letter} must contain a step that writes CLAUDE.md"
        )

    @pytest.mark.parametrize("letter", ["A", "B"])
    def test_written_section_satisfies_master_check(self, letter):
        blocks = written_section_blocks(branch_section(letter))
        assert blocks, (
            f"Branch {letter} must include the literal CLAUDE.md section text with a SweetClaude heading"
        )
        assert master_requires_sweetclaude_section()
        assert HEADING.search(blocks[0])
