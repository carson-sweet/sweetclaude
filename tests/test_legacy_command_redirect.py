from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "legacy-command-redirect.sh"


def run(prompt: str, cwd: Path) -> dict | None:
    result = subprocess.run(["bash", str(HOOK)], cwd=cwd, input=json.dumps({"prompt": prompt, "hook_event_name": "UserPromptSubmit"}), capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    out = result.stdout.strip()
    return json.loads(out) if out else None


def test_removed_workflow_command_names_its_replacement(tmp_path):
    payload = run("/sweetclaude:doctor", tmp_path)
    assert "/sweetclaude:configure doctor" in payload["systemMessage"]
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "sweetclaude:configure" in context
    assert "doctor" in context


def test_arguments_are_carried_into_the_replacement(tmp_path):
    payload = run("/sweetclaude:code-feature add shift swaps", tmp_path)
    assert "/sweetclaude:build code-feature" in payload["systemMessage"]
    assert "code-feature add shift swaps" in payload["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize("command", ["go", "plan", "design", "build", "maintain", "configure", "utils", "status", "help"])
def test_tier_one_commands_pass_through(tmp_path, command):
    assert run(f"/sweetclaude:{command} something", tmp_path) is None


@pytest.mark.parametrize("prompt", ["fix the doctor page", "please run /sweetclaude:doctor later", "/other-plugin:doctor", ""])
def test_ordinary_prompts_pass_through(tmp_path, prompt):
    assert run(prompt, tmp_path) is None


def test_unknown_command_points_to_help(tmp_path):
    payload = run("/sweetclaude:behavioral-regression", tmp_path)
    assert "/sweetclaude:help" in payload["systemMessage"]
    assert "/sweetclaude:behavioral-regression" in payload["systemMessage"]


def test_malformed_input_is_silent(tmp_path):
    result = subprocess.run(["bash", str(HOOK)], cwd=tmp_path, input="not json", capture_output=True, text=True, timeout=30)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_hook_is_registered_and_listed():
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text())["hooks"]["UserPromptSubmit"]
    commands = [h["command"] for entry in hooks for h in entry["hooks"]]
    assert "${CLAUDE_PLUGIN_ROOT}/hooks/legacy-command-redirect.sh" in commands
    manifest = json.loads((ROOT / "hooks" / "hooks-manifest.json").read_text())["hooks"]
    assert any(h["file"] == "legacy-command-redirect.sh" and h["event"] == "UserPromptSubmit" for h in manifest)
    assert HOOK.stat().st_mode & 0o111
