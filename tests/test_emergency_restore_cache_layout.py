"""R-247: emergency-hook-restore resolves the real sweetclaude-stable cache layout."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
SCRIPT = REPO_ROOT / "scripts" / "emergency-hook-restore.sh"
KEY = "sweetclaude@sweetclaude-stable"


def _dry_run(home: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "INSTALL_PATH"}
    env["HOME"] = str(home)
    return subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"], capture_output=True, text=True, env=env
    )


@pytest.fixture
def stable_install(tmp_path: Path) -> tuple[Path, Path]:
    home = tmp_path / "home"
    install = (
        home / ".claude" / "plugins" / "cache" / "sweetclaude-stable"
        / "sweetclaude" / "5.0.2"
    )
    (install / "hooks").mkdir(parents=True)
    (install / "hooks" / "guard.sh").write_text("#!/bin/bash\nexit 0\n")
    return home, install


class TestR247EmergencyRestoreResolvesStableCacheLayout:
    def test_installed_plugins_json_keyed_with_marketplace_suffix_resolves(
        self, stable_install
    ):
        home, install = stable_install
        registry = home / ".claude" / "plugins" / "installed_plugins.json"
        registry.write_text(json.dumps({
            "version": 2,
            "plugins": {KEY: [{
                "scope": "user",
                "installPath": str(install),
                "version": "5.0.2",
                "lastUpdated": "2026-10-20T00:00:00.000Z",
            }]},
        }))

        result = _dry_run(home)

        assert result.returncode == 0, result.stderr
        assert f"Resolved install path: {install}" in result.stdout.splitlines()
        assert "FATAL" not in result.stderr

    def test_find_fallback_resolves_cache_without_a_registry_entry(self, stable_install):
        home, install = stable_install

        result = _dry_run(home)

        assert result.returncode == 0, result.stderr
        assert f"Resolved install path: {install}" in result.stdout.splitlines()

    def test_fatal_hint_names_the_real_cache_directory(self, tmp_path):
        home = tmp_path / "empty-home"
        (home / ".claude" / "plugins" / "cache").mkdir(parents=True)

        result = _dry_run(home)

        assert result.returncode != 0
        assert "FATAL: Cannot find installed hooks path." in result.stderr
        assert "sweetclaude-stable" in result.stderr
