from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import routing_behavior as rb

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS = ROOT / "tests" / "fixtures" / "routing_transcripts"
CASES = {case["id"]: case for case in rb.load_cases()}
needs_jq = pytest.mark.skipif(shutil.which("jq") is None, reason="session preflight shells out to jq")


def transcript(name: str) -> list[dict]:
    return [json.loads(line) for line in (TRANSCRIPTS / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]


def grade(name: str, case: dict) -> str:
    return rb.classify(case, rb.parse(transcript(name)), "/repo")[0]


def test_case_file_is_valid_against_the_library():
    assert rb.validate_cases(rb.load_cases()) == []


def test_case_file_covers_every_category():
    assert {case["category"] for case in CASES.values()} == set(rb.CATEGORIES)


def test_validation_rejects_yaml_boolean_workflow_names(tmp_path):
    path = tmp_path / "cases.yaml"
    path.write_text("cases:\n  - id: off-case\n    prompt: Turn it off\n    category: configure\n    workflows: [off]\n", encoding="utf-8")
    assert rb.validate_cases(rb.load_cases(path)) == ["off-case: workflow False is not a string"]


def test_validation_rejects_workflows_outside_the_category():
    case = {"id": "x", "prompt": "p", "category": "plan", "workflows": ["hotfix"]}
    assert rb.validate_cases([case]) == ["x: plan/hotfix has no SKILL.md"]


def test_validation_rejects_unknown_category_and_duplicates():
    case = {"id": "x", "prompt": "p", "category": "monitor", "workflows": ["a"]}
    assert rb.validate_cases([case, case]) == ["x: unknown category 'monitor'", "x: duplicate id", "x: unknown category 'monitor'"]


@pytest.mark.parametrize(
    ("name", "case_id", "expected"),
    [
        ("go-maintain-hotfix", "maintain-live-defect", "pass"),
        ("go-maintain-hotfix", "build-repair-defect", "wrong-category"),
        ("configure-doctor", "configure-health-check", "pass"),
        ("configure-setup", "configure-health-check", "wrong-workflow"),
        ("go-maintain-index-question", "maintain-triage-incident", "clarified"),
        ("go-maintain-index-question", "build-repair-defect", "wrong-category"),
        ("go-find-skill-question", "build-repair-defect", "pass-clarified"),
        ("go-find-skill-question", "maintain-live-defect", "clarified"),
        ("plan-index-question", "plan-product-brief", "clarified"),
        ("go-no-route", "maintain-live-defect", "no-route"),
        ("preflight-stop", "maintain-live-defect", "harness-error"),
    ],
)
def test_recorded_transcripts_are_classified(name, case_id, expected):
    assert grade(name, CASES[case_id]) == expected


def test_only_the_first_workflow_read_counts():
    events = transcript("configure-doctor") + [{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/repo/skill-library/configure/setup/SKILL.md"}}]}}]
    assert rb.parse(events).workflow == ("configure", "doctor")


def test_prose_naming_a_workflow_is_not_evidence():
    events = [event for event in transcript("go-no-route") if event["type"] != "result"]
    events.append({"type": "assistant", "message": {"content": [{"type": "text", "text": "Selected skill-library/maintain/hotfix/SKILL.md"}]}})
    events.append({"type": "result", "subtype": "success", "total_cost_usd": 0.01})
    assert grade_events(events, "maintain-live-defect") == "no-route"


def test_question_before_routing_starts_is_not_a_clarification():
    events = [transcript("go-no-route")[0], {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "AskUserQuestion", "input": {}}]}}, {"type": "result"}]
    assert grade_events(events, "build-repair-defect") == "no-route"


def grade_events(events: list[dict], case_id: str) -> str:
    return rb.classify(CASES[case_id], rb.parse(events), "/repo")[0]


def test_plugin_loaded_from_another_checkout_is_a_harness_error():
    status, detail = rb.classify(CASES["maintain-live-defect"], rb.parse(transcript("go-maintain-hotfix")), "/elsewhere")
    assert status == "harness-error"
    assert "/elsewhere" in detail


def test_missing_tier_one_command_is_a_harness_error():
    events = transcript("go-maintain-hotfix")
    events[0] = {**events[0], "skills": [s for s in events[0]["skills"] if s != "sweetclaude:utils"]}
    assert grade_events(events, "maintain-live-defect") == "harness-error"


def test_library_workflow_exposed_as_a_command_is_a_harness_error():
    events = transcript("go-maintain-hotfix")
    events[0] = {**events[0], "skills": [*events[0]["skills"], "sweetclaude:hotfix"]}
    assert grade_events(events, "maintain-live-defect") == "harness-error"


def test_unfinished_run_without_a_workflow_is_a_harness_error():
    events = [event for event in transcript("go-no-route") if event["type"] != "result"]
    assert grade_events(events, "maintain-live-defect") == "harness-error"


def test_library_load_arguments_identify_the_category():
    trace = rb.parse([{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "sweetclaude:library-load", "args": "category=design request=\"x\""}}]}}])
    assert trace.category == "design"


def test_handoff_to_a_tier_one_utility_is_a_wrong_category():
    events = [transcript("go-no-route")[0]]
    events.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "sweetclaude:find-skill", "args": "x"}}, {"type": "tool_use", "name": "Skill", "input": {"skill": "sweetclaude:status", "args": "x"}}]}})
    events.append({"type": "assistant", "message": {"content": [{"type": "text", "text": "Want me to retry?"}]}})
    events.append({"type": "result"})
    assert grade_events(events, "utils-big-picture") == "wrong-category"


def test_smoke_tier_runs_one_case_per_category_through_go():
    runs = rb.select_runs(rb.load_cases(), "smoke", None, [])
    assert [case["category"] for case, _ in runs] == list(rb.CATEGORIES)
    assert {entry for _, entry in runs} == {"go"}


def test_full_tier_runs_every_case_through_go():
    runs = rb.select_runs(rb.load_cases(), "full", None, [])
    assert len(runs) == len(CASES)
    assert {entry for _, entry in runs} == {"go"}


def test_both_entry_points_can_be_requested():
    assert len(rb.select_runs(rb.load_cases(), "full", "both", [])) == 2 * len(CASES)


def test_unknown_case_id_is_rejected():
    with pytest.raises(SystemExit):
        rb.select_runs(rb.load_cases(), "full", None, ["nope"])


def test_prompts_name_the_entry_point_and_carry_no_workflow_hint():
    case = CASES["design-api"]
    assert rb.prompt_for(case, "go") == f"/sweetclaude:go {case['prompt']}"
    assert rb.prompt_for(case, "category") == f"/sweetclaude:design {case['prompt']}"
    for case in CASES.values():
        assert not any(workflow in case["prompt"] for workflow in case["workflows"] if "-" in workflow)


def test_command_allows_bash_blocks_mutation_and_caps_spend():
    argv = rb.command("p", ROOT, "sonnet", 1.0)
    allowed = argv[argv.index("--allowedTools") + 1:argv.index("--disallowedTools")]
    disallowed = argv[argv.index("--disallowedTools") + 1:]
    assert allowed == ["Skill", "Read", "Glob", "Grep", "Bash"]
    assert disallowed == ["Write", "Edit", "NotebookEdit"]
    assert argv[argv.index("--permission-mode") + 1] == "default"
    assert argv[argv.index("--max-budget-usd") + 1] == "1.00"
    assert argv[argv.index("--plugin-dir") + 1] == str(ROOT)
    assert argv[argv.index("--setting-sources") + 1] == "project,local"


def test_fixture_project_marks_bootstrap_as_ran(tmp_path):
    project = rb.make_project(tmp_path)
    digest = hashlib.md5(str(project.resolve()).encode()).hexdigest()
    flag = Path(f"/tmp/.sweetclaude-bootstrap-ran-{digest}")
    assert flag.is_file()
    flag.unlink()


def test_fixture_project_is_a_committed_git_repository(tmp_path):
    project = rb.make_project(tmp_path)
    state = yaml.safe_load((project / ".sweetclaude" / "state" / "sweetclaude.yaml").read_text())
    assert state["schema_version"] == 2
    assert state["framework"]["setup_complete"] is True
    assert (project / ".git").is_dir()


def test_approved_story_fixture_has_a_ready_story_and_code(tmp_path):
    project = rb.make_project(tmp_path, "approved-story")
    story = project / ".sweetclaude/product/roadmap/issues/ISSUE-001-shift-swap.md"
    assert "status: ready" in story.read_text()
    assert (project / "src/shiftboard/shifts.py").is_file()
    assert (project / "tests/test_shifts.py").is_file()


def test_review_branch_fixture_has_a_change_set_on_a_feature_branch(tmp_path):
    project = rb.make_project(tmp_path, "review-branch")
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=project, capture_output=True, text=True, check=True).stdout.strip()
    diff = subprocess.run(["git", "diff", "--name-only", "main...HEAD"], cwd=project, capture_output=True, text=True, check=True).stdout.split()
    assert branch == "feature/availability-calendar"
    assert diff == ["src/shiftboard/availability.py"]


def test_release_history_fixture_has_two_tagged_releases_and_a_deploy_pipeline(tmp_path):
    project = rb.make_project(tmp_path, "release-history")
    tags = subprocess.run(["git", "tag", "--sort=creatordate"], cwd=project, capture_output=True, text=True, check=True).stdout.split()
    changed = subprocess.run(["git", "diff", "--name-only", "v0.1.0", "v0.2.0"], cwd=project, capture_output=True, text=True, check=True).stdout.split()
    assert tags == ["v0.1.0", "v0.2.0"]
    assert changed == ["src/shiftboard/reminders.py"]
    assert (project / ".github" / "workflows" / "deploy.yml").is_file()


def test_validation_rejects_an_unknown_fixture():
    case = {**CASES["build-review-change"], "fixture": "nope"}
    assert rb.validate_cases([case]) == ["build-review-change: unknown fixture 'nope'"]


@needs_jq
def test_session_preflight_accepts_the_fixture(tmp_path):
    assert rb.preflight(rb.make_project(tmp_path)) is None


@needs_jq
def test_session_preflight_leaves_no_pending_prompts(tmp_path):
    project = rb.make_project(tmp_path)
    assert rb.preflight(project) is None
    state = project / ".sweetclaude" / "state"
    assert not (state / "doctor-prompt-pending.json").exists()
    assert not (state / "pending-drift-decision.yaml").exists()


@needs_jq
def test_session_preflight_rejection_is_reported(tmp_path):
    project = rb.make_project(tmp_path)
    state = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    state.write_text(state.read_text().replace("setup_complete: true", "setup_complete: false"))
    assert "setup not complete" in rb.preflight(project)


FAKE_CLAUDE = """#!/usr/bin/env python3
import json, sys
events = [json.loads(line) for line in open({transcript!r})]
sys.stdin.readline()
for event in events:
    if event["type"] != "result":
        print(json.dumps(event), flush=True)
line = sys.stdin.readline()
stopped = bool(line) and json.loads(line).get("request", {{}}).get("subtype") == "interrupt"
open({marker!r}, "w").write("interrupted" if stopped else "not-interrupted")
print(json.dumps({{"type": "result", "subtype": "error_during_execution", "total_cost_usd": 0.042}}), flush=True)
"""


def fake_args(tmp_path: Path, transcript_name: str) -> tuple[argparse.Namespace, Path]:
    marker = tmp_path / "marker"
    fake = tmp_path / "fake-claude"
    fake.write_text(FAKE_CLAUDE.format(transcript=str(TRANSCRIPTS / f"{transcript_name}.jsonl"), marker=str(marker)))
    fake.chmod(0o755)
    args = argparse.Namespace(repo=Path("/repo"), model="sonnet", case_budget=0.25, timeout=30.0, stop_grace=10.0, claude=str(fake))
    return args, marker


def test_driver_interrupts_once_a_workflow_is_loaded(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "preflight", lambda project, repo=None: None)
    args, marker = fake_args(tmp_path, "go-maintain-hotfix")
    row = rb.run_case(CASES["maintain-live-defect"], "go", args)
    assert row["status"] == "pass"
    assert row["cost_usd"] == 0.042
    assert marker.read_text() == "interrupted"


def test_driver_reports_preflight_rejection_without_calling_claude(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "preflight", lambda project, repo=None: "preflight rejects the fixture: x")
    args, marker = fake_args(tmp_path, "go-maintain-hotfix")
    row = rb.run_case(CASES["maintain-live-defect"], "go", args)
    assert row["status"] == "harness-error"
    assert not marker.exists()


def test_driver_reports_a_missing_executable(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "preflight", lambda project, repo=None: None)
    args, _ = fake_args(tmp_path, "go-maintain-hotfix")
    args.claude = str(tmp_path / "fake-claude-broken")
    (tmp_path / "fake-claude-broken").write_text("#!/bin/sh\necho boom >&2\nexit 3\n")
    (tmp_path / "fake-claude-broken").chmod(0o755)
    row = rb.run_case(CASES["maintain-live-defect"], "go", args)
    assert row["status"] == "harness-error"
    assert "boom" in row["detail"]


def test_dry_run_reports_worst_case_spend(capsys):
    assert rb.main(["--tier", "full", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert f"{len(CASES)} runs, up to {3 * len(CASES)} with reruns; worst case ${3 * len(CASES) * 0.5:.2f}, capped at $8.00" in out


def test_go_failures_are_rerun_through_the_category_command(tmp_path, monkeypatch, capsys):
    calls = []

    def fake(case, entry, args):
        calls.append((case["id"], entry))
        status = "wrong-workflow" if (case["id"], entry) == ("plan-customer-problem", "go") else "pass"
        return rb.record(case, entry, status, "x", 0.1, [], 0.0)

    monkeypatch.setattr(rb, "run_case", fake)
    assert rb.main(["--tier", "smoke", "--repeat", "1", "--out", str(tmp_path)]) == 1
    assert calls[:2] == [("plan-customer-problem", "go"), ("plan-customer-problem", "category")]
    saved = json.loads(next(tmp_path.glob("routing-smoke-*.json")).read_text())
    assert saved["summary"]["diagnostics"] == {"plan-customer-problem": "pass"}
    assert saved["summary"]["runs"] == 6
    assert saved["summary"]["cost_usd"] == 0.7


def test_main_stops_at_the_run_budget(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(rb, "run_case", lambda case, entry, args: calls.append(case["id"]) or rb.record(case, entry, "pass", "ok", 0.20, [], 0.0))
    code = rb.main(["--tier", "full", "--repeat", "1", "--case-budget", "0.25", "--run-budget", "1.0", "--out", str(tmp_path)])
    assert len(calls) == 4
    assert code == 1
    saved = json.loads(next(tmp_path.glob("routing-full-*.json")).read_text())
    assert saved["summary"]["runs"] == 4
    assert saved["summary"]["cost_usd"] == 0.8


def rows(case_id: str, statuses: list[str], cost: float = 0.1) -> list[dict]:
    return [rb.record(CASES[case_id], "go", status, "x", cost, [], 0.0) for status in statuses]


def test_three_of_three_passes_is_a_stable_pass():
    graded = rb.grade_cases(rows("design-api", ["pass"] * 3))["design-api"]
    assert (graded["runs"], graded["passes"], graded["verdict"], graded["unstable"]) == (3, 3, "pass", False)
    assert graded["median_cost_usd"] == 0.1


def test_two_of_three_passes_is_an_unstable_pass():
    graded = rb.grade_cases(rows("design-api", ["pass", "wrong-workflow", "pass-clarified"]))["design-api"]
    assert (graded["passes"], graded["verdict"], graded["unstable"]) == (2, "pass", True)


def test_one_of_three_passes_is_an_unstable_fail():
    graded = rb.grade_cases(rows("design-api", ["pass", "no-route", "clarified"]))["design-api"]
    assert (graded["passes"], graded["verdict"], graded["unstable"]) == (1, "fail", True)


def test_zero_of_three_is_a_stable_fail():
    graded = rb.grade_cases(rows("design-api", ["no-route"] * 3))["design-api"]
    assert (graded["verdict"], graded["unstable"]) == ("fail", False)


def test_harness_errors_are_excluded_from_the_denominator():
    graded = rb.grade_cases(rows("design-api", ["pass", "pass", "harness-error"]))["design-api"]
    assert (graded["runs"], graded["passes"], graded["verdict"], graded["unstable"]) == (2, 2, "pass", False)
    single = rb.grade_cases(rows("design-api", ["pass", "harness-error", "harness-error"]))["design-api"]
    assert (single["runs"], single["verdict"]) == (1, "pass")


def test_only_a_failed_first_run_is_rerun_while_a_majority_is_reachable():
    assert not rb.needs_rerun(rows("design-api", ["pass"]), 3)
    assert rb.needs_rerun(rows("design-api", ["no-route"]), 3)
    assert rb.needs_rerun(rows("design-api", ["no-route", "pass"]), 3)
    assert not rb.needs_rerun(rows("design-api", ["no-route", "no-route"]), 3)
    assert not rb.needs_rerun(rows("design-api", ["no-route", "pass", "pass"]), 3)
    assert not rb.needs_rerun(rows("design-api", ["no-route"]), 1)
    assert not rb.needs_rerun(rows("design-api", ["harness-error"]), 3)


def test_all_harness_errors_is_a_harness_error_verdict():
    graded = rb.grade_cases(rows("design-api", ["harness-error"] * 3))["design-api"]
    assert (graded["runs"], graded["verdict"], graded["unstable"]) == (0, "harness-error", False)
    assert graded["median_cost_usd"] is None


def test_cases_are_graded_independently():
    graded = rb.grade_cases(rows("design-api", ["pass"] * 3) + rows("plan-milestone", ["no-route"] * 3))
    assert {cid: g["verdict"] for cid, g in graded.items()} == {"design-api": "pass", "plan-milestone": "fail"}


def test_failing_case_is_diagnosed_once_and_summary_carries_verdicts(tmp_path, monkeypatch, capsys):
    calls = []

    def fake(case, entry, args):
        calls.append((case["id"], entry))
        status = "pass" if entry == "category" or case["id"] != "plan-customer-problem" else "wrong-workflow"
        return rb.record(case, entry, status, "x", 0.1, [], 0.0)

    monkeypatch.setattr(rb, "run_case", fake)
    assert rb.main(["--tier", "smoke", "--out", str(tmp_path)]) == 1
    assert calls.count(("plan-customer-problem", "category")) == 1
    summary = json.loads(next(tmp_path.glob("routing-smoke-*.json")).read_text())["summary"]
    assert summary["verdicts"] == {"pass": 5, "fail": 1, "harness-error": 0}
    assert summary["cases"]["plan-customer-problem"]["passes"] == 0
    assert summary["unstable"] == []
    assert summary["diagnostics"] == {"plan-customer-problem": "pass"}
    assert "fail            plan-customer-problem" in capsys.readouterr().out


def test_each_run_is_saved_to_the_progress_log_as_it_completes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rb, "run_case", lambda case, entry, args: rb.record(case, entry, "pass", "ok", 0.20, [], 0.0))
    rb.main(["--tier", "full", "--case-budget", "0.25", "--run-budget", "1.0", "--out", str(tmp_path)])
    lines = next(tmp_path.glob("routing-full-*.jsonl")).read_text().splitlines()
    assert len(lines) == 4
    assert json.loads(lines[0])["diagnostic"] is False
