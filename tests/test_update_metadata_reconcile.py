"""ISSUE-231 regression: cmd_metadata must reconcile framework.update.available
against the newly-installed version, in the same write that bumps
installed_version. A stale available at or below the new version is cleared;
a genuinely newer available is preserved. Not deferred to any health check.
"""
import argparse
import json

import pytest
import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import update as update_mod



@pytest.fixture(autouse=True)
def isolated_plugin_registry(tmp_path, monkeypatch):
    home = tmp_path / "home"
    registry = home / ".claude/plugins/installed_plugins.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"plugins": {"sweetclaude-beta": [{
        "scope": "local", "projectPath": str(tmp_path),
        "installPath": str(tmp_path / "install"), "version": "4.3.8-beta"
    }]}}))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)


def _write_state(project: Path, installed: str, available):
    state_dir = project / ".sweetclaude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": 2,
        "framework": {
            "installed_version": installed,
            "update": {
                "available": available,
                "last_checked": "2026-06-27T00:01:35+00:00",
                "declined": None,
                "check_error": None,
            },
        },
    }
    path = state_dir / "sweetclaude.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path


def _run_metadata(project: Path, version: str):
    args = argparse.Namespace(
        project_dir=str(project),
        plugin_key="sweetclaude-beta",
        install_path=str(project / "install"),
        version=version,
        sha="deadbeef",
    )
    rc = update_mod.cmd_metadata(args)
    assert rc == 0
    return yaml.safe_load((project / ".sweetclaude" / "state" / "sweetclaude.yaml").read_text())


def test_update_clears_stale_available_at_or_below_installed(tmp_path):
    sc = _write_state(tmp_path, installed="4.3.8-beta", available="4.3.8-beta")
    assert sc.exists()
    d = _run_metadata(tmp_path, version="4.3.12-beta")
    fw = d["framework"]
    assert fw["installed_version"] == "4.3.12-beta", fw
    # The reported bug: available (4.3.8) is now below installed (4.3.12) and
    # must be cleared, not left as a downgrade offer.
    assert fw["update"]["available"] is None, fw["update"]


def test_update_preserves_genuinely_newer_available(tmp_path):
    _write_state(tmp_path, installed="4.3.8-beta", available="4.4.0-beta")
    d = _run_metadata(tmp_path, version="4.3.12-beta")
    fw = d["framework"]
    assert fw["installed_version"] == "4.3.12-beta", fw
    # A real pending update above the installed version is not destroyed.
    assert fw["update"]["available"] == "4.4.0-beta", fw["update"]
