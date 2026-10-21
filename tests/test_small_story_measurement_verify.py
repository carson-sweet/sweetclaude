import json
import os
import sys
import time
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
TESTS_DIR = Path(__file__).parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from small_story_controller import (
    _completion_gate_result,
    enter_verify_phase,
    init_workflow,
    record_evidence,
)
from success_criteria_contracts import compute_success_criteria_contract_hash
from test_small_story_gate import (
    _advance_to_implement,
    _create_backlog_file,
    _write_contract,
)

STORY = "STORY-001"


def _criterion(index, command, timeout=None, **overrides):
    cid = f"SC-{index:03d}"
    criterion = {
        "id": cid,
        "outcome_id": "OUTCOME-001",
        "statement": f"Measurement command {index} exits with code 0.",
        "binary_predicate": f"measurement command {index} exits with code 0",
        "measurement_type": "command",
        "measurement_command": command,
        "measurement_procedure": f"Run measurement command {index}; record the exit code.",
        "evidence_artifact": f".sweetclaude/reports/small-story/{STORY}/evidence/{cid}.json",
        "evidence_owner": "controller",
        "pass_condition": "Exit code equals 0",
        "fail_condition": "Exit code differs from 0",
        "allowed_phase_to_measure": "implementation",
        "amendment_policy": "human_approved_only",
        "backlog_routing": "Backlog any new concern.",
    }
    if timeout is not None:
        criterion["measurement_timeout_seconds"] = timeout
    criterion.update(overrides)
    return criterion


def _contract(criteria):
    contract = {
        "story_id": STORY,
        "story_title": "Controller runs measurements",
        "story_objective": "Prove the controller executes criterion measurement commands.",
        "expected_outcomes": [{"id": "OUTCOME-001", "statement": "Verification is measured."}],
        "non_goals": [{"id": "NONGOAL-001", "statement": "Do not add reviewers."}],
        "success_criteria": criteria,
        "contract_freeze": {
            "frozen_at": "2026-10-21T12:00:00Z",
            "frozen_by": "test",
            "contract_hash": "",
        },
    }
    contract["contract_freeze"]["contract_hash"] = compute_success_criteria_contract_hash(contract)
    return contract


def _verify_ready(tmp_path, criteria):
    project = tmp_path / "proj"
    project.mkdir()
    _create_backlog_file(project, STORY)
    _write_contract(project, _contract(criteria))
    assert init_workflow(project_dir=project, workflow_id=STORY)["ok"]
    _advance_to_implement(project, STORY)
    record_evidence(project_dir=project, tool="Write", file_path="app.py", workflow_id=STORY)
    return project


def _ledger(project):
    path = project / ".sweetclaude" / "reports" / "success-criteria-ledger.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _ledger_entry(project, criterion_id):
    return next(e for e in _ledger(project)["criteria"] if e["id"] == criterion_id)


def _evidence(project, criterion_id):
    path = project / ".sweetclaude" / "reports" / "small-story" / STORY / "evidence" / f"{criterion_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


class TestControllerRunsMeasurementAtVerify:
    def test_passing_command_records_pass_and_evidence(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "echo measured-ok; true")])
        result = enter_verify_phase(project_dir=project, workflow_id=STORY)
        assert result["ok"] is True
        assert result["all_success_criteria_passed"] is True

        entry = _ledger_entry(project, "SC-001")
        assert entry["status"] == "pass"
        assert entry["measured_command"] == "echo measured-ok; true"
        assert entry["measured_at"] != "controller-generated"

        evidence = _evidence(project, "SC-001")
        assert evidence["measured_command"] == "echo measured-ok; true"
        assert evidence["exit_code"] == 0
        assert "measured-ok" in evidence["output_tail"]
        assert evidence["ok"] is True
        stamp = evidence["measured_at"]
        assert isinstance(stamp, str) and stamp.endswith("Z") and int(stamp[:4]) >= 2026

    def test_nonzero_exit_records_fail_with_exit_code(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "sh -c 'exit 3'")])
        result = enter_verify_phase(project_dir=project, workflow_id=STORY)
        assert result["ok"] is False
        assert _ledger_entry(project, "SC-001")["status"] == "fail"
        evidence = _evidence(project, "SC-001")
        assert evidence["exit_code"] == 3
        assert evidence["ok"] is False
        assert evidence["measured_command"] == "sh -c 'exit 3'"

    def test_command_runs_in_project_directory(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "touch ran-here.marker")])
        assert enter_verify_phase(project_dir=project, workflow_id=STORY)["ok"] is True
        assert (project / "ran-here.marker").exists()

    def test_cwd_is_project_dir_when_caller_cwd_differs(self, tmp_path, monkeypatch):
        project = _verify_ready(
            tmp_path,
            [_criterion(1, f'test "$(pwd -P)" = "{os.path.realpath(tmp_path / "proj")}" && touch cwd-ok.marker')],
        )
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        assert enter_verify_phase(project_dir=project, workflow_id=STORY)["ok"] is True
        assert (project / "cwd-ok.marker").exists()

    def test_output_tail_is_bounded_and_keeps_the_end(self, tmp_path):
        command = "python3 -c \"print('x' * 200000); print('FINAL-MARKER')\""
        project = _verify_ready(tmp_path, [_criterion(1, command)])
        assert enter_verify_phase(project_dir=project, workflow_id=STORY)["ok"] is True
        tail = _evidence(project, "SC-001")["output_tail"]
        assert len(tail) <= 20000
        assert "FINAL-MARKER" in tail

    def test_each_command_criterion_is_run(self, tmp_path):
        project = _verify_ready(
            tmp_path, [_criterion(1, "touch one.marker"), _criterion(2, "touch two.marker")]
        )
        assert enter_verify_phase(project_dir=project, workflow_id=STORY)["ok"] is True
        assert (project / "one.marker").exists() and (project / "two.marker").exists()
        assert [e["id"] for e in _ledger(project)["criteria"]] == ["SC-001", "SC-002"]


class TestCallerCannotOverrideCommandStatus:
    def test_supplied_pass_for_failing_command_still_fails(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "false")])
        result = enter_verify_phase(
            project_dir=project,
            workflow_id=STORY,
            criterion_results={"SC-001": {"status": "pass", "measured_command": "true"}},
        )
        assert result["ok"] is False
        entry = _ledger_entry(project, "SC-001")
        assert entry["status"] == "fail"
        assert entry["measured_command"] == "false"
        assert _evidence(project, "SC-001")["exit_code"] == 1

    def test_supplied_fail_for_passing_command_still_passes(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "true")])
        result = enter_verify_phase(
            project_dir=project,
            workflow_id=STORY,
            criterion_results={"SC-001": {"status": "fail", "observed_output": "forged"}},
        )
        assert result["ok"] is True
        assert _ledger_entry(project, "SC-001")["status"] == "pass"
        assert "forged" not in json.dumps(_evidence(project, "SC-001"))

    def test_omitting_results_no_longer_defaults_to_pass(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "false")])
        result = enter_verify_phase(project_dir=project, workflow_id=STORY)
        assert result["ok"] is False
        assert _ledger_entry(project, "SC-001")["status"] == "fail"
        assert _ledger(project)["all_success_criteria_passed"] is False

    def test_supplied_results_do_not_skip_the_measurement(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "touch measured.marker")])
        enter_verify_phase(
            project_dir=project,
            workflow_id=STORY,
            criterion_results={"SC-001": {"status": "pass", "observed_output": "claimed"}},
        )
        assert (project / "measured.marker").exists()


class TestFailingMeasurementBlocksCompletion:
    def test_verify_blocks_and_names_only_failing_criterion(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "true"), _criterion(2, "sh -c 'exit 3'")])
        result = enter_verify_phase(project_dir=project, workflow_id=STORY)
        assert result["ok"] is False
        assert result["next_allowed_stage"] != "ship"
        dumped = json.dumps(result)
        assert "SC-002" in dumped
        assert "SC-001" not in dumped

    def test_completion_gate_denies_and_names_failing_ids(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "true"), _criterion(2, "false")])
        enter_verify_phase(project_dir=project, workflow_id=STORY)
        gate = _completion_gate_result(project_dir=project, workflow_id=STORY)
        assert gate["ok"] is False
        assert gate.get("completion_claim_allowed", False) is False
        dumped = json.dumps(gate)
        assert "SC-002" in dumped
        assert "SC-001" not in dumped

    def test_all_commands_passing_leaves_completion_gate_valid(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "true"), _criterion(2, "true")])
        assert enter_verify_phase(project_dir=project, workflow_id=STORY)["ok"] is True
        gate = _completion_gate_result(project_dir=project, workflow_id=STORY)
        assert gate["ok"] is True
        assert _ledger_entry(project, "SC-002")["measured_command"] == "true"
        assert _evidence(project, "SC-002")["exit_code"] == 0


class TestMeasurementTimeout:
    def test_command_exceeding_timeout_records_fail_with_reason(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "sleep 5", timeout=1)])
        started = time.monotonic()
        result = enter_verify_phase(project_dir=project, workflow_id=STORY)
        elapsed = time.monotonic() - started
        assert elapsed < 4.5
        assert result["ok"] is False
        assert _ledger_entry(project, "SC-001")["status"] == "fail"
        evidence = _evidence(project, "SC-001")
        assert evidence["ok"] is False
        assert evidence["timed_out"] is True
        assert "timeout" in evidence["failure_reason"].lower()
        assert evidence["measured_command"] == "sleep 5"

    def test_timed_out_criterion_is_named_and_blocks(self, tmp_path):
        project = _verify_ready(
            tmp_path, [_criterion(1, "true"), _criterion(2, "sleep 5", timeout=1)]
        )
        result = enter_verify_phase(project_dir=project, workflow_id=STORY)
        assert result["ok"] is False
        assert result["next_allowed_stage"] != "ship"
        dumped = json.dumps(result)
        assert "SC-002" in dumped
        assert "SC-001" not in dumped

    def test_command_within_timeout_is_not_marked_timed_out(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "true", timeout=5)])
        assert enter_verify_phase(project_dir=project, workflow_id=STORY)["ok"] is True
        assert _evidence(project, "SC-001")["timed_out"] is False

    def test_default_timeout_allows_a_short_command_without_declared_timeout(self, tmp_path):
        project = _verify_ready(tmp_path, [_criterion(1, "sleep 1")])
        assert enter_verify_phase(project_dir=project, workflow_id=STORY)["ok"] is True
        assert _evidence(project, "SC-001")["timed_out"] is False
