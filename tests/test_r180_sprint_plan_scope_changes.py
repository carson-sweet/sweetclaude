"""R-180: product-sprint-plan surfaces scope changes since the previous sprint."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
SPRINT_PLAN = REPO_ROOT / "skill-library" / "build" / "product-sprint-plan" / "SKILL.md"
SCOPE_FILE = ".sweetclaude/state/scope-changes.md"


def _holders() -> list[str]:
    sections = re.split(r"(?m)^## ", SPRINT_PLAN.read_text(encoding="utf-8"))
    return [s for s in sections if SCOPE_FILE in s]


class TestR180SprintPlanSurfacesScopeChanges:
    def test_skill_reads_scope_changes_file(self) -> None:
        assert any(re.search(r"(?i)\bread", s) for s in _holders()), (
            "no sprint-plan step reads .sweetclaude/state/scope-changes.md"
        )

    def test_filters_entries_dated_after_previous_sprint_start(self) -> None:
        assert any(
            re.search(r"(?i)dated\s+after", s)
            and re.search(r"(?i)(previous|last)\s+sprint('s)?\s+start|start\s+of\s+the\s+(previous|last)\s+sprint", s)
            for s in _holders()
        )

    def test_lists_entries_in_plan_output(self) -> None:
        assert any(
            re.search(r"(?i)\b(list|report|include|surface)\b", s)
            and re.search(r"(?i)plan output|sprint plan|in the plan", s)
            for s in _holders()
        )
