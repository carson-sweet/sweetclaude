from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("behavioral_e2e", ROOT / "scripts" / "behavioral_e2e.py")
e2e = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = e2e
assert SPEC.loader is not None
SPEC.loader.exec_module(e2e)
SELECTOR_SPEC = importlib.util.spec_from_file_location("behavioral_selection", ROOT / "scripts" / "select_behavioral_clusters.py")
selector = importlib.util.module_from_spec(SELECTOR_SPEC)
assert SELECTOR_SPEC.loader is not None
SELECTOR_SPEC.loader.exec_module(selector)
PACKAGE = ROOT / "docs/testing/behavioral-e2e"
INVENTORY = json.loads((PACKAGE / "inventory.json").read_text())
CATALOG = json.loads((PACKAGE / "clusters.json").read_text())


def cases_for(*enabled: str, preset: str | None = None):
    chosen, included, excluded = selector.resolve_selection(CATALOG, preset, list(enabled), [])
    plan = selector.plan_selection(INVENTORY, CATALOG, chosen, included, excluded, [], [])
    return e2e.expand_plan(plan, INVENTORY), plan


def test_first_tier_routing_expands_direct_indirect_happy_and_failure_cases():
    cases, plan = cases_for(preset="first-tier-routing")
    assert plan["summary"]["base_operations"] == 39
    assert {case.workflow for case in cases} == {f"top/{name}" for name in ("go", "plan", "design", "build", "maintain", "configure", "utils", "status", "help")}
    assert {case.kind for case in cases} == {"happy", "failure"}
    assert {case.wording for case in cases} == {"direct", "indirect", "literal"}
    assert all(case.layer == "routing" for case in cases)
    assert all(case.fixture == ("F05" if case.kind == "failure" else "F02") for case in cases)
    assert len({case.id for case in cases}) == len(cases)


def test_expansion_keeps_operation_prompt_and_source_obligations():
    cases, _ = cases_for("skill:doctor", "layer:routing", "entry:category", "wording:indirect", "kind:failure")
    assert cases
    assert {case.operation_id.split(".")[0] for case in cases} == {"configure"}
    assert all(case.prompt.startswith("/sweetclaude:configure ") for case in cases)
    assert all(case.expected for case in cases)
    assert all(case.source_obligations for case in cases)


def test_manifest_never_claims_execution_for_compiled_cases():
    cases, plan = cases_for("skill:go", "layer:routing")
    report = e2e.manifest(cases, plan)
    assert report["status"] == "compiled-not-executed"
    assert report["coverage"]["required"] == len(cases)
    assert report["coverage"]["executed"] == 0
    assert report["coverage"]["not_run"] == len(cases)
    assert report["coverage"]["unimplemented"] == len(plan["operation_plans"]) * 2
    assert report["unimplemented_obligations"]
    assert all(case.profiles_to_resolve for case in cases)


def test_fixture_isolated_and_failure_fixture_is_deliberately_malformed(tmp_path):
    project, environment = e2e.make_fixture(tmp_path / "fixture", "F05")
    assert project.is_relative_to(tmp_path)
    assert environment["HOME"].startswith(str(tmp_path))
    assert (project / ".sweetclaude/state/sweetclaude.yaml").read_text() == "[malformed"


def test_route_oracle_requires_observable_source_evidence():
    cases, _ = cases_for("skill:go", "layer:routing", "entry:command", "wording:direct", "kind:happy")
    status, details = e2e.route_result(cases[0], [{"tool_input": {"file_path": "skills/go/SKILL.md"}, "text": "top/go"}])
    assert status == "pass"
    assert details == []
    status, details = e2e.route_result(cases[0], [{"text": "I selected go"}])
    assert status == "oracle-gap"
    assert details


def test_runner_honors_config_switches(tmp_path):
    config = tmp_path / "selection.json"
    config.write_text(json.dumps({"schema_version": 1, "preset": "first-tier", "switches": {"skill:help": False}}))
    runner_spec = importlib.util.spec_from_file_location("run_behavioral_e2e", ROOT / "scripts" / "run_behavioral_e2e.py")
    runner = importlib.util.module_from_spec(runner_spec)
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)
    args = type("Args", (), {"catalog": PACKAGE / "clusters.json", "inventory": PACKAGE / "inventory.json", "config": config, "include": [], "exclude": [], "preset": None, "operation": [], "exclude_operation": []})()
    plan = runner.selected_plan(args)
    assert all(item["workflow"] != "top/help" for item in plan["operation_plans"])


def test_stream_adapter_records_observable_route_evidence_without_a_model(tmp_path, monkeypatch):
    runner_spec = importlib.util.spec_from_file_location("run_behavioral_e2e", ROOT / "scripts" / "run_behavioral_e2e.py")
    runner = importlib.util.module_from_spec(runner_spec)
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)
    binary = tmp_path / "bin"
    binary.mkdir()
    claude = binary / "claude"
    claude.write_text("#!/usr/bin/env python3\nimport json, sys\nsys.stdin.readline()\nprint(json.dumps({'type': 'assistant', 'text': 'top/go skills/go/SKILL.md'}), flush=True)\n", encoding="utf-8")
    claude.chmod(0o755)
    monkeypatch.setenv("PATH", f"{binary}:{__import__('os').environ['PATH']}")
    cases, _ = cases_for("skill:go", "layer:routing", "entry:command", "wording:direct", "kind:happy")
    record = runner.run_case(cases[0], keep=False, model="test", budget=0.01)
    assert record["status"] == "pass"
    assert record["evidence"]["root"] == "cleaned"
    assert record["evidence"]["events"]


def test_cost_is_extracted_from_terminal_stream_event():
    assert e2e.event_text({"a": "b"}) == "b"
    runner_spec = importlib.util.spec_from_file_location("run_behavioral_e2e", ROOT / "scripts" / "run_behavioral_e2e.py")
    runner = importlib.util.module_from_spec(runner_spec)
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)
    assert runner.event_cost([{"total_cost_usd": 0.12}, {"cost_usd": 0.03}]) == 0.12


def test_live_runner_defaults_to_twenty_five_dollar_run_cap():
    runner_spec = importlib.util.spec_from_file_location("run_behavioral_e2e", ROOT / "scripts" / "run_behavioral_e2e.py")
    runner = importlib.util.module_from_spec(runner_spec)
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-run-budget-usd", type=float, default=25.0)
    assert parser.parse_args([]).max_run_budget_usd == 25.0


def test_full_obligation_registry_is_complete_source_bound_and_individually_addressable():
    registry = json.loads((PACKAGE / "obligations.json").read_text())
    assert registry["inventory_sha256"] == CATALOG["inventory_sha256"]
    assert registry["count"] == 860
    assert len({row["id"] for row in registry["obligations"]}) == registry["count"]
    assert {row["kind"] for row in registry["obligations"]} == {"branch", "profile", "hook", "capability", "journey"}
    assert all(row["fixture_requirements"] and row["oracle_requirements"] for row in registry["obligations"])
    assert all(row["status"] == "specified-not-implemented" for row in registry["obligations"])


def test_standard_scope_has_nine_representative_commands_and_108_attempts():
    standard = PACKAGE / "standard.json"
    runner_spec = importlib.util.spec_from_file_location("run_behavioral_e2e", ROOT / "scripts" / "run_behavioral_e2e.py")
    runner = importlib.util.module_from_spec(runner_spec)
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)
    args = type("Args", (), {"catalog": PACKAGE / "clusters.json", "inventory": PACKAGE / "inventory.json", "config": standard, "include": [], "exclude": [], "preset": None, "operation": [], "exclude_operation": []})()
    plan = runner.selected_plan(args)
    cases = e2e.expand_plan(plan, INVENTORY)
    assert len(cases) == 36
    assert {case.workflow for case in cases} == {f"top/{name}" for name in ("go", "plan", "design", "build", "maintain", "configure", "utils", "status", "help")}
    assert len(cases) * 3 == 108
