"""End-to-end dead-end totality tests.

Locks the contract that every maintenance detection path connects to a
resolution path. Corpus shapes mirror three real projects observed on
2026-06-10 (see docs/plans/2026-06-10-maintenance-dead-end-resolution-plan.md):

- graduation-blocked: compatibility mode, v4-compliant except one duplicate
  work-item ID, stale recovery.taxonomy.compatibility_exited flag (syncog)
- recovery-required: typed backlog dirs with legacy taxonomy prefixes
  (llm-session-harness)
- healthy-control: current layout, migration complete (syncog-mk2a)
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
DOCTOR = REPO_ROOT / "scripts" / "doctor.py"
RECOVER = REPO_ROOT / "scripts" / "recovery" / "recover_project.py"
MANIFEST = REPO_ROOT / "config" / "capability-manifest.yaml"
BOOTSTRAP_SKILL = REPO_ROOT / "skills" / "bootstrap" / "SKILL.md"
V4_COMPAT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "v4-compliant-compat"
SYNCOG_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "syncog-layout"


def _write_state(project: Path, **overrides) -> None:
    state_dir = project / ".sweetclaude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "schema_version": 2,
        "framework": {
            "installed_version": "4.2.7-beta",
            "migration_status": "deferred",
        },
        "paths": {"product_base": "docs/product"},
        "recovery": {
            "taxonomy": {
                "status": "stabilized-without-migration",
                "migration_required": False,
                "blind_taxonomy_migration_allowed": False,
            },
        },
    }
    for key, value in overrides.items():
        if value is None:
            state.pop(key, None)
        else:
            state[key] = value
    (state_dir / "sweetclaude.yaml").write_text(
        yaml.safe_dump(state, default_flow_style=False), encoding="utf-8",
    )


def _make_graduation_ready_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(V4_COMPAT_FIXTURE, project)
    _write_state(project)
    return project


def _make_graduation_blocked_project(tmp_path: Path) -> Path:
    project = _make_graduation_ready_project(tmp_path)
    # Mirrors syncog: the duplicate pair lives in done/ directories, where
    # graduation's characterize_project counts it but doctor's
    # file-diagnostics scan historically did not look.
    dupe = (
        project / "docs" / "product" / "roadmap" / "issues" / "done"
        / "ISSUE-003-duplicate.md"
    )
    dupe.parent.mkdir(parents=True, exist_ok=True)
    dupe.write_text(
        "---\nid: ISSUE-003\ntitle: Duplicate\ntype: bug-fix\nstatus: done\n"
        "created: '2026-05-25T00:00:00+00:00'\n---\n\nDuplicate.\n",
        encoding="utf-8",
    )
    state_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    state = yaml.safe_load(state_path.read_text())
    state["recovery"]["taxonomy"]["compatibility_exited"] = True
    state_path.write_text(yaml.safe_dump(state, default_flow_style=False))
    return project


def _make_recovery_required_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(SYNCOG_FIXTURE, project)
    (project / ".sweetclaude").mkdir(parents=True, exist_ok=True)
    (project / ".sweetclaude" / "artifact-privacy.yaml").write_text(
        "schema_version: 1\n"
        "categories:\n"
        "  product:\n"
        "    privacy: private\n"
        "    base_path: docs/product\n",
        encoding="utf-8",
    )
    _write_state(project, recovery=None)
    state_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    state = yaml.safe_load(state_path.read_text())
    state["framework"]["migration_status"] = "incomplete"
    state_path.write_text(yaml.safe_dump(state, default_flow_style=False))
    return project


def _make_compat_mode_project(tmp_path: Path) -> Path:
    """Typed legacy layout, stabilized without migration: structural blockers
    (old prefixes) keep this honestly in compatibility mode."""
    project = tmp_path / "project"
    shutil.copytree(SYNCOG_FIXTURE, project)
    (project / ".sweetclaude").mkdir(parents=True, exist_ok=True)
    (project / ".sweetclaude" / "artifact-privacy.yaml").write_text(
        "schema_version: 1\n"
        "categories:\n"
        "  product:\n"
        "    privacy: private\n"
        "    base_path: docs/product\n",
        encoding="utf-8",
    )
    _write_state(project)
    return project


def _make_healthy_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(V4_COMPAT_FIXTURE, project)
    _write_state(
        project,
        framework={
            "installed_version": "4.2.7-beta",
            "migration_status": "complete",
        },
        recovery=None,
    )
    return project


def _run_json(script: Path, *args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(script), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    return json.loads(result.stdout)


def _guard(project: Path) -> dict:
    return _run_json(RECOVER, "guard", "--project-dir", str(project))


def _scan(project: Path) -> dict:
    return _run_json(DOCTOR, "scan", "--project-dir", str(project))


def _maintenance_route(project: Path) -> dict:
    payload = _run_json(DOCTOR, "maintenance-route", "--project-dir", str(project))
    return payload.get("maintenance_route", payload)


# --- Step 1 contract: guard propagates graduation blockers ---


def test_guard_reports_graduation_blocked_with_blockers(tmp_path):
    project = _make_graduation_blocked_project(tmp_path)
    guard = _guard(project)

    assert guard["status"] == "graduation-blocked"
    blocker_codes = [b["code"] for b in guard["graduation_blockers"]]
    assert "duplicate-ids" in blocker_codes


def test_guard_blockers_carry_resolution(tmp_path):
    project = _make_graduation_blocked_project(tmp_path)
    guard = _guard(project)

    for blocker in guard["graduation_blockers"]:
        resolution = blocker.get("resolution") or {}
        assert resolution.get("capability_id"), (
            f"blocker {blocker.get('code')} has no resolving capability"
        )
        assert resolution.get("command"), (
            f"blocker {blocker.get('code')} has no runnable resolution command"
        )


def test_guard_reports_graduation_available_when_unblocked(tmp_path):
    project = _make_graduation_ready_project(tmp_path)
    guard = _guard(project)

    assert guard["status"] == "graduation-available"
    assert guard["project_shape"] == "graduation_candidate"


# --- Step 2 contract: no fake exits, scan and route agree ---


@pytest.mark.parametrize("make_project", [
    _make_graduation_blocked_project,
    _make_compat_mode_project,
])
def test_scan_never_offers_the_flag_write_exit(tmp_path, make_project):
    project = make_project(tmp_path)
    scan = _scan(project)

    for finding in scan["findings"]:
        recipe = finding.get("fix_recipe") or {}
        key_path = recipe.get("key_path") or []
        assert "compatibility_exited" not in key_path, (
            "scan offers the compatibility_exited flag write, but the guard "
            "never reads that flag for status — the only real exit is "
            "graduation"
        )
        assert recipe.get("type") != "exit_compatibility_mode", (
            "scan offers exit_compatibility_mode, a no-op exit; the only "
            "real exit is graduation"
        )


def test_scan_surfaces_graduation_blocker_with_resolution(tmp_path):
    project = _make_graduation_blocked_project(tmp_path)
    scan = _scan(project)

    blocker_findings = [
        f for f in scan["findings"]
        if "duplicate" in json.dumps(f).lower()
    ]
    assert blocker_findings, (
        "doctor scan does not surface the duplicate-ID graduation blocker"
    )
    assert any(
        f.get("fix_type") in ("auto", "prompted") for f in blocker_findings
    ), "the duplicate-ID blocker finding has no resolution path"


def test_route_names_blockers_on_blocked_project(tmp_path):
    project = _make_graduation_blocked_project(tmp_path)
    route = _maintenance_route(project)

    assert route["status"] == "graduation-blocked"
    blocker_codes = [b["code"] for b in route.get("graduation_blockers", [])]
    assert "duplicate-ids" in blocker_codes
    primary = route.get("primary_action") or {}
    assert primary.get("id") != "continue-compatibility-mode", (
        "route tells the user to stay in compatibility mode while a fixable "
        "blocker is the only thing preventing graduation"
    )


# --- Step 3 contract: bootstrap handles every guard status ---


def test_bootstrap_skill_handles_every_guard_status():
    manifest = yaml.safe_load(MANIFEST.read_text())
    statuses = {
        str(cfg.get("guard_status"))
        for cfg in (manifest.get("project_shapes") or {}).values()
        if cfg.get("guard_status")
    }
    statuses.discard("ok")
    statuses.add("guard-unavailable")

    skill_text = BOOTSTRAP_SKILL.read_text()
    missing = sorted(s for s in statuses if s not in skill_text)
    assert not missing, (
        f"bootstrap SKILL.md does not handle guard status(es): {missing}. "
        "Every status the guard can emit needs an explicit route or an "
        "honest explanation in the entry point."
    )


# --- Step 4 contract: recover acknowledges schema drift ---


def test_diagnose_reports_state_schema_drift(tmp_path):
    project = _make_healthy_project(tmp_path)
    state_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    state = yaml.safe_load(state_path.read_text())
    state["schema_version"] = 1
    state_path.write_text(yaml.safe_dump(state, default_flow_style=False))

    diagnosis = _run_json(RECOVER, "diagnose", "--project-dir", str(project))
    codes = [fc["code"] for fc in diagnosis.get("failure_classes", [])]
    assert "state-schema-drift" in codes, (
        "diagnose says 'no recovery needed' on a project whose state schema "
        "is behind the registry target"
    )


# --- Step 6 contract: the full chain resolves ---


def test_blocked_graduation_resolves_end_to_end(tmp_path):
    project = _make_graduation_blocked_project(tmp_path)

    guard = _guard(project)
    assert guard["status"] == "graduation-blocked"

    for blocker in guard["graduation_blockers"]:
        command = blocker["resolution"]["command"].replace(
            "<project>", str(project),
        )
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"resolution command for {blocker['code']} failed: {result.stderr}"
        )

    check = _run_json(RECOVER, "graduation-check", "--project-dir", str(project))
    assert check["graduation_allowed"] is True, (
        f"blockers remain after running their resolutions: {check.get('blockers')}"
    )

    _run_json(RECOVER, "graduate", "--project-dir", str(project))

    final_guard = _guard(project)
    assert final_guard["status"] == "ok"
    assert final_guard["project_shape"] == "current_layout"


def test_misnamed_file_resolves_by_rename_not_renumber(tmp_path):
    """Syncog's real case: the 'duplicate' is a filename collision where the
    file's frontmatter id is a DIFFERENT, valid id. The fix is renaming the
    file to match its frontmatter — renumbering would clobber a valid id that
    other artifacts may reference."""
    project = _make_graduation_ready_project(tmp_path)
    misnamed = (
        project / "docs" / "product" / "roadmap" / "issues" / "done"
        / "ISSUE-003-misnamed.md"
    )
    misnamed.parent.mkdir(parents=True, exist_ok=True)
    misnamed.write_text(
        "---\nid: ISSUE-777\ntitle: Misnamed\ntype: bug-fix\nstatus: done\n"
        "created: '2026-05-25T00:00:00+00:00'\n---\n\nMisnamed file.\n",
        encoding="utf-8",
    )

    guard = _guard(project)
    assert guard["status"] == "graduation-blocked"
    blockers = {b["code"]: b for b in guard["graduation_blockers"]}
    assert "duplicate-ids" in blockers

    command = blockers["duplicate-ids"]["resolution"]["command"].replace(
        "<project>", str(project),
    )
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"resolution failed: {result.stderr}"

    renamed = misnamed.parent / "ISSUE-777-misnamed.md"
    assert renamed.is_file(), "misnamed file must be renamed to its frontmatter id"
    assert not misnamed.exists()
    fm = yaml.safe_load(renamed.read_text().split("---", 2)[1])
    assert fm["id"] == "ISSUE-777", "frontmatter id must be preserved, not renumbered"

    keeper = project / "docs" / "product" / "backlog" / "done" / "ISSUE-003-completed-item.md"
    keeper_fm = yaml.safe_load(keeper.read_text().split("---", 2)[1])
    assert keeper_fm["id"] == "ISSUE-003", "the canonical copy must be untouched"

    check = _run_json(RECOVER, "graduation-check", "--project-dir", str(project))
    assert check["graduation_allowed"] is True

    _run_json(RECOVER, "graduate", "--project-dir", str(project))
    assert _guard(project)["status"] == "ok"


def test_missing_skills_yaml_is_not_reported_at_all(tmp_path):
    """This asserted the finding auto-fixed. Now it asserts there is no finding.

    The dead end was real — the fix pointed at a generator that did not exist —
    but giving it a working auto-fix treated the symptom. v4 onboarding never
    writes skills.yaml; the six data-owning skills create it on first use, the
    same lazy lifecycle as phase.yaml, which doctor does not flag. So a healthy
    project was being told to run a repair for a file that was correctly absent
    (ISSUE-284).

    Removing a detection is a resolution to a dead end, and a better one than a
    fix that reconciles the user to noise.
    """
    project = _make_healthy_project(tmp_path)
    assert not (project / ".sweetclaude" / "state" / "skills.yaml").exists()

    ids = [f["id"] for f in _scan(project)["findings"]]

    assert "onboarding-state:missing:skills.yaml" not in ids, ids


# --- characterization locks: paths that already work must keep working ---


def test_healthy_project_guard_is_ok(tmp_path):
    project = _make_healthy_project(tmp_path)
    guard = _guard(project)

    assert guard["status"] == "ok"
    assert guard["project_shape"] == "current_layout"


def test_recovery_required_project_routes_to_recover(tmp_path):
    project = _make_recovery_required_project(tmp_path)
    guard = _guard(project)

    assert guard["status"] == "run-recover"
    assert guard["project_shape"] == "recovery_required"

    route = _maintenance_route(project)
    assert route["status"] == "recovery-available"
    primary = route.get("primary_action") or {}
    assert primary.get("delegate_skill") == "sweetclaude:recover"
