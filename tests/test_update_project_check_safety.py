"""Project checks must distinguish clean results from unavailable scans."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/update.py"


def invoke(project, runner, orphan):
    return subprocess.run([sys.executable, str(SCRIPT), "project-check", "--project-dir", str(project),
                           "--runner", str(runner), "--migrate-script", str(orphan)],
                          capture_output=True, text=True, timeout=30)


def project_state(tmp_path):
    project = tmp_path / "project"
    state = project / ".sweetclaude/state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text("schema_version: 2\nframework: {}\n")
    return project


def test_project_check_reports_clean_only_after_both_successful_scans(tmp_path):
    project = project_state(tmp_path)
    runner = tmp_path / "runner.py"
    runner.write_text('print("Drift scan (test): 0 finding(s)")\n')
    orphan = tmp_path / "orphan.py"
    orphan.write_text('print(\'{"orphan_count":0,"findings":[]}\')\n')
    result = invoke(project, runner, orphan)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["ok"] and report["scans"]["drift"]["status"] == "completed"
    assert report["scans"]["orphans"]["status"] == "completed"
    assert report["drift_count"] == 0 and report["orphan_count"] == 0


@pytest.mark.parametrize("broken", ["nonzero", "empty", "invalid", "shape", "missing"])
def test_project_check_does_not_report_clean_when_orphan_scan_fails(tmp_path, broken):
    project = project_state(tmp_path)
    runner = tmp_path / "runner.py"
    runner.write_text('print("Drift scan (test): 0 finding(s)")\n')
    orphan = tmp_path / "orphan.py"
    source = {"nonzero": 'import sys; print("scan failure",file=sys.stderr); sys.exit(9)',
              "empty": "pass", "invalid": 'print("not json")', "shape": 'print("[]")'}
    if broken != "missing":
        orphan.write_text(source[broken] + "\n")
    result = invoke(project, runner, orphan)
    report = json.loads(result.stdout)
    assert result.returncode != 0 and not report["ok"]
    assert report["scans"]["orphans"]["status"] == "failed"
    assert report["orphan_count"] is None


def test_project_check_reports_drift_scanner_failure(tmp_path):
    project = project_state(tmp_path)
    runner = tmp_path / "runner.py"
    runner.write_text('import sys; print("failed", file=sys.stderr); sys.exit(9)\n')
    orphan = tmp_path / "orphan.py"
    orphan.write_text('print(\'{"orphan_count":0,"findings":[]}\')\n')
    result = invoke(project, runner, orphan)
    report = json.loads(result.stdout)
    assert result.returncode != 0 and not report["ok"]
    assert report["scans"]["drift"]["status"] == "failed"
    assert report["drift_count"] is None


def test_real_project_check_reports_legacy_and_preserves_work_items(tmp_path):
    project = project_state(tmp_path)
    backlog = project / ".sweetclaude/product/backlog"
    orphan = backlog / "stories/STORY-001-old.md"
    orphan.parent.mkdir(parents=True)
    orphan.write_text('---\nid: STORY-001\ntitle: Old\ntype: story\nstatus: new\ncreated: 2026-01-01\n---\n')
    legacy = backlog / "BL-002-primary.md"
    legacy.write_text('---\nid: BL-002\ntitle: Legacy\nstatus: backlog\n---\n')
    before = {p.relative_to(backlog): p.read_bytes() for p in backlog.rglob('*') if p.is_file()}
    result = invoke(project, ROOT / "scripts/migrations/runner.py", ROOT / "scripts/migrate/migrate-v3-to-v4.py")
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["ok"] and report["old_taxonomy_count"] == 2
    assert report["orphan_count"] > 0
    after = {p.relative_to(backlog): p.read_bytes() for p in backlog.rglob('*') if p.is_file()}
    assert after == before
    assert not (project / ".sweetclaude/state/doctor-prompt-pending.json").exists()


@pytest.mark.parametrize("broken", ["missing", "empty", "malformed", "count-mismatch"])
def test_project_check_rejects_missing_or_invalid_drift_output(tmp_path, broken):
    project = project_state(tmp_path)
    runner = tmp_path / "runner.py"
    scripts = {"empty": "pass", "malformed": 'print("not a drift report")',
               "count-mismatch": 'print("Drift scan (test): 1 finding(s)")'}
    if broken != "missing":
        runner.write_text(scripts[broken] + "\n")
    orphan = tmp_path / "orphan.py"
    orphan.write_text('print(\'{"orphan_count":0,"findings":[]}\')\n')
    result = invoke(project, runner, orphan)
    report = json.loads(result.stdout)
    assert result.returncode != 0 and not report["ok"]
    assert report["scans"]["drift"]["status"] == "failed"
    assert report["drift_count"] is None


def test_update_workflow_stops_on_failed_required_scans():
    text = (ROOT / "skill-library/configure/update/SKILL.md").read_text()
    project_checks = text.split("## Step 5: Project checks", 1)[1].split("## Step 6:", 1)[0]
    assert 'if the command exits nonzero or `ok` is false' in project_checks.lower()
    assert "never report the project clean" in project_checks.lower()


def test_update_workflow_does_not_call_skipped_project_check_clean():
    text = (ROOT / "skill-library/configure/update/SKILL.md").read_text()
    project_checks = text.split("## Step 5: Project checks", 1)[1].split("## Step 6:", 1)[0].lower()
    assert '`skipped` is true' in project_checks
    assert 'do not report the project clean' in project_checks
