"""Behavior tests for the enforcement hooks (ISSUE-277).

coverage.py cannot measure bash, so the repo's coverage figure covers Python
only and says nothing about the hooks — which are the enforcement layer. They
gate tool calls, block writes, and stop sessions.

A hook is a function from input and project state to an allow-or-block
decision. That is what these assert. Line coverage would not have caught what
this file caught on its first run.

Twelve hooks had no test that executed them. These cover the ones whose
failure is silent: a guard that disables itself allows everything, and nothing
in the system notices.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
HOOKS = REPO_ROOT / "hooks"


def run_hook(name: str, project: Path, *, env: dict | None = None,
             stdin: str = "") -> subprocess.CompletedProcess:
    hook_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(project),
        "PROJECT_DIR": str(project),
    }
    hook_env.update(env or {})
    return subprocess.run(["bash", str(HOOKS / name)], cwd=str(project),
                          env=hook_env, input=stdin,
                          capture_output=True, text=True, timeout=60)


def decision(result: subprocess.CompletedProcess) -> bool | None:
    """True = allow, False = block, None = no JSON decision emitted."""
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return bool(json.loads(line).get("ok"))
            except json.JSONDecodeError:
                continue
    return None


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)],
                   capture_output=True, timeout=30)


@pytest.fixture
def v4_project(tmp_path: Path) -> Path:
    """A correctly configured v4 project: sweetclaude.yaml, no phase.yaml.

    phase.yaml is a mirror the story controllers write lazily; onboarding
    never creates it. That is the state most real projects are in.
    """
    p = tmp_path / "v4"
    state = p / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2,
        "project": {"name": "t", "version_stage": "GA", "mode": "kanban"},
        "framework": {"setup_complete": True},
        "work": {"active": {"id": "ISSUE-1", "phase": "IMPLEMENT"}},
    }), encoding="utf-8")
    _git_init(p)
    return p


@pytest.fixture
def v3_project(tmp_path: Path) -> Path:
    """A project that still carries phase.yaml."""
    p = tmp_path / "v3"
    state = p / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2, "framework": {"setup_complete": True}}), encoding="utf-8")
    (state / "phase.yaml").write_text(yaml.safe_dump({
        "schema_version": 2, "phase": "IMPLEMENT"}), encoding="utf-8")
    _git_init(p)
    return p


def _enable_guardian(project: Path) -> None:
    (project / ".sweetclaude" / "state" / "guardian-enabled").touch()


def _kanban_at_wip(project: Path, *, limit: int = 2, in_progress: int = 3) -> None:
    state = project / ".sweetclaude" / "state"
    (state / "effective-gates.yaml").write_text(
        yaml.safe_dump({"mode": "kanban", "wip_limit": limit}), encoding="utf-8")
    issues = project / ".sweetclaude" / "artifacts" / "issues"
    issues.mkdir(parents=True, exist_ok=True)
    for i in range(in_progress):
        (issues / f"ISSUE-{i}.yaml").write_text(
            yaml.safe_dump({"status": "in_progress"}), encoding="utf-8")


# --- wip-limit -----------------------------------------------------------

def test_wip_limit_blocks_when_the_limit_is_reached(v3_project: Path) -> None:
    _kanban_at_wip(v3_project)
    assert decision(run_hook("wip-limit.sh", v3_project)) is False


def test_wip_limit_allows_under_the_limit(v3_project: Path) -> None:
    _kanban_at_wip(v3_project, limit=5, in_progress=1)
    assert decision(run_hook("wip-limit.sh", v3_project)) is True


def test_wip_limit_block_message_names_the_reason(v3_project: Path) -> None:
    _kanban_at_wip(v3_project)
    out = run_hook("wip-limit.sh", v3_project).stdout
    assert "WIP limit reached" in out
    assert "3/2" in out, "the block must say how far over the limit the project is"


def test_wip_limit_allows_outside_kanban_mode(v3_project: Path) -> None:
    _kanban_at_wip(v3_project)
    (v3_project / ".sweetclaude" / "state" / "effective-gates.yaml").write_text(
        yaml.safe_dump({"mode": "flow", "wip_limit": 2}), encoding="utf-8")
    assert decision(run_hook("wip-limit.sh", v3_project)) is True


def test_wip_limit_allows_when_gates_are_not_compiled(v3_project: Path) -> None:
    _kanban_at_wip(v3_project)
    (v3_project / ".sweetclaude" / "state" / "effective-gates.yaml").unlink()
    assert decision(run_hook("wip-limit.sh", v3_project)) is True


def test_wip_limit_applies_on_a_v4_project(v4_project: Path) -> None:
    """ISSUE-281 regression.

    The hook used to read the active phase from phase.yaml and allow when that
    file was absent. Onboarding never creates phase.yaml, so the WIP limit did
    not apply on any correctly configured v4 project — choosing kanban is
    choosing the limit, and the limit was off. Phase now resolves from
    work.active.phase in sweetclaude.yaml.
    """
    _kanban_at_wip(v4_project)
    assert not (v4_project / ".sweetclaude" / "state" / "phase.yaml").exists()
    assert decision(run_hook("wip-limit.sh", v4_project)) is False


def test_wip_limit_still_reads_the_mirror_for_projects_mid_migration(
    tmp_path: Path
) -> None:
    """A project part-way through migration may have phase.yaml and no
    work.active yet. The fallback must keep working."""
    p = tmp_path / "mid"
    state = p / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text(
        yaml.safe_dump({"schema_version": 2, "framework": {"setup_complete": True}}),
        encoding="utf-8")
    (state / "phase.yaml").write_text(
        yaml.safe_dump({"schema_version": 2, "phase": "IMPLEMENT"}), encoding="utf-8")
    _git_init(p)
    _kanban_at_wip(p)

    assert decision(run_hook("wip-limit.sh", p)) is False


# --- phase-dwelling-guard ------------------------------------------------

ADVANCEMENT = ("The architecture document is complete.\n\n"
               "Ready to move on to the next phase?")


def _transcript(project: Path, text: str) -> Path:
    path = project / "transcript.jsonl"
    path.write_text(json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }) + "\n", encoding="utf-8")
    return path


def test_phase_dwelling_guard_allows_without_the_guardian(v3_project: Path) -> None:
    """It is guardian-only enforcement by design."""
    t = _transcript(v3_project, ADVANCEMENT)
    r = run_hook("phase-dwelling-guard.sh", v3_project,
                 env={"CLAUDE_TRANSCRIPT_PATH": str(t)})
    assert r.returncode == 0


def test_phase_dwelling_guard_allows_a_response_with_no_pushing(v3_project: Path) -> None:
    _enable_guardian(v3_project)
    t = _transcript(v3_project, "Here is the architecture document. "
                                "Push back if the boundaries are wrong.")
    r = run_hook("phase-dwelling-guard.sh", v3_project,
                 env={"CLAUDE_TRANSCRIPT_PATH": str(t)})
    assert r.returncode == 0


def test_phase_dwelling_guard_blocks_advancement_pushing(v3_project: Path) -> None:
    """The rule it exists to enforce: never ask the user to advance a phase."""
    _enable_guardian(v3_project)
    t = _transcript(v3_project, ADVANCEMENT)
    r = run_hook("phase-dwelling-guard.sh", v3_project,
                 env={"CLAUDE_TRANSCRIPT_PATH": str(t)})
    assert r.returncode != 0 or decision(r) is False, (
        "advancement-pushing language was not blocked")


def test_phase_dwelling_guard_allows_when_no_transcript_is_available(
    v3_project: Path
) -> None:
    _enable_guardian(v3_project)
    r = run_hook("phase-dwelling-guard.sh", v3_project)
    assert r.returncode == 0


def test_phase_dwelling_guard_runs_on_a_v4_project(v4_project: Path) -> None:
    """ISSUE-281 regression.

    The guard used to return before reading the transcript whenever phase.yaml
    was absent, so it never ran on a v4 project even with the Protocol Guardian
    explicitly enabled. A user who turned the guardian on got no enforcement
    and no indication it was inactive.
    """
    _enable_guardian(v4_project)
    t = _transcript(v4_project, ADVANCEMENT)
    r = run_hook("phase-dwelling-guard.sh", v4_project,
                 env={"CLAUDE_TRANSCRIPT_PATH": str(t)})
    assert r.returncode != 0 or decision(r) is False, (
        "guard did not act on advancement language on a v4 project")


def test_phase_dwelling_guard_still_allows_clean_responses_on_v4(
    v4_project: Path
) -> None:
    """Enabling the guard must not make it block everything."""
    _enable_guardian(v4_project)
    t = _transcript(v4_project, "Here is the document. Push back if it is wrong.")
    r = run_hook("phase-dwelling-guard.sh", v4_project,
                 env={"CLAUDE_TRANSCRIPT_PATH": str(t)})
    assert r.returncode == 0


# --- tdd-prewrite-guardian -----------------------------------------------

def _write_env(project: Path, file_path: str, tool: str = "Write") -> dict:
    return {"CLAUDE_FILE_PATH": str(project / file_path), "CLAUDE_TOOL_NAME": tool}


def test_tdd_prewrite_allows_without_the_guardian(v3_project: Path) -> None:
    r = run_hook("tdd-prewrite-guardian.sh", v3_project,
                 env=_write_env(v3_project, "src/thing.py"))
    assert decision(r) is True


def test_tdd_prewrite_ignores_tools_other_than_write_and_edit(v3_project: Path) -> None:
    _enable_guardian(v3_project)
    r = run_hook("tdd-prewrite-guardian.sh", v3_project,
                 env=_write_env(v3_project, "src/thing.py", tool="Read"))
    assert decision(r) is True


def test_tdd_prewrite_emits_a_decision_for_a_source_write(v3_project: Path) -> None:
    """Whatever it decides, a PreToolUse hook must emit a parseable decision —
    the caller blocks or allows on it."""
    _enable_guardian(v3_project)
    (v3_project / "src").mkdir(exist_ok=True)
    r = run_hook("tdd-prewrite-guardian.sh", v3_project,
                 env=_write_env(v3_project, "src/thing.py"))
    assert decision(r) is not None, f"no JSON decision emitted: {r.stdout!r}"


# --- contracts every hook must satisfy -----------------------------------

ALL_HOOKS = sorted(p.name for p in HOOKS.glob("*.sh"))


@pytest.mark.parametrize("name", ALL_HOOKS)
def test_every_hook_is_syntactically_valid(name: str) -> None:
    r = subprocess.run(["bash", "-n", str(HOOKS / name)],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("name", ALL_HOOKS)
def test_no_hook_crashes_outside_a_project(name: str, tmp_path: Path) -> None:
    """A hook runs on every matching tool call, including in directories that
    are not SweetClaude projects. Crashing there breaks unrelated work."""
    r = run_hook(name, tmp_path, env={"CLAUDE_TOOL_NAME": "Read",
                                      "CLAUDE_FILE_PATH": str(tmp_path / "x.txt")})
    assert r.returncode in (0, 1), (
        f"{name} exited {r.returncode} outside a project: {r.stderr[:200]}")
    assert "Traceback" not in r.stderr


@pytest.mark.parametrize("name", ALL_HOOKS)
def test_no_hook_emits_a_traceback_on_a_bare_project(name: str, tmp_path: Path) -> None:
    (tmp_path / ".sweetclaude" / "state").mkdir(parents=True)
    _git_init(tmp_path)
    r = run_hook(name, tmp_path, env={"CLAUDE_TOOL_NAME": "Read",
                                      "CLAUDE_FILE_PATH": str(tmp_path / "x.txt")})
    assert "Traceback" not in r.stderr, r.stderr[:300]


def test_every_hook_has_a_behavior_test_or_is_declared_untested() -> None:
    """A new hook must not land silently untested.

    The allowlist is the honest part: it names what is not covered rather than
    letting absence pass for coverage.
    """
    tests_text = "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in (REPO_ROOT / "tests").rglob("*")
        if p.is_file() and p.suffix in {".py", ".sh"})

    # Empty, and it stays empty (ISSUE-277). Every hook now has a test that
    # drives the script and asserts both directions of what it does — allow and
    # block for the gates, acts and stands down for the rest. A new hook landing
    # with no test fails here rather than being waved through by an entry
    # nobody revisits.
    UNTESTED: set[str] = set()
    missing = [h for h in ALL_HOOKS
               if h not in tests_text and h not in UNTESTED]
    assert not missing, f"hooks with no test and not declared untested: {missing}"

    stale = [h for h in UNTESTED if h not in ALL_HOOKS]
    assert not stale, f"UNTESTED names hooks that no longer exist: {stale}"
