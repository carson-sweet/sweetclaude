"""R-249: score refuses the keyword-heuristic stub unless explicitly opted in."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
SCRIPT = REPO_ROOT / "scripts" / "behavioral_judge.py"
CONTRACT = "CONTRACT-05"


def _transcript(tmp_path: Path) -> Path:
    records = [
        {"type": "user", "message": {"content": "do the thing"}},
        {"type": "assistant",
         "message": {"content": [{"type": "text", "text": "done"}]}},
    ]
    p = tmp_path / "session.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return p


def _score(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "score", "--transcript",
         str(_transcript(tmp_path)), "--contract", CONTRACT, *extra],
        capture_output=True, text=True,
    )


class TestR249ScoreRequiresRealBackendOrExplicitStubOptIn:
    def test_no_backend_exits_nonzero(self, tmp_path):
        result = _score(tmp_path)

        assert result.returncode != 0

    def test_no_backend_message_names_the_real_backends(self, tmp_path):
        result = _score(tmp_path)

        message = result.stdout + result.stderr
        assert "openai" in message
        assert "codex" in message

    def test_explicit_stub_without_opt_in_is_refused(self, tmp_path):
        result = _score(tmp_path, "--backend", "stub")

        assert result.returncode != 0
        assert "--allow-stub" in result.stdout + result.stderr

    def test_explicit_stub_with_opt_in_flag_is_accepted(self, tmp_path):
        result = _score(tmp_path, "--backend", "stub", "--allow-stub")

        assert result.returncode == 0, result.stderr
        assert "stub" in result.stdout
