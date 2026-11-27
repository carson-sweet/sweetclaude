"""Legacy items remain visible in diagnostics until supported migration indexes them."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from cache import rebuild
from migrate.migrate_taxonomy import build_plan, create_snapshot, execute


def test_legacy_story_and_bug_are_diagnosed_through_taxonomy_migration(tmp_path):
    backlog = tmp_path / ".sweetclaude/product/backlog"
    story = backlog / "done/STORY-015-old.md"
    bug = backlog / "bugs/BUG-005-old.md"
    for path, item_id, kind in [(story, "STORY-015", "story"), (bug, "BUG-005", "bug-fix")]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nid: {item_id}\ntype: {kind}\ntitle: Legacy\nstatus: done\ncreated: 2026-01-01\n---\n")
    before = rebuild(str(tmp_path))
    assert {Path(item["path"]).name for item in before["skipped"]} == {story.name, bug.name}
    assert all(any("invalid id" in reason for reason in item["reasons"]) for item in before["skipped"])
    plan = build_plan(project_dir=str(tmp_path))
    snapshot = create_snapshot(project_dir=str(tmp_path), base_paths=[str(backlog)])
    execute(plan, project_dir=str(tmp_path), snapshot_path=str(snapshot))
    after = rebuild(str(tmp_path))
    assert not story.exists()
    assert list((tmp_path / ".sweetclaude/product/roadmap/issues/done").glob("ISSUE-015-*.md"))
    assert after["ingested"] == 1
    assert bug.exists(), "unsupported typed BUG artifact must not be silently discarded"
    assert {Path(item["path"]).name for item in after["skipped"]} == {bug.name}


def test_shell_cache_checks_report_empty_result_and_continue(tmp_path):
    shim = tmp_path / "python3"
    shim.write_text(f'''#!/bin/sh
case " $* " in
  *" --query epic-stories "*) printf '[]\\n'; exit 0 ;;
esac
exec "{sys.executable}" "$@"
''')
    shim.chmod(0o755)
    result = subprocess.run(["bash", str(ROOT / "tests/test-cache.sh")], cwd=ROOT,
                            env={**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"]},
                            capture_output=True, text=True, timeout=90)
    assert result.returncode != 0
    assert "FAIL: wrong order" in result.stdout
    assert "[19]" in result.stdout and "Results:" in result.stdout
    assert "IndexError" not in result.stderr
