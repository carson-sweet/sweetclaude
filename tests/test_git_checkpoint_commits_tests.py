"""R-238: git-checkpoint commits the failing tests, not only .sweetclaude/ state."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
HOOK = REPO_ROOT / "hooks" / "git-checkpoint.sh"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "README.md").write_text("seed\n")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-q", "-m", "seed")
    return tmp_path


def _checkpoint(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(HOOK), *args], cwd=repo, capture_output=True, text=True
    )


def _write_test_file(repo: Path) -> None:
    (repo / "tests").mkdir()
    (repo / "tests" / "test_x.py").write_text("def test_x():\n    assert False\n")


class TestR238GitCheckpointCommitsTestFiles:
    def test_untracked_test_file_named_on_the_command_line_is_committed(self, repo):
        _write_test_file(repo)

        result = _checkpoint(repo, "test: RED - X", "tests/test_x.py")

        assert result.returncode == 0, result.stderr
        assert _git(repo, "log", "-1", "--format=%s").strip() == "test: RED - X"
        committed = _git(repo, "show", "--name-only", "--format=", "HEAD").split()
        assert "tests/test_x.py" in committed

    def test_the_test_file_is_tracked_and_clean_afterwards(self, repo):
        _write_test_file(repo)

        _checkpoint(repo, "test: RED - X", "tests/test_x.py")

        assert _git(repo, "status", "--porcelain").strip() == ""

    def test_files_not_named_are_not_swept_into_the_commit(self, repo):
        _write_test_file(repo)
        (repo / "unrelated.txt").write_text("keep out\n")

        _checkpoint(repo, "test: RED - X", "tests/test_x.py")

        committed = _git(repo, "show", "--name-only", "--format=", "HEAD").split()
        assert "tests/test_x.py" in committed
        assert "unrelated.txt" not in committed

    def test_sweetclaude_state_is_still_checkpointed_alongside_named_files(self, repo):
        (repo / ".sweetclaude" / "state").mkdir(parents=True)
        (repo / ".sweetclaude" / "state" / "phase.yaml").write_text("phase: build\n")
        _write_test_file(repo)

        _checkpoint(repo, "test: RED - X", "tests/test_x.py")

        committed = _git(repo, "show", "--name-only", "--format=", "HEAD").split()
        assert ".sweetclaude/state/phase.yaml" in committed
        assert "tests/test_x.py" in committed
