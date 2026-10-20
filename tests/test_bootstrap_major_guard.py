"""Bootstrap Step 5b maintenance guard across plugin and project majors.

Runs the guard's real bash block out of skills/bootstrap/SKILL.md against a
fake HOME, so an edit to the skill is an edit to what this test exercises.
The plugin version comes from installed_plugins.json exactly as bootstrap
reads it; the recovery script is deliberately unreachable so only the guard
mode decision is under test.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
BOOTSTRAP_SKILL = REPO_ROOT / "skills" / "bootstrap" / "SKILL.md"


def _guard_block() -> str:
    text = BOOTSTRAP_SKILL.read_text(encoding="utf-8")
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        if "GUARD_MODE=none" in block:
            return block
    raise AssertionError("bootstrap Step 5b guard block not found")


def _project(tmp_path: Path, project_version: str, bl_files: bool) -> Path:
    project = tmp_path / "project"
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text(
        f"framework:\n  installed_version: '{project_version}'\n",
        encoding="utf-8",
    )
    backlog = project / ".sweetclaude" / "product" / "backlog"
    backlog.mkdir(parents=True)
    if bl_files:
        (backlog / "BL-001-old.md").write_text("# Old item\n", encoding="utf-8")
    return project


def _home(tmp_path: Path, plugin_version: str | None) -> Path:
    home = tmp_path / "home"
    plugins = home / ".claude" / "plugins"
    plugins.mkdir(parents=True)
    if plugin_version is not None:
        (plugins / "installed_plugins.json").write_text(json.dumps({
            "plugins": {
                "sweetclaude@sweetclaude-stable": [{
                    "scope": "user",
                    "installPath": str(plugins / "cache" / "sweetclaude-stable" / "sweetclaude" / plugin_version),
                    "version": plugin_version,
                    "lastUpdated": "2026-10-20T10:00:00Z",
                }]
            }
        }), encoding="utf-8")
    return home


def _guard_mode(tmp_path: Path, plugin_version: str | None,
                project_version: str, bl_files: bool) -> str:
    project = _project(tmp_path, project_version, bl_files)
    home = _home(tmp_path, plugin_version)
    plugin_root = tmp_path / "isolated" / "plugin-root"
    plugin_root.mkdir(parents=True)
    env = dict(os.environ, HOME=str(home), CLAUDE_PLUGIN_ROOT=str(plugin_root))
    proc = subprocess.run(["bash", "-c", _guard_block()], cwd=str(project),
                          env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    for line in proc.stdout.splitlines():
        if line.startswith("GUARD_MODE="):
            return line.split("=", 1)[1]
    return "none"


@pytest.mark.parametrize("plugin_version,project_version,bl_files,expected", [
    ("5.0.0", "4.5.3", True, "hard-stop"),
    ("5.0.0", "3.68.0", False, "hard-stop"),
    ("5.0.0", "", False, "hard-stop"),
    ("5.0.0", "5.0.0", False, "none"),
    ("5.0.0", "4.5.3", False, "none"),
    ("4.6.0", "3.68.0", False, "hard-stop"),
    ("4.6.0", "4.6.0", True, "hard-stop"),
    ("4.6.0", "4.6.0", False, "none"),
])
def test_guard_mode_by_plugin_and_project_major(tmp_path, plugin_version,
                                                project_version, bl_files,
                                                expected) -> None:
    assert _guard_mode(tmp_path, plugin_version, project_version, bl_files) == expected


def test_v3_backlog_files_raise_an_advisory_when_plugin_version_is_unreadable(tmp_path) -> None:
    assert _guard_mode(tmp_path, None, "4.6.0", True) == "advisory"


def test_no_guard_when_plugin_version_is_unreadable_and_project_is_clean(tmp_path) -> None:
    assert _guard_mode(tmp_path, None, "4.6.0", False) == "none"
