"""R-029: setup Branch B and C snapshot HEAD to pre-sweetclaude before writing."""

from __future__ import annotations

import re

import pytest

from setup_skill_sections import branch_section

BRANCH_CREATE = re.compile(r"git\s+(branch|checkout\s+-b|switch\s+-c)\s+pre-sweetclaude(?![\w-])")
FILE_WRITE_MARKERS = [
    "mkdir",
    "sweetclaude-yaml-template",
    "directory setup",
    "write as Branch A",
    "CLAUDE.md",
    "v4 Storage Setup",
    "SCAFFOLD:",
    ".write_text",
]


class TestR029SnapshotBranch:
    @pytest.mark.parametrize("letter", ["B", "C"])
    def test_branch_creates_pre_sweetclaude_at_head(self, letter):
        section = branch_section(letter)
        assert BRANCH_CREATE.search(section), (
            f"Branch {letter} must run `git branch pre-sweetclaude` (or checkout -b / switch -c)"
        )

    @pytest.mark.parametrize("letter", ["B", "C"])
    def test_branch_step_is_conditioned_on_git_repository(self, letter):
        section = branch_section(letter)
        assert re.search(r"git rev-parse|git repository|inside a git|in a git repo", section), (
            f"Branch {letter} must scope the snapshot to a git repository"
        )

    @pytest.mark.parametrize("letter", ["B", "C"])
    def test_branch_step_precedes_first_file_writing_step(self, letter):
        section = branch_section(letter)
        create = BRANCH_CREATE.search(section)
        assert create, f"Branch {letter} has no pre-sweetclaude branch step"
        positions = [section.find(m) for m in FILE_WRITE_MARKERS if m in section]
        assert positions, f"Branch {letter} has no recognizable file-writing step"
        assert create.start() < min(positions)

    @pytest.mark.parametrize("letter", ["B", "C"])
    def test_branch_stops_without_writing_when_creation_fails(self, letter):
        section = branch_section(letter)
        create = BRANCH_CREATE.search(section)
        assert create, f"Branch {letter} has no pre-sweetclaude branch step"
        after = section[create.start():]
        assert re.search(r"(?i)\bstop\b", after), "must instruct to stop on failure"
        assert re.search(r"(?i)(without writing|do not write|not write any|no files? (are|is)? ?written)", after), (
            "must state nothing is written when the branch cannot be created"
        )
