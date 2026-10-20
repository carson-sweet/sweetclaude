import os
import copy
import json
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from maintenance.capability_manifest import (  # noqa: E402
    capability_config,
    expected_marketplace,
    expected_ref,
    load_manifest,
    minimum_safe_version,
    project_shape_config,
    required_release_checks,
    validate_manifest,
)


ROOT = Path(__file__).parents[1]


def test_capability_manifest_loads_channel_facts():
    # ISSUE-239 (decision log #34, #36): promotion-time three-channel model.
    # stable -> main/major 5 (major 4 until the 5.0.0 release); beta unchanged (retired later in ISSUE-241);
    # legacy -> stable-3.x/major 3.
    manifest = load_manifest(ROOT / "config" / "capability-manifest.yaml")

    assert expected_ref("stable", manifest) == "main"
    assert expected_marketplace("stable", manifest) == "sweetclaude-stable"
    assert manifest["channels"]["stable"]["major_version"] == 5
    assert manifest["channels"]["stable"]["prerelease_allowed"] is False

    # beta channel is untouched by this story
    assert expected_ref("beta", manifest) == "beta-4.x"
    assert expected_marketplace("beta", manifest) == "sweetclaude-beta"
    assert minimum_safe_version("beta", manifest) == "4.1.9-beta"

    assert expected_ref("legacy", manifest) == "stable-3.x"
    assert expected_marketplace("legacy", manifest) == "sweetclaude-legacy"
    assert manifest["channels"]["legacy"]["major_version"] == 3


def test_capability_manifest_loads_release_checks():
    checks = required_release_checks()

    assert checks == {
        "tests",
        "channel-isolation",
        "installation-smoke",
        "static-checks",
        "release-metadata",
        "manifest-validation",
        "release-identity",
        "docs-capability",
        "public-distribution",
    }


def test_capability_manifest_loads_project_shape_routes():
    assert project_shape_config("recovery_required")["guard_status"] == "run-recover"
    assert project_shape_config("flat_bl_backlog")["migrate_allowed"] is True
    assert project_shape_config("typed_legacy_backlog")["guard_status"] == (
        "supported-migration-available"
    )


def test_capability_manifest_loads_capability_contracts():
    recovery = capability_config("recover.stabilize_without_migration")
    migration = capability_config("migrate.flat_bl_to_issue")
    typed_legacy = capability_config("migrate.typed_legacy_backlog")

    assert recovery["delegate_skill"] == "sweetclaude:recover"
    assert "recovery_required" in recovery["supports_project_shapes"]
    assert "snapshot" in recovery["safety_contract"]
    assert migration["delegate_skill"] == "sweetclaude:migrate"
    assert migration["preflight_required"] is True
    assert migration["supports_project_shapes"] == ["flat_bl_backlog"]
    assert migration["mutation_class"] == "planned_write"
    assert migration["rollback_support"]["supported"] is True
    assert migration["rollback_support"]["command"]
    assert migration["unsupported_states"][0]["behavior"] == "block"
    assert migration["version_metadata"]["introduced_in"] == "4.0.0-beta"
    assert typed_legacy["supported"] is True


def test_capability_manifest_validates_capability_shape_references():
    manifest = load_manifest(ROOT / "config" / "capability-manifest.yaml")
    manifest["project_shapes"]["flat_bl_backlog"]["migration_capability"] = (
        "migrate.typed_legacy_backlog"
    )

    try:
        validate_manifest(manifest)
    except ValueError as exc:
        assert "capability does not support shape" in str(exc)
    else:
        raise AssertionError("validate_manifest accepted a mismatched capability shape")


def test_capability_manifest_requires_rollback_support_for_mutating_capabilities():
    manifest = load_manifest(ROOT / "config" / "capability-manifest.yaml")
    broken = copy.deepcopy(manifest)
    del broken["capabilities"]["migrate.flat_bl_to_issue"]["rollback_support"]

    try:
        validate_manifest(broken)
    except ValueError as exc:
        assert "rollback_support" in str(exc)
    else:
        raise AssertionError("validate_manifest accepted missing rollback support")


def test_capability_manifest_rejects_mutating_capability_without_supported_rollback():
    manifest = load_manifest(ROOT / "config" / "capability-manifest.yaml")
    broken = copy.deepcopy(manifest)
    broken["capabilities"]["migrate.flat_bl_to_issue"]["rollback_support"] = {
        "supported": False,
        "command": None,
        "limitations": ["not implemented"],
    }

    try:
        validate_manifest(broken)
    except ValueError as exc:
        assert "rollback_support.supported" in str(exc)
    else:
        raise AssertionError("validate_manifest accepted unsupported rollback")


def test_capability_manifest_validates_unsupported_state_policy():
    manifest = load_manifest(ROOT / "config" / "capability-manifest.yaml")
    broken = copy.deepcopy(manifest)
    broken["capabilities"]["migrate.flat_bl_to_issue"]["unsupported_states"] = [
        {"condition": "typed_legacy_backlog", "behavior": "mutate_anyway"},
    ]

    try:
        validate_manifest(broken)
    except ValueError as exc:
        assert "unsupported_states" in str(exc)
    else:
        raise AssertionError("validate_manifest accepted invalid unsupported-state behavior")


def test_capability_manifest_validate_cli_emits_summary():
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "maintenance" / "capability_manifest.py"),
            "validate",
            "--path",
            str(ROOT / "config" / "capability-manifest.yaml"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert "migrate.flat_bl_to_issue" in payload["capabilities"]


TIER1_SLASH_COMMANDS = {
    f"/sweetclaude:{name}"
    for name in ("go", "plan", "design", "build", "maintain", "configure", "utils", "status", "help")
}


def test_capability_slash_commands_resolve_to_tier1_or_library_workflow():
    manifest = load_manifest(ROOT / "config" / "capability-manifest.yaml")
    unresolved = []
    for capability_id, config in manifest["capabilities"].items():
        slash_command = (config.get("command_entrypoint") or {}).get("slash_command")
        if slash_command is None or slash_command in TIER1_SLASH_COMMANDS:
            continue
        parts = slash_command.removeprefix("/sweetclaude:").split(" ")
        if (
            slash_command.startswith("/sweetclaude:")
            and len(parts) == 2
            and f"/sweetclaude:{parts[0]}" in TIER1_SLASH_COMMANDS
            and (ROOT / "skill-library" / parts[0] / parts[1] / "SKILL.md").is_file()
        ):
            continue
        unresolved.append(f"{capability_id}: {slash_command}")

    assert unresolved == []
