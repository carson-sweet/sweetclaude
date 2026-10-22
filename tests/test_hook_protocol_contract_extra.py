"""Protocol contract tests for the remaining hooks that touched the dead protocol (phase 2).

Companion to tests/test_hook_protocol_contract.py. Each hook here is run with
the real captured stdin payload for its event, an environment that never
carries CLAUDE_TOOL_NAME, CLAUDE_FILE_PATH or CLAUDE_TRANSCRIPT_PATH, and its
output judged against docs/design/hook-protocol.md.

Hooks covered: state-regenerator (PostToolUse Write|Edit), skill-tracker
(PostToolUse Skill), auto-reindex (PostToolUse file edits),
migration-decision-reminder (UserPromptSubmit), small-story-stop-guard and
large-story-stop-guard (Stop).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from hook_stdin import (  # noqa: E402
    assert_allowed, assert_blocked, feedback_text, payload, prompt_payload, run_hook, stdout_json,
    stop_payload,
)
import test_large_story_hooks as large  # noqa: E402
import test_small_story_hooks as small  # noqa: E402

needs_jq = pytest.mark.skipif(shutil.which("jq") is None, reason="hook shells out to jq")


@pytest.fixture
def project(tmp_path_factory):
    path = tmp_path_factory.mktemp("proj").resolve()
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True, timeout=30)
    state = path / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2,
        "project": {"name": "t", "version_stage": "GA"},
        "framework": {"setup_complete": True},
        "work": {"active": {"id": "ISSUE-1", "phase": "IMPLEMENT"}},
    }), encoding="utf-8")
    return path


def state_dir(project: Path) -> Path:
    return project / ".sweetclaude" / "state"


class TestStateRegeneratorPostToolUse:
    def regenerated(self, project: Path, stdin: str, *, timeout: float = 20.0) -> bool:
        out = state_dir(project) / "session-state.yaml"
        out.unlink(missing_ok=True)
        result = run_hook("state-regenerator.sh", project, stdin)
        assert_allowed(result)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if out.exists():
                return True
            time.sleep(0.1)
        return False

    def test_regenerates_when_write_payload_names_a_watched_file(self, project):
        stdin = payload("PostToolUse-Write", project, file_path=str(state_dir(project) / "sweetclaude.yaml"))
        assert self.regenerated(project, stdin)

    def test_regenerates_when_edit_payload_names_a_watched_file(self, project):
        stdin = payload("PostToolUse-Edit", project, file_path=str(state_dir(project) / "sweetclaude.yaml"))
        assert self.regenerated(project, stdin)

    def test_does_not_regenerate_for_an_unwatched_write(self, project):
        stdin = payload("PostToolUse-Write", project, file_path=str(project / "src" / "main.py"))
        assert not self.regenerated(project, stdin, timeout=2.0)

    def test_does_not_regenerate_for_a_bash_payload(self, project):
        stdin = payload("PostToolUse-Bash", project, command="echo hi")
        assert not self.regenerated(project, stdin, timeout=2.0)

    def test_does_not_regenerate_for_a_read_of_a_watched_file(self, project):
        stdin = payload("PostToolUse-Write", project, tool="Read",
                        file_path=str(state_dir(project) / "sweetclaude.yaml"))
        assert not self.regenerated(project, stdin, timeout=2.0)


class TestSkillTrackerPostToolUse:
    def prepare(self, project: Path, *, guardian: bool = True) -> Path:
        session = state_dir(project) / "session-guardian.json"
        session.write_text(json.dumps({"enabled": True, "skills_invoked": [], "test_files_written": [],
                                       "artifacts_created": [], "tdd_status": "pending"}), encoding="utf-8")
        if guardian:
            (state_dir(project) / "guardian-enabled").write_text("", encoding="utf-8")
        return session

    @needs_jq
    def test_records_the_skill_named_in_the_payload(self, project):
        session = self.prepare(project)
        result = run_hook("skill-tracker.sh", project, payload("PostToolUse-Skill", project, skill="sweetclaude:code-feature"))
        assert_allowed(result)
        assert json.loads(session.read_text())["skills_invoked"] == ["sweetclaude:code-feature"]

    @needs_jq
    def test_appends_successive_skills(self, project):
        session = self.prepare(project)
        run_hook("skill-tracker.sh", project, payload("PostToolUse-Skill", project, skill="sweetclaude:one"))
        run_hook("skill-tracker.sh", project, payload("PostToolUse-Skill", project, skill="sweetclaude:two"))
        assert json.loads(session.read_text())["skills_invoked"] == ["sweetclaude:one", "sweetclaude:two"]

    @needs_jq
    def test_ignores_a_write_payload(self, project):
        session = self.prepare(project)
        stdin = payload("PostToolUse-Write", project, file_path=str(project / "src" / "a.py"), skill="sweetclaude:sneaky")
        assert_allowed(run_hook("skill-tracker.sh", project, stdin))
        assert json.loads(session.read_text())["skills_invoked"] == []

    @needs_jq
    def test_records_nothing_when_guardian_is_off(self, project):
        session = self.prepare(project, guardian=False)
        assert_allowed(run_hook("skill-tracker.sh", project, payload("PostToolUse-Skill", project, skill="sweetclaude:one")))
        assert json.loads(session.read_text())["skills_invoked"] == []


class TestAutoReindexPostToolUse:
    def rag_config(self, project: Path, *dirs: Path) -> None:
        (state_dir(project) / "rag-config.yaml").write_text(
            "indexed_paths:\n" + "".join(f"  - {d}\n" for d in dirs), encoding="utf-8")

    def indexed_doc(self, project: Path) -> Path:
        docs = project / "docs"
        docs.mkdir()
        self.rag_config(project, docs)
        target = docs / "note.md"
        target.write_text("x\n", encoding="utf-8")
        return target

    def reported(self, result) -> str:
        return result.stderr + feedback_text(result)

    def test_reindexes_a_written_indexed_file(self, project):
        target = self.indexed_doc(project)
        result = run_hook("auto-reindex.sh", project, payload("PostToolUse-Write", project, file_path=str(target)))
        assert result.returncode == 0, result.stderr
        assert f"RAG: Reindexing {target}" in self.reported(result)

    def test_reindexes_an_edited_indexed_file(self, project):
        target = self.indexed_doc(project)
        result = run_hook("auto-reindex.sh", project, payload("PostToolUse-Edit", project, file_path=str(target)))
        assert result.returncode == 0, result.stderr
        assert f"RAG: Reindexing {target}" in self.reported(result)

    def test_stands_down_for_a_bash_payload(self, project):
        self.indexed_doc(project)
        result = run_hook("auto-reindex.sh", project, payload("PostToolUse-Bash", project, command="echo hi"))
        assert_allowed(result)
        assert "RAG" not in self.reported(result)

    def test_stands_down_outside_the_indexed_paths(self, project):
        self.indexed_doc(project)
        other = project / "elsewhere" / "note.md"
        other.parent.mkdir()
        other.write_text("x\n", encoding="utf-8")
        result = run_hook("auto-reindex.sh", project, payload("PostToolUse-Write", project, file_path=str(other)))
        assert_allowed(result)
        assert "RAG" not in self.reported(result)

    def test_stands_down_without_a_rag_config(self, project):
        target = project / "note.md"
        target.write_text("x\n", encoding="utf-8")
        result = run_hook("auto-reindex.sh", project, payload("PostToolUse-Write", project, file_path=str(target)))
        assert_allowed(result)
        assert "RAG" not in self.reported(result)


class TestMigrationDecisionReminderUserPromptSubmit:
    def marker(self, project: Path, turn_count: int) -> Path:
        path = state_dir(project) / "pending-migration-decision.yaml"
        path.write_text(yaml.safe_dump({
            "turn_count": turn_count,
            "snapshot": {"tarball_path": "/snap.tar", "git_tag": "pre-migrate"}}), encoding="utf-8")
        return path

    def run(self, project: Path):
        return run_hook("migration-decision-reminder.sh", project, payload("UserPromptSubmit-none", project))

    def test_is_silent_with_no_pending_decision(self, project):
        result = self.run(project)
        assert_allowed(result)
        assert feedback_text(result) == ""
        assert result.stdout.strip() == ""

    def test_reminds_through_additional_context(self, project):
        self.marker(project, 0)
        result = self.run(project)
        assert_allowed(result)
        data = stdout_json(result)
        assert data["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        assert "pending Accept/Rollback decision" in data["hookSpecificOutput"]["additionalContext"]
        assert data.get("continue") is not False

    def test_reminder_carries_the_snapshot(self, project):
        self.marker(project, 0)
        message = stdout_json(self.run(project))["systemMessage"]
        assert "/snap.tar" in message
        assert "pre-migrate" in message

    def test_turn_count_advances(self, project):
        marker = self.marker(project, 3)
        self.run(project)
        assert yaml.safe_load(marker.read_text())["turn_count"] == 4

    def test_stops_work_at_the_limit_through_additional_context(self, project):
        self.marker(project, 9)
        result = self.run(project)
        data = stdout_json(result)
        assert data["continue"] is False
        assert data["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        assert "Defer decision window has expired" in data["hookSpecificOutput"]["additionalContext"]
        assert "ok" not in data

    def test_fails_open_on_an_unreadable_marker(self, project):
        (state_dir(project) / "pending-migration-decision.yaml").write_text("{ not: valid: yaml", encoding="utf-8")
        result = self.run(project)
        assert_allowed(result)
        assert "continue" not in result.stdout

    def test_prompt_text_does_not_change_the_outcome(self, project):
        self.marker(project, 0)
        result = run_hook("migration-decision-reminder.sh", project, prompt_payload(project, "something else entirely"))
        assert_allowed(result)
        assert "Pending migration decision" in stdout_json(result)["systemMessage"]


class TestStopGuardsRealStopPayload:
    @pytest.mark.parametrize("hook,module", [
        ("small-story-stop-guard.sh", small),
        ("large-story-stop-guard.sh", large),
    ])
    def test_blocks_while_a_workflow_is_active(self, tmp_path, hook, module):
        workflow_project = module._project_with_workflow(tmp_path)
        module._advance_to_implement(workflow_project)
        result = run_hook(hook, workflow_project, stop_payload(workflow_project, "Done.", active=False))
        assert_blocked(result)
        assert "STORY-001" in stdout_json(result)["reason"]

    @pytest.mark.parametrize("hook,module", [
        ("small-story-stop-guard.sh", small),
        ("large-story-stop-guard.sh", large),
    ])
    def test_does_not_block_when_stop_hook_is_already_active(self, tmp_path, hook, module):
        workflow_project = module._project_with_workflow(tmp_path)
        module._advance_to_implement(workflow_project)
        result = run_hook(hook, workflow_project, stop_payload(workflow_project, "Done.", active=True))
        assert_allowed(result)
        assert result.stdout.strip() == ""

    @pytest.mark.parametrize("hook", ["small-story-stop-guard.sh", "large-story-stop-guard.sh"])
    def test_is_silent_without_a_workflow(self, project, hook):
        result = run_hook(hook, project, stop_payload(project, "Done."))
        assert_allowed(result)
        assert result.stdout.strip() == ""
