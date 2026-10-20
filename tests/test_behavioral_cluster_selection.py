from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("behavioral_selection", ROOT / "scripts/select_behavioral_clusters.py")
selection = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(selection)
PACKAGE = ROOT / "docs/testing/behavioral-e2e"
CATALOG = json.loads((PACKAGE / "clusters.json").read_text())
INVENTORY = json.loads((PACKAGE / "inventory.json").read_text())


def plan(enabled=(), disabled=(), preset=None, operations=(), excluded_operations=()):
    chosen, positive, negative = selection.resolve_selection(CATALOG, preset, list(enabled), list(disabled))
    return selection.plan_selection(INVENTORY, CATALOG, chosen, positive, negative, list(operations), list(excluded_operations))


def test_full_scope_preserves_every_inventory_operation_and_auxiliary_subject():
    result = plan(preset="full")
    assert {op["operation_id"] for op in result["operation_plans"]} == {op["id"] for op in INVENTORY["operations"]}
    assert len(result["operation_plans"]) == 347
    assert result["summary"]["auxiliary_by_type"] == {"capability": 132, "hook": 19, "journey": 15}
    assert result["status"] == "selection-preview-no-tests-executed"
    assert all(item["status"] == "planned-unexpanded" for item in result["operation_plans"] + result["auxiliary_plans"])


@pytest.mark.parametrize("preset", sorted(CATALOG["presets"]))
def test_every_saved_preset_resolves_to_applicable_scope(preset):
    result = plan(preset=preset)
    assert result["operation_plans"] or result["auxiliary_plans"]


def test_first_tier_routing_has_no_library_or_auxiliary_standalone_cases():
    result = plan(preset="first-tier-routing")
    assert result["summary"]["workflows"] == 9
    assert result["summary"]["base_operations"] == 39
    assert result["auxiliary_plans"] == []
    assert all(op["workflow"].startswith("top/") and op["layers"] == ["routing"] for op in result["operation_plans"])
    assert all("stop at library handoff" in op["execution_boundary"] for op in result["operation_plans"])


def test_family_union_intersects_depth_and_kind_with_exclusions_winning():
    result = plan(["family:build", "family:maintain", "layer:routing", "kind:failure"], ["skill:john-wick"])
    keys = {op["workflow"] for op in result["operation_plans"]}
    assert keys <= {key for key in INVENTORY["workflows"] if key.startswith(("build/", "maintain/")) or key in {"top/build", "top/maintain"}}
    assert "build/code-feature" in keys and "maintain/hotfix" in keys
    assert "build/john-wick" not in keys
    assert all(op["layers"] == ["routing"] and op["kinds"] == ["failure"] for op in result["operation_plans"])


def test_explicit_skill_replaces_preset_subject_and_preserves_routing_depth():
    result = plan(["skill:doctor"], preset="routing")
    assert {op["workflow"] for op in result["operation_plans"]} == {"configure/doctor"}
    assert result["summary"]["base_operations"] == 12
    assert result["summary"]["effective_layers"] == ["routing"]
    assert "scope:workflows" not in result["enabled_clusters"]


def test_indirect_category_only_reaches_exact_requested_skill():
    result = plan(["skill:code-review", "wording:indirect", "entry:category", "kind:failure"])
    assert {op["workflow"] for op in result["operation_plans"]} == {"build/code-review"}
    assert all(op["variants"] == [{"entry": "category", "wording": "indirect", "id": "category-indirect"}] for op in result["operation_plans"])


def test_overlapping_clusters_do_not_duplicate_operation_plans():
    result = plan(["family:build", "skill:project-issues", "topic:issue-tracking"])
    ids = [op["operation_id"] for op in result["operation_plans"]]
    assert len(ids) == len(set(ids))
    assert {op["workflow"] for op in result["operation_plans"]} == {k for k in INVENTORY["workflows"] if k.startswith("build/") or k == "top/build"}


def test_operation_filter_selects_github_management_without_local_or_implementation():
    result = plan(["topic:github"], operations=["build.project-issues.*-github"], excluded_operations=["*.decline-github"])
    ids = {op["operation_id"] for op in result["operation_plans"]}
    assert "build.project-issues.tracker-github" in ids
    assert "build.project-issues.close-github" in ids
    assert all(op.startswith("build.project-issues.") and op.endswith("-github") for op in ids)
    assert "build.project-issues.decline-github" not in ids


def test_internal_skill_cannot_be_selected_as_a_public_category_entry():
    with pytest.raises(ValueError, match="no applicable"):
        plan(["skill:code-tdd", "entry:category"])
    result = plan(["skill:code-tdd", "entry:caller"])
    assert {v["entry"] for op in result["operation_plans"] for v in op["variants"]} == {"caller"}


def test_literal_discovery_is_once_per_public_skill_and_absent_from_operation_filters():
    result = plan(["tier:1-public"])
    literal = [op for op in result["operation_plans"] for v in op["variants"] if v["entry"] == "literal"]
    assert len(literal) == 9
    filtered = plan(["skill:go"], operations=["top.go.request"])
    assert all(v["entry"] != "literal" for op in filtered["operation_plans"] for v in op["variants"])


def test_auxiliary_subjects_obey_layer_and_entry_filters():
    with pytest.raises(ValueError, match="no applicable"):
        plan(["scope:journeys", "layer:routing"])
    with pytest.raises(ValueError, match="no applicable"):
        plan(["scope:hooks", "entry:go"])
    result = plan(["hook:PreToolUse/test-guardian", "layer:routing", "entry:caller"])
    assert result["operation_plans"] == []
    assert len(result["auxiliary_plans"]) == 1
    assert result["auxiliary_plans"][0]["layers"] == ["routing"]


@pytest.mark.parametrize("enabled,disabled", [
    ([], []),
    (["skill:doctro"], []),
    (["skill:configure/missing-*"], []),
    (["family:build"], ["family:build"]),
    (["skill:doctor"], ["profile:*"]),
])
def test_invalid_or_empty_selection_is_an_error(enabled, disabled):
    with pytest.raises(ValueError):
        plan(enabled, disabled)


def test_false_switch_excludes_subject_and_does_not_modify_configuration(tmp_path, capsys):
    config = tmp_path / "selection.json"
    body = json.dumps({"schema_version": 1, "preset": "first-tier", "switches": {"skill:help": False}})
    config.write_text(body)
    assert selection.main(["--config", str(config), "--format", "json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["summary"]["workflows"] == 8
    assert all(op["workflow"] != "top/help" for op in result["operation_plans"])
    assert config.read_text() == body


def test_unknown_config_switch_types_fail_explicitly(tmp_path, capsys):
    config = tmp_path / "selection.json"
    config.write_text(json.dumps({"switches": {"skill:doctor": "false"}}))
    assert selection.main(["--config", str(config)]) == 2
    assert "true/false" in capsys.readouterr().err


def test_catalog_from_different_inventory_cannot_produce_a_plan(tmp_path, capsys):
    catalog = tmp_path / "clusters.json"
    catalog.write_text(json.dumps({**CATALOG, "inventory_sha256": "outdated"}))
    assert selection.main(["--catalog", str(catalog), "--preset", "full"]) == 2
    assert "does not match" in capsys.readouterr().err


def test_preview_refuses_existing_output_and_protected_inventory(tmp_path, capsys):
    output = tmp_path / "output.json"
    output.write_text("preserve this")
    assert selection.main(["--preset", "first-tier", "--output", str(output)]) == 2
    assert output.read_text() == "preserve this"
    assert "already exists" in capsys.readouterr().err
    inventory = PACKAGE / "inventory.json"
    before = inventory.read_bytes()
    assert selection.main(["--preset", "first-tier", "--output", str(inventory)]) == 2
    assert inventory.read_bytes() == before
    assert "must not overwrite" in capsys.readouterr().err


def test_fresh_json_output_is_a_preview_and_preserves_cluster_provenance(tmp_path):
    output = tmp_path / "plan.json"
    assert selection.main(["--include", "skill:doctor", "--include", "layer:routing", "--format", "json", "--output", str(output)]) == 0
    result = json.loads(output.read_text())
    assert result["enabled_clusters"] == ["layer:routing", "skill:configure/doctor"]
    assert result["inventory_sha256"] == CATALOG["inventory_sha256"]
    assert result["status"] == "selection-preview-no-tests-executed"


def test_saved_operation_filters_define_standard_scope_without_literal_cases():
    config = PACKAGE / "standard.json"
    assert selection.main(["--config", str(config), "--format", "json"]) == 0
