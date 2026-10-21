"""Small-story terminal gate tests — per-story file protection.

Mirrors the large-story gate tests for the terminal history lockout bug:
completing one story must not prevent starting the next.
"""
import json
import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from small_story_controller import (
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
)
from success_criteria_contracts import compute_success_criteria_contract_hash


def _contract(story_id: str = "STORY-001") -> dict:
    criterion = {
        "id": "SC-001",
        "outcome_id": "OUTCOME-001",
        "statement": "The completion validator returns status success.",
        "binary_predicate": "completion validator returns status success",
        "measurement_type": "schema_check",
        "measurement_procedure": "Run completion validator.",
        "evidence_artifact": f".sweetclaude/reports/small-story/{story_id}/evidence/SC-001.json",
        "evidence_owner": "controller",
        "pass_condition": "validator status equals success",
        "fail_condition": "validator status does not equal success",
        "allowed_phase_to_measure": "implementation",
        "amendment_policy": "human_approved_only",
        "backlog_routing": "Backlog any new concern.",
    }
    contract = {
        "story_id": story_id,
        "story_title": "Small story gate test",
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


def _ship_story(project, story_id="STORY-001"):
    _advance_to_implement(project, story_id)
    record_evidence(project_dir=project, tool="Write", file_path="app.py", workflow_id=story_id)
    assert enter_verify_phase(project_dir=project, workflow_id=story_id)["ok"]
    assert enter_ship_phase(project_dir=project, workflow_id=story_id)["ok"]


# --- Active workflow: read-only Bash allowed ----------------------------------


def test_gate_allows_readonly_bash_during_active_workflow(tmp_path):
    """Read-only commands referencing protected paths must not be denied."""
    project = _init_project(tmp_path)
    for cmd in (
        "cat .sweetclaude/state/phase.yaml",
        "ls .sweetclaude/state/workflows/",
        "grep status .sweetclaude/state/workflows/STORY-001.yaml",
        "python3 scripts/small_story_controller.py render-status",
    ):
        result = gate_tool_use(project_dir=project, tool="Bash", command=cmd)
        assert result["allow"] is True, f"Read-only Bash denied during active workflow: {cmd}"


def test_gate_denies_write_bash_to_protected_during_active_workflow(tmp_path):
    """Write commands targeting protected paths must be denied."""
    project = _init_project(tmp_path)
    result = gate_tool_use(
        project_dir=project,
        tool="Bash",
        command="sed -i '' 's/phase: DEFINE/phase: SHIP/' .sweetclaude/state/phase.yaml",
    )
    assert result["allow"] is False


# --- Terminal gate: completed-story files are protected -----------------------


def test_gate_denies_history_writes_after_terminal_closeout(tmp_path):
    project = _init_project(tmp_path)
    _ship_story(project)
    for path in (
        ".sweetclaude/reports/success-criteria-ledger.json",
        ".sweetclaude/reports/small-story/STORY-001/ship/closeout.json",
        ".sweetclaude/state/workflows/archived/STORY-001.yaml",
    ):
        result = gate_tool_use(project_dir=project, tool="Write", file_path=path)
        assert result["allow"] is False, path
        assert result["decision"] == "deny"


def test_gate_allows_app_and_phase_writes_after_terminal_closeout(tmp_path):
    project = _init_project(tmp_path)
    _ship_story(project)
    assert gate_tool_use(project_dir=project, tool="Write", file_path="app.py")["allow"] is True
    assert gate_tool_use(
        project_dir=project, tool="Edit", file_path=".sweetclaude/state/phase.yaml"
    )["allow"] is True


# --- Terminal gate: new stories are allowed -----------------------------------


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
    new_report = ".sweetclaude/reports/small-story/STORY-002/design/notes.md"
    result = gate_tool_use(project_dir=project, tool="Write", file_path=new_report)
    assert result["allow"] is True, f"New story report should be writable: {result['reason']}"


def test_gate_allows_new_workflow_yaml_after_first_completes(tmp_path):
    """New workflow state file must be writable after completion."""
    project = _init_project(tmp_path)
    _ship_story(project)
    new_workflow = ".sweetclaude/state/workflows/STORY-002.yaml"
    result = gate_tool_use(project_dir=project, tool="Write", file_path=new_workflow)
    assert result["allow"] is True, f"New workflow YAML should be writable: {result['reason']}"


# --- Terminal gate: Bash commands ---------------------------------------------


def test_gate_allows_readonly_bash_after_terminal_closeout(tmp_path):
    """Read-only commands mentioning protected paths must not be denied."""
    project = _init_project(tmp_path)
    _ship_story(project)
    for cmd in (
        "ls .sweetclaude/reports/small-story/STORY-001/",
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


def test_gate_denies_bash_history_tampering_after_terminal_closeout(tmp_path):
    project = _init_project(tmp_path)
    _ship_story(project)
    result = gate_tool_use(
        project_dir=project,
        tool="Bash",
        command="echo '{}' > .sweetclaude/reports/success-criteria-ledger.json",
    )
    assert result["allow"] is False


# --- Regression: cross-controller contamination (ISSUE-211) -------------------


def test_gate_ignores_large_story_workflow(tmp_path):
    """ISSUE-211 regression: a large-story workflow must not block the small-story gate."""
    from large_story_controller import init_workflow as large_init

    project = tmp_path
    _create_backlog_file(project, "LARGE-001")
    _write_contract(project, _contract("LARGE-001"))
    large_result = large_init(project_dir=project, workflow_id="LARGE-001")
    assert large_result["ok"], large_result

    result = gate_tool_use(project_dir=project, tool="Write", file_path="app.py")
    assert result["allow"] is True, (
        f"Small-story gate should not be blocked by a large-story workflow: {result['reason']}"
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


def test_init_contract_small_story_evidence_paths_match_controller(tmp_path):
    """Small-story contracts must freeze small-story evidence paths.

    The skeleton previously hardcoded large-story/ in every evidence_artifact,
    while the small-story controller writes small-story/ at VERIFY. The frozen
    contract and the controller ledger then disagreed and the completion
    cross-check always failed. init_contract must honor workflow_type.
    """
    from success_criteria_contracts import init_contract

    _create_backlog_file(tmp_path, "STORY-001")
    init_contract(
        project_dir=tmp_path,
        story_id="STORY-001",
        criteria_count=2,
        workflow_type="small-story",
    )
    contract = yaml.safe_load(
        (tmp_path / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml").read_text(
            encoding="utf-8"
        )
    )
    for index, criterion in enumerate(contract["success_criteria"], start=1):
        assert criterion["evidence_artifact"] == (
            f".sweetclaude/reports/small-story/STORY-001/evidence/SC-{index:03d}.json"
        )


def _replace_placeholder_commands(project_dir):
    contract_path = project_dir / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    for criterion in contract["success_criteria"]:
        if criterion.get("measurement_type") == "command":
            criterion["measurement_command"] = "true"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")


def test_small_story_verify_passes_with_init_contract_generated_contract(tmp_path):
    """End-to-end: a contract scaffolded via init-contract must clear VERIFY.

    Reproduces the real SKILL path (init-contract, not a hand-built fixture).
    Before the workflow_type fix the frozen contract carried large-story/
    evidence paths while the controller wrote small-story/, so the completion
    cross-check raised at VERIFY. This drives the full flow to prove it passes.
    """
    from success_criteria_contracts import freeze_contract, init_contract

    project = tmp_path
    _create_backlog_file(project, "STORY-001")
    assert init_contract(
        project_dir=project,
        story_id="STORY-001",
        criteria_count=1,
        workflow_type="small-story",
    )["ok"]
    _replace_placeholder_commands(project)
    assert freeze_contract(project_dir=project)["ok"]
    assert init_workflow(project_dir=project, workflow_id="STORY-001")["ok"]
    _advance_to_implement(project, "STORY-001")
    record_evidence(project_dir=project, tool="Write", file_path="app.py", workflow_id="STORY-001")
    result = enter_verify_phase(project_dir=project, workflow_id="STORY-001")
    assert result["ok"], result


def test_init_contract_defaults_to_large_story(tmp_path):
    """Default workflow_type preserves the historical large-story path."""
    from success_criteria_contracts import init_contract

    _create_backlog_file(tmp_path, "STORY-001")
    init_contract(project_dir=tmp_path, story_id="STORY-001", criteria_count=1)
    contract = yaml.safe_load(
        (tmp_path / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert contract["success_criteria"][0]["evidence_artifact"] == (
        ".sweetclaude/reports/large-story/STORY-001/evidence/SC-001.json"
    )


# --- Small-story contract amendment path --------------------------------------
#
# Parity with the large-story approval-gated amendment flow. A frozen small-story
# contract must be amendable in-flight under a single-use, scoped, audited
# approval — without re-initializing the workflow (which is blocked while active).


def _write_amendable_small_story(tmp_path: Path, story_id: str = "STORY-001") -> Path:
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
                "state_owner": "small_story_controller",
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


def test_small_story_approve_amendment_records_scoped_single_use_token(tmp_path):
    from small_story_controller import approve_amendment

    project = _write_amendable_small_story(tmp_path)
    res = approve_amendment(
        project_dir=project,
        workflow_id="STORY-001",
        criterion_id="SC-001",
        reason="SC-001 encodes the wrong mechanism",
    )
    assert res["ok"] is True, res
    assert res["approval_ref"]
    receipt = json.loads((project / res["receipt_path"]).read_text())
    assert receipt["consumed"] is False
    assert receipt["workflow_id"] == "STORY-001"
    assert receipt["criterion_id"] == "SC-001"
    assert receipt["single_use"] is True


def test_small_story_approve_amendment_rejects_unknown_criterion(tmp_path):
    from small_story_controller import approve_amendment

    project = _write_amendable_small_story(tmp_path)
    res = approve_amendment(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-999", reason="x"
    )
    assert res["ok"] is False


def test_small_story_amend_contract_applies_refreezes_rebinds_and_audits(tmp_path):
    from small_story_controller import amend_contract, approve_amendment

    project = _write_amendable_small_story(tmp_path)
    cpath = project / ".sweetclaude/contracts/success-criteria-contract.yaml"
    wpath = project / ".sweetclaude/state/workflows/STORY-001.yaml"
    old_hash = yaml.safe_load(wpath.read_text())["success_criteria_contract_hash"]
    ref = approve_amendment(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001", reason="wrong mechanism"
    )["approval_ref"]

    res = amend_contract(
        project_dir=project,
        workflow_id="STORY-001",
        criterion_id="SC-001",
        approval_ref=ref,
        fields={"statement": "Amended statement."},
    )
    assert res["ok"] is True, res
    assert res["new_contract_hash"] and res["new_contract_hash"] != old_hash

    sc1 = next(
        c for c in yaml.safe_load(cpath.read_text())["success_criteria"] if c["id"] == "SC-001"
    )
    assert sc1["statement"] == "Amended statement."

    # workflow rebound to new hash, phase preserved (NOT reset to DEFINE)
    wstate = yaml.safe_load(wpath.read_text())
    assert wstate["success_criteria_contract_hash"] == res["new_contract_hash"]
    assert wstate["phase"] == "DESIGN"

    audit = json.loads((project / res["receipt_path"]).read_text())
    assert audit["old_contract_hash"] == old_hash
    assert audit["new_contract_hash"] == res["new_contract_hash"]
    assert audit["field_diff"]["statement"]["new"] == "Amended statement."


def test_small_story_amend_contract_token_is_single_use(tmp_path):
    from small_story_controller import amend_contract, approve_amendment

    project = _write_amendable_small_story(tmp_path)
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


def test_small_story_amend_contract_without_approval_is_blocked(tmp_path):
    from small_story_controller import amend_contract

    project = _write_amendable_small_story(tmp_path)
    res = amend_contract(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001",
        approval_ref="deadbeefdeadbeef", fields={"statement": "A"},
    )
    assert res["ok"] is False
    assert res["code"] == "blocked_amend_no_approval"


def test_small_story_amend_contract_rejects_non_amendable_field(tmp_path):
    from small_story_controller import amend_contract, approve_amendment

    project = _write_amendable_small_story(tmp_path)
    ref = approve_amendment(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001", reason="x"
    )["approval_ref"]
    res = amend_contract(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001",
        approval_ref=ref, fields={"id": "SC-XYZ"},
    )
    assert res["ok"] is False
    assert res["code"] == "blocked_amend_fields"


def test_small_story_amendment_cli_end_to_end(tmp_path):
    """The approve-amendment and amend-contract CLI subcommands are wired."""
    import subprocess

    project = _write_amendable_small_story(tmp_path)
    controller = str(SCRIPTS_DIR / "small_story_controller.py")

    approve = subprocess.run(
        [
            sys.executable, controller, "--project-dir", str(project),
            "approve-amendment", "--workflow-id", "STORY-001",
            "--criterion", "SC-001", "--reason", "CLI wiring check",
        ],
        capture_output=True, text=True,
    )
    assert approve.returncode == 0, approve.stderr
    ref = json.loads(approve.stdout)["approval_ref"]

    amend = subprocess.run(
        [
            sys.executable, controller, "--project-dir", str(project),
            "amend-contract", "--workflow-id", "STORY-001", "--criterion", "SC-001",
            "--approval-ref", ref, "--fields", json.dumps({"statement": "CLI amended."}),
        ],
        capture_output=True, text=True,
    )
    assert amend.returncode == 0, amend.stderr
    out = json.loads(amend.stdout)
    assert out["ok"] is True
    assert out["status"] == "amended"


def test_small_story_amend_inflight_then_complete_verify(tmp_path):
    """Rebind-in-flight replaces the blocked re-init path end to end.

    Scaffold via init_contract, init the workflow, amend a criterion in-flight
    (no re-init), then advance through implementation — which binds the rebound
    hash — and confirm VERIFY clears against the amended contract.
    """
    from small_story_controller import amend_contract, approve_amendment
    from success_criteria_contracts import freeze_contract, init_contract

    project = tmp_path
    _create_backlog_file(project, "STORY-001")
    assert init_contract(
        project_dir=project, story_id="STORY-001", criteria_count=1,
        workflow_type="small-story",
    )["ok"]
    _replace_placeholder_commands(project)
    assert freeze_contract(project_dir=project)["ok"]
    assert init_workflow(project_dir=project, workflow_id="STORY-001")["ok"]

    ref = approve_amendment(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001",
        reason="tighten the predicate before building",
    )["approval_ref"]
    amended = amend_contract(
        project_dir=project, workflow_id="STORY-001", criterion_id="SC-001",
        approval_ref=ref,
        fields={"statement": "The amended observable behavior holds."},
    )
    assert amended["ok"] is True, amended

    _advance_to_implement(project, "STORY-001")
    record_evidence(project_dir=project, tool="Write", file_path="app.py", workflow_id="STORY-001")
    result = enter_verify_phase(project_dir=project, workflow_id="STORY-001")
    assert result["ok"], result
    assert result["success_criteria_contract_hash"] == amended["new_contract_hash"]


# --- Regression: no-arg finalize / render-status resolve the workflow id ------
# (bug: finalize/render passed the raw workflow_id=None into completion
#  validation instead of the id already resolved from state, so the no-arg
#  forms documented in the skill failed on a correctly-completed story.)


def test_finalize_no_arg_forwards_resolved_workflow_id(monkeypatch):
    import small_story_controller as ssc

    monkeypatch.setattr(ssc, "_workflow_id_from_state", lambda project: "STORY-077")
    monkeypatch.setattr(ssc, "_check_state_phase_consistency", lambda project, wid: None)
    captured = {}

    def fake_completion(*, project_dir, workflow_id):
        captured["id"] = workflow_id
        return {"ok": True}

    monkeypatch.setattr(ssc, "_completion_result", fake_completion)

    result = ssc.finalize_small_story(project_dir=".")  # no workflow_id argument
    # The id resolved from state must be forwarded to completion validation,
    # not the raw None (the bug).
    assert captured["id"] == "STORY-077"
    assert result["ok"] is True
    assert result["workflow_id"] == "STORY-077"


def test_render_status_no_arg_forwards_resolved_workflow_id(monkeypatch):
    import small_story_controller as ssc

    monkeypatch.setattr(ssc, "_workflow_id_from_state", lambda project: "STORY-077")
    monkeypatch.setattr(ssc, "_check_state_phase_consistency", lambda project, wid: None)
    monkeypatch.setattr(ssc, "_status_details", lambda *a, **k: {})
    captured = {"completion": [], "gate": []}

    def fake_completion(*, project_dir, workflow_id):
        captured["completion"].append(workflow_id)
        return {"ok": True, "code": "ok", "message": ""}

    def fake_gate(*, project_dir, workflow_id):
        captured["gate"].append(workflow_id)
        return {"ok": True, "workflow_id": workflow_id}

    monkeypatch.setattr(ssc, "_completion_result", fake_completion)
    monkeypatch.setattr(ssc, "_completion_gate_result", fake_gate)

    result = ssc.render_small_story_status(project_dir=".")  # no workflow_id argument
    assert captured["completion"] == ["STORY-077"]
    assert captured["gate"] == ["STORY-077"]
    assert result["workflow_id"] == "STORY-077"
