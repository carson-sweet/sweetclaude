"""Artifact quality evaluation, and proof it discriminates (ISSUE-271, ISSUE-272).

An evaluator that has never been shown to fail is not evidence. Earlier in this
same work a byte-identical rollback assertion passed while tar extraction was
disabled — it looked like verification and verified nothing.

So the corpus comes first and the confusion matrix is the headline test. A
linter that passes everything and a linter that fails everything both produce
a green "no failures" line; only the matrix tells them apart from one that
works.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
SCRIPT = REPO_ROOT / "scripts" / "artifact_lint.py"
CRITERIA = REPO_ROOT / "config" / "artifact-criteria.yaml"
CORPUS = REPO_ROOT / "tests" / "fixtures" / "artifact-quality"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import artifact_lint as lint  # noqa: E402

GOOD = sorted((CORPUS / "good").glob("*.md"))
DEGRADED = sorted((CORPUS / "degraded").glob("*.md"))
BENIGN = sorted((CORPUS / "benign").glob("*.md"))


def _fixture_meta(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path.name} has no frontmatter"
    return yaml.safe_load(text.split("---", 2)[1]) or {}


def _run(path: Path) -> list[dict]:
    return lint.check(path.read_text(encoding="utf-8"),
                      _fixture_meta(path).get("artifact_type", "product-brief"),
                      lint.load_criteria())


def _failed_ids(results: list[dict]) -> set[str]:
    return {r["id"] for r in results if r["status"] == lint.FAIL}


# --- the corpus is real --------------------------------------------------

def test_corpus_has_all_three_halves() -> None:
    assert GOOD, "no known-good artifacts"
    assert DEGRADED, "no degraded artifacts"
    assert BENIGN, "no benign variants — without these the corpus rewards an "\
                   "evaluator that simply fails everything"


def test_every_degraded_fixture_declares_what_it_violates() -> None:
    for path in DEGRADED:
        violates = _fixture_meta(path).get("violates")
        assert violates and violates != "none", (
            f"{path.name} does not declare which criterion it violates, so a "
            "failure cannot be attributed"
        )


def test_declared_violations_reference_real_criteria() -> None:
    known = {c["id"] for c in
             lint.load_criteria()["artifact_types"]["product-brief"]["criteria"]}
    for path in DEGRADED:
        violates = _fixture_meta(path)["violates"]
        assert violates in known, f"{path.name} names an unknown criterion: {violates}"


# --- discrimination ------------------------------------------------------

@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.name)
def test_known_good_artifacts_pass(path: Path) -> None:
    """These are artifacts the project shipped and stands behind."""
    failed = _failed_ids(_run(path))
    assert not failed, f"{path.name} failed on {sorted(failed)}"


@pytest.mark.parametrize("path", BENIGN, ids=lambda p: p.name)
def test_benign_variants_pass(path: Path) -> None:
    """Reordering sections and rewording prose are not quality defects. An
    evaluator that fails these is measuring shape, not substance."""
    failed = _failed_ids(_run(path))
    assert not failed, f"{path.name} failed on {sorted(failed)}"


@pytest.mark.parametrize("path", DEGRADED, ids=lambda p: p.name)
def test_degraded_artifacts_are_rejected(path: Path) -> None:
    meta = _fixture_meta(path)
    violates = meta["violates"]
    results = _run(path)
    failed = _failed_ids(results)

    tier = next(c["tier"] for c in
                lint.load_criteria()["artifact_types"]["product-brief"]["criteria"]
                if c["id"] == violates)
    if tier != "mechanical":
        pytest.skip(f"{violates} is {tier}; the rubric judge covers it (ISSUE-273)")

    assert failed, f"{path.name} was not rejected at all — {meta['note']}"
    assert violates in failed, (
        f"{path.name} was rejected, but not for {violates}. It failed on "
        f"{sorted(failed)} instead, so the rejection is incidental rather than "
        "attributable."
    )


def test_confusion_matrix_shows_real_discrimination() -> None:
    """The headline. A linter that passes everything and one that fails
    everything both look fine test-by-test; only the matrix separates them."""
    crit = lint.load_criteria()["artifact_types"]["product-brief"]["criteria"]
    mechanical = {c["id"] for c in crit if c["tier"] == "mechanical"}

    should_pass = GOOD + BENIGN
    should_fail = [p for p in DEGRADED if _fixture_meta(p)["violates"] in mechanical]

    true_pass = sum(1 for p in should_pass if not _failed_ids(_run(p)))
    true_fail = sum(1 for p in should_fail
                    if _fixture_meta(p)["violates"] in _failed_ids(_run(p)))
    false_fail = len(should_pass) - true_pass
    false_pass = len(should_fail) - true_fail

    assert false_fail == 0, f"{false_fail} good artifact(s) wrongly rejected"
    assert false_pass == 0, f"{false_pass} degraded artifact(s) wrongly accepted"
    assert true_pass and true_fail, (
        "the corpus must contain artifacts on both sides, or the matrix proves "
        "nothing"
    )


# --- the linter's own contract ------------------------------------------

def test_criteria_config_declares_a_tier_for_every_criterion() -> None:
    for atype, spec in lint.load_criteria()["artifact_types"].items():
        for c in spec["criteria"]:
            assert c.get("tier") in {"mechanical", "judgment", "blocked"}, (
                f"{atype}.{c['id']} has no valid tier")


def test_every_criterion_cites_its_gate_text() -> None:
    """Criteria must be traceable to phase-gates.md or the two drift apart."""
    for atype, spec in lint.load_criteria()["artifact_types"].items():
        for c in spec["criteria"]:
            assert c.get("gate_text"), f"{atype}.{c['id']} cites no gate text"


def test_unevaluable_criteria_are_reported_not_skipped() -> None:
    """Silence about what was not checked reads as 'it passed'."""
    results = _run(GOOD[0])
    statuses = {r["id"]: r["status"] for r in results}
    assert statuses.get("BRIEF-CONCRETE-SCENARIO") == lint.JUDGMENT
    assert statuses.get("BRIEF-ASSUMPTION-CHALLENGED") == lint.BLOCKED


def test_every_configured_criterion_appears_in_the_report() -> None:
    configured = {c["id"] for c in
                  lint.load_criteria()["artifact_types"]["product-brief"]["criteria"]}
    reported = {r["id"] for r in _run(GOOD[0])}
    assert reported == configured, f"unreported: {configured - reported}"


def test_report_carries_no_composite_score() -> None:
    """A single number cannot be acted on and launders judgment."""
    text = lint.render(str(GOOD[0]), _run(GOOD[0]))
    import re
    assert not re.search(r"\b\d+(\.\d+)?\s*/\s*10\b", text)
    assert "score" not in text.lower()


# --- section handling ----------------------------------------------------

def test_section_numbering_is_ignored() -> None:
    """A renumbered brief is not a restructured one."""
    plain = lint.split_sections("## Problem Statement\nbody\n")
    numbered = lint.split_sections("## 1. Problem Statement\nbody\n")
    assert set(plain) == set(numbered) == {"problem statement"}


def test_subsections_do_not_become_sections() -> None:
    sections = lint.split_sections("## Scope\n### In scope\n- a\n### Out of scope\n- b\n")
    assert set(sections) == {"scope"}
    assert "in scope" in sections["scope"].lower()


def test_a_bulleted_section_counts_as_substantive() -> None:
    """The false positive the corpus caught: a Scope section is all bullets and
    contains no full stop, but is plainly substantive."""
    assert lint._substance("- one\n- two\n- three\n") >= 2


# --- CLI -----------------------------------------------------------------

def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, timeout=60)


def test_cli_exits_zero_on_a_good_artifact() -> None:
    r = _cli(str(GOOD[0]))
    assert r.returncode == 0, r.stdout


def test_cli_exits_nonzero_on_a_degraded_artifact() -> None:
    target = next(p for p in DEGRADED
                  if _fixture_meta(p)["violates"] == "BRIEF-OUT-OF-SCOPE-3")
    r = _cli(str(target))
    assert r.returncode == 1
    assert "BRIEF-OUT-OF-SCOPE-3" in r.stdout


def test_cli_json_is_parseable() -> None:
    r = _cli(str(GOOD[0]), "--format", "json")
    assert r.returncode == 0
    assert json.loads(r.stdout)["results"]


def test_cli_reports_a_missing_file() -> None:
    r = _cli("does-not-exist.md")
    assert r.returncode == 2


def test_cli_reports_an_unknown_artifact_type() -> None:
    r = _cli(str(GOOD[0]), "--type", "not-a-real-type")
    assert r.returncode == 2
    assert "unknown artifact type" in r.stderr
