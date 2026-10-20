#!/usr/bin/env python3
"""ISSUE-222 + ISSUE-223: story-workflow init must create a dedicated branch
every time, and must route-and-resume story creation when no story exists
(never dead-end, never auto-guess).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from small_story_controller import init_workflow as small_init
from large_story_controller import init_workflow as large_init
from success_criteria_contracts import compute_success_criteria_contract_hash


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(path),
                          capture_output=True, text=True, timeout=10)


def _init_git_repo(path: Path, branch: str = "main") -> None:
    _git(path, "init", "-b", branch)
    _git(path, "config", "user.email", "t@t.com")
    _git(path, "config", "user.name", "T")
    (path / "README.md").write_text("init\n")
    _git(path, "add", "-A")
    _git(path, "commit", "-m", "initial")


def _current_branch(path: Path) -> str:
    return _git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def _contract(story_id: str) -> dict:
    criterion = {
        "id": "SC-001", "outcome_id": "OUTCOME-001",
        "statement": "The completion validator returns status success.",
        "binary_predicate": "completion validator returns status success",
        "measurement_type": "schema_check",
        "measurement_procedure": "Run completion validator.",
        "evidence_artifact": f".sweetclaude/reports/{story_id}/SC-001.json",
        "evidence_owner": "controller",
        "pass_condition": "validator status equals success",
        "fail_condition": "validator status does not equal success",
        "allowed_phase_to_measure": "implementation",
        "amendment_policy": "human_approved_only",
        "backlog_routing": "Backlog any new concern.",
    }
    c = {
        "story_id": story_id, "story_title": "Init branch test",
        "story_objective": "Prove init creates a branch.",
        "expected_outcomes": [{"id": "OUTCOME-001", "statement": "x"}],
        "non_goals": [{"id": "NONGOAL-001", "statement": "y"}],
        "success_criteria": [criterion],
        "contract_freeze": {"frozen_at": "2026-07-14T00:00:00Z",
                            "frozen_by": "test", "contract_hash": ""},
    }
    c["contract_freeze"]["contract_hash"] = compute_success_criteria_contract_hash(c)
    return c


def _write_contract(project: Path, contract: dict) -> None:
    p = project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")


def _write_backlog(project: Path, story_id: str) -> None:
    d = project / "docs" / "product" / "backlog"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{story_id}-test.md").write_text(
        f"---\nid: {story_id}\nstatus: new\n---\nTest.\n", encoding="utf-8")


# --- ISSUE-222: init creates and switches to a dedicated story branch -------

def test_small_init_creates_dedicated_branch_in_git_repo(tmp_path):
    _init_git_repo(tmp_path)
    _write_backlog(tmp_path, "STORY-001")
    _write_contract(tmp_path, _contract("STORY-001"))
    result = small_init(project_dir=tmp_path, workflow_id="STORY-001")
    assert result["ok"], result
    branch = _current_branch(tmp_path)
    assert branch != "main", "init must not leave the workflow on main"
    assert "story-001" in branch.lower() or "STORY-001" in branch
    assert result.get("branch") == branch


def test_large_init_creates_dedicated_branch_in_git_repo(tmp_path):
    _init_git_repo(tmp_path)
    _write_backlog(tmp_path, "STORY-002")
    _write_contract(tmp_path, _contract("STORY-002"))
    result = large_init(project_dir=tmp_path, workflow_id="STORY-002")
    assert result["ok"], result
    assert _current_branch(tmp_path) != "main"
    assert "story-002" in _current_branch(tmp_path).lower()


def test_init_branch_creation_noops_outside_git_repo(tmp_path):
    # Existing gate tests init in a non-git tmpdir and expect ok — branch
    # creation must not break that path.
    _write_backlog(tmp_path, "STORY-003")
    _write_contract(tmp_path, _contract("STORY-003"))
    result = small_init(project_dir=tmp_path, workflow_id="STORY-003")
    assert result["ok"], result


# --- ISSUE-223: no story -> resumable creation signal, not a dead-end -------

def test_small_init_no_story_returns_resumable_creation_signal(tmp_path):
    _init_git_repo(tmp_path)
    _write_contract(tmp_path, _contract("STORY-404"))
    # deliberately no backlog file
    result = small_init(project_dir=tmp_path, workflow_id="STORY-404")
    assert result["ok"] is False
    assert result["code"] == "needs_story_creation", result
    # route-and-resume: the signal must tell the caller how to resume, and must
    # NOT be the old terminal dead-end code
    assert result["code"] != "blocked_init_no_story"
    assert result.get("resume_after_story_creation") is True


def test_large_init_no_story_returns_resumable_creation_signal(tmp_path):
    _init_git_repo(tmp_path)
    _write_contract(tmp_path, _contract("STORY-405"))
    result = large_init(project_dir=tmp_path, workflow_id="STORY-405")
    assert result["ok"] is False
    assert result["code"] == "needs_story_creation", result
    assert result.get("resume_after_story_creation") is True


def test_story_skills_document_route_and_resume(tmp_path):
    root = Path(__file__).resolve().parents[1]
    for rel in ("skill-library/build/small-story/SKILL.md", "skill-library/build/large-story/SKILL.md"):
        text = (root / rel).read_text(encoding="utf-8")
        assert "needs_story_creation" in text, (
            f"{rel} must handle the resumable no-story signal"
        )
        assert "resume" in text.lower()
