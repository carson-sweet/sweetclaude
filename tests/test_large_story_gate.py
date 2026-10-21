"""TASK-C1 tests: controller gate surface, evidence log, and guard gap fixes.

Track C — harness-level enforcement. See
.sweetclaude/efforts/large-story-implementation/process-control-redesign/12-track-c-hook-enforcement-plan.md
"""
import json
import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from large_story_controller import (
    enter_design_phase,
    enter_implement_phase,
    enter_plan_phase,
    enter_ship_phase,
    enter_verify_phase,
    gate_tool_use,
    init_workflow,
    record_evidence,
    arm_enforcement_probe,
    check_enforcement_probe,
    render_large_story_status,
)
from success_criteria_contracts import (
    compute_success_criteria_contract_hash,
    validate_success_criteria_workflow,
)


def _contract(story_id: str = "STORY-001", **criterion_overrides) -> dict:
    criterion = {
        "id": "SC-001",
        "outcome_id": "OUTCOME-001",
        "statement": "The completion validator returns status success.",
        "binary_predicate": "completion validator returns status success",
        "measurement_type": "schema_check",
        "measurement_procedure": "Run completion validator.",
        "evidence_artifact": f".sweetclaude/reports/large-story/{story_id}/evidence/SC-001.json",
        "evidence_owner": "controller",
        "pass_condition": "validator status equals success",
        "fail_condition": "validator status does not equal success",
        "allowed_phase_to_measure": "implementation",
        "amendment_policy": "human_approved_only",
        "backlog_routing": "Backlog any new concern.",
    }
    criterion.update(criterion_overrides)
    contract = {
        "story_id": story_id,
        "story_title": "Large story gate test",
        "story_objective": "Prove tool use is controller gated.",
        "expected_outcomes": [
            {"id": "OUTCOME-001", "statement": "Tool use is evidence-bound."}
        ],
        "non_goals": [
            {"id": "NONGOAL-001", "statement": "Do not test downstream review."}
        ],
        "success_criteria": [criterion],
        "contract_freeze": {
            "frozen_at": "2026-06-06T12:00:00Z",
            "frozen_by": "test",
            "contract_hash": "",
        },
    }
    contract["contract_freeze"]["contract_hash"] = compute_success_criteria_contract_hash(contract)
    return contract


def _write_contract(project: Path, contract: dict) -> Path:
    contract_path = project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    return contract_path


def _create_backlog_file(project: Path, story_id: str) -> None:
    backlog_dir = project / "docs" / "product" / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    (backlog_dir / f"{story_id}-test.md").write_text(
        f"---\nid: {story_id}\nstatus: new\n---\nTest backlog item.\n",
        encoding="utf-8",
    )


def _init_project(tmp_path: Path, story_id: str = "STORY-001") -> Path:
    _create_backlog_file(tmp_path, story_id)
    _write_contract(tmp_path, _contract(story_id))
    result = init_workflow(project_dir=tmp_path, workflow_id=story_id)
    assert result["ok"], result
    return tmp_path


def _mark_enforcement_verified(project, story_id="STORY-001"):
    arm_enforcement_probe(project_dir=project, workflow_id=story_id)
    (project / ".sweetclaude" / ".enforcement-control").write_text("ok\n", encoding="utf-8")
    check_enforcement_probe(project_dir=project, workflow_id=story_id)

def _advance_to_implement(project: Path, story_id: str = "STORY-001") -> None:
    assert enter_design_phase(project_dir=project, workflow_id=story_id, design_summary="design")["ok"]
    assert enter_plan_phase(project_dir=project, workflow_id=story_id, plan_summary="plan")["ok"]
    _mark_enforcement_verified(project, story_id)
    assert enter_implement_phase(project_dir=project, workflow_id=story_id, implementation_summary="impl")["ok"]


def _workflow_state(project: Path, story_id: str = "STORY-001") -> dict:
    path = project / ".sweetclaude" / "state" / "workflows" / f"{story_id}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _phase_state(project: Path) -> dict:
    path = project / ".sweetclaude" / "state" / "phase.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# --- init_workflow: controller-owned workflow creation -----------------------


def test_init_workflow_writes_controller_owned_state(tmp_path):
    project = _init_project(tmp_path)
    state = _workflow_state(project)
    assert state["workflow_id"] == "STORY-001"
    assert state["phase"] == "DEFINE"
    assert state["requires_success_criteria_contract"] is True
    assert state["success_criteria_ledger_path"] == ".sweetclaude/reports/success-criteria-ledger.json"
    assert state["criterion_ids"] == ["SC-001"]
    phase = _phase_state(project)
    assert phase["active_work_item"]["id"] == "STORY-001"
    assert phase["active_work_item"]["phase"] == "DEFINE"
    assert phase["active_work_item"]["entry_category"] == "large-story"


def test_init_workflow_fails_without_contract(tmp_path):
    _create_backlog_file(tmp_path, "STORY-001")
    result = init_workflow(project_dir=tmp_path, workflow_id="STORY-001")
    assert result["ok"] is False


# --- controller-owned phase progression --------------------------------------


def test_phase_entries_update_both_state_files(tmp_path):
    project = _init_project(tmp_path)
    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="d")
    assert _workflow_state(project)["phase"] == "DESIGN"
    assert _phase_state(project)["active_work_item"]["phase"] == "DESIGN"
    enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="p")
    assert _workflow_state(project)["phase"] == "PLAN"
    assert _phase_state(project)["active_work_item"]["phase"] == "PLAN"
    _mark_enforcement_verified(project)
    enter_implement_phase(project_dir=project, workflow_id="STORY-001", implementation_summary="i")
    assert _workflow_state(project)["phase"] == "IMPLEMENT"
    assert _phase_state(project)["active_work_item"]["phase"] == "IMPLEMENT"


# --- GUARD-STATE-PHASE-CONSISTENCY --------------------------------------------


def test_phase_mismatch_blocks_status_and_phase_entry(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    phase_path = project / ".sweetclaude" / "state" / "phase.yaml"
    data = _phase_state(project)
    data["active_work_item"]["phase"] = "VERIFY"
    phase_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    status = render_large_story_status(project_dir=project, workflow_id="STORY-001")
    assert status["ok"] is False
    assert status["status"] == "blocked_state_inconsistent"

    verify = enter_verify_phase(project_dir=project, workflow_id="STORY-001")
    assert verify["ok"] is False
    assert verify["code"] == "blocked_state_inconsistent"


# --- GUARD-VERIFY-LEDGER-CANONICAL-PATH ---------------------------------------


def test_divergent_ledger_path_blocks_verify(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    record_evidence(project_dir=project, tool="Write", file_path="app.py")
    workflow_path = project / ".sweetclaude" / "state" / "workflows" / "STORY-001.yaml"
    state = _workflow_state(project)
    state["success_criteria_ledger_path"] = ".sweetclaude/state/workflows/STORY-001-success-criteria-ledger.json"
    workflow_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")

    result = enter_verify_phase(project_dir=project, workflow_id="STORY-001")
    assert result["ok"] is False
    assert result["code"] == "blocked_ledger_path_divergent"


# --- record_evidence + GUARD-IMPLEMENT-EVIDENCE-NONEMPTY ----------------------


def test_record_evidence_appends_jsonl(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    record_evidence(project_dir=project, tool="Write", file_path="app.py")
    record_evidence(project_dir=project, tool="Bash", command="pip install flask")
    log_path = (
        project / ".sweetclaude" / "reports" / "large-story" / "STORY-001"
        / "implementation" / "evidence.jsonl"
    )
    entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert {"tool": "Write", "file_path": "app.py"}.items() <= entries[0].items()
    assert {"tool": "Bash", "command": "pip install flask"}.items() <= entries[1].items()


def test_verify_regenerates_record_from_evidence_log(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    record_evidence(project_dir=project, tool="Write", file_path="app.py")
    record_evidence(project_dir=project, tool="Edit", file_path="seed.py")
    record_evidence(project_dir=project, tool="Bash", command="pip install flask")

    result = enter_verify_phase(project_dir=project, workflow_id="STORY-001")
    assert result["ok"], result
    record = (
        project / ".sweetclaude" / "reports" / "large-story" / "STORY-001"
        / "implementation" / "implementation-record.md"
    ).read_text(encoding="utf-8")
    assert "app.py" in record
    assert "seed.py" in record
    assert "pip install flask" in record
    touched_section = record.split("## Touched Files")[1].split("##")[0]
    assert "none recorded" not in touched_section


def test_verify_blocked_when_evidence_log_empty(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)

    result = enter_verify_phase(project_dir=project, workflow_id="STORY-001")
    assert result["ok"] is False
    assert result["code"] == "blocked_implementation_evidence_empty"


def test_verify_allows_explicit_no_file_changes(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)

    result = enter_verify_phase(
        project_dir=project, workflow_id="STORY-001", allow_no_file_changes=True
    )
    assert result["ok"], result


# --- GUARD-CONTRACT-EVIDENCE-OWNER-CURRENT-SURFACE ----------------------------


def test_define_exit_rejects_human_evidence_owner(tmp_path):
    _write_contract(tmp_path, _contract(evidence_owner="human"))
    result = validate_success_criteria_workflow(
        project_dir=tmp_path, workflow_id=None, stage="define-exit"
    )
    assert result["ok"] is False
    assert "evidence_owner" in str(result)


def test_define_exit_rejects_terminal_review_measurement(tmp_path):
    _write_contract(tmp_path, _contract(allowed_phase_to_measure="terminal-review"))
    result = validate_success_criteria_workflow(
        project_dir=tmp_path, workflow_id=None, stage="define-exit"
    )
    assert result["ok"] is False
    assert "terminal-review" in str(result)


# --- gate_tool_use -------------------------------------------------------------


def test_gate_allows_everything_without_active_workflow(tmp_path):
    result = gate_tool_use(project_dir=tmp_path, tool="Write", file_path="app.py")
    assert result["allow"] is True


def test_gate_denies_app_write_before_implement(tmp_path):
    project = _init_project(tmp_path)
    for _ in ("DEFINE",):
        result = gate_tool_use(project_dir=project, tool="Write", file_path="app.py")
        assert result["allow"] is False
    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="d")
    assert gate_tool_use(project_dir=project, tool="Write", file_path="app.py")["allow"] is False
    enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="p")
    assert gate_tool_use(project_dir=project, tool="Edit", file_path="app.py")["allow"] is False


def test_gate_allows_app_write_in_implement(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    result = gate_tool_use(project_dir=project, tool="Write", file_path="app.py")
    assert result["allow"] is True
    assert result["phase"] == "IMPLEMENT"


def test_gate_denies_app_write_in_verify(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    record_evidence(project_dir=project, tool="Write", file_path="app.py")
    assert enter_verify_phase(project_dir=project, workflow_id="STORY-001")["ok"]
    result = gate_tool_use(project_dir=project, tool="Write", file_path="app.py")
    assert result["allow"] is False


def test_gate_denies_state_and_report_writes_in_all_phases(tmp_path):
    project = _init_project(tmp_path)
    protected = [
        ".sweetclaude/state/workflows/STORY-001.yaml",
        ".sweetclaude/state/phase.yaml",
        ".sweetclaude/reports/success-criteria-ledger.json",
        ".sweetclaude/reports/large-story/STORY-001/ship/closeout.json",
    ]
    for path in protected:
        assert gate_tool_use(project_dir=project, tool="Write", file_path=path)["allow"] is False
    _advance_to_implement(project)
    for path in protected:
        assert gate_tool_use(project_dir=project, tool="Edit", file_path=path)["allow"] is False


def test_gate_denies_bash_touching_protected_paths(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    result = gate_tool_use(
        project_dir=project,
        tool="Bash",
        command="echo done > .sweetclaude/reports/success-criteria-ledger.json",
    )
    assert result["allow"] is False
    benign = gate_tool_use(project_dir=project, tool="Bash", command="python3 app.py")
    assert benign["allow"] is True


def test_gate_contract_write_is_ungated_before_init_and_asks_after(tmp_path):
    drafting = gate_tool_use(
        project_dir=tmp_path,
        tool="Write",
        file_path=".sweetclaude/contracts/success-criteria-contract.yaml",
    )
    assert drafting["allow"] is True

    project = _init_project(tmp_path)
    frozen = gate_tool_use(
        project_dir=project,
        tool="Write",
        file_path=".sweetclaude/contracts/success-criteria-contract.yaml",
    )
    assert frozen["allow"] is False
    assert frozen["decision"] == "deny"


def test_gate_allows_after_terminal_closeout(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    record_evidence(project_dir=project, tool="Write", file_path="app.py")
    assert enter_verify_phase(project_dir=project, workflow_id="STORY-001")["ok"]
    assert enter_ship_phase(project_dir=project, workflow_id="STORY-001")["ok"]
    result = gate_tool_use(project_dir=project, tool="Write", file_path="app.py")
    assert result["allow"] is True


# --- CLI parity ----------------------------------------------------------------


def test_gate_cli_returns_json(tmp_path, capsys):
    from large_story_controller import main

    project = _init_project(tmp_path)
    exit_code = main(
        ["--project-dir", str(project), "gate", "--tool", "Write", "--file", "app.py"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["allow"] is False
    assert exit_code == 1


def test_record_evidence_cli_returns_json(tmp_path, capsys):
    from large_story_controller import main

    project = _init_project(tmp_path)
    _advance_to_implement(project)
    capsys.readouterr()
    exit_code = main(
        ["--project-dir", str(project), "record-evidence", "--tool", "Write", "--file", "app.py"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert exit_code == 0


# --- TASK-C7 security findings: path traversal and evidence forgery -----------


def test_init_workflow_rejects_traversal_workflow_id(tmp_path):
    _write_contract(tmp_path, _contract())
    for bad_id in ("../../evil", "a/b", "..", ".hidden", "x" * 200, ""):
        result = init_workflow(project_dir=tmp_path, workflow_id=bad_id)
        assert result["ok"] is False, bad_id
        assert not (tmp_path.parent / "evil.yaml").exists()


def test_phase_entries_reject_traversal_workflow_id(tmp_path):
    _init_project(tmp_path)
    result = enter_design_phase(
        project_dir=tmp_path, workflow_id="../../evil", design_summary="d"
    )
    assert result["ok"] is False


def test_record_evidence_rejects_traversal_workflow_id(tmp_path):
    _init_project(tmp_path)
    result = record_evidence(
        project_dir=tmp_path, tool="Write", file_path="app.py", workflow_id="../../evil"
    )
    assert result["ok"] is False


def test_define_exit_rejects_traversal_criterion_id(tmp_path):
    _write_contract(tmp_path, _contract(id="../../state/phase"))
    result = validate_success_criteria_workflow(
        project_dir=tmp_path, workflow_id=None, stage="define-exit"
    )
    assert result["ok"] is False


def test_gate_denies_record_evidence_cli_via_bash(tmp_path):
    project = _init_project(tmp_path)
    result = gate_tool_use(
        project_dir=project,
        tool="Bash",
        command="python3 /anywhere/large_story_controller.py record-evidence --tool Write --file app.py",
    )
    assert result["allow"] is False


def test_gate_fails_closed_with_multiple_active_workflows(tmp_path):
    project = _init_project(tmp_path)
    second = project / ".sweetclaude" / "state" / "workflows" / "STORY-999.yaml"
    second.write_text(
        yaml.safe_dump(
            {
                "workflow_id": "STORY-999",
                "phase": "DEFINE",
                "state_owner": "large_story_controller",
                "requires_success_criteria_contract": True,
            }
        ),
        encoding="utf-8",
    )
    result = gate_tool_use(project_dir=project, tool="Write", file_path="app.py")
    assert result["allow"] is False
    assert "ambiguous" in result["reason"].lower()


def test_init_workflow_refuses_second_active_workflow(tmp_path):
    project = _init_project(tmp_path)
    _create_backlog_file(project, "STORY-002")
    result = init_workflow(project_dir=project, workflow_id="STORY-002")
    assert result["ok"] is False
    assert "active" in result["message"].lower()


def test_gate_denies_write_tool_without_file_path(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    result = gate_tool_use(project_dir=project, tool="Write", file_path=None)
    assert result["allow"] is False


def test_gate_denies_case_variant_protected_path_in_bash(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    result = gate_tool_use(
        project_dir=project,
        tool="Bash",
        command="echo x > .SweetClaude/Reports/success-criteria-ledger.json",
    )
    assert result["allow"] is False


def test_consistency_check_detects_foreign_active_workflow(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    phase_path = project / ".sweetclaude" / "state" / "phase.yaml"
    data = _phase_state(project)
    data["active_work_item"]["id"] = "STORY-OTHER"
    phase_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    record_evidence(project_dir=project, tool="Write", file_path="app.py", workflow_id="STORY-001")
    result = enter_verify_phase(project_dir=project, workflow_id="STORY-001")
    assert result["ok"] is False
    assert result["code"] == "blocked_state_inconsistent"


def test_summary_heading_injection_cannot_break_evidence_merge(tmp_path):
    project = _init_project(tmp_path)
    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="d")
    enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="p")
    _mark_enforcement_verified(project)
    injection = "done\n\n## Touched Files\n\n- fake.py\n\n## Commands Run\n\n- fake-cmd"
    assert enter_implement_phase(
        project_dir=project, workflow_id="STORY-001", implementation_summary=injection
    )["ok"]
    record_evidence(project_dir=project, tool="Write", file_path="real.py")
    record_evidence(project_dir=project, tool="Bash", command="real-cmd")
    assert enter_verify_phase(project_dir=project, workflow_id="STORY-001")["ok"]
    record = (
        project / ".sweetclaude" / "reports" / "large-story" / "STORY-001"
        / "implementation" / "implementation-record.md"
    ).read_text(encoding="utf-8")
    touched_section = record.split("## Touched Files")[1].split("## Commands Run")[0]
    assert "real.py" in touched_section


def test_verify_blocked_when_ledger_contradicts_contract_artifact_paths(tmp_path):
    _create_backlog_file(tmp_path, "STORY-001")
    _write_contract(
        tmp_path,
        _contract(evidence_artifact=".sweetclaude/reports/large-story/OTHER/evidence/SC-001.json"),
    )
    assert init_workflow(project_dir=tmp_path, workflow_id="STORY-001")["ok"]
    _advance_to_implement(tmp_path)
    record_evidence(project_dir=tmp_path, tool="Write", file_path="app.py")
    result = enter_verify_phase(project_dir=tmp_path, workflow_id="STORY-001")
    assert result["ok"] is False
    assert result["code"] == "blocked_verify_entry_failed"


def test_status_and_finalize_resolve_terminal_workflow_without_explicit_id(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    record_evidence(project_dir=project, tool="Write", file_path="app.py")
    assert enter_verify_phase(project_dir=project, workflow_id="STORY-001")["ok"]
    assert enter_ship_phase(project_dir=project, workflow_id="STORY-001")["ok"]

    from large_story_controller import finalize_large_story

    status = render_large_story_status(project_dir=project)
    assert status["ok"] is True, status
    assert status["workflow_id"] == "STORY-001"
    finalize = finalize_large_story(project_dir=project)
    assert finalize["ok"] is True
    assert finalize["completion_claim_allowed"] is True


# --- Human-gated contract amendment + contract authoring commands -------------


def test_gate_denies_contract_amendment_when_workflow_active(tmp_path):
    project = _init_project(tmp_path)
    result = gate_tool_use(
        project_dir=project,
        tool="Write",
        file_path=".sweetclaude/contracts/success-criteria-contract.yaml",
    )
    assert result["allow"] is False
    assert result["decision"] == "deny"
    assert "amendment" in result["reason"].lower()


def test_gate_decision_field_present_for_allow_and_deny(tmp_path):
    project = _init_project(tmp_path)
    _advance_to_implement(project)
    allowed = gate_tool_use(project_dir=project, tool="Write", file_path="app.py")
    assert allowed["decision"] == "allow"
    denied = gate_tool_use(project_dir=project, tool="Write", file_path=".sweetclaude/state/phase.yaml")
    assert denied["decision"] == "deny"


def test_gate_denies_bash_referencing_contracts(tmp_path):
    project = _init_project(tmp_path)
    result = gate_tool_use(
        project_dir=project,
        tool="Bash",
        command="cat extra.yaml >> .sweetclaude/contracts/success-criteria-contract.yaml",
    )
    assert result["allow"] is False
    assert result["decision"] == "deny"


def _replace_placeholder_commands(project_dir):
    contract_path = project_dir / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    for criterion in contract["success_criteria"]:
        if criterion.get("measurement_type") == "command":
            criterion["measurement_command"] = "true"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")


def test_init_contract_skeleton_freezes_and_validates(tmp_path):
    from success_criteria_contracts import freeze_contract, init_contract

    _create_backlog_file(tmp_path, "WI-001")
    created = init_contract(project_dir=tmp_path, story_id="WI-001", criteria_count=3)
    assert created["ok"], created
    _replace_placeholder_commands(tmp_path)
    frozen = freeze_contract(project_dir=tmp_path)
    assert frozen["ok"], frozen
    assert frozen["contract_hash"].startswith("sha256:")
    result = validate_success_criteria_workflow(
        project_dir=tmp_path, workflow_id=None, stage="define-exit"
    )
    assert result["ok"] is True, result
    assert result["criterion_ids"] == ["SC-001", "SC-002", "SC-003"]


def test_init_contract_evidence_paths_match_controller_format(tmp_path):
    from success_criteria_contracts import init_contract

    _create_backlog_file(tmp_path, "WI-001")
    init_contract(project_dir=tmp_path, story_id="WI-001", criteria_count=2)
    contract = yaml.safe_load(
        (tmp_path / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml").read_text(encoding="utf-8")
    )
    for index, criterion in enumerate(contract["success_criteria"], start=1):
        assert criterion["evidence_artifact"] == (
            f".sweetclaude/reports/large-story/WI-001/evidence/SC-{index:03d}.json"
        )
        assert criterion["evidence_owner"] == "controller"
        assert criterion["allowed_phase_to_measure"] == "implementation"


def test_init_contract_refuses_overwrite_when_workflow_active(tmp_path):
    from success_criteria_contracts import init_contract

    project = _init_project(tmp_path)
    result = init_contract(project_dir=project, story_id="WI-001", criteria_count=1, force=True)
    assert result["ok"] is False
    assert "active" in result["error"].lower()


def test_init_contract_requires_force_to_overwrite_draft(tmp_path):
    from success_criteria_contracts import init_contract

    _create_backlog_file(tmp_path, "WI-001")
    assert init_contract(project_dir=tmp_path, story_id="WI-001")["ok"]
    again = init_contract(project_dir=tmp_path, story_id="WI-001")
    assert again["ok"] is False
    forced = init_contract(project_dir=tmp_path, story_id="WI-001", force=True)
    assert forced["ok"] is True


def test_freeze_contract_recomputes_hash_after_edit(tmp_path):
    from success_criteria_contracts import freeze_contract, init_contract

    _create_backlog_file(tmp_path, "WI-001")
    init_contract(project_dir=tmp_path, story_id="WI-001", criteria_count=1)
    _replace_placeholder_commands(tmp_path)
    first = freeze_contract(project_dir=tmp_path)
    contract_path = tmp_path / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["success_criteria"][0]["statement"] = "The index route returns HTTP status 200."
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    second = freeze_contract(project_dir=tmp_path)
    assert second["ok"]
    assert second["contract_hash"] != first["contract_hash"]
    result = validate_success_criteria_workflow(
        project_dir=tmp_path, workflow_id=None, stage="define-exit"
    )
    assert result["ok"] is True, result


# --- Post-terminal history protection (TASK-C8 micro-probe finding) -----------


def _ship_story(project, story_id="STORY-001"):
    _advance_to_implement(project, story_id)
    record_evidence(project_dir=project, tool="Write", file_path="app.py", workflow_id=story_id)
    assert enter_verify_phase(project_dir=project, workflow_id=story_id)["ok"]
    assert enter_ship_phase(project_dir=project, workflow_id=story_id)["ok"]


def test_gate_denies_history_writes_after_terminal_closeout(tmp_path):
    project = _init_project(tmp_path)
    _ship_story(project)
    for path in (
        ".sweetclaude/reports/success-criteria-ledger.json",
        ".sweetclaude/reports/large-story/STORY-001/ship/closeout.json",
        ".sweetclaude/state/workflows/archived/STORY-001.yaml",
    ):
        result = gate_tool_use(project_dir=project, tool="Write", file_path=path)
        assert result["allow"] is False, path
        assert result["decision"] == "deny"


def test_gate_allows_contract_reuse_after_terminal_closeout(tmp_path):
    """Contract at the default path is a reusable draft, not permanent evidence."""
    project = _init_project(tmp_path)
    _ship_story(project)
    result = gate_tool_use(
        project_dir=project,
        tool="Write",
        file_path=".sweetclaude/contracts/success-criteria-contract.yaml",
    )
    assert result["allow"] is True


def test_gate_allows_app_and_phase_writes_after_terminal_closeout(tmp_path):
    project = _init_project(tmp_path)
    _ship_story(project)
    assert gate_tool_use(project_dir=project, tool="Write", file_path="app.py")["allow"] is True
    assert gate_tool_use(
        project_dir=project, tool="Edit", file_path=".sweetclaude/state/phase.yaml"
    )["allow"] is True


def test_gate_denies_bash_history_tampering_after_terminal_closeout(tmp_path):
    project = _init_project(tmp_path)
    _ship_story(project)
    result = gate_tool_use(
        project_dir=project,
        tool="Bash",
        command="echo '{}' > .sweetclaude/reports/success-criteria-ledger.json",
    )
    assert result["allow"] is False


def test_gate_allows_new_story_contract_after_first_completes(tmp_path):
    """Regression: completing one story must not lock out authoring the next."""
    project = _init_project(tmp_path)
    _ship_story(project)
    new_contract = ".sweetclaude/contracts/success-criteria-contract.yaml"
    (project / new_contract).parent.mkdir(parents=True, exist_ok=True)
    (project / new_contract).write_text("story_id: STORY-002\n", encoding="utf-8")
    result = gate_tool_use(project_dir=project, tool="Write", file_path=new_contract)
    assert result["allow"] is True, f"New story contract should be writable: {result['reason']}"
    result = gate_tool_use(project_dir=project, tool="Edit", file_path=new_contract)
    assert result["allow"] is True, f"New story contract should be editable: {result['reason']}"


def test_gate_allows_new_story_reports_after_first_completes(tmp_path):
    """New story reports dir must be writable even with completed stories."""
    project = _init_project(tmp_path)
    _ship_story(project)
    new_report = ".sweetclaude/reports/large-story/STORY-002/design/notes.md"
    result = gate_tool_use(project_dir=project, tool="Write", file_path=new_report)
    assert result["allow"] is True, f"New story report should be writable: {result['reason']}"


def test_gate_allows_new_workflow_yaml_after_first_completes(tmp_path):
    """New workflow state file must be writable after completion."""
    project = _init_project(tmp_path)
    _ship_story(project)
    new_workflow = ".sweetclaude/state/workflows/STORY-002.yaml"
    result = gate_tool_use(project_dir=project, tool="Write", file_path=new_workflow)
    assert result["allow"] is True, f"New workflow YAML should be writable: {result['reason']}"


def test_gate_allows_readonly_bash_after_terminal_closeout(tmp_path):
    """Read-only commands mentioning protected paths must not be denied."""
    project = _init_project(tmp_path)
    _ship_story(project)
    for cmd in (
        "ls .sweetclaude/reports/large-story/STORY-001/",
        "cat .sweetclaude/state/workflows/STORY-001.yaml",
        "grep -r contract .sweetclaude/contracts/",
    ):
        result = gate_tool_use(project_dir=project, tool="Bash", command=cmd)
        assert result["allow"] is True, f"Read-only Bash should be allowed: {cmd}"


def test_gate_denies_bash_write_to_completed_story_files(tmp_path):
    """Write commands targeting completed-story files must be denied."""
    project = _init_project(tmp_path)
    _ship_story(project)
    result = gate_tool_use(
        project_dir=project,
        tool="Bash",
        command="echo '{}' > .sweetclaude/reports/success-criteria-ledger.json",
    )
    assert result["allow"] is False


# --- T2: hook-load self-check (enforcement probe) -----------------------------


def _control_path(project):
    return project / ".sweetclaude" / ".enforcement-control"


def _canary_path(project):
    return project / ".sweetclaude" / "state" / "workflows" / ".enforcement-canary"


def _simulate_probe(project, gate_active: bool):
    """Mimic the skill's probe writes: control always lands (unprotected);
    canary lands only if the gate is NOT active (gate would block it)."""
    from large_story_controller import arm_enforcement_probe, check_enforcement_probe

    arm = arm_enforcement_probe(project_dir=project, workflow_id="STORY-001")
    assert arm["ok"], arm
    _control_path(project).parent.mkdir(parents=True, exist_ok=True)
    _control_path(project).write_text("control\n", encoding="utf-8")
    if not gate_active:
        _canary_path(project).parent.mkdir(parents=True, exist_ok=True)
        _canary_path(project).write_text("leaked\n", encoding="utf-8")
    return check_enforcement_probe(project_dir=project, workflow_id="STORY-001")


def test_arm_clears_stale_canary_and_control(tmp_path):
    from large_story_controller import arm_enforcement_probe

    project = _init_project(tmp_path)
    _canary_path(project).parent.mkdir(parents=True, exist_ok=True)
    _canary_path(project).write_text("stale\n", encoding="utf-8")
    _control_path(project).parent.mkdir(parents=True, exist_ok=True)
    _control_path(project).write_text("stale\n", encoding="utf-8")
    result = arm_enforcement_probe(project_dir=project, workflow_id="STORY-001")
    assert result["ok"]
    assert not _canary_path(project).exists()
    assert not _control_path(project).exists()
    assert _workflow_state(project).get("enforcement_verified") is False


def test_check_verified_when_gate_blocks_canary(tmp_path):
    project = _init_project(tmp_path)
    result = _simulate_probe(project, gate_active=True)
    assert result["verified"] is True
    assert _workflow_state(project)["enforcement_verified"] is True


def test_check_unverified_when_canary_leaks(tmp_path):
    project = _init_project(tmp_path)
    result = _simulate_probe(project, gate_active=False)
    assert result["verified"] is False
    assert "not active" in result["reason"].lower() or "leak" in result["reason"].lower()
    assert _workflow_state(project)["enforcement_verified"] is False


def test_check_unverified_when_probe_not_performed(tmp_path):
    from large_story_controller import arm_enforcement_probe, check_enforcement_probe

    project = _init_project(tmp_path)
    arm_enforcement_probe(project_dir=project, workflow_id="STORY-001")
    # neither control nor canary written → probe never ran
    result = check_enforcement_probe(project_dir=project, workflow_id="STORY-001")
    assert result["verified"] is False
    assert _workflow_state(project)["enforcement_verified"] is False


def test_implement_blocked_until_enforcement_verified(tmp_path):
    project = _init_project(tmp_path)
    assert enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="d")["ok"]
    assert enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="p")["ok"]

    blocked = enter_implement_phase(project_dir=project, workflow_id="STORY-001", implementation_summary="i")
    assert blocked["ok"] is False
    assert blocked["code"] == "blocked_enforcement_unverified"

    _simulate_probe(project, gate_active=True)
    allowed = enter_implement_phase(project_dir=project, workflow_id="STORY-001", implementation_summary="i")
    assert allowed["ok"] is True


def test_implement_blocked_when_enforcement_probe_leaked(tmp_path):
    project = _init_project(tmp_path)
    assert enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="d")["ok"]
    assert enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="p")["ok"]
    _simulate_probe(project, gate_active=False)
    blocked = enter_implement_phase(project_dir=project, workflow_id="STORY-001", implementation_summary="i")
    assert blocked["ok"] is False
    assert blocked["code"] == "blocked_enforcement_unverified"


def test_gate_denies_canary_path(tmp_path):
    project = _init_project(tmp_path)
    result = gate_tool_use(
        project_dir=project,
        tool="Write",
        file_path=".sweetclaude/state/workflows/.enforcement-canary",
    )
    assert result["allow"] is False


def test_gate_allows_control_path(tmp_path):
    project = _init_project(tmp_path)
    result = gate_tool_use(
        project_dir=project, tool="Write", file_path=".sweetclaude/.enforcement-control"
    )
    assert result["allow"] is True


# --- Regression: cross-controller contamination (ISSUE-211) -------------------


def test_gate_ignores_small_story_workflow(tmp_path):
    """ISSUE-211 regression: a small-story workflow must not block the large-story gate."""
    from small_story_controller import init_workflow as small_init

    project = tmp_path
    _create_backlog_file(project, "SMALL-001")
    _write_contract(project, _contract("SMALL-001"))
    small_result = small_init(project_dir=project, workflow_id="SMALL-001")
    assert small_result["ok"], small_result

    result = gate_tool_use(project_dir=project, tool="Write", file_path="app.py")
    assert result["allow"] is True, (
        f"Large-story gate should not be blocked by a small-story workflow: {result['reason']}"
    )


# --- Regression: init without backlog story (ISSUE-215) -----------------------


def test_init_workflow_fails_without_backlog_file(tmp_path):
    """ISSUE-215 + ISSUE-223: init must not proceed storyless. ISSUE-223
    supersedes bare refusal with a resumable route-and-resume signal — but the
    phantom-workflow invariant still holds: no workflow state is written."""
    project = tmp_path
    _write_contract(project, _contract("PHANTOM-001"))
    result = init_workflow(project_dir=project, workflow_id="PHANTOM-001")
    assert result["ok"] is False
    assert result["code"] == "needs_story_creation"
    assert result.get("resume_after_story_creation") is True
    wf_path = project / ".sweetclaude" / "state" / "workflows" / "PHANTOM-001.yaml"
    assert not wf_path.exists(), "No workflow state should be written without a backlog story"
