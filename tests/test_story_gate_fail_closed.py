"""A story gate that cannot read its own state denies (ISSUE-288).

Both gates state the contract in their own headers:

    Fail-safe: no active workflow -> allow on any error.
                  active workflow -> fail closed (deny) on any error.

The fail-closed branch only fired when the controller import or call raised. A
workflow file that existed but did not parse never raised: `_load_yaml_dict`
catches `yaml.YAMLError` and returns `{}`, `_is_active_workflow_state({})` is
False, the workflow is not counted active, and everything is allowed.

So corrupting one state file switched the whole discipline off, silently, on
both gates. The hook's fast path globs for `*.yaml` and proves a workflow
exists; the parse decides whether it is active. Nothing owned the gap between
them.

The fix lives in the controllers rather than the hook scripts — the hooks are
protocol adapters and say so, and putting policy in bash would have needed
writing it twice.
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
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import large_story_controller as large  # noqa: E402
import small_story_controller as small  # noqa: E402

GATES = [
    pytest.param("small", small, "small-story-gate.sh", id="small"),
    pytest.param("large", large, "large-story-gate.sh", id="large"),
]


def _project(tmp_path: Path) -> Path:
    p = tmp_path / "proj"
    (p / ".sweetclaude" / "state" / "workflows").mkdir(parents=True)
    (p / ".sweetclaude" / "state" / "sweetclaude.yaml").write_text(
        yaml.safe_dump({"schema_version": 2}), encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(p)],
                   capture_output=True, timeout=30)
    return p


def _workflow(project: Path, kind: str, *, body: str | None = None,
              phase: str = "PLAN") -> Path:
    f = project / ".sweetclaude" / "state" / "workflows" / "ISSUE-1.yaml"
    f.write_text(body if body is not None else yaml.safe_dump({
        "workflow_id": "ISSUE-1", "state_owner": f"{kind}_story_controller",
        "requires_success_criteria_contract": True, "status": "active",
        "phase": phase}), encoding="utf-8")
    return f


def _gate(mod, project: Path) -> dict:
    return mod.gate_tool_use(project_dir=str(project), tool="Write",
                             file_path=str(project / "src" / "main.py"))


# --- the defect ------------------------------------------------------------

@pytest.mark.parametrize("kind,mod,hook", GATES)
def test_unparseable_state_denies(kind, mod, hook, tmp_path: Path) -> None:
    """One corrupt file used to disable the gate entirely."""
    project = _project(tmp_path)
    _workflow(project, kind, body="{ not: valid: yaml")

    assert _gate(mod, project)["allow"] is False


@pytest.mark.parametrize("kind,mod,hook", GATES)
def test_a_file_that_is_not_a_mapping_denies(kind, mod, hook,
                                             tmp_path: Path) -> None:
    """Valid YAML, wrong shape. Parses without error and answers no questions,
    which is the same position as a parse failure."""
    project = _project(tmp_path)
    _workflow(project, kind, body="- just\n- a list\n")

    assert _gate(mod, project)["allow"] is False


@pytest.mark.parametrize("kind,mod,hook", GATES)
def test_the_reason_says_the_state_is_damaged(kind, mod, hook,
                                              tmp_path: Path) -> None:
    """A deny reading like a phase violation sends someone to change phase when
    the actual repair is to a file."""
    project = _project(tmp_path)
    _workflow(project, kind, body="{ bad")

    reason = _gate(mod, project)["reason"]

    assert "unreadable" in reason
    assert "ISSUE-1.yaml" in reason, "the reason must name the file to repair"
    assert "not a phase violation" in reason


@pytest.mark.parametrize("kind,mod,hook", GATES)
def test_the_two_denials_are_distinguishable(kind, mod, hook,
                                             tmp_path: Path) -> None:
    """Both deny, so only the reason separates 'repair a file' from 'you are in
    the wrong phase'."""
    damaged = _project(tmp_path / "a")
    _workflow(damaged, kind, body="{ bad")
    healthy = _project(tmp_path / "b")
    _workflow(healthy, kind, phase="PLAN")

    damaged_reason = _gate(mod, damaged)["reason"]
    healthy_reason = _gate(mod, healthy)["reason"]

    assert _gate(mod, healthy)["allow"] is False, "fixture must also deny"
    assert damaged_reason != healthy_reason
    assert "unreadable" not in healthy_reason


# --- what must keep working ------------------------------------------------

@pytest.mark.parametrize("kind,mod,hook", GATES)
def test_no_workflow_state_still_allows(kind, mod, hook, tmp_path: Path) -> None:
    """Most projects are never under story discipline. Failing closed for them
    would stop all work everywhere."""
    project = _project(tmp_path)

    assert _gate(mod, project)["allow"] is True


@pytest.mark.parametrize("kind,mod,hook", GATES)
def test_an_empty_workflow_file_is_not_treated_as_damaged(kind, mod, hook,
                                                          tmp_path: Path) -> None:
    """An empty file parses to None. That is absence, not corruption, and
    denying on it would fail closed on a condition that is not an error."""
    project = _project(tmp_path)
    _workflow(project, kind, body="")

    assert _gate(mod, project)["allow"] is True


@pytest.mark.parametrize("kind,mod,hook", GATES)
def test_a_valid_workflow_still_denies_on_phase(kind, mod, hook,
                                                tmp_path: Path) -> None:
    project = _project(tmp_path)
    _workflow(project, kind, phase="PLAN")

    result = _gate(mod, project)

    assert result["allow"] is False
    assert "unreadable" not in result["reason"]


@pytest.mark.parametrize("kind,mod,hook", GATES)
def test_the_detector_ignores_directories_it_does_not_own(kind, mod, hook,
                                                          tmp_path: Path) -> None:
    """Archived workflows are history. A damaged one is not a reason to stop
    current work."""
    project = _project(tmp_path)
    archived = project / ".sweetclaude" / "state" / "workflows" / "archived"
    archived.mkdir()
    (archived / "OLD.yaml").write_text("{ bad", encoding="utf-8")

    assert _gate(mod, project)["allow"] is True


# --- through the hook, as Claude Code invokes it ---------------------------

def _run_hook(hook: str, project: Path) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": "Write",
                          "tool_input": {"file_path": str(project / "src" / "m.py")}})
    # Inherit the environment. A hand-built PATH loses the interpreter that has
    # pyyaml, and the controller exits on the missing import — which the hook
    # correctly renders as a deny, so the test passes for the wrong reason and
    # proves nothing about damaged state.
    return subprocess.run(["bash", str(HOOKS / hook)], cwd=str(project),
                          env={**os.environ, "HOME": str(project),
                               "CLAUDE_PROJECT_DIR": str(project)},
                          input=payload, capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("kind,mod,hook", GATES)
def test_the_hook_emits_a_deny_for_damaged_state(kind, mod, hook,
                                                 tmp_path: Path) -> None:
    """The controller returning deny is not enough — the adapter has to render
    it as the deny shape Claude Code acts on."""
    project = _project(tmp_path)
    _workflow(project, kind, body="{ bad")

    r = _run_hook(hook, project)

    assert r.returncode == 0
    payload = json.loads(r.stdout)["hookSpecificOutput"]
    assert payload["permissionDecision"] == "deny"
    assert "unreadable" in payload["permissionDecisionReason"]


@pytest.mark.parametrize("kind,mod,hook", GATES)
def test_the_hook_stays_silent_when_there_is_nothing_to_gate(kind, mod, hook,
                                                             tmp_path: Path) -> None:
    project = _project(tmp_path)

    r = _run_hook(hook, project)

    assert r.returncode == 0
    assert r.stdout.strip() == "", r.stdout
