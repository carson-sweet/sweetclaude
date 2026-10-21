import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from large_story_controller import (
    BLOCKED_CLOSEOUT_MISSING_MESSAGE,
    BLOCKED_MISSING_LEDGER_MESSAGE,
    BLOCKED_SLICE0_MESSAGE,
    enter_design_phase,
    enter_implement_phase,
    enter_plan_phase,
    enter_ship_phase,
    enter_verify_phase,
    record_evidence,
    arm_enforcement_probe,
    check_enforcement_probe,
    route_large_story,
    transition_large_story,
    finalize_large_story,
    render_large_story_status,
    validate_ledger_evidence_paths,
    _check_init_preconditions,
    gate_tool_use,
    approve_amendment,
    amend_contract,
    init_workflow,
)
from success_criteria_contracts import compute_success_criteria_contract_hash


CRUD_SQLITE_PROMPT = (
    "/sweetclaude:large-story build a prototype CRUD-style web application "
    "with no authentication, using SQLite for the data."
)


def _mark_enforcement_verified(project, story_id="STORY-001"):
    """Simulate a passed enforcement probe (gate active: canary blocked)."""
    arm_enforcement_probe(project_dir=project, workflow_id=story_id)
    (project / ".sweetclaude" / ".enforcement-control").write_text("ok\n", encoding="utf-8")
    check_enforcement_probe(project_dir=project, workflow_id=story_id)


def _contract(story_id: str = "STORY-001") -> dict:
    contract = {
        "story_id": story_id,
        "story_title": "Large story controller test",
        "story_objective": "Prove large story completion is controller gated.",
        "expected_outcomes": [
            {"id": "OUTCOME-001", "statement": "Completion is evidence-bound."}
        ],
        "non_goals": [
            {"id": "NONGOAL-001", "statement": "Do not implement downstream workflow."}
        ],
        "success_criteria": [
            {
                "id": "SC-001",
                "outcome_id": "OUTCOME-001",
                "statement": "The completion validator returns status success.",
                "binary_predicate": "completion validator returns status success",
                "measurement_type": "schema_check",
                "measurement_procedure": "Run completion validator.",
                "evidence_artifact": ".sweetclaude/reports/large-story/STORY-001/evidence/SC-001.json",
                "evidence_owner": "controller",
                "pass_condition": "validator status equals success",
                "fail_condition": "validator status does not equal success",
                "allowed_phase_to_measure": "implementation",
                "amendment_policy": "human_approved_only",
                "backlog_routing": "Backlog any new concern.",
            }
        ],
        "contract_freeze": {
            "frozen_at": "2026-06-02T12:00:00Z",
            "frozen_by": "test",
            "contract_hash": "",
        },
    }
    contract["contract_freeze"]["contract_hash"] = compute_success_criteria_contract_hash(contract)
    return contract


def _crud_contract(story_id: str = "STORY-007") -> dict:
    contract = {
        "story_id": story_id,
        "story_title": "CRUD SQLite prototype regression",
        "story_objective": CRUD_SQLITE_PROMPT,
        "expected_outcomes": [
            {"id": "OUTCOME-001", "statement": "The prototype serves a web index."},
            {"id": "OUTCOME-002", "statement": "The prototype persists model rows in SQLite."},
            {"id": "OUTCOME-003", "statement": "The prototype records create behavior."},
        ],
        "non_goals": [
            {"id": "NONGOAL-001", "statement": "Authentication is excluded."}
        ],
        "success_criteria": [
            {
                "id": "SC-001",
                "outcome_id": "OUTCOME-001",
                "statement": "The index route returns HTTP 200.",
                "binary_predicate": "HTTP GET / returns status 200",
                "measurement_type": "command",
                "measurement_command": "test -s templates/index.html",
                "measurement_procedure": "Run curl against the local index route.",
                "evidence_artifact": f".sweetclaude/reports/large-story/{story_id}/evidence/SC-001.json",
                "evidence_owner": "controller",
                "pass_condition": "HTTP status equals 200",
                "fail_condition": "HTTP status is not 200",
                "allowed_phase_to_measure": "implementation",
                "amendment_policy": "human_approved_only",
                "backlog_routing": "Backlog any additional interface concern.",
            },
            {
                "id": "SC-002",
                "outcome_id": "OUTCOME-002",
                "statement": "The SQLite database file exists.",
                "binary_predicate": "models.db exists",
                "measurement_type": "command",
                "measurement_command": "test -s models.db",
                "measurement_procedure": "Run test -s models.db.",
                "evidence_artifact": f".sweetclaude/reports/large-story/{story_id}/evidence/SC-002.json",
                "evidence_owner": "controller",
                "pass_condition": "models.db exists",
                "fail_condition": "models.db is absent",
                "allowed_phase_to_measure": "implementation",
                "amendment_policy": "human_approved_only",
                "backlog_routing": "Backlog any additional persistence concern.",
            },
            {
                "id": "SC-003",
                "outcome_id": "OUTCOME-003",
                "statement": "The create path stores TestModel.",
                "binary_predicate": "sqlite query returns TestModel",
                "measurement_type": "command",
                "measurement_command": "grep -q TestModel models.db",
                "measurement_procedure": "Run sqlite3 query for TestModel.",
                "evidence_artifact": f".sweetclaude/reports/large-story/{story_id}/evidence/SC-003.json",
                "evidence_owner": "controller",
                "pass_condition": "sqlite query returns TestModel",
                "fail_condition": "sqlite query returns zero rows",
                "allowed_phase_to_measure": "implementation",
                "amendment_policy": "human_approved_only",
                "backlog_routing": "Backlog any additional CRUD concern.",
            },
        ],
        "contract_freeze": {
            "frozen_at": "2026-06-06T12:00:00Z",
            "frozen_by": "test",
            "contract_hash": "",
        },
    }
    contract["contract_freeze"]["contract_hash"] = compute_success_criteria_contract_hash(contract)
    return contract


def _write_define_ready_project(tmp_path: Path, story_id: str = "STORY-001") -> Path:
    project = tmp_path
    contract = _contract(story_id)
    contract_path = project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    workflow_path = project / ".sweetclaude" / "state" / "workflows" / f"{story_id}.yaml"
    phase_path = project / ".sweetclaude" / "state" / "phase.yaml"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    phase_path.parent.mkdir(parents=True, exist_ok=True)
    (project / ".sweetclaude" / "reports").mkdir(parents=True, exist_ok=True)
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    workflow_path.write_text(
        yaml.safe_dump(
            {
                "workflow_id": story_id,
                "requires_success_criteria_contract": True,
                "success_criteria_contract_path": str(contract_path.relative_to(project)),
                "success_criteria_contract_hash": contract["contract_freeze"]["contract_hash"],
                "criterion_ids": ["SC-001"],
                "success_criteria_ledger_path": ".sweetclaude/reports/success-criteria-ledger.json",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    phase_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "active_work_item": {
                    "id": story_id,
                    "phase": "DEFINE",
                    "entry_category": "large-story",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    _mark_enforcement_verified(project, story_id)
    return project


def _write_contract_project(project: Path, contract: dict) -> Path:
    story_id = contract["story_id"]
    contract_path = project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    workflow_path = project / ".sweetclaude" / "state" / "workflows" / f"{story_id}.yaml"
    phase_path = project / ".sweetclaude" / "state" / "phase.yaml"
    prompt_path = project / ".sweetclaude" / "reports" / "large-story" / story_id / "prompt.txt"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    phase_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    criterion_ids = [criterion["id"] for criterion in contract["success_criteria"]]
    workflow_path.write_text(
        yaml.safe_dump(
            {
                "workflow_id": story_id,
                "requires_success_criteria_contract": True,
                "success_criteria_contract_path": str(contract_path.relative_to(project)),
                "success_criteria_contract_hash": contract["contract_freeze"]["contract_hash"],
                "criterion_ids": criterion_ids,
                "success_criteria_ledger_path": ".sweetclaude/reports/success-criteria-ledger.json",
                "source_prompt_path": str(prompt_path.relative_to(project)),
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    phase_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "active_work_item": {
                    "id": story_id,
                    "phase": "DEFINE",
                    "entry_category": "large-story",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    prompt_path.write_text(CRUD_SQLITE_PROMPT + "\n", encoding="utf-8")
    _mark_enforcement_verified(project, contract['story_id'])
    return project


def _write_valid_ledger(project: Path, story_id: str = "STORY-001") -> Path:
    contract = yaml.safe_load(
        (project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml").read_text(
            encoding="utf-8"
        )
    )
    contract_hash = contract["contract_freeze"]["contract_hash"]
    evidence_path = project / ".sweetclaude" / "reports" / "large-story" / story_id / "evidence" / "SC-001.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps({"ok": True}) + "\n", encoding="utf-8")
    ledger_path = project / ".sweetclaude" / "reports" / "success-criteria-ledger.json"
    ledger_path.write_text(
        json.dumps(
            {
                "story_id": story_id,
                "workflow_id": story_id,
                "success_criteria_contract_hash": contract_hash,
                "generated_by": "large_story_controller",
                "generated_at": "2026-06-02T12:01:00Z",
                "all_success_criteria_passed": True,
                "criteria": [
                    {
                        "id": "SC-001",
                        "status": "pass",
                        "success_criteria_contract_hash": contract_hash,
                        "evidence_artifact": ".sweetclaude/reports/large-story/STORY-001/evidence/SC-001.json",
                        "evidence_owner": "controller",
                        "evidence_path": ".sweetclaude/reports/large-story/STORY-001/evidence/SC-001.json",
                        "measured_command": "pytest -q",
                        "measured_at": "2026-06-02T12:00:00Z",
                        "observed_output_path": ".sweetclaude/reports/large-story/STORY-001/evidence/SC-001.json",
                        "evidence_fresh": True,
                        "freshness_status": "fresh",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return ledger_path


def _record_hook_evidence(
    project: Path,
    workflow_id: str = "STORY-001",
    files: tuple[str, ...] = ("app.py",),
    commands: tuple[str, ...] = ("pytest -q",),
) -> None:
    """Mirror the Track C PostToolUse evidence hook for simulated flows."""
    for file_path in files:
        record_evidence(project_dir=project, tool="Write", file_path=file_path, workflow_id=workflow_id)
    for command in commands:
        record_evidence(project_dir=project, tool="Bash", command=command, workflow_id=workflow_id)


def _run_through_verify(project: Path) -> dict:
    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="Design.")
    enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="Plan.")
    enter_implement_phase(
        project_dir=project,
        workflow_id="STORY-001",
        implementation_summary="Implementation.",
        touched_files=["app.py"],
        commands_run=["pytest -q"],
    )
    _record_hook_evidence(project)
    return enter_verify_phase(project_dir=project, workflow_id="STORY-001")


def _write_fake_crud_app_files(project: Path) -> list[Path]:
    files = [
        project / "app.py",
        project / "templates" / "index.html",
        project / "models.db",
    ]
    files[1].parent.mkdir(parents=True, exist_ok=True)
    files[0].write_text("from flask import Flask\napp = Flask(__name__)\n", encoding="utf-8")
    files[1].write_text("<h1>LLM Models</h1>\n", encoding="utf-8")
    files[2].write_bytes(b"SQLite regression fixture\nTestModel\n")
    return files


def test_all_large_story_route_surfaces_are_final_status_enabled_until_later_slices(tmp_path):
    project = _write_define_ready_project(tmp_path)

    for route_surface in ("/sweetclaude:go", "sweetclaude:find-skill", "sweetclaude:_route"):
        result = route_large_story(project_dir=project, route_surface=route_surface)

        assert result["ok"] is True
        assert result["route_surface"] == route_surface
        assert result["large_story_behavior"] == "final_status_enabled_controller"
        assert result["design_enabled"] is True
        assert result["plan_enabled"] is True
        assert result["implementation_enabled"] is True
        assert result["verify_enabled"] is True
        assert result["ship_enabled"] is True
        assert result["final_status_enabled"] is True


def test_post_design_downstream_transition_is_blocked(tmp_path):
    project = _write_define_ready_project(tmp_path)

    result = transition_large_story(project_dir=project, workflow_id="STORY-001", target_stage="implement")

    assert result["ok"] is False
    assert result["code"] == "blocked_implementation_entry_failed"
    assert result["next_allowed_stage"] != "complete"


def test_design_can_enter_only_after_define_exit_validation_passes(tmp_path):
    project = _write_define_ready_project(tmp_path)

    result = enter_design_phase(
        project_dir=project,
        workflow_id="STORY-001",
        design_summary="Design uses a small web app and SQLite storage.",
    )

    assert result["ok"] is True
    assert result["status"] == "design"
    assert result["design_artifact_path"] == ".sweetclaude/reports/large-story/STORY-001/design/design-artifact.md"


def test_design_produces_durable_artifact_with_contract_hash(tmp_path):
    project = _write_define_ready_project(tmp_path)

    result = enter_design_phase(
        project_dir=project,
        workflow_id="STORY-001",
        design_summary="Design uses server-rendered pages and SQLite.",
    )

    artifact = project / result["design_artifact_path"]
    contract = yaml.safe_load(
        (project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml").read_text(
            encoding="utf-8"
        )
    )
    text = artifact.read_text(encoding="utf-8")
    assert artifact.exists()
    assert contract["contract_freeze"]["contract_hash"] in text
    assert "Design uses server-rendered pages and SQLite." in text
    assert "success_criteria:" not in text


def test_design_failure_blocks_instead_of_entering_implementation(tmp_path):
    project = _write_define_ready_project(tmp_path)
    (project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml").write_text(
        "not: a valid success criteria contract\n",
        encoding="utf-8",
    )

    result = enter_design_phase(
        project_dir=project,
        workflow_id="STORY-001",
        design_summary="Design should not be accepted.",
    )

    assert result["ok"] is False
    assert result["code"] == "blocked_design_entry_failed"
    assert result["next_allowed_stage"] != "implement"


def test_plan_can_enter_only_after_design_passes(tmp_path):
    project = _write_define_ready_project(tmp_path)

    blocked = enter_plan_phase(
        project_dir=project,
        workflow_id="STORY-001",
        plan_summary="Build from the approved design.",
    )

    assert blocked["ok"] is False
    assert blocked["code"] == "blocked_plan_entry_failed"
    assert blocked["next_allowed_stage"] != "implement"

    enter_design_phase(
        project_dir=project,
        workflow_id="STORY-001",
        design_summary="Design uses server-rendered pages and SQLite.",
    )

    allowed = enter_plan_phase(
        project_dir=project,
        workflow_id="STORY-001",
        plan_summary="Build from the approved design.",
    )

    assert allowed["ok"] is True
    assert allowed["status"] == "plan"
    assert allowed["next_allowed_stage"] == "implement"


def test_plan_produces_durable_artifact_with_contract_hash_and_criteria_mapping(tmp_path):
    project = _write_define_ready_project(tmp_path)
    enter_design_phase(
        project_dir=project,
        workflow_id="STORY-001",
        design_summary="Design uses server-rendered pages and SQLite.",
    )

    result = enter_plan_phase(
        project_dir=project,
        workflow_id="STORY-001",
        plan_summary="Implement routes, templates, and SQLite storage.",
    )

    artifact = project / result["plan_artifact_path"]
    contract = yaml.safe_load(
        (project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml").read_text(
            encoding="utf-8"
        )
    )
    text = artifact.read_text(encoding="utf-8")
    assert artifact.exists()
    assert contract["contract_freeze"]["contract_hash"] in text
    assert "SC-001" in text
    assert result["criterion_ids"] == ["SC-001"]
    assert "Implement routes, templates, and SQLite storage." in text


def test_plan_cannot_add_completion_criteria(tmp_path):
    project = _write_define_ready_project(tmp_path)
    enter_design_phase(
        project_dir=project,
        workflow_id="STORY-001",
        design_summary="Design uses server-rendered pages and SQLite.",
    )

    result = enter_plan_phase(
        project_dir=project,
        workflow_id="STORY-001",
        plan_summary="success_criteria:\n- Add a new criterion",
    )

    artifact = project / result["plan_artifact_path"]
    text = artifact.read_text(encoding="utf-8")
    assert result["ok"] is True
    assert "success_criteria:" not in text
    assert "Add a new criterion" in text


def test_plan_failure_blocks_instead_of_entering_implementation(tmp_path):
    project = _write_define_ready_project(tmp_path)
    enter_design_phase(
        project_dir=project,
        workflow_id="STORY-001",
        design_summary="Design uses server-rendered pages and SQLite.",
    )
    design_artifact = project / ".sweetclaude" / "reports" / "large-story" / "STORY-001" / "design" / "design-artifact.md"
    design_artifact.unlink()

    result = enter_plan_phase(
        project_dir=project,
        workflow_id="STORY-001",
        plan_summary="Plan should not be accepted.",
    )

    assert result["ok"] is False
    assert result["code"] == "blocked_plan_entry_failed"
    assert result["next_allowed_stage"] != "implement"


def test_implement_can_enter_only_after_plan_passes(tmp_path):
    project = _write_define_ready_project(tmp_path)

    blocked = enter_implement_phase(
        project_dir=project,
        workflow_id="STORY-001",
        implementation_summary="Implement from the approved plan.",
    )

    assert blocked["ok"] is False
    assert blocked["code"] == "blocked_implementation_entry_failed"
    assert blocked["next_allowed_stage"] != "verify"

    enter_design_phase(
        project_dir=project,
        workflow_id="STORY-001",
        design_summary="Design uses server-rendered pages and SQLite.",
    )
    enter_plan_phase(
        project_dir=project,
        workflow_id="STORY-001",
        plan_summary="Implement routes, templates, and SQLite storage.",
    )

    allowed = enter_implement_phase(
        project_dir=project,
        workflow_id="STORY-001",
        implementation_summary="Implement from the approved plan.",
    )

    assert allowed["ok"] is True
    assert allowed["status"] == "implement"
    assert allowed["next_allowed_stage"] == "verify"


def test_implement_records_touched_files_commands_and_environment_changes(tmp_path):
    project = _write_define_ready_project(tmp_path)
    enter_design_phase(
        project_dir=project,
        workflow_id="STORY-001",
        design_summary="Design uses server-rendered pages and SQLite.",
    )
    enter_plan_phase(
        project_dir=project,
        workflow_id="STORY-001",
        plan_summary="Implement routes, templates, and SQLite storage.",
    )

    result = enter_implement_phase(
        project_dir=project,
        workflow_id="STORY-001",
        implementation_summary="Created Flask CRUD app.",
        touched_files=["app.py", "templates/index.html"],
        commands_run=["python3 seed.py", "pytest -q"],
        dependency_changes=["requirements.txt: added flask"],
        environment_changes=["created models.db locally"],
    )

    artifact = project / result["implementation_artifact_path"]
    text = artifact.read_text(encoding="utf-8")
    assert artifact.exists()
    assert "app.py" in text
    assert "templates/index.html" in text
    assert "python3 seed.py" in text
    assert "pytest -q" in text
    assert "requirements.txt: added flask" in text
    assert "created models.db locally" in text
    assert result["touched_files"] == ["app.py", "templates/index.html"]
    assert result["commands_run"] == ["python3 seed.py", "pytest -q"]
    assert result["dependency_changes"] == ["requirements.txt: added flask"]
    assert result["environment_changes"] == ["created models.db locally"]


def test_implement_cannot_claim_criteria_pass(tmp_path):
    project = _write_define_ready_project(tmp_path)
    enter_design_phase(
        project_dir=project,
        workflow_id="STORY-001",
        design_summary="Design uses server-rendered pages and SQLite.",
    )
    enter_plan_phase(
        project_dir=project,
        workflow_id="STORY-001",
        plan_summary="Implement routes, templates, and SQLite storage.",
    )

    result = enter_implement_phase(
        project_dir=project,
        workflow_id="STORY-001",
        implementation_summary="All success criteria pass. Story complete.",
    )

    artifact = project / result["implementation_artifact_path"]
    text = artifact.read_text(encoding="utf-8").lower()
    assert result["ok"] is True
    assert "all success criteria pass" not in text
    assert "story complete" not in text
    assert result["completion_claim_allowed"] is False


def test_implement_failure_blocks_instead_of_entering_completion(tmp_path):
    project = _write_define_ready_project(tmp_path)
    enter_design_phase(
        project_dir=project,
        workflow_id="STORY-001",
        design_summary="Design uses server-rendered pages and SQLite.",
    )
    enter_plan_phase(
        project_dir=project,
        workflow_id="STORY-001",
        plan_summary="Implement routes, templates, and SQLite storage.",
    )
    plan_artifact = project / ".sweetclaude" / "reports" / "large-story" / "STORY-001" / "plan" / "implementation-plan.md"
    plan_artifact.unlink()

    result = enter_implement_phase(
        project_dir=project,
        workflow_id="STORY-001",
        implementation_summary="Implementation should not be accepted.",
    )

    assert result["ok"] is False
    assert result["code"] == "blocked_implementation_entry_failed"
    assert result["next_allowed_stage"] != "complete"


def test_verify_can_enter_only_after_implement_passes(tmp_path):
    project = _write_define_ready_project(tmp_path)

    blocked = enter_verify_phase(project_dir=project, workflow_id="STORY-001")

    assert blocked["ok"] is False
    assert blocked["code"] == "blocked_verify_entry_failed"
    assert blocked["next_allowed_stage"] != "ship"

    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="Design.")
    enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="Plan.")
    enter_implement_phase(
        project_dir=project,
        workflow_id="STORY-001",
        implementation_summary="Implementation evidence.",
        touched_files=["app.py"],
        commands_run=["pytest -q"],
    )
    _record_hook_evidence(project)

    allowed = enter_verify_phase(project_dir=project, workflow_id="STORY-001")

    assert allowed["ok"] is True
    assert allowed["status"] == "verify"
    assert allowed["next_allowed_stage"] == "ship"


def test_verify_writes_ledger_and_evidence_for_every_frozen_criterion(tmp_path):
    project = _write_define_ready_project(tmp_path)
    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="Design.")
    enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="Plan.")
    enter_implement_phase(
        project_dir=project,
        workflow_id="STORY-001",
        implementation_summary="Implementation evidence.",
        touched_files=["app.py"],
        commands_run=["pytest -q"],
    )
    _record_hook_evidence(project)

    result = enter_verify_phase(project_dir=project, workflow_id="STORY-001")

    ledger_path = project / result["ledger_path"]
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    contract = yaml.safe_load(
        (project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml").read_text(
            encoding="utf-8"
        )
    )
    contract_hash = contract["contract_freeze"]["contract_hash"]

    assert ledger_path.exists()
    assert ledger["generated_by"] == "large_story_controller"
    assert ledger["workflow_id"] == "STORY-001"
    assert ledger["success_criteria_contract_hash"] == contract_hash
    assert ledger["all_success_criteria_passed"] is True
    assert [entry["id"] for entry in ledger["criteria"]] == ["SC-001"]
    assert ledger["criteria"][0]["success_criteria_contract_hash"] == contract_hash
    assert ledger["criteria"][0]["measured_command"] == "controller.verify SC-001"
    assert ledger["criteria"][0]["evidence_path"]
    assert ledger["criteria"][0]["observed_output_path"]
    assert (project / ledger["criteria"][0]["evidence_path"]).exists()
    assert (project / ledger["criteria"][0]["observed_output_path"]).exists()


def test_verify_fails_closed_if_criterion_lacks_evidence(tmp_path):
    project = _write_define_ready_project(tmp_path)
    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="Design.")
    enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="Plan.")
    enter_implement_phase(project_dir=project, workflow_id="STORY-001", implementation_summary="Implementation.")
    _record_hook_evidence(project)

    result = enter_verify_phase(
        project_dir=project,
        workflow_id="STORY-001",
        criterion_results={"SC-001": {"status": "pass", "evidence_present": False}},
    )

    assert result["ok"] is False
    assert result["code"] == "blocked_verify_entry_failed"
    assert result["next_allowed_stage"] != "ship"


def test_verify_validation_fails_for_missing_or_bad_evidence_path(tmp_path):
    project = _write_define_ready_project(tmp_path)
    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="Design.")
    enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="Plan.")
    enter_implement_phase(project_dir=project, workflow_id="STORY-001", implementation_summary="Implementation.")
    _record_hook_evidence(project)
    result = enter_verify_phase(project_dir=project, workflow_id="STORY-001")
    ledger_path = project / result["ledger_path"]
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["criteria"][0]["evidence_path"] = ".sweetclaude/reports/large-story/STORY-001/evidence/missing.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    validation = validate_ledger_evidence_paths(project, ledger_path)

    assert validation["ok"] is False
    assert validation["code"] == "blocked_completion_validation_failed"
    assert "evidence_path does not exist" in validation["message"]


def test_verify_fails_closed_if_ledger_hash_does_not_match_contract(tmp_path):
    project = _write_define_ready_project(tmp_path)
    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="Design.")
    enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="Plan.")
    enter_implement_phase(project_dir=project, workflow_id="STORY-001", implementation_summary="Implementation.")
    _record_hook_evidence(project)
    result = enter_verify_phase(project_dir=project, workflow_id="STORY-001")
    ledger_path = project / result["ledger_path"]
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["success_criteria_contract_hash"] = "sha256:bad"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    completion = finalize_large_story(project_dir=project, workflow_id="STORY-001")

    assert completion["ok"] is False
    assert completion["code"] == "blocked_completion_validation_failed"


def test_missing_ledger_blocks_completion_and_success_language(tmp_path):
    project = _write_define_ready_project(tmp_path)

    result = finalize_large_story(
        project_dir=project,
        workflow_id="STORY-001",
        attempted_response="All success criteria pass. Story complete.",
    )

    assert result["ok"] is False
    assert result["code"] == "blocked_missing_completion_ledger"
    assert result["message"] == BLOCKED_MISSING_LEDGER_MESSAGE
    assert result["completion_claim_allowed"] is False
    assert result["forbidden_phrases_detected"]


def test_terminal_transition_requires_ship_closeout_even_with_valid_ledger(tmp_path):
    project = _write_define_ready_project(tmp_path)

    blocked = transition_large_story(project_dir=project, workflow_id="STORY-001", target_stage="complete")
    assert blocked["ok"] is False
    assert blocked["code"] == "blocked_missing_completion_ledger"

    _write_valid_ledger(project)

    still_blocked = transition_large_story(project_dir=project, workflow_id="STORY-001", target_stage="complete")
    assert still_blocked["ok"] is False
    assert still_blocked["code"] == "blocked_ship_closeout_missing"
    assert still_blocked["message"] == BLOCKED_CLOSEOUT_MISSING_MESSAGE
    assert still_blocked["completion_claim_allowed"] is False


def test_ship_can_enter_only_after_verify_passes(tmp_path):
    project = _write_define_ready_project(tmp_path)

    blocked = enter_ship_phase(project_dir=project, workflow_id="STORY-001")

    assert blocked["ok"] is False
    assert blocked["code"] == "blocked_missing_completion_ledger"
    assert blocked["next_allowed_stage"] != "complete"

    verify = _run_through_verify(project)

    allowed = enter_ship_phase(project_dir=project, workflow_id="STORY-001")

    assert verify["ok"] is True
    assert allowed["ok"] is True
    assert allowed["status"] == "ship"
    assert allowed["next_allowed_stage"] == "complete"
    assert allowed["completion_claim_allowed"] is True


def test_ship_blocks_if_ledger_all_success_is_not_true(tmp_path):
    project = _write_define_ready_project(tmp_path)
    _run_through_verify(project)
    ledger_path = project / ".sweetclaude" / "reports" / "success-criteria-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["all_success_criteria_passed"] = False
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    result = enter_ship_phase(project_dir=project, workflow_id="STORY-001")

    assert result["ok"] is False
    assert result["code"] == "blocked_completion_validation_failed"
    assert result["completion_claim_allowed"] is False


def test_ship_blocks_terminal_state_written_by_assistant_narrative(tmp_path):
    project = _write_define_ready_project(tmp_path)
    _run_through_verify(project)

    result = enter_ship_phase(
        project_dir=project,
        workflow_id="STORY-001",
        terminal_actor="assistant_narrative",
    )

    assert result["ok"] is False
    assert result["code"] == "blocked_assistant_terminal_state_mutation"
    assert result["completion_claim_allowed"] is False


def test_ship_writes_controller_owned_closeout_artifact_and_state(tmp_path):
    project = _write_define_ready_project(tmp_path)
    _run_through_verify(project)

    result = enter_ship_phase(project_dir=project, workflow_id="STORY-001")

    closeout_path = project / result["closeout_artifact_path"]
    closeout = json.loads(closeout_path.read_text(encoding="utf-8"))
    archived_path = project / ".sweetclaude" / "state" / "workflows" / "archived" / "STORY-001.yaml"
    active_path = project / ".sweetclaude" / "state" / "workflows" / "STORY-001.yaml"
    assert archived_path.exists(), "Completed workflow should be archived"
    assert not active_path.exists(), "ISSUE-212 regression: active workflow file must be removed after archiving"
    workflow = yaml.safe_load(archived_path.read_text(encoding="utf-8"))

    assert closeout_path.exists()
    assert closeout["generated_by"] == "large_story_controller"
    assert closeout["workflow_id"] == "STORY-001"
    assert closeout["terminal_state"] == "complete"
    assert closeout["terminal_state_owner"] == "large_story_controller"
    assert closeout["completion_validation_ok"] is True
    assert workflow["status"] == "complete"
    assert workflow["terminal_state_written_by"] == "large_story_controller"
    assert workflow["ship_closeout_artifact_path"] == result["closeout_artifact_path"]


def test_completion_allowed_only_after_ship_closeout(tmp_path):
    project = _write_define_ready_project(tmp_path)
    verify = _run_through_verify(project)

    completion = finalize_large_story(
        project_dir=project,
        workflow_id="STORY-001",
        attempted_response="All success criteria pass. Story complete.",
    )

    assert verify["ok"] is True
    assert completion["ok"] is False
    assert completion["code"] == "blocked_ship_closeout_missing"
    assert completion["completion_claim_allowed"] is False
    assert completion["forbidden_phrases_detected"]

    ship = enter_ship_phase(project_dir=project, workflow_id="STORY-001")
    completion_after_ship = finalize_large_story(
        project_dir=project,
        workflow_id="STORY-001",
        attempted_response="All success criteria pass. Story complete.",
    )
    rendered = render_large_story_status(project_dir=project, workflow_id="STORY-001")

    assert ship["ok"] is True
    assert completion_after_ship["ok"] is True
    assert completion_after_ship["completion_claim_allowed"] is True
    assert rendered["status"] == "complete"
    assert rendered["completion_claim_allowed"] is True


def test_final_status_distinguishes_phase_artifacts_from_workflow_completion(tmp_path):
    project = _write_define_ready_project(tmp_path)
    _run_through_verify(project)

    rendered = render_large_story_status(project_dir=project, workflow_id="STORY-001")

    assert rendered["generated_by"] == "large_story_controller"
    assert rendered["controller_owned"] is True
    assert rendered["status"] == "blocked_ship_closeout_missing"
    assert rendered["workflow_completion"]["complete"] is False
    assert rendered["phase_artifacts"]["design"]["present"] is True
    assert rendered["phase_artifacts"]["plan"]["present"] is True
    assert rendered["phase_artifacts"]["implementation"]["present"] is True
    assert rendered["phase_artifacts"]["ledger"]["present"] is True
    assert rendered["phase_artifacts"]["ship_closeout"]["present"] is False
    assert rendered["completion_validator_result"]["ok"] is True
    assert rendered["completion_claim_allowed"] is False


def test_final_status_lists_missing_criteria_when_ledger_is_missing(tmp_path):
    project = _write_define_ready_project(tmp_path)

    rendered = render_large_story_status(project_dir=project, workflow_id="STORY-001")

    assert rendered["status"] == "blocked_missing_completion_ledger"
    assert rendered["completion_validator_result"]["ok"] is False
    assert rendered["criteria_summary"]["missing_criteria"] == ["SC-001"]
    assert rendered["criteria_summary"]["failed_criteria"] == []
    assert rendered["completion_claim_allowed"] is False


def test_final_status_lists_failed_criteria_from_ledger(tmp_path):
    project = _write_define_ready_project(tmp_path)
    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="Design.")
    enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="Plan.")
    enter_implement_phase(project_dir=project, workflow_id="STORY-001", implementation_summary="Implementation.")
    _record_hook_evidence(project)
    result = enter_verify_phase(
        project_dir=project,
        workflow_id="STORY-001",
        criterion_results={"SC-001": {"status": "fail", "observed_output": "criterion failed"}},
    )

    rendered = render_large_story_status(project_dir=project, workflow_id="STORY-001")

    assert result["ok"] is False
    assert rendered["status"] == "blocked_completion_validation_failed"
    assert rendered["criteria_summary"]["failed_criteria"] == ["SC-001"]
    assert rendered["criteria_summary"]["criteria"][0]["status"] == "fail"
    assert rendered["workflow_completion"]["complete"] is False


def test_final_status_after_ship_includes_completion_validator_and_closeout(tmp_path):
    project = _write_define_ready_project(tmp_path)
    _run_through_verify(project)
    enter_ship_phase(project_dir=project, workflow_id="STORY-001")

    rendered = render_large_story_status(project_dir=project, workflow_id="STORY-001")

    assert rendered["status"] == "complete"
    assert rendered["workflow_completion"]["complete"] is True
    assert rendered["completion_validator_result"]["ok"] is True
    assert rendered["criteria_summary"]["all_success_criteria_passed"] is True
    assert rendered["criteria_summary"]["failed_criteria"] == []
    assert rendered["phase_artifacts"]["ship_closeout"]["present"] is True
    assert rendered["product_readiness"]["ready"] is False
    assert "TASK-008" in rendered["product_readiness"]["remaining_tasks"]
    assert "TASK-007" not in rendered["product_readiness"]["remaining_tasks"]


def test_full_crud_sqlite_large_story_regression_controller_flow(tmp_path):
    project = tmp_path / "crud-sqlite-large-story-regression"
    contract = _crud_contract()
    workflow_id = contract["story_id"]
    _write_contract_project(project, contract)

    app_files = [
        project / "app.py",
        project / "templates" / "index.html",
        project / "models.db",
    ]
    prompt_path = project / ".sweetclaude" / "reports" / "large-story" / workflow_id / "prompt.txt"

    assert prompt_path.read_text(encoding="utf-8").strip() == CRUD_SQLITE_PROMPT
    assert all(not path.exists() for path in app_files)

    phases = []
    define = transition_large_story(project_dir=project, workflow_id=workflow_id, target_stage="define")
    phases.append(define["status"])

    design = enter_design_phase(
        project_dir=project,
        workflow_id=workflow_id,
        design_summary="Use a small server-rendered CRUD web app backed by SQLite.",
    )
    phases.append(design["status"])

    plan = enter_plan_phase(
        project_dir=project,
        workflow_id=workflow_id,
        plan_summary="Implement index route, SQLite persistence, and create behavior.",
    )
    phases.append(plan["status"])

    assert all(not path.exists() for path in app_files)

    implement = enter_implement_phase(
        project_dir=project,
        workflow_id=workflow_id,
        implementation_summary="Created prototype CRUD app files for the approved SQLite story.",
        touched_files=["app.py", "templates/index.html", "models.db"],
        commands_run=["python3 seed.py", "pytest -q tests/crud_regression"],
        dependency_changes=["requirements.txt: flask"],
        environment_changes=["models.db local fixture"],
    )
    phases.append(implement["status"])
    created_files = _write_fake_crud_app_files(project)
    _record_hook_evidence(
        project,
        workflow_id=workflow_id,
        files=("app.py", "templates/index.html", "models.db"),
        commands=("python3 seed.py", "pytest -q tests/crud_regression"),
    )

    assert all(path.exists() and path.stat().st_size > 0 for path in created_files)
    assert not (project / ".sweetclaude" / "reports" / "success-criteria-ledger.json").exists()

    verify = enter_verify_phase(
        project_dir=project,
        workflow_id=workflow_id,
        criterion_results={
            "SC-001": {
                "status": "pass",
                "measured_command": "curl -s -o /dev/null -w '%{http_code}' http://localhost:5001/",
                "observed_output": "200",
            },
            "SC-002": {
                "status": "pass",
                "measured_command": "test -s models.db",
                "observed_output": "models.db exists",
            },
            "SC-003": {
                "status": "pass",
                "measured_command": "sqlite3 models.db \"SELECT model FROM models WHERE model='TestModel'\"",
                "observed_output": "TestModel",
            },
        },
    )
    phases.append(verify["status"])

    ledger_path = project / verify["ledger_path"]
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger_path.exists()
    assert [entry["id"] for entry in ledger["criteria"]] == ["SC-001", "SC-002", "SC-003"]
    assert ledger["all_success_criteria_passed"] is True

    blocked_completion = finalize_large_story(
        project_dir=project,
        workflow_id=workflow_id,
        attempted_response="All success criteria pass. Story complete.",
    )
    assert blocked_completion["ok"] is False
    assert blocked_completion["code"] == "blocked_ship_closeout_missing"
    assert blocked_completion["completion_claim_allowed"] is False

    ship = enter_ship_phase(project_dir=project, workflow_id=workflow_id)
    phases.append(ship["status"])

    status_before_final_response = render_large_story_status(project_dir=project, workflow_id=workflow_id)
    assert status_before_final_response["completion_validator_result"]["ok"] is True
    assert status_before_final_response["workflow_completion"]["complete"] is True
    assert status_before_final_response["product_readiness"]["ready"] is False
    assert "TASK-008" in status_before_final_response["product_readiness"]["remaining_tasks"]

    final = finalize_large_story(
        project_dir=project,
        workflow_id=workflow_id,
        attempted_response="All success criteria pass. Story complete.",
    )
    phases.append(final["status"])

    assert phases == ["define", "design", "plan", "implement", "verify", "ship", "complete"]
    assert final["ok"] is True
    assert final["completion_claim_allowed"] is True

    durable_artifacts = [
        project / design["design_artifact_path"],
        project / plan["plan_artifact_path"],
        project / implement["implementation_artifact_path"],
        ledger_path,
        project / ship["closeout_artifact_path"],
        prompt_path,
        *[project / entry["evidence_path"] for entry in ledger["criteria"]],
    ]
    assert all(path.exists() and path.stat().st_size > 0 for path in durable_artifacts)


def test_transition_ship_and_complete_are_controller_owned(tmp_path):
    project = _write_define_ready_project(tmp_path)
    _run_through_verify(project)

    ship = transition_large_story(project_dir=project, workflow_id="STORY-001", target_stage="ship")
    completion = transition_large_story(project_dir=project, workflow_id="STORY-001", target_stage="complete")

    assert ship["ok"] is True
    assert ship["status"] == "ship"
    assert completion["ok"] is True
    assert completion["status"] == "complete"


def test_ledger_evidence_path_is_required_and_must_exist(tmp_path):
    project = _write_define_ready_project(tmp_path)
    ledger_path = _write_valid_ledger(project)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["criteria"][0]["evidence_path"] = ".sweetclaude/reports/large-story/STORY-001/evidence/missing.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    result = validate_ledger_evidence_paths(project, ledger_path)

    assert result["ok"] is False
    assert result["code"] == "blocked_completion_validation_failed"
    assert "evidence_path does not exist" in result["message"]


def test_wlf063_integrated_regression_blocks_overclaim(tmp_path):
    project = _write_define_ready_project(tmp_path)

    downstream = transition_large_story(
        project_dir=project,
        workflow_id="STORY-001",
        target_stage="implement",
    )
    completion = finalize_large_story(
        project_dir=project,
        workflow_id="STORY-001",
        attempted_response="All 1 success criteria pass. The story is complete.",
    )
    rendered = render_large_story_status(project_dir=project, workflow_id="STORY-001")

    assert downstream["code"] == "blocked_implementation_entry_failed"
    assert completion["code"] == "blocked_missing_completion_ledger"
    assert completion["completion_claim_allowed"] is False
    assert rendered["status"] == "blocked_missing_completion_ledger"
    assert rendered["completion_claim_allowed"] is False
    assert "complete" not in rendered["allowed_summary"].lower()


# --- ER: re-init/rebind of the SAME in-flight workflow (init precondition fix) ---

def _git_init_main(project: Path) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.test",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.test",
    }
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=project, check=True)
    (project / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=project, env=env, check=True)


def _commit_all(project: Path) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.test",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.test",
    }
    subprocess.run(["git", "add", "-A"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "wf"], cwd=project, env=env, check=True)


def _write_inflight_workflow(project: Path, story_id: str) -> None:
    wf = project / ".sweetclaude" / "state" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    (wf / f"{story_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "workflow_id": story_id,
                "phase": "DEFINE",
                "state_owner": "large_story_controller",
                "requires_success_criteria_contract": True,
                "status": "define",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_reinit_same_inflight_workflow_not_blocked_by_preconditions(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    _git_init_main(project)
    _write_inflight_workflow(project, "STORY-001")
    _commit_all(project)
    # Re-binding the SAME in-flight workflow must not be blocked by preconditions.
    assert _check_init_preconditions(project, workflow_id="STORY-001") is None


def test_init_blocked_when_a_different_workflow_is_inflight(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    _git_init_main(project)
    _write_inflight_workflow(project, "STORY-001")
    _commit_all(project)
    result = _check_init_preconditions(project, workflow_id="STORY-002")
    assert result is not None
    assert result["code"] == "blocked_inflight_workflow"


# --- ER: approval-gated contract amendment + gate scratchpad scoping ---

def _write_amendable_project(tmp_path: Path, story_id: str = "STORY-001") -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    contract = _contract(story_id)
    cdir = project / ".sweetclaude" / "contracts"
    cdir.mkdir(parents=True)
    (cdir / "success-criteria-contract.yaml").write_text(
        yaml.safe_dump(contract, sort_keys=False), encoding="utf-8"
    )
    wfdir = project / ".sweetclaude" / "state" / "workflows"
    wfdir.mkdir(parents=True)
    (wfdir / f"{story_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "workflow_id": story_id,
                "phase": "DESIGN",
                "state_owner": "large_story_controller",
                "requires_success_criteria_contract": True,
                "status": "design",
                "success_criteria_contract_path": ".sweetclaude/contracts/success-criteria-contract.yaml",
                "success_criteria_contract_hash": contract["contract_freeze"]["contract_hash"],
                "criterion_ids": ["SC-001"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return project


def test_approve_amendment_records_scoped_single_use_token(tmp_path):
    project = _write_amendable_project(tmp_path)
    res = approve_amendment(
        project_dir=project, workflow_id="STORY-001",
        criterion_id="SC-001", reason="SC-001 encodes the wrong mechanism",
    )
    assert res["ok"] is True
    assert res["approval_ref"]
    receipt = json.loads((project / res["receipt_path"]).read_text())
    assert receipt["consumed"] is False
    assert receipt["workflow_id"] == "STORY-001"
    assert receipt["criterion_id"] == "SC-001"
    assert receipt["single_use"] is True


def test_approve_amendment_rejects_unknown_criterion(tmp_path):
    project = _write_amendable_project(tmp_path)
    res = approve_amendment(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-999", reason="x"
    )
    assert res["ok"] is False


def test_amend_contract_applies_refreezes_rebinds_and_audits(tmp_path):
    project = _write_amendable_project(tmp_path)
    cpath = project / ".sweetclaude/contracts/success-criteria-contract.yaml"
    wpath = project / ".sweetclaude/state/workflows/STORY-001.yaml"
    old_hash = yaml.safe_load(wpath.read_text())["success_criteria_contract_hash"]
    ref = approve_amendment(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001", reason="wrong mechanism"
    )["approval_ref"]

    res = amend_contract(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001",
        approval_ref=ref, fields={"statement": "Amended statement."},
    )
    assert res["ok"] is True
    assert res["new_contract_hash"] and res["new_contract_hash"] != old_hash

    # contract content changed
    sc1 = next(c for c in yaml.safe_load(cpath.read_text())["success_criteria"] if c["id"] == "SC-001")
    assert sc1["statement"] == "Amended statement."

    # workflow rebound to new hash, phase preserved (NOT reset to DEFINE)
    wstate = yaml.safe_load(wpath.read_text())
    assert wstate["success_criteria_contract_hash"] == res["new_contract_hash"]
    assert wstate["phase"] == "DESIGN"

    # audit record
    audit = json.loads((project / res["receipt_path"]).read_text())
    assert audit["old_contract_hash"] == old_hash
    assert audit["new_contract_hash"] == res["new_contract_hash"]
    assert audit["field_diff"]["statement"]["new"] == "Amended statement."


def test_amend_contract_token_is_single_use(tmp_path):
    project = _write_amendable_project(tmp_path)
    ref = approve_amendment(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001", reason="x"
    )["approval_ref"]
    first = amend_contract(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001",
        approval_ref=ref, fields={"statement": "A"},
    )
    assert first["ok"] is True
    second = amend_contract(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001",
        approval_ref=ref, fields={"statement": "B"},
    )
    assert second["ok"] is False
    assert second["code"] == "blocked_amend_consumed"


def test_amend_contract_without_approval_is_blocked(tmp_path):
    project = _write_amendable_project(tmp_path)
    res = amend_contract(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001",
        approval_ref="deadbeefdeadbeef", fields={"statement": "A"},
    )
    assert res["ok"] is False
    assert res["code"] == "blocked_amend_no_approval"


def test_amend_contract_rejects_non_amendable_field(tmp_path):
    project = _write_amendable_project(tmp_path)
    ref = approve_amendment(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001", reason="x"
    )["approval_ref"]
    res = amend_contract(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001",
        approval_ref=ref, fields={"id": "SC-XYZ"},
    )
    assert res["ok"] is False
    assert res["code"] == "blocked_amend_fields"


def test_gate_allows_out_of_project_scratchpad_write(tmp_path):
    project = _write_amendable_project(tmp_path)
    scratch = tmp_path / "scratch_out"
    scratch.mkdir()
    res = gate_tool_use(project_dir=project, tool="Write", file_path=str(scratch / "notes.md"))
    assert res["allow"] is True


def test_gate_still_blocks_inproject_source_write_outside_implement(tmp_path):
    project = _write_amendable_project(tmp_path)
    (project / "src").mkdir()
    res = gate_tool_use(project_dir=project, tool="Write", file_path=str(project / "src" / "app.py"))
    assert res["allow"] is False


# --- init rebind preserves an active workflow's phase ---

def _seed_backlog(project: Path, story_id: str) -> None:
    bl = project / ".sweetclaude" / "product" / "backlog"
    bl.mkdir(parents=True, exist_ok=True)
    (bl / f"{story_id}-test.md").write_text(f"# {story_id}\n", encoding="utf-8")


def test_init_rebind_preserves_phase_for_active_workflow(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    _git_init_main(project)
    contract = _contract("STORY-001")
    cdir = project / ".sweetclaude" / "contracts"
    cdir.mkdir(parents=True)
    (cdir / "success-criteria-contract.yaml").write_text(
        yaml.safe_dump(contract, sort_keys=False), encoding="utf-8"
    )
    _seed_backlog(project, "STORY-001")
    _commit_all(project)

    first = init_workflow(project_dir=project, workflow_id="STORY-001")
    assert first["ok"] is True
    assert first["status"] == "define"

    # Simulate in-flight progress to DESIGN, then commit (clean tree for re-init).
    wpath = project / ".sweetclaude/state/workflows/STORY-001.yaml"
    w = yaml.safe_load(wpath.read_text())
    w["phase"] = "DESIGN"
    w["status"] = "design"
    wpath.write_text(yaml.safe_dump(w, sort_keys=False), encoding="utf-8")
    _commit_all(project)

    # Re-init the SAME workflow must REBIND, not reset to DEFINE.
    second = init_workflow(project_dir=project, workflow_id="STORY-001")
    assert second["ok"] is True
    assert second["status"] == "rebound"
    assert second["phase"] == "DESIGN"
    assert yaml.safe_load(wpath.read_text())["phase"] == "DESIGN"
