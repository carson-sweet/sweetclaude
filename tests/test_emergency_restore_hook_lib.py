"""emergency-hook-restore recreates hooks/lib/hook_io.py that every ported hook calls."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
SCRIPT = REPO_ROOT / "scripts" / "emergency-hook-restore.sh"
REPO_HOOK_IO = REPO_ROOT / "hooks" / "lib" / "hook_io.py"


def _run(plugin: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["INSTALL_PATH"] = str(plugin)
    return subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env
    )


@pytest.fixture
def plugin(tmp_path: Path) -> Path:
    root = tmp_path / "plugin"
    (root / "hooks").mkdir(parents=True)
    (root / "hooks" / "guard.sh").write_text("#!/bin/bash\nexit 1\n")
    return root


class TestAllHooksRestoreRecreatesHookLib:
    def test_repo_restore_recreates_missing_hook_io_byte_identical(self, plugin):
        target = plugin / "hooks" / "lib" / "hook_io.py"
        assert not target.exists()

        result = _run(plugin)

        assert result.returncode == 0, result.stderr
        assert target.is_file()
        assert target.read_bytes() == REPO_HOOK_IO.read_bytes()

    def test_backup_restore_recreates_hook_io_from_backup(self, plugin):
        backup = plugin / "hooks.bak"
        (backup / "lib").mkdir(parents=True)
        (backup / "guard.sh").write_text("#!/bin/bash\nexit 0\n")
        marker = b"# backup copy of hook_io\n"
        (backup / "lib" / "hook_io.py").write_bytes(marker)
        target = plugin / "hooks" / "lib" / "hook_io.py"

        result = _run(plugin)

        assert result.returncode == 0, result.stderr
        assert target.read_bytes() == marker

    def test_dry_run_lists_hook_io_and_writes_nothing(self, plugin):
        result = _run(plugin, "--dry-run")

        assert result.returncode == 0, result.stderr
        assert "Would restore: hooks/lib/hook_io.py" in result.stdout.splitlines()
        assert not (plugin / "hooks" / "lib").exists()


class TestNamedHookRestoreStaysSingleFile:
    def test_named_restore_copies_only_that_hook(self, plugin):
        result = _run(plugin, "artifact-guardian.sh")

        assert result.returncode == 0, result.stderr
        assert (plugin / "hooks" / "artifact-guardian.sh").read_bytes() == (
            REPO_ROOT / "hooks" / "artifact-guardian.sh"
        ).read_bytes()
        assert not (plugin / "hooks" / "lib").exists()
