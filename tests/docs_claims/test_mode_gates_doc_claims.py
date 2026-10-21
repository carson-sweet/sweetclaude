"""Phase 5 docs-claims for the mode-gate remediation rows: R-013.

R-013: the README Agile bullet must state the block/warn semantics that
config/mode-gates.yaml actually encodes — implementation blocked when no
sprint is active, warned when the issue is outside the active sprint —
and, once the gate evaluator enforces it, must not carry the
"Not currently enforced" marker.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def agile_bullet() -> str:
    text = (REPO / "README.md").read_text(encoding="utf-8")
    match = re.search(r"^\* \*\*Agile\*\* .*$", text, re.MULTILINE)
    assert match, "README.md has no Agile bullet"
    return match.group(0)


def test_r013_agile_bullet_states_block_without_active_sprint():
    assert "implementation is blocked when no sprint is active" in agile_bullet().lower()


def test_r013_agile_bullet_states_warn_outside_active_sprint():
    assert "warned when the issue is outside the active sprint" in agile_bullet().lower()


def test_r013_agile_bullet_carries_no_unenforced_marker():
    assert "Not currently enforced" not in agile_bullet()