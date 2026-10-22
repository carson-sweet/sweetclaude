"""R-248: emergency-hook-restore refuses to copy a broken install over itself."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
SCRIPT = REPO_ROOT / "scripts" / "emergency-hook-restore.sh"
BROKEN = "#!/bin/bash\nthis is broken (\n"


@pytest.fixture
def broken_install(tmp_path: Path) -> Path:
    plugin = tmp_path / "plugin"
    (plugin / "scripts").mkdir(parents=True)
    (plugin / "hooks").mkdir()
    shutil.copy(SCRIPT, plugin / "scripts" / "emergency-hook-restore.sh")
    (plugin / "hooks" / "guard.sh").write_text(BROKEN)
    return plugin


def _run(plugin: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["INSTALL_PATH"] = str(plugin)
    return subprocess.run(
        ["bash", str(plugin / "scripts" / "emergency-hook-restore.sh"), *args],
        capture_output=True, text=True, env=env,
    )


class TestR248RestoreRefusesSelfCopy:
    def test_all_hooks_restore_exits_nonzero_when_source_is_the_install(
        self, broken_install
    ):
        result = _run(broken_install)

        assert result.returncode != 0

    def test_nothing_is_reported_restored_when_source_is_the_install(
        self, broken_install
    ):
        result = _run(broken_install)

        assert "RESTORED" not in result.stdout
        assert "Restoring ALL hooks from repo" not in result.stdout

    def test_hooks_are_left_untouched(self, broken_install):
        hook = broken_install / "hooks" / "guard.sh"
        before = hook.stat().st_mtime_ns

        _run(broken_install)

        assert hook.read_text() == BROKEN
        assert hook.stat().st_mtime_ns == before

    def test_named_hook_restore_also_refuses(self, broken_install):
        result = _run(broken_install, "guard.sh")

        assert result.returncode != 0
        assert "RESTORED" not in result.stdout

    def test_stderr_names_the_source_options(self, broken_install):
        result = _run(broken_install)

        stderr = result.stderr.lower()
        assert "hooks.bak" in stderr
        assert "clone" in stderr or "checkout" in stderr
