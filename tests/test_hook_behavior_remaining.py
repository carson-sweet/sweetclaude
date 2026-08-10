"""Behavior tests for the last nine untested hooks (ISSUE-277).

PR #127 covered the hooks that make an allow/deny decision and left an explicit
allowlist of nine that did not. This file empties it.

Only two of the nine actually gate a tool call. The rest act on the filesystem
or emit context, and for those the meaningful pair is not allow/block but
**acts / correctly stands down** — because a hook that quietly does nothing is
indistinguishable from one that is broken, which is how three protections
stayed off for months before ISSUE-281.

So every hook here gets both directions asserted, whichever shape it takes.

Two findings came out of writing these:

  * `new-skill-lint.sh` grepped for `skills/*/skill.md` and every skill is
    `SKILL.md`, so it never fired. Retired under ISSUE-287; its intent now lives
    in tests/test_skill_contracts.py.
  * `state-regenerator.sh` still watches only `phase.yaml`, so canonical v4
    state changes regenerate nothing (ISSUE-281's remainder). Marked
    xfail(strict=True) against the behaviour it claims, so it turns green by
    itself when fixed rather than needing someone to remember this file.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
HOOKS = REPO_ROOT / "hooks"

sys.path.insert(0, str(Path(__file__).parent))
from test_hook_behavior import run_hook, _git_init  # noqa: E402

needs_jq = pytest.mark.skipif(shutil.which("jq") is None,
                              reason="hook shells out to jq")


def _configured(project: Path, **work) -> Path:
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2,
        "project": {"name": "t", "version_stage": "GA"},
        "framework": {"setup_complete": True},
        "work": {"active": work or {"id": "ISSUE-1", "phase": "IMPLEMENT"}},
    }), encoding="utf-8")
    _git_init(project)
    return project


# =========================================================================
# small-story-gate.sh — PreToolUse allow/deny
# =========================================================================

GATE = "small-story-gate.sh"


def _tool_call(tool: str = "Write", file_path: str = "/tmp/x.py") -> str:
    return json.dumps({"tool_name": tool, "tool_input": {"file_path": file_path}})


def _decision(result: subprocess.CompletedProcess) -> str | None:
    """The PreToolUse contract: deny is JSON on stdout, allow is silence."""
    out = result.stdout.strip()
    if not out:
        return None
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


def test_small_story_gate_allows_when_no_workflow_state_exists(tmp_path: Path) -> None:
    """The fast path. Most projects are never under small-story discipline and
    must not pay for it."""
    project = _configured(tmp_path / "p")

    r = run_hook(GATE, project, stdin=_tool_call())

    assert r.returncode == 0
    assert _decision(r) is None, r.stdout


def _active_workflow(project: Path, phase: str = "PLAN",
                     body: str | None = None) -> Path:
    workflows = project / ".sweetclaude" / "state" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    p = workflows / "ISSUE-1.yaml"
    p.write_text(body if body is not None else yaml.safe_dump({
        "workflow_id": "ISSUE-1", "state_owner": "small_story_controller",
        "requires_success_criteria_contract": True, "status": "active",
        "phase": phase}), encoding="utf-8")
    return p


def test_small_story_gate_denies_a_write_outside_the_permitted_phase(
    tmp_path: Path
) -> None:
    """The block half. Project files are writable only in IMPLEMENT."""
    project = _configured(tmp_path / "p")
    _active_workflow(project, phase="PLAN")

    r = run_hook(GATE, project, stdin=_tool_call(
        file_path=str(project / "src" / "main.py")),
        env={"CLAUDE_PROJECT_DIR": str(project)})

    assert r.returncode == 0
    assert _decision(r) == "deny", r.stdout


def test_small_story_gate_names_the_phase_when_it_denies(tmp_path: Path) -> None:
    """A deny with no reason is indistinguishable from a malfunction, and the
    phase is the one fact that tells the operator what to do next."""
    project = _configured(tmp_path / "p")
    _active_workflow(project, phase="PLAN")

    r = run_hook(GATE, project, stdin=_tool_call(
        file_path=str(project / "src" / "main.py")),
        env={"CLAUDE_PROJECT_DIR": str(project)})
    reason = json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"]

    assert "IMPLEMENT" in reason
    assert "PLAN" in reason


def test_small_story_gate_emits_the_shape_the_caller_parses(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    _active_workflow(project, phase="PLAN")

    payload = json.loads(run_hook(GATE, project, stdin=_tool_call(
        file_path=str(project / "src" / "main.py")),
        env={"CLAUDE_PROJECT_DIR": str(project)}).stdout)

    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert set(payload["hookSpecificOutput"]) == {
        "hookEventName", "permissionDecision", "permissionDecisionReason"}


def test_small_story_gate_denies_when_it_cannot_read_its_own_state(
    tmp_path: Path
) -> None:
    """Was xfail(strict) against ISSUE-288, now a live assertion.

    The hook's header promises `active workflow -> fail closed (deny) on any
    error`. A corrupt state file did not raise — the loader returns {} — so the
    workflow was not counted active and everything was allowed. Corrupting one
    file disabled the gate silently. See tests/test_story_gate_fail_closed.py
    for the full pair, including the large-story gate.
    """
    project = _configured(tmp_path / "p")
    _active_workflow(project, body="{ not: valid: yaml")

    r = run_hook(GATE, project, stdin=_tool_call(
        file_path=str(project / "src" / "main.py")),
        env={"CLAUDE_PROJECT_DIR": str(project)})

    assert _decision(r) == "deny", r.stdout


# =========================================================================
# migration-decision-reminder.sh — UserPromptSubmit, escalating to a block
# =========================================================================

REMINDER = "migration-decision-reminder.sh"


def _marker(project: Path, turn_count: int) -> Path:
    p = project / ".sweetclaude" / "state" / "pending-migration-decision.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump({
        "turn_count": turn_count,
        "snapshot": {"tarball_path": "/snap.tar", "git_tag": "pre-migrate"}}),
        encoding="utf-8")
    return p


def test_reminder_is_silent_with_no_pending_decision(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")

    payload = json.loads(run_hook(REMINDER, project).stdout)

    assert payload == {"ok": True}


def test_reminder_surfaces_a_pending_decision(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    _marker(project, 0)

    payload = json.loads(run_hook(REMINDER, project).stdout)

    assert "Pending migration decision" in payload["systemMessage"]
    assert payload.get("continue") is not False, "a reminder must not block"


def test_the_reminder_carries_the_snapshot_so_rollback_is_possible(
    tmp_path: Path
) -> None:
    """Telling someone to decide without telling them what they would roll back
    to is not an actionable prompt."""
    project = _configured(tmp_path / "p")
    _marker(project, 0)

    msg = json.loads(run_hook(REMINDER, project).stdout)["systemMessage"]

    assert "/snap.tar" in msg
    assert "pre-migrate" in msg


def test_the_turn_count_advances_so_the_deadline_is_real(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    marker = _marker(project, 3)

    run_hook(REMINDER, project)

    assert yaml.safe_load(marker.read_text())["turn_count"] == 4


def test_the_decision_is_forced_at_the_limit(tmp_path: Path) -> None:
    """The block half. Without it the reminder is advice nobody has to take."""
    project = _configured(tmp_path / "p")
    _marker(project, 9)

    payload = json.loads(run_hook(REMINDER, project).stdout)

    assert payload["continue"] is False
    assert "limit reached" in payload["systemMessage"]


def test_it_fails_open_on_an_unreadable_marker(tmp_path: Path) -> None:
    """A corrupt marker must not wedge every prompt in the session."""
    project = _configured(tmp_path / "p")
    p = project / ".sweetclaude" / "state" / "pending-migration-decision.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ not: valid: yaml", encoding="utf-8")

    payload = json.loads(run_hook(REMINDER, project).stdout)

    assert payload == {"ok": True}


# =========================================================================
# artifact-guardian.sh — warns, never blocks
# =========================================================================

GUARDIAN = "artifact-guardian.sh"


def _commit_call(command: str = "git commit -m x") -> str:
    return json.dumps({"command": command})


@needs_jq
def test_artifact_guardian_warns_when_committing_without_artifacts(
    tmp_path: Path
) -> None:
    project = _configured(tmp_path / "p", id="ISSUE-1", phase="DESIGN")
    (project / ".sweetclaude" / "state" / "guardian-enabled").touch()
    (project / ".sweetclaude" / "state" / "session-guardian.json").write_text(
        json.dumps({"artifacts_created": []}), encoding="utf-8")

    r = run_hook(GUARDIAN, project, stdin=_commit_call(),
                 env={"CLAUDE_TOOL_NAME": "Bash"})

    assert "[Protocol Guardian]" in r.stderr
    assert "DESIGN" in r.stderr, "the warning must name the phase it applies to"


@needs_jq
def test_artifact_guardian_says_so_when_it_cannot_verify(tmp_path: Path) -> None:
    """Distinct from the warning above: with no session record the hook does not
    know whether artifacts exist. Reporting that as 'no artifacts' would be a
    claim it cannot support."""
    project = _configured(tmp_path / "p", id="ISSUE-1", phase="DESIGN")
    (project / ".sweetclaude" / "state" / "guardian-enabled").touch()

    r = run_hook(GUARDIAN, project, stdin=_commit_call(),
                 env={"CLAUDE_TOOL_NAME": "Bash"})

    assert "Cannot verify" in r.stderr


@needs_jq
def test_artifact_guardian_is_quiet_when_the_artifacts_are_there(
    tmp_path: Path
) -> None:
    """The allow half. A guardian that warns even when satisfied is noise."""
    project = _configured(tmp_path / "p", id="ISSUE-1", phase="DESIGN")
    (project / ".sweetclaude" / "state" / "guardian-enabled").touch()
    (project / ".sweetclaude" / "state" / "session-guardian.json").write_text(
        json.dumps({"artifacts_created": ["docs/architecture.md"]}),
        encoding="utf-8")

    r = run_hook(GUARDIAN, project, stdin=_commit_call(),
                 env={"CLAUDE_TOOL_NAME": "Bash"})

    assert r.stderr.strip() == ""


@needs_jq
def test_artifact_guardian_never_blocks_the_commit(tmp_path: Path) -> None:
    """The whole point of this hook is that it is advisory. If it ever starts
    blocking, a warning becomes a work stoppage."""
    project = _configured(tmp_path / "p", id="ISSUE-1", phase="DESIGN")
    (project / ".sweetclaude" / "state" / "guardian-enabled").touch()

    r = run_hook(GUARDIAN, project, stdin=_commit_call(),
                 env={"CLAUDE_TOOL_NAME": "Bash"})

    assert r.returncode == 0
    assert r.stdout.strip() == "", "a warning hook must emit no decision"


@needs_jq
def test_artifact_guardian_is_silent_when_the_guardian_is_off(
    tmp_path: Path
) -> None:
    """Off must mean silent. Warning anyway would train people to ignore it."""
    project = _configured(tmp_path / "p", id="ISSUE-1", phase="DESIGN")

    r = run_hook(GUARDIAN, project, stdin=_commit_call(),
                 env={"CLAUDE_TOOL_NAME": "Bash"})

    assert r.stderr.strip() == ""


@needs_jq
def test_artifact_guardian_ignores_commands_that_are_not_commits(
    tmp_path: Path
) -> None:
    project = _configured(tmp_path / "p", id="ISSUE-1", phase="DESIGN")
    (project / ".sweetclaude" / "state" / "guardian-enabled").touch()

    r = run_hook(GUARDIAN, project, stdin=_commit_call("git status"),
                 env={"CLAUDE_TOOL_NAME": "Bash"})

    assert r.stderr.strip() == ""


@needs_jq
def test_artifact_guardian_ignores_tools_that_are_not_bash(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p", id="ISSUE-1", phase="DESIGN")
    (project / ".sweetclaude" / "state" / "guardian-enabled").touch()

    r = run_hook(GUARDIAN, project, stdin=_commit_call(),
                 env={"CLAUDE_TOOL_NAME": "Write"})

    assert r.stderr.strip() == ""


# =========================================================================
# git-checkpoint.sh — commits state, or refuses with a reason
# =========================================================================

CHECKPOINT = "git-checkpoint.sh"


def _run_checkpoint(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(HOOKS / CHECKPOINT), *args],
                          cwd=str(project), capture_output=True, text=True,
                          timeout=60,
                          env={**os.environ, "HOME": str(project)})


def _git_identity(project: Path) -> None:
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(project), "config", k, v],
                       capture_output=True, timeout=30)


def test_checkpoint_commits_state_changes(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    _git_identity(project)

    r = _run_checkpoint(project, "checkpoint: phase gate")

    assert r.returncode == 0
    log = subprocess.run(["git", "-C", str(project), "log", "--oneline"],
                         capture_output=True, text=True, timeout=30).stdout
    assert "checkpoint: phase gate" in log


def test_checkpoint_commits_only_sweetclaude_state(tmp_path: Path) -> None:
    """Checkpoints run mid-work. Sweeping up the user's in-progress source
    would commit half-written code under a state-management message."""
    project = _configured(tmp_path / "p")
    _git_identity(project)
    (project / "app.py").write_text("half written\n", encoding="utf-8")

    _run_checkpoint(project, "checkpoint")

    committed = subprocess.run(
        ["git", "-C", str(project), "show", "--name-only", "--format=", "HEAD"],
        capture_output=True, text=True, timeout=30).stdout
    assert ".sweetclaude" in committed
    assert "app.py" not in committed


def test_checkpoint_refuses_without_a_message(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")

    r = _run_checkpoint(project)

    assert r.returncode == 1
    assert "Usage" in r.stderr


def test_checkpoint_refuses_outside_a_repository(tmp_path: Path) -> None:
    bare = tmp_path / "bare"
    (bare / ".sweetclaude" / "state").mkdir(parents=True)

    r = _run_checkpoint(bare, "checkpoint")

    assert r.returncode == 1
    assert "Not in a git repo" in r.stderr


def test_checkpoint_is_a_no_op_when_nothing_changed(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    _git_identity(project)
    _run_checkpoint(project, "first")
    before = subprocess.run(["git", "-C", str(project), "rev-parse", "HEAD"],
                            capture_output=True, text=True, timeout=30).stdout

    r = _run_checkpoint(project, "second")

    after = subprocess.run(["git", "-C", str(project), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30).stdout
    assert r.returncode == 0
    assert before == after, "an empty checkpoint must not create a commit"


# =========================================================================
# plan-tracker.sh — records which plan is active
# =========================================================================

TRACKER = "plan-tracker.sh"


def test_plan_tracker_records_the_newest_plan(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    plans = project / ".sweetclaude" / "plans"
    plans.mkdir(parents=True)
    (plans / "old.md").write_text("old\n", encoding="utf-8")
    time.sleep(0.05)
    (plans / "new.md").write_text("new\n", encoding="utf-8")

    run_hook(TRACKER, project)

    pointer = (project / ".sweetclaude" / "state" / "active-plan.txt").read_text()
    assert "new.md" in pointer
    assert "old.md" not in pointer


def test_plan_tracker_records_when_it_ran(tmp_path: Path) -> None:
    """A pointer with no timestamp cannot be told from a stale one."""
    project = _configured(tmp_path / "p")
    plans = project / ".sweetclaude" / "plans"
    plans.mkdir(parents=True)
    (plans / "a.md").write_text("a\n", encoding="utf-8")

    run_hook(TRACKER, project)

    assert "recorded_at:" in (
        project / ".sweetclaude" / "state" / "active-plan.txt").read_text()


def test_plan_tracker_writes_nothing_without_a_plan(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    (project / ".sweetclaude" / "plans").mkdir(parents=True)

    run_hook(TRACKER, project)

    assert not (project / ".sweetclaude" / "state" / "active-plan.txt").exists()


def test_plan_tracker_stands_down_on_an_unconfigured_project(
    tmp_path: Path
) -> None:
    project = tmp_path / "bare"
    (project / ".sweetclaude" / "plans").mkdir(parents=True)
    (project / ".sweetclaude" / "plans" / "a.md").write_text("a\n", encoding="utf-8")
    _git_init(project)

    r = run_hook(TRACKER, project)

    assert r.returncode == 0
    assert not (project / ".sweetclaude" / "state" / "active-plan.txt").exists()


# =========================================================================
# state-regenerator.sh — dispatches the session-state rebuild
# =========================================================================

REGEN = "state-regenerator.sh"


def _regenerated(project: Path, file_path: Path, tool: str = "Write",
                 timeout: float = 20.0) -> bool:
    """The hook backgrounds the generator, so the effect is polled for."""
    out = project / ".sweetclaude" / "state" / "session-state.yaml"
    if out.exists():
        out.unlink()
    run_hook(REGEN, project, env={"CLAUDE_TOOL_NAME": tool,
                                  "CLAUDE_FILE_PATH": str(file_path)})
    deadline = time.time() + timeout
    while time.time() < deadline:
        if out.exists():
            return True
        time.sleep(0.1)
    return False


def test_regenerator_rebuilds_when_a_watched_file_changes(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    watched = project / ".sweetclaude" / "state" / "phase.yaml"
    watched.write_text(yaml.safe_dump({"schema_version": 2, "phase": "IMPLEMENT"}),
                       encoding="utf-8")

    assert _regenerated(project, watched)


def test_regenerator_stands_down_for_an_unwatched_file(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")

    assert not _regenerated(project, project / "src" / "main.py", timeout=2.0)


def test_regenerator_stands_down_for_a_read(tmp_path: Path) -> None:
    """Only writes change state. Rebuilding on every Read would fire constantly."""
    project = _configured(tmp_path / "p")
    watched = project / ".sweetclaude" / "state" / "phase.yaml"
    watched.write_text(yaml.safe_dump({"schema_version": 2}), encoding="utf-8")

    assert not _regenerated(project, watched, tool="Read", timeout=2.0)


@pytest.mark.xfail(strict=True, reason="ISSUE-281 remainder: the watch list "
                                       "still names only phase.yaml")
def test_regenerator_rebuilds_when_canonical_state_changes(tmp_path: Path) -> None:
    """sweetclaude.yaml is the canonical file; phase.yaml is a lazily-written
    mirror most projects never have. Watching only the mirror means a v4
    project's session state goes stale after every real state change, silently.
    """
    project = _configured(tmp_path / "p")
    canonical = project / ".sweetclaude" / "state" / "sweetclaude.yaml"

    assert _regenerated(project, canonical, timeout=5.0)


# =========================================================================
# auto-reindex.sh — triggers RAG ingest for indexed files only
# =========================================================================

REINDEX = "auto-reindex.sh"


def _rag_config(project: Path, *dirs: str) -> None:
    p = project / ".sweetclaude" / "state" / "rag-config.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("indexed_paths:\n" + "".join(f"  - {d}\n" for d in dirs),
                 encoding="utf-8")


def test_reindex_fires_for_an_indexed_file(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    docs = project / "docs"
    docs.mkdir()
    _rag_config(project, str(docs))
    target = docs / "note.md"
    target.write_text("x\n", encoding="utf-8")

    r = run_hook(REINDEX, project, env={"CLAUDE_FILE_PATH": str(target)})

    assert "RAG: Reindexing" in r.stderr


def test_reindex_stands_down_without_a_rag_config(tmp_path: Path) -> None:
    """Most projects have no RAG. Silence here is correct, and it is the
    common case, so it has to be asserted rather than assumed."""
    project = _configured(tmp_path / "p")
    target = project / "docs" / "note.md"
    target.parent.mkdir()
    target.write_text("x\n", encoding="utf-8")

    r = run_hook(REINDEX, project, env={"CLAUDE_FILE_PATH": str(target)})

    assert r.returncode == 0
    assert "RAG" not in r.stderr


def test_reindex_stands_down_for_an_unindexable_type(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    src = project / "src"
    src.mkdir()
    _rag_config(project, str(src))
    target = src / "main.py"
    target.write_text("x\n", encoding="utf-8")

    r = run_hook(REINDEX, project, env={"CLAUDE_FILE_PATH": str(target)})

    assert "RAG" not in r.stderr


def test_reindex_stands_down_outside_the_indexed_paths(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    (project / "docs").mkdir()
    _rag_config(project, str(project / "docs"))
    target = project / "elsewhere" / "note.md"
    target.parent.mkdir()
    target.write_text("x\n", encoding="utf-8")

    r = run_hook(REINDEX, project, env={"CLAUDE_FILE_PATH": str(target)})

    assert "RAG" not in r.stderr


# =========================================================================
# new-skill-lint.sh — retired (ISSUE-287)
# =========================================================================
#
# It grepped `skills/*/skill.md`; every skill is `SKILL.md`, so it never matched
# and never ran once in its life. It also required `disable-model-invocation`,
# a key no skill in the corpus sets. Both halves were dead.
#
# Its intent — a skill must not advertise that it invokes itself — is asserted
# in tests/test_skill_contracts.py, where it runs in CI for everyone instead of
# per-clone, and where `--no-verify` cannot skip it. That check found a live
# violation on its first run (`big-picture` advertised trigger phrases), which
# the hook could never have caught.


def test_the_retired_lint_is_not_still_registered() -> None:
    """A dead gate left in place reads as a control. Nothing should invoke it."""
    referenced = [
        p for p in (REPO_ROOT / "hooks").glob("*")
        if p.is_file() and "new-skill-lint" in p.read_text(
            encoding="utf-8", errors="ignore")
    ]

    assert not (HOOKS / "new-skill-lint.sh").exists()
    assert referenced == [], referenced


# =========================================================================
# sc-artifact.sh — a sourced function library, not a decision hook
# =========================================================================

SC_ARTIFACT = "sc-artifact.sh"


def _source_and_run(project: Path, snippet: str) -> subprocess.CompletedProcess:
    script = f'source "{HOOKS / SC_ARTIFACT}"\n{snippet}\n'
    return subprocess.run(["bash", "-c", script], cwd=str(project),
                          capture_output=True, text=True, timeout=60,
                          env={**os.environ, "HOME": str(project),
                               "SWEETCLAUDE_PROJECT_ROOT": str(project),
                               "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)})


def test_sourcing_the_adapter_defines_its_functions(tmp_path: Path) -> None:
    """Unlike the others this makes no decision — it is a library skills source.
    Its failure mode is a skill calling a function that does not exist."""
    project = _configured(tmp_path / "p")

    r = _source_and_run(project, "declare -F | awk '{print $3}' | grep '^sc_artifact_'")

    defined = set(r.stdout.split())
    assert defined >= {"sc_artifact_read", "sc_artifact_write",
                       "sc_artifact_create", "sc_artifact_query",
                       "sc_artifact_delete", "sc_artifact_list"}


def test_the_adapter_reports_a_missing_implementation(tmp_path: Path) -> None:
    """Sourced libraries fail quietly. If the python side goes missing, the
    caller must be told rather than getting an empty result.

    The adapter is copied somewhere without its impl beside it — resolution
    prefers BASH_SOURCE's own directory, so sourcing the real file always finds
    the real impl no matter what CLAUDE_PLUGIN_ROOT says.
    """
    project = _configured(tmp_path / "p")
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    shutil.copy(HOOKS / SC_ARTIFACT, lonely / SC_ARTIFACT)

    r = subprocess.run(
        ["bash", "-c", f'source "{lonely / SC_ARTIFACT}"\nsc_artifact_read EP-1\n'],
        cwd=str(project), capture_output=True, text=True, timeout=60,
        env={**os.environ, "HOME": str(project),
             "SWEETCLAUDE_PROJECT_ROOT": str(project),
             "CLAUDE_PLUGIN_ROOT": str(tmp_path / "nowhere")})

    assert r.returncode != 0
    assert "sc-artifact" in r.stderr


def _write_artifact(project: Path, rel: str, entity_id: str) -> None:
    d = project / ".sweetclaude" / "product" / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{entity_id}-thing.md").write_text(
        f"---\nid: {entity_id}\ntitle: thing\nstatus: new\n---\n\nbody\n",
        encoding="utf-8")


def test_the_adapter_reads_an_artifact_back(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    _write_artifact(project, "roadmap/epics", "EP-1")

    r = _source_and_run(project, "sc_artifact_read EP-1")

    assert r.returncode == 0, r.stderr
    assert "EP-1" in r.stdout


def test_a_genuinely_absent_id_reads_as_empty(tmp_path: Path) -> None:
    project = _configured(tmp_path / "p")
    _write_artifact(project, "roadmap/epics", "EP-1")

    r = _source_and_run(project, "sc_artifact_read EP-99")

    assert r.stdout.strip() == "{}"


def test_the_adapter_reads_an_issue(tmp_path: Path) -> None:
    """Was xfail(strict) against ISSUE-289 and is now a live assertion.

    The adapter read every issue as empty, which is the same answer as "no such
    issue", so 14 skills sourcing it could not tell a missing issue from a
    broken lookup.
    """
    project = _configured(tmp_path / "p")
    _write_artifact(project, "roadmap/issues", "ISSUE-1")

    r = _source_and_run(project, "sc_artifact_read ISSUE-1")

    assert "ISSUE-1" in r.stdout, r.stdout
