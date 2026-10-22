"""R-030: setup Branches A, B and C ask the mode question and persist project.mode."""

from __future__ import annotations

import re

import pytest

from setup_skill_sections import branch_section

MODES = ["Flow", "Kanban", "Shape Up", "Agile"]
MODE_WRITE = re.compile(r"--mode\b|\['project'\]\['mode'\]|\[\"project\"\]\[\"mode\"\]|project\.mode|project:\s*\{?\s*mode")
HANDOFF = re.compile(r"library-load _features|Handoff|All set")


class TestR030ModeQuestion:
    @pytest.mark.parametrize("letter", ["A", "B", "C"])
    def test_branch_asks_mode_question_with_four_modes(self, letter):
        section = branch_section(letter)
        assert re.search(r"(?i)\bmode\b", section), f"Branch {letter} must ask a mode question"
        for mode in MODES:
            assert mode in section, f"Branch {letter} mode question must offer {mode}"

    @pytest.mark.parametrize("letter", ["A", "B", "C"])
    def test_branch_writes_mode_to_project_mode_key(self, letter):
        section = branch_section(letter)
        assert MODE_WRITE.search(section), (
            f"Branch {letter} must write the chosen mode to project.mode in sweetclaude.yaml"
        )
        assert "sweetclaude.yaml" in section

    @pytest.mark.parametrize("letter", ["A", "B", "C"])
    def test_mode_is_written_before_handoff(self, letter):
        section = branch_section(letter)
        write = MODE_WRITE.search(section)
        handoff = HANDOFF.search(section)
        assert write, f"Branch {letter} never writes project.mode"
        assert handoff, f"Branch {letter} has no handoff"
        assert write.start() < handoff.start()
