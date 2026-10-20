"""
Tests for ISSUE-224: controllers must own the full deterministic close-out
state write set.

Fixture approach: Direct file construction rather than calling init_workflow /
enter_verify_phase in sequence. Rationale:
  - init_workflow has git precondition checks (must be on main, clean tree)
    that block in a tmp dir that is not a git repo.
  - enter_verify_phase requires enforcement_verified=True in workflow state,
    which requires running the enforcement probe — not realistic in a unit
    fixture.
  - The focus of ISSUE-224 is enter_ship_phase's post-conditions, not the
    preceding phase transitions. We verify the correct preconditions exist
    (frozen contract, satisfied ledger, evidence files, workflow state) then
    call enter_ship_phase directly to observe the outputs.

All tests are expected to FAIL against the current implementation. They will
go GREEN once the fix described in ISSUE-224 is applied.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

# ---------------------------------------------------------------------------
# sys.path setup
#
# The controllers (small_story_controller, large_story_controller) live in
# the main repo's scripts/ directory. When this test runs from a git worktree
# that does not contain those files, we fall back to the main repo by
# resolving it from the worktree's .git pointer file.
# In normal (non-worktree) checkouts, .git is a directory, not a file, so
# the fallback is skipped and ../scripts resolves to the correct local path.
# ---------------------------------------------------------------------------

def _resolve_scripts_dir() -> Path:
    here = Path(__file__).resolve().parent
    local = (here / ".." / "scripts").resolve()
    if (local / "small_story_controller.py").exists():
        return local
    # Worktree fallback: .git is a file with "gitdir: <path>" pointing to
    # the main repo's .git/worktrees/<name>. Navigate up to find main scripts.
    git_pointer = (here / ".." / ".git").resolve()
    if git_pointer.is_file():
        content = git_pointer.read_text(encoding="utf-8").strip()
        if content.startswith("gitdir: "):
            gitdir = Path(content[len("gitdir: "):])
            if not gitdir.is_absolute():
                gitdir = (git_pointer.parent / gitdir).resolve()
            # gitdir = .git/worktrees/<name>  =>  main .git = parent.parent
            main_git = gitdir.parent.parent
            main_scripts = main_git.parent / "scripts"
            if (main_scripts / "small_story_controller.py").exists():
                return main_scripts
    return local


_SCRIPTS_DIR = str(_resolve_scripts_dir())
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import small_story_controller
import large_story_controller
import orchestrator_loop
from success_criteria_contracts import record_workflow_closeout


# ---------------------------------------------------------------------------
# Canonical "done" status — read directly from schema instead of hard-coding
# ---------------------------------------------------------------------------

from status import CANONICAL_STATUSES, TERMINAL_STATUSES

DONE_STATUS = "done"
assert DONE_STATUS in CANONICAL_STATUSES and DONE_STATUS in TERMINAL_STATUSES


# ---------------------------------------------------------------------------
# Contract builder helpers
# ---------------------------------------------------------------------------

def _compute_contract_hash(contract: dict[str, Any]) -> str:
    """Replicate compute_success_criteria_contract_hash from success_criteria_contracts."""
    canonical = copy.deepcopy(contract)
    freeze = canonical.get("contract_freeze")
    if isinstance(freeze, dict):
        freeze.pop("contract_hash", None)
    encoded = yaml.safe_dump(canonical, sort_keys=True, allow_unicode=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _minimal_contract(
    story_id: str,
    criterion_ids: list[str],
    evidence_artifact_prefix: str,
) -> dict[str, Any]:
    """Build a minimal valid frozen success-criteria contract for a given story."""
    criteria = []
    for cid in criterion_ids:
        criteria.append({
            "id": cid,
            "outcome_id": "OUTCOME-001",
            "statement": f"The system exits 0 when {cid} is measured.",
            "binary_predicate": f"python3 -m pytest -k {cid} exits 0",
            "measurement_type": "command",
            "measurement_procedure": f"Run: python3 -m pytest -k {cid}",
            "evidence_artifact": f"{evidence_artifact_prefix}/{cid}.json",
            "evidence_owner": "controller",
            "pass_condition": "Exit code equals 0",
            "fail_condition": "Exit code is non-zero",
            "allowed_phase_to_measure": "implementation",
            "amendment_policy": "human_approved_only",
            "backlog_routing": story_id,
        })
    contract = {
        "story_id": story_id,
        "story_title": f"Test story {story_id}",
        "story_objective": f"Objective for {story_id}",
        "authored_by": "test-fixture",
        "expected_outcomes": [
            {"id": "OUTCOME-001", "statement": "The story completes successfully."}
        ],
        "non_goals": [
            {"id": "NONGOAL-001", "statement": "Out of scope."}
        ],
        "success_criteria": criteria,
        "contract_freeze": {
            "frozen_at": "2026-06-26T00:00:00+00:00",
            "frozen_by": "test-fixture",
            "contract_hash": None,
        },
    }
    contract["contract_freeze"]["contract_hash"] = _compute_contract_hash(contract)
    return contract


# ---------------------------------------------------------------------------
# Ship-ready fixture builder
#
# Builds a project directory that has:
#   - A backlog item (status=new) for the given workflow_id
#   - A frozen success-criteria contract
#   - Evidence files for each criterion
#   - A satisfied ledger (all_success_criteria_passed=True)
#   - A workflow state file (phase=VERIFY, active, points to contract/ledger)
#   - phase.yaml with active_work_item set (matching VERIFY phase)
#   - sweetclaude.yaml with work.active set
#
# Intentionally does NOT call enter_ship_phase — the tests do that.
# ---------------------------------------------------------------------------

def _build_ship_ready_project(
    project: Path,
    workflow_id: str,
    story_type: str = "small",
) -> dict[str, Any]:
    """
    Populate a tmp_path directory with all state required for enter_ship_phase
    to succeed. Returns a dict with 'contract_hash' and 'item_file'.
    """
    story_prefix = "small-story" if story_type == "small" else "large-story"
    state_owner = "small_story_controller" if story_type == "small" else "large_story_controller"
    entry_category = f"{story_type}-story"

    # 1. Backlog item file (status=new, schema-valid frontmatter)
    backlog_dir = project / ".sweetclaude" / "product" / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    item_file = backlog_dir / f"{workflow_id}-test-story.md"
    item_file.write_text(
        "---\n"
        f"id: {workflow_id}\n"
        "status: new\n"
        "type: bug-fix\n"
        f"title: Test story {workflow_id}\n"
        "created: '2026-06-26T00:00:00+00:00'\n"
        "---\n\n"
        f"Test backlog item for {workflow_id}.\n",
        encoding="utf-8",
    )

    # 2. Contract — placed at the default canonical path
    contracts_dir = project / ".sweetclaude" / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    contract_path = contracts_dir / "success-criteria-contract.yaml"

    # Evidence artifact paths must be under .sweetclaude/reports/ and match
    # what the controller generates in enter_verify_phase.
    criterion_ids = ["SC-001"]
    evidence_artifact_prefix = (
        f".sweetclaude/reports/{story_prefix}/{workflow_id}/evidence"
    )
    contract = _minimal_contract(
        story_id=workflow_id,
        criterion_ids=criterion_ids,
        evidence_artifact_prefix=evidence_artifact_prefix,
    )
    contract_hash = str(contract["contract_freeze"]["contract_hash"])
    contract_path.write_text(
        yaml.safe_dump(contract, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )

    # 3. Evidence file for SC-001
    evidence_dir = (
        project / ".sweetclaude" / "reports" / story_prefix / workflow_id / "evidence"
    )
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "SC-001.json"
    evidence_file.write_text(
        json.dumps(
            {
                "ok": True,
                "criterion_id": "SC-001",
                "workflow_id": workflow_id,
                "success_criteria_contract_hash": contract_hash,
                "measured_command": "python3 -m pytest -k SC-001",
                "observed_output": "test passed",
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    # 4. Ledger — must satisfy validate_success_criteria_ledger
    ledger_dir = project / ".sweetclaude" / "reports"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_dir / "success-criteria-ledger.json"
    evidence_artifact_rel = f"{evidence_artifact_prefix}/SC-001.json"
    ledger = {
        "story_id": workflow_id,
        "workflow_id": workflow_id,
        "success_criteria_contract_hash": contract_hash,
        "generated_by": state_owner,
        "generated_at": "controller-generated",
        "all_success_criteria_passed": True,
        "criteria": [
            {
                "id": "SC-001",
                "status": "pass",
                "success_criteria_contract_hash": contract_hash,
                "evidence_artifact": evidence_artifact_rel,
                "evidence_owner": "controller",
                "evidence_path": evidence_artifact_rel,
                "measured_command": "python3 -m pytest -k SC-001",
                "measured_at": "controller-generated",
                "observed_output_path": evidence_artifact_rel,
                "evidence_fresh": True,
                "freshness_status": "fresh",
            }
        ],
    }
    ledger_path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # 5. Workflow state (phase=VERIFY, not complete, pointing to contract/ledger)
    workflows_dir = project / ".sweetclaude" / "state" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    workflow_state = {
        "workflow_id": workflow_id,
        "phase": "VERIFY",
        "state_owner": state_owner,
        "requires_success_criteria_contract": True,
        "success_criteria_contract_path": ".sweetclaude/contracts/success-criteria-contract.yaml",
        "success_criteria_contract_hash": contract_hash,
        "criterion_ids": criterion_ids,
        "success_criteria_ledger_path": ".sweetclaude/reports/success-criteria-ledger.json",
    }
    (workflows_dir / f"{workflow_id}.yaml").write_text(
        yaml.safe_dump(workflow_state, sort_keys=False),
        encoding="utf-8",
    )

    # 6. phase.yaml — active_work_item pointing at workflow_id / VERIFY
    state_dir = project / ".sweetclaude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    phase_yaml_path = state_dir / "phase.yaml"
    phase_yaml_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "active_work_item": {
                    "id": workflow_id,
                    "phase": "VERIFY",
                    "entry_category": entry_category,
                },
                "last_work_item_id": None,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # 7. sweetclaude.yaml — work.active pointing at workflow_id
    sc_yaml_path = state_dir / "sweetclaude.yaml"
    sc_yaml_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "work": {
                    "active": {"id": workflow_id, "phase": "VERIFY"},
                    "last_item_id": None,
                },
                "work_history": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    return {"contract_hash": contract_hash, "item_file": item_file}


# ---------------------------------------------------------------------------
# State-reading helpers
# ---------------------------------------------------------------------------

def _read_phase_yaml(project: Path) -> dict[str, Any]:
    path = project / ".sweetclaude" / "state" / "phase.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _read_sweetclaude_yaml(project: Path) -> dict[str, Any]:
    path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _read_backlog_frontmatter(item_file: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a markdown file with --- delimiters."""
    text = item_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}
    return yaml.safe_load("\n".join(lines[1:end])) or {}


def _find_item_file_any_status(project: Path, workflow_id: str) -> Path | None:
    """Find the backlog item file for workflow_id in all possible locations."""
    bases = [
        project / ".sweetclaude" / "product",
        project / "docs" / "product",
    ]
    for base in bases:
        for subdir in ("backlog", "done", "backlog/archived"):
            d = base / subdir
            if d.is_dir():
                matches = list(d.glob(f"{workflow_id}-*.md"))
                if matches:
                    return matches[0]
    return None


# ---------------------------------------------------------------------------
# TestSmallStoryCloseout
# ---------------------------------------------------------------------------

class TestSmallStoryCloseout:
    """SC-001, SC-002, SC-003: small-story enter_ship_phase writes all close-out state."""

    def test_phase_yaml_last_and_active(self, tmp_path):
        """
        SC-001: after a successful small_story_controller.enter_ship_phase for
        workflow X, phase.yaml last_work_item_id == X AND active_work_item is None.
        """
        workflow_id = "ISSUE-901"
        _build_ship_ready_project(tmp_path, workflow_id, story_type="small")

        result = small_story_controller.enter_ship_phase(
            project_dir=tmp_path,
            workflow_id=workflow_id,
            terminal_actor="small_story_controller",
        )
        assert result.get("ok") is True, f"enter_ship_phase must succeed; got: {result}"

        phase = _read_phase_yaml(tmp_path)
        assert phase.get("last_work_item_id") == workflow_id, (
            f"phase.yaml last_work_item_id must be {workflow_id!r}; "
            f"got {phase.get('last_work_item_id')!r}"
        )
        assert phase.get("active_work_item") is None, (
            f"phase.yaml active_work_item must be None after close-out; "
            f"got {phase.get('active_work_item')!r}"
        )

    def test_sweetclaude_yaml_record(self, tmp_path):
        """
        SC-002: after close-out, sweetclaude.yaml work.last_item_id == X,
        work.active is None, and work_history contains an entry for X with
        shape {id, completed, outcome, title}.
        """
        workflow_id = "ISSUE-902"
        _build_ship_ready_project(tmp_path, workflow_id, story_type="small")

        result = small_story_controller.enter_ship_phase(
            project_dir=tmp_path,
            workflow_id=workflow_id,
            terminal_actor="small_story_controller",
        )
        assert result.get("ok") is True, f"enter_ship_phase must succeed; got: {result}"

        sc = _read_sweetclaude_yaml(tmp_path)
        work = sc.get("work", {})

        assert work.get("last_item_id") == workflow_id, (
            f"sweetclaude.yaml work.last_item_id must be {workflow_id!r}; "
            f"got {work.get('last_item_id')!r}"
        )
        assert work.get("active") is None, (
            f"sweetclaude.yaml work.active must be None after close-out; "
            f"got {work.get('active')!r}"
        )

        history = sc.get("work_history", [])
        entry = next((h for h in history if h.get("id") == workflow_id), None)
        assert entry is not None, (
            f"work_history must contain an entry for {workflow_id!r}; "
            f"history: {history!r}"
        )
        # Shape contract: {id, completed, outcome, title}
        assert entry.get("id") == workflow_id, (
            f"history entry id must be {workflow_id!r}; got {entry.get('id')!r}"
        )
        assert isinstance(entry.get("completed"), str) and entry["completed"], (
            f"history entry 'completed' must be a non-empty timestamp string; "
            f"got {entry.get('completed')!r}"
        )
        assert entry.get("outcome"), (
            f"history entry 'outcome' must indicate done/complete; "
            f"got {entry.get('outcome')!r}"
        )
        assert isinstance(entry.get("title"), str), (
            f"history entry 'title' must be a string; got {entry.get('title')!r}"
        )

    def test_item_file_done(self, tmp_path):
        """
        SC-003: after close-out, the backlog item file for X has frontmatter
        status equal to the canonical "done" status.
        """
        workflow_id = "ISSUE-903"
        _build_ship_ready_project(tmp_path, workflow_id, story_type="small")

        result = small_story_controller.enter_ship_phase(
            project_dir=tmp_path,
            workflow_id=workflow_id,
            terminal_actor="small_story_controller",
        )
        assert result.get("ok") is True, f"enter_ship_phase must succeed; got: {result}"

        item_file = _find_item_file_any_status(tmp_path, workflow_id)
        assert item_file is not None, (
            f"backlog item file for {workflow_id} must still be findable after close-out"
        )
        fm = _read_backlog_frontmatter(item_file)
        assert fm.get("status") == DONE_STATUS, (
            f"backlog item frontmatter status must be {DONE_STATUS!r}; "
            f"got {fm.get('status')!r} from {item_file}"
        )


# ---------------------------------------------------------------------------
# TestLargeStoryCloseout
# ---------------------------------------------------------------------------

class TestLargeStoryCloseout:
    """SC-004, SC-005, SC-006: large-story enter_ship_phase writes all close-out state."""

    def test_phase_yaml_last_and_active(self, tmp_path):
        """
        SC-004: after a successful large_story_controller.enter_ship_phase for
        workflow X, phase.yaml last_work_item_id == X AND active_work_item is None.
        """
        workflow_id = "ISSUE-904"
        _build_ship_ready_project(tmp_path, workflow_id, story_type="large")

        result = large_story_controller.enter_ship_phase(
            project_dir=tmp_path,
            workflow_id=workflow_id,
            terminal_actor="large_story_controller",
        )
        assert result.get("ok") is True, f"enter_ship_phase must succeed; got: {result}"

        phase = _read_phase_yaml(tmp_path)
        assert phase.get("last_work_item_id") == workflow_id, (
            f"phase.yaml last_work_item_id must be {workflow_id!r}; "
            f"got {phase.get('last_work_item_id')!r}"
        )
        assert phase.get("active_work_item") is None, (
            f"phase.yaml active_work_item must be None after close-out; "
            f"got {phase.get('active_work_item')!r}"
        )

    def test_sweetclaude_yaml_record(self, tmp_path):
        """
        SC-005: after close-out, sweetclaude.yaml work.last_item_id == X,
        work.active is None, and work_history contains an entry for X with
        shape {id, completed, outcome, title}.
        """
        workflow_id = "ISSUE-905"
        _build_ship_ready_project(tmp_path, workflow_id, story_type="large")

        result = large_story_controller.enter_ship_phase(
            project_dir=tmp_path,
            workflow_id=workflow_id,
            terminal_actor="large_story_controller",
        )
        assert result.get("ok") is True, f"enter_ship_phase must succeed; got: {result}"

        sc = _read_sweetclaude_yaml(tmp_path)
        work = sc.get("work", {})

        assert work.get("last_item_id") == workflow_id, (
            f"sweetclaude.yaml work.last_item_id must be {workflow_id!r}; "
            f"got {work.get('last_item_id')!r}"
        )
        assert work.get("active") is None, (
            f"sweetclaude.yaml work.active must be None after close-out; "
            f"got {work.get('active')!r}"
        )

        history = sc.get("work_history", [])
        entry = next((h for h in history if h.get("id") == workflow_id), None)
        assert entry is not None, (
            f"work_history must contain an entry for {workflow_id!r}; "
            f"history: {history!r}"
        )
        assert entry.get("id") == workflow_id
        assert isinstance(entry.get("completed"), str) and entry["completed"], (
            f"history entry 'completed' must be a non-empty timestamp string; "
            f"got {entry.get('completed')!r}"
        )
        assert entry.get("outcome"), (
            f"history entry 'outcome' must indicate done/complete; "
            f"got {entry.get('outcome')!r}"
        )
        assert isinstance(entry.get("title"), str), (
            f"history entry 'title' must be a string; got {entry.get('title')!r}"
        )

    def test_item_file_done(self, tmp_path):
        """
        SC-006: after close-out, the backlog item file for X has frontmatter
        status equal to the canonical "done" status.
        """
        workflow_id = "ISSUE-906"
        _build_ship_ready_project(tmp_path, workflow_id, story_type="large")

        result = large_story_controller.enter_ship_phase(
            project_dir=tmp_path,
            workflow_id=workflow_id,
            terminal_actor="large_story_controller",
        )
        assert result.get("ok") is True, f"enter_ship_phase must succeed; got: {result}"

        item_file = _find_item_file_any_status(tmp_path, workflow_id)
        assert item_file is not None, (
            f"backlog item file for {workflow_id} must still be findable after close-out"
        )
        fm = _read_backlog_frontmatter(item_file)
        assert fm.get("status") == DONE_STATUS, (
            f"backlog item frontmatter status must be {DONE_STATUS!r}; "
            f"got {fm.get('status')!r} from {item_file}"
        )


# ---------------------------------------------------------------------------
# TestCloseoutGuards
# ---------------------------------------------------------------------------

class TestCloseoutGuards:
    """SC-007: no-clobber guard — closing X must not clobber active pointer for Y."""

    def test_mismatched_active_not_clobbered(self, tmp_path):
        """
        SC-007: when phase.yaml active_work_item points at workflow Y (a different
        workflow), closing X must NOT clear Y's active pointer and must NOT set
        last_work_item_id to X.

        This guard may already be implemented (the test may pass today). If so,
        that is intentional: SC-007 locks existing fail-safe behavior.
        """
        workflow_x = "ISSUE-907"
        workflow_y = "ISSUE-908"

        # Build a ship-ready project for X
        _build_ship_ready_project(tmp_path, workflow_x, story_type="small")

        # Overwrite phase.yaml and sweetclaude.yaml to point at Y instead of X,
        # simulating a state where Y is active and X is trying to close out.
        state_dir = tmp_path / ".sweetclaude" / "state"
        phase_yaml_path = state_dir / "phase.yaml"
        phase_yaml_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 2,
                    "active_work_item": {
                        "id": workflow_y,
                        "phase": "IMPLEMENT",
                        "entry_category": "small-story",
                    },
                    "last_work_item_id": None,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        sc_yaml_path = state_dir / "sweetclaude.yaml"
        sc_yaml_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 2,
                    "work": {
                        "active": {"id": workflow_y, "phase": "IMPLEMENT"},
                        "last_item_id": None,
                    },
                    "work_history": [],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        # Attempt to close X — result may be blocked or succeed; the guard
        # behavior is what matters regardless.
        small_story_controller.enter_ship_phase(
            project_dir=tmp_path,
            workflow_id=workflow_x,
            terminal_actor="small_story_controller",
        )

        phase = _read_phase_yaml(tmp_path)
        sc = _read_sweetclaude_yaml(tmp_path)

        # Y's active pointer must NOT have been cleared
        active_item = phase.get("active_work_item")
        assert isinstance(active_item, dict) and active_item.get("id") == workflow_y, (
            f"phase.yaml active_work_item must still point to {workflow_y!r} "
            f"(not be clobbered by close-out of {workflow_x!r}); "
            f"got {active_item!r}"
        )

        # last_work_item_id must NOT have been set to X (Y was active, not X)
        last = phase.get("last_work_item_id")
        assert last != workflow_x, (
            f"phase.yaml last_work_item_id must NOT be set to {workflow_x!r} "
            f"when {workflow_y!r} was the active item; got {last!r}"
        )

        sc_active = (sc.get("work") or {}).get("active")
        assert sc_active is not None and sc_active.get("id") == workflow_y, (
            f"sweetclaude.yaml work.active must still be {workflow_y!r}; "
            f"got {sc_active!r}"
        )

    def test_phase_active_other_sweetclaude_none_no_split_brain(self, tmp_path):
        """
        Regression (review #2): when phase.yaml active points at a DIFFERENT
        workflow Y but sweetclaude.yaml work.active is None, closing X must NOT
        advance EITHER file to X. The two files must not disagree (split brain):
        phase stays at Y; sweetclaude must not record X as last/ in history.
        """
        workflow_x = "ISSUE-921"
        workflow_y = "ISSUE-922"
        _build_ship_ready_project(tmp_path, workflow_x, story_type="small")

        state_dir = tmp_path / ".sweetclaude" / "state"
        (state_dir / "phase.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 2,
                    "active_work_item": {
                        "id": workflow_y,
                        "phase": "IMPLEMENT",
                        "entry_category": "small-story",
                    },
                    "last_work_item_id": None,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (state_dir / "sweetclaude.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 2,
                    "work": {"active": None, "last_item_id": None},
                    "work_history": [],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        record_workflow_closeout(tmp_path, workflow_x)

        phase = _read_phase_yaml(tmp_path)
        sc = _read_sweetclaude_yaml(tmp_path)
        work = sc.get("work", {})

        # phase.yaml: Y preserved, X not recorded as last
        active_item = phase.get("active_work_item")
        assert isinstance(active_item, dict) and active_item.get("id") == workflow_y, (
            f"phase.yaml active must still be {workflow_y!r}; got {active_item!r}"
        )
        assert phase.get("last_work_item_id") != workflow_x, (
            f"phase.yaml last_work_item_id must NOT advance to {workflow_x!r} "
            f"while {workflow_y!r} is active; got {phase.get('last_work_item_id')!r}"
        )
        # sweetclaude.yaml: must NOT advance to X either (no split brain)
        assert work.get("last_item_id") != workflow_x, (
            f"sweetclaude work.last_item_id must NOT advance to {workflow_x!r} "
            f"while phase.yaml shows {workflow_y!r} active; "
            f"got {work.get('last_item_id')!r}"
        )
        assert not any(
            isinstance(h, dict) and h.get("id") == workflow_x
            for h in sc.get("work_history", [])
        ), f"work_history must not record {workflow_x!r} when close-out is blocked"

    def test_reentry_with_cleared_active_still_records_last(self, tmp_path):
        """
        Regression (review #6): on a re-entry / idempotency close-out where the
        active pointer is already None in BOTH files (not pointing at any other
        item), record_workflow_closeout must still advance last_work_item_id /
        work.last_item_id to X — the record must not be lost.
        """
        workflow_x = "ISSUE-923"
        _build_ship_ready_project(tmp_path, workflow_x, story_type="small")

        state_dir = tmp_path / ".sweetclaude" / "state"
        (state_dir / "phase.yaml").write_text(
            yaml.safe_dump(
                {"schema_version": 2, "active_work_item": None, "last_work_item_id": None},
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (state_dir / "sweetclaude.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 2,
                    "work": {"active": None, "last_item_id": None},
                    "work_history": [],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        record_workflow_closeout(tmp_path, workflow_x)

        phase = _read_phase_yaml(tmp_path)
        sc = _read_sweetclaude_yaml(tmp_path)
        assert phase.get("last_work_item_id") == workflow_x, (
            f"phase.yaml last_work_item_id must advance to {workflow_x!r} even when "
            f"active was already None; got {phase.get('last_work_item_id')!r}"
        )
        assert sc.get("work", {}).get("last_item_id") == workflow_x, (
            f"sweetclaude work.last_item_id must advance to {workflow_x!r} even when "
            f"active was already None; got {sc.get('work', {}).get('last_item_id')!r}"
        )


# ---------------------------------------------------------------------------
# TestPathParity
# ---------------------------------------------------------------------------

class TestPathParity:
    """SC-008: orchestrator _complete_sc and controller enter_ship_phase produce identical state."""

    def test_controller_orchestrator_parity(self, tmp_path):
        """
        SC-008: two separate projects start with identical state. One is closed
        via small_story_controller.enter_ship_phase, the other via
        orchestrator_loop._complete_sc. After close-out, both must have:
          - identical phase.yaml: last_work_item_id == X, active_work_item == None
          - identical sweetclaude.yaml: work.last_item_id == X, work.active == None
          - work_history entry shape {id, completed, outcome, title} in both
          - backlog item file status == "done" in both

        Volatile fields (timestamps) are normalized out for the shape comparison.
        """
        workflow_id = "ISSUE-909"

        # Two isolated project dirs
        proj_controller = tmp_path / "via_controller"
        proj_controller.mkdir()
        proj_orchestrator = tmp_path / "via_orchestrator"
        proj_orchestrator.mkdir()

        # Identical starting state for both
        _build_ship_ready_project(proj_controller, workflow_id, story_type="small")
        _build_ship_ready_project(proj_orchestrator, workflow_id, story_type="small")

        # Path 1: controller close-out
        ctrl_result = small_story_controller.enter_ship_phase(
            project_dir=proj_controller,
            workflow_id=workflow_id,
            terminal_actor="small_story_controller",
        )
        assert ctrl_result.get("ok") is True, (
            f"controller path must succeed; got: {ctrl_result}"
        )

        # Path 2: orchestrator _complete_sc close-out.
        # _complete_sc reads sweetclaude.yaml work.active to find the item id,
        # then calls _update_item_status to set the file done. The item file is
        # in .sweetclaude/product/ which _find_item_file searches.
        orchestrator_loop._complete_sc(
            str(proj_orchestrator),
            workflow_id,
            "complete",
            workflow_state=None,
        )

        def _normalize_history_entry(entry: dict) -> dict:
            """Strip volatile timestamp keys, keep shape-relevant keys only."""
            return {k: v for k, v in entry.items() if k not in ("completed", "at")}

        # --- phase.yaml assertions ---

        phase_ctrl = _read_phase_yaml(proj_controller)
        phase_orch = _read_phase_yaml(proj_orchestrator)

        assert phase_ctrl.get("last_work_item_id") == workflow_id, (
            f"controller: phase.yaml last_work_item_id must be {workflow_id!r}; "
            f"got {phase_ctrl.get('last_work_item_id')!r}"
        )
        assert phase_orch.get("last_work_item_id") == workflow_id, (
            f"orchestrator: phase.yaml last_work_item_id must be {workflow_id!r}; "
            f"got {phase_orch.get('last_work_item_id')!r}"
        )
        assert phase_ctrl.get("active_work_item") is None, (
            "controller: phase.yaml active_work_item must be None after close-out"
        )
        assert phase_orch.get("active_work_item") is None, (
            "orchestrator: phase.yaml active_work_item must be None after close-out"
        )

        # --- sweetclaude.yaml assertions ---

        sc_ctrl = _read_sweetclaude_yaml(proj_controller)
        sc_orch = _read_sweetclaude_yaml(proj_orchestrator)
        work_ctrl = sc_ctrl.get("work", {})
        work_orch = sc_orch.get("work", {})

        assert work_ctrl.get("last_item_id") == workflow_id, (
            f"controller: work.last_item_id must be {workflow_id!r}; "
            f"got {work_ctrl.get('last_item_id')!r}"
        )
        assert work_orch.get("last_item_id") == workflow_id, (
            f"orchestrator: work.last_item_id must be {workflow_id!r}; "
            f"got {work_orch.get('last_item_id')!r}"
        )
        assert work_ctrl.get("active") is None, (
            "controller: sweetclaude.yaml work.active must be None"
        )
        assert work_orch.get("active") is None, (
            "orchestrator: sweetclaude.yaml work.active must be None"
        )

        # --- work_history shape parity ---

        hist_ctrl = sc_ctrl.get("work_history", [])
        hist_orch = sc_orch.get("work_history", [])

        entry_ctrl = next(
            (h for h in hist_ctrl if isinstance(h, dict) and h.get("id") == workflow_id), None
        )
        entry_orch = next(
            (h for h in hist_orch if isinstance(h, dict) and h.get("id") == workflow_id), None
        )

        assert entry_ctrl is not None, (
            f"controller: work_history must have an entry for {workflow_id!r}"
        )
        assert entry_orch is not None, (
            f"orchestrator: work_history must have an entry for {workflow_id!r}"
        )

        norm_ctrl = _normalize_history_entry(entry_ctrl)
        norm_orch = _normalize_history_entry(entry_orch)

        assert set(norm_ctrl.keys()) == set(norm_orch.keys()), (
            f"work_history entry shape mismatch between controller and orchestrator:\n"
            f"  controller keys (minus timestamps): {sorted(norm_ctrl.keys())}\n"
            f"  orchestrator keys (minus timestamps): {sorted(norm_orch.keys())}"
        )

        # Both entries must have the required shape keys
        for required_key in ("id", "outcome", "title"):
            assert required_key in norm_ctrl, (
                f"controller work_history entry missing key {required_key!r}"
            )
            assert required_key in norm_orch, (
                f"orchestrator work_history entry missing key {required_key!r}"
            )

        # Regression (review #5): shared keys must carry IDENTICAL values across
        # paths, not just identical key sets. A successful close-out is the same
        # event regardless of which path ran it.
        for shared_key in set(norm_ctrl) & set(norm_orch):
            if shared_key == "id":
                continue
            assert norm_ctrl[shared_key] == norm_orch[shared_key], (
                f"work_history entry value mismatch for {shared_key!r} between paths: "
                f"controller={norm_ctrl[shared_key]!r} orchestrator={norm_orch[shared_key]!r}"
            )

        # --- item file parity ---

        ctrl_item = _find_item_file_any_status(proj_controller, workflow_id)
        orch_item = _find_item_file_any_status(proj_orchestrator, workflow_id)

        assert ctrl_item is not None, (
            "controller: item file must be findable after close-out"
        )
        assert orch_item is not None, (
            "orchestrator: item file must be findable after close-out"
        )

        fm_ctrl = _read_backlog_frontmatter(ctrl_item)
        fm_orch = _read_backlog_frontmatter(orch_item)

        assert fm_ctrl.get("status") == DONE_STATUS, (
            f"controller: item file status must be {DONE_STATUS!r}; "
            f"got {fm_ctrl.get('status')!r}"
        )
        assert fm_orch.get("status") == DONE_STATUS, (
            f"orchestrator: item file status must be {DONE_STATUS!r}; "
            f"got {fm_orch.get('status')!r}"
        )


# ---------------------------------------------------------------------------
# TestSkillDoc
# ---------------------------------------------------------------------------

class TestSkillDoc:
    """SC-009: deploy-ship SKILL.md must not instruct hand-editing of state fields."""

    def test_no_manual_state_edit_instruction(self):
        """
        SC-009: skill-library/build/deploy-ship/SKILL.md must NOT contain:
          - any instruction to manually update/edit last_work_item_id
          - any instruction to hand-edit active_work_item in a YAML block

        Currently Step 7 of the skill tells the LLM to edit both fields
        directly. This test MUST fail until the skill is updated.
        """
        skill_path = (
            Path(__file__).resolve().parent.parent
            / "skill-library"
            / "build"
            / "deploy-ship"
            / "SKILL.md"
        )
        assert skill_path.exists(), f"deploy-ship SKILL.md not found at {skill_path}"
        content = skill_path.read_text(encoding="utf-8")

        # The skill must not tell the LLM to set or update last_work_item_id manually.
        assert "last_work_item_id" not in content, (
            "skill-library/build/deploy-ship/SKILL.md must not contain 'last_work_item_id'. "
            "The field must be written deterministically by the controller, not "
            "hand-edited by the LLM following prose instructions."
        )

        # The skill must not instruct hand-editing active_work_item via a YAML
        # code block. The current Step 7 shows a YAML block with active_work_item
        # fields under an "Update" / "edit" heading — detect that pattern.
        yaml_block_with_active = re.search(
            r"```(?:yaml|yml)[^`]*active_work_item[^`]*```",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        assert yaml_block_with_active is None, (
            "skill-library/build/deploy-ship/SKILL.md must not contain a YAML code block that "
            "instructs the LLM to hand-edit active_work_item. "
            "Close-out state writes must be owned by the controller."
        )
