"""Phase 3 contract tests: make enforcement real (plan 2026-10-20, phase 3).

Each hook is run the way Claude Code 2.1.305 runs it: a subprocess whose stdin
is a captured JSON payload from tests/fixtures/hook_payloads/, with
CLAUDE_PROJECT_DIR and CLAUDE_PLUGIN_ROOT set and never CLAUDE_TOOL_NAME,
CLAUDE_FILE_PATH or CLAUDE_TRANSCRIPT_PATH. Output is judged against
docs/design/hook-protocol.md. NotebookEdit has no captured fixture, so its
payload is the Write envelope with the NotebookEdit tool_input shape
(notebook_path, new_source, cell_id, edit_mode).

One class per ledger row. Tests named allows_* or silent_* are negative
controls that pin what must keep working while the denials are added.

Ledger rows covered: R-077, R-078, R-079, R-081, R-082, R-239, R-241, R-242,
R-243, R-244, R-245, R-246. R-080 and R-240 are already covered by the phase 2
R-072 case test_reports_failing_run_back_to_the_model.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from hook_stdin import deny_reason, run_hook as run_hook_with_env  # noqa: E402
from test_hook_protocol_contract import (  # noqa: E402
    HOOKS,
    PAYLOADS,
    REPO_ROOT,
    activate_with_sc_artifact,
    assert_allowed,
    assert_denied,
    enable_guardian,
    feedback_text,
    needs_preflight_flag,
    payload,
    project,
    run_hook,
    state_dir,
    stdout_json,
    write_issue,
    write_kanban_gates,
    write_sweetclaude_yaml,
)

HOOKS_JSON = HOOKS / "hooks.json"
MANIFEST_JSON = HOOKS / "hooks-manifest.json"
SETUP_SKILL = REPO_ROOT / "skill-library" / "configure" / "setup" / "SKILL.md"
CODE_TESTING_SKILL = REPO_ROOT / "skill-library" / "build" / "code-testing" / "SKILL.md"

BACKLOG = Path("backlog")
ISSUES_DONE = Path("roadmap") / "issues" / "done"


def registrations(event: str) -> list[tuple[str, str]]:
    config = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    found = []
    for entry in config.get("hooks", {}).get(event, []):
        for hook in entry.get("hooks", []):
            found.append((entry.get("matcher", ""), hook.get("command", "")))
    return found


def matcher_covers(matcher: str, tool: str) -> bool:
    if matcher in ("", "*", ".*"):
        return True
    return tool in matcher.split("|")


def registered_matchers(event: str, script: str) -> list[str]:
    return [matcher for matcher, command in registrations(event) if command.endswith(f"/hooks/{script}")]


def manifest_entry(script: str) -> dict:
    hooks = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))["hooks"]
    return next((entry for entry in hooks if entry.get("file") == script), {})


def bash_call(project: Path, command: str) -> str:
    return payload("PreToolUse-Bash", project, command=command)


def write_call(project: Path, relative: str, content: str) -> str:
    return payload("PreToolUse-Write", project, file_path=str(project / relative), content=content)


def edit_call(project: Path, relative: str, old: str, new: str) -> str:
    return payload("PreToolUse-Edit", project, file_path=str(project / relative), old_string=old, new_string=new)


def notebook_call(project: Path, relative: str) -> str:
    data = json.loads(payload("PreToolUse-Write", project))
    data["tool_name"] = "NotebookEdit"
    data["tool_input"] = {
        "notebook_path": str(project / relative),
        "cell_id": "cell-1",
        "new_source": "assert True",
        "edit_mode": "replace",
    }
    return json.dumps(data)


def active_issue_text(number: int, *, bold: bool = False) -> str:
    issue_id = f"ISSUE-{number:03d}"
    if bold:
        return f"# {issue_id}: Work item {number}\n\n**Status:** active\n"
    return f"---\nid: {issue_id}\ntitle: Work item {number}\nstatus: active\n---\n\n# {issue_id}: Work item {number}\n"


def kanban_project(project: Path, *, active: int = 3, phase: str = "IMPLEMENT", bold: bool = False,
                   product_base: str = ".sweetclaude/product", limit: int = 3) -> None:
    write_sweetclaude_yaml(project, phase=phase)
    write_kanban_gates(project, wip_limit=limit)
    for number in range(1, active + 1):
        write_issue(project, number, "active", bold=bold, product_base=product_base)
    write_issue(project, 4, "ready", bold=bold, product_base=product_base)


ISSUE_FOUR = ".sweetclaude/product/roadmap/issues/ISSUE-004-work-item-4.md"
ISSUE_ONE = ".sweetclaude/product/roadmap/issues/ISSUE-001-work-item-1.md"


class TestWipLimitCountsRealIssuesR077:
    def test_denies_fourth_activation_with_three_active_frontmatter_issues(self, project):
        kanban_project(project)
        result = run_hook("wip-limit.sh", project, bash_call(project, activate_with_sc_artifact("ISSUE-004")))
        assert_denied(result)

    def test_denial_names_the_wip_limit_and_the_count(self, project):
        kanban_project(project)
        result = run_hook("wip-limit.sh", project, bash_call(project, activate_with_sc_artifact("ISSUE-004")))
        assert_denied(result)
        reason = deny_reason(result)
        assert "WIP limit" in reason
        assert "3/3" in reason

    def test_counts_active_issues_written_with_bold_metadata(self, project):
        kanban_project(project, bold=True)
        result = run_hook("wip-limit.sh", project, bash_call(project, activate_with_sc_artifact("ISSUE-004")))
        assert_denied(result)

    def test_denies_activation_through_the_sc_artifact_impl_script(self, project):
        kanban_project(project)
        command = ('python3 "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact-impl.py" write . .sweetclaude/product '
                   ".sweetclaude/state ISSUE-004 '{\"status\":\"active\"}'")
        assert_denied(run_hook("wip-limit.sh", project, bash_call(project, command)))

    def test_counts_issues_under_a_relocated_product_base(self, project):
        kanban_project(project, product_base="docs/product")
        (project / ".sweetclaude" / "artifact-privacy.yaml").write_text(
            yaml.safe_dump({"categories": {"product": {"base_path": "docs/product"}}}), encoding="utf-8")
        result = run_hook("wip-limit.sh", project, bash_call(project, activate_with_sc_artifact("ISSUE-004")))
        assert_denied(result)

    def test_allows_activation_with_two_active_issues(self, project):
        kanban_project(project, active=2)
        result = run_hook("wip-limit.sh", project, bash_call(project, activate_with_sc_artifact("ISSUE-004")))
        assert_allowed(result)

    def test_done_issues_do_not_count_toward_the_limit(self, project):
        kanban_project(project, active=2)
        write_issue(project, 5, "done", directory=ISSUES_DONE)
        write_issue(project, 6, "done", directory=ISSUES_DONE)
        write_issue(project, 7, "ready", directory=BACKLOG)
        result = run_hook("wip-limit.sh", project, bash_call(project, activate_with_sc_artifact("ISSUE-004")))
        assert_allowed(result)


class TestWipLimitGuardsEveryActivationPathR078:
    def test_denies_write_creating_a_fourth_active_issue(self, project):
        kanban_project(project)
        stdin = write_call(project, ".sweetclaude/product/roadmap/issues/ISSUE-005-fifth.md", active_issue_text(5))
        assert_denied(run_hook("wip-limit.sh", project, stdin))

    def test_denies_write_moving_a_ready_issue_to_active(self, project):
        kanban_project(project)
        stdin = write_call(project, ISSUE_FOUR, active_issue_text(4))
        assert_denied(run_hook("wip-limit.sh", project, stdin))

    def test_denies_write_activating_a_backlog_issue(self, project):
        kanban_project(project)
        write_issue(project, 8, "ready", directory=BACKLOG)
        stdin = write_call(project, ".sweetclaude/product/backlog/ISSUE-008-work-item-8.md", active_issue_text(8))
        assert_denied(run_hook("wip-limit.sh", project, stdin))

    def test_denies_edit_changing_status_to_active(self, project):
        kanban_project(project)
        stdin = edit_call(project, ISSUE_FOUR, "status: ready", "status: active")
        assert_denied(run_hook("wip-limit.sh", project, stdin))

    def test_denies_edit_changing_bold_status_to_active(self, project):
        kanban_project(project, bold=True)
        stdin = edit_call(project, ISSUE_FOUR, "**Status:** ready", "**Status:** active")
        assert_denied(run_hook("wip-limit.sh", project, stdin))

    @pytest.mark.parametrize("phase", ["IMPLEMENT", "PLAN", "DEFINE"])
    def test_denies_in_any_phase(self, project, phase):
        kanban_project(project, phase=phase)
        stdin = write_call(project, ISSUE_FOUR, active_issue_text(4))
        assert_denied(run_hook("wip-limit.sh", project, stdin))

    def test_denies_in_a_project_with_no_active_work_item(self, project):
        kanban_project(project)
        (state_dir(project) / "sweetclaude.yaml").write_text(
            yaml.safe_dump({"schema_version": 2, "project": {"name": "t", "mode": "kanban"}}), encoding="utf-8")
        stdin = write_call(project, ISSUE_FOUR, active_issue_text(4))
        assert_denied(run_hook("wip-limit.sh", project, stdin))

    def test_denies_bash_activation_outside_the_implement_phase(self, project):
        kanban_project(project, phase="DEFINE")
        result = run_hook("wip-limit.sh", project, bash_call(project, activate_with_sc_artifact("ISSUE-004")))
        assert_denied(result)

    def test_denial_names_the_wip_limit(self, project):
        kanban_project(project)
        result = run_hook("wip-limit.sh", project, write_call(project, ISSUE_FOUR, active_issue_text(4)))
        assert_denied(result)
        assert "WIP limit" in deny_reason(result)

    def test_allows_rewriting_an_issue_that_is_already_active(self, project):
        kanban_project(project)
        stdin = write_call(project, ISSUE_ONE, active_issue_text(1) + "\nUpdated notes.\n")
        assert_allowed(run_hook("wip-limit.sh", project, stdin))

    def test_allows_bash_rewrite_of_an_issue_that_is_already_active(self, project):
        kanban_project(project)
        result = run_hook("wip-limit.sh", project, bash_call(project, activate_with_sc_artifact("ISSUE-001")))
        assert_allowed(result)

    @pytest.mark.parametrize("status", ["ready", "blocked", "done", "in-review"])
    def test_allows_write_that_does_not_activate(self, project, status):
        kanban_project(project)
        stdin = write_call(project, ISSUE_FOUR, active_issue_text(4).replace("status: active", f"status: {status}"))
        assert_allowed(run_hook("wip-limit.sh", project, stdin))

    def test_allows_write_of_status_active_outside_issue_files(self, project):
        kanban_project(project)
        stdin = write_call(project, "docs/notes.md", "---\nstatus: active\n---\nnotes\n")
        assert_allowed(run_hook("wip-limit.sh", project, stdin))

    def test_allows_edit_of_source_file(self, project):
        kanban_project(project)
        stdin = edit_call(project, "src/calc.py", "status = 'ready'", "status = 'active'")
        assert_allowed(run_hook("wip-limit.sh", project, stdin))

    def test_allows_fourth_active_write_when_not_kanban(self, project):
        kanban_project(project)
        write_kanban_gates(project, mode="flow")
        stdin = write_call(project, ISSUE_FOUR, active_issue_text(4))
        assert_allowed(run_hook("wip-limit.sh", project, stdin))

    def test_allows_write_activating_a_third_issue(self, project):
        kanban_project(project, active=2)
        stdin = write_call(project, ISSUE_FOUR, active_issue_text(4))
        assert_allowed(run_hook("wip-limit.sh", project, stdin))

    def test_hooks_json_registers_wip_limit_for_bash_write_and_edit(self, project):
        matchers = registered_matchers("PreToolUse", "wip-limit.sh")
        assert matchers, "wip-limit.sh is not registered as a PreToolUse hook"
        for tool in ("Bash", "Write", "Edit"):
            assert any(matcher_covers(matcher, tool) for matcher in matchers), (
                f"no wip-limit.sh PreToolUse registration covers {tool}: {matchers}")

    def test_manifest_matcher_covers_bash_write_and_edit(self, project):
        entry = manifest_entry("wip-limit.sh")
        for tool in ("Bash", "Write", "Edit"):
            assert matcher_covers(entry.get("matcher", ""), tool), (
                f"hooks-manifest.json wip-limit.sh matcher {entry.get('matcher')!r} omits {tool}")


class TestWipLimitBlocksOnlyActivationR243:
    RECOVERY_COMMANDS = [
        "cp .sweetclaude/state/sweetclaude.yaml /tmp/sweetclaude-backup.yaml",
        "cp -r .sweetclaude/product /tmp/product-restore",
        "git status",
        "bash -n hooks/wip-limit.sh",
        "echo start-new-work",
        "ls -la .sweetclaude/product/roadmap/issues",
        'source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh" && sc_artifact_read ISSUE-001',
        'source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh" && sc_artifact_write ISSUE-004 \'{"status":"ready"}\'',
    ]

    @pytest.mark.parametrize("command", RECOVERY_COMMANDS)
    def test_allows_non_activating_command_at_the_limit(self, project, command):
        kanban_project(project)
        assert_allowed(run_hook("wip-limit.sh", project, bash_call(project, command)))

    def test_denies_the_command_that_activates_a_fourth_issue(self, project):
        kanban_project(project)
        result = run_hook("wip-limit.sh", project, bash_call(project, activate_with_sc_artifact("ISSUE-004")))
        assert_denied(result)

    def test_denies_activation_chained_after_a_recovery_command(self, project):
        kanban_project(project)
        command = f"git status && {activate_with_sc_artifact('ISSUE-004')}"
        assert_denied(run_hook("wip-limit.sh", project, bash_call(project, command)))


def pytest_path_env() -> dict:
    return {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", "")}


PYTEST_PYPROJECT = '[project]\nname = "fixture"\nversion = "0.0.1"\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
FAILING_TEST = 'def test_fails():\n    assert False, "AUTODETECT_SENTINEL"\n'


def implementing_project(project: Path) -> None:
    write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase="implementing")


def autodetect_feedback(project: Path, kind: str = "PostToolUse-Write", **env) -> str:
    stdin = payload(kind, project, file_path=str(project / "src" / "calc.py"))
    result = run_hook_with_env("auto-test-runner.sh", project, stdin, env={**pytest_path_env(), **env})
    assert result.returncode == 0, result.stderr
    return feedback_text(result)


class TestAutoTestRunnerResolvesTestCommandR079:
    def test_runs_the_detected_pytest_command_when_project_yaml_is_absent(self, project):
        implementing_project(project)
        (project / "pyproject.toml").write_text(PYTEST_PYPROJECT, encoding="utf-8")
        (project / "tests" / "test_calc.py").write_text(FAILING_TEST, encoding="utf-8")
        assert not (state_dir(project) / "project.yaml").exists()
        assert "AUTODETECT_SENTINEL" in autodetect_feedback(project)

    def test_runs_the_detected_command_when_project_yaml_has_no_test_command(self, project):
        implementing_project(project)
        (state_dir(project) / "project.yaml").write_text("project:\n  name: fixture\n", encoding="utf-8")
        (project / "pyproject.toml").write_text(PYTEST_PYPROJECT, encoding="utf-8")
        (project / "tests" / "test_calc.py").write_text(FAILING_TEST, encoding="utf-8")
        assert "AUTODETECT_SENTINEL" in autodetect_feedback(project)

    def test_setup_or_code_testing_records_test_command_in_project_yaml(self):
        recorded = []
        for skill in (SETUP_SKILL, CODE_TESTING_SKILL):
            text = skill.read_text(encoding="utf-8")
            names_file = ".sweetclaude/state/project.yaml" in text
            names_key = bool(re.search(r"testing:\s*\n\s+test_command:", text)) or "testing.test_command" in text
            if names_file and names_key:
                recorded.append(skill.name)
        assert recorded, (
            "neither skill-library/configure/setup/SKILL.md nor skill-library/build/code-testing/SKILL.md "
            "records testing.test_command in .sweetclaude/state/project.yaml")


class TestAutoTestRunnerNeedsNoManualConfigR239:
    def test_runs_pytest_detected_from_pytest_ini_after_a_source_edit(self, project):
        implementing_project(project)
        (project / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
        (project / "tests" / "test_calc.py").write_text(FAILING_TEST, encoding="utf-8")
        assert "AUTODETECT_SENTINEL" in autodetect_feedback(project, "PostToolUse-Edit")

    def test_runs_pytest_detected_from_pyproject_after_a_source_edit(self, project):
        implementing_project(project)
        (project / "pyproject.toml").write_text(PYTEST_PYPROJECT, encoding="utf-8")
        (project / "tests" / "test_calc.py").write_text(FAILING_TEST, encoding="utf-8")
        assert "AUTODETECT_SENTINEL" in autodetect_feedback(project, "PostToolUse-Edit")

    @pytest.mark.skipif(shutil.which("npm") is None, reason="npm not on PATH")
    def test_runs_npm_test_detected_from_package_json_after_a_source_edit(self, project):
        implementing_project(project)
        (project / "package.json").write_text(json.dumps({
            "name": "fixture", "version": "0.0.1",
            "scripts": {"test": "echo NPM_AUTODETECT_SENTINEL; exit 1"},
        }), encoding="utf-8")
        assert "NPM_AUTODETECT_SENTINEL" in autodetect_feedback(project, "PostToolUse-Edit")

    def test_explicit_project_yaml_command_wins_over_detection(self, project):
        implementing_project(project)
        marker = project / "explicit.marker"
        (state_dir(project) / "project.yaml").write_text(
            f"testing:\n  test_command: touch {marker}\n", encoding="utf-8")
        (project / "pyproject.toml").write_text(PYTEST_PYPROJECT, encoding="utf-8")
        (project / "tests" / "test_calc.py").write_text(FAILING_TEST, encoding="utf-8")
        feedback = autodetect_feedback(project, "PostToolUse-Edit")
        assert marker.exists()
        assert "AUTODETECT_SENTINEL" not in feedback

    def test_silent_when_nothing_is_detectable(self, project):
        implementing_project(project)
        stdin = payload("PostToolUse-Edit", project, file_path=str(project / "src" / "calc.py"))
        result = run_hook_with_env("auto-test-runner.sh", project, stdin, env=pytest_path_env())
        assert_allowed(result)
        assert result.stdout.strip() == ""

    def test_silent_for_detected_command_when_not_implementing(self, project):
        write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase="red")
        (project / "pyproject.toml").write_text(PYTEST_PYPROJECT, encoding="utf-8")
        (project / "tests" / "test_calc.py").write_text(FAILING_TEST, encoding="utf-8")
        assert autodetect_feedback(project) == ""

    def test_silent_for_detected_command_when_a_test_file_is_edited(self, project):
        implementing_project(project)
        (project / "pyproject.toml").write_text(PYTEST_PYPROJECT, encoding="utf-8")
        (project / "tests" / "test_calc.py").write_text(FAILING_TEST, encoding="utf-8")
        stdin = payload("PostToolUse-Edit", project, file_path=str(project / "tests" / "test_calc.py"))
        result = run_hook_with_env("auto-test-runner.sh", project, stdin, env=pytest_path_env())
        assert_allowed(result)
        assert feedback_text(result) == ""


def v4_guardian_project(project: Path, *, phase: str = "IMPLEMENT") -> None:
    enable_guardian(project)
    write_sweetclaude_yaml(project, phase=phase)
    assert not (state_dir(project) / "phase.yaml").exists()


class TestTddPrewriteGuardianReadsSweetclaudeYamlR081:
    def test_denies_source_write_when_only_sweetclaude_yaml_says_implement(self, project):
        v4_guardian_project(project)
        assert_denied(run_hook("tdd-prewrite-guardian.sh", project, write_call(project, "src/app.py", "x = 1\n")))

    def test_denies_source_edit_when_only_sweetclaude_yaml_says_implement(self, project):
        v4_guardian_project(project)
        assert_denied(run_hook("tdd-prewrite-guardian.sh", project, edit_call(project, "src/app.py", "a", "b")))

    def test_denies_when_sweetclaude_yaml_phase_is_lowercase(self, project):
        v4_guardian_project(project, phase="implement")
        assert_denied(run_hook("tdd-prewrite-guardian.sh", project, write_call(project, "src/app.py", "x = 1\n")))

    def test_sweetclaude_yaml_phase_wins_over_the_phase_yaml_mirror(self, project):
        v4_guardian_project(project, phase="DESIGN")
        (state_dir(project) / "phase.yaml").write_text("phase: IMPLEMENT\n", encoding="utf-8")
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, write_call(project, "src/app.py", "x = 1\n")))

    def test_allows_source_write_outside_implement_in_sweetclaude_yaml(self, project):
        v4_guardian_project(project, phase="DESIGN")
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, write_call(project, "src/app.py", "x = 1\n")))

    def test_allows_source_write_when_guardian_flag_is_absent(self, project):
        v4_guardian_project(project)
        (state_dir(project) / "guardian-enabled").unlink()
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, write_call(project, "src/app.py", "x = 1\n")))


class TestTddPrewriteGuardianOnCurrentProjectsR246:
    def test_denies_write_of_src_app_py_with_no_phase_yaml_and_no_test_evidence(self, project):
        v4_guardian_project(project)
        assert_denied(run_hook("tdd-prewrite-guardian.sh", project, write_call(project, "src/app.py", "x = 1\n")))

    def test_denial_tells_the_model_to_write_tests_first(self, project):
        v4_guardian_project(project)
        result = run_hook("tdd-prewrite-guardian.sh", project, write_call(project, "src/app.py", "x = 1\n"))
        assert_denied(result)
        assert re.search(r"test", deny_reason(result), re.IGNORECASE)

    def test_python_style_test_file_in_git_status_counts_as_test_evidence(self, project):
        v4_guardian_project(project)
        source_write = write_call(project, "src/app.py", "x = 1\n")
        assert_denied(run_hook("tdd-prewrite-guardian.sh", project, source_write))
        (project / "tests" / "test_app.py").write_text("def test_app():\n    assert False\n", encoding="utf-8")
        subprocess.run(["git", "add", "tests/test_app.py"], cwd=project, check=True, capture_output=True, timeout=30)
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, source_write))

    def test_untracked_python_style_test_file_in_a_tracked_directory_counts_as_test_evidence(self, project):
        v4_guardian_project(project)
        source_write = write_call(project, "src/app.py", "x = 1\n")
        assert_denied(run_hook("tdd-prewrite-guardian.sh", project, source_write))
        (project / "tests" / ".gitkeep").write_text("", encoding="utf-8")
        git = ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=T"]
        subprocess.run([*git, "add", "-A"], cwd=project, check=True, capture_output=True, timeout=30)
        subprocess.run([*git, "commit", "-qm", "scaffold"], cwd=project, check=True, capture_output=True, timeout=30)
        (project / "tests" / "test_app.py").write_text("def test_app():\n    assert False\n", encoding="utf-8")
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, source_write))

    def test_allows_test_file_write(self, project):
        v4_guardian_project(project)
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, write_call(project, "tests/test_app.py", "x = 1\n")))


