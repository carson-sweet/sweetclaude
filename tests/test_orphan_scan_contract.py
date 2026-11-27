"""Orphan reports identify exact stray work, not primary migration inputs."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/migrate/migrate-v3-to-v4.py"


def write_item(path, item_id):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nid: {item_id}\ntitle: Example\nstatus: new\n---\n")


def scan(project):
    result = subprocess.run([sys.executable, str(SCRIPT), "scan-orphans", "--project-dir", str(project)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("stage", ["legacy", "partial", "post-migration"])
def test_scan_reports_exact_strays_without_consuming_primary_inputs(tmp_path, stage):
    project = tmp_path / "project"
    backlog = project / ".sweetclaude/product/backlog"
    state = project / ".sweetclaude/state"
    state.mkdir(parents=True)
    version = {"legacy": "3.18.0", "partial": "4.1.0", "post-migration": "5.1.3"}[stage]
    (state / "sweetclaude.yaml").write_text(f'framework:\n  installed_version: "{version}"\n')
    primary = backlog / "BL-001-primary.md"
    write_item(primary, "BL-001")
    if stage != "legacy":
        write_item(backlog / "ISSUE-001-migrated.md", "ISSUE-001")
    typed = backlog / "stories/STORY-002-stray.md"
    write_item(typed, "STORY-002")
    scratch = project / "scratch/STORY-003-notes.md"
    write_item(scratch, "STORY-003")
    notes = project / "scratch/notes.md"
    notes.write_text("ordinary notes\n")
    before = {p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    result = scan(project)
    found = {(f["file"], f["category"]) for f in result["findings"]}
    assert found == {(str(typed.relative_to(project)), "typed-subdir")}
    assert result["orphan_count"] == 1
    assert {p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()} == before
