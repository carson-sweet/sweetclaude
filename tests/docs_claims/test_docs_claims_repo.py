"""Row id: docs_claims_red_baseline. Every reference in README.md and docs/user-guide resolves (phase 5 item 3)."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_docs_claims_red_baseline():
    res = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "docs_claims_check.py"), "--root", str(REPO)],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
