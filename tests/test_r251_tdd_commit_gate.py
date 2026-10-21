"""R-251: committing implementation before the RED tests is refused by a PreToolUse hook.

Assumed interface: hooks/tdd-commit-gate.sh, registered in hooks/hooks.json as a
PreToolUse Bash hook and declared in hooks/hooks-manifest.json, denies a `git
commit` whose staged, added or `-a`-committed paths include a non-test project
source file when ALL of these hold: the active phase is implement, a TDD cycle
marker (work.active.tdd_phase in sweetclaude.yaml, one of writing_tests /
implementing / refactoring — never written for Level 0) is present, the current
branch is a story branch (issue-NNN/... or story/... per the code-tdd skill and
the story controllers), and no commit reachable from HEAD has a subject starting
`test: RED`. The denial is the standard PreToolUse deny JSON naming the remedy
(commit the failing tests first as `test: RED - <description>`). Everything else
allows: no cycle, non-implement phase, non-story branch, non-commit commands,
test-only or docs-only commits, an unresolvable `git add` target, and projects
without SweetClaude state. A project whose state cannot be read because PyYAML
is missing is denied, the test-guardian convention for the same state read.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
HOOKS = REPO_ROOT / "hooks"
sys.path.insert(0, str(Path(__file__).parent))
from hook_stdin import (  # noqa: E402
    assert_allowed, assert_denied, deny_reason, hook_env, payload, run_hook, verdict,
)

GIT_IDENTITY = ("-c", "user.email=t@example.invalid", "-c", "user.name=T")
HOOK = "tdd-commit-gate.sh"
RED_MESSAGE = "test: RED - ISSUE-001 failing tests"


def _git(project: Path, *args: str) -> None:
    result = subprocess.run(["git", *GIT_IDENTITY, "-C", str(project), *args],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def _write_active(project: Path, phase: str, tdd_phase: str | None) -> None:
    active = {"id": "ISSUE-001", "phase": phase}
    if tdd_phase:
        active["tdd_phase"] = tdd_phase
    (project / ".sweetclaude" / "state" / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2,
        "project": {"name": "t", "mode": "kanban"},
        "framework": {"setup_complete": True},
        "work": {"active": active},
    }), encoding="utf-8")


@pytest.fixture
def story_project(tmp_path: Path) -> Path:
    p = tmp_path / "story"
    (p / ".sweetclaude" / "state").mkdir(parents=True)
    (p / "src").mkdir()
    (p / "tests").mkdir()
    _write_active(p, "IMPLEMENT", "implementing")
    (p / "src" / ".gitkeep").write_text("", encoding="utf-8")
    (p / "tests" / ".gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(p)], capture_output=True, timeout=30)
    _git(p, "add", "-A")
    _git(p, "commit", "-qm", "scaffold")
    _git(p, "checkout", "-q", "-b", "ISSUE-001/add-calc")
    return p


def _call(project: Path, command: str) -> subprocess.CompletedProcess:
    return run_hook(HOOK, project, payload("PreToolUse-Bash", project, command=command))


def _stage(project: Path, relative: str, content: str = "x = 1\n") -> None:
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(project, "add", "--", relative)


class TestDenyWithoutRed:
    def test_denies_commit_that_stages_source_with_no_red_commit(self, story_project: Path) -> None:
        _stage(story_project, "src/calc.py")
        result = _call(story_project, "git commit -m 'feat: GREEN - adder'")
        assert_denied(result)

    @pytest.mark.parametrize("command", [
        "git commit -m 'feat: GREEN - adder'",
        "git commit --amend --no-edit",
        "git commit -a -m 'feat: GREEN - adder'",
        "git -c user.email=t@example.invalid commit -m 'feat: GREEN - adder'",
        "git add src/calc.py && git commit -m 'feat: GREEN - adder'",
    ])
    def test_denies_each_commit_form(self, story_project: Path, command: str) -> None:
        _stage(story_project, "src/calc.py")
        result = _call(story_project, command)
        assert_denied(result)

    def test_denies_when_only_an_earlier_segment_stages_the_source(self, story_project: Path) -> None:
        result = _call(story_project, "git add src/calc.py && git commit -m 'feat: GREEN - adder'")
        assert_denied(result)

    def test_denies_dash_a_commit_of_a_modified_tracked_source(self, story_project: Path) -> None:
        _git(story_project, "rm", "-q", "src/.gitkeep")
        _git(story_project, "commit", "-qm", "drop keepers")
        _stage(story_project, "src/calc.py", "x = 1\n")
        _git(story_project, "commit", "-qm", "track source")
        (story_project / "src" / "calc.py").write_text("x = 2\n", encoding="utf-8")
        assert_denied(_call(story_project, "git commit -a -m 'feat: GREEN - adder'"))

    def test_deny_reason_names_the_remedy_and_the_source_file(self, story_project: Path) -> None:
        _stage(story_project, "src/calc.py")
        reason = deny_reason(_call(story_project, "git commit -m 'feat: GREEN - adder'"))
        assert "test: RED" in reason
        assert "src/calc.py" in reason

    def test_denies_on_a_lowercase_issue_prefixed_branch(self, tmp_path: Path) -> None:
        story_project = tmp_path / "lower"
        (story_project / ".sweetclaude" / "state").mkdir(parents=True)
        (story_project / "src").mkdir()
        _write_active(story_project, "IMPLEMENT", "implementing")
        (story_project / "src" / ".gitkeep").write_text("", encoding="utf-8")
        subprocess.run(["git", "init", "-q", "-b", "main", str(story_project)], capture_output=True, timeout=30)
        _git(story_project, "add", "-A")
        _git(story_project, "commit", "-qm", "scaffold")
        _git(story_project, "checkout", "-q", "-b", "issue-9/add-calc")
        _stage(story_project, "src/calc.py")
        assert_denied(_call(story_project, "git commit -m 'feat: GREEN - adder'"))

    def test_denies_on_a_controller_fallback_story_branch(self, tmp_path: Path) -> None:
        story_project = tmp_path / "fallback"
        (story_project / ".sweetclaude" / "state").mkdir(parents=True)
        (story_project / "src").mkdir()
        _write_active(story_project, "IMPLEMENT", "implementing")
        (story_project / "src" / ".gitkeep").write_text("", encoding="utf-8")
        subprocess.run(["git", "init", "-q", "-b", "main", str(story_project)], capture_output=True, timeout=30)
        _git(story_project, "add", "-A")
        _git(story_project, "commit", "-qm", "scaffold")
        _git(story_project, "checkout", "-q", "-b", "story/ISSUE-047")
        _stage(story_project, "src/calc.py")
        assert_denied(_call(story_project, "git commit -m 'feat: GREEN - adder'"))


class TestAllowControls:
    def test_allows_when_a_red_commit_exists_on_the_branch(self, story_project: Path) -> None:
        _stage(story_project, "tests/test_calc.py", "def test_add():\n    assert False\n")
        _git(story_project, "commit", "-qm", RED_MESSAGE)
        _stage(story_project, "src/calc.py")
        assert_allowed(_call(story_project, "git commit -m 'feat: GREEN - adder'"))

    def test_allows_when_the_cycle_has_returned_to_writing_tests(self, story_project: Path) -> None:
        _write_active(story_project, "IMPLEMENT", "writing_tests")
        _stage(story_project, "src/calc.py")
        assert_allowed(_call(story_project, "git commit -m 'feat: GREEN - adder'"))

    @pytest.mark.parametrize("command", [
        "git status",
        "git add src/calc.py",
        "git log --oneline",
        "git add src/calc.py && git status",
        'echo "git commit"',
        "git commit-tree abc",
    ])
    def test_allows_commands_that_are_not_a_commit(self, story_project: Path, command: str) -> None:
        assert_allowed(_call(story_project, command))

    def test_allows_commit_that_stages_only_test_files(self, story_project: Path) -> None:
        _stage(story_project, "tests/test_calc.py", "def test_add():\n    assert False\n")
        assert_allowed(_call(story_project, "git commit -m 'test: RED - ISSUE-001 failing tests'"))

    def test_allows_commit_with_only_doc_changes_staged(self, story_project: Path) -> None:
        _stage(story_project, "docs/notes.md")
        assert_allowed(_call(story_project, "git commit -m 'docs: notes'"))

    def test_allows_when_no_tdd_cycle_marker_exists_level_zero(self, story_project: Path) -> None:
        _write_active(story_project, "IMPLEMENT", None)
        _stage(story_project, "src/calc.py")
        assert_allowed(_call(story_project, "git commit -m 'feat: adder'"))

    def test_allows_when_phase_is_not_implement(self, story_project: Path) -> None:
        _write_active(story_project, "DESIGN", "implementing")
        _stage(story_project, "src/calc.py")
        assert_allowed(_call(story_project, "git commit -m 'feat: adder'"))

    def test_allows_when_the_branch_is_not_a_story_branch(self, story_project: Path) -> None:
        _git(story_project, "checkout", "-q", "main")
        _stage(story_project, "src/calc.py")
        assert_allowed(_call(story_project, "git commit -m 'feat: adder'"))

    def test_allows_outside_a_sweetclaude_project(self, tmp_path: Path) -> None:
        p = tmp_path / "plain"
        (p / "src").mkdir()
        (p / "src" / ".gitkeep").write_text("", encoding="utf-8")
        subprocess.run(["git", "init", "-q", "-b", "main", str(p)], capture_output=True, timeout=30)
        _git(p, "add", "-A")
        _git(p, "commit", "-qm", "scaffold")
        _git(p, "checkout", "-q", "-b", "ISSUE-001/add-calc")
        (p / "src" / "calc.py").write_text("x = 1\n", encoding="utf-8")
        _git(p, "add", "--", "src/calc.py")
        assert_allowed(_call(p, "git commit -m 'feat: adder'"))

    def test_allows_when_the_staged_target_cannot_be_resolved(self, story_project: Path) -> None:
        result = _call(story_project, "git add 'src/*.py' && git commit -m 'feat: adder'")
        assert_allowed(result)

    def test_allows_a_commit_with_nothing_staged(self, story_project: Path) -> None:
        assert_allowed(_call(story_project, "git commit --allow-empty -m 'chore: nothing'"))


@pytest.fixture
def hidden_yaml(tmp_path_factory):
    shadow = tmp_path_factory.mktemp("shadow")
    (shadow / "yaml.py").write_text("raise ImportError(\"No module named 'yaml'\")\n", encoding="utf-8")
    return {"PYTHONPATH": str(shadow)}


class TestFailClosedWithoutYaml:
    def test_denies_when_pyyaml_is_unavailable(self, story_project: Path, hidden_yaml) -> None:
        _stage(story_project, "src/calc.py")
        result = run_hook(HOOK, story_project, payload("PreToolUse-Bash", story_project,
                                                       command="git commit -m 'feat: adder'"),
                          env=hidden_yaml)
        assert_denied(result)

    def test_denial_names_the_missing_yaml_dependency(self, story_project: Path, hidden_yaml) -> None:
        _stage(story_project, "src/calc.py")
        result = run_hook(HOOK, story_project, payload("PreToolUse-Bash", story_project,
                                                       command="git commit -m 'feat: adder'"),
                          env=hidden_yaml)
        assert "yaml" in deny_reason(result).lower()


def registrations(event: str) -> list[tuple[str, str]]:
    config = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))
    found = []
    for entry in config.get("hooks", {}).get(event, []):
        for hook in entry.get("hooks", []):
            found.append((entry.get("matcher", ""), hook.get("command", "")))
    return found


class TestRegistration:
    def test_hooks_json_registers_the_gate_as_a_pretooluse_bash_hook(self) -> None:
        found = [matcher for matcher, command in registrations("PreToolUse")
                 if command.endswith(f"/hooks/{HOOK}")]
        assert found, f"hooks/hooks.json has no PreToolUse registration for hooks/{HOOK}"
        assert any(matcher == "Bash" for matcher in found), (
            f"the {HOOK} matchers do not cover Bash: {found}")

    def test_registered_command_resolves_to_an_existing_script(self) -> None:
        commands = [command for _, command in registrations("PreToolUse")
                    if command.endswith(f"/hooks/{HOOK}")]
        assert commands, f"hooks/hooks.json does not name hooks/{HOOK}"
        for command in commands:
            assert (REPO_ROOT / command.replace("${CLAUDE_PLUGIN_ROOT}/", "")).is_file()

    def test_manifest_declares_the_gate_with_event_matcher_and_command_path(self) -> None:
        entries = json.loads((HOOKS / "hooks-manifest.json").read_text(encoding="utf-8"))["hooks"]
        entry = next((e for e in entries if e.get("file") == HOOK), None)
        assert entry, f"hooks/hooks-manifest.json has no entry for {HOOK}"
        assert entry.get("event") == "PreToolUse"
        assert entry.get("matcher") == "Bash"
        assert entry.get("scope") == "plugin-native"
        assert entry.get("command_path") == "${CLAUDE_PLUGIN_ROOT}/hooks/" + HOOK

    def test_drives_a_commit_refusal_the_way_claude_code_runs_it(self, story_project: Path) -> None:
        _stage(story_project, "src/calc.py")
        result = subprocess.run(
            ["bash", str(HOOKS / HOOK)], cwd=str(story_project),
            env=hook_env(story_project),
            input=payload("PreToolUse-Bash", story_project, command="git commit -m 'feat: adder'"),
            capture_output=True, text=True, timeout=60)
        assert verdict(result) == "deny", f"verdict was {verdict(result)!r}: {result.stdout!r} {result.stderr!r}"


def test_gate_script_exists() -> None:
    assert (HOOKS / HOOK).is_file(), f"hooks/{HOOK} does not exist yet"