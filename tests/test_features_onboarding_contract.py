"""Contract tests for the feature-onboarding table in configure/_features.

Step 4 of that skill dispatches each newly enabled feature to an onboarding
operation on another skill. Nothing checked that those targets exist. BUG-2
(2026-10-23) was a row pointing `product_backlog` at
`library-load project-backlog onboard`, an operation project-backlog does not
define. Because unmatched arguments fall through to a default, the call
silently ran the wrong operation and reported success.

Two failure modes are pinned here: a target skill that does not define the
named operation, and a target skill that is contractually read-only and so
must never be asked to mutate.

Step 4 is model-executed prose, so these tests read the table rather than run
it. A table that stops being parseable fails loudly instead of passing empty.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
FEATURES_SKILL = REPO_ROOT / "skill-library" / "configure" / "_features" / "SKILL.md"
MANIFEST = REPO_ROOT / "config" / "capability-manifest.yaml"

FEATURE_ROW = re.compile(r"^\|\s*`([a-z_]+)`\s*\|", re.M)
ONBOARD_ROW = re.compile(
    r"^\|\s*`([a-z_]+)`\s*\|\s*invoke\s+`sweetclaude:library-load\s+([^`]+)`"
    r"(?:\s+with\s+argument\s+`([^`]+)`)?",
    re.M,
)
STATED_COUNT = re.compile(r"with all (\d+) features as options")


def _text() -> str:
    return FEATURES_SKILL.read_text(encoding="utf-8")


def _slice(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def _feature_table(text: str) -> str:
    return _slice(
        text,
        "Use this table for all feature labels and descriptions:",
        "If `FIRST_TIME` is `TRUE`:",
    )


def _onboarding_table(text: str) -> str:
    return _slice(text, "## Step 4:", "**Handling a paused onboard:**")


def _feature_keys(text: str) -> list[str]:
    return FEATURE_ROW.findall(_feature_table(text))


def _onboarding_targets(text: str) -> list[tuple[str, str, str | None]]:
    """(feature key, target skill, operation) for every Step 4 row.

    The operation arrives two ways: inside the same code span
    (``library-load usage on``) or in a trailing `with argument` clause.
    """
    targets = []
    for key, payload, argument in ONBOARD_ROW.findall(_onboarding_table(text)):
        tokens = payload.split()
        skill = tokens[0]
        operation = argument or (tokens[1] if len(tokens) > 1 else None)
        targets.append((key, skill, operation))
    return targets


def _skill_path(skill: str) -> Path | None:
    matches = sorted(REPO_ROOT.glob(f"skill-library/*/{skill}/SKILL.md"))
    return matches[0] if matches else None


def test_the_tables_are_parseable() -> None:
    """Guards the other three: a regex that silently stops matching would make
    them pass on an empty list."""
    text = _text()
    keys = _feature_keys(text)
    targets = _onboarding_targets(text)
    assert len(keys) == 7, keys
    assert len(targets) == 7, targets
    assert [k for k, _, _ in targets] == keys, "Step 4 must cover every feature"
    assert all(op for _, _, op in targets), targets


def test_the_stated_feature_count_matches_the_feature_table() -> None:
    """BUG-3: the prompt said 'all 8 features' over a table of 7."""
    text = _text()
    stated = STATED_COUNT.search(text)
    assert stated, "the AskUserQuestion prompt no longer states a feature count"
    assert int(stated.group(1)) == len(_feature_keys(text))


def test_the_prompt_fits_the_askuserquestion_option_ceiling() -> None:
    """AskUserQuestion accepts at most four options, so seven features cannot
    be offered in one call. The skill has to say to split them."""
    assert "4 options" in _text() or "four options" in _text(), (
        "the feature prompt must note the AskUserQuestion four-option ceiling "
        "and instruct splitting across questions"
    )


@pytest.mark.parametrize("key,skill,operation", _onboarding_targets(_text()))
def test_every_onboarding_target_names_an_operation_the_skill_defines(
    key: str, skill: str, operation: str | None
) -> None:
    """BUG-2: `product_backlog` pointed at an operation that did not exist."""
    path = _skill_path(skill)
    assert path is not None, f"{key} -> {skill} is not a skill in skill-library/"
    assert operation is not None, f"{key} -> {skill} names no operation"
    body = path.read_text(encoding="utf-8")
    assert re.search(rf"\b{re.escape(operation)}\b", body), (
        f"{key} -> {skill} {operation}: {skill} never mentions `{operation}`, "
        "so the call would fall through to that skill's default operation"
    )


def test_no_onboarding_target_is_a_read_only_capability() -> None:
    """An onboarding operation writes the feature's data tree and its
    skills.yaml entry. A capability declared read_only must not be asked to."""
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    read_only = {
        entry["delegate_skill"].split(":")[-1]
        for entry in manifest["capabilities"].values()
        if isinstance(entry, dict)
        and entry.get("mutation_class") == "read_only"
        and entry.get("delegate_skill")
    }
    assert read_only, "no read_only capabilities found - manifest shape changed"
    bad = sorted({skill for _, skill, _ in _onboarding_targets(_text())} & read_only)
    assert not bad, (
        f"{bad} are declared read_only in capability-manifest.yaml but are "
        "onboarding targets. Point the feature at the mutating skill that owns "
        "the data, or reclassify the capability."
    )
