"""Protocol contract tests for the eight inert-enforcement hooks (phase 2).

Each hook is run exactly as Claude Code 2.1.305 runs it: a subprocess whose
stdin is the real captured JSON payload, whose environment carries
CLAUDE_PROJECT_DIR and CLAUDE_PLUGIN_ROOT but never CLAUDE_TOOL_NAME,
CLAUDE_FILE_PATH or CLAUDE_TRANSCRIPT_PATH, and whose output is judged against
docs/design/hook-protocol.md: a PreToolUse block is a permissionDecision deny
or exit 2 with stderr, feedback is additionalContext or a decision block, and
an {"ok": ...} object is ignored by Claude Code so it never counts as a
decision.

Ledger rows covered: R-070 test-guardian, R-071 tdd-prewrite-guardian, R-072
auto-test-runner, R-073 wip-limit, R-074 preflight-guard, R-075
phase-dwelling-guard, R-076 master-preflight, R-236 artifact-guardian.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
HOOKS = REPO_ROOT / "hooks"
PAYLOADS = REPO_ROOT / "tests" / "fixtures" / "hook_payloads"
UNSET_IN_CLAUDE_CODE = ("CLAUDE_TOOL_NAME", "CLAUDE_FILE_PATH", "CLAUDE_TRANSCRIPT_PATH", "PROJECT_DIR")


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


@pytest.fixture
def project(tmp_path_factory):
    path = tmp_path_factory.mktemp("proj").resolve()
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True, timeout=30)
    (path / "src").mkdir()
    (path / "tests").mkdir()
    flags = [
        Path(f"/tmp/.sweetclaude-needs-preflight-{_md5(str(path))}"),
        Path(f"/tmp/.sweetclaude-bootstrap-ran-{_md5(str(path))}"),
    ]
    for flag in flags:
        flag.unlink(missing_ok=True)
    yield path
    for flag in flags:
        flag.unlink(missing_ok=True)


def needs_preflight_flag(project: Path) -> Path:
    return Path(f"/tmp/.sweetclaude-needs-preflight-{_md5(str(project))}")


def bootstrap_flag(project: Path) -> Path:
    return Path(f"/tmp/.sweetclaude-bootstrap-ran-{_md5(str(project))}")


def state_dir(project: Path) -> Path:
    path = project / ".sweetclaude" / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_sweetclaude_yaml(project: Path, *, phase: str = "IMPLEMENT", tdd_phase: str | None = None) -> None:
    active = {"id": "ISSUE-1", "phase": phase}
    if tdd_phase:
        active["tdd_phase"] = tdd_phase
    (state_dir(project) / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2,
        "project": {"name": "t", "mode": "kanban"},
        "framework": {"setup_complete": True},
        "work": {"active": active},
    }), encoding="utf-8")


def enable_guardian(project: Path) -> None:
    (state_dir(project) / "guardian-enabled").write_text("", encoding="utf-8")


def payload(kind: str, project: Path, **tool_input) -> str:
    raw = (PAYLOADS / f"{kind}.json").read_text(encoding="utf-8").replace("__CWD__", str(project))
    data = json.loads(raw)
    if tool_input:
        data["tool_input"] = {**data.get("tool_input", {}), **tool_input}
    return json.dumps(data)


def run_hook(name: str, project: Path, stdin: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    for var in UNSET_IN_CLAUDE_CODE:
        env.pop(var, None)
    env.update({
        "HOME": str(project),
        "CLAUDE_PROJECT_DIR": str(project),
        "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT),
        "CLAUDE_PLUGIN_DATA": str(project / ".plugin-data"),
    })
    runner = ["python3"] if name.endswith(".py") else ["bash"]
    return subprocess.run([*runner, str(HOOKS / name)], cwd=str(project), env=env, input=stdin,
                          capture_output=True, text=True, timeout=60)


def stdout_json(result: subprocess.CompletedProcess):
    text = result.stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def feedback_text(result: subprocess.CompletedProcess) -> str:
    data = stdout_json(result)
    if not isinstance(data, dict):
        return ""
    specific = data.get("hookSpecificOutput") or {}
    parts = [specific.get("additionalContext") or ""]
    if data.get("decision") == "block":
        parts.append(data.get("reason") or "")
    return "\n".join(part for part in parts if part)


def assert_denied(result: subprocess.CompletedProcess) -> None:
    if result.returncode == 2:
        assert result.stderr.strip(), "exit 2 must carry the reason on stderr"
        return
    assert result.returncode == 0, f"unexpected exit {result.returncode}: {result.stderr}"
    data = stdout_json(result)
    assert isinstance(data, dict), f"no JSON decision on stdout: {result.stdout!r}"
    specific = data.get("hookSpecificOutput") or {}
    assert specific.get("permissionDecision") == "deny", f"not a deny decision: {result.stdout!r}"
    assert str(specific.get("permissionDecisionReason") or "").strip(), "deny needs a non-empty reason"


def assert_allowed(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 0, f"unexpected exit {result.returncode}: {result.stderr}"
    data = stdout_json(result)
    if isinstance(data, dict):
        specific = data.get("hookSpecificOutput") or {}
        assert specific.get("permissionDecision") != "deny", result.stdout
        assert data.get("decision") != "block", result.stdout
        assert "ok" not in data, f'{{"ok": ...}} is ignored by Claude Code and must not be emitted: {result.stdout!r}'
    assert '"ok"' not in result.stdout.replace("'", '"'), f'{{"ok": ...}} output is forbidden: {result.stdout!r}'


class TestTestGuardianR070:
    def prepare(self, project: Path, *, tdd_phase: str = "implementing") -> None:
        write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase=tdd_phase)

    def test_blocks_write_to_test_file_during_implementing(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "tests" / "test_calc.py"))
        assert_denied(run_hook("test-guardian.sh", project, stdin))

    def test_blocks_edit_to_test_file_during_implementing(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Edit", project, file_path=str(project / "tests" / "test_calc.py"))
        assert_denied(run_hook("test-guardian.sh", project, stdin))

    def test_allows_source_file_during_implementing(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        assert_allowed(run_hook("test-guardian.sh", project, stdin))

    def test_allows_test_file_when_not_implementing(self, project):
        self.prepare(project, tdd_phase="red")
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "tests" / "test_calc.py"))
        assert_allowed(run_hook("test-guardian.sh", project, stdin))


class TestTddPrewriteGuardianR071:
    def prepare(self, project: Path, *, phase: str = "IMPLEMENT") -> None:
        enable_guardian(project)
        (state_dir(project) / "phase.yaml").write_text(f"phase: {phase}\n", encoding="utf-8")

    def test_blocks_source_write_with_no_test_files(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        assert_denied(run_hook("tdd-prewrite-guardian.sh", project, stdin))

    def test_blocks_source_edit_with_no_test_files(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Edit", project, file_path=str(project / "src" / "calc.py"))
        assert_denied(run_hook("tdd-prewrite-guardian.sh", project, stdin))

    def test_allows_source_write_once_tests_are_recorded(self, project):
        self.prepare(project)
        (state_dir(project) / "session-guardian.json").write_text(
            json.dumps({"test_files_written": ["tests/test_calc.py"]}), encoding="utf-8")
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, stdin))

    def test_allows_test_file_write(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "tests" / "test_calc.py"))
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, stdin))

    def test_allows_source_write_when_guardian_disabled(self, project):
        self.prepare(project)
        (state_dir(project) / "guardian-enabled").unlink()
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, stdin))

    def test_allows_source_write_outside_implement_phase(self, project):
        self.prepare(project, phase="DESIGN")
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        assert_allowed(run_hook("tdd-prewrite-guardian.sh", project, stdin))


class TestAutoTestRunnerR072:
    def prepare(self, project: Path, command: str, *, tdd_phase: str = "implementing") -> Path:
        write_sweetclaude_yaml(project, phase="IMPLEMENT", tdd_phase=tdd_phase)
        (state_dir(project) / "project.yaml").write_text(f"testing:\n  test_command: {command}\n", encoding="utf-8")
        return project / "ran.marker"

    def test_runs_configured_command_on_source_write(self, project):
        marker = project / "ran.marker"
        self.prepare(project, f"touch {marker}")
        stdin = payload("PostToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        result = run_hook("auto-test-runner.sh", project, stdin)
        assert result.returncode == 0, result.stderr
        assert marker.exists(), "configured test command did not run"

    def test_runs_configured_command_on_source_edit(self, project):
        marker = project / "ran.marker"
        self.prepare(project, f"touch {marker}")
        stdin = payload("PostToolUse-Edit", project, file_path=str(project / "src" / "calc.py"))
        result = run_hook("auto-test-runner.sh", project, stdin)
        assert result.returncode == 0, result.stderr
        assert marker.exists(), "configured test command did not run"

    def test_reports_failing_run_back_to_the_model(self, project):
        marker = project / "ran.marker"
        self.prepare(project, f"echo AUTOTEST_FAILURE_SENTINEL; touch {marker}; exit 1")
        stdin = payload("PostToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        result = run_hook("auto-test-runner.sh", project, stdin)
        assert result.returncode == 0, result.stderr
        assert marker.exists(), "configured test command did not run before the process returned"
        assert "AUTOTEST_FAILURE_SENTINEL" in feedback_text(result), (
            f"failing test output must reach the model via additionalContext or a decision block: {result.stdout!r}")

    def test_does_not_run_for_test_file_edit(self, project):
        marker = project / "ran.marker"
        self.prepare(project, f"touch {marker}")
        stdin = payload("PostToolUse-Write", project, file_path=str(project / "tests" / "test_calc.py"))
        result = run_hook("auto-test-runner.sh", project, stdin)
        assert result.returncode == 0
        assert not marker.exists()
        assert_allowed(result)

    def test_does_not_run_when_not_implementing(self, project):
        marker = project / "ran.marker"
        self.prepare(project, f"touch {marker}", tdd_phase="red")
        stdin = payload("PostToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        result = run_hook("auto-test-runner.sh", project, stdin)
        assert result.returncode == 0
        assert not marker.exists()
        assert_allowed(result)


class TestPreflightGuardR074:
    def test_denies_tool_call_when_flagged_and_unconfigured(self, project):
        needs_preflight_flag(project).write_text("", encoding="utf-8")
        stdin = payload("PreToolUse-Bash", project, command="echo hi")
        assert_denied(run_hook("preflight-guard.sh", project, stdin))

    def test_denies_write_when_flagged_and_unconfigured(self, project):
        needs_preflight_flag(project).write_text("", encoding="utf-8")
        stdin = payload("PreToolUse-Write", project, file_path=str(project / "src" / "calc.py"))
        assert_denied(run_hook("preflight-guard.sh", project, stdin))

    def test_allows_when_no_flag(self, project):
        stdin = payload("PreToolUse-Bash", project, command="echo hi")
        assert_allowed(run_hook("preflight-guard.sh", project, stdin))

    def test_allows_when_project_is_configured(self, project):
        needs_preflight_flag(project).write_text("", encoding="utf-8")
        write_sweetclaude_yaml(project)
        stdin = payload("PreToolUse-Bash", project, command="echo hi")
        assert_allowed(run_hook("preflight-guard.sh", project, stdin))

    def test_allows_when_project_opted_out(self, project):
        needs_preflight_flag(project).write_text("", encoding="utf-8")
        (project / ".sweetclaude-skip").write_text("", encoding="utf-8")
        stdin = payload("PreToolUse-Bash", project, command="echo hi")
        assert_allowed(run_hook("preflight-guard.sh", project, stdin))


class TestPhaseDwellingGuardR075:
    def transcript(self, project: Path, text: str) -> None:
        lines = [
            {"type": "user", "message": {"role": "user", "content": "how is the design?"}},
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}},
        ]
        (project / ".transcript.jsonl").write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")

    def stop_payload(self, project: Path, text: str, *, active: bool = False) -> str:
        data = json.loads(payload("Stop-none", project))
        data["stop_hook_active"] = active
        data["last_assistant_message"] = text
        return json.dumps(data)

    def prepare(self, project: Path, text: str) -> None:
        write_sweetclaude_yaml(project)
        enable_guardian(project)
        self.transcript(project, text)

    def test_blocks_stop_when_response_pushes_advancement(self, project):
        text = "The design is drafted. Ready to move on?"
        self.prepare(project, text)
        result = run_hook("phase-dwelling-guard.sh", project, self.stop_payload(project, text))
        assert result.returncode == 0, result.stderr
        data = stdout_json(result)
        assert isinstance(data, dict), f"no JSON decision on stdout: {result.stdout!r}"
        assert data.get("decision") == "block"
        assert str(data.get("reason") or "").strip()

    def test_does_not_block_when_stop_hook_already_active(self, project):
        text = "The design is drafted. Ready to move on?"
        self.prepare(project, text)
        result = run_hook("phase-dwelling-guard.sh", project, self.stop_payload(project, text, active=True))
        assert_allowed(result)

    def test_allows_neutral_response(self, project):
        text = "The design is drafted. Tell me what to change."
        self.prepare(project, text)
        assert_allowed(run_hook("phase-dwelling-guard.sh", project, self.stop_payload(project, text)))

    def test_allows_advancement_language_when_guardian_disabled(self, project):
        text = "The design is drafted. Ready to move on?"
        self.prepare(project, text)
        (state_dir(project) / "guardian-enabled").unlink()
        assert_allowed(run_hook("phase-dwelling-guard.sh", project, self.stop_payload(project, text)))


class TestMasterPreflightR076:
    def prepare(self, project: Path) -> None:
        write_sweetclaude_yaml(project)

    def test_denies_sweetclaude_skill_without_bootstrap(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:status")
        assert_denied(run_hook("master-preflight.sh", project, stdin))

    def test_denies_sweetclaude_skill_with_pending_drift_decision(self, project):
        self.prepare(project)
        bootstrap_flag(project).write_text("", encoding="utf-8")
        (state_dir(project) / "pending-drift-decision.yaml").write_text("case: A\n", encoding="utf-8")
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:status")
        assert_denied(run_hook("master-preflight.sh", project, stdin))

    def test_allows_after_bootstrap_ran(self, project):
        self.prepare(project)
        bootstrap_flag(project).write_text("", encoding="utf-8")
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:status")
        assert_allowed(run_hook("master-preflight.sh", project, stdin))

    def test_allows_bootstrap_skill_itself(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:bootstrap")
        assert_allowed(run_hook("master-preflight.sh", project, stdin))

    def test_allows_non_sweetclaude_skill(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Skill", project, skill="other-plugin:thing")
        assert_allowed(run_hook("master-preflight.sh", project, stdin))

    def test_allows_when_project_not_configured(self, project):
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:status")
        assert_allowed(run_hook("master-preflight.sh", project, stdin))


class TestWipLimitR073:
    def prepare(self, project: Path, *, in_progress: int, mode: str = "kanban") -> None:
        write_sweetclaude_yaml(project, phase="IMPLEMENT")
        (state_dir(project) / "effective-gates.yaml").write_text(
            yaml.safe_dump({"mode": mode, "wip_limit": 3}), encoding="utf-8")
        issues = project / ".sweetclaude" / "artifacts" / "issues"
        issues.mkdir(parents=True)
        for number in range(in_progress):
            (issues / f"ISSUE-{number}.yaml").write_text(yaml.safe_dump({"status": "in_progress"}), encoding="utf-8")

    def test_denies_when_kanban_wip_limit_reached(self, project):
        self.prepare(project, in_progress=3)
        stdin = payload("PreToolUse-Bash", project, command="echo start-new-work")
        assert_denied(run_hook("wip-limit.sh", project, stdin))

    def test_allows_below_limit(self, project):
        self.prepare(project, in_progress=2)
        stdin = payload("PreToolUse-Bash", project, command="echo start-new-work")
        assert_allowed(run_hook("wip-limit.sh", project, stdin))

    def test_allows_when_mode_is_not_kanban(self, project):
        self.prepare(project, in_progress=3, mode="flow")
        stdin = payload("PreToolUse-Bash", project, command="echo start-new-work")
        assert_allowed(run_hook("wip-limit.sh", project, stdin))


class TestArtifactGuardianR236:
    def prepare(self, project: Path) -> None:
        write_sweetclaude_yaml(project, phase="implement")
        enable_guardian(project)

    def test_warns_on_commit_with_missing_artifacts_without_blocking(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Bash", project, command="git commit -m x")
        result = run_hook("artifact-guardian.sh", project, stdin)
        assert result.returncode == 0, result.stderr
        data = stdout_json(result)
        assert isinstance(data, dict), (
            f"warning must be on stdout as JSON additionalContext; stderr is not shown to the model: {result.stdout!r}")
        specific = data.get("hookSpecificOutput") or {}
        assert "[Protocol Guardian] WARNING" in str(specific.get("additionalContext") or "")
        assert specific.get("permissionDecision") != "deny"
        assert data.get("decision") != "block"

    def test_warns_on_commit_with_all_flag_forms(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Bash", project, command="git commit --amend --no-edit")
        assert "[Protocol Guardian] WARNING" in feedback_text(run_hook("artifact-guardian.sh", project, stdin))

    def test_silent_for_non_commit_command(self, project):
        self.prepare(project)
        stdin = payload("PreToolUse-Bash", project, command="git status")
        result = run_hook("artifact-guardian.sh", project, stdin)
        assert_allowed(result)
        assert "[Protocol Guardian]" not in result.stdout + result.stderr

    def test_silent_when_guardian_disabled(self, project):
        self.prepare(project)
        (state_dir(project) / "guardian-enabled").unlink()
        stdin = payload("PreToolUse-Bash", project, command="git commit -m x")
        result = run_hook("artifact-guardian.sh", project, stdin)
        assert_allowed(result)
        assert "[Protocol Guardian]" not in result.stdout + result.stderr

    def test_silent_when_artifacts_present(self, project):
        self.prepare(project)
        (state_dir(project) / "session-guardian.json").write_text(
            json.dumps({"test_files_written": ["tests/test_calc.py"], "tdd_status": "green"}), encoding="utf-8")
        stdin = payload("PreToolUse-Bash", project, command="git commit -m x")
        result = run_hook("artifact-guardian.sh", project, stdin)
        assert_allowed(result)
        assert "[Protocol Guardian]" not in result.stdout + result.stderr
