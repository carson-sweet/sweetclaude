"""The rubric judge harness, and its ability to detect a useless judge (ISSUE-273).

Tier 3 output is non-deterministic, so what gets tested is the harness: that a
verdict without a citation is discarded, that one criterion is evaluated at a
time, and — the point of the whole thing — that a judge which cannot tell good
from bad is reported as not discriminating rather than quietly believed.

Two degenerate backends exist purely so that last property is demonstrable. An
always-pass judge scores high accuracy on an imbalanced corpus while being
worth nothing; if the harness cannot catch that, no verdict it ever reports
means anything.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
SCRIPT = REPO_ROOT / "scripts" / "artifact_judge.py"
RUBRICS = REPO_ROOT / "config" / "artifact-rubrics.yaml"
CORPUS = REPO_ROOT / "tests" / "fixtures" / "artifact-quality"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import artifact_judge as judge  # noqa: E402

GOOD = CORPUS / "good" / "product-brief-doctor.md"
ABSTRACT = CORPUS / "degraded" / "abstract-problem-statement.md"


def _rubric(cid: str) -> dict:
    return judge.load_rubrics()[cid]


# --- rubric config -------------------------------------------------------

def test_rubrics_exist_for_every_judgment_criterion() -> None:
    """A criterion tiered `judgment` with no rubric is unevaluable by anything."""
    import artifact_lint as lint
    crit = lint.load_criteria()["artifact_types"]["product-brief"]["criteria"]
    judgment = {c["id"] for c in crit if c["tier"] == "judgment"}
    assert judgment <= set(judge.load_rubrics()), (
        f"no rubric for: {judgment - set(judge.load_rubrics())}")


@pytest.mark.parametrize("cid", sorted(judge.load_rubrics()))
def test_each_rubric_states_both_directions(cid: str) -> None:
    """A rubric that only says what passes invites a judge to pass everything."""
    r = _rubric(cid)
    assert r.get("question", "").strip()
    assert r.get("passes_when", "").strip()
    assert r.get("fails_when", "").strip()


@pytest.mark.parametrize("cid", sorted(judge.load_rubrics()))
def test_each_rubric_requires_a_citation(cid: str) -> None:
    assert _rubric(cid).get("citation_required") is True


# --- prompt construction -------------------------------------------------

def test_prompt_scopes_to_the_relevant_section() -> None:
    """Handing the judge the whole brief invites it to answer from elsewhere."""
    prompt = judge.build_prompt(GOOD.read_text(encoding="utf-8"),
                                "BRIEF-CONCRETE-SCENARIO",
                                _rubric("BRIEF-CONCRETE-SCENARIO"))
    assert "Concrete scenario:" in prompt
    assert "## 7. Scope" not in prompt, "prompt leaked unrelated sections"


def test_prompt_carries_one_criterion_only() -> None:
    prompt = judge.build_prompt(GOOD.read_text(encoding="utf-8"),
                                "BRIEF-CONCRETE-SCENARIO",
                                _rubric("BRIEF-CONCRETE-SCENARIO"))
    assert "BRIEF-CONCRETE-SCENARIO" in prompt
    assert "BRIEF-MEASURABLE-ALL" not in prompt


def test_prompt_demands_a_verbatim_citation() -> None:
    prompt = judge.build_prompt(GOOD.read_text(encoding="utf-8"),
                                "BRIEF-CONCRETE-SCENARIO",
                                _rubric("BRIEF-CONCRETE-SCENARIO"))
    assert "verbatim" in prompt.lower()
    assert "discarded" in prompt.lower()


# --- citation enforcement ------------------------------------------------

def test_a_verdict_without_a_citation_is_discarded(monkeypatch) -> None:
    """An uncited verdict is a guess wearing a verdict's clothes."""
    monkeypatch.setattr(judge, "_stub",
                        lambda p, t: {"verdict": "pass", "citation": "", "reason": "x"})
    r = judge.evaluate(GOOD.read_text(encoding="utf-8"), "BRIEF-CONCRETE-SCENARIO",
                       _rubric("BRIEF-CONCRETE-SCENARIO"))
    assert r["counted"] is False
    assert "no citation" in r["discarded"]


def test_a_fabricated_citation_is_discarded(monkeypatch) -> None:
    """The strongest guard: a citation that is not in the artifact means the
    judge invented its evidence."""
    monkeypatch.setattr(judge, "_stub",
                        lambda p, t: {"verdict": "pass",
                                      "citation": "this text appears nowhere in the brief",
                                      "reason": "x"})
    r = judge.evaluate(GOOD.read_text(encoding="utf-8"), "BRIEF-CONCRETE-SCENARIO",
                       _rubric("BRIEF-CONCRETE-SCENARIO"))
    assert r["counted"] is False
    assert "not present" in r["discarded"]


def test_a_cited_verdict_is_counted() -> None:
    r = judge.evaluate(GOOD.read_text(encoding="utf-8"), "BRIEF-CONCRETE-SCENARIO",
                       _rubric("BRIEF-CONCRETE-SCENARIO"))
    assert r["counted"] is True
    assert r["citation"]


def test_an_unusable_verdict_raises(monkeypatch) -> None:
    monkeypatch.setattr(judge, "_stub",
                        lambda p, t: {"verdict": "maybe", "citation": "x", "reason": "y"})
    with pytest.raises(judge.JudgeError):
        judge.evaluate(GOOD.read_text(encoding="utf-8"), "BRIEF-CONCRETE-SCENARIO",
                       _rubric("BRIEF-CONCRETE-SCENARIO"))


# --- the property that matters -------------------------------------------

def test_a_working_judge_discriminates() -> None:
    report = judge.discriminate(backend="stub")
    assert report["matrix"]["discriminates"] is True, report["matrix"]


@pytest.mark.parametrize("backend", ["always-pass", "always-fail"])
def test_a_degenerate_judge_is_caught(backend: str) -> None:
    """If the harness cannot catch these, nothing it reports is evidence."""
    report = judge.discriminate(backend=backend)
    assert report["matrix"]["discriminates"] is False, (
        f"{backend} backend was not detected as useless: {report['matrix']}")


def test_high_accuracy_alone_does_not_certify_a_judge() -> None:
    """always-pass scores well on an imbalanced corpus while being worthless.
    Accuracy is reported; the boolean is the verdict."""
    report = judge.discriminate(backend="always-pass")
    assert report["matrix"]["accuracy"] > 0.5
    assert report["matrix"]["discriminates"] is False


def test_degraded_fixtures_only_count_against_their_own_criterion() -> None:
    """A brief with vague success criteria is not evidence about its problem
    statement. Counting it as such would inflate the matrix."""
    rows = judge.discriminate(backend="stub")["rows"]
    for row in rows:
        if row.get("expected") == "fail":
            meta = yaml.safe_load(
                (CORPUS / "degraded" / row["file"]).read_text(encoding="utf-8")
                .split("---", 2)[1])
            assert row["criterion"] == meta["violates"]


def test_unknown_backend_raises() -> None:
    with pytest.raises(judge.JudgeError):
        judge.evaluate(GOOD.read_text(encoding="utf-8"), "BRIEF-CONCRETE-SCENARIO",
                       _rubric("BRIEF-CONCRETE-SCENARIO"), backend="nonsense")


def test_command_backend_requires_a_command() -> None:
    with pytest.raises(judge.JudgeError):
        judge.evaluate(GOOD.read_text(encoding="utf-8"), "BRIEF-CONCRETE-SCENARIO",
                       _rubric("BRIEF-CONCRETE-SCENARIO"), backend="command")


# --- CLI -----------------------------------------------------------------

def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, timeout=120)


def test_cli_discriminate_exits_zero_for_a_working_judge() -> None:
    assert _cli("discriminate", "--backend", "stub").returncode == 0


@pytest.mark.parametrize("backend", ["always-pass", "always-fail"])
def test_cli_discriminate_exits_nonzero_for_a_degenerate_judge(backend: str) -> None:
    r = _cli("discriminate", "--backend", backend)
    assert r.returncode == 1
    assert "DOES NOT DISCRIMINATE" in r.stdout


def test_cli_judge_reports_a_single_criterion() -> None:
    r = _cli("judge", str(ABSTRACT), "--criterion", "BRIEF-CONCRETE-SCENARIO")
    payload = json.loads(r.stdout)
    assert payload["criterion"] == "BRIEF-CONCRETE-SCENARIO"
    assert payload["verdict"] == "fail"
    assert payload["citation"]


def test_cli_rejects_an_unknown_criterion() -> None:
    r = _cli("judge", str(GOOD), "--criterion", "NOT-A-CRITERION")
    assert r.returncode == 2


def test_cli_discriminate_json_is_parseable() -> None:
    r = _cli("discriminate", "--backend", "stub", "--format", "json")
    assert json.loads(r.stdout)["matrix"]["discriminates"] is True
