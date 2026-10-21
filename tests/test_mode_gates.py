"""Contract tests for mode-gate enforcement (ledger rows R-092, R-094, R-095).

scripts/gate_check.py is the single evaluator for the compiled mode gates in
.sweetclaude/state/effective-gates.yaml. It resolves sprints and issues through
the canonical artifact store (hooks/sc-artifact-impl.py), so a fixture project
in Agile mode never plants artifacts under legacy paths.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_CHECK = REPO_ROOT / "scripts" / "gate_check.py"

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
                directory: str = "roadmap/issues") -> Path:
    issue_id = f"ISSUE-{number:03d}"
    folder = project / ".sweetclaude" / "product" / directory
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{issue_id}-work-item-{number}.md"
    frontmatter = {"id": issue_id, "title": f"Work item {number}", "status": status,
                   "mode_introduced": "agile", "created": "2026-10-01", "updated": "2026-10-01"}
    if sprint:
        frontmatter["sprint"] = sprint
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