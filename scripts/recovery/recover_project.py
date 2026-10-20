#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
SweetClaude project recovery command.

Diagnosis and planning are read-only. Execution is mutating, requires explicit
approval, creates a snapshot first, and is intentionally limited to operations
represented in the recovery manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from maintenance.capability_manifest import capability_config, project_shape_config
from mutation_safety import (
    hash_payload,
    should_stop_repair_loop,
    validate_approval_scope,
    validate_postconditions,
    validate_restore_proof,
    validate_snapshot_scope,
    validate_write_set,
)

try:
    from recovery.characterize_project import characterize_project, is_derived_file
except ModuleNotFoundError:  # Allows direct script execution.
    from characterize_project import characterize_project, is_derived_file


SCHEMA_VERSION = 1
PLAN_SCHEMA_VERSION = 1
EXECUTION_SCHEMA_VERSION = 1
RECOVERY_RUNS_DIR = Path(".sweetclaude/state/recovery-runs")
OLD_TAXONOMY_PREFIXES = {"STORY", "BUG", "DEBT", "CHORE", "BL"}
PENDING_DOCTOR_PROMPT_PATHS = (
    Path(".sweetclaude/state/doctor-prompt-pending.json"),
    Path(".sweetclaude/doctor-prompt-pending.json"),
)


def _safe_load_yaml(path: Path) -> tuple[Any | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(errors="replace")
    try:
        return yaml.safe_load(text), None
    except yaml.YAMLError as exc:
        return None, str(exc)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _read_sweetclaude_state(project: Path) -> dict[str, Any]:
    state_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    state: dict[str, Any] = {
        "path": str(state_path),
        "exists": state_path.exists(),
        "parse_error": None,
        "installed_version": None,
        "migration_status": None,
        "product_base": None,
        "taxonomy_recovery_status": None,
        "taxonomy_migration_required": None,
        "taxonomy_blind_migration_allowed": None,
        "taxonomy_compatibility_exited": None,
    }
    if not state_path.exists():
        return state

    data, error = _safe_load_yaml(state_path)
    if error:
        state["parse_error"] = error
        return state
    if not isinstance(data, dict):
        state["parse_error"] = "sweetclaude.yaml is not a mapping"
        return state

    framework = data.get("framework")
    if isinstance(framework, dict):
        state["installed_version"] = framework.get("installed_version")
        state["migration_status"] = framework.get("migration_status")

    if state["migration_status"] is None:
        state["migration_status"] = data.get("migration_status")

    paths = data.get("paths")
    if isinstance(paths, dict):
        state["product_base"] = paths.get("product_base")

    recovery = data.get("recovery")
    if isinstance(recovery, dict):
        taxonomy = recovery.get("taxonomy")
        if isinstance(taxonomy, dict):
            state["taxonomy_recovery_status"] = taxonomy.get("status")
            state["taxonomy_migration_required"] = taxonomy.get("migration_required")
            state["taxonomy_blind_migration_allowed"] = taxonomy.get(
                "blind_taxonomy_migration_allowed"
            )
            state["taxonomy_compatibility_exited"] = taxonomy.get(
                "compatibility_exited"
            )

    return state


def _project_relative_path(project: Path, path: Path | str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            return candidate.relative_to(project).as_posix()
        except ValueError:
            return str(candidate)
    return candidate.as_posix()


def _project_file_fingerprint(project: Path) -> dict[str, str]:
    fingerprint: dict[str, str] = {}
    for path in sorted(project.rglob("*")):
        if path.is_file():
            fingerprint[_project_relative_path(project, path)] = _sha256_file(path)
    return fingerprint


def _changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    changed = [
        path
        for path, digest in after.items()
        if before.get(path) != digest
    ]
    removed = [
        path
        for path in before
        if path not in after
    ]
    return sorted(set(changed + removed))


def _resolve_project_path(project: Path, rel_path: str) -> Path:
    candidate = Path(rel_path)
    if candidate.is_absolute():
        raise ValueError(f"recovery path must be project-relative: {rel_path}")
    resolved = (project / candidate).resolve()
    if not _is_relative_to(resolved, project.resolve()):
        raise ValueError(f"recovery path escapes project root: {rel_path}")
    return resolved


def _is_recovery_run_path(project: Path, path: Path) -> bool:
    recovery_root = (project / RECOVERY_RUNS_DIR).resolve()
    return _is_relative_to(path.resolve(), recovery_root)


def _pending_doctor_prompts(project: Path) -> list[str]:
    prompts: list[str] = []
    for rel_path in PENDING_DOCTOR_PROMPT_PATHS:
        path = project / rel_path
        if path.exists() and _is_migration_related_doctor_prompt(path):
            prompts.append(rel_path.as_posix())
    return prompts


def _is_migration_related_doctor_prompt(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return "migration" in text.lower() or "migrate" in text.lower()

    if not isinstance(data, dict):
        return False

    values = [
        data.get("trigger"),
        data.get("category"),
        data.get("recommendation"),
        data.get("reason"),
        data.get("fix_type"),
    ]
    return any(
        isinstance(value, str)
        and ("migration" in value.lower() or "migrate" in value.lower())
        for value in values
    )


def _old_prefix_count(characterization: dict[str, Any]) -> int:
    prefixes = characterization.get("counts", {}).get("prefixes", {})
    if not isinstance(prefixes, dict):
        return 0
    return sum(int(prefixes.get(prefix, 0) or 0) for prefix in OLD_TAXONOMY_PREFIXES)


def _add_failure_class(
    failure_classes: list[dict[str, Any]],
    code: str,
    severity: str,
    title: str,
    evidence: dict[str, Any],
    recovery_strategy: str,
) -> None:
    failure_classes.append({
        "code": code,
        "severity": severity,
        "title": title,
        "evidence": evidence,
        "recovery_strategy": recovery_strategy,
    })


def _has_failure(diagnosis: dict[str, Any], code: str) -> bool:
    return code in diagnosis.get("failure_class_codes", [])


def _state_schema_drift_findings(project: Path) -> list[dict[str, Any]]:
    """Read-only drift report from the migration runner's registry.

    Drift is resolved by the runner (bootstrap Step 5c offers it; doctor
    auto-fixes through it), not by recovery — so callers report these as
    informational, never as route-driving failure classes.
    """
    runner = SCRIPTS_DIR / "migrations" / "runner.py"
    if not runner.is_file():
        return []
    completed = subprocess.run(
        [sys.executable, str(runner), "--project-dir", str(project),
         "--report-drift-for-skill"],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        return []
    findings: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        if not line.startswith("FINDING|"):
            continue
        parts = line.split("|")
        findings.append({
            "file": parts[1] if len(parts) > 1 else "",
            "migration": parts[2] if len(parts) > 2 else "",
            "chain": (parts[3].removeprefix("chain=")
                      if len(parts) > 3 else ""),
        })
    return findings


def _taxonomy_recovery_accepts_legacy_layout(state: dict[str, Any]) -> bool:
    return (
        state.get("migration_status") == "deferred"
        and state.get("taxonomy_recovery_status") == "stabilized-without-migration"
        and state.get("taxonomy_migration_required") is False
        and state.get("taxonomy_blind_migration_allowed") is False
    )


def _plan_id(project: Path, route: str, operations: list[dict[str, Any]]) -> str:
    payload = {
        "project_dir": str(project),
        "route": route,
        "operations": [
            {
                "id": op.get("id"),
                "action": op.get("action"),
                "target": op.get("target"),
            }
            for op in operations
        ],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"recovery-plan-{digest}"


def _diagnosis_summary(diagnosis: dict[str, Any]) -> dict[str, Any]:
    characterization = diagnosis.get("characterization", {})
    return {
        "failure_class_codes": diagnosis.get("failure_class_codes", []),
        "blocking_factor_codes": [
            factor.get("code") for factor in diagnosis.get("blocking_factors", [])
        ],
        "recovery_route": diagnosis.get("recovery_route"),
        "product_base": characterization.get("product_base"),
        "product_base_exists": characterization.get("product_base_exists"),
        "taxonomy_candidate_count": characterization.get("migration_risk", {}).get(
            "taxonomy_candidate_count", 0
        ),
        "duplicate_id_count": characterization.get("ids", {}).get("duplicate_count", 0),
        "typed_backlog_dirs": characterization.get("counts", {}).get(
            "typed_backlog_dirs", {}
        ),
        "sweetclaude_state": diagnosis.get("sweetclaude_state", {}),
    }


def _recovery_project_shape(route: str) -> str:
    if route == "stabilize-without-migration":
        return "recovery_required"
    if route == "typed-legacy-migrate":
        return "typed_legacy_backlog"
    if route == "manual-escalation":
        return "manual_escalation"
    if route == "no-recovery-needed":
        return "current_layout"
    return "manual_escalation"


def _recovery_capability_contract(project_shape: str) -> dict[str, Any]:
    shape = project_shape_config(project_shape)
    capability_id = str(shape.get("recovery_capability", "") or "")
    if not capability_id:
        return {
            "capability_id": "",
            "project_shape": project_shape,
            "manifest_supported": False,
            "supported_project_shapes": [],
            "safety_contract": [],
            "verification_commands": [],
        }
    capability = capability_config(capability_id)
    supported_shapes = list(capability.get("supports_project_shapes") or [])
    return {
        "capability_id": capability_id,
        "project_shape": project_shape,
        "manifest_supported": project_shape in supported_shapes,
        "supported_project_shapes": supported_shapes,
        "safety_contract": list(capability.get("safety_contract") or []),
        "verification_commands": list(capability.get("verification_commands") or []),
        "requires_approval": bool(capability.get("requires_approval", False)),
        "mutates_project": bool(capability.get("mutates_project", False)),
    }


def _validate_recovery_plan_capability(plan: dict[str, Any]) -> None:
    capability_id = str(plan.get("capability_id", "") or "")
    project_shape = str(plan.get("project_shape", "") or "")
    if not capability_id or not project_shape:
        raise ValueError("recovery plan is missing manifest capability metadata")
    capability = capability_config(capability_id)
    supported_shapes = list(capability.get("supports_project_shapes") or [])
    if project_shape not in supported_shapes:
        raise ValueError(
            f"recovery capability {capability_id} does not support project_shape={project_shape}"
        )


def _approval_context(project: Path, plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_dir": str(project),
        "plan_id": plan.get("plan_id"),
        "capability_id": plan.get("capability_id"),
        "project_shape": plan.get("project_shape"),
    }


def _recovery_write_set(plan: dict[str, Any]) -> list[str]:
    write_set = {str(path) for path in plan.get("affected_paths", [])}
    write_set.add((RECOVERY_RUNS_DIR.as_posix()).rstrip("/") + "/")
    return sorted(write_set)


def _recovery_plan_payload(plan: dict[str, Any], write_set: list[str]) -> dict[str, Any]:
    return {
        "plan_id": plan.get("plan_id"),
        "capability_id": plan.get("capability_id"),
        "project_shape": plan.get("project_shape"),
        "operations": list(plan.get("operations", [])),
        "declared_write_set": write_set,
        "declared_blast_radius": list(plan.get("snapshot", {}).get("paths", [])),
        "verification": list(plan.get("verification", [])),
    }


def _attach_mutation_plan(project: Path, plan: dict[str, Any]) -> dict[str, Any]:
    write_set = _recovery_write_set(plan)
    payload = _recovery_plan_payload(plan, write_set)
    plan_hash = hash_payload(payload)
    write_set_hash = hash_payload(write_set)
    mutation_plan = {
        "status": "approval-required" if plan.get("can_execute_after_snapshot") else "not-executable",
        "plan_hash": plan_hash,
        "write_set_hash": write_set_hash,
        "declared_write_set": write_set,
        "declared_blast_radius": list(payload["declared_blast_radius"]),
        "postconditions": [
            {"id": check.get("id"), "status": "pending"}
            for check in plan.get("verification", [])
        ] + [{"id": "verification", "status": "pending"}],
        "approval_receipt_template": {
            "schema_version": 1,
            "kind": "sweetclaude.recovery.approval",
            "approved": False,
            "plan_hash": plan_hash,
            "write_set_hash": write_set_hash,
            "snapshot_hash": "",
            "context": _approval_context(project, plan),
        },
    }
    plan["mutation_plan"] = mutation_plan
    return plan


def _load_approval_receipt(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid approval receipt: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("invalid approval receipt: not a JSON object")
    return data


def _validate_approval_receipt(
    *,
    receipt: dict[str, Any],
    project: Path,
    plan: dict[str, Any],
) -> dict[str, Any]:
    if receipt.get("schema_version") != 1:
        raise ValueError("approval receipt schema_version must be 1")
    if receipt.get("kind") != "sweetclaude.recovery.approval":
        raise ValueError("approval receipt kind mismatch")
    if receipt.get("approved") is not True:
        raise ValueError("approval receipt is not approved")
    mutation_plan = plan["mutation_plan"]
    return validate_approval_scope(
        receipt,
        plan_hash=mutation_plan["plan_hash"],
        write_set_hash=mutation_plan["write_set_hash"],
        snapshot_hash=str(receipt.get("snapshot_hash", "")),
        context=_approval_context(project, plan),
    )


def _snapshot_paths(project: Path, diagnosis: dict[str, Any]) -> list[str]:
    paths = [".sweetclaude/state"]
    artifact_privacy = project / ".sweetclaude" / "artifact-privacy.yaml"
    if artifact_privacy.exists():
        paths.append(".sweetclaude/artifact-privacy.yaml")
    product_base = diagnosis.get("characterization", {}).get("product_base")
    if product_base:
        paths.append(_project_relative_path(project, product_base))
    return sorted(dict.fromkeys(paths))


def _state_operations(project: Path, diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    state = diagnosis.get("sweetclaude_state", {})
    if not state.get("exists"):
        return operations

    state_target = _project_relative_path(project, state["path"])
    if _has_failure(diagnosis, "stale-migration-complete-state"):
        current_status = state.get("migration_status")
        operations.append({
            "id": "set-migration-status-deferred",
            "action": "yaml-set",
            "target": state_target,
            "yaml_path": ["framework", "migration_status"],
            "current_value": current_status,
            "planned_value": "deferred",
            "reason": (
                "State says migration is complete, but legacy taxonomy files "
                "remain in a layout SweetClaude cannot safely migrate."
            ),
            "rollback": {
                "action": "yaml-set",
                "target": state_target,
                "yaml_path": ["framework", "migration_status"],
                "value": current_status,
            },
        })
    elif (
        _has_failure(diagnosis, "unsupported-typed-backlog-layout")
        and state.get("migration_status") == "incomplete"
    ):
        operations.append({
            "id": "set-migration-status-deferred",
            "action": "yaml-set",
            "target": state_target,
            "yaml_path": ["framework", "migration_status"],
            "current_value": "incomplete",
            "planned_value": "deferred",
            "reason": (
                "Normalize an interrupted (incomplete) migration to deferred so "
                "the recovered typed-legacy project can be migrated rather than "
                "cycling back into recovery."
            ),
            "rollback": {
                "action": "yaml-set",
                "target": state_target,
                "yaml_path": ["framework", "migration_status"],
                "value": "incomplete",
            },
        })

    if _has_failure(diagnosis, "unsupported-typed-backlog-layout"):
        operations.append({
            "id": "record-taxonomy-recovery-state",
            "action": "yaml-merge",
            "target": state_target,
            "yaml_path": ["recovery", "taxonomy"],
            "planned_value": {
                "status": "stabilized-without-migration",
                "accepted_layout": "typed-backlog-prefixes",
                "migration_required": False,
                "blind_taxonomy_migration_allowed": False,
                "reason": (
                    "Typed backlog folders with legacy prefixes are accepted "
                    "as a compatibility state until a layout-specific migrator "
                    "passes manifest and rollback drills."
                ),
            },
            "reason": (
                "Record that recovery intentionally stabilized the project "
                "without moving product artifacts."
            ),
            "rollback": {
                "action": "restore-yaml-subtree-from-snapshot",
                "target": state_target,
                "yaml_path": ["recovery", "taxonomy"],
            },
        })

    return operations


def _pending_prompt_operations(
    diagnosis: dict[str, Any],
) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for index, prompt in enumerate(diagnosis.get("pending_doctor_prompts", []), start=1):
        operations.append({
            "id": f"delete-pending-doctor-prompt-{index}",
            "action": "delete-file",
            "target": prompt,
            "if_exists": True,
            "reason": (
                "Pending doctor prompt must be cleared because recovery "
                "diagnosis supersedes old migration recommendations."
            ),
            "rollback": {
                "action": "restore-file-from-snapshot",
                "target": prompt,
            },
        })
    return operations


def _blocked_actions(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    return []


def _get_yaml_path(data: dict[str, Any], path: list[str]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _set_yaml_path(data: dict[str, Any], path: list[str], value: Any) -> None:
    current = data
    for key in path[:-1]:
        child = current.get(key)
        if not isinstance(child, dict):
            child = {}
            current[key] = child
        current = child
    current[path[-1]] = value


def _merge_yaml_path(data: dict[str, Any], path: list[str], value: dict[str, Any]) -> None:
    current = data
    for key in path:
        child = current.get(key)
        if not isinstance(child, dict):
            child = {}
            current[key] = child
        current = child
    current.update(value)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    data, error = _safe_load_yaml(path)
    if error:
        raise ValueError(f"could not parse YAML at {path}: {error}")
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML at {path} is not a mapping")
    return data


def _write_yaml_mapping(path: Path, data: dict[str, Any]) -> None:
    _atomic_write_text(path, yaml.safe_dump(data, sort_keys=False))


def _iter_snapshot_files(project: Path, rel_paths: list[str]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel_path in rel_paths:
        root = _resolve_project_path(project, rel_path)
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        for path in candidates:
            if _is_recovery_run_path(project, path):
                continue
            rel = path.relative_to(project).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            files.append({
                "path": rel,
                "sha256": _sha256_file(path),
                "size": path.stat().st_size,
            })
    return sorted(files, key=lambda item: item["path"])


def _create_snapshot(project: Path, plan: dict[str, Any]) -> dict[str, Any]:
    run_id = f"{plan['plan_id']}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = _resolve_project_path(project, (RECOVERY_RUNS_DIR / run_id).as_posix())
    run_dir.mkdir(parents=True, exist_ok=False)

    snapshot_paths = plan.get("snapshot", {}).get("paths", [])
    files = _iter_snapshot_files(project, snapshot_paths)
    snapshot_path = run_dir / "snapshot.tar.gz"
    with tarfile.open(snapshot_path, "w:gz") as tar:
        for item in files:
            tar.add(project / item["path"], arcname=item["path"], recursive=False)

    snapshot = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "path": str(snapshot_path),
        "sha256": _sha256_file(snapshot_path),
        "paths": snapshot_paths,
        "file_count": len(files),
        "files": files,
    }
    _atomic_write_json(run_dir / "snapshot-manifest.json", snapshot)
    _atomic_write_json(run_dir / "plan.json", plan)
    return snapshot


def _execute_operation(project: Path, operation: dict[str, Any]) -> dict[str, Any]:
    action = operation["action"]
    target = _resolve_project_path(project, operation["target"])

    if action == "yaml-set":
        data = _load_yaml_mapping(target)
        current_value = _get_yaml_path(data, operation["yaml_path"])
        if "current_value" in operation and current_value != operation["current_value"]:
            raise ValueError(
                f"{operation['id']} expected {operation['yaml_path']}="
                f"{operation['current_value']!r}, found {current_value!r}"
            )
        _set_yaml_path(data, operation["yaml_path"], operation["planned_value"])
        _write_yaml_mapping(target, data)
    elif action == "yaml-merge":
        data = _load_yaml_mapping(target)
        planned_value = operation.get("planned_value")
        if not isinstance(planned_value, dict):
            raise ValueError(f"{operation['id']} planned_value must be a mapping")
        _merge_yaml_path(data, operation["yaml_path"], planned_value)
        _write_yaml_mapping(target, data)
    elif action == "delete-file":
        if target.exists():
            if not target.is_file():
                raise ValueError(f"{operation['id']} target is not a file: {target}")
            target.unlink()
    else:
        raise ValueError(f"unsupported recovery operation action: {action}")

    return {
        "id": operation["id"],
        "action": action,
        "target": operation["target"],
        "status": "applied",
    }


def _product_files_unchanged(project: Path, snapshot: dict[str, Any]) -> tuple[bool, list[str]]:
    changed: list[str] = []
    product_roots = [
        rel_path.rstrip("/") + "/"
        for rel_path in snapshot.get("paths", [])
        if rel_path.rstrip("/").endswith("docs/product")
        or rel_path.rstrip("/").endswith(".sweetclaude/product")
        or rel_path.rstrip("/").endswith(".sweetclaude/artifacts/product")
    ]
    if not product_roots:
        return True, []

    before = {
        item["path"]: item
        for item in snapshot.get("files", [])
        if any(item["path"].startswith(root) for root in product_roots)
    }
    for rel_path, item in before.items():
        path = project / rel_path
        if not path.exists():
            changed.append(rel_path)
        elif _sha256_file(path) != item["sha256"]:
            changed.append(rel_path)

    for root in product_roots:
        root_path = project / root
        if root_path.exists():
            for path in root_path.rglob("*"):
                if not path.is_file():
                    continue
                if _is_recovery_run_path(project, path):
                    continue
                rel = path.relative_to(project).as_posix()
                if rel not in before:
                    changed.append(rel)

    return not changed, sorted(changed)


def _run_json_command(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    result: dict[str, Any] = {
        "cmd": cmd,
        "returncode": completed.returncode,
        "stderr": completed.stderr.strip(),
    }
    try:
        result["json"] = json.loads(completed.stdout) if completed.stdout.strip() else None
    except json.JSONDecodeError as exc:
        result["json_error"] = str(exc)
        result["stdout_sample"] = completed.stdout[:1000]
    return result


def _is_supported_migration_capability(capability_id: str) -> bool:
    """A migration capability is safe to offer iff the manifest marks it
    supported (not explicitly ``supported: false``) and declares the shapes it
    handles. Post-WI-017 the typed-legacy migrator is supported, so offering it
    is the sanctioned exit from compatibility mode — not the old unsafe loop."""
    if not capability_id:
        return False
    capability = capability_config(capability_id)
    return capability.get("supported", True) is not False and bool(
        capability.get("supports_project_shapes")
    )


def _doctor_migration_scan_check(project: Path) -> dict[str, Any]:
    doctor = Path(__file__).resolve().parents[1] / "doctor.py"
    result = _run_json_command([
        sys.executable,
        str(doctor),
        "scan",
        "--project-dir",
        str(project),
        "--category",
        "migration_currency",
    ])
    data = result.get("json") if isinstance(result.get("json"), dict) else {}
    findings = data.get("findings", []) if isinstance(data, dict) else []
    migration_recommendations = (
        data.get("migration_recommendations", []) if isinstance(data, dict) else []
    )
    # Post-WI-017 a safe, supported migrator exists, so a migration finding or
    # recommendation is no longer the old "blind/unsafe migration" loop the
    # check was guarding against. The postcondition now fails only if doctor
    # recommends an UNSUPPORTED migration capability; surfacing the supported
    # migrator (or a prompted old-prefix finding it can resolve) is safe.
    unsupported_recommendations = [
        rec for rec in migration_recommendations
        if not _is_supported_migration_capability(rec.get("capability_id", ""))
    ]
    prompted_migration_findings = [
        finding.get("id")
        for finding in findings
        if finding.get("fix_recipe", {}).get("type") == "migration"
        and finding.get("fix_type") != "report-only"
    ]
    taxonomy_findings = [
        {
            "id": finding.get("id"),
            "fix_type": finding.get("fix_type"),
            "summary": finding.get("summary"),
        }
        for finding in findings
        if "taxonomy" in str(finding.get("id", ""))
        or "orphan" in str(finding.get("id", ""))
    ]
    passed = (
        result["returncode"] == 0
        and "json_error" not in result
        and not unsupported_recommendations
    )
    return {
        "id": "doctor-migration-scan-safe",
        "status": "passed" if passed else "failed",
        "returncode": result["returncode"],
        "migration_recommendation_count": len(migration_recommendations),
        "unsupported_recommendation_count": len(unsupported_recommendations),
        "prompted_migration_findings": prompted_migration_findings,
        "taxonomy_findings": taxonomy_findings[:10],
        "stderr": result.get("stderr", ""),
        "json_error": result.get("json_error"),
    }


def _migrate_orphan_scan_check(project: Path) -> dict[str, Any]:
    script = Path(__file__).resolve().parents[1] / "migrate" / "migrate-v3-to-v4.py"
    result = _run_json_command([
        sys.executable,
        str(script),
        "scan-orphans",
        "--project-dir",
        str(project),
    ])
    data = result.get("json") if isinstance(result.get("json"), dict) else {}
    findings = data.get("findings", []) if isinstance(data, dict) else []
    orphan_count = data.get("orphan_count") if isinstance(data, dict) else None
    count_matches = orphan_count == len(findings)
    passed = result["returncode"] == 0 and "json_error" not in result and count_matches
    return {
        "id": "migrate-orphan-scan-consistent",
        "status": "passed" if passed else "failed",
        "returncode": result["returncode"],
        "orphan_count": orphan_count,
        "finding_count": len(findings),
        "count_matches": count_matches,
        "sample": findings[:5],
        "stderr": result.get("stderr", ""),
        "json_error": result.get("json_error"),
    }


def _update_skill_contract_check(root: Path | None = None) -> dict[str, Any]:
    base = root or Path(__file__).resolve().parents[2]
    skill = base / "skill-library" / "configure" / "update" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    # These anchors must match the Contract section of skill-library/configure/update/SKILL.md
    # and the assertions in tests/test_recovery_skill.py — the three files
    # move together.
    required = [
        "Update never mutates project work-item state.",
        "Update does not run project-state migrations inline; route project repair to `/sweetclaude:configure doctor`.",
        "Do not present a migration prompt from update.",
        "Do not write `doctor-prompt-pending.json` from update.",
    ]
    missing = [phrase for phrase in required if phrase not in text]
    return {
        "id": "update-skill-taxonomy-prompt-disabled",
        "status": "passed" if not missing else "failed",
        "missing_phrases": missing,
    }


def _update_script_contract_check(root: Path | None = None) -> dict[str, Any]:
    base = root or Path(__file__).resolve().parents[2]
    update_script = base / "scripts" / "update.py"
    producer_script = base / "scripts" / "maintenance" / "plugin-state.py"
    forbidden = [
        "doctor-prompt-pending",
        "reonboard-orphans",
        "archive-orphans",
        "acknowledge-orphans",
        "resolve-orphan",
        "group-orphans",
    ]
    producer_keys = ['"stale_beta_install"', '"SC_PLUGIN_STALE_BETA"']
    missing_files = []
    forbidden_found: list[str] = []
    missing_keys: list[str] = []
    try:
        update_text = update_script.read_text(encoding="utf-8")
        forbidden_found = [marker for marker in forbidden if marker in update_text]
    except OSError:
        missing_files.append(str(update_script))
    try:
        producer_text = producer_script.read_text(encoding="utf-8")
        missing_keys = [key for key in producer_keys if key not in producer_text]
    except OSError:
        missing_files.append(str(producer_script))
    passed = not forbidden_found and not missing_keys and not missing_files
    return {
        "id": "update-script-contract-markers",
        "status": "passed" if passed else "failed",
        "forbidden_markers_found": forbidden_found,
        "missing_producer_keys": missing_keys,
        "missing_files": missing_files,
    }


def _fix_skill_contract_check() -> dict[str, Any]:
    skill = (
        Path(__file__).resolve().parents[2]
        / "skill-library"
        / "configure"
        / "fix-sweetclaude"
        / "SKILL.md"
    )
    text = skill.read_text(encoding="utf-8")
    required = [
        "replaced by `/sweetclaude:configure doctor`",
        "Invoke `sweetclaude:library-load doctor` now.",
    ]
    missing = [phrase for phrase in required if phrase not in text]
    return {
        "id": "fix-sweetclaude-delegates-to-doctor",
        "status": "passed" if not missing else "failed",
        "missing_phrases": missing,
    }


def _maintenance_entrypoint_checks(project: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.append(_doctor_migration_scan_check(project))
    checks.append(_migrate_orphan_scan_check(project))
    checks.append(_update_skill_contract_check())
    checks.append(_update_script_contract_check())
    checks.append(_fix_skill_contract_check())
    return checks


def _read_run_plan(run_dir: Path) -> dict[str, Any]:
    plan_path = run_dir / "plan.json"
    if not plan_path.exists():
        return {}
    return json.loads(plan_path.read_text(encoding="utf-8"))


def _write_recovery_report(
    run_dir: Path,
    result: dict[str, Any],
    rollback: dict[str, Any] | None = None,
) -> str:
    plan = _read_run_plan(run_dir)
    report_path = run_dir / "recovery-report.md"
    applied = {
        operation.get("id"): operation
        for operation in result.get("operations", [])
        if operation.get("status") == "applied"
    }
    lines = [
        "# SweetClaude Recovery Report",
        "",
        f"Run ID: `{result.get('run_id', 'unknown')}`",
        f"Status: `{result.get('status', 'unknown')}`",
        f"Project: `{result.get('project_dir', 'unknown')}`",
        f"Run directory: `{run_dir}`",
        "",
        "## Recovery Route",
        "",
        f"- Route: `{plan.get('recovery_route', 'unknown')}`",
        f"- Plan status: `{plan.get('plan_status', 'unknown')}`",
        f"- Plan ID: `{plan.get('plan_id', result.get('plan_id', 'unknown'))}`",
        "",
        "## What Changed",
        "",
    ]

    operations = plan.get("operations", [])
    if operations:
        for operation in operations:
            status = "applied" if operation.get("id") in applied else "not applied"
            lines.append(
                "- "
                f"`{operation.get('id')}`: {operation.get('action')} "
                f"`{operation.get('target')}` - {status}"
            )
    else:
        lines.append("- No recovery operations were planned.")

    if result.get("error"):
        lines.extend(["", "## Error", "", f"`{result['error']}`"])

    verification = result.get("verification", [])
    lines.extend(["", "## Verification", ""])
    if verification:
        for check in verification:
            lines.append(f"- `{check.get('id')}`: `{check.get('status')}`")
    else:
        lines.append("- Verification has not completed.")

    snapshot = result.get("snapshot", {})
    lines.extend([
        "",
        "## Snapshot And Rollback",
        "",
        f"- Snapshot: `{snapshot.get('path', 'unknown')}`",
        f"- Snapshot file count: `{snapshot.get('file_count', 'unknown')}`",
        f"- Rollback command: `python3 scripts/recovery/recover_project.py rollback --run-dir {run_dir}`",
    ])

    if rollback:
        lines.extend([
            "",
            "## Rollback Status",
            "",
            f"- Status: `{rollback.get('status', 'unknown')}`",
            f"- Snapshot restored from: `{rollback.get('snapshot_path', 'unknown')}`",
        ])

    lines.extend([
        "",
        "## Notes",
        "",
        "- Product artifacts are expected to remain unchanged for this recovery route.",
        "- Taxonomy migration remains blocked until a layout-specific manifest and rollback drill pass.",
        "- Recovery run directories contain snapshots and should stay out of source control. Add `.sweetclaude/state/recovery-runs/` to `.gitignore` if your project does not already ignore it.",
        "",
    ])
    _atomic_write_text(report_path, "\n".join(lines))
    return str(report_path)


def _cli_result(result: dict[str, Any]) -> dict[str, Any]:
    output = json.loads(json.dumps(result))
    snapshot = output.get("snapshot")
    if isinstance(snapshot, dict) and isinstance(snapshot.get("files"), list):
        snapshot["files_omitted_from_cli"] = len(snapshot["files"])
        del snapshot["files"]
    return output


def _verify_execution(project: Path, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    diagnosis = diagnose_project(project)
    checks: list[dict[str, Any]] = []

    stale_complete_ok = "stale-migration-complete-state" not in diagnosis.get(
        "failure_class_codes", []
    )
    checks.append({
        "id": "diagnosis-no-stale-complete-state",
        "status": "passed" if stale_complete_ok else "failed",
    })

    prompts_ok = not diagnosis.get("pending_doctor_prompts")
    checks.append({
        "id": "no-pending-doctor-prompts",
        "status": "passed" if prompts_ok else "failed",
        "pending_doctor_prompts": diagnosis.get("pending_doctor_prompts", []),
    })

    entrypoint_checks = _maintenance_entrypoint_checks(project)
    checks.extend(entrypoint_checks)

    product_ok, changed = _product_files_unchanged(project, snapshot)
    checks.append({
        "id": "no-product-artifact-mutations",
        "status": "passed" if product_ok else "failed",
        "changed_paths": changed[:50],
        "changed_count": len(changed),
    })

    maintenance_ok = (
        stale_complete_ok
        and prompts_ok
        and all(check["status"] == "passed" for check in entrypoint_checks)
    )
    checks.append({
        "id": "maintenance-entrypoints-safe",
        "status": "passed" if maintenance_ok else "failed",
        "checked": [check["id"] for check in entrypoint_checks],
    })

    return checks


def _finalize_execution_result(
    project: Path,
    snapshot: dict[str, Any],
    result: dict[str, Any],
    manifest_path: Path,
) -> dict[str, Any]:
    result["verification"] = _verify_execution(project, snapshot)
    result["status"] = (
        "succeeded"
        if all(check["status"] == "passed" for check in result["verification"])
        else "verification_failed"
    )
    result.pop("error", None)
    result["report_path"] = _write_recovery_report(manifest_path.parent, result)
    _atomic_write_json(manifest_path, result)
    return result


def execute_project(
    project_dir: Path | str,
    approve: bool = False,
    approval_receipt: Path | str | None = None,
    fail_after_operations: int | None = None,
) -> dict[str, Any]:
    if not approve:
        raise PermissionError("execute requires explicit --approve")

    project = Path(project_dir).expanduser().resolve()
    plan = plan_project(project)
    if not plan.get("can_execute_after_snapshot"):
        raise ValueError(f"plan is not executable: {plan.get('plan_status')}")
    _validate_recovery_plan_capability(plan)
    if approval_receipt is None:
        raise PermissionError("execute requires an approval receipt")
    receipt = _load_approval_receipt(Path(approval_receipt))
    approval_validation = _validate_approval_receipt(
        receipt=receipt or {},
        project=project,
        plan=plan,
    )

    before_fingerprint = _project_file_fingerprint(project)
    snapshot = _create_snapshot(project, plan)
    receipt_snapshot_hash = str((receipt or {}).get("snapshot_hash", ""))
    if receipt_snapshot_hash and receipt_snapshot_hash != snapshot["sha256"]:
        raise ValueError("snapshot_hash mismatch")
    snapshot_scope_validation = validate_snapshot_scope(
        declared_blast_radius=plan["mutation_plan"]["declared_blast_radius"],
        snapshot_paths=snapshot["paths"],
    )
    run_dir = Path(snapshot["run_dir"])
    result: dict[str, Any] = {
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "command": "execute",
        "project_dir": str(project),
        "run_id": snapshot["run_id"],
        "run_dir": snapshot["run_dir"],
        "plan_id": plan["plan_id"],
        "status": "in_progress",
        "snapshot": snapshot,
        "operations": [],
        "verification": [],
        "max_resume_attempts": 3,
    }
    manifest_path = run_dir / "execution-manifest.json"
    _atomic_write_json(manifest_path, result)

    try:
        for operation in plan["operations"]:
            applied = _execute_operation(project, operation)
            result["operations"].append(applied)
            _atomic_write_json(manifest_path, result)
            if (
                fail_after_operations is not None
                and len(result["operations"]) >= fail_after_operations
            ):
                raise RuntimeError(
                    f"injected failure after {len(result['operations'])} operation(s)"
                )

        _finalize_execution_result(project, snapshot, result, manifest_path)
        after_fingerprint = _project_file_fingerprint(project)
        write_set_validation = validate_write_set(
            project,
            approved_write_set=plan["mutation_plan"]["declared_write_set"],
            actual_changed_paths=_changed_paths(before_fingerprint, after_fingerprint),
        )
        postcondition_validation = validate_postconditions(
            exit_code=0,
            postconditions=result["verification"],
        )
        result["mutation_lifecycle"] = {
            "status": "pass",
            "mutation_plan": plan["mutation_plan"],
            "approval": approval_validation,
            "snapshot_scope_validation": snapshot_scope_validation,
            "write_set_validation": write_set_validation,
            "postcondition_validation": postcondition_validation,
        }
        _atomic_write_json(manifest_path, result)
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        result["report_path"] = _write_recovery_report(run_dir, result)
        _atomic_write_json(manifest_path, result)
        raise

    return result


def resume_project(run_dir: Path | str) -> dict[str, Any]:
    run_path = Path(run_dir).expanduser().resolve()
    manifest_path = run_path / "execution-manifest.json"
    plan_path = run_path / "plan.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"execution manifest not found: {manifest_path}")
    if not plan_path.exists():
        raise FileNotFoundError(f"plan manifest not found: {plan_path}")

    result = json.loads(manifest_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    _validate_recovery_plan_capability(plan)
    project = Path(result["project_dir"]).resolve()
    snapshot = result.get("snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError("execution manifest does not contain a snapshot")
    snapshot_path = Path(snapshot["path"])
    if not snapshot_path.exists():
        raise FileNotFoundError(f"snapshot not found: {snapshot_path}")

    repair_loop = should_stop_repair_loop(
        attempts=int(result.get("resume_count", 0) or 0),
        max_attempts=int(result.get("max_resume_attempts", 3) or 3),
        previous_postcondition_hash=result.get("previous_postcondition_hash"),
        current_postcondition_hash=result.get("current_postcondition_hash"),
        new_regressions=list(result.get("new_regressions", []) or []),
    )
    if repair_loop["stop"]:
        result = dict(result)
        result["command"] = "resume"
        result["status"] = "stopped"
        result["repair_loop"] = repair_loop
        result["report_path"] = _write_recovery_report(run_path, result)
        _atomic_write_json(manifest_path, result)
        return result

    if result.get("status") == "succeeded":
        result = dict(result)
        result["command"] = "resume"
        result["resume_status"] = "already_succeeded"
        if not result.get("report_path"):
            result["report_path"] = _write_recovery_report(run_path, result)
        return result

    applied_ids = {
        operation.get("id")
        for operation in result.get("operations", [])
        if operation.get("status") == "applied"
    }
    result["command"] = "resume"
    result["status"] = "in_progress"
    result["resumed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result["resume_count"] = int(result.get("resume_count", 0) or 0) + 1
    _atomic_write_json(manifest_path, result)

    try:
        for operation in plan.get("operations", []):
            if operation.get("id") in applied_ids:
                continue
            applied = _execute_operation(project, operation)
            result.setdefault("operations", []).append(applied)
            applied_ids.add(operation.get("id"))
            _atomic_write_json(manifest_path, result)

        _finalize_execution_result(project, snapshot, result, manifest_path)
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        result["report_path"] = _write_recovery_report(run_path, result)
        _atomic_write_json(manifest_path, result)
        raise

    return result


def rollback_project(run_dir: Path | str) -> dict[str, Any]:
    run_path = Path(run_dir).expanduser().resolve()
    manifest_path = run_path / "execution-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"execution manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    project = Path(manifest["project_dir"]).resolve()
    snapshot_path = Path(manifest["snapshot"]["path"]).resolve()
    if not snapshot_path.exists():
        raise FileNotFoundError(f"snapshot not found: {snapshot_path}")

    with tarfile.open(snapshot_path, "r:gz") as tar:
        for member in tar.getmembers():
            target = (project / member.name).resolve()
            if not _is_relative_to(target, project):
                raise ValueError(f"snapshot member escapes project root: {member.name}")
        tar.extractall(project)

    proof = validate_restore_proof({
        "method": "command",
        "status": "pass",
        "command": f"python3 scripts/recovery/recover_project.py rollback --run-dir {run_path}",
        "evidence": f"restored snapshot {snapshot_path}",
    })

    result = {
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "command": "rollback",
        "project_dir": str(project),
        "run_id": manifest.get("run_id"),
        "run_dir": str(run_path),
        "status": "rolled_back",
        "snapshot_path": str(snapshot_path),
        "restore_proof": proof,
    }
    result["report_path"] = _write_recovery_report(run_path, manifest, rollback=result)
    _atomic_write_json(run_path / "rollback-manifest.json", result)
    return result


def plan_project(project_dir: Path | str) -> dict[str, Any]:
    project = Path(project_dir).expanduser().resolve()
    diagnosis = diagnose_project(project)
    route = diagnosis["recovery_route"]
    can_plan = bool(diagnosis["can_plan_recovery"])
    project_shape = _recovery_project_shape(route)
    capability = _recovery_capability_contract(project_shape)

    operations: list[dict[str, Any]] = []
    blocked = _blocked_actions(diagnosis)

    if (
        can_plan
        and route == "stabilize-without-migration"
        and capability["manifest_supported"]
    ):
        operations.extend(_state_operations(project, diagnosis))
        operations.extend(_pending_prompt_operations(diagnosis))

    if route == "no-recovery-needed":
        plan_status = "no-op"
        next_step = "No recovery plan is needed."
    elif can_plan and operations:
        plan_status = "planned"
        next_step = "Create the required snapshot, review the manifest, then execute with approval."
    elif can_plan and not capability["manifest_supported"]:
        plan_status = "manual-review"
        next_step = "Recovery route is recognized, but the manifest capability does not support it."
    elif can_plan:
        plan_status = "manual-review"
        next_step = "Recovery is recognized, but this route has no executable operations yet."
    else:
        plan_status = "not-plannable"
        next_step = "Resolve blocking factors before automated recovery planning."

    plan_id = _plan_id(project, route, operations)
    affected_paths = sorted(dict.fromkeys(op["target"] for op in operations))

    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "command": "plan",
        "plan_id": plan_id,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_dir": str(project),
        "plan_status": plan_status,
        "recovery_route": route,
        "capability_id": capability["capability_id"],
        "project_shape": project_shape,
        "manifest_supported": capability["manifest_supported"],
        "supported_project_shapes": capability["supported_project_shapes"],
        "safety_contract": capability["safety_contract"],
        "verification_commands": capability["verification_commands"],
        "mutating_actions_allowed": False,
        "execute_requires_approval": True,
        "requires_snapshot_before_execute": can_plan,
        "can_execute_after_snapshot": plan_status == "planned",
        "diagnosis_summary": _diagnosis_summary(diagnosis),
        "snapshot": {
            "required": can_plan,
            "scope": "sweetclaude-state-and-product-artifacts",
            "paths": _snapshot_paths(project, diagnosis) if can_plan else [],
        },
        "affected_paths": affected_paths,
        "blocked_actions": blocked,
        "operations": operations,
        "verification": [
            {
                "id": "diagnosis-no-stale-complete-state",
                "description": (
                    "After execution, diagnosis must not report "
                    "stale-migration-complete-state."
                ),
            },
            {
                "id": "no-pending-doctor-prompts",
                "description": "No doctor migration prompt should remain pending.",
            },
            {
                "id": "no-product-artifact-mutations",
                "description": "Product artifacts must have unchanged checksums.",
            },
            {
                "id": "maintenance-entrypoints-safe",
                "description": (
                    "doctor, update, migrate, and fix must not recreate the "
                    "unsafe taxonomy migration loop."
                ),
            },
        ] if can_plan else [],
        "next_step": next_step,
    }
    return _attach_mutation_plan(project, plan)


def diagnose_project(project_dir: Path | str) -> dict[str, Any]:
    project = Path(project_dir).expanduser().resolve()
    characterization = characterize_project(project)
    sweetclaude_state = _read_sweetclaude_state(project)
    pending_prompts = _pending_doctor_prompts(project)

    taxonomy_candidate_count = int(
        characterization.get("migration_risk", {}).get("taxonomy_candidate_count", 0)
        or 0
    )
    old_prefix_count = _old_prefix_count(characterization)
    duplicate_count = int(characterization.get("ids", {}).get("duplicate_count", 0) or 0)
    layout = characterization.get("layout", {})
    has_typed_backlog_dirs = bool(layout.get("has_typed_backlog_dirs"))
    accepted_legacy_layout = _taxonomy_recovery_accepts_legacy_layout(
        sweetclaude_state
    )

    failure_classes: list[dict[str, Any]] = []
    blocking_factors: list[dict[str, Any]] = []

    migration_complete_no_old = (
        sweetclaude_state.get("migration_status") == "complete"
        and old_prefix_count == 0
    )
    compatibility_exited = bool(sweetclaude_state.get("taxonomy_compatibility_exited"))
    # S7: emit unsupported-typed-backlog-layout whenever typed layout + old prefixes exist,
    # even if accepted_legacy_layout is True — migration is now supported so this is
    # a resolvable failure class, not suppressed.
    if has_typed_backlog_dirs and taxonomy_candidate_count and not migration_complete_no_old and not compatibility_exited:
        _add_failure_class(
            failure_classes,
            code="unsupported-typed-backlog-layout",
            severity="recoverable",
            title="Typed backlog layout with legacy taxonomy prefixes",
            evidence={
                "typed_backlog_dirs": characterization.get("counts", {}).get(
                    "typed_backlog_dirs", {}
                ),
                "taxonomy_candidate_count": taxonomy_candidate_count,
            },
            recovery_strategy="migrate",
        )

    migration_status = sweetclaude_state.get("migration_status")
    if migration_status == "complete" and old_prefix_count:
        _add_failure_class(
            failure_classes,
            code="stale-migration-complete-state",
            severity="recoverable",
            title="SweetClaude state says migration is complete while legacy prefixes remain",
            evidence={
                "migration_status": migration_status,
                "old_prefix_count": old_prefix_count,
                "prefixes": characterization.get("counts", {}).get("prefixes", {}),
            },
            recovery_strategy="stabilize-without-migration",
        )

    if pending_prompts:
        _add_failure_class(
            failure_classes,
            code="bad-doctor-migration-recommendation",
            severity="recoverable",
            title="Pending doctor prompt exists and must be revalidated before use",
            evidence={"pending_prompt_files": pending_prompts},
            recovery_strategy="clear-or-rewrite-pending-recommendation",
        )

    if duplicate_count and not accepted_legacy_layout:
        blocking_factors.append({
            "code": "duplicate-work-item-ids",
            "severity": "manual-decision-required-before-taxonomy-migration",
            "detail": "Duplicate IDs block blind taxonomy migration but do not block stabilization.",
            "count": duplicate_count,
            "sample": characterization.get("ids", {}).get("duplicates", [])[:10],
        })

    product_base_exists = bool(characterization.get("product_base_exists"))
    if not product_base_exists:
        blocking_factors.append({
            "code": "product-base-not-found",
            "severity": "cannot-plan",
            "detail": "Recovery cannot plan project artifact changes until product base is resolved.",
        })

    if sweetclaude_state.get("parse_error"):
        blocking_factors.append({
            "code": "sweetclaude-state-parse-error",
            "severity": "cannot-plan",
            "detail": sweetclaude_state["parse_error"],
        })

    drift_findings = _state_schema_drift_findings(project)
    if drift_findings:
        _add_failure_class(
            failure_classes,
            code="state-schema-drift",
            severity="informational",
            title="State files are behind the registry schema",
            evidence={"findings": drift_findings},
            recovery_strategy="run-migration-runner",
        )

    failure_codes = [entry["code"] for entry in failure_classes]
    cannot_plan = any(factor["severity"] == "cannot-plan" for factor in blocking_factors)
    # Informational classes are reported but never drive the route: schema
    # drift belongs to the migration runner (bootstrap Step 5c / doctor
    # auto-fix), not to recovery planning.
    route_driving_classes = [
        entry for entry in failure_classes
        if entry.get("severity") != "informational"
    ]
    has_recoverable_state = bool(route_driving_classes) and not cannot_plan

    has_typed_backlog_failure = _has_failure(
        {"failure_class_codes": [e["code"] for e in route_driving_classes]},
        "unsupported-typed-backlog-layout",
    )

    if not route_driving_classes and not blocking_factors:
        recovery_route = "no-recovery-needed"
        if drift_findings:
            drifted = ", ".join(f["file"] for f in drift_findings)
            next_step = (
                f"No recovery action is needed, but state schema drift was "
                f"detected ({drifted}). The migration runner resolves it — "
                "bootstrap offers this at session start, or run "
                "/sweetclaude:configure doctor to auto-fix."
            )
        else:
            next_step = "No recovery action is currently indicated by read-only diagnosis."
    elif has_recoverable_state and has_typed_backlog_failure and migration_status != "incomplete":
        recovery_route = "typed-legacy-migrate"
        next_step = "Run /sweetclaude:configure migrate to migrate the typed legacy backlog to unified ISSUE-NNN taxonomy."
    elif has_recoverable_state:
        recovery_route = "stabilize-without-migration"
        next_step = "Run recovery plan generation after creating a project snapshot."
    else:
        recovery_route = "manual-escalation"
        next_step = "Resolve blocking factors before automated recovery planning."

    recommended_actions: list[dict[str, str]] = []
    if recovery_route == "typed-legacy-migrate":
        recommended_actions.extend([
            {
                "id": "snapshot-before-migration",
                "description": "Create a complete snapshot of SweetClaude state and product artifacts before migrating.",
            },
            {
                "id": "run-typed-legacy-migration",
                "description": "Run the supported typed-legacy to ISSUE-NNN migrator (dry-run, then execute with rollback).",
            },
            {
                "id": "verify-migration",
                "description": "Verify the migrated project re-characterizes as a clean v4 layout.",
            },
        ])
    elif has_recoverable_state:
        recommended_actions.extend([
            {
                "id": "snapshot-before-recovery",
                "description": "Create a complete snapshot of SweetClaude state and product artifacts.",
            },
            {
                "id": "plan-stabilize-without-taxonomy-migration",
                "description": "Generate a reversible plan that disables unsafe migration loops.",
            },
            {
                "id": "verify-maintenance-entrypoints",
                "description": "Verify doctor, update, migrate, and fix do not recreate the failure loop.",
            },
        ])
    elif recovery_route == "manual-escalation":
        recommended_actions.append({
            "id": "manual-review",
            "description": "Review blocking factors before allowing automated recovery.",
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "command": "diagnose",
        "project_dir": str(project),
        "mutating_actions_allowed": False,
        "characterization": characterization,
        "sweetclaude_state": sweetclaude_state,
        "pending_doctor_prompts": pending_prompts,
        "failure_classes": failure_classes,
        "failure_class_codes": failure_codes,
        "blocking_factors": blocking_factors,
        "recovery_route": recovery_route,
        "can_plan_recovery": has_recoverable_state,
        "requires_snapshot_before_execute": has_recoverable_state,
        "next_step": next_step,
        "recommended_actions": recommended_actions,
    }


def graduation_check(project_dir: Path | str) -> dict[str, Any]:
    """Read-only validation: is this project v4-compliant and ready to exit compatibility mode?"""
    project = Path(project_dir).expanduser().resolve()
    characterization = characterize_project(project)
    state = _read_sweetclaude_state(project)

    taxonomy_status = state.get("taxonomy_recovery_status")
    if taxonomy_status not in ("stabilized-without-migration", "migrated", None):
        if taxonomy_status == "graduated":
            return {
                "graduation_allowed": False,
                "reason": "already-graduated",
                "detail": "This project has already graduated from compatibility mode.",
            }

    accepted = _taxonomy_recovery_accepts_legacy_layout(state)
    # S7: also allow graduation after successful typed-legacy migration
    migrated = taxonomy_status == "migrated"
    if not accepted and not migrated and taxonomy_status != "stabilized-without-migration":
        return {
            "graduation_allowed": False,
            "reason": "not-in-compatibility-mode",
            "detail": "Project is not in compatibility mode or accepted legacy taxonomy state.",
        }

    v4c = characterization.get("v4_compliance", {})
    blockers: list[dict[str, Any]] = []

    if not v4c.get("is_v4_only"):
        blockers.append({
            "code": "old-prefix-files-remain",
            "detail": f"{v4c.get('old_prefix_count', 0)} files with old taxonomy prefixes remain.",
        })

    if not v4c.get("no_duplicates"):
        dup_count = characterization.get("ids", {}).get("duplicate_count", 0)
        blockers.append({
            "code": "duplicate-ids",
            "detail": f"{dup_count} duplicate work-item IDs found.",
        })

    if not v4c.get("has_required_fields"):
        blockers.append({
            "code": "missing-required-fields",
            "detail": "One or more work items are missing required fields (id, type, title, status).",
        })

    if not v4c.get("canonical_types_only"):
        blockers.append({
            "code": "legacy-type-aliases",
            "detail": "One or more work items use legacy type aliases (bug, feature, debt, chore).",
        })

    if characterization.get("frontmatter", {}).get("parse_errors", 0) > 0:
        blockers.append({
            "code": "frontmatter-parse-errors",
            "detail": f"{characterization['frontmatter']['parse_errors']} files have unparseable frontmatter.",
        })

    if not v4c.get("standard_structure"):
        blockers.append({
            "code": "non-standard-structure",
            "detail": "Project layout does not match standard v4 structure.",
        })

    if blockers:
        return {
            "graduation_allowed": False,
            "reason": "validation-failures",
            "blockers": blockers,
            "v4_compliance": v4c,
        }

    return {
        "graduation_allowed": True,
        "reason": "v4-compliant",
        "v4_compliance": v4c,
    }


def graduate(project_dir: Path | str) -> dict[str, Any]:
    """Execute graduation: write state marking project as graduated from compatibility mode.

    Precondition: graduation_check must pass. This function re-validates before writing.
    """
    project = Path(project_dir).expanduser().resolve()
    check = graduation_check(project)
    if not check.get("graduation_allowed"):
        return {
            "status": "blocked",
            "reason": check.get("reason", "unknown"),
            "detail": check.get("blockers", check.get("detail", "")),
        }

    sc_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    if not sc_path.exists():
        return {"status": "error", "reason": "sweetclaude-yaml-missing"}

    data = _load_yaml_mapping(sc_path)
    now = datetime.now(timezone.utc).isoformat()

    recovery = data.setdefault("recovery", {})
    taxonomy = recovery.setdefault("taxonomy", {})
    taxonomy["status"] = "graduated"
    taxonomy["compatibility_exited"] = True
    taxonomy["migration_required"] = False
    taxonomy["graduated_at"] = now

    framework = data.setdefault("framework", {})
    framework["migration_status"] = "complete"

    _write_yaml_mapping(sc_path, data)

    return {
        "status": "graduated",
        "graduated_at": now,
        "sweetclaude_yaml_path": str(sc_path),
    }


_BLOCKER_RESOLUTION_CAPABILITY = "doctor.fix_graduation_blockers"
_RESOLVABLE_BLOCKER_CODES = {"duplicate-ids"}

# Blockers doctor's prompted-fix flow can clear, even without a deterministic
# one-shot command. Structural blockers (old taxonomy prefixes, non-standard
# layout) are NOT here: fixing those means migration, which stays blocked by
# policy — those projects remain honestly in compatibility mode.
_FIXABLE_BLOCKER_CODES = _RESOLVABLE_BLOCKER_CODES | {
    "legacy-type-aliases",
    "missing-required-fields",
    "frontmatter-parse-errors",
}


def _with_blocker_resolution(blocker: dict[str, Any]) -> dict[str, Any]:
    code = str(blocker.get("code", ""))
    resolution: dict[str, Any] = {
        "capability_id": _BLOCKER_RESOLUTION_CAPABILITY,
        "delegate_skill": "sweetclaude:library-load doctor",
    }
    if code in _RESOLVABLE_BLOCKER_CODES:
        script = Path(__file__).resolve()
        resolution["command"] = (
            f"python3 {script} resolve-graduation-blocker "
            f"--code {code} --project-dir <project>"
        )
    return {**blocker, "resolution": resolution}


def _frontmatter_id(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    for line in parts[1].splitlines():
        if line.startswith("id:"):
            value = line.split(":", 1)[1].strip().strip("'\"")
            return value or None
    return None


_WORK_ITEM_ID_RE = re.compile(r"^[A-Z]+(?:-[A-Z0-9]+)*-\d+$")


def _collect_known_ids(product_base: Path) -> set[str]:
    ids: set[str] = set()
    for path in product_base.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(product_base).as_posix()
        except ValueError:
            continue
        if is_derived_file(rel):
            continue
        value = _frontmatter_id(path)
        if value:
            ids.add(value)
    return ids


def _next_available_id(duplicate_id: str, known_ids: set[str]) -> str:
    prefix, _, number = duplicate_id.rpartition("-")
    width = len(number)
    highest = 0
    for known in known_ids:
        k_prefix, _, k_number = known.rpartition("-")
        if k_prefix == prefix and k_number.isdigit():
            highest = max(highest, int(k_number))
    return f"{prefix}-{highest + 1:0{width}d}"


def _pick_renumber_targets(
    files: list[Path], product_base: Path, choose: str | None,
) -> list[Path]:
    if choose:
        chosen = Path(choose).expanduser().resolve()
        matches = [f for f in files if f.resolve() == chosen]
        if not matches:
            raise ValueError(
                f"--choose did not match a duplicate file: {choose}"
            )
        return matches
    ordered = sorted(files)
    in_backlog = [
        f for f in ordered
        if f.resolve().is_relative_to(product_base)
        and f.resolve().relative_to(product_base).parts[:1] == ("backlog",)
    ]
    canonical = in_backlog[0] if in_backlog else ordered[0]
    return [f for f in ordered if f != canonical]


def resolve_graduation_blocker(
    project_dir: Path | str, code: str, choose: str | None = None,
) -> dict[str, Any]:
    """Resolve a graduation blocker through doctor's executor (archived, reversible).

    Only blocker codes with a deterministic resolution are supported here;
    everything else routes to the doctor skill's prompted-fix flow.
    """
    project = Path(project_dir).expanduser().resolve()
    if code not in _RESOLVABLE_BLOCKER_CODES:
        return {
            "status": "unsupported",
            "code": code,
            "detail": (
                f"No deterministic resolution for blocker '{code}'. "
                "Run /sweetclaude:configure doctor for the prompted-fix flow."
            ),
        }

    characterization = characterize_project(project)
    product_base = Path(
        characterization.get("product_base")
        or project / ".sweetclaude" / "product"
    ).resolve()
    duplicates = characterization.get("ids", {}).get("duplicates", [])
    if not duplicates:
        return {
            "status": "nothing-to-resolve",
            "code": code,
            "detail": "No duplicate work-item IDs found.",
        }

    known_ids = _collect_known_ids(product_base)
    doctor_script = SCRIPTS_DIR / "doctor.py"

    archive_result = subprocess.run(
        [sys.executable, str(doctor_script), "create-archive",
         "--project-dir", str(project)],
        capture_output=True, text=True, check=False,
    )
    if archive_result.returncode != 0:
        return {
            "status": "error",
            "detail": f"create-archive failed: {archive_result.stderr}",
        }
    archive_dir = json.loads(archive_result.stdout)["archive_dir"]

    findings: list[dict[str, Any]] = []
    renumbered: list[dict[str, Any]] = []
    renamed: list[dict[str, Any]] = []
    for group in duplicates:
        dup_id = str(group.get("id", ""))
        files = [
            (product_base / f) if not Path(f).is_absolute() else Path(f)
            for f in group.get("files", [])
        ]
        # The duplicate groups key on FILENAME ids (characterize_project).
        # A file whose frontmatter carries a different valid id is misnamed,
        # not duplicated: rename it to match its frontmatter. Renumbering it
        # would clobber a valid id other artifacts may reference.
        colliding: list[Path] = []
        for path in files:
            fm_id = _frontmatter_id(path)
            if fm_id and fm_id != dup_id and _WORK_ITEM_ID_RE.match(fm_id):
                dest = path.parent / path.name.replace(dup_id, fm_id, 1)
                findings.append({
                    "id": f"graduation-blocker:misnamed-file:{path.name}",
                    "category": "file_diagnostics",
                    "summary": (
                        f"Rename {path.name} to match its frontmatter id {fm_id}"
                    ),
                    "fix_type": "prompted",
                    "fix_recipe": {
                        "action": "file_move",
                        "src": str(path),
                        "dest": str(dest),
                        "file": str(path),
                    },
                })
                renamed.append({
                    "id": fm_id,
                    "from": str(path),
                    "to": str(dest),
                })
            else:
                colliding.append(path)

        if len(colliding) < 2:
            continue
        targets = _pick_renumber_targets(colliding, product_base, choose)
        for target in targets:
            new_id = _next_available_id(dup_id, known_ids)
            known_ids.add(new_id)
            findings.append({
                "id": f"graduation-blocker:duplicate-id:{dup_id}",
                "category": "file_diagnostics",
                "summary": f"Renumber duplicate {dup_id} -> {new_id}",
                "fix_type": "prompted",
                "fix_recipe": {
                    "action": "renumber_duplicate",
                    "file": str(target),
                    "old_id": dup_id,
                    "new_id": new_id,
                },
            })
            renumbered.append({
                "old_id": dup_id,
                "new_id": new_id,
                "file": str(target),
            })

    fix_result = subprocess.run(
        [sys.executable, str(doctor_script), "auto-fix",
         "--project-dir", str(project),
         "--archive-dir", archive_dir,
         "--include-prompted"],
        input=json.dumps(findings),
        capture_output=True, text=True, check=False,
    )
    if fix_result.returncode != 0:
        return {
            "status": "error",
            "detail": f"auto-fix failed: {fix_result.stderr}",
            "archive_dir": archive_dir,
        }
    fix_payload = json.loads(fix_result.stdout)
    failed = [
        a for a in fix_payload.get("actions", [])
        if a.get("action") == "auto-fix-failed"
    ]
    if failed:
        return {
            "status": "error",
            "detail": f"{len(failed)} renumber action(s) failed",
            "failed_actions": failed,
            "archive_dir": archive_dir,
        }

    return {
        "status": "resolved",
        "code": code,
        "renumbered": renumbered,
        "renamed": renamed,
        "archive_dir": archive_dir,
        "restore_hint": (
            f"python3 {doctor_script} restore --project-dir {project} "
            f"--archive-dir {archive_dir}"
        ),
    }


def _get_real_duplicate_ids(project: Path, characterization: dict[str, Any]) -> list[str]:
    """Return a list of duplicate work-item IDs from the characterization.

    Only counts real (non-backup/non-derived) files. Uses is_derived_file
    to exclude .bak and other derived files.
    """
    duplicates = characterization.get("ids", {}).get("duplicates", [])
    if not duplicates:
        return []
    real_dup_ids: list[str] = []
    for group in duplicates:
        dup_id = str(group.get("id", ""))
        files = group.get("files", [])
        real_files = [
            f for f in files
            if not is_derived_file(str(f))
        ]
        if len(real_files) >= 2:
            real_dup_ids.append(dup_id)
    return real_dup_ids


def guard_project(project_dir: Path | str) -> dict[str, Any]:
    """Return a concise read-only routing decision for migration guards."""
    project = Path(project_dir).expanduser().resolve()
    diagnosis = diagnose_project(project)
    characterization = diagnosis.get("characterization", {})
    state = diagnosis.get("sweetclaude_state", {})

    product_base = characterization.get("product_base")
    product_base_exists = bool(characterization.get("product_base_exists"))
    standard_product_dir_exists = (project / ".sweetclaude" / "product").is_dir()
    old_prefix_count = _old_prefix_count(characterization)
    prefix_counts = characterization.get("counts", {}).get("prefixes", {})
    flat_bl_count = int(prefix_counts.get("BL", 0) or 0) if isinstance(prefix_counts, dict) else 0
    has_typed_backlog_dirs = bool(
        characterization.get("layout", {}).get("has_typed_backlog_dirs")
    )
    accepted_legacy_layout = _taxonomy_recovery_accepts_legacy_layout(state)
    route = diagnosis.get("recovery_route")

    graduation_blockers: list[dict[str, Any]] = []

    # S7: typed-legacy-migrate route is primary check for typed layout
    if route == "typed-legacy-migrate":
        project_shape = "typed_legacy_backlog"
        duplicate_ids = _get_real_duplicate_ids(project, characterization)
        if duplicate_ids:
            # Surface duplicates as graduation_blockers so they appear in the payload
            # and the user can see which ids need resolution before migration.
            graduation_blockers = [{
                "code": "duplicate-ids",
                "detail": f"Duplicate work-item IDs must be resolved before migration: {', '.join(sorted(duplicate_ids))}",
                "duplicate_ids": sorted(duplicate_ids),
                "resolution": {
                    "capability_id": "doctor.fix_graduation_blockers",
                    "delegate_skill": "sweetclaude:library-load doctor",
                },
            }]
    elif route == "stabilize-without-migration":
        project_shape = "recovery_required"
    elif route == "manual-escalation":
        project_shape = "manual_escalation"
    elif accepted_legacy_layout and old_prefix_count == 0:
        # No old prefixes remain — check graduation eligibility
        grad_check = graduation_check(project)
        if grad_check.get("graduation_allowed"):
            project_shape = "graduation_candidate"
        elif grad_check.get("reason") == "validation-failures" and all(
            b.get("code") in _FIXABLE_BLOCKER_CODES
            for b in grad_check.get("blockers", [])
        ):
            project_shape = "graduation_blocked"
            graduation_blockers = [
                _with_blocker_resolution(b)
                for b in grad_check.get("blockers", [])
            ]
        else:
            project_shape = "accepted_legacy_taxonomy"
    elif accepted_legacy_layout and old_prefix_count:
        # Stabilized but old prefixes still on disk — route to migration
        project_shape = "typed_legacy_backlog"
        duplicate_ids = _get_real_duplicate_ids(project, characterization)
        if duplicate_ids:
            graduation_blockers = [{
                "code": "duplicate-ids",
                "detail": f"Duplicate work-item IDs must be resolved before migration: {', '.join(sorted(duplicate_ids))}",
                "duplicate_ids": sorted(duplicate_ids),
                "resolution": {
                    "capability_id": "doctor.fix_graduation_blockers",
                    "delegate_skill": "sweetclaude:library-load doctor",
                },
            }]
    elif old_prefix_count and flat_bl_count and not has_typed_backlog_dirs:
        project_shape = "flat_bl_backlog"
    elif old_prefix_count:
        project_shape = "manual_escalation"
    elif not product_base_exists:
        project_shape = "missing_product_base"
    else:
        project_shape = "current_layout"

    shape_config = project_shape_config(project_shape)
    status = str(shape_config.get("guard_status", "") or "")
    migrate_allowed = bool(shape_config.get("migrate_allowed", False))
    message = str(shape_config.get("message", "") or "")

    # S7: collect real duplicate ids from graduation_blockers for payload inclusion
    real_dup_ids_flat: list[str] = []
    for b in graduation_blockers:
        if b.get("code") == "duplicate-ids":
            real_dup_ids_flat.extend(b.get("duplicate_ids", []))

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": "guard",
        "project_dir": str(project),
        "status": status,
        "message": message,
        "project_shape": project_shape,
        "recovery_route": route,
        "migrate_allowed": migrate_allowed,
        "standard_product_dir_exists": standard_product_dir_exists,
        "product_base": product_base,
        "product_base_exists": product_base_exists,
        "old_prefix_count": old_prefix_count,
        "graduation_blockers": graduation_blockers,
        "failure_class_codes": diagnosis.get("failure_class_codes", []),
        "blocking_factor_codes": [
            factor.get("code") for factor in diagnosis.get("blocking_factors", [])
        ],
        "pending_doctor_prompts": diagnosis.get("pending_doctor_prompts", []),
        "taxonomy_recovery_status": state.get("taxonomy_recovery_status"),
    }
    if real_dup_ids_flat:
        payload["duplicate_ids"] = sorted(set(real_dup_ids_flat))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SweetClaude project recovery")
    subparsers = parser.add_subparsers(dest="command")

    guard_parser = subparsers.add_parser(
        "guard",
        help="Read-only migration/recovery guard decision",
    )
    guard_parser.add_argument("--project-dir", default=".", help="Project directory")
    guard_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    diagnose_parser = subparsers.add_parser(
        "diagnose",
        help="Read-only project recovery diagnosis",
    )
    diagnose_parser.add_argument("--project-dir", default=".", help="Project directory")
    diagnose_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    plan_parser = subparsers.add_parser(
        "plan",
        help="Build a non-mutating recovery manifest",
    )
    plan_parser.add_argument("--project-dir", default=".", help="Project directory")
    plan_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    execute_parser = subparsers.add_parser(
        "execute",
        help="Execute an approved recovery manifest",
    )
    execute_parser.add_argument("--project-dir", default=".", help="Project directory")
    execute_parser.add_argument(
        "--approve",
        action="store_true",
        help="Required confirmation for mutating recovery execution",
    )
    execute_parser.add_argument(
        "--approval-receipt",
        type=Path,
        help="Approval receipt generated from the current recovery plan",
    )
    execute_parser.add_argument(
        "--fail-after-operations",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )
    execute_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    rollback_parser = subparsers.add_parser(
        "rollback",
        help="Restore a project from a recovery run snapshot",
    )
    rollback_parser.add_argument("--run-dir", required=True, help="Recovery run directory")
    rollback_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume an interrupted recovery run",
    )
    resume_parser.add_argument("--run-dir", required=True, help="Recovery run directory")
    resume_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    grad_check_parser = subparsers.add_parser(
        "graduation-check",
        help="Read-only check: is this project ready to graduate from compatibility mode?",
    )
    grad_check_parser.add_argument("--project-dir", default=".", help="Project directory")
    grad_check_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    grad_parser = subparsers.add_parser(
        "graduate",
        help="Graduate project from compatibility mode (state-only write)",
    )
    grad_parser.add_argument("--project-dir", default=".", help="Project directory")
    grad_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    resolve_parser = subparsers.add_parser(
        "resolve-graduation-blocker",
        help="Resolve a graduation blocker through doctor's executor (archived, reversible)",
    )
    resolve_parser.add_argument("--project-dir", default=".", help="Project directory")
    resolve_parser.add_argument("--code", required=True, help="Blocker code to resolve")
    resolve_parser.add_argument(
        "--choose", default=None,
        help="Duplicate file to renumber (defaults to the non-canonical copy)",
    )
    resolve_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    args = parser.parse_args(argv)

    try:
        if args.command is None:
            result = diagnose_project(Path("."))
        elif args.command == "guard":
            result = guard_project(Path(args.project_dir))
        elif args.command == "diagnose":
            result = diagnose_project(Path(args.project_dir))
        elif args.command == "plan":
            result = plan_project(Path(args.project_dir))
        elif args.command == "execute":
            result = execute_project(
                Path(args.project_dir),
                approve=args.approve,
                approval_receipt=args.approval_receipt,
                fail_after_operations=args.fail_after_operations,
            )
        elif args.command == "rollback":
            result = rollback_project(Path(args.run_dir))
        elif args.command == "resume":
            result = resume_project(Path(args.run_dir))
        elif args.command == "graduation-check":
            result = graduation_check(Path(args.project_dir))
        elif args.command == "graduate":
            result = graduate(Path(args.project_dir))
        elif args.command == "resolve-graduation-blocker":
            result = resolve_graduation_blocker(
                Path(args.project_dir), args.code, choose=args.choose,
            )
        else:
            parser.error(f"unsupported command: {args.command}")
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2

    pretty = bool(getattr(args, "pretty", False))
    print(json.dumps(_cli_result(result), indent=2 if pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
