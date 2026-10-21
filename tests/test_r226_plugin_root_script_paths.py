import importlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from success_criteria_contracts import compute_success_criteria_contract_hash

SKILL_ROOTS = [REPO_ROOT / "skills", REPO_ROOT / "skill-library"]

BARE_COMMAND = re.compile(r"\b(?:python3?|bash|sh|source)\s+['\"]?(?:\./)?scripts/")
BARE_FENCED_LINE = re.compile(r"^\s*(?:\$\s*)?(?:\./)?scripts/[\w./-]+\.(?:py|sh)\b")
BARE_SCRIPT_PATH = re.compile(r"(?<![\w/}])scripts/[\w./-]+\.(?:py|sh)")

CONTROLLERS = ["large_story_controller", "small_story_controller"]


def _skill_files() -> list[Path]:
    files = []
    for root in SKILL_ROOTS:
        files.extend(sorted(root.rglob("*.md")))
    return files


def _bare_command_lines(path: Path) -> list[str]:
    offenders = []
    in_fence = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if BARE_COMMAND.search(line) or (in_fence and BARE_FENCED_LINE.search(line)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{number}: {line.strip()}")
    return offenders


class TestR226SkillsUsePluginRootPaths:
    def test_no_skill_tells_the_model_to_run_a_bare_scripts_path(self):
        offenders = []
        for path in _skill_files():
            offenders.extend(_bare_command_lines(path))

        assert offenders == [], "bare scripts/ commands in skills:\n" + "\n".join(offenders)

    def test_large_story_skill_ship_command_resolves_from_plugin_root(self):
        text = (REPO_ROOT / "skill-library" / "build" / "large-story" / "SKILL.md").read_text(encoding="utf-8")
        ship_lines = [line for line in text.splitlines() if "large_story_controller.py" in line and " ship" in line]

        assert ship_lines
        for line in ship_lines:
            assert "${CLAUDE_PLUGIN_ROOT}/scripts/large_story_controller.py" in line, line

    def test_go_skill_controller_route_commands_resolve_from_plugin_root(self):
        text = (REPO_ROOT / "skills" / "go" / "SKILL.md").read_text(encoding="utf-8")
        for controller in ("large_story_controller.py", "small_story_controller.py"):
            lines = [line for line in text.splitlines() if controller in line and "route" in line]
            assert lines
            for line in lines:
                assert f"${{CLAUDE_PLUGIN_ROOT}}/scripts/{controller}" in line, line


def _contract(story_id: str) -> dict:
    criterion = {
        "id": "SC-001",
        "outcome_id": "OUTCOME-001",
        "statement": "The completion validator returns status success.",
        "binary_predicate": "completion validator returns status success",
        "measurement_type": "schema_check",
        "measurement_procedure": "Run completion validator.",
        "evidence_artifact": f".sweetclaude/reports/story/{story_id}/evidence/SC-001.json",
        "evidence_owner": "controller",
        "pass_condition": "validator status equals success",
        "fail_condition": "validator status does not equal success",
        "allowed_phase_to_measure": "implementation",
        "amendment_policy": "human_approved_only",
        "backlog_routing": "Backlog any new concern.",
    }
    contract = {
        "story_id": story_id,
        "story_title": "R-226 controller message test",
        "story_objective": "Controller messages resolve from the plugin root.",
        "expected_outcomes": [{"id": "OUTCOME-001", "statement": "Messages are runnable."}],
        "non_goals": [{"id": "NONGOAL-001", "statement": "Nothing else."}],
        "success_criteria": [criterion],
        "contract_freeze": {"frozen_at": "2026-06-06T12:00:00Z", "frozen_by": "test", "contract_hash": ""},
    }
    contract["contract_freeze"]["contract_hash"] = compute_success_criteria_contract_hash(contract)
    return contract


def _implementing_project(module, tmp_path: Path, story_id: str = "STORY-001") -> Path:
    backlog = tmp_path / "docs" / "product" / "backlog"
    backlog.mkdir(parents=True, exist_ok=True)
    (backlog / f"{story_id}-test.md").write_text(
        f"---\nid: {story_id}\nstatus: new\n---\nTest backlog item.\n", encoding="utf-8"
    )
    contract_path = tmp_path / ".sweetclaude" / "contracts" / "success-criteria-contract.yaml"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(yaml.safe_dump(_contract(story_id), sort_keys=False), encoding="utf-8")
    assert module.init_workflow(project_dir=tmp_path, workflow_id=story_id)["ok"]
    assert module.enter_design_phase(project_dir=tmp_path, workflow_id=story_id, design_summary="d")["ok"]
    assert module.enter_plan_phase(project_dir=tmp_path, workflow_id=story_id, plan_summary="p")["ok"]
    module.arm_enforcement_probe(project_dir=tmp_path, workflow_id=story_id)
    (tmp_path / ".sweetclaude" / ".enforcement-control").write_text("ok\n", encoding="utf-8")
    module.check_enforcement_probe(project_dir=tmp_path, workflow_id=story_id)
    assert module.enter_implement_phase(project_dir=tmp_path, workflow_id=story_id, implementation_summary="i")["ok"]
    return tmp_path


def _controller_messages(module, project: Path) -> dict[str, str]:
    messages = {
        "contract-amendment": module.CONTRACT_AMENDMENT_MESSAGE,
        "write-phase-yaml": module.gate_tool_use(
            project_dir=project, tool="Write", file_path=".sweetclaude/state/phase.yaml"
        )["reason"],
        "bash-phase-yaml": module.gate_tool_use(
            project_dir=project, tool="Bash", command="echo x > .sweetclaude/state/phase.yaml"
        )["reason"],
    }
    workflows = project / ".sweetclaude" / "state" / "workflows"
    (workflows / "BROKEN.yaml").write_text("{unclosed: [", encoding="utf-8")
    messages["unreadable-state"] = module.gate_tool_use(
        project_dir=project, tool="Write", file_path="app.py"
    )["reason"]
    (workflows / "BROKEN.yaml").unlink()
    return messages


@pytest.mark.parametrize("controller", CONTROLLERS)
class TestR226ControllerMessagesUsePluginRootPaths:
    def test_no_controller_message_names_a_bare_scripts_path(self, controller, tmp_path):
        module = importlib.import_module(controller)
        project = _implementing_project(module, tmp_path)

        offenders = {
            name: message
            for name, message in _controller_messages(module, project).items()
            if BARE_SCRIPT_PATH.search(message)
        }

        assert offenders == {}

    def test_emitted_ship_command_runs_from_a_project_without_scripts_dir(self, controller, tmp_path):
        module = importlib.import_module(controller)
        project = _implementing_project(module, tmp_path)
        reason = module.gate_tool_use(
            project_dir=project, tool="Write", file_path=".sweetclaude/state/phase.yaml"
        )["reason"]

        match = re.search(r"`(python3 [^`]*\bship\b[^`]*)`", reason)
        assert match, reason
        command = match.group(1).replace("<id>", "STORY-001")
        assert "${CLAUDE_PLUGIN_ROOT}/scripts/" in command or "python3 /" in command, command
        assert not (project / "scripts").exists()

        env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)}
        result = subprocess.run(
            command, shell=True, cwd=project, env=env, capture_output=True, text=True, check=False
        )

        assert "can't open file" not in result.stderr, result.stderr
        assert "No such file" not in result.stderr, result.stderr
