from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lifecycle_behavioral_e2e", ROOT / "scripts" / "lifecycle_behavioral_e2e.py")
lifecycle = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lifecycle
assert SPEC.loader is not None
SPEC.loader.exec_module(lifecycle)


def test_feature_compiles_all_lifecycle_stories_into_direct_indirect_happy_failure_cases():
    stories = lifecycle.parse_feature()
    cases = lifecycle.compile_cases(stories)
    assert len(stories) == 96
    assert Counter(story.phase for story in stories) == {phase: 12 for phase in lifecycle.PHASES}
    assert len(cases) == 384
    assert Counter((case.wording, case.outcome_kind) for case in cases) == {
        ("direct", "happy"): 96,
        ("indirect", "happy"): 96,
        ("direct", "failure"): 96,
        ("indirect", "failure"): 96,
    }
    assert all(case.givens and case.expected_outcomes for case in cases)


def test_phase_clusters_can_be_selected_independently():
    stories = lifecycle.parse_feature()
    cases = lifecycle.compile_cases(stories, ["lifecycle-design", "lifecycle-test"])
    assert len(cases) == 96
    assert {case.cluster for case in cases} == {"lifecycle-design", "lifecycle-test"}
    assert {case.phase for case in cases} == {"Design", "Test"}


def test_each_story_has_four_unique_plain_language_cases_and_safe_failure_contract():
    cases = lifecycle.compile_cases(lifecycle.parse_feature())
    by_story: dict[str, list] = {}
    for case in cases:
        by_story.setdefault(case.story_id, []).append(case)
    assert len(by_story) == 96
    for story_cases in by_story.values():
        assert len(story_cases) == 4
        assert len({case.id for case in story_cases}) == 4
        assert len({case.prompt for case in story_cases}) == 4
        failures = [case for case in story_cases if case.outcome_kind == "failure"]
        assert all("not available yet" in case.prompt for case in failures)
        assert all("refuse safely" in case.required_behavior for case in failures)


def test_manifest_preserves_story_traceability_and_compiled_not_executed_status():
    stories = lifecycle.parse_feature()
    selected = ["lifecycle-plan"]
    report = lifecycle.manifest(lifecycle.compile_cases(stories, selected), stories, selected)
    assert report["status"] == "compiled-not-executed"
    assert report["story_count"] == 12
    assert report["case_count"] == 48
    assert report["coverage"]["executed"] == 0
    assert report["feature"].endswith("new-saas-lifecycle.feature")


def test_standard_config_enables_every_lifecycle_cluster(tmp_path):
    config = ROOT / "docs/testing/behavioral-e2e/lifecycle-standard.json"
    expected = [f"lifecycle-{lifecycle.slug(phase)}" for phase in lifecycle.PHASES]
    assert json.loads(config.read_text())["clusters"] == expected
    output = tmp_path / "manifest.json"
    assert lifecycle.main(["--config", str(config), "--output", str(output)]) == 0
    report = json.loads(output.read_text())
    assert report["selected_clusters"] == expected
    assert report["case_count"] == 384


def test_stop_story_uses_a_direct_plain_language_stop_request():
    case = next(case for case in lifecycle.compile_cases(lifecycle.parse_feature()) if case.story_id == "plan.stop-an-unapproved-planning-change" and case.wording == "direct" and case.outcome_kind == "happy")
    assert case.prompt.startswith("I want to stop.")


def test_execution_runner_can_pass_one_lifecycle_case_without_using_old_routing_inventory(tmp_path, monkeypatch):
    runner_spec = importlib.util.spec_from_file_location("run_lifecycle_behavioral_e2e", ROOT / "scripts" / "run_lifecycle_behavioral_e2e.py")
    runner = importlib.util.module_from_spec(runner_spec)
    sys.modules[runner_spec.name] = runner
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)
    binary = tmp_path / "bin"
    binary.mkdir()
    claude = binary / "claude"
    claude.write_text("#!/usr/bin/env python3\nimport json, sys\nsys.stdin.readline()\nprint(json.dumps({'type': 'assistant', 'text': 'I need evidence before proceeding.'}), flush=True)\n", encoding="utf-8")
    claude.chmod(0o755)
    monkeypatch.setenv("PATH", f"{binary}:{__import__('os').environ['PATH']}")
    output = tmp_path / "result.json"
    assert runner.main(["--include", "lifecycle-plan", "--story", "plan.capture-a-customer-problem", "--execute", "--model", "test", "--max-run-budget-usd", "0.01", "--output", str(output)]) == 0
    result = json.loads(output.read_text())
    assert result["case_count"] == 4
    assert len(result["results"]) == 4
    assert {row["cluster"] for row in result["results"]} == {"lifecycle-plan"}
    assert {row["status"] for row in result["results"]} == {"pass"}


def test_every_lifecycle_case_has_a_bounded_recorded_user_reply():
    cases = lifecycle.compile_cases(lifecycle.parse_feature())
    assert all(len(case.decision_script) == 1 for case in cases)
    assert all(case.decision_script[0] for case in cases)
    assert all("Do not make changes" in case.decision_script[0] for case in cases if case.outcome_kind == "failure")


def test_event_cost_accumulates_nested_usage_fields():
    runner_spec = importlib.util.spec_from_file_location("run_lifecycle_behavioral_e2e", ROOT / "scripts" / "run_lifecycle_behavioral_e2e.py")
    runner = importlib.util.module_from_spec(runner_spec)
    sys.modules[runner_spec.name] = runner
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)

    # Flat keys (original format, still works)
    events_flat = [{"cost_usd": 0.01}, {"type": "token_count", "total_cost_usd": 0.02}]
    assert runner.event_cost(events_flat) == pytest.approx(0.03)

    # Nested usage (what Claude Code actually emits)
    events_nested = [
        {"type": "token_count", "usage": {"cost_usd": 0.005}},
        {"type": "token_count", "usage": {"total_cost_usd": 0.015}},
        {"type": "result"},
    ]
    assert runner.event_cost(events_nested) == pytest.approx(0.02)

    # No cost fields at all
    events_no_money = [{"type": "system"}, {"type": "assistant", "text": "done"}]
    assert runner.event_cost(events_no_money) == 0.0
    assert runner.event_cost([]) == 0.0


def test_domain_only_keeps_domain_files_and_excludes_sweetclaude_state():
    runner_spec = importlib.util.spec_from_file_location("run_lifecycle_behavioral_e2e", ROOT / "scripts" / "run_lifecycle_behavioral_e2e.py")
    runner = importlib.util.module_from_spec(runner_spec)
    sys.modules[runner_spec.name] = runner
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)
    d = {
        "README.md": "abc1",
        "src/app.py": "def1",
        "docs/product.md": "ghi1",
        "evidence/test.log": "jkl1",
        ".sweetclaude/state/sweetclaude.yaml": "mno1",
        ".sweetclaude/state/session-status.txt": "pqr1",
        ".sweetclaude/outputs/session-001.json": "stu1",
        ".git/HEAD": "vwx1",
    }
    domain = runner.domain_only(d)
    expected = {"README.md", "src/app.py", "docs/product.md", "evidence/test.log"}
    assert set(domain.keys()) == expected


def test_evaluator_does_not_report_fail_effect_for_sweetclaude_state_changes():
    runner_spec = importlib.util.spec_from_file_location("run_lifecycle_behavioral_e2e", ROOT / "scripts" / "run_lifecycle_behavioral_e2e.py")
    runner = importlib.util.module_from_spec(runner_spec)
    sys.modules[runner_spec.name] = runner
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)

    from lifecycle_behavioral_e2e import LifecycleCase
    fake = LifecycleCase(
        id="test-fail", story_id="plan.test", cluster="lifecycle-plan", phase="Plan",
        title="test", wording="direct", outcome_kind="failure", prompt="fake",
        givens=("a",), expected_outcomes=("b",), required_behavior="x", fixture="f",
        decision_script=(),
    )
    before = {"README.md": "old_hash", ".sweetclaude/state/sweetclaude.yaml": "before_sha"}
    after = {"README.md": "old_hash", ".sweetclaude/state/sweetclaude.yaml": "after_sha"}
    events = [{"type": "result", "text": "done"}]
    status, details = runner.evaluate(fake, events, before, after, 0)
    assert status != "fail-effect"


def test_evaluator_reports_fail_effect_for_domain_file_changes():
    runner_spec = importlib.util.spec_from_file_location("run_lifecycle_behavioral_e2e", ROOT / "scripts" / "run_lifecycle_behavioral_e2e.py")
    runner = importlib.util.module_from_spec(runner_spec)
    sys.modules[runner_spec.name] = runner
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)

    from lifecycle_behavioral_e2e import LifecycleCase
    fake = LifecycleCase(
        id="test-fail", story_id="plan.test", cluster="lifecycle-plan", phase="Plan",
        title="test", wording="direct", outcome_kind="failure", prompt="fake",
        givens=("a",), expected_outcomes=("b",), required_behavior="x", fixture="f",
        decision_script=(),
    )
    before = {"README.md": "hash_old", ".sweetclaude/state/sweet claude.yaml": "sha1"}
    after = {"README.md": "hash_new", ".sweet claude/state/sweetclaude.yaml": "sha2"}
    events = [{"type": "result", "text": "done"}]
    status, details = runner.evaluate(fake, events, before, after, 0)
    assert status == "fail-effect"
