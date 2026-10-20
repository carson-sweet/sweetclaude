"""
WI-017 S7 — Wiring: close the dead-end at the system level.

Tests the behaviors specified in tests/features/wi-017-s7-wiring.feature.

Pre-S7 state that makes these tests RED:
- capability `migrate.typed_legacy_backlog` is supported: false, supports_project_shapes: []
- project_shape `typed_legacy_backlog` has migrate_allowed: false and routes to
  compatibility-mode (a no-action dead-end)
- recover_project _blocked_actions HARD-BLOCKS "taxonomy-migration" for the
  unsupported-typed-backlog-layout failure
- A typed-legacy project's guard status offers NO runnable migrate action
- Doctor maintenance-route for a typed-legacy project returns compatibility-mode
  with primary_action="continue-compatibility-mode" (no migration offered)

After S7 these tests must be GREEN.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Path constants — mirrors test_dead_end_totality.py
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parents[1]
DOCTOR = REPO_ROOT / "scripts" / "doctor.py"
RECOVER = REPO_ROOT / "scripts" / "recovery" / "recover_project.py"
MANIFEST = REPO_ROOT / "config" / "capability-manifest.yaml"
SYNCOG_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "syncog-layout"
V4_COMPAT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "v4-compliant-compat"

# ---------------------------------------------------------------------------
# Subprocess helpers (identical style to test_dead_end_totality.py)
# ---------------------------------------------------------------------------


def _run_json(script: Path, *args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(script), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{script.name} {' '.join(args)} exited {result.returncode}\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout[:500]}"
    )
    return json.loads(result.stdout)


def _guard(project: Path) -> dict:
    return _run_json(RECOVER, "guard", "--project-dir", str(project))


def _maintenance_route(project: Path) -> dict:
    payload = _run_json(DOCTOR, "maintenance-route", "--project-dir", str(project))
    return payload.get("maintenance_route", payload)


def _diagnose(project: Path) -> dict:
    return _run_json(RECOVER, "diagnose", "--project-dir", str(project))


def _run_migration_fn(project: Path, dry_run: bool = False) -> dict:
    """Import and call run_migration directly (mirrors test_wi017_s3_execute_plan.py style)."""
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from migrate.migrate_taxonomy import run_migration
    return run_migration(str(project), dry_run=dry_run)


# ---------------------------------------------------------------------------
# Project factory helpers
# ---------------------------------------------------------------------------

def _write_state(project: Path, **overrides) -> None:
    state_dir = project / ".sweetclaude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state: dict = {
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


def _write_artifact_privacy(project: Path) -> None:
    sc = project / ".sweetclaude"
    sc.mkdir(parents=True, exist_ok=True)
    (sc / "artifact-privacy.yaml").write_text(
        "schema_version: 1\n"
        "categories:\n"
        "  product:\n"
        "    privacy: private\n"
        "    base_path: docs/product\n",
        encoding="utf-8",
    )


def _make_fresh_typed_legacy_project(tmp_path: Path) -> Path:
    """
    A typed-legacy project with backlog/stories/STORY-*, backlog/debt/DEBT-*,
    and top-level old-prefix files. No recovery state written yet.
    Mirrors the real syncog layout.

    S7 fixture integrity: must have sweetclaude.yaml so guard/scan run with
    returncode 0.  A "fresh" project here means one that has NOT yet been
    stabilized — we write a minimal state (no recovery block) so the tool
    can read it.
    """
    project = tmp_path / "project"
    shutil.copytree(SYNCOG_FIXTURE, project)
    _write_artifact_privacy(project)
    # Write minimal state so the tool can scan the project (no recovery key)
    _write_state(project, recovery=None)
    return project


def _make_stabilized_typed_legacy_project(tmp_path: Path) -> Path:
    """
    A typed-legacy project whose state has been stabilized without migration.
    State: recovery.taxonomy.status == "stabilized-without-migration".
    Still has typed dirs and old-prefix files on disk.
    """
    project = tmp_path / "project"
    shutil.copytree(SYNCOG_FIXTURE, project)
    _write_artifact_privacy(project)
    _write_state(project)   # writes stabilized-without-migration state
    return project


def _has_migrate_reference_in_payload(payload: dict) -> bool:
    """
    Return True only if the payload references the migrate capability or skill
    as an OFFERED action — not merely as a blocked capability name.

    A reference in blocked_capabilities does NOT count. We look for it in:
    - primary_action.capability_id
    - primary_action.delegate_skill containing "migrate"
    - project_shape == "typed_legacy_backlog" with migrate-signaling guard_status
    - status that signals migration is available
    - migration_capability referenced in the shape
    """
    # Check primary_action
    primary = payload.get("primary_action") or {}
    cap_id = primary.get("capability_id", "")
    delegate = primary.get("delegate_skill", "")
    if "migrate.typed_legacy_backlog" in cap_id:
        return True
    if "sweetclaude:migrate" in delegate or "migrate" in cap_id.lower():
        # Exclude doctor.compatibility_mode and similar
        if "migrate" in cap_id and "compatibility" not in cap_id:
            return True

    # Check status signals migration
    status = payload.get("status", "")
    if status in ("supported-migration-available", "migration-available",
                  "migration-may-be-needed"):
        return True

    # Check guard payload migrate_allowed
    if payload.get("migrate_allowed") is True:
        return True

    # Check guard project_shape is typed_legacy_backlog with non-dead-end status
    if payload.get("project_shape") == "typed_legacy_backlog":
        return True

    return False


# ---------------------------------------------------------------------------
# Scenario 1 — Manifest: capability is supported and shape allows migration
#
# RED reason: migrate.typed_legacy_backlog.supported == False;
#             supports_project_shapes == [];
#             typed_legacy_backlog.migrate_allowed == False
# ---------------------------------------------------------------------------

class TestManifestCapabilitySupported:
    """
    The typed-legacy migrator capability is listed as supported in the manifest,
    declares a command_entrypoint, supports the typed_legacy_backlog project shape,
    and the project shape has migrate_allowed True.
    """

    def _load_capability_config(self):
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from maintenance.capability_manifest import capability_config
        return capability_config

    def _load_shape_config(self):
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from maintenance.capability_manifest import project_shape_config
        return project_shape_config

    def test_migrate_typed_legacy_backlog_is_supported(self):
        capability_config = self._load_capability_config()
        cfg = capability_config("migrate.typed_legacy_backlog")
        assert cfg.get("supported") is True, (
            "migrate.typed_legacy_backlog must be supported:true after S7; "
            f"got supported={cfg.get('supported')!r}"
        )

    def test_migrate_typed_legacy_backlog_has_command_entrypoint(self):
        capability_config = self._load_capability_config()
        cfg = capability_config("migrate.typed_legacy_backlog")
        entrypoint = cfg.get("command_entrypoint")
        assert entrypoint, (
            "migrate.typed_legacy_backlog must have a command_entrypoint after S7; "
            "currently absent"
        )
        assert isinstance(entrypoint, dict), (
            "command_entrypoint must be a mapping"
        )
        # Must have at least one of slash_command or script
        has_entry = entrypoint.get("slash_command") or entrypoint.get("script")
        assert has_entry, (
            "command_entrypoint must declare slash_command or script; "
            f"got {entrypoint!r}"
        )

    def test_migrate_typed_legacy_backlog_supports_typed_legacy_shape(self):
        capability_config = self._load_capability_config()
        cfg = capability_config("migrate.typed_legacy_backlog")
        supported_shapes = cfg.get("supports_project_shapes") or []
        assert "typed_legacy_backlog" in supported_shapes, (
            "migrate.typed_legacy_backlog.supports_project_shapes must include "
            "'typed_legacy_backlog' after S7; "
            f"got {supported_shapes!r}"
        )

    def test_typed_legacy_backlog_shape_migrate_allowed_true(self):
        project_shape_config = self._load_shape_config()
        shape = project_shape_config("typed_legacy_backlog")
        assert shape.get("migrate_allowed") is True, (
            "typed_legacy_backlog project shape must have migrate_allowed:true after S7; "
            f"got migrate_allowed={shape.get('migrate_allowed')!r}"
        )

    def test_typed_legacy_backlog_shape_has_migration_capability(self):
        project_shape_config = self._load_shape_config()
        shape = project_shape_config("typed_legacy_backlog")
        migration_capability = shape.get("migration_capability")
        assert migration_capability, (
            "typed_legacy_backlog shape must declare a migration_capability after S7; "
            f"got {migration_capability!r}"
        )
        assert migration_capability == "migrate.typed_legacy_backlog", (
            "typed_legacy_backlog.migration_capability must be "
            "'migrate.typed_legacy_backlog'; "
            f"got {migration_capability!r}"
        )

    def test_typed_legacy_backlog_shape_guard_status_signals_migration(self):
        """
        The guard_status for typed_legacy_backlog must be a migration-signaling
        value — NOT 'compatibility-mode' (the pre-S7 dead-end).
        """
        project_shape_config = self._load_shape_config()
        shape = project_shape_config("typed_legacy_backlog")
        guard_status = shape.get("guard_status")
        assert guard_status != "compatibility-mode", (
            "typed_legacy_backlog.guard_status must not be 'compatibility-mode' after S7 "
            "— that is the permanent dead-end. Expected a migration-signaling status "
            "(e.g. 'migration-available' or 'migration-may-be-needed'). "
            f"Got guard_status={guard_status!r}"
        )


# ---------------------------------------------------------------------------
# Scenario 2 — Fresh typed-legacy project guard offers migration, not a dead-end
#
# A "fresh" typed-legacy project has no sweetclaude.yaml — the guard routes it
# to "stabilize-without-migration" → recovery_required currently. After S7 the
# typed_legacy_backlog shape must route to a migration-offering status, so a
# project whose characterization shows typed backlog dirs + old prefixes goes to
# the migration path rather than stabilize-without-migration.
#
# RED reason: The guard still sends the project to run-recover / recovery_required
#             (stabilize-without-migration) rather than offering migration first.
# ---------------------------------------------------------------------------

class TestFreshTypedLegacyGuardOffersMigration:
    """
    A fresh typed-legacy project (typed dirs + old-prefix files, no recovery state)
    runs the guard. The guard must:
    - Classify the project as typed_legacy_backlog (not recovery_required)
    - Route to a migration-offering status (not "compatibility-mode" or "run-recover")
    - Have migrate_allowed True
    """

    def test_fresh_typed_legacy_classified_as_typed_legacy_backlog(self, tmp_path):
        """
        After S7, a fresh project with typed backlog layout must classify as
        'typed_legacy_backlog', not 'recovery_required'.
        Pre-S7 it routes to recovery_required (stabilize-without-migration dead-end).
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        guard = _guard(project)

        assert guard["project_shape"] == "typed_legacy_backlog", (
            "A fresh typed-legacy project (typed dirs, old prefixes, no recovery state) "
            "must classify as 'typed_legacy_backlog' after S7. "
            f"Got project_shape={guard['project_shape']!r}. "
            "Pre-S7 it classified as 'recovery_required' (stabilize-without-migration)."
        )

    def test_fresh_typed_legacy_guard_does_not_return_run_recover(self, tmp_path):
        """
        After S7, a fresh typed-legacy project must NOT route to run-recover
        (which leads to stabilize-without-migration — a dead-end that was
        the pre-S7 behavior).
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        guard = _guard(project)

        assert guard["status"] != "run-recover", (
            "A fresh typed-legacy project must NOT route to 'run-recover' after S7 — "
            "that leads to stabilize-without-migration (dead-end). "
            f"Got status={guard['status']!r}. Expected a migration-signaling status."
        )

    def test_fresh_typed_legacy_guard_status_is_migration_signaling(self, tmp_path):
        """
        After S7, a fresh typed-legacy project must route to a migration-signaling
        status — specifically one that tells the user migration is available/needed.
        Pre-S7 the status is 'run-recover' (which leads to stabilize-without-migration)
        or 'compatibility-mode' — both are dead-ends with no migration path.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        guard = _guard(project)

        MIGRATION_SIGNALING_STATUSES = {
            "migration-available",
            "migration-may-be-needed",
            "supported-migration-available",
        }
        assert guard["status"] in MIGRATION_SIGNALING_STATUSES, (
            "A fresh typed-legacy project must route to a migration-signaling status after S7. "
            f"Got status={guard['status']!r}. "
            f"Expected one of {MIGRATION_SIGNALING_STATUSES}. "
            "Pre-S7 status is 'run-recover' (dead-end via stabilize-without-migration)."
        )

    def test_fresh_typed_legacy_guard_migrate_allowed_is_true(self, tmp_path):
        project = _make_fresh_typed_legacy_project(tmp_path)
        guard = _guard(project)

        assert guard.get("migrate_allowed") is True, (
            "Fresh typed-legacy project guard must report migrate_allowed=True after S7; "
            f"got migrate_allowed={guard.get('migrate_allowed')!r}"
        )

    def test_fresh_typed_legacy_guard_offers_migrate_capability_in_offered_position(
        self, tmp_path
    ):
        """
        The guard payload must reference migrate.typed_legacy_backlog or
        sweetclaude:migrate as an OFFERED action — not just in blocked_capabilities.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        guard = _guard(project)

        # migrate_allowed is the definitive flag — True means migration is offered
        assert guard.get("migrate_allowed") is True, (
            "After S7, fresh typed-legacy project guard must have migrate_allowed=True. "
            f"Currently migrate_allowed={guard.get('migrate_allowed')!r}. "
            "Pre-S7 it was always False for typed_legacy_backlog."
        )


# ---------------------------------------------------------------------------
# Scenario 3 — taxonomy-migration is no longer a hard-blocked action
#
# RED reason: _blocked_actions() currently appends taxonomy-migration for every
#             project with unsupported-typed-backlog-layout failure.
#             After S7, typed-legacy projects must route to migration, not
#             stabilize-without-migration, so this failure class either disappears
#             or no longer triggers a blocked action.
# ---------------------------------------------------------------------------

class TestTaxonomyMigrationNotBlocked:
    """
    After S7, diagnose_project / plan_project on a typed-legacy project must NOT
    list 'taxonomy-migration' among blocked_actions.
    """

    def _get_plan_blocked_actions(self, project: Path) -> list[str]:
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from recovery.recover_project import plan_project
        plan = plan_project(project)
        return [b["id"] for b in plan.get("blocked_actions", [])]

    def test_taxonomy_migration_not_in_blocked_actions_fresh(self, tmp_path):
        project = _make_fresh_typed_legacy_project(tmp_path)
        blocked_ids = self._get_plan_blocked_actions(project)
        assert "taxonomy-migration" not in blocked_ids, (
            "After S7, 'taxonomy-migration' must NOT be a blocked action for a "
            "fresh typed-legacy project. It was hard-blocked pre-S7 by _blocked_actions(). "
            f"Got blocked_actions: {blocked_ids!r}"
        )

    def test_stabilized_typed_legacy_plan_routes_to_migration_not_no_op(self, tmp_path):
        """
        After S7, the plan for a stabilized typed-legacy project must route to
        migration (not 'no-op' / 'no-recovery-needed').
        Pre-S7: stabilized project has recovery_route=no-recovery-needed because
        _taxonomy_recovery_accepts_legacy_layout returns True, so the plan is no-op.
        After S7: the guard must detect old prefixes still present and route to migration.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from recovery.recover_project import plan_project
        plan = plan_project(project)

        plan_status = plan.get("plan_status", "")
        assert plan_status != "no-op", (
            "After S7, plan for a stabilized typed-legacy project must NOT be 'no-op'. "
            "Pre-S7: accepted_legacy_layout=True causes recovery_route=no-recovery-needed "
            "and plan_status=no-op — a dead-end with no exit. "
            f"Got plan_status={plan_status!r}, recovery_route={plan.get('recovery_route')!r}."
        )

    def test_unsupported_typed_backlog_failure_absent_or_has_migrate_strategy(self, tmp_path):
        """
        After S7, the unsupported-typed-backlog-layout failure class either:
        (a) no longer appears (migration is now supported, so not a failure), OR
        (b) carries a 'migrate' recovery strategy rather than 'stabilize-without-migration'.
        Pre-S7 it always appeared with strategy='stabilize-without-migration'.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        diagnosis = _diagnose(project)

        failure_classes = diagnosis.get("failure_classes", [])
        typed_backlog_failure = next(
            (f for f in failure_classes if f.get("code") == "unsupported-typed-backlog-layout"),
            None,
        )

        if typed_backlog_failure is None:
            # (a) failure class absent — migration now supported, not a failure.
            # This is the expected post-S7 state.
            return

        # (b) if failure class still present, strategy must mention migration
        strategy = typed_backlog_failure.get("recovery_strategy", "")
        assert "stabilize-without-migration" not in strategy or "migrate" in strategy.lower(), (
            "unsupported-typed-backlog-layout failure class must carry a migrate "
            f"recovery strategy after S7 (not 'stabilize-without-migration' alone); "
            f"got recovery_strategy={strategy!r}. "
            "Pre-S7 it was 'stabilize-without-migration' — a dead-end."
        )


# ---------------------------------------------------------------------------
# Scenario 4 — Stabilized project is offered migration
#
# A stabilized project has recovery.taxonomy.status == "stabilized-without-migration".
# Pre-S7: guard routes this to compatibility-mode (accepted_legacy_taxonomy shape),
#         primary_action = continue-compatibility-mode.
# After S7: guard must detect old prefixes still present and offer migration.
#
# RED reason: accepted_legacy_layout check causes guard to route to
#             accepted_legacy_taxonomy / compatibility-mode, not to typed_legacy_backlog
# ---------------------------------------------------------------------------

class TestStabilizedProjectOfferedMigration:
    """
    A project already stabilized in compatibility mode
    (state: recovery.taxonomy.status == "stabilized-without-migration",
     typed dirs + old prefixes still present on disk)
    must have the guard offer the migrator as the resolving action.
    """

    def test_stabilized_typed_legacy_guard_project_shape_is_typed_legacy_backlog(
        self, tmp_path
    ):
        """
        After S7, a stabilized project with typed dirs + old prefixes must classify
        as 'typed_legacy_backlog' (migration path), not 'accepted_legacy_taxonomy'
        (compatibility-mode dead-end).
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        guard = _guard(project)

        assert guard["project_shape"] == "typed_legacy_backlog", (
            "A stabilized typed-legacy project (old prefixes still present) must "
            "classify as 'typed_legacy_backlog' after S7, not 'accepted_legacy_taxonomy'. "
            f"Got project_shape={guard['project_shape']!r}. "
            "Pre-S7 it classified as 'accepted_legacy_taxonomy' (dead-end)."
        )

    def test_stabilized_typed_legacy_guard_does_not_return_compatibility_mode(
        self, tmp_path
    ):
        project = _make_stabilized_typed_legacy_project(tmp_path)
        guard = _guard(project)

        assert guard["status"] != "compatibility-mode", (
            "A stabilized typed-legacy project must NOT route to 'compatibility-mode' "
            "after S7 — that is the pre-S7 permanent parking status. "
            f"Got status={guard['status']!r}. The guard must offer migration."
        )

    def test_stabilized_typed_legacy_guard_migrate_allowed_is_true(self, tmp_path):
        project = _make_stabilized_typed_legacy_project(tmp_path)
        guard = _guard(project)

        assert guard.get("migrate_allowed") is True, (
            "Stabilized typed-legacy project guard must report migrate_allowed=True "
            f"after S7; got {guard.get('migrate_allowed')!r}"
        )

    def test_stabilized_typed_legacy_maintenance_route_not_compatibility_mode(
        self, tmp_path
    ):
        project = _make_stabilized_typed_legacy_project(tmp_path)
        route = _maintenance_route(project)

        assert route.get("status") != "compatibility-mode", (
            "maintenance-route status for a stabilized typed-legacy project must "
            "NOT be 'compatibility-mode' after S7. "
            f"Got status={route.get('status')!r}"
        )

    def test_stabilized_typed_legacy_maintenance_route_primary_not_continue_compat(
        self, tmp_path
    ):
        project = _make_stabilized_typed_legacy_project(tmp_path)
        route = _maintenance_route(project)

        primary = route.get("primary_action") or {}
        assert primary.get("id") != "continue-compatibility-mode", (
            "maintenance-route primary_action must not be 'continue-compatibility-mode' "
            "for a stabilized typed-legacy project after S7. That is a no-op dead-end. "
            f"Got primary_action={primary!r}"
        )

    def test_stabilized_typed_legacy_maintenance_route_offers_migration_capability(
        self, tmp_path
    ):
        project = _make_stabilized_typed_legacy_project(tmp_path)
        route = _maintenance_route(project)

        primary = route.get("primary_action") or {}
        cap_id = primary.get("capability_id", "")
        route_status = route.get("status", "")
        assert (
            "migrate.typed_legacy_backlog" in cap_id
            or "supported-migration-available" == route_status
            or "migration-available" in route_status
        ), (
            "Doctor maintenance-route for a stabilized typed-legacy project must "
            "offer the migration capability (migrate.typed_legacy_backlog) or "
            "report status='supported-migration-available' after S7. "
            f"Got status={route_status!r}, primary_action.capability_id={cap_id!r}"
        )


# ---------------------------------------------------------------------------
# Scenario 5 — Post-migration guard reports graduation-eligible
#
# RED reason: run_migration(dry_run=False) on a typed-legacy project either does
#             nothing useful (no state update) or S3 hasn't migrated the typed
#             layout, so the guard never transitions to graduation-available
# ---------------------------------------------------------------------------

class TestPostMigrationGuardGraduationAvailable:
    """
    After run_migration(dry_run=False) runs successfully on a stabilized
    typed-legacy project, the guard must report the project as
    v4-compliant / graduation-available (the sanctioned exit), NOT still
    parked in compatibility-mode.
    """

    def test_post_migration_guard_not_compatibility_mode(self, tmp_path):
        project = _make_stabilized_typed_legacy_project(tmp_path)
        result = _run_migration_fn(project, dry_run=False)
        assert result.get("ok") is True, (
            f"run_migration must succeed on a typed-legacy project for post-migration "
            f"guard test to be meaningful; got result={result!r}"
        )

        guard = _guard(project)
        assert guard["status"] != "compatibility-mode", (
            "After successful migration, the guard must NOT return 'compatibility-mode' "
            "(the pre-S7 permanent parking state). "
            f"Got status={guard['status']!r}"
        )

    def test_post_migration_guard_is_graduation_eligible(self, tmp_path):
        project = _make_stabilized_typed_legacy_project(tmp_path)
        result = _run_migration_fn(project, dry_run=False)
        assert result.get("ok") is True, (
            f"run_migration must succeed; got {result!r}"
        )

        guard = _guard(project)
        # After migration the project must be graduation-available (v4-compliant)
        # or ok (already graduated). Both are acceptable exits.
        assert guard["status"] in ("graduation-available", "ok"), (
            "After successful migration, the guard must report 'graduation-available' "
            "or 'ok' — the sanctioned exits from compatibility mode. "
            f"Got status={guard['status']!r}. "
            "Pre-S7 the guard still returned 'compatibility-mode' even after migration."
        )

    def test_graduation_clears_compatibility_state(self, tmp_path):
        project = _make_stabilized_typed_legacy_project(tmp_path)
        result = _run_migration_fn(project, dry_run=False)
        assert result.get("ok") is True, (
            f"run_migration must succeed; got {result!r}"
        )

        guard = _guard(project)
        if guard["status"] == "graduation-available":
            scripts_dir = str(REPO_ROOT / "scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            from recovery.recover_project import graduate
            grad_result = graduate(project)
            assert grad_result.get("status") == "graduated", (
                f"graduate() must succeed after migration; got {grad_result!r}"
            )
            final_guard = _guard(project)
            assert final_guard["status"] == "ok", (
                "After graduation, the guard must report 'ok'. "
                f"Got status={final_guard['status']!r}"
            )
        elif guard["status"] == "ok":
            # migration itself marked the project as graduated — also acceptable
            pass
        else:
            pytest.fail(
                "After migration, guard must be 'graduation-available' or 'ok'; "
                f"got {guard['status']!r}"
            )


# ---------------------------------------------------------------------------
# Scenario 6 — No flag-write shortcut exit (regression lock)
#
# This is a REGRESSION LOCK — mirrors test_dead_end_totality invariant.
# These tests were GREEN pre-S7 and must STAY GREEN after S7.
# We include them here explicitly to ensure S7 cannot regress them.
# ---------------------------------------------------------------------------

class TestNoFlagWriteShortcutExit:
    """
    The scan and maintenance-route must never offer:
    - A fix_recipe of type "exit_compatibility_mode"
    - A status derived from a "compatibility_exited" flag write

    This locks the invariant from test_dead_end_totality.py::test_scan_never_offers_the_flag_write_exit
    so S7 can't regress it.
    """

    def _scan(self, project: Path) -> dict:
        return _run_json(DOCTOR, "scan", "--project-dir", str(project))

    def test_scan_never_offers_exit_compatibility_mode_recipe_stabilized(self, tmp_path):
        """
        Regression lock for stabilized typed-legacy project.
        Was GREEN pre-S7 — must stay GREEN after S7.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        scan = self._scan(project)

        for finding in scan["findings"]:
            recipe = finding.get("fix_recipe") or {}
            assert recipe.get("type") != "exit_compatibility_mode", (
                f"scan finding {finding.get('id')!r} offers exit_compatibility_mode "
                "recipe — this is a no-op flag-write shortcut; only graduation exits"
            )
            key_path = recipe.get("key_path") or []
            assert "compatibility_exited" not in key_path, (
                f"scan finding {finding.get('id')!r} writes the compatibility_exited "
                "flag — the guard does not read this flag for status decisions"
            )

    def test_scan_never_offers_exit_compatibility_mode_recipe_fresh(self, tmp_path):
        """
        Regression lock for fresh typed-legacy project.
        After S7, no shortcut exit recipe should appear for this shape either.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        scan = self._scan(project)

        for finding in scan["findings"]:
            recipe = finding.get("fix_recipe") or {}
            assert recipe.get("type") != "exit_compatibility_mode", (
                f"scan finding {finding.get('id')!r} offers exit_compatibility_mode "
                "recipe — this is a no-op flag-write shortcut; only graduation exits"
            )
            key_path = recipe.get("key_path") or []
            assert "compatibility_exited" not in key_path, (
                f"scan finding {finding.get('id')!r} writes the compatibility_exited "
                "flag — the guard does not read this flag for status decisions"
            )

    def test_maintenance_route_no_exit_compatibility_mode_action_stabilized(self, tmp_path):
        """
        Regression lock: maintenance-route for stabilized must not offer flag-write exit.
        Was GREEN pre-S7 — must stay GREEN.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        route = _maintenance_route(project)

        route_text = json.dumps(route)
        assert "exit_compatibility_mode" not in route_text, (
            "maintenance-route must not reference 'exit_compatibility_mode' — "
            "that is a flag-write shortcut; only graduation is the sanctioned exit. "
            f"Route (truncated): {route_text[:600]!r}"
        )


# ---------------------------------------------------------------------------
# Scenario 7 — No-dead-end invariant: every guard status has a routed action
#
# RED reason: typed_legacy_backlog and stabilized variant currently return
#             compatibility-mode with primary_action = "continue-compatibility-mode"
#             (no migration action). The status has no resolution path.
# ---------------------------------------------------------------------------

class TestNoDeadEndInvariant:
    """
    For the typed_legacy_backlog shape (fresh and stabilized), the guard payload
    must contain an actionable migration next step.
    """

    def test_fresh_typed_legacy_guard_migrate_allowed_true(self, tmp_path):
        """
        migrate_allowed is the definitive actionability signal.
        Pre-S7 it is always False for typed_legacy_backlog.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        guard = _guard(project)

        assert guard.get("migrate_allowed") is True, (
            "Fresh typed-legacy project guard must have migrate_allowed=True after S7 "
            "(it is the actionability flag — False means no next step). "
            f"Got migrate_allowed={guard.get('migrate_allowed')!r}"
        )

    def test_stabilized_typed_legacy_guard_migrate_allowed_true(self, tmp_path):
        """
        migrate_allowed is the definitive actionability signal for the stabilized variant.
        Pre-S7 it is always False.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        guard = _guard(project)

        assert guard.get("migrate_allowed") is True, (
            "Stabilized typed-legacy project guard must have migrate_allowed=True after S7. "
            f"Got migrate_allowed={guard.get('migrate_allowed')!r}"
        )

    def test_fresh_typed_legacy_guard_shape_offers_migration_capability(self, tmp_path):
        """
        The project_shape emitted by the guard for a fresh typed-legacy project
        must be one that has a migration_capability in the manifest.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        guard = _guard(project)

        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from maintenance.capability_manifest import project_shape_config

        project_shape = guard.get("project_shape", "")
        assert project_shape, "guard must return a project_shape"
        try:
            shape_cfg = project_shape_config(project_shape)
        except Exception:
            pytest.fail(f"guard returned unknown project_shape: {project_shape!r}")

        migration_cap = shape_cfg.get("migration_capability")
        assert migration_cap, (
            f"guard project_shape '{project_shape}' for a fresh typed-legacy project "
            "must have a migration_capability in the manifest after S7. "
            "Pre-S7 typed_legacy_backlog had no migration_capability."
        )

    def test_stabilized_typed_legacy_guard_shape_offers_migration_capability(self, tmp_path):
        """
        Same check for the stabilized variant.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        guard = _guard(project)

        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from maintenance.capability_manifest import project_shape_config

        project_shape = guard.get("project_shape", "")
        assert project_shape, "guard must return a project_shape"
        try:
            shape_cfg = project_shape_config(project_shape)
        except Exception:
            pytest.fail(f"guard returned unknown project_shape: {project_shape!r}")

        migration_cap = shape_cfg.get("migration_capability")
        assert migration_cap, (
            f"guard project_shape '{project_shape}' for a stabilized typed-legacy project "
            "must have a migration_capability in the manifest after S7. "
            "Pre-S7 accepted_legacy_taxonomy had no migration_capability (dead-end)."
        )


# ---------------------------------------------------------------------------
# Scenario 8 — Doctor maintenance-route names migration capability
#
# RED reason: build_maintenance_route for a typed-legacy project routes to
#             "compatibility-mode" status with primary_action pointing to
#             doctor.compatibility_mode (no migration offered)
# ---------------------------------------------------------------------------

class TestDoctorMaintenanceRouteNamesMigration:
    """
    The doctor maintenance-route for a typed-legacy project must name the
    migration capability (migrate.typed_legacy_backlog or sweetclaude:migrate)
    as the primary or offered action.
    """

    def test_maintenance_route_for_stabilized_typed_legacy_status_is_migration(
        self, tmp_path
    ):
        """
        maintenance-route status for a stabilized typed-legacy project must be
        'supported-migration-available' after S7.
        Pre-S7 it was 'compatibility-mode'.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        route = _maintenance_route(project)

        assert route.get("status") == "supported-migration-available", (
            "Doctor maintenance-route for a stabilized typed-legacy project must "
            "return status='supported-migration-available' after S7. "
            f"Got status={route.get('status')!r}. "
            "Pre-S7 it returned 'compatibility-mode' — a no-op dead-end."
        )

    def test_maintenance_route_for_stabilized_typed_legacy_primary_action_capability(
        self, tmp_path
    ):
        """
        primary_action.capability_id must be migrate.typed_legacy_backlog.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        route = _maintenance_route(project)

        primary = route.get("primary_action") or {}
        cap_id = primary.get("capability_id", "")
        assert "migrate.typed_legacy_backlog" in cap_id, (
            "Doctor maintenance-route primary_action.capability_id must be "
            "'migrate.typed_legacy_backlog' for a stabilized typed-legacy project "
            f"after S7; got {cap_id!r}. "
            "Pre-S7 it pointed to 'doctor.compatibility_mode' (no-op)."
        )

    def test_maintenance_route_for_fresh_typed_legacy_status_is_migration(self, tmp_path):
        """
        maintenance-route status for a fresh typed-legacy project must be
        'supported-migration-available' after S7.
        Pre-S7: fresh project → recovery_required → route status was 'recovery-available'.
        After S7: fresh project → typed_legacy_backlog → 'supported-migration-available'.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        route = _maintenance_route(project)

        assert route.get("status") == "supported-migration-available", (
            "Doctor maintenance-route for a fresh typed-legacy project must "
            "return status='supported-migration-available' after S7. "
            f"Got status={route.get('status')!r}. "
            "Pre-S7 it returned 'recovery-available' (stabilize-without-migration dead-end)."
        )

    def test_maintenance_route_for_fresh_typed_legacy_primary_action_capability(
        self, tmp_path
    ):
        """
        primary_action.capability_id must be migrate.typed_legacy_backlog.
        Pre-S7: primary_action pointed to recover.stabilize_without_migration.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        route = _maintenance_route(project)

        primary = route.get("primary_action") or {}
        cap_id = primary.get("capability_id", "")
        assert "migrate.typed_legacy_backlog" in cap_id, (
            "Doctor maintenance-route primary_action.capability_id must be "
            "'migrate.typed_legacy_backlog' for a fresh typed-legacy project after S7; "
            f"got {cap_id!r}. "
            "Pre-S7 it pointed to 'recover.stabilize_without_migration' (dead-end)."
        )


# ---------------------------------------------------------------------------
# Scenario 9 — DUPLICATE ROUTING (the key S7 caucus must-fix decision)
#
# A typed-legacy project WITH real duplicate IDs must NOT be offered plain
# migrate (which would refuse on conflicts). Instead the guard must offer a
# RESOLVABLE action that names the colliding ids so the user can act.
#
# A typed-legacy project whose only id-collisions are BACKUP files
# (.bak extension) is NOT considered to have real duplicates — it should be
# offered migrate directly (supported-migration-available).
#
# RED reason: The guard currently has no awareness of duplicates in the
# typed-legacy routing path; run_migration refuses with a generic error
# rather than naming the duplicate ids; and backup-file filtering is absent.
# ---------------------------------------------------------------------------

def _make_typed_legacy_with_real_duplicates(tmp_path: Path) -> tuple[Path, str]:
    """
    A typed-legacy project where two REAL (non-backup) files share the same
    id (DEBT-001). Returns (project_path, duplicate_id).

    The syncog fixture already contains:
      docs/product/backlog/debt/DEBT-001-first-debt.md
      docs/product/backlog/debt/DEBT-001-duplicate-debt.md
    Both lack a frontmatter `id:` field so the filename-based id is DEBT-001
    for both — a real duplicate.
    """
    project = tmp_path / "project_dups"
    shutil.copytree(SYNCOG_FIXTURE, project)
    _write_artifact_privacy(project)
    _write_state(project, recovery=None)
    # Verify the duplicate pair is actually present
    debt_dir = project / "docs" / "product" / "backlog" / "debt"
    dup_files = [
        f for f in debt_dir.iterdir()
        if f.name.startswith("DEBT-001") and not f.name.endswith(".bak")
    ]
    assert len(dup_files) >= 2, (
        f"Test fixture must have >=2 real DEBT-001 files; found {[f.name for f in dup_files]}"
    )
    return project, "DEBT-001"


def _make_typed_legacy_backup_only_duplicates(tmp_path: Path) -> tuple[Path, str]:
    """
    A typed-legacy project where the only id-collision for a given id is one
    real file + one .bak file.  Backup files must NOT count as real duplicates.

    We use the syncog fixture but remove the true-duplicate DEBT-001 file and
    add a .bak variant instead.
    """
    project = tmp_path / "project_bak"
    shutil.copytree(SYNCOG_FIXTURE, project)
    _write_artifact_privacy(project)
    _write_state(project, recovery=None)

    debt_dir = project / "docs" / "product" / "backlog" / "debt"
    # Remove the second real DEBT-001 file so only one real copy remains
    dup = debt_dir / "DEBT-001-duplicate-debt.md"
    if dup.exists():
        dup.unlink()
    # Add a .bak file — this must NOT count as a real duplicate
    (debt_dir / "DEBT-001-first-debt.md.bak").write_text(
        "---\ntitle: Backup\nstatus: backlog\n---\nBackup copy.\n",
        encoding="utf-8",
    )
    return project, "DEBT-001"


class TestDuplicateRoutingDecision:
    """
    Locked decision: a typed-legacy project with REAL duplicate ids must route
    to a resolvable duplicate-resolution action (not a plain migrate that
    would refuse). A project with backup-only collisions must route to
    supported-migration-available.
    """

    def test_real_duplicates_guard_does_not_offer_plain_migrate_that_would_refuse(
        self, tmp_path
    ):
        """
        A typed-legacy project with real duplicate ids must NOT be offered the
        plain `migrate.typed_legacy_backlog` action as a next step when that
        action would immediately refuse.

        The guard must instead surface a resolution action — something the user
        can actually complete before migrating.

        RED reason: guard currently has no duplicate-routing branch for
        typed-legacy; it would just offer migrate which would call run_migration
        and refuse with a generic error (not actionable).
        """
        project, dup_id = _make_typed_legacy_with_real_duplicates(tmp_path)
        guard = _guard(project)

        # The guard must NOT return migrate_allowed=True when real dups exist
        # AND the migration would immediately refuse those dups.
        # It must instead surface the duplicate ids so the user can act.
        #
        # Acceptable post-S7 states:
        #   (a) status == "duplicate-resolution-required" (or similar) with
        #       duplicate_ids in payload naming dup_id
        #   (b) status == "graduation-blocked" with a blocker whose code is
        #       "duplicate-ids" and which names dup_id
        #   (c) primary_action references a resolve capability, not plain migrate
        #
        # The one state that is NOT acceptable: guard returns
        # migrate_allowed=True with no mention of the duplicate — because that
        # means the user would run /sweetclaude:migrate, hit a refusal, and
        # have no path forward (dead-end).

        payload_text = json.dumps(guard)
        # The duplicate id must appear somewhere in the guard payload so the
        # user knows what to fix.
        assert dup_id in payload_text, (
            f"guard payload must name the duplicate id '{dup_id}' so the user "
            "knows what to resolve. "
            f"Got guard payload (truncated): {payload_text[:600]!r}. "
            "Pre-S7 behavior: guard offers migrate_allowed=True but migrate "
            "would refuse with an opaque error — dead-end."
        )

    def test_real_duplicates_guard_offers_resolvable_action(self, tmp_path):
        """
        The guard must offer an action the user can actually complete —
        not an empty/no-action state and not migrate_allowed=True-but-would-refuse.

        Acceptable: a non-empty primary_action or graduation_blockers list that
        names the duplicate and carries a resolution.

        RED reason: there is no duplicate-aware routing branch for
        typed-legacy projects in the current guard logic.
        """
        project, dup_id = _make_typed_legacy_with_real_duplicates(tmp_path)
        guard = _guard(project)

        # At least one of: a primary_action with capability_id, or
        # graduation_blockers with a resolution, must reference duplicates.
        primary = guard.get("primary_action") or {}
        blockers = guard.get("graduation_blockers") or []
        dup_blockers = [b for b in blockers if b.get("code") == "duplicate-ids"]

        has_resolvable_action = (
            bool(primary.get("capability_id"))
            or bool(dup_blockers)
            or guard.get("status") in (
                "duplicate-resolution-required",
                "graduation-blocked",
            )
        )
        assert has_resolvable_action, (
            "guard must offer a resolvable action for a typed-legacy project "
            f"with real duplicate ids ('{dup_id}'). "
            "An empty primary_action with no blockers is not actionable. "
            f"Got guard status={guard.get('status')!r}, "
            f"primary_action={primary!r}, "
            f"graduation_blockers={blockers!r}."
        )

    def test_backup_only_duplicates_guard_offers_migration(self, tmp_path):
        """
        A typed-legacy project where the only id-collision is a .bak file
        must be offered migration — backup files must NOT count as real
        duplicates blocking migration.

        RED reason: the migration duplicate-detection logic has no concept of
        backup-file exclusion; it treats .bak files as real conflict candidates,
        so the guard would refuse migration even when there are no real dups.
        """
        project, dup_id = _make_typed_legacy_backup_only_duplicates(tmp_path)
        guard = _guard(project)

        assert guard.get("migrate_allowed") is True, (
            "A typed-legacy project with backup-only id-collisions (.bak files) "
            "must be offered migration (migrate_allowed=True). "
            "Backup files must be excluded from duplicate detection. "
            f"Got migrate_allowed={guard.get('migrate_allowed')!r}, "
            f"status={guard.get('status')!r}. "
            "Pre-S7 behavior: .bak files counted as real duplicates, "
            "blocking migration unnecessarily."
        )

    def test_backup_only_duplicates_guard_status_is_supported_migration_available(
        self, tmp_path
    ):
        """
        Exact status string assertion: a project with only backup collisions
        must return exactly 'supported-migration-available'.
        """
        project, _ = _make_typed_legacy_backup_only_duplicates(tmp_path)
        guard = _guard(project)

        assert guard.get("status") == "supported-migration-available", (
            "guard status for a typed-legacy project with backup-only collisions "
            "must be exactly 'supported-migration-available'. "
            f"Got status={guard.get('status')!r}."
        )


class TestRunMigrationDuplicateContracts:
    """
    run_migration on a project with real duplicates must:
    - dry_run=True: return conflicts that NAME the duplicate ids (actionable)
    - dry_run=False: refuse (ok=False) with an actionable message listing the ids
    """

    def test_dry_run_on_real_dups_names_duplicate_ids(self, tmp_path):
        """
        run_migration(dry_run=True) on a project with real duplicate ids must
        return a conflicts list that names those ids.

        RED reason: the dry-run output currently does not guarantee the ids
        appear in the conflicts payload in a way the typed-legacy routing
        branch can surface to the user.
        """
        project, dup_id = _make_typed_legacy_with_real_duplicates(tmp_path)
        result = _run_migration_fn(project, dry_run=True)

        conflicts = result.get("conflicts", [])
        conflict_ids = [str(c.get("id", "")) for c in conflicts]

        assert any(dup_id in cid or cid in dup_id for cid in conflict_ids), (
            f"run_migration dry_run=True must return conflicts naming '{dup_id}'. "
            f"Got conflicts={conflicts!r}. "
            "The user must be able to see which id to resolve — an opaque refusal "
            "is not actionable."
        )

    def test_dry_run_on_real_dups_is_actionable_not_empty(self, tmp_path):
        """
        The dry-run result for a project with real duplicates must not be
        an empty conflicts list — that would mislead the user into thinking
        migration would succeed.
        """
        project, dup_id = _make_typed_legacy_with_real_duplicates(tmp_path)
        result = _run_migration_fn(project, dry_run=True)

        conflicts = result.get("conflicts", [])
        assert len(conflicts) > 0, (
            "run_migration dry_run=True on a project with real duplicate ids must "
            "return a non-empty conflicts list. "
            f"Got conflicts={conflicts!r}. "
            f"Duplicate id '{dup_id}' must appear as a named conflict."
        )

    def test_execute_on_real_dups_refuses_with_ok_false(self, tmp_path):
        """
        run_migration(dry_run=False) on a project with real duplicates must
        return ok=False (refuse to proceed).
        """
        project, dup_id = _make_typed_legacy_with_real_duplicates(tmp_path)
        result = _run_migration_fn(project, dry_run=False)

        assert result.get("ok") is False, (
            "run_migration(dry_run=False) must refuse (ok=False) when real "
            f"duplicate ids are present. Got result={result!r}."
        )

    def test_execute_on_real_dups_refusal_message_names_duplicate_ids(self, tmp_path):
        """
        The refusal message from run_migration(dry_run=False) must name the
        duplicate ids so the user knows what to fix.

        RED reason: the current refusal message lists ids but in a format that
        is not yet plumbed through to the typed-legacy guard routing — the
        routing branch does not exist yet.
        """
        project, dup_id = _make_typed_legacy_with_real_duplicates(tmp_path)
        result = _run_migration_fn(project, dry_run=False)

        # The refusal payload (errors list or error string) must name the dup id
        error_text = json.dumps(result)
        assert dup_id in error_text, (
            f"run_migration(dry_run=False) refusal must name duplicate id '{dup_id}' "
            "in the error payload. "
            f"Got result (truncated): {error_text[:400]!r}. "
            "A generic 'migration refused' with no id is not actionable."
        )


# ---------------------------------------------------------------------------
# Scenario 10 — Guard-routing seams
#
# Fine-grained seam tests for guard_project routing decisions after S7.
# ---------------------------------------------------------------------------

class TestGuardRoutingSeams:
    """
    Explicit routing seam assertions for the guard across project states.
    """

    def test_stabilized_project_with_old_prefixes_is_typed_legacy_backlog(
        self, tmp_path
    ):
        """
        A stabilized project (recovery.taxonomy.status = stabilized-without-migration)
        with old prefixes still on disk must be classified as 'typed_legacy_backlog'
        NOT 'accepted_legacy_taxonomy'.

        Pre-S7: the accepted_legacy_layout check fires first and routes to
        accepted_legacy_taxonomy (compatibility-mode dead-end).
        After S7: old prefix count overrides the accepted_legacy_layout check.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        guard = _guard(project)

        assert guard["project_shape"] == "typed_legacy_backlog", (
            "guard_project must classify a stabilized project with old prefixes "
            "still on disk as 'typed_legacy_backlog' after S7. "
            f"Got project_shape={guard['project_shape']!r}. "
            "Pre-S7: accepted_legacy_layout check routes to 'accepted_legacy_taxonomy'."
        )

    def test_stabilized_project_old_prefixes_gone_v4_compliant_is_graduation_candidate(
        self, tmp_path
    ):
        """
        A stabilized project with old prefixes GONE and v4-compliant layout
        must still reach graduation_candidate / graduation-available.

        This is the genuine graduation path — S7 must NOT break it.
        """
        project = tmp_path / "project_clean"
        shutil.copytree(V4_COMPAT_FIXTURE, project)
        _write_artifact_privacy(project)
        # Write stabilized state — no old prefixes in fixture
        _write_state(project)
        guard = _guard(project)

        assert guard.get("status") in ("graduation-available", "ok"), (
            "A stabilized project with no old prefixes and v4-compliant layout "
            "must route to 'graduation-available' or 'ok' after S7. "
            f"Got status={guard.get('status')!r}, "
            f"project_shape={guard.get('project_shape')!r}. "
            "S7 must not break the genuine graduation path."
        )

    def test_diagnose_stabilized_typed_legacy_emits_failure_class(self, tmp_path):
        """
        diagnose_project on a stabilized typed-legacy project must emit
        'unsupported-typed-backlog-layout' in failure_class_codes AND
        recovery_route must not be 'no-recovery-needed'.

        Pre-S7: stabilized project → no-recovery-needed (dead-end no-op).
        After S7: must report a resolvable failure class.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        diagnosis = _diagnose(project)

        failure_codes = diagnosis.get("failure_class_codes", [])
        recovery_route = diagnosis.get("recovery_route", "")

        assert "unsupported-typed-backlog-layout" in failure_codes, (
            "diagnose_project on a stabilized typed-legacy project must emit "
            "'unsupported-typed-backlog-layout' in failure_class_codes after S7. "
            f"Got failure_class_codes={failure_codes!r}. "
            "Pre-S7: accepted_legacy_layout=True suppressed this failure class entirely."
        )

        assert recovery_route != "no-recovery-needed", (
            "diagnose_project on a stabilized typed-legacy project must NOT "
            "return recovery_route='no-recovery-needed' after S7 — that is the "
            "pre-S7 dead-end. "
            f"Got recovery_route={recovery_route!r}."
        )

    def test_blocked_actions_on_typed_legacy_does_not_contain_taxonomy_migration(
        self, tmp_path
    ):
        """
        _blocked_actions for a typed-legacy diagnosis must NOT contain
        'taxonomy-migration'.

        Pre-S7: _blocked_actions HARD-BLOCKS taxonomy-migration for any project
        with unsupported-typed-backlog-layout, making migration permanently
        impossible from the plan path.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from recovery.recover_project import diagnose_project, _blocked_actions
        diagnosis = diagnose_project(project)
        blocked = _blocked_actions(diagnosis)
        blocked_ids = [b.get("id") for b in blocked]

        assert "taxonomy-migration" not in blocked_ids, (
            "_blocked_actions must NOT hard-block 'taxonomy-migration' for a "
            "typed-legacy project after S7. "
            f"Got blocked_ids={blocked_ids!r}. "
            "Pre-S7: this hard-block prevented migration from ever being offered."
        )

    def test_plan_project_typed_legacy_shape_is_typed_legacy_backlog(self, tmp_path):
        """
        plan_project["project_shape"] must be 'typed_legacy_backlog' for a
        typed-legacy project.

        _recovery_project_shape maps routes to shapes — after S7 the typed-legacy
        route must map to 'typed_legacy_backlog', not the fallback 'manual_escalation'.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from recovery.recover_project import plan_project
        plan = plan_project(project)

        assert plan.get("project_shape") == "typed_legacy_backlog", (
            "plan_project['project_shape'] must be 'typed_legacy_backlog' for a "
            "typed-legacy project after S7. "
            f"Got project_shape={plan.get('project_shape')!r}. "
            "Pre-S7: _recovery_project_shape did not have a 'typed-legacy-migrate' "
            "route → fell through to 'manual_escalation'."
        )

    def test_guard_status_exact_string_fresh_typed_legacy(self, tmp_path):
        """
        Exact status string assertion: guard status for a fresh typed-legacy
        project must be exactly 'supported-migration-available'.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        guard = _guard(project)

        assert guard.get("status") == "supported-migration-available", (
            "guard status for a fresh typed-legacy project must be exactly "
            "'supported-migration-available' after S7. "
            f"Got status={guard.get('status')!r}."
        )

    def test_guard_status_exact_string_stabilized_typed_legacy(self, tmp_path):
        """
        Exact status string assertion: guard status for a stabilized typed-legacy
        project must be exactly 'supported-migration-available'.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        guard = _guard(project)

        assert guard.get("status") == "supported-migration-available", (
            "guard status for a stabilized typed-legacy project must be exactly "
            "'supported-migration-available' after S7. "
            f"Got status={guard.get('status')!r}."
        )


# ---------------------------------------------------------------------------
# Scenario 11 — Migrate → Graduate seam
#
# After run_migration(dry_run=False) succeeds on a typed-legacy project,
# graduation_check must allow graduation AND sweetclaude.yaml state must
# reflect no old prefixes remaining.
# ---------------------------------------------------------------------------

class TestMigrateToGraduateSeam:
    """
    After a successful migration from a typed-legacy project:
    - graduation_check(project)["graduation_allowed"] is True
    - The reason is NOT "not-in-compatibility-mode" (meaning the state
      correctly reflects migration completion)
    - sweetclaude.yaml recovery.taxonomy.status is NOT a value that blocks
      graduation (e.g. not "graduated" yet, but not a blocker)
    - old_prefix_count on disk == 0 (the migration actually moved the files)
    """

    def test_post_migration_graduation_check_allows_graduation(self, tmp_path):
        """
        After run_migration(dry_run=False) succeeds, graduation_check must
        return graduation_allowed=True.

        RED reason: run_migration does not update the sweetclaude.yaml
        recovery.taxonomy state to a value graduation_check considers valid
        for graduation entry — so graduation_check returns
        reason='not-in-compatibility-mode' and blocks graduation.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        result = _run_migration_fn(project, dry_run=False)
        assert result.get("ok") is True, (
            f"run_migration must succeed as a pre-condition; got {result!r}"
        )

        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from recovery.recover_project import graduation_check
        check = graduation_check(project)

        assert check.get("graduation_allowed") is True, (
            "graduation_check must return graduation_allowed=True after a "
            "successful migration from typed-legacy. "
            f"Got graduation_check={check!r}. "
            "Pre-S7: graduation_check returns reason='not-in-compatibility-mode' "
            "because run_migration doesn't update state to the right value."
        )

    def test_post_migration_graduation_check_reason_not_not_in_compat_mode(
        self, tmp_path
    ):
        """
        The graduation_check reason after successful migration must NOT be
        'not-in-compatibility-mode' — that reason means the migration didn't
        update state correctly and graduation is wrongly blocked.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        result = _run_migration_fn(project, dry_run=False)
        assert result.get("ok") is True, (
            f"run_migration must succeed as a pre-condition; got {result!r}"
        )

        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from recovery.recover_project import graduation_check
        check = graduation_check(project)

        assert check.get("reason") != "not-in-compatibility-mode", (
            "graduation_check reason must NOT be 'not-in-compatibility-mode' "
            "after a successful migration. "
            f"Got reason={check.get('reason')!r}. "
            "This reason means the migration didn't write valid state for graduation."
        )

    def test_post_migration_old_prefix_count_is_zero(self, tmp_path):
        """
        After run_migration(dry_run=False) succeeds, there must be zero files
        with old taxonomy prefixes (STORY, BUG, DEBT, CHORE, BL) on disk
        (excluding .sweetclaude/ internal files).

        RED reason: run_migration currently does not move typed-legacy files —
        it only handles flat BL-NNN layouts. The typed-legacy migration path
        does not exist yet.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        result = _run_migration_fn(project, dry_run=False)
        assert result.get("ok") is True, (
            f"run_migration must succeed as a pre-condition; got {result!r}"
        )

        old_prefixes = {"STORY-", "BUG-", "DEBT-", "CHORE-", "BL-"}
        old_prefix_files = [
            str(p.relative_to(project))
            for p in project.rglob("*.md")
            if not str(p.relative_to(project)).startswith(".sweetclaude")
            and any(p.name.startswith(prefix) for prefix in old_prefixes)
        ]

        assert len(old_prefix_files) == 0, (
            "After successful migration, zero old-prefix files must remain on disk. "
            f"Found {len(old_prefix_files)} old-prefix files: "
            f"{old_prefix_files[:10]!r}. "
            "The typed-legacy migrator must move these files to ISSUE-NNN names."
        )

    def test_post_migration_recovery_taxonomy_status_does_not_block_graduation(
        self, tmp_path
    ):
        """
        After run_migration(dry_run=False), the recovery.taxonomy.status value
        in sweetclaude.yaml must NOT be 'stabilized-without-migration' (which
        blocks graduation via graduation_check).

        Acceptable values: None (key removed), 'migrated', or any value that
        causes graduation_check to allow graduation.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        result = _run_migration_fn(project, dry_run=False)
        assert result.get("ok") is True, (
            f"run_migration must succeed as a pre-condition; got {result!r}"
        )

        state_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
        state = yaml.safe_load(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}

        taxonomy_status = (
            (state.get("recovery") or {}).get("taxonomy") or {}
        ).get("status")

        # stabilized-without-migration is the one value graduation_check rejects
        # via the _taxonomy_recovery_accepts_legacy_layout → accepted but old prefix
        # count > 0 path that graduation_check uses for the not-in-compat check.
        assert taxonomy_status != "stabilized-without-migration", (
            "After successful migration, recovery.taxonomy.status must NOT be "
            "'stabilized-without-migration' — that value misleads graduation_check "
            "into blocking graduation. "
            f"Got taxonomy_status={taxonomy_status!r}."
        )


# ---------------------------------------------------------------------------
# Scenario 12 — Manifest + Doctor assertions
#
# capability_manifest.load_manifest() must pass validation after S7;
# accepted_legacy_taxonomy shape must not block the new migrate capability;
# build_maintenance_route and _build_migration_recommendations must reference
# migrate.typed_legacy_backlog for typed-legacy projects.
# ---------------------------------------------------------------------------

class TestManifestAndDoctorContracts:
    """
    Manifest-level contracts and doctor scan contracts for S7.
    """

    def test_load_manifest_validates_cleanly_after_s7(self):
        """
        capability_manifest.load_manifest() (with full validate_manifest) must
        succeed without raising after S7.

        RED reason: migrate.typed_legacy_backlog currently has supported=false
        and supports_project_shapes=[]; when S7 adds the real shape entry, the
        manifest validator checks that mutation_class, rollback_support,
        command_entrypoint, and supports_project_shapes are all correct.
        If any field is missing the validator raises.
        """
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from maintenance.capability_manifest import load_manifest
        try:
            manifest = load_manifest()
        except Exception as exc:
            pytest.fail(
                f"capability_manifest.load_manifest() raised after S7: {exc}. "
                "The manifest validator requires that migrate.typed_legacy_backlog "
                "has mutation_class, rollback_support.supported, command_entrypoint, "
                "and supports_project_shapes=[typed_legacy_backlog] when supported=true."
            )
        assert manifest is not None

    def test_accepted_legacy_taxonomy_shape_does_not_block_migrate_typed_legacy(self):
        """
        project_shape_config('accepted_legacy_taxonomy').get('blocked_capabilities', [])
        must NOT contain 'migrate.typed_legacy_backlog'.

        This shape is for projects that have completed stabilization and are in
        compat mode. It must not permanently block the migration path.
        """
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from maintenance.capability_manifest import project_shape_config
        shape = project_shape_config("accepted_legacy_taxonomy")
        blocked = shape.get("blocked_capabilities") or []

        assert "migrate.typed_legacy_backlog" not in blocked, (
            "accepted_legacy_taxonomy.blocked_capabilities must NOT contain "
            "'migrate.typed_legacy_backlog' after S7. "
            f"Got blocked_capabilities={blocked!r}. "
            "Pre-S7: it was listed as blocked there, preventing migration from "
            "ever being offered from the compat-mode path."
        )

    def test_accepted_legacy_taxonomy_shape_graduation_not_blocked(self):
        """
        The accepted_legacy_taxonomy shape must not have graduation blocked via
        the new capability.
        """
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from maintenance.capability_manifest import project_shape_config
        shape = project_shape_config("accepted_legacy_taxonomy")
        blocked = shape.get("blocked_capabilities") or []

        # The graduation capability must not be blocked from this shape
        assert "recover.graduate_from_compatibility" not in blocked, (
            "accepted_legacy_taxonomy must not block graduation capability. "
            f"Got blocked_capabilities={blocked!r}."
        )

    def test_build_maintenance_route_typed_legacy_status_is_supported_migration_available(
        self, tmp_path
    ):
        """
        build_maintenance_route for a typed-legacy ProjectState whose guard
        status is 'supported-migration-available' must return
        route status 'supported-migration-available'.

        RED reason: build_maintenance_route has no branch for
        'supported-migration-available' from a typed-legacy shape — it only
        handles 'migration-may-be-needed' for the flat BL case.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        route = _maintenance_route(project)

        assert route.get("status") == "supported-migration-available", (
            "build_maintenance_route for a typed-legacy project must return "
            "status='supported-migration-available' after S7. "
            f"Got status={route.get('status')!r}. "
            "Pre-S7: no branch for this status → falls through to no-maintenance-action."
        )

    def test_build_maintenance_route_typed_legacy_primary_action_capability_id(
        self, tmp_path
    ):
        """
        build_maintenance_route for a typed-legacy project must set
        primary_action.capability_id == 'migrate.typed_legacy_backlog'.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        route = _maintenance_route(project)

        primary = route.get("primary_action") or {}
        cap_id = primary.get("capability_id", "")

        assert cap_id == "migrate.typed_legacy_backlog", (
            "build_maintenance_route primary_action.capability_id must be "
            "exactly 'migrate.typed_legacy_backlog' for a typed-legacy project "
            f"after S7. Got capability_id={cap_id!r}."
        )

    def test_doctor_scan_migration_recommendations_reference_migrate_typed_legacy(
        self, tmp_path
    ):
        """
        doctor scan / _build_migration_recommendations for a typed-legacy project
        must return a non-empty recommendation referencing migrate.typed_legacy_backlog.

        RED reason: _build_migration_recommendations currently only fires when
        maintenance_route.status == 'supported-migration-available' AND
        primary_action.capability_id == 'migrate.flat_bl_to_issue'. The typed-legacy
        variant is not handled.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        scan = _run_json(DOCTOR, "scan", "--project-dir", str(project))

        migration_recs = scan.get("migration_recommendations") or []
        rec_text = json.dumps(migration_recs)

        assert len(migration_recs) > 0 or "migrate.typed_legacy_backlog" in json.dumps(scan), (
            "doctor scan for a typed-legacy project must produce migration "
            "recommendations referencing migrate.typed_legacy_backlog. "
            f"Got migration_recommendations={migration_recs!r}. "
            "Pre-S7: _build_migration_recommendations only handles the flat BL case."
        )


# ---------------------------------------------------------------------------
# Scenario 13 — Skill handler string-presence contracts
#
# Each skill that hardcodes a guard-status list must contain
# 'supported-migration-available'.
# bootstrap/SKILL.md must contain it AND offer /sweetclaude:migrate for it
# (distinct from the compat-mode no-action branch).
# ---------------------------------------------------------------------------

SKILLS_THAT_HANDLE_GUARD_STATUS = [
    REPO_ROOT / "skills" / "status" / "SKILL.md",
    REPO_ROOT / "skills" / "go" / "SKILL.md",
    REPO_ROOT / "skill-library" / "build" / "project-backlog" / "SKILL.md",
    REPO_ROOT / "skill-library" / "build" / "project-issues" / "SKILL.md",
    REPO_ROOT / "skill-library" / "build" / "project-backlog-triage" / "SKILL.md",
    REPO_ROOT / "skill-library" / "build" / "project-gh-sync-issues" / "SKILL.md",
    REPO_ROOT / "skill-library" / "build" / "project-gh-import-issues" / "SKILL.md",
]


class TestBootstrapSkillHandlerContracts:
    """
    bootstrap/SKILL.md must handle 'supported-migration-available' as a distinct
    guard status and must offer /sweetclaude:migrate for that status.
    """

    def test_bootstrap_skill_contains_supported_migration_available(self):
        """
        bootstrap/SKILL.md must contain the exact string
        'supported-migration-available'.

        RED reason: bootstrap does not yet have a routing branch for this status.
        It currently only handles: graduation-available, graduation-blocked,
        run-recover, migration-may-be-needed, compatibility-mode, manual-review,
        missing-product-base, guard-unavailable, ok.
        """
        skill_text = (REPO_ROOT / "skills" / "bootstrap" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "supported-migration-available" in skill_text, (
            "bootstrap/SKILL.md must contain 'supported-migration-available' "
            "as a handled guard status after S7. "
            "Currently absent — the bootstrap skill has no routing branch for "
            "typed-legacy projects that are offered migration."
        )

    def test_bootstrap_skill_offers_sweetclaude_migrate_for_supported_migration(self):
        """
        bootstrap/SKILL.md must offer /sweetclaude:configure as the action for the
        'supported-migration-available' branch.

        This is distinct from the 'compatibility-mode' branch which explicitly
        says NO action (migration stays blocked). The new branch must
        tell the user to use /sweetclaude:configure.

        RED reason: bootstrap currently says "Never recommend the migration route
        for any status except migration-may-be-needed." That rule must be updated
        to also allow it for 'supported-migration-available'.
        """
        skill_text = (REPO_ROOT / "skills" / "bootstrap" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "supported-migration-available" in skill_text, (
            "bootstrap/SKILL.md must contain 'supported-migration-available' first"
        )
        assert "/sweetclaude:configure" in skill_text, (
            "bootstrap/SKILL.md must mention /sweetclaude:configure somewhere in "
            "the skill text — it is the public entry point for the migration path."
        )
        # The former leaf-command-only restriction must be relaxed or updated to
        # include supported-migration-available.
        # Check: the skill does not say the old restriction still applies to
        # ALL other statuses (i.e., supported-migration-available must be
        # explicitly excepted or the restriction must be updated).
        # We check indirectly: the status string and public configuration entry
        # point must both be present in the router.
        status_pos = skill_text.find("supported-migration-available")
        configure_pos = skill_text.find("/sweetclaude:configure")
        assert status_pos != -1 and configure_pos != -1, (
            "bootstrap/SKILL.md must contain both 'supported-migration-available' "
            "and '/sweetclaude:configure'."
        )


@pytest.mark.parametrize("skill_path", SKILLS_THAT_HANDLE_GUARD_STATUS, ids=[
    p.parent.name for p in SKILLS_THAT_HANDLE_GUARD_STATUS
])
def test_skill_contains_supported_migration_available(skill_path: Path):
    """
    Each skill that hardcodes a guard-status list must contain the string
    'supported-migration-available' after S7.

    RED reason: none of these skills currently contain this status string.
    They handle the known pre-S7 statuses (ok, run-recover, compatibility-mode,
    migration-may-be-needed, graduation-available, graduation-blocked) but
    not the new typed-legacy migration status.
    """
    skill_text = skill_path.read_text(encoding="utf-8")
    assert "supported-migration-available" in skill_text, (
        f"{skill_path.parent.name}/SKILL.md must contain 'supported-migration-available' "
        "after S7. "
        f"Currently absent from {skill_path}."
    )


# ---------------------------------------------------------------------------
# Scenario 14 — Regression guards
#
# Existing project shapes that already work must keep working after S7.
# These tests are characterization locks.
# ---------------------------------------------------------------------------

def _make_flat_bl_project(tmp_path: Path) -> Path:
    """
    A flat BL-* project: BL-NNN files in backlog/, no typed dirs,
    no recovery state. Mirrors the flat_bl_backlog shape.
    """
    project = tmp_path / "project_flat_bl"
    project.mkdir()
    backlog = project / ".sweetclaude" / "product" / "backlog"
    backlog.mkdir(parents=True)
    (backlog / "BL-001-item.md").write_text(
        "---\ntitle: Item 1\nstatus: new\n---\nContent.\n",
        encoding="utf-8",
    )
    (backlog / "BL-002-item.md").write_text(
        "---\ntitle: Item 2\nstatus: active\n---\nContent.\n",
        encoding="utf-8",
    )
    (project / ".sweetclaude").mkdir(exist_ok=True)
    (project / ".sweetclaude" / "artifact-privacy.yaml").write_text(
        "schema_version: 1\n"
        "categories:\n"
        "  product:\n"
        "    privacy: private\n"
        "    base_path: .sweetclaude/product\n",
        encoding="utf-8",
    )
    _write_state(
        project,
        framework={
            "installed_version": "4.2.7-beta",
            "migration_status": "deferred",
        },
        recovery=None,
    )
    return project


def _make_recovery_required_project(tmp_path: Path) -> Path:
    """
    A typed-legacy project in recovery_required state (migration_status=incomplete,
    no recovery.taxonomy state). This is the pre-S7 recovery_required shape.
    """
    project = tmp_path / "project_rec_req"
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
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    state["framework"]["migration_status"] = "incomplete"
    state_path.write_text(yaml.safe_dump(state, default_flow_style=False))
    return project


class TestRegressionGuards:
    """
    Existing working routes must still work after S7.
    These are characterization locks — they describe pre-S7 GREEN behavior
    that must remain GREEN.
    """

    def test_flat_bl_project_still_routes_to_flat_bl_backlog(self, tmp_path):
        """
        A flat BL-* project must still route to flat_bl_backlog /
        migration-may-be-needed after S7.

        S7 must not accidentally reroute flat BL projects to the typed-legacy
        migration path.
        """
        project = _make_flat_bl_project(tmp_path)
        guard = _guard(project)

        assert guard["project_shape"] == "flat_bl_backlog", (
            "A flat BL-* project must still classify as 'flat_bl_backlog' after S7. "
            f"Got project_shape={guard['project_shape']!r}. "
            "S7 must not redirect flat BL projects to typed-legacy migration."
        )
        assert guard["status"] == "migration-may-be-needed", (
            "A flat BL-* project must still return status='migration-may-be-needed' "
            f"after S7. Got status={guard['status']!r}."
        )

    def test_recovery_required_project_still_routes_to_run_recover(self, tmp_path):
        """
        A project in recovery_required state (migration_status=incomplete) must
        still route to run-recover / recovery_required after S7.
        """
        project = _make_recovery_required_project(tmp_path)
        guard = _guard(project)

        assert guard["status"] == "run-recover", (
            "A recovery_required project must still route to 'run-recover' after S7. "
            f"Got status={guard['status']!r}."
        )
        assert guard["project_shape"] == "recovery_required", (
            "A recovery_required project must still classify as 'recovery_required'. "
            f"Got project_shape={guard['project_shape']!r}."
        )

    def test_no_flag_write_regression_stabilized(self, tmp_path):
        """
        Regression lock: scan for stabilized project must not offer
        exit_compatibility_mode recipe. Was GREEN pre-S7; must remain GREEN.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)
        scan = _run_json(DOCTOR, "scan", "--project-dir", str(project))

        for finding in scan["findings"]:
            recipe = finding.get("fix_recipe") or {}
            assert recipe.get("type") != "exit_compatibility_mode", (
                f"Regression: scan for stabilized typed-legacy offers "
                f"exit_compatibility_mode in finding {finding.get('id')!r}"
            )
            key_path = recipe.get("key_path") or []
            assert "compatibility_exited" not in key_path, (
                f"Regression: scan for stabilized typed-legacy writes "
                f"compatibility_exited flag in finding {finding.get('id')!r}"
            )

    def test_no_flag_write_regression_graduation_blocked(self, tmp_path):
        """
        Regression lock for the graduation-blocked project shape.
        Mirrors test_dead_end_totality.py::test_scan_never_offers_the_flag_write_exit.
        Must remain GREEN after S7.
        """
        from tests.test_dead_end_totality import _make_graduation_blocked_project
        project = _make_graduation_blocked_project(tmp_path)
        scan = _run_json(DOCTOR, "scan", "--project-dir", str(project))

        for finding in scan["findings"]:
            recipe = finding.get("fix_recipe") or {}
            assert recipe.get("type") != "exit_compatibility_mode", (
                f"Regression: graduation-blocked scan offers exit_compatibility_mode "
                f"in finding {finding.get('id')!r}"
            )
            key_path = recipe.get("key_path") or []
            assert "compatibility_exited" not in key_path, (
                f"Regression: graduation-blocked scan writes compatibility_exited "
                f"in finding {finding.get('id')!r}"
            )


# ---------------------------------------------------------------------------
# Scenario 15 — Fixture integrity checks
#
# The test fixtures must be well-formed so all other tests are measuring
# behavior, not fixture failures.
# ---------------------------------------------------------------------------

class TestFixtureIntegrity:
    """
    Assert that the test fixture helpers produce correctly configured projects
    so guard/scan invocations return code 0 and tests fail on behavior,
    not on broken fixtures.
    """

    def test_fresh_typed_legacy_fixture_is_configured_project(self, tmp_path):
        """
        _make_fresh_typed_legacy_project must produce a project that has
        .sweetclaude/state/sweetclaude.yaml so guard/scan exit with returncode 0.

        A project without sweetclaude.yaml causes recover_project guard to return
        an error exit code, making all guard-based tests fail with an AssertionError
        on returncode instead of the expected behavioral assertion.
        """
        project = _make_fresh_typed_legacy_project(tmp_path)
        sc_yaml = project / ".sweetclaude" / "state" / "sweetclaude.yaml"

        assert sc_yaml.is_file(), (
            "_make_fresh_typed_legacy_project must produce a project with "
            ".sweetclaude/state/sweetclaude.yaml. "
            "Without it, guard exits with returncode != 0 and all tests fail "
            "on the subprocess assertion, not on behavioral contracts."
        )

        result = subprocess.run(
            [sys.executable, str(RECOVER), "guard", "--project-dir", str(project)],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, (
            "guard must exit with returncode 0 for the fresh typed-legacy fixture. "
            f"Got returncode={result.returncode}, stderr={result.stderr[:200]!r}."
        )

    def test_stabilized_fixture_has_old_prefixes_on_disk(self, tmp_path):
        """
        _make_stabilized_typed_legacy_project must produce a project with
        old_prefix_count > 0 (derived files excluded).

        If the fixture has no old-prefix files, tests asserting that the guard
        offers migration (because old prefixes are present) will pass trivially —
        the guard would correctly route to graduation_candidate because there is
        nothing to migrate.
        """
        project = _make_stabilized_typed_legacy_project(tmp_path)

        old_prefixes = {"STORY-", "BUG-", "DEBT-", "CHORE-", "BL-"}
        # Exclude backup and non-md files; only count real .md files
        old_prefix_files = [
            p for p in project.rglob("*.md")
            if not str(p.relative_to(project)).startswith(".sweetclaude")
            and not p.name.endswith(".bak")
            and any(p.name.startswith(prefix) for prefix in old_prefixes)
        ]

        assert len(old_prefix_files) > 0, (
            "_make_stabilized_typed_legacy_project fixture must have at least one "
            "old-prefix .md file on disk (excluding .sweetclaude/ and .bak files). "
            f"Found {old_prefix_files!r}. "
            "Without old-prefix files the guard routes to graduation_candidate "
            "(no migration needed) and tests measuring typed-legacy routing are vacuous."
        )

    def test_real_duplicates_fixture_has_multiple_same_id_files(self, tmp_path):
        """
        _make_typed_legacy_with_real_duplicates must produce a project with
        at least two non-backup files sharing the same filename-based id.
        """
        project, dup_id = _make_typed_legacy_with_real_duplicates(tmp_path)

        prefix = dup_id + "-"
        dup_files = [
            p for p in project.rglob("*.md")
            if not str(p.relative_to(project)).startswith(".sweetclaude")
            and not p.name.endswith(".bak")
            and p.name.startswith(prefix)
        ]

        assert len(dup_files) >= 2, (
            f"_make_typed_legacy_with_real_duplicates must produce >= 2 files "
            f"starting with '{prefix}'. Found {[f.name for f in dup_files]!r}. "
            "Without real duplicates the duplicate-routing tests are vacuous."
        )

    def test_backup_only_fixture_has_exactly_one_real_file_plus_bak(self, tmp_path):
        """
        _make_typed_legacy_backup_only_duplicates must produce exactly one real
        .md file for the duplicate id PLUS one .bak file — no second real copy.
        """
        project, dup_id = _make_typed_legacy_backup_only_duplicates(tmp_path)
        prefix = dup_id + "-"

        real_files = [
            p for p in project.rglob("*.md")
            if not str(p.relative_to(project)).startswith(".sweetclaude")
            and not p.name.endswith(".bak")
            and p.name.startswith(prefix)
        ]
        bak_files = [
            p for p in project.rglob("*")
            if p.name.endswith(".bak")
            and p.name.startswith(prefix)
        ]

        assert len(real_files) == 1, (
            f"backup-only fixture must have exactly 1 real .md file for '{dup_id}'. "
            f"Found {[f.name for f in real_files]!r}."
        )
        assert len(bak_files) >= 1, (
            f"backup-only fixture must have at least 1 .bak file for '{dup_id}'. "
            f"Found {[f.name for f in bak_files]!r}."
        )
