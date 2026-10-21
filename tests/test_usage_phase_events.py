"""Tests for phase_gate_check and phase_transition events from controllers (SC-004)."""

import subprocess
from pathlib import Path

import pytest
import yaml

CONTROLLER = Path(__file__).resolve().parent.parent / "scripts" / "large_story_controller.py"
SMALL_CONTROLLER = Path(__file__).resolve().parent.parent / "scripts" / "small_story_controller.py"
CONTRACTS = Path(__file__).resolve().parent.parent / "scripts" / "success_criteria_contracts.py"


@pytest.fixture()
def workflow_project(tmp_path):
    """Create a project with a frozen contract ready for phase transitions."""
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    sc = tmp_path / ".sweetclaude"
    (sc / "state").mkdir(parents=True)
    (sc / "metrics").mkdir(parents=True)
    (sc / "metrics" / "config.yaml").write_text("schema_version: 1\nenabled: true\n")
    (sc / "state" / "sweetclaude.yaml").write_text(yaml.dump({
        "schema_version": 2,
        "framework": {"setup_complete": True},
        "work": {"active": {"phase": "DEFINE"}},
    }))
    (sc / "state" / "phase.yaml").write_text("phase: DEFINE\n")

    backlog_dir = tmp_path / "docs" / "product" / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    (backlog_dir / "TEST-001-test.md").write_text(
        "---\nid: TEST-001\nstatus: new\n---\nTest.\n", encoding="utf-8",
    )

    subprocess.run(
        ["python3", str(CONTRACTS), "init-contract", "--project-dir", str(tmp_path),
         "--story-id", "TEST-001", "--title", "Test", "--criteria", "1"],
        capture_output=True, check=True,
    )
    contract_path = sc / "contracts" / "success-criteria-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text())
    contract["story_objective"] = "Test objective"
    contract["expected_outcomes"][0]["statement"] = "Test outcome"
    contract["non_goals"][0]["statement"] = "Test non-goal"
    sc_crit = contract["success_criteria"][0]
    sc_crit["statement"] = "Test criterion passes"
    sc_crit["binary_predicate"] = "true exits with code 0"
    sc_crit["measurement_command"] = "true"
    contract_path.write_text(yaml.dump(contract, default_flow_style=False))

    subprocess.run(
        ["python3", str(CONTRACTS), "freeze-contract", "--project-dir", str(tmp_path)],
        capture_output=True, check=True,
    )
    subprocess.run(
        ["python3", str(CONTROLLER), "--project-dir", str(tmp_path),
         "init", "--workflow-id", "TEST-001"],
        capture_output=True, check=True,
    )
    return tmp_path


def _read_events(project_dir: Path) -> list[dict]:
    log = project_dir / ".sweetclaude" / "metrics" / "events.log"
    if not log.exists():
        return []
    text = log.read_text()
    blocks = [b.strip() for b in text.split("---") if b.strip()]
    return [yaml.safe_load(b) for b in blocks]


class TestPhaseEvents:
    def test_design_transition_emits_gate_check_and_transition(self, workflow_project):
        subprocess.run(
            ["python3", str(CONTROLLER), "--project-dir", str(workflow_project),
             "design", "--workflow-id", "TEST-001", "--design-summary", "test design"],
            capture_output=True, check=True,
        )
        events = _read_events(workflow_project)
        gate_checks = [e for e in events if e["event"] == "phase_gate_check"]
        transitions = [e for e in events if e["event"] == "phase_transition"]
        assert len(gate_checks) >= 1
        assert gate_checks[0]["phase"] == "DEFINE"
        assert gate_checks[0]["result"] == "pass"
        assert len(transitions) >= 1
        assert transitions[0]["from"] == "DEFINE"
        assert transitions[0]["to"] == "DESIGN"

    def test_plan_transition_emits_events(self, workflow_project):
        subprocess.run(
            ["python3", str(CONTROLLER), "--project-dir", str(workflow_project),
             "design", "--workflow-id", "TEST-001", "--design-summary", "test"],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["python3", str(CONTROLLER), "--project-dir", str(workflow_project),
             "plan", "--workflow-id", "TEST-001", "--plan-summary", "test plan"],
            capture_output=True, check=True,
        )
        events = _read_events(workflow_project)
        transitions = [e for e in events if e["event"] == "phase_transition"]
        assert any(t["from"] == "DESIGN" and t["to"] == "PLAN" for t in transitions)
