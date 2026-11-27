import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "maintenance" / "plugin-state.py"
spec = importlib.util.spec_from_file_location("plugin_state", SCRIPT)
plugin_state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin_state)


def _write_installed(home: Path, data: dict) -> Path:
    path = home / ".claude" / "plugins" / "installed_plugins.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _install_dir(home: Path, *parts: str) -> str:
    path = home.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def test_inspect_detects_legacy_beta_channel_and_expected_ref(tmp_path):
    install = _install_dir(tmp_path, ".claude", "plugins", "cache", "sweetclaude", "sweetclaude", "4.1.2-beta")
    _write_installed(tmp_path, {
        "version": 2,
        "plugins": {
            "sweetclaude@sweetclaude": [{
                "scope": "user",
                "installPath": install,
                "version": "4.1.2-beta",
                "gitCommitSha": "d2ff161",
                "lastUpdated": "2026-05-25T18:48:15Z",
            }]
        },
    })

    result = plugin_state.inspect_state(tmp_path, None, None)

    assert result["ok"] is True
    assert result["plugin_key"] == "sweetclaude@sweetclaude"
    assert result["legacy_marketplace"] is True
    assert result["channel"] == "beta"
    assert result["expected_ref"] == "beta-4.x"
    assert result["expected_marketplace"] == "sweetclaude-beta"
    assert result["git_commit_sha"] == "d2ff161"
    assert result["stale_beta_install"] is True
    assert result["minimum_safe_beta_version"] == "4.1.9-beta"
    assert result["plugin_update_command"] == "/plugin update sweetclaude@sweetclaude"
    assert result["restart_required_after_plugin_update"] is True


def test_inspect_does_not_mark_current_beta_as_stale(tmp_path):
    install = _install_dir(tmp_path, ".claude", "plugins", "cache", "sweetclaude-beta", "sweetclaude", "4.1.12-beta")
    _write_installed(tmp_path, {
        "version": 2,
        "plugins": {
            "sweetclaude@sweetclaude-beta": [{
                "scope": "user",
                "installPath": install,
                "version": "4.1.12-beta",
                "gitCommitSha": "nextbeta",
                "lastUpdated": "2026-05-25T18:48:15Z",
            }]
        },
    })

    result = plugin_state.inspect_state(tmp_path, None, None)

    assert result["channel"] == "beta"
    assert result["stale_beta_install"] is False
    assert result["plugin_update_command"] == "/plugin update sweetclaude@sweetclaude-beta"


def test_inspect_detects_stable_channel_from_stable_marketplace(tmp_path):
    install = _install_dir(tmp_path, ".claude", "plugins", "cache", "sweetclaude-stable", "sweetclaude", "3.68.5")
    _write_installed(tmp_path, {
        "plugins": {
            "sweetclaude@sweetclaude-stable": [{
                "scope": "user",
                "installPath": install,
                "version": "3.68.5",
                "lastUpdated": "2026-05-25T10:00:00Z",
            }]
        },
    })

    result = plugin_state.inspect_state(tmp_path, None, None)

    assert result["channel"] == "stable"
    assert result["expected_ref"] == "main"
    assert result["expected_marketplace"] == "sweetclaude-stable"


def test_inspect_detects_stable_channel_for_bare_marketplace_5x(tmp_path):
    install = _install_dir(tmp_path, ".claude", "plugins", "cache", "sweetclaude", "sweetclaude", "5.0.0")
    _write_installed(tmp_path, {
        "plugins": {
            "sweetclaude@sweetclaude": [{
                "scope": "user",
                "installPath": install,
                "version": "5.0.0",
                "lastUpdated": "2026-10-20T10:00:00Z",
            }]
        },
    })

    result = plugin_state.inspect_state(tmp_path, None, None)

    assert result["channel"] == "stable"
    assert result["expected_ref"] == "main"
    assert result["expected_marketplace"] == "sweetclaude-stable"


def test_inspect_ignores_local_entry_for_other_project(tmp_path):
    project = tmp_path / "project"
    other_project = tmp_path / "other"
    project.mkdir()
    other_project.mkdir()
    user_install = _install_dir(tmp_path, ".claude", "plugins", "cache", "sweetclaude-beta", "sweetclaude", "4.1.8-beta")
    local_install = _install_dir(tmp_path, ".claude", "plugins", "cache", "sweetclaude-beta", "sweetclaude", "4.1.9-beta")
    _write_installed(tmp_path, {
        "plugins": {
            "sweetclaude@sweetclaude-beta": [
                {
                    "scope": "user",
                    "installPath": user_install,
                    "version": "4.1.8-beta",
                    "lastUpdated": "2026-05-25T10:00:00Z",
                },
                {
                    "scope": "local",
                    "projectPath": str(other_project),
                    "installPath": local_install,
                    "version": "4.1.9-beta",
                    "lastUpdated": "2026-05-25T11:00:00Z",
                },
            ]
        },
    })

    result = plugin_state.inspect_state(tmp_path, project, None)

    assert result["scope"] == "user"
    assert result["version"] == "4.1.8-beta"


def test_repair_updates_exact_plugin_metadata_entry(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    old_install = _install_dir(tmp_path, ".claude", "plugins", "cache", "sweetclaude", "sweetclaude", "4.1.2-beta")
    new_install = _install_dir(tmp_path, ".claude", "plugins", "cache", "sweetclaude", "sweetclaude", "4.1.8-beta")
    path = _write_installed(tmp_path, {
        "version": 2,
        "plugins": {
            "sweetclaude@sweetclaude": [{
                "scope": "user",
                "installPath": old_install,
                "version": "4.1.2-beta",
                "gitCommitSha": "d2ff161",
                "lastUpdated": "2026-05-25T18:48:15Z",
            }]
        },
    })

    result = plugin_state.repair_state(
        tmp_path,
        plugin_key="sweetclaude@sweetclaude",
        install_path=new_install,
        version="4.1.8-beta",
        sha="a217639",
        project_dir=project,
    )

    assert result["ok"] is True
    data = json.loads(path.read_text(encoding="utf-8"))
    entry = data["plugins"]["sweetclaude@sweetclaude"][0]
    assert entry["installPath"] == new_install
    assert entry["version"] == "4.1.8-beta"
    assert entry["gitCommitSha"] == "a217639"
    assert entry["lastUpdated"].endswith("Z")


def test_inspect_prefers_current_project_local_entry_when_cache_is_shared(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    install = _install_dir(tmp_path, ".claude", "plugins", "cache", "sweetclaude-stable", "sweetclaude", "5.1.2")
    _write_installed(tmp_path, {"plugins": {"sweetclaude@sweetclaude-stable": [
        {"scope": "user", "installPath": install, "version": "5.1.2"},
        {"scope": "local", "projectPath": str(project), "installPath": install, "version": "5.1.2"},
    ]}})
    result = plugin_state.inspect_state(tmp_path, project, Path(install))
    assert result["scope"] == "local"


def test_repair_local_scope_preserves_user_entry_with_shared_cache(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    old = _install_dir(tmp_path, ".claude", "plugins", "cache", "sweetclaude-stable", "sweetclaude", "5.1.2")
    new = _install_dir(tmp_path, ".claude", "plugins", "cache", "sweetclaude-stable", "sweetclaude", "5.1.3")
    path = _write_installed(tmp_path, {"plugins": {"sweetclaude@sweetclaude-stable": [
        {"scope": "user", "installPath": old, "version": "5.1.2"},
        {"scope": "local", "projectPath": str(project), "installPath": old, "version": "5.1.2"},
    ]}})
    before = json.loads(path.read_text())["plugins"]["sweetclaude@sweetclaude-stable"][0]
    plugin_state.repair_state(tmp_path, plugin_key="sweetclaude@sweetclaude-stable",
                              install_path=new, version="5.1.3", sha="abc", project_dir=project,
                              scope="local")
    entries = json.loads(path.read_text())["plugins"]["sweetclaude@sweetclaude-stable"]
    assert entries[0] == before
    assert entries[1]["installPath"] == new


def test_inspect_respects_claude_config_dir(tmp_path):
    import os
    import subprocess
    import sys

    home = tmp_path / "home"
    home.mkdir()
    config = tmp_path / "config"
    project = tmp_path / "project"
    project.mkdir()
    install = config / "plugins/cache/sweetclaude-stable/sweetclaude/5.1.2"
    install.mkdir(parents=True)
    (config / "plugins/installed_plugins.json").write_text(json.dumps({"plugins": {
        "sweetclaude@sweetclaude-stable": [{"scope": "local", "projectPath": str(project),
            "installPath": str(install), "version": "5.1.2"}]}}))
    result = subprocess.run([sys.executable, str(SCRIPT), "--project-dir", str(project), "inspect",
                             "--current-root", str(install)], capture_output=True, text=True,
                            env={**os.environ, "HOME": str(home), "CLAUDE_CONFIG_DIR": str(config)}, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["scope"] == "local"


def test_inspect_ignores_project_scope_entry_for_another_project(tmp_path):
    project = tmp_path / "project"
    other = tmp_path / "other"
    project.mkdir()
    other.mkdir()
    user_install = _install_dir(tmp_path, "user-install")
    other_install = _install_dir(tmp_path, "other-install")
    _write_installed(tmp_path, {"plugins": {"sweetclaude@sweetclaude-stable": [
        {"scope": "user", "installPath": user_install, "version": "5.1.2"},
        {"scope": "project", "projectPath": str(other), "installPath": other_install, "version": "5.1.3"},
    ]}})
    result = plugin_state.inspect_state(tmp_path, project, Path(other_install))
    assert result["scope"] == "user"
    assert result["install_path"] == user_install


def test_repair_rejects_ambiguous_scope_without_writing(tmp_path):
    import pytest

    project = tmp_path / "project"
    project.mkdir()
    install = _install_dir(tmp_path, "shared-install")
    registry = _write_installed(tmp_path, {"plugins": {"sweetclaude@stable": [
        {"scope": "user", "installPath": install, "version": "5.1.2"},
        {"scope": "local", "projectPath": str(project), "installPath": install, "version": "5.1.2"},
    ]}})
    before = registry.read_bytes()
    with pytest.raises(ValueError, match="ambiguous"):
        plugin_state.repair_state(tmp_path, plugin_key="sweetclaude@stable", install_path=install,
                                  version="5.1.3", sha="abc", project_dir=project)
    assert registry.read_bytes() == before


def test_retired_channel_switch_uses_explicit_local_scope():
    commands = plugin_state._switch_commands("beta", "stable")
    assert "claude plugin install sweetclaude@sweetclaude-stable --scope local" in commands
