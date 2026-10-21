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


def run_registered_stop_hooks(project: Path, stdin: str) -> list[subprocess.CompletedProcess]:
    env = os.environ.copy()
    env.update({"HOME": str(project), "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)})
    results = []
    for _, command in registrations("Stop"):
        resolved = command.replace("${CLAUDE_PLUGIN_ROOT}", str(REPO_ROOT))
        results.append(subprocess.run(["bash", resolved], cwd=str(project), env=env, input=stdin,
                                      capture_output=True, text=True, timeout=60))
    return results


def stop_stdin(project: Path, text: str, *, last_message: bool = True) -> str:
    data = json.loads(payload("Stop-none", project))
    data["stop_hook_active"] = False
    data["last_assistant_message"] = text if last_message else ""
    return json.dumps(data)


class TestPhaseDwellingGuardRegisteredR082:
    ADVANCEMENT = "The design is drafted. Ready to move on?"

    def test_hooks_json_registers_phase_dwelling_guard_as_a_stop_hook(self):
        assert registered_matchers("Stop", "phase-dwelling-guard.sh"), (
            "hooks/hooks.json has no Stop registration for hooks/phase-dwelling-guard.sh")

    def test_registered_command_resolves_to_an_existing_script(self):
        commands = [command for _, command in registrations("Stop") if command.endswith("/hooks/phase-dwelling-guard.sh")]
        assert commands, "phase-dwelling-guard.sh is not registered as a Stop hook"
        for command in commands:
            assert (REPO_ROOT / command.replace("${CLAUDE_PLUGIN_ROOT}/", "")).is_file()

    def test_registered_stop_hooks_block_advancement_language_when_guardian_is_on(self, project):
        write_sweetclaude_yaml(project)
        enable_guardian(project)
        results = run_registered_stop_hooks(project, stop_stdin(project, self.ADVANCEMENT))
        blocks = [stdout_json(r) for r in results if (stdout_json(r) or {}).get("decision") == "block"]
        assert any("move on" in json.dumps(b).lower() or "dwell" in json.dumps(b).lower() for b in blocks), (
            f"no registered Stop hook blocked advancement language: {[r.stdout for r in results]}")

    def test_registered_stop_hooks_stay_quiet_for_neutral_text_when_guardian_is_on(self, project):
        write_sweetclaude_yaml(project)
        enable_guardian(project)
        results = run_registered_stop_hooks(project, stop_stdin(project, "The design is drafted. Tell me what to change."))
        assert not [r for r in results if (stdout_json(r) or {}).get("decision") == "block"]

    def test_the_guardian_stop_hook_does_not_run_its_check_when_guardian_is_off(self, project):
        write_sweetclaude_yaml(project)
        results = run_registered_stop_hooks(project, stop_stdin(project, self.ADVANCEMENT))
        assert not [r for r in results if (stdout_json(r) or {}).get("decision") == "block"]


class TestPhaseDwellingGuardRegistrationPathR245:
    def test_registration_uses_the_plugin_root_command_path(self):
        commands = [command for _, command in registrations("Stop")]
        assert "${CLAUDE_PLUGIN_ROOT}/hooks/phase-dwelling-guard.sh" in commands

    def test_manifest_declares_the_hook_as_a_stop_hook_with_its_command_path(self):
        entry = manifest_entry("phase-dwelling-guard.sh")
        assert entry.get("event") == "Stop"
        assert entry.get("command_path") == "${CLAUDE_PLUGIN_ROOT}/hooks/phase-dwelling-guard.sh"

    def test_registered_hook_reads_the_response_from_the_stdin_transcript_path(self, project):
        write_sweetclaude_yaml(project)
        enable_guardian(project)
        lines = [
            {"type": "user", "message": {"role": "user", "content": "how is the design?"}},
            {"type": "assistant", "message": {"role": "assistant",
                                              "content": [{"type": "text", "text": "Drafted. Ready to move on?"}]}},
        ]
        (project / ".transcript.jsonl").write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
        results = run_registered_stop_hooks(project, stop_stdin(project, "", last_message=False))
        assert [r for r in results if (stdout_json(r) or {}).get("decision") == "block"], (
            f"no registered Stop hook blocked from the transcript: {[r.stdout for r in results]}")


BASH_WRITES_TO_TEST_FILES = [
    "echo 'def test_x(): pass' > tests/test_x.py",
    "echo 'def test_x(): pass' >> tests/test_x.py",
    "echo 'def test_x(): pass' > ./tests/test_x.py",
    "cat > tests/test_x.py <<'EOF'\ndef test_x(): pass\nEOF",
    "printf 'x' | tee tests/test_x.py",
    "printf 'x' | tee -a tests/test_x.py",
    "sed -i 's/a/b/' tests/test_x.py",
    "sed -i '' 's/a/b/' tests/test_x.py",
    "sed -i.bak 's/a/b/' tests/test_x.py",
    "cp /tmp/replacement.py tests/test_x.py",
    "mv /tmp/replacement.py tests/test_x.py",
    "echo x > src/calc.py && echo y > tests/test_x.py",
    "echo x > web/calc.test.ts",
    "echo x > spec/calc_spec.rb",
    "echo x > features/calc.feature",
]

BASH_THAT_LEAVE_TEST_FILES_ALONE = [
    "cat tests/test_x.py",
    "pytest tests/test_x.py",
    "python3 -m pytest tests -q 2>&1 | tail -20",
    "pytest tests/ > out.txt 2>&1",
    "grep -n add tests/test_x.py",
    "sed -n '1,20p' tests/test_x.py",
    "ls tests > listing.txt",
    "echo x > src/calc.py",
    "sed -i 's/a/b/' src/calc.py",
    "cp tests/test_x.py /tmp/backup.py",
    "git diff tests/test_x.py > changes.patch",
    "git status",
    "sed -i 's/a/b/' src/calc.py && pytest tests/test_x.py",
    "echo x > out.txt; cat tests/test_x.py",
    "cat tests/test_x.py | tee out.log",
]


def guarded_project(project: Path, *, tdd_phase: str = "implementing") -> None:
    write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase=tdd_phase)
    (project / "tests" / "test_x.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")


class TestTestGuardianCoversBashAndNotebooksR241:
    @pytest.mark.parametrize("command", BASH_WRITES_TO_TEST_FILES)
    def test_denies_bash_command_that_writes_into_a_test_file(self, project, command):
        guarded_project(project)
        result = run_hook("test-guardian.sh", project, bash_call(project, command))
        assert_denied(result)
        assert re.search(r"immutable|test files", deny_reason(result), re.IGNORECASE)

    def test_denies_bash_write_to_an_absolute_test_path(self, project):
        guarded_project(project)
        assert_denied(run_hook("test-guardian.sh", project, bash_call(project, f"echo x > {project}/tests/test_x.py")))

    @pytest.mark.parametrize("path", ["tests/test_analysis.ipynb", "notebooks/analysis_test.ipynb", "spec/model.ipynb"])
    def test_denies_notebook_edit_of_a_test_pattern_notebook(self, project, path):
        guarded_project(project)
        result = run_hook("test-guardian.sh", project, notebook_call(project, path))
        assert_denied(result)
        assert re.search(r"immutable|test files", deny_reason(result), re.IGNORECASE)

    def test_allows_notebook_edit_of_a_non_test_notebook(self, project):
        guarded_project(project)
        assert_allowed(run_hook("test-guardian.sh", project, notebook_call(project, "notebooks/explore.ipynb")))

    @pytest.mark.parametrize("command", BASH_THAT_LEAVE_TEST_FILES_ALONE)
    def test_allows_bash_command_that_only_reads_or_runs_tests(self, project, command):
        guarded_project(project)
        assert_allowed(run_hook("test-guardian.sh", project, bash_call(project, command)))

    @pytest.mark.parametrize("command", ["echo x > tests/test_x.py", "sed -i 's/a/b/' tests/test_x.py"])
    def test_allows_bash_test_write_when_not_implementing(self, project, command):
        guarded_project(project, tdd_phase="red")
        assert_allowed(run_hook("test-guardian.sh", project, bash_call(project, command)))

    def test_allows_notebook_edit_when_not_implementing(self, project):
        guarded_project(project, tdd_phase="red")
        assert_allowed(run_hook("test-guardian.sh", project, notebook_call(project, "tests/test_analysis.ipynb")))

    def test_hooks_json_registers_test_guardian_for_bash_and_notebook_edit(self):
        matchers = registered_matchers("PreToolUse", "test-guardian.sh")
        assert matchers, "test-guardian.sh is not registered as a PreToolUse hook"
        for tool in ("Write", "Edit", "Bash", "NotebookEdit"):
            assert any(matcher_covers(matcher, tool) for matcher in matchers), (
                f"no test-guardian.sh PreToolUse registration covers {tool}: {matchers}")

    def test_manifest_matcher_covers_bash_and_notebook_edit(self):
        entry = manifest_entry("test-guardian.sh")
        for tool in ("Write", "Edit", "Bash", "NotebookEdit"):
            assert matcher_covers(entry.get("matcher", ""), tool), (
                f"hooks-manifest.json test-guardian.sh matcher {entry.get('matcher')!r} omits {tool}")


@pytest.fixture
def hidden_yaml(tmp_path_factory):
    shadow = tmp_path_factory.mktemp("shadow")
    (shadow / "yaml.py").write_text("raise ImportError(\"No module named 'yaml'\")\n", encoding="utf-8")
    return {"PYTHONPATH": str(shadow)}


class TestTestGuardianNeedsYamlToStayEnforcedR242:
    def test_hidden_yaml_really_cannot_be_imported(self, hidden_yaml):
        env = {**os.environ, **hidden_yaml}
        probe = subprocess.run(["python3", "-c", "import yaml"], env=env, capture_output=True, text=True, timeout=30)
        assert probe.returncode != 0

    def test_denies_test_file_write_when_yaml_is_missing(self, project, hidden_yaml):
        guarded_project(project)
        result = run_hook_with_env("test-guardian.sh", project, write_call(project, "tests/test_calc.py", "x\n"),
                                   env=hidden_yaml)
        assert_denied(result)

    def test_denial_names_the_missing_yaml_dependency(self, project, hidden_yaml):
        guarded_project(project)
        result = run_hook_with_env("test-guardian.sh", project, write_call(project, "tests/test_calc.py", "x\n"),
                                   env=hidden_yaml)
        assert_denied(result)
        assert "yaml" in deny_reason(result).lower()

    def test_denies_test_file_edit_when_yaml_is_missing(self, project, hidden_yaml):
        guarded_project(project)
        result = run_hook_with_env("test-guardian.sh", project, edit_call(project, "tests/test_x.py", "True", "False"),
                                   env=hidden_yaml)
        assert_denied(result)
        assert "yaml" in deny_reason(result).lower()

    def test_allows_source_write_when_yaml_is_missing(self, project, hidden_yaml):
        guarded_project(project)
        result = run_hook_with_env("test-guardian.sh", project, write_call(project, "src/calc.py", "x = 1\n"),
                                   env=hidden_yaml)
        assert_allowed(result)

    def test_allows_test_file_write_when_yaml_is_missing_and_sweetclaude_is_not_set_up(self, project, hidden_yaml):
        result = run_hook_with_env("test-guardian.sh", project, write_call(project, "tests/test_calc.py", "x\n"),
                                   env=hidden_yaml)
        assert_allowed(result)


class TestPreflightGuardAllowsItsOwnRemedyR244:
    def flagged(self, project: Path) -> None:
        needs_preflight_flag(project).write_text("", encoding="utf-8")

    def test_allows_the_configure_skill(self, project):
        self.flagged(project)
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:configure")
        assert_allowed(run_hook("preflight-guard.sh", project, stdin))

    @pytest.mark.parametrize("target", [".sweetclaude-skip", "./.sweetclaude-skip", "__PROJECT__/.sweetclaude-skip"])
    def test_allows_touching_the_skip_file(self, project, target):
        self.flagged(project)
        command = f"touch {target.replace('__PROJECT__', str(project))}"
        assert_allowed(run_hook("preflight-guard.sh", project, bash_call(project, command)))

    def test_denies_a_write(self, project):
        self.flagged(project)
        assert_denied(run_hook("preflight-guard.sh", project, write_call(project, "src/calc.py", "x = 1\n")))

    def test_denies_other_bash_commands(self, project):
        self.flagged(project)
        assert_denied(run_hook("preflight-guard.sh", project, bash_call(project, "echo hi")))

    def test_denies_touching_a_different_file(self, project):
        self.flagged(project)
        assert_denied(run_hook("preflight-guard.sh", project, bash_call(project, "touch other.txt")))

    def test_denies_the_skip_file_command_chained_with_another_command(self, project):
        self.flagged(project)
        command = "touch .sweetclaude-skip && rm -rf src"
        assert_denied(run_hook("preflight-guard.sh", project, bash_call(project, command)))

    def test_denies_a_different_skill(self, project):
        self.flagged(project)
        stdin = payload("PreToolUse-Skill", project, skill="other-plugin:thing")
        assert_denied(run_hook("preflight-guard.sh", project, stdin))
