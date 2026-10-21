#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Load SweetClaude release-channel and capability safety metadata."""
from __future__ import annotations

import os
import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


MANIFEST_RELATIVE_PATH = Path("config") / "capability-manifest.yaml"
MUTATION_CLASSES = {"read_only", "planned_write", "destructive", "release"}
UNSUPPORTED_STATE_BEHAVIORS = {"diagnose_only", "block", "escalate"}
LOCAL_PROOF_KINDS = ("live-enforcement", "routing", "upgrade-path", "docs-claims")


def _versionless_config_path() -> Path:
    return Path.home() / ".claude" / "config" / "sweetclaude" / "capability-manifest.yaml"


def _candidate_paths() -> list[Path]:
    script_path = Path(__file__).resolve()
    candidates = [
        # Dev clone and plugin-cache install layout.
        script_path.parents[2] / MANIFEST_RELATIVE_PATH,
        # Versionless installed script layout.
        _versionless_config_path(),
    ]
    explicit = os.environ.get("SWEETCLAUDE_CAPABILITY_MANIFEST")
    if explicit:
        candidates.insert(0, Path(explicit))
    return candidates


def _require_bool(config: dict[str, Any], key: str, context: str) -> None:
    if not isinstance(config.get(key), bool):
        raise ValueError(f"Capability manifest {context}.{key} must be a boolean")


def _require_string_list(config: dict[str, Any], key: str, context: str) -> list[str]:
    value = config.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Capability manifest {context}.{key} must be a string list")
    return value


def _require_optional_string(config: dict[str, Any], key: str, context: str) -> None:
    value = config.get(key)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"Capability manifest {context}.{key} must be a string or null")


def _validate_command_entrypoint(config: dict[str, Any], context: str) -> None:
    entrypoint = config.get("command_entrypoint")
    if entrypoint is None:
        return
    if not isinstance(entrypoint, dict):
        raise ValueError(f"Capability manifest {context}.command_entrypoint must be a mapping")
    for key in ("slash_command", "script", "module"):
        _require_optional_string(entrypoint, key, f"{context}.command_entrypoint")


def _validate_postconditions(config: dict[str, Any], context: str) -> None:
    postconditions = config.get("postconditions")
    if postconditions is None:
        return
    if not isinstance(postconditions, list):
        raise ValueError(f"Capability manifest {context}.postconditions must be a list")
    for index, postcondition in enumerate(postconditions, start=1):
        pc_context = f"{context}.postconditions[{index}]"
        if not isinstance(postcondition, dict):
            raise ValueError(f"Capability manifest {pc_context} must be a mapping")
        for key in ("id", "check"):
            if not isinstance(postcondition.get(key), str) or not postcondition[key]:
                raise ValueError(f"Capability manifest {pc_context}.{key} must be a non-empty string")


def _validate_rollback_support(config: dict[str, Any], context: str) -> None:
    rollback = config.get("rollback_support")
    if rollback is None:
        if config.get("mutates_project"):
            raise ValueError(f"Capability manifest {context}.rollback_support is required for mutating capabilities")
        return
    if not isinstance(rollback, dict):
        raise ValueError(f"Capability manifest {context}.rollback_support must be a mapping")
    if not isinstance(rollback.get("supported"), bool):
        raise ValueError(f"Capability manifest {context}.rollback_support.supported must be a boolean")
    if config.get("mutates_project") and not rollback["supported"]:
        raise ValueError(f"Capability manifest {context}.rollback_support.supported must be true for mutating capabilities")
    command = rollback.get("command")
    if rollback["supported"] and (not isinstance(command, str) or not command):
        raise ValueError(f"Capability manifest {context}.rollback_support.command must be a non-empty string when rollback is supported")
    _require_string_list(rollback, "limitations", f"{context}.rollback_support")


def _validate_unsupported_states(config: dict[str, Any], context: str) -> None:
    unsupported_states = config.get("unsupported_states")
    if unsupported_states is None:
        return
    if not isinstance(unsupported_states, list):
        raise ValueError(f"Capability manifest {context}.unsupported_states must be a list")
    for index, state in enumerate(unsupported_states, start=1):
        state_context = f"{context}.unsupported_states[{index}]"
        if not isinstance(state, dict):
            raise ValueError(f"Capability manifest {state_context} must be a mapping")
        if not isinstance(state.get("condition"), str) or not state["condition"]:
            raise ValueError(f"Capability manifest {state_context}.condition must be a non-empty string")
        behavior = state.get("behavior")
        if behavior not in UNSUPPORTED_STATE_BEHAVIORS:
            raise ValueError(
                f"Capability manifest {state_context}.behavior must be one of "
                f"{sorted(UNSUPPORTED_STATE_BEHAVIORS)}"
            )


def _validate_version_metadata(config: dict[str, Any], context: str) -> None:
    version_metadata = config.get("version_metadata")
    if version_metadata is None:
        return
    if not isinstance(version_metadata, dict):
        raise ValueError(f"Capability manifest {context}.version_metadata must be a mapping")
    _require_optional_string(version_metadata, "introduced_in", f"{context}.version_metadata")
    _require_optional_string(version_metadata, "deprecated_in", f"{context}.version_metadata")


def validate_manifest(data: dict[str, Any]) -> None:
    """Validate the capability manifest graph and high-stakes safety fields."""
    channels = data.get("channels")
    if not isinstance(channels, dict) or not channels:
        raise ValueError("Capability manifest must define channels")
    for channel, config in channels.items():
        context = f"channels.{channel}"
        if not isinstance(config, dict):
            raise ValueError(f"Capability manifest {context} must be a mapping")
        for key in ("branch", "expected_marketplace"):
            if not isinstance(config.get(key), str) or not config[key]:
                raise ValueError(f"Capability manifest {context}.{key} must be a non-empty string")
        if not isinstance(config.get("major_version"), int):
            raise ValueError(f"Capability manifest {context}.major_version must be an integer")
        _require_bool(config, "prerelease_required", context)
        _require_bool(config, "prerelease_allowed", context)
        if config.get("retired") is not None and not isinstance(config["retired"], bool):
            raise ValueError(f"Capability manifest {context}.retired must be a boolean")
        target = config.get("retirement_target_channel")
        if config.get("retired") is True:
            if not isinstance(target, str) or target not in channels:
                raise ValueError(
                    f"Capability manifest {context}.retirement_target_channel must name a defined channel"
                )
            if channels[target].get("retired") is True:
                raise ValueError(
                    f"Capability manifest {context}.retirement_target_channel must not be a retired channel"
                )

    release = data.get("release")
    if not isinstance(release, dict):
        raise ValueError("Capability manifest must define release")
    _require_string_list(release, "required_evidence_checks", "release")

    local_proofs = release.get("required_local_proofs")
    if local_proofs is not None:
        if not isinstance(local_proofs, dict):
            raise ValueError("Capability manifest release.required_local_proofs must be a mapping")
        for channel, kinds in local_proofs.items():
            context = f"release.required_local_proofs.{channel}"
            if channel not in channels:
                raise ValueError(f"Capability manifest {context} must name a defined channel")
            if not isinstance(kinds, list) or not all(isinstance(kind, str) for kind in kinds):
                raise ValueError(f"Capability manifest {context} must be a string list")
            unknown = sorted(set(kinds) - set(LOCAL_PROOF_KINDS))
            if unknown:
                raise ValueError(
                    f"Capability manifest {context} references unknown local proof kinds: "
                    + ", ".join(unknown)
                )
            if len(set(kinds)) != len(kinds):
                raise ValueError(f"Capability manifest {context} must not contain duplicate local proof kinds")

    capabilities = data.get("capabilities")
    if not isinstance(capabilities, dict) or not capabilities:
        raise ValueError("Capability manifest must define capabilities")

    project_shapes = data.get("project_shapes")
    if not isinstance(project_shapes, dict) or not project_shapes:
        raise ValueError("Capability manifest must define project_shapes")

    for capability_id, config in capabilities.items():
        context = f"capabilities.{capability_id}"
        if not isinstance(config, dict):
            raise ValueError(f"Capability manifest {context} must be a mapping")
        if not isinstance(config.get("title"), str) or not config["title"]:
            raise ValueError(f"Capability manifest {context}.title must be a non-empty string")
        supported_shapes = _require_string_list(config, "supports_project_shapes", context)
        for shape in supported_shapes:
            if shape not in project_shapes:
                raise ValueError(
                    f"Capability manifest {context}.supports_project_shapes references unknown shape: {shape}"
                )
        _require_bool(config, "mutates_project", context)
        _require_bool(config, "requires_approval", context)
        if config.get("supported") is not None:
            _require_bool(config, "supported", context)
        if config.get("mutates_project") and not config.get("requires_approval"):
            raise ValueError(f"Capability manifest {context} mutates_project requires approval")
        mutation_class = config.get("mutation_class")
        if mutation_class is not None and mutation_class not in MUTATION_CLASSES:
            raise ValueError(
                f"Capability manifest {context}.mutation_class must be one of {sorted(MUTATION_CLASSES)}"
            )
        if config.get("mutates_project") and mutation_class not in {
            "planned_write", "destructive", "release",
        }:
            raise ValueError(
                f"Capability manifest {context}.mutation_class must describe mutating behavior"
            )
        if not config.get("mutates_project") and mutation_class in {"planned_write", "destructive"}:
            raise ValueError(
                f"Capability manifest {context}.mutation_class cannot be mutating when mutates_project is false"
            )
        _validate_command_entrypoint(config, context)
        if config.get("required_preconditions") is not None:
            _require_string_list(config, "required_preconditions", context)
        if config.get("snapshot_scope_hints") is not None:
            _require_string_list(config, "snapshot_scope_hints", context)
        _validate_postconditions(config, context)
        _validate_rollback_support(config, context)
        _validate_unsupported_states(config, context)
        _validate_version_metadata(config, context)

    for shape, config in project_shapes.items():
        context = f"project_shapes.{shape}"
        if not isinstance(config, dict):
            raise ValueError(f"Capability manifest {context} must be a mapping")
        if not isinstance(config.get("guard_status"), str) or not config["guard_status"]:
            raise ValueError(f"Capability manifest {context}.guard_status must be a non-empty string")
        _require_bool(config, "migrate_allowed", context)
        for key in ("recovery_capability", "doctor_capability", "migration_capability"):
            capability_id = config.get(key)
            if capability_id is None:
                continue
            if capability_id not in capabilities:
                raise ValueError(f"Capability manifest {context}.{key} references unknown capability: {capability_id}")
            supported_shapes = capabilities[capability_id].get("supports_project_shapes") or []
            if shape not in supported_shapes:
                raise ValueError(
                    f"Capability manifest {context}.{key} capability does not support shape: {shape}"
                )
        for capability_id in config.get("blocked_capabilities") or []:
            if capability_id not in capabilities:
                raise ValueError(
                    f"Capability manifest {context}.blocked_capabilities references unknown capability: {capability_id}"
                )


def load_manifest(path: Path | str | None = None) -> dict[str, Any]:
    candidates = [Path(path)] if path else _candidate_paths()
    manifest_path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"Capability manifest not found: {manifest_path}") from None
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid capability manifest YAML: {manifest_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Capability manifest must be a mapping: {manifest_path}")
    if data.get("schema_version") != 1:
        raise ValueError("Capability manifest schema_version must be 1")
    validate_manifest(data)
    return data


def channel_config(channel: str, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    data = manifest or load_manifest()
    channels = data.get("channels") or {}
    config = channels.get(channel)
    if not isinstance(config, dict):
        raise ValueError(f"Unknown SweetClaude channel: {channel}")
    return config


def expected_ref(channel: str, manifest: dict[str, Any] | None = None) -> str:
    return str(channel_config(channel, manifest).get("branch", "") or "")


def expected_marketplace(channel: str, manifest: dict[str, Any] | None = None) -> str:
    return str(channel_config(channel, manifest).get("expected_marketplace", "") or "")


def minimum_safe_version(channel: str, manifest: dict[str, Any] | None = None) -> str:
    return str(channel_config(channel, manifest).get("minimum_safe_version", "") or "")


def channel_retired(channel: str, manifest: dict[str, Any] | None = None) -> bool:
    return bool(channel_config(channel, manifest).get("retired", False))


def control_lint_required(channel: str, manifest: dict[str, Any] | None = None) -> bool:
    return bool(channel_config(channel, manifest).get("control_lint_required", False))


def retirement_target_channel(channel: str, manifest: dict[str, Any] | None = None) -> str:
    return str(channel_config(channel, manifest).get("retirement_target_channel", "") or "")


def required_release_checks(manifest: dict[str, Any] | None = None) -> set[str]:
    data = manifest or load_manifest()
    release = data.get("release") or {}
    checks = release.get("required_evidence_checks")
    if not isinstance(checks, list) or not all(isinstance(check, str) for check in checks):
        raise ValueError("Capability manifest release.required_evidence_checks must be a string list")
    return set(checks)


def required_local_proofs(channel: str, manifest: dict[str, Any] | None = None) -> list[str]:
    data = manifest or load_manifest()
    release = data.get("release") or {}
    scoped = release.get("required_local_proofs") or {}
    if not isinstance(scoped, dict):
        raise ValueError("Capability manifest release.required_local_proofs must be a mapping")
    kinds = scoped.get(channel) or []
    if not isinstance(kinds, list) or not all(isinstance(kind, str) for kind in kinds):
        raise ValueError(
            f"Capability manifest release.required_local_proofs.{channel} must be a string list"
        )
    return list(kinds)


def capability_config(
    capability_id: str, manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = manifest or load_manifest()
    capabilities = data.get("capabilities") or {}
    config = capabilities.get(capability_id)
    if not isinstance(config, dict):
        raise ValueError(f"Unknown SweetClaude capability: {capability_id}")
    return config


def project_shape_config(
    shape: str, manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = manifest or load_manifest()
    shapes = data.get("project_shapes") or {}
    config = shapes.get(shape)
    if not isinstance(config, dict):
        raise ValueError(f"Unknown SweetClaude project shape: {shape}")
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SweetClaude capability manifest tools")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--path", type=Path)
    validate.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            manifest = load_manifest(args.path)
            result = {
                "ok": True,
                "schema_version": manifest["schema_version"],
                "channels": sorted(manifest["channels"].keys()),
                "capabilities": sorted(manifest["capabilities"].keys()),
                "project_shapes": sorted(manifest["project_shapes"].keys()),
            }
            print(json.dumps(result, indent=2 if args.pretty else None))
            return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
