"""Contract tests for mode-gate enforcement (ledger rows R-089, R-091, R-092,
R-093, R-094, R-095).

scripts/gate_check.py is the single evaluator for the compiled mode gates in
.sweetclaude/state/effective-gates.yaml. It resolves sprints and issues through
the canonical artifact store (hooks/sc-artifact-impl.py), so a fixture project
in Agile mode never plants artifacts under legacy paths.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_CHECK = REPO_ROOT / "scripts" / "gate_check.py"

from test_hook_protocol_contract import (  # noqa: E402
    _md5,
    assert_allowed,
    assert_denied,
    feedback_text,
    payload,
    run_hook,
    stdout_json,
)


def denial_reason(result) -> str:
    specific = (stdout_json(result) or {}).get("hookSpecificOutput") or {}
    return str(specific.get("permissionDecisionReason") or "")

AGILE_GATES = [
    {"phase": "IMPLEMENT", "condition": "no_active_sprint", "action": "block",
     "message": "No active sprint. Run /sweetclaude:project-sprints start to activate a sprint."},
    {"phase": "IMPLEMENT", "condition": "issue_not_in_sprint", "action": "warn",
     "message": "This issue is not assigned to the active sprint. Assign it or start a new sprint."},
    {"phase": "SHIP", "condition": "sprint_complete", "action": "prompt",
     "message": "All sprint issues are done. Run sprint close before shipping."},
]


def write_effective_gates(project: Path, mode: str, gates: list[dict], **extra) -> None:
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "mode": mode, "default_tdd_level": 1,
               "blocked_skills": [], "gates": gates}
    payload.update(extra)
    (state / "effective-gates.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")


def write_sweetclaude_yaml(project: Path, *, active_id: str = "", mode: str = "agile") -> None:
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True, exist_ok=True)
    active = {"id": active_id, "phase": "IMPLEMENT"} if active_id else {}
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2,
        "project": {"name": "t", "mode": mode},
        "framework": {"setup_complete": True},
        "work": {"active": active},
    }), encoding="utf-8")


def write_sprint(project: Path, number: int, status: str, title: str = "sprint") -> Path:
    sprint_id = f"SP-{number:03d}"
    folder = project / ".sweetclaude" / "product" / "sprints"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sprint_id}-{title.replace(' ', '-')}.md"
    path.write_text(
        f"---\nid: {sprint_id}\ntitle: {title}\nstatus: {status}\n"
        "start_date: 2026-10-01\nend_date: 2026-10-14\n---\n\n"
        f"# {sprint_id}: {title}\n",
        encoding="utf-8")
    return path


def write_issue(project: Path, number: int, status: str, sprint: str = "", *,
                directory: str = "roadmap/issues", extra: dict | None = None) -> Path:
    issue_id = f"ISSUE-{number:03d}"
    folder = project / ".sweetclaude" / "product" / directory
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{issue_id}-work-item-{number}.md"
    frontmatter = {"id": issue_id, "title": f"Work item {number}", "status": status,
                   "mode_introduced": "agile", "created": "2026-10-01", "updated": "2026-10-01"}
    if sprint:
        frontmatter["sprint"] = sprint
    if extra:
        frontmatter.update(extra)
    path.write_text(
        "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n\n"
        f"# {issue_id}: Work item {number}\n\n## Description\n\nDo the thing.\n",
        encoding="utf-8")
    return path


def run_gate_check(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GATE_CHECK), *args],
                          capture_output=True, text=True, timeout=30)


def gate_json(result: subprocess.CompletedProcess) -> dict:
    return json.loads(result.stdout)


def agile_project(root: Path, *, sprint_status: str | None) -> Path:
    project = root / "project"
    project.mkdir(parents=True)
    write_effective_gates(project, "agile", AGILE_GATES)
    write_sweetclaude_yaml(project, active_id="ISSUE-001")
    write_issue(project, 1, "in_progress", sprint="SP-001")
    if sprint_status is not None:
        write_sprint(project, 1, sprint_status, title="sprint one")
    return project


class TestR094AgileImplementGateResolvesActiveSprint:
    def test_active_sprint_in_canonical_store_passes(self, tmp_path):
        project = agile_project(tmp_path, sprint_status="active")
        result = run_gate_check("load", "--skill", "sweetclaude:build",
                                "--project-dir", str(project))
        assert result.returncode == 0, result.stderr
        payload = gate_json(result)
        assert payload["allow"] is True

    def test_no_sprint_at_all_is_denied(self, tmp_path):
        project = agile_project(tmp_path, sprint_status=None)
        result = run_gate_check("load", "--skill", "sweetclaude:build",
                                "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        payload = gate_json(result)
        assert payload["allow"] is False
        assert "no_active_sprint" in payload["unmet"]
        assert any("No active sprint" in reason for reason in payload["reasons"])

    def test_closed_sprint_is_denied(self, tmp_path):
        project = agile_project(tmp_path, sprint_status="closed")
        result = run_gate_check("load", "--skill", "sweetclaude:build",
                                "--project-dir", str(project))
        assert result.returncode == 2
        assert gate_json(result)["allow"] is False

    def test_direct_workflow_invocation_names_the_gate_reason_text(self, tmp_path):
        project = agile_project(tmp_path, sprint_status=None)
        result = run_gate_check("load", "--skill", "sweetclaude:library-load",
                                "--args", "code-feature implement the login form",
                                "--project-dir", str(project))
        assert result.returncode == 2
        payload = gate_json(result)
        assert any("Gate no_active_sprint unmet:" in reason for reason in payload["reasons"])
        assert any("Unmet:" in reason for reason in payload["reasons"])
        assert any("Hard gate" in reason for reason in payload["reasons"])

    def test_advance_to_implement_matches_load(self, tmp_path):
        project = agile_project(tmp_path, sprint_status="active")
        passing = run_gate_check("advance", "--to", "IMPLEMENT", "--project-dir", str(project))
        assert passing.returncode == 0
        assert gate_json(passing)["allow"] is True
        project_no_sprint = agile_project(tmp_path / "second", sprint_status=None)
        denied = run_gate_check("advance", "--to", "IMPLEMENT",
                                "--project-dir", str(project_no_sprint))
        assert denied.returncode == 2
        assert gate_json(denied)["allow"] is False

    def test_sprint_management_workflows_are_not_gated(self, tmp_path):
        project = agile_project(tmp_path, sprint_status=None)
        result = run_gate_check("load", "--skill", "sweetclaude:library-load",
                                "--args", "project-sprints start sprint two",
                                "--project-dir", str(project))
        assert result.returncode == 0
        assert gate_json(result)["allow"] is True

    def test_missing_effective_gates_fails_open(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        result = run_gate_check("load", "--skill", "sweetclaude:build",
                                "--project-dir", str(project))
        assert result.returncode == 0
        assert gate_json(result) == {"allow": True, "reasons": [], "unmet": []}

    def test_flow_mode_project_with_no_gates_allows(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        write_effective_gates(project, "flow", [])
        write_sweetclaude_yaml(project)
        result = run_gate_check("load", "--skill", "sweetclaude:build",
                                "--project-dir", str(project))
        assert result.returncode == 0
        assert gate_json(result)["allow"] is True

def bootstrap_ran(project: Path) -> None:
    Path(f"/tmp/.sweetclaude-bootstrap-ran-{_md5(str(project))}").write_text("", encoding="utf-8")


class TestR092SameGatesOnEveryImplementEntry:
    def prepare(self, tmp_path: Path, *, sprint_status: str | None = None) -> Path:
        project = agile_project(tmp_path, sprint_status=sprint_status)
        bootstrap_ran(project)
        return project

    def test_master_preflight_denies_build_without_active_sprint(self, tmp_path):
        project = self.prepare(tmp_path)
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:build")
        result = run_hook("master-preflight.sh", project, stdin)
        assert_denied(result)
        assert "No active sprint" in denial_reason(result)

    def test_master_preflight_denies_direct_workflow_invocation(self, tmp_path):
        project = self.prepare(tmp_path)
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:library-load",
                        args="code-feature implement the login form")
        result = run_hook("master-preflight.sh", project, stdin)
        assert_denied(result)
        assert "No active sprint" in denial_reason(result)

    def test_master_preflight_allows_build_with_active_sprint(self, tmp_path):
        project = self.prepare(tmp_path, sprint_status="active")
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:build")
        assert_allowed(run_hook("master-preflight.sh", project, stdin))

    def test_master_preflight_allows_the_sprint_remedy(self, tmp_path):
        project = self.prepare(tmp_path)
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:library-load",
                        args="project-sprints start sprint two")
        assert_allowed(run_hook("master-preflight.sh", project, stdin))

    def test_master_preflight_allows_unrelated_skills(self, tmp_path):
        project = self.prepare(tmp_path)
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:status")
        assert_allowed(run_hook("master-preflight.sh", project, stdin))

    def test_master_preflight_fails_open_without_compiled_gates(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        write_sweetclaude_yaml(project)
        bootstrap_ran(project)
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:build")
        assert_allowed(run_hook("master-preflight.sh", project, stdin))

    def test_load_and_advance_agree_for_the_same_project(self, tmp_path):
        project = self.prepare(tmp_path)
        denied = run_gate_check("load", "--skill", "sweetclaude:build", "--project-dir", str(project))
        advance = run_gate_check("advance", "--to", "IMPLEMENT", "--project-dir", str(project))
        assert gate_json(denied)["unmet"] == gate_json(advance)["unmet"]

    def test_library_loader_gates_between_selection_and_load(self):
        loader = (REPO_ROOT / "skills" / "library-load" / "SKILL.md").read_text(encoding="utf-8")
        assert loader.index("Select exactly one workflow") < loader.index("gate_check.py load")
        assert loader.index("gate_check.py load") < loader.index("<category>/<skill>/SKILL.md")
        assert "Output every entry in `reasons` and stop" in loader

    def test_go_evaluates_the_same_gate_script(self):
        go = (REPO_ROOT / "skills" / "go" / "SKILL.md").read_text(encoding="utf-8")
        assert "scripts/gate_check.py advance --to IMPLEMENT" in go


def sprint_project(root: Path, *, issue_status: str = "done", sprint_status: str = "active") -> Path:
    project = root / "project"
    project.mkdir(parents=True)
    write_effective_gates(project, "agile", AGILE_GATES)
    write_sweetclaude_yaml(project, active_id="ISSUE-001")
    write_issue(project, 1, issue_status, sprint="SP-001")
    if sprint_status is not None:
        write_sprint(project, 1, sprint_status, title="sprint one")
    return project


class TestR095SprintCloseRequirementWhenEnteringShip:
    def test_all_issues_done_and_sprint_open_prompts_sprint_close(self, tmp_path):
        project = sprint_project(tmp_path)
        result = run_gate_check("advance", "--to", "SHIP", "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        payload = gate_json(result)
        assert payload["allow"] is True
        assert "sprint_complete" in payload["unmet"]
        assert any("All sprint issues are done" in reason for reason in payload["reasons"])
        assert any("Soft gate" in reason for reason in payload["reasons"])

    def test_override_text_replaces_the_soft_escape(self, tmp_path):
        project = sprint_project(tmp_path)
        result = run_gate_check("advance", "--to", "SHIP",
                                "--override-text", "close the sprint with /sweetclaude:build project-sprints close",
                                "--project-dir", str(project))
        assert any(reason.endswith("close the sprint with /sweetclaude:build project-sprints close.")
                   for reason in gate_json(result)["reasons"])

    def test_open_issue_suppresses_the_requirement(self, tmp_path):
        project = sprint_project(tmp_path, issue_status="in_progress")
        payload = gate_json(run_gate_check("advance", "--to", "SHIP", "--project-dir", str(project)))
        assert payload == {"allow": True, "reasons": [], "unmet": []}

    def test_closed_sprint_suppresses_the_requirement(self, tmp_path):
        project = sprint_project(tmp_path, sprint_status="closed")
        payload = gate_json(run_gate_check("advance", "--to", "SHIP", "--project-dir", str(project)))
        assert payload == {"allow": True, "reasons": [], "unmet": []}

    def test_no_sprint_suppresses_the_requirement(self, tmp_path):
        project = sprint_project(tmp_path, sprint_status=None)
        payload = gate_json(run_gate_check("advance", "--to", "SHIP", "--project-dir", str(project)))
        assert payload == {"allow": True, "reasons": [], "unmet": []}

    def test_loading_deploy_ship_prompts_sprint_close(self, tmp_path):
        project = sprint_project(tmp_path)
        result = run_gate_check("load", "--skill", "sweetclaude:library-load",
                                "--args", "deploy-ship ship the milestone",
                                "--project-dir", str(project))
        assert result.returncode == 0
        assert any("All sprint issues are done" in reason
                   for reason in gate_json(result)["reasons"])

    def test_preflight_surfaces_the_requirement_as_context(self, tmp_path):
        project = sprint_project(tmp_path)
        bootstrap_ran(project)
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:library-load",
                        args="deploy-ship ship the milestone")
        result = run_hook("master-preflight.sh", project, stdin)
        assert_allowed(result)
        assert "All sprint issues are done" in feedback_text(result)

    def test_go_evaluates_the_ship_gate_before_deploy_ship(self):
        go = (REPO_ROOT / "skills" / "go" / "SKILL.md").read_text(encoding="utf-8")
        assert "scripts/gate_check.py advance --to SHIP" in go


KANBAN_GATES = [
    {"phase": "IMPLEMENT", "condition": "wip_limit_reached", "action": "block",
     "message": "WIP limit reached ({current}/{limit} items in_progress). Complete or move an item before starting new work."},
]


def kanban_project(root: Path, *, blocked=("project-sprints", "product-sprint-plan"),
                   active_id: str = "") -> Path:
    project = root / "project"
    project.mkdir(parents=True)
    write_effective_gates(project, "kanban", KANBAN_GATES, blocked_skills=list(blocked))
    write_sweetclaude_yaml(project, active_id=active_id, mode="kanban")
    if active_id:
        write_issue(project, 1, "in_progress")
    return project


class TestR089KanbanBlocksSprintPlanningSkills:
    def test_product_sprint_plan_is_denied_in_kanban(self, tmp_path):
        project = kanban_project(tmp_path)
        result = run_gate_check("load", "--skill", "sweetclaude:library-load",
                                "--args", "product-sprint-plan plan the next sprint",
                                "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        payload = gate_json(result)
        assert payload["allow"] is False
        assert payload["unmet"] == ["blocked_skill:product-sprint-plan"]
        assert any("product-sprint-plan is disabled in kanban mode" in reason
                   for reason in payload["reasons"])

    def test_project_sprints_is_denied_in_kanban(self, tmp_path):
        project = kanban_project(tmp_path)
        result = run_gate_check("load", "--skill", "sweetclaude:library-load",
                                "--args", "project-sprints start sprint two",
                                "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        assert "blocked_skill:project-sprints" in gate_json(result)["unmet"]

    def test_build_route_to_sprint_planning_is_denied(self, tmp_path):
        project = kanban_project(tmp_path)
        result = run_gate_check("load", "--skill", "sweetclaude:build",
                                "--args", "product-sprint-plan plan the next sprint",
                                "--project-dir", str(project))
        assert result.returncode == 2
        assert gate_json(result)["allow"] is False

    def test_compiled_chain_denies_sprint_planning(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir(parents=True)
        write_sweetclaude_yaml(project, mode="kanban")
        compiled = subprocess.run(
            ["bash", str(REPO_ROOT / "scripts" / "generate-effective-gates.sh")],
            env={**os.environ, "PROJECT_DIR": str(project)},
            capture_output=True, text=True, timeout=30)
        assert compiled.returncode == 0, compiled.stderr
        effective = yaml.safe_load(
            (project / ".sweetclaude" / "state" / "effective-gates.yaml").read_text(encoding="utf-8"))
        assert "product-sprint-plan" in effective["blocked_skills"]
        result = run_gate_check("load", "--skill", "sweetclaude:library-load",
                                "--args", "product-sprint-plan plan the next sprint",
                                "--project-dir", str(project))
        assert result.returncode == 2
        assert gate_json(result)["allow"] is False

    def test_issue_workflows_still_load_in_kanban(self, tmp_path):
        project = kanban_project(tmp_path, active_id="ISSUE-001")
        result = run_gate_check("load", "--skill", "sweetclaude:library-load",
                                "--args", "code-feature implement the login form",
                                "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result)["allow"] is True

    def test_agile_sprint_remedy_is_not_blocked(self, tmp_path):
        project = agile_project(tmp_path, sprint_status=None)
        result = run_gate_check("load", "--skill", "sweetclaude:library-load",
                                "--args", "project-sprints start sprint two",
                                "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result)["allow"] is True

    def test_master_preflight_denies_sprint_planning_in_kanban(self, tmp_path):
        project = kanban_project(tmp_path)
        bootstrap_ran(project)
        stdin = payload("PreToolUse-Skill", project, skill="sweetclaude:library-load",
                        args="product-sprint-plan plan the next sprint")
        result = run_hook("master-preflight.sh", project, stdin)
        assert_denied(result)
        assert "disabled in kanban mode" in denial_reason(result)


SHAPE_UP_GATES = [
    {"phase": "IMPLEMENT", "requires": "betting_table_approved", "action": "block",
     "message": "Work must be pitched and bet before implementation begins. Run /sweetclaude:project-issues to create issues from a pitch."},
    {"phase": "VERIFY", "condition": "ship_no_ship_decision", "action": "required",
     "message": "Ship/no-ship decision required. Did the core outcome land within appetite?"},
    {"phase": "PLAN", "condition": "issues_from_backlog", "action": "block",
     "message": "Shape Up has no backlog. Issues must be derived from an approved pitch."},
]


def shape_up_project(root: Path, *, approved: bool = False,
                     active_id: str = "ISSUE-001") -> Path:
    project = root / "project"
    project.mkdir(parents=True)
    write_effective_gates(project, "shape_up", SHAPE_UP_GATES)
    write_sweetclaude_yaml(project, active_id=active_id, mode="shape_up")
    if active_id:
        extra = {"betting_table_approved": True} if approved else None
        write_issue(project, 1, "in_progress", extra=extra)
    return project


class TestR091BettingTableApprovalGate:
    def test_approved_issue_passes_the_implement_gate(self, tmp_path):
        project = shape_up_project(tmp_path, approved=True)
        result = run_gate_check("advance", "--to", "IMPLEMENT", "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result)["allow"] is True

    def test_unapproved_issue_is_denied_before_implement(self, tmp_path):
        project = shape_up_project(tmp_path)
        result = run_gate_check("advance", "--to", "IMPLEMENT", "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        payload = gate_json(result)
        assert payload["allow"] is False
        assert "betting_table_approved" in payload["unmet"]
        assert any("pitched and bet" in reason for reason in payload["reasons"])
        assert any("Hard gate" in reason for reason in payload["reasons"])

    def test_load_matches_advance_for_betting_table(self, tmp_path):
        project = shape_up_project(tmp_path)
        result = run_gate_check("load", "--skill", "sweetclaude:library-load",
                                "--args", "code-feature implement the login form",
                                "--project-dir", str(project))
        assert result.returncode == 2
        assert "betting_table_approved" in gate_json(result)["unmet"]

    def test_no_active_issue_is_denied_before_implement(self, tmp_path):
        project = shape_up_project(tmp_path, active_id="")
        result = run_gate_check("advance", "--to", "IMPLEMENT", "--project-dir", str(project))
        assert result.returncode == 2

    def test_betting_table_write_produces_the_gate_flag(self, tmp_path):
        project = shape_up_project(tmp_path)
        write = subprocess.run(
            ["bash", "-c",
             f"source '{REPO_ROOT / 'hooks' / 'sc-artifact.sh'}' && "
             "sc_artifact_write ISSUE-001 '{\"betting_table_approved\": true}'"],
            cwd=project, capture_output=True, text=True, timeout=30)
        assert write.returncode == 0, write.stderr
        issue = (project / ".sweetclaude" / "product" / "roadmap" / "issues"
                 / "ISSUE-001-work-item-1.md").read_text(encoding="utf-8")
        assert "betting_table_approved: true" in issue
        allowed = run_gate_check("advance", "--to", "IMPLEMENT", "--project-dir", str(project))
        assert allowed.returncode == 0, allowed.stdout

    def test_betting_table_step_pins_the_canonical_write(self):
        skill = (REPO_ROOT / "skill-library" / "configure" / "project-mode" / "SKILL.md").read_text(encoding="utf-8")
        start = skill.index("## Shape Up — Solo Betting Table")
        betting = skill[start:skill.index("## ", start + 1)]
        assert "betting_table_approved: true" in betting
        assert "sc_artifact_write" in betting


def write_cycle(project: Path, number: int, status: str = "active",
                ship_no_ship: str | None = None) -> Path:
    cycle_id = f"CYC-{number:03d}"
    folder = project / ".sweetclaude" / "product" / "cycles"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{cycle_id}-cycle-{number}.md"
    frontmatter = {"id": cycle_id, "title": f"Cycle {number}", "type": "cycle",
                   "status": status}
    if ship_no_ship is not None:
        frontmatter["ship_no_ship"] = ship_no_ship
    path.write_text(
        "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n\n"
        f"# {cycle_id}: Cycle {number}\n",
        encoding="utf-8")
    return path


class TestR093ShipNoShipGateAtCycleEnd:
    def test_advance_past_verify_without_a_decision_is_refused(self, tmp_path):
        project = shape_up_project(tmp_path, approved=True)
        write_cycle(project, 1)
        result = run_gate_check("advance", "--to", "SHIP", "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        payload = gate_json(result)
        assert payload["allow"] is False
        assert "ship_no_ship_decision" in payload["unmet"]
        assert any("Ship/no-ship decision required" in reason for reason in payload["reasons"])
        assert any("Hard gate" in reason for reason in payload["reasons"])

    def test_ship_decision_allows_the_advance(self, tmp_path):
        project = shape_up_project(tmp_path, approved=True)
        write_cycle(project, 1, ship_no_ship="ship")
        result = run_gate_check("advance", "--to", "SHIP", "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result)["allow"] is True

    def test_no_ship_decision_still_refuses_the_advance(self, tmp_path):
        project = shape_up_project(tmp_path, approved=True)
        write_cycle(project, 1, ship_no_ship="no-ship")
        result = run_gate_check("advance", "--to", "SHIP", "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        payload = gate_json(result)
        assert payload["allow"] is False
        assert "ship_no_ship_decision" in payload["unmet"]

    def test_missing_cycle_file_refuses_the_advance(self, tmp_path):
        project = shape_up_project(tmp_path, approved=True)
        result = run_gate_check("advance", "--to", "SHIP", "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        assert gate_json(result)["allow"] is False

    def test_entering_verify_needs_no_decision_yet(self, tmp_path):
        project = shape_up_project(tmp_path, approved=True)
        write_cycle(project, 1)
        result = run_gate_check("advance", "--to", "VERIFY", "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result) == {"allow": True, "reasons": [], "unmet": []}

    def test_decision_on_the_active_cycle_is_the_one_read(self, tmp_path):
        project = shape_up_project(tmp_path, approved=True)
        write_cycle(project, 1, status="closed")
        write_cycle(project, 2, ship_no_ship="ship")
        result = run_gate_check("advance", "--to", "SHIP", "--project-dir", str(project))
        assert result.returncode == 0, result.stdout

    def test_loading_deploy_ship_is_denied_without_a_decision(self, tmp_path):
        project = shape_up_project(tmp_path, approved=True)
        write_cycle(project, 1)
        result = run_gate_check("load", "--skill", "sweetclaude:library-load",
                                "--args", "deploy-ship ship the milestone",
                                "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        assert "ship_no_ship_decision" in gate_json(result)["unmet"]

    def test_cycle_close_step_pins_the_canonical_write(self):
        skill = (REPO_ROOT / "skill-library" / "configure" / "project-mode" / "SKILL.md").read_text(encoding="utf-8")
        start = skill.index("## Shape Up — Ship/No-Ship")
        step = skill[start:skill.index("## ", start + 1)]
        assert "ship_no_ship" in step
        assert "sc_artifact_write" in step
