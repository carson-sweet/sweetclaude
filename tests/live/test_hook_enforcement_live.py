"""Live hook enforcement checks against a real Claude Code session (phase 2).

Skipped unless SWEETCLAUDE_LIVE=1. Each case builds a fixture project, asks
haiku to attempt the action one hook guards, and judges the stream-json
transcript and the filesystem. The model's prose is never asserted on. Twelve
cases at a 0.10 USD cap each keep worst-case spend at 1.20 USD.

Ledger rows covered: R-070 test-guardian, R-071 tdd-prewrite-guardian, R-072
auto-test-runner, R-073 wip-limit, R-074 preflight-guard, R-075
phase-dwelling-guard, R-076 master-preflight, R-236 artifact-guardian, the
phase 3 rows R-077 wip-limit on Write, R-241 test-guardian on Bash and
R-244 preflight-guard allowing its own remedy, R-251 tdd-commit-gate, R-089
the Kanban blocked-skill denial, R-091 the Shape Up betting-table gate, and
R-093 the Shape Up ship/no-ship gate.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from routing_behavior import make_project  # noqa: E402

pytestmark = [
    pytest.mark.skipif(os.environ.get("SWEETCLAUDE_LIVE") != "1", reason="set SWEETCLAUDE_LIVE=1 to run live Claude Code checks"),
    pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI not on PATH"),
]

BUDGET_USD = "0.10"
TIMEOUT_SECONDS = 300


def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _record_cost(events: list[dict], project: Path) -> None:
    cost_file = os.environ.get("SWEETCLAUDE_LIVE_COST_FILE")
    if not cost_file:
        return
    cost = None
    for event in events:
        value = event.get("total_cost_usd")
        if isinstance(value, (int, float)):
            cost = float(value)
    with open(cost_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"project": str(project), "cost_usd": cost}) + "\n")


def run_claude(project: Path, prompt: str) -> list[dict]:
    command = [
        "claude", "-p", prompt,
        "--plugin-dir", str(REPO_ROOT),
        "--setting-sources", "project,local",
        "--strict-mcp-config",
        "--model", "haiku",
        "--max-budget-usd", BUDGET_USD,
        "--output-format", "stream-json", "--verbose", "--include-hook-events",
        "--permission-mode", "acceptEdits",
        "--allowedTools", "Bash", "Write", "Edit", "Skill",
    ]
    proc = subprocess.run(command, cwd=project, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    events = []
    for line in proc.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    assert events, f"claude produced no events (exit {proc.returncode}): {proc.stderr[:400]}"
    _record_cost(events, project)
    return events


def blocks(event: dict) -> list[dict]:
    content = (event.get("message") or {}).get("content")
    return content if isinstance(content, list) else []


def tool_uses(events: list[dict], name: str) -> list[dict]:
    return [b for e in events if e.get("type") == "assistant" for b in blocks(e) if b.get("type") == "tool_use" and b.get("name") == name]


def result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, list):
        return " ".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return str(content or "")


def tool_results(events: list[dict], tool_use_id: str) -> list[dict]:
    return [b for e in events if e.get("type") == "user" for b in blocks(e) if b.get("type") == "tool_result" and b.get("tool_use_id") == tool_use_id]


def assert_tool_refused(events: list[dict], tool: str, reason_pattern: str) -> None:
    uses = tool_uses(events, tool)
    assert uses, f"the model never attempted {tool}"
    refused = [r for use in uses for r in tool_results(events, use["id"]) if r.get("is_error")]
    assert refused, f"no {tool} call was refused by a hook"
    assert any(re.search(reason_pattern, result_text(r), re.IGNORECASE) for r in refused), (
        f"refusal did not carry the hook reason /{reason_pattern}/: {[result_text(r)[:200] for r in refused]}")


def reached_model(events: list[dict], needle: str) -> bool:
    for event in events:
        if event.get("type") in ("assistant", "result"):
            continue
        if event.get("type") == "system" and event.get("subtype") in ("init", None):
            continue
        if needle in json.dumps(event):
            return True
    return False


def git_commit_all(project: Path, message: str) -> None:
    git = ["git", "-c", "user.email=live@example.invalid", "-c", "user.name=Live"]
    subprocess.run([*git, "add", "-A"], cwd=project, check=True)
    subprocess.run([*git, "commit", "-qm", message, "--allow-empty"], cwd=project, check=True)


def write_state(project: Path, *, phase: str, tdd_phase: str | None = None) -> None:
    path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    active = {"id": "ISSUE-1", "phase": phase}
    if tdd_phase:
        active["tdd_phase"] = tdd_phase
    data["work"] = {"active": active}
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def write_issue_file(project: Path, number: int, status: str, directory: str = "roadmap/issues") -> Path:
    folder = project / ".sweetclaude" / "product" / directory
    folder.mkdir(parents=True, exist_ok=True)
    issue_id = f"ISSUE-{number:03d}"
    path = folder / f"{issue_id}-work-item-{number}.md"
    path.write_text(f"---\nid: {issue_id}\ntitle: Work item {number}\nstatus: {status}\n---\n\n# {issue_id}: Work item {number}\n", encoding="utf-8")
    return path


def kanban_at_limit(project: Path, *, phase: str) -> Path:
    write_state(project, phase=phase)
    (project / ".sweetclaude" / "state" / "effective-gates.yaml").write_text(
        yaml.safe_dump({"mode": "kanban", "wip_limit": 3}), encoding="utf-8")
    for number in (1, 2, 3):
        write_issue_file(project, number, "active")
    fourth = write_issue_file(project, 4, "ready")
    git_commit_all(project, "wip state")
    return fourth


def assert_tool_not_refused(events: list[dict], tool: str, reason_pattern: str) -> None:
    uses = tool_uses(events, tool)
    assert uses, f"the model never attempted {tool}"
    refused = [r for use in uses for r in tool_results(events, use["id"]) if r.get("is_error")]
    assert not any(re.search(reason_pattern, result_text(r), re.IGNORECASE) for r in refused), (
        f"a hook refused {tool} with /{reason_pattern}/: {[result_text(r)[:200] for r in refused]}")


def enable_guardian(project: Path) -> None:
    (project / ".sweetclaude" / "state" / "guardian-enabled").write_text("", encoding="utf-8")


@pytest.fixture
def live_project(tmp_path):
    project = make_project(tmp_path).resolve()
    flags = [
        Path(f"/tmp/.sweetclaude-needs-preflight-{md5(str(project))}"),
        Path(f"/tmp/.sweetclaude-bootstrap-ran-{md5(str(project))}"),
    ]
    for flag in flags:
        flag.unlink(missing_ok=True)
    yield project
    for flag in flags:
        flag.unlink(missing_ok=True)


def test_test_guardian_refuses_test_file_write_r070(live_project):
    write_state(live_project, phase="IMPLEMENT", tdd_phase="implementing")
    target = live_project / "tests" / "test_calc.py"
    target.parent.mkdir()
    target.write_text("def test_add():\n    assert 1 + 1 == 2\n", encoding="utf-8")
    original = target.read_text(encoding="utf-8")
    git_commit_all(live_project, "add test")
    events = run_claude(live_project, "Use the Write tool to overwrite tests/test_calc.py with the single line: # changed. Do nothing else.")
    assert_tool_refused(events, "Write", r"immutable|test files")
    assert target.read_text(encoding="utf-8") == original


def test_tdd_prewrite_guardian_refuses_source_write_without_tests_r071(live_project):
    enable_guardian(live_project)
    (live_project / ".sweetclaude" / "state" / "phase.yaml").write_text("phase: IMPLEMENT\n", encoding="utf-8")
    (live_project / "src").mkdir()
    (live_project / "src" / ".gitkeep").write_text("", encoding="utf-8")
    git_commit_all(live_project, "scaffold")
    events = run_claude(live_project, "Use the Write tool to create src/calc.py containing: def add(a, b): return a + b. Do nothing else.")
    assert_tool_refused(events, "Write", r"no test files|tdd")
    assert not (live_project / "src" / "calc.py").exists()


def test_auto_test_runner_runs_tests_and_reports_failure_r072(live_project):
    write_state(live_project, phase="IMPLEMENT", tdd_phase="implementing")
    marker = live_project / "autotest.marker"
    (live_project / ".sweetclaude" / "state" / "project.yaml").write_text(
        f"testing:\n  test_command: echo AUTOTEST_LIVE_SENTINEL; touch {marker}; exit 1\n", encoding="utf-8")
    (live_project / "src").mkdir()
    (live_project / "src" / ".gitkeep").write_text("", encoding="utf-8")
    git_commit_all(live_project, "scaffold")
    events = run_claude(live_project, "Use the Write tool to create src/calc.py containing: def add(a, b): return a + b. Do nothing else.")
    assert (live_project / "src" / "calc.py").exists()
    assert marker.exists(), "configured test command never ran after the source write"
    assert reached_model(events, "AUTOTEST_LIVE_SENTINEL"), "failing test output never reached the model"


def test_wip_limit_refuses_bash_activation_at_limit_r073(live_project):
    fourth = kanban_at_limit(live_project, phase="IMPLEMENT")
    before = fourth.read_text(encoding="utf-8")
    command = f"source {REPO_ROOT}/hooks/sc-artifact.sh && sc_artifact_write ISSUE-004 '{{\"status\":\"active\"}}'"
    events = run_claude(live_project, f"Run this exact shell command with the Bash tool: {command}. Do nothing else.")
    assert_tool_refused(events, "Bash", r"wip limit")
    assert fourth.read_text(encoding="utf-8") == before


def test_wip_limit_refuses_write_of_fourth_active_issue_r077(live_project):
    kanban_at_limit(live_project, phase="PLAN")
    target = live_project / ".sweetclaude" / "product" / "roadmap" / "issues" / "ISSUE-005-fifth.md"
    prompt = ("Use the Write tool to create .sweetclaude/product/roadmap/issues/ISSUE-005-fifth.md with exactly this content:\n"
              "---\nid: ISSUE-005\ntitle: Fifth\nstatus: active\n---\n\n# ISSUE-005: Fifth\n\nDo nothing else.")
    events = run_claude(live_project, prompt)
    assert_tool_refused(events, "Write", r"wip limit")
    assert not target.exists()


def test_preflight_guard_refuses_tool_in_unconfigured_flagged_project_r074(live_project):
    shutil.rmtree(live_project / ".sweetclaude")
    git_commit_all(live_project, "unconfigure")
    Path(f"/tmp/.sweetclaude-needs-preflight-{md5(str(live_project))}").write_text("", encoding="utf-8")
    events = run_claude(live_project, "Run this exact shell command with the Bash tool: echo hello > out.txt. Do nothing else.")
    assert_tool_refused(events, "Bash", r"not configured|sweetclaude")
    assert not (live_project / "out.txt").exists()


def test_phase_dwelling_guard_blocks_stop_on_advancement_language_r075(live_project):
    enable_guardian(live_project)
    events = run_claude(live_project, "Reply with exactly this sentence and nothing else: Draft complete, ready to move on?")
    assert reached_model(events, "PHASE DWELLING GUARD"), "Stop hook block reason never reached the model"


def test_master_preflight_refuses_skill_without_bootstrap_r076(live_project):
    Path(f"/tmp/.sweetclaude-bootstrap-ran-{md5(str(live_project))}").unlink(missing_ok=True)
    events = run_claude(live_project, "Invoke the Skill tool with skill sweetclaude:status. Do nothing else.")
    assert_tool_refused(events, "Skill", r"bootstrap")


def test_artifact_guardian_warns_on_commit_without_blocking_r236(live_project):
    write_state(live_project, phase="implement")
    enable_guardian(live_project)
    git_commit_all(live_project, "state")
    before = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=live_project, capture_output=True, text=True, check=True).stdout.strip()
    events = run_claude(live_project, "Run this exact shell command with the Bash tool: git -c user.email=a@b.c -c user.name=x commit --allow-empty -m guarded. Do nothing else.")
    after = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=live_project, capture_output=True, text=True, check=True).stdout.strip()
    assert int(after) == int(before) + 1, "the warning hook must not block the commit"
    assert reached_model(events, "[Protocol Guardian] WARNING"), "warning never reached the model"


def test_test_guardian_refuses_bash_write_to_test_file_r241(live_project):
    write_state(live_project, phase="IMPLEMENT", tdd_phase="implementing")
    target = live_project / "tests" / "test_calc.py"
    target.parent.mkdir()
    target.write_text("def test_add():\n    assert 1 + 1 == 2\n", encoding="utf-8")
    original = target.read_text(encoding="utf-8")
    git_commit_all(live_project, "add test")
    events = run_claude(live_project, "Run this exact shell command with the Bash tool: echo '# changed' > tests/test_calc.py. Do nothing else.")
    assert_tool_refused(events, "Bash", r"immutable|test files")
    assert target.read_text(encoding="utf-8") == original


def test_preflight_guard_allows_the_configure_skill_r244(live_project):
    shutil.rmtree(live_project / ".sweetclaude")
    git_commit_all(live_project, "unconfigure")
    Path(f"/tmp/.sweetclaude-needs-preflight-{md5(str(live_project))}").write_text("", encoding="utf-8")
    events = run_claude(live_project, "Invoke the Skill tool with skill sweetclaude:configure. Do nothing else.")
    assert_tool_not_refused(events, "Skill", r"not configured|preflight")


def agile_gates_state(project: Path, *, sprint_active: bool) -> None:
    write_state(project, phase="IMPLEMENT")
    gates = [
        {"phase": "IMPLEMENT", "condition": "no_active_sprint", "action": "block",
         "message": "No active sprint. Run /sweetclaude:project-sprints start to activate a sprint."},
        {"phase": "SHIP", "condition": "sprint_complete", "action": "prompt",
         "message": "All sprint issues are done. Run sprint close before shipping."},
    ]
    (project / ".sweetclaude" / "state" / "effective-gates.yaml").write_text(
        yaml.safe_dump({"mode": "agile", "default_tdd_level": 2, "blocked_skills": [], "gates": gates}),
        encoding="utf-8")
    if sprint_active:
        sprints = project / ".sweetclaude" / "product" / "sprints"
        sprints.mkdir(parents=True, exist_ok=True)
        (sprints / "SP-001-sprint-one.md").write_text(
            "---\nid: SP-001\ntitle: Sprint one\nstatus: active\n---\n\n# SP-001: Sprint one\n",
            encoding="utf-8")


def test_master_preflight_denies_build_without_active_sprint_r092(live_project):
    agile_gates_state(live_project, sprint_active=False)
    events = run_claude(live_project, "Invoke the Skill tool with skill sweetclaude:build. Do nothing else.")
    assert_tool_refused(events, "Skill", r"No active sprint")


def test_library_load_implement_allowed_with_active_sprint_r094(live_project):
    agile_gates_state(live_project, sprint_active=True)
    events = run_claude(
        live_project,
        "Invoke the Skill tool with skill sweetclaude:library-load and args: code-feature implement the login form. Do nothing else.")
    assert_tool_not_refused(events, "Skill", r"No active sprint")


def test_library_load_implement_denied_without_active_sprint_r094(live_project):
    agile_gates_state(live_project, sprint_active=False)
    events = run_claude(
        live_project,
        "Invoke the Skill tool with skill sweetclaude:library-load and args: code-feature implement the login form. Do nothing else.")
    assert_tool_refused(events, "Skill", r"No active sprint")


def kanban_gates_state(project: Path) -> None:
    write_state(project, phase="PLAN")
    gates = [
        {"phase": "IMPLEMENT", "condition": "wip_limit_reached", "action": "block",
         "message": "WIP limit reached ({current}/{limit} items in_progress). "
                    "Complete or move an item before starting new work."},
    ]
    (project / ".sweetclaude" / "state" / "effective-gates.yaml").write_text(
        yaml.safe_dump({"mode": "kanban", "default_tdd_level": 1,
                        "blocked_skills": ["project-sprints", "product-sprint-plan"],
                        "gates": gates}),
        encoding="utf-8")


def test_library_load_sprint_plan_denied_in_kanban_r089(live_project):
    kanban_gates_state(live_project)
    events = run_claude(
        live_project,
        "Invoke the Skill tool with skill sweetclaude:library-load and args: "
        "product-sprint-plan plan the next sprint. Do nothing else.")
    assert_tool_refused(events, "Skill", r"disabled in kanban mode")


def shape_up_gates_state(project: Path, *, approved: bool) -> None:
    state = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    data = yaml.safe_load(state.read_text(encoding="utf-8"))
    data["work"] = {"active": {"id": "ISSUE-001", "phase": "IMPLEMENT"}}
    state.write_text(yaml.safe_dump(data), encoding="utf-8")
    gates = [
        {"phase": "IMPLEMENT", "requires": "betting_table_approved", "action": "block",
         "message": "Work must be pitched and bet before implementation begins. "
                    "Run /sweetclaude:project-issues to create issues from a pitch."},
    ]
    (project / ".sweetclaude" / "state" / "effective-gates.yaml").write_text(
        yaml.safe_dump({"mode": "shape_up", "default_tdd_level": 2,
                        "blocked_skills": [], "gates": gates}),
        encoding="utf-8")
    folder = project / ".sweetclaude" / "product" / "roadmap" / "issues"
    folder.mkdir(parents=True, exist_ok=True)
    approved_line = "betting_table_approved: true\n" if approved else ""
    (folder / "ISSUE-001-work-item-1.md").write_text(
        f"---\nid: ISSUE-001\ntitle: Work item 1\nstatus: active\n{approved_line}---\n\n"
        "# ISSUE-001: Work item 1\n", encoding="utf-8")
    git_commit_all(project, "shape up state")


def test_library_load_implement_denied_without_betting_table_approval_r091(live_project):
    shape_up_gates_state(live_project, approved=False)
    events = run_claude(
        live_project,
        "Invoke the Skill tool with skill sweetclaude:library-load and args: "
        "code-feature implement the login form. Do nothing else.")
    assert_tool_refused(events, "Skill", r"pitched and bet")


def test_library_load_implement_allowed_with_betting_table_approval_r091(live_project):
    shape_up_gates_state(live_project, approved=True)
    events = run_claude(
        live_project,
        "Invoke the Skill tool with skill sweetclaude:library-load and args: "
        "code-feature implement the login form. Do nothing else.")
    assert_tool_not_refused(events, "Skill", r"pitched and bet")


def test_deploy_ship_denied_without_ship_no_ship_decision_r093(live_project):
    shape_up_gates_state(live_project, approved=True)
    gates_path = live_project / ".sweetclaude" / "state" / "effective-gates.yaml"
    gates = yaml.safe_load(gates_path.read_text(encoding="utf-8"))
    gates["gates"].append(
        {"phase": "VERIFY", "condition": "ship_no_ship_decision", "action": "required",
         "message": "Ship/no-ship decision required. Did the core outcome land within appetite?"})
    gates_path.write_text(yaml.safe_dump(gates), encoding="utf-8")
    cycles = live_project / ".sweetclaude" / "product" / "cycles"
    cycles.mkdir(parents=True, exist_ok=True)
    (cycles / "CYC-001-cycle-1.md").write_text(
        "---\nid: CYC-001\ntitle: Cycle 1\ntype: cycle\nstatus: active\n---\n\n"
        "# CYC-001: Cycle 1\n", encoding="utf-8")
    git_commit_all(live_project, "shape up cycle state")
    events = run_claude(
        live_project,
        "Invoke the Skill tool with skill sweetclaude:library-load and args: "
        "deploy-ship ship the milestone. Do nothing else.")
    assert_tool_refused(events, "Skill", r"Ship/no-ship decision required")


def test_tdd_commit_gate_refuses_implementation_commit_without_red_r251(live_project):
    write_state(live_project, phase="IMPLEMENT", tdd_phase="implementing")
    (live_project / "src").mkdir()
    (live_project / "src" / ".gitkeep").write_text("", encoding="utf-8")
    git_commit_all(live_project, "scaffold")
    subprocess.run(["git", "checkout", "-q", "-b", "ISSUE-001/add-calc"], cwd=live_project,
                   check=True, capture_output=True, timeout=30)
    (live_project / "src" / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    command = ("git -c user.email=a@b.c -c user.name=x add src/calc.py && "
               "git -c user.email=a@b.c -c user.name=x commit -m 'feat: adder'")
    events = run_claude(live_project, f"Run this exact shell command with the Bash tool: {command}. Do nothing else.")
    assert_tool_refused(events, "Bash", r"test: RED")
