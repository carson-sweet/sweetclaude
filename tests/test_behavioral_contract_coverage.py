"""Every interaction-model rule has a behavioral contract (ISSUE-265).

The behavioral suite is Tier 3 — it needs a live model and cannot be a CI
percentage. What CI can enforce is that no rule exists without a contract
pointed at it. Before this, five sections of rules/interaction-model.md had
none: Bounded Decisions Use the Menu, Status Changes and Cascade Offer,
Protocol Guardian Offer, Recap, and Dual Context Window Awareness.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
RULES = REPO_ROOT / "rules" / "interaction-model.md"
SUITE = REPO_ROOT / "skills" / "behavioral-regression" / "SKILL.md"

# Rule section -> the contract(s) that exercise it. Adding a rule section
# without adding an entry here fails test_every_rule_section_has_a_contract.
RULE_TO_CONTRACT = {
    "Deference Levels": ["CONTRACT-06", "CONTRACT-07"],
    "Phase Dwelling": ["CONTRACT-01"],
    "Propose and Challenge": ["CONTRACT-02", "CONTRACT-03"],
    "Bounded Decisions Use the Menu": ["CONTRACT-16"],
    "Status Changes — User Intent and Cascade Offer": ["CONTRACT-17"],
    "Adaptive Language": ["CONTRACT-09", "CONTRACT-10"],
    "Early-Phase Depth Rules (Discover and Define)": ["CONTRACT-03", "CONTRACT-04"],
    "Adaptive Flow": ["CONTRACT-08"],
    "Recap": ["CONTRACT-19"],
    "Context Continuity — Detour Management": ["CONTRACT-08", "CONTRACT-19"],
    "Dual Context Window Awareness": ["CONTRACT-20"],
    "Creative Partnership": ["CONTRACT-02", "CONTRACT-03"],
    "Continuous Improvement": ["CONTRACT-11", "CONTRACT-15"],
    "Protocol Guardian Offer": ["CONTRACT-18"],
    "No Time-Based Anxiety": ["CONTRACT-05"],
}


def _rule_sections() -> list[str]:
    return re.findall(r"^##\s+(.+?)\s*$", RULES.read_text(encoding="utf-8"), re.M)


def _contract_ids() -> list[str]:
    return re.findall(r"^###\s+(CONTRACT-\d+):", SUITE.read_text(encoding="utf-8"), re.M)


def test_rules_file_exists() -> None:
    assert RULES.is_file()


def test_every_rule_section_has_a_contract() -> None:
    """A rule nobody tests is a rule nobody keeps."""
    uncovered = [s for s in _rule_sections() if s not in RULE_TO_CONTRACT]
    assert not uncovered, (
        "interaction-model sections with no behavioral contract:\n  "
        + "\n  ".join(uncovered)
        + "\nAdd a CONTRACT to skills/behavioral-regression/SKILL.md and map it "
          "in RULE_TO_CONTRACT."
    )


def test_contract_map_has_no_stale_sections() -> None:
    """A mapping entry for a rule that no longer exists hides a real gap."""
    sections = set(_rule_sections())
    stale = [s for s in RULE_TO_CONTRACT if s not in sections]
    assert not stale, f"mapped sections no longer in the rules file: {stale}"


@pytest.mark.parametrize(
    "section,contracts", sorted(RULE_TO_CONTRACT.items()), ids=lambda v: v if isinstance(v, str) else ""
)
def test_mapped_contracts_exist(section: str, contracts: list[str]) -> None:
    present = set(_contract_ids())
    missing = [c for c in contracts if c not in present]
    assert not missing, f"{section} maps to contracts that do not exist: {missing}"


def test_contract_ids_are_contiguous_and_unique() -> None:
    ids = _contract_ids()
    numbers = [int(c.split("-")[1]) for c in ids]
    assert len(set(numbers)) == len(numbers), f"duplicate contract ids: {ids}"
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"contract ids must run 1..N with no gaps, got {numbers}"
    )


def test_scorecard_lists_every_contract() -> None:
    """The scorecard is how a run is reported. A contract missing from it is
    a contract that silently never gets scored."""
    text = SUITE.read_text(encoding="utf-8")
    scorecard = text.split("## Step 3: Score and report", 1)[-1]
    for cid in _contract_ids():
        assert cid in scorecard, f"{cid} is not on the scorecard"


def test_scorecard_total_matches_the_contract_count() -> None:
    text = SUITE.read_text(encoding="utf-8")
    m = re.search(r"Score:\s*\{N\}/(\d+)", text)
    assert m, "scorecard has no Score: {N}/total line"
    assert int(m.group(1)) == len(_contract_ids()), (
        f"scorecard total is {m.group(1)} but there are {len(_contract_ids())} contracts"
    )


@pytest.mark.parametrize("cid", _contract_ids())
def test_each_contract_states_pass_and_fail(cid: str) -> None:
    """A contract without both criteria cannot be scored consistently."""
    text = SUITE.read_text(encoding="utf-8")
    block = text.split(f"### {cid}:", 1)[1].split("\n### ", 1)[0]
    assert "**PASS:**" in block, f"{cid} has no PASS criterion"
    assert "**FAIL:**" in block, f"{cid} has no FAIL criterion"


def test_menu_contract_checks_for_the_tool_call_not_the_text() -> None:
    """The failure mode is prose that looks like a menu, so the contract has
    to distinguish a real AskUserQuestion call from formatted text."""
    text = SUITE.read_text(encoding="utf-8")
    block = text.split("### CONTRACT-16:", 1)[1].split("\n### ", 1)[0]
    assert "AskUserQuestion" in block
    assert "tool call" in block.lower() or "tool invocation" in block.lower(), (
        "CONTRACT-16 must key on the tool call appearing in the transcript"
    )
