"""Completion receipts record what happened, not what was claimed (ISSUE-283).

`evidence.py` had no subprocess import and never ran the command it recorded.
A receipt reading `status: pass, command: "npm test"` asserted that the suite
passed; it was not evidence of it. Found by writing exactly that receipt
against a project with no test script, during the non-self-project trial.

The receipt is what gates closing an issue, so the completion gate was
accepting an assertion. That is not a fail-closed gate — it is a formality
producing an audit trail of claims.

The fix is not better trust. Once the script runs the command itself, nobody
is being asked to be honest about the result, so the question does not arise.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
EVIDENCE = REPO_ROOT / "scripts" / "evidence.py"
STATUS = REPO_ROOT / "scripts" / "status.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import evidence as ev  # noqa: E402


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".sweetclaude" / "state").mkdir(parents=True)
    return tmp_path


def write(project: Path, *args: str) -> dict:
    r = subprocess.run([sys.executable, str(EVIDENCE), "write",
                        "--project-dir", str(project), *args],
                       capture_output=True, text=True, timeout=120)
    return json.loads(r.stdout)


def latest(project: Path, subject: str) -> Path:
    return sorted((project / ".sweetclaude" / "state" / "evidence")
                  .glob(f"{subject}-*.json"))[-1]


# --- the bug this closes -------------------------------------------------

def test_a_pass_cannot_be_claimed_for_a_command_that_fails(project: Path) -> None:
    """The exact shape of the original defect: assert success, run something
    that fails, and see whether anything objects."""
    out = write(project, "--subject-id", "ISSUE-1", "--receipt-type", "completion",
                "--check", "tests", "--status", "pass",
                "--command", "exit 1", "--run")
    assert out["ok"] is False
    assert "must be pass" in out["error"]


def test_what_happened_overrides_what_was_claimed(project: Path) -> None:
    """Preserving the caller's optimistic status would defeat running it."""
    result = ev.run_check("exit 3", project)
    assert result["status"] == "fail"
    assert result["exit_code"] == 3
    assert result["verified"] is True


def test_a_genuinely_passing_command_is_recorded_verified(project: Path) -> None:
    out = write(project, "--subject-id", "ISSUE-2", "--receipt-type", "completion",
                "--check", "tests", "--status", "pass", "--command", "true", "--run")
    assert out["ok"] is True
    assert out["verified"] is True

    receipt = json.loads(latest(project, "ISSUE-2").read_text())
    assert receipt["verified"] is True
    assert receipt["checks"][0]["verified"] is True
    assert receipt["checks"][0]["exit_code"] == 0


def test_the_output_is_kept_so_a_pass_can_be_inspected(project: Path) -> None:
    """A receipt saying pass with no output is still only a claim about a run."""
    write(project, "--subject-id", "ISSUE-3", "--receipt-type", "completion",
          "--check", "tests", "--status", "pass",
          "--command", "echo 'distinctive marker text'", "--run")
    receipt = json.loads(latest(project, "ISSUE-3").read_text())
    assert "distinctive marker text" in receipt["checks"][0]["output_tail"]


# --- unverified receipts are marked, not banned --------------------------

def test_without_run_the_receipt_is_marked_unverified(project: Path) -> None:
    """Still writable — some checks are genuinely manual — but the difference
    between evidence and a claim is recorded rather than assumed."""
    out = write(project, "--subject-id", "ISSUE-4", "--receipt-type", "completion",
                "--check", "manual review", "--status", "pass",
                "--command", "npm test")
    assert out["ok"] is True
    assert out["verified"] is False

    receipt = json.loads(latest(project, "ISSUE-4").read_text())
    assert receipt["verified"] is False
    assert receipt["checks"][0]["verified"] is False, (
        "the per-check field must agree with the receipt, or a reader looking "
        "at the check sees a verification that did not happen")


def test_run_without_a_command_is_refused(project: Path) -> None:
    out = write(project, "--subject-id", "ISSUE-5", "--receipt-type", "completion",
                "--check", "tests", "--status", "pass", "--run")
    assert out["ok"] is False
    assert "command" in out["error"]


# --- validation ----------------------------------------------------------

def test_validate_rejects_an_unverified_receipt_when_asked(project: Path) -> None:
    write(project, "--subject-id", "ISSUE-6", "--receipt-type", "completion",
          "--check", "tests", "--status", "pass", "--command", "npm test")
    with pytest.raises(ValueError, match="not verified"):
        ev.validate_receipt(latest(project, "ISSUE-6"), subject_id="ISSUE-6",
                            require_verified=True)


def test_validate_accepts_a_verified_receipt(project: Path) -> None:
    write(project, "--subject-id", "ISSUE-7", "--receipt-type", "completion",
          "--check", "tests", "--status", "pass", "--command", "true", "--run")
    receipt = ev.validate_receipt(latest(project, "ISSUE-7"), subject_id="ISSUE-7",
                                  require_verified=True)
    assert receipt["verified"] is True


def test_a_more_specific_fault_is_reported_ahead_of_verification(
    project: Path
) -> None:
    """"Re-run with --run" is unhelpful advice when the real problem is that
    this receipt belongs to a different issue."""
    write(project, "--subject-id", "ISSUE-OTHER", "--receipt-type", "completion",
          "--check", "tests", "--status", "pass", "--command", "npm test")
    with pytest.raises(ValueError, match="subject mismatch"):
        ev.validate_receipt(latest(project, "ISSUE-OTHER"), subject_id="ISSUE-MINE",
                            require_verified=True)


def test_validation_stays_lenient_by_default(project: Path) -> None:
    """Receipts written before verification existed must remain readable."""
    write(project, "--subject-id", "ISSUE-8", "--receipt-type", "completion",
          "--check", "tests", "--status", "pass", "--command", "npm test")
    assert ev.validate_receipt(latest(project, "ISSUE-8"), subject_id="ISSUE-8")


def test_a_historic_receipt_without_the_field_is_not_verified(project: Path) -> None:
    """Absence of the field means nobody watched, which is different from a
    recorded failure to verify."""
    d = project / ".sweetclaude" / "state" / "evidence"
    d.mkdir(parents=True, exist_ok=True)
    old = d / "ISSUE-9-completion-2026-01-01T00-00-00Z.json"
    old.write_text(json.dumps({
        "schema_version": 1, "receipt_type": "completion", "subject_id": "ISSUE-9",
        "status": "pass", "created_at": "2026-01-01T00:00:00Z",
        "checks": [{"name": "tests", "status": "pass",
                    "command": "npm test"}]}), encoding="utf-8")

    assert ev.validate_receipt(old, subject_id="ISSUE-9")
    with pytest.raises(ValueError, match="not verified"):
        ev.validate_receipt(old, subject_id="ISSUE-9", require_verified=True)


# --- the completion gate -------------------------------------------------

def _issue(project: Path, iid: str = "ISSUE-900") -> Path:
    import datetime
    issues = project / ".sweetclaude" / "product" / "roadmap" / "issues"
    (issues / "done").mkdir(parents=True, exist_ok=True)
    (project / ".sweetclaude" / "state" / "sweetclaude.yaml").write_text(
        yaml.safe_dump({"schema_version": 2, "framework": {"setup_complete": True}}),
        encoding="utf-8")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    fm = {"id": iid, "type": "bug-fix", "title": "thing", "status": "in-review",
          "priority": "P2", "effort": "s", "epic": None, "milestone": None,
          "sprint": None, "tags": [], "origin": "manual", "created": now,
          "updated": now, "closed_date": None}
    path = issues / f"{iid}-thing.md"
    path.write_text(f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---\n\nbody\n",
                    encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(project)],
                   capture_output=True, timeout=30)
    return path


def _close(project: Path, issue: Path, receipt: Path) -> dict:
    r = subprocess.run([sys.executable, str(STATUS), "set-terminal",
                        "--file", str(issue), "--status", "done", "--actor", "test",
                        "--project-dir", str(project),
                        "--evidence-receipt", str(receipt)],
                       capture_output=True, text=True, timeout=120)
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_an_issue_cannot_be_closed_on_an_unverified_receipt(project: Path) -> None:
    """The point of the whole change. Before this, an assertion closed an issue."""
    issue = _issue(project)
    write(project, "--subject-id", "ISSUE-900", "--receipt-type", "completion",
          "--check", "tests", "--status", "pass", "--command", "npm test")

    out = _close(project, issue, latest(project, "ISSUE-900"))

    assert "error" in out
    assert "not verified" in out["error"]
    assert issue.exists(), "the issue must not have moved to done"


def test_an_issue_closes_on_a_verified_receipt(project: Path) -> None:
    issue = _issue(project)
    write(project, "--subject-id", "ISSUE-900", "--receipt-type", "completion",
          "--check", "tests", "--status", "pass", "--command", "true", "--run")

    out = _close(project, issue, latest(project, "ISSUE-900"))

    assert out.get("status") == "done", out


def test_closing_still_requires_a_receipt_at_all(project: Path) -> None:
    issue = _issue(project)
    r = subprocess.run([sys.executable, str(STATUS), "set-terminal",
                        "--file", str(issue), "--status", "done", "--actor", "test",
                        "--project-dir", str(project)],
                       capture_output=True, text=True, timeout=120)
    assert "error" in json.loads(r.stdout.strip().splitlines()[-1])


# --- run_check's own behaviour -------------------------------------------

def test_a_failing_command_is_reported_verified_and_failed(project: Path) -> None:
    """Verified means observed, not successful. A watched failure is evidence."""
    result = ev.run_check("exit 1", project)
    assert result["verified"] is True
    assert result["status"] == "fail"


def test_a_command_that_cannot_run_is_a_failure_not_a_crash(project: Path) -> None:
    result = ev.run_check("this-command-does-not-exist-anywhere", project)
    assert result["status"] == "fail"
    assert result["verified"] is True


def test_a_timeout_is_recorded_as_a_failure(project: Path) -> None:
    result = ev.run_check("sleep 5", project, timeout=1)
    assert result["status"] == "fail"
    assert "timed out" in result["output_tail"]


def test_the_command_runs_in_the_project_directory(project: Path) -> None:
    """A check must run against the project it is evidence for."""
    (project / "marker.txt").write_text("x", encoding="utf-8")
    assert ev.run_check("test -f marker.txt", project)["status"] == "pass"


def test_output_is_truncated_rather_than_unbounded(project: Path) -> None:
    result = ev.run_check("head -c 100000 /dev/zero | tr '\\0' 'a'", project)
    assert len(result["output_tail"]) <= ev.OUTPUT_TAIL_CHARS
