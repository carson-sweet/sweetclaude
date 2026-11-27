"""Session health checks inspect the active bundle, not legacy global hooks."""
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks/sweetclaude-health-check.sh"


def run_health(tmp_path, bundle):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    project = tmp_path / "project"
    state = project / ".sweetclaude/state"
    state.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    config = state / "sweetclaude.yaml"
    config.write_text(yaml.safe_dump({"framework": {"setup_complete": True,
        "consistency": {"last_checked": (now - timedelta(hours=25)).isoformat(), "status": "ok", "drift": []},
        "update": {"last_checked": now.isoformat()}}}))
    env = {**os.environ, "HOME": str(home), "PROJECT_DIR": str(project)}
    env.pop("CLAUDE_CONFIG_DIR", None)
    if bundle is None:
        env.pop("CLAUDE_PLUGIN_ROOT", None)
    else:
        env["CLAUDE_PLUGIN_ROOT"] = str(bundle)
    result = subprocess.run(["bash", str(HOOK)], env=env, cwd=project, capture_output=True, text=True, timeout=30)
    return yaml.safe_load(config.read_text())["framework"]["consistency"], home, result


def test_healthy_active_bundle_requires_no_global_hooks(tmp_path):
    status, home, result = run_health(tmp_path, ROOT)
    assert result.returncode == 0, result.stderr
    assert status["status"] == "ok"
    assert status["drift"] == []
    assert not (home / ".claude/hooks/sweetclaude").exists()


@pytest.mark.parametrize("case", ["missing-root", "missing-manifest", "malformed-manifest"])
def test_invalid_bundle_produces_actionable_check_error(tmp_path, case):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    if case == "malformed-manifest":
        (bundle / "hooks").mkdir()
        (bundle / "hooks/hooks.json").write_text('{broken')
    status, _, result = run_health(tmp_path, None if case == "missing-root" else bundle)
    assert result.returncode != 0
    assert status.get("check_error") == "plugin_hooks_missing_or_invalid", (status, result.stderr)
    assert status["status"] != "ok"
