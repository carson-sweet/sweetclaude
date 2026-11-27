"""Exercise current migration gates and real guards against isolated fixtures."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MIGRATOR = ROOT / "scripts/migrate/migrate-v3-to-v4.py"
FIXTURE = ROOT / "tests/fixtures/migrate-smoke"
SKILLS = ["project-backlog", "project-issues", "project-backlog-triage",
          "project-gh-import-issues", "project-gh-sync-issues"]


def command(project, *args):
    result = subprocess.run([sys.executable, str(MIGRATOR), *args, "--project-dir", str(project)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def migration_projects(tmp_path_factory):
    root = tmp_path_factory.mktemp("ep0085")
    legacy = root / "legacy"
    migrated = root / "migrated"
    shutil.copytree(FIXTURE, legacy)
    shutil.copytree(FIXTURE, migrated)
    preflight = command(migrated, "preflight")
    assert preflight["migrate_allowed"]
    plan = command(migrated, "plan", "--include-done")
    receipt = dict(plan["mutation_plan"]["approval_receipt_template"])
    receipt["approved"] = True
    receipt_path = root / "approval.json"
    receipt_path.write_text(json.dumps(receipt))
    result = command(migrated, "execute", "--include-done", "--approval-receipt", str(receipt_path))
    manifest = json.loads(Path(result["execution_manifest"]).read_text())
    lifecycle = manifest["mutation_lifecycle"]
    for key in ("approval", "snapshot_scope_validation", "restore_proof", "postcondition_validation"):
        assert lifecycle[key]["status"] == "pass", (key, lifecycle)
    created = root / "created.json"
    created.write_text(json.dumps(result["created_paths"]))
    assert not command(migrated, "verify", "--created-paths-file", str(created))["failures"]
    command(migrated, "finalize")
    command(migrated, "cleanup-v3-files")
    return legacy, migrated


@pytest.mark.parametrize("skill", SKILLS)
def test_real_skill_guard_reports_legacy_and_allows_migrated_project(migration_projects, tmp_path, skill):
    text = (ROOT / "skill-library/build" / skill / "SKILL.md").read_text()
    section = text.split("## MIGRATION GUARD", 1)[1]
    blocks = re.findall(r"```bash\n(.*?)```", section, re.S)
    guard = next(block for block in blocks if "guard --project-dir" in block)
    home = tmp_path / "home"
    home.mkdir()
    env = {**os.environ, "HOME": str(home), "CLAUDE_PLUGIN_ROOT": str(ROOT)}
    legacy, migrated = migration_projects
    result = subprocess.run(["bash", "-c", guard], cwd=legacy, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "migration-may-be-needed"
    result = subprocess.run(["bash", "-c", guard], cwd=migrated, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert not result.stdout.strip(), result.stdout
