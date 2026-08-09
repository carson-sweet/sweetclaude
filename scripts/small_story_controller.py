#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Controller guards for SweetClaude small-story execution."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required: pip install pyyaml")

from success_criteria_contracts import (
    DEFAULT_CONTRACT_PATH,
    DEFAULT_LEDGER_PATH,
    find_backlog_file,
    freeze_contract,
    record_workflow_closeout,
    validate_success_criteria_contract,
    validate_success_criteria_workflow,
)


BLOCKED_SLICE0_MESSAGE = (
    "Small-story downstream execution is blocked: the current product surface "
    "has SHIP/closeout after VERIFY. The success criteria contract may be "
    "defined, frozen, designed against, mapped into an implementation plan, "
    "implemented with evidence recorded, and verified into a controller-owned "
    "ledger, and closed through controller-owned SHIP/closeout, but terminal "
    "review and product-readiness validation are not available until later "
    "Track B tasks are implemented."
)
BLOCKED_DESIGN_ENTRY_MESSAGE = (
    "Small-story DESIGN is blocked: define-exit validation must pass before a "
    "design artifact can be accepted."
)
BLOCKED_PLAN_ENTRY_MESSAGE = (
    "Small-story PLAN is blocked: DESIGN must produce a durable design artifact "
    "before an implementation plan can be accepted."
)
BLOCKED_IMPLEMENTATION_ENTRY_MESSAGE = (
    "Small-story IMPLEMENT is blocked: PLAN must produce a durable implementation "
    "plan artifact before implementation evidence can be accepted."
)
BLOCKED_VERIFY_ENTRY_MESSAGE = (
    "Small-story VERIFY is blocked: IMPLEMENT must produce durable implementation "
    "evidence before verification can generate the success criteria ledger."
)
BLOCKED_MISSING_LEDGER_MESSAGE = (
    "Small-story completion is blocked: .sweetclaude/reports/success-criteria-ledger.json "
    "is missing. Do not claim completion. Generate controller-owned ledger "
    "evidence for every frozen success criterion, then rerun completion "
    "validation."
)
BLOCKED_COMPLETION_VALIDATION_MESSAGE = (
    "Small-story completion is blocked: success criteria completion validation "
    "failed. Do not claim completion. Fix the ledger or evidence against the "
    "frozen contract before requesting terminal completion."
)
BLOCKED_SHIP_ENTRY_MESSAGE = (
    "Small-story SHIP is blocked: VERIFY must produce a valid controller-owned "
    "success criteria ledger before closeout."
)
BLOCKED_CLOSEOUT_MISSING_MESSAGE = (
    "Small-story completion is blocked: SHIP/closeout has not written a "
    "durable controller-owned closeout artifact."
)
BLOCKED_TERMINAL_MUTATION_MESSAGE = (
    "Small-story terminal state mutation is blocked: terminal workflow state "
    "must be written by the small-story controller after validation, not by "
    "assistant narrative or direct YAML editing."
)
BLOCKED_FINAL_RESPONSE_MESSAGE = (
    "Small-story final response is blocked: the response would contradict "
    "controller state or completion validation. Render status through the "
    "small-story finalizer."
)

BLOCKED_STATE_INCONSISTENT_MESSAGE = (
    "Small-story state is inconsistent: phase.yaml and the workflow state file "
    "disagree on the active phase. Status rendering and phase transitions are "
    "blocked until the controller-owned state is repaired. Do not edit state "
    "files directly."
)
BLOCKED_LEDGER_PATH_DIVERGENT_MESSAGE = (
    "Small-story VERIFY is blocked: workflow state points to a non-canonical "
    f"success criteria ledger path. The canonical path is {DEFAULT_LEDGER_PATH}."
)
BLOCKED_EVIDENCE_EMPTY_MESSAGE = (
    "Small-story VERIFY is blocked: no hook-observed implementation evidence "
    "was recorded in evidence.jsonl. Implementation evidence is captured by "
    "the harness, not self-reported. If this story genuinely changed no "
    "project files, re-run verify with --allow-no-file-changes."
)
BLOCKED_GATE_MESSAGE = (
    "Small-story gate denied this tool use. Project files may only be "
    "modified during IMPLEMENT, after the controller has entered the phase. "
    "Controller-owned state and report files may never be modified directly."
)

CANONICAL_LEDGER_REL = Path(DEFAULT_LEDGER_PATH)
PROTECTED_WORKFLOWS_REL = Path(".sweetclaude") / "state" / "workflows"
PROTECTED_PHASE_REL = Path(".sweetclaude") / "state" / "phase.yaml"
PROTECTED_REPORTS_REL = Path(".sweetclaude") / "reports"
PROTECTED_BASH_WRITE_TOKENS = (
    ".sweetclaude/state/workflows",
    ".sweetclaude/state/phase.yaml",
    ".sweetclaude/reports",
    ".sweetclaude/contracts",
)
PROTECTED_BASH_COMMAND_TOKENS = (
    "record-evidence",
)
PROTECTED_CONTRACTS_REL = Path(".sweetclaude") / "contracts"
CONTRACT_AMENDMENT_MESSAGE = (
    "Frozen success criteria contract amendment is blocked. The contract was "
    "frozen at workflow init and is human-gated (amendment_policy: "
    "human_approved_only); the model may not edit it. To amend with recorded "
    "user approval: (1) get explicit user approval for the change, (2) record "
    "it: python3 scripts/small_story_controller.py approve-amendment "
    "--workflow-id <id> --criterion <SC-NNN> --reason <why>, then (3) apply it: "
    "python3 scripts/small_story_controller.py amend-contract --workflow-id <id> "
    "--criterion <SC-NNN> --approval-ref <ref> --fields <json>. This re-freezes "
    "the contract and rebinds the active workflow in place (no re-init). Without "
    "a valid single-use approval, amendment stays blocked. Otherwise route the "
    "concern to backlog or a new story."
)

VALID_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")


def _record_event(project: Path, event_type: str, **kwargs: str) -> None:
    import subprocess
    script = Path(__file__).resolve().parent / "record-event.sh"
    if not script.is_file():
        return
    args = ["bash", str(script), event_type]
    args.extend(f"{k}={v}" for k, v in kwargs.items())
    subprocess.run(args, cwd=str(project), capture_output=True, timeout=5)  # noqa: S603


ROUTE_SURFACES = {"/sweetclaude:go", "sweetclaude:find-skill", "sweetclaude:_route"}
POST_SHIP_STAGES = {"terminal_review"}
FORBIDDEN_SUCCESS_PHRASES = (
    "all success criteria pass",
    "all criteria pass",
    "story complete",
    "ship-ready",
)


def route_small_story(*, project_dir: str | Path = ".", route_surface: str) -> dict[str, Any]:
    """Return current bounded routing behavior for every small-story route surface."""
    if route_surface not in ROUTE_SURFACES:
        return _failure(
            "blocked_unknown_small_story_route",
            f"Unknown small-story route surface: {route_surface}",
        )
    return {
        "ok": True,
        "route_surface": route_surface,
        "small_story_behavior": "final_status_enabled_controller",
        "current_slice": "track_b_regression_covered",
        "design_enabled": True,
        "plan_enabled": True,
        "implementation_enabled": True,
        "verify_enabled": True,
        "ship_enabled": True,
        "final_status_enabled": True,
        "next_allowed_stage": "define",
        "blocked_stages": sorted(POST_SHIP_STAGES),
        "message": "Small-story route supports DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP/closeout, and final status rendering; automated end-to-end regression is covered. Fresh disposable execution remains blocked until TASK-008.",
    }


def transition_small_story(
    *,
    project_dir: str | Path = ".",
    workflow_id: str | None = None,
    target_stage: str,
) -> dict[str, Any]:
    """Validate a small-story state transition."""
    stage = target_stage.strip().lower()
    if stage == "design":
        return enter_design_phase(project_dir=project_dir, workflow_id=workflow_id)
    if stage == "plan":
        return enter_plan_phase(project_dir=project_dir, workflow_id=workflow_id)
    if stage in {"implement", "implementation"}:
        return enter_implement_phase(project_dir=project_dir, workflow_id=workflow_id)
    if stage == "verify":
        return enter_verify_phase(project_dir=project_dir, workflow_id=workflow_id)
    if stage == "ship":
        return enter_ship_phase(project_dir=project_dir, workflow_id=workflow_id)
    if stage in POST_SHIP_STAGES:
        return _failure("blocked_slice0_downstream_unavailable", BLOCKED_SLICE0_MESSAGE)
    if stage in {"complete", "done"}:
        completion = _completion_result(project_dir=project_dir, workflow_id=workflow_id)
        if not completion["ok"]:
            return completion
        return {
            "ok": True,
            "status": "complete",
            "workflow_id": workflow_id,
            "completion_claim_allowed": True,
            "message": "Small-story completion validation passed; terminal state may be written by controller.",
        }
    if stage in {"define", "define_exit_validated", "blocked_slice0_downstream_unavailable"}:
        return {
            "ok": True,
            "status": stage,
            "workflow_id": workflow_id,
            "message": "Small-story transition is allowed by Slice 0 controller contract.",
        }
    return _failure("blocked_unknown_small_story_transition", f"Unknown small-story target stage: {target_stage}")


def enter_design_phase(
    *,
    project_dir: str | Path = ".",
    workflow_id: str | None = None,
    design_summary: str = "",
) -> dict[str, Any]:
    """Enter DESIGN after define-exit validation and write a durable design artifact."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    if workflow_id is not None and not _valid_workflow_id(workflow_id):
        return _failure(
            "blocked_invalid_workflow_id",
            "Small-story phase entry is blocked: workflow_id must match "
            f"{VALID_ID_RE.pattern} (no path separators or traversal).",
        )
    define_result = validate_success_criteria_workflow(
        project_dir=project,
        workflow_id=workflow_id,
        stage="define-exit",
    )
    if not define_result.get("ok"):
        return {
            **_failure("blocked_design_entry_failed", BLOCKED_DESIGN_ENTRY_MESSAGE),
            "validator_result": define_result,
            "next_allowed_stage": "blocked",
        }

    resolved_workflow_id = workflow_id or define_result.get("workflow_id") or _workflow_id_from_state(project)
    if not _valid_workflow_id(resolved_workflow_id):
        return {
            **_failure("blocked_design_entry_failed", "Small-story DESIGN is blocked: workflow_id is required."),
            "next_allowed_stage": "blocked",
        }

    inconsistency = _check_state_phase_consistency(project, resolved_workflow_id)
    if inconsistency is not None:
        return {**inconsistency, "next_allowed_stage": "blocked"}

    contract_hash = str(define_result.get("contract_hash") or "")
    artifact_rel = Path(".sweetclaude") / "reports" / "small-story" / resolved_workflow_id / "design" / "design-artifact.md"
    artifact_path = project / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    summary = _strip_markdown_headings(design_summary.strip()) or "Design pending user/assistant elaboration."
    artifact_path.write_text(
        "\n".join(
            [
                "# Small Story Design Artifact",
                "",
                f"Workflow ID: {resolved_workflow_id}",
                f"Success Criteria Contract Hash: {contract_hash}",
                "",
                "## Design Summary",
                "",
                summary,
                "",
                "## Completion Criteria Policy",
                "",
                "This design artifact may not add, remove, or modify success criteria.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _set_workflow_phase(project, resolved_workflow_id, "DESIGN")
    _record_event(project, "phase_gate_check", phase="DEFINE", result="pass", workflow=resolved_workflow_id)
    _record_event(project, "phase_transition", **{"from": "DEFINE", "to": "DESIGN"}, workflow=resolved_workflow_id)
    return {
        "ok": True,
        "status": "design",
        "workflow_id": resolved_workflow_id,
        "success_criteria_contract_hash": contract_hash,
        "design_artifact_path": str(artifact_rel),
        "next_allowed_stage": "plan",
        "message": "Small-story DESIGN entered; durable design artifact written.",
    }


def enter_plan_phase(
    *,
    project_dir: str | Path = ".",
    workflow_id: str | None = None,
    plan_summary: str = "",
) -> dict[str, Any]:
    """Enter PLAN after DESIGN and write a durable criterion-mapped plan artifact."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    if workflow_id is not None and not _valid_workflow_id(workflow_id):
        return _failure(
            "blocked_invalid_workflow_id",
            "Small-story phase entry is blocked: workflow_id must match "
            f"{VALID_ID_RE.pattern} (no path separators or traversal).",
        )
    define_result = validate_success_criteria_workflow(
        project_dir=project,
        workflow_id=workflow_id,
        stage="define-exit",
    )
    if not define_result.get("ok"):
        return {
            **_failure("blocked_plan_entry_failed", BLOCKED_PLAN_ENTRY_MESSAGE),
            "validator_result": define_result,
            "next_allowed_stage": "blocked",
        }

    resolved_workflow_id = workflow_id or define_result.get("workflow_id") or _workflow_id_from_state(project)
    if not _valid_workflow_id(resolved_workflow_id):
        return {
            **_failure("blocked_plan_entry_failed", "Small-story PLAN is blocked: workflow_id is required."),
            "next_allowed_stage": "blocked",
        }

    inconsistency = _check_state_phase_consistency(project, resolved_workflow_id)
    if inconsistency is not None:
        return {**inconsistency, "next_allowed_stage": "blocked"}

    contract_hash = str(define_result.get("contract_hash") or "")
    design_rel = Path(".sweetclaude") / "reports" / "small-story" / resolved_workflow_id / "design" / "design-artifact.md"
    design_path = project / design_rel
    if not design_path.exists() or design_path.stat().st_size == 0:
        return {
            **_failure("blocked_plan_entry_failed", BLOCKED_PLAN_ENTRY_MESSAGE),
            "design_artifact_path": str(design_rel),
            "next_allowed_stage": "blocked",
        }
    design_text = design_path.read_text(encoding="utf-8")
    if contract_hash and contract_hash not in design_text:
        return {
            **_failure(
                "blocked_plan_entry_failed",
                "Small-story PLAN is blocked: design artifact is not bound to the frozen contract hash.",
            ),
            "design_artifact_path": str(design_rel),
            "next_allowed_stage": "blocked",
        }

    criterion_ids = _criterion_ids(project, resolved_workflow_id, define_result)
    artifact_rel = Path(".sweetclaude") / "reports" / "small-story" / resolved_workflow_id / "plan" / "implementation-plan.md"
    artifact_path = project / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    summary = _sanitize_no_success_criteria(plan_summary.strip() or "Implementation plan pending elaboration.")
    artifact_path.write_text(
        "\n".join(
            [
                "# Small Story Implementation Plan",
                "",
                f"Workflow ID: {resolved_workflow_id}",
                f"Success Criteria Contract Hash: {contract_hash}",
                f"Design Artifact: {design_rel}",
                "",
                "## Plan Summary",
                "",
                summary,
                "",
                "## Frozen Criterion Mapping",
                "",
                *[f"- {criterion_id}: planned work must preserve this frozen criterion." for criterion_id in criterion_ids],
                "",
                "## Completion Criteria Policy",
                "",
                "This plan artifact may not add, remove, or modify success criteria.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _set_workflow_phase(project, resolved_workflow_id, "PLAN")
    _record_event(project, "phase_gate_check", phase="DESIGN", result="pass", workflow=resolved_workflow_id)
    _record_event(project, "phase_transition", **{"from": "DESIGN", "to": "PLAN"}, workflow=resolved_workflow_id)
    return {
        "ok": True,
        "status": "plan",
        "workflow_id": resolved_workflow_id,
        "success_criteria_contract_hash": contract_hash,
        "design_artifact_path": str(design_rel),
        "plan_artifact_path": str(artifact_rel),
        "criterion_ids": criterion_ids,
        "next_allowed_stage": "implement",
        "message": "Small-story PLAN entered; durable criterion-mapped implementation plan written.",
    }


def enter_implement_phase(
    *,
    project_dir: str | Path = ".",
    workflow_id: str | None = None,
    implementation_summary: str = "",
    touched_files: list[str] | None = None,
    commands_run: list[str] | None = None,
    dependency_changes: list[str] | None = None,
    environment_changes: list[str] | None = None,
) -> dict[str, Any]:
    """Enter IMPLEMENT after PLAN and write durable implementation evidence."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    if workflow_id is not None and not _valid_workflow_id(workflow_id):
        return _failure(
            "blocked_invalid_workflow_id",
            "Small-story phase entry is blocked: workflow_id must match "
            f"{VALID_ID_RE.pattern} (no path separators or traversal).",
        )
    define_result = validate_success_criteria_workflow(
        project_dir=project,
        workflow_id=workflow_id,
        stage="define-exit",
    )
    if not define_result.get("ok"):
        return {
            **_failure("blocked_implementation_entry_failed", BLOCKED_IMPLEMENTATION_ENTRY_MESSAGE),
            "validator_result": define_result,
            "next_allowed_stage": "blocked",
        }

    resolved_workflow_id = workflow_id or define_result.get("workflow_id") or _workflow_id_from_state(project)
    if not _valid_workflow_id(resolved_workflow_id):
        return {
            **_failure("blocked_implementation_entry_failed", "Small-story IMPLEMENT is blocked: workflow_id is required."),
            "next_allowed_stage": "blocked",
        }

    inconsistency = _check_state_phase_consistency(project, resolved_workflow_id)
    if inconsistency is not None:
        return {**inconsistency, "next_allowed_stage": "blocked"}

    contract_hash = str(define_result.get("contract_hash") or "")
    plan_rel = Path(".sweetclaude") / "reports" / "small-story" / resolved_workflow_id / "plan" / "implementation-plan.md"
    plan_path = project / plan_rel
    if not plan_path.exists() or plan_path.stat().st_size == 0:
        return {
            **_failure("blocked_implementation_entry_failed", BLOCKED_IMPLEMENTATION_ENTRY_MESSAGE),
            "plan_artifact_path": str(plan_rel),
            "next_allowed_stage": "blocked",
        }
    plan_text = plan_path.read_text(encoding="utf-8")
    if contract_hash and contract_hash not in plan_text:
        return {
            **_failure(
                "blocked_implementation_entry_failed",
                "Small-story IMPLEMENT is blocked: plan artifact is not bound to the frozen contract hash.",
            ),
            "plan_artifact_path": str(plan_rel),
            "next_allowed_stage": "blocked",
        }

    # Enforcement self-check (T2): only after structural gates pass, refuse to
    # enter IMPLEMENT — where project writes are unlocked — unless the gate
    # hook was verified live this session via the enforcement probe.
    if _load_yaml_dict(_workflow_state_path(project, resolved_workflow_id)).get("enforcement_verified") is not True:
        return {
            **_failure(
                "blocked_enforcement_unverified",
                "Small-story IMPLEMENT is blocked: enforcement hooks have not "
                "been verified live this session. Run the enforcement probe "
                "(enforcement-probe --arm, perform the two probe writes, "
                "enforcement-probe --check) and confirm 'verified' before "
                "IMPLEMENT. If the probe reports the gate is not active, the "
                "workflow cannot guarantee its evidence gate — fix hook loading "
                "rather than proceeding unprotected.",
            ),
            "next_allowed_stage": "blocked",
        }

    files = _clean_list(touched_files)
    commands = _clean_list(commands_run)
    deps = _clean_list(dependency_changes)
    env = _clean_list(environment_changes)
    summary = _sanitize_no_completion_claims(
        implementation_summary.strip() or "Implementation evidence pending elaboration."
    )
    artifact_rel = Path(".sweetclaude") / "reports" / "small-story" / resolved_workflow_id / "implementation" / "implementation-record.md"
    artifact_path = project / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        "\n".join(
            [
                "# Small Story Implementation Record",
                "",
                f"Workflow ID: {resolved_workflow_id}",
                f"Success Criteria Contract Hash: {contract_hash}",
                f"Plan Artifact: {plan_rel}",
                "",
                "## Implementation Summary",
                "",
                summary,
                "",
                "## Touched Files",
                "",
                *_markdown_list(files),
                "",
                "## Commands Run",
                "",
                *_markdown_list(commands),
                "",
                "## Dependency Changes",
                "",
                *_markdown_list(deps),
                "",
                "## Environment Changes",
                "",
                *_markdown_list(env),
                "",
                "## Completion Criteria Policy",
                "",
                "This implementation record may not claim success criteria pass or workflow completion.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _set_workflow_phase(project, resolved_workflow_id, "IMPLEMENT")
    _record_event(project, "phase_gate_check", phase="PLAN", result="pass", workflow=resolved_workflow_id)
    _record_event(project, "phase_transition", **{"from": "PLAN", "to": "IMPLEMENT"}, workflow=resolved_workflow_id)
    return {
        "ok": True,
        "status": "implement",
        "workflow_id": resolved_workflow_id,
        "success_criteria_contract_hash": contract_hash,
        "plan_artifact_path": str(plan_rel),
        "implementation_artifact_path": str(artifact_rel),
        "touched_files": files,
        "commands_run": commands,
        "dependency_changes": deps,
        "environment_changes": env,
        "completion_claim_allowed": False,
        "next_allowed_stage": "verify",
        "message": "Small-story IMPLEMENT entered; durable implementation evidence written.",
    }


def enter_verify_phase(
    *,
    project_dir: str | Path = ".",
    workflow_id: str | None = None,
    criterion_results: dict[str, dict[str, Any]] | None = None,
    allow_no_file_changes: bool = False,
) -> dict[str, Any]:
    """Enter VERIFY after IMPLEMENT and write controller-owned ledger evidence."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    if workflow_id is not None and not _valid_workflow_id(workflow_id):
        return _failure(
            "blocked_invalid_workflow_id",
            "Small-story phase entry is blocked: workflow_id must match "
            f"{VALID_ID_RE.pattern} (no path separators or traversal).",
        )
    define_result = validate_success_criteria_workflow(
        project_dir=project,
        workflow_id=workflow_id,
        stage="define-exit",
    )
    if not define_result.get("ok"):
        return {
            **_failure("blocked_verify_entry_failed", BLOCKED_VERIFY_ENTRY_MESSAGE),
            "validator_result": define_result,
            "next_allowed_stage": "blocked",
        }

    resolved_workflow_id = workflow_id or define_result.get("workflow_id") or _workflow_id_from_state(project)
    if not _valid_workflow_id(resolved_workflow_id):
        return {
            **_failure("blocked_verify_entry_failed", "Small-story VERIFY is blocked: workflow_id is required."),
            "next_allowed_stage": "blocked",
        }

    inconsistency = _check_state_phase_consistency(project, resolved_workflow_id)
    if inconsistency is not None:
        return {**inconsistency, "next_allowed_stage": "blocked"}

    workflow_state = _load_yaml_dict(_workflow_state_path(project, resolved_workflow_id))
    ledger_setting = workflow_state.get("success_criteria_ledger_path")
    if (
        isinstance(ledger_setting, str)
        and ledger_setting.strip()
        and Path(ledger_setting) != CANONICAL_LEDGER_REL
    ):
        return {
            **_failure("blocked_ledger_path_divergent", BLOCKED_LEDGER_PATH_DIVERGENT_MESSAGE),
            "configured_ledger_path": ledger_setting,
            "canonical_ledger_path": str(CANONICAL_LEDGER_REL),
            "next_allowed_stage": "blocked",
        }

    contract_hash = str(define_result.get("contract_hash") or "")
    implementation_rel = (
        Path(".sweetclaude")
        / "reports"
        / "small-story"
        / resolved_workflow_id
        / "implementation"
        / "implementation-record.md"
    )
    implementation_path = project / implementation_rel
    if not implementation_path.exists() or implementation_path.stat().st_size == 0:
        return {
            **_failure("blocked_verify_entry_failed", BLOCKED_VERIFY_ENTRY_MESSAGE),
            "implementation_artifact_path": str(implementation_rel),
            "next_allowed_stage": "blocked",
        }
    implementation_text = implementation_path.read_text(encoding="utf-8")
    if contract_hash and contract_hash not in implementation_text:
        return {
            **_failure(
                "blocked_verify_entry_failed",
                "Small-story VERIFY is blocked: implementation artifact is not bound to the frozen contract hash.",
            ),
            "implementation_artifact_path": str(implementation_rel),
            "next_allowed_stage": "blocked",
        }

    evidence_entries = _evidence_log_entries(project, resolved_workflow_id)
    evidence_files = sorted(
        {str(entry["file_path"]) for entry in evidence_entries if entry.get("file_path")}
    )
    evidence_commands = [
        str(entry["command"]) for entry in evidence_entries if entry.get("command")
    ]
    if not evidence_files and not allow_no_file_changes:
        return {
            **_failure("blocked_implementation_evidence_empty", BLOCKED_EVIDENCE_EMPTY_MESSAGE),
            "evidence_log_path": str(_evidence_log_rel(resolved_workflow_id)),
            "next_allowed_stage": "blocked",
        }
    if evidence_entries:
        merged_files = sorted(
            set(_record_section_items(implementation_text, "Touched Files")) | set(evidence_files)
        )
        existing_commands = _record_section_items(implementation_text, "Commands Run")
        merged_commands = existing_commands + [
            command for command in evidence_commands if command not in existing_commands
        ]
        implementation_text = _replace_record_section(implementation_text, "Touched Files", merged_files)
        implementation_text = _replace_record_section(implementation_text, "Commands Run", merged_commands)
        implementation_path.write_text(implementation_text, encoding="utf-8")

    criterion_ids = _criterion_ids(project, resolved_workflow_id, define_result)
    if not criterion_ids:
        return {
            **_failure("blocked_verify_entry_failed", "Small-story VERIFY is blocked: no frozen criterion IDs found."),
            "next_allowed_stage": "blocked",
        }
    invalid_ids = [cid for cid in criterion_ids if not _valid_workflow_id(cid)]
    if invalid_ids:
        return {
            **_failure(
                "blocked_verify_entry_failed",
                f"Small-story VERIFY is blocked: criterion ids are invalid: {invalid_ids}.",
            ),
            "next_allowed_stage": "blocked",
        }

    supplied_results = criterion_results or {}
    criteria_entries = []
    evidence_dir = project / ".sweetclaude" / "reports" / "small-story" / resolved_workflow_id / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for criterion_id in criterion_ids:
        supplied = supplied_results.get(criterion_id, {})
        if supplied.get("evidence_present") is False:
            return {
                **_failure("blocked_verify_entry_failed", f"Small-story VERIFY is blocked: {criterion_id} lacks evidence."),
                "criterion_id": criterion_id,
                "next_allowed_stage": "blocked",
            }
        status = str(supplied.get("status") or "pass")
        measured_command = str(supplied.get("measured_command") or f"controller.verify {criterion_id}")
        evidence_rel = (
            Path(".sweetclaude")
            / "reports"
            / "small-story"
            / resolved_workflow_id
            / "evidence"
            / f"{criterion_id}.json"
        )
        evidence_path = project / evidence_rel
        evidence_payload = {
            "ok": status.lower() in {"pass", "passed", "ok", "success"},
            "criterion_id": criterion_id,
            "workflow_id": resolved_workflow_id,
            "success_criteria_contract_hash": contract_hash,
            "measured_command": measured_command,
            "observed_output": supplied.get("observed_output", "controller verification evidence recorded"),
        }
        evidence_path.write_text(json.dumps(evidence_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        criteria_entries.append(
            {
                "id": criterion_id,
                "status": status,
                "success_criteria_contract_hash": contract_hash,
                "evidence_artifact": str(evidence_rel),
                "evidence_owner": "controller",
                "evidence_path": str(evidence_rel),
                "measured_command": measured_command,
                "measured_at": str(supplied.get("measured_at") or "controller-generated"),
                "observed_output_path": str(evidence_rel),
                "evidence_fresh": True,
                "freshness_status": "fresh",
            }
        )

    ledger_rel = Path(".sweetclaude") / "reports" / "success-criteria-ledger.json"
    ledger_path = project / ledger_rel
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    all_passed = all(entry["status"].lower() in {"pass", "passed", "ok", "success"} for entry in criteria_entries)
    ledger = {
        "story_id": resolved_workflow_id,
        "workflow_id": resolved_workflow_id,
        "success_criteria_contract_hash": contract_hash,
        "generated_by": "small_story_controller",
        "generated_at": "controller-generated",
        "all_success_criteria_passed": all_passed,
        "criteria": criteria_entries,
    }
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    evidence_result = validate_ledger_evidence_paths(project, ledger_path)
    if not evidence_result.get("ok"):
        return {
            **_failure("blocked_verify_entry_failed", evidence_result["message"]),
            "ledger_path": str(ledger_rel),
            "next_allowed_stage": "blocked",
        }
    if not all_passed:
        return {
            **_failure("blocked_verify_entry_failed", "Small-story VERIFY is blocked: one or more criteria failed."),
            "ledger_path": str(ledger_rel),
            "next_allowed_stage": "blocked",
        }
    contract_cross_check = validate_success_criteria_workflow(
        project_dir=project,
        workflow_id=resolved_workflow_id,
        stage="completion",
    )
    if not contract_cross_check.get("ok"):
        return {
            **_failure(
                "blocked_verify_entry_failed",
                "Small-story VERIFY is blocked: the generated ledger does not "
                "satisfy the frozen contract (evidence_artifact, owner, or "
                "freshness mismatch). Fix the contract/controller alignment "
                "before VERIFY can pass.",
            ),
            "validator_result": contract_cross_check,
            "ledger_path": str(ledger_rel),
            "next_allowed_stage": "blocked",
        }
    _set_workflow_phase(project, resolved_workflow_id, "VERIFY")
    _record_event(project, "phase_gate_check", phase="IMPLEMENT", result="pass", workflow=resolved_workflow_id)
    _record_event(project, "phase_transition", **{"from": "IMPLEMENT", "to": "VERIFY"}, workflow=resolved_workflow_id)
    return {
        "ok": True,
        "status": "verify",
        "workflow_id": resolved_workflow_id,
        "success_criteria_contract_hash": contract_hash,
        "implementation_artifact_path": str(implementation_rel),
        "ledger_path": str(ledger_rel),
        "criterion_ids": criterion_ids,
        "criteria_verified": len(criteria_entries),
        "all_success_criteria_passed": True,
        "next_allowed_stage": "ship",
        "message": "Small-story VERIFY entered; controller-owned success criteria ledger written.",
    }


def enter_ship_phase(
    *,
    project_dir: str | Path = ".",
    workflow_id: str | None = None,
    terminal_actor: str = "small_story_controller",
) -> dict[str, Any]:
    """Enter SHIP after VERIFY and write controller-owned closeout evidence."""
    if terminal_actor != "small_story_controller":
        return _failure("blocked_assistant_terminal_state_mutation", BLOCKED_TERMINAL_MUTATION_MESSAGE)

    project = Path(project_dir).expanduser().resolve(strict=False)

    resolved_workflow_id = workflow_id or _workflow_id_from_state(project)
    if resolved_workflow_id and _valid_workflow_id(resolved_workflow_id):
        wf_state = _load_yaml_dict(_workflow_state_path(project, resolved_workflow_id))
        if wf_state.get("status") == "complete":
            wf_path = _workflow_state_path(project, resolved_workflow_id)
            if wf_path.exists():
                _archive_terminal_workflow(wf_path)
            _cleanup_stop_ack(project, resolved_workflow_id)
            record_workflow_closeout(project, resolved_workflow_id)
            return {
                "ok": True,
                "status": "ship",
                "workflow_id": resolved_workflow_id,
                "completion_claim_allowed": True,
                "next_allowed_stage": "complete",
                "message": "Small-story already complete; cleared stale active work item.",
            }

    completion_gate = _completion_gate_result(project_dir=project, workflow_id=workflow_id)
    if not completion_gate.get("ok"):
        result = {**completion_gate, "next_allowed_stage": "blocked"}
        return result

    resolved_workflow_id = completion_gate["workflow_id"]
    if not _valid_workflow_id(resolved_workflow_id):
        return {
            **_failure("blocked_ship_entry_failed", "Small-story SHIP is blocked: workflow_id is invalid."),
            "next_allowed_stage": "blocked",
        }
    inconsistency = _check_state_phase_consistency(project, resolved_workflow_id)
    if inconsistency is not None:
        return {**inconsistency, "next_allowed_stage": "blocked"}
    contract_hash = completion_gate["success_criteria_contract_hash"]
    ledger_rel = completion_gate["ledger_path"]
    closeout_rel = (
        Path(".sweetclaude")
        / "reports"
        / "small-story"
        / resolved_workflow_id
        / "ship"
        / "closeout.json"
    )
    closeout_path = project / closeout_rel
    closeout_path.parent.mkdir(parents=True, exist_ok=True)
    closeout = {
        "ok": True,
        "workflow_id": resolved_workflow_id,
        "success_criteria_contract_hash": contract_hash,
        "generated_by": "small_story_controller",
        "generated_at": "controller-generated",
        "ledger_path": ledger_rel,
        "completion_validation_ok": True,
        "terminal_state": "complete",
        "terminal_state_owner": "small_story_controller",
    }
    closeout_path.write_text(json.dumps(closeout, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_workflow_terminal_state(project, resolved_workflow_id, closeout_rel)
    record_workflow_closeout(project, resolved_workflow_id)
    _record_event(project, "phase_gate_check", phase="VERIFY", result="pass", workflow=resolved_workflow_id)
    _record_event(project, "phase_transition", **{"from": "VERIFY", "to": "SHIP"}, workflow=resolved_workflow_id)
    return {
        "ok": True,
        "status": "ship",
        "workflow_id": resolved_workflow_id,
        "success_criteria_contract_hash": contract_hash,
        "ledger_path": ledger_rel,
        "closeout_artifact_path": str(closeout_rel),
        "completion_claim_allowed": True,
        "next_allowed_stage": "complete",
        "message": "Small-story SHIP entered; controller-owned closeout artifact written.",
    }


def finalize_small_story(
    *,
    project_dir: str | Path = ".",
    workflow_id: str | None = None,
    attempted_response: str = "",
) -> dict[str, Any]:
    """Authorize or block final small-story response language."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    resolved_workflow_id = workflow_id or _workflow_id_from_state(project)
    if resolved_workflow_id:
        inconsistency = _check_state_phase_consistency(project, resolved_workflow_id)
        if inconsistency is not None:
            inconsistency["completion_claim_allowed"] = False
            inconsistency["forbidden_phrases_detected"] = _forbidden_phrases(attempted_response)
            inconsistency["allowed_summary"] = _blocked_summary("blocked_state_inconsistent")
            return inconsistency
    completion = _completion_result(project_dir=project_dir, workflow_id=resolved_workflow_id)
    forbidden = _forbidden_phrases(attempted_response)
    if not completion["ok"]:
        completion["completion_claim_allowed"] = False
        completion["forbidden_phrases_detected"] = forbidden
        completion["allowed_summary"] = _blocked_summary(completion["code"])
        return completion
    return {
        "ok": True,
        "status": "complete",
        "workflow_id": resolved_workflow_id,
        "completion_claim_allowed": True,
        "forbidden_phrases_detected": forbidden,
        "allowed_summary": "Small-story completion validation passed. Controller state permits completion.",
    }


def render_small_story_status(
    *,
    project_dir: str | Path = ".",
    workflow_id: str | None = None,
) -> dict[str, Any]:
    """Render controller-owned status for small-story responses."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    resolved_workflow_id = workflow_id or _workflow_id_from_state(project)
    if resolved_workflow_id:
        inconsistency = _check_state_phase_consistency(project, resolved_workflow_id)
        if inconsistency is not None:
            return {
                "ok": False,
                "status": "blocked_state_inconsistent",
                "workflow_id": resolved_workflow_id,
                "completion_claim_allowed": False,
                "allowed_summary": _blocked_summary("blocked_state_inconsistent"),
                "message": inconsistency["message"],
                "workflow_phase": inconsistency.get("workflow_phase"),
                "phase_yaml_phase": inconsistency.get("phase_yaml_phase"),
            }
    completion = _completion_result(project_dir=project_dir, workflow_id=resolved_workflow_id)
    gate = _completion_gate_result(project_dir=project_dir, workflow_id=resolved_workflow_id)
    details = _status_details(project, resolved_workflow_id, completion, gate)
    if completion["ok"]:
        return {
            "ok": True,
            "status": "complete",
            "workflow_id": resolved_workflow_id,
            "completion_claim_allowed": True,
            "allowed_summary": "Small-story completion validation passed. Controller state permits completion.",
            **details,
        }
    return {
        "ok": False,
        "status": completion["code"],
        "workflow_id": resolved_workflow_id,
        "completion_claim_allowed": False,
        "allowed_summary": _blocked_summary(completion["code"]),
        "message": completion["message"],
        **details,
    }


def _configured_trunk_branch(project: Path) -> str | None:
    sc_yaml = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    if not sc_yaml.exists():
        return None
    try:
        data = yaml.safe_load(sc_yaml.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    project_block = data.get("project")
    if not isinstance(project_block, dict):
        return None
    trunk = project_block.get("trunk_branch")
    if not isinstance(trunk, str) or not trunk.strip():
        return None
    return trunk


def _detect_main_branch(project: Path) -> str:
    configured = _configured_trunk_branch(project)
    if configured is not None:
        return configured
    try:
        r = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=str(project), capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            ref = r.stdout.strip()
            return ref.removeprefix("refs/remotes/origin/")
    except Exception:
        pass
    for candidate in ("main", "master"):
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--verify", candidate],
                cwd=str(project), capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                return candidate
        except Exception:
            pass
    return "main"


def _is_git_repo(project: Path) -> bool:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(project), capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        return False


def _has_commits(project: Path) -> bool:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project), capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


# Untracked files under these prefixes are init inputs (the frozen contract,
# the backlog story, and controller-owned state init is about to write), not
# unrelated in-progress work, so they do not trip the clean-tree gate.
_INIT_INPUT_UNTRACKED_PREFIXES = (".sweetclaude/", "docs/product/")


def _blocking_dirty_entries(porcelain: str) -> list[str]:
    """Porcelain lines that count as a dirty tree, ignoring init-input untracked files."""
    blocking: list[str] = []
    for line in porcelain.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path = line[3:].strip().strip('"')
        if status == "??" and path.startswith(_INIT_INPUT_UNTRACKED_PREFIXES):
            continue
        blocking.append(line)
    return blocking


def _slugify(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (text or "").lower())).strip("-")


def _story_branch_name(project: Path, workflow_id: str) -> str:
    slug = ""
    backlog = find_backlog_file(project, workflow_id, exclude_done=True)
    if backlog is not None:
        stem = backlog.stem
        remainder = stem[len(workflow_id):] if stem.lower().startswith(workflow_id.lower()) else stem
        slug = _slugify(remainder)
    wf_lower = workflow_id.lower()
    return f"{wf_lower}/{slug}" if slug else f"story/{wf_lower}"


def _create_story_branch(project: Path, workflow_id: str) -> dict[str, Any]:
    """Create and switch to the story's dedicated branch off current HEAD.

    Off-git projects are a silent no-op. If git operations fail we do not crash
    init; we return a warning and leave the branch unchanged.
    """
    if not _is_git_repo(project):
        return {}
    name = _story_branch_name(project, workflow_id)
    try:
        r = subprocess.run(
            ["git", "checkout", "-b", name],
            cwd=str(project), capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            r2 = subprocess.run(
                ["git", "checkout", name],
                cwd=str(project), capture_output=True, text=True, timeout=10,
            )
            if r2.returncode != 0:
                return {
                    "branch": None,
                    "branch_warning": (
                        f"could not create or switch to story branch '{name}': "
                        f"{(r.stderr or r2.stderr).strip()}"
                    ),
                }
        return {"branch": name}
    except Exception as exc:  # noqa: BLE001 - init must not crash on git failure
        return {"branch": None, "branch_warning": f"branch creation failed: {exc}"}


def _check_init_preconditions(
    project: Path, *, workflow_id: str | None = None
) -> dict[str, Any] | None:
    if not _is_git_repo(project):
        return None

    if not _has_commits(project):
        return None

    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(project), capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return None
        current_branch = r.stdout.strip()
    except Exception:
        return None

    main_branch = _detect_main_branch(project)
    # Re-init of an existing workflow legitimately runs from that workflow's own
    # dedicated story branch (ISSUE-222 switches off trunk at init), so tolerate it.
    story_branch = _story_branch_name(project, workflow_id) if workflow_id else None
    if not current_branch or (current_branch != main_branch and current_branch != story_branch):
        display = current_branch if current_branch and current_branch != "HEAD" else "(detached)"
        return _failure(
            "blocked_not_on_main",
            f"Small-story init is blocked: current branch is '{display}', "
            f"not '{main_branch}'. init must run on the trunk branch. Correct sequence: "
            f"commit the frozen contract on {main_branch}, run init on {main_branch}, then "
            f"create your implementation branch (git checkout -b feat/<id>-...) to carry the "
            f"workflow state forward.",
        )

    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=str(project), capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and _blocking_dirty_entries(r.stdout):
            return _failure(
                "blocked_dirty_tree",
                "Small-story init is blocked: working tree has uncommitted changes. "
                "Commit the frozen contract (or stash/discard other changes) on the trunk "
                "branch before running init; create your implementation branch after init.",
            )
        if r.returncode != 0:
            return _failure(
                "blocked_dirty_tree",
                "Small-story init is blocked: git status failed. "
                "Resolve any git index issues before starting a new story.",
            )
    except Exception:
        return _failure(
            "blocked_dirty_tree",
            "Small-story init is blocked: git status failed. "
            "Resolve any git index issues before starting a new story.",
        )

    workflows_dir = project / ".sweetclaude" / "state" / "workflows"
    if workflows_dir.exists():
        for candidate in sorted(workflows_dir.glob("*.yaml")):
            state = _load_yaml_dict(candidate)
            wf_id = state.get("workflow_id") if isinstance(state.get("workflow_id"), str) else candidate.stem
            if not _valid_workflow_id(wf_id):
                continue
            owner = state.get("state_owner", "")
            if (
                state
                and state.get("requires_success_criteria_contract")
                and state.get("status") != "complete"
            ):
                return _failure(
                    "blocked_inflight_workflow",
                    f"Small-story init is blocked: active workflow {wf_id} ({owner}) "
                    "is still in progress. Complete, ship, or close it out before "
                    "starting another story.",
                )

    return None


def init_workflow(
    *,
    project_dir: str | Path = ".",
    workflow_id: str,
    contract_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create controller-owned small-story workflow state from a frozen contract."""
    if not _valid_workflow_id(workflow_id):
        return _failure(
            "blocked_init_failed",
            "Small-story init is blocked: workflow_id must match "
            f"{VALID_ID_RE.pattern} (no path separators or traversal).",
        )
    project = Path(project_dir).expanduser().resolve(strict=False)
    precondition_failure = _check_init_preconditions(project, workflow_id=workflow_id)
    if precondition_failure is not None:
        return precondition_failure
    if find_backlog_file(project, workflow_id, exclude_done=True) is None:
        return {
            **_failure(
                "needs_story_creation",
                f"Small-story init is paused: no backlog file exists for {workflow_id} yet. "
                "This is not a dead-end — init will RESUME once the story is created. "
                "Route the user through story creation now by one of: "
                "(1) interview — walk through a structured intake, "
                "(2) point to a file — seed from an existing spec or scratch note, "
                "(3) search for WIP — scan scratch/, .sweetclaude/work/, and feature branches. "
                f"Once the story exists, re-run init with the same workflow_id ({workflow_id}) to resume.",
            ),
            "resume_after_story_creation": True,
            "workflow_id": workflow_id,
        }
    existing = [
        (existing_id, state)
        for existing_id, state in _active_small_story_workflows(project)
        if existing_id != workflow_id
    ]
    if existing:
        return _failure(
            "blocked_init_failed",
            "Small-story init is blocked: an active small-story workflow already "
            f"exists ({existing[0][0]}). Complete or repair it before starting "
            "another.",
        )
    contract_rel = Path(contract_path) if contract_path else Path(DEFAULT_CONTRACT_PATH)
    resolved_contract = contract_rel if contract_rel.is_absolute() else project / contract_rel
    if not resolved_contract.exists():
        return _failure(
            "blocked_init_failed",
            f"Small-story init is blocked: contract not found at {contract_rel}.",
        )
    try:
        contract_result = validate_success_criteria_contract(resolved_contract)
    except Exception as exc:
        return _failure("blocked_init_failed", f"Small-story init is blocked: {exc}")

    contract_hash = str(contract_result.get("contract_hash") or "")
    criterion_ids = list(contract_result.get("criterion_ids") or [])
    workflow_path = _workflow_state_path(project, workflow_id)
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(
        yaml.safe_dump(
            {
                "workflow_id": workflow_id,
                "phase": "DEFINE",
                "state_owner": "small_story_controller",
                "requires_success_criteria_contract": True,
                "success_criteria_contract_path": str(
                    resolved_contract.relative_to(project)
                    if resolved_contract.is_relative_to(project)
                    else resolved_contract
                ),
                "success_criteria_contract_hash": contract_hash,
                "criterion_ids": criterion_ids,
                "success_criteria_ledger_path": str(CANONICAL_LEDGER_REL),
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    _sync_phase_yaml(project, workflow_id, "DEFINE")
    _sync_sweetclaude_yaml_active(project, workflow_id, "DEFINE")
    branch_info = _create_story_branch(project, workflow_id)
    return {
        "ok": True,
        "status": "define",
        "workflow_id": workflow_id,
        "success_criteria_contract_hash": contract_hash,
        "criterion_ids": criterion_ids,
        "success_criteria_ledger_path": str(CANONICAL_LEDGER_REL),
        "next_allowed_stage": "design",
        "message": "Small-story workflow state initialized by controller.",
        **branch_info,
    }


def gate_tool_use(
    *,
    project_dir: str | Path = ".",
    tool: str,
    file_path: str | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    """Deterministic allow/deny decision for a tool use under small-story discipline."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    unreadable = _unreadable_workflow_files(project)
    if unreadable:
        # Fail closed. A state file that will not parse means the phase cannot
        # be determined, and allowing on that basis lets one corrupt file
        # switch the whole discipline off silently (ISSUE-288).
        return {
            "allow": False,
            "ok": False,
            "decision": "deny",
            "reason": (
                "Small-story gate failed closed: workflow state is unreadable "
                f"({', '.join(unreadable)}). This is a damaged state file, not "
                "a phase violation — repair or remove it, then retry. Run "
                "'python3 scripts/small_story_controller.py render-status' to "
                "inspect."
            ),
            "workflow_id": None,
            "phase": None,
        }
    actives = _active_small_story_workflows(project)
    if not actives:
        if _any_small_story_workflow_exists(project):
            # Completed stories: their evidence is permanent history. Project
            # files and shared session state are free again, but
            # controller-owned reports/state stay immutable and contract
            # changes remain human-gated (micro-probe finding, 2026-06-06:
            # an agent retroactively invalidated a closed story's record).
            return _gate_terminal_history(project, tool, file_path, command)
        return {
            "allow": True,
            "ok": True,
            "decision": "allow",
            "reason": "No small-story workflow state in this project; gate does not apply.",
            "workflow_id": None,
            "phase": None,
        }
    if len(actives) > 1:
        return {
            "allow": False,
            "ok": False,
            "decision": "deny",
            "reason": (
                "Small-story workflow state is ambiguous: multiple active "
                f"workflows found ({', '.join(item[0] for item in actives)}). "
                "The gate fails closed until the ambiguity is repaired."
            ),
            "workflow_id": None,
            "phase": None,
        }
    workflow_id, state = actives[0]
    phase = str(state.get("phase") or "DEFINE")

    def _decision(allow: bool, reason: str, decision: str | None = None) -> dict[str, Any]:
        return {
            "allow": allow,
            "ok": allow,
            "decision": decision or ("allow" if allow else "deny"),
            "reason": reason,
            "workflow_id": workflow_id,
            "phase": phase,
        }

    if tool in {"Write", "Edit", "NotebookEdit"}:
        if not file_path:
            return _decision(
                False,
                f"{BLOCKED_GATE_MESSAGE} {tool} call without a file path is anomalous.",
            )
        rel = _project_relative(project, file_path)
        if rel is None:
            return _decision(
                False,
                f"{BLOCKED_GATE_MESSAGE} Target is outside the project directory.",
            )
        if (
            rel == PROTECTED_PHASE_REL
            or PROTECTED_WORKFLOWS_REL in rel.parents
            or rel == PROTECTED_WORKFLOWS_REL
            or PROTECTED_REPORTS_REL in rel.parents
            or rel == PROTECTED_REPORTS_REL
        ):
            if rel == PROTECTED_PHASE_REL:
                return _decision(
                    False,
                    f"{BLOCKED_GATE_MESSAGE} {rel} is controller-owned state. "
                    "To complete the workflow and clear the active work item, "
                    "run `python3 scripts/small_story_controller.py ship "
                    f"--workflow-id {workflow_id}` via Bash instead of editing "
                    "phase.yaml directly.",
                )
            return _decision(
                False,
                f"{BLOCKED_GATE_MESSAGE} {rel} is controller-owned state or evidence.",
            )
        if PROTECTED_CONTRACTS_REL in rel.parents or rel == PROTECTED_CONTRACTS_REL:
            return _decision(False, CONTRACT_AMENDMENT_MESSAGE, decision="deny")
        if rel.parts and rel.parts[0] == ".sweetclaude":
            return _decision(True, f"{rel} is non-protected SweetClaude project state.")
        if phase == "IMPLEMENT" and _implementation_record_present(project, workflow_id):
            return _decision(True, "IMPLEMENT phase entered via controller; project writes allowed.")
        return _decision(
            False,
            f"{BLOCKED_GATE_MESSAGE} Current phase is {phase}.",
        )

    if tool == "Bash" and command:
        lowered = command.lower()
        for token in PROTECTED_BASH_COMMAND_TOKENS:
            if token in lowered:
                return _decision(
                    False,
                    f"{BLOCKED_GATE_MESSAGE} Command references controller-owned command {token}.",
                )
        if not _BASH_WRITE_TOKENS.search(command):
            return _decision(True, "Read-only command; protected paths are readable.")
        for token in PROTECTED_BASH_WRITE_TOKENS:
            if token in lowered:
                if "phase.yaml" in token:
                    return _decision(
                        False,
                        f"{BLOCKED_GATE_MESSAGE} Command references controller-owned "
                        "phase.yaml. To complete the workflow and clear the active "
                        "work item, run `python3 scripts/small_story_controller.py "
                        f"ship --workflow-id {workflow_id}` instead.",
                    )
                return _decision(
                    False,
                    f"{BLOCKED_GATE_MESSAGE} Command references controller-owned path or command {token}.",
                )
        return _decision(True, "Command does not reference controller-owned paths.")

    return _decision(True, "Tool is not gated.")


def record_evidence(
    *,
    project_dir: str | Path = ".",
    tool: str,
    file_path: str | None = None,
    command: str | None = None,
    workflow_id: str | None = None,
) -> dict[str, Any]:
    """Append a harness-observed implementation evidence entry (JSONL)."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    resolved_workflow_id = workflow_id
    state: dict[str, Any] = {}
    if resolved_workflow_id is None:
        active = _active_small_story_workflow(project)
        if active is None:
            return _failure(
                "blocked_no_active_workflow",
                "Evidence recording is blocked: no active small-story workflow.",
            )
        resolved_workflow_id, state = active
    elif not _valid_workflow_id(resolved_workflow_id):
        return _failure(
            "blocked_no_active_workflow",
            "Evidence recording is blocked: workflow_id is invalid.",
        )
    else:
        wf_path = _workflow_state_path(project, resolved_workflow_id)
        if not wf_path.exists():
            return _failure(
                "blocked_no_active_workflow",
                f"Evidence recording is blocked: no workflow state file for {resolved_workflow_id}.",
            )
        state = _load_yaml_dict(wf_path)

    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "phase": str(state.get("phase") or "UNKNOWN"),
        "workflow_id": resolved_workflow_id,
    }
    if file_path:
        rel = _project_relative(project, file_path)
        entry["file_path"] = str(rel) if rel is not None else file_path
    if command:
        entry["command"] = command

    log_rel = _evidence_log_rel(resolved_workflow_id)
    log_path = project / log_rel
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    total = sum(1 for _ in log_path.open(encoding="utf-8"))
    return {
        "ok": True,
        "workflow_id": resolved_workflow_id,
        "evidence_log_path": str(log_rel),
        "entries": total,
    }


def _evidence_log_rel(workflow_id: str) -> Path:
    return (
        Path(".sweetclaude")
        / "reports"
        / "small-story"
        / workflow_id
        / "implementation"
        / "evidence.jsonl"
    )


def _evidence_log_entries(project: Path, workflow_id: str) -> list[dict[str, Any]]:
    log_path = project / _evidence_log_rel(workflow_id)
    if not log_path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            entries.append(data)
    return entries


def _implementation_record_present(project: Path, workflow_id: str) -> bool:
    record = (
        project
        / ".sweetclaude"
        / "reports"
        / "small-story"
        / workflow_id
        / "implementation"
        / "implementation-record.md"
    )
    return record.exists() and record.stat().st_size > 0


def _project_relative(project: Path, file_path: str) -> Path | None:
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = project / candidate
    resolved = candidate.resolve(strict=False)
    try:
        return resolved.relative_to(project)
    except ValueError:
        return None


ENFORCEMENT_CONTROL_REL = Path(".sweetclaude") / ".enforcement-control"
ENFORCEMENT_CANARY_REL = Path(".sweetclaude") / "state" / "workflows" / ".enforcement-canary"


def arm_enforcement_probe(
    *,
    project_dir: str | Path = ".",
    workflow_id: str | None = None,
) -> dict[str, Any]:
    """Clear stale probe files and mark enforcement unverified.

    The skill then writes the control path (gate allows) and attempts the
    canary path (gate denies if loaded). check_enforcement_probe reads the
    filesystem result. The model cannot fake verification: 'verified' requires
    the protected canary to be ABSENT, which only an active gate produces.
    """
    project = Path(project_dir).expanduser().resolve(strict=False)
    resolved = workflow_id or _workflow_id_from_state(project)
    if not _valid_workflow_id(resolved):
        return _failure("blocked_enforcement_probe", "Enforcement probe is blocked: workflow_id is required.")
    wf_path = _workflow_state_path(project, resolved)
    if not wf_path.exists():
        return _failure(
            "blocked_enforcement_probe",
            f"Enforcement probe is blocked: no workflow state file for {resolved}.",
        )
    for rel in (ENFORCEMENT_CONTROL_REL, ENFORCEMENT_CANARY_REL):
        target = project / rel
        if target.exists():
            target.unlink()
    state = _load_yaml_dict(wf_path)
    state["enforcement_verified"] = False
    _write_workflow_dict(project, resolved, state)
    return {
        "ok": True,
        "workflow_id": resolved,
        "control_path": str(ENFORCEMENT_CONTROL_REL),
        "canary_path": str(ENFORCEMENT_CANARY_REL),
        "instructions": (
            "Write a short file at control_path (the gate allows it), then "
            "attempt a Write at canary_path (the gate must deny it). Then run "
            "enforcement-probe --check."
        ),
    }


def check_enforcement_probe(
    *,
    project_dir: str | Path = ".",
    workflow_id: str | None = None,
) -> dict[str, Any]:
    """Decide whether the small-story gate is live, from filesystem evidence."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    resolved = workflow_id or _workflow_id_from_state(project)
    if not _valid_workflow_id(resolved):
        return _failure("blocked_enforcement_probe", "Enforcement probe is blocked: workflow_id is required.")
    wf_path = _workflow_state_path(project, resolved)
    if not wf_path.exists():
        return _failure(
            "blocked_enforcement_probe",
            f"Enforcement probe is blocked: no workflow state file for {resolved}.",
        )
    control_present = (project / ENFORCEMENT_CONTROL_REL).exists()
    canary_present = (project / ENFORCEMENT_CANARY_REL).exists()
    if not control_present:
        verified, reason = False, (
            "Enforcement unverified: the probe control write was not observed, "
            "so the probe did not run. Re-arm and perform both probe writes."
        )
    elif canary_present:
        verified, reason = False, (
            "Enforcement NOT active: the protected canary write was not blocked. "
            "The small-story gate hook is not loaded in this session. Fix hook "
            "loading before trusting the workflow (see small-story dev-testing doc)."
        )
    else:
        verified, reason = True, "Enforcement active: the gate blocked the protected canary write."
    state = _load_yaml_dict(_workflow_state_path(project, resolved))
    state["enforcement_verified"] = verified
    state["enforcement_checked_at"] = datetime.now(timezone.utc).isoformat()
    _write_workflow_dict(project, resolved, state)
    # Leave control/canary in place; arm cleans them on the next probe.
    return {"ok": verified, "verified": verified, "reason": reason, "workflow_id": resolved}


def _write_workflow_dict(project: Path, workflow_id: str, state: dict[str, Any]) -> None:
    path = _workflow_state_path(project, workflow_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")


def _workflow_state_path(project: Path, workflow_id: str) -> Path:
    active = project / ".sweetclaude" / "state" / "workflows" / f"{workflow_id}.yaml"
    if active.exists():
        return active
    archived = project / ".sweetclaude" / "state" / "workflows" / "archived" / f"{workflow_id}.yaml"
    if archived.exists():
        return archived
    return active


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _valid_workflow_id(value: Any) -> bool:
    return isinstance(value, str) and bool(VALID_ID_RE.fullmatch(value))


def _is_active_workflow_state(state: dict[str, Any]) -> bool:
    return bool(
        state
        and state.get("state_owner") == "small_story_controller"
        and state.get("requires_success_criteria_contract")
        and state.get("status") != "complete"
    )


AMENDMENT_APPROVAL_RECEIPT_TYPE = "contract-amendment-approval"
AMENDMENT_RECEIPT_TYPE = "contract-amendment"
# Fields of a success criterion that an approved amendment may change. The
# criterion id is intentionally excluded: amendments may edit existing criteria,
# never add, remove, or re-key them.
AMENDABLE_CRITERION_FIELDS = {
    "statement",
    "binary_predicate",
    "measurement_type",
    "measurement_procedure",
    "evidence_artifact",
    "evidence_owner",
    "pass_condition",
    "fail_condition",
    "allowed_phase_to_measure",
    "backlog_routing",
}


def _evidence_dir(project: Path) -> Path:
    return project / ".sweetclaude" / "state" / "evidence"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _approval_receipt_path(project: Path, approval_ref: str) -> Path:
    return _evidence_dir(project) / f"amendment-approval-{approval_ref}.json"


def _rel(project: Path, path: Path) -> str:
    return str(path.relative_to(project) if path.is_relative_to(project) else path)


def approve_amendment(
    *,
    project_dir: str | Path = ".",
    workflow_id: str,
    criterion_id: str,
    reason: str,
    approved_by: str = "user",
) -> dict[str, Any]:
    """Record a single-use, scoped approval token for a frozen-contract amendment.

    LOCAL/ADVISORY: this records, scopes, and audits an approval; it is not an
    external enforcement boundary (a single-actor machine can run it directly).
    """
    project = Path(project_dir).expanduser().resolve(strict=False)
    if not _valid_workflow_id(workflow_id):
        return _failure("blocked_amend_approval", "Invalid workflow_id.")
    state = _load_yaml_dict(_workflow_state_path(project, workflow_id))
    if not _is_active_workflow_state(state):
        return _failure(
            "blocked_amend_approval",
            f"No active small-story workflow {workflow_id} to approve an amendment for.",
        )
    criterion_ids = state.get("criterion_ids") or []
    if criterion_id not in criterion_ids:
        return _failure(
            "blocked_amend_approval",
            f"Criterion {criterion_id} is not part of workflow {workflow_id} "
            f"(known: {', '.join(map(str, criterion_ids)) or 'none'}).",
        )
    if not (reason and reason.strip()):
        return _failure("blocked_amend_approval", "An amendment approval requires a reason.")
    approval_ref = uuid.uuid4().hex
    receipt = {
        "schema_version": 2,
        "receipt_type": AMENDMENT_APPROVAL_RECEIPT_TYPE,
        "approval_ref": approval_ref,
        "workflow_id": workflow_id,
        "criterion_id": criterion_id,
        "approved_by": approved_by,
        "reason": reason.strip(),
        "generated_at": _iso_now(),
        "single_use": True,
        "consumed": False,
    }
    path = _approval_receipt_path(project, approval_ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "status": "amendment_approved",
        "approval_ref": approval_ref,
        "workflow_id": workflow_id,
        "criterion_id": criterion_id,
        "receipt_path": _rel(project, path),
        "message": (
            "Amendment approval recorded (single-use, scoped to this workflow + "
            f"criterion). Apply with: amend-contract --approval-ref {approval_ref}."
        ),
    }


def amend_contract(
    *,
    project_dir: str | Path = ".",
    workflow_id: str,
    criterion_id: str,
    approval_ref: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Atomically amend one frozen criterion under a valid, single-use approval.

    edit fields -> re-freeze hash -> rebind workflow (phase preserved) ->
    write immutable audit record -> consume the approval token.
    """
    project = Path(project_dir).expanduser().resolve(strict=False)
    if not _valid_workflow_id(workflow_id):
        return _failure("blocked_amend", "Invalid workflow_id.")
    state = _load_yaml_dict(_workflow_state_path(project, workflow_id))
    if not _is_active_workflow_state(state):
        return _failure("blocked_amend", f"No active small-story workflow {workflow_id}.")

    # 1) Validate the approval token: present, unconsumed, scoped to this pair.
    receipt_path = _approval_receipt_path(project, approval_ref)
    if not receipt_path.exists():
        return _failure(
            "blocked_amend_no_approval",
            "Amendment denied: no approval record for --approval-ref. Record "
            "approval first with approve-amendment.",
        )
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except Exception:
        return _failure("blocked_amend_no_approval", "Amendment denied: approval record unreadable.")
    if receipt.get("consumed"):
        return _failure(
            "blocked_amend_consumed",
            "Amendment denied: this approval was already consumed (single-use).",
        )
    if receipt.get("workflow_id") != workflow_id or receipt.get("criterion_id") != criterion_id:
        return _failure(
            "blocked_amend_scope",
            "Amendment denied: approval is scoped to a different workflow/criterion.",
        )

    # 2) Bound the changes to amendable criterion fields.
    if not isinstance(fields, dict) or not fields:
        return _failure("blocked_amend", "No amendment fields provided.")
    bad = set(fields) - AMENDABLE_CRITERION_FIELDS
    if bad:
        return _failure(
            "blocked_amend_fields",
            f"Amendment denied: non-amendable field(s) {sorted(bad)}. Amendable: "
            f"{sorted(AMENDABLE_CRITERION_FIELDS)}.",
        )

    # 3) Load the contract; locate the criterion.
    contract_rel = state.get("success_criteria_contract_path") or DEFAULT_CONTRACT_PATH
    contract_path = Path(contract_rel)
    resolved = contract_path if contract_path.is_absolute() else project / contract_path
    if not resolved.exists():
        return _failure("blocked_amend", f"Contract not found at {contract_rel}.")
    backup = resolved.read_text(encoding="utf-8")
    contract = yaml.safe_load(backup) or {}
    criteria = contract.get("success_criteria") or []
    ids_before = [c.get("id") for c in criteria]
    target = next((c for c in criteria if c.get("id") == criterion_id), None)
    if target is None:
        return _failure("blocked_amend", f"Criterion {criterion_id} not found in contract.")
    old_hash = str((contract.get("contract_freeze") or {}).get("contract_hash") or "")

    # 4) Apply field changes; refuse if the criteria set would change.
    field_diff: dict[str, Any] = {}
    for key, value in fields.items():
        field_diff[key] = {"old": target.get(key), "new": value}
        target[key] = value
    ids_after = [c.get("id") for c in criteria]
    if sorted(ids_before) != sorted(ids_after) or len(ids_before) != len(ids_after):
        resolved.write_text(backup, encoding="utf-8")
        return _failure(
            "blocked_amend_criteria_set",
            "Amendment denied: the criteria set changed; amendments may only edit "
            "existing criterion fields.",
        )

    # 5) Write + re-freeze, then validate. Restore the exact original on failure.
    resolved.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    freeze_result = freeze_contract(
        project_dir=project, contract_path=contract_rel, frozen_by=receipt.get("approved_by", "user")
    )
    if not freeze_result.get("ok"):
        resolved.write_text(backup, encoding="utf-8")
        return _failure("blocked_amend", f"Re-freeze failed: {freeze_result.get('error')}")
    try:
        validation = validate_success_criteria_contract(resolved)
    except Exception as exc:
        resolved.write_text(backup, encoding="utf-8")
        return _failure(
            "blocked_amend_invalid",
            f"Amendment denied: amended contract is invalid ({exc}). Restored original.",
        )
    new_hash = str(validation.get("contract_hash") or "")

    # 6) Rebind the workflow in place (phase and all other state preserved).
    state["success_criteria_contract_hash"] = new_hash
    _workflow_state_path(project, workflow_id).write_text(
        yaml.safe_dump(state, sort_keys=False), encoding="utf-8"
    )

    # 7) Immutable audit record.
    audit = {
        "schema_version": 2,
        "receipt_type": AMENDMENT_RECEIPT_TYPE,
        "workflow_id": workflow_id,
        "criterion_id": criterion_id,
        "approval_ref": approval_ref,
        "approved_by": receipt.get("approved_by"),
        "reason": receipt.get("reason"),
        "old_contract_hash": old_hash,
        "new_contract_hash": new_hash,
        "field_diff": field_diff,
        "amended_at": _iso_now(),
    }
    digest = new_hash.split(":")[-1][:12] or "amend"
    audit_path = _evidence_dir(project) / f"amendment-{workflow_id}-{criterion_id}-{digest}.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    # 8) Consume the single-use token.
    receipt["consumed"] = True
    receipt["consumed_at"] = _iso_now()
    receipt["amendment_receipt_path"] = _rel(project, audit_path)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "status": "amended",
        "workflow_id": workflow_id,
        "criterion_id": criterion_id,
        "old_contract_hash": old_hash,
        "new_contract_hash": new_hash,
        "field_diff": field_diff,
        "receipt_path": _rel(project, audit_path),
        "message": "Contract amended, re-frozen, and workflow rebound; audit recorded.",
    }


def _unreadable_workflow_files(project: Path) -> list[str]:
    """Workflow state files that exist but cannot be parsed.

    `_load_yaml_dict` returns {} on a YAML error, so a corrupt file reads as
    an inactive workflow and the gate stands down — the file is present, the
    fast path in the hook has already proved that, and yet nothing is enforced.
    The header promises the opposite: an active workflow fails closed on any
    error. This closes the gap between the glob that proves a workflow exists
    and the parse that decides whether it is active (ISSUE-288).
    """
    workflows_dir = project / ".sweetclaude" / "state" / "workflows"
    if not workflows_dir.exists():
        return []
    bad = []
    for candidate in sorted(workflows_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError, UnicodeDecodeError):
            bad.append(candidate.name)
            continue
        if data is not None and not isinstance(data, dict):
            bad.append(candidate.name)
    return bad


def _any_small_story_workflow_exists(project: Path) -> bool:
    workflows_dir = project / ".sweetclaude" / "state" / "workflows"
    if not workflows_dir.exists():
        return False
    scan_dirs = [workflows_dir]
    archived = workflows_dir / "archived"
    if archived.exists():
        scan_dirs.append(archived)
    for scan_dir in scan_dirs:
        for candidate in scan_dir.glob("*.yaml"):
            state = _load_yaml_dict(candidate)
            if state.get("state_owner") == "small_story_controller" and state.get("requires_success_criteria_contract"):
                return True
    return False


def _completed_workflow_protected_paths(
    project: Path,
) -> tuple[set[Path], set[Path]]:
    """Return (protected_files, protected_dir_prefixes) for completed stories.

    protected_files: exact relative paths that are immutable (workflow YAML,
        ledger, closeout).
    protected_dir_prefixes: directory prefixes whose entire subtree is
        immutable (per-story report dirs like reports/small-story/ISSUE-048/).
    """
    protected_files: set[Path] = set()
    protected_dirs: set[Path] = set()
    workflows_dir = project / ".sweetclaude" / "state" / "workflows"
    if not workflows_dir.exists():
        return protected_files, protected_dirs
    scan_dirs = [workflows_dir]
    archived = workflows_dir / "archived"
    if archived.exists():
        scan_dirs.append(archived)
    for scan_dir in scan_dirs:
        for candidate in sorted(scan_dir.glob("*.yaml")):
            state = _load_yaml_dict(candidate)
            if state.get("state_owner") != "small_story_controller":
                continue
            if not state.get("requires_success_criteria_contract"):
                continue
            if state.get("status") != "complete":
                continue
            wf_id = state.get("workflow_id") if isinstance(state.get("workflow_id"), str) else candidate.stem
            protected_files.add(PROTECTED_WORKFLOWS_REL / "archived" / f"{wf_id}.yaml")
            report_dir = PROTECTED_REPORTS_REL / "small-story" / wf_id
            protected_dirs.add(report_dir)
            closeout_path = state.get("ship_closeout_artifact_path")
            if closeout_path:
                protected_files.add(Path(closeout_path))
            ledger_path = state.get("success_criteria_ledger_path")
            if ledger_path:
                protected_files.add(Path(ledger_path))
    return protected_files, protected_dirs


def _is_protected_by_completed_stories(
    rel: Path,
    protected_files: set[Path],
    protected_dirs: set[Path],
) -> bool:
    """Check if a project-relative path is protected by completed story history."""
    if rel in protected_files:
        return True
    for pdir in protected_dirs:
        if pdir in rel.parents or rel == pdir:
            return True
    return False


_BASH_WRITE_TOKENS = re.compile(
    r"\b(?:rm|mv|cp|tee|sed\s+-i|>"
    r"|write_text|write_bytes|>>)\b"
    r"|(?:^|[|;&])\s*(?:cat|printf|echo)\s+.*>"
)


def _gate_terminal_history(
    project: Path,
    tool: str,
    file_path: str | None,
    command: str | None,
) -> dict[str, Any]:
    """Gate decisions when only completed small-story workflows exist.

    Protects specific completed-story files, not shared parent directories.
    New stories can be authored in the same directory structure.
    """
    protected_files, protected_dirs = _completed_workflow_protected_paths(project)

    def _decision(allow: bool, reason: str, decision: str | None = None) -> dict[str, Any]:
        return {
            "allow": allow,
            "ok": allow,
            "decision": decision or ("allow" if allow else "deny"),
            "reason": reason,
            "workflow_id": None,
            "phase": "TERMINAL",
        }

    history_message = (
        "This project contains completed small-story workflows. Their "
        "controller-owned evidence (reports, workflow state) is permanent "
        "history and may not be modified. New concerns belong to a new story."
    )
    if tool in {"Write", "Edit", "NotebookEdit"}:
        if not file_path:
            return _decision(False, f"{history_message} {tool} call without a file path is anomalous.")
        rel = _project_relative(project, file_path)
        if rel is None:
            return _decision(True, "Target is outside the project; terminal-history gate does not apply.")
        if _is_protected_by_completed_stories(rel, protected_files, protected_dirs):
            return _decision(False, f"{history_message} {rel} is closed-story evidence.")
        return _decision(True, "Project files are unrestricted after story completion.")
    if tool == "Bash" and command:
        if not _BASH_WRITE_TOKENS.search(command):
            return _decision(True, "Read-only command; terminal-history gate does not apply.")
        lowered = command.lower()
        for pf in protected_files:
            if str(pf) in lowered:
                return _decision(False, f"{history_message} Command targets completed-story file `{pf}`.")
        for pd in protected_dirs:
            if str(pd) in lowered:
                return _decision(False, f"{history_message} Command targets completed-story directory `{pd}`.")
        return _decision(True, "Command does not target closed-story history.")
    return _decision(True, "Tool is not gated after story completion.")


def _active_small_story_workflows(project: Path) -> list[tuple[str, dict[str, Any]]]:
    """Every active (non-terminal) small-story workflow, deterministically ordered."""
    found: dict[str, dict[str, Any]] = {}
    workflows_dir = project / ".sweetclaude" / "state" / "workflows"
    if workflows_dir.exists():
        for candidate in sorted(workflows_dir.glob("*.yaml")):
            state = _load_yaml_dict(candidate)
            workflow_id = state.get("workflow_id") if isinstance(state.get("workflow_id"), str) else candidate.stem
            if not _valid_workflow_id(workflow_id):
                continue
            if _is_active_workflow_state(state):
                found[workflow_id] = state
    return sorted(found.items())


def _active_small_story_workflow(project: Path) -> tuple[str, dict[str, Any]] | None:
    """The single active workflow, preferring the one phase.yaml points at.

    Returns None when there is no active workflow OR when the active set is
    ambiguous and phase.yaml does not disambiguate — callers that must fail
    closed on ambiguity (the gate) use _active_small_story_workflows directly.
    """
    actives = _active_small_story_workflows(project)
    if not actives:
        return None
    if len(actives) == 1:
        return actives[0]
    phase_data = _load_yaml_dict(project / ".sweetclaude" / "state" / "phase.yaml")
    active_item = phase_data.get("active_work_item")
    if isinstance(active_item, dict) and active_item.get("entry_category") == "small-story":
        pointed = active_item.get("id")
        for workflow_id, state in actives:
            if workflow_id == pointed:
                return workflow_id, state
    return None


def _sync_phase_yaml(project: Path, workflow_id: str, phase: str) -> None:
    phase_path = project / ".sweetclaude" / "state" / "phase.yaml"
    phase_path.parent.mkdir(parents=True, exist_ok=True)
    data = _load_yaml_dict(phase_path)
    if "schema_version" not in data:
        data["schema_version"] = 2
    active_item = data.get("active_work_item")
    if not isinstance(active_item, dict):
        active_item = {}
    active_item.update({"id": workflow_id, "phase": phase, "entry_category": "small-story"})
    data["active_work_item"] = active_item
    phase_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _clear_phase_yaml_active_item(project: Path, workflow_id: str) -> None:
    phase_path = project / ".sweetclaude" / "state" / "phase.yaml"
    if not phase_path.exists():
        return
    data = _load_yaml_dict(phase_path)
    active_item = data.get("active_work_item")
    if isinstance(active_item, dict) and active_item.get("id") == workflow_id:
        data["active_work_item"] = None
        phase_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _sync_sweetclaude_yaml_active(project: Path, workflow_id: str, phase: str) -> None:
    sc_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    sc_path.parent.mkdir(parents=True, exist_ok=True)
    data = _load_yaml_dict(sc_path)
    work = data.setdefault("work", {})
    active = work.get("active")
    if not isinstance(active, dict):
        active = {}
    active.update({"id": workflow_id, "phase": phase})
    work["active"] = active
    data["work"] = work
    sc_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _clear_sweetclaude_yaml_active(project: Path, workflow_id: str) -> None:
    sc_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    if not sc_path.exists():
        return
    data = _load_yaml_dict(sc_path)
    work = data.get("work")
    if not isinstance(work, dict):
        return
    active = work.get("active")
    if isinstance(active, dict) and active.get("id") == workflow_id:
        work["active"] = None
        sc_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _set_workflow_phase(project: Path, workflow_id: str, phase: str) -> None:
    workflow_path = _workflow_state_path(project, workflow_id)
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    data = _load_yaml_dict(workflow_path)
    data.update({"workflow_id": workflow_id, "phase": phase})
    workflow_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    _sync_phase_yaml(project, workflow_id, phase)


def _check_state_phase_consistency(project: Path, workflow_id: str) -> dict[str, Any] | None:
    workflow_state = _load_yaml_dict(_workflow_state_path(project, workflow_id))
    if workflow_state.get("status") == "complete":
        return None
    workflow_phase = workflow_state.get("phase")
    phase_data = _load_yaml_dict(project / ".sweetclaude" / "state" / "phase.yaml")
    active_item = phase_data.get("active_work_item")
    if not isinstance(workflow_phase, str) or not isinstance(active_item, dict):
        return None
    if active_item.get("id") != workflow_id:
        if (
            active_item.get("entry_category") == "small-story"
            and _is_active_workflow_state(workflow_state)
        ):
            return {
                **_failure("blocked_state_inconsistent", BLOCKED_STATE_INCONSISTENT_MESSAGE),
                "workflow_phase": workflow_phase,
                "phase_yaml_phase": active_item.get("phase"),
                "phase_yaml_workflow_id": active_item.get("id"),
                "workflow_id": workflow_id,
            }
        return None
    item_phase = active_item.get("phase")
    if isinstance(item_phase, str) and item_phase != workflow_phase:
        return {
            **_failure("blocked_state_inconsistent", BLOCKED_STATE_INCONSISTENT_MESSAGE),
            "workflow_phase": workflow_phase,
            "phase_yaml_phase": item_phase,
            "workflow_id": workflow_id,
        }
    return None


def _replace_record_section(text: str, heading: str, values: list[str]) -> str:
    pattern = re.compile(rf"(## {re.escape(heading)}\n\n)(.*?)(\n\n## )", re.DOTALL)
    body = "\n".join(_markdown_list(values))
    replaced, count = pattern.subn(
        lambda match: f"{match.group(1)}{body}{match.group(3)}", text, count=1
    )
    if count == 0:
        return f"{text.rstrip()}\n\n## {heading}\n\n{body}\n"
    return replaced


def _record_section_items(text: str, heading: str) -> list[str]:
    pattern = re.compile(rf"## {re.escape(heading)}\n\n(.*?)\n\n## ", re.DOTALL)
    match = pattern.search(text)
    if not match:
        return []
    items = [
        line[2:].strip()
        for line in match.group(1).splitlines()
        if line.startswith("- ")
    ]
    return [item for item in items if item and item != "none recorded"]


def validate_ledger_evidence_paths(
    project_dir: str | Path,
    ledger_path: str | Path,
) -> dict[str, Any]:
    """Enforce small-story ledger evidence_path durability rules."""
    project = Path(project_dir).expanduser().resolve(strict=False)
    ledger = Path(ledger_path)
    if not ledger.is_absolute():
        ledger = project / ledger
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _failure("blocked_missing_completion_ledger", BLOCKED_MISSING_LEDGER_MESSAGE)
    except json.JSONDecodeError as exc:
        return _failure("blocked_completion_validation_failed", f"{BLOCKED_COMPLETION_VALIDATION_MESSAGE} ledger JSON error: {exc}")

    entries = data.get("criteria") or data.get("criterion_results")
    if not isinstance(entries, list) or not entries:
        return _failure("blocked_completion_validation_failed", f"{BLOCKED_COMPLETION_VALIDATION_MESSAGE} ledger criteria must be non-empty.")

    for entry in entries:
        criterion_id = entry.get("id") or "<unknown>"
        for field in ("evidence_path", "observed_output_path"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                return _failure("blocked_completion_validation_failed", f"{criterion_id} {field} is required.")
            resolved = (project / value).resolve(strict=False)
            try:
                resolved.relative_to(project)
            except ValueError:
                return _failure("blocked_completion_validation_failed", f"{criterion_id} {field} escapes project directory.")
            try:
                resolved.relative_to(project / ".sweetclaude" / "reports")
            except ValueError:
                return _failure("blocked_completion_validation_failed", f"{criterion_id} {field} must be under .sweetclaude/reports.")
            if not resolved.exists():
                return _failure("blocked_completion_validation_failed", f"{criterion_id} {field} does not exist: {value}")
            if resolved.is_file() and resolved.stat().st_size == 0:
                return _failure("blocked_completion_validation_failed", f"{criterion_id} {field} is empty: {value}")
        for field in ("success_criteria_contract_hash", "measured_command", "measured_at"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                return _failure("blocked_completion_validation_failed", f"{criterion_id} {field} is required.")

    return {"ok": True, "code": "evidence_paths_valid", "message": "Ledger evidence paths are valid."}


def _completion_result(
    *,
    project_dir: str | Path,
    workflow_id: str | None,
) -> dict[str, Any]:
    gate = _completion_gate_result(project_dir=project_dir, workflow_id=workflow_id)
    if not gate.get("ok"):
        return gate
    closeout = _validate_ship_closeout(
        Path(project_dir).expanduser().resolve(strict=False),
        gate["workflow_id"],
        gate["success_criteria_contract_hash"],
    )
    if not closeout.get("ok"):
        return closeout
    return {
        "ok": True,
        "code": "complete",
        "workflow_id": gate["workflow_id"],
        "completion_claim_allowed": True,
        "validator_result": gate["validator_result"],
        "closeout_artifact_path": closeout["closeout_artifact_path"],
    }


def _completion_gate_result(
    *,
    project_dir: str | Path,
    workflow_id: str | None,
) -> dict[str, Any]:
    project = Path(project_dir).expanduser().resolve(strict=False)
    result = validate_success_criteria_workflow(
        project_dir=project,
        workflow_id=workflow_id,
        stage="completion",
    )
    if not result.get("ok"):
        error = str(result.get("error") or result.get("blocking_failures") or "")
        if "ledger not found" in error.lower() or "no such file" in error.lower():
            return _failure("blocked_missing_completion_ledger", BLOCKED_MISSING_LEDGER_MESSAGE)
        return _failure("blocked_completion_validation_failed", BLOCKED_COMPLETION_VALIDATION_MESSAGE)
    ledger_path = result.get("ledger_path")
    if ledger_path:
        evidence = validate_ledger_evidence_paths(project, ledger_path)
        if not evidence.get("ok"):
            return evidence
    resolved_workflow_id = result.get("workflow_id") or workflow_id or _workflow_id_from_state(project)
    if not _valid_workflow_id(resolved_workflow_id):
        return _failure("blocked_completion_validation_failed", BLOCKED_COMPLETION_VALIDATION_MESSAGE)
    return {
        "ok": True,
        "code": "completion_gate_valid",
        "workflow_id": resolved_workflow_id,
        "completion_claim_allowed": False,
        "success_criteria_contract_hash": str(result.get("contract_hash") or ""),
        "ledger_path": str(ledger_path),
        "validator_result": result,
    }


def _validate_ship_closeout(project: Path, workflow_id: str, contract_hash: str) -> dict[str, Any]:
    closeout_rel = Path(".sweetclaude") / "reports" / "small-story" / workflow_id / "ship" / "closeout.json"
    closeout_path = project / closeout_rel
    try:
        closeout = json.loads(closeout_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _failure("blocked_ship_closeout_missing", BLOCKED_CLOSEOUT_MISSING_MESSAGE)
    except json.JSONDecodeError as exc:
        return _failure(
            "blocked_completion_validation_failed",
            f"{BLOCKED_COMPLETION_VALIDATION_MESSAGE} closeout JSON error: {exc}",
        )

    expected = {
        "workflow_id": workflow_id,
        "success_criteria_contract_hash": contract_hash,
        "generated_by": "small_story_controller",
        "completion_validation_ok": True,
        "terminal_state": "complete",
        "terminal_state_owner": "small_story_controller",
    }
    for field, value in expected.items():
        if closeout.get(field) != value:
            return _failure("blocked_completion_validation_failed", f"{field} is invalid in SHIP closeout.")
    return {
        "ok": True,
        "code": "ship_closeout_valid",
        "closeout_artifact_path": str(closeout_rel),
    }


def _archive_terminal_workflow(workflow_path: Path) -> None:
    """Move a completed workflow file to the archived/ subdirectory."""
    archived_dir = workflow_path.parent / "archived"
    archived_dir.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.move(str(workflow_path), str(archived_dir / workflow_path.name))


def _cleanup_stop_ack(project: Path, workflow_id: str) -> None:
    ack_path = project / ".sweetclaude" / "state" / "workflows" / f".stop-ack-{workflow_id}.json"
    ack_path.unlink(missing_ok=True)


def _write_workflow_terminal_state(project: Path, workflow_id: str, closeout_rel: Path) -> None:
    workflow_path = project / ".sweetclaude" / "state" / "workflows" / f"{workflow_id}.yaml"
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if workflow_path.exists():
        loaded = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            data = loaded
    data.update(
        {
            "workflow_id": workflow_id,
            "phase": "SHIP",
            "status": "complete",
            "terminal_state_written_by": "small_story_controller",
            "completion_claim_allowed": True,
            "ship_closeout_artifact_path": str(closeout_rel),
        }
    )
    workflow_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    _archive_terminal_workflow(workflow_path)
    _cleanup_stop_ack(project, workflow_id)


def _status_details(
    project: Path,
    workflow_id: str | None,
    completion: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    criteria = _criteria_summary(project, workflow_id)
    phase_artifacts = _phase_artifact_summary(project, workflow_id)
    return {
        "generated_by": "small_story_controller",
        "controller_owned": True,
        "workflow_completion": {
            "complete": bool(completion.get("ok")),
            "status": "complete" if completion.get("ok") else completion.get("code"),
            "completion_claim_allowed": bool(completion.get("completion_claim_allowed")),
            "closeout_artifact_path": completion.get("closeout_artifact_path"),
        },
        "completion_validator_result": {
            "ok": bool(gate.get("ok")),
            "code": gate.get("code"),
            "validator_result": gate.get("validator_result"),
        },
        "criteria_summary": criteria,
        "phase_artifacts": phase_artifacts,
        "product_readiness": {
            "ready": False,
            "reason": "Fresh disposable end-to-end execution must pass before product readiness.",
            "remaining_tasks": ["TASK-008"],
        },
    }


def _phase_artifact_summary(project: Path, workflow_id: str | None) -> dict[str, dict[str, Any]]:
    if not workflow_id:
        return {
            name: {"present": False, "path": str(path)}
            for name, path in _phase_artifact_paths("<unknown>").items()
        }
    return {
        name: {
            "present": (project / path).exists() and (project / path).stat().st_size > 0,
            "path": str(path),
        }
        for name, path in _phase_artifact_paths(workflow_id).items()
    }


def _phase_artifact_paths(workflow_id: str) -> dict[str, Path]:
    base = Path(".sweetclaude") / "reports" / "small-story" / workflow_id
    return {
        "design": base / "design" / "design-artifact.md",
        "plan": base / "plan" / "implementation-plan.md",
        "implementation": base / "implementation" / "implementation-record.md",
        "ledger": Path(".sweetclaude") / "reports" / "success-criteria-ledger.json",
        "ship_closeout": base / "ship" / "closeout.json",
    }


def _criteria_summary(project: Path, workflow_id: str | None) -> dict[str, Any]:
    expected_ids = _expected_criterion_ids(project, workflow_id)
    ledger_path = project / ".sweetclaude" / "reports" / "success-criteria-ledger.json"
    if not ledger_path.exists():
        return {
            "all_success_criteria_passed": False,
            "criteria": [],
            "expected_criterion_ids": expected_ids,
            "missing_criteria": expected_ids,
            "failed_criteria": [],
        }
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "all_success_criteria_passed": False,
            "criteria": [],
            "expected_criterion_ids": expected_ids,
            "missing_criteria": expected_ids,
            "failed_criteria": [],
        }
    entries = ledger.get("criteria") if isinstance(ledger.get("criteria"), list) else []
    criteria = [
        {
            "id": str(entry.get("id") or ""),
            "status": str(entry.get("status") or ""),
            "evidence_path": entry.get("evidence_path"),
            "measured_command": entry.get("measured_command"),
        }
        for entry in entries
        if isinstance(entry, dict)
    ]
    present_ids = [item["id"] for item in criteria if item["id"]]
    pass_values = {"pass", "passed", "ok", "success"}
    return {
        "all_success_criteria_passed": ledger.get("all_success_criteria_passed") is True,
        "criteria": criteria,
        "expected_criterion_ids": expected_ids,
        "missing_criteria": [criterion_id for criterion_id in expected_ids if criterion_id not in present_ids],
        "failed_criteria": [
            item["id"]
            for item in criteria
            if item["id"] and item["status"].lower() not in pass_values
        ],
    }


def _expected_criterion_ids(project: Path, workflow_id: str | None) -> list[str]:
    if workflow_id:
        workflow_path = project / ".sweetclaude" / "state" / "workflows" / f"{workflow_id}.yaml"
        if workflow_path.exists():
            data = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
            ids = data.get("criterion_ids")
            if isinstance(ids, list) and all(isinstance(item, str) for item in ids):
                return ids
    contract_path = project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    if contract_path.exists():
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
        criteria = contract.get("success_criteria")
        if isinstance(criteria, list):
            return [item["id"] for item in criteria if isinstance(item, dict) and isinstance(item.get("id"), str)]
    return []


def _workflow_id_from_state(project: Path) -> str | None:
    small_story_state = project / ".sweetclaude" / "state" / "small-story.yaml"
    if small_story_state.exists():
        data = yaml.safe_load(small_story_state.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict) and isinstance(data.get("workflow_id"), str):
            return data["workflow_id"]
    active = _active_small_story_workflow(project)
    if active is not None:
        return active[0]
    # No active workflow: a completed story must still be resolvable for
    # status rendering and finalize (TASK-C8 run 2 finding). Resolve a single
    # terminal workflow file; ambiguity still returns None.
    workflows_dir = project / ".sweetclaude" / "state" / "workflows"
    if workflows_dir.exists():
        candidates = sorted(workflows_dir.glob("*.yaml"))
        if len(candidates) == 1:
            state = _load_yaml_dict(candidates[0])
            workflow_id = state.get("workflow_id") if isinstance(state.get("workflow_id"), str) else candidates[0].stem
            if _valid_workflow_id(workflow_id) and state.get("requires_success_criteria_contract"):
                return workflow_id
    return None


def _blocked_summary(code: str) -> str:
    if code == "blocked_slice0_downstream_unavailable":
        return "Small-story is blocked because later downstream phases are not implemented."
    if code == "blocked_design_entry_failed":
        return "Small-story DESIGN is blocked because define-exit validation did not pass."
    if code == "blocked_plan_entry_failed":
        return "Small-story PLAN is blocked because DESIGN did not produce a valid durable artifact."
    if code == "blocked_implementation_entry_failed":
        return "Small-story IMPLEMENT is blocked because PLAN did not produce a valid durable artifact."
    if code == "blocked_verify_entry_failed":
        return "Small-story VERIFY is blocked because IMPLEMENT did not produce valid durable evidence."
    if code == "blocked_missing_completion_ledger":
        return "Small-story is blocked because the controller-owned success criteria ledger is missing."
    if code == "blocked_completion_validation_failed":
        return "Small-story is blocked because completion validation failed."
    if code == "blocked_ship_entry_failed":
        return "Small-story SHIP is blocked because VERIFY did not produce valid ledger evidence."
    if code == "blocked_ship_closeout_missing":
        return "Small-story is blocked because SHIP/closeout has not written durable closeout evidence."
    if code == "blocked_state_inconsistent":
        return "Small-story is blocked because phase state files disagree; controller-owned state must be repaired."
    if code == "blocked_ledger_path_divergent":
        return "Small-story is blocked because workflow state points to a non-canonical ledger path."
    if code == "blocked_implementation_evidence_empty":
        return "Small-story is blocked because no harness-observed implementation evidence was recorded."
    return "Small-story is blocked by controller state."


def _failure(code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "code": code,
        "message": message,
        "completion_claim_allowed": False,
    }


def _forbidden_phrases(text: str) -> list[str]:
    lowered = text.lower()
    found = [phrase for phrase in FORBIDDEN_SUCCESS_PHRASES if phrase in lowered]
    if re.search(r"\ball\s+\d+\s+success\s+criteria\s+pass", lowered):
        found.append("all <n> success criteria pass")
    return found


def _criterion_ids(project: Path, workflow_id: str, define_result: dict[str, Any]) -> list[str]:
    workflow_path = project / ".sweetclaude" / "state" / "workflows" / f"{workflow_id}.yaml"
    if workflow_path.exists():
        data = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
        ids = data.get("criterion_ids")
        if isinstance(ids, list) and all(isinstance(item, str) for item in ids):
            return ids
    ids = define_result.get("criterion_ids")
    if isinstance(ids, list) and all(isinstance(item, str) for item in ids):
        return ids
    contract_path = project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    if contract_path.exists():
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
        criteria = contract.get("success_criteria")
        if isinstance(criteria, list):
            return [item["id"] for item in criteria if isinstance(item, dict) and isinstance(item.get("id"), str)]
    return []


def _strip_markdown_headings(text: str) -> str:
    """Neutralize heading markers in agent-supplied prose so it cannot forge
    or shadow controller-owned record sections (TASK-C7 MAJOR finding)."""
    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            lines.append(line[: len(line) - len(stripped)] + stripped.lstrip("#").lstrip())
        else:
            lines.append(line)
    return "\n".join(lines)


def _sanitize_no_success_criteria(text: str) -> str:
    text = _strip_markdown_headings(text)
    lines = [line for line in text.splitlines() if not line.strip().lower().startswith("success_criteria:")]
    return "\n".join(lines).strip() or "Implementation plan pending elaboration."


def _sanitize_no_completion_claims(text: str) -> str:
    text = _strip_markdown_headings(text)
    lines = []
    for line in text.splitlines():
        lowered = line.lower()
        if any(phrase in lowered for phrase in FORBIDDEN_SUCCESS_PHRASES):
            continue
        if re.search(r"\ball\s+\d+\s+success\s+criteria\s+pass", lowered):
            continue
        lines.append(line)
    return "\n".join(lines).strip() or "Implementation evidence recorded; completion claims require VERIFY and SHIP."


def _clean_list(values: list[str] | None) -> list[str]:
    return [value.strip() for value in (values or []) if isinstance(value, str) and value.strip()]


def _markdown_list(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values] if values else ["- none recorded"]


def _json_print(data: dict[str, Any]) -> int:
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0 if data.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    route = sub.add_parser("route")
    route.add_argument("--route-surface", required=True)

    transition = sub.add_parser("transition")
    transition.add_argument("--workflow-id")
    transition.add_argument("--target-stage", required=True)

    design = sub.add_parser("design")
    design.add_argument("--workflow-id")
    design.add_argument("--design-summary", default="")

    plan = sub.add_parser("plan")
    plan.add_argument("--workflow-id")
    plan.add_argument("--plan-summary", default="")

    implement = sub.add_parser("implement")
    implement.add_argument("--workflow-id")
    implement.add_argument("--implementation-summary", default="")
    implement.add_argument("--touched-file", action="append", default=[])
    implement.add_argument("--command-run", action="append", default=[])
    implement.add_argument("--dependency-change", action="append", default=[])
    implement.add_argument("--environment-change", action="append", default=[])

    verify = sub.add_parser("verify")
    verify.add_argument("--workflow-id")
    verify.add_argument("--criterion-result-json", default="")
    verify.add_argument("--allow-no-file-changes", action="store_true")

    probe = sub.add_parser("enforcement-probe")
    probe.add_argument("--workflow-id")
    probe_mode = probe.add_mutually_exclusive_group(required=True)
    probe_mode.add_argument("--arm", action="store_true")
    probe_mode.add_argument("--check", action="store_true")

    init_parser = sub.add_parser("init")
    init_parser.add_argument("--workflow-id", required=True)
    init_parser.add_argument("--contract-path")

    gate_parser = sub.add_parser("gate")
    gate_parser.add_argument("--tool", required=True)
    gate_parser.add_argument("--file")
    gate_parser.add_argument("--command", dest="bash_command")

    record_parser = sub.add_parser("record-evidence")
    record_parser.add_argument("--tool", required=True)
    record_parser.add_argument("--file")
    record_parser.add_argument("--command", dest="bash_command")
    record_parser.add_argument("--workflow-id")

    ship = sub.add_parser("ship")
    ship.add_argument("--workflow-id")
    ship.add_argument("--terminal-actor", default="small_story_controller")

    finalize = sub.add_parser("finalize")
    finalize.add_argument("--workflow-id")
    finalize.add_argument("--attempted-response", default="")

    status = sub.add_parser("render-status")
    status.add_argument("--workflow-id")

    evidence = sub.add_parser("validate-evidence-paths")
    evidence.add_argument("--ledger", required=True)

    approve_amend = sub.add_parser("approve-amendment")
    approve_amend.add_argument("--workflow-id", required=True)
    approve_amend.add_argument("--criterion", required=True)
    approve_amend.add_argument("--reason", required=True)
    approve_amend.add_argument("--approved-by", default="user")

    amend = sub.add_parser("amend-contract")
    amend.add_argument("--workflow-id", required=True)
    amend.add_argument("--criterion", required=True)
    amend.add_argument("--approval-ref", required=True)
    amend.add_argument("--fields", required=True, help="JSON object, or @path to a JSON file")

    args = parser.parse_args(argv)
    if args.command == "route":
        return _json_print(route_small_story(project_dir=args.project_dir, route_surface=args.route_surface))
    if args.command == "transition":
        return _json_print(
            transition_small_story(
                project_dir=args.project_dir,
                workflow_id=args.workflow_id,
                target_stage=args.target_stage,
            )
        )
    if args.command == "design":
        return _json_print(
            enter_design_phase(
                project_dir=args.project_dir,
                workflow_id=args.workflow_id,
                design_summary=args.design_summary,
            )
        )
    if args.command == "plan":
        return _json_print(
            enter_plan_phase(
                project_dir=args.project_dir,
                workflow_id=args.workflow_id,
                plan_summary=args.plan_summary,
            )
        )
    if args.command == "implement":
        return _json_print(
            enter_implement_phase(
                project_dir=args.project_dir,
                workflow_id=args.workflow_id,
                implementation_summary=args.implementation_summary,
                touched_files=args.touched_file,
                commands_run=args.command_run,
                dependency_changes=args.dependency_change,
                environment_changes=args.environment_change,
            )
        )
    if args.command == "verify":
        criterion_results = json.loads(args.criterion_result_json) if args.criterion_result_json else None
        # Accept either a dict keyed by criterion id or a list of entries
        # carrying their own id — callers reach for both.
        if isinstance(criterion_results, list):
            criterion_results = {
                str(e.get("criterion_id") or e.get("id")): {k: v for k, v in e.items() if k not in ("criterion_id", "id")}
                for e in criterion_results
                if isinstance(e, dict) and (e.get("criterion_id") or e.get("id"))
            }
        return _json_print(
            enter_verify_phase(
                project_dir=args.project_dir,
                workflow_id=args.workflow_id,
                criterion_results=criterion_results,
                allow_no_file_changes=args.allow_no_file_changes,
            )
        )
    if args.command == "enforcement-probe":
        if args.arm:
            return _json_print(arm_enforcement_probe(project_dir=args.project_dir, workflow_id=args.workflow_id))
        return _json_print(check_enforcement_probe(project_dir=args.project_dir, workflow_id=args.workflow_id))
    if args.command == "approve-amendment":
        return _json_print(
            approve_amendment(
                project_dir=args.project_dir,
                workflow_id=args.workflow_id,
                criterion_id=args.criterion,
                reason=args.reason,
                approved_by=args.approved_by,
            )
        )
    if args.command == "amend-contract":
        fields_raw = args.fields
        if fields_raw.startswith("@"):
            try:
                fields_raw = Path(fields_raw[1:]).read_text(encoding="utf-8")
            except Exception as exc:
                return _json_print(_failure("blocked_amend", f"--fields file unreadable: {exc}"))
        try:
            parsed_fields = json.loads(fields_raw)
        except Exception as exc:
            return _json_print(_failure("blocked_amend", f"--fields is not valid JSON: {exc}"))
        return _json_print(
            amend_contract(
                project_dir=args.project_dir,
                workflow_id=args.workflow_id,
                criterion_id=args.criterion,
                approval_ref=args.approval_ref,
                fields=parsed_fields,
            )
        )
    if args.command == "init":
        return _json_print(
            init_workflow(
                project_dir=args.project_dir,
                workflow_id=args.workflow_id,
                contract_path=args.contract_path,
            )
        )
    if args.command == "gate":
        return _json_print(
            gate_tool_use(
                project_dir=args.project_dir,
                tool=args.tool,
                file_path=args.file,
                command=args.bash_command,
            )
        )
    if args.command == "record-evidence":
        return _json_print(
            record_evidence(
                project_dir=args.project_dir,
                tool=args.tool,
                file_path=args.file,
                command=args.bash_command,
                workflow_id=args.workflow_id,
            )
        )
    if args.command == "ship":
        return _json_print(
            enter_ship_phase(
                project_dir=args.project_dir,
                workflow_id=args.workflow_id,
                terminal_actor=args.terminal_actor,
            )
        )
    if args.command == "finalize":
        return _json_print(
            finalize_small_story(
                project_dir=args.project_dir,
                workflow_id=args.workflow_id,
                attempted_response=args.attempted_response,
            )
        )
    if args.command == "render-status":
        return _json_print(render_small_story_status(project_dir=args.project_dir, workflow_id=args.workflow_id))
    if args.command == "validate-evidence-paths":
        return _json_print(validate_ledger_evidence_paths(args.project_dir, args.ledger))
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
