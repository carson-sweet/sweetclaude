"""Skill outcomes are recorded and reported honestly (ISSUE-276).

The metrics log recorded that skills ran and never whether they worked. The
properties worth defending are the ones that stop a useless log from reading
as a healthy one:

  * silence is never success — an invocation with no completion is `unknown`
  * never-invoked is not zero-failure — it is `unobserved`
  * the success rate divides by recorded outcomes, not by everything, or a log
    with no outcomes at all reports 100%
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
RECORD = REPO_ROOT / "scripts" / "record-event.sh"
REPORT = REPO_ROOT / "scripts" / "usage_report.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import usage_report as ur  # noqa: E402


@pytest.fixture
def project(tmp_path: Path) -> Path:
    metrics = tmp_path / ".sweetclaude" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "config.yaml").write_text("enabled: true\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    d = tmp_path / "skills"
    for name in ("doctor", "code-verify", "never-run"):
        (d / name).mkdir(parents=True)
    return d


def _record(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(RECORD), *args],
                          env={"PATH": "/usr/bin:/bin:/usr/local/bin",
                               "PROJECT_DIR": str(project)},
                          capture_output=True, text=True, timeout=60)


def _report(project: Path, skills_dir: Path | None = None) -> dict:
    return ur.build_report(project, skills_dir)


# --- the writer ----------------------------------------------------------

def test_a_valid_outcome_is_written(project: Path) -> None:
    r = _record(project, "skill_completed", "skill=sweetclaude:doctor",
                "outcome=completed")
    assert r.returncode == 0, r.stderr
    log = (project / ".sweetclaude" / "metrics" / "events.log").read_text()
    assert "event: skill_completed" in log
    assert "outcome: completed" in log


@pytest.mark.parametrize("outcome", ["completed", "failed", "abandoned", "blocked"])
def test_every_documented_outcome_is_accepted(project: Path, outcome: str) -> None:
    assert _record(project, "skill_completed", "skill=x",
                   f"outcome={outcome}").returncode == 0


def test_an_invalid_outcome_is_rejected_not_downgraded(project: Path) -> None:
    """Writing it as unknown would make a typo indistinguishable from a skill
    that never reported at all."""
    r = _record(project, "skill_completed", "skill=x", "outcome=succeeded")
    assert r.returncode == 2
    assert "outcome=" in r.stderr
    assert not (project / ".sweetclaude" / "metrics" / "events.log").exists()


def test_a_missing_outcome_is_rejected(project: Path) -> None:
    r = _record(project, "skill_completed", "skill=x")
    assert r.returncode == 2


def test_other_event_types_are_unaffected(project: Path) -> None:
    """Validation must not break the events that predate outcomes."""
    assert _record(project, "skill_invoked", "skill=x", "phase=none").returncode == 0
    assert _record(project, "session_start", "phase=none").returncode == 0


def test_recording_is_silent_when_metrics_are_disabled(tmp_path: Path) -> None:
    metrics = tmp_path / ".sweetclaude" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "config.yaml").write_text("enabled: false\n", encoding="utf-8")

    assert _record(tmp_path, "skill_completed", "skill=x",
                   "outcome=completed").returncode == 0
    assert not (metrics / "events.log").exists()


# --- both paths, per the acceptance criteria -----------------------------

def test_a_success_path_is_recorded_and_reported(project: Path, skills_dir: Path) -> None:
    _record(project, "skill_invoked", "skill=sweetclaude:doctor", "phase=none")
    _record(project, "skill_completed", "skill=sweetclaude:doctor",
            "outcome=completed", "detail=2 errors auto-fixed")

    report = _report(project, skills_dir)
    assert report["totals"][ur.COMPLETED] == 1
    assert report["totals"][ur.UNKNOWN] == 0
    assert report["success_rate"] == 1.0


def test_a_failure_path_is_recorded_with_its_reason(project: Path, skills_dir: Path) -> None:
    """A failure with no detail cannot be acted on later."""
    _record(project, "skill_invoked", "skill=sweetclaude:code-verify", "phase=none")
    _record(project, "skill_completed", "skill=sweetclaude:code-verify",
            "outcome=failed", "detail=mutation testing failed")

    report = _report(project, skills_dir)
    assert report["totals"][ur.FAILED] == 1
    assert report["failures"][0]["detail"] == "mutation testing failed"
    assert report["success_rate"] == 0.0


# --- silence is not success ---------------------------------------------

def test_an_invocation_without_a_completion_is_unknown(project: Path, skills_dir: Path) -> None:
    _record(project, "skill_invoked", "skill=sweetclaude:doctor", "phase=none")

    report = _report(project, skills_dir)
    assert report["totals"][ur.UNKNOWN] == 1
    assert report["totals"][ur.COMPLETED] == 0


def test_a_log_with_no_outcomes_reports_no_success_rate(project: Path, skills_dir: Path) -> None:
    """The failure this guards: dividing by all invocations would report 100%
    on a log that has never recorded a single outcome."""
    for _ in range(5):
        _record(project, "skill_invoked", "skill=sweetclaude:doctor", "phase=none")

    report = _report(project, skills_dir)
    assert report["success_rate"] is None
    assert report["totals"][ur.UNKNOWN] == 5


def test_unknowns_do_not_inflate_the_success_rate(project: Path, skills_dir: Path) -> None:
    _record(project, "skill_invoked", "skill=sweetclaude:doctor", "phase=none")
    _record(project, "skill_completed", "skill=sweetclaude:doctor", "outcome=completed")
    for _ in range(9):
        _record(project, "skill_invoked", "skill=sweetclaude:doctor", "phase=none")

    report = _report(project, skills_dir)
    assert report["success_rate"] == 1.0, "rate is over recorded outcomes"
    assert report["totals"][ur.UNKNOWN] == 9
    assert report["recorded_outcomes"] == 1


def test_a_second_invocation_before_completion_leaves_the_first_unknown(
    project: Path, skills_dir: Path
) -> None:
    _record(project, "skill_invoked", "skill=sweetclaude:doctor", "phase=none")
    _record(project, "skill_invoked", "skill=sweetclaude:doctor", "phase=none")
    _record(project, "skill_completed", "skill=sweetclaude:doctor", "outcome=completed")

    report = _report(project, skills_dir)
    assert report["totals"][ur.COMPLETED] == 1
    assert report["totals"][ur.UNKNOWN] == 1


# --- unobserved is not zero-failure -------------------------------------

def test_never_invoked_skills_are_reported_as_unobserved(project: Path, skills_dir: Path) -> None:
    _record(project, "skill_invoked", "skill=sweetclaude:doctor", "phase=none")

    report = _report(project, skills_dir)
    assert "sweetclaude:never-run" in report["unobserved_skills"]
    assert "sweetclaude:doctor" not in report["unobserved_skills"]
    assert report["observed_skills"] == 1
    assert report["known_skills"] == 3


def test_an_unobserved_skill_is_absent_from_per_skill_counts(
    project: Path, skills_dir: Path
) -> None:
    """It must not appear as a row of zeros, which would read as a clean record."""
    _record(project, "skill_invoked", "skill=sweetclaude:doctor", "phase=none")
    assert "sweetclaude:never-run" not in _report(project, skills_dir)["by_skill"]


# --- robustness ----------------------------------------------------------

def test_historic_events_without_outcomes_still_parse(project: Path, skills_dir: Path) -> None:
    """The existing log predates outcomes and must remain readable."""
    log = project / ".sweetclaude" / "metrics" / "events.log"
    log.write_text(
        "---\ntimestamp: 2026-05-01T00:00:00Z\nevent: skill_invoked\n"
        "skill: sweetclaude:doctor\nphase: none\n"
        "---\ntimestamp: 2026-05-01T00:01:00Z\nevent: session_start\nphase: none\n",
        encoding="utf-8")

    report = _report(project, skills_dir)
    assert report["events_parsed"] == 2
    assert report["totals"][ur.UNKNOWN] == 1


def test_a_malformed_record_does_not_discard_the_rest(project: Path, skills_dir: Path) -> None:
    """A half-written record from an interrupted shell redirect must not take
    the whole file with it."""
    log = project / ".sweetclaude" / "metrics" / "events.log"
    log.write_text(
        "---\ntimestamp: bad\nevent: skill_invoked\nskill: sweetclaude:doctor\n"
        "---\nthis line has no colon and no event\n"
        "---\ntimestamp: 2026-05-01T00:00:00Z\nevent: skill_completed\n"
        "skill: sweetclaude:doctor\noutcome: completed\n",
        encoding="utf-8")

    report = _report(project, skills_dir)
    assert report["totals"][ur.COMPLETED] == 1


def test_an_absent_log_reports_nothing_rather_than_failing(tmp_path: Path,
                                                           skills_dir: Path) -> None:
    report = _report(tmp_path, skills_dir)
    assert report["invocations"] == 0
    assert report["success_rate"] is None


def test_a_completion_with_no_invocation_is_still_counted(project: Path,
                                                          skills_dir: Path) -> None:
    """It happened. Dropping it would hide real outcomes."""
    _record(project, "skill_completed", "skill=sweetclaude:doctor", "outcome=failed")
    report = _report(project, skills_dir)
    assert report["totals"][ur.FAILED] == 1


def test_an_unrecognised_outcome_in_an_old_log_reads_as_unknown(project: Path,
                                                                skills_dir: Path) -> None:
    """The writer rejects these now, but a hand-edited or historic log may
    still contain one."""
    (project / ".sweetclaude" / "metrics" / "events.log").write_text(
        "---\ntimestamp: t\nevent: skill_invoked\nskill: sweetclaude:doctor\n"
        "---\ntimestamp: t\nevent: skill_completed\nskill: sweetclaude:doctor\n"
        "outcome: succeeded\n", encoding="utf-8")

    report = _report(project, skills_dir)
    assert report["totals"][ur.UNKNOWN] == 1
    assert report["totals"][ur.COMPLETED] == 0


# --- CLI and wiring ------------------------------------------------------

def test_cli_reports_json(project: Path, skills_dir: Path) -> None:
    _record(project, "skill_invoked", "skill=sweetclaude:doctor", "phase=none")
    r = subprocess.run([sys.executable, str(REPORT), "--project-dir", str(project),
                        "--skills-dir", str(skills_dir), "--format", "json"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["totals"]["unknown"] == 1


def test_cli_text_output_labels_unknown_as_not_a_success(project: Path,
                                                         skills_dir: Path) -> None:
    _record(project, "skill_invoked", "skill=sweetclaude:doctor", "phase=none")
    r = subprocess.run([sys.executable, str(REPORT), "--project-dir", str(project),
                        "--skills-dir", str(skills_dir)],
                       capture_output=True, text=True, timeout=60)
    assert "not a success" in r.stdout
    assert "unobserved, not zero-failure" in r.stdout


@pytest.mark.parametrize("skill", ["doctor", "code-verify"])
def test_wired_skills_record_their_outcome(skill: str) -> None:
    """The mechanism is worthless if nothing calls it."""
    category = {"doctor": "configure", "code-verify": "build"}[skill]
    text = (REPO_ROOT / "skill-library" / category / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "record-event.sh skill_completed" in text, (
        f"{skill} does not record an outcome")
    assert f"skill=sweetclaude:library-load {skill}" in text


def test_usage_skill_documents_the_outcome_event() -> None:
    text = (REPO_ROOT / "skill-library" / "configure" / "usage" / "SKILL.md").read_text(encoding="utf-8")
    assert "skill_completed" in text
    assert "unobserved" in text
