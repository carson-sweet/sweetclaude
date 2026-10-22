import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "maintenance" / "plugin-state.py"
spec = importlib.util.spec_from_file_location("plugin_state_r216", SCRIPT)
plugin_state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin_state)


def _install(home: Path, plugin_key: str, version: str) -> None:
    market = plugin_key.split("@", 1)[1]
    install = home / ".claude" / "plugins" / "cache" / market / "sweetclaude" / version
    install.mkdir(parents=True, exist_ok=True)
    path = home / ".claude" / "plugins" / "installed_plugins.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "version": 2,
            "plugins": {
                plugin_key: [{
                    "scope": "user",
                    "installPath": str(install),
                    "version": version,
                }]
            },
        }),
        encoding="utf-8",
    )


class TestR216LegacyKeySwitchCommands:
    def test_bare_key_prerelease_removes_bare_marketplace_as_third_command(self, tmp_path):
        _install(tmp_path, "sweetclaude@sweetclaude", "4.5.1-beta")

        result = plugin_state.inspect_state(tmp_path, None, None)

        assert result["channel"] == "beta"
        assert result["channel_retired"] is True
        assert result["retirement_switch_commands"][2] == "/plugin marketplace remove sweetclaude"

    def test_bare_key_switch_never_names_the_uninstalled_beta_marketplace(self, tmp_path):
        _install(tmp_path, "sweetclaude@sweetclaude", "4.5.1-beta")

        commands = plugin_state.inspect_state(tmp_path, None, None)["retirement_switch_commands"]

        assert len(commands) == 3
        assert commands[0] == "/plugin marketplace add carson-sweet/sweetclaude@main"
        assert commands[1] == "/plugin install sweetclaude@sweetclaude-stable"
        assert "/plugin marketplace remove sweetclaude-beta" not in commands
