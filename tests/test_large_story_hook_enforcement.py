"""TASK-C6: real-path regression harness for large-story hook enforcement.

Replays the WLF-TASK008-2026-06-06 failure sequence against the REAL artifacts
that run in a live session: the hook shell scripts (fed genuine hook stdin
JSON) and the controller CLI (invoked as a subprocess, exactly as the skill
invokes it). No controller function is called in-process on the main flow.

Every condition in the failure report's Recurrence Policy is asserted
impossible:
- app/code artifacts without a non-empty implementation record
- reaching VERIFY without writing a success criteria ledger
- reaching SHIP without a valid completion ledger
- rendering final status without controller output
- contradictory phase state going undetected
- completion claims based on artifacts alone
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from success_criteria_contracts import compute_success_criteria_contract_hash

CONTROLLER = SCRIPTS_DIR / "large_story_controller.py"
CONTRACTS_CLI = SCRIPTS_DIR / "success_criteria_contracts.py"
GATE_HOOK = REPO_ROOT / "hooks" / "large-story-gate.sh"
EVIDENCE_HOOK = REPO_ROOT / "hooks" / "large-story-evidence.sh"
STOP_HOOK = REPO_ROOT / "hooks" / "large-story-stop-guard.sh"

HOOK_PATH = f"{os.path.dirname(sys.executable)}:/usr/bin:/bin:/usr/local/bin"

CRUD_SQLITE_PROMPT = (
    "/sweetclaude:go build a prototype CRUD-style web application "
    "with no authentication, using SQLite for the data."
)
STORY_ID = "WI-001"


def _crud_contract() -> dict:
    def criterion(num: int, outcome: str, statement: str, predicate: str, command: str) -> dict:
        return {
            "id": f"SC-00{num}",
            "outcome_id": outcome,
            "statement": statement,
            "binary_predicate": predicate,
            "measurement_type": "command",
            "measurement_command": command,
            "measurement_procedure": f"Measure: {predicate}.",
            "evidence_artifact": f".sweetclaude/reports/large-story/{STORY_ID}/evidence/SC-00{num}.json",
            "evidence_owner": "controller",
            "pass_condition": predicate,
            "fail_condition": f"not ({predicate})",
            "allowed_phase_to_measure": "implementation",
            "amendment_policy": "human_approved_only",
            "backlog_routing": "Backlog any new concern.",
        }

    contract = {
        "story_id": STORY_ID,
        "story_title": "CRUD SQLite fresh disposable regression",
        "story_objective": CRUD_SQLITE_PROMPT,
        "expected_outcomes": [
            {"id": "OUTCOME-001", "statement": "The prototype serves a web index."},
            {"id": "OUTCOME-002", "statement": "The prototype persists rows in SQLite."},
        ],
        "non_goals": [{"id": "NONGOAL-001", "statement": "Authentication is excluded."}],
        "success_criteria": [
            criterion(1, "OUTCOME-001", "The index route returns HTTP 200.", "GET / returns 200", "test -s app.py"),
            criterion(2, "OUTCOME-002", "The SQLite database file exists.", "models.db exists", "test -s models.db"),
        ],
        "contract_freeze": {
            "frozen_at": "2026-06-06T12:00:00Z",
            "frozen_by": "test",
            "contract_hash": "",
        },
    }
    contract["contract_freeze"]["contract_hash"] = compute_success_criteria_contract_hash(contract)
    return contract


def _env(project: Path) -> dict:
    return {
        "PATH": HOOK_PATH,
        "CLAUDE_PROJECT_DIR": str(project),
        "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT),
        "HOME": str(project),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def _controller(project: Path, *args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(CONTROLLER), "--project-dir", str(project), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT / "scripts"),
    )
    assert result.stdout.strip(), f"controller produced no output: {result.stderr}"
    return json.loads(result.stdout)


def _hook(hook: Path, project: Path, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
        env=_env(project),
        cwd=str(project),
    )


def _tool_payload(project: Path, event: str, tool: str, **tool_input) -> dict:
    payload = {
        "session_id": "regression-session",
        "transcript_path": str(project / "transcript.jsonl"),
        "cwd": str(project),
        "permission_mode": "default",
        "hook_event_name": event,
        "tool_name": tool,
        "tool_input": tool_input,
    }
    if event == "PostToolUse":
        payload["tool_response"] = {"success": True}
    return payload


def _gate_denies(project: Path, tool: str, **tool_input) -> bool:
    result = _hook(GATE_HOOK, project, _tool_payload(project, "PreToolUse", tool, **tool_input))
    if not result.stdout.strip():
        return False
    decision = json.loads(result.stdout).get("hookSpecificOutput") or {}
    return decision.get("permissionDecision") == "deny"


def _simulated_agent_write(project: Path, rel_path: str, content: str) -> bool:
    """Write a file the way the live session would: gate first, write only if
    allowed, then fire the evidence hook. Returns True if the write happened."""
    if _gate_denies(project, "Write", file_path=rel_path, content=content):
        return False
    target = project / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _hook(EVIDENCE_HOOK, project, _tool_payload(project, "PostToolUse", "Write", file_path=rel_path, content=content))
    return True


def _simulated_agent_bash(project: Path, command: str) -> bool:
    if _gate_denies(project, "Bash", command=command):
        return False
    _hook(EVIDENCE_HOOK, project, _tool_payload(project, "PostToolUse", "Bash", command=command))
    return True


def _stop_attempt(project: Path) -> dict | None:
    result = _hook(STOP_HOOK, project, {
        "session_id": "regression-session",
        "transcript_path": str(project / "transcript.jsonl"),
        "cwd": str(project),
        "permission_mode": "default",
        "hook_event_name": "Stop",
        "stop_hook_active": False,
    })
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def _verify_enforcement_cli(project: Path) -> None:
    """Mark enforcement verified without a live gate (control present, canary
    absent = simulated active gate), for tests not exercising the real hook."""
    _controller(project, "enforcement-probe", "--arm", "--workflow-id", STORY_ID)
    (project / ".sweetclaude" / ".enforcement-control").write_text("ok\n", encoding="utf-8")
    _controller(project, "enforcement-probe", "--check", "--workflow-id", STORY_ID)


def _write_contract(project: Path) -> None:
    contract_path = project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(yaml.safe_dump(_crud_contract(), sort_keys=False), encoding="utf-8")


def test_full_fresh_disposable_sequence_with_real_hooks_and_cli(tmp_path):
    project = tmp_path / "fresh-disposable"
    project.mkdir()
    app_files = ["app.py", "templates/index.html", "models.db"]

    # --- DEFINE: contract first; app writes physically denied -----------------
    backlog_dir = project / "docs" / "product" / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    (backlog_dir / f"{STORY_ID}-test.md").write_text(
        f"---\nid: {STORY_ID}\nstatus: new\n---\nTest.\n", encoding="utf-8",
    )
    _write_contract(project)
    init = _controller(project, "init", "--workflow-id", STORY_ID)
    assert init["ok"], init

    for rel in app_files:
        assert not _simulated_agent_write(project, rel, "premature"), rel
        assert not (project / rel).exists()

    # State writes denied in every phase (single-writer rule).
    assert _gate_denies(project, "Write", file_path=f".sweetclaude/state/workflows/{STORY_ID}.yaml", content="x")
    assert _gate_denies(project, "Bash", command="echo '{}' > .sweetclaude/reports/success-criteria-ledger.json")

    # --- DESIGN / PLAN: still no app writes ------------------------------------
    assert _controller(project, "design", "--workflow-id", STORY_ID, "--design-summary", "Server-rendered CRUD over SQLite.")["ok"]
    assert not _simulated_agent_write(project, "app.py", "premature")
    assert _controller(project, "plan", "--workflow-id", STORY_ID, "--plan-summary", "Index route, persistence, create flow.")["ok"]
    assert not _simulated_agent_write(project, "app.py", "premature")

    # --- Stop attempt mid-story is blocked with controller status --------------
    stop = _stop_attempt(project)
    assert stop is not None and stop["decision"] == "block"
    assert STORY_ID in stop["reason"]

    # --- Enforcement self-check via the REAL gate -----------------------------
    # IMPLEMENT is blocked until the gate is verified live.
    blocked = _controller(project, "implement", "--workflow-id", STORY_ID, "--implementation-summary", "premature")
    assert blocked["ok"] is False and blocked["code"] == "blocked_enforcement_unverified"
    assert _controller(project, "enforcement-probe", "--arm", "--workflow-id", STORY_ID)["ok"]
    # control write (gate allows) lands; canary write (gate denies) does not.
    assert _simulated_agent_write(project, ".sweetclaude/.enforcement-control", "ok")
    assert not _simulated_agent_write(project, ".sweetclaude/state/workflows/.enforcement-canary", "leak")
    probe = _controller(project, "enforcement-probe", "--check", "--workflow-id", STORY_ID)
    assert probe["verified"] is True, probe

    # --- IMPLEMENT: writes allowed AND observed --------------------------------
    assert _controller(project, "implement", "--workflow-id", STORY_ID, "--implementation-summary", "Build CRUD app files.")["ok"]
    for rel in app_files:
        assert _simulated_agent_write(project, rel, f"content of {rel}"), rel
    assert _simulated_agent_bash(project, "python3 seed.py")

    evidence_log = project / ".sweetclaude" / "reports" / "large-story" / STORY_ID / "implementation" / "evidence.jsonl"
    assert evidence_log.exists()
    observed = [json.loads(line) for line in evidence_log.read_text(encoding="utf-8").splitlines()]
    assert {entry.get("file_path") for entry in observed if entry.get("file_path")} == set(app_files)

    # --- Premature completion attempts fail closed -----------------------------
    finalize_early = _controller(project, "finalize", "--workflow-id", STORY_ID)
    assert finalize_early["ok"] is False
    assert finalize_early["completion_claim_allowed"] is False
    ledger = project / ".sweetclaude" / "reports" / "success-criteria-ledger.json"
    assert not ledger.exists()

    # --- VERIFY: canonical ledger written; record derived from observation -----
    criterion_results = json.dumps({
        "SC-001": {"status": "pass", "measured_command": "curl -s -o /dev/null -w '%{http_code}' http://localhost:5017/", "observed_output": "200"},
        "SC-002": {"status": "pass", "measured_command": "test -s models.db", "observed_output": "models.db exists"},
    })
    verify = _controller(project, "verify", "--workflow-id", STORY_ID, "--criterion-result-json", criterion_results)
    assert verify["ok"], verify
    assert ledger.exists()
    ledger_data = json.loads(ledger.read_text(encoding="utf-8"))
    assert ledger_data["all_success_criteria_passed"] is True
    assert {entry["id"] for entry in ledger_data["criteria"]} == {"SC-001", "SC-002"}

    record_text = (project / ".sweetclaude" / "reports" / "large-story" / STORY_ID / "implementation" / "implementation-record.md").read_text(encoding="utf-8")
    for rel in app_files:
        assert rel in record_text
    assert "python3 seed.py" in record_text
    touched_section = record_text.split("## Touched Files")[1].split("##")[0]
    assert "none recorded" not in touched_section

    # App writes are closed again after IMPLEMENT.
    assert not _simulated_agent_write(project, "extra.py", "late change")

    # Stop is still blocked before closeout.
    stop = _stop_attempt(project)
    assert stop is not None and stop["decision"] == "block"

    # --- SHIP: closeout, completion allowed, stop allowed -----------------------
    ship = _controller(project, "ship", "--workflow-id", STORY_ID)
    assert ship["ok"], ship
    closeout = project / ".sweetclaude" / "reports" / "large-story" / STORY_ID / "ship" / "closeout.json"
    assert closeout.exists()

    finalize = _controller(project, "finalize", "--workflow-id", STORY_ID)
    assert finalize["ok"] is True
    assert finalize["completion_claim_allowed"] is True

    status = _controller(project, "render-status", "--workflow-id", STORY_ID)
    assert status["ok"] is True
    assert status["generated_by"] == "large_story_controller"

    assert _stop_attempt(project) is None


def _create_backlog_file(project: Path, story_id: str) -> None:
    backlog_dir = project / "docs" / "product" / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    (backlog_dir / f"{story_id}-test.md").write_text(
        f"---\nid: {story_id}\nstatus: new\n---\nTest.\n", encoding="utf-8",
    )


def test_task008_artifact_state_is_unreachable(tmp_path):
    """The exact observed TASK-008 end state (app artifacts + DEFINE/VERIFY
    state contradiction + no ledger) cannot be reproduced through the gated
    path, and if produced by external tampering it is detected, not masked."""
    project = tmp_path / "tampered"
    project.mkdir()
    _create_backlog_file(project, STORY_ID)
    _write_contract(project)
    assert _controller(project, "init", "--workflow-id", STORY_ID)["ok"]
    assert _controller(project, "design", "--workflow-id", STORY_ID, "--design-summary", "d")["ok"]

    # Tamper phase.yaml the way the failed run left it (workflow file DEFINE-era
    # phase vs phase.yaml VERIFY).
    phase_path = project / ".sweetclaude" / "state" / "phase.yaml"
    data = yaml.safe_load(phase_path.read_text(encoding="utf-8"))
    data["active_work_item"]["phase"] = "VERIFY"
    phase_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    status = _controller(project, "render-status", "--workflow-id", STORY_ID)
    assert status["ok"] is False
    assert status["status"] == "blocked_state_inconsistent"

    finalize = _controller(project, "finalize", "--workflow-id", STORY_ID)
    assert finalize["ok"] is False
    assert finalize["code"] == "blocked_state_inconsistent"


def test_verify_without_observed_evidence_is_blocked_via_cli(tmp_path):
    """Skipping the evidence hook (e.g. hooks disabled) fails closed at VERIFY."""
    project = tmp_path / "no-evidence"
    project.mkdir()
    _create_backlog_file(project, STORY_ID)
    _write_contract(project)
    assert _controller(project, "init", "--workflow-id", STORY_ID)["ok"]
    assert _controller(project, "design", "--workflow-id", STORY_ID, "--design-summary", "d")["ok"]
    assert _controller(project, "plan", "--workflow-id", STORY_ID, "--plan-summary", "p")["ok"]
    _verify_enforcement_cli(project)
    assert _controller(project, "implement", "--workflow-id", STORY_ID, "--implementation-summary", "i")["ok"]

    (project / "app.py").write_text("written without evidence hook\n", encoding="utf-8")

    verify = _controller(project, "verify", "--workflow-id", STORY_ID)
    assert verify["ok"] is False
    assert verify["code"] == "blocked_implementation_evidence_empty"
    assert not (project / ".sweetclaude" / "reports" / "success-criteria-ledger.json").exists()


def test_contract_requiring_terminal_review_is_rejected_at_define_exit(tmp_path):
    project = tmp_path / "bad-contract"
    project.mkdir()
    contract = _crud_contract()
    contract["success_criteria"][0]["allowed_phase_to_measure"] = "terminal-review"
    contract["contract_freeze"]["contract_hash"] = compute_success_criteria_contract_hash(contract)
    contract_path = project / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CONTRACTS_CLI), "validate-workflow", "--project-dir", str(project), "--stage", "define-exit"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT / "scripts"),
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "terminal-review" in str(payload)
