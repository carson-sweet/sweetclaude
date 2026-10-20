import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parents[1]
SCRIPT = REPO_ROOT / "scripts" / "migrate" / "migrate-v3-to-v4.py"
SYNCOG_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "syncog-layout"
MIGRATE_SMOKE = REPO_ROOT / "tests" / "fixtures" / "migrate-smoke"


def _copy_syncog_fixture(tmp_path: Path) -> Path:
    project = tmp_path / "syncog-layout"
    shutil.copytree(SYNCOG_FIXTURE, project)
    state_dir = project / ".sweetclaude" / "state"
    state_dir.mkdir(parents=True)
    (project / ".sweetclaude" / "artifact-privacy.yaml").write_text(
        "categories:\n"
        "  product:\n"
        "    base_path: docs/product\n",
        encoding="utf-8",
    )
    (state_dir / "sweetclaude.yaml").write_text(
        "framework:\n"
        "  installed_version: 4.1.3-beta\n"
        "  migration_status: complete\n"
        "paths:\n"
        "  product_base: docs/product\n",
        encoding="utf-8",
    )
    return project


def _copy_flat_bl_fixture(tmp_path: Path) -> Path:
    project = tmp_path / "flat-bl"
    shutil.copytree(MIGRATE_SMOKE, project)
    return project


def _file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _run_migrator(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--project-dir", str(project)],
        check=False,
        capture_output=True,
        text=True,
    )


def _blocking_codes(preflight: dict) -> set[str]:
    return {factor["code"] for factor in preflight.get("blocking_factors", [])}


def _approval_receipt_from_plan(project: Path, plan: dict, **overrides) -> Path:
    receipt = dict(plan["mutation_plan"]["approval_receipt_template"])
    receipt["approved"] = True
    for key, value in overrides.items():
        if key == "context":
            context = dict(receipt["context"])
            context.update(value)
            receipt["context"] = context
        else:
            receipt[key] = value
    path = project / ".sweetclaude" / "state" / "migrations" / "approval-receipt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_migrate_preflight_blocks_unsupported_typed_layout_without_writes(tmp_path):
    project = _copy_syncog_fixture(tmp_path)
    before = _file_snapshot(project)

    result = _run_migrator(project, "preflight")

    assert result.returncode == 0, result.stderr
    preflight = json.loads(result.stdout)
    assert preflight["status"] == "blocked"
    assert preflight["migrate_allowed"] is False
    assert preflight["capability_id"] == "migrate.flat_bl_to_issue"
    assert preflight["project_shape"] == "typed_legacy_backlog"
    assert preflight["manifest_supported"] is False
    assert preflight["supported_project_shapes"] == ["flat_bl_backlog"]
    assert preflight["flat_bl_count"] == 0
    assert preflight["typed_old_prefix_count"] == 5
    assert {
        "manifest-capability-unsupported",
        "unsupported-project-shape",
        "unsupported-typed-backlog-layout",
        "duplicate-work-item-ids",
    }.issubset(_blocking_codes(preflight))
    assert _file_snapshot(project) == before


def test_migrate_execute_blocks_unsupported_typed_layout_before_writes(tmp_path):
    project = _copy_syncog_fixture(tmp_path)
    before = _file_snapshot(project)

    result = _run_migrator(project, "execute", "--include-done")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert "unsupported-typed-backlog-layout" in _blocking_codes(payload["preflight"])
    assert payload["preflight"]["project_shape"] == "typed_legacy_backlog"
    assert _file_snapshot(project) == before
    assert not (project / ".sweetclaude" / "product" / "backlog" / "MIGRATION-MAP.md").exists()


def test_migrate_preflight_allows_manifest_supported_flat_bl_fixture(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    before = _file_snapshot(project)

    result = _run_migrator(project, "preflight")

    assert result.returncode == 0, result.stderr
    preflight = json.loads(result.stdout)
    assert preflight["status"] == "ok"
    assert preflight["migrate_allowed"] is True
    assert preflight["capability_id"] == "migrate.flat_bl_to_issue"
    assert preflight["project_shape"] == "flat_bl_backlog"
    assert preflight["manifest_supported"] is True
    assert preflight["supported_project_shapes"] == ["flat_bl_backlog"]
    assert "snapshot" in preflight["safety_contract"]
    assert preflight["flat_bl_count"] > 0
    assert preflight["blocking_factors"] == []
    assert _file_snapshot(project) == before


def test_migrate_plan_emits_manifest_contract_for_supported_flat_bl_fixture(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    before = _file_snapshot(project)

    result = _run_migrator(project, "plan", "--include-done")

    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan["capability_id"] == "migrate.flat_bl_to_issue"
    assert plan["project_shape"] == "flat_bl_backlog"
    assert plan["manifest_supported"] is True
    assert plan["preflight"]["migrate_allowed"] is True
    assert len(plan["plan_items"]) > 0
    assert _file_snapshot(project) == before


def test_migrate_plan_emits_mutation_lifecycle_plan_for_supported_fixture(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)

    result = _run_migrator(project, "plan", "--include-done")

    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    mutation_plan = plan["mutation_plan"]
    assert mutation_plan["status"] == "approval-required"
    assert mutation_plan["approval_receipt_template"]
    assert mutation_plan["approval_receipt_template"]["approved"] is False
    assert mutation_plan["declared_write_set"]
    assert mutation_plan["write_set_hash"]
    assert ".sweetclaude/product/backlog/MIGRATION-MAP.md" in mutation_plan["declared_write_set"]
    assert ".sweetclaude/state/migrations/v3-to-v4-execution.json" in mutation_plan["declared_write_set"]
    assert ".sweetclaude/state" in mutation_plan["declared_blast_radius"]
    assert ".sweetclaude/product/backlog" in mutation_plan["declared_blast_radius"]
    assert any(check["id"] == "migration-map" for check in mutation_plan["postconditions"])


def test_migrate_execute_requires_plan_bound_approval_before_writes(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    before = _file_snapshot(project)

    result = _run_migrator(project, "execute", "--include-done")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert "missing-approval-receipt" in _blocking_codes(payload["preflight"])
    assert _file_snapshot(project) == before


def test_migrate_execute_rejects_stale_plan_hash_before_writes(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    plan_result = _run_migrator(project, "plan", "--include-done")
    plan = json.loads(plan_result.stdout)
    receipt = _approval_receipt_from_plan(project, plan, plan_hash="stale-plan-hash")
    before = _file_snapshot(project)

    result = _run_migrator(
        project,
        "execute",
        "--include-done",
        "--approval-receipt",
        str(receipt),
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert "stale-plan-hash" in _blocking_codes(payload["preflight"])
    assert _file_snapshot(project) == before


def test_migrate_execute_rejects_stale_write_set_hash_before_writes(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    plan_result = _run_migrator(project, "plan", "--include-done")
    plan = json.loads(plan_result.stdout)
    receipt = _approval_receipt_from_plan(project, plan, write_set_hash="stale-write-set")
    before = _file_snapshot(project)

    result = _run_migrator(
        project,
        "execute",
        "--include-done",
        "--approval-receipt",
        str(receipt),
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert "stale-write-set-hash" in _blocking_codes(payload["preflight"])
    assert _file_snapshot(project) == before


def test_migrate_execute_rejects_mismatched_approval_context_before_writes(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    plan_result = _run_migrator(project, "plan", "--include-done")
    plan = json.loads(plan_result.stdout)
    receipt = _approval_receipt_from_plan(project, plan, context={"project_dir": "/wrong/project"})
    before = _file_snapshot(project)

    result = _run_migrator(
        project,
        "execute",
        "--include-done",
        "--approval-receipt",
        str(receipt),
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert "approval-context-mismatch" in _blocking_codes(payload["preflight"])
    assert _file_snapshot(project) == before


def test_migrate_execute_rejects_stale_snapshot_hash_before_status_success(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    plan_result = _run_migrator(project, "plan", "--include-done")
    plan = json.loads(plan_result.stdout)
    receipt = _approval_receipt_from_plan(project, plan, snapshot_hash="stale-snapshot")

    result = _run_migrator(
        project,
        "execute",
        "--include-done",
        "--approval-receipt",
        str(receipt),
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert "stale-snapshot-hash" in _blocking_codes(payload["preflight"])
    assert not (project / ".sweetclaude" / "product" / "backlog" / "MIGRATION-MAP.md").exists()
    assert not list((project / ".sweetclaude" / "product" / "backlog").glob("ISSUE-*.md"))


def test_migrate_execute_records_mutation_lifecycle_receipt(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    plan_result = _run_migrator(project, "plan", "--include-done")
    approval_receipt = _approval_receipt_from_plan(project, json.loads(plan_result.stdout))

    result = _run_migrator(
        project,
        "execute",
        "--include-done",
        "--approval-receipt",
        str(approval_receipt),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    manifest_path = Path(payload["execution_manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lifecycle = manifest["mutation_lifecycle"]
    assert lifecycle["status"] == "pass"
    assert lifecycle["approval"]["status"] == "pass"
    assert lifecycle["write_set_validation"]["status"] == "pass"
    assert lifecycle["snapshot_scope_validation"]["status"] == "pass"
    assert lifecycle["restore_proof"]["status"] == "pass"
    assert lifecycle["restore_proof"]["method"] == "fixture"
    assert lifecycle["postcondition_validation"]["status"] == "pass"
    assert lifecycle["postcondition_validation"]["postcondition_count"] >= 3


def test_migrate_plan_blocks_malformed_state_before_planning(tmp_path):
    project = _copy_syncog_fixture(tmp_path)
    state_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    state_path.write_text("framework:\n  migration_status: [\n", encoding="utf-8")
    before = _file_snapshot(project)

    result = _run_migrator(project, "plan", "--include-done")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert payload["preflight"]["project_shape"] == "manual_escalation"
    assert {
        "sweetclaude-state-parse-error",
        "manifest-capability-unsupported",
        "unsupported-project-shape",
    }.issubset(_blocking_codes(payload["preflight"]))
    assert _file_snapshot(project) == before


def test_migrate_finalize_blocks_before_successful_execute(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    before = _file_snapshot(project)

    result = _run_migrator(project, "finalize")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert {
        "missing-migration-map",
        "missing-migrated-issues",
    }.issubset(_blocking_codes(payload["preflight"]))
    assert _file_snapshot(project) == before


def test_migrate_cleanup_blocks_before_successful_execute(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    before = _file_snapshot(project)

    result = _run_migrator(project, "cleanup-v3-files")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert "missing-migration-map" in _blocking_codes(payload["preflight"])
    assert _file_snapshot(project) == before


def test_migrate_finalize_rejects_forged_completion_state(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    backlog = project / ".sweetclaude" / "product" / "backlog"
    backlog.mkdir(parents=True, exist_ok=True)
    (backlog / "MIGRATION-MAP.md").write_text("# forged\n", encoding="utf-8")
    (backlog / "ISSUE-001-forged.md").write_text(
        "---\nid: ISSUE-001\ntitle: Forged\nstatus: new\ntype: story\n---\n\nForged.\n",
        encoding="utf-8",
    )
    before = _file_snapshot(project)

    result = _run_migrator(project, "finalize")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert "missing-execution-manifest" in _blocking_codes(payload["preflight"])
    assert _file_snapshot(project) == before


def test_migrate_cleanup_rejects_forged_completion_state(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    backlog = project / ".sweetclaude" / "product" / "backlog"
    backlog.mkdir(parents=True, exist_ok=True)
    (backlog / "MIGRATION-MAP.md").write_text("# forged\n", encoding="utf-8")
    (backlog / "ISSUE-001-forged.md").write_text(
        "---\nid: ISSUE-001\ntitle: Forged\nstatus: new\ntype: story\n---\n\nForged.\n",
        encoding="utf-8",
    )
    before = _file_snapshot(project)

    result = _run_migrator(project, "cleanup-v3-files")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert "missing-execution-manifest" in _blocking_codes(payload["preflight"])
    assert _file_snapshot(project) == before


def test_migrate_finalize_rejects_forged_execution_manifest_without_integrity(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    backlog = project / ".sweetclaude" / "product" / "backlog"
    backlog.mkdir(parents=True, exist_ok=True)
    (backlog / "MIGRATION-MAP.md").write_text("# forged\n", encoding="utf-8")
    (backlog / "ISSUE-001-forged.md").write_text(
        "---\nid: ISSUE-001\ntitle: Forged\nstatus: new\ntype: story\n---\n\nForged.\n",
        encoding="utf-8",
    )
    manifest = project / ".sweetclaude" / "state" / "migrations" / "v3-to-v4-execution.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps({
            "schema_version": 1,
            "status": "succeeded",
            "capability_id": "migrate.flat_bl_to_issue",
            "project_shape": "flat_bl_backlog",
            "manifest_supported": True,
        }),
        encoding="utf-8",
    )
    before = _file_snapshot(project)

    result = _run_migrator(project, "finalize")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "migration-blocked"
    assert {
        "missing-created-file-integrity",
        "missing-source-file-integrity",
        "missing-migration-map-integrity",
    }.issubset(_blocking_codes(payload["preflight"]))
    assert _file_snapshot(project) == before


def test_migrate_execute_refuses_rerun_on_5x_migrated_project(tmp_path):
    project = _copy_flat_bl_fixture(tmp_path)
    sc_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    sc_path.write_text(
        "framework:\n"
        "  installed_version: 5.0.0\n",
        encoding="utf-8",
    )
    backlog = project / ".sweetclaude" / "product" / "backlog"
    (backlog / "ISSUE-001-migrated.md").write_text(
        "---\nid: ISSUE-001\ntitle: Migrated\nstatus: new\ntype: story\n---\n\nMigrated.\n",
        encoding="utf-8",
    )
    before = _file_snapshot(project)

    result = _run_migrator(project, "execute", "--include-done")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "already-migrated"
    assert payload["installed_version"] == "5.0.0"
    assert _file_snapshot(project) == before
