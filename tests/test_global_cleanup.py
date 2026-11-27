"""Explicit cleanup previews and backs up user-wide legacy configuration."""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "maintenance" / "global-cleanup.py"


def run_cleanup(home, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], env={**os.environ, "HOME": str(home)},
                          capture_output=True, text=True, timeout=30)


def test_preview_then_apply_backs_up_only_selected_legacy_entries(tmp_path):
    home = tmp_path / "home"
    claude = home / ".claude"
    rules = claude / "rules/sweetclaude"
    rules.mkdir(parents=True)
    (rules / "legacy.md").write_text("legacy rules\n")
    settings = claude / "settings.json"
    original = {"theme": "dark", "hooks": {"SessionStart": [{"hooks": [
        {"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-preflight.sh"},
        {"type": "command", "command": "other-tool --safe"},
    ]}]}}
    settings.write_text(json.dumps(original))
    first = run_cleanup(home, "preview")
    assert first.returncode == 0, first.stderr
    preview = json.loads(first.stdout)
    assert preview["remove_hooks"] == ["${CLAUDE_PLUGIN_ROOT}/hooks/session-preflight.sh"]
    assert preview["remove_hook_entries"] == [{"event": "SessionStart", "matcher": None,
        "hook": {"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-preflight.sh"}}]
    assert str(rules / "legacy.md") in preview["remove_files"]
    assert json.loads(settings.read_text()) == original
    assert (rules / "legacy.md").read_text() == "legacy rules\n"
    applied = run_cleanup(home, "apply", "--plan-hash", preview["plan_hash"])
    assert applied.returncode == 0, applied.stderr
    result = json.loads(applied.stdout)
    backup = Path(result["backup"])
    assert json.loads((backup / "settings.json").read_text()) == original
    assert (backup / "rules/sweetclaude/legacy.md").read_text() == "legacy rules\n"
    assert not rules.exists()
    after = json.loads(settings.read_text())
    assert after["theme"] == "dark"
    assert after["hooks"]["SessionStart"][0]["hooks"] == [{"type": "command", "command": "other-tool --safe"}]


def test_changed_configuration_invalidates_approval(tmp_path):
    home = tmp_path / "home"
    claude = home / ".claude"
    claude.mkdir(parents=True)
    settings = claude / "settings.json"
    settings.write_text('{}')
    preview = json.loads(run_cleanup(home, "preview").stdout)
    settings.write_text('{"theme":"changed"}')
    result = run_cleanup(home, "apply", "--plan-hash", preview["plan_hash"])
    assert result.returncode != 0
    assert settings.read_text() == '{"theme":"changed"}'
    assert not (claude / ".sweetclaude-legacy-backup").exists()


def test_invalid_global_settings_fail_without_mutation(tmp_path):
    home = tmp_path / "home"
    claude = home / ".claude"
    claude.mkdir(parents=True)
    settings = claude / "settings.json"
    settings.write_text('{broken')
    result = run_cleanup(home, "preview")
    assert result.returncode != 0
    assert settings.read_text() == '{broken'
    assert not (claude / ".sweetclaude-legacy-backup").exists()


def test_cleanup_preserves_unrelated_empty_hook_entries(tmp_path):
    home = tmp_path / "home"
    claude = home / ".claude"
    claude.mkdir(parents=True)
    settings = claude / "settings.json"
    settings.write_text(json.dumps({"hooks": {"Stop": [{"matcher": "kept", "hooks": []}],
        "SessionStart": [{"hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-preflight.sh"}]}]}}))
    preview = json.loads(run_cleanup(home, "preview").stdout)
    result = run_cleanup(home, "apply", "--plan-hash", preview["plan_hash"])
    assert result.returncode == 0, result.stderr
    assert json.loads(settings.read_text())["hooks"]["Stop"] == [{"matcher": "kept", "hooks": []}]


def test_cleanup_refuses_symlinked_rules_parent(tmp_path):
    home = tmp_path / "home"
    claude = home / ".claude"
    claude.mkdir(parents=True)
    external = tmp_path / "external"
    (external / "sweetclaude").mkdir(parents=True)
    (external / "sweetclaude/legacy.md").write_text("do not touch")
    (claude / "rules").symlink_to(external, target_is_directory=True)
    result = run_cleanup(home, "preview")
    assert result.returncode != 0
    assert (external / "sweetclaude/legacy.md").read_text() == "do not touch"


def test_preview_respects_claude_config_dir(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    config = tmp_path / "isolated-config"
    rules = config / "rules/sweetclaude"
    rules.mkdir(parents=True)
    (rules / "legacy.md").write_text("isolated")
    result = subprocess.run([sys.executable, str(SCRIPT), "preview"], capture_output=True, text=True,
                            env={**os.environ, "HOME": str(home), "CLAUDE_CONFIG_DIR": str(config)}, timeout=30)
    assert result.returncode == 0, result.stderr
    assert str(rules / "legacy.md") in json.loads(result.stdout)["remove_files"]
    assert not (home / ".claude").exists()
