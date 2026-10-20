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
