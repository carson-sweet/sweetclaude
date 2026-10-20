"""Coverage for the update orchestrator (ISSUE-256).

scripts/update.py rewrites the installed plugin tree. It sat at 24% across 486
statements — the largest single gap in the repo, and the path behind the
4.2.10-beta incident.

Existing suites cover the beta-channel nudge and retirement
(test_beta_migration_nudge.py, test_beta_channel_retirement.py). This covers
the command surface those do not touch: version comparison, the safety check
for removed skills, the major-version gate, sync, cleanup, and project-check.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
SCRIPT = REPO_ROOT / "scripts" / "update.py"


def _load():
    spec = importlib.util.spec_from_file_location("sc_update", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load()


def _capture(fn, args) -> dict:
    """Run a cmd_* function and return the JSON it printed."""
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(args)
    return json.loads(buf.getvalue())


# --- version helpers -----------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("4.5.2", 4), ("v4.5.2", 4), ("3.18.2", 3), ("10.0.0", 10),
    ("", 0), ("garbage", 0), (None, 0),
])
def test_major_version(raw, expected) -> None:
    assert mod._major_version(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("4.5.2", (4, 5, 2)), ("v4.5.2", (4, 5, 2)), ("4.5.2-beta", (4, 5, 2)),
])
def test_semver_tuple_parses(raw, expected) -> None:
    assert mod._semver_tuple(raw) == expected


@pytest.mark.parametrize("raw", ["", None, "not-a-version", "4.5", "abc"])
def test_semver_tuple_returns_none_for_unparseable(raw) -> None:
    assert mod._semver_tuple(raw) is None


@pytest.mark.parametrize("raw,expected", [
    ("4.5.2-beta", True), ("4.5.2-rc1", True), ("4.5.2-alpha", True),
    ("4.5.2-BETA", True), ("4.5.2", False), ("", False), (None, False),
])
def test_is_prerelease(raw, expected) -> None:
    """ISSUE-248: a stable install must never be offered a prerelease, so this
    predicate decides whether an offer is suppressed."""
    assert mod._is_prerelease(raw) is expected


# --- json sanitising -----------------------------------------------------

def test_sanitize_for_json_flattens_newlines_in_strings() -> None:
    """Output is echoed through zsh by the update skill; a raw newline in a
    JSON string value breaks the caller's parse."""
    out = mod._sanitize_for_json({"msg": "line one\nline two\r"})
    assert "\n" not in out["msg"]
    assert "\r" not in out["msg"]
    assert out["msg"] == "line one | line two"


def test_sanitize_for_json_recurses_into_dicts_and_lists() -> None:
    out = mod._sanitize_for_json({
        "nested": {"msg": "a\nb"},
        "items": ["c\nd", {"msg": "e\nf"}, 3],
    })
    assert out["nested"]["msg"] == "a | b"
    assert out["items"][0] == "c | d"
    assert out["items"][1]["msg"] == "e | f"
    assert out["items"][2] == 3
    json.dumps(out)


def test_sanitize_for_json_leaves_non_strings_alone() -> None:
    out = mod._sanitize_for_json({"n": 1, "b": True, "none": None})
    assert out == {"n": 1, "b": True, "none": None}


# --- major gate ----------------------------------------------------------

def test_major_gate_fires_on_the_v3_to_v4_boundary() -> None:
    """The gate is specifically the 3 -> 4 migration, not any major bump."""
    out = _capture(mod.cmd_major_gate,
                   argparse.Namespace(installed_version="3.18.2",
                                      incoming_version="4.0.0"))
    assert out["gate_applies"] is True
    assert out["current_major"] == 3
    assert out["incoming_major"] == 4


def test_major_gate_ignores_a_minor_bump() -> None:
    out = _capture(mod.cmd_major_gate,
                   argparse.Namespace(installed_version="4.5.1",
                                      incoming_version="4.5.2"))
    assert out["gate_applies"] is False


def test_major_gate_does_not_fire_on_a_downgrade() -> None:
    out = _capture(mod.cmd_major_gate,
                   argparse.Namespace(installed_version="4.5.2",
                                      incoming_version="3.18.2"))
    assert out["gate_applies"] is False


def test_major_gate_fires_its_own_notice_on_the_v4_to_v5_boundary() -> None:
    out = _capture(mod.cmd_major_gate,
                   argparse.Namespace(installed_version="4.0.0",
                                      incoming_version="5.0.0"))
    assert out["gate_applies"] is True
    assert out["gate"] == "v4-to-v5"
    assert out["current_major"] == 4
    assert out["incoming_major"] == 5


def test_major_gate_names_the_v3_to_v4_gate() -> None:
    out = _capture(mod.cmd_major_gate,
                   argparse.Namespace(installed_version="3.18.2",
                                      incoming_version="4.0.0"))
    assert out["gate"] == "v3-to-v4"


def test_major_gate_keeps_the_v3_gate_for_a_v3_to_v5_jump() -> None:
    out = _capture(mod.cmd_major_gate,
                   argparse.Namespace(installed_version="3.18.2",
                                      incoming_version="5.0.0"))
    assert out["gate_applies"] is True
    assert out["gate"] == "v3-to-v4"


def test_major_gate_has_no_gate_within_v5() -> None:
    out = _capture(mod.cmd_major_gate,
                   argparse.Namespace(installed_version="5.0.0",
                                      incoming_version="5.1.0"))
    assert out["gate_applies"] is False
    assert out["gate"] is None


def test_update_skill_presents_a_distinct_v5_notice() -> None:
    skill = (REPO_ROOT / "skill-library" / "configure" / "update" / "SKILL.md").read_text(encoding="utf-8")
    step = skill.split("## Step 2c: Major version gate", 1)[1].split("\n## Step 3", 1)[0]
    assert "`v3-to-v4`" in step
    assert "`v4-to-v5`" in step
    assert "SweetClaude 5.0" in step
    for command in ("go", "plan", "design", "build", "maintain",
                    "configure", "utils", "status", "help"):
        assert f"/sweetclaude:{command}`" in step
    assert "`/sweetclaude:configure doctor`" in step
    assert "project data does not change" in step


def test_major_gate_tolerates_unparseable_versions() -> None:
    out = _capture(mod.cmd_major_gate,
                   argparse.Namespace(installed_version="",
                                      incoming_version="garbage"))
    assert out["current_major"] == 0
    assert out["incoming_major"] == 0


# --- safety check --------------------------------------------------------

@pytest.fixture
def install_pair(tmp_path: Path):
    """A source tree and an install tree, plus a project directory."""
    source = tmp_path / "source"
    install = tmp_path / "install"
    project = tmp_path / "project"
    for base in (source, install):
        (base / "skills").mkdir(parents=True)
    (project / ".sweetclaude").mkdir(parents=True)

    def add_skill(base: Path, name: str) -> None:
        (base / "skills" / name).mkdir(parents=True, exist_ok=True)
        (base / "skills" / name / "SKILL.md").write_text("---\n---\n", encoding="utf-8")

    return source, install, project, add_skill


def test_safety_check_skips_a_project_without_sweetclaude(tmp_path: Path) -> None:
    args = argparse.Namespace(source=str(tmp_path), install_path=str(tmp_path),
                              project_dir=tmp_path / "nothing-here")
    out = _capture(mod.cmd_safety_check, args)
    assert out["ok"] is True
    assert out["has_live_artifacts"] is False


def test_safety_check_reports_no_removals_when_trees_match(install_pair) -> None:
    source, install, project, add_skill = install_pair
    add_skill(source, "product-milestones")
    add_skill(install, "product-milestones")

    args = argparse.Namespace(source=str(source), install_path=str(install),
                              project_dir=project)
    out = _capture(mod.cmd_safety_check, args)
    assert out["removed_skills"] == []


def test_safety_check_detects_a_removed_skill(install_pair) -> None:
    source, install, project, add_skill = install_pair
    add_skill(install, "product-milestones")  # present installed, absent in source

    args = argparse.Namespace(source=str(source), install_path=str(install),
                              project_dir=project)
    out = _capture(mod.cmd_safety_check, args)
    assert "product-milestones" in out["removed_skills"]


def test_safety_check_flags_live_artifacts_for_a_removed_skill(install_pair) -> None:
    """The point of the check: removing a skill whose artifacts the user still
    has must be surfaced before the sync deletes it."""
    source, install, project, add_skill = install_pair
    add_skill(install, "product-milestones")
    milestones = project / ".sweetclaude" / "product" / "milestones"
    milestones.mkdir(parents=True)
    (milestones / "MS-001-launch.md").write_text("# MS-001\n", encoding="utf-8")

    args = argparse.Namespace(source=str(source), install_path=str(install),
                              project_dir=project)
    out = _capture(mod.cmd_safety_check, args)

    assert out["has_live_artifacts"] is True
    assert any(a["skill"] == "product-milestones" for a in out["affected"])


def test_safety_check_reports_no_live_artifacts_when_none_exist(install_pair) -> None:
    source, install, project, add_skill = install_pair
    add_skill(install, "product-milestones")

    args = argparse.Namespace(source=str(source), install_path=str(install),
                              project_dir=project)
    out = _capture(mod.cmd_safety_check, args)
    assert out["removed_skills"] == ["product-milestones"]
    assert out["has_live_artifacts"] is False


def test_safety_check_honours_a_relocated_product_base(install_pair) -> None:
    """artifact-privacy.yaml can move the product tree; the check must follow
    it or it looks in the wrong place and reports a false all-clear."""
    source, install, project, add_skill = install_pair
    add_skill(install, "product-milestones")
    (project / ".sweetclaude" / "artifact-privacy.yaml").write_text(
        yaml.safe_dump({"categories": {"product": {"base_path": "docs/product"}}}),
        encoding="utf-8")
    milestones = project / "docs" / "product" / "milestones"
    milestones.mkdir(parents=True)
    (milestones / "MS-001-launch.md").write_text("# MS-001\n", encoding="utf-8")

    args = argparse.Namespace(source=str(source), install_path=str(install),
                              project_dir=project)
    out = _capture(mod.cmd_safety_check, args)
    assert out["has_live_artifacts"] is True


def test_safety_check_survives_a_corrupt_privacy_manifest(install_pair) -> None:
    source, install, project, add_skill = install_pair
    add_skill(install, "product-milestones")
    (project / ".sweetclaude" / "artifact-privacy.yaml").write_text(
        "{ not: valid: yaml", encoding="utf-8")

    args = argparse.Namespace(source=str(source), install_path=str(install),
                              project_dir=project)
    out = _capture(mod.cmd_safety_check, args)
    assert out["ok"] is True


# --- cleanup -------------------------------------------------------------

def test_cleanup_removes_a_temp_directory() -> None:
    import tempfile

    tmpdir = tempfile.mkdtemp()
    (Path(tmpdir) / "file.txt").write_text("x", encoding="utf-8")

    out = _capture(mod.cmd_cleanup, argparse.Namespace(tmpdir=tmpdir))

    assert out["ok"] is True
    assert not Path(tmpdir).exists()


def test_cleanup_refuses_a_path_outside_the_temp_base(tmp_path: Path, monkeypatch) -> None:
    """Guard against rmtree on an arbitrary path — the check that keeps a bad
    --tmpdir from deleting a real directory.

    pytest's tmp_path already lives under the system temp base, so the temp
    base is repointed elsewhere to put the victim genuinely outside it.
    """
    victim = tmp_path / "not-a-temp-dir"
    victim.mkdir()
    (victim / "precious.txt").write_text("do not delete\n", encoding="utf-8")

    elsewhere = tmp_path / "other-temp-base"
    elsewhere.mkdir()
    monkeypatch.setattr(mod.tempfile, "gettempdir", lambda: str(elsewhere))

    out = _capture(mod.cmd_cleanup, argparse.Namespace(tmpdir=str(victim)))

    assert out["ok"] is False
    assert victim.exists(), "cleanup deleted a directory outside the temp base"
    assert (victim / "precious.txt").read_text(encoding="utf-8") == "do not delete\n"


def test_cleanup_refuses_an_empty_path() -> None:
    out = _capture(mod.cmd_cleanup, argparse.Namespace(tmpdir=""))
    assert out["ok"] is False


def test_cleanup_refuses_the_temp_base_itself() -> None:
    import tempfile

    out = _capture(mod.cmd_cleanup,
                   argparse.Namespace(tmpdir=tempfile.gettempdir()))
    assert out["ok"] is False, "cleanup would have removed the whole temp base"


# --- project check -------------------------------------------------------

def test_project_check_skips_an_unconfigured_project(tmp_path: Path) -> None:
    args = argparse.Namespace(project_dir=tmp_path, runner="", migrate_script="")
    out = _capture(mod.cmd_project_check, args)
    assert out["skipped"] is True
    assert out["reason"] == "no_project"


def test_project_check_runs_on_a_configured_project(tmp_path: Path) -> None:
    state = tmp_path / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text(
        yaml.safe_dump({"schema_version": 2}), encoding="utf-8")

    args = argparse.Namespace(project_dir=tmp_path, runner="", migrate_script="")
    out = _capture(mod.cmd_project_check, args)
    assert out["skipped"] is False
    assert out["ok"] is True
    assert out["drift_count"] == 0


# --- sync ----------------------------------------------------------------

def test_sync_copies_skills_and_hooks(tmp_path: Path) -> None:
    source = tmp_path / "source"
    install = tmp_path / "install"
    (source / "skills" / "demo").mkdir(parents=True)
    (source / "skills" / "demo" / "SKILL.md").write_text("---\n---\nx\n", encoding="utf-8")
    (source / "hooks").mkdir(parents=True)
    (source / "hooks" / "demo.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (source / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (source / ".claude-plugin").mkdir(parents=True)
    (source / ".claude-plugin" / "plugin.json").write_text(
        '{"name": "sweetclaude"}\n', encoding="utf-8")
    (source / "scripts").mkdir(parents=True)
    (source / "scripts" / "noop.py").write_text("# noop\n", encoding="utf-8")
    install.mkdir()

    args = argparse.Namespace(source=str(source), install_path=str(install),
                              plugin_root="")
    out = _capture(mod.cmd_sync, args)

    assert (install / "skills" / "demo" / "SKILL.md").is_file()
    assert (install / "hooks" / "demo.sh").is_file()
    assert (install / "CHANGELOG.md").is_file()
    assert (install / ".claude-plugin" / "plugin.json").is_file()
    assert not out.get("errors"), out["errors"]


def test_sync_reports_errors_rather_than_raising(tmp_path: Path) -> None:
    """A source that does not exist must produce a reported error, not an
    exception that aborts the update mid-way."""
    args = argparse.Namespace(source=str(tmp_path / "missing"),
                              install_path=str(tmp_path / "install"),
                              plugin_root="")
    out = _capture(mod.cmd_sync, args)
    assert isinstance(out, dict)


# --- CLI dispatch --------------------------------------------------------

def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, timeout=120)


def test_cli_requires_a_subcommand() -> None:
    r = _run_cli()
    assert r.returncode != 0


def test_cli_rejects_an_unknown_subcommand() -> None:
    r = _run_cli("not-a-real-command")
    assert r.returncode != 0


def test_cli_major_gate_emits_json() -> None:
    r = _run_cli("major-gate", "--installed-version", "3.18.2",
                 "--incoming-version", "4.0.0")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["gate_applies"] is True


def test_cli_cleanup_emits_json(tmp_path: Path) -> None:
    r = _run_cli("cleanup", "--tmpdir", str(tmp_path / "nope"))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["ok"] is False


# --- changelog fallback (ISSUE-246) --------------------------------------

def test_top_changelog_section_returns_the_first_release_block(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\nintro text\n\n---\n\n"
        "## [4.5.2] — 2026-08-03\n\nnewest notes\n\n"
        "## [4.5.1] — 2026-07-15\n\nolder notes\n",
        encoding="utf-8")

    section = mod._top_changelog_section(str(tmp_path))

    assert "4.5.2" in section
    assert "newest notes" in section
    assert "older notes" not in section, "fallback bled into the previous release"


def test_top_changelog_section_strips_horizontal_rules(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text(
        "## [4.5.2] — 2026-08-03\n\nnotes\n\n---\n\n## [4.5.1] — x\n", encoding="utf-8")
    assert "---" not in mod._top_changelog_section(str(tmp_path))


def test_top_changelog_section_is_empty_without_a_changelog(tmp_path: Path) -> None:
    """Shallow clones may lack it; the caller must get "" rather than raise."""
    assert mod._top_changelog_section(str(tmp_path)) == ""


def test_top_changelog_section_is_empty_when_no_release_heading(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\nno sections yet\n",
                                           encoding="utf-8")
    assert mod._top_changelog_section(str(tmp_path)) == ""


# --- check (network mocked) ---------------------------------------------

class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def test_check_reports_clone_failure_without_raising(monkeypatch) -> None:
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    monkeypatch.setattr(mod, "_run",
                        lambda cmd, **kw: _Result(1, "", "fatal: repository not found"))

    out = _capture(mod.cmd_check, argparse.Namespace(
        ref="main", installed_sha="abc", repo="", install_path="", plugin_root=""))

    assert out["ok"] is False
    assert out["error"] == "clone_failed"
    assert out["auth_error"] is False


def test_check_flags_an_auth_failure_distinctly(monkeypatch) -> None:
    """An auth failure needs different user guidance than a missing repo."""
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    monkeypatch.setattr(mod, "_run",
                        lambda cmd, **kw: _Result(1, "", "Permission denied (publickey)"))

    out = _capture(mod.cmd_check, argparse.Namespace(
        ref="main", installed_sha="abc", repo="", install_path="", plugin_root=""))

    assert out["auth_error"] is True


def test_check_reports_up_to_date_when_sha_matches(monkeypatch, tmp_path: Path) -> None:
    sha = "deadbeef"

    def fake_run(cmd, **kw):
        if "clone" in cmd:
            target = cmd[-1] if "gh" not in cmd[0] else cmd[3]
            Path(target).mkdir(parents=True, exist_ok=True)
            (Path(target) / "package.json").write_text(
                '{"version": "4.5.2"}\n', encoding="utf-8")
            return _Result(0)
        if "rev-parse" in cmd:
            return _Result(0, sha + "\n")
        return _Result(0, "")

    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    monkeypatch.setattr(mod, "_run", fake_run)

    out = _capture(mod.cmd_check, argparse.Namespace(
        ref="main", installed_sha=sha, repo="", install_path="", plugin_root=""))

    assert out["ok"] is True
    assert out["up_to_date"] is True


def test_check_reports_a_new_version_with_changelog_fallback(
    monkeypatch, tmp_path: Path
) -> None:
    """ISSUE-246: a shallow clone makes the git-range log fail, so the top
    CHANGELOG section must fill in rather than leaving the notes blank."""
    def fake_run(cmd, **kw):
        if "clone" in cmd:
            target = cmd[-1] if "gh" not in cmd[0] else cmd[3]
            t = Path(target)
            t.mkdir(parents=True, exist_ok=True)
            (t / "package.json").write_text('{"version": "4.5.3"}\n', encoding="utf-8")
            (t / "CHANGELOG.md").write_text(
                "## [4.5.3] — 2026-08-09\n\nthe new notes\n", encoding="utf-8")
            return _Result(0)
        if "rev-parse" in cmd:
            return _Result(0, "newsha\n")
        if "log" in cmd:
            return _Result(128, "", "fatal: bad revision")
        return _Result(0, "")

    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    monkeypatch.setattr(mod, "_run", fake_run)

    out = _capture(mod.cmd_check, argparse.Namespace(
        ref="main", installed_sha="oldsha", repo="", install_path="", plugin_root=""))

    assert out["ok"] is True
    assert out["up_to_date"] is False
    assert out["new_version"] == "4.5.3"
    assert "the new notes" in out["changelog"]


def test_check_tolerates_an_unreadable_package_json(monkeypatch) -> None:
    def fake_run(cmd, **kw):
        if "clone" in cmd:
            Path(cmd[-1]).mkdir(parents=True, exist_ok=True)
            return _Result(0)
        if "rev-parse" in cmd:
            return _Result(0, "sha\n")
        return _Result(0, "")

    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    monkeypatch.setattr(mod, "_run", fake_run)

    out = _capture(mod.cmd_check, argparse.Namespace(
        ref="main", installed_sha="old", repo="", install_path="", plugin_root=""))

    assert out["new_version"] == "unknown"


# --- preflight (home redirected) ----------------------------------------

def test_preflight_runs_against_an_empty_home(monkeypatch, tmp_path: Path) -> None:
    """cmd_preflight reads and can rewrite ~/.claude/plugins/installed_plugins.json.
    Home is redirected so the real file is never touched."""
    fake_home = tmp_path / "home"
    (fake_home / ".claude" / "plugins").mkdir(parents=True)
    monkeypatch.setattr(mod.Path, "home", classmethod(lambda cls: fake_home))

    out = _capture(mod.cmd_preflight, argparse.Namespace(
        project_dir=tmp_path, plugin_root="", from_update=False))

    assert out["version_dir_healed"] is False
    assert "runner" in out


def test_preflight_ignores_a_corrupt_plugins_json(monkeypatch, tmp_path: Path) -> None:
    fake_home = tmp_path / "home"
    plugins = fake_home / ".claude" / "plugins"
    plugins.mkdir(parents=True)
    (plugins / "installed_plugins.json").write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(mod.Path, "home", classmethod(lambda cls: fake_home))

    out = _capture(mod.cmd_preflight, argparse.Namespace(
        project_dir=tmp_path, plugin_root="", from_update=False))

    assert out["version_dir_healed"] is False


def test_preflight_leaves_an_already_versioned_install_alone(
    monkeypatch, tmp_path: Path
) -> None:
    """The heal only fires when installPath is not already a version-named
    directory. ISSUE-207 removed the versionless assumption; this locks it."""
    fake_home = tmp_path / "home"
    plugins = fake_home / ".claude" / "plugins"
    plugins.mkdir(parents=True)
    install = tmp_path / "cache" / "sweetclaude" / "4.5.2"
    install.mkdir(parents=True)
    payload = {"plugins": {"sweetclaude-stable": [
        {"scope": "user", "installPath": str(install), "version": "4.5.2"}]}}
    (plugins / "installed_plugins.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(mod.Path, "home", classmethod(lambda cls: fake_home))

    out = _capture(mod.cmd_preflight, argparse.Namespace(
        project_dir=tmp_path, plugin_root="", from_update=False))

    assert out["version_dir_healed"] is False
    assert json.loads((plugins / "installed_plugins.json").read_text()) == payload
