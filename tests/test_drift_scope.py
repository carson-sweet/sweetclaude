"""Drift detection must use the active SweetClaude bundle."""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks/drift-gate.sh"


def test_active_local_bundle_runner_detects_drift_without_global_install(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "project"
    state = project / ".sweetclaude/state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text("framework: {}\n")
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    bundle = tmp_path / "bundle"
    runner = bundle / "scripts/migrations/runner.py"
    runner.parent.mkdir(parents=True)
    (bundle / ".claude-plugin").mkdir()
    (bundle / ".claude-plugin/plugin.json").write_text('{"name":"sweetclaude"}')
    runner.write_text('print("DRIFT_COUNT=1")\nprint("FINDING|state.yaml|v1->v2|chain=ok")\n')
    result = subprocess.run(["bash", str(HOOK)], cwd=project, env={**os.environ, "HOME": str(home),
                            "CLAUDE_PLUGIN_ROOT": str(bundle)}, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert (state / "pending-drift-decision.yaml").is_file()
    assert "drift detected" in json.loads(result.stdout)["systemMessage"].lower()
    assert not (home / ".claude").exists()


def test_scan_failures_emit_blocking_actionable_context(tmp_path):
    project = tmp_path / 'project'
    state = project / '.sweetclaude/state'
    state.mkdir(parents=True)
    (state / 'sweetclaude.yaml').write_text('framework: {}\n')
    subprocess.run(['git', 'init', '-q', str(project)], check=True)
    bundle = tmp_path / 'bundle'
    runner = bundle / 'scripts/migrations/runner.py'
    runner.parent.mkdir(parents=True)
    manifest = bundle / '.claude-plugin/plugin.json'
    manifest.parent.mkdir()
    manifest.write_text('{"name":"sweetclaude"}')
    env = {**os.environ, 'HOME': str(tmp_path), 'CLAUDE_PLUGIN_ROOT': str(bundle)}
    for source in (None, 'raise SystemExit(1)', 'print("garbage")', 'print("DRIFT_COUNT=garbage")', 'print("DRIFT_COUNT=2\\nFINDING|a|v1->v2|chain=ok")'):
        if source is None:
            runner.unlink(missing_ok=True)
        else:
            runner.write_text(source)
        result = subprocess.run(['bash', str(HOOK)], cwd=project, env=env, capture_output=True, text=True)
        context = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
        assert 'STOP' in context and 'drift' in context.lower()
        assert 'doctor' in context.lower()
        assert not (state / 'pending-drift-decision.yaml').exists()


def test_wrong_bundle_identity_never_executes_runner(tmp_path):
    project = tmp_path / 'project'
    state = project / '.sweetclaude/state'
    state.mkdir(parents=True)
    (state / 'sweetclaude.yaml').write_text('framework: {}\n')
    subprocess.run(['git', 'init', '-q', str(project)], check=True)
    bundle = tmp_path / 'bundle'
    runner = bundle / 'scripts/migrations/runner.py'
    runner.parent.mkdir(parents=True)
    marker = tmp_path / 'executed'
    runner.write_text(f'from pathlib import Path\nPath({str(marker)!r}).touch()\nprint("DRIFT_COUNT=0")')
    manifest = bundle / '.claude-plugin/plugin.json'
    manifest.parent.mkdir()
    manifest.write_text('{"name":"other"}')
    result = subprocess.run(['bash', str(HOOK)], cwd=project, env={**os.environ, 'CLAUDE_PLUGIN_ROOT': str(bundle)}, capture_output=True, text=True)
    assert 'STOP' in json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
    assert not marker.exists()


def test_opt_out_and_existing_decision_do_not_run_missing_runner(tmp_path):
    project = tmp_path / 'project'
    state = project / '.sweetclaude/state'
    state.mkdir(parents=True)
    (state / 'sweetclaude.yaml').write_text('framework: {}\n')
    subprocess.run(['git', 'init', '-q', str(project)], check=True)
    env = {**os.environ, 'CLAUDE_PLUGIN_ROOT': str(tmp_path / 'missing')}
    skip = project / '.sweetclaude-skip'
    skip.touch()
    result = subprocess.run(['bash', str(HOOK)], cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout == ''
    skip.unlink()
    (state / 'pending-drift-decision.yaml').write_text('case: A\ndrift_count: 2\n')
    result = subprocess.run(['bash', str(HOOK)], cwd=project, env=env, capture_output=True, text=True)
    assert 'drift detected' in json.loads(result.stdout)['systemMessage'].lower()
