"""Row id: docs_claims_red_baseline. Strict gate, enabled by phase 5 via DOCS_CLAIMS_STRICT=1."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(os.environ.get("DOCS_CLAIMS_STRICT") != "1", reason="enabled in phase 5 via DOCS_CLAIMS_STRICT=1")
def test_docs_claims_red_baseline():
    res = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "docs_claims_check.py"), "--root", str(REPO)],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
