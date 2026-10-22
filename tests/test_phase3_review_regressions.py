"""Phase 3 review regressions: gaps found reviewing the phase 3 enforcement hooks.

One class per review item. Tests named allows_* or silent_* are controls that
already hold and must keep holding while the failing cases are fixed.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from hook_stdin import deny_reason, run_hook as run_hook_with_env  # noqa: E402
from test_hook_protocol_contract import (  # noqa: E402
    REPO_ROOT,
    assert_allowed,
    assert_denied,
    enable_guardian,
    feedback_text,
    needs_preflight_flag,
    payload,
    project,
    run_hook,
    state_dir,
    write_kanban_gates,
    write_sweetclaude_yaml,
)
from test_phase3_enforcement_contract import (  # noqa: E402
    FAILING_TEST,
    PYTEST_PYPROJECT,
    bash_call,
    edit_call,
    guarded_project,
    hidden_yaml,
    implementing_project,
    pytest_path_env,
    write_call,
)

ISSUES = Path(".sweetclaude") / "product" / "roadmap" / "issues"
ACTIVATE_FOURTH = ('source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh" && '
                   "sc_artifact_write ISSUE-004 '{\"status\":\"active\"}'")


class TestPreflightGuardLetsTheRemedyThroughR244:
    def flagged(self, project: Path) -> None:
        needs_preflight_flag(project).write_text("", encoding="utf-8")

    @pytest.mark.parametrize("skill", ["sweetclaude:configure", "sweetclaude:status", "sweetclaude:library-load"])
    def test_allows_any_sweetclaude_skill(self, project, skill):
        self.flagged(project)
        assert_allowed(run_hook("preflight-guard.sh", project, payload("PreToolUse-Skill", project, skill=skill)))

    def test_allows_library_load_with_setup_args(self, project):
        self.flagged(project)
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:library-load", args="setup")
        assert_allowed(run_hook("preflight-guard.sh", project, stdin))

    def test_denies_a_skill_from_another_plugin(self, project):
        self.flagged(project)
        stdin = payload("PreToolUse-Skill", project, skill="otherplugin:thing")
        assert_denied(run_hook("preflight-guard.sh", project, stdin))

    @pytest.mark.parametrize("relative", [".sweetclaude/state/sweetclaude.yaml", ".sweetclaude/state/project.yaml",
                                          ".sweetclaude-skip"])
    def test_allows_write_under_sweetclaude_or_the_skip_file(self, project, relative):
        self.flagged(project)
        assert_allowed(run_hook("preflight-guard.sh", project, write_call(project, relative, "x: 1\n")))

    def test_allows_edit_under_sweetclaude(self, project):
        self.flagged(project)
        stdin = edit_call(project, ".sweetclaude/state/sweetclaude.yaml", "a", "b")
        assert_allowed(run_hook("preflight-guard.sh", project, stdin))

    @pytest.mark.parametrize("command", ["mkdir -p .sweetclaude/state", "touch .sweetclaude/state/guardian-enabled",
                                         "touch .sweetclaude-skip"])
    def test_allows_bash_targeting_sweetclaude_paths(self, project, command):
        self.flagged(project)
        assert_allowed(run_hook("preflight-guard.sh", project, bash_call(project, command)))

    def test_still_denies_source_write(self, project):
        self.flagged(project)
        assert_denied(run_hook("preflight-guard.sh", project, write_call(project, "src/app.py", "x = 1\n")))

    def test_still_denies_unrelated_bash(self, project):
        self.flagged(project)
        assert_denied(run_hook("preflight-guard.sh", project, bash_call(project, "echo hi")))

    def test_does_not_spawn_python_when_the_flag_is_absent(self, project, tmp_path):
        shim_dir = tmp_path / "shim"
        shim_dir.mkdir()
        marker = tmp_path / "python-spawned.marker"
        shim = shim_dir / "python3"
        shim.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 1\n", encoding="utf-8")
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        env = {"PATH": f"{shim_dir}{os.pathsep}/usr/bin{os.pathsep}/bin{os.pathsep}/sbin"}
        result = run_hook_with_env("preflight-guard.sh", project, bash_call(project, "echo hi"), env=env)
        assert not marker.exists(), "the hook spawned python3 although no preflight flag is set"
        assert_allowed(result)


class TestTestGuardianWithoutYamlR242:
    def test_denies_test_write_when_yaml_is_missing_and_sweetclaude_yaml_exists(self, project, hidden_yaml):
        guarded_project(project)
        result = run_hook_with_env("test-guardian.sh", project, write_call(project, "tests/test_calc.py", "x\n"),
                                   env=hidden_yaml)
        assert_denied(result)

    def test_allows_test_write_when_yaml_is_missing_and_no_sweetclaude_yaml_exists(self, project, hidden_yaml):
        assert not (project / ".sweetclaude" / "state" / "sweetclaude.yaml").exists()
        result = run_hook_with_env("test-guardian.sh", project, write_call(project, "tests/test_calc.py", "x\n"),
                                   env=hidden_yaml)
        assert_allowed(result)

    def test_allows_test_write_when_state_dir_has_no_sweetclaude_yaml_and_yaml_is_missing(self, project, hidden_yaml):
        enable_guardian(project)
        result = run_hook_with_env("test-guardian.sh", project, write_call(project, "tests/test_calc.py", "x\n"),
                                   env=hidden_yaml)
        assert_allowed(result)


ALLOWED_DURING_IMPLEMENTING = [
    "pytest tests/ > pytest_output.txt",
    "python3 -m pytest -q 2>&1 | tee run.log",
    "cp tests/test_a.py /tmp/x.py",
]
DENIED_DURING_IMPLEMENTING = [
    "rm tests/test_a.py",
    "mv tests/test_a.py /tmp/",
    "git checkout -- tests/test_a.py",
    "git restore tests/test_a.py",
    "cd tests && echo x > test_a.py",
    'python3 -c "print(1 << 3)"; echo x > tests/test_a.py',
    'python3 -c "print(1 << 3)"\necho x > tests/test_a.py',
]


class TestTestGuardianPathClassificationIsAnchoredR241:
    def prepare(self, project: Path) -> None:
        guarded_project(project)
        (project / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")

    @pytest.mark.parametrize("command", ALLOWED_DURING_IMPLEMENTING)
    def test_allows_bash_that_only_runs_or_reads_tests(self, project, command):
        self.prepare(project)
        assert_allowed(run_hook("test-guardian.sh", project, bash_call(project, command)))

    @pytest.mark.parametrize("relative", ["src/latest_x.py", "docs/specs/x.md", "src/contest_results.py"])
    def test_allows_write_to_non_test_paths_that_merely_contain_a_test_pattern(self, project, relative):
        self.prepare(project)
        assert_allowed(run_hook("test-guardian.sh", project, write_call(project, relative, "x\n")))

    @pytest.mark.parametrize("command", DENIED_DURING_IMPLEMENTING)
    def test_denies_bash_that_removes_moves_restores_or_overwrites_a_test(self, project, command):
        self.prepare(project)
        assert_denied(run_hook("test-guardian.sh", project, bash_call(project, command)))

    def test_still_denies_write_to_a_test_file(self, project):
        self.prepare(project)
        assert_denied(run_hook("test-guardian.sh", project, write_call(project, "tests/test_a.py", "x\n")))


def runner_project(project: Path, command: str) -> Path:
    implementing_project(project)
    marker = project / "ran.marker"
    (state_dir(project) / "project.yaml").write_text(f"testing:\n  test_command: {command.replace('MARKER', str(marker))}\n",
                                                      encoding="utf-8")
    return marker


def post_write(project: Path, path: Path | str) -> subprocess.CompletedProcess:
    stdin = payload("PostToolUse-Write", project, file_path=str(path))
    return run_hook("auto-test-runner.sh", project, stdin)


class TestAutoTestRunnerSkipsNonSourceFilesR072:
    @pytest.mark.parametrize("relative", ["README.md", "docs/x.md", ".sweetclaude/state/x.yaml", "config/x.yaml"])
    def test_does_not_run_for_documentation_or_config_writes(self, project, relative):
        marker = runner_project(project, "touch MARKER")
        result = post_write(project, project / relative)
        assert result.returncode == 0, result.stderr
        assert not marker.exists(), f"tests ran for a write to {relative}"

    def test_does_not_run_for_a_file_outside_the_project(self, project):
        marker = runner_project(project, "touch MARKER")
        outside = project.parent / "outside-the-project" / "app.py"
        result = post_write(project, outside)
        assert result.returncode == 0, result.stderr
        assert not marker.exists(), "tests ran for a write outside the project"

    def test_runs_for_a_source_write(self, project):
        marker = runner_project(project, "touch MARKER")
        post_write(project, project / "src" / "app.py")
        assert marker.exists()


class TestAutoTestRunnerCommandHandlingR079:
    def test_runs_a_yaml_quoted_command_without_its_quotes(self, project):
        marker = runner_project(project, "\"touch MARKER; printf 'QUOTED_%s' SENTINEL; exit 1\"")
        result = post_write(project, project / "src" / "app.py")
        assert marker.exists(), "the quoted command was not run as a command line"
        assert "QUOTED_SENTINEL" in feedback_text(result)

    def test_reports_exit_code_5_as_no_tests_collected(self, project):
        runner_project(project, "exit 5")
        result = post_write(project, project / "src" / "app.py")
        feedback = feedback_text(result)
        assert "no tests collected" in feedback.lower(), result.stdout
        assert "Tests failed" not in feedback

    def test_still_reports_exit_code_1_as_tests_failed(self, project):
        runner_project(project, "exit 1")
        feedback = feedback_text(post_write(project, project / "src" / "app.py"))
        assert "Tests failed" in feedback


def detection_feedback(project: Path) -> str:
    stdin = payload("PostToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
    result = run_hook_with_env("auto-test-runner.sh", project, stdin, env=pytest_path_env())
    assert result.returncode == 0, result.stderr
    return feedback_text(result)


class TestAutoTestRunnerDetectsOnlyDeclaredPytestR239:
    def prepare(self, project: Path) -> None:
        implementing_project(project)
        (project / "tests" / "test_calc.py").write_text(FAILING_TEST, encoding="utf-8")

    def test_detects_pytest_from_pyproject_ini_options(self, project):
        self.prepare(project)
        (project / "pyproject.toml").write_text(PYTEST_PYPROJECT, encoding="utf-8")
        assert "AUTODETECT_SENTINEL" in detection_feedback(project)

    def test_detects_pytest_from_setup_cfg_section(self, project):
        self.prepare(project)
        (project / "setup.cfg").write_text("[tool:pytest]\ntestpaths = tests\n", encoding="utf-8")
        assert "AUTODETECT_SENTINEL" in detection_feedback(project)

    def test_detects_pytest_from_pytest_ini(self, project):
        self.prepare(project)
        (project / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
        assert "AUTODETECT_SENTINEL" in detection_feedback(project)

    def test_detects_pytest_from_root_conftest(self, project):
        self.prepare(project)
        (project / "conftest.py").write_text("", encoding="utf-8")
        assert "AUTODETECT_SENTINEL" in detection_feedback(project)

    def test_pyproject_that_only_lists_pytest_as_a_dependency_does_not_trigger_detection(self, project):
        self.prepare(project)
        (project / "pyproject.toml").write_text(
            '[project]\nname = "fixture"\nversion = "0.0.1"\ndependencies = ["pytest>=8"]\n', encoding="utf-8")
        assert detection_feedback(project) == ""

    def test_setup_cfg_that_only_mentions_pytest_does_not_trigger_detection(self, project):
        self.prepare(project)
        (project / "setup.cfg").write_text("[metadata]\nname = fixture\n\n[options]\ninstall_requires =\n    pytest\n",
                                           encoding="utf-8")
        assert detection_feedback(project) == ""


def write_issue_bytes(project: Path, number: int, raw: bytes) -> None:
    folder = project / ISSUES
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"ISSUE-{number:03d}-work-item-{number}.md").write_bytes(raw)


def frontmatter(number: int, status: str, newline: str = "\n", trailing: bool = True) -> bytes:
    text = newline.join(["---", f"id: ISSUE-{number:03d}", f"title: Work item {number}", f"status: {status}", "---"])
    return (text + (newline if trailing else "")).encode("utf-8")


class TestWipLimitCountsEveryActiveSpellingR077:
    def prepare(self, project: Path) -> None:
        write_sweetclaude_yaml(project, phase="IMPLEMENT")
        write_kanban_gates(project, wip_limit=3)
        write_issue_bytes(project, 4, frontmatter(4, "ready"))

    def deny_fourth(self, project: Path) -> None:
        assert_denied(run_hook("wip-limit.sh", project, bash_call(project, ACTIVATE_FOURTH)))

    def test_counts_in_progress_issues(self, project):
        self.prepare(project)
        for number in (1, 2, 3):
            write_issue_bytes(project, number, frontmatter(number, "in_progress"))
        self.deny_fourth(project)

    def test_counts_a_mix_of_active_and_in_progress(self, project):
        self.prepare(project)
        write_issue_bytes(project, 1, frontmatter(1, "active"))
        write_issue_bytes(project, 2, frontmatter(2, "in_progress"))
        write_issue_bytes(project, 3, frontmatter(3, "in_progress"))
        self.deny_fourth(project)

    def test_counts_crlf_frontmatter(self, project):
        self.prepare(project)
        for number in (1, 2, 3):
            write_issue_bytes(project, number, frontmatter(number, "active", newline="\r\n"))
        self.deny_fourth(project)

    def test_counts_a_final_delimiter_without_trailing_newline(self, project):
        self.prepare(project)
        for number in (1, 2, 3):
            write_issue_bytes(project, number, frontmatter(number, "active", trailing=False))
        self.deny_fourth(project)

    def test_counts_crlf_frontmatter_without_trailing_newline(self, project):
        self.prepare(project)
        for number in (1, 2, 3):
            write_issue_bytes(project, number, frontmatter(number, "in_progress", newline="\r\n", trailing=False))
        self.deny_fourth(project)

    def test_allows_activation_with_two_in_progress_issues(self, project):
        self.prepare(project)
        for number in (1, 2):
            write_issue_bytes(project, number, frontmatter(number, "in_progress"))
        assert_allowed(run_hook("wip-limit.sh", project, bash_call(project, ACTIVATE_FOURTH)))

    def test_done_issues_do_not_count(self, project):
        self.prepare(project)
        for number in (1, 2):
            write_issue_bytes(project, number, frontmatter(number, "in_progress"))
        write_issue_bytes(project, 3, frontmatter(3, "done"))
        assert_allowed(run_hook("wip-limit.sh", project, bash_call(project, ACTIVATE_FOURTH)))


class TestTddPrewriteGuardianEvidenceAndScopeR081:
    def prepare(self, project: Path) -> None:
        enable_guardian(project)
        write_sweetclaude_yaml(project, phase="IMPLEMENT")

    def test_untracked_new_tests_directory_counts_as_test_evidence(self, project):
        self.prepare(project)
        (project / "tests" / "test_x.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
        status = subprocess.run(["git", "-C", str(project), "status", "--short"], capture_output=True, text=True)
        assert "?? tests/" in status.stdout
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, write_call(project, "src/app.py", "x = 1\n")))

    def test_denies_source_write_without_any_test_evidence(self, project):
        self.prepare(project)
        assert_denied(run_hook("tdd-prewrite-guardian.sh", project, write_call(project, "src/app.py", "x = 1\n")))

    def test_allows_a_write_to_a_path_outside_the_project(self, project):
        self.prepare(project)
        outside = project.parent / "outside-the-project" / "app.py"
        stdin = payload("PreToolUse-Write", project, file_path=str(outside), content="x = 1\n")
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, stdin))


class TestPhaseDwellingGuardLeadingDashesR075:
    def prepare(self, project: Path) -> None:
        write_sweetclaude_yaml(project)
        enable_guardian(project)

    def stop(self, project: Path, text: str) -> subprocess.CompletedProcess:
        data = json.loads(payload("Stop-none", project))
        data["stop_hook_active"] = False
        data["last_assistant_message"] = text
        return run_hook("phase-dwelling-guard.sh", project, json.dumps(data))

    @pytest.mark.parametrize("text", ["-n Ready to move on?", "-e Ready to move on?", "-n\nThe design is drafted. Ready to move on?",
                                      "-e \nShall we proceed?"])
    def test_blocks_advancement_language_after_a_leading_echo_flag(self, project, text):
        self.prepare(project)
        data = json.loads(self.stop(project, text).stdout or "{}")
        assert data.get("decision") == "block"

    @pytest.mark.parametrize("text", ["-n The design is drafted.", "-e Tell me what to change."])
    def test_allows_neutral_text_after_a_leading_echo_flag(self, project, text):
        self.prepare(project)
        assert_allowed(self.stop(project, text))


class TestProtectionStatusWithoutYamlCli:
    def run_cli(self, project: Path, hidden_yaml: dict) -> subprocess.CompletedProcess:
        env = {**os.environ, **hidden_yaml}
        return subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "protection_status.py"),
                               "--project-dir", str(project)],
                              env=env, capture_output=True, text=True, timeout=60)

    def test_prints_a_notice_instead_of_a_traceback(self, project, hidden_yaml):
        write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase="implementing")
        result = self.run_cli(project, hidden_yaml)
        output = result.stdout + result.stderr
        assert "Traceback" not in output, output
        assert "cannot be evaluated" in output.lower(), output
        assert "yaml" in output.lower()

    def test_exits_nonzero_when_protections_cannot_be_evaluated(self, project, hidden_yaml):
        write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase="implementing")
        result = self.run_cli(project, hidden_yaml)
        assert result.returncode != 0
        assert "Traceback" not in result.stderr

    def test_runs_normally_when_yaml_is_available(self, project):
        write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase="implementing")
        result = self.run_cli(project, {})
        assert "Traceback" not in result.stderr
        assert "cannot be evaluated" not in (result.stdout + result.stderr).lower()
