"""Phase 2 review regressions: path classification, flag hash, test-runner bound.

Contract: docs/design/hook-protocol.md. Helpers are shared with
tests/test_hook_protocol_contract.py.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from test_hook_protocol_contract import (
    HOOKS,
    REPO_ROOT,
    UNSET_IN_CLAUDE_CODE,
    _md5,
    assert_allowed,
    assert_denied,
    enable_guardian,
    feedback_text,
    payload,
    run_hook,
    state_dir,
    stdout_json,
    write_sweetclaude_yaml,
)


@pytest.fixture
def project(tmp_path_factory):
    parent = tmp_path_factory.mktemp("test_parent").resolve()
    path = parent / "project"
    path.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True, timeout=30)
    (path / "src").mkdir()
    (path / "tests").mkdir()
    assert "test" in str(path.parent.name)
    return path


@pytest.fixture
def plain_project(tmp_path_factory):
    path = tmp_path_factory.mktemp("proj").resolve()
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True, timeout=30)
    (path / "src").mkdir()
    return path


@pytest.fixture
def flags():
    created: list[Path] = []
    yield created
    for flag in created:
        flag.unlink(missing_ok=True)


def flag_path(kind: str, hashed_path: str) -> Path:
    return Path(f"/tmp/.sweetclaude-{kind}-{_md5(hashed_path)}")


def run_hook_in(name: str, cwd: Path, project_dir: str, stdin: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    for var in UNSET_IN_CLAUDE_CODE:
        env.pop(var, None)
    env.update({
        "HOME": str(cwd),
        "CLAUDE_PROJECT_DIR": project_dir,
        "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT),
        "CLAUDE_PLUGIN_DATA": str(cwd / ".plugin-data"),
    })
    return subprocess.run(["bash", str(HOOKS / name)], cwd=str(cwd), env=env, input=stdin,
                          capture_output=True, text=True, timeout=60)


class TestPathClassificationUsesProjectRelativePath:
    def test_test_guardian_allows_source_write_when_project_path_contains_test(self, project):
        write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase="implementing")
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        assert_allowed(run_hook("test-guardian.sh", project, stdin))

    def test_test_guardian_still_denies_test_file_when_project_path_contains_test(self, project):
        write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase="implementing")
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "tests" / "test_calc.py"))
        assert_denied(run_hook("test-guardian.sh", project, stdin))

    def test_tdd_prewrite_guardian_denies_source_write_when_project_path_contains_test(self, project):
        enable_guardian(project)
        (state_dir(project) / "phase.yaml").write_text("phase: IMPLEMENT\n", encoding="utf-8")
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        assert_denied(run_hook("tdd-prewrite-guardian.sh", project, stdin))

    def test_auto_test_runner_runs_command_for_source_write_when_project_path_contains_test(self, project):
        marker = project / "ran.marker"
        write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase="implementing")
        (state_dir(project) / "project.yaml").write_text(f"testing:\n  test_command: touch {marker}\n", encoding="utf-8")
        stdin = payload("PostToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        result = run_hook("auto-test-runner.sh", project, stdin)
        assert result.returncode == 0, result.stderr
        assert marker.exists(), "configured test command did not run"

    def test_artifact_guardian_warns_on_commit_when_project_path_contains_test(self, project):
        write_sweetclaude_yaml(project, phase="implement")
        enable_guardian(project)
        stdin = payload("PreToolUse-Bash", project, command="git commit -m x")
        result = run_hook("artifact-guardian.sh", project, stdin)
        assert result.returncode == 0, result.stderr
        assert "[Protocol Guardian] WARNING" in feedback_text(result)


class TestFlagHashMatchesBootstrapSkill:
    def repo_with_subdir(self, project: Path) -> Path:
        sub = project / "pkg"
        sub.mkdir()
        return sub

    def test_master_preflight_allows_when_launched_from_subdirectory_of_repo(self, project, flags):
        sub = self.repo_with_subdir(project)
        write_sweetclaude_yaml(project)
        write_sweetclaude_yaml(sub)
        flag = flag_path("bootstrap-ran", str(project))
        flag.write_text("", encoding="utf-8")
        flags.extend([flag, flag_path("bootstrap-ran", str(sub))])
        stdin = payload("PreToolUse-Skill", sub, skill="sweetclaude:status")
        assert_allowed(run_hook_in("master-preflight.sh", sub, str(sub), stdin))

    def test_master_preflight_allows_when_project_dir_has_trailing_slash(self, project, flags):
        write_sweetclaude_yaml(project)
        flag = flag_path("bootstrap-ran", str(project))
        flag.write_text("", encoding="utf-8")
        flags.extend([flag, flag_path("bootstrap-ran", f"{project}/")])
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:status")
        assert_allowed(run_hook_in("master-preflight.sh", project, f"{project}/", stdin))

    def test_master_preflight_hashes_plain_directory_when_not_a_git_repo(self, tmp_path_factory, flags):
        plain = tmp_path_factory.mktemp("test_parent").resolve() / "plain"
        plain.mkdir()
        write_sweetclaude_yaml(plain)
        flag = flag_path("bootstrap-ran", str(plain))
        flag.write_text("", encoding="utf-8")
        flags.append(flag)
        stdin = payload("PreToolUse-Skill", plain, skill="sweetclaude:status")
        assert_allowed(run_hook_in("master-preflight.sh", plain, f"{plain}/", stdin))

    def test_preflight_guard_denies_when_flag_hashed_by_repo_root_and_launched_from_subdirectory(self, project, flags):
        sub = self.repo_with_subdir(project)
        flag = flag_path("needs-preflight", str(project))
        flag.write_text("", encoding="utf-8")
        flags.extend([flag, flag_path("needs-preflight", str(sub))])
        stdin = payload("PreToolUse-Bash", sub, command="echo hi")
        assert_denied(run_hook_in("preflight-guard.sh", sub, str(sub), stdin))

    def test_preflight_guard_denies_when_project_dir_has_trailing_slash(self, project, flags):
        flag = flag_path("needs-preflight", str(project))
        flag.write_text("", encoding="utf-8")
        flags.extend([flag, flag_path("needs-preflight", f"{project}/")])
        stdin = payload("PreToolUse-Bash", project, command="echo hi")
        assert_denied(run_hook_in("preflight-guard.sh", project, f"{project}/", stdin))


class TestAutoTestRunnerBound:
    def prepare(self, project: Path, command: str, timeout_seconds: int | None = None) -> None:
        write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase="implementing")
        text = f"testing:\n  test_command: {command}\n"
        if timeout_seconds is not None:
            text += f"  timeout_seconds: {timeout_seconds}\n"
        (state_dir(project) / "project.yaml").write_text(text, encoding="utf-8")

    def test_times_out_a_command_that_outlives_the_configured_bound(self, plain_project):
        self.prepare(plain_project, "sleep 30", timeout_seconds=2)
        stdin = payload("PostToolUse-Write", plain_project, file_path=str(plain_project / "src" / "calc.py"))
        started = time.monotonic()
        try:
            result = run_hook("auto-test-runner.sh", plain_project, stdin)
        except subprocess.TimeoutExpired:
            pytest.fail("auto-test-runner blocked past 60s on a 2s bound")
        elapsed = time.monotonic() - started
        assert elapsed < 12, f"runner took {elapsed:.1f}s with timeout_seconds 2"
        assert result.returncode == 0, result.stderr
        text = feedback_text(result)
        assert "timed out" in text, f"timeout must be reported via additionalContext: {result.stdout!r}"
        assert "sleep 30" in text

    def test_very_long_single_line_output_yields_valid_json_with_the_tail(self, plain_project):
        script = plain_project / "noisy.sh"
        script.write_text("python3 -c \"print('x' * 300000 + 'TAIL_SENTINEL')\"\nexit 1\n", encoding="utf-8")
        self.prepare(plain_project, f"bash {script}")
        stdin = payload("PostToolUse-Write", plain_project, file_path=str(plain_project / "src" / "calc.py"))
        result = run_hook("auto-test-runner.sh", plain_project, stdin)
        assert result.returncode == 0, result.stderr
        data = stdout_json(result)
        assert isinstance(data, dict), f"stdout is not valid JSON: {result.stdout[:200]!r} stderr={result.stderr[:200]!r}"
        text = feedback_text(result)
        assert text.rstrip().endswith("TAIL_SENTINEL"), "additionalContext must carry the tail of the output"
        assert len(text) < 64 * 1024, f"additionalContext must be bounded, got {len(text)} chars"


class TestArtifactGuardianCommitForms:
    WARNING = "[Protocol Guardian] WARNING"

    def prepare(self, project: Path) -> None:
        write_sweetclaude_yaml(project, phase="implement")
        enable_guardian(project)

    @pytest.mark.parametrize("command", [
        "git -c user.email=a@b.c -c user.name=x commit --allow-empty -m guarded",
        "git -C sub commit -m x",
        "cd sub && git commit -m x",
        "make && git commit -m x",
    ])
    def test_warns_without_blocking_for_commit_form(self, project, command):
        self.prepare(project)
        result = run_hook("artifact-guardian.sh", project, payload("PreToolUse-Bash", project, command=command))
        assert_allowed(result)
        data = stdout_json(result)
        assert isinstance(data, dict), f"warning must be JSON on stdout: {result.stdout!r}"
        specific = data.get("hookSpecificOutput") or {}
        assert self.WARNING in str(specific.get("additionalContext") or "")
        assert specific.get("permissionDecision") != "deny"
        assert data.get("decision") != "block"

    @pytest.mark.parametrize("command", [
        "git commit-tree abc",
        'echo "git commit"',
        "git log --grep commit",
    ])
    def test_silent_for_non_commit_control(self, project, command):
        self.prepare(project)
        result = run_hook("artifact-guardian.sh", project, payload("PreToolUse-Bash", project, command=command))
        assert_allowed(result)
        assert "[Protocol Guardian]" not in result.stdout + result.stderr
