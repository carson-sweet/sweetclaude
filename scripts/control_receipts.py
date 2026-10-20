#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""MS-007 control receipt helpers and active artifact lint."""
from __future__ import annotations

import argparse
import hashlib
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

from maintenance.capability_manifest import load_manifest


PASS_RESULTS = {"pass", "passed", "ok", "success", "judgment_pass"}
CONTROL_LINT_RECEIPT_TYPE = "control-lint"
SOURCE_DISCOVERY_RECEIPT_TYPE = "source-discovery"
SOURCE_PRECEDENCE_RECEIPT_TYPE = "source-precedence"
CONTRACT_TEST_RECEIPT_TYPE = "contract-test"
INVARIANT_TEST_RECEIPT_TYPE = "invariant-test"
HIGH_CRITICAL_EXEMPTION_RECEIPT_TYPE = "high-critical-exemption"
OBJECTIVE_CRITERIA_RECEIPT_TYPE = "objective-criteria"
PHASE_EXIT_RECEIPT_TYPE = "phase-exit"
FINDING_DISPOSITION_RECEIPT_TYPE = "finding-disposition"
BACKLOG_PROMOTION_RECEIPT_TYPE = "backlog-promotion"
CHANGE_CONTEXT_RECEIPT_TYPE = "change-context"
RELEASE_IDENTITY_RECEIPT_TYPE = "release-identity"
DOCS_CAPABILITY_RECEIPT_TYPE = "docs-capability"
PUBLIC_DISTRIBUTION_RECEIPT_TYPE = "public-distribution"
RELEASE_ARTIFACT_BUILD_RECEIPT_TYPE = "release-artifact-build"
UPDATE_DISCOVERY_EXECUTION_RECEIPT_TYPE = "update-discovery-execution"
INSTALLED_SMOKE_RECEIPT_TYPE = "installed-smoke"
PUBLIC_DISTRIBUTION_INVENTORY_RECEIPT_TYPE = "public-distribution-inventory"
CONTROL_REF_RE = re.compile(r"\bCTL-\d{3}\b")
IMPLEMENTATION_RANGE_RE = re.compile(
    r"\b(?:CTL|T)-\d{3}[A-Z]?\s+through\s+(?:CTL|T)-\d{3}[A-Z]?\b"
    r"|\bthrough\s+(?:CTL|T)-\d{3}[A-Z]?\b"
)
CONTROL_DEFINITION_RE = re.compile(r"^\|\s*(CTL-\d{3})\b")
PATH_CONTEXT_FIELDS = {
    "cwd",
    "repo_root",
    "install_path",
    "installed_path",
    "artifact_path",
    "build_receipt_path",
    "execution_receipt_path",
    "installed_manifest_path",
    "installed_smoke_receipt_path",
    "inventory_receipt_path",
    "release_artifact_path",
    "smoke_output_path",
    "stderr_path",
    "stdout_path",
}
HIGH_CRITICAL_SEVERITIES = {"high", "critical"}
DISPOSITION_STATUSES = {"resolved", "backlogged", "accepted"}
DISCOVERY_TYPES = {
    "bug",
    "failing_test",
    "unsafe_route",
    "unsupported_recommendation",
    "surprising_mutation",
}
CHANGE_CONTEXT_DECISIONS = {"proceed", "rebase", "wait", "rescope"}
DOCS_CAPABILITY_CLAIM_STATUSES = {"proven", "future", "deferred"}
SEMVER_TAG_RE = re.compile(r"^v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?P<prerelease>-[A-Za-z0-9.-]+)?$")


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_timestamp(value: str, *, field: str) -> datetime.datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return parsed.astimezone(datetime.timezone.utc)


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return slug or "receipt"


def hash_file(path: str | Path) -> str:
    """Return the sha256 hex digest for a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"Control receipt not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Control receipt is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Control receipt must be a JSON object")
    return data


def _require_non_empty_string(data: dict[str, Any], field: str, *, context: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} is missing {field}")
    return value.strip()


def _require_non_empty_list(data: dict[str, Any], field: str, *, context: str) -> list[Any]:
    value = data.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{context} {field} must be a non-empty list")
    return value


def _require_list_of_strings(data: dict[str, Any], field: str, *, context: str) -> list[str]:
    values = _require_non_empty_list(data, field, context=context)
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ValueError(f"{context} {field} must contain non-empty strings")
    return [str(value).strip() for value in values]


def _require_list_of_objects(data: dict[str, Any], field: str, *, context: str) -> list[dict[str, Any]]:
    values = _require_non_empty_list(data, field, context=context)
    if not all(isinstance(value, dict) for value in values):
        raise ValueError(f"{context} {field} must contain objects")
    return values


def _normalize_context_value(field: str, value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if field in PATH_CONTEXT_FIELDS:
        return str(Path(text).expanduser().resolve(strict=False))
    return text


def _defined_controls(controls_map_path: str | Path) -> set[str]:
    controls_map = Path(controls_map_path)
    defined: set[str] = set()
    for line in controls_map.read_text(encoding="utf-8").splitlines():
        match = CONTROL_DEFINITION_RE.match(line)
        if match:
            defined.add(match.group(1))
    if not defined:
        raise ValueError(f"No control definitions found in {controls_map}")
    return defined


def lint_control_artifacts(
    *,
    controls_map_path: str | Path,
    artifact_paths: list[str | Path],
) -> None:
    """Fail on undefined CTL references or implementation-significant ranges."""
    defined = _defined_controls(controls_map_path)
    violations: list[str] = []

    for artifact_path in artifact_paths:
        artifact = Path(artifact_path)
        text = artifact.read_text(encoding="utf-8")

        for match in IMPLEMENTATION_RANGE_RE.finditer(text):
            violations.append(
                f"{artifact}: implementation-significant numeric range "
                f"{match.group(0)!r}"
            )

        for control in sorted(set(CONTROL_REF_RE.findall(text))):
            if control not in defined:
                violations.append(f"{artifact}: undefined control reference {control}")

    if violations:
        raise ValueError("; ".join(violations))


def _artifact_entry(repo_root: Path, artifact_path: str | Path) -> dict[str, str]:
    path = Path(artifact_path).resolve(strict=False)
    try:
        display_path = str(path.relative_to(repo_root))
    except ValueError:
        display_path = str(path)
    return {
        "path": display_path,
        "sha256": hash_file(path),
    }


def write_control_lint_receipt(
    project_dir: Path,
    *,
    subject_id: str,
    branch: str,
    commit: str,
    controls_map_path: str | Path,
    artifact_paths: list[str | Path],
) -> Path:
    """Run control-artifact lint and write a release-bound receipt."""
    project_dir = project_dir.resolve()
    controls_map = Path(controls_map_path)
    artifacts = [Path(path) for path in artifact_paths]

    lint_control_artifacts(
        controls_map_path=controls_map,
        artifact_paths=artifacts,
    )

    receipt = {
        "schema_version": 2,
        "receipt_type": CONTROL_LINT_RECEIPT_TYPE,
        "receipt_id": f"{_slug(subject_id)}-control-lint",
        "subject_id": subject_id,
        "generated_at": _now(),
        "command_or_workflow_step": "control-artifact-lint",
        "cwd": str(project_dir),
        "repo_root": str(project_dir),
        "branch": branch,
        "commit": commit,
        "result": "pass",
        "input_artifacts": [
            _artifact_entry(project_dir, controls_map),
            *[_artifact_entry(project_dir, artifact) for artifact in artifacts],
        ],
    }
    out_dir = project_dir / ".sweetclaude" / "state" / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{_slug(subject_id)}-control-lint.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    validate_control_lint_receipt(
        path,
        subject_id=subject_id,
        expected_context={
            "repo_root": str(project_dir),
            "branch": branch,
            "commit": commit,
        },
    )
    return path


def validate_control_receipt_context(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
    verify_artifact_hashes: bool = False,
) -> dict[str, Any]:
    """Validate a v2-style control receipt against context and artifact hashes.

    This helper is intentionally separate from the existing v1 evidence receipt
    validator so current completion/release receipts remain backward-compatible.
    """
    receipt = _load_json(receipt_path)

    if receipt.get("schema_version") != 2:
        raise ValueError("Control receipt schema_version must be 2")

    result = str(receipt.get("result", "")).lower()
    if result not in PASS_RESULTS:
        raise ValueError(f"Control receipt result must pass, got {result!r}")

    for field in ("receipt_type", "receipt_id", "generated_at"):
        if not str(receipt.get(field, "")).strip():
            raise ValueError(f"Control receipt is missing {field}")

    if expected_context:
        for field, expected in expected_context.items():
            actual = receipt.get(field)
            if actual is None:
                raise ValueError(f"Control receipt is missing context field {field}")
            if _normalize_context_value(field, actual) != _normalize_context_value(
                field, expected
            ):
                raise ValueError(
                    f"{field} mismatch: expected {expected!r}, got {actual!r}"
                )

    if verify_artifact_hashes:
        repo_root = Path(str(receipt.get("repo_root", ""))).expanduser()
        if not str(repo_root).strip():
            raise ValueError("Control receipt is missing repo_root")
        artifacts = receipt.get("input_artifacts")
        if not isinstance(artifacts, list):
            raise ValueError("Control receipt input_artifacts must be a list")

        for index, artifact in enumerate(artifacts, start=1):
            if not isinstance(artifact, dict):
                raise ValueError(
                    f"Control receipt input_artifacts #{index} must be an object"
                )
            artifact_path = artifact.get("path")
            expected_hash = artifact.get("sha256")
            if not artifact_path or not expected_hash:
                raise ValueError(
                    f"Control receipt input_artifacts #{index} needs path and sha256"
                )
            path = Path(str(artifact_path))
            if not path.is_absolute():
                path = repo_root / path
            actual_hash = hash_file(path)
            if actual_hash != expected_hash:
                raise ValueError(
                    f"file hash mismatch for {artifact_path}: "
                    f"expected {expected_hash}, got {actual_hash}"
                )

    return receipt


def validate_control_lint_receipt(
    receipt_path: str | Path,
    *,
    subject_id: str,
    expected_context: dict[str, Any],
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=True,
    )
    if receipt.get("receipt_type") != CONTROL_LINT_RECEIPT_TYPE:
        raise ValueError(
            "Control lint receipt type mismatch: "
            f"expected {CONTROL_LINT_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    actual_subject = receipt.get("subject_id")
    if actual_subject != subject_id:
        raise ValueError(
            f"Control lint receipt subject mismatch: expected {subject_id}, got {actual_subject}"
        )
    return receipt


def validate_source_discovery_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
    required_source_classes: set[str] | None = None,
) -> dict[str, Any]:
    """Validate source discovery evidence for high-stakes work."""
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != SOURCE_DISCOVERY_RECEIPT_TYPE:
        raise ValueError(
            "Source discovery receipt type mismatch: "
            f"expected {SOURCE_DISCOVERY_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )

    _require_list_of_strings(receipt, "searched_locations", context="Source discovery receipt")
    governing_sources = _require_list_of_objects(
        receipt,
        "governing_sources",
        context="Source discovery receipt",
    )
    _require_non_empty_string(receipt, "confidence", context="Source discovery receipt")
    if "help_needed" not in receipt:
        raise ValueError("Source discovery receipt is missing help_needed")
    if "excluded_likely_sources" not in receipt or not isinstance(
        receipt.get("excluded_likely_sources"), list
    ):
        raise ValueError("Source discovery receipt excluded_likely_sources must be a list")

    found_classes: set[str] = set()
    for index, source in enumerate(governing_sources, start=1):
        context = f"Source discovery receipt governing_sources #{index}"
        _require_non_empty_string(source, "path", context=context)
        _require_non_empty_string(source, "summary", context=context)
        source_class = _require_non_empty_string(source, "source_class", context=context)
        found_classes.add(source_class)

    missing = sorted((required_source_classes or set()) - found_classes)
    if missing:
        raise ValueError(
            "Source discovery receipt is missing governing source classes: "
            + ", ".join(missing)
        )

    return receipt


def validate_source_precedence_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate evidence that governing sources outrank drifted local behavior."""
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != SOURCE_PRECEDENCE_RECEIPT_TYPE:
        raise ValueError(
            "Source precedence receipt type mismatch: "
            f"expected {SOURCE_PRECEDENCE_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )

    checks = _require_list_of_objects(
        receipt,
        "precedence_checks",
        context="Source precedence receipt",
    )
    for index, check in enumerate(checks, start=1):
        context = f"Source precedence receipt precedence_checks #{index}"
        governing_type = _require_non_empty_string(check, "governing_source_type", context=context)
        if governing_type not in {"ADR", "contract", "spec"}:
            raise ValueError(
                f"{context} governing_source_type must be ADR, contract, or spec"
            )
        _require_non_empty_string(check, "governing_source", context=context)
        _require_non_empty_string(check, "observed_behavior", context=context)
        decision = _require_non_empty_string(check, "decision", context=context)
        if decision not in {"follow_governing_source", "spec_amendment_required"}:
            raise ValueError(
                f"{context} decision must follow governing source or require spec amendment"
            )
        if check.get("implementation_source_treated_as_authority") is True:
            raise ValueError(
                f"{context} treats implementation or shallow docs as authority"
            )

    return receipt


def validate_executable_test_receipt(
    receipt_path: str | Path,
    *,
    receipt_type: str,
    expected_context: dict[str, Any] | None = None,
    verify_test_file: bool = False,
) -> dict[str, Any]:
    """Validate contract/invariant evidence that names executable test proof."""
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != receipt_type:
        raise ValueError(
            f"Executable evidence receipt type mismatch: expected {receipt_type}, "
            f"got {receipt.get('receipt_type')}"
        )

    test_file = _require_non_empty_string(receipt, "test_file", context="Executable evidence receipt")
    _require_non_empty_string(receipt, "test_command", context="Executable evidence receipt")
    _require_non_empty_string(receipt, "expected_assertion", context="Executable evidence receipt")
    _require_non_empty_string(receipt, "commit", context="Executable evidence receipt")
    last_run = _require_non_empty_string(receipt, "last_run_result", context="Executable evidence receipt")
    if last_run.lower() not in PASS_RESULTS:
        raise ValueError(
            f"Executable evidence receipt last_run_result must pass, got {last_run!r}"
        )

    if verify_test_file:
        repo_root = Path(str(receipt.get("repo_root", ""))).expanduser()
        if not str(repo_root).strip():
            raise ValueError("Executable evidence receipt is missing repo_root")
        path = Path(test_file)
        if not path.is_absolute():
            path = repo_root / path
        if not path.exists():
            raise ValueError(f"Executable evidence test file not found: {test_file}")

    return receipt


def validate_contract_test_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
    verify_test_file: bool = False,
) -> dict[str, Any]:
    return validate_executable_test_receipt(
        receipt_path,
        receipt_type=CONTRACT_TEST_RECEIPT_TYPE,
        expected_context=expected_context,
        verify_test_file=verify_test_file,
    )


def validate_invariant_test_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
    verify_test_file: bool = False,
) -> dict[str, Any]:
    return validate_executable_test_receipt(
        receipt_path,
        receipt_type=INVARIANT_TEST_RECEIPT_TYPE,
        expected_context=expected_context,
        verify_test_file=verify_test_file,
    )


def validate_high_critical_exemption_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    """Validate a deliberately explicit High/Critical evidence exemption."""
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != HIGH_CRITICAL_EXEMPTION_RECEIPT_TYPE:
        raise ValueError(
            "High/Critical exemption receipt type mismatch: "
            f"expected {HIGH_CRITICAL_EXEMPTION_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )

    for field in (
        "authority",
        "scope",
        "reason",
        "accepted_risk",
        "finding_disposition",
    ):
        _require_non_empty_string(receipt, field, context="High/Critical exemption receipt")

    expires_at = _require_non_empty_string(
        receipt,
        "expires_at",
        context="High/Critical exemption receipt",
    )
    current_time = now or datetime.datetime.now(datetime.timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=datetime.timezone.utc)
    current_time = current_time.astimezone(datetime.timezone.utc)
    if _parse_timestamp(expires_at, field="expires_at") <= current_time:
        raise ValueError("High/Critical exemption receipt is expired")

    severity = _require_non_empty_string(receipt, "severity", context="High/Critical exemption receipt")
    if severity.lower() not in HIGH_CRITICAL_SEVERITIES:
        raise ValueError("High/Critical exemption receipt severity must be High or Critical")

    return receipt


def validate_contract_test_or_exemption(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
    verify_test_file: bool = False,
) -> dict[str, Any]:
    try:
        return validate_contract_test_receipt(
            receipt_path,
            expected_context=expected_context,
            verify_test_file=verify_test_file,
        )
    except ValueError as contract_error:
        try:
            return validate_high_critical_exemption_receipt(
                receipt_path,
                expected_context=expected_context,
            )
        except ValueError as exemption_error:
            raise ValueError(
                "Contract conformance claim requires executable contract test "
                "evidence or a valid High/Critical exemption: "
                f"{contract_error}; {exemption_error}"
            ) from exemption_error


def validate_invariant_test_or_exemption(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
    verify_test_file: bool = False,
) -> dict[str, Any]:
    try:
        return validate_invariant_test_receipt(
            receipt_path,
            expected_context=expected_context,
            verify_test_file=verify_test_file,
        )
    except ValueError as invariant_error:
        try:
            return validate_high_critical_exemption_receipt(
                receipt_path,
                expected_context=expected_context,
            )
        except ValueError as exemption_error:
            raise ValueError(
                "Load-bearing invariant claim requires executable invariant test "
                "evidence or a valid High/Critical exemption: "
                f"{invariant_error}; {exemption_error}"
            ) from exemption_error


def validate_objective_criteria_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != OBJECTIVE_CRITERIA_RECEIPT_TYPE:
        raise ValueError(
            "Objective criteria receipt type mismatch: "
            f"expected {OBJECTIVE_CRITERIA_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    criteria = _require_list_of_objects(
        receipt,
        "criteria",
        context="Objective criteria receipt",
    )
    for index, criterion in enumerate(criteria, start=1):
        context = f"Objective criteria receipt criteria #{index}"
        _require_non_empty_string(criterion, "id", context=context)
        _require_non_empty_string(criterion, "description", context=context)
        _require_non_empty_string(criterion, "evidence_type", context=context)
    return receipt


def validate_phase_exit_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != PHASE_EXIT_RECEIPT_TYPE:
        raise ValueError(
            "Phase exit receipt type mismatch: "
            f"expected {PHASE_EXIT_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    _require_list_of_strings(
        receipt,
        "required_artifacts",
        context="Phase exit receipt",
    )
    checks = _require_list_of_objects(
        receipt,
        "checks",
        context="Phase exit receipt",
    )
    for index, check in enumerate(checks, start=1):
        context = f"Phase exit receipt checks #{index}"
        _require_non_empty_string(check, "name", context=context)
        status = _require_non_empty_string(check, "status", context=context)
        if status.lower() not in PASS_RESULTS:
            raise ValueError(f"{context} status must pass, got {status!r}")
        _require_non_empty_string(check, "evidence", context=context)
    if "findings" not in receipt or not isinstance(receipt.get("findings"), list):
        raise ValueError("Phase exit receipt findings must be a list")
    outcome = _require_non_empty_string(receipt, "outcome", context="Phase exit receipt")
    if outcome.lower() not in PASS_RESULTS:
        raise ValueError(f"Phase exit receipt outcome must pass, got {outcome!r}")
    return receipt


def validate_finding_disposition_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != FINDING_DISPOSITION_RECEIPT_TYPE:
        raise ValueError(
            "Finding disposition receipt type mismatch: "
            f"expected {FINDING_DISPOSITION_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    _require_non_empty_string(receipt, "finding_id", context="Finding disposition receipt")
    severity = _require_non_empty_string(receipt, "severity", context="Finding disposition receipt")
    if severity.lower() not in HIGH_CRITICAL_SEVERITIES:
        raise ValueError("Finding disposition receipt severity must be High or Critical")
    disposition = _require_non_empty_string(
        receipt,
        "disposition_status",
        context="Finding disposition receipt",
    )
    if disposition not in DISPOSITION_STATUSES:
        raise ValueError(
            f"Finding disposition receipt disposition_status must be one of {sorted(DISPOSITION_STATUSES)}"
        )
    for field in ("owner", "evidence", "authority", "rationale"):
        _require_non_empty_string(receipt, field, context="Finding disposition receipt")
    return receipt


def _finding_id(finding: dict[str, Any]) -> str:
    return str(finding.get("id") or finding.get("finding_id") or "").strip()


def _finding_severity(finding: dict[str, Any]) -> str:
    return str(finding.get("severity", "")).strip().lower()


def validate_finding_disposition_gate(
    findings: list[dict[str, Any]],
    *,
    disposition_receipt_paths: list[str | Path],
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dispositions = {
        str(receipt.get("finding_id")): receipt
        for receipt in (
            validate_finding_disposition_receipt(path, expected_context=expected_context)
            for path in disposition_receipt_paths
        )
    }

    missing: list[str] = []
    mismatched: list[str] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        finding_id = _finding_id(finding)
        severity = _finding_severity(finding)
        status = str(finding.get("status", "open")).strip().lower()
        if severity not in HIGH_CRITICAL_SEVERITIES or status in DISPOSITION_STATUSES:
            continue
        if finding_id not in dispositions:
            missing.append(finding_id or "<missing-id>")
            continue
        disposition_severity = str(dispositions[finding_id].get("severity", "")).lower()
        if disposition_severity != severity:
            mismatched.append(
                f"{finding_id or '<missing-id>'}: finding={severity}, "
                f"disposition={disposition_severity}"
            )

    if missing:
        raise ValueError(
            "High/Critical findings need disposition receipts: " + ", ".join(missing)
        )
    if mismatched:
        raise ValueError(
            "Finding disposition severity mismatch: " + ", ".join(mismatched)
        )

    return {"ok": True, "dispositioned_findings": sorted(dispositions)}


def validate_backlog_promotion_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != BACKLOG_PROMOTION_RECEIPT_TYPE:
        raise ValueError(
            "Backlog promotion receipt type mismatch: "
            f"expected {BACKLOG_PROMOTION_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    _require_non_empty_string(receipt, "discovery_id", context="Backlog promotion receipt")
    discovery_type = _require_non_empty_string(
        receipt,
        "discovery_type",
        context="Backlog promotion receipt",
    )
    if discovery_type not in DISCOVERY_TYPES:
        raise ValueError(
            f"Backlog promotion receipt discovery_type must be one of {sorted(DISCOVERY_TYPES)}"
        )
    has_backlog = bool(str(receipt.get("backlog_item_id", "")).strip()) and bool(
        str(receipt.get("backlog_item_path", "")).strip()
    )
    has_no_action = bool(str(receipt.get("no_action_rationale", "")).strip())
    if not has_backlog and not has_no_action:
        raise ValueError(
            "Backlog promotion receipt requires backlog item id/path or no-action rationale"
        )
    if has_no_action:
        if not str(receipt.get("no_action_authority", "")).strip():
            raise ValueError("Backlog promotion receipt no-action authority is required")
        if not str(receipt.get("no_action_scope", "")).strip():
            raise ValueError("Backlog promotion receipt no-action scope is required")
    return receipt


def validate_backlog_promotion_gate(
    discoveries: list[dict[str, Any]],
    *,
    backlog_promotion_receipt_paths: list[str | Path],
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    promotions = {
        str(receipt.get("discovery_id")): receipt
        for receipt in (
            validate_backlog_promotion_receipt(path, expected_context=expected_context)
            for path in backlog_promotion_receipt_paths
        )
    }
    missing: list[str] = []
    for discovery in discoveries:
        if not isinstance(discovery, dict):
            continue
        discovery_id = str(discovery.get("id") or discovery.get("discovery_id") or "").strip()
        discovery_type = str(discovery.get("type") or discovery.get("discovery_type") or "").strip()
        if discovery_type not in DISCOVERY_TYPES:
            continue
        if discovery_id not in promotions:
            missing.append(discovery_id or "<missing-id>")
    if missing:
        raise ValueError(
            "Discovered bugs/failures need backlog promotion receipts: "
            + ", ".join(missing)
        )
    return {"ok": True, "promoted_discoveries": sorted(promotions)}


def validate_change_context_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != CHANGE_CONTEXT_RECEIPT_TYPE:
        raise ValueError(
            "Change context receipt type mismatch: "
            f"expected {CHANGE_CONTEXT_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    for field in ("recent_commits", "dirty_state", "open_prs", "touched_files"):
        if field not in receipt or not isinstance(receipt.get(field), list):
            raise ValueError(f"Change context receipt {field} must be a list")
    _require_non_empty_string(receipt, "branch_divergence", context="Change context receipt")
    _require_non_empty_string(receipt, "impact_classification", context="Change context receipt")
    decision = _require_non_empty_string(receipt, "decision", context="Change context receipt")
    if decision not in CHANGE_CONTEXT_DECISIONS:
        raise ValueError(
            f"Change context receipt decision must be one of {sorted(CHANGE_CONTEXT_DECISIONS)}"
        )
    return receipt


def _resolve_receipt_path(receipt: dict[str, Any], value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    repo_root = Path(str(receipt.get("repo_root", ""))).expanduser()
    if not str(repo_root).strip():
        raise ValueError("Receipt is missing repo_root for relative path resolution")
    return repo_root / path


def _verify_receipt_file_hash(
    receipt: dict[str, Any],
    *,
    path_field: str,
    hash_field: str,
    context: str,
) -> Path:
    path_value = _require_non_empty_string(receipt, path_field, context=context)
    expected_hash = _require_non_empty_string(receipt, hash_field, context=context)
    path = _resolve_receipt_path(receipt, path_value)
    actual_hash = hash_file(path)
    if actual_hash != expected_hash:
        raise ValueError(
            f"{context} {hash_field} mismatch: expected {expected_hash}, got {actual_hash}"
        )
    return path


def _read_json_artifact(path: Path, *, context: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{context} must be JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{context} must be a JSON object")
    return data


def _string_contains_entrypoint(path: Path, entrypoint: str) -> bool:
    if path.is_file():
        try:
            return entrypoint in path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return False
    if path.is_dir():
        for candidate in path.rglob("*"):
            if not candidate.is_file():
                continue
            if ".git" in candidate.parts:
                continue
            try:
                if entrypoint in candidate.read_text(encoding="utf-8"):
                    return True
            except UnicodeDecodeError:
                continue
    return False


# Canonical plugin distribution surface. Claude Code installs SweetClaude by
# cloning the repo (see .claude-plugin/marketplace.json), so the distributable
# plugin is the clone root: skills/skill-library/agents/commands ship from the root, the
# manifest lives under .claude-plugin/, and hooks/ ship too. The release gate's
# distribution inventory and entrypoint search must walk this surface, not the
# manifest dir alone.
PLUGIN_DISTRIBUTION_ROOTS = ("skills", "skill-library", "agents", "commands", ".claude-plugin")
PLUGIN_HOOK_ROOT = "hooks"


def _inventory_files(root: Path) -> set[str]:
    if not root.exists():
        return set()
    if root.is_file():
        return {str(root)}
    files: set[str] = set()
    for candidate in root.rglob("*"):
        if candidate.is_file() and ".git" not in candidate.parts:
            files.add(str(candidate))
    return files


def _require_zero_exit(data: dict[str, Any], *, context: str) -> None:
    if data.get("exit_code") != 0:
        raise ValueError(f"{context} exit_code must be 0")


def _parse_semver_tag(value: str, *, context: str) -> tuple[int, bool]:
    match = SEMVER_TAG_RE.match(value.strip())
    if not match:
        raise ValueError(f"{context} tag must be a semantic version tag")
    return int(match.group("major")), bool(match.group("prerelease"))


def _require_discovery_entry(discovery: dict[str, Any], channel: str) -> dict[str, Any]:
    value = discovery.get(channel)
    if not isinstance(value, dict):
        raise ValueError(f"Release identity receipt update_discovery.{channel} must be an object")
    for field in (
        "channel",
        "tag",
        "artifact",
        "artifact_sha256",
        "source",
        "command",
        "last_run_result",
        "execution_receipt_path",
    ):
        _require_non_empty_string(
            value,
            field,
            context=f"Release identity receipt update_discovery.{channel}",
        )
    result = str(value.get("last_run_result", "")).lower()
    if result not in PASS_RESULTS:
        raise ValueError(
            f"Release identity receipt update_discovery.{channel} last_run_result must pass"
        )
    return value


def validate_release_artifact_build_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
    expected_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != RELEASE_ARTIFACT_BUILD_RECEIPT_TYPE:
        raise ValueError(
            "Release artifact build receipt type mismatch: "
            f"expected {RELEASE_ARTIFACT_BUILD_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    for field in (
        "branch",
        "commit",
        "tag",
        "build_command",
        "run_at",
        "source_clean_state",
        "artifact_path",
        "artifact_sha256",
    ):
        _require_non_empty_string(receipt, field, context="Release artifact build receipt")
    _require_zero_exit(receipt, context="Release artifact build receipt")
    _parse_timestamp(str(receipt["run_at"]), field="Release artifact build receipt run_at")
    if str(receipt.get("source_clean_state", "")).strip() != "clean":
        raise ValueError("Release artifact build receipt source_clean_state must be clean")
    _verify_receipt_file_hash(
        receipt,
        path_field="artifact_path",
        hash_field="artifact_sha256",
        context="Release artifact build receipt",
    )
    if expected_identity:
        for field, expected in expected_identity.items():
            actual = receipt.get(field)
            if _normalize_context_value(field, actual) != _normalize_context_value(
                field,
                expected,
            ):
                raise ValueError(
                    f"Release artifact build {field} mismatch: "
                    f"expected {expected!r}, got {actual!r}"
                )
    return receipt


def validate_update_discovery_execution_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
    expected_discovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != UPDATE_DISCOVERY_EXECUTION_RECEIPT_TYPE:
        raise ValueError(
            "Update discovery execution receipt type mismatch: "
            f"expected {UPDATE_DISCOVERY_EXECUTION_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    for field in (
        "channel",
        "command",
        "run_at",
        "stdout_path",
        "stdout_sha256",
        "stderr_path",
        "stderr_sha256",
        "resolved_channel",
        "resolved_tag",
        "resolved_artifact",
        "resolved_artifact_sha256",
    ):
        _require_non_empty_string(receipt, field, context="Update discovery execution receipt")
    _require_zero_exit(receipt, context="Update discovery execution receipt")
    _parse_timestamp(str(receipt["run_at"]), field="Update discovery execution receipt run_at")
    _verify_receipt_file_hash(
        receipt,
        path_field="stdout_path",
        hash_field="stdout_sha256",
        context="Update discovery execution receipt",
    )
    _verify_receipt_file_hash(
        receipt,
        path_field="stderr_path",
        hash_field="stderr_sha256",
        context="Update discovery execution receipt",
    )
    _verify_receipt_file_hash(
        receipt,
        path_field="resolved_artifact",
        hash_field="resolved_artifact_sha256",
        context="Update discovery execution receipt",
    )
    stdout = _resolve_receipt_path(receipt, str(receipt["stdout_path"]))
    parsed_output = _read_json_artifact(
        stdout,
        context="Update discovery execution receipt stdout",
    )
    for output_field, receipt_field in (
        ("channel", "resolved_channel"),
        ("tag", "resolved_tag"),
        ("artifact", "resolved_artifact"),
    ):
        parsed_value = parsed_output.get(output_field)
        if parsed_value is None:
            raise ValueError(
                f"Update discovery execution stdout is missing {output_field}"
            )
        normalize_field = "artifact_path" if output_field == "artifact" else output_field
        if _normalize_context_value(normalize_field, parsed_value) != _normalize_context_value(
            normalize_field,
            receipt[receipt_field],
        ):
            raise ValueError(
                "Update discovery execution stdout "
                f"{output_field} mismatch: expected {receipt[receipt_field]!r}, "
                f"got {parsed_value!r}"
            )
    parsed_hash = parsed_output.get("artifact_sha256")
    if not isinstance(parsed_hash, str) or not parsed_hash.strip():
        raise ValueError("Update discovery execution stdout is missing artifact_sha256")
    if parsed_hash != receipt["resolved_artifact_sha256"]:
        raise ValueError(
            "Update discovery execution stdout artifact_sha256 mismatch: "
            f"expected {receipt['resolved_artifact_sha256']!r}, got {parsed_hash!r}"
        )
    if expected_discovery:
        comparisons = {
            "channel": expected_discovery.get("channel"),
            "command": expected_discovery.get("command"),
            "resolved_channel": expected_discovery.get("channel"),
            "resolved_tag": expected_discovery.get("tag"),
            "resolved_artifact": expected_discovery.get("artifact"),
            "resolved_artifact_sha256": expected_discovery.get("artifact_sha256"),
        }
        for field, expected in comparisons.items():
            if expected is None:
                continue
            actual = receipt.get(field)
            normalize_field = "artifact_path" if field == "resolved_artifact" else field
            if _normalize_context_value(normalize_field, actual) != _normalize_context_value(
                normalize_field,
                expected,
            ):
                raise ValueError(
                    f"Update discovery execution {field} mismatch: "
                    f"expected {expected!r}, got {actual!r}"
                )
    return receipt


def validate_installed_smoke_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
    expected_claim: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != INSTALLED_SMOKE_RECEIPT_TYPE:
        raise ValueError(
            "Installed smoke receipt type mismatch: "
            f"expected {INSTALLED_SMOKE_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    for field in (
        "installed_entrypoint",
        "installed_path",
        "plugin_identity",
        "installed_manifest_path",
        "installed_manifest_sha256",
        "command",
        "run_at",
        "stdout_path",
        "stdout_sha256",
        "stderr_path",
        "stderr_sha256",
        "entrypoint_lookup_result",
        "release_artifact_path",
        "release_artifact_sha256",
    ):
        _require_non_empty_string(receipt, field, context="Installed smoke receipt")
    _require_zero_exit(receipt, context="Installed smoke receipt")
    _parse_timestamp(str(receipt["run_at"]), field="Installed smoke receipt run_at")
    if "sweetclaude" not in str(receipt.get("plugin_identity", "")).lower():
        raise ValueError("Installed smoke receipt plugin_identity must identify SweetClaude")
    installed = _resolve_receipt_path(receipt, str(receipt["installed_path"]))
    if not installed.exists():
        raise ValueError(f"Installed smoke receipt installed_path does not exist: {installed}")
    manifest = _verify_receipt_file_hash(
        receipt,
        path_field="installed_manifest_path",
        hash_field="installed_manifest_sha256",
        context="Installed smoke receipt",
    )
    try:
        manifest.relative_to(installed)
    except ValueError as exc:
        raise ValueError(
            "Installed smoke receipt installed_manifest_path must be inside installed_path"
        ) from exc
    _verify_receipt_file_hash(
        receipt,
        path_field="stdout_path",
        hash_field="stdout_sha256",
        context="Installed smoke receipt",
    )
    _verify_receipt_file_hash(
        receipt,
        path_field="stderr_path",
        hash_field="stderr_sha256",
        context="Installed smoke receipt",
    )
    _verify_receipt_file_hash(
        receipt,
        path_field="release_artifact_path",
        hash_field="release_artifact_sha256",
        context="Installed smoke receipt",
    )
    entrypoint = str(receipt["installed_entrypoint"])
    if entrypoint not in str(receipt["entrypoint_lookup_result"]):
        raise ValueError("Installed smoke receipt entrypoint_lookup_result must name entrypoint")
    entrypoint_sources = receipt.get("entrypoint_source_paths")
    if not isinstance(entrypoint_sources, list) or not entrypoint_sources:
        raise ValueError("Installed smoke receipt entrypoint_source_paths must be a non-empty list")
    found_entrypoint = False
    for index, source in enumerate(entrypoint_sources, start=1):
        if not isinstance(source, dict):
            raise ValueError(
                f"Installed smoke receipt entrypoint_source_paths #{index} must be an object"
            )
        source_path = _require_non_empty_string(
            source,
            "path",
            context=f"Installed smoke receipt entrypoint_source_paths #{index}",
        )
        source_hash = _require_non_empty_string(
            source,
            "sha256",
            context=f"Installed smoke receipt entrypoint_source_paths #{index}",
        )
        resolved_source = _resolve_receipt_path(receipt, source_path)
        actual_hash = hash_file(resolved_source)
        if actual_hash != source_hash:
            raise ValueError(
                "Installed smoke receipt entrypoint_source_paths "
                f"#{index} sha256 mismatch"
            )
        load_roots = [
            installed / root_name
            for root_name in (*PLUGIN_DISTRIBUTION_ROOTS, PLUGIN_HOOK_ROOT)
        ]
        if not any(resolved_source.is_relative_to(root) for root in load_roots):
            raise ValueError(
                "Installed smoke receipt entrypoint_source_paths "
                f"#{index} must be inside the installed plugin load surface"
            )
        if _string_contains_entrypoint(resolved_source, entrypoint):
            found_entrypoint = True
    if not found_entrypoint:
        raise ValueError(
            "Installed smoke receipt installed_entrypoint was not found in entrypoint sources"
        )
    if expected_claim:
        comparisons = {
            "installed_entrypoint": expected_claim.get("installed_entrypoint"),
            "installed_path": expected_claim.get("installed_path"),
            "plugin_identity": expected_claim.get("plugin_identity"),
            "command": expected_claim.get("smoke_command"),
            "stdout_path": expected_claim.get("smoke_output_path"),
            "stdout_sha256": expected_claim.get("smoke_output_sha256"),
        }
        for field, expected in comparisons.items():
            if expected is None:
                continue
            actual = receipt.get(field)
            normalize_field = "smoke_output_path" if field == "stdout_path" else field
            if _normalize_context_value(normalize_field, actual) != _normalize_context_value(
                normalize_field,
                expected,
            ):
                raise ValueError(
                    f"Installed smoke {field} mismatch: expected {expected!r}, got {actual!r}"
                )
    return receipt


def validate_public_distribution_inventory_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != PUBLIC_DISTRIBUTION_INVENTORY_RECEIPT_TYPE:
        raise ValueError(
            "Public distribution inventory receipt type mismatch: "
            f"expected {PUBLIC_DISTRIBUTION_INVENTORY_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    for field in (
        "manifest_capabilities",
        "installed_plugin_files",
        "hook_files",
        "mutation_commands",
        "network_commands",
        "generated_from",
    ):
        _require_list_of_strings(
            receipt,
            field,
            context="Public distribution inventory receipt",
        )
    artifacts = receipt.get("input_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError(
            "Public distribution inventory receipt input_artifacts must be a non-empty list"
        )
    repo_root = Path(str(receipt.get("repo_root", ""))).expanduser()
    if not str(repo_root).strip():
        raise ValueError("Public distribution inventory receipt is missing repo_root")
    artifact_paths: dict[str, Path] = {}
    for index, artifact in enumerate(artifacts, start=1):
        if not isinstance(artifact, dict):
            raise ValueError(
                f"Public distribution inventory receipt input_artifacts #{index} must be an object"
            )
        artifact_path = _require_non_empty_string(
            artifact,
            "path",
            context=f"Public distribution inventory receipt input_artifacts #{index}",
        )
        artifact_hash = _require_non_empty_string(
            artifact,
            "sha256",
            context=f"Public distribution inventory receipt input_artifacts #{index}",
        )
        resolved = Path(artifact_path)
        if not resolved.is_absolute():
            resolved = repo_root / resolved
        actual_hash = hash_file(resolved)
        if actual_hash != artifact_hash:
            raise ValueError(
                "Public distribution inventory receipt input_artifacts "
                f"#{index} sha256 mismatch"
            )
        artifact_paths[str(Path(artifact_path))] = resolved
        artifact_paths[str(resolved)] = resolved
    for field in ("generated_from", "installed_plugin_files", "hook_files"):
        for listed_path in receipt[field]:
            path = Path(listed_path)
            resolved = path if path.is_absolute() else repo_root / path
            if not resolved.exists():
                raise ValueError(
                    f"Public distribution inventory receipt {field} path does not exist: "
                    f"{listed_path}"
                )
            if str(path) not in artifact_paths and str(resolved) not in artifact_paths:
                raise ValueError(
                    f"Public distribution inventory receipt {field} path lacks hash evidence: "
                    f"{listed_path}"
                )
    installed_discovered: set[str] = set()
    for root_name in PLUGIN_DISTRIBUTION_ROOTS:
        installed_discovered |= _inventory_files(repo_root / root_name)
    for field, discovered in (
        ("installed_plugin_files", installed_discovered),
        ("hook_files", _inventory_files(repo_root / PLUGIN_HOOK_ROOT)),
    ):
        listed = {
            str(path if path.is_absolute() else repo_root / path)
            for path in (Path(value) for value in receipt[field])
        }
        missing = sorted(discovered - listed)
        if missing:
            display_missing = [
                str(Path(value).relative_to(repo_root))
                if Path(value).is_relative_to(repo_root)
                else value
                for value in missing
            ]
            raise ValueError(
                f"Public distribution inventory receipt {field} omits discovered files: "
                + ", ".join(display_missing)
            )
    capability_manifest = receipt.get("capability_manifest_path")
    if isinstance(capability_manifest, str) and capability_manifest.strip():
        manifest_path = Path(capability_manifest)
        resolved_manifest = (
            manifest_path if manifest_path.is_absolute() else repo_root / manifest_path
        )
        manifest_text = resolved_manifest.read_text(encoding="utf-8")
        for capability in receipt["manifest_capabilities"]:
            if capability not in manifest_text:
                raise ValueError(
                    "Public distribution inventory receipt manifest_capabilities "
                    f"entry not found in manifest: {capability!r}"
                )
    return receipt


def validate_release_identity_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
    expected_identity: dict[str, Any] | None = None,
    verify_artifact_hash: bool = False,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != RELEASE_IDENTITY_RECEIPT_TYPE:
        raise ValueError(
            "Release identity receipt type mismatch: "
            f"expected {RELEASE_IDENTITY_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    for field in (
        "branch",
        "commit",
        "tag",
        "package_version",
        "plugin_version",
        "changelog_version",
        "channel",
        "install_path",
        "artifact_path",
        "artifact_sha256",
    ):
        _require_non_empty_string(receipt, field, context="Release identity receipt")

    build_receipt_path = _require_non_empty_string(
        receipt,
        "build_receipt_path",
        context="Release identity receipt",
    )
    validate_release_artifact_build_receipt(
        _resolve_receipt_path(receipt, build_receipt_path),
        expected_context=expected_context,
        expected_identity={
            "branch": receipt["branch"],
            "commit": receipt["commit"],
            "tag": receipt["tag"],
            "artifact_path": receipt["artifact_path"],
            "artifact_sha256": receipt["artifact_sha256"],
        },
    )

    update_discovery = receipt.get("update_discovery")
    if not isinstance(update_discovery, dict):
        raise ValueError("Release identity receipt update_discovery must be an object")
    manifest_channels = load_manifest().get("channels") or {}
    # Retired channels no longer publish artifacts (ISSUE-241) — identity
    # evidence covers live channels only, matching the generate side.
    manifest_channels = {
        channel: facts
        for channel, facts in manifest_channels.items()
        if not (isinstance(facts, dict) and facts.get("retired"))
    }
    for channel, channel_facts in manifest_channels.items():
        entry = _require_discovery_entry(update_discovery, channel)
        validate_update_discovery_execution_receipt(
            _resolve_receipt_path(receipt, entry["execution_receipt_path"]),
            expected_context=expected_context,
            expected_discovery=entry,
        )
        expected_major = int(channel_facts["major_version"])
        prerelease_required = bool(channel_facts.get("prerelease_required"))
        major, prerelease = _parse_semver_tag(
            entry["tag"],
            context=f"Release identity receipt {channel} update discovery",
        )
        if (
            entry["channel"] != channel
            or major != expected_major
            or prerelease != prerelease_required
        ):
            raise ValueError(
                f"Release identity receipt {channel} update discovery "
                f"does not match the {channel} channel contract"
            )

    if expected_identity:
        for field, expected in expected_identity.items():
            actual = receipt.get(field)
            if _normalize_context_value(field, actual) != _normalize_context_value(
                field,
                expected,
            ):
                raise ValueError(
                    f"Release identity {field} mismatch: expected {expected!r}, got {actual!r}"
                )
        expected_channel = str(expected_identity.get("channel", "")).strip()
        expected_tag = str(expected_identity.get("tag", "")).strip()
        expected_artifact = expected_identity.get("artifact_path")
        if expected_channel in manifest_channels:
            channel_entry = update_discovery[expected_channel]
            if channel_entry["tag"] != expected_tag:
                raise ValueError(
                    "Release identity update discovery tag mismatch: "
                    f"expected {expected_tag!r}, got {channel_entry['tag']!r}"
                )
            if expected_artifact is not None and _normalize_context_value(
                "artifact_path",
                channel_entry["artifact"],
            ) != _normalize_context_value("artifact_path", expected_artifact):
                raise ValueError(
                    "Release identity update discovery artifact mismatch: "
                    f"expected {expected_artifact!r}, got {channel_entry['artifact']!r}"
                )

    if verify_artifact_hash:
        artifact = _resolve_receipt_path(receipt, str(receipt["artifact_path"]))
        actual = hash_file(artifact)
        if actual != receipt["artifact_sha256"]:
            raise ValueError(
                "Release identity artifact hash mismatch: "
                f"expected {receipt['artifact_sha256']}, got {actual}"
            )
        for channel in manifest_channels:
            entry = update_discovery[channel]
            discovery_artifact = _resolve_receipt_path(receipt, str(entry["artifact"]))
            discovery_actual = hash_file(discovery_artifact)
            if discovery_actual != entry["artifact_sha256"]:
                raise ValueError(
                    f"Release identity update_discovery.{channel} artifact hash mismatch: "
                    f"expected {entry['artifact_sha256']}, got {discovery_actual}"
                )

    return receipt


def validate_docs_capability_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != DOCS_CAPABILITY_RECEIPT_TYPE:
        raise ValueError(
            "Docs capability receipt type mismatch: "
            f"expected {DOCS_CAPABILITY_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    claims = _require_list_of_objects(
        receipt,
        "claims",
        context="Docs capability receipt",
    )
    for index, claim in enumerate(claims, start=1):
        context = f"Docs capability receipt claims #{index}"
        _require_non_empty_string(claim, "claim", context=context)
        status = _require_non_empty_string(claim, "status", context=context)
        if status not in DOCS_CAPABILITY_CLAIM_STATUSES:
            raise ValueError(
                f"{context} status must be one of {sorted(DOCS_CAPABILITY_CLAIM_STATUSES)}"
            )
        if status == "proven":
            _require_non_empty_string(claim, "installed_entrypoint", context=context)
            _require_non_empty_string(claim, "smoke_command", context=context)
            installed_path = _require_non_empty_string(
                claim,
                "installed_path",
                context=context,
            )
            plugin_identity = _require_non_empty_string(
                claim,
                "plugin_identity",
                context=context,
            )
            if "sweetclaude" not in plugin_identity.lower():
                raise ValueError(f"{context} plugin_identity must identify SweetClaude")
            _parse_timestamp(
                _require_non_empty_string(claim, "run_at", context=context),
                field=f"{context} run_at",
            )
            result = _require_non_empty_string(claim, "last_run_result", context=context)
            if result.lower() not in PASS_RESULTS:
                raise ValueError(f"{context} last_run_result must pass, got {result!r}")
            exit_code = claim.get("exit_code")
            if exit_code != 0:
                raise ValueError(f"{context} exit_code must be 0")
            smoke_output_path = _require_non_empty_string(
                claim,
                "smoke_output_path",
                context=context,
            )
            smoke_output_sha256 = _require_non_empty_string(
                claim,
                "smoke_output_sha256",
                context=context,
            )
            receipt_root = Path(str(receipt.get("repo_root", ""))).expanduser()
            if not str(receipt_root).strip():
                raise ValueError("Docs capability receipt is missing repo_root")
            installed = Path(installed_path)
            if not installed.is_absolute():
                installed = receipt_root / installed
            if not installed.exists():
                raise ValueError(f"{context} installed_path does not exist: {installed}")
            smoke_output = Path(smoke_output_path)
            if not smoke_output.is_absolute():
                smoke_output = receipt_root / smoke_output
            if hash_file(smoke_output) != smoke_output_sha256:
                raise ValueError(f"{context} smoke_output_sha256 mismatch")
            installed_smoke_receipt_path = _require_non_empty_string(
                claim,
                "installed_smoke_receipt_path",
                context=context,
            )
            validate_installed_smoke_receipt(
                _resolve_receipt_path(receipt, installed_smoke_receipt_path),
                expected_context=expected_context,
                expected_claim=claim,
            )
        else:
            _require_non_empty_string(claim, "label", context=context)
    return receipt


def validate_public_distribution_receipt(
    receipt_path: str | Path,
    *,
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = validate_control_receipt_context(
        receipt_path,
        expected_context=expected_context,
        verify_artifact_hashes=False,
    )
    if receipt.get("receipt_type") != PUBLIC_DISTRIBUTION_RECEIPT_TYPE:
        raise ValueError(
            "Public distribution receipt type mismatch: "
            f"expected {PUBLIC_DISTRIBUTION_RECEIPT_TYPE}, got {receipt.get('receipt_type')}"
        )
    for field in (
        "permissions",
        "installed_user_file_access",
        "network_access",
        "hooks",
        "project_mutation_commands",
        "provider_bound_data",
        "auth_assumptions",
    ):
        _require_list_of_strings(receipt, field, context="Public distribution receipt")
    for field in (
        "secrets_handling",
        "channel_visibility",
        "marketplace_or_distribution_visibility",
        "evidence_source",
        "approved_trust_model",
    ):
        _require_non_empty_string(receipt, field, context="Public distribution receipt")
    inventory_receipt_path = _require_non_empty_string(
        receipt,
        "inventory_receipt_path",
        context="Public distribution receipt",
    )
    inventory = validate_public_distribution_inventory_receipt(
        _resolve_receipt_path(receipt, inventory_receipt_path),
        expected_context=expected_context,
    )
    declared_mutations = set(receipt["project_mutation_commands"])
    for command in inventory["mutation_commands"]:
        if command not in declared_mutations:
            raise ValueError(
                "Public distribution receipt missing inventory mutation command "
                f"{command!r}"
            )
    declared_hooks = set(receipt["hooks"])
    for hook in inventory["hook_files"]:
        if hook not in declared_hooks:
            raise ValueError(
                "Public distribution receipt missing inventory hook file "
                f"{hook!r}"
            )
    if inventory["network_commands"]:
        declared_network = {value.lower() for value in receipt["network_access"]}
        if declared_network <= {"none", "no network", "no network access"}:
            raise ValueError(
                "Public distribution receipt cannot claim no network access "
                "when inventory includes network commands"
            )
    return receipt


def validate_status_closure_gate(
    *,
    subject_id: str,
    objective_criteria_receipt_path: str | Path | None,
    phase_exit_receipt_path: str | Path | None,
    findings: list[dict[str, Any]],
    finding_disposition_receipt_paths: list[str | Path],
    discoveries: list[dict[str, Any]],
    backlog_promotion_receipt_paths: list[str | Path],
    expected_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not str(subject_id or "").strip():
        raise ValueError("Status closure gate requires subject_id")
    if not objective_criteria_receipt_path:
        raise ValueError("Status closure gate requires objective criteria receipt")
    if not phase_exit_receipt_path:
        raise ValueError("Status closure gate requires phase_exit_receipt")

    objective = validate_objective_criteria_receipt(
        objective_criteria_receipt_path,
        expected_context=expected_context,
    )
    phase_exit = validate_phase_exit_receipt(
        phase_exit_receipt_path,
        expected_context=expected_context,
    )
    finding_result = validate_finding_disposition_gate(
        findings,
        disposition_receipt_paths=finding_disposition_receipt_paths,
        expected_context=expected_context,
    )
    backlog_result = validate_backlog_promotion_gate(
        discoveries,
        backlog_promotion_receipt_paths=backlog_promotion_receipt_paths,
        expected_context=expected_context,
    )
    return {
        "ok": True,
        "subject_id": subject_id,
        "objective_criteria_receipt": objective.get("receipt_id"),
        "phase_exit_receipt": phase_exit.get("receipt_id"),
        "dispositioned_findings": finding_result["dispositioned_findings"],
        "promoted_discoveries": backlog_result["promoted_discoveries"],
    }


def _load_json_argument(value: str, *, field: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field} must be valid JSON: {exc}") from exc
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError(f"{field} must be a JSON list of objects")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SweetClaude MS-007 control receipts")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("validate-status-closure")
    p_status.add_argument("--subject-id", required=True)
    p_status.add_argument("--objective-criteria-receipt", required=True)
    p_status.add_argument("--phase-exit-receipt", required=True)
    p_status.add_argument("--findings-json", default="[]")
    p_status.add_argument("--finding-disposition-receipt", action="append", default=[])
    p_status.add_argument("--discoveries-json", default="[]")
    p_status.add_argument("--backlog-promotion-receipt", action="append", default=[])

    args = parser.parse_args(argv)

    try:
        if args.cmd == "validate-status-closure":
            result = validate_status_closure_gate(
                subject_id=args.subject_id,
                objective_criteria_receipt_path=args.objective_criteria_receipt,
                phase_exit_receipt_path=args.phase_exit_receipt,
                findings=_load_json_argument(args.findings_json, field="findings-json"),
                finding_disposition_receipt_paths=args.finding_disposition_receipt,
                discoveries=_load_json_argument(args.discoveries_json, field="discoveries-json"),
                backlog_promotion_receipt_paths=args.backlog_promotion_receipt,
            )
            print(json.dumps(result))
            return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
