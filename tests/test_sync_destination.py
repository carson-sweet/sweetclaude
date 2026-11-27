"""Developer sync must never resolve an unrelated or ambiguous plugin."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def fixture(tmp_path):
    home = tmp_path / "home"
    config = home / ".claude"
    (config / "plugins").mkdir(parents=True)
    repo = tmp_path / "repo"
    for name in ("scripts", "tests", "hooks", "skills", "skill-library", "config"):
        (repo / name).mkdir(parents=True)
    shutil.copy(ROOT / "scripts/sync-to-installed.sh", repo / "scripts/sync-to-installed.sh")
    test = repo / "tests/test-hooks.sh"
    test.write_text("#!/bin/sh\nexit 0\n")
    test.chmod(0o755)
    (repo / "hooks/sweet.sh").write_text("#!/bin/sh\necho sweet\n")
    (repo / "scripts/sentinel.py").write_text("# sweet\n")
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    return home, config, repo, project


def bundle(config, name, manifest="sweetclaude"):
    path = config / "plugins/cache" / name / "1.0"
    (path / "hooks").mkdir(parents=True)
    (path / "hooks/original.sh").write_text(f"{name} original\n")
    (path / ".claude-plugin").mkdir()
    (path / ".claude-plugin/plugin.json").write_text(json.dumps({"name": manifest}))
    return path


def run(repo, home, project, *args):
    return subprocess.run(["bash", str(repo / "scripts/sync-to-installed.sh"), *args],
                          cwd=project, env={**os.environ, "HOME": str(home)}, capture_output=True,
                          text=True, timeout=30)


def registry(config, entries):
    (config / "plugins/installed_plugins.json").write_text(json.dumps({"plugins": entries}))


def test_sync_targets_sweetclaude_when_other_plugin_is_newer(tmp_path):
    home, config, repo, project = fixture(tmp_path)
    sweet = bundle(config, "sweetclaude")
    other = bundle(config, "other", "other")
    registry(config, {"sweetclaude@stable": [{"scope": "user", "installPath": str(sweet), "lastUpdated": "2025"}],
                      "other@vendor": [{"scope": "user", "installPath": str(other), "lastUpdated": "2026"}]})
    before = (other / "hooks/original.sh").read_bytes()
    result = run(repo, home, project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (sweet / "hooks/sweet.sh").exists()
    assert (other / "hooks/original.sh").read_bytes() == before
    assert not (other / "hooks/sweet.sh").exists()


def test_no_sweetclaude_entry_fails_before_writes(tmp_path):
    home, config, repo, project = fixture(tmp_path)
    other = bundle(config, "other", "other")
    registry(config, {"other@vendor": [{"scope": "user", "installPath": str(other)}]})
    before = (other / "hooks/original.sh").read_bytes()
    result = run(repo, home, project)
    assert result.returncode != 0
    assert (other / "hooks/original.sh").read_bytes() == before
    assert not (other / "hooks.bak").exists()


def test_ambiguous_scopes_fail_and_explicit_local_selects_project(tmp_path):
    home, config, repo, project = fixture(tmp_path)
    user = bundle(config, "user")
    local = bundle(config, "local")
    registry(config, {"sweetclaude@stable": [{"scope": "user", "installPath": str(user)},
        {"scope": "local", "projectPath": str(project), "installPath": str(local)}]})
    assert run(repo, home, project, "--dry-run").returncode != 0
    result = run(repo, home, project, "--scope", "local", "--plugin-key", "sweetclaude@stable", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert str(local) in result.stdout
    assert (user / "hooks/original.sh").exists() and (local / "hooks/original.sh").exists()


@pytest.mark.parametrize("kind", ["wrong-identity", "outside", "symlink"])
def test_invalid_target_fails_before_mutation(tmp_path, kind):
    home, config, repo, project = fixture(tmp_path)
    target = bundle(config, "candidate", "other" if kind == "wrong-identity" else "sweetclaude")
    if kind == "outside":
        target = tmp_path / "outside"
        (target / "hooks").mkdir(parents=True)
        (target / ".claude-plugin").mkdir()
        (target / ".claude-plugin/plugin.json").write_text('{"name":"sweetclaude"}')
    elif kind == "symlink":
        link = config / "plugins/cache/link"
        link.symlink_to(target, target_is_directory=True)
        target = link
    registry(config, {"sweetclaude@stable": [{"scope": "user", "installPath": str(target)}]})
    result = run(repo, home, project)
    assert result.returncode != 0
    assert not (target / "hooks.bak").exists()


def test_explicit_local_sync_does_not_change_user_bundle(tmp_path):
    home, config, repo, project = fixture(tmp_path)
    user = bundle(config, "user")
    local = bundle(config, "local")
    registry(config, {"sweetclaude@stable": [{"scope": "user", "installPath": str(user)},
        {"scope": "local", "projectPath": str(project), "installPath": str(local)}]})
    result = run(repo, home, project, "--scope", "local", "--plugin-key", "sweetclaude@stable")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (local / "hooks/sweet.sh").exists()
    assert (user / "hooks/original.sh").read_text() == "user original\n"
    assert not (user / "hooks.bak").exists()


def test_symlinked_hooks_directory_is_rejected_before_sync(tmp_path):
    home, config, repo, project = fixture(tmp_path)
    target = bundle(config, "candidate")
    external = tmp_path / "external"
    external.mkdir()
    (external / "sentinel").write_text("keep")
    (external / "original.sh").write_text("external original")
    shutil.rmtree(target / "hooks")
    (target / "hooks").symlink_to(external, target_is_directory=True)
    registry(config, {"sweetclaude@stable": [{"scope": "user", "installPath": str(target)}]})
    result = run(repo, home, project)
    assert result.returncode != 0
    assert "symlink" in result.stderr.lower()
    assert (external / "sentinel").read_text() == "keep"
    assert not (target / "hooks.bak").exists()


@pytest.mark.parametrize("name", ["skills", "skill-library", "scripts", "config"])
def test_symlinked_sync_destination_fails_before_any_write(tmp_path, name):
    home, config, repo, project = fixture(tmp_path)
    target = bundle(config, "candidate")
    external = tmp_path / "external"
    external.mkdir()
    (external / "keep").write_text("original")
    (target / name).symlink_to(external, target_is_directory=True)
    registry(config, {"sweetclaude@stable": [{"scope": "user", "installPath": str(target)}]})
    result = run(repo, home, project)
    assert result.returncode != 0
    assert "symlink" in result.stderr.lower()
    assert (external / "keep").read_text() == "original"
    assert (target / "hooks/original.sh").read_text() == "candidate original\n"


def test_symlinked_version_destination_fails_before_any_write(tmp_path):
    home, config, repo, project = fixture(tmp_path)
    target = bundle(config, "candidate")
    external = tmp_path / "external"
    external.mkdir()
    (external / "keep").write_text("original")
    (target.parent / "2.0.0").symlink_to(external, target_is_directory=True)
    (repo / "package.json").write_text('{"version":"2.0.0"}')
    registry(config, {"sweetclaude@stable": [{"scope": "user", "installPath": str(target)}]})
    result = run(repo, home, project)
    assert result.returncode != 0
    assert "symlink" in result.stderr.lower()
    assert (external / "keep").read_text() == "original"
    assert (target / "hooks/original.sh").exists()
