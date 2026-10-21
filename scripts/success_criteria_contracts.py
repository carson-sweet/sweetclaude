#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate SweetClaude success criteria contracts and ledgers."""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


VALID_MEASUREMENT_TYPES = {
    "command",
    "schema_check",
    "file_hash",
    "ui_assertion",
    "human_terminal_approval",
    "external_system",
}
VALID_EVIDENCE_OWNERS = {"controller", "test", "human", "external_system"}
VALID_MEASUREMENT_PHASES = {
    "success-criteria-definition",
    "contribution-discovery",
    "authority-review",
    "story-design",
    "acceptance-and-red-test-validation",
    "implementation",
    "terminal-review",
}
PASS_STATUSES = {"pass", "passed", "ok", "success"}
FRESHNESS_STATUSES = {"fresh", "current", "valid"}
WORKFLOW_STAGES = {"draft", "define-exit", "completion"}
DEFAULT_CONTRACT_PATH = ".sweetclaude/contracts/success-criteria-contract.yaml"
DEFAULT_LEDGER_PATH = ".sweetclaude/reports/success-criteria-ledger.json"
VAGUE_TERMS = {
    "adequate",
    "appropriate",
    "complete",
    "comprehensive",
    "good",
    "handle",
    "handles",
    "improve",
    "improved",
    "proper",
    "properly",
    "production-ready",
    "reasonable",
    "robust",
    "sota",
    "support",
    "supports",
}
OBJECTIVE_SIGNALS = {
    "contains",
    "equals",
    "exists",
    "exits",
    "fails",
    "matches",
    "must be",
    "not contain",
    "passes",
    "returns",
    "sha256",
    "status",
}


class SuccessCriteriaValidationError(ValueError):
    """Raised when a success criteria contract or ledger fails closed."""


def validate_success_criteria_contract(path: str | Path) -> dict[str, Any]:
    """Validate a frozen success criteria contract YAML artifact."""
    contract_path = Path(path)
    contract = _load_yaml_object(contract_path, context="Success criteria contract")
    _validate_contract_shape(contract)
    expected_hash = compute_success_criteria_contract_hash(contract)
    declared_hash = _normalize_hash(
        _require_non_empty_string(
            _require_object(contract, "contract_freeze", context="Success criteria contract"),
            "contract_hash",
            context="Success criteria contract contract_freeze",
        )
    )
    if declared_hash != expected_hash:
        raise SuccessCriteriaValidationError(
            "Success criteria contract contract_hash mismatch: "
            f"expected {expected_hash}, got {declared_hash}"
        )
    criterion_ids = [criterion["id"] for criterion in contract["success_criteria"]]
    return {
        "ok": True,
        "contract_hash": expected_hash,
        "criterion_ids": criterion_ids,
        "criteria_count": len(criterion_ids),
    }


def validate_success_criteria_ledger(
    *,
    contract_path: str | Path,
    ledger_path: str | Path,
) -> dict[str, Any]:
    """Validate final completion evidence against a frozen criteria contract."""
    contract = _load_yaml_object(contract_path, context="Success criteria contract")
    contract_result = validate_success_criteria_contract(contract_path)
    contract_hash = contract_result["contract_hash"]
    expected_criteria = {criterion["id"]: criterion for criterion in contract["success_criteria"]}

    ledger = _load_json_object(ledger_path, context="Success criteria ledger")
    story_id = _require_non_empty_string(ledger, "story_id", context="Success criteria ledger")
    if story_id != contract["story_id"]:
        raise SuccessCriteriaValidationError(
            "Success criteria ledger story_id mismatch: "
            f"expected {contract['story_id']}, got {story_id}"
        )
    ledger_hash = _normalize_hash(
        _require_non_empty_string(
            ledger,
            "success_criteria_contract_hash",
            context="Success criteria ledger",
        )
    )
    if ledger_hash != contract_hash:
        raise SuccessCriteriaValidationError(
            "Success criteria ledger success_criteria_contract_hash mismatch: "
            f"expected {contract_hash}, got {ledger_hash}"
        )
    if ledger.get("all_success_criteria_passed") is not True:
        raise SuccessCriteriaValidationError(
            "Success criteria ledger all_success_criteria_passed must be true"
        )

    entries = _ledger_entries(ledger)
    seen: set[str] = set()
    missing_or_failed: list[str] = []
    for index, entry in enumerate(entries):
        context = f"Success criteria ledger criteria[{index}]"
        criterion_id = _require_non_empty_string(entry, "id", context=context)
        if criterion_id in seen:
            raise SuccessCriteriaValidationError(
                f"Success criteria ledger has duplicate criterion id {criterion_id}"
            )
        seen.add(criterion_id)
        expected = expected_criteria.get(criterion_id)
        if expected is None:
            raise SuccessCriteriaValidationError(
                f"Success criteria ledger contains unknown criterion id {criterion_id}"
            )
        status = _entry_status(entry, context=context)
        if status not in PASS_STATUSES:
            missing_or_failed.append(criterion_id)
            continue
        entry_hash = entry.get("success_criteria_contract_hash")
        if entry_hash is not None and _normalize_hash(str(entry_hash)) != contract_hash:
            raise SuccessCriteriaValidationError(
                f"Success criteria ledger criterion {criterion_id} has stale contract hash"
            )
        evidence_artifact = _require_non_empty_string(
            entry,
            "evidence_artifact",
            context=context,
        )
        evidence_owner = _require_non_empty_string(entry, "evidence_owner", context=context)
        if evidence_artifact != expected["evidence_artifact"]:
            raise SuccessCriteriaValidationError(
                f"Success criteria ledger criterion {criterion_id} evidence_artifact mismatch: "
                f"expected {expected['evidence_artifact']}, got {evidence_artifact}"
            )
        if evidence_owner != expected["evidence_owner"]:
            raise SuccessCriteriaValidationError(
                f"Success criteria ledger criterion {criterion_id} evidence_owner mismatch: "
                f"expected {expected['evidence_owner']}, got {evidence_owner}"
            )
        if not _entry_evidence_is_fresh(entry):
            raise SuccessCriteriaValidationError(
                f"Success criteria ledger criterion {criterion_id} evidence is stale or unverified"
            )

    expected_ids = set(expected_criteria)
    if seen != expected_ids:
        missing = sorted(expected_ids - seen)
        extra = sorted(seen - expected_ids)
        details = []
        if missing:
            details.append(f"missing {missing}")
        if extra:
            details.append(f"extra {extra}")
        raise SuccessCriteriaValidationError(
            "Success criteria ledger criterion ids do not match contract: " + "; ".join(details)
        )
    if missing_or_failed:
        raise SuccessCriteriaValidationError(
            "Success criteria ledger has failed criteria: " + ", ".join(sorted(missing_or_failed))
        )
    return {
        "ok": True,
        "contract_hash": contract_hash,
        "criterion_ids": sorted(expected_ids),
        "criteria_count": len(expected_ids),
        "all_success_criteria_passed": True,
    }


def validate_success_criteria_workflow(
    *,
    project_dir: str | Path = ".",
    stage: str,
    workflow_id: str | None = None,
    contract_path: str | Path | None = None,
    ledger_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate the success-criteria gate for a workflow lifecycle stage."""
    if stage not in WORKFLOW_STAGES:
        raise SuccessCriteriaValidationError(
            f"Workflow validation stage must be one of {sorted(WORKFLOW_STAGES)}"
        )
    resolver = WorkflowArtifactResolver(project_dir=Path(project_dir), workflow_id=workflow_id)
    resolved_contract = resolver.resolve_contract_path(contract_path)
    resolved_ledger = resolver.resolve_ledger_path(ledger_path)
    resolved_workflow_id = workflow_id or resolver.workflow_id

    try:
        if stage in {"draft", "define-exit"}:
            result = validate_success_criteria_contract(resolved_contract)
            if stage == "define-exit":
                _validate_current_surface_measurability(resolved_contract)
        elif stage == "completion":
            result = validate_success_criteria_ledger(
                contract_path=resolved_contract,
                ledger_path=resolved_ledger,
            )
        else:
            raise AssertionError(stage)
    except Exception as exc:
        failure = {
            "ok": False,
            "workflow_id": resolved_workflow_id,
            "stage": stage,
            "contract_path": str(resolved_contract),
            "ledger_path": str(resolved_ledger) if resolved_ledger else None,
            "blocking": stage != "draft",
            "blocking_failures": [str(exc)] if stage != "draft" else [],
            "error": str(exc),
            "recovery_hint": _workflow_recovery_hint(stage, str(exc)),
        }
        return failure

    return {
        "ok": True,
        "workflow_id": resolved_workflow_id,
        "stage": stage,
        "contract_path": str(resolved_contract),
        "ledger_path": str(resolved_ledger) if resolved_ledger else None,
        "contract_hash": result.get("contract_hash"),
        "criterion_ids": result.get("criterion_ids", []),
        "criteria_count": result.get("criteria_count"),
        "all_success_criteria_passed": result.get("all_success_criteria_passed"),
        "blocking": False,
        "blocking_failures": [],
        "recovery_hint": "",
    }


class WorkflowArtifactResolver:
    """Resolve success-criteria artifacts from workflow or John Wick state."""

    def __init__(self, *, project_dir: Path, workflow_id: str | None = None) -> None:
        self.project_dir = project_dir.expanduser().resolve(strict=False)
        self.workflow_id = workflow_id
        self.workflow_state = self._load_workflow_state(workflow_id) if workflow_id else {}
        self.john_wick_state = self._load_optional_yaml(
            self.project_dir / ".sweetclaude" / "state" / "john-wick.yaml"
        )

    def resolve_contract_path(self, explicit: str | Path | None = None) -> Path:
        return self._resolve_path(
            explicit
            or self._extract_contract_path(self.workflow_state)
            or self._extract_contract_path(self.john_wick_state)
            or DEFAULT_CONTRACT_PATH,
            field="contract",
        )

    def resolve_ledger_path(self, explicit: str | Path | None = None) -> Path | None:
        value = (
            explicit
            or self._extract_ledger_path(self.workflow_state)
            or self._extract_ledger_path(self.john_wick_state)
            or DEFAULT_LEDGER_PATH
        )
        return self._resolve_path(value, field="ledger")

    def _load_workflow_state(self, workflow_id: str | None) -> dict[str, Any]:
        if not workflow_id:
            return {}
        if not re.match(r"^[A-Za-z0-9_-]+$", workflow_id):
            raise SuccessCriteriaValidationError(f"Invalid workflow id: {workflow_id}")
        state_path = (
            self.project_dir
            / ".sweetclaude"
            / "state"
            / "workflows"
            / f"{workflow_id}.yaml"
        )
        state = self._load_optional_yaml(state_path)
        if state and state.get("workflow_id") not in {None, workflow_id}:
            raise SuccessCriteriaValidationError(
                f"Workflow state id mismatch: expected {workflow_id}, got {state.get('workflow_id')}"
            )
        return state

    def _load_optional_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise SuccessCriteriaValidationError(f"Workflow state is not valid YAML: {path}: {exc}") from exc
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise SuccessCriteriaValidationError(f"Workflow state must be a YAML object: {path}")
        return data

    def _resolve_path(self, value: str | Path, *, field: str) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.project_dir / path
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(self.project_dir)
        except ValueError:
            raise SuccessCriteriaValidationError(
                f"Resolved {field} path escapes project directory: {resolved}"
            ) from None
        return resolved

    def _extract_contract_path(self, state: dict[str, Any]) -> str | None:
        return self._extract_path(
            state,
            nested_key="success_criteria_contract",
            direct_keys=("success_criteria_contract_path", "contract_path"),
            artifact_keys=(
                "success_criteria_contract",
                "success_criteria_contract_path",
                "success-criteria-contract",
            ),
        )

    def _extract_ledger_path(self, state: dict[str, Any]) -> str | None:
        return self._extract_path(
            state,
            nested_key="success_criteria_ledger",
            direct_keys=("success_criteria_ledger_path", "ledger_path"),
            artifact_keys=(
                "success_criteria_ledger",
                "success_criteria_ledger_path",
                "success-criteria-ledger",
            ),
        )

    def _extract_path(
        self,
        state: dict[str, Any],
        *,
        nested_key: str,
        direct_keys: tuple[str, ...],
        artifact_keys: tuple[str, ...],
    ) -> str | None:
        nested = state.get(nested_key)
        if isinstance(nested, dict):
            value = nested.get("path")
            if isinstance(value, str) and value.strip():
                return value.strip()
        elif isinstance(nested, str) and nested.strip():
            return nested.strip()

        for key in direct_keys:
            value = state.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        artifacts = state.get("artifacts")
        if isinstance(artifacts, dict):
            for key in artifact_keys:
                value = artifacts.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, dict):
                    nested_value = value.get("path")
                    if isinstance(nested_value, str) and nested_value.strip():
                        return nested_value.strip()
        return None


def compute_success_criteria_contract_hash(contract: dict[str, Any]) -> str:
    """Return the canonical hash for a contract, excluding its declared hash."""
    canonical = copy.deepcopy(contract)
    freeze = canonical.get("contract_freeze")
    if isinstance(freeze, dict):
        freeze.pop("contract_hash", None)
    encoded = yaml.safe_dump(canonical, sort_keys=True, allow_unicode=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _validate_contract_shape(contract: dict[str, Any]) -> None:
    required_top = (
        "story_id",
        "story_title",
        "story_objective",
        "expected_outcomes",
        "non_goals",
        "success_criteria",
        "contract_freeze",
    )
    for field in required_top:
        if _blank(contract.get(field)):
            raise SuccessCriteriaValidationError(
                f"Success criteria contract is missing {field}"
            )
    story_id = str(contract["story_id"])
    if not re.match(r"^[A-Z]+-[0-9]+$", story_id):
        raise SuccessCriteriaValidationError(
            f"Success criteria contract story_id is invalid: {story_id}"
        )
    _validate_outcomes(contract)
    _validate_criteria(contract)
    freeze = _require_object(contract, "contract_freeze", context="Success criteria contract")
    _require_non_empty_string(freeze, "frozen_at", context="Success criteria contract contract_freeze")
    _require_non_empty_string(freeze, "frozen_by", context="Success criteria contract contract_freeze")
    _parse_timestamp(str(freeze["frozen_at"]), field="contract_freeze.frozen_at")


def _validate_outcomes(contract: dict[str, Any]) -> None:
    outcomes = _require_non_empty_list(
        contract,
        "expected_outcomes",
        context="Success criteria contract",
    )
    seen: set[str] = set()
    for index, outcome in enumerate(outcomes):
        if not isinstance(outcome, dict):
            raise SuccessCriteriaValidationError(
                f"Success criteria contract expected_outcomes[{index}] must be an object"
            )
        outcome_id = _require_non_empty_string(
            outcome,
            "id",
            context=f"Success criteria contract expected_outcomes[{index}]",
        )
        if not re.match(r"^OUTCOME-[0-9]{3,}$", outcome_id):
            raise SuccessCriteriaValidationError(
                f"Success criteria contract outcome id is invalid: {outcome_id}"
            )
        if outcome_id in seen:
            raise SuccessCriteriaValidationError(
                f"Success criteria contract duplicate outcome id: {outcome_id}"
            )
        seen.add(outcome_id)
        _require_non_empty_string(
            outcome,
            "statement",
            context=f"Success criteria contract expected_outcomes[{index}]",
        )


SURFACE_UNSUPPORTED_EVIDENCE_OWNERS = {"human", "external_system"}
SURFACE_UNSUPPORTED_MEASUREMENT_PHASES = {"terminal-review"}


def _validate_current_surface_measurability(contract_path: str | Path) -> None:
    """Reject contracts the current large-story surface cannot convert into ledger evidence.

    GUARD-CONTRACT-EVIDENCE-OWNER-CURRENT-SURFACE: terminal review is not
    implemented, so criteria requiring terminal-review measurement or
    human/external evidence owners would be unverifiable and must be rejected
    at define-exit (route them to backlog or rewrite them as
    controller/test-measurable criteria).
    """
    contract = _load_yaml_object(Path(contract_path), context="Success criteria contract")
    for criterion in contract.get("success_criteria") or []:
        if not isinstance(criterion, dict):
            continue
        criterion_id = criterion.get("id", "<unknown>")
        owner = criterion.get("evidence_owner")
        if owner in SURFACE_UNSUPPORTED_EVIDENCE_OWNERS:
            raise SuccessCriteriaValidationError(
                f"Success criteria contract criterion {criterion_id} has evidence_owner "
                f"'{owner}', which the current large-story surface cannot convert into "
                "controller ledger evidence. Use a controller- or test-owned criterion, "
                "or route this concern to backlog."
            )
        phase = criterion.get("allowed_phase_to_measure")
        if phase in SURFACE_UNSUPPORTED_MEASUREMENT_PHASES:
            raise SuccessCriteriaValidationError(
                f"Success criteria contract criterion {criterion_id} requires "
                f"allowed_phase_to_measure '{phase}', but terminal-review is not "
                "implemented on the current large-story surface. Use an "
                "implementation-measurable criterion or route this concern to backlog."
            )


def _validate_criteria(contract: dict[str, Any]) -> None:
    criteria = _require_non_empty_list(
        contract,
        "success_criteria",
        context="Success criteria contract",
    )
    outcome_ids = {
        outcome["id"]
        for outcome in contract["expected_outcomes"]
        if isinstance(outcome, dict) and isinstance(outcome.get("id"), str)
    }
    seen: set[str] = set()
    required_fields = (
        "id",
        "outcome_id",
        "statement",
        "binary_predicate",
        "measurement_type",
        "measurement_procedure",
        "evidence_artifact",
        "evidence_owner",
        "pass_condition",
        "fail_condition",
        "allowed_phase_to_measure",
        "amendment_policy",
        "backlog_routing",
    )
    # Report all compound-predicate criteria at once — fixing them one refreeze
    # at a time was a recurring source of churn.
    compound = [
        str(c.get("id") or f"index {i}")
        for i, c in enumerate(criteria)
        if isinstance(c, dict) and _has_multiple_outcomes(c)
    ]
    if compound:
        raise SuccessCriteriaValidationError(
            "Success criteria contract criteria have multiple outcomes "
            f"(split each into one observable behavior): {', '.join(compound)}"
        )

    for index, criterion in enumerate(criteria):
        context = f"Success criteria contract success_criteria[{index}]"
        if not isinstance(criterion, dict):
            raise SuccessCriteriaValidationError(f"{context} must be an object")
        for field in required_fields:
            if _blank(criterion.get(field)):
                criterion_id = str(criterion.get("id") or f"index {index}")
                raise SuccessCriteriaValidationError(
                    f"Success criteria contract criterion {criterion_id} is missing {field}"
                )
        criterion_id = str(criterion["id"])
        if not re.match(r"^SC-[0-9]{3,}$", criterion_id):
            raise SuccessCriteriaValidationError(
                f"Success criteria contract criterion id is invalid: {criterion_id}"
            )
        if criterion_id in seen:
            raise SuccessCriteriaValidationError(
                f"Success criteria contract duplicate criterion id: {criterion_id}"
            )
        seen.add(criterion_id)
        if criterion["outcome_id"] not in outcome_ids:
            raise SuccessCriteriaValidationError(
                f"Success criteria contract criterion {criterion_id} maps to undeclared outcome"
            )
        if criterion["measurement_type"] not in VALID_MEASUREMENT_TYPES:
            raise SuccessCriteriaValidationError(
                f"Success criteria contract criterion {criterion_id} has invalid measurement_type"
            )
        if criterion["measurement_type"] == "command":
            _validate_measurement_command(criterion_id, criterion)
        if criterion["evidence_owner"] not in VALID_EVIDENCE_OWNERS:
            raise SuccessCriteriaValidationError(
                f"Success criteria contract criterion {criterion_id} has invalid evidence_owner"
            )
        if criterion["allowed_phase_to_measure"] not in VALID_MEASUREMENT_PHASES:
            raise SuccessCriteriaValidationError(
                f"Success criteria contract criterion {criterion_id} has invalid allowed_phase_to_measure"
            )
        if criterion["amendment_policy"] != "human_approved_only":
            raise SuccessCriteriaValidationError(
                f"Success criteria contract criterion {criterion_id} has invalid amendment_policy"
            )
        if str(criterion["pass_condition"]).strip() == str(criterion["fail_condition"]).strip():
            raise SuccessCriteriaValidationError(
                f"Success criteria contract criterion {criterion_id} pass/fail conditions must differ"
            )
        if _has_vague_unmeasured_language(criterion):
            raise SuccessCriteriaValidationError(
                f"Success criteria contract criterion {criterion_id} is not objectively measurable"
            )
        if _human_judgment_without_predicate(criterion):
            raise SuccessCriteriaValidationError(
                f"Success criteria contract criterion {criterion_id} uses human judgment without a binary predicate"
            )


def _validate_measurement_command(criterion_id: str, criterion: dict[str, Any]) -> None:
    command = criterion.get("measurement_command")
    if not isinstance(command, str) or not command.strip():
        raise SuccessCriteriaValidationError(
            f"Success criteria contract criterion {criterion_id} is missing measurement_command "
            "(a command-type criterion needs a real shell command the controller runs at VERIFY)"
        )
    if "placeholder" in command.lower():
        raise SuccessCriteriaValidationError(
            f"Success criteria contract criterion {criterion_id} measurement_command is still a "
            "placeholder; replace it with a real command"
        )
    timeout = criterion.get("measurement_timeout_seconds")
    if timeout is not None and (
        isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0
    ):
        raise SuccessCriteriaValidationError(
            f"Success criteria contract criterion {criterion_id} measurement_timeout_seconds "
            "must be a positive number"
        )


def _has_multiple_outcomes(criterion: dict[str, Any]) -> bool:
    text = f"{criterion.get('statement', '')} {criterion.get('binary_predicate', '')}".lower()
    if any(token in text for token in ("all of", "every ", "both ")):
        return False
    return bool(re.search(r"\b(and|also)\b", text))


def _has_vague_unmeasured_language(criterion: dict[str, Any]) -> bool:
    text = " ".join(
        str(criterion.get(field, ""))
        for field in ("statement", "binary_predicate", "pass_condition", "fail_condition")
    ).lower()
    words = set(re.findall(r"[a-z][a-z-]*", text))
    if not words.intersection(VAGUE_TERMS):
        return False
    measurement = " ".join(
        str(criterion.get(field, ""))
        for field in (
            "binary_predicate",
            "measurement_procedure",
            "pass_condition",
            "fail_condition",
        )
    ).lower()
    return not any(signal in measurement for signal in OBJECTIVE_SIGNALS)


def _human_judgment_without_predicate(criterion: dict[str, Any]) -> bool:
    if criterion.get("measurement_type") != "human_terminal_approval":
        return False
    measurement = " ".join(
        str(criterion.get(field, ""))
        for field in (
            "binary_predicate",
            "measurement_procedure",
            "pass_condition",
            "fail_condition",
        )
    ).lower()
    weak_patterns = (
        "human approves",
        "reviewer approved",
        "reviewer approves",
        "looks good",
        "acceptable",
        "satisfactory",
    )
    if any(pattern in measurement for pattern in weak_patterns):
        return True
    return not any(signal in measurement for signal in OBJECTIVE_SIGNALS)


def _ledger_entries(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    entries = ledger.get("criteria")
    if entries is None:
        entries = ledger.get("criterion_results")
    if not isinstance(entries, list) or not entries:
        raise SuccessCriteriaValidationError(
            "Success criteria ledger criteria must be a non-empty list"
        )
    if not all(isinstance(entry, dict) for entry in entries):
        raise SuccessCriteriaValidationError(
            "Success criteria ledger criteria must contain objects"
        )
    return entries


def _entry_status(entry: dict[str, Any], *, context: str) -> str:
    raw = entry.get("status", entry.get("result", entry.get("disposition")))
    if not isinstance(raw, str) or not raw.strip():
        raise SuccessCriteriaValidationError(f"{context} is missing status")
    return raw.strip().lower()


def _entry_evidence_is_fresh(entry: dict[str, Any]) -> bool:
    if entry.get("evidence_fresh") is True:
        return True
    if entry.get("evidence_stale") is True:
        return False
    freshness = entry.get("evidence_freshness")
    if isinstance(freshness, str) and freshness.strip().lower() in FRESHNESS_STATUSES:
        return True
    return False


def _load_yaml_object(path: str | Path, *, context: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SuccessCriteriaValidationError(f"{context} not found: {path}") from None
    except yaml.YAMLError as exc:
        raise SuccessCriteriaValidationError(f"{context} is not valid YAML: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SuccessCriteriaValidationError(f"{context} must be a YAML object")
    return data


def _load_json_object(path: str | Path, *, context: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SuccessCriteriaValidationError(f"{context} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SuccessCriteriaValidationError(f"{context} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SuccessCriteriaValidationError(f"{context} must be a JSON object")
    return data


def _require_object(data: dict[str, Any], field: str, *, context: str) -> dict[str, Any]:
    value = data.get(field)
    if not isinstance(value, dict):
        raise SuccessCriteriaValidationError(f"{context} {field} must be an object")
    return value


def _require_non_empty_list(data: dict[str, Any], field: str, *, context: str) -> list[Any]:
    value = data.get(field)
    if not isinstance(value, list) or not value:
        raise SuccessCriteriaValidationError(f"{context} {field} must be a non-empty list")
    return value


def _require_non_empty_string(data: dict[str, Any], field: str, *, context: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SuccessCriteriaValidationError(f"{context} is missing {field}")
    return value.strip()


def _parse_timestamp(value: str, *, field: str) -> datetime.datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SuccessCriteriaValidationError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise SuccessCriteriaValidationError(f"{field} must include timezone")
    return parsed.astimezone(datetime.timezone.utc)


def _normalize_hash(value: str) -> str:
    raw = value.strip().lower()
    if raw.startswith("sha256:"):
        digest = raw.removeprefix("sha256:")
    else:
        digest = raw
    if not re.match(r"^[0-9a-f]{64}$", digest):
        raise SuccessCriteriaValidationError(f"Invalid sha256 hash: {value}")
    return "sha256:" + digest


def _blank(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _workflow_recovery_hint(stage: str, error: str) -> str:
    if stage == "draft":
        return "Draft validation failed; continue editing until the contract validates before freeze."
    if stage == "define-exit":
        return "Do not leave Define. Fix and refreeze the success criteria contract before planning."
    if "ledger" in error.lower():
        return "Do not claim completion. Regenerate or correct success-criteria-ledger.json against the frozen contract."
    return "Do not claim completion. Re-run validation after correcting success-criteria artifacts."


def find_backlog_file(
    project: Path, item_id: str, *, exclude_done: bool = False,
) -> Path | None:
    """Search product backlog directories for a file matching {item_id}-*.md.

    When *exclude_done* is True the ``done/`` subdirectory is skipped so that
    completed items cannot be used to re-initialize workflows or contracts.
    """
    product_bases: list[Path] = []
    privacy_path = project / ".sweetclaude" / "artifact-privacy.yaml"
    if privacy_path.exists():
        try:
            data = yaml.safe_load(privacy_path.read_text(encoding="utf-8")) or {}
            base = (data.get("categories") or {}).get("product", {}).get("base_path", "")
            if base:
                product_bases.append(project / base.rstrip("/"))
        except yaml.YAMLError:
            pass
    product_bases.extend([
        project / "docs" / "product",
        project / ".sweetclaude" / "product",
    ])
    subdirs = ("backlog", "backlog/archived") if exclude_done else ("backlog", "done", "backlog/archived")
    for base in product_bases:
        for subdir in subdirs:
            search_dir = base / subdir
            if search_dir.is_dir():
                matches = list(search_dir.glob(f"{item_id}-*.md"))
                if matches:
                    return matches[0]
    return None


def record_workflow_closeout(
    project: Path,
    workflow_id: str,
    *,
    title: str | None = None,
    outcome: str = "done",
    _legacy_result: str | None = None,
) -> None:
    """Write the full deterministic close-out state for a completed workflow.

    Writes phase.yaml, sweetclaude.yaml, and the item file status. Guard:
    if active_work_item / work.active in EITHER state file points at a DIFFERENT
    workflow, the close-out is blocked — no record is advanced in either file
    and the item file is left untouched. When not blocked, both files are
    advanced identically (whether their active pointer was None or matching), so
    the two files can never disagree about the last completed item.
    """
    import datetime as _dt

    # Defensive: this library may be imported by a caller that has not put the
    # sibling scripts/ dir on sys.path. The status module lives alongside us.
    _scripts_dir = str(Path(__file__).resolve().parent)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    import status as _status_mod

    project = Path(project)

    # A successful completion is "complete" in workflow vocabulary; map the
    # done item-status outcome back to it so controller and orchestrator paths
    # record the same value.
    result_val = (
        _legacy_result
        if _legacy_result is not None
        else ("complete" if outcome == "done" else outcome)
    )

    # --- Resolve title (fall back to backlog file frontmatter, then workflow_id) ---
    item_file = find_backlog_file(project, workflow_id)
    resolved_title = title
    if resolved_title is None and item_file is not None:
        try:
            text = item_file.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            if len(parts) >= 3:
                fm = yaml.safe_load(parts[1]) or {}
                resolved_title = fm.get("title") or None
        except Exception:
            pass
    if resolved_title is None:
        resolved_title = workflow_id

    # --- Load both state files up front so the guard sees the whole picture ---
    phase_path = project / ".sweetclaude" / "state" / "phase.yaml"
    phase_data: dict[str, Any] = {}
    if phase_path.exists():
        try:
            loaded = yaml.safe_load(phase_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            loaded = {}
        if isinstance(loaded, dict):
            phase_data = loaded

    sc_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    sc_data: dict[str, Any] = {}
    if sc_path.exists():
        try:
            loaded = yaml.safe_load(sc_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            loaded = {}
        if isinstance(loaded, dict):
            sc_data = loaded

    work = sc_data.setdefault("work", {})
    if not isinstance(work, dict):
        work = {}
        sc_data["work"] = work

    # --- Unified no-clobber guard: blocked if EITHER file's active points
    #     at a different workflow. Otherwise advance both identically. ---
    def _points_elsewhere(active: Any) -> bool:
        return isinstance(active, dict) and active.get("id") not in (None, workflow_id)

    blocked = _points_elsewhere(phase_data.get("active_work_item")) or _points_elsewhere(
        work.get("active")
    )
    if blocked:
        return

    # --- phase.yaml ---
    if phase_path.exists():
        phase_data["active_work_item"] = None
        phase_data["last_work_item_id"] = workflow_id
        phase_path.write_text(yaml.safe_dump(phase_data, sort_keys=False), encoding="utf-8")

    # --- sweetclaude.yaml ---
    work["active"] = None
    work["last_item_id"] = workflow_id

    history = sc_data.setdefault("work_history", [])
    if not isinstance(history, list):
        history = []
        sc_data["work_history"] = history

    already = any(
        isinstance(h, dict) and h.get("id") == workflow_id and h.get("outcome") == outcome
        for h in history
    )
    if not already:
        history.append({
            "id": workflow_id,
            "completed": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "outcome": outcome,
            "title": resolved_title,
            "result": result_val,
        })

    sc_path.parent.mkdir(parents=True, exist_ok=True)
    sc_path.write_text(yaml.safe_dump(sc_data, sort_keys=False), encoding="utf-8")

    # --- item file: only mark terminal for an actual completion ---
    if item_file is None or outcome != "done":
        return
    current_status = None
    try:
        raw = item_file.read_text(encoding="utf-8-sig")
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            current_status = (yaml.safe_load(parts[1]) or {}).get("status")
    except Exception:
        current_status = None
    if current_status in getattr(_status_mod, "TERMINAL_STATUSES", set()):
        return  # already terminal — nothing to do
    # The item-file status is a best-effort secondary write: a malformed or
    # legacy item file must not crash close-out (the state-file writes above
    # are the primary job). But failures are surfaced, not silently swallowed.
    try:
        _status_mod.set_terminal(
            str(item_file),
            "done",
            "controller",
            project_dir=str(project),
            _from_sync=True,
        )
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(
            f"WARNING: close-out could not set {item_file} to done: {exc}",
            file=sys.stderr,
        )


def _active_workflow_for_different_story(project: Path, story_id: str) -> bool:
    """True if an active workflow exists for a DIFFERENT story than story_id."""
    workflows_dir = project / ".sweetclaude" / "state" / "workflows"
    if not workflows_dir.exists():
        return False
    for candidate in workflows_dir.glob("*.yaml"):
        try:
            state = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if (
            isinstance(state, dict)
            and state.get("requires_success_criteria_contract")
            and state.get("status") != "complete"
            and state.get("workflow_id") != story_id
        ):
            return True
    return False


VALID_WORKFLOW_TYPES = ("large-story", "small-story")


def _skeleton_criterion(
    story_id: str, index: int, workflow_type: str = "large-story"
) -> dict[str, Any]:
    criterion_id = f"SC-{index:03d}"
    return {
        "id": criterion_id,
        "outcome_id": "OUTCOME-001",
        "statement": f"PLACEHOLDER criterion {index}: replace with one observable behavior.",
        "binary_predicate": f"placeholder measurement command {index} exits with code 0",
        "measurement_type": "command",
        "measurement_command": f"echo PLACEHOLDER measurement command {index}; exit 1",
        "measurement_procedure": f"Run the criterion {index} measurement command; record the exit code.",
        "evidence_artifact": f".sweetclaude/reports/{workflow_type}/{story_id}/evidence/{criterion_id}.json",
        "evidence_owner": "controller",
        "pass_condition": "Exit code equals 0",
        "fail_condition": "Exit code differs from 0",
        "allowed_phase_to_measure": "implementation",
        "amendment_policy": "human_approved_only",
        "backlog_routing": "Route new concerns to backlog; this criterion is frozen.",
    }


def init_contract(
    *,
    project_dir: str | Path = ".",
    story_id: str,
    title: str = "",
    objective: str = "",
    criteria_count: int = 3,
    workflow_type: str = "large-story",
    force: bool = False,
) -> dict[str, Any]:
    """Write a schema-valid success criteria contract skeleton.

    Evidence paths, enum fields, and structure are pre-filled so DEFINE only
    has to replace the placeholder statements/predicates, then run
    freeze-contract. Refuses to overwrite while a workflow is active —
    post-freeze amendment is human-gated at the file layer.
    """
    if workflow_type not in VALID_WORKFLOW_TYPES:
        return {
            "ok": False,
            "error": (
                f"workflow_type must be one of {VALID_WORKFLOW_TYPES}; got {workflow_type!r}."
            ),
        }
    project = Path(project_dir).expanduser().resolve(strict=False)
    contract_path = project / DEFAULT_CONTRACT_PATH
    if _active_workflow_for_different_story(project, story_id):
        return {
            "ok": False,
            "error": (
                "init-contract is blocked: an active workflow exists for a different story. "
                "Frozen contract amendment is human-gated; do not regenerate the "
                "contract while another story's workflow is active."
            ),
        }
    if find_backlog_file(project, story_id, exclude_done=True) is None:
        return {
            "ok": False,
            "error": (
                f"init-contract is blocked: no backlog file found for {story_id}. "
                "A backlog item must exist before a success criteria contract can "
                "be scaffolded. Create the backlog file first."
            ),
        }
    if contract_path.exists() and contract_path.stat().st_size > 0 and not force:
        return {
            "ok": False,
            "error": f"Contract already exists at {DEFAULT_CONTRACT_PATH}; pass --force to overwrite the draft.",
        }
    if criteria_count < 1:
        return {"ok": False, "error": "criteria_count must be at least 1."}

    skeleton = {
        "story_id": story_id,
        "story_title": title or f"PLACEHOLDER title for {story_id}",
        "story_objective": objective or (
            "PLACEHOLDER objective: replace with what this story must achieve, "
            "stated in one or two sentences."
        ),
        "expected_outcomes": [
            {
                "id": "OUTCOME-001",
                "statement": "PLACEHOLDER outcome: replace with the observable end state.",
            }
        ],
        "non_goals": [
            {"id": "NONGOAL-001", "statement": "PLACEHOLDER non-goal: replace with one exclusion."}
        ],
        "success_criteria": [
            _skeleton_criterion(story_id, index, workflow_type)
            for index in range(1, criteria_count + 1)
        ],
        "contract_freeze": {
            "frozen_at": "",
            "frozen_by": "",
            "contract_hash": "",
        },
    }
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(yaml.safe_dump(skeleton, sort_keys=False), encoding="utf-8")
    return {
        "ok": True,
        "contract_path": str(DEFAULT_CONTRACT_PATH),
        "story_id": story_id,
        "criterion_ids": [criterion["id"] for criterion in skeleton["success_criteria"]],
        "next_step": (
            "Replace every PLACEHOLDER, then run freeze-contract, then "
            "validate-workflow --stage define-exit."
        ),
    }


def freeze_contract(
    *,
    project_dir: str | Path = ".",
    contract_path: str | Path | None = None,
    frozen_by: str = "user",
) -> dict[str, Any]:
    """Compute and write the freeze hash for the current contract content.

    Safe to run at any time: it only certifies existing content. Content
    changes are what is gated (human-approved file edits).
    """
    project = Path(project_dir).expanduser().resolve(strict=False)
    target = Path(contract_path) if contract_path else Path(DEFAULT_CONTRACT_PATH)
    resolved = target if target.is_absolute() else project / target
    if not resolved.exists():
        return {"ok": False, "error": f"Contract not found: {target}"}
    contract = _load_yaml_object(resolved, context="Success criteria contract")
    freeze = contract.get("contract_freeze")
    if not isinstance(freeze, dict):
        freeze = {}
    freeze["frozen_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    freeze["frozen_by"] = frozen_by
    contract["contract_freeze"] = freeze
    contract_hash = compute_success_criteria_contract_hash(contract)
    freeze["contract_hash"] = contract_hash
    resolved.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    return {
        "ok": True,
        "contract_path": str(target),
        "contract_hash": contract_hash,
        "frozen_at": freeze["frozen_at"],
        "frozen_by": frozen_by,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_contract = sub.add_parser("validate-contract")
    p_contract.add_argument("--contract", required=True)

    p_ledger = sub.add_parser("validate-ledger")
    p_ledger.add_argument("--contract", required=True)
    p_ledger.add_argument("--ledger", required=True)

    p_workflow = sub.add_parser("validate-workflow")
    p_workflow.add_argument("--project-dir", default=".")
    p_workflow.add_argument("--workflow-id")
    p_workflow.add_argument("--stage", required=True, choices=sorted(WORKFLOW_STAGES))
    p_workflow.add_argument("--contract")
    p_workflow.add_argument("--ledger")

    p_init = sub.add_parser("init-contract")
    p_init.add_argument("--project-dir", default=".")
    p_init.add_argument("--story-id", required=True)
    p_init.add_argument("--title", default="")
    p_init.add_argument("--objective", default="")
    p_init.add_argument("--criteria", type=int, default=3)
    p_init.add_argument(
        "--workflow-type",
        default="large-story",
        choices=sorted(VALID_WORKFLOW_TYPES),
    )
    p_init.add_argument("--force", action="store_true")

    p_freeze = sub.add_parser("freeze-contract")
    p_freeze.add_argument("--project-dir", default=".")
    p_freeze.add_argument("--contract")
    p_freeze.add_argument("--frozen-by", default="user")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "validate-contract":
            result = validate_success_criteria_contract(args.contract)
        elif args.cmd == "validate-ledger":
            result = validate_success_criteria_ledger(
                contract_path=args.contract,
                ledger_path=args.ledger,
            )
        elif args.cmd == "validate-workflow":
            result = validate_success_criteria_workflow(
                project_dir=args.project_dir,
                workflow_id=args.workflow_id,
                stage=args.stage,
                contract_path=args.contract,
                ledger_path=args.ledger,
            )
        elif args.cmd == "init-contract":
            result = init_contract(
                project_dir=args.project_dir,
                story_id=args.story_id,
                title=args.title,
                objective=args.objective,
                criteria_count=args.criteria,
                workflow_type=args.workflow_type,
                force=args.force,
            )
        elif args.cmd == "freeze-contract":
            result = freeze_contract(
                project_dir=args.project_dir,
                contract_path=args.contract,
                frozen_by=args.frozen_by,
            )
        else:
            raise SuccessCriteriaValidationError(f"Unknown command: {args.cmd}")
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("ok") or not result.get("blocking", True) else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
