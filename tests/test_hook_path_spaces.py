"""Hook commands must execute correctly when the plugin path contains spaces."""
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_manifest_hook_commands_execute_with_spaces_and_preserve_exit(tmp_path):
    plugin = tmp_path / "plugin path with spaces"
    hooks = plugin / "hooks"
    hooks.mkdir(parents=True)
    config = json.loads((ROOT / "hooks/hooks.json").read_text())
    commands = [h["command"] for groups in config["hooks"].values()
                for group in groups for h in group["hooks"] if h.get("type") == "command"]
    assert commands
    for command in commands:
        name = command.replace('"', '').rsplit('/', 1)[-1]
        script = hooks / name
        script.write_text('#!/bin/sh\nprintf "hook-executed\\n"\nexit 37\n')
        script.chmod(0o755)
        result = subprocess.run(command, shell=True, env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin)},
                                input="{}", capture_output=True, text=True, timeout=10)
        assert result.returncode == 37, (command, result.returncode, result.stderr)
        assert result.stdout == "hook-executed\n"


def test_tdd_checkpoint_instructions_quote_plugin_path():
    skill = (ROOT / "skill-library/build/code-tdd/SKILL.md").read_text()
    assert 'bash ${CLAUDE_PLUGIN_ROOT}/hooks/git-checkpoint.sh' not in skill
    assert 'bash "${CLAUDE_PLUGIN_ROOT}/hooks/git-checkpoint.sh"' in skill
