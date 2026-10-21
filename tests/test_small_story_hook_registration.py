"""Registration regression tests for small-story hooks.

Mirrors test_large_story_hook_registration.py — proves hooks.json wires
the small-story gate, evidence, and stop-guard hooks to the correct events
with correct matchers, and that the registered commands actually fire.
"""
import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from small_story_controller import (
    arm_enforcement_probe,
    check_enforcement_probe,
    enter_design_phase,
    enter_implement_phase,
    enter_plan_phase,
    init_workflow,
)
from success_criteria_contracts import compute_success_criteria_contract_hash

HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
MANIFEST_JSON = REPO_ROOT / "hooks" / "hooks-manifest.json"
HOOK_PATH = f"{os.path.dirname(sys.executable)}:/usr/bin:/bin:/usr/local/bin"

GATE = "small-story-gate.sh"
EVIDENCE = "small-story-evidence.sh"
STOP = "small-story-stop-guard.sh"


def _config():
    return json.loads(HOOKS_JSON.read_text(encoding="utf-8"))


def _resolve(command: str) -> str:
    return command.replace("${CLAUDE_PLUGIN_ROOT}", str(REPO_ROOT))


def _entries(config, event):
    for entry in config.get("hooks", {}).get(event, []):
        matcher = entry.get("matcher", "")
        for h in entry.get("hooks", []):
            yield matcher, _resolve(h.get("command", ""))


def _matcher_matches(matcher: str, tool: str) -> bool:
    if matcher in ("", "*", ".*"):
        return True
    if all(part.isalnum() or part == "" for part in matcher.split("|")):
        return tool in matcher.split("|")
    return re.fullmatch(matcher, tool) is not None


def _registered(config, event, script: str, required_tools=()) -> bool:
    for matcher, command in _entries(config, event):
        if command.endswith(script):
            return all(_matcher_matches(matcher, t) for t in required_tools)
    return False


# --- registration assertions --------------------------------------------------


def test_gate_registered_pretooluse_for_all_modifying_tools():
    config = _config()
    assert _registered(config, "PreToolUse", GATE, ("Write", "Edit", "NotebookEdit", "Bash"))


def test_evidence_registered_posttooluse_for_modifying_tools():
    config = _config()
    assert _registered(config, "PostToolUse", EVIDENCE, ("Write", "Edit", "Bash"))


def test_stop_guard_registered_stop():
    config = _config()
    assert _registered(config, "Stop", STOP)


def test_manifest_lists_all_small_story_hooks():
    files = {h.get("file") for h in json.loads(MANIFEST_JSON.read_text(encoding="utf-8")).get("hooks", [])}
    assert {GATE, EVIDENCE, STOP} <= files


def test_registration_detection_has_teeth():
    config = _config()
    assert _registered(config, "PreToolUse", GATE, ("Write",))
    mutated = copy.deepcopy(config)
    mutated["hooks"]["PreToolUse"] = [
        e for e in mutated["hooks"]["PreToolUse"]
        if not any(GATE in h.get("command", "") for h in e.get("hooks", []))
    ]
    assert not _registered(mutated, "PreToolUse", GATE, ("Write",))


# --- the registered command actually fires ------------------------------------


def _contract(story_id="STORY-001"):
    c = {
        "story_id": story_id,
        "story_title": "Registration regression",
        "story_objective": "Prove registered hook commands fire.",
        "expected_outcomes": [{"id": "OUTCOME-001", "statement": "Hooks fire."}],
        "non_goals": [{"id": "NONGOAL-001", "statement": "No terminal review."}],
        "success_criteria": [{
            "id": "SC-001",
            "outcome_id": "OUTCOME-001",
            "statement": "The probe check command exits zero.",
            "binary_predicate": "probe measurement command exits with code 0",
            "measurement_type": "command",
            "measurement_command": "true",
            "measurement_procedure": "Run the probe command; record the exit code.",
            "evidence_artifact": f".sweetclaude/reports/small-story/{story_id}/evidence/SC-001.json",
            "evidence_owner": "controller",
            "pass_condition": "Exit code equals 0",
            "fail_condition": "Exit code differs from 0",
            "allowed_phase_to_measure": "implementation",
            "amendment_policy": "human_approved_only",
            "backlog_routing": "Backlog any new concern.",
        }],
        "contract_freeze": {"frozen_at": "2026-06-07T00:00:00Z", "frozen_by": "test", "contract_hash": ""},
    }
    c["contract_freeze"]["contract_hash"] = compute_success_criteria_contract_hash(c)
    return c


def _project(tmp_path):
    backlog_dir = tmp_path / "docs" / "product" / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    (backlog_dir / "STORY-001-test.md").write_text(
        "---\nid: STORY-001\nstatus: new\n---\nTest.\n", encoding="utf-8",
    )
    cp = tmp_path / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(yaml.safe_dump(_contract(), sort_keys=False), encoding="utf-8")
    assert init_workflow(project_dir=tmp_path, workflow_id="STORY-001")["ok"]
    return tmp_path


def _run_registered(event, script, project, payload):
    command = next(c for m, c in _entries(_config(), event) if c.endswith(script))
    return subprocess.run(
        ["bash", command],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=30,
        env={"PATH": HOOK_PATH, "CLAUDE_PROJECT_DIR": str(project),
             "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT), "HOME": str(project)},
        cwd=str(project),
    )


def _pre(project, tool, **ti):
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": str(project),
            "permission_mode": "default", "tool_input": ti}


def test_registered_gate_command_denies_define_write(tmp_path):
    project = _project(tmp_path)
    result = _run_registered("PreToolUse", GATE, project, _pre(project, "Write", file_path="app.py", content="x"))
    decision = json.loads(result.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"


def test_registered_stop_command_blocks_nonterminal(tmp_path):
    project = _project(tmp_path)
    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="d")
    payload = {"hook_event_name": "Stop", "cwd": str(project), "permission_mode": "default",
               "stop_hook_active": False}
    result = _run_registered("Stop", STOP, project, payload)
    assert json.loads(result.stdout)["decision"] == "block"


def test_registered_evidence_command_records_in_implement(tmp_path):
    project = _project(tmp_path)
    enter_design_phase(project_dir=project, workflow_id="STORY-001", design_summary="d")
    enter_plan_phase(project_dir=project, workflow_id="STORY-001", plan_summary="p")
    arm_enforcement_probe(project_dir=project, workflow_id="STORY-001")
    (project / ".sweetclaude" / ".enforcement-control").write_text("ok\n", encoding="utf-8")
    check_enforcement_probe(project_dir=project, workflow_id="STORY-001")
    assert enter_implement_phase(project_dir=project, workflow_id="STORY-001", implementation_summary="i")["ok"]
    payload = {"hook_event_name": "PostToolUse", "tool_name": "Write", "cwd": str(project),
               "permission_mode": "default", "tool_input": {"file_path": "app.py", "content": "x"},
               "tool_response": {"success": True}}
    _run_registered("PostToolUse", EVIDENCE, project, payload)
    log = project / ".sweetclaude" / "reports" / "small-story" / "STORY-001" / "implementation" / "evidence.jsonl"
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(e.get("file_path") == "app.py" for e in entries)
