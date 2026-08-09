"""
Tests for scripts/doctor.py (ISSUE-177 E5).

Test file structure follows E5 story order:
  E5-S01: Fixture builder
  E5-S02: Per-category scan tests
  E5-S03: Auto-fix tests
  E5-S04: Content-based backup tests
  E5-S05: Post-fix rescan tests
  E5-S06: Archive integrity tests
  E5-S07: Retention tests
  E5-S08: Suppression tests
  E5-S09: Dry-run simulation tests
  E5-S10: Graceful degradation tests
  E5-S11: Early exit test
  E5-S12: Happy-path test
  E5-S13: Manifest completeness test
"""
import io
import json
import os
import shutil
import subprocess
import sys

import pytest
import yaml

_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from pathlib import Path

from doctor import (
    Finding,
    ProjectState,
    RecipeResult,
    DependencyMissing,
    CHECKS,
    build_project_state,
    build_state_summary,
    _scan,
    check_state_integrity,
    check_hook_health,
    check_storage_lint,
    check_migration_currency,
    check_config_compat,
    check_file_diagnostics,
    check_onboarding_state,
    check_env_wiring,
    check_derived_status,
    create_archive,
    backup_content,
    write_diff,
    write_manifest,
    prune_archives,
    execute_recipe,
    auto_fix,
    post_fix_rescan,
    dry_run,
    record_action,
    persist,
    load_suppressions,
    save_suppressions,
    suppress_finding,
    unsuppress_finding,
    compute_resolved_suppressions,
    prune_resolved_suppressions,
    main,
    _apply_transform,
    _atomic_write,
    _script_has_cli_entrypoint,
    build_maintenance_route,
)


# ---------------------------------------------------------------------------
# E5-S01: Fixture builder
# ---------------------------------------------------------------------------

import doctor as _doctor_module


@pytest.fixture
def patch_scripts_dir(tmp_path, monkeypatch):
    """Redirect doctor._SCRIPTS_DIR to the test fixture's scripts/ directory."""
    scripts_dir = tmp_path / "project" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(_doctor_module, "_SCRIPTS_DIR", scripts_dir)
    return scripts_dir


def _write_frontmatter_file(path, frontmatter, body=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"---\n{yaml.safe_dump(frontmatter)}---\n{body}"
    path.write_text(content)


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    claude_dir = home / ".claude"

    hooks_dir = claude_dir / "hooks" / "sweetclaude"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "hooks.json").write_text(json.dumps({"hooks": []}))

    rules_dir = claude_dir / "rules" / "sweetclaude"
    rules_dir.mkdir(parents=True)
    for rf in ["interaction-model.md", "phase-gates.md", "tdd-levels.md"]:
        (rules_dir / rf).write_text(f"# {rf}\nPlaceholder content.")

    (claude_dir / "settings.json").write_text(json.dumps({
        "plansDirectory": ".sweetclaude/plans",
    }))

    plugins_dir = claude_dir / "plugins"
    plugins_dir.mkdir(parents=True)
    (plugins_dir / "installed_plugins.json").write_text(json.dumps({
        "plugins": {
            "sweetclaude/sweetclaude": [{"version": "4.0.8-beta"}],
        },
    }))

    monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: home))
    return home


def build_fixture(tmp_path, overrides=None):
    overrides = overrides or {}
    project_dir = tmp_path / "project"

    sc = project_dir / ".sweetclaude"
    state_dir = sc / "state"
    state_dir.mkdir(parents=True)

    sc_yaml = overrides.get("sweetclaude_yaml", {
        # schema_version 2 keeps the fixture genuinely migration-current: the real
        # migration runner reports DRIFT_COUNT=0 for it. Without it the runner
        # reports sweetclaude.yaml as drifted/missing (C3.5b previously masked this
        # because the doctor swallowed the runner output).
        "schema_version": 2,
        "phase_schema_version": 2,
        "framework": {"installed_version": "4.0.8-beta"},
    })
    if sc_yaml is not None:
        (state_dir / "sweetclaude.yaml").write_text(yaml.safe_dump(sc_yaml))

    ss = overrides.get("session_state", {
        "paths": {"product_base": ".sweetclaude/product"},
    })
    if ss is not None:
        (state_dir / "session-state.yaml").write_text(yaml.safe_dump(ss))

    ap = overrides.get("artifact_privacy", {
        "categories": {"product": {"base_path": ".sweetclaude/product"}},
    })
    if ap is not None:
        (sc / "artifact-privacy.yaml").write_text(yaml.safe_dump(ap))

    skills = overrides.get("skills_yaml", {"schema_version": 2, "skills": {}})
    if skills is not None:
        (state_dir / "skills.yaml").write_text(yaml.safe_dump(skills))

    product_base = project_dir / ".sweetclaude" / "product"
    (product_base / "backlog").mkdir(parents=True, exist_ok=True)
    (product_base / "roadmap").mkdir(parents=True, exist_ok=True)

    (sc / "plans").mkdir(parents=True, exist_ok=True)

    claude_md = overrides.get("claude_md", "# Project\n\n## SweetClaude\nConfigured.")
    if claude_md is not None:
        (project_dir / "CLAUDE.md").write_text(claude_md)

    (project_dir / "hooks").mkdir(exist_ok=True)

    # Default migration runner stub. C3.5b: the doctor reads the runner's
    # machine-parseable --report-drift-for-skill mode (DRIFT_COUNT=N then
    # FINDING|<key>|v<from>-><to>|chain=<ok|broken>), NOT the human-prose
    # --scan-drift mode. This default reports a healthy project (DRIFT_COUNT=0).
    # The previous stub emitted JSON `[]`, which matched the buggy --scan-drift +
    # json.loads call and so masked the dead-path defect. NOTE: this stub only
    # takes effect for tests that also use patch_scripts_dir (which redirects
    # doctor._SCRIPTS_DIR to project/scripts); otherwise the real repo runner runs.
    runner_dir = project_dir / "scripts" / "migrations"
    runner_dir.mkdir(parents=True, exist_ok=True)
    (runner_dir / "runner.py").write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "if '--report-drift-for-skill' in sys.argv:\n"
        "    print('DRIFT_COUNT=0')\n"
        "    sys.exit(0)\n"
        "if '--scan-drift' in sys.argv:\n"
        "    print('Drift scan (2026-06-09): 0 finding(s)')\n"
        "    sys.exit(0)\n"
        "sys.exit(0)\n"
    )

    for bf in overrides.get("backlog_files", []):
        path = product_base / "backlog" / bf["name"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if "frontmatter" in bf:
            _write_frontmatter_file(path, bf["frontmatter"], bf.get("body", ""))
        else:
            path.write_text(bf.get("content", ""))

    for rf in overrides.get("roadmap_files", []):
        path = product_base / "roadmap" / rf["name"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if "frontmatter" in rf:
            _write_frontmatter_file(path, rf["frontmatter"], rf.get("body", ""))
        else:
            path.write_text(rf.get("content", ""))

    for hf in overrides.get("hook_files", []):
        hooks_dir = Path.home() / ".claude" / "hooks" / "sweetclaude"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        path = hooks_dir / hf["name"]
        path.write_text(hf["content"])

    if "hook_manifest" in overrides:
        hooks_dir = Path.home() / ".claude" / "hooks" / "sweetclaude"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (hooks_dir / "hooks-manifest.json").write_text(
            json.dumps(overrides["hook_manifest"])
        )

    if "suppressions" in overrides:
        (state_dir / "doctor-suppressions.json").write_text(
            json.dumps(overrides["suppressions"])
        )

    if "settings_local" in overrides:
        local_dir = project_dir / ".claude"
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "settings.local.json").write_text(
            json.dumps(overrides["settings_local"])
        )

    return project_dir


@pytest.fixture
def healthy_project(tmp_path, fake_home):
    return build_fixture(tmp_path)


class TestFixtureBuilder:
    def test_healthy_default_zero_findings(self, healthy_project, fake_home):
        state = build_project_state(healthy_project)
        result = _scan(state)
        assert result["findings"] == [], (
            f"Healthy fixture should produce zero findings, got: "
            f"{[f['id'] for f in result['findings']]}"
        )

    def test_healthy_default_no_skipped_categories(self, healthy_project, fake_home):
        state = build_project_state(healthy_project)
        result = _scan(state)
        assert result["skipped_categories"] == []

    def test_fixture_creates_required_directories(self, healthy_project):
        assert (healthy_project / ".sweetclaude" / "state").is_dir()
        assert (healthy_project / ".sweetclaude" / "product" / "backlog").is_dir()
        assert (healthy_project / ".sweetclaude" / "product" / "roadmap").is_dir()
        assert (healthy_project / ".sweetclaude" / "plans").is_dir()
        assert (healthy_project / "hooks").is_dir()

    def test_fixture_creates_required_files(self, healthy_project):
        state_dir = healthy_project / ".sweetclaude" / "state"
        assert (state_dir / "sweetclaude.yaml").exists()
        assert (state_dir / "session-state.yaml").exists()
        assert (state_dir / "skills.yaml").exists()
        assert (healthy_project / ".sweetclaude" / "artifact-privacy.yaml").exists()
        assert (healthy_project / "CLAUDE.md").exists()

    def test_fixture_overrides_backlog_files(self, tmp_path, fake_home):
        project = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "active",
                }},
            ],
        })
        assert (project / ".sweetclaude" / "product" / "backlog" / "ISSUE-001-test.md").exists()

    def test_fixture_overrides_hook_files(self, tmp_path, fake_home):
        project = build_fixture(tmp_path, overrides={
            "hook_files": [{"name": "test-hook.sh", "content": "#!/bin/bash\nexit 0\n"}],
        })
        assert (Path.home() / ".claude" / "hooks" / "sweetclaude" / "test-hook.sh").exists()

    def test_fixture_overrides_suppressions(self, tmp_path, fake_home):
        project = build_fixture(tmp_path, overrides={
            "suppressions": [{"finding_id": "test:id", "suppressed_at": "2026-01-01"}],
        })
        data = json.loads(
            (project / ".sweetclaude" / "state" / "doctor-suppressions.json").read_text()
        )
        assert len(data) == 1
        assert data[0]["finding_id"] == "test:id"

    def test_build_project_state_populates_all_fields(self, healthy_project, fake_home):
        state = build_project_state(healthy_project)
        assert state.project_dir == healthy_project
        assert state.sweetclaude_yaml is not None
        assert state.session_state is not None
        assert state.artifact_privacy is not None
        assert state.skills_yaml is not None
        assert state.hooks_json is not None
        assert state.settings_global is not None
        assert state.claude_md_project is not None
        assert state.installed_version == "4.0.8-beta"
        assert len(state.rules_files) == 3


# ---------------------------------------------------------------------------
# State integrity checks (doctor-state-integrity.feature)
# ---------------------------------------------------------------------------

class TestStateIntegrity:
    """
    Tests for check_state_integrity(state) -> list[Finding].

    Each method corresponds to one Gherkin scenario in
    tests/features/doctor-state-integrity.feature.
    """

    # ------------------------------------------------------------------
    # Scenario: Healthy project produces no state_integrity findings
    # ------------------------------------------------------------------

    def test_healthy_project_produces_no_state_integrity_findings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_state_integrity(state)
        assert findings == [], (
            f"Healthy project should produce 0 state_integrity findings, "
            f"got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # Scenario: sweetclaude.yaml has a YAML parse error
    # ------------------------------------------------------------------

    def test_yaml_parse_error_in_sweetclaude_yaml(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={"sweetclaude_yaml": None})
        sc_yaml_path = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
        sc_yaml_path.write_text("{{bad: yaml: [unclosed")

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        assert len(findings) == 1
        f = findings[0]
        assert f.id == "state-integrity:yaml-parse:sweetclaude.yaml"
        assert f.severity == "error"
        assert f.fix_type == "prompted"
        assert f.fix_recipe["action"] == "prompt"

    # ------------------------------------------------------------------
    # Scenario: session-state.yaml is missing
    # ------------------------------------------------------------------

    def test_missing_session_state_yaml(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={"session_state": None})

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        assert len(findings) == 1
        f = findings[0]
        assert f.id == "state-integrity:missing:session-state.yaml"
        assert f.severity == "warning"
        assert f.fix_type == "auto"
        assert f.fix_recipe["action"] == "run_script"

    # ------------------------------------------------------------------
    # Scenario: phase_schema_version is not 2
    # ------------------------------------------------------------------

    def test_phase_schema_version_not_2(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "sweetclaude_yaml": {
                "phase_schema_version": 1,
                "framework": {"installed_version": "4.0.8-beta"},
            },
        })

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        assert len(findings) == 1
        f = findings[0]
        assert f.id == "state-integrity:schema-version:sweetclaude.yaml"
        assert f.severity == "warning"
        assert f.fix_type in ("auto", "report-only")
        if f.fix_type == "auto":
            assert f.fix_recipe["action"] == "run_script"
            assert "runner.py" in f.fix_recipe["cmd"][1]

    # ------------------------------------------------------------------
    # Scenario: installed_version drifts from installed_plugins.json
    # ------------------------------------------------------------------

    def test_installed_version_drift(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "sweetclaude_yaml": {
                "phase_schema_version": 2,
                "framework": {"installed_version": "3.0.0"},
            },
        })
        # fake_home already has installed_plugins.json reporting "4.0.8-beta"

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        assert len(findings) == 1
        f = findings[0]
        assert f.id == "state-integrity:version-drift:installed_version"
        assert f.severity == "warning"
        assert f.fix_type == "auto"
        assert f.fix_recipe["action"] == "write_field"
        assert f.fix_recipe["key"] == "framework"
        assert f.fix_recipe["value"]["installed_version"] == "4.0.8-beta"

    # ------------------------------------------------------------------
    # Scenario: product_base diverges between artifact-privacy.yaml and
    #           session-state.yaml
    # ------------------------------------------------------------------

    def test_product_base_drift_between_artifact_privacy_and_session_state(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "artifact_privacy": {
                "categories": {"product": {"base_path": ".sweetclaude/product"}},
            },
            "session_state": {
                "paths": {"product_base": "docs/product"},
            },
        })

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        assert len(findings) == 1
        f = findings[0]
        assert f.id == "state-integrity:product-base-drift:session-state"
        assert f.severity == "warning"
        assert f.fix_type == "auto"
        assert f.fix_recipe["action"] == "run_script"
        assert len(f.file_paths) == 2

    # ------------------------------------------------------------------
    # Scenario: sweetclaude.yaml exists but is empty (parsed as None)
    # ------------------------------------------------------------------

    def test_empty_sweetclaude_yaml_does_not_trigger_parse_or_schema_findings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={"sweetclaude_yaml": None})
        sc_yaml_path = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
        sc_yaml_path.write_text("---\n---")

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        yaml_parse_ids = [
            f.id for f in findings if f.id.startswith("state-integrity:yaml-parse")
        ]
        schema_version_ids = [
            f.id for f in findings if f.id.startswith("state-integrity:schema-version")
        ]
        assert yaml_parse_ids == [], (
            f"Expected no yaml-parse findings but got: {yaml_parse_ids}"
        )
        assert schema_version_ids == [], (
            f"Expected no schema-version findings but got: {schema_version_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Both artifact-privacy and session-state are missing
    # ------------------------------------------------------------------

    def test_both_artifact_privacy_and_session_state_missing(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "artifact_privacy": None,
            "session_state": None,
        })

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        missing_findings = [
            f for f in findings if f.id.startswith("state-integrity:missing")
        ]
        assert len(missing_findings) == 1, (
            f"Expected exactly 1 finding with id prefix 'state-integrity:missing', "
            f"got: {[f.id for f in missing_findings]}"
        )

    # ------------------------------------------------------------------
    # Scenario: sweetclaude.yaml does not exist on disk (R1)
    # ------------------------------------------------------------------

    def test_sweetclaude_yaml_absent_skips_parse_schema_and_version_drift(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={"sweetclaude_yaml": None})
        # Do NOT write the file — leave it absent entirely

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        yaml_parse_ids = [
            f.id for f in findings if f.id.startswith("state-integrity:yaml-parse")
        ]
        schema_version_ids = [
            f.id for f in findings if f.id.startswith("state-integrity:schema-version")
        ]
        version_drift_ids = [
            f.id for f in findings if f.id.startswith("state-integrity:version-drift")
        ]
        assert yaml_parse_ids == [], (
            f"Expected no yaml-parse findings when file absent, got: {yaml_parse_ids}"
        )
        assert schema_version_ids == [], (
            f"Expected no schema-version findings when file absent, "
            f"got: {schema_version_ids}"
        )
        assert version_drift_ids == [], (
            f"Expected no version-drift findings when file absent, "
            f"got: {version_drift_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Multiple problems produce multiple findings in a single
    #           run (R2)
    # ------------------------------------------------------------------

    def test_multiple_problems_accumulate_findings(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={"sweetclaude_yaml": None, "session_state": None})
        sc_yaml_path = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
        sc_yaml_path.write_text("{{bad: yaml: [unclosed")
        # session-state.yaml is also absent (session_state=None means not written)

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        assert len(findings) == 2
        finding_ids = [f.id for f in findings]
        assert "state-integrity:yaml-parse:sweetclaude.yaml" in finding_ids, (
            f"Expected yaml-parse finding, got: {finding_ids}"
        )
        assert "state-integrity:missing:session-state.yaml" in finding_ids, (
            f"Expected missing session-state finding, got: {finding_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Trailing slashes on product base paths do not trigger
    #           false drift (R3)
    # ------------------------------------------------------------------

    def test_trailing_slash_normalization_no_false_drift(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "artifact_privacy": {
                "categories": {"product": {"base_path": ".sweetclaude/product/"}},
            },
            "session_state": {
                "paths": {"product_base": ".sweetclaude/product"},
            },
        })

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        drift_ids = [
            f.id for f in findings if f.id.startswith("state-integrity:product-base-drift")
        ]
        assert drift_ids == [], (
            f"Trailing slash difference should not trigger drift, got: {drift_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: framework key missing from sweetclaude.yaml skips
    #           version drift (R4)
    # ------------------------------------------------------------------

    def test_missing_framework_key_skips_version_drift(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "sweetclaude_yaml": {
                "phase_schema_version": 2,
                # no "framework" key
            },
        })

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        drift_ids = [
            f.id for f in findings if f.id.startswith("state-integrity:version-drift")
        ]
        assert drift_ids == [], (
            f"Missing framework key should skip version-drift check, got: {drift_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: installed_plugins.json absent skips version drift
    #           silently (R5)
    # ------------------------------------------------------------------

    def test_absent_installed_plugins_json_skips_version_drift(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "sweetclaude_yaml": {
                "phase_schema_version": 2,
                "framework": {"installed_version": "3.0.0"},
            },
        })

        plugins_json = (
            fake_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        plugins_json.unlink()

        state = build_project_state(project_dir)
        assert state.installed_version is None, (
            f"Expected installed_version to be None when file absent, "
            f"got: {state.installed_version}"
        )

        findings = check_state_integrity(state)

        drift_ids = [
            f.id for f in findings if f.id.startswith("state-integrity:version-drift")
        ]
        assert drift_ids == [], (
            f"Absent installed_plugins.json should skip version-drift silently, "
            f"got: {drift_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: artifact-privacy with null categories skips product
    #           base drift (R6)
    # ------------------------------------------------------------------

    def test_null_categories_in_artifact_privacy_skips_product_base_drift(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "artifact_privacy": {
                "categories": None,
            },
        })

        state = build_project_state(project_dir)
        findings = check_state_integrity(state)

        drift_ids = [
            f.id for f in findings if f.id.startswith("state-integrity:product-base-drift")
        ]
        assert drift_ids == [], (
            f"Null categories should skip product-base-drift check, got: {drift_ids}"
        )


# ---------------------------------------------------------------------------
# Hook health checks (doctor-hook-health.feature)
# ---------------------------------------------------------------------------

class TestHookHealth:
    """
    Tests for check_hook_health(state) -> list[Finding].

    Each method corresponds to one Gherkin scenario in
    tests/features/doctor-hook-health.feature.
    """

    # ------------------------------------------------------------------
    # Scenario: Healthy project produces no hook_health findings
    # ------------------------------------------------------------------

    def test_healthy_project_produces_no_hook_health_findings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_hook_health(state)
        assert findings == [], (
            f"Healthy project should produce 0 hook_health findings, "
            f"got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # hooks.json checks
    # ------------------------------------------------------------------

    # Scenario: hooks.json is missing
    def test_hooks_json_missing_produces_error_finding(self, tmp_path, fake_home):
        hooks_json_path = (
            fake_home / ".claude" / "hooks" / "sweetclaude" / "hooks.json"
        )
        hooks_json_path.unlink()

        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert len(findings) >= 1, f"Expected at least 1 finding, got: {ids}"
        assert "hook-health:missing:hooks.json" in ids, (
            f"Expected finding 'hook-health:missing:hooks.json' in {ids}"
        )

        f = next(x for x in findings if x.id == "hook-health:missing:hooks.json")
        assert f.severity == "error"
        assert f.fix_type == "prompted"
        assert f.fix_recipe["action"] == "prompt"
        assert f.fix_recipe["type"] == "hook_restore"

    # Scenario: hooks.json is empty dict (not None) produces no finding
    def test_hooks_json_empty_dict_produces_no_missing_finding(
        self, tmp_path, fake_home
    ):
        hooks_json_path = (
            fake_home / ".claude" / "hooks" / "sweetclaude" / "hooks.json"
        )
        hooks_json_path.write_text("{}")

        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert "hook-health:missing:hooks.json" not in ids, (
            f"Empty dict hooks.json should not produce missing finding, got: {ids}"
        )

    # ------------------------------------------------------------------
    # Hook script syntax checks
    # ------------------------------------------------------------------

    # Scenario: Hook script with valid syntax produces no finding
    def test_valid_hook_script_produces_no_syntax_finding(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "hook_files": [{"name": "good-hook.sh", "content": "#!/bin/bash\nexit 0\n"}],
        })
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        syntax_ids = [
            f.id for f in findings if f.id.startswith("hook-health:syntax-error")
        ]
        assert syntax_ids == [], (
            f"Valid hook script should produce no syntax-error finding, got: {syntax_ids}"
        )

    # Scenario: Hook script with syntax error produces error finding
    def test_bad_hook_script_produces_syntax_error_finding(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "hook_files": [{"name": "bad-hook.sh", "content": "#!/bin/bash\nif then\n"}],
        })
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert "hook-health:syntax-error:bad-hook.sh" in ids, (
            f"Expected 'hook-health:syntax-error:bad-hook.sh' in {ids}"
        )

        f = next(x for x in findings if x.id == "hook-health:syntax-error:bad-hook.sh")
        assert f.severity == "error"
        assert f.fix_type == "prompted"
        assert f.fix_recipe["type"] == "hook_restore"

    # Scenario: Multiple hook scripts with mixed syntax
    def test_mixed_hook_scripts_only_bad_gets_syntax_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "hook_files": [
                {"name": "good.sh", "content": "#!/bin/bash\nexit 0\n"},
                {"name": "bad.sh", "content": "#!/bin/bash\nif then\n"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert "hook-health:syntax-error:bad.sh" in ids, (
            f"Expected finding for bad.sh in {ids}"
        )
        assert "hook-health:syntax-error:good.sh" not in ids, (
            f"Should not have finding for good.sh, got: {ids}"
        )

    # Scenario: No hook files in project produces no syntax findings
    def test_no_hook_files_produces_no_syntax_findings(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        syntax_ids = [
            f.id for f in findings if f.id.startswith("hook-health:syntax-error")
        ]
        assert syntax_ids == [], (
            f"No hook files should produce no syntax-error findings, got: {syntax_ids}"
        )

    # Scenario: Empty hook file (zero bytes) passes syntax check
    def test_empty_hook_file_passes_syntax_check(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "hook_files": [{"name": "empty.sh", "content": ""}],
        })
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert "hook-health:syntax-error:empty.sh" not in ids, (
            f"Empty hook file should pass syntax check, got: {ids}"
        )

    # Scenario: Binary content in hook file produces syntax error finding
    def test_binary_hook_file_produces_syntax_error_finding(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "hook_files": [
                {
                    "name": "not-bash.sh",
                    "content": "this is not a valid shell script at all \x00\x01",
                }
            ],
        })
        # Write the actual bytes directly (overriding the text write in build_fixture)
        hook_path = project_dir / "hooks" / "not-bash.sh"
        hook_path.write_bytes(b"this is not a valid shell script at all \x00\x01")

        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert "hook-health:syntax-error:not-bash.sh" in ids, (
            f"Binary hook file should produce syntax error finding, got: {ids}"
        )

    # ------------------------------------------------------------------
    # Exception handling (bash -n timeout/crash)
    # ------------------------------------------------------------------

    # Scenario: bash -n timeout is silently skipped
    def test_timeout_on_bash_syntax_check_is_silently_skipped(
        self, tmp_path, fake_home, monkeypatch
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "hook_files": [{"name": "slow.sh", "content": "#!/bin/bash\nexit 0\n"}],
        })

        original_run = subprocess.run

        def mock_run(cmd, **kwargs):
            if any("slow.sh" in str(c) for c in cmd):
                raise subprocess.TimeoutExpired(cmd, 5)
            return original_run(cmd, **kwargs)

        monkeypatch.setattr("subprocess.run", mock_run)

        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert "hook-health:syntax-error:slow.sh" not in ids, (
            f"TimeoutExpired should be silently skipped, got: {ids}"
        )

    # Scenario: bash -n OSError is silently skipped and other files still checked
    def test_oserror_on_bash_syntax_check_is_silently_skipped(
        self, tmp_path, fake_home, monkeypatch
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "hook_files": [
                {"name": "broken.sh", "content": "#!/bin/bash\nexit 0\n"},
                {"name": "good.sh", "content": "#!/bin/bash\nexit 0\n"},
            ],
        })

        original_run = subprocess.run

        def mock_run(cmd, **kwargs):
            if any("broken.sh" in str(c) for c in cmd):
                raise OSError("bash not found")
            return original_run(cmd, **kwargs)

        monkeypatch.setattr("subprocess.run", mock_run)

        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert "hook-health:syntax-error:broken.sh" not in ids, (
            f"OSError should be silently skipped for broken.sh, got: {ids}"
        )
        assert "hook-health:syntax-error:good.sh" not in ids, (
            f"OSError on broken.sh should not affect good.sh check, got: {ids}"
        )

    # ------------------------------------------------------------------
    # Rules file checks
    # ------------------------------------------------------------------

    # Scenario: One rules file missing produces one warning
    def test_one_rules_file_missing_produces_one_warning(self, tmp_path, fake_home):
        rules_file = (
            fake_home / ".claude" / "rules" / "sweetclaude" / "interaction-model.md"
        )
        rules_file.unlink()

        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert "hook-health:missing-rule:interaction-model.md" in ids, (
            f"Expected finding for missing interaction-model.md in {ids}"
        )

        f = next(
            x for x in findings
            if x.id == "hook-health:missing-rule:interaction-model.md"
        )
        assert f.severity == "warning"
        assert f.fix_type == "prompted"
        assert f.fix_recipe["action"] == "prompt"
        assert f.fix_recipe["type"] == "hook_restore"

    # Scenario: All three rules files missing produces three warnings
    def test_all_three_rules_files_missing_produces_three_warnings(
        self, tmp_path, fake_home
    ):
        rules_dir = fake_home / ".claude" / "rules" / "sweetclaude"
        for rf in ["interaction-model.md", "phase-gates.md", "tdd-levels.md"]:
            (rules_dir / rf).unlink()

        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        rule_ids = [
            f.id for f in findings if f.id.startswith("hook-health:missing-rule")
        ]
        assert len(rule_ids) >= 3, (
            f"Expected at least 3 missing-rule findings, got: {rule_ids}"
        )
        assert "hook-health:missing-rule:interaction-model.md" in rule_ids
        assert "hook-health:missing-rule:phase-gates.md" in rule_ids
        assert "hook-health:missing-rule:tdd-levels.md" in rule_ids

    # ------------------------------------------------------------------
    # Interaction: multiple check blocks fire together
    # ------------------------------------------------------------------

    # Scenario: hooks.json missing and rules file missing accumulate findings
    def test_hooks_json_missing_and_rules_file_missing_accumulate_findings(
        self, tmp_path, fake_home
    ):
        hooks_json_path = (
            fake_home / ".claude" / "hooks" / "sweetclaude" / "hooks.json"
        )
        hooks_json_path.unlink()

        rules_file = (
            fake_home / ".claude" / "rules" / "sweetclaude" / "tdd-levels.md"
        )
        rules_file.unlink()

        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert len(findings) >= 2, (
            f"Expected at least 2 findings, got: {ids}"
        )
        assert "hook-health:missing:hooks.json" in ids, (
            f"Expected hooks.json finding in {ids}"
        )
        assert "hook-health:missing-rule:tdd-levels.md" in ids, (
            f"Expected tdd-levels.md finding in {ids}"
        )

    # ------------------------------------------------------------------
    # C3.2a: missing hook scripts (manifest-declared but absent on disk)
    # ------------------------------------------------------------------

    # Scenario: a manifest-declared hook is absent from disk -> finding
    def test_manifest_declared_hook_absent_produces_missing_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "hook_manifest": {
                "hooks": [
                    {"file": "auto-test-runner.sh", "required": True},
                ],
            },
        })
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert "hook-health:missing-hook:auto-test-runner.sh" in ids, (
            f"Expected missing-hook finding for auto-test-runner.sh, got: {ids}"
        )

        f = next(
            x for x in findings
            if x.id == "hook-health:missing-hook:auto-test-runner.sh"
        )
        assert f.fix_type == "prompted"
        assert f.fix_recipe["action"] == "prompt"
        assert f.fix_recipe["type"] == "hook_restore"
        assert f.fix_recipe["hook"] == "auto-test-runner.sh"

    # Scenario: a manifest-declared hook present on disk -> no missing finding
    def test_manifest_declared_hook_present_produces_no_missing_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "hook_manifest": {
                "hooks": [
                    {"file": "auto-test-runner.sh", "required": True},
                ],
            },
            "hook_files": [
                {"name": "auto-test-runner.sh",
                 "content": "#!/bin/bash\nexit 0\n"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert "hook-health:missing-hook:auto-test-runner.sh" not in ids, (
            f"Present hook should produce no missing-hook finding, got: {ids}"
        )

    # Scenario: no manifest at all -> no missing-hook findings (no regression)
    def test_no_manifest_produces_no_missing_hook_findings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        assert state.hook_manifest is None
        findings = check_hook_health(state)

        missing_ids = [
            f.id for f in findings if f.id.startswith("hook-health:missing-hook")
        ]
        assert missing_ids == [], (
            f"No manifest should produce no missing-hook findings, got: {missing_ids}"
        )

    # Scenario: missing hook AND missing hooks.json both detected (no regression)
    def test_missing_hook_and_missing_hooks_json_both_detected(
        self, tmp_path, fake_home
    ):
        hooks_json_path = (
            fake_home / ".claude" / "hooks" / "sweetclaude" / "hooks.json"
        )
        hooks_json_path.unlink()

        project_dir = build_fixture(tmp_path, overrides={
            "hook_manifest": {
                "hooks": [
                    {"file": "auto-test-runner.sh", "required": True},
                ],
            },
        })
        state = build_project_state(project_dir)
        findings = check_hook_health(state)

        ids = [f.id for f in findings]
        assert "hook-health:missing:hooks.json" in ids, (
            f"Expected hooks.json finding in {ids}"
        )
        assert "hook-health:missing-hook:auto-test-runner.sh" in ids, (
            f"Expected missing-hook finding in {ids}"
        )


# ---------------------------------------------------------------------------
# Storage lint checks (doctor-storage-lint.feature)
# ---------------------------------------------------------------------------

def _make_cache_stub(project_dir, next_id="ISSUE-100"):
    """Create a minimal scripts/cache.py stub that returns a safe next_id."""
    cache_script = project_dir / "scripts" / "cache.py"
    cache_script.parent.mkdir(parents=True, exist_ok=True)
    cache_script.write_text(
        f'import json, sys\n'
        f'print(json.dumps({{"next_id": "{next_id}"}}))\n'
    )
    return cache_script


class TestStorageLint:
    """
    Tests for check_storage_lint(state) -> list[Finding].

    Each method corresponds to one Gherkin scenario in
    tests/features/doctor-storage-lint.feature.
    """

    # ------------------------------------------------------------------
    # Negative (healthy)
    # ------------------------------------------------------------------

    # Scenario: Healthy project produces no storage_lint findings
    def test_healthy_project_produces_no_storage_lint_findings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)
        assert findings == [], (
            f"Healthy project should produce 0 storage_lint findings, "
            f"got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # Cross-location duplicate IDs
    # ------------------------------------------------------------------

    # Scenario: Same ID in both backlog and roadmap produces error
    def test_same_id_in_backlog_and_roadmap_produces_error(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "active",
                }},
            ],
            "roadmap_files": [
                {"name": "ISSUE-001-dup.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Dup",
                }},
            ],
        })
        _make_cache_stub(project_dir)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:cross-location-duplicate-id:ISSUE-001" in ids, (
            f"Expected cross-location-duplicate-id finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "storage-lint:cross-location-duplicate-id:ISSUE-001")
        assert f.severity == "error"
        # Carries the renumber resolution: this finding supersedes
        # file-diagnostics:duplicate-id in scan dedup (F5.1.4), so leaving it
        # report-only would strand the user with no fix path.
        assert f.fix_type == "prompted"
        assert f.fix_recipe.get("type") == "renumber_duplicate"
        assert f.fix_recipe.get("duplicate_id") == "ISSUE-001"
        assert len(f.fix_recipe.get("files", [])) == 2
        assert f.fix_recipe.get("proposed_new_id")

    # Scenario: Different IDs in backlog and roadmap produce no duplicate finding
    def test_different_ids_in_backlog_and_roadmap_no_duplicate_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "active",
                }},
            ],
            "roadmap_files": [
                {"name": "ISSUE-002-other.md", "frontmatter": {
                    "id": "ISSUE-002", "type": "story", "title": "Other",
                }},
            ],
        })
        _make_cache_stub(project_dir)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        dup_ids = [f.id for f in findings if f.id.startswith("storage-lint:cross-location-duplicate-id")]
        assert dup_ids == [], (
            f"Different IDs should produce no duplicate finding, got: {dup_ids}"
        )

    # Scenario: INDEX.md files are excluded from duplicate ID scan
    def test_index_md_excluded_from_duplicate_id_scan(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "INDEX.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Index",
                }},
            ],
            "roadmap_files": [
                {"name": "ISSUE-001-dup.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Dup",
                }},
            ],
        })
        # No ISSUE-NNN-* backlog files, so no cache.py needed for counter drift
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        dup_ids = [f.id for f in findings if f.id.startswith("storage-lint:cross-location-duplicate-id")]
        assert dup_ids == [], (
            f"INDEX.md should be excluded from duplicate ID scan, got: {dup_ids}"
        )

    # Scenario: MIGRATION-MAP.md files are excluded from duplicate ID scan
    def test_migration_map_excluded_from_duplicate_id_scan(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "MIGRATION-MAP.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Migration map",
                }},
            ],
            "roadmap_files": [
                {"name": "ISSUE-001-dup.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Dup",
                }},
            ],
        })
        # No ISSUE-NNN-* backlog files, so no cache.py needed
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        dup_ids = [f.id for f in findings if f.id.startswith("storage-lint:cross-location-duplicate-id")]
        assert dup_ids == [], (
            f"MIGRATION-MAP.md should be excluded from duplicate ID scan, got: {dup_ids}"
        )

    # Scenario: File with malformed frontmatter excluded from duplicate ID scan
    def test_malformed_frontmatter_excluded_from_duplicate_id_scan(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-broken.md", "content": "no frontmatter here"},
            ],
            "roadmap_files": [
                {"name": "ISSUE-001-dup.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Dup",
                }},
            ],
        })
        # ISSUE-001-broken.md matches ISSUE-(\d+)- so cache.py is required
        _make_cache_stub(project_dir)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        dup_ids = [f.id for f in findings if f.id.startswith("storage-lint:cross-location-duplicate-id")]
        assert dup_ids == [], (
            f"Malformed frontmatter should be excluded from duplicate scan, got: {dup_ids}"
        )

    # ------------------------------------------------------------------
    # Counter drift
    # ------------------------------------------------------------------

    # Scenario: Counter drift raises DependencyMissing when cache.py absent
    def test_counter_drift_skipped_silently_when_cache_absent(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-005-test.md", "frontmatter": {
                    "id": "ISSUE-005", "type": "story", "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)
        assert not any(f.id.startswith("storage-lint:counter-drift") for f in findings)

    # Scenario: No backlog issue files with cache.py absent does not raise
    def test_no_backlog_issue_files_with_cache_absent_does_not_raise(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        # No backlog ISSUE-* files, no cache.py
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)
        assert findings == [], (
            f"No ISSUE files and no cache.py should produce 0 findings, "
            f"got: {[f.id for f in findings]}"
        )

    # Scenario: Counter drift detected when file max exceeds cache max
    def test_counter_drift_detected_when_file_max_exceeds_cache_max(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-010-test.md", "frontmatter": {
                    "id": "ISSUE-010", "type": "story", "title": "Test", "status": "active",
                }},
            ],
        })
        cache_script = project_dir / "scripts" / "cache.py"
        cache_script.parent.mkdir(parents=True, exist_ok=True)
        cache_script.write_text(
            'import json, sys\n'
            'print(json.dumps({"next_id": "ISSUE-005"}))\n'
        )

        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:counter-drift:issue" in ids, (
            f"Expected counter-drift finding when file max > cache max, got: {ids}"
        )

        f = next(x for x in findings if x.id == "storage-lint:counter-drift:issue")
        assert f.severity == "warning"
        assert f.fix_type == "auto"
        assert f.fix_recipe["action"] == "rebuild_cache"

    # Scenario: No drift when cache max matches or exceeds file max
    def test_no_drift_when_cache_max_exceeds_file_max(self, tmp_path, fake_home, patch_scripts_dir):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-003-test.md", "frontmatter": {
                    "id": "ISSUE-003", "type": "story", "title": "Test", "status": "active",
                }},
            ],
        })
        cache_script = project_dir / "scripts" / "cache.py"
        cache_script.parent.mkdir(parents=True, exist_ok=True)
        cache_script.write_text(
            'import json, sys\n'
            'print(json.dumps({"next_id": "ISSUE-010"}))\n'
        )

        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:counter-drift:issue" not in ids, (
            f"Cache max >= file max should produce no drift finding, got: {ids}"
        )

    # Scenario: Counter drift exact boundary — file max equals cache max
    def test_counter_drift_exact_boundary_no_finding(self, tmp_path, fake_home, patch_scripts_dir):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-005-test.md", "frontmatter": {
                    "id": "ISSUE-005", "type": "story", "title": "Test", "status": "active",
                }},
            ],
        })
        cache_script = project_dir / "scripts" / "cache.py"
        cache_script.parent.mkdir(parents=True, exist_ok=True)
        # next_id "ISSUE-006" means cache_max = 6-1 = 5 == file_max of 5: no drift
        cache_script.write_text(
            'import json, sys\n'
            'print(json.dumps({"next_id": "ISSUE-006"}))\n'
        )

        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:counter-drift:issue" not in ids, (
            f"Exact boundary (file max == cache max) should produce no drift finding, got: {ids}"
        )

    # Scenario: Subprocess exception during counter drift silently suppresses drift
    def test_subprocess_exception_silently_suppresses_drift(self, tmp_path, fake_home, patch_scripts_dir):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-010-test.md", "frontmatter": {
                    "id": "ISSUE-010", "type": "story", "title": "Test", "status": "active",
                }},
            ],
        })
        cache_script = project_dir / "scripts" / "cache.py"
        cache_script.parent.mkdir(parents=True, exist_ok=True)
        cache_script.write_text('raise RuntimeError("broken")\n')

        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:counter-drift:issue" not in ids, (
            f"Subprocess exception should silently suppress drift finding, got: {ids}"
        )

    # ------------------------------------------------------------------
    # V3 file remnants
    # ------------------------------------------------------------------

    # Scenario: BL-prefixed files on v4 produce warning
    def test_bl_prefixed_files_on_v4_produce_warning(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "BL-001-old.md", "content": "# Old item"},
            ],
            "sweetclaude_yaml": {
                "phase_schema_version": 2,
                "framework": {"installed_version": "4.0.8-beta"},
            },
        })
        # BL-001-old.md does not match ISSUE-(\d+)- so no cache.py needed
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:v3-files-present:backlog" in ids, (
            f"Expected v3-files-present finding for BL-prefix files on v4, got: {ids}"
        )

        f = next(x for x in findings if x.id == "storage-lint:v3-files-present:backlog")
        assert f.severity == "warning"
        assert f.fix_type == "prompted"

    # Scenario: BL-prefixed files on v3 do not produce warning
    def test_bl_prefixed_files_on_v3_no_warning(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "BL-001-old.md", "content": "# Old item"},
            ],
            "sweetclaude_yaml": {
                "phase_schema_version": 2,
                "framework": {"installed_version": "3.2.1"},
            },
        })
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:v3-files-present:backlog" not in ids, (
            f"BL-prefix files on v3 should not produce v3-files-present finding, got: {ids}"
        )

    # Scenario: sweetclaude.yaml absent with BL-files does not flag v3 remnants
    def test_sweetclaude_yaml_absent_with_bl_files_no_v3_flag(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "BL-001-old.md", "content": "# Old item"},
            ],
            "sweetclaude_yaml": None,
        })
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:v3-files-present:backlog" not in ids, (
            f"Absent sweetclaude.yaml should not flag v3 remnants, got: {ids}"
        )

    # Scenario: BL-file in subdirectory not detected by non-recursive glob
    def test_bl_file_in_subdirectory_not_detected(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "done/BL-001-old.md", "content": "# Old item"},
            ],
            "sweetclaude_yaml": {
                "phase_schema_version": 2,
                "framework": {"installed_version": "4.0.8-beta"},
            },
        })
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:v3-files-present:backlog" not in ids, (
            f"BL-file in subdirectory should not be detected by non-recursive glob, got: {ids}"
        )

    # ------------------------------------------------------------------
    # Done/status mismatch: backlog done/ directory
    # ------------------------------------------------------------------

    # Scenario: File in done/ without done status produces mismatch warning
    def test_file_in_done_without_done_status_produces_mismatch_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "done/ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "active",
                }},
            ],
        })
        # done/ISSUE-001-test.md is found by rglob so cache.py is needed
        _make_cache_stub(project_dir)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:done-status-mismatch:ISSUE-001-test.md" in ids, (
            f"Expected done-status-mismatch finding for active file in done/, got: {ids}"
        )

        f = next(x for x in findings if x.id == "storage-lint:done-status-mismatch:ISSUE-001-test.md")
        assert f.severity == "warning"
        assert f.fix_type == "prompted"

    # Scenario: File in done/ with status "done" produces no mismatch
    def test_file_in_done_with_done_status_no_mismatch(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "done/ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "done",
                }},
            ],
        })
        _make_cache_stub(project_dir)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:done-status-mismatch:ISSUE-001-test.md" not in ids, (
            f"File in done/ with status 'done' should not produce mismatch, got: {ids}"
        )

    # Scenario: File in done/ with status "abandoned" produces no mismatch
    def test_file_in_done_with_abandoned_status_no_mismatch(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "done/ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "abandoned",
                }},
            ],
        })
        _make_cache_stub(project_dir)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:done-status-mismatch:ISSUE-001-test.md" not in ids, (
            f"File in done/ with status 'abandoned' should not produce mismatch, got: {ids}"
        )

    # ------------------------------------------------------------------
    # Done/status mismatch: backlog root (reverse)
    # ------------------------------------------------------------------

    # Scenario: File in backlog root with done status produces mismatch warning
    def test_file_in_backlog_root_with_done_status_produces_mismatch_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "done",
                }},
            ],
        })
        _make_cache_stub(project_dir)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:done-status-mismatch:ISSUE-001-test.md" in ids, (
            f"Expected done-status-mismatch for root file with done status, got: {ids}"
        )

        f = next(x for x in findings if x.id == "storage-lint:done-status-mismatch:ISSUE-001-test.md")
        assert f.fix_recipe["action"] == "prompt"
        assert f.fix_recipe["type"] == "file_move"

    # Scenario: File in backlog root with active status produces no mismatch
    def test_file_in_backlog_root_with_active_status_no_mismatch(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "active",
                }},
            ],
        })
        _make_cache_stub(project_dir)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:done-status-mismatch:ISSUE-001-test.md" not in ids, (
            f"Root file with active status should produce no mismatch, got: {ids}"
        )

    # Scenario: File in backlog root with abandoned status produces mismatch warning
    def test_file_in_backlog_root_with_abandoned_status_produces_mismatch_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "abandoned",
                }},
            ],
        })
        _make_cache_stub(project_dir)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:done-status-mismatch:ISSUE-001-test.md" in ids, (
            f"Root file with abandoned status should produce mismatch finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "storage-lint:done-status-mismatch:ISSUE-001-test.md")
        assert f.fix_recipe["type"] == "file_move"

    # Scenario: File in archived/ directory with done status not flagged
    def test_file_in_archived_directory_with_done_status_not_flagged(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "archived/ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "done",
                }},
            ],
        })
        # archived/ISSUE-001-test.md is found by rglob so cache.py is needed
        _make_cache_stub(project_dir)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:done-status-mismatch:ISSUE-001-test.md" not in ids, (
            f"File in archived/ with done status should not be flagged, got: {ids}"
        )

    # ------------------------------------------------------------------
    # Done/status mismatch: roadmap issues
    # ------------------------------------------------------------------

    # Scenario: Roadmap issue with done status outside done/ produces mismatch
    def test_roadmap_issue_done_status_outside_done_produces_mismatch(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        issues_dir = project_dir / ".sweetclaude" / "product" / "roadmap" / "issues"
        issues_dir.mkdir(parents=True, exist_ok=True)
        _write_frontmatter_file(
            issues_dir / "ISSUE-001-test.md",
            {"id": "ISSUE-001", "type": "story", "title": "Test", "status": "done"},
        )

        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:done-status-mismatch:ISSUE-001-test.md" in ids, (
            f"Roadmap issue with done status outside done/ should produce mismatch, got: {ids}"
        )

    # Scenario: Roadmap issue in done/ directory is not flagged
    def test_roadmap_issue_in_done_directory_not_flagged(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        done_dir = project_dir / ".sweetclaude" / "product" / "roadmap" / "issues" / "done"
        done_dir.mkdir(parents=True, exist_ok=True)
        _write_frontmatter_file(
            done_dir / "ISSUE-001-test.md",
            {"id": "ISSUE-001", "type": "story", "title": "Test", "status": "done"},
        )

        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:done-status-mismatch:ISSUE-001-test.md" not in ids, (
            f"Roadmap issue in done/ should not be flagged, got: {ids}"
        )

    # Scenario: Roadmap issue with abandoned status outside done/ produces mismatch
    def test_roadmap_issue_abandoned_status_outside_done_produces_mismatch(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        issues_dir = project_dir / ".sweetclaude" / "product" / "roadmap" / "issues"
        issues_dir.mkdir(parents=True, exist_ok=True)
        _write_frontmatter_file(
            issues_dir / "ISSUE-001-test.md",
            {"id": "ISSUE-001", "type": "story", "title": "Test", "status": "abandoned"},
        )

        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:done-status-mismatch:ISSUE-001-test.md" in ids, (
            f"Roadmap issue with abandoned status outside done/ should produce mismatch, got: {ids}"
        )

    # ------------------------------------------------------------------
    # Epic missing completion criteria
    # ------------------------------------------------------------------

    # Scenario: Active epic without completion_criteria produces info finding
    def test_active_epic_without_completion_criteria_produces_info_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        epics_dir = project_dir / ".sweetclaude" / "product" / "roadmap" / "epics"
        epics_dir.mkdir(parents=True, exist_ok=True)
        _write_frontmatter_file(
            epics_dir / "EP-001-test.md",
            {"id": "EP-001", "type": "epic", "title": "Test", "status": "active"},
        )

        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert "storage-lint:epic-missing-criteria:EP-001" in ids, (
            f"Expected epic-missing-criteria finding for active epic without criteria, got: {ids}"
        )

        f = next(x for x in findings if x.id == "storage-lint:epic-missing-criteria:EP-001")
        assert f.severity == "info"
        assert f.fix_type == "report-only"

    # Scenario: Done epic without completion_criteria is not flagged
    def test_done_epic_without_completion_criteria_not_flagged(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        epics_dir = project_dir / ".sweetclaude" / "product" / "roadmap" / "epics"
        epics_dir.mkdir(parents=True, exist_ok=True)
        _write_frontmatter_file(
            epics_dir / "EP-001-test.md",
            {"id": "EP-001", "type": "epic", "title": "Test", "status": "done"},
        )

        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        epic_ids = [f.id for f in findings if f.id.startswith("storage-lint:epic-missing-criteria")]
        assert epic_ids == [], (
            f"Done epic without criteria should not be flagged, got: {epic_ids}"
        )

    # Scenario: Active epic with completion_criteria produces no finding
    def test_active_epic_with_completion_criteria_no_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        epics_dir = project_dir / ".sweetclaude" / "product" / "roadmap" / "epics"
        epics_dir.mkdir(parents=True, exist_ok=True)
        _write_frontmatter_file(
            epics_dir / "EP-001-test.md",
            {
                "id": "EP-001",
                "type": "epic",
                "title": "Test",
                "status": "active",
                "completion_criteria": [{"text": "criterion 1"}],
            },
        )

        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        epic_ids = [f.id for f in findings if f.id.startswith("storage-lint:epic-missing-criteria")]
        assert epic_ids == [], (
            f"Active epic with completion_criteria should produce no finding, got: {epic_ids}"
        )

    # ------------------------------------------------------------------
    # Interaction: multiple check blocks fire together
    # ------------------------------------------------------------------

    # Scenario: Duplicate ID and v3 file findings accumulate
    def test_duplicate_id_and_v3_file_findings_accumulate(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "active",
                }},
                {"name": "BL-001-old.md", "content": "# Old item"},
            ],
            "roadmap_files": [
                {"name": "ISSUE-001-dup.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Dup",
                }},
            ],
            "sweetclaude_yaml": {
                "phase_schema_version": 2,
                "framework": {"installed_version": "4.0.8-beta"},
            },
        })
        _make_cache_stub(project_dir)
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)

        ids = [f.id for f in findings]
        assert len(findings) >= 2, (
            f"Expected at least 2 findings for combined conditions, got: {ids}"
        )
        assert "storage-lint:cross-location-duplicate-id:ISSUE-001" in ids, (
            f"Expected cross-location-duplicate-id finding, got: {ids}"
        )
        assert "storage-lint:v3-files-present:backlog" in ids, (
            f"Expected v3-files-present finding, got: {ids}"
        )


# ---------------------------------------------------------------------------
# Migration currency checks (doctor-migration-currency.feature)
# ---------------------------------------------------------------------------

class TestMigrationCurrency:
    """
    Tests for check_migration_currency(state) -> list[Finding].

    Each method corresponds to one Gherkin scenario in
    tests/features/doctor-migration-currency.feature.
    """

    # ------------------------------------------------------------------
    # Negative (healthy)
    # ------------------------------------------------------------------

    # Scenario: Healthy project produces no migration_currency findings
    #
    # patch_scripts_dir redirects doctor._SCRIPTS_DIR to project/scripts so the
    # build_fixture default runner stub (DRIFT_COUNT=0 on --report-drift-for-skill)
    # drives the check, rather than the real repo runner.
    def test_healthy_project_produces_no_migration_currency_findings(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)
        assert findings == [], (
            f"Healthy project should produce 0 migration_currency findings, "
            f"got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # Stale drift marker
    # ------------------------------------------------------------------

    # Scenario: pending-drift-decision.yaml exists produces info finding
    def test_pending_drift_decision_yaml_exists_produces_info_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        drift_marker = project_dir / ".sweetclaude" / "state" / "pending-drift-decision.yaml"
        drift_marker.write_text("drift: true\n")

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        ids = [f.id for f in findings]
        assert "migration-currency:stale-drift-marker:pending-drift-decision.yaml" in ids, (
            f"Expected stale-drift-marker finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "migration-currency:stale-drift-marker:pending-drift-decision.yaml")
        assert f.severity == "info"
        assert f.fix_type == "auto"
        assert f.fix_recipe["action"] == "delete_file"

    # Scenario: No drift marker produces no stale-drift finding
    def test_no_drift_marker_produces_no_stale_drift_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        stale_ids = [f.id for f in findings if f.id.startswith("migration-currency:stale-drift-marker")]
        assert stale_ids == [], (
            f"No drift marker should produce no stale-drift finding, got: {stale_ids}"
        )

    # ------------------------------------------------------------------
    # Schema drift via migration runner
    # ------------------------------------------------------------------

    # Scenario: Migration runner absent skips schema drift check
    #
    # patch_scripts_dir redirects doctor._SCRIPTS_DIR (where _find_migration_runner
    # resolves the runner) to project/scripts; removing the fixture runner there
    # makes migration_runner_path None. The documented contract for an absent
    # runner is DependencyMissing (the scan layer catches it into
    # skipped_categories), NOT a silent empty result. The old bug masked this:
    # build_fixture + the real repo _SCRIPTS_DIR always supplied a runner whose
    # prose --scan-drift output was json.loads()'d and swallowed, so this test
    # never actually exercised the absent path.
    def test_migration_runner_absent_skips_schema_drift_check(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)
        # Remove the default fixture runner so the runner is genuinely absent
        # (patch_scripts_dir points _SCRIPTS_DIR at project/scripts).
        (project_dir / "scripts" / "migrations" / "runner.py").unlink()
        state = build_project_state(project_dir)
        assert state.migration_runner_path is None
        with pytest.raises(DependencyMissing):
            check_migration_currency(state)

    # Scenario: Migration runner reports schema drift produces warning
    #
    # C3.5b: the runner's machine-parseable mode is --report-drift-for-skill,
    # which emits DRIFT_COUNT=N then FINDING|<key>|v<from>-><to>|chain=<ok|broken>.
    # --scan-drift prints human prose, NOT JSON. This REAL stub (no mocks) mirrors
    # the production contract: prose on --scan-drift, line format on
    # --report-drift-for-skill. The doctor must shell out to --report-drift-for-skill.
    def test_migration_runner_reports_schema_drift_produces_warning(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--report-drift-for-skill' in sys.argv:\n"
            "    print('DRIFT_COUNT=1')\n"
            "    print('FINDING|sweetclaude.yaml|v1->v2|chain=ok')\n"
            "    sys.exit(0)\n"
            "if '--scan-drift' in sys.argv:\n"
            "    print('Drift scan (2026-06-09): 1 finding(s)')\n"
            "    print('  [DRIFT] sweetclaude.yaml: on_disk=v1 target=v2 type=state')\n"
            "    sys.exit(0)\n"
            "sys.exit(0)\n"
        )

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_findings = [f for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert len(schema_findings) >= 1, (
            f"Expected at least 1 schema-drift finding, got: {[f.id for f in findings]}"
        )

        first = schema_findings[0]
        assert first.id == "migration-currency:schema-drift:sweetclaude.yaml"
        assert first.severity == "warning"
        assert first.fix_type == "auto"
        assert first.fix_recipe["action"] == "run_script"
        assert "runner.py" in first.fix_recipe["cmd"][1]

    # Scenario: Migration runner reports zero drift (DRIFT_COUNT=0)
    def test_migration_runner_reports_zero_drift_produces_no_finding(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--report-drift-for-skill' in sys.argv:\n"
            "    print('DRIFT_COUNT=0')\n"
            "    sys.exit(0)\n"
            "sys.exit(0)\n"
        )

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = [f.id for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert schema_ids == [], (
            f"DRIFT_COUNT=0 should produce no schema-drift findings, got: {schema_ids}"
        )

    # Scenario: Migration runner subprocess times out is silently skipped
    def test_migration_runner_timeout_is_silently_skipped(
        self, tmp_path, fake_home, monkeypatch
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text('import time; time.sleep(30)\n')

        original_run = subprocess.run

        def mock_run(cmd, **kwargs):
            if "runner.py" in str(cmd):
                raise subprocess.TimeoutExpired(cmd, 15)
            return original_run(cmd, **kwargs)

        monkeypatch.setattr("subprocess.run", mock_run)

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = [f.id for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert schema_ids == [], (
            f"Timeout should be silently skipped, got: {schema_ids}"
        )

    # Scenario: Drifted file reported via --report-drift-for-skill IS detected
    #
    # C3.5b regression lock. This test previously asserted the OPPOSITE — that a
    # runner emitting prose (`print("not json")`, exactly what the real runner
    # prints on --scan-drift) was "silently skipped" — which enshrined the bug:
    # the doctor json.loads()'d the prose --scan-drift output, swallowed the
    # JSONDecodeError, and could NEVER produce a schema-drift finding. The dead
    # path is now fixed: the doctor calls --report-drift-for-skill and parses the
    # DRIFT_COUNT / FINDING| line format, so a drifted file MUST surface a finding.
    def test_migration_runner_reported_drift_is_detected(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        # Realistic runner: human prose on --scan-drift (the BUGGY call), and the
        # machine line format on --report-drift-for-skill (the CORRECT call).
        runner_path.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--report-drift-for-skill' in sys.argv:\n"
            "    print('DRIFT_COUNT=1')\n"
            "    print('FINDING|phase.yaml|v2->v3|chain=ok')\n"
            "    sys.exit(0)\n"
            "if '--scan-drift' in sys.argv:\n"
            "    print('Drift scan (2026-06-09): 1 finding(s)')\n"
            "    print('  [DRIFT] phase.yaml: on_disk=v2 target=v3 type=state')\n"
            "    sys.exit(0)\n"
            "sys.exit(0)\n"
        )

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = [f.id for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert "migration-currency:schema-drift:phase.yaml" in schema_ids, (
            f"A drifted file reported via --report-drift-for-skill MUST produce a "
            f"schema-drift finding, got: {schema_ids}"
        )

    # Scenario: Migration runner exits non-zero is silently skipped
    def test_migration_runner_exits_nonzero_is_silently_skipped(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text('import sys; sys.exit(1)\n')

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = [f.id for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert schema_ids == [], (
            f"Non-zero exit from runner should be silently skipped, got: {schema_ids}"
        )

    # Scenario: Migration runner emits multiple drift findings -> one per file
    def test_migration_runner_reports_multiple_drift_findings(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--report-drift-for-skill' in sys.argv:\n"
            "    print('DRIFT_COUNT=2')\n"
            "    print('FINDING|sweetclaude.yaml|v1->v2|chain=ok')\n"
            "    print('FINDING|phase.yaml|v9->v3|chain=broken')\n"
            "    sys.exit(0)\n"
            "sys.exit(0)\n"
        )

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = sorted(
            f.id for f in findings if f.id.startswith("migration-currency:schema-drift")
        )
        assert schema_ids == [
            "migration-currency:schema-drift:phase.yaml",
            "migration-currency:schema-drift:sweetclaude.yaml",
        ], f"Each drifted file should produce its own finding, got: {schema_ids}"

    # Scenario: Migration runner emits unparseable line format is tolerated
    #
    # Under the line-format contract there is no JSON to decode. Malformed output
    # (no FINDING| lines, garbage text) must not crash and must produce no finding.
    def test_migration_runner_malformed_line_format_is_tolerated(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--report-drift-for-skill' in sys.argv:\n"
            "    print('unexpected garbage with no parseable lines')\n"
            "    sys.exit(0)\n"
            "sys.exit(0)\n"
        )

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = [f.id for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert schema_ids == [], (
            f"Malformed runner output should produce no schema-drift findings, got: {schema_ids}"
        )

    # Scenario: Migration runner OSError is silently skipped
    def test_migration_runner_oserror_is_silently_skipped(
        self, tmp_path, fake_home, monkeypatch
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--report-drift-for-skill' in sys.argv:\n"
            "    print('DRIFT_COUNT=0')\n"
            "    sys.exit(0)\n"
            "sys.exit(0)\n"
        )

        original_run = subprocess.run

        def mock_run(cmd, **kwargs):
            if "runner.py" in str(cmd):
                raise OSError("runner not executable")
            return original_run(cmd, **kwargs)

        monkeypatch.setattr("subprocess.run", mock_run)

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = [f.id for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert schema_ids == [], (
            f"OSError from runner should be silently skipped, got: {schema_ids}"
        )

    # Scenario: Migration runner timeout does not prevent orphan scan (S4)
    def test_migration_runner_timeout_does_not_prevent_orphan_scan(
        self, tmp_path, fake_home, monkeypatch, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)

        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text('import time; time.sleep(30)\n')

        orphan_script = project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py"
        orphan_script.parent.mkdir(parents=True, exist_ok=True)
        orphan_script.write_text(
            'import json; print(json.dumps({"findings": [{"file": "orphan.md"}]}))\n'
        )

        original_run = subprocess.run

        def mock_run(cmd, **kwargs):
            if "runner.py" in str(cmd):
                raise subprocess.TimeoutExpired(cmd, 15)
            return original_run(cmd, **kwargs)

        monkeypatch.setattr("subprocess.run", mock_run)

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = [f.id for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert schema_ids == [], (
            f"Runner timeout should produce no schema-drift findings, got: {schema_ids}"
        )

        orphan_ids = [f.id for f in findings
                      if f.id.startswith("migration-currency:orphan:")]
        assert len(orphan_ids) >= 1, (
            f"Runner timeout should not prevent orphan scan, got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # Taxonomy drift (old-prefixed files)
    # ------------------------------------------------------------------

    # Scenario: STORY-prefixed file in backlog produces taxonomy drift warning
    # T3b update (plan §8.2, LOCKED): this previously asserted the OLD blocked
    # behavior (report-only, "not currently executable") because the real
    # migrate_taxonomy.py had no CLI entrypoint. The locked decision built that
    # CLI, so the unpatched _SCRIPTS_DIR now reads a runnable script and the
    # finding is a runnable prompted migration routing to migrate_taxonomy.py.
    def test_story_prefixed_file_produces_taxonomy_drift_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [{"name": "STORY-001-old.md", "content": "# Old story"}],
        })
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        ids = [f.id for f in findings]
        assert "migration-currency:taxonomy-drift:old-prefixes" in ids, (
            f"Expected taxonomy-drift finding for STORY-prefix, got: {ids}"
        )

        f = next(x for x in findings if x.id == "migration-currency:taxonomy-drift:old-prefixes")
        assert f.severity == "warning"
        assert f.fix_type == "prompted"
        assert f.fix_recipe["script"] == "migrate_taxonomy.py"

    def test_story_prefixed_file_with_runnable_taxonomy_cli_is_prompted(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        migrate_dir = patch_scripts_dir / "migrate"
        migrate_dir.mkdir(parents=True, exist_ok=True)
        (migrate_dir / "migrate_taxonomy.py").write_text(
            "if __name__ == '__main__':\n    pass\n"
        )
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [{"name": "STORY-001-old.md", "content": "# Old story"}],
        })
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        f = next(x for x in findings if x.id == "migration-currency:taxonomy-drift:old-prefixes")
        assert f.fix_type == "prompted"
        assert f.fix_recipe["script"] == "migrate_taxonomy.py"

    def test_unrunnable_taxonomy_migration_is_not_recommended(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        migrate_dir = patch_scripts_dir / "migrate"
        migrate_dir.mkdir(parents=True, exist_ok=True)
        (migrate_dir / "migrate_taxonomy.py").write_text("# library only\n")
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [{"name": "STORY-001-old.md", "content": "# Old story"}],
        })
        state = build_project_state(project_dir)
        result = _scan(state, categories=["migration_currency"])

        assert result["migration_recommendations"] == []

    # Scenario: BUG-prefixed file in backlog produces taxonomy drift warning
    def test_bug_prefixed_file_produces_taxonomy_drift_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [{"name": "BUG-001-old.md", "content": "# Old bug"}],
        })
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        ids = [f.id for f in findings]
        assert "migration-currency:taxonomy-drift:old-prefixes" in ids, (
            f"Expected taxonomy-drift finding for BUG-prefix, got: {ids}"
        )

    # Scenario: DEBT-prefixed file in backlog produces taxonomy drift warning
    def test_debt_prefixed_file_produces_taxonomy_drift_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [{"name": "DEBT-001-old.md", "content": "# Old debt"}],
        })
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        ids = [f.id for f in findings]
        assert "migration-currency:taxonomy-drift:old-prefixes" in ids, (
            f"Expected taxonomy-drift finding for DEBT-prefix, got: {ids}"
        )

    # Scenario: CHORE-prefixed file in backlog produces taxonomy drift warning
    def test_chore_prefixed_file_produces_taxonomy_drift_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [{"name": "CHORE-001-old.md", "content": "# Old chore"}],
        })
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        ids = [f.id for f in findings]
        assert "migration-currency:taxonomy-drift:old-prefixes" in ids, (
            f"Expected taxonomy-drift finding for CHORE-prefix, got: {ids}"
        )

    # Scenario: ISSUE-prefixed file does not produce taxonomy drift
    def test_issue_prefixed_file_does_not_produce_taxonomy_drift(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {
                    "name": "ISSUE-001-test.md",
                    "frontmatter": {"id": "ISSUE-001"},
                }
            ],
        })
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        taxonomy_ids = [f.id for f in findings if f.id.startswith("migration-currency:taxonomy-drift")]
        assert taxonomy_ids == [], (
            f"ISSUE-prefix should not produce taxonomy-drift finding, got: {taxonomy_ids}"
        )

    # Scenario: Mid-filename prefix does not match taxonomy drift
    def test_mid_filename_prefix_does_not_match_taxonomy_drift(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [{"name": "old-STORY-001.md", "content": "# Not a match"}],
        })
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        taxonomy_ids = [f.id for f in findings if f.id.startswith("migration-currency:taxonomy-drift")]
        assert taxonomy_ids == [], (
            f"Mid-filename prefix should not produce taxonomy-drift finding, got: {taxonomy_ids}"
        )

    # Scenario: Backlog directory absent produces no taxonomy drift finding
    def test_backlog_directory_absent_produces_no_taxonomy_drift_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        backlog_dir = project_dir / ".sweetclaude" / "product" / "backlog"
        shutil.rmtree(backlog_dir)

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        taxonomy_ids = [f.id for f in findings if f.id.startswith("migration-currency:taxonomy-drift")]
        assert taxonomy_ids == [], (
            f"Absent backlog directory should produce no taxonomy-drift finding, got: {taxonomy_ids}"
        )

    # Scenario: Old-prefixed file in backlog subdirectory detected by rglob
    def test_old_prefixed_file_in_subdirectory_detected_by_rglob(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [{"name": "stories/STORY-001-old.md", "content": "# Old story in subdir"}],
        })
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        ids = [f.id for f in findings]
        assert "migration-currency:taxonomy-drift:old-prefixes" in ids, (
            f"Old-prefix in subdirectory should be detected by rglob, got: {ids}"
        )

    # Scenario: Multiple old-prefixed files produce single taxonomy drift finding
    def test_multiple_old_prefixed_files_produce_single_taxonomy_drift_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "STORY-001-old.md", "content": "# Old story"},
                {"name": "BUG-002-old.md", "content": "# Old bug"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        matching = [f for f in findings if f.id == "migration-currency:taxonomy-drift:old-prefixes"]
        assert len(matching) == 1, (
            f"Multiple old-prefix files should produce exactly 1 taxonomy-drift finding, "
            f"got: {len(matching)}"
        )

    # ------------------------------------------------------------------
    # Orphan scan
    # ------------------------------------------------------------------

    # Scenario: Orphan scan script absent skips orphan check
    def test_orphan_scan_script_absent_skips_orphan_check(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        # Explicitly do NOT create scripts/migrate/migrate-v3-to-v4.py
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        orphan_ids = [f.id for f in findings if f.id.startswith("migration-currency:orphan")]
        assert orphan_ids == [], (
            f"Absent orphan script should skip orphan check, got: {orphan_ids}"
        )

    # Scenario: Orphan scan finds orphans produces warning
    def test_orphan_scan_finds_orphans_produces_warning(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)
        orphan_script = project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py"
        orphan_script.parent.mkdir(parents=True, exist_ok=True)
        orphan_script.write_text(
            'import json; print(json.dumps({"findings": [{"file": "orphan.md"}]}))\n'
        )

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        ids = [f.id for f in findings]
        assert "migration-currency:orphan:orphan.md" in ids, (
            f"Expected one per-file orphan finding, got: {ids}"
        )
        assert "migration-currency:orphans:scan" not in ids, (
            f"Aggregate orphan finding is retired (ISSUE-235) — per-file "
            f"resolve_orphans findings replace it, got: {ids}"
        )

        f = next(x for x in findings
                 if x.id == "migration-currency:orphan:orphan.md")
        assert f.severity == "warning"
        assert f.fix_type == "prompted"
        assert f.fix_recipe.get("type") == "resolve_orphans"
        assert f.fix_recipe.get("file") == "orphan.md"

    # Scenario: Orphan scan finds no orphans produces no finding
    def test_orphan_scan_finds_no_orphans_produces_no_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        orphan_script = project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py"
        orphan_script.parent.mkdir(parents=True, exist_ok=True)
        orphan_script.write_text(
            'import json; print(json.dumps({"findings": []}))\n'
        )

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        ids = [f.id for f in findings
               if f.id.startswith("migration-currency:orphan")]
        assert ids == [], (
            f"Empty orphans list should produce no finding, got: {ids}"
        )

    # Scenario: Orphan scan subprocess timeout is silently skipped
    def test_orphan_scan_timeout_is_silently_skipped(
        self, tmp_path, fake_home, monkeypatch
    ):
        project_dir = build_fixture(tmp_path)
        orphan_script = project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py"
        orphan_script.parent.mkdir(parents=True, exist_ok=True)
        orphan_script.write_text('import time; time.sleep(30)\n')

        original_run = subprocess.run

        def mock_run(cmd, **kwargs):
            if "migrate-v3-to-v4.py" in str(cmd):
                raise subprocess.TimeoutExpired(cmd, 15)
            return original_run(cmd, **kwargs)

        monkeypatch.setattr("subprocess.run", mock_run)

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        orphan_ids = [f.id for f in findings if f.id.startswith("migration-currency:orphan")]
        assert orphan_ids == [], (
            f"Orphan scan timeout should be silently skipped, got: {orphan_ids}"
        )

    # Scenario: Orphan scan returns invalid JSON is silently skipped
    def test_orphan_scan_invalid_json_is_silently_skipped(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        orphan_script = project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py"
        orphan_script.parent.mkdir(parents=True, exist_ok=True)
        orphan_script.write_text('print("not json")\n')

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        orphan_ids = [f.id for f in findings if f.id.startswith("migration-currency:orphan")]
        assert orphan_ids == [], (
            f"Invalid JSON from orphan script should be silently skipped, got: {orphan_ids}"
        )

    # Scenario: Orphan scan exits non-zero is silently skipped
    def test_orphan_scan_exits_nonzero_is_silently_skipped(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        orphan_script = project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py"
        orphan_script.parent.mkdir(parents=True, exist_ok=True)
        orphan_script.write_text('import sys; sys.exit(1)\n')

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        orphan_ids = [f.id for f in findings if f.id.startswith("migration-currency:orphan")]
        assert orphan_ids == [], (
            f"Non-zero orphan exit should be silently skipped, got: {orphan_ids}"
        )

    # ------------------------------------------------------------------
    # Interaction: multiple check blocks fire together
    # ------------------------------------------------------------------

    # Scenario: Drift marker and taxonomy drift findings accumulate
    def test_drift_marker_and_taxonomy_drift_findings_accumulate(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [{"name": "STORY-001-old.md", "content": "# Old story"}],
        })
        drift_marker = project_dir / ".sweetclaude" / "state" / "pending-drift-decision.yaml"
        drift_marker.write_text("drift: true\n")

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        assert len(findings) >= 2, (
            f"Expected at least 2 findings with both conditions, "
            f"got: {[f.id for f in findings]}"
        )

        ids = [f.id for f in findings]
        assert "migration-currency:stale-drift-marker:pending-drift-decision.yaml" in ids, (
            f"Expected stale-drift-marker finding in {ids}"
        )
        assert "migration-currency:taxonomy-drift:old-prefixes" in ids, (
            f"Expected taxonomy-drift finding in {ids}"
        )


# ---------------------------------------------------------------------------
# Config compat checks (doctor-config-compat.feature)
# ---------------------------------------------------------------------------

class TestConfigCompat:
    """
    Tests for check_config_compat(state) -> list[Finding].

    Each method corresponds to one Gherkin scenario in
    tests/features/doctor-config-compat.feature.
    """

    # ------------------------------------------------------------------
    # Negative (healthy)
    # ------------------------------------------------------------------

    # Scenario: Healthy project produces no config_compat findings
    def test_healthy_project_produces_no_config_compat_findings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)
        assert findings == [], (
            f"Healthy project should produce 0 config_compat findings, "
            f"got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # F1: allowedTools missing required tools
    # ------------------------------------------------------------------

    # Scenario: Global settings missing Agent from allowedTools produces error
    def test_global_settings_missing_agent_from_allowed_tools_produces_error(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "allowedTools": ["Read", "Edit", "Bash", "Write"],
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        ids = [f.id for f in findings]
        assert "config-compat:F1:~/.claude/settings.json:Agent" in ids, (
            f"Expected F1 finding for missing Agent in global settings, got: {ids}"
        )
        f = next(x for x in findings if x.id == "config-compat:F1:~/.claude/settings.json:Agent")
        assert f.severity == "error"
        assert f.fix_type == "prompted"

    # Scenario: Global settings missing Bash from allowedTools produces error
    def test_global_settings_missing_bash_from_allowed_tools_produces_error(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "allowedTools": ["Read", "Edit", "Agent", "Write"],
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        ids = [f.id for f in findings]
        assert "config-compat:F1:~/.claude/settings.json:Bash" in ids, (
            f"Expected F1 finding for missing Bash in global settings, got: {ids}"
        )

    # Scenario: Global settings missing Write from allowedTools produces error
    def test_global_settings_missing_write_from_allowed_tools_produces_error(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "allowedTools": ["Read", "Edit", "Agent", "Bash"],
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        ids = [f.id for f in findings]
        assert "config-compat:F1:~/.claude/settings.json:Write" in ids, (
            f"Expected F1 finding for missing Write in global settings, got: {ids}"
        )

    # Scenario: Local settings missing required tool produces error
    def test_local_settings_missing_agent_from_allowed_tools_produces_error(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "settings_local": {
                "allowedTools": ["Read", "Edit", "Bash", "Write"],
            },
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        ids = [f.id for f in findings]
        assert "config-compat:F1:.claude/settings.local.json:Agent" in ids, (
            f"Expected F1 finding for missing Agent in local settings, got: {ids}"
        )

    # Scenario: AllowedTools containing all required tools produces no F1 finding
    def test_allowed_tools_containing_all_required_tools_produces_no_f1_finding(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "allowedTools": ["Read", "Edit", "Bash", "Write", "Agent"],
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f1_ids = [f.id for f in findings if f.id.startswith("config-compat:F1")]
        assert f1_ids == [], (
            f"All required tools present should produce no F1 finding, got: {f1_ids}"
        )

    # Scenario: No allowedTools key at all produces no F1 finding
    def test_no_allowed_tools_key_produces_no_f1_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f1_ids = [f.id for f in findings if f.id.startswith("config-compat:F1")]
        assert f1_ids == [], (
            f"No allowedTools key should produce no F1 finding, got: {f1_ids}"
        )

    # Scenario: Empty allowedTools list produces F1 for all three required tools
    def test_empty_allowed_tools_produces_f1_for_all_three_required_tools(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "allowedTools": [],
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        ids = [f.id for f in findings]
        assert "config-compat:F1:~/.claude/settings.json:Agent" in ids, (
            f"Expected F1:Agent, got: {ids}"
        )
        assert "config-compat:F1:~/.claude/settings.json:Bash" in ids, (
            f"Expected F1:Bash, got: {ids}"
        )
        assert "config-compat:F1:~/.claude/settings.json:Write" in ids, (
            f"Expected F1:Write, got: {ids}"
        )

    # ------------------------------------------------------------------
    # F2: non-SweetClaude hooks on test files
    # ------------------------------------------------------------------

    # Scenario: Non-SC hook targeting test files produces error
    def test_non_sc_hook_targeting_test_files_produces_error(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "test",
                        "hooks": [{"command": "run-linter"}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f2_findings = [f for f in findings if f.id.startswith("config-compat:F2")]
        assert len(f2_findings) >= 1, (
            f"Expected at least 1 F2 finding, got: {[f.id for f in findings]}"
        )
        assert f2_findings[0].severity == "error"

    # Scenario: Hook targeting test files with sweetclaude command is not flagged
    def test_hook_with_sweetclaude_command_not_flagged_as_f2(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "test",
                        "hooks": [{"command": "sweetclaude run-tests"}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f2_ids = [f.id for f in findings if f.id.startswith("config-compat:F2")]
        assert f2_ids == [], (
            f"Hook with 'sweetclaude' command should not be flagged as F2, got: {f2_ids}"
        )

    # Scenario: Hook targeting test files with plugin root variable is not flagged
    def test_hook_with_plugin_root_variable_not_flagged_as_f2(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "test",
                        "hooks": [{"command": "${CLAUDE_PLUGIN_ROOT}/run-tests"}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f2_ids = [f.id for f in findings if f.id.startswith("config-compat:F2")]
        assert f2_ids == [], (
            f"Hook with '${{CLAUDE_PLUGIN_ROOT}}' command should not be flagged as F2, got: {f2_ids}"
        )

    # Scenario: Hook targeting spec files produces F2 error
    def test_hook_targeting_spec_files_produces_f2_error(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "spec",
                        "hooks": [{"command": "run-linter"}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f2_findings = [f for f in findings if f.id.startswith("config-compat:F2")]
        assert len(f2_findings) >= 1, (
            f"Hook targeting 'spec' with external command should produce F2 finding, "
            f"got: {[f.id for f in findings]}"
        )

    # Scenario: Hook not targeting test/spec files is not flagged as F2
    def test_hook_not_targeting_test_spec_files_not_flagged_as_f2(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "src",
                        "hooks": [{"command": "run-linter"}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f2_ids = [f.id for f in findings if f.id.startswith("config-compat:F2")]
        assert f2_ids == [], (
            f"Hook targeting 'src' should not be flagged as F2, got: {f2_ids}"
        )

    # ------------------------------------------------------------------
    # F3: direct test runner in hooks
    # ------------------------------------------------------------------

    # Scenario: Hook command containing "pytest" produces F3 error
    def test_hook_with_pytest_command_produces_f3_error(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "anything",
                        "hooks": [{"command": "pytest tests/"}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f3_findings = [f for f in findings if f.id.startswith("config-compat:F3")]
        assert len(f3_findings) >= 1, (
            f"Hook with 'pytest' command should produce F3 finding, "
            f"got: {[f.id for f in findings]}"
        )
        assert f3_findings[0].severity == "error"

    # Scenario: Hook command containing "npm test" produces F3 error
    def test_hook_with_npm_test_command_produces_f3_error(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "anything",
                        "hooks": [{"command": "npm test"}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f3_findings = [f for f in findings if f.id.startswith("config-compat:F3")]
        assert len(f3_findings) >= 1, (
            f"Hook with 'npm test' command should produce F3 finding, "
            f"got: {[f.id for f in findings]}"
        )

    # Scenario: Hook command containing "cargo test" produces F3 error
    def test_hook_with_cargo_test_command_produces_f3_error(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "anything",
                        "hooks": [{"command": "cargo test --release"}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f3_findings = [f for f in findings if f.id.startswith("config-compat:F3")]
        assert len(f3_findings) >= 1, (
            f"Hook with 'cargo test' command should produce F3 finding, "
            f"got: {[f.id for f in findings]}"
        )

    # Scenario: Hook command containing "jest " with trailing space produces F3 error
    def test_hook_with_jest_command_produces_f3_error(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "anything",
                        "hooks": [{"command": "jest --coverage"}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f3_findings = [f for f in findings if f.id.startswith("config-compat:F3")]
        assert len(f3_findings) >= 1, (
            f"Hook with 'jest ' command should produce F3 finding, "
            f"got: {[f.id for f in findings]}"
        )

    # Scenario: Hook command containing "go test" produces F3 error
    def test_hook_with_go_test_command_produces_f3_error(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "anything",
                        "hooks": [{"command": "go test ./..."}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f3_findings = [f for f in findings if f.id.startswith("config-compat:F3")]
        assert len(f3_findings) >= 1, (
            f"Hook with 'go test' command should produce F3 finding, "
            f"got: {[f.id for f in findings]}"
        )

    # Scenario: Hook command not containing any test runner is not flagged as F3
    def test_hook_without_test_runner_not_flagged_as_f3(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "anything",
                        "hooks": [{"command": "echo done"}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f3_ids = [f.id for f in findings if f.id.startswith("config-compat:F3")]
        assert f3_ids == [], (
            f"'echo done' should not be flagged as F3, got: {f3_ids}"
        )

    # Scenario: Hook with test matcher and test runner command produces both F2 and F3
    def test_hook_with_test_matcher_and_test_runner_produces_both_f2_and_f3(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "test",
                        "hooks": [{"command": "pytest tests/"}],
                    }
                ]
            },
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f2_findings = [f for f in findings if f.id.startswith("config-compat:F2")]
        f3_findings = [f for f in findings if f.id.startswith("config-compat:F3")]
        assert len(f2_findings) >= 1, (
            f"Expected at least 1 F2 finding, got: {[f.id for f in findings]}"
        )
        assert len(f3_findings) >= 1, (
            f"Expected at least 1 F3 finding, got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # F4: skip-hooks instructions in text sources
    # ------------------------------------------------------------------

    # Scenario: CLAUDE.md containing "--no-verify" produces F4 error
    def test_claude_md_with_no_verify_produces_f4_error(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nAlways use --no-verify when committing.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f4_findings = [f for f in findings if f.id.startswith("config-compat:F4")]
        assert len(f4_findings) >= 1, (
            f"Expected at least 1 F4 finding for '--no-verify', "
            f"got: {[f.id for f in findings]}"
        )
        assert f4_findings[0].severity == "error"
        assert f4_findings[0].fix_type == "prompted"

    # Scenario: CLAUDE.md containing "skip hooks" produces F4 error
    def test_claude_md_with_skip_hooks_produces_f4_error(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nYou can skip hooks if needed.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f4_findings = [f for f in findings if f.id.startswith("config-compat:F4")]
        assert len(f4_findings) >= 1, (
            f"Expected at least 1 F4 finding for 'skip hooks', "
            f"got: {[f.id for f in findings]}"
        )

    # Scenario: SweetClaude rules files are excluded from text scanning
    def test_sweetclaude_rules_files_excluded_from_text_scanning(
        self, tmp_path, fake_home
    ):
        rules_path = fake_home / ".claude" / "rules" / "sweetclaude" / "interaction-model.md"
        rules_path.write_text("# Rules\nAlways skip hooks when possible.\n")

        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f4_ids = [f.id for f in findings if f.id.startswith("config-compat:F4")]
        assert f4_ids == [], (
            f"SweetClaude rules files should be excluded from text scanning, got: {f4_ids}"
        )

    # Scenario: Non-SweetClaude rules file containing flagged pattern produces finding
    def test_non_sweetclaude_rules_file_with_flagged_pattern_produces_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        state.rules_files["myproject/coding.md"] = "skip hooks always"
        findings = check_config_compat(state)

        f4_findings = [f for f in findings if f.id.startswith("config-compat:F4")]
        assert len(f4_findings) >= 1, (
            f"Non-SC rules file with 'skip hooks' should produce F4 finding, "
            f"got: {[f.id for f in findings]}"
        )

    # Scenario: Global CLAUDE.md containing skip-hooks pattern produces F4 error
    def test_global_claude_md_with_bypass_hooks_produces_f4_error(
        self, tmp_path, fake_home
    ):
        (fake_home / ".claude" / "CLAUDE.md").write_text(
            "bypass hooks when possible\n"
        )
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f4_findings = [f for f in findings if f.id.startswith("config-compat:F4")]
        assert len(f4_findings) >= 1, (
            f"Global CLAUDE.md with 'bypass hooks' should produce F4 finding, "
            f"got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # W1: time-estimate instructions
    # ------------------------------------------------------------------

    # Scenario: CLAUDE.md containing "estimate" produces W1 warning
    def test_claude_md_with_estimate_produces_w1_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nAlways provide an estimate for tasks.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        w1_findings = [f for f in findings if f.id.startswith("config-compat:W1")]
        assert len(w1_findings) >= 1, (
            f"Expected at least 1 W1 finding for 'estimate', "
            f"got: {[f.id for f in findings]}"
        )
        assert w1_findings[0].severity == "warning"

    # Scenario: CLAUDE.md containing "story points" produces W1 warning
    def test_claude_md_with_story_points_produces_w1_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nInclude story points in your output.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        w1_findings = [f for f in findings if f.id.startswith("config-compat:W1")]
        assert len(w1_findings) >= 1, (
            f"Expected at least 1 W1 finding for 'story points', "
            f"got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # W2: comment-everywhere instructions
    # ------------------------------------------------------------------

    # Scenario: CLAUDE.md containing "always add comments" produces W2 warning
    def test_claude_md_with_always_add_comments_produces_w2_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nAlways add comments to every function.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        w2_findings = [f for f in findings if f.id.startswith("config-compat:W2")]
        assert len(w2_findings) >= 1, (
            f"Expected at least 1 W2 finding for 'always add comments', "
            f"got: {[f.id for f in findings]}"
        )
        assert w2_findings[0].severity == "warning"

    # ------------------------------------------------------------------
    # W3: skip-tests instructions
    # ------------------------------------------------------------------

    # Scenario: CLAUDE.md containing "skip tests" produces W3 warning
    def test_claude_md_with_skip_tests_produces_w3_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nYou can skip tests if the change is small.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        w3_findings = [f for f in findings if f.id.startswith("config-compat:W3")]
        assert len(w3_findings) >= 1, (
            f"Expected at least 1 W3 finding for 'skip tests', "
            f"got: {[f.id for f in findings]}"
        )
        assert w3_findings[0].severity == "warning"

    # Scenario (ISSUE-240): prohibitions are not conflicts. "Never skip
    # tests" ENFORCES TDD; flagging it is a false positive that recurs on
    # every scan.
    def test_negated_skip_tests_is_not_flagged(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\n- Never skip tests to ship faster.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)
        w3 = [f for f in findings if f.id.startswith("config-compat:W3")]
        assert w3 == [], (
            f"prohibition must not be flagged as a skip-tests conflict: "
            f"{[f.detail for f in w3]}"
        )

    def test_do_not_variants_are_not_flagged(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": (
                "# Project\n\n"
                "- Do not skip tests.\n"
                "- You should never skip confirmation for destructive commands.\n"
                "- Avoid time estimates; never estimate durations.\n"
            ),
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)
        flagged = [f for f in findings
                   if f.id.startswith(("config-compat:W1", "config-compat:W3",
                                       "config-compat:W4"))]
        assert flagged == [], (
            f"negated phrases must not be flagged: {[f.detail for f in flagged]}"
        )

    def test_intrinsically_negative_pattern_still_flagged(
        self, tmp_path, fake_home
    ):
        # "don't write tests" IS the anti-TDD instruction — the negation is
        # part of the pattern, not a prohibition of it.
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nFor spikes you don't write tests.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)
        w3 = [f for f in findings if f.id.startswith("config-compat:W3")]
        assert len(w3) >= 1, "anti-TDD instruction must still be flagged"

    # ------------------------------------------------------------------
    # W4: skip-confirmation instructions
    # ------------------------------------------------------------------

    # Scenario: CLAUDE.md containing "proceed without asking" produces W4 warning
    def test_claude_md_with_proceed_without_asking_produces_w4_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nProceed without asking for confirmation.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        w4_findings = [f for f in findings if f.id.startswith("config-compat:W4")]
        assert len(w4_findings) >= 1, (
            f"Expected at least 1 W4 finding for 'proceed without asking', "
            f"got: {[f.id for f in findings]}"
        )
        assert w4_findings[0].severity == "warning"

    # ------------------------------------------------------------------
    # I1: duplicate phase-dwelling rule
    # ------------------------------------------------------------------

    # Scenario: CLAUDE.md containing phase-dwelling duplicate produces I1 info
    def test_claude_md_with_phase_dwelling_duplicate_produces_i1_info(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nNever ask if ready to move on.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        i1_findings = [f for f in findings if f.id.startswith("config-compat:I1")]
        assert len(i1_findings) >= 1, (
            f"Expected at least 1 I1 finding for 'never ask if ready to move', "
            f"got: {[f.id for f in findings]}"
        )
        assert i1_findings[0].severity == "info"
        assert i1_findings[0].fix_type == "report-only"

    # ------------------------------------------------------------------
    # I2: duplicate proposal-mode rule
    # ------------------------------------------------------------------

    # Scenario: CLAUDE.md containing proposal-mode duplicate produces I2 info
    def test_claude_md_with_proposal_mode_duplicate_produces_i2_info(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nPropose don't ask.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        i2_findings = [f for f in findings if f.id.startswith("config-compat:I2")]
        assert len(i2_findings) >= 1, (
            f"Expected at least 1 I2 finding for 'propose don\\'t ask', "
            f"got: {[f.id for f in findings]}"
        )
        assert i2_findings[0].severity == "info"
        assert i2_findings[0].fix_type == "report-only"

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    # Scenario: Pattern matching is case-insensitive
    def test_pattern_matching_is_case_insensitive(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nSKIP HOOKS in production.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f4_findings = [f for f in findings if f.id.startswith("config-compat:F4")]
        assert len(f4_findings) >= 1, (
            f"Pattern matching should be case-insensitive; 'SKIP HOOKS' should produce F4, "
            f"got: {[f.id for f in findings]}"
        )

    # Scenario: Info findings have empty fix_recipe
    def test_info_findings_have_empty_fix_recipe(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nPropose don't ask.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        i2_findings = [f for f in findings if f.id.startswith("config-compat:I2")]
        assert len(i2_findings) >= 1, (
            f"Expected at least 1 I2 finding, got: {[f.id for f in findings]}"
        )
        assert not i2_findings[0].fix_recipe, (
            f"I2 finding fix_recipe should be empty, got: {i2_findings[0].fix_recipe}"
        )

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    # Scenario: F1 and F4 findings from different sources accumulate
    def test_f1_and_f4_findings_from_different_sources_accumulate(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "allowedTools": ["Read", "Edit", "Bash", "Write"],
        }))
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nAlways use --no-verify when committing.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        assert len(findings) >= 2, (
            f"Expected at least 2 findings for combined F1 + F4 conditions, "
            f"got: {[f.id for f in findings]}"
        )
        f1_ids = [f.id for f in findings if f.id.startswith("config-compat:F1")]
        f4_ids = [f.id for f in findings if f.id.startswith("config-compat:F4")]
        assert len(f1_ids) >= 1, f"Expected at least 1 F1 finding, got: {[f.id for f in findings]}"
        assert len(f4_ids) >= 1, f"Expected at least 1 F4 finding, got: {[f.id for f in findings]}"


# ---------------------------------------------------------------------------
# Onboarding state checks (doctor-onboarding-state.feature)
# ---------------------------------------------------------------------------

class TestOnboardingState:
    """
    Tests for check_onboarding_state(state) -> list[Finding].

    Each method corresponds to one Gherkin scenario in
    tests/features/doctor-onboarding-state.feature.
    """

    # ------------------------------------------------------------------
    # Scenario: Healthy project produces no onboarding_state findings
    # ------------------------------------------------------------------

    def test_healthy_project_produces_no_onboarding_state_findings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_onboarding_state(state)
        assert findings == [], (
            f"Healthy project should produce 0 onboarding_state findings, "
            f"got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # Scenario: skills.yaml missing produces no finding — v4 never writes it
    # ------------------------------------------------------------------

    def test_skills_yaml_missing_produces_no_finding(self, tmp_path, fake_home):
        """This asserted the opposite until ISSUE-284.

        v4 onboarding never writes skills.yaml — the six data-owning skills
        create it the first time one of them is used, the same lazy lifecycle
        as phase.yaml, which doctor deliberately does not flag. Reporting it
        put a permanent finding on every correctly configured project, and
        noise in a diagnostic is how real findings get skimmed past.
        """
        project_dir = build_fixture(tmp_path, overrides={"skills_yaml": None})
        state = build_project_state(project_dir)

        ids = [f.id for f in check_onboarding_state(state)]

        assert "onboarding-state:missing:skills.yaml" not in ids, ids

    # ------------------------------------------------------------------
    # Scenario: skills.yaml missing when state directory absent produces
    #           no finding
    # ------------------------------------------------------------------

    def test_skills_yaml_missing_when_state_dir_absent_produces_no_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={"skills_yaml": None})
        state_dir = project_dir / ".sweetclaude" / "state"
        shutil.rmtree(state_dir)

        state = build_project_state(project_dir)
        findings = check_onboarding_state(state)

        missing_ids = [f.id for f in findings if f.id.startswith("onboarding-state:missing")]
        assert missing_ids == [], (
            f"Absent state dir should produce no missing finding, got: {missing_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: skills.yaml with schema_version 1 produces warning
    # ------------------------------------------------------------------

    def test_skills_yaml_schema_version_1_produces_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(
            tmp_path,
            overrides={"skills_yaml": {"schema_version": 1, "skills": {}}},
        )
        state = build_project_state(project_dir)
        findings = check_onboarding_state(state)

        ids = [f.id for f in findings]
        assert "onboarding-state:schema-v1:skills.yaml" in ids, (
            f"Expected 'onboarding-state:schema-v1:skills.yaml' in {ids}"
        )

        f = next(x for x in findings if x.id == "onboarding-state:schema-v1:skills.yaml")
        assert f.severity == "warning", (
            f"Expected severity 'warning', got: {f.severity}"
        )
        assert f.fix_type in ("auto", "report-only"), (
            f"Expected fix_type 'auto' or 'report-only', got: {f.fix_type}"
        )
        if f.fix_type == "auto":
            assert f.fix_recipe["action"] == "run_script"
            assert "runner.py" in f.fix_recipe["cmd"][1]

    # ------------------------------------------------------------------
    # Scenario: skills.yaml with schema_version 2 produces no finding
    # ------------------------------------------------------------------

    def test_skills_yaml_schema_version_2_produces_no_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_onboarding_state(state)

        schema_v1_ids = [
            f.id for f in findings if f.id.startswith("onboarding-state:schema-v1")
        ]
        assert schema_v1_ids == [], (
            f"skills.yaml with schema_version 2 should produce no schema-v1 finding, "
            f"got: {schema_v1_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: skills.yaml with no schema_version key produces no
    #           schema finding
    # ------------------------------------------------------------------

    def test_skills_yaml_no_schema_version_key_produces_no_schema_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(
            tmp_path,
            overrides={"skills_yaml": {"skills": {}}},
        )
        state = build_project_state(project_dir)
        findings = check_onboarding_state(state)

        schema_v1_ids = [
            f.id for f in findings if f.id.startswith("onboarding-state:schema-v1")
        ]
        assert schema_v1_ids == [], (
            f"skills.yaml with no schema_version key should produce no schema-v1 finding, "
            f"got: {schema_v1_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: an empty skills.yaml is treated as absent, not as damaged
    # ------------------------------------------------------------------

    def test_skills_yaml_empty_parsed_as_none_produces_no_finding(
        self, tmp_path, fake_home
    ):
        """An empty file parses to None and is indistinguishable from absent.
        Neither is a fault (ISSUE-284)."""
        project_dir = build_fixture(tmp_path, overrides={"skills_yaml": None})
        (project_dir / ".sweetclaude" / "state" / "skills.yaml").write_text("")

        ids = [f.id for f in check_onboarding_state(build_project_state(project_dir))]

        assert "onboarding-state:missing:skills.yaml" not in ids, ids


# ---------------------------------------------------------------------------
# Env wiring checks (doctor-env-wiring.feature)
# ---------------------------------------------------------------------------

class TestEnvWiring:
    """
    Tests for check_env_wiring(state) -> list[Finding].

    Each method corresponds to one Gherkin scenario in
    tests/features/doctor-env-wiring.feature.
    """

    # ------------------------------------------------------------------
    # Scenario: Healthy project produces no env_wiring findings
    # ------------------------------------------------------------------

    def test_healthy_project_produces_no_env_wiring_findings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_env_wiring(state)
        assert findings == [], (
            f"Healthy project should produce 0 env_wiring findings, "
            f"got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # Scenario: Plans directory missing produces info finding
    # ------------------------------------------------------------------

    def test_plans_directory_missing_produces_info_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"
        shutil.rmtree(plans_dir)

        state = build_project_state(project_dir)
        findings = check_env_wiring(state)

        ids = [f.id for f in findings]
        assert "env-wiring:missing:plans-directory" in ids, (
            f"Expected 'env-wiring:missing:plans-directory' in {ids}"
        )

        f = next(x for x in findings if x.id == "env-wiring:missing:plans-directory")
        assert f.severity == "info", (
            f"Expected severity 'info', got: {f.severity}"
        )
        assert f.fix_type == "auto", (
            f"Expected fix_type 'auto', got: {f.fix_type}"
        )
        assert f.fix_recipe["action"] == "create_dir", (
            f"Expected fix_recipe action 'create_dir', got: {f.fix_recipe.get('action')}"
        )

    # ------------------------------------------------------------------
    # Scenario: Global settings without plansDirectory produces warning
    # ------------------------------------------------------------------

    def test_global_settings_without_plans_directory_produces_warning(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({}))

        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_env_wiring(state)

        ids = [f.id for f in findings]
        assert "env-wiring:plans-directory-unset:settings_global" in ids, (
            f"Expected 'env-wiring:plans-directory-unset:settings_global' in {ids}"
        )

        f = next(
            x for x in findings
            if x.id == "env-wiring:plans-directory-unset:settings_global"
        )
        assert f.severity == "warning", (
            f"Expected severity 'warning', got: {f.severity}"
        )
        assert f.fix_type == "auto", (
            f"Expected fix_type 'auto', got: {f.fix_type}"
        )
        assert f.fix_recipe["action"] == "write_field", (
            f"Expected fix_recipe action 'write_field', got: {f.fix_recipe.get('action')}"
        )

    # ------------------------------------------------------------------
    # Scenario: Global settings with plansDirectory set produces no finding
    # ------------------------------------------------------------------

    def test_global_settings_with_plans_directory_produces_no_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_env_wiring(state)

        unset_ids = [
            f.id for f in findings
            if f.id.startswith("env-wiring:plans-directory-unset")
        ]
        assert unset_ids == [], (
            f"Global settings with plansDirectory set should produce no unset finding, "
            f"got: {unset_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Local settings without plansDirectory checked when global is absent
    # ------------------------------------------------------------------

    def test_local_settings_checked_when_global_settings_absent(
        self, tmp_path, fake_home
    ):
        (fake_home / ".claude" / "settings.json").unlink()

        project_dir = build_fixture(
            tmp_path,
            overrides={"settings_local": {"someKey": "value"}},
        )
        state = build_project_state(project_dir)
        findings = check_env_wiring(state)

        ids = [f.id for f in findings]
        assert "env-wiring:plans-directory-unset:settings_local" in ids, (
            f"Expected 'env-wiring:plans-directory-unset:settings_local' in {ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: plansDirectory check stops after first settings source with the key
    # ------------------------------------------------------------------

    def test_plans_directory_check_stops_after_first_source_with_key(
        self, tmp_path, fake_home
    ):
        # Global already has plansDirectory set (via fake_home fixture default).
        # Local settings deliberately lacks plansDirectory.
        project_dir = build_fixture(
            tmp_path,
            overrides={"settings_local": {"someKey": "value"}},
        )
        state = build_project_state(project_dir)
        findings = check_env_wiring(state)

        unset_ids = [
            f.id for f in findings
            if f.id.startswith("env-wiring:plans-directory-unset")
        ]
        assert unset_ids == [], (
            f"Check should stop after global (which has the key); "
            f"no unset finding expected, got: {unset_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: CLAUDE.md without sweetclaude mention produces warning
    # ------------------------------------------------------------------

    def test_claude_md_without_sweetclaude_mention_produces_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\nNo framework mention here.",
        })
        state = build_project_state(project_dir)
        findings = check_env_wiring(state)

        ids = [f.id for f in findings]
        assert "env-wiring:claude-md-missing-section:CLAUDE.md" in ids, (
            f"Expected 'env-wiring:claude-md-missing-section:CLAUDE.md' in {ids}"
        )

        f = next(
            x for x in findings
            if x.id == "env-wiring:claude-md-missing-section:CLAUDE.md"
        )
        assert f.severity == "warning", (
            f"Expected severity 'warning', got: {f.severity}"
        )
        assert f.fix_type == "report-only", (
            f"Expected fix_type 'report-only', got: {f.fix_type}"
        )

    # ------------------------------------------------------------------
    # Scenario: CLAUDE.md mentioning sweetclaude produces no finding
    # ------------------------------------------------------------------

    def test_claude_md_mentioning_sweetclaude_produces_no_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_env_wiring(state)

        missing_ids = [
            f.id for f in findings
            if f.id.startswith("env-wiring:claude-md-missing-section")
        ]
        assert missing_ids == [], (
            f"CLAUDE.md with sweetclaude mention should produce no missing-section finding, "
            f"got: {missing_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Case-insensitive match for sweetclaude in CLAUDE.md
    # ------------------------------------------------------------------

    def test_case_insensitive_match_for_sweetclaude_in_claude_md(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n## SweetClaude Rules\nHere.",
        })
        state = build_project_state(project_dir)
        findings = check_env_wiring(state)

        missing_ids = [
            f.id for f in findings
            if f.id.startswith("env-wiring:claude-md-missing-section")
        ]
        assert missing_ids == [], (
            f"'SweetClaude' in mixed case should match case-insensitively; "
            f"no missing-section finding expected, got: {missing_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: CLAUDE.md absent produces no missing-section finding
    # ------------------------------------------------------------------

    def test_claude_md_absent_produces_no_missing_section_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={"claude_md": None})
        state = build_project_state(project_dir)
        findings = check_env_wiring(state)

        missing_ids = [
            f.id for f in findings
            if f.id.startswith("env-wiring:claude-md-missing-section")
        ]
        assert missing_ids == [], (
            f"Absent CLAUDE.md should produce no missing-section finding, "
            f"got: {missing_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Plans directory missing and settings unset accumulate
    # ------------------------------------------------------------------

    def test_plans_directory_missing_and_settings_unset_accumulate(
        self, tmp_path, fake_home
    ):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({}))

        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"
        shutil.rmtree(plans_dir)

        state = build_project_state(project_dir)
        findings = check_env_wiring(state)

        assert len(findings) >= 2, (
            f"Expected at least 2 findings for combined conditions, "
            f"got: {[f.id for f in findings]}"
        )

        ids = [f.id for f in findings]
        assert "env-wiring:missing:plans-directory" in ids, (
            f"Expected 'env-wiring:missing:plans-directory' in {ids}"
        )
        assert "env-wiring:plans-directory-unset:settings_global" in ids, (
            f"Expected 'env-wiring:plans-directory-unset:settings_global' in {ids}"
        )


# ---------------------------------------------------------------------------
# File diagnostics checks (doctor-file-diagnostics.feature)
# ---------------------------------------------------------------------------

class TestFileDiagnostics:
    """
    Tests for check_file_diagnostics(state) -> list[Finding].

    Each method corresponds to one Gherkin scenario in
    tests/features/doctor-file-diagnostics.feature.
    """

    # ------------------------------------------------------------------
    # Scenario: Healthy project produces no file_diagnostics findings
    # ------------------------------------------------------------------

    def test_healthy_project_produces_no_file_diagnostics_findings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)
        assert findings == [], (
            f"Healthy project should produce 0 file_diagnostics findings, "
            f"got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # Scenario: File without frontmatter delimiter produces error
    # ------------------------------------------------------------------

    def test_file_without_frontmatter_delimiter_produces_error(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "content": "No frontmatter here"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:no-frontmatter:ISSUE-001-test.md" in ids, (
            f"Expected no-frontmatter finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "file-diagnostics:no-frontmatter:ISSUE-001-test.md")
        assert f.severity == "error", (
            f"Expected severity 'error', got: {f.severity}"
        )
        assert f.fix_type == "report-only", (
            f"Expected fix_type 'report-only', got: {f.fix_type}"
        )

    # ------------------------------------------------------------------
    # Scenario: File with broken YAML in frontmatter produces error
    # ------------------------------------------------------------------

    def test_file_with_broken_yaml_produces_parse_error(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "content": "---\n{{bad: yaml\n---\n# Body"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:parse-error:ISSUE-001-test.md" in ids, (
            f"Expected parse-error finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "file-diagnostics:parse-error:ISSUE-001-test.md")
        assert f.severity == "error", (
            f"Expected severity 'error', got: {f.severity}"
        )
        assert f.fix_type == "report-only", (
            f"Expected fix_type 'report-only', got: {f.fix_type}"
        )

    # ------------------------------------------------------------------
    # Scenario: Two files with the same ID produce duplicate-id error
    # ------------------------------------------------------------------

    def test_two_files_with_same_id_produce_duplicate_id_error(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-first.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "First", "status": "active",
                }},
                {"name": "ISSUE-001-second.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Second", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:duplicate-id:ISSUE-001" in ids, (
            f"Expected duplicate-id finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "file-diagnostics:duplicate-id:ISSUE-001")
        assert f.severity == "error", (
            f"Expected severity 'error', got: {f.severity}"
        )
        assert f.fix_type == "prompted", (
            f"Expected fix_type 'prompted', got: {f.fix_type}"
        )
        assert len(f.file_paths) == 2, (
            f"Expected 2 file_paths, got: {f.file_paths}"
        )

    # ------------------------------------------------------------------
    # Scenario: Duplicate IDs across backlog and roadmap produce error
    # ------------------------------------------------------------------

    def test_duplicate_ids_across_backlog_and_roadmap_produce_error(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "active",
                }},
            ],
            "roadmap_files": [
                {"name": "ISSUE-001-dup.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "milestone", "title": "Dup", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:duplicate-id:ISSUE-001" in ids, (
            f"Expected duplicate-id finding across backlog and roadmap, got: {ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Different IDs do not produce duplicate finding
    # ------------------------------------------------------------------

    def test_different_ids_do_not_produce_duplicate_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "First", "status": "active",
                }},
                {"name": "ISSUE-002-test.md", "frontmatter": {
                    "id": "ISSUE-002", "type": "story", "title": "Second", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        dup_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:duplicate-id")]
        assert dup_ids == [], (
            f"Different IDs should not produce duplicate-id finding, got: {dup_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: File with no id in frontmatter produces warning
    # ------------------------------------------------------------------

    def test_file_with_no_id_in_frontmatter_produces_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "type": "story", "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:missing-field-id:ISSUE-001-test.md" in ids, (
            f"Expected missing-field-id finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "file-diagnostics:missing-field-id:ISSUE-001-test.md")
        assert f.severity == "warning", (
            f"Expected severity 'warning', got: {f.severity}"
        )

    # ------------------------------------------------------------------
    # Scenario: File with no title in frontmatter produces warning
    # ------------------------------------------------------------------

    def test_file_with_no_title_in_frontmatter_produces_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:missing-field-title:ISSUE-001-test.md" in ids, (
            f"Expected missing-field-title finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "file-diagnostics:missing-field-title:ISSUE-001-test.md")
        assert f.severity == "warning", (
            f"Expected severity 'warning', got: {f.severity}"
        )

    # ------------------------------------------------------------------
    # Scenario: File with no type in frontmatter produces warning
    # ------------------------------------------------------------------

    def test_file_with_no_type_in_frontmatter_produces_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:missing-field-type:ISSUE-001-test.md" in ids, (
            f"Expected missing-field-type finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "file-diagnostics:missing-field-type:ISSUE-001-test.md")
        assert f.severity == "warning", (
            f"Expected severity 'warning', got: {f.severity}"
        )
        assert f.fix_type == "prompted", (
            f"Expected fix_type 'prompted', got: {f.fix_type}"
        )

    # ------------------------------------------------------------------
    # Scenario: File with no status in frontmatter produces warning
    # ------------------------------------------------------------------

    def test_file_with_no_status_in_frontmatter_produces_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:missing-field-status:ISSUE-001-test.md" in ids, (
            f"Expected missing-field-status finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "file-diagnostics:missing-field-status:ISSUE-001-test.md")
        assert f.severity == "warning", (
            f"Expected severity 'warning', got: {f.severity}"
        )
        assert f.fix_type == "prompted", (
            f"Expected fix_type 'prompted', got: {f.fix_type}"
        )

    # ------------------------------------------------------------------
    # Scenario: File with unrecognized status produces warning
    # ------------------------------------------------------------------

    def test_file_with_unrecognized_status_produces_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "invented",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:unknown-status:ISSUE-001-test.md" in ids, (
            f"Expected unknown-status finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "file-diagnostics:unknown-status:ISSUE-001-test.md")
        assert f.severity == "warning", (
            f"Expected severity 'warning', got: {f.severity}"
        )

    # ------------------------------------------------------------------
    # Scenario: File with valid status "active" produces no unknown-status finding
    # ------------------------------------------------------------------

    def test_valid_status_active_produces_no_unknown_status_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        unknown_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:unknown-status")]
        assert unknown_ids == [], (
            f"Valid status 'active' should produce no unknown-status finding, got: {unknown_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: File with valid status "done" produces no unknown-status finding
    # ------------------------------------------------------------------

    def test_valid_status_done_produces_no_unknown_status_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "done",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        unknown_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:unknown-status")]
        assert unknown_ids == [], (
            f"Valid status 'done' should produce no unknown-status finding, got: {unknown_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Status with parenthetical suffix is parsed correctly
    # ------------------------------------------------------------------

    def test_status_with_parenthetical_suffix_is_parsed_correctly(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test",
                    "status": "active(in review)",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        unknown_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:unknown-status")]
        assert unknown_ids == [], (
            f"Status 'active(in review)' should be parsed as 'active'; "
            f"no unknown-status finding expected, got: {unknown_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Status with em-dash suffix is parsed correctly
    # ------------------------------------------------------------------

    def test_status_with_em_dash_suffix_is_parsed_correctly(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test",
                    "status": "done—shipped",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        unknown_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:unknown-status")]
        assert unknown_ids == [], (
            f"Status 'done—shipped' should be parsed as 'done'; "
            f"no unknown-status finding expected, got: {unknown_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Uppercase status is normalized and accepted
    # ------------------------------------------------------------------

    def test_uppercase_status_is_normalized_and_accepted(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "Active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        unknown_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:unknown-status")]
        assert unknown_ids == [], (
            f"Status 'Active' should normalize to 'active'; "
            f"no unknown-status finding expected, got: {unknown_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: File with unrecognized type produces warning
    # ------------------------------------------------------------------

    def test_file_with_unrecognized_type_produces_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "invented-type", "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:unknown-type:ISSUE-001-test.md" in ids, (
            f"Expected unknown-type finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "file-diagnostics:unknown-type:ISSUE-001-test.md")
        assert f.severity == "warning", (
            f"Expected severity 'warning', got: {f.severity}"
        )

    # ------------------------------------------------------------------
    # Scenario: File with valid type "story" produces no unknown-type finding
    # ------------------------------------------------------------------

    def test_valid_type_story_produces_no_unknown_type_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        unknown_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:unknown-type")]
        assert unknown_ids == [], (
            f"Valid type 'story' should produce no unknown-type finding, got: {unknown_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Mixed-case type is normalized and accepted
    # ------------------------------------------------------------------

    def test_mixed_case_type_is_normalized_and_accepted(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "Story", "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        unknown_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:unknown-type")]
        assert unknown_ids == [], (
            f"Type 'Story' should normalize to 'story'; "
            f"no unknown-type finding expected, got: {unknown_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Type with parenthetical suffix is flagged as unknown
    # ------------------------------------------------------------------

    def test_type_with_parenthetical_suffix_is_flagged_as_unknown(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story(core)", "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:unknown-type:ISSUE-001-test.md" in ids, (
            f"Type 'story(core)' should not strip parenthetical; "
            f"expected unknown-type finding, got: {ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: INDEX.md is excluded from file diagnostics
    # ------------------------------------------------------------------

    def test_index_md_is_excluded_from_file_diagnostics(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "INDEX.md", "content": "No frontmatter"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        diag_ids = [f.id for f in findings if f.id.startswith("file-diagnostics")]
        assert diag_ids == [], (
            f"INDEX.md should be excluded from file diagnostics, got: {diag_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: MIGRATION-MAP.md is excluded from file diagnostics
    # ------------------------------------------------------------------

    def test_migration_map_md_is_excluded_from_file_diagnostics(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "MIGRATION-MAP.md", "content": "No frontmatter"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        diag_ids = [f.id for f in findings if f.id.startswith("file-diagnostics")]
        assert diag_ids == [], (
            f"MIGRATION-MAP.md should be excluded from file diagnostics, got: {diag_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Files ending in -INDEX.md are excluded
    # ------------------------------------------------------------------

    def test_files_ending_in_index_md_are_excluded(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "STORY-INDEX.md", "content": "No frontmatter"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        diag_ids = [f.id for f in findings if f.id.startswith("file-diagnostics")]
        assert diag_ids == [], (
            f"STORY-INDEX.md should be excluded from file diagnostics, got: {diag_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Files in archived/ directory are excluded
    # ------------------------------------------------------------------

    def test_files_in_archived_directory_are_excluded(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "archived/ISSUE-001-test.md", "content": "No frontmatter"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        diag_ids = [f.id for f in findings if f.id.startswith("file-diagnostics")]
        assert diag_ids == [], (
            f"Files in archived/ should be excluded from file diagnostics, got: {diag_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Empty frontmatter block produces missing-field warnings
    # ------------------------------------------------------------------

    def test_empty_frontmatter_block_produces_missing_field_warnings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "content": "---\n---\n# Body"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:missing-field-id:ISSUE-001-test.md" in ids, (
            f"Empty frontmatter should produce missing-field-id finding, got: {ids}"
        )

        no_fm_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:no-frontmatter")]
        assert no_fm_ids == [], (
            f"Empty frontmatter should not produce no-frontmatter finding, got: {no_fm_ids}"
        )

        parse_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:parse-error")]
        assert parse_ids == [], (
            f"Empty frontmatter should not produce parse-error finding, got: {parse_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Roadmap file with missing fields produces warnings
    # ------------------------------------------------------------------

    def test_roadmap_file_with_missing_fields_produces_warnings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "roadmap_files": [
                {"name": "MS-001-launch.md", "frontmatter": {
                    "type": "milestone", "title": "Launch", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:missing-field-id:MS-001-launch.md" in ids, (
            f"Roadmap file with missing id should produce missing-field-id finding, got: {ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Multiple field issues on same file produce multiple findings
    # ------------------------------------------------------------------

    def test_multiple_field_issues_on_same_file_produce_multiple_findings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "description": "just a description",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        assert len(findings) >= 4, (
            f"Expected at least 4 findings for file missing id, title, type, and status, "
            f"got: {[f.id for f in findings]}"
        )

        ids = [f.id for f in findings]
        assert "file-diagnostics:missing-field-id:ISSUE-001-test.md" in ids, (
            f"Expected missing-field-id finding, got: {ids}"
        )
        assert "file-diagnostics:missing-field-title:ISSUE-001-test.md" in ids, (
            f"Expected missing-field-title finding, got: {ids}"
        )
        assert "file-diagnostics:missing-field-type:ISSUE-001-test.md" in ids, (
            f"Expected missing-field-type finding, got: {ids}"
        )
        assert "file-diagnostics:missing-field-status:ISSUE-001-test.md" in ids, (
            f"Expected missing-field-status finding, got: {ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Parse error stops further field checks for that file
    # ------------------------------------------------------------------

    def test_parse_error_stops_further_field_checks_for_that_file(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "content": "---\n{{bad: yaml\n---\n# Body"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:parse-error:ISSUE-001-test.md" in ids, (
            f"Expected parse-error finding, got: {ids}"
        )

        missing_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:missing-field")]
        assert missing_ids == [], (
            f"Parse error should stop further field checks; "
            f"no missing-field findings expected, got: {missing_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: No-frontmatter error stops further field checks for that file
    # ------------------------------------------------------------------

    def test_no_frontmatter_error_stops_further_field_checks_for_that_file(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "content": "No frontmatter here"},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:no-frontmatter:ISSUE-001-test.md" in ids, (
            f"Expected no-frontmatter finding, got: {ids}"
        )

        missing_ids = [f.id for f in findings if f.id.startswith("file-diagnostics:missing-field")]
        assert missing_ids == [], (
            f"No-frontmatter error should stop further field checks; "
            f"no missing-field findings expected, got: {missing_ids}"
        )

    # ------------------------------------------------------------------
    # C3.4f: legacy item-type aliases are detected and remapped to canonical
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("alias,canonical", [
        ("bug", "bug-fix"),
        ("debt", "tech-debt"),
        ("chore", "tech-debt"),
        ("feature", "net-new-feature"),
    ])
    def test_legacy_type_alias_produces_remap_finding(
        self, tmp_path, fake_home, alias, canonical
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": alias,
                    "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        ids = [f.id for f in findings]
        assert "file-diagnostics:legacy-type-alias:ISSUE-001-test.md" in ids, (
            f"Legacy alias '{alias}' should produce a remap finding, got: {ids}"
        )

        f = next(
            x for x in findings
            if x.id == "file-diagnostics:legacy-type-alias:ISSUE-001-test.md"
        )
        assert f.severity == "warning"
        assert f.fix_type == "prompted"
        assert f.fix_recipe["action"] == "prompt"
        assert f.fix_recipe["type"] == "choose_value"
        assert f.fix_recipe["field"] == "type"
        assert f.fix_recipe["file"] == str(
            project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-001-test.md"
        )
        # The recommended/expected value is the canonical target.
        assert f.fix_recipe["recommended"] == canonical, (
            f"Alias '{alias}' should recommend '{canonical}', "
            f"got: {f.fix_recipe.get('recommended')}"
        )
        # The canonical target is genuinely a valid type, offered in options.
        assert canonical in f.fix_recipe["options"]

    # Scenario: a legacy alias does NOT also produce a generic unknown-type
    # finding (the remap finding supersedes it).
    def test_legacy_type_alias_produces_no_unknown_type_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "bug",
                    "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        unknown_ids = [
            f.id for f in findings
            if f.id.startswith("file-diagnostics:unknown-type")
        ]
        assert unknown_ids == [], (
            f"Legacy alias should not also produce unknown-type finding, "
            f"got: {unknown_ids}"
        )

    # Scenario: valid type "story" is NOT treated as a legacy alias (no finding)
    def test_valid_type_story_produces_no_legacy_alias_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story",
                    "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        alias_ids = [
            f.id for f in findings
            if f.id.startswith("file-diagnostics:legacy-type-alias")
        ]
        invalid_type_ids = [
            f.id for f in findings
            if f.id.startswith("file-diagnostics:unknown-type")
            or f.id.startswith("file-diagnostics:invalid-type")
        ]
        assert alias_ids == [], (
            f"Valid type 'story' should produce no legacy-alias finding, got: {alias_ids}"
        )
        assert invalid_type_ids == [], (
            f"Valid type 'story' should produce no invalid-type finding, got: {invalid_type_ids}"
        )

    # Scenario: valid type "release" is NOT treated as a legacy alias (no finding)
    def test_valid_type_release_produces_no_legacy_alias_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "release",
                    "title": "Test", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)

        alias_ids = [
            f.id for f in findings
            if f.id.startswith("file-diagnostics:legacy-type-alias")
        ]
        assert alias_ids == [], (
            f"Valid type 'release' should produce no legacy-alias finding, got: {alias_ids}"
        )

    # Scenario: applying the remap sets the canonical type through the executor
    # (content-backed up, reversible) by reusing write_frontmatter_field.
    def test_remap_applies_canonical_type_through_executor(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "bug",
                    "title": "Test", "status": "active",
                }},
            ],
        })
        target = (
            project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-001-test.md"
        )

        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)
        f = next(
            x for x in findings
            if x.id == "file-diagnostics:legacy-type-alias:ISSUE-001-test.md"
        )
        canonical = f.fix_recipe["recommended"]
        assert canonical == "bug-fix"

        archive = create_archive(project_dir)
        result = execute_recipe(
            project_dir,
            {
                "action": "write_frontmatter_field",
                "file": str(target),
                "key": "type",
                "value": canonical,
            },
            archive,
        )
        assert result.success is True

        fm = yaml.safe_load(target.read_text().split("---", 2)[1])
        assert fm["type"] == "bug-fix"

        # The before/ backup must exist (reversible).
        before_entries = list((archive / "before").iterdir())
        assert before_entries, "remap must write a before/ backup"


# ---------------------------------------------------------------------------
# E5-S03: Auto-fix tests — recipe types, idempotency, partial failure
# ---------------------------------------------------------------------------

def _make_finding(
    fix_type="auto",
    action="write_field",
    category="env_wiring",
    finding_id=None,
    **recipe_extras,
):
    """Build a minimal finding dict for auto_fix tests."""
    recipe: dict = {"action": action}
    recipe.update(recipe_extras)
    return {
        "id": finding_id or f"{category}:test:{action}",
        "category": category,
        "severity": "warning",
        "summary": f"Test finding for {action}",
        "detail": "",
        "file_paths": [],
        "fix_type": fix_type,
        "fix_recipe": recipe,
        "previously_suppressed": False,
    }


class TestAutoFix:
    """E5-S03: Auto-fix recipe types, filtering, idempotency, partial failure."""

    # ------------------------------------------------------------------
    # write_field recipe — updates a YAML field
    # ------------------------------------------------------------------

    def test_write_field_updates_yaml_field(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss_path.write_text("phase_schema_version: 1\n")

        finding = _make_finding(
            action="write_field",
            file=str(ss_path),
            key="phase_schema_version",
            value=2,
        )
        result = auto_fix(project_dir, [finding], archive)

        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "auto-fix"
        data = yaml.safe_load(ss_path.read_text())
        assert data["phase_schema_version"] == 2

    def test_write_field_records_before_and_after_hashes(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss_path.write_text("phase_schema_version: 1\n")

        finding = _make_finding(
            action="write_field",
            file=str(ss_path),
            key="phase_schema_version",
            value=2,
        )
        result = auto_fix(project_dir, [finding], archive)

        action = result["actions"][0]
        assert action["before_hash"].startswith("sha256:")
        assert action["after_hash"]
        assert action["before_hash"] != action["after_hash"]

    def test_write_field_precondition_skips_when_value_already_correct(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss_path.write_text("phase_schema_version: 2\n")

        finding = _make_finding(
            action="write_field",
            file=str(ss_path),
            key="phase_schema_version",
            value=2,
        )
        result = auto_fix(project_dir, [finding], archive)

        action = result["actions"][0]
        assert action["before_hash"] == action["after_hash"]

    # ------------------------------------------------------------------
    # create_dir recipe — creates a missing directory
    # ------------------------------------------------------------------

    def test_create_dir_creates_missing_directory(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"
        if plans_dir.exists():
            plans_dir.rmdir()
        archive = create_archive(project_dir)

        finding = {
            "id": "env-wiring:missing:plans-directory",
            "category": "env_wiring",
            "severity": "info",
            "summary": "Plans directory missing",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "create_dir", "path": str(plans_dir)},
            "previously_suppressed": False,
        }

        result = auto_fix(project_dir, [finding], archive)

        assert plans_dir.is_dir()
        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "auto-fix"

    def test_create_dir_precondition_skips_when_dir_exists(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        archive = create_archive(project_dir)

        finding = {
            "id": "env_wiring:test:create_dir",
            "category": "env_wiring",
            "severity": "info",
            "summary": "Plans dir missing",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "create_dir", "path": str(plans_dir)},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        action = result["actions"][0]
        assert action["before_hash"] == action["after_hash"]

    # ------------------------------------------------------------------
    # delete_file recipe — removes target file
    # ------------------------------------------------------------------

    def test_delete_file_removes_target_file(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        target = project_dir / ".sweetclaude" / "state" / "pending-drift-decision.yaml"
        target.write_text("decision: pending\n")
        archive = create_archive(project_dir)

        finding = {
            "id": "migration-currency:stale-drift-marker:pending-drift-decision.yaml",
            "category": "migration_currency",
            "severity": "info",
            "summary": "Stale drift marker",
            "detail": "",
            "file_paths": [str(target)],
            "fix_type": "auto",
            "fix_recipe": {"action": "delete_file", "file": str(target)},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        assert not target.exists()
        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "auto-fix"

    def test_delete_file_precondition_skips_when_file_absent(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        target = project_dir / ".sweetclaude" / "state" / "pending-drift-decision.yaml"
        # Do NOT create the file
        archive = create_archive(project_dir)

        finding = {
            "id": "migration-currency:stale-drift-marker:pending-drift-decision.yaml",
            "category": "migration_currency",
            "severity": "info",
            "summary": "Stale drift marker",
            "detail": "",
            "file_paths": [str(target)],
            "fix_type": "auto",
            "fix_recipe": {"action": "delete_file", "file": str(target)},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        action = result["actions"][0]
        assert action["before_hash"] == action["after_hash"]

    # ------------------------------------------------------------------
    # rebuild_cache recipe
    # ------------------------------------------------------------------

    def test_rebuild_cache_succeeds_with_stub_script(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        cache_script = project_dir / "scripts" / "cache.py"
        cache_script.parent.mkdir(parents=True, exist_ok=True)
        cache_script.write_text("import sys; sys.exit(0)\n")
        archive = create_archive(project_dir)

        finding = {
            "id": "storage-lint:counter-drift:issue",
            "category": "storage_lint",
            "severity": "warning",
            "summary": "Counter drift",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "rebuild_cache"},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "auto-fix"

    def test_rebuild_cache_records_failure_when_cache_missing(self, tmp_path, fake_home, patch_scripts_dir):
        project_dir = build_fixture(tmp_path)
        # Ensure cache.py does NOT exist
        cache_script = project_dir / "scripts" / "cache.py"
        if cache_script.exists():
            cache_script.unlink()
        archive = create_archive(project_dir)

        finding = {
            "id": "storage-lint:counter-drift:issue",
            "category": "storage_lint",
            "severity": "warning",
            "summary": "Counter drift",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "rebuild_cache"},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "auto-fix-failed"
        assert result["actions"][0]["error"]

    # ------------------------------------------------------------------
    # run_script recipe
    # ------------------------------------------------------------------

    def test_run_script_runs_allowlisted_script(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        stub = scripts_dir / "generate-session-state.sh"
        stub.write_text("#!/bin/bash\nexit 0\n")
        stub.chmod(0o755)
        archive = create_archive(project_dir)

        finding = {
            "id": "state-integrity:missing:session-state.yaml",
            "category": "state_integrity",
            "severity": "warning",
            "summary": "session-state.yaml missing",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "run_script", "cmd": ["bash", "scripts/generate-session-state.sh"]},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "auto-fix"

    def test_run_script_rejects_non_allowlisted_script(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        finding = {
            "id": "some-category:some-check:evil",
            "category": "env_wiring",
            "severity": "warning",
            "summary": "Evil script",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "run_script", "cmd": ["python3", "scripts/evil.py"]},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "auto-fix-failed"
        assert "not in allowlist" in result["actions"][0]["error"]

    # ------------------------------------------------------------------
    # P1-Tier2: rebuild_cache + run_script routed through the backup pipeline
    # (PRD absolute invariants P2/P7/T1h/S6 — every mutation backed up,
    # rollback always possible). NO MOCKS — real cache.py / real stub scripts.
    # ------------------------------------------------------------------

    def test_rebuild_cache_backs_up_and_restores_existing_cache(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        # A pre-existing cache file whose rebuild CHANGES it must be captured
        # before/, diffed, and reversed byte-identically by restore.
        from cache import db_path as _db_path

        project_dir = build_fixture(tmp_path)
        cache_path = Path(_db_path(str(project_dir)))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        original = b"PRE-EXISTING CACHE BYTES (not a real db)\n"
        cache_path.write_bytes(original)

        # a real cache.py at the patched _SCRIPTS_DIR that rewrites the cache
        # file to different bytes on --rebuild (so before != after)
        cache_script = patch_scripts_dir / "cache.py"
        cache_script.write_text(
            "#!/usr/bin/env python3\n"
            "import sys, os\n"
            "args = sys.argv\n"
            "pd = args[args.index('--project-dir') + 1]\n"
            "dbp = os.path.join(pd, '.sweetclaude', 'cache', 'roadmap.db')\n"
            "os.makedirs(os.path.dirname(dbp), exist_ok=True)\n"
            "open(dbp, 'wb').write(b'REBUILT CACHE BYTES - different\\n')\n"
            "sys.exit(0)\n"
        )
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {"action": "rebuild_cache"}, archive)
        assert result.success is True, f"rebuild_cache must succeed: {result.error}"
        assert result.before_hash != result.after_hash, (
            "a real cache rebuild must report before != after")

        # P2 — before/ image keyed to the cache path holds the original bytes
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(cache_path))
        assert before_entry.exists(), "rebuild_cache must record a before/ image"
        assert before_entry.read_bytes() == original

        # P7 — non-empty diffs/ entry
        diff_entry = (archive / "diffs"
                      / (_p0_doctor._sanitize_path(str(cache_path)) + ".diff"))
        assert diff_entry.exists() and diff_entry.stat().st_size > 0, (
            "rebuild_cache must record a non-empty diffs/ entry")

    def test_rebuild_cache_restores_cache_byte_identically_via_autofix(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        # End-to-end through auto_fix (the skill's path) + restore: the cache
        # is reverted byte-identically. S6.
        from cache import db_path as _db_path

        project_dir = build_fixture(tmp_path)
        cache_path = Path(_db_path(str(project_dir)))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        original = b"ORIGINAL CACHE v1\n"
        cache_path.write_bytes(original)

        cache_script = patch_scripts_dir / "cache.py"
        cache_script.write_text(
            "#!/usr/bin/env python3\n"
            "import sys, os\n"
            "args = sys.argv\n"
            "pd = args[args.index('--project-dir') + 1]\n"
            "dbp = os.path.join(pd, '.sweetclaude', 'cache', 'roadmap.db')\n"
            "os.makedirs(os.path.dirname(dbp), exist_ok=True)\n"
            "open(dbp, 'wb').write(b'REBUILT CACHE v2\\n')\n"
            "sys.exit(0)\n"
        )
        archive = create_archive(project_dir)

        finding = {
            "id": "storage-lint:counter-drift:issue",
            "category": "storage_lint",
            "summary": "Counter drift",
            "fix_type": "auto",
            "fix_recipe": {"action": "rebuild_cache"},
        }
        result = auto_fix(project_dir, [finding], archive)
        assert result["actions"][0]["action"] == "auto-fix"
        assert cache_path.read_bytes() != original, "rebuild must have changed the cache"

        res = _p0_doctor.restore(project_dir, archive, restore_all=True)
        assert res["restored"], "restore must report reversing the cache rebuild"
        assert cache_path.read_bytes() == original, (
            "restore must revert the cache byte-identically")

    def test_rebuild_cache_first_build_treats_before_as_create(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        # No pre-existing cache: before is b"" (a create). restore removes it.
        from cache import db_path as _db_path

        project_dir = build_fixture(tmp_path)
        cache_path = Path(_db_path(str(project_dir)))
        if cache_path.exists():
            cache_path.unlink()
        assert not cache_path.exists(), "precondition: no cache yet"

        cache_script = patch_scripts_dir / "cache.py"
        cache_script.write_text(
            "#!/usr/bin/env python3\n"
            "import sys, os\n"
            "args = sys.argv\n"
            "pd = args[args.index('--project-dir') + 1]\n"
            "dbp = os.path.join(pd, '.sweetclaude', 'cache', 'roadmap.db')\n"
            "os.makedirs(os.path.dirname(dbp), exist_ok=True)\n"
            "open(dbp, 'wb').write(b'FIRST BUILD\\n')\n"
            "sys.exit(0)\n"
        )
        archive = create_archive(project_dir)

        # drive through auto_fix so the action is recorded and restore can act
        finding = {
            "id": "storage-lint:counter-drift:issue",
            "category": "storage_lint",
            "summary": "first cache build",
            "fix_type": "auto",
            "fix_recipe": {"action": "rebuild_cache"},
        }
        result = auto_fix(project_dir, [finding], archive)
        assert result["actions"][0]["action"] == "auto-fix"
        assert cache_path.exists(), "rebuild must create the cache"

        # before-image holds b"" (a create); restore reverts the content to the
        # pre-build state (empty) — the cache's content before the first build.
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(cache_path))
        assert before_entry.exists() and before_entry.read_bytes() == b"", (
            "first build records an empty before-image (a create)")
        res = _p0_doctor.restore(project_dir, archive, restore_all=True)
        assert res["restored"], "restore must act on the create"
        assert cache_path.read_bytes() == b"", (
            "restoring a create reverts to empty content")

    def test_run_script_with_regenerates_backs_up_and_restores(
        self, tmp_path, fake_home
    ):
        # A run_script recipe declaring regenerates=[session-state.yaml] running
        # a stub that rewrites that file -> before/ image + diff recorded, and
        # restore reverts it byte-identically. P2/P7/S6 for run_script.
        project_dir = build_fixture(tmp_path)
        ss = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        original = ss.read_bytes()
        assert original, "fixture writes session-state.yaml"

        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        stub = scripts_dir / "generate-session-state.sh"
        stub.write_text(
            "#!/bin/bash\n"
            "cat > .sweetclaude/state/session-state.yaml <<'EOF'\n"
            "paths:\n  product_base: .sweetclaude/REGENERATED\n"
            "EOF\n"
        )
        stub.chmod(0o755)
        archive = create_archive(project_dir)

        recipe = {
            "action": "run_script",
            "cmd": ["bash", str(stub)],
            "args": [],
            "regenerates": [".sweetclaude/state/session-state.yaml"],
        }
        result = execute_recipe(project_dir, recipe, archive)
        assert result.success is True, f"run_script must succeed: {result.error}"
        assert ss.read_bytes() != original, "stub must have rewritten session-state"
        assert result.before_hash != result.after_hash

        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(ss))
        assert before_entry.exists() and before_entry.read_bytes() == original, (
            "run_script must back up each regenerated target")
        diff_entry = (archive / "diffs"
                      / (_p0_doctor._sanitize_path(str(ss)) + ".diff"))
        assert diff_entry.exists() and diff_entry.stat().st_size > 0

    def test_run_script_regenerates_restores_via_autofix(
        self, tmp_path, fake_home
    ):
        # End-to-end through auto_fix + restore.
        project_dir = build_fixture(tmp_path)
        ss = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        original = ss.read_bytes()

        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        stub = scripts_dir / "generate-session-state.sh"
        stub.write_text(
            "#!/bin/bash\n"
            "cat > .sweetclaude/state/session-state.yaml <<'EOF'\n"
            "paths:\n  product_base: .sweetclaude/CHANGED\n"
            "EOF\n"
        )
        stub.chmod(0o755)
        archive = create_archive(project_dir)

        finding = {
            "id": "state-integrity:missing:session-state.yaml",
            "category": "state_integrity",
            "summary": "session-state regenerated",
            "fix_type": "auto",
            "fix_recipe": {
                "action": "run_script",
                "cmd": ["bash", str(stub)],
                "args": [],
                "regenerates": [".sweetclaude/state/session-state.yaml"],
            },
        }
        result = auto_fix(project_dir, [finding], archive)
        assert result["actions"][0]["action"] == "auto-fix"
        assert ss.read_bytes() != original, "stub must have rewritten the file"

        res = _p0_doctor.restore(project_dir, archive, restore_all=True)
        assert res["restored"], "restore must reverse the regenerated file"
        assert ss.read_bytes() == original, (
            "restore must revert the regenerated file byte-identically")

    def test_run_script_without_regenerates_is_reversible_false_not_crash(
        self, tmp_path, fake_home
    ):
        # Absent/empty regenerates: fall back to current behavior, honestly
        # reporting reversible:false (no before-image) without crashing.
        project_dir = build_fixture(tmp_path)
        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        stub = scripts_dir / "generate-session-state.sh"
        stub.write_text("#!/bin/bash\nexit 0\n")
        stub.chmod(0o755)
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "run_script",
            "cmd": ["bash", str(stub)],
        }, archive)
        assert result.success is True, f"run_script must succeed: {result.error}"
        assert result.backup_path is None, (
            "no regenerates -> no backup -> reversible:false, honestly")
        assert list((archive / "before").iterdir()) == [], (
            "no regenerates means no before-image recorded")

    def test_state_integrity_run_script_recipe_declares_regenerates(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        # The emitting check (missing session-state.yaml) must populate
        # regenerates so the executor can back up what the script rewrites.
        project_dir = build_fixture(tmp_path)
        ss = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss.unlink()
        state = build_project_state(project_dir)
        findings = check_state_integrity(state)
        run_findings = [
            f for f in findings
            if (f.fix_recipe or {}).get("action") == "run_script"
        ]
        assert run_findings, "missing session-state must emit a run_script fix"
        for f in run_findings:
            regen = f.fix_recipe.get("regenerates")
            assert regen, f"{f.id}: run_script recipe must declare regenerates"
            assert any("session-state.yaml" in r for r in regen), (
                f"{f.id}: must name session-state.yaml as regenerated")

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def test_auto_fix_skips_report_only_findings(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        finding = {
            "id": "state-integrity:schema-version:sweetclaude.yaml",
            "category": "state_integrity",
            "severity": "warning",
            "summary": "Schema version outdated",
            "detail": "",
            "file_paths": [],
            "fix_type": "report-only",
            "fix_recipe": {},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        assert len(result["actions"]) == 0

    def test_auto_fix_skips_prompted_by_default(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"

        finding = {
            "id": "state-integrity:test:prompted",
            "category": "state_integrity",
            "severity": "warning",
            "summary": "Prompted fix needed",
            "detail": "",
            "file_paths": [],
            "fix_type": "prompted",
            "fix_recipe": {"action": "write_field", "file": str(ss_path), "key": "x", "value": "y"},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        assert len(result["actions"]) == 0

    def test_auto_fix_includes_prompted_when_include_prompted_true(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss_path.write_text("x: old\n")

        finding = {
            "id": "state-integrity:test:prompted",
            "category": "state_integrity",
            "severity": "warning",
            "summary": "Prompted fix needed",
            "detail": "",
            "file_paths": [],
            "fix_type": "prompted",
            "fix_recipe": {"action": "write_field", "file": str(ss_path), "key": "x", "value": "y"},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive, include_prompted=True)

        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "auto-fix"

    def test_auto_fix_skips_prompted_finding_with_prompt_recipe_even_when_include_prompted(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        finding = {
            "id": "hook-health:missing:hooks.json",
            "category": "hook_health",
            "severity": "error",
            "summary": "hooks.json missing",
            "detail": "",
            "file_paths": [],
            "fix_type": "prompted",
            "fix_recipe": {"action": "prompt", "type": "hook_restore"},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive, include_prompted=True)

        assert len(result["actions"]) == 0

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def test_running_auto_fix_twice_produces_no_op_on_second_run(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss_path.write_text("phase_schema_version: 1\n")

        finding = {
            "id": "state-integrity:schema-version:sweetclaude.yaml",
            "category": "state_integrity",
            "severity": "warning",
            "summary": "Schema version",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "write_field", "file": str(ss_path), "key": "phase_schema_version", "value": 2},
            "previously_suppressed": False,
        }
        archive1 = create_archive(project_dir)
        auto_fix(project_dir, [finding], archive1)

        archive2 = create_archive(project_dir)
        result2 = auto_fix(project_dir, [finding], archive2)

        for action in result2["actions"]:
            assert action["before_hash"] == action["after_hash"], (
                f"Second run should produce no-op, but action changed: {action}"
            )

    # ------------------------------------------------------------------
    # Partial failure
    # ------------------------------------------------------------------

    def test_one_recipe_fails_while_others_succeed(self, tmp_path, fake_home, patch_scripts_dir):
        project_dir = build_fixture(tmp_path)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss_path.write_text("phase_schema_version: 1\n")

        # Ensure cache.py does NOT exist
        cache_script = project_dir / "scripts" / "cache.py"
        if cache_script.exists():
            cache_script.unlink()

        archive = create_archive(project_dir)
        findings = [
            {
                "id": "state-integrity:schema:test",
                "category": "state_integrity",
                "severity": "warning",
                "summary": "Write field",
                "detail": "",
                "file_paths": [],
                "fix_type": "auto",
                "fix_recipe": {"action": "write_field", "file": str(ss_path), "key": "phase_schema_version", "value": 2},
                "previously_suppressed": False,
            },
            {
                "id": "storage-lint:counter-drift:issue",
                "category": "storage_lint",
                "severity": "warning",
                "summary": "Counter drift",
                "detail": "",
                "file_paths": [],
                "fix_type": "auto",
                "fix_recipe": {"action": "rebuild_cache"},
                "previously_suppressed": False,
            },
        ]
        result = auto_fix(project_dir, findings, archive)

        assert len(result["actions"]) == 2
        action_types = {a["action"] for a in result["actions"]}
        assert "auto-fix" in action_types
        assert "auto-fix-failed" in action_types

        # write_field change persists on disk
        data = yaml.safe_load(ss_path.read_text())
        assert data["phase_schema_version"] == 2

    # ------------------------------------------------------------------
    # post_fix_categories
    # ------------------------------------------------------------------

    def test_changed_categories_appear_in_post_fix_categories(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"
        if plans_dir.exists():
            plans_dir.rmdir()
        archive = create_archive(project_dir)

        finding = {
            "id": "env-wiring:missing:plans-directory",
            "category": "env_wiring",
            "severity": "info",
            "summary": "Plans directory missing",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "create_dir", "path": str(plans_dir)},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        assert "env_wiring" in result["post_fix_categories"]

    def test_no_op_fix_does_not_appear_in_post_fix_categories(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)  # already exists
        archive = create_archive(project_dir)

        finding = {
            "id": "env-wiring:missing:plans-directory",
            "category": "env_wiring",
            "severity": "info",
            "summary": "Plans directory missing",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "create_dir", "path": str(plans_dir)},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        assert result["post_fix_categories"] == []

    # ------------------------------------------------------------------
    # actions.json persistence
    # ------------------------------------------------------------------

    def test_auto_fix_writes_actions_json_to_archive(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"
        if plans_dir.exists():
            plans_dir.rmdir()
        archive = create_archive(project_dir)

        finding = {
            "id": "env-wiring:missing:plans-directory",
            "category": "env_wiring",
            "severity": "info",
            "summary": "Plans directory missing",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "create_dir", "path": str(plans_dir)},
            "previously_suppressed": False,
        }
        auto_fix(project_dir, [finding], archive)

        actions_file = archive / "actions.json"
        assert actions_file.exists()
        data = json.loads(actions_file.read_text())
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# E5-S04: Content-based backup tests
# ---------------------------------------------------------------------------

class TestContentBackup:
    """E5-S04: before/ files, diffs/ files, no-op behavior."""

    def test_after_write_field_before_dir_contains_original_content(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        original_content = "phase_schema_version: 1\nfoo: bar\n"
        ss_path.write_text(original_content)
        archive = create_archive(project_dir)

        finding = {
            "id": "state-integrity:schema:test",
            "category": "state_integrity",
            "severity": "warning",
            "summary": "Schema version",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "write_field", "file": str(ss_path), "key": "phase_schema_version", "value": 2},
            "previously_suppressed": False,
        }
        auto_fix(project_dir, [finding], archive)

        before_dir = archive / "before"
        before_files = list(before_dir.iterdir())
        assert len(before_files) == 1
        assert before_files[0].read_bytes() == original_content.encode("utf-8")

    def test_after_write_field_diffs_dir_contains_valid_unified_diff(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss_path.write_text("phase_schema_version: 1\n")
        archive = create_archive(project_dir)

        finding = {
            "id": "state-integrity:schema:test",
            "category": "state_integrity",
            "severity": "warning",
            "summary": "Schema version",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "write_field", "file": str(ss_path), "key": "phase_schema_version", "value": 2},
            "previously_suppressed": False,
        }
        auto_fix(project_dir, [finding], archive)

        diffs_dir = archive / "diffs"
        diff_files = list(diffs_dir.iterdir())
        assert len(diff_files) == 1
        diff_text = diff_files[0].read_text()
        assert diff_text.startswith("---")
        assert "+++" in diff_text

    def test_after_delete_file_before_dir_contains_deleted_content(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        target = project_dir / ".sweetclaude" / "state" / "pending-drift-decision.yaml"
        original_content = "decision: pending\n"
        target.write_text(original_content)
        archive = create_archive(project_dir)

        finding = {
            "id": "migration-currency:stale-drift-marker:pending-drift-decision.yaml",
            "category": "migration_currency",
            "severity": "info",
            "summary": "Stale drift marker",
            "detail": "",
            "file_paths": [str(target)],
            "fix_type": "auto",
            "fix_recipe": {"action": "delete_file", "file": str(target)},
            "previously_suppressed": False,
        }
        auto_fix(project_dir, [finding], archive)

        before_dir = archive / "before"
        before_files = list(before_dir.iterdir())
        assert len(before_files) == 1
        assert before_files[0].read_bytes() == original_content.encode("utf-8")

    def test_no_op_fix_writes_no_backup_or_diff(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss_path.write_text("phase_schema_version: 2\n")
        archive = create_archive(project_dir)

        finding = {
            "id": "state-integrity:schema:test",
            "category": "state_integrity",
            "severity": "warning",
            "summary": "Schema version already correct",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "write_field", "file": str(ss_path), "key": "phase_schema_version", "value": 2},
            "previously_suppressed": False,
        }
        auto_fix(project_dir, [finding], archive)

        before_files = list((archive / "before").iterdir())
        diffs_files = list((archive / "diffs").iterdir())
        assert before_files == []
        assert diffs_files == []


# ---------------------------------------------------------------------------
# E5-S05: Post-fix rescan tests
# ---------------------------------------------------------------------------

class TestPostFixRescan:
    """E5-S05: post_fix_rescan behavior."""

    def test_rescan_returns_empty_when_all_problems_fixed(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"
        if plans_dir.exists():
            plans_dir.rmdir()

        original_finding_ids = {"env-wiring:missing:plans-directory"}

        # Apply the fix manually
        plans_dir.mkdir(parents=True, exist_ok=True)

        result = post_fix_rescan(project_dir, ["env_wiring"], original_finding_ids)

        env_wiring_findings = [
            f for f in result["findings"]
            if f["id"] == "env-wiring:missing:plans-directory"
        ]
        assert env_wiring_findings == []

    def test_rescan_filters_out_original_finding_ids(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        # Remove plansDirectory from global settings to provoke that finding
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({}))

        original_finding_ids = {"env-wiring:plans-directory-unset:settings_global"}

        result = post_fix_rescan(project_dir, ["env_wiring"], original_finding_ids)

        returned_ids = [f["id"] for f in result["findings"]]
        assert "env-wiring:plans-directory-unset:settings_global" not in returned_ids

    def test_rescan_returns_genuinely_new_findings(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"

        # Condition A: plans directory missing
        if plans_dir.exists():
            plans_dir.rmdir()

        # Condition B: settings has no plansDirectory (remove it from global settings)
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({}))

        # Original finding IDs include only A
        original_finding_ids = {"env-wiring:missing:plans-directory"}

        # Fix A (create the dir)
        plans_dir.mkdir(parents=True, exist_ok=True)

        # Now rescan — B should appear, A should not
        result = post_fix_rescan(project_dir, ["env_wiring"], original_finding_ids)

        returned_ids = [f["id"] for f in result["findings"]]
        assert "env-wiring:plans-directory-unset:settings_global" in returned_ids
        assert "env-wiring:missing:plans-directory" not in returned_ids

    def test_categories_not_requested_are_not_rescanned(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "session_state": None,
        })
        # session-state.yaml missing would produce a state_integrity finding
        # We request only env_wiring — state_integrity should NOT be rescanned

        result = post_fix_rescan(project_dir, ["env_wiring"], set())

        state_integrity_findings = [
            f for f in result["findings"]
            if f["category"] == "state_integrity"
        ]
        assert state_integrity_findings == []


# ---------------------------------------------------------------------------
# E5-S06: Archive integrity tests
# ---------------------------------------------------------------------------

class TestArchiveIntegrity:
    """E5-S06: archive structure, record_action, persist, manifest."""

    # ------------------------------------------------------------------
    # create_archive structure
    # ------------------------------------------------------------------

    def test_create_archive_produces_correct_directory_structure(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        assert archive.is_dir()
        assert (archive / "before").is_dir()
        assert (archive / "diffs").is_dir()

    def test_create_archive_name_matches_iso8601_format(self, tmp_path, fake_home):
        import re
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        pattern = re.compile(r"^\d{8}T\d{6}Z$")
        assert pattern.match(archive.name), (
            f"Archive name '{archive.name}' does not match YYYYMMDDTHHMMSSZ format"
        )

    # ------------------------------------------------------------------
    # Manifest before/ and diffs/ counts match changed actions
    # ------------------------------------------------------------------

    def test_before_and_diffs_counts_match_changed_actions(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss_path.write_text("phase_schema_version: 1\n")
        archive = create_archive(project_dir)

        finding = {
            "id": "state-integrity:schema:test",
            "category": "state_integrity",
            "severity": "warning",
            "summary": "Schema version",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "write_field", "file": str(ss_path), "key": "phase_schema_version", "value": 2},
            "previously_suppressed": False,
        }
        result = auto_fix(project_dir, [finding], archive)

        changed_count = sum(
            1 for a in result["actions"]
            if a.get("before_hash") != a.get("after_hash")
        )
        before_count = len(list((archive / "before").iterdir()))
        diffs_count = len(list((archive / "diffs").iterdir()))

        assert before_count == changed_count
        assert diffs_count == changed_count

    # ------------------------------------------------------------------
    # record_action
    # ------------------------------------------------------------------

    def test_record_action_appends_to_pending_actions_jsonl(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        record_action(archive, {"action": "prompted-fix", "finding_id": "test-1"})
        record_action(archive, {"action": "skip", "finding_id": "test-2"})

        pending_file = archive / "pending-actions.jsonl"
        assert pending_file.exists()
        lines = [l for l in pending_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 2
        for line in lines:
            json.loads(line)  # must be valid JSON

    # ------------------------------------------------------------------
    # persist
    # ------------------------------------------------------------------

    def test_persist_assembles_manifest_from_auto_and_prompted_actions(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        # Write actions.json with 1 auto-fix
        auto_actions = [{"action": "auto-fix", "finding_id": "x-1"}]
        (archive / "actions.json").write_text(json.dumps(auto_actions))

        # Write pending-actions.jsonl with 1 prompted-fix and 1 skip
        pending_lines = [
            json.dumps({"action": "prompted-fix", "finding_id": "x-2"}),
            json.dumps({"action": "skip", "finding_id": "x-3"}),
        ]
        (archive / "pending-actions.jsonl").write_text("\n".join(pending_lines) + "\n")

        persist(project_dir, archive)

        manifest = json.loads((archive / "manifest.json").read_text())
        assert len(manifest["actions"]) == 3
        assert manifest["summary"]["auto_fixed"] == 1
        assert manifest["summary"]["user_fixed"] == 1
        assert manifest["summary"]["skipped"] == 1

    def test_persist_writes_last_doctor_run_json_with_required_fields(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        auto_actions = [{"action": "auto-fix", "finding_id": "x-1"}]
        (archive / "actions.json").write_text(json.dumps(auto_actions))

        scan_findings = [
            {"id": "env-wiring:test", "severity": "warning", "summary": "test finding"}
        ]
        persist(project_dir, archive, menu_preference="proceed", scan_findings=scan_findings)

        last_run_path = project_dir / ".sweetclaude" / "state" / "last-doctor-run.json"
        assert last_run_path.exists()
        data = json.loads(last_run_path.read_text())

        assert "timestamp" in data
        assert "version" in data
        assert "summary" in data
        assert "findings" in data
        assert data["menu_preference"] == "proceed"
        assert data["summary"]["warnings"] == 1
        assert data["summary"]["errors"] == 0
        assert data["summary"]["total_findings"] == 1
        assert data["findings_total"] == 1
        assert data["findings_truncated"] == 0

    def test_persist_caps_last_doctor_run_findings_to_keep_status_compact(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        scan_findings = [
            {
                "id": f"file-diagnostics:test-{idx}",
                "severity": "warning",
                "summary": f"test finding {idx}",
            }
            for idx in range(150)
        ]
        persist(project_dir, archive, scan_findings=scan_findings)

        last_run_path = project_dir / ".sweetclaude" / "state" / "last-doctor-run.json"
        data = json.loads(last_run_path.read_text())

        assert data["summary"]["warnings"] == 150
        assert data["summary"]["total_findings"] == 150
        assert data["findings_total"] == 150
        assert data["findings_truncated"] == 50
        assert len(data["findings"]) == 100

    def test_persist_records_safety_branch_in_manifest(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        persist(project_dir, archive, safety_branch="doctor/run-20260522T120000Z")

        manifest = json.loads((archive / "manifest.json").read_text())
        assert manifest["safety_branch"] == "doctor/run-20260522T120000Z"


# ---------------------------------------------------------------------------
# E5-S07: Retention / pruning tests
# ---------------------------------------------------------------------------

import datetime


def _make_archive_dir(runs_dir: "Path", days_old: int) -> "Path":
    """Create a doctor-run archive directory with a name that is `days_old` days in the past."""
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_old)
    name = dt.strftime("%Y%m%dT%H%M%SZ")
    d = runs_dir / name
    d.mkdir(parents=True, exist_ok=True)
    return d


class TestRetention:
    """E5-S07: prune_archives retention and pruning logic."""

    # ------------------------------------------------------------------
    # Scenario: With 3 archives all within 30 days, none are pruned
    # ------------------------------------------------------------------

    def test_three_recent_archives_none_pruned(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        runs_dir = project_dir / ".sweetclaude" / "state" / "doctor-runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        for days in [1, 2, 3]:
            _make_archive_dir(runs_dir, days)

        pruned = prune_archives(project_dir)

        assert pruned == [], f"Expected no pruning for 3 recent archives, got: {pruned}"
        assert len(list(runs_dir.iterdir())) == 3

    # ------------------------------------------------------------------
    # Scenario: With 7 archives and 3 older than 30 days, 2 oldest are pruned
    # ------------------------------------------------------------------

    def test_seven_archives_three_old_prunes_two_oldest(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        runs_dir = project_dir / ".sweetclaude" / "state" / "doctor-runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        # 4 recent archives (within 30 days)
        for days in [1, 2, 3, 4]:
            _make_archive_dir(runs_dir, days)
        # 3 old archives (older than 30 days) — sorted descending means
        # positions 4,5,6 after keep_min=5 are 6th and older
        for days in [35, 40, 45]:
            _make_archive_dir(runs_dir, days)

        pruned = prune_archives(project_dir)

        assert len(pruned) == 2, (
            f"Expected 2 pruned, got {len(pruned)}: {pruned}"
        )
        assert len(list(runs_dir.iterdir())) == 5

    # ------------------------------------------------------------------
    # Scenario: With 10 archives and 8 older than 30 days, 5 oldest are pruned
    # ------------------------------------------------------------------

    def test_ten_archives_eight_old_prunes_five_oldest(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        runs_dir = project_dir / ".sweetclaude" / "state" / "doctor-runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        # 2 recent
        for days in [1, 2]:
            _make_archive_dir(runs_dir, days)
        # 8 old (older than 30 days), at various ages
        for days in [31, 35, 40, 45, 50, 55, 60, 65]:
            _make_archive_dir(runs_dir, days)

        pruned = prune_archives(project_dir)

        # keep_min=5: dirs[5:] are 5 oldest, all old → pruned
        assert len(pruned) == 5, (
            f"Expected 5 pruned, got {len(pruned)}: {pruned}"
        )
        assert len(list(runs_dir.iterdir())) == 5

    # ------------------------------------------------------------------
    # Scenario: With 6 archives and 1 older than 30 days, 1 is pruned
    # ------------------------------------------------------------------

    def test_six_archives_one_old_prunes_one(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        runs_dir = project_dir / ".sweetclaude" / "state" / "doctor-runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        # 5 recent
        for days in [1, 2, 3, 4, 5]:
            _make_archive_dir(runs_dir, days)
        # 1 old
        _make_archive_dir(runs_dir, 45)

        pruned = prune_archives(project_dir)

        assert len(pruned) == 1, (
            f"Expected 1 pruned, got {len(pruned)}: {pruned}"
        )
        assert len(list(runs_dir.iterdir())) == 5

    # ------------------------------------------------------------------
    # Scenario: Pruning uses directory name timestamp, not mtime
    # ------------------------------------------------------------------

    def test_pruning_uses_name_timestamp_not_mtime(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        runs_dir = project_dir / ".sweetclaude" / "state" / "doctor-runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        # 5 recent dirs (not prunable)
        for days in [1, 2, 3, 4, 5]:
            _make_archive_dir(runs_dir, days)
        # 1 dir with an OLD timestamp in the name, but set mtime to now
        old_dir = _make_archive_dir(runs_dir, 45)
        import time
        now = time.time()
        os.utime(old_dir, (now, now))

        pruned = prune_archives(project_dir)

        # Should be pruned based on name, despite recent mtime
        assert len(pruned) == 1, (
            f"Expected 1 pruned based on name timestamp, got {len(pruned)}: {pruned}"
        )

    # ------------------------------------------------------------------
    # Scenario: No doctor-runs directory returns empty list
    # ------------------------------------------------------------------

    def test_no_doctor_runs_directory_returns_empty_list(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        runs_dir = project_dir / ".sweetclaude" / "state" / "doctor-runs"
        if runs_dir.exists():
            shutil.rmtree(runs_dir)

        pruned = prune_archives(project_dir)

        assert pruned == [], f"Expected empty list when no runs dir, got: {pruned}"

    # ------------------------------------------------------------------
    # Scenario: Non-timestamp directory names are skipped during pruning
    # ------------------------------------------------------------------

    def test_non_timestamp_directory_names_are_skipped(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        runs_dir = project_dir / ".sweetclaude" / "state" / "doctor-runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        # 5 recent valid dirs
        for days in [1, 2, 3, 4, 5]:
            _make_archive_dir(runs_dir, days)
        # 1 old valid dir that would be pruned if it weren't for the "temp" distractor
        _make_archive_dir(runs_dir, 45)
        # 1 non-timestamp dir named "temp"
        temp_dir = runs_dir / "temp"
        temp_dir.mkdir()

        prune_archives(project_dir)

        assert temp_dir.exists(), (
            "Non-timestamp directory 'temp' should not be removed by pruning"
        )


# ---------------------------------------------------------------------------
# E5-S08: Suppression tests
# ---------------------------------------------------------------------------


class TestSuppression:
    """E5-S08: suppression filtering, auto-cleanup, and persistence."""

    # ------------------------------------------------------------------
    # Scenario: Suppressed finding is excluded from scan output
    # ------------------------------------------------------------------

    def test_suppressed_finding_excluded_from_scan_output(self, tmp_path, fake_home):
        # Create a project that produces an unknown-status finding
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test",
                    "status": "invented",
                }},
            ],
            "suppressions": [
                {"finding_id": "file-diagnostics:unknown-status:ISSUE-001-test.md"},
            ],
        })

        state = build_project_state(project_dir)
        result = _scan(state)

        finding_ids = [f["id"] for f in result["findings"]]
        assert "file-diagnostics:unknown-status:ISSUE-001-test.md" not in finding_ids, (
            f"Suppressed finding should be excluded from scan output, got: {finding_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Resolved finding has its suppression entry auto-removed
    # ------------------------------------------------------------------

    def test_resolved_suppression_reported_but_not_pruned_during_scan(self, tmp_path, fake_home):
        # Suppress "env-wiring:missing:plans-directory" but don't actually remove plans dir
        # (so the finding resolves — the plans dir exists → finding won't appear)
        project_dir = build_fixture(tmp_path, overrides={
            "suppressions": [
                {"finding_id": "env-wiring:missing:plans-directory"},
            ],
        })
        # Plans dir exists in healthy fixture, so the finding is NOT produced → resolved

        state = build_project_state(project_dir)
        result = _scan(state)

        assert "env-wiring:missing:plans-directory" in result["suppressions_resolved"], (
            f"Resolved suppression should appear in suppressions_resolved, "
            f"got: {result['suppressions_resolved']}"
        )
        # P4/P2: scan is read-only — the resolved entry is REPORTED but NOT pruned
        # during scan. The prune is deferred to the execute phase (see TestP5).
        remaining = load_suppressions(project_dir)
        remaining_ids = [e.get("finding_id") for e in remaining]
        assert "env-wiring:missing:plans-directory" in remaining_ids, (
            f"scan must not prune the ledger (read-only); entry should remain, got: {remaining_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Auto-removed suppression ID appears in auto_cleanup result
    # ------------------------------------------------------------------

    def test_prune_removes_stale_suppression_retains_active_and_backs_up(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "suppressions": [
                {"finding_id": "finding-A"},
                {"finding_id": "finding-B"},
            ],
        })

        archive = create_archive(project_dir)
        resolved = prune_resolved_suppressions(project_dir, archive, {"finding-B"})

        assert "finding-A" in resolved, (
            f"finding-A should be in resolved set, got: {resolved}"
        )
        remaining = load_suppressions(project_dir)
        remaining_ids = [e.get("finding_id") for e in remaining]
        assert "finding-B" in remaining_ids, (
            f"finding-B should remain in suppression file, got: {remaining_ids}"
        )
        assert "finding-A" not in remaining_ids, (
            f"finding-A should be removed from suppression file, got: {remaining_ids}"
        )
        # P2: the prune is backed up through the archive (restore-reversible).
        before_text = "\n".join(
            p.read_text() for p in (archive / "before").rglob("*") if p.is_file()
        )
        assert "finding-A" in before_text, (
            "prune must back up the pre-prune ledger under the archive's before/"
        )

    # ------------------------------------------------------------------
    # Scenario: Re-emerged finding (still suppressed, not in resolved)
    # ------------------------------------------------------------------

    def test_re_emerged_finding_still_suppressed_in_scan(self, tmp_path, fake_home):
        # Remove plans dir so the finding IS produced, but also suppress it
        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"
        if plans_dir.exists():
            shutil.rmtree(plans_dir)
        suppression_path = project_dir / ".sweetclaude" / "state" / "doctor-suppressions.json"
        suppression_path.write_text(json.dumps([
            {"finding_id": "env-wiring:missing:plans-directory"}
        ]))

        state = build_project_state(project_dir)
        result = _scan(state)

        finding_ids = [f["id"] for f in result["findings"]]
        assert "env-wiring:missing:plans-directory" not in finding_ids, (
            f"Re-emerged but still-suppressed finding should be excluded from active findings, "
            f"got: {finding_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: load_suppressions returns empty list for missing file
    # ------------------------------------------------------------------

    def test_load_suppressions_returns_empty_list_for_missing_file(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        suppression_path = project_dir / ".sweetclaude" / "state" / "doctor-suppressions.json"
        if suppression_path.exists():
            suppression_path.unlink()

        result = load_suppressions(project_dir)

        assert result == [], (
            f"load_suppressions should return [] for missing file, got: {result}"
        )

    # ------------------------------------------------------------------
    # Scenario: load_suppressions returns empty list for malformed file
    # ------------------------------------------------------------------

    def test_load_suppressions_returns_empty_list_for_malformed_file(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        suppression_path = project_dir / ".sweetclaude" / "state" / "doctor-suppressions.json"
        suppression_path.write_text('"not a list"')

        result = load_suppressions(project_dir)

        assert result == [], (
            f"load_suppressions should return [] for a non-list JSON value, got: {result}"
        )

    # ------------------------------------------------------------------
    # Scenario: save_suppressions creates parent directories if needed
    # ------------------------------------------------------------------

    def test_save_suppressions_creates_parent_dirs_if_needed(self, tmp_path, fake_home):
        project_dir = tmp_path / "new-project"
        project_dir.mkdir()
        # state dir does NOT exist

        entries = [{"finding_id": "test:id", "suppressed_at": "2026-01-01"}]
        save_suppressions(project_dir, entries)

        suppression_path = project_dir / ".sweetclaude" / "state" / "doctor-suppressions.json"
        assert suppression_path.exists(), (
            "save_suppressions should create parent dirs and write the file"
        )
        data = json.loads(suppression_path.read_text())
        assert data == entries, (
            f"Written entries should match input, got: {data}"
        )


class TestP5ScanReadOnlySuppression:
    """P5: the read-only scan phase must not mutate the suppression ledger.

    Closes the FINAL-audit residual (P2 + P4): scan formerly pruned stale
    suppressions via auto_cleanup_suppressions -> save_suppressions, writing
    doctor-suppressions.json during the read-only scan and bypassing the
    executor backup pipeline. Scan now only computes the resolved set
    (read-only); the prune is deferred to the execute phase (persist) and
    routed through the archive so it is backed up + diffed + restore-reversible.
    """

    def test_scan_leaves_suppression_ledger_byte_identical(self, tmp_path, fake_home):
        # A resolved suppression (its finding no longer fires) must still be
        # REPORTED by scan, but the ledger file must be untouched (P4).
        project_dir = build_fixture(tmp_path, overrides={
            "suppressions": [
                {"finding_id": "env-wiring:missing:plans-directory"},
            ],
        })
        supp_path = project_dir / ".sweetclaude" / "state" / "doctor-suppressions.json"
        before_bytes = supp_path.read_bytes()

        state = build_project_state(project_dir)
        result = _scan(state)

        assert "env-wiring:missing:plans-directory" in result["suppressions_resolved"], (
            "scan must still report the resolved suppression read-only, "
            f"got: {result['suppressions_resolved']}"
        )
        assert supp_path.read_bytes() == before_bytes, (
            "scan must not write doctor-suppressions.json (P4 read-only / P2 backup)"
        )

    def test_execute_phase_prunes_and_backs_up_resolved_suppression(self, tmp_path, fake_home):
        # The deferred prune happens in the execute phase (persist) and is
        # routed through the archive backup pipeline (P2).
        project_dir = build_fixture(tmp_path, overrides={
            "suppressions": [
                {"finding_id": "env-wiring:missing:plans-directory"},
            ],
        })
        state = build_project_state(project_dir)
        scan_result = _scan(state)

        archive = create_archive(project_dir)
        persist(project_dir, archive, scan_findings=scan_result["findings"])

        remaining_ids = [e.get("finding_id") for e in load_suppressions(project_dir)]
        assert "env-wiring:missing:plans-directory" not in remaining_ids, (
            f"execute phase must prune the resolved suppression, got: {remaining_ids}"
        )

        # Parse the before-image as JSON (not a text search) and confirm the
        # pruned entry was present in the backed-up ledger at the canonical path.
        before_images = [p for p in (archive / "before").rglob("*")
                         if p.is_file() and "doctor-suppressions" in p.name]
        assert before_images, "the pre-prune ledger must be backed up under before/"
        backed_up = json.loads(before_images[0].read_text())
        assert any(e.get("finding_id") == "env-wiring:missing:plans-directory"
                   for e in backed_up), (
            f"the backed-up before-image must contain the pruned entry, got: {backed_up}"
        )
        diff_text = "\n".join(
            p.read_text() for p in (archive / "diffs").rglob("*.diff")
        )
        assert "env-wiring:missing:plans-directory" in diff_text, (
            "the prune must record a diff under the archive's diffs/"
        )

    def test_pruned_suppression_is_restore_reversible(self, tmp_path, fake_home):
        # S6: the execute-phase prune registers an action, so `restore` reverts
        # the ledger to its pre-prune state from the archived before-image.
        project_dir = build_fixture(tmp_path, overrides={
            "suppressions": [
                {"finding_id": "env-wiring:missing:plans-directory"},
            ],
        })
        state = build_project_state(project_dir)
        scan_result = _scan(state)

        archive = create_archive(project_dir)
        persist(project_dir, archive, scan_findings=scan_result["findings"])

        # Pruned away:
        assert "env-wiring:missing:plans-directory" not in [
            e.get("finding_id") for e in load_suppressions(project_dir)
        ]

        result = _doctor_module.restore(project_dir, archive, restore_all=True)

        supp_path = project_dir / ".sweetclaude" / "state" / "doctor-suppressions.json"
        assert str(supp_path) in result["restored"], (
            f"restore must revert the suppression ledger, got: {result}"
        )
        assert "env-wiring:missing:plans-directory" in [
            e.get("finding_id") for e in load_suppressions(project_dir)
        ], "restore must bring the pruned entry back"

    def test_execute_phase_no_prune_when_findings_not_passed(self, tmp_path, fake_home):
        # When persist is called without scan_findings the current finding set
        # is unknown, so no entry may be pruned (avoid clobbering live entries).
        project_dir = build_fixture(tmp_path, overrides={
            "suppressions": [
                {"finding_id": "env-wiring:missing:plans-directory"},
            ],
        })
        supp_path = project_dir / ".sweetclaude" / "state" / "doctor-suppressions.json"
        before_bytes = supp_path.read_bytes()

        archive = create_archive(project_dir)
        persist(project_dir, archive)

        assert supp_path.read_bytes() == before_bytes, (
            "persist without scan_findings must not prune (findings unknown)"
        )

    def test_prune_keeps_entry_without_finding_id(self, tmp_path, fake_home):
        # C1: an entry lacking a finding_id (hand-written/legacy) must survive a
        # prune rather than being collateral-dropped by the resolved-set filter.
        project_dir = build_fixture(tmp_path, overrides={
            "suppressions": [
                {"reason": "legacy entry, no finding_id"},
                {"finding_id": "stale-resolved-finding"},
            ],
        })
        archive = create_archive(project_dir)
        # "stale-resolved-finding" is not in the current set -> resolved/pruned;
        # the finding_id-less entry must remain.
        resolved = prune_resolved_suppressions(project_dir, archive, {"other-live"})
        assert "stale-resolved-finding" in resolved
        remaining = load_suppressions(project_dir)
        assert any("finding_id" not in e for e in remaining), (
            f"entry without finding_id must survive prune, got: {remaining}"
        )
        assert all(e.get("finding_id") != "stale-resolved-finding" for e in remaining)


class TestPrePushHardening:
    """Path-containment guards surfaced by the pre-push security review (F1/F3/F5).

    doctor may only write inside the project tree or the user's ~/.claude install
    — never an arbitrary path supplied via a crafted recipe or archive.
    """

    def test_file_move_rejects_dest_outside_project(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        src = project_dir / ".sweetclaude" / "state" / "moveme.md"
        src.write_text("payload\n")
        escape = tmp_path / "outside" / "owned.md"  # outside the project tree
        archive = create_archive(project_dir)
        result = execute_recipe(
            project_dir,
            {"action": "file_move", "src": str(src), "dest": str(escape)},
            archive,
        )
        assert result.success is False
        assert "outside project" in (result.error or "")
        assert not escape.exists(), "file_move must not write outside the project"
        assert src.exists(), "source must be untouched on a rejected move"

    def test_run_script_rejects_path_outside_trusted_roots(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        evil = tmp_path / "evil"
        evil.mkdir()
        # Allowlisted basename, but living outside every trusted root.
        stub = evil / "generate-session-state.sh"
        stub.write_text("#!/bin/bash\necho pwned\n")
        with pytest.raises(ValueError, match="outside trusted roots"):
            execute_recipe(
                project_dir,
                {"action": "run_script", "cmd": ["bash", str(stub)]},
                archive,
            )

    def test_restore_skips_action_escaping_allowed_roots(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        # Forge an archive action pointing at a path outside project + ~/.claude,
        # with a before-image present, and confirm restore refuses to write it.
        escape = tmp_path / "outside" / "victim.txt"
        from doctor import backup_content, write_manifest
        backup_content(archive, escape, b"original\n")
        write_manifest(archive, {"actions": [{"action": "auto-fix", "file_path": str(escape)}]})
        result = _doctor_module.restore(project_dir, archive, restore_all=True)
        assert str(escape) not in result["restored"]
        assert any(s["reason"] == "outside allowed roots" for s in result["skipped"]), (
            f"restore must skip the escaping action, got: {result}"
        )
        assert not escape.exists(), "restore must not write outside allowed roots"

    def test_delete_file_restore_recreates_file_byte_identically(self, tmp_path, fake_home):
        # Test gap: no standalone proof that restore recreates a DELETED file.
        project_dir = build_fixture(tmp_path)
        target = project_dir / ".sweetclaude" / "state" / "deleteme.yaml"
        target.write_text("foo: bar\n")
        original = target.read_bytes()
        archive = create_archive(project_dir)
        finding = {
            "id": "x", "category": "y", "summary": "s", "fix_type": "auto",
            "fix_recipe": {"action": "delete_file", "file": str(target)},
        }
        auto_fix(project_dir, [finding], archive)
        assert not target.exists(), "precondition: file deleted by auto_fix"

        result = _doctor_module.restore(project_dir, archive, restore_all=True)
        assert str(target) in result["restored"], (
            f"restore must recreate the deleted file, got: {result}"
        )
        assert target.exists() and target.read_bytes() == original


# ---------------------------------------------------------------------------
# E5-S09: Dry-run simulation tests
# ---------------------------------------------------------------------------


def _make_dry_run_finding(
    fix_type: str = "auto",
    action: str = "write_field",
    finding_id: str = "test:finding:id",
    summary: str = "Test finding",
    file: str = "",
    key: str = "",
    value=None,
    cmd=None,
) -> dict:
    """Build a minimal finding dict for dry_run tests."""
    recipe: dict = {"action": action}
    if file:
        recipe["file"] = file
    if key:
        recipe["key"] = key
    if value is not None:
        recipe["value"] = value
    if cmd is not None:
        recipe["cmd"] = cmd
    return {
        "id": finding_id,
        "category": "test",
        "severity": "warning",
        "summary": summary,
        "detail": "",
        "file_paths": [],
        "fix_type": fix_type,
        "fix_recipe": recipe,
        "previously_suppressed": False,
    }


class TestDryRun:
    """E5-S09: dry_run simulation output for various fix types and recipe actions."""

    # ------------------------------------------------------------------
    # Scenario: Dry-run of write_field shows before/after values
    # ------------------------------------------------------------------

    def test_write_field_shows_before_and_after(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss_path.write_text("phase_schema_version: 1\n")

        # dry_run uses a relative file key resolved against project_dir
        relative_key = ".sweetclaude/state/session-state.yaml"
        finding = _make_dry_run_finding(
            fix_type="auto",
            action="write_field",
            finding_id="state-integrity:schema-version:session-state.yaml",
            file=relative_key,
            key="phase_schema_version",
            value=2,
        )

        result = dry_run(project_dir, [finding])

        assert len(result["simulations"]) == 1, (
            f"Expected 1 simulation entry, got {len(result['simulations'])}"
        )
        sim = result["simulations"][0]
        assert "before" in sim, f"Expected 'before' key in simulation, got: {sim}"
        assert "after" in sim, f"Expected 'after' key in simulation, got: {sim}"
        assert "phase_schema_version: 1" in sim["before"] or "1" in sim["before"], (
            f"'before' should contain original value, got: {sim['before']}"
        )
        assert "phase_schema_version: 2" in sim["after"] or "2" in sim["after"], (
            f"'after' should contain new value, got: {sim['after']}"
        )

    # ------------------------------------------------------------------
    # Scenario: Dry-run of rebuild_cache shows requires-execution note
    # ------------------------------------------------------------------

    def test_rebuild_cache_shows_requires_execution_note(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        finding = _make_dry_run_finding(
            fix_type="auto",
            action="rebuild_cache",
            finding_id="storage-lint:counter-drift:issue",
        )

        result = dry_run(project_dir, [finding])

        assert len(result["simulations"]) == 1
        sim = result["simulations"][0]
        assert "note" in sim, f"Expected 'note' key in simulation, got: {sim}"
        assert "requires real execution" in sim["note"].lower(), (
            f"Note should mention 'requires real execution', got: {sim['note']}"
        )

    # ------------------------------------------------------------------
    # Scenario: Dry-run of run_script shows requires-execution note
    # ------------------------------------------------------------------

    def test_run_script_shows_requires_execution_note(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        finding = _make_dry_run_finding(
            fix_type="auto",
            action="run_script",
            finding_id="state-integrity:missing:session-state.yaml",
            cmd=["bash", "scripts/generate-session-state.sh"],
        )

        result = dry_run(project_dir, [finding])

        assert len(result["simulations"]) == 1
        sim = result["simulations"][0]
        assert "note" in sim, f"Expected 'note' key in simulation, got: {sim}"
        assert "requires real execution" in sim["note"].lower(), (
            f"Note should mention 'requires real execution', got: {sim['note']}"
        )

    # ------------------------------------------------------------------
    # Scenario: Dry-run of prompted finding shows approval note
    # ------------------------------------------------------------------

    def test_prompted_finding_shows_approval_note(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        finding = _make_dry_run_finding(
            fix_type="prompted",
            action="write_field",
            finding_id="state-integrity:test:prompted",
            file=".sweetclaude/state/session-state.yaml",
            key="x",
            value="y",
        )

        result = dry_run(project_dir, [finding])

        assert len(result["simulations"]) == 1
        sim = result["simulations"][0]
        assert sim.get("note") == "Will be presented for your approval", (
            f"Expected exact approval note, got: {sim.get('note')}"
        )

    # ------------------------------------------------------------------
    # Scenario: Dry-run produces zero side effects
    # ------------------------------------------------------------------

    def test_dry_run_produces_no_side_effects(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        ss_path = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        original_content = "phase_schema_version: 1\n"
        ss_path.write_text(original_content)

        relative_key = ".sweetclaude/state/session-state.yaml"
        finding = _make_dry_run_finding(
            fix_type="auto",
            action="write_field",
            finding_id="state-integrity:schema-version:session-state.yaml",
            file=relative_key,
            key="phase_schema_version",
            value=2,
        )

        dry_run(project_dir, [finding])

        # File should be unchanged
        assert ss_path.read_text() == original_content, (
            f"dry_run must not modify session-state.yaml; "
            f"got: {ss_path.read_text()!r}"
        )
        # No archive directory created
        runs_dir = project_dir / ".sweetclaude" / "state" / "doctor-runs"
        assert not runs_dir.exists() or len(list(runs_dir.iterdir())) == 0, (
            "dry_run must not create any archive directories"
        )

    # ------------------------------------------------------------------
    # Scenario: Dry-run of create_dir shows description
    # ------------------------------------------------------------------

    def test_create_dir_shows_description(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"
        if plans_dir.exists():
            shutil.rmtree(plans_dir)

        finding = {
            "id": "env-wiring:missing:plans-directory",
            "category": "env_wiring",
            "severity": "info",
            "summary": "Plans directory missing",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {
                "action": "create_dir",
                "path": str(plans_dir),
            },
            "previously_suppressed": False,
        }

        result = dry_run(project_dir, [finding])

        assert len(result["simulations"]) == 1
        sim = result["simulations"][0]
        assert "description" in sim, f"Expected 'description' key in simulation, got: {sim}"
        assert "create_dir" in sim["description"], (
            f"Description should mention 'create_dir', got: {sim['description']}"
        )

    # ------------------------------------------------------------------
    # Scenario: Dry-run of report-only finding produces no simulation entry
    # ------------------------------------------------------------------

    def test_report_only_finding_produces_no_simulation_entry(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        finding = {
            "id": "state-integrity:schema-version:sweetclaude.yaml",
            "category": "state_integrity",
            "severity": "warning",
            "summary": "Schema version outdated",
            "detail": "",
            "file_paths": [],
            "fix_type": "report-only",
            "fix_recipe": {},
            "previously_suppressed": False,
        }

        result = dry_run(project_dir, [finding])

        assert len(result["simulations"]) == 0, (
            f"report-only finding should produce no simulation entry, "
            f"got: {result['simulations']}"
        )


# ---------------------------------------------------------------------------
# E5-S10: Graceful degradation tests
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    """
    E5-S10: _scan() catches DependencyMissing per check function and
    populates skipped_categories without aborting the scan.
    """

    # ------------------------------------------------------------------
    # Scenario: Missing cache.py skips counter-drift but other storage rules run
    # ------------------------------------------------------------------

    def test_missing_cache_skips_counter_drift_but_not_storage_lint_category(
        self, tmp_path, fake_home
    ):
        # Duplicate ID in both backlog and roadmap triggers cross-location-duplicate-id
        # which does not need cache.py. No ISSUE-NNN files means max_seen == 0
        # so cache.py absence does NOT raise DependencyMissing.
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {
                    "name": "ISSUE-001-item.md",
                    "frontmatter": {
                        "id": "EPIC-001",
                        "type": "story",
                        "title": "Duplicate",
                        "status": "active",
                    },
                }
            ],
            "roadmap_files": [
                {
                    "name": "EPIC-001-item.md",
                    "frontmatter": {
                        "id": "EPIC-001",
                        "type": "epic",
                        "title": "Duplicate",
                        "status": "active",
                    },
                }
            ],
        })
        # Ensure cache.py does not exist
        cache_script = project_dir / "scripts" / "cache.py"
        assert not cache_script.exists()

        state = build_project_state(project_dir)
        result = _scan(state)

        skipped_names = [s["category"] for s in result["skipped_categories"]]
        assert "storage_lint" not in skipped_names, (
            f"storage_lint should NOT be skipped when cache.py is missing "
            f"(only counter-drift sub-check skips); skipped={skipped_names}"
        )
        finding_ids = [f["id"] for f in result["findings"]]
        cross_dup = [fid for fid in finding_ids if "cross-location-duplicate-id" in fid]
        assert cross_dup, (
            f"Expected cross-location-duplicate-id finding to be present; "
            f"findings={finding_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Missing migration runner skips migration_currency schema drift
    # ------------------------------------------------------------------

    def test_missing_migration_runner_skips_migration_currency(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)
        runner = project_dir / "scripts" / "migrations" / "runner.py"
        runner.unlink(missing_ok=True)
        assert not runner.exists()

        state = build_project_state(project_dir)
        assert state.migration_runner_path is None, (
            "migration_runner_path should be None when runner.py is absent"
        )

        result = _scan(state)

        skipped_names = [s["category"] for s in result["skipped_categories"]]
        assert "migration_currency" in skipped_names, (
            f"migration_currency should be in skipped_categories when runner.py is missing; "
            f"skipped={result['skipped_categories']}"
        )

    # ------------------------------------------------------------------
    # Scenario: Missing migrate_taxonomy.py skips taxonomy drift check
    # ------------------------------------------------------------------

    def test_missing_migrate_taxonomy_skips_taxonomy_drift(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        # Create migration runner so check_migration_currency proceeds past the guard
        runner = project_dir / "scripts" / "migrations" / "runner.py"
        runner.parent.mkdir(parents=True, exist_ok=True)
        runner.write_text("# stub runner\nimport sys; sys.exit(1)\n")

        # No migrate_taxonomy.py exists
        taxonomy_script = project_dir / "scripts" / "migrate_taxonomy.py"
        assert not taxonomy_script.exists()

        state = build_project_state(project_dir)
        assert state.migration_runner_path is not None

        findings = check_migration_currency(state)

        taxonomy_ids = [f.id for f in findings if f.id.startswith("migration-currency:taxonomy-drift")]
        assert taxonomy_ids == [], (
            f"taxonomy-drift finding should not be produced when migrate_taxonomy.py "
            f"is absent; got: {taxonomy_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Missing migrate-v3-to-v4.py skips orphan scan
    # ------------------------------------------------------------------

    def test_missing_migrate_v3_to_v4_skips_orphan_scan(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        # Create migration runner
        runner = project_dir / "scripts" / "migrations" / "runner.py"
        runner.parent.mkdir(parents=True, exist_ok=True)
        runner.write_text("# stub runner\nimport sys; sys.exit(1)\n")

        # Confirm migrate-v3-to-v4.py does not exist
        orphan_script = project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py"
        assert not orphan_script.exists()

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        orphan_ids = [f.id for f in findings if f.id.startswith("migration-currency:orphan")]
        assert orphan_ids == [], (
            f"orphan scan should be skipped when migrate-v3-to-v4.py is absent; "
            f"got: {orphan_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Scan completes and returns valid structure despite all deps missing
    # ------------------------------------------------------------------

    def test_scan_returns_valid_structure_when_all_dep_scripts_missing(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        (project_dir / "scripts" / "migrations" / "runner.py").unlink(missing_ok=True)
        assert not (project_dir / "scripts" / "cache.py").exists()
        assert not (project_dir / "scripts" / "migrations" / "runner.py").exists()
        assert not (project_dir / "scripts" / "migrate_taxonomy.py").exists()
        assert not (project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py").exists()

        state = build_project_state(project_dir)
        result = _scan(state)

        assert "findings" in result, "scan result must contain 'findings'"
        assert "skipped_categories" in result, "scan result must contain 'skipped_categories'"
        assert "suppressions_resolved" in result, "scan result must contain 'suppressions_resolved'"
        assert "project_state_summary" in result, "scan result must contain 'project_state_summary'"

    # ------------------------------------------------------------------
    # Scenario: DependencyMissing populates skipped_categories with category and reason
    # ------------------------------------------------------------------

    def test_dependency_missing_populates_skipped_category_and_reason(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        project_dir = build_fixture(tmp_path)
        runner = project_dir / "scripts" / "migrations" / "runner.py"
        runner.unlink(missing_ok=True)
        assert not runner.exists()

        state = build_project_state(project_dir)
        result = _scan(state)

        mc_entries = [
            s for s in result["skipped_categories"]
            if s.get("category") == "migration_currency"
        ]
        assert mc_entries, (
            f"skipped_categories should contain a migration_currency entry; "
            f"got: {result['skipped_categories']}"
        )
        entry = mc_entries[0]
        assert "category" in entry, "skipped entry must have 'category' key"
        assert entry["category"] == "migration_currency"
        assert "reason" in entry, "skipped entry must have 'reason' key"
        assert entry["reason"], "reason must be a non-empty string"


# ---------------------------------------------------------------------------
# E5-S11: Early exit tests
# ---------------------------------------------------------------------------

class TestEarlyExit:
    """
    E5-S11: main() scan subcommand returns a not-configured error (exit 0)
    when sweetclaude.yaml does not exist.
    """

    # ------------------------------------------------------------------
    # Scenario: Project with no sweetclaude.yaml returns not-configured error
    # ------------------------------------------------------------------

    def test_scan_without_sweetclaude_yaml_emits_not_configured_error(
        self, tmp_path, fake_home, capsys
    ):
        project_dir = build_fixture(tmp_path, overrides={"sweetclaude_yaml": None})
        sc_yaml = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
        assert not sc_yaml.exists()

        from doctor import main
        exit_code = main(["scan", "--project-dir", str(project_dir)])
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output.get("error") == "not-configured", (
            f"Expected error='not-configured', got: {output}"
        )
        assert "message" in output, (
            f"Expected 'message' key in output, got: {output}"
        )
        assert exit_code == 0, f"Expected exit code 0, got: {exit_code}"

    # ------------------------------------------------------------------
    # Scenario: Not-configured output has no findings or skipped_categories
    # ------------------------------------------------------------------

    def test_scan_not_configured_output_has_no_findings_or_skipped_categories(
        self, tmp_path, fake_home, capsys
    ):
        project_dir = build_fixture(tmp_path, overrides={"sweetclaude_yaml": None})

        from doctor import main
        main(["scan", "--project-dir", str(project_dir)])
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "findings" not in output, (
            f"not-configured response must not contain 'findings'; got keys: {list(output.keys())}"
        )
        assert "skipped_categories" not in output, (
            f"not-configured response must not contain 'skipped_categories'; "
            f"got keys: {list(output.keys())}"
        )


# ---------------------------------------------------------------------------
# E5-S12: Happy-path tests
# ---------------------------------------------------------------------------

class TestHappyPath:
    """
    E5-S12: A healthy fixture produces zero findings, a populated summary,
    and a zero-action manifest after the full pipeline.
    """

    # ------------------------------------------------------------------
    # Scenario: Healthy fixture produces zero findings and zero skipped categories
    # ------------------------------------------------------------------

    def test_healthy_fixture_produces_zero_findings_and_no_skipped(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        result = _scan(state)

        assert result["findings"] == [], (
            f"Healthy fixture should produce 0 findings; "
            f"got: {[f['id'] for f in result['findings']]}"
        )
        assert result["skipped_categories"] == [], (
            f"Healthy fixture should have 0 skipped categories; "
            f"got: {result['skipped_categories']}"
        )

    # ------------------------------------------------------------------
    # Scenario: Healthy fixture has populated project_state_summary
    # ------------------------------------------------------------------

    def test_healthy_fixture_project_state_summary_has_required_keys(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        result = _scan(state)

        summary = result["project_state_summary"]
        assert "backlog_count" in summary, (
            f"project_state_summary missing 'backlog_count'; keys={list(summary.keys())}"
        )
        assert "roadmap_count" in summary, (
            f"project_state_summary missing 'roadmap_count'; keys={list(summary.keys())}"
        )
        assert "hook_count" in summary, (
            f"project_state_summary missing 'hook_count'; keys={list(summary.keys())}"
        )
        assert "has_sweetclaude_yaml" in summary, (
            f"project_state_summary missing 'has_sweetclaude_yaml'; keys={list(summary.keys())}"
        )
        assert summary["has_sweetclaude_yaml"] is True, (
            f"project_state_summary 'has_sweetclaude_yaml' should be True; "
            f"got: {summary['has_sweetclaude_yaml']}"
        )

    # ------------------------------------------------------------------
    # Scenario: Full pipeline on healthy fixture produces zero-action manifest
    # ------------------------------------------------------------------

    def test_full_pipeline_healthy_fixture_produces_zero_action_manifest(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        scan_result = _scan(state)

        assert scan_result["findings"] == [], (
            f"Precondition: healthy fixture must produce 0 findings; "
            f"got: {[f['id'] for f in scan_result['findings']]}"
        )

        archive = create_archive(project_dir)
        auto_fix(project_dir, scan_result["findings"], archive)
        persist(project_dir, archive, scan_findings=scan_result["findings"])

        manifest_path = archive / "manifest.json"
        assert manifest_path.exists(), "manifest.json must be written by persist()"
        manifest = json.loads(manifest_path.read_text())

        assert manifest["actions"] == [], (
            f"manifest actions should be empty for zero findings; "
            f"got: {manifest['actions']}"
        )
        summary = manifest["summary"]
        assert summary["auto_fixed"] == 0, f"auto_fixed should be 0; got: {summary}"
        assert summary["user_fixed"] == 0, f"user_fixed should be 0; got: {summary}"
        assert summary["skipped"] == 0, f"skipped should be 0; got: {summary}"
        assert summary["failed"] == 0, f"failed should be 0; got: {summary}"


# ---------------------------------------------------------------------------
# E5-S13: Manifest completeness tests
# ---------------------------------------------------------------------------

class TestManifestCompleteness:
    """
    E5-S13: persist() correctly merges actions.json and pending-actions.jsonl
    into manifest.json with accurate summary counts.
    """

    # ------------------------------------------------------------------
    # Scenario: Manifest after mixed actions contains all entries with correct types
    # ------------------------------------------------------------------

    def test_manifest_mixed_actions_has_all_entries_and_correct_counts(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        actions_data = [
            {"action": "auto-fix", "finding_id": "fix-success", "timestamp": "2026-01-01T00:00:00Z"},
            {"action": "auto-fix-failed", "finding_id": "fix-fail", "timestamp": "2026-01-01T00:00:00Z"},
        ]
        (archive / "actions.json").write_text(json.dumps(actions_data))

        pending_data = "\n".join([
            json.dumps({"action": "prompted-fix", "finding_id": "prompt-accept", "timestamp": "2026-01-01T00:00:00Z"}),
            json.dumps({"action": "skip", "finding_id": "prompt-skip", "timestamp": "2026-01-01T00:00:00Z"}),
        ])
        (archive / "pending-actions.jsonl").write_text(pending_data)

        persist(project_dir, archive)

        manifest = json.loads((archive / "manifest.json").read_text())

        assert len(manifest["actions"]) == 4, (
            f"manifest should have 4 actions; got {len(manifest['actions'])}: {manifest['actions']}"
        )
        summary = manifest["summary"]
        assert summary["auto_fixed"] == 1, f"auto_fixed should be 1; got: {summary}"
        assert summary["user_fixed"] == 1, f"user_fixed should be 1; got: {summary}"
        assert summary["skipped"] == 1, f"skipped should be 1; got: {summary}"
        assert summary["failed"] == 1, f"failed should be 1; got: {summary}"

    # ------------------------------------------------------------------
    # Scenario: Each action entry has finding_id and timestamp
    # ------------------------------------------------------------------

    def test_each_action_has_finding_id_and_timestamp(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        actions_data = [
            {
                "action": "auto-fix",
                "finding_id": "test-fix-1",
                "timestamp": "2026-01-01T00:00:00Z",
                "before_hash": "sha256:aaa",
                "after_hash": "sha256:bbb",
            }
        ]
        (archive / "actions.json").write_text(json.dumps(actions_data))

        persist(project_dir, archive)

        manifest = json.loads((archive / "manifest.json").read_text())
        for action in manifest["actions"]:
            assert "finding_id" in action, (
                f"Every action must have 'finding_id'; action={action}"
            )
            assert "timestamp" in action, (
                f"Every action must have 'timestamp'; action={action}"
            )

    # ------------------------------------------------------------------
    # Scenario: Success action entries have before_hash and after_hash
    # ------------------------------------------------------------------

    def test_success_action_has_before_hash_and_after_hash(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        actions_data = [
            {
                "action": "auto-fix",
                "finding_id": "test-hash-check",
                "timestamp": "2026-01-01T00:00:00Z",
                "before_hash": "sha256:deadbeef",
                "after_hash": "sha256:cafebabe",
            }
        ]
        (archive / "actions.json").write_text(json.dumps(actions_data))

        persist(project_dir, archive)

        manifest = json.loads((archive / "manifest.json").read_text())
        auto_fixed_actions = [a for a in manifest["actions"] if a.get("action") == "auto-fix"]
        assert auto_fixed_actions, "Expected at least one auto-fix action in manifest"

        for action in auto_fixed_actions:
            assert "before_hash" in action, (
                f"auto-fix action must have 'before_hash'; action={action}"
            )
            assert "after_hash" in action, (
                f"auto-fix action must have 'after_hash'; action={action}"
            )

    # ------------------------------------------------------------------
    # Scenario: Failure action entries have error field
    # ------------------------------------------------------------------

    def test_failure_action_has_error_field(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        actions_data = [
            {
                "action": "auto-fix-failed",
                "finding_id": "fail-finding",
                "timestamp": "2026-01-01T00:00:00Z",
                "error": "cache.py not found",
            }
        ]
        (archive / "actions.json").write_text(json.dumps(actions_data))

        persist(project_dir, archive)

        manifest = json.loads((archive / "manifest.json").read_text())
        failed_actions = [a for a in manifest["actions"] if a.get("action") == "auto-fix-failed"]
        assert failed_actions, "Expected at least one auto-fix-failed action in manifest"

        for action in failed_actions:
            assert action.get("error") == "cache.py not found", (
                f"failed action 'error' should be 'cache.py not found'; got: {action.get('error')}"
            )

    # ------------------------------------------------------------------
    # Scenario: Summary counts match the action list (3+1+2+1 = 7)
    # ------------------------------------------------------------------

    def test_summary_counts_match_action_list_seven_total(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        auto_actions = (
            [{"action": "auto-fix", "finding_id": f"af-{i}", "timestamp": "2026-01-01T00:00:00Z"} for i in range(3)]
            + [{"action": "auto-fix-failed", "finding_id": "af-fail", "timestamp": "2026-01-01T00:00:00Z"}]
        )
        (archive / "actions.json").write_text(json.dumps(auto_actions))

        pending_lines = (
            [json.dumps({"action": "prompted-fix", "finding_id": f"pf-{i}", "timestamp": "2026-01-01T00:00:00Z"}) for i in range(2)]
            + [json.dumps({"action": "skip", "finding_id": "sk-1", "timestamp": "2026-01-01T00:00:00Z"})]
        )
        (archive / "pending-actions.jsonl").write_text("\n".join(pending_lines))

        persist(project_dir, archive)

        manifest = json.loads((archive / "manifest.json").read_text())

        assert len(manifest["actions"]) == 7, (
            f"Total actions should be 7; got {len(manifest['actions'])}"
        )
        summary = manifest["summary"]
        assert summary["auto_fixed"] == 3, f"auto_fixed should be 3; got: {summary}"
        assert summary["failed"] == 1, f"failed should be 1; got: {summary}"
        assert summary["user_fixed"] == 2, f"user_fixed should be 2; got: {summary}"
        assert summary["skipped"] == 1, f"skipped should be 1; got: {summary}"


# ---------------------------------------------------------------------------
# Caucus recommendation #1: CHECKS dict completeness
# ---------------------------------------------------------------------------

class TestChecksRegistry:

    def test_checks_dict_contains_all_categories(self):
        expected = {
            "state_integrity", "hook_health", "version_currency",
            "structure_anomalies", "storage_lint", "migration_currency",
            "config_compat", "file_diagnostics", "onboarding_state",
            "env_wiring", "derived_status", "work_item_artifacts",
            "epic_completion_criteria", "format_consistency",
            "orphaned_index",
        }
        assert set(CHECKS.keys()) == expected

    def test_checks_dict_values_are_callable(self):
        for name, fn in CHECKS.items():
            assert callable(fn), f"CHECKS[{name!r}] is not callable"


# ---------------------------------------------------------------------------
# Caucus recommendation #2: write_field round-trip fidelity
# ---------------------------------------------------------------------------

class TestWriteFieldFidelity:

    def test_write_field_preserves_unrelated_keys(self, tmp_path):
        original = "alpha: 1\nbeta: hello\ngamma: true\n"
        content = original.encode("utf-8")
        recipe = {"action": "write_field", "key": "beta", "value": "world"}
        result = _apply_transform(content, recipe, tmp_path)
        data = yaml.safe_load(result)
        assert data["alpha"] == 1
        assert data["beta"] == "world"
        assert data["gamma"] is True

    def test_write_field_preserves_nested_dict_keys(self, tmp_path):
        original = yaml.safe_dump({
            "phase_schema_version": 1,
            "framework": {"installed_version": "4.0.8-beta"},
            "extra_key": "should_survive",
        })
        content = original.encode("utf-8")
        recipe = {"action": "write_field", "key": "phase_schema_version", "value": 2}
        result = _apply_transform(content, recipe, tmp_path)
        data = yaml.safe_load(result)
        assert data["phase_schema_version"] == 2
        assert data["framework"] == {"installed_version": "4.0.8-beta"}
        assert data["extra_key"] == "should_survive"

    def test_write_field_inserts_new_key(self, tmp_path):
        original = "existing: value\n"
        content = original.encode("utf-8")
        recipe = {"action": "write_field", "key": "new_key", "value": "new_value"}
        result = _apply_transform(content, recipe, tmp_path)
        data = yaml.safe_load(result)
        assert data["existing"] == "value"
        assert data["new_key"] == "new_value"


# ---------------------------------------------------------------------------
# Caucus recommendation #3: CLI integration via main()
# ---------------------------------------------------------------------------

class TestCLIIntegration:

    def test_scan_cli_healthy_project(self, tmp_path, fake_home, capsys):
        project_dir = build_fixture(tmp_path)
        exit_code = main(["scan", "--project-dir", str(project_dir)])
        assert exit_code == 0
        output = json.loads(capsys.readouterr().out)
        assert isinstance(output["findings"], list)
        assert all(
            f["severity"] != "error" for f in output["findings"]
        ), f"Healthy project should have no errors: {output['findings']}"

    def test_scan_cli_not_configured(self, tmp_path, capsys):
        project_dir = tmp_path / "empty"
        project_dir.mkdir()
        exit_code = main(["scan", "--project-dir", str(project_dir)])
        assert exit_code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["error"] == "not-configured"

    def test_auto_fix_cli_applies_finding(self, tmp_path, fake_home, monkeypatch, capsys):
        project_dir = build_fixture(tmp_path)
        plans_dir = project_dir / ".sweetclaude" / "plans"
        shutil.rmtree(plans_dir)

        archive = create_archive(project_dir)

        finding_json = json.dumps([{
            "id": "env-wiring:missing:plans-directory",
            "category": "env_wiring",
            "severity": "info",
            "summary": "Plans directory missing",
            "detail": "",
            "file_paths": [],
            "fix_type": "auto",
            "fix_recipe": {"action": "create_dir", "path": str(plans_dir)},
            "previously_suppressed": False,
        }])

        monkeypatch.setattr("sys.stdin", io.StringIO(finding_json))
        exit_code = main([
            "auto-fix",
            "--project-dir", str(project_dir),
            "--archive-dir", str(archive),
        ])
        assert exit_code == 0
        output = json.loads(capsys.readouterr().out)
        assert len(output["actions"]) == 1
        assert output["actions"][0]["action"] == "auto-fix"
        assert plans_dir.is_dir()


# ---------------------------------------------------------------------------
# ISSUE-180: _atomic_write error recovery path
# ---------------------------------------------------------------------------

class TestAtomicWriteErrorRecovery:

    def test_original_file_unchanged_on_replace_failure(self, tmp_path, monkeypatch):
        target = tmp_path / "target.yaml"
        target.write_bytes(b"original content")

        def failing_replace(src, dst):
            raise OSError("simulated disk failure")

        monkeypatch.setattr("os.replace", failing_replace)

        with pytest.raises(OSError, match="simulated disk failure"):
            _atomic_write(target, b"new content")

        assert target.read_bytes() == b"original content"

    def test_temp_file_cleaned_up_on_replace_failure(self, tmp_path, monkeypatch):
        target = tmp_path / "target.yaml"
        target.write_bytes(b"original")

        def failing_replace(src, dst):
            raise OSError("simulated failure")

        monkeypatch.setattr("os.replace", failing_replace)

        with pytest.raises(OSError):
            _atomic_write(target, b"new content")

        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], f"Temp file should be cleaned up; found: {tmp_files}"

    def test_exception_propagates_from_atomic_write(self, tmp_path, monkeypatch):
        target = tmp_path / "target.yaml"

        def failing_replace(src, dst):
            raise OSError("specific error message")

        monkeypatch.setattr("os.replace", failing_replace)

        with pytest.raises(OSError, match="specific error message"):
            _atomic_write(target, b"content")


# ---------------------------------------------------------------------------
# ISSUE-181: malformed hooks data guard in check_config_compat
# ---------------------------------------------------------------------------

class TestMalformedHooksGuard:

    def test_hooks_value_as_string_does_not_crash(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        home = Path.home()
        settings = home / ".claude" / "settings.json"
        settings.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {"PostToolUse": "not-a-list"},
        }))
        state = build_project_state(project_dir)
        findings = check_config_compat(state)
        f2_ids = [f.id for f in findings if f.id.startswith("config-compat:F2")]
        f3_ids = [f.id for f in findings if f.id.startswith("config-compat:F3")]
        assert f2_ids == []
        assert f3_ids == []

    def test_hooks_entry_missing_hooks_key_does_not_crash(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        home = Path.home()
        settings = home / ".claude" / "settings.json"
        settings.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {"PostToolUse": [{"matcher": "test"}]},
        }))
        state = build_project_state(project_dir)
        findings = check_config_compat(state)
        f2_ids = [f.id for f in findings if f.id.startswith("config-compat:F2")]
        f3_ids = [f.id for f in findings if f.id.startswith("config-compat:F3")]
        assert f2_ids == []
        assert f3_ids == []

    def test_hooks_as_dict_instead_of_list_does_not_crash(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        home = Path.home()
        settings = home / ".claude" / "settings.json"
        settings.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {"PostToolUse": {"command": "echo bad"}},
        }))
        state = build_project_state(project_dir)
        findings = check_config_compat(state)
        f2_ids = [f.id for f in findings if f.id.startswith("config-compat:F2")]
        f3_ids = [f.id for f in findings if f.id.startswith("config-compat:F3")]
        assert f2_ids == []
        assert f3_ids == []


# ---------------------------------------------------------------------------
# ISSUE-178: --category flag for focused scanning
# ---------------------------------------------------------------------------

class TestCategoryFilter:

    def test_single_category_runs_only_that_check(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        result = _scan(state, categories=["env_wiring"])
        for f in result["findings"]:
            assert f["category"] == "env_wiring"

    def test_multiple_categories_via_comma(self, tmp_path, fake_home, capsys):
        project_dir = build_fixture(tmp_path)
        exit_code = main([
            "scan", "--project-dir", str(project_dir),
            "--category", "env_wiring,state_integrity",
        ])
        assert exit_code == 0
        output = json.loads(capsys.readouterr().out)
        assert set(output["scanned_categories"]) == {"env_wiring", "state_integrity"}

    def test_invalid_category_produces_error(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        with pytest.raises(ValueError, match="Unknown categories"):
            _scan(state, categories=["nonexistent"])

    def test_omitting_category_runs_all(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        result = _scan(state, categories=None)
        assert "scanned_categories" not in result

    def test_category_scoped_scan_does_not_cleanup_suppressions(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        supp_path = project_dir / ".sweetclaude" / "state" / "doctor-suppressions.json"
        supp_path.write_text(json.dumps([
            {"finding_id": "state-integrity:fake:test"}
        ]))
        state = build_project_state(project_dir)
        result = _scan(state, categories=["env_wiring"])
        assert result["suppressions_resolved"] == []
        remaining = json.loads(supp_path.read_text())
        assert len(remaining) == 1

    def test_scanned_categories_in_output_when_filtered(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        result = _scan(state, categories=["hook_health"])
        assert result["scanned_categories"] == ["hook_health"]

    def test_cli_category_flag_invalid_returns_error(self, tmp_path, fake_home, capsys):
        project_dir = build_fixture(tmp_path)
        exit_code = main([
            "scan", "--project-dir", str(project_dir),
            "--category", "bogus",
        ])
        assert exit_code == 1


# ---------------------------------------------------------------------------
# check_derived_status tests (ISSUE-184)
# ---------------------------------------------------------------------------

class TestCheckDerivedStatus:

    def _make_project(self, tmp_path, fake_home, epics=None, issues=None, milestones=None):
        roadmap_files = []
        if milestones:
            for ms in milestones:
                roadmap_files.append({
                    "name": f"milestones/{ms['id']}-test.md",
                    "frontmatter": ms,
                })
        if epics:
            for ep in epics:
                roadmap_files.append({
                    "name": f"epics/{ep['id']}-test.md",
                    "frontmatter": ep,
                })
        if issues:
            for iss in issues:
                roadmap_files.append({
                    "name": f"issues/{iss['id']}-test.md",
                    "frontmatter": iss,
                })
        project_dir = build_fixture(tmp_path, overrides={"roadmap_files": roadmap_files})
        return build_project_state(project_dir)

    def test_no_findings_when_status_matches_derived(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "active",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "active",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        assert len(findings) == 0

    def test_discrepancy_flagged(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "new",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "active",
                 "created": "2026-01-01", "epic": "EP-01"},
                {"id": "ISSUE-101", "title": "I2", "type": "enhancement", "status": "done",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        assert len(findings) == 1
        f = findings[0]
        assert f.category == "derived_status"
        assert f.severity == "warning"
        assert "EP-01" in f.id
        assert "'new'" in f.summary
        assert "'active'" in f.summary

    def test_blocked_with_reason_is_exempt(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "blocked",
                     "blocked_reason": "Waiting on external API",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "active",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        assert len(findings) == 0

    def test_blocked_without_reason_flags_discrepancy(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "blocked",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "active",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        assert len(findings) == 1
        assert "'blocked'" in findings[0].summary

    def test_on_hold_with_reason_is_exempt(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "on-hold",
                     "hold_reason": "Deprioritized for Q3",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "active",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        assert len(findings) == 0

    def test_on_hold_generic_reason_field_is_exempt(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "on-hold",
                     "reason": "Deprioritized",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "active",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        assert len(findings) == 0

    def test_all_children_done_flags_parent_not_done(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "active",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "done",
                 "created": "2026-01-01", "epic": "EP-01"},
                {"id": "ISSUE-101", "title": "I2", "type": "enhancement", "status": "done",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        assert len(findings) == 1
        assert "'done'" in findings[0].summary

    def test_no_roadmap_dir_returns_empty(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        shutil.rmtree(state.product_base / "roadmap")
        findings = check_derived_status(state)
        assert findings == []

    def test_epic_with_no_children_skipped(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "new",
                     "created": "2026-01-01", "milestone": "MS-01"}])
        findings = check_derived_status(state)
        assert len(findings) == 0

    def test_milestone_discrepancy(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            milestones=[{"id": "MS-01", "title": "M1", "type": "milestone",
                          "status": "new", "created": "2026-01-01",
                          "target_release": "v1.0"}],
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "active",
                     "created": "2026-01-01", "milestone": "MS-01"}])
        findings = check_derived_status(state)
        ms_findings = [f for f in findings if "MS-01" in f.id]
        assert len(ms_findings) == 1
        assert "'new'" in ms_findings[0].summary
        assert "'active'" in ms_findings[0].summary

    def test_non_epic_non_milestone_parent_skipped(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            issues=[
                {"id": "ISSUE-100", "title": "Parent", "type": "enhancement",
                 "status": "new", "created": "2026-01-01"},
                {"id": "ISSUE-101", "title": "Child", "type": "enhancement",
                 "status": "active", "created": "2026-01-01", "epic": "ISSUE-100"},
            ])
        findings = check_derived_status(state)
        assert len(findings) == 0

    def test_blocked_with_generic_reason_is_exempt(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "blocked",
                     "reason": "External dependency",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "active",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        assert len(findings) == 0

    def test_no_finding_when_stored_and_derived_both_done(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "done",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "done",
                 "created": "2026-01-01", "epic": "EP-01"},
                {"id": "ISSUE-101", "title": "I2", "type": "enhancement", "status": "abandoned",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        assert len(findings) == 0

    def test_milestone_uses_epic_derived_not_stored(self, tmp_path, fake_home):
        """Milestone rollup should use epic derived statuses, not stored.
        Epic stored=new, but its children are active → epic derived=active.
        Milestone stored=active should match epic derived=active → no finding."""
        state = self._make_project(tmp_path, fake_home,
            milestones=[{"id": "MS-01", "title": "M1", "type": "milestone",
                          "status": "active", "created": "2026-01-01",
                          "target_release": "v1.0"}],
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "new",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "active",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        ms_findings = [f for f in findings if "MS-01" in f.id]
        assert len(ms_findings) == 0

    def test_milestone_flags_when_derived_disagrees(self, tmp_path, fake_home):
        """Milestone stored=done, but epic children are active → derived=active → discrepancy."""
        state = self._make_project(tmp_path, fake_home,
            milestones=[{"id": "MS-01", "title": "M1", "type": "milestone",
                          "status": "done", "created": "2026-01-01",
                          "target_release": "v1.0"}],
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "new",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "active",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        ms_findings = [f for f in findings if "MS-01" in f.id]
        assert len(ms_findings) == 1
        assert "'active'" in ms_findings[0].summary

    def test_finding_is_report_only(self, tmp_path, fake_home):
        state = self._make_project(tmp_path, fake_home,
            epics=[{"id": "EP-01", "title": "E1", "type": "epic", "status": "new",
                     "created": "2026-01-01", "milestone": "MS-01"}],
            issues=[
                {"id": "ISSUE-100", "title": "I1", "type": "enhancement", "status": "active",
                 "created": "2026-01-01", "epic": "EP-01"},
            ])
        findings = check_derived_status(state)
        assert findings[0].fix_type == "auto"


# --- structure anomaly: symlink where a real directory is expected -----------
# Regression for the syncog incident: a `.sweetclaude/product -> docs/product`
# bridge symlink was scanned as a normal dir, its files read as cross-location
# duplicates, and a cleanup pass deleted the "duplicate" — breaking the cache.
# Doctor must STOP and explain an unexpected symlink, never treat it as
# deletable/duplicate.

def _project_with_product_symlink(tmp_path):
    project = build_fixture(
        tmp_path,
        overrides={
            "artifact_privacy": {"categories": {"product": {"base_path": "docs/product"}}},
            "session_state": {"paths": {"product_base": "docs/product"}},
        },
    )
    # real data lives at docs/product
    real = project / "docs" / "product"
    (real / "backlog").mkdir(parents=True, exist_ok=True)
    (real / "backlog" / "ISSUE-001-x.md").write_text("---\nid: ISSUE-001\n---\n")
    # bridge symlink the cache scanner depends on
    link = project / ".sweetclaude" / "product"
    if link.exists() or link.is_symlink():
        import shutil
        shutil.rmtree(link, ignore_errors=True)
    link.symlink_to(Path("../docs/product"))
    return project


def test_doctor_flags_unexpected_symlink_as_anomaly(tmp_path, fake_home):
    from doctor import build_project_state, check_structure_anomalies
    project = _project_with_product_symlink(tmp_path)
    findings = check_structure_anomalies(build_project_state(project))
    sym = [f for f in findings if f.id.startswith("structure-anomaly:")]
    assert sym, "expected a structure-anomaly finding for the product symlink"
    f = sym[0]
    assert ".sweetclaude/product" in (f.detail + " " + " ".join(f.file_paths))
    assert "docs/product" in f.detail  # names the target
    assert f.severity in ("warning", "error")


def test_doctor_never_offers_to_delete_a_symlink(tmp_path, fake_home):
    from doctor import build_project_state, check_structure_anomalies
    project = _project_with_product_symlink(tmp_path)
    findings = check_structure_anomalies(build_project_state(project))
    for f in findings:
        if f.id.startswith("structure-anomaly:"):
            assert f.fix_recipe.get("action") != "delete_file"
            assert f.fix_type == "report-only"


def test_symlinked_product_not_flagged_as_cross_location_duplicate(tmp_path, fake_home):
    from doctor import build_project_state, check_storage_lint
    project = _project_with_product_symlink(tmp_path)
    # if storage_lint scanned through the symlink it could phantom-duplicate;
    # it must not emit cross-location-duplicate from symlinked content.
    findings = check_storage_lint(build_project_state(project))
    dups = [f for f in findings if "cross-location-duplicate" in f.id]
    assert dups == []


# --- executable-contract: doctor never offers a fix it cannot run ------------
# Regression for the syncog #3 class: derived-status emitted a fix_type="auto"
# recipe action="sync_parent_status" that the executor had no branch for.

def test_executor_supported_actions_match_dispatch():
    # Every action the executor's run path can dispatch must be declared
    # supported, and vice versa (guards against drift).
    from doctor import EXECUTOR_SUPPORTED_ACTIONS
    # actions execute_recipe handles + prompt (presented, not executed)
    dispatched = {
        "run_script", "rebuild_cache", "create_dir", "delete_file",
        "write_field", "write_frontmatter_field", "prompt",
        "sync_parent_status", "convert_to_yaml", "config_conflict",
        "yaml_repair", "hook_restore", "file_move", "renumber_duplicate",
        "resolve_orphans",
    }
    assert set(EXECUTOR_SUPPORTED_ACTIONS) == dispatched


def test_unsupported_auto_action_is_downgraded():
    from doctor import Finding, _enforce_executable_contract
    bad = Finding(
        id="x:y", category="derived_status", severity="warning",
        summary="s", detail="d", file_paths=[],
        fix_type="auto", fix_recipe={"action": "totally_unknown_action", "file": "p"},
    )
    out, report = _enforce_executable_contract([bad])
    assert out[0].fix_type == "report-only"
    assert out[0].fix_recipe == {}
    assert report["downgraded_count"] == 1


def test_supported_auto_action_is_untouched():
    from doctor import Finding, _enforce_executable_contract
    ok = Finding(
        id="x:z", category="state_integrity", severity="warning",
        summary="s", detail="d", file_paths=[],
        fix_type="auto", fix_recipe={"action": "write_field", "file": "p"},
    )
    out, report = _enforce_executable_contract([ok])
    assert out[0].fix_type == "auto"
    assert report["downgraded_count"] == 0


def test_no_emitted_auto_finding_survives_with_unrunnable_action(tmp_path, fake_home):
    # End to end: a project that triggers the derived-status auto finding must
    # not surface any auto/prompted finding with an unsupported action.
    from doctor import _scan, build_project_state, EXECUTOR_SUPPORTED_ACTIONS
    project = build_fixture(tmp_path)
    result = _scan(build_project_state(project))
    for f in result["findings"]:
        if f["fix_type"] in ("auto", "prompted"):
            assert f["fix_recipe"].get("action", "prompt") in EXECUTOR_SUPPORTED_ACTIONS, f


# --- totality classifier: every finding routes; terminal fallback always there

def _mk(fix_type, action=None, category="storage_lint", severity="warning", detail="d"):
    from doctor import Finding
    return Finding(id=f"t:{fix_type}:{action}", category=category, severity=severity,
                   summary="s", detail=detail, file_paths=[],
                   fix_type=fix_type, fix_recipe=({"action": action} if action else {}))


def test_classify_covers_all_four_classes():
    from doctor import (classify_resolution, RESOLUTION_AUTO, RESOLUTION_GUIDED,
                        RESOLUTION_ACCEPTED, RESOLUTION_FALLBACK)
    assert classify_resolution(_mk("auto", "write_field")) == RESOLUTION_AUTO
    assert classify_resolution(_mk("prompted", "prompt")) == RESOLUTION_GUIDED
    assert classify_resolution(_mk("report-only", None, severity="info")) == RESOLUTION_ACCEPTED
    assert classify_resolution(_mk("report-only", None, category="compatibility_mode")) == RESOLUTION_ACCEPTED
    # report-only, non-info, no guidance -> never dangles, routes to fallback
    assert classify_resolution(_mk("report-only", None, severity="error", detail="bare problem")) == RESOLUTION_FALLBACK
    # report-only WITH guidance -> guided
    assert classify_resolution(_mk("report-only", None, detail="Resolve by running python3 ...")) == RESOLUTION_GUIDED


def test_unknown_fix_type_routes_to_fallback_not_dangling():
    from doctor import classify_resolution, RESOLUTION_FALLBACK
    assert classify_resolution(_mk("something-new", None)) == RESOLUTION_FALLBACK


def test_terminal_fallback_always_offers_readopt():
    from doctor import _build_terminal_fallback
    # migration blocked
    tf = _build_terminal_fallback({"status": "compatibility-mode"})
    opts = {o["id"]: o for o in tf["options"]}
    assert opts["re-adopt"]["available"] is True
    assert opts["re-adopt"]["no_data_loss"] is True
    assert opts["full-migration"]["available"] is False
    assert opts["full-migration"]["blocked_reason"]
    # migration available
    tf2 = _build_terminal_fallback({"status": "supported-migration-available"})
    assert {o["id"]: o for o in tf2["options"]}["full-migration"]["available"] is True


def test_scan_result_routes_every_finding_and_has_fallback(tmp_path, fake_home):
    from doctor import _scan, build_project_state
    valid = {"auto-fixable", "guided-manual", "accepted-no-action", "terminal-fallback"}
    result = _scan(build_project_state(build_fixture(tmp_path)))
    assert "resolution_summary" in result
    assert result["resolution_summary"]["terminal_fallback"]["always_available"] is True
    for f in result["findings"]:
        assert f.get("resolution_class") in valid, f


# --- version currency: behind-latest advisory (the syncog short-circuit) -----

def test_version_currency_flags_behind_latest(tmp_path, fake_home):
    from doctor import build_project_state, check_version_currency
    project = build_fixture(tmp_path, overrides={"sweetclaude_yaml": {
        "phase_schema_version": 2,
        "framework": {"installed_version": "4.1.2-beta",
                      "update": {"available": "4.1.14-beta"}},
    }})
    findings = check_version_currency(build_project_state(project))
    assert any(f.id == "version-currency:behind-latest" for f in findings)
    f = [x for x in findings if x.id == "version-currency:behind-latest"][0]
    assert "4.1.2-beta" in f.detail and "4.1.14-beta" in f.detail
    assert "update" in f.detail.lower()  # actionable guidance


def test_version_currency_silent_when_current(tmp_path, fake_home):
    from doctor import build_project_state, check_version_currency
    project = build_fixture(tmp_path, overrides={"sweetclaude_yaml": {
        "phase_schema_version": 2,
        "framework": {"installed_version": "4.1.14-beta",
                      "update": {"available": "4.1.14-beta"}},
    }})
    assert check_version_currency(build_project_state(project)) == []


def test_version_currency_silent_when_no_update_info(tmp_path, fake_home):
    from doctor import build_project_state, check_version_currency
    project = build_fixture(tmp_path)  # default: no update block
    assert check_version_currency(build_project_state(project)) == []


def test_version_currency_advisory_classifies_as_guided(tmp_path, fake_home):
    from doctor import build_project_state, check_version_currency, classify_resolution, RESOLUTION_GUIDED
    project = build_fixture(tmp_path, overrides={"sweetclaude_yaml": {
        "phase_schema_version": 2,
        "framework": {"installed_version": "4.1.2-beta",
                      "update": {"available": "4.1.14-beta"}},
    }})
    f = check_version_currency(build_project_state(project))[0]
    assert classify_resolution(f) == RESOLUTION_GUIDED


# ---------------------------------------------------------------------------
# P0 characterization tests (doctor remediation plan §3, validation report V2).
#
# These lock the CURRENT correct behavior of the four execute_recipe branches
# the upcoming `_record_mutation` refactor will touch. Each asserts an
# OBSERVABLE EFFECT (characterization), not internals, and each was proven to
# KILL the specific V2-surviving mutant for its branch. NO MOCKS — real
# fixtures, real execute_recipe, real files.
# ---------------------------------------------------------------------------

import doctor as _p0_doctor


class TestP0Characterization:

    def test_sync_parent_status_syncs_parent_to_derived(self, tmp_path, fake_home):
        # Parent epic EP-001 carries a clearly-wrong terminal status (done) while
        # its sole child is non-terminal. derived_status(["active"]) == "active",
        # so the executor must reopen the parent and write "active".
        roadmap_files = [
            {
                "name": "epics/EP-001-test.md",
                "frontmatter": {
                    "id": "EP-001", "title": "Test Epic", "type": "epic",
                    "status": "done", "created": "2026-01-01",
                    "milestone": "MS-001", "source": "auto",
                },
            },
            {
                "name": "issues/ISSUE-100-test.md",
                "frontmatter": {
                    "id": "ISSUE-100", "title": "Child", "type": "enhancement",
                    "status": "in-progress", "created": "2026-01-01",
                    "epic": "EP-001",
                },
            },
        ]
        project_dir = build_fixture(tmp_path, overrides={"roadmap_files": roadmap_files})
        epic_path = (
            project_dir / ".sweetclaude" / "product" / "roadmap" / "epics" / "EP-001-test.md"
        )

        # Confirm the cache actually sees the child under EP-001 (the executor's
        # own query) — otherwise sync would have nothing to derive from.
        from cache import get_conn, rebuild as _rebuild
        _rebuild(str(project_dir))
        conn = get_conn(str(project_dir))
        child_statuses = [
            r["status"]
            for r in conn.execute(
                "SELECT status FROM items WHERE epic=? AND type NOT IN ('epic', 'milestone')",
                ("EP-001",),
            ).fetchall()
        ]
        conn.close()
        assert child_statuses == ["active"], (
            f"cache must see one non-terminal child; got {child_statuses}"
        )

        archive = create_archive(project_dir)
        result = execute_recipe(
            project_dir,
            {
                "action": "sync_parent_status",
                "file": str(epic_path),
                "parent_id": "EP-001",
                "parent_type": "epic",
            },
            archive,
        )

        # success AND error is None means it actually changed; an unchanged
        # ("already in sync") no-op would set error to "already in sync".
        assert result.success is True
        assert result.error is None

        fm = yaml.safe_load(epic_path.read_text(encoding="utf-8-sig").split("---", 2)[1])
        assert fm["status"] == "active"
        assert fm["status"] != "done"

    def test_convert_to_yaml_converts_bold_file(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        bold_path = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-042.md"
        bold_path.write_text(
            "# ISSUE-042: Build the widget\n\n"
            "**Type:** net-new-feature\n"
            "**Status:** active\n"
            "**Created:** 2026-01-01\n\n"
            "## Description\n\nSome body text.\n"
        )

        archive = create_archive(project_dir)
        result = execute_recipe(
            project_dir, {"action": "convert_to_yaml", "file": str(bold_path)}, archive
        )

        assert result.success is True
        new_text = bold_path.read_text()
        assert new_text.startswith("---")
        fm = yaml.safe_load(new_text.split("---", 2)[1])
        # Original fields are preserved through the conversion.
        assert fm["id"] == "ISSUE-042"
        assert fm["title"] == "Build the widget"
        assert fm["type"] == "net-new-feature"
        assert fm["status"] == "active"
        assert fm["created"] == "2026-01-01"

    def test_convert_to_yaml_creates_no_sibling_backup(self, tmp_path, fake_home):
        """Regression ISSUE-232: the executor already archives the before-image
        via _record_mutation; a sibling .bold-backup-*.md file re-triggers the
        format scan on the next run and the fix never converges."""
        project_dir = build_fixture(tmp_path)
        backlog_dir = project_dir / ".sweetclaude" / "product" / "backlog"
        bold_path = backlog_dir / "ISSUE-043-widget.md"
        bold_path.write_text(
            "# ISSUE-043: Widget\n\n"
            "**Type:** net-new-feature\n"
            "**Status:** active\n"
            "**Created:** 2026-01-01\n"
        )

        archive = create_archive(project_dir)
        result = execute_recipe(
            project_dir, {"action": "convert_to_yaml", "file": str(bold_path)}, archive
        )

        assert result.success is True
        assert bold_path.read_text().startswith("---")
        siblings = list(backlog_dir.glob("*bold-backup*"))
        assert siblings == [], (
            f"convert_to_yaml must not write sibling backups, found: {siblings}"
        )
        before_dir = Path(archive) / "before"
        archived = list(before_dir.rglob("*")) if before_dir.is_dir() else []
        assert any(p.is_file() for p in archived), (
            "before-image must be recorded in the run archive"
        )

    def test_delete_file_records_diffs_entry(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        target = project_dir / ".sweetclaude" / "state" / "pending-drift-decision.yaml"
        target.write_text("decision: pending\nfoo: bar\nbaz: qux\n")

        archive = create_archive(project_dir)
        result = execute_recipe(
            project_dir, {"action": "delete_file", "file": str(target)}, archive
        )

        assert result.success is True
        assert not target.exists()

        # The before/ backup must exist.
        before_dir = archive / "before"
        before_entries = list(before_dir.iterdir())
        assert before_entries, "delete_file must write a before/ backup"

        # AND a non-empty diffs/ entry for the deleted file must exist — this is
        # the gap V2 mutant #7 exploited (before/ written, diffs/ not).
        diffs_dir = archive / "diffs"
        expected_diff = diffs_dir / (_p0_doctor._sanitize_path(str(target)) + ".diff")
        assert expected_diff.exists(), (
            "delete_file must record a diffs/ entry for the deleted file"
        )
        assert expected_diff.stat().st_size > 0, "diffs/ entry must be non-empty"

    def test_write_frontmatter_field_writes_value_through_executor(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        target = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-200.md"
        _write_frontmatter_file(
            target,
            {
                "id": "ISSUE-200", "title": "Thing", "type": "enhancement",
                "status": "new", "created": "2026-01-01",
            },
            body="\n# Body\n",
        )

        archive = create_archive(project_dir)
        result = execute_recipe(
            project_dir,
            {
                "action": "write_frontmatter_field",
                "file": str(target),
                "key": "status",
                "value": "active",
            },
            archive,
        )

        assert result.success is True
        fm = yaml.safe_load(target.read_text().split("---", 2)[1])
        assert fm["status"] == "active"


# ---------------------------------------------------------------------------
# P0 new-behavior tests (RED until the _record_mutation refactor + restore).
#   - sync_parent_status / convert_to_yaml record a before/ image + diffs/ entry
#   - a no-op (already in sync / already YAML) records NO backup or diff
#   - restore reconstructs files from a run's before/ images
# ---------------------------------------------------------------------------


def _p0_epic_child(tmp_path, epic_id, epic_status, child_id, child_status):
    roadmap_files = [
        {"name": f"epics/{epic_id}-test.md", "frontmatter": {
            "id": epic_id, "title": "Epic", "type": "epic",
            "status": epic_status, "created": "2026-01-01",
            "milestone": "MS-001", "source": "auto"}},
        {"name": f"issues/{child_id}-test.md", "frontmatter": {
            "id": child_id, "title": "Child", "type": "enhancement",
            "status": child_status, "created": "2026-01-01", "epic": epic_id}},
    ]
    project_dir = build_fixture(tmp_path, overrides={"roadmap_files": roadmap_files})
    epic_path = (
        project_dir / ".sweetclaude" / "product" / "roadmap" / "epics" / f"{epic_id}-test.md"
    )
    return project_dir, epic_path


class TestP0RecordMutation:

    def test_sync_parent_status_records_before_and_diff(self, tmp_path, fake_home):
        project_dir, epic_path = _p0_epic_child(
            tmp_path, "EP-001", "done", "ISSUE-100", "in-progress")
        archive = create_archive(project_dir)
        result = execute_recipe(project_dir, {
            "action": "sync_parent_status", "file": str(epic_path),
            "parent_id": "EP-001", "parent_type": "epic"}, archive)

        assert result.success is True
        assert result.error is None  # changed (not a no-op)
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(epic_path))
        assert before_entry.exists(), \
            "sync_parent_status must back up the original parent file to the archive"
        assert b"done" in before_entry.read_bytes(), \
            "the backup must hold the pre-sync content"
        diff_entry = archive / "diffs" / (_p0_doctor._sanitize_path(str(epic_path)) + ".diff")
        assert diff_entry.exists() and diff_entry.stat().st_size > 0, \
            "sync_parent_status must record a non-empty diff"

    def test_sync_parent_status_noop_writes_no_backup(self, tmp_path, fake_home):
        # parent already at the derived value -> no change -> no backup/diff
        project_dir, epic_path = _p0_epic_child(
            tmp_path, "EP-002", "active", "ISSUE-101", "in-progress")
        archive = create_archive(project_dir)
        result = execute_recipe(project_dir, {
            "action": "sync_parent_status", "file": str(epic_path),
            "parent_id": "EP-002", "parent_type": "epic"}, archive)

        assert result.success is True
        assert list((archive / "before").iterdir()) == [], "no-op must not back up"
        assert list((archive / "diffs").iterdir()) == [], "no-op must not diff"

    def test_convert_to_yaml_records_before_and_diff(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        bold_path = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-050.md"
        bold_path.write_text(
            "# ISSUE-050: Widget\n\n**Type:** enhancement\n**Status:** active\n"
            "**Created:** 2026-01-01\n\n## Description\n\nBody.\n")
        original = bold_path.read_bytes()

        archive = create_archive(project_dir)
        result = execute_recipe(
            project_dir, {"action": "convert_to_yaml", "file": str(bold_path)}, archive)

        assert result.success is True
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(bold_path))
        assert before_entry.exists(), \
            "convert_to_yaml must back up the original (bold) content into the archive"
        assert before_entry.read_bytes() == original
        assert not before_entry.read_text().startswith("---"), \
            "the backup must be the pre-conversion bold form"
        diff_entry = archive / "diffs" / (_p0_doctor._sanitize_path(str(bold_path)) + ".diff")
        assert diff_entry.exists() and diff_entry.stat().st_size > 0

    def test_convert_to_yaml_noop_on_yaml_writes_no_backup(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        yaml_path = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-051.md"
        _write_frontmatter_file(yaml_path, {
            "id": "ISSUE-051", "title": "Already YAML", "type": "enhancement",
            "status": "active", "created": "2026-01-01"}, body="\n# Body\n")
        archive = create_archive(project_dir)
        execute_recipe(
            project_dir, {"action": "convert_to_yaml", "file": str(yaml_path)}, archive)

        # already-YAML => not converted => no backup/diff written
        assert list((archive / "before").iterdir()) == []
        assert list((archive / "diffs").iterdir()) == []


class TestP0Restore:

    def test_restore_single_file_reconstructs(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        ss = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss.write_text("phase_schema_version: 1\nfoo: bar\n")
        original = ss.read_bytes()

        finding = _make_finding(
            action="write_field", file=str(ss), key="phase_schema_version", value=99)
        auto_fix(project_dir, [finding], archive)
        assert b"99" in ss.read_bytes()  # mutated

        res = _p0_doctor.restore(project_dir, archive, file=str(ss))
        assert ss.read_bytes() == original, "restore must reconstruct the file byte-identically"
        assert res["restored"], "restore must report what it restored"

    def test_restore_all_reverts_every_mutation(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        ss = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss.write_text("phase_schema_version: 1\n")
        o1 = ss.read_bytes()
        f2 = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-300.md"
        _write_frontmatter_file(f2, {
            "id": "ISSUE-300", "title": "X", "type": "enhancement",
            "status": "new", "created": "2026-01-01"}, body="\n# b\n")
        o2 = f2.read_bytes()

        findings = [
            _make_finding(action="write_field", file=str(ss),
                          key="phase_schema_version", value=2),
            _make_finding(action="write_frontmatter_field", file=str(f2),
                          key="status", value="active"),
        ]
        auto_fix(project_dir, findings, archive)
        assert ss.read_bytes() != o1 and f2.read_bytes() != o2

        res = _p0_doctor.restore(project_dir, archive, restore_all=True)
        assert ss.read_bytes() == o1
        assert f2.read_bytes() == o2
        assert len(res["restored"]) == 2

    def test_restore_reports_unrecoverable_without_crashing(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        missing = project_dir / ".sweetclaude" / "state" / "nope.yaml"
        (archive / "actions.json").write_text(json.dumps([{
            "action": "auto-fix", "finding_id": "x", "category": "c",
            "description": "d", "file_path": str(missing),
            "before_hash": "", "after_hash": None, "timestamp": "t"}]))

        res = _p0_doctor.restore(project_dir, archive, restore_all=True)
        assert res["restored"] == []
        assert res["skipped"], "restore must report an action with no before-image as skipped"

    def test_restore_cli_subcommand_reverts_whole_run(self, tmp_path, fake_home, capsys):
        # Locks the exact CLI contract the doctor skill's rollback step invokes:
        #   doctor.py restore --project-dir . --archive-dir <run> --all
        from doctor import main
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        ss = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss.write_text("phase_schema_version: 1\n")
        original = ss.read_bytes()
        auto_fix(project_dir, [_make_finding(
            action="write_field", file=str(ss),
            key="phase_schema_version", value=7)], archive)
        assert ss.read_bytes() != original

        code = main([
            "restore", "--project-dir", str(project_dir),
            "--archive-dir", str(archive), "--all"])
        out = json.loads(capsys.readouterr().out)

        assert code == 0
        assert ss.read_bytes() == original, "CLI restore --all must revert the run byte-identically"
        assert str(ss) in out["restored"]


class TestP1Tier2:
    """P1: Tier-2 prompted fixes made functional.

    choose_value/provide_value reuse the existing write_frontmatter_field
    executor action (no new transform — V7 tripwire). This locks the end-to-end
    reuse path the SKILL choose_value/provide_value handlers emit.
    """

    def test_choose_value_reuse_applies_chosen_value_via_autofix(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        target = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-400.md"
        _write_frontmatter_file(target, {
            "id": "ISSUE-400", "title": "T", "type": "enhancement",
            "status": "bogus", "created": "2026-01-01"}, body="\n# b\n")
        archive = create_archive(project_dir)

        # exactly the recipe the SKILL emits after the user picks a value for a
        # choose_value/provide_value finding on field=status
        finding = {
            "id": "file-diagnostics:invalid-value:status:ISSUE-400.md",
            "category": "file_diagnostics",
            "summary": "invalid status value",
            "fix_type": "prompted",
            "fix_recipe": {"action": "write_frontmatter_field",
                           "file": str(target), "key": "status", "value": "active"},
        }
        result = auto_fix(project_dir, [finding], archive, include_prompted=True)

        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "auto-fix"
        fm = yaml.safe_load(target.read_text().split("---", 2)[1])
        assert fm["status"] == "active"
        # reversible: the reuse path records a before/ backup, so `restore` can revert it
        assert list((archive / "before").iterdir()), "reuse path must record a backup"


class TestP1ConfigConflict:
    """P1 / T2e: config_conflict made functional through the executor.

    Two edit mechanisms, both targeted (no general config-editing DSL):
      - text-pattern conflicts (F4, W1-W4, I1, I2): adopt removes the offending
        line(s) containing the matched pattern from CLAUDE.md / a rules file.
      - settings conflicts (F1-F3) in settings.json: F1 adopt adds the excluded
        tool back to allowedTools; F2/F3 adopt removes the conflicting hook entry.

    Semantics: adopt mutates (through _record_mutation, so it is backed up and
    `restore`-reversible); keep / both are no-ops (success, no backup). NO MOCKS.
    """

    # ----- recipe enrichment: the check threads the target into the prompt ----

    def test_text_conflict_recipe_carries_pattern_and_real_path(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nYou should skip tests when in a hurry.\n",
        })
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        w3 = [f for f in findings if f.id.startswith("config-compat:W3")]
        assert w3, f"expected a W3 finding, got {[f.id for f in findings]}"
        recipe = w3[0].fix_recipe
        # the executor needs the matched literal and a real filesystem path
        assert recipe.get("pattern") == "skip tests"
        assert recipe.get("path") == str(project_dir / "CLAUDE.md")
        assert recipe.get("type") == "config_conflict"

    def test_f1_recipe_carries_tool_and_real_path(self, tmp_path, fake_home):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "allowedTools": ["Read", "Edit", "Agent", "Write"],
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f1 = next(f for f in findings
                  if f.id == "config-compat:F1:~/.claude/settings.json:Bash")
        recipe = f1.fix_recipe
        assert recipe.get("tool") == "Bash"
        assert recipe.get("conflict") == "F1"
        assert recipe.get("path") == str(fake_home / ".claude" / "settings.json")

    def test_f3_recipe_carries_hook_command_and_real_path(self, tmp_path, fake_home):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {"PostToolUse": [
                {"matcher": "anything", "hooks": [{"command": "pytest tests/"}]},
            ]},
        }))
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        findings = check_config_compat(state)

        f3 = next(f for f in findings if f.id.startswith("config-compat:F3"))
        recipe = f3.fix_recipe
        assert recipe.get("hook_command") == "pytest tests/"
        assert recipe.get("conflict") == "F3"
        assert recipe.get("path") == str(fake_home / ".claude" / "settings.json")

    # ----- text adopt: removes the offending line --------------------------

    def test_text_adopt_removes_skip_tests_line(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nYou should skip tests when in a hurry.\n\n## Notes\nKeep this line.\n",
        })
        claude_md = project_dir / "CLAUDE.md"
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "config_conflict",
            "file": "CLAUDE.md",
            "path": str(claude_md),
            "choice": "adopt",
            "conflict": "W3",
            "pattern": "skip tests",
        }, archive)

        assert result.success is True
        text = claude_md.read_text()
        assert "skip tests" not in text.lower(), "adopt must remove the offending line"
        # surrounding content left intact
        assert "# Project" in text
        assert "Keep this line." in text
        # backed up so it is reversible
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(claude_md))
        assert before_entry.exists(), "text adopt must back up the original"
        assert "skip tests" in before_entry.read_text().lower()

    # ----- settings F1 adopt: restores the excluded tool -------------------

    def test_f1_adopt_restores_excluded_tool(self, tmp_path, fake_home):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "allowedTools": ["Read", "Edit", "Agent", "Write"],
        }))
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "config_conflict",
            "file": "~/.claude/settings.json",
            "path": str(settings_path),
            "choice": "adopt",
            "conflict": "F1",
            "tool": "Bash",
        }, archive)

        assert result.success is True
        data = json.loads(settings_path.read_text())
        assert "Bash" in data["allowedTools"], "F1 adopt must add the excluded tool back"
        # other settings preserved
        assert data["plansDirectory"] == ".sweetclaude/plans"
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(settings_path))
        assert before_entry.exists(), "F1 adopt must back up the original settings"
        assert "Bash" not in json.loads(before_entry.read_text()).get("allowedTools", [])

    # ----- settings F3 adopt: removes the conflicting hook -----------------

    def test_f3_adopt_removes_conflicting_hook(self, tmp_path, fake_home):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "hooks": {"PostToolUse": [
                {"matcher": "anything", "hooks": [{"command": "pytest tests/"}]},
                {"matcher": "src", "hooks": [{"command": "echo keep me"}]},
            ]},
        }))
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "config_conflict",
            "file": "~/.claude/settings.json",
            "path": str(settings_path),
            "choice": "adopt",
            "conflict": "F3",
            "hook_command": "pytest tests/",
            "matcher": "anything",
        }, archive)

        assert result.success is True
        data = json.loads(settings_path.read_text())
        entries = data["hooks"]["PostToolUse"]
        commands = [h["command"] for e in entries for h in e.get("hooks", [])]
        assert "pytest tests/" not in commands, "F3 adopt must remove the conflicting hook"
        assert "echo keep me" in commands, "unrelated hooks must be preserved"
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(settings_path))
        assert before_entry.exists(), "F3 adopt must back up the original settings"

    # ----- keep / both are no-ops -----------------------------------------

    def test_keep_is_noop_no_backup(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nYou should skip tests when in a hurry.\n",
        })
        claude_md = project_dir / "CLAUDE.md"
        original = claude_md.read_bytes()
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "config_conflict",
            "file": "CLAUDE.md",
            "path": str(claude_md),
            "choice": "keep",
            "conflict": "W3",
            "pattern": "skip tests",
        }, archive)

        assert result.success is True
        assert claude_md.read_bytes() == original, "keep must leave the file untouched"
        assert list((archive / "before").iterdir()) == [], "keep must not back up"
        assert list((archive / "diffs").iterdir()) == [], "keep must not diff"

    def test_both_is_noop_no_backup(self, tmp_path, fake_home):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "allowedTools": ["Read", "Edit", "Agent", "Write"],
        }))
        original = settings_path.read_bytes()
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "config_conflict",
            "file": "~/.claude/settings.json",
            "path": str(settings_path),
            "choice": "both",
            "conflict": "F1",
            "tool": "Bash",
        }, archive)

        assert result.success is True
        assert settings_path.read_bytes() == original, "both must leave the file untouched"
        assert list((archive / "before").iterdir()) == [], "both must not back up"

    # ----- restore reversibility ------------------------------------------

    def test_text_adopt_is_restore_reversible(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "claude_md": "# Project\n\nYou should skip tests when in a hurry.\n\n## Notes\nKeep this.\n",
        })
        claude_md = project_dir / "CLAUDE.md"
        original = claude_md.read_bytes()
        archive = create_archive(project_dir)

        # apply through the auto-fix pipeline (the path the skill uses) so the
        # action is recorded in actions.json for restore to find
        finding = {
            "id": "config-compat:W3:CLAUDE.md:deadbeef",
            "category": "config_compat",
            "summary": "skip-tests conflict",
            "fix_type": "prompted",
            "fix_recipe": {
                "action": "config_conflict", "file": "CLAUDE.md",
                "path": str(claude_md), "choice": "adopt",
                "conflict": "W3", "pattern": "skip tests",
            },
        }
        auto_fix(project_dir, [finding], archive, include_prompted=True)
        assert claude_md.read_bytes() != original, "adopt must mutate the file"

        res = _p0_doctor.restore(project_dir, archive, file=str(claude_md))
        assert claude_md.read_bytes() == original, "restore must revert byte-identically"
        assert res["restored"], "restore must report what it restored"

    # ----- end-to-end through auto_fix with the enriched recipe -----------

    def test_adopt_via_autofix_pipeline(self, tmp_path, fake_home):
        settings_path = fake_home / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "plansDirectory": ".sweetclaude/plans",
            "allowedTools": ["Read", "Edit", "Agent", "Write"],
        }))
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)

        finding = {
            "id": "config-compat:F1:~/.claude/settings.json:Bash",
            "category": "config_compat",
            "summary": "settings block Bash",
            "fix_type": "prompted",
            "fix_recipe": {
                "action": "config_conflict", "file": "~/.claude/settings.json",
                "path": str(settings_path), "choice": "adopt",
                "conflict": "F1", "tool": "Bash",
            },
        }
        result = auto_fix(project_dir, [finding], archive, include_prompted=True)

        assert result["actions"][0]["action"] == "auto-fix"
        assert "Bash" in json.loads(settings_path.read_text())["allowedTools"]


def test_config_conflict_is_a_supported_action():
    from doctor import EXECUTOR_SUPPORTED_ACTIONS
    assert "config_conflict" in EXECUTOR_SUPPORTED_ACTIONS


class TestP1YamlRepair:
    """P1 / T2g: yaml_repair made functional through the executor.

    Three user choices, all routed through the executor:
      - auto: deterministically repair unambiguous frontmatter-delimiter
        breakage (a missing closing ``---``, a missing opening ``---`` with a
        closing one present) and re-serialize. Mutation only when the repaired
        text actually re-parses into the same field mapping. Ambiguous garbage
        is NOT guessed at — it returns success=False with a manual-edit signal.
      - restore: delegate to the existing ``restore`` path (revert to a prior
        run's archived before-image).
      - manual: no-op success, no backup (the skill shows the file for editing).

    auto routes its write through _record_mutation, so it is backed up, diffed,
    and ``restore``-reversible. NO MOCKS.
    """

    # ----- auto-repair: recoverable missing-closing-delimiter --------------

    def test_auto_repair_fixes_missing_closing_delimiter(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        broken = backlog / "ISSUE-001.md"
        # opening delimiter present, closing delimiter missing — the YAML region
        # is well-formed and the body is unambiguously markdown prose.
        broken.write_text(
            "---\n"
            "id: ISSUE-001\n"
            "title: Fix the thing\n"
            "status: active\n"
            "type: story\n"
            "# Fix the thing\n\n"
            "Some body text.\n"
        )
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "yaml_repair",
            "file": str(broken),
            "choice": "auto",
        }, archive)

        assert result.success is True, f"auto repair should succeed: {result.error}"
        # the file now parses as valid frontmatter
        fm, err = _p0_doctor._read_frontmatter_raw(broken)
        assert err is None, f"repaired file must parse cleanly, got: {err}"
        assert isinstance(fm, dict)
        # original fields preserved
        assert fm["id"] == "ISSUE-001"
        assert fm["title"] == "Fix the thing"
        assert fm["status"] == "active"
        assert fm["type"] == "story"
        # body preserved
        assert "Some body text." in broken.read_text()
        # backed up so it is reversible
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(broken))
        assert before_entry.exists(), "auto repair must back up the original"

    def test_auto_repair_fixes_missing_opening_delimiter(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        broken = backlog / "ISSUE-002.md"
        # opening delimiter missing, closing present — leading mapping is YAML.
        broken.write_text(
            "id: ISSUE-002\n"
            "title: Second thing\n"
            "status: active\n"
            "type: story\n"
            "---\n"
            "# Second thing\n\n"
            "Body.\n"
        )
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "yaml_repair",
            "file": str(broken),
            "choice": "auto",
        }, archive)

        assert result.success is True, f"auto repair should succeed: {result.error}"
        fm, err = _p0_doctor._read_frontmatter_raw(broken)
        assert err is None, f"repaired file must parse cleanly, got: {err}"
        assert fm["id"] == "ISSUE-002"
        assert fm["type"] == "story"
        assert "Body." in broken.read_text()

    # ----- auto-repair: ambiguous garbage must NOT be silently corrupted ----

    def test_auto_repair_ambiguous_garbage_signals_manual(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        broken = backlog / "ISSUE-003.md"
        # genuinely ambiguous: malformed mid-mapping YAML (bad indentation /
        # broken structure) that no delimiter insertion can salvage.
        garbage = (
            "---\n"
            "id: ISSUE-003\n"
            "title: : : broken\n"
            "  nested without key\n"
            "status: [unterminated\n"
            "garbage line :: :: more\n"
            "Definitely not parseable as a clean mapping.\n"
        )
        broken.write_text(garbage)
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "yaml_repair",
            "file": str(broken),
            "choice": "auto",
        }, archive)

        # must NOT claim a successful repair on ambiguous garbage
        assert result.success is False, "ambiguous garbage must not produce a bogus repair"
        assert result.error, "must surface a manual-edit-needed signal"
        # the file must be left untouched (no silent corruption)
        assert broken.read_text() == garbage, "ambiguous case must not mutate the file"
        # nothing backed up either
        assert list((archive / "before").iterdir()) == [], "no backup on a refused repair"

    # ----- manual: no-op, no backup ----------------------------------------

    def test_manual_choice_is_noop_no_backup(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        broken = backlog / "ISSUE-004.md"
        original = (
            "---\n"
            "id: ISSUE-004\n"
            "title: Manual\n"
            "# heading\n"
            "body\n"
        )
        broken.write_text(original)
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "yaml_repair",
            "file": str(broken),
            "choice": "manual",
        }, archive)

        assert result.success is True
        assert broken.read_text() == original, "manual must leave the file untouched"
        assert list((archive / "before").iterdir()) == [], "manual must not back up"
        assert list((archive / "diffs").iterdir()) == [], "manual must not diff"

    # ----- restore reversibility after an auto-repair ----------------------

    def test_auto_repair_is_restore_reversible(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        broken = backlog / "ISSUE-005.md"
        original = (
            "---\n"
            "id: ISSUE-005\n"
            "title: Reversible\n"
            "status: active\n"
            "type: story\n"
            "# Reversible\n\n"
            "Body content.\n"
        )
        broken.write_text(original)
        original_bytes = broken.read_bytes()
        archive = create_archive(project_dir)

        # apply through the auto-fix pipeline (the path the skill uses) so the
        # action is recorded in actions.json for restore to find
        finding = {
            "id": "state-integrity:yaml-parse:ISSUE-005.md",
            "category": "state_integrity",
            "summary": "broken frontmatter",
            "fix_type": "prompted",
            "fix_recipe": {
                "action": "yaml_repair", "file": str(broken), "choice": "auto",
            },
        }
        auto_fix(project_dir, [finding], archive, include_prompted=True)
        assert broken.read_bytes() != original_bytes, "auto repair must mutate the file"

        res = _p0_doctor.restore(project_dir, archive, file=str(broken))
        assert broken.read_bytes() == original_bytes, "restore must revert byte-identically"
        assert res["restored"], "restore must report what it restored"

    # ----- end-to-end through auto_fix with the prompted recipe -----------

    def test_auto_repair_via_autofix_pipeline(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        broken = backlog / "ISSUE-006.md"
        broken.write_text(
            "---\n"
            "id: ISSUE-006\n"
            "title: Pipeline\n"
            "status: active\n"
            "type: story\n"
            "# Pipeline\n\n"
            "Body.\n"
        )
        archive = create_archive(project_dir)

        finding = {
            "id": "state-integrity:yaml-parse:ISSUE-006.md",
            "category": "state_integrity",
            "summary": "broken frontmatter",
            "fix_type": "prompted",
            "fix_recipe": {
                "action": "yaml_repair", "file": str(broken), "choice": "auto",
            },
        }
        result = auto_fix(project_dir, [finding], archive, include_prompted=True)

        assert result["actions"][0]["action"] == "auto-fix"
        fm, err = _p0_doctor._read_frontmatter_raw(broken)
        assert err is None
        assert fm["id"] == "ISSUE-006"


def test_yaml_repair_is_a_supported_action():
    from doctor import EXECUTOR_SUPPORTED_ACTIONS
    assert "yaml_repair" in EXECUTOR_SUPPORTED_ACTIONS


def _build_fake_plugin(tmp_path):
    """Build a real plugin source tree mirroring the installed plugin layout:
    hook scripts + hooks.json + hooks-manifest.json under hooks/, rules .md
    under rules/. Returns the plugin root. NO MOCKS — real files on disk.
    """
    plugin = tmp_path / "plugin"
    hooks = plugin / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "hooks.json").write_text(json.dumps({"hooks": [{"x": 1}]}, indent=2))
    (hooks / "hooks-manifest.json").write_text(json.dumps({"manifest": True}))
    (hooks / "auto-test-runner.sh").write_text("#!/bin/bash\necho run\nexit 0\n")
    (hooks / "git-checkpoint.sh").write_text("#!/bin/bash\nexit 0\n")
    rules = plugin / "rules"
    rules.mkdir(parents=True)
    for rf in ("interaction-model.md", "phase-gates.md", "tdd-levels.md"):
        (rules / rf).write_text(f"# {rf}\nCanonical rule body for {rf}.\n")
    return plugin


class TestP1HookRestore:
    """P1 / T2h: hook_restore made a real, executor-owned action.

    The old skill-side ``cp $PLUGIN_DIR/config/{hook}`` always hit
    SOURCE_NOT_FOUND because the hook scripts ship in the plugin ``hooks/``
    dir and the rules ship in ``rules/`` — never ``config/``. This locks the
    correct source -> dest mapping per restorable kind:

      - hook script (``*.sh``)        : {plugin}/hooks/{name}  -> ~/.claude/hooks/sweetclaude/{name}
      - hooks.json / hooks-manifest   : {plugin}/hooks/{name}  -> ~/.claude/hooks/sweetclaude/{name}
      - rules file (``*.md``)         : {plugin}/rules/{name}  -> ~/.claude/rules/sweetclaude/{name}

    Any overwrite of an existing dest is backed up through _record_mutation so
    it is ``restore``-reversible (these ~/.claude files are outside the project
    git tree, so the safety branch cannot cover them). A genuinely absent
    source returns success=False with an error — never a silent skip, never a
    wrong-path write. NO MOCKS — a real fake plugin source tree is built.
    """

    # ----- restore a missing hook script: source present -> copied to dest --

    def test_restore_missing_hook_script_copies_from_plugin_to_dest(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        plugin = _build_fake_plugin(tmp_path)
        dest = Path.home() / ".claude" / "hooks" / "sweetclaude" / "auto-test-runner.sh"
        assert not dest.exists(), "precondition: dest hook script is missing"
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "hook_restore",
            "hook": "auto-test-runner.sh",
            "plugin_dir": str(plugin),
        }, archive)

        assert result.success is True, f"restore should succeed: {result.error}"
        # landed at the exact dest check_hook_health scans
        assert dest.exists(), "hook script must be restored to ~/.claude/hooks/sweetclaude/"
        assert dest.read_text() == (plugin / "hooks" / "auto-test-runner.sh").read_text()

    def test_restore_hooks_json_copies_from_plugin_hooks_dir(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plugin = _build_fake_plugin(tmp_path)
        # remove the fixture's placeholder hooks.json so this is a true restore
        dest = Path.home() / ".claude" / "hooks" / "sweetclaude" / "hooks.json"
        dest.unlink()
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "hook_restore",
            "hook": "hooks.json",
            "plugin_dir": str(plugin),
        }, archive)

        assert result.success is True, f"restore should succeed: {result.error}"
        assert dest.exists()
        assert dest.read_text() == (plugin / "hooks" / "hooks.json").read_text()

    def test_restore_rules_file_copies_from_plugin_rules_dir(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plugin = _build_fake_plugin(tmp_path)
        dest = Path.home() / ".claude" / "rules" / "sweetclaude" / "interaction-model.md"
        dest.unlink()
        assert not dest.exists()
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "hook_restore",
            "hook": "interaction-model.md",
            "plugin_dir": str(plugin),
        }, archive)

        assert result.success is True, f"restore should succeed: {result.error}"
        # rules go to ~/.claude/rules/sweetclaude/, NOT the hooks dir
        assert dest.exists(), "rules file must land in ~/.claude/rules/sweetclaude/"
        assert dest.read_text() == (plugin / "rules" / "interaction-model.md").read_text()
        wrong = Path.home() / ".claude" / "hooks" / "sweetclaude" / "interaction-model.md"
        assert not wrong.exists(), "rules file must not be written into the hooks dir"

    # ----- overwriting a stale dest is backed up (restore-reversible) -------

    def test_restore_over_stale_dest_backs_up_prior_content(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plugin = _build_fake_plugin(tmp_path)
        dest = Path.home() / ".claude" / "hooks" / "sweetclaude" / "auto-test-runner.sh"
        stale = "#!/bin/bash\n# STALE corrupted content\nexit 1\n"
        dest.write_text(stale)
        stale_bytes = dest.read_bytes()
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "hook_restore",
            "hook": "auto-test-runner.sh",
            "plugin_dir": str(plugin),
        }, archive)

        assert result.success is True, f"restore should succeed: {result.error}"
        # dest now holds the canonical content
        assert dest.read_text() == (plugin / "hooks" / "auto-test-runner.sh").read_text()
        # the prior (stale) content was backed up to before/ for reversibility
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(dest))
        assert before_entry.exists(), "overwrite must back up the prior dest content"
        assert before_entry.read_bytes() == stale_bytes, "backup must hold the stale bytes"

    def test_restore_over_stale_dest_is_restore_reversible(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plugin = _build_fake_plugin(tmp_path)
        dest = Path.home() / ".claude" / "hooks" / "sweetclaude" / "git-checkpoint.sh"
        stale = "#!/bin/bash\n# old version\nexit 7\n"
        dest.write_text(stale)
        stale_bytes = dest.read_bytes()
        archive = create_archive(project_dir)

        # apply through the auto-fix pipeline (the path the skill uses) so the
        # action is recorded for restore to find
        finding = {
            "id": "hook-health:syntax-error:git-checkpoint.sh",
            "category": "hook_health",
            "summary": "hook script broken",
            "fix_type": "prompted",
            "fix_recipe": {
                "action": "hook_restore",
                "hook": "git-checkpoint.sh",
                "plugin_dir": str(plugin),
            },
        }
        auto_fix(project_dir, [finding], archive, include_prompted=True)
        assert dest.read_bytes() != stale_bytes, "restore must overwrite the stale dest"

        res = _p0_doctor.restore(project_dir, archive, file=str(dest))
        assert dest.read_bytes() == stale_bytes, "restore must revert to the prior bytes"
        assert res["restored"], "restore must report what it restored"

    # ----- genuinely absent source -> success=False, no wrong-path write ----

    def test_restore_absent_source_fails_without_writing(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        plugin = _build_fake_plugin(tmp_path)
        # a target that does not exist anywhere in the plugin source tree
        dest = Path.home() / ".claude" / "hooks" / "sweetclaude" / "does-not-exist.sh"
        assert not dest.exists()
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "hook_restore",
            "hook": "does-not-exist.sh",
            "plugin_dir": str(plugin),
        }, archive)

        assert result.success is False, "absent source must not report success"
        assert result.error, "absent source must surface a clear error"
        # never a silent success, never a wrong-path write
        assert not dest.exists(), "absent source must not write the dest"
        assert list((archive / "before").iterdir()) == [], "no backup on a failed restore"

    def test_restore_missing_plugin_dir_fails_cleanly(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        missing_plugin = tmp_path / "no-such-plugin"
        dest = Path.home() / ".claude" / "hooks" / "sweetclaude" / "auto-test-runner.sh"
        dest_existed = dest.exists()
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "hook_restore",
            "hook": "auto-test-runner.sh",
            "plugin_dir": str(missing_plugin),
        }, archive)

        assert result.success is False
        assert result.error
        assert dest.exists() == dest_existed, "must not create the dest from a missing plugin"


def test_hook_restore_is_a_supported_action():
    from doctor import EXECUTOR_SUPPORTED_ACTIONS
    assert "hook_restore" in EXECUTOR_SUPPORTED_ACTIONS


class TestP1FileMove:
    """P1 / T2c: file_move made a real, executor-owned action with move-aware
    rollback.

    storage-lint emits ``{"action":"prompt","type":"file_move","src":...,
    "dest":...}`` for done-status items in the wrong folder. The executor moves
    src -> dest, backing up src's content keyed to src so the move is
    reversible. A move does NOT fit the content-revert restore model — backing
    up src and writing it back to src would leave BOTH src and dest. So
    ``restore`` must REVERSE the move: delete dest, recreate src from its
    before-image. NO MOCKS — real files on disk.
    """

    def test_file_move_moves_src_to_dest_and_backs_up_src(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        done_dir = project_dir / ".sweetclaude" / "product" / "backlog" / "done"
        src = done_dir / "ISSUE-500.md"
        _write_frontmatter_file(src, {
            "id": "ISSUE-500", "title": "Misfiled", "type": "enhancement",
            "status": "new", "created": "2026-01-01"}, body="\n# body\n")
        original = src.read_bytes()
        dest = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-500.md"
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "file_move", "src": str(src), "dest": str(dest),
        }, archive)

        assert result.success is True, f"file_move should succeed: {result.error}"
        assert not src.exists(), "src must be gone after the move"
        assert dest.exists(), "dest must exist after the move"
        assert dest.read_bytes() == original, "dest must hold the original src content"
        # src's content was backed up to before/ keyed to src (reversible)
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(src))
        assert before_entry.exists(), "move must back up src's content keyed to src"
        assert before_entry.read_bytes() == original

    def test_file_move_creates_missing_dest_parent_dir(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        src = backlog / "ISSUE-501.md"
        _write_frontmatter_file(src, {
            "id": "ISSUE-501", "title": "Done item", "type": "enhancement",
            "status": "done", "created": "2026-01-01"}, body="\n# body\n")
        original = src.read_bytes()
        # dest parent (done/) does not yet exist
        dest = backlog / "done" / "ISSUE-501.md"
        assert not dest.parent.exists(), "precondition: dest parent dir is absent"
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "file_move", "src": str(src), "dest": str(dest),
        }, archive)

        assert result.success is True, f"file_move should succeed: {result.error}"
        assert dest.parent.is_dir(), "dest parent dir must be created"
        assert dest.exists() and dest.read_bytes() == original
        assert not src.exists()

    def test_file_move_missing_src_fails_without_writing(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        src = backlog / "done" / "ISSUE-502.md"  # never created
        dest = backlog / "ISSUE-502.md"
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "file_move", "src": str(src), "dest": str(dest),
        }, archive)

        assert result.success is False, "missing src must not report success"
        assert result.error, "missing src must surface a clear error"
        assert not dest.exists(), "missing src must not create dest"
        assert list((archive / "before").iterdir()) == [], "no backup on a failed move"

    def test_move_aware_restore_reverses_the_move(self, tmp_path, fake_home):
        # The wrinkle: restore must REVERSE a move, not double the file.
        project_dir = build_fixture(tmp_path)
        done_dir = project_dir / ".sweetclaude" / "product" / "backlog" / "done"
        src = done_dir / "ISSUE-503.md"
        _write_frontmatter_file(src, {
            "id": "ISSUE-503", "title": "Misfiled", "type": "enhancement",
            "status": "new", "created": "2026-01-01"}, body="\n# body\n")
        original = src.read_bytes()
        dest = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-503.md"
        archive = create_archive(project_dir)

        # apply through the auto-fix pipeline (the path the skill uses) so the
        # move action is recorded for restore to find
        finding = {
            "id": "storage-lint:done-status-mismatch:ISSUE-503.md",
            "category": "storage_lint",
            "summary": "ISSUE-503.md is in done/ but isn't marked done",
            "fix_type": "prompted",
            "fix_recipe": {"action": "file_move", "src": str(src), "dest": str(dest)},
        }
        auto_fix(project_dir, [finding], archive, include_prompted=True)
        assert not src.exists() and dest.exists(), "precondition: the move happened"

        res = _p0_doctor.restore(project_dir, archive, restore_all=True)

        assert src.exists(), "restore must recreate src"
        assert src.read_bytes() == original, "restored src must be byte-identical"
        assert not dest.exists(), "restore must REMOVE dest — never leave a double file"
        assert res["restored"], "restore must report what it reversed"

    def test_move_aware_restore_by_file_targets_the_src(self, tmp_path, fake_home):
        # restore(file=src) reverses the move keyed to the recorded src path
        project_dir = build_fixture(tmp_path)
        done_dir = project_dir / ".sweetclaude" / "product" / "backlog" / "done"
        src = done_dir / "ISSUE-504.md"
        _write_frontmatter_file(src, {
            "id": "ISSUE-504", "title": "Misfiled", "type": "enhancement",
            "status": "new", "created": "2026-01-01"}, body="\n# body\n")
        original = src.read_bytes()
        dest = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-504.md"
        archive = create_archive(project_dir)

        finding = {
            "id": "storage-lint:done-status-mismatch:ISSUE-504.md",
            "category": "storage_lint",
            "summary": "misfiled",
            "fix_type": "prompted",
            "fix_recipe": {"action": "file_move", "src": str(src), "dest": str(dest)},
        }
        auto_fix(project_dir, [finding], archive, include_prompted=True)

        res = _p0_doctor.restore(project_dir, archive, file=str(src))

        assert src.exists() and src.read_bytes() == original
        assert not dest.exists(), "restore must remove dest, not leave a double"
        assert res["restored"]

    def test_non_move_action_in_same_archive_still_content_restores(
        self, tmp_path, fake_home
    ):
        # A plain content mutation and a move coexist in one archive; restoring
        # all reverses both correctly — the move is reversed, the plain edit is
        # content-reverted. No regression to the existing restore model.
        project_dir = build_fixture(tmp_path)
        ss = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss.write_text("phase_schema_version: 1\n")
        ss_original = ss.read_bytes()
        done_dir = project_dir / ".sweetclaude" / "product" / "backlog" / "done"
        src = done_dir / "ISSUE-505.md"
        _write_frontmatter_file(src, {
            "id": "ISSUE-505", "title": "Misfiled", "type": "enhancement",
            "status": "new", "created": "2026-01-01"}, body="\n# body\n")
        src_original = src.read_bytes()
        dest = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-505.md"
        archive = create_archive(project_dir)

        findings = [
            _make_finding(action="write_field", file=str(ss),
                          key="phase_schema_version", value=2),
            {
                "id": "storage-lint:done-status-mismatch:ISSUE-505.md",
                "category": "storage_lint", "summary": "misfiled",
                "fix_type": "prompted",
                "fix_recipe": {"action": "file_move", "src": str(src), "dest": str(dest)},
            },
        ]
        auto_fix(project_dir, findings, archive, include_prompted=True)
        assert ss.read_bytes() != ss_original and not src.exists()

        res = _p0_doctor.restore(project_dir, archive, restore_all=True)

        # plain content mutation reverted by content
        assert ss.read_bytes() == ss_original
        # move reversed: src back, dest gone
        assert src.exists() and src.read_bytes() == src_original
        assert not dest.exists()
        assert len(res["restored"]) == 2


def test_file_move_is_a_supported_action():
    from doctor import EXECUTOR_SUPPORTED_ACTIONS
    assert "file_move" in EXECUTOR_SUPPORTED_ACTIONS


class TestP1Renumber:
    """P1 / T2d: renumber_duplicate made a real, executor-owned action.

    Two items share an ID. check_file_diagnostics emits a ``renumber_duplicate``
    prompt recipe carrying the colliding files, their labels, the duplicate id,
    and a proposed next-available id. The executor action rewrites the chosen
    file's ``id`` frontmatter field AND renames OLD-ID*.md -> NEW-ID*.md. Like
    file_move, a rename does NOT fit the content-revert restore model: the move
    is recorded move-aware (before-image keyed to the original path, a
    ``moved_to`` marker carrying the renamed path) so ``restore`` reverses BOTH
    the rename (delete the new file, recreate the original) and the id rewrite
    (the before-image holds the old id). NO MOCKS — real files on disk.
    """

    def test_duplicate_id_emits_renumber_recipe_with_valid_new_id(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-010-a.md", "frontmatter": {
                    "id": "ISSUE-010", "title": "First", "type": "enhancement",
                    "status": "new", "created": "2026-01-01"}, "body": "\n# a\n"},
                {"name": "ISSUE-010-b.md", "frontmatter": {
                    "id": "ISSUE-010", "title": "Second", "type": "enhancement",
                    "status": "new", "created": "2026-01-01"}, "body": "\n# b\n"},
                {"name": "ISSUE-042-c.md", "frontmatter": {
                    "id": "ISSUE-042", "title": "Highest", "type": "enhancement",
                    "status": "new", "created": "2026-01-01"}, "body": "\n# c\n"},
            ],
        })
        findings = check_file_diagnostics(build_project_state(project_dir))
        dup = [f for f in findings
               if f.id == "file-diagnostics:duplicate-id:ISSUE-010"]
        assert dup, "a duplicate id must emit a duplicate-id finding"
        recipe = dup[0].fix_recipe
        assert recipe.get("action") == "prompt"
        assert recipe.get("type") == "renumber_duplicate", (
            f"duplicate-id must emit a renumber_duplicate prompt, got {recipe}")
        assert recipe.get("duplicate_id") == "ISSUE-010"
        assert len(recipe.get("files", [])) == 2, "both colliding files carried"
        assert len(recipe.get("labels", [])) == 2, "a label per file"
        # proposed next-available id: highest among scanned is ISSUE-042 -> 043
        assert recipe.get("proposed_new_id") == "ISSUE-043", (
            f"proposed_new_id must be next-available, got "
            f"{recipe.get('proposed_new_id')}")

    def test_renumber_rewrites_id_and_renames_file(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        target = backlog / "ISSUE-010-second.md"
        _write_frontmatter_file(target, {
            "id": "ISSUE-010", "title": "Second", "type": "enhancement",
            "status": "new", "created": "2026-01-01"}, body="\n# body\n")
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "renumber_duplicate", "file": str(target),
            "old_id": "ISSUE-010", "new_id": "ISSUE-043",
        }, archive)

        assert result.success is True, f"renumber should succeed: {result.error}"
        assert not target.exists(), "old filename must be gone after the rename"
        renamed = backlog / "ISSUE-043-second.md"
        assert renamed.exists(), "file must be renamed to match the new id"
        fm = yaml.safe_load(renamed.read_text().split("---", 2)[1])
        assert fm["id"] == "ISSUE-043", "id frontmatter must be rewritten"
        # before-image of the original path was recorded (reversible)
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(target))
        assert before_entry.exists(), "renumber must back up the original path"

    def test_renumber_missing_file_fails_without_writing(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        target = backlog / "ISSUE-010-nope.md"  # never created
        archive = create_archive(project_dir)

        result = execute_recipe(project_dir, {
            "action": "renumber_duplicate", "file": str(target),
            "old_id": "ISSUE-010", "new_id": "ISSUE-043",
        }, archive)

        assert result.success is False, "missing file must not report success"
        assert result.error, "missing file must surface a clear error"
        assert list((archive / "before").iterdir()) == [], "no backup on failure"

    def test_renumber_restore_reverses_rename_and_id(self, tmp_path, fake_home):
        # The wrinkle: restore must REVERSE the rename + id rewrite, not double.
        project_dir = build_fixture(tmp_path)
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        target = backlog / "ISSUE-010-second.md"
        _write_frontmatter_file(target, {
            "id": "ISSUE-010", "title": "Second", "type": "enhancement",
            "status": "new", "created": "2026-01-01"}, body="\n# body\n")
        original = target.read_bytes()
        archive = create_archive(project_dir)

        # apply through the auto-fix pipeline (the path the skill uses) so the
        # rename action is recorded for restore to find
        finding = {
            "id": "file-diagnostics:duplicate-id:ISSUE-010",
            "category": "file_diagnostics",
            "summary": "ID ISSUE-010 is used by multiple files",
            "fix_type": "prompted",
            "fix_recipe": {"action": "renumber_duplicate", "file": str(target),
                           "old_id": "ISSUE-010", "new_id": "ISSUE-043"},
        }
        auto_fix(project_dir, [finding], archive, include_prompted=True)
        renamed = backlog / "ISSUE-043-second.md"
        assert not target.exists() and renamed.exists(), "precondition: renamed"

        res = _p0_doctor.restore(project_dir, archive, restore_all=True)

        assert target.exists(), "restore must recreate the original file"
        assert target.read_bytes() == original, "restored file must be byte-identical"
        assert not renamed.exists(), "restore must REMOVE the renamed file — no double"
        fm = yaml.safe_load(target.read_text().split("---", 2)[1])
        assert fm["id"] == "ISSUE-010", "restore must reverse the id rewrite"
        assert res["restored"], "restore must report what it reversed"


def test_renumber_duplicate_is_a_supported_action():
    from doctor import EXECUTOR_SUPPORTED_ACTIONS
    assert "renumber_duplicate" in EXECUTOR_SUPPORTED_ACTIONS


class TestP1ExitCompat:
    """T2f revisited: the flag-write exit was removed as a no-op dead end.

    The original T2f surfaced an ``exit_compatibility_mode`` prompt that set
    ``recovery.taxonomy.compatibility_exited: true`` — but the guard never read
    that flag for status, so the prompt re-offered itself every scan while
    changing nothing the user could see. The only real exit from compatibility
    mode is graduation (graduation-available / graduation-blocked routes).
    The scan must therefore NOT surface the flag-write prompt. The nested
    key_path write_field reuse (the V7-tripwire mechanism T2f introduced) stays
    a supported executor capability and remains backed up and
    restore-reversible. NO MOCKS.
    """

    @staticmethod
    def _compat_project(tmp_path):
        return build_fixture(tmp_path, overrides={
            "sweetclaude_yaml": {
                "phase_schema_version": 2,
                "framework": {
                    "installed_version": "4.0.8-beta",
                    "migration_status": "deferred",
                },
                "recovery": {"taxonomy": {
                    "status": "stabilized-without-migration",
                    "migration_required": False,
                    "blind_taxonomy_migration_allowed": False,
                }},
            },
        })

    def test_compatibility_mode_does_not_surface_flag_write_exit(
        self, tmp_path, fake_home
    ):
        project_dir = self._compat_project(tmp_path)
        result = _scan(build_project_state(project_dir))
        exit_findings = [
            f for f in result["findings"]
            if f.get("fix_recipe", {}).get("type") == "exit_compatibility_mode"
            or "compatibility_exited" in (f.get("fix_recipe", {}).get("key_path") or [])
        ]
        assert not exit_findings, (
            "the flag-write exit is a no-op (guard never reads the flag for "
            "status) — the only real exit is graduation")

    def test_exit_compat_apply_sets_flag_via_write_field_reuse(
        self, tmp_path, fake_home
    ):
        project_dir = self._compat_project(tmp_path)
        sc_yaml = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
        archive = create_archive(project_dir)

        # exactly the recipe the SKILL emits after the user confirms exit:
        # a write_field reuse with a nested key_path (no new transform).
        finding = {
            "id": "compatibility-mode:exit-available",
            "category": "compatibility_mode",
            "summary": "Exit compatibility mode",
            "fix_type": "prompted",
            "fix_recipe": {
                "action": "write_field", "file": str(sc_yaml),
                "key_path": ["recovery", "taxonomy", "compatibility_exited"],
                "value": True,
            },
        }
        result = auto_fix(project_dir, [finding], archive, include_prompted=True)

        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "auto-fix"
        data = yaml.safe_load(sc_yaml.read_text())
        assert data["recovery"]["taxonomy"]["compatibility_exited"] is True, (
            "exit must set recovery.taxonomy.compatibility_exited: true")
        # backed up + reversible
        assert list((archive / "before").iterdir()), "reuse path must record a backup"

    def test_exit_compat_apply_is_restore_reversible(self, tmp_path, fake_home):
        project_dir = self._compat_project(tmp_path)
        sc_yaml = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
        original = sc_yaml.read_bytes()
        archive = create_archive(project_dir)

        finding = {
            "id": "compatibility-mode:exit-available",
            "category": "compatibility_mode",
            "summary": "Exit compatibility mode",
            "fix_type": "prompted",
            "fix_recipe": {
                "action": "write_field", "file": str(sc_yaml),
                "key_path": ["recovery", "taxonomy", "compatibility_exited"],
                "value": True,
            },
        }
        auto_fix(project_dir, [finding], archive, include_prompted=True)
        assert sc_yaml.read_bytes() != original, "precondition: flag was written"

        res = _p0_doctor.restore(project_dir, archive, file=str(sc_yaml))

        assert sc_yaml.read_bytes() == original, "restore must revert byte-identically"
        data = yaml.safe_load(sc_yaml.read_text())
        exited = (data.get("recovery", {}).get("taxonomy", {})
                  .get("compatibility_exited"))
        assert not exited, "restore must clear the compatibility_exited flag"
        assert res["restored"]


class TestP1Suppress:
    """P1 / S3: close the last skill-side direct file write.

    The SKILL.md suppress flow previously wrote ``doctor-suppressions.json``
    inline (a ``python3 -c`` / file write in the skill), violating the PRD
    principle "the skill layer never writes files directly" (S3) — while
    SKILL.md's own Safety properties section claimed the opposite. The fix
    routes suppression through a ``suppress`` CLI subcommand in doctor.py, so
    the script owns the write and the no-direct-writes claim becomes true.
    NO MOCKS — real fixtures, real files, real ``main()`` dispatch.
    """

    def test_suppress_subcommand_adds_finding_id(self, tmp_path, fake_home, capsys):
        project_dir = build_fixture(tmp_path)
        exit_code = main([
            "suppress",
            "--project-dir", str(project_dir),
            "--finding-id", "file-diagnostics:unknown-status:ISSUE-009-x.md",
            "--reason", "intentional custom status",
        ])
        assert exit_code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["suppressed"] is True
        assert output["finding_id"] == "file-diagnostics:unknown-status:ISSUE-009-x.md"

        entries = load_suppressions(project_dir)
        ids = [e.get("finding_id") for e in entries]
        assert "file-diagnostics:unknown-status:ISSUE-009-x.md" in ids, (
            f"suppress subcommand must add the finding id to the file, got: {ids}"
        )
        entry = next(
            e for e in entries
            if e.get("finding_id") == "file-diagnostics:unknown-status:ISSUE-009-x.md"
        )
        assert entry.get("reason") == "intentional custom status"
        assert entry.get("suppressed_at"), "entry must carry a suppression timestamp"

    def test_suppress_is_idempotent(self, tmp_path, fake_home, capsys):
        project_dir = build_fixture(tmp_path)
        fid = "env-wiring:missing:plans-directory"

        main(["suppress", "--project-dir", str(project_dir), "--finding-id", fid])
        capsys.readouterr()
        main(["suppress", "--project-dir", str(project_dir), "--finding-id", fid])
        capsys.readouterr()

        entries = load_suppressions(project_dir)
        matching = [e for e in entries if e.get("finding_id") == fid]
        assert len(matching) == 1, (
            f"suppressing the same id twice must not duplicate it, got: {entries}"
        )

    def test_suppress_preserves_existing_entries(self, tmp_path, fake_home, capsys):
        project_dir = build_fixture(tmp_path, overrides={
            "suppressions": [{"finding_id": "pre-existing:one"}],
        })

        main([
            "suppress", "--project-dir", str(project_dir),
            "--finding-id", "newly:added",
        ])
        capsys.readouterr()

        ids = [e.get("finding_id") for e in load_suppressions(project_dir)]
        assert "pre-existing:one" in ids, (
            f"suppress must preserve existing entries, got: {ids}"
        )
        assert "newly:added" in ids

    def test_suppressed_finding_filtered_out_of_scan(self, tmp_path, fake_home, capsys):
        # Produce a real unknown-status finding, then suppress it via the
        # subcommand and confirm it drops out of the next scan (reusing the
        # existing suppression-filter behavior).
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test",
                    "status": "invented",
                }},
            ],
        })
        fid = "file-diagnostics:unknown-status:ISSUE-001-test.md"

        before = _scan(build_project_state(project_dir))
        assert fid in [f["id"] for f in before["findings"]], (
            "precondition: finding must be present before suppression"
        )

        main(["suppress", "--project-dir", str(project_dir), "--finding-id", fid])
        capsys.readouterr()

        after = _scan(build_project_state(project_dir))
        assert fid not in [f["id"] for f in after["findings"]], (
            "a subsequently-suppressed finding must be filtered out of a scan"
        )

    def test_skill_suppress_flow_invokes_subcommand_not_inline_write(self):
        # Structural: the SKILL.md suppress flow must invoke the suppress
        # subcommand and contain NO inline file write to doctor-suppressions.json.
        skill = (
            Path(__file__).parents[1] / "skills" / "doctor" / "SKILL.md"
        ).read_text(encoding="utf-8")

        assert "doctor.py suppress" in skill, (
            "SKILL.md suppress flow must invoke the suppress subcommand"
        )
        # No inline python writing the suppressions file (the V9 violation).
        assert "# Add to doctor-suppressions.json" not in skill, (
            "SKILL.md must not contain the inline suppressions-file write block"
        )
        assert 'suppressed_at": "{ISO timestamp}"' not in skill, (
            "SKILL.md must not hand-construct a suppression entry inline"
        )


# ---------------------------------------------------------------------------
# Capstone: enumerate-all-actions executor invariants.
#
# The keystone that ENFORCES the §6 Safety Model going forward. Every action
# in EXECUTOR_SUPPORTED_ACTIONS must be classified into exactly one of three
# disjoint sets, and every content-mutating action must be exercised through
# the real backup/diff/restore pipeline. The classification assertion fails
# the moment a NEW action is added without being classified here, so no future
# action can silently bypass the backup pipeline (P2/P7) or escape rollback
# (S6). NO MOCKS — real fixtures, real files, real execute_recipe / restore.
# ---------------------------------------------------------------------------


# --- the three classification sets (built in the test, asserted exhaustive) --

# Content-mutating: when the action actually changes a file it MUST record a
# before/ image AND a diffs/ entry, and be reversible by restore. create_dir is
# included here as a content-mutating *kind* (it is a filesystem mutation the
# executor owns) but is exercised specially — a directory create has no
# authored before-image (it is reversed by removing the dir), so it is verified
# through its own assertion rather than the content-revert loop.
_CONTENT_MUTATING_ACTIONS = frozenset({
    "write_field",
    "write_frontmatter_field",
    "delete_file",
    "create_dir",
    "sync_parent_status",
    "convert_to_yaml",
    "config_conflict",
    "yaml_repair",
    "hook_restore",
    "file_move",
    "renumber_duplicate",
})

# Backed-up subprocess actions — run an external script/rebuild but capture the
# bytes of the file(s) they regenerate (the cache file for rebuild_cache; the
# recipe's `regenerates` targets for run_script) BEFORE running, then route each
# changed target through _record_mutation. They are backed up, diffed, and
# reversible by restore — closing PRD invariants P2/P7/T1h/S6.
_BACKED_UP_SUBPROCESS_ACTIONS = frozenset({
    "run_script",
    "rebuild_cache",
    # resolve_orphans wraps migrate-v3-to-v4.py subcommands with before-images
    # through _record_mutation (move-aware for archive/reonboard); its backup +
    # restore behavior has dedicated coverage in TestResolveOrphansExecutor.
    "resolve_orphans",
})

# Explicitly reversible:false — derived/regenerable output that carries no
# authored before-image. Kept (empty is fine) as an allowlist so the script can
# never quietly grow an un-backed-up mutation under this banner: any new action
# placed here is a deliberate, reviewed exception, and the partition test still
# forces every supported action into exactly one class.
_REVERSIBLE_FALSE_ACTIONS = frozenset()

# Presentation-only — surfaced for user approval, never executed by the
# executor as a file mutation.
_PRESENTATION_ONLY_ACTIONS = frozenset({
    "prompt",
})


def _capstone_build_content_mutation(tmp_path, action):
    """Build a real fixture + recipe for a content-mutating action and return
    (project_dir, archive, recipe, mutated_path, original_bytes).

    ``mutated_path`` is the path whose before-image the archive records (for
    file_move / renumber_duplicate this is the SOURCE path, keyed how the
    move-aware restore reverses it). ``original_bytes`` is that path's content
    before the mutation. Each builder reuses the exact recipe shape the
    per-action P0/P1 tests already lock. NO MOCKS — real files on disk.
    """
    project_dir = build_fixture(tmp_path)
    backlog = project_dir / ".sweetclaude" / "product" / "backlog"

    if action == "write_field":
        ss = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        ss.write_text("phase_schema_version: 1\nfoo: bar\n")
        archive = create_archive(project_dir)
        recipe = {"action": "write_field", "file": str(ss),
                  "key": "phase_schema_version", "value": 99}
        return project_dir, archive, recipe, ss, ss.read_bytes()

    if action == "write_frontmatter_field":
        target = backlog / "ISSUE-900.md"
        _write_frontmatter_file(target, {
            "id": "ISSUE-900", "title": "Thing", "type": "enhancement",
            "status": "new", "created": "2026-01-01"}, body="\n# Body\n")
        archive = create_archive(project_dir)
        recipe = {"action": "write_frontmatter_field", "file": str(target),
                  "key": "status", "value": "active"}
        return project_dir, archive, recipe, target, target.read_bytes()

    if action == "delete_file":
        target = project_dir / ".sweetclaude" / "state" / "pending-drift-decision.yaml"
        target.write_text("decision: pending\nfoo: bar\n")
        archive = create_archive(project_dir)
        recipe = {"action": "delete_file", "file": str(target)}
        return project_dir, archive, recipe, target, target.read_bytes()

    if action == "sync_parent_status":
        # distinct subdir: _p0_epic_child builds its own fixture, must not collide
        # with the build_fixture(tmp_path) at the top of this helper.
        project_dir, epic_path = _p0_epic_child(
            tmp_path / "sync", "EP-900", "done", "ISSUE-901", "in-progress")
        archive = create_archive(project_dir)
        recipe = {"action": "sync_parent_status", "file": str(epic_path),
                  "parent_id": "EP-900", "parent_type": "epic"}
        return project_dir, archive, recipe, epic_path, epic_path.read_bytes()

    if action == "convert_to_yaml":
        bold = backlog / "ISSUE-902.md"
        bold.write_text(
            "# ISSUE-902: Widget\n\n**Type:** enhancement\n**Status:** active\n"
            "**Created:** 2026-01-01\n\n## Description\n\nBody.\n")
        archive = create_archive(project_dir)
        recipe = {"action": "convert_to_yaml", "file": str(bold)}
        return project_dir, archive, recipe, bold, bold.read_bytes()

    if action == "config_conflict":
        # distinct subdir: this branch rebuilds with a claude_md override and must
        # not collide with the build_fixture(tmp_path) at the top of this helper.
        project_dir = build_fixture(tmp_path / "cfg", overrides={
            "claude_md": "# Project\n\nYou should skip tests when in a hurry.\n\n"
                         "## Notes\nKeep this.\n"})
        claude_md = project_dir / "CLAUDE.md"
        archive = create_archive(project_dir)
        recipe = {"action": "config_conflict", "file": "CLAUDE.md",
                  "path": str(claude_md), "choice": "adopt",
                  "conflict": "W3", "pattern": "skip tests"}
        return project_dir, archive, recipe, claude_md, claude_md.read_bytes()

    if action == "yaml_repair":
        broken = backlog / "ISSUE-903.md"
        broken.write_text(
            "---\nid: ISSUE-903\ntitle: Reversible\nstatus: active\ntype: story\n"
            "# Reversible\n\nBody content.\n")
        archive = create_archive(project_dir)
        recipe = {"action": "yaml_repair", "file": str(broken), "choice": "auto"}
        return project_dir, archive, recipe, broken, broken.read_bytes()

    if action == "hook_restore":
        plugin = _build_fake_plugin(tmp_path)
        dest = Path.home() / ".claude" / "hooks" / "sweetclaude" / "auto-test-runner.sh"
        dest.write_text("#!/bin/bash\n# STALE\nexit 1\n")
        archive = create_archive(project_dir)
        recipe = {"action": "hook_restore", "hook": "auto-test-runner.sh",
                  "plugin_dir": str(plugin)}
        # hook_restore threads the resolved dest back onto recipe["file"]; the
        # before-image is keyed to dest, so dest is the mutated path.
        return project_dir, archive, recipe, dest, dest.read_bytes()

    if action == "file_move":
        done_dir = backlog / "done"
        src = done_dir / "ISSUE-904.md"
        _write_frontmatter_file(src, {
            "id": "ISSUE-904", "title": "Misfiled", "type": "enhancement",
            "status": "new", "created": "2026-01-01"}, body="\n# body\n")
        dest = backlog / "ISSUE-904.md"
        archive = create_archive(project_dir)
        recipe = {"action": "file_move", "src": str(src), "dest": str(dest)}
        # the before-image is keyed to SRC; restore reverses the move.
        return project_dir, archive, recipe, src, src.read_bytes()

    if action == "renumber_duplicate":
        target = backlog / "ISSUE-010-second.md"
        _write_frontmatter_file(target, {
            "id": "ISSUE-010", "title": "Second", "type": "enhancement",
            "status": "new", "created": "2026-01-01"}, body="\n# body\n")
        archive = create_archive(project_dir)
        recipe = {"action": "renumber_duplicate", "file": str(target),
                  "old_id": "ISSUE-010", "new_id": "ISSUE-943"}
        # the before-image is keyed to the ORIGINAL path; restore reverses the
        # rename + id rewrite.
        return project_dir, archive, recipe, target, target.read_bytes()

    raise AssertionError(f"no capstone builder for content-mutating action {action!r}")


class TestP1ExecutorInvariants:
    """Capstone enumerate-all-actions invariant: enforces the §6 Safety Model.

    1. Every action in EXECUTOR_SUPPORTED_ACTIONS is classified into exactly
       one of three disjoint sets — content-mutating, reversible:false, or
       presentation-only — and their union equals EXECUTOR_SUPPORTED_ACTIONS.
       A new, unclassified action fails this test, so nothing can silently
       bypass the backup pipeline.
    2. Every content-mutating action, exercised through execute_recipe against
       a real fixture, records a before/ image AND a diffs/ entry on a real
       change AND is reversed by restore (content-reverted, or move reversed).
       create_dir is verified specially (dir create, no authored before-image).
    3. No skill-side direct file writes remain — the skill invokes script
       subcommands for every mutation; only read-only inline python remains
       (structural assertion over SKILL.md).
    """

    # ----- 1. exhaustive, disjoint classification --------------------------

    def test_classification_partitions_every_supported_action(self):
        from doctor import EXECUTOR_SUPPORTED_ACTIONS

        union = (
            _CONTENT_MUTATING_ACTIONS
            | _BACKED_UP_SUBPROCESS_ACTIONS
            | _REVERSIBLE_FALSE_ACTIONS
            | _PRESENTATION_ONLY_ACTIONS
        )

        # Exhaustive: every supported action is classified. A new action added
        # to EXECUTOR_SUPPORTED_ACTIONS without being placed in one of the three
        # sets here FAILS — it cannot silently bypass the backup pipeline.
        unclassified = set(EXECUTOR_SUPPORTED_ACTIONS) - union
        assert not unclassified, (
            f"unclassified action(s) added to EXECUTOR_SUPPORTED_ACTIONS without "
            f"a safety classification: {sorted(unclassified)} — every action MUST "
            f"be content-mutating (backed up + reversible), reversible:false "
            f"(derived/cache allowlist), or presentation-only"
        )

        # No phantom classifications: every classified action really is a
        # supported action (keeps the sets honest if one is removed).
        phantom = union - set(EXECUTOR_SUPPORTED_ACTIONS)
        assert not phantom, (
            f"classified action(s) not in EXECUTOR_SUPPORTED_ACTIONS: "
            f"{sorted(phantom)}"
        )

        # The partition is the full set, exactly.
        assert union == set(EXECUTOR_SUPPORTED_ACTIONS)

    def test_reversible_false_actions_stays_empty(self):
        # The reversible:false allowlist is currently empty — every mutating
        # action is backed up. Adding an action here is a deliberate, reviewed
        # exception that bypasses backup; this lock forces that review by failing
        # if the set silently grows. (Partition alone would still pass.)
        assert _REVERSIBLE_FALSE_ACTIONS == frozenset(), (
            f"a mutating action was placed in _REVERSIBLE_FALSE_ACTIONS "
            f"(bypasses the backup pipeline): {sorted(_REVERSIBLE_FALSE_ACTIONS)} — "
            f"this needs an explicit safety review, not a silent allowlist add"
        )

    def test_classification_sets_are_disjoint(self):
        # Each action belongs to exactly one class — no action is both
        # backed-up and reversible:false, etc.
        sets = [
            _CONTENT_MUTATING_ACTIONS,
            _BACKED_UP_SUBPROCESS_ACTIONS,
            _REVERSIBLE_FALSE_ACTIONS,
            _PRESENTATION_ONLY_ACTIONS,
        ]
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                assert not (sets[i] & sets[j]), (
                    f"classification sets {i} and {j} overlap: {sets[i] & sets[j]}")

    # ----- 2a. every content-mutating action backs up + diffs + reverses ----

    @pytest.mark.parametrize("action", sorted(
        _CONTENT_MUTATING_ACTIONS - {"create_dir"}))
    def test_content_mutating_action_backs_up_diffs_and_restores(
        self, action, tmp_path, fake_home
    ):
        project_dir, archive, recipe, mutated_path, original = (
            _capstone_build_content_mutation(tmp_path, action))

        # Drive through auto_fix — the exact path the skill uses. It calls the
        # real execute_recipe (which routes content mutations through
        # _record_mutation, writing before/ + diffs/) AND records the action to
        # actions.json (which move-aware actions thread moved_to into) so restore
        # can reverse it. One real run exercises P2, P7 and S6 together. NO MOCKS.
        finding = {
            "id": f"capstone:{action}",
            "category": "capstone",
            "summary": f"capstone {action}",
            "fix_type": "prompted",
            "fix_recipe": recipe,
        }
        result = auto_fix(project_dir, [finding], archive, include_prompted=True)
        recorded = result["actions"]
        assert recorded and recorded[0]["action"] == "auto-fix", (
            f"{action}: auto_fix must record a successful auto-fix, got {recorded}")
        assert recorded[0]["before_hash"] != recorded[0]["after_hash"], (
            f"{action}: fixture must produce a real mutation (before != after hash)")

        # P2 — a before/ image was recorded, keyed to the mutated path
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(mutated_path))
        assert before_entry.exists(), (
            f"{action}: a real change MUST record a before/ image at {before_entry}")
        assert before_entry.read_bytes() == original, (
            f"{action}: the before/ image must hold the pre-mutation content")

        # P7 — a non-empty diffs/ entry was recorded, reconstructable
        diff_entry = (archive / "diffs"
                      / (_p0_doctor._sanitize_path(str(mutated_path)) + ".diff"))
        assert diff_entry.exists() and diff_entry.stat().st_size > 0, (
            f"{action}: a real change MUST record a non-empty diffs/ entry")

        # S6 — restore reverses it. delete_file removes the file; every other
        # content-mutating action leaves a changed or moved file. In all cases
        # restore must reconstruct the original path byte-identically (and for
        # move-aware actions, remove the destination — never a double file).
        res = _p0_doctor.restore(project_dir, archive, restore_all=True)
        assert res["restored"], f"{action}: restore must report what it reversed"
        assert mutated_path.exists(), (
            f"{action}: restore must reconstruct the original file")
        assert mutated_path.read_bytes() == original, (
            f"{action}: restore must revert the mutated path byte-identically")

        # move-aware actions: the destination created by the move must be gone
        # after restore — never a doubled file.
        if action in ("file_move", "renumber_duplicate"):
            moved_to = next(
                (a["moved_to"] for a in recorded if a.get("moved_to")), None)
            assert moved_to, f"{action}: a move-aware action must record moved_to"
            dest = Path(moved_to)
            if not dest.is_absolute():
                dest = project_dir / dest
            assert not dest.exists(), (
                f"{action}: restore must REMOVE the move destination — no double file")

    # ----- 2b. create_dir handled specially (dir create) -------------------

    def test_create_dir_creates_directory_and_is_owned_by_executor(
        self, tmp_path, fake_home
    ):
        # create_dir is content-mutating in kind (a filesystem mutation the
        # executor owns) but has no authored before-image: it is reversed by
        # removing the created directory, not by writing bytes back. Verify the
        # executor performs and owns the create.
        project_dir = build_fixture(tmp_path)
        target = project_dir / ".sweetclaude" / "state" / "doctor-runs"
        # ensure absent so the create is a real change
        if target.exists():
            shutil.rmtree(target)
        assert not target.exists(), "precondition: target dir absent"
        archive = create_archive(project_dir)

        result = execute_recipe(
            project_dir, {"action": "create_dir", "path": str(target)}, archive)

        assert result.success is True, f"create_dir must succeed: {result.error}"
        assert target.is_dir(), "create_dir must create the directory"

        # idempotent: re-running on an existing dir is a no-op success
        result2 = execute_recipe(
            project_dir, {"action": "create_dir", "path": str(target)}, archive)
        assert result2.success is True
        assert result2.before_hash == result2.after_hash, (
            "create_dir on an existing dir must be a no-op (before == after)")

    # ----- 2c. backed-up subprocess actions: regenerated targets are backed
    # up, diffed, and restorable (PRD P2/P7/T1h/S6) ------------------------

    def test_backed_up_subprocess_rebuild_cache_backs_up_diffs_restores(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        # rebuild_cache captures the cache file's bytes before rebuild, then
        # routes them through _record_mutation: before/ image + diffs/ entry,
        # reversible by restore. NO MOCKS — a real cache.py that rewrites bytes.
        from cache import db_path as _db_path

        assert "rebuild_cache" in _BACKED_UP_SUBPROCESS_ACTIONS
        project_dir = build_fixture(tmp_path)
        cache_path = Path(_db_path(str(project_dir)))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        original = b"CAPSTONE CACHE original bytes\n"
        cache_path.write_bytes(original)

        cache_script = patch_scripts_dir / "cache.py"
        cache_script.write_text(
            "#!/usr/bin/env python3\n"
            "import sys, os\n"
            "args = sys.argv\n"
            "pd = args[args.index('--project-dir') + 1]\n"
            "dbp = os.path.join(pd, '.sweetclaude', 'cache', 'roadmap.db')\n"
            "os.makedirs(os.path.dirname(dbp), exist_ok=True)\n"
            "open(dbp, 'wb').write(b'CAPSTONE CACHE rebuilt bytes\\n')\n"
            "sys.exit(0)\n"
        )
        archive = create_archive(project_dir)

        # drive through auto_fix — the skill's path — so the action is recorded
        # to actions.json and restore can reverse it.
        finding = {
            "id": "capstone:rebuild_cache",
            "category": "capstone",
            "summary": "capstone rebuild_cache",
            "fix_type": "prompted",
            "fix_recipe": {"action": "rebuild_cache"},
        }
        result = auto_fix(project_dir, [finding], archive, include_prompted=True)
        recorded = result["actions"]
        assert recorded and recorded[0]["action"] == "auto-fix", (
            f"rebuild_cache must record a successful auto-fix, got {recorded}")
        assert recorded[0]["before_hash"] != recorded[0]["after_hash"], (
            "a real cache rebuild must produce before != after")

        # P2
        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(cache_path))
        assert before_entry.exists() and before_entry.read_bytes() == original, (
            "rebuild_cache MUST record a before/ image of the cache")
        # P7
        diff_entry = (archive / "diffs"
                      / (_p0_doctor._sanitize_path(str(cache_path)) + ".diff"))
        assert diff_entry.exists() and diff_entry.stat().st_size > 0, (
            "rebuild_cache MUST record a non-empty diffs/ entry")
        # S6
        res = _p0_doctor.restore(project_dir, archive, restore_all=True)
        assert res["restored"], "restore must reverse the cache rebuild"
        assert cache_path.read_bytes() == original, (
            "restore must revert the cache byte-identically")

    def test_backed_up_subprocess_run_script_backs_up_diffs_restores(
        self, tmp_path, fake_home
    ):
        # run_script with regenerates=[session-state.yaml] backs up each
        # regenerated target, diffs it, and is reversed by restore. NO MOCKS.
        assert "run_script" in _BACKED_UP_SUBPROCESS_ACTIONS
        project_dir = build_fixture(tmp_path)
        ss = project_dir / ".sweetclaude" / "state" / "session-state.yaml"
        original = ss.read_bytes()

        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        stub = scripts_dir / "generate-session-state.sh"
        stub.write_text(
            "#!/bin/bash\n"
            "cat > .sweetclaude/state/session-state.yaml <<'EOF'\n"
            "paths:\n  product_base: .sweetclaude/CAPSTONE\n"
            "EOF\n"
        )
        stub.chmod(0o755)
        archive = create_archive(project_dir)

        finding = {
            "id": "capstone:run_script",
            "category": "capstone",
            "summary": "capstone run_script",
            "fix_type": "prompted",
            "fix_recipe": {
                "action": "run_script",
                "cmd": ["bash", str(stub)],
                "args": [],
                "regenerates": [".sweetclaude/state/session-state.yaml"],
            },
        }
        result = auto_fix(project_dir, [finding], archive, include_prompted=True)
        recorded = result["actions"]
        assert recorded and recorded[0]["action"] == "auto-fix", (
            f"run_script must record a successful auto-fix, got {recorded}")
        assert recorded[0]["before_hash"] != recorded[0]["after_hash"], (
            "regenerating session-state must produce before != after")

        before_entry = archive / "before" / _p0_doctor._sanitize_path(str(ss))
        assert before_entry.exists() and before_entry.read_bytes() == original, (
            "run_script MUST back up each regenerated target")
        diff_entry = (archive / "diffs"
                      / (_p0_doctor._sanitize_path(str(ss)) + ".diff"))
        assert diff_entry.exists() and diff_entry.stat().st_size > 0, (
            "run_script MUST record a non-empty diffs/ entry")
        res = _p0_doctor.restore(project_dir, archive, restore_all=True)
        assert res["restored"], "restore must reverse the regenerated target"
        assert ss.read_bytes() == original, (
            "restore must revert the regenerated target byte-identically")

    # ----- 3. no skill-side direct file writes remain ----------------------

    def test_skill_performs_no_direct_file_writes(self):
        # S3 — the skill layer never writes files directly: every mutation goes
        # through a doctor.py subcommand. Only READ-ONLY inline python may
        # remain. This is the structural backstop that keeps every mutation on
        # the backed-up executor path.
        skill_path = Path(__file__).parents[1] / "skills" / "doctor" / "SKILL.md"
        skill = skill_path.read_text(encoding="utf-8")

        # No write-mode file opens in inline python (open(..., "w"/"a"/"x"...)).
        import re
        write_opens = re.findall(r"open\([^)]*,\s*['\"][wax]", skill)
        assert not write_opens, (
            f"SKILL.md must not open files for writing inline: {write_opens}")

        # No filesystem-mutation utilities invoked from the skill — every
        # mutation must route through a doctor.py subcommand.
        # Write-operation patterns only — NOT bare filenames (the skill may name
        # doctor-suppressions.json in prose explaining it does NOT write it). Any
        # actual inline write (incl. re-introducing the V9 suppress-write) uses one
        # of these and is caught.
        for forbidden in (
            "json.dump(",                # writing JSON inline (the V9 suppress-write pattern)
            ".write_text(",
            ".write_bytes(",
            "shutil.move(",
            "shutil.copy",
        ):
            assert forbidden not in skill, (
                f"SKILL.md must not perform a direct file mutation ({forbidden!r}) — "
                f"route it through a doctor.py subcommand")

        # Positive: the skill DOES drive mutations via the executor subcommands.
        assert "doctor.py" in skill, (
            "SKILL.md must invoke doctor.py subcommands for mutations")

        # Any remaining inline `python3 -c` must be read-only (no assignment to
        # a file write, no os.replace/rename). The two known inline blocks only
        # json.load + print.
        for line in skill.splitlines():
            if "python3 -c" in line:
                lowered = line.lower()
                assert "os.replace" not in lowered and "os.rename" not in lowered, (
                    f"inline python in SKILL.md must be read-only, found: {line}")
                assert not re.search(r"open\([^)]*,\s*['\"][wax]", line), (
                    f"inline python in SKILL.md must be read-only, found: {line}")


# ---------------------------------------------------------------------------
# P2 Tier-4 fallback surfacing — SCRIPT contract (doctor remediation plan §5,
# §8.4). The terminal_fallback object must be COMPLETE (full-migration /
# re-adopt / purge) and carry the script-computed triggers that tell the SKILL
# WHEN to surface the Tier-4 menu. This is the script half only — these tests
# never assert the skill renders/invokes the AskUserQuestion menu (false-green
# guard #3); that is a separate behavioral increment.
#
# NO MOCKS — real fixtures, a real stub runner emitting the line format, and a
# real recovery-runs execution-manifest carrying recover_project's repair-loop
# signal.
# ---------------------------------------------------------------------------

import doctor as _p2_doctor


class TestP2Tier4Fallback:

    # ----- 1. the fallback object is complete: full-migration / re-adopt /
    #          purge -----------------------------------------------------------

    def test_terminal_fallback_includes_purge_clean_break_option(self):
        from doctor import _build_terminal_fallback

        tf = _build_terminal_fallback({"status": "compatibility-mode"})
        opts = {o["id"]: o for o in tf["options"]}

        # the existing two options remain
        assert "full-migration" in opts
        assert "re-adopt" in opts

        # the new clean-break purge option
        assert "purge" in opts, (
            "terminal_fallback must offer a 'purge' clean-break option alongside "
            "full-migration and re-adopt")
        purge = opts["purge"]
        assert purge["capability"] == "purge", (
            "purge option must route to the purge capability (sweetclaude:purge)")
        assert purge["no_data_loss"] is False, (
            "purge is a clean break — it does NOT preserve data, so no_data_loss "
            "must be False")
        assert purge["snapshot_first"] is True, (
            "purge must still snapshot first (last-resort safety net)")
        assert "clean break" in purge["label"].lower(), (
            "purge label must communicate it is a clean break with no legacy "
            f"archive, got: {purge['label']!r}")
        assert "no legacy archive" in purge["label"].lower()

    # ----- 2. re-adopt hands off to init, not a nonexistent 'adopt' skill ----

    def test_readopt_option_references_init_not_adopt(self):
        from doctor import _build_terminal_fallback

        tf = _build_terminal_fallback({"status": "compatibility-mode"})
        readopt = {o["id"]: o for o in tf["options"]}["re-adopt"]

        # V8 / plan §8.4: re-adopt archives .sweetclaude/ then routes to
        # sweetclaude:init — there is NO sweetclaude:adopt skill.
        assert readopt["capability"] == "init", (
            "re-adopt must route to the 'init' re-onboard entry point (V8), "
            f"not 'adopt'; got capability={readopt['capability']!r}")
        # the executable that archives + hands to init is still re_adopt.py
        assert readopt.get("executable") == "scripts/recovery/re_adopt.py", (
            "re_adopt.py remains the executable that archives state and hands to init")
        # the ghost 'adopt' must not appear anywhere in the option metadata
        assert "adopt" not in str(readopt.get("capability", "")), (
            "the 'adopt' ghost capability must be gone")

    # ----- 3. healthy project: every trigger False --------------------------

    def test_healthy_project_all_triggers_false(self, tmp_path, fake_home):
        from doctor import _build_terminal_fallback, build_project_state

        state = build_project_state(build_fixture(tmp_path))
        tf = _build_terminal_fallback(
            {"status": "no-maintenance-action"}, state=state, findings=[])
        triggers = tf["triggers"]

        assert triggers["out_of_chain"] is False
        assert triggers["uncorrectable_after_repair"] is False
        assert triggers["recovery_looped"] is False
        assert triggers["user_requested"] is False  # default; skill-set only
        assert triggers["any"] is False, (
            "a healthy project must not surface Tier-4 — triggers.any must be False")

    # ----- 4. out_of_chain: runner reports chain=broken ---------------------

    def test_out_of_chain_true_when_runner_reports_chain_broken(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        from doctor import _build_terminal_fallback, build_project_state

        project_dir = build_fixture(tmp_path)
        # A REAL stub runner that emits the --report-drift-for-skill line format
        # with a chain=broken finding (schema outside the supported migration
        # chain). NO MOCKS — doctor shells out to this exactly as in production.
        runner_path = patch_scripts_dir / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--report-drift-for-skill' in sys.argv:\n"
            "    print('DRIFT_COUNT=1')\n"
            "    print('FINDING|sweetclaude.yaml|v9->v2|chain=broken')\n"
            "    sys.exit(0)\n"
            "sys.exit(0)\n"
        )

        state = build_project_state(project_dir)
        tf = _build_terminal_fallback(
            {"status": "no-maintenance-action"}, state=state, findings=[])

        assert tf["triggers"]["out_of_chain"] is True, (
            "a runner FINDING with chain=broken must set out_of_chain True")
        assert tf["triggers"]["any"] is True

    def test_out_of_chain_false_when_runner_reports_chain_ok(
        self, tmp_path, fake_home, patch_scripts_dir
    ):
        from doctor import _build_terminal_fallback, build_project_state

        project_dir = build_fixture(tmp_path)
        runner_path = patch_scripts_dir / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--report-drift-for-skill' in sys.argv:\n"
            "    print('DRIFT_COUNT=1')\n"
            "    print('FINDING|sweetclaude.yaml|v1->v2|chain=ok')\n"
            "    sys.exit(0)\n"
            "sys.exit(0)\n"
        )
        state = build_project_state(project_dir)
        tf = _build_terminal_fallback(
            {"status": "no-maintenance-action"}, state=state, findings=[])
        assert tf["triggers"]["out_of_chain"] is False, (
            "chain=ok must NOT set out_of_chain")

    def test_out_of_chain_false_when_runner_absent_no_crash(
        self, tmp_path, fake_home
    ):
        from doctor import _build_terminal_fallback, build_project_state

        # No runner present (migration_runner_path is None). Must degrade
        # gracefully — trigger False, no crash.
        project_dir = build_fixture(tmp_path)
        state = build_project_state(project_dir)
        state.migration_runner_path = None  # simulate absent runner explicitly
        tf = _build_terminal_fallback(
            {"status": "no-maintenance-action"}, state=state, findings=[])
        assert tf["triggers"]["out_of_chain"] is False

    # ----- 5. uncorrectable_after_repair: sweetclaude.yaml unparseable ------

    def test_uncorrectable_after_repair_true_when_yaml_unparseable(
        self, tmp_path, fake_home
    ):
        from doctor import _build_terminal_fallback, build_project_state

        # A genuinely broken core config — a state-file repair cannot fix a
        # core parse error, so Tier-4 is the honest path. Reuses
        # check_state_integrity's parse detection.
        project_dir = build_fixture(tmp_path, overrides={"sweetclaude_yaml": None})
        sc_yaml = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
        sc_yaml.write_text("framework: {installed_version: '4.0.8'\n  bad: [unclosed\n")

        state = build_project_state(project_dir)
        tf = _build_terminal_fallback(
            {"status": "no-maintenance-action"}, state=state, findings=[])

        assert tf["triggers"]["uncorrectable_after_repair"] is True, (
            "an unparseable core sweetclaude.yaml must set uncorrectable_after_repair")
        assert tf["triggers"]["any"] is True

    def test_uncorrectable_after_repair_false_when_healthy(self, tmp_path, fake_home):
        from doctor import _build_terminal_fallback, build_project_state

        state = build_project_state(build_fixture(tmp_path))
        tf = _build_terminal_fallback(
            {"status": "no-maintenance-action"}, state=state, findings=[])
        assert tf["triggers"]["uncorrectable_after_repair"] is False

    # ----- 6. recovery_looped: consume recover_project's stop signal --------

    def test_recovery_looped_true_when_recovery_state_signals_loop(
        self, tmp_path, fake_home
    ):
        from doctor import _build_terminal_fallback, build_project_state

        # Write a REAL recovery-runs execution-manifest exactly as
        # recover_project.resume_project does when should_stop_repair_loop fires:
        # status=stopped + repair_loop.stop=True. Doctor must READ this signal,
        # not re-derive it. NO MOCKS.
        project_dir = build_fixture(tmp_path)
        run_dir = (project_dir / ".sweetclaude" / "state" / "recovery-runs"
                   / "run-20260609-000000")
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "project_dir": str(project_dir),
            "command": "resume",
            "status": "stopped",
            "resume_count": 3,
            "repair_loop": {
                "stop": True,
                "reason": "attempt-budget-exhausted",
                "route": "backlog-or-escalation",
            },
        }
        (run_dir / "execution-manifest.json").write_text(json.dumps(manifest))

        state = build_project_state(project_dir)
        tf = _build_terminal_fallback(
            {"status": "no-maintenance-action"}, state=state, findings=[])

        assert tf["triggers"]["recovery_looped"] is True, (
            "a recovery manifest with repair_loop.stop=True must set recovery_looped")
        assert tf["triggers"]["any"] is True

    def test_recovery_looped_false_when_no_recovery_state(self, tmp_path, fake_home):
        from doctor import _build_terminal_fallback, build_project_state

        # No recovery-runs at all — must degrade gracefully to False.
        state = build_project_state(build_fixture(tmp_path))
        tf = _build_terminal_fallback(
            {"status": "no-maintenance-action"}, state=state, findings=[])
        assert tf["triggers"]["recovery_looped"] is False

    def test_recovery_looped_false_when_recovery_progressing(
        self, tmp_path, fake_home
    ):
        from doctor import _build_terminal_fallback, build_project_state

        # A recovery run that is progressing (not stopped) must NOT trip the
        # trigger.
        project_dir = build_fixture(tmp_path)
        run_dir = (project_dir / ".sweetclaude" / "state" / "recovery-runs"
                   / "run-20260609-111111")
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "project_dir": str(project_dir),
            "command": "resume",
            "status": "in_progress",
            "resume_count": 1,
            "repair_loop": {"stop": False, "reason": "progress-or-budget-remains"},
        }
        (run_dir / "execution-manifest.json").write_text(json.dumps(manifest))

        state = build_project_state(project_dir)
        tf = _build_terminal_fallback(
            {"status": "no-maintenance-action"}, state=state, findings=[])
        assert tf["triggers"]["recovery_looped"] is False

    # ----- 7. user_requested is skill-set, defaults False -------------------

    def test_user_requested_defaults_false_and_is_skill_set(self, tmp_path, fake_home):
        from doctor import _build_terminal_fallback, build_project_state

        state = build_project_state(build_fixture(tmp_path))
        tf = _build_terminal_fallback(
            {"status": "no-maintenance-action"}, state=state, findings=[])
        # user_requested is never script-computed — it is a flag the skill sets
        # on explicit user request. The script always reports the default.
        assert tf["triggers"]["user_requested"] is False
        # and it does not feed `any` (which covers only the 3 script-computed
        # triggers).
        assert tf["triggers"]["any"] is False

    # ----- 8. backward compat: no state/findings still yields safe object ---

    def test_no_state_yields_all_false_triggers(self):
        from doctor import _build_terminal_fallback

        # The existing call site / older callers pass only maintenance_route.
        # The object must still carry a safe triggers dict (all False, no crash).
        tf = _build_terminal_fallback({"status": "supported-migration-available"})
        triggers = tf["triggers"]
        assert triggers["out_of_chain"] is False
        assert triggers["uncorrectable_after_repair"] is False
        assert triggers["recovery_looped"] is False
        assert triggers["user_requested"] is False
        assert triggers["any"] is False


# ---------------------------------------------------------------------------
# P2.2 Tier-4 fallback surfacing — SKILL RENDER half (doctor remediation plan
# §5, §8.4). The script contract landed in P2.1; this is the skill that reads
# resolution_summary.terminal_fallback and renders the last-resort menu. These
# are structural assertions over SKILL.md — the render logic must be present,
# delegate every mutation to a script/skill, and never name a ghost
# 'sweetclaude:adopt' skill.
# ---------------------------------------------------------------------------


class TestP2SkillRendersTier4:

    def _skill(self):
        return (
            Path(__file__).parents[1] / "skills" / "doctor" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_skill_has_step_2c_reading_terminal_fallback_triggers(self):
        skill = self._skill()
        assert "Step 2c" in skill, (
            "SKILL.md must add a Step 2c that surfaces the Tier-4 fallback")
        # it reads the script-provided fallback object and its triggers
        assert "terminal_fallback" in skill, (
            "Step 2c must read resolution_summary.terminal_fallback")
        assert "triggers" in skill, (
            "Step 2c must gate on terminal_fallback.triggers")
        assert "triggers.any" in skill or "triggers[\"any\"]" in skill or \
            "`any`" in skill, (
            "Step 2c must surface the menu only when triggers.any is True "
            "(or on explicit user request)")

    def test_step_2c_offers_reonboard_and_remove_routes(self):
        skill = self._skill()
        # Re-onboard route invokes the re_adopt CLI (no skill-side mv) then init.
        assert "re_adopt.py" in skill, (
            "Step 2c re-onboard route must invoke the re_adopt.py script "
            "(archives .sweetclaude/ — no skill-side mv)")
        assert "re_adopt.py execute" in skill, (
            "Step 2c re-onboard route must call the execute subcommand")
        assert "sweetclaude:init" in skill, (
            "Step 2c re-onboard route hands off to sweetclaude:init")
        # Remove route delegates to the purge skill (clean break).
        assert "sweetclaude:purge" in skill, (
            "Step 2c remove route must delegate to sweetclaude:purge")
        # legacy archive is preserved, not auto-imported
        assert ".sweetclaude.legacy" in skill, (
            "Step 2c must state the re-onboard archives to .sweetclaude.legacy/")

    def test_step_2c_does_not_reference_ghost_adopt_skill(self):
        skill = self._skill()
        # There is NO sweetclaude:adopt skill — re-adopt routes to init.
        assert "sweetclaude:adopt" not in skill, (
            "SKILL.md must not reference a nonexistent sweetclaude:adopt skill; "
            "re-adopt routes to sweetclaude:init")

    def test_step_2c_uses_no_inline_file_mutation(self):
        # Step 2c must not introduce any skill-side mv/cp/write — every mutation
        # routes through re_adopt.py (execute) or sweetclaude:purge. This is the
        # same invariant the P1.8 capstone enforces globally; assert it here for
        # the specific shell-mutation forms a re-onboard would tempt.
        skill = self._skill()
        # isolate the Step 2c section so we test the new render logic precisely
        start = skill.index("Step 2c")
        nxt = skill.find("\n## ", start)
        section = skill[start:nxt] if nxt != -1 else skill[start:]
        import re
        for forbidden in ("mv ", "cp ", "shutil.move", "shutil.copy",
                          ".write_text(", ".write_bytes(", "json.dump("):
            assert forbidden not in section, (
                f"Step 2c must not perform a direct file mutation ({forbidden!r}) "
                f"— delegate to re_adopt.py / sweetclaude:purge")
        assert not re.search(r"open\([^)]*,\s*['\"][wax]", section), (
            "Step 2c must not open files for writing inline")


# ---------------------------------------------------------------------------
# P4 final remediation increment — T3b, F5.1.4, T3e (doctor remediation plan
# §8.2). T3b: taxonomy migration becomes a runnable prompted fix routing to
# sweetclaude:migrate once migrate_taxonomy.py grows a CLI entrypoint (LOCKED:
# build the CLI). F5.1.4: a _scan dedup pass where a cross-location duplicate
# supersedes the same-directory/file duplicate-id for the same id. T3e: the
# Step-7 prompted-fix delegation handlers carry the re-scan-after-delegation
# instruction the Step 1a handoffs have.
# ---------------------------------------------------------------------------


class TestT3bTaxonomyMigrationRoutesToMigrate:
    """The taxonomy-drift finding must become a runnable prompted migration that
    routes to sweetclaude:migrate — not a capability_blocked_migration — once
    migrate_taxonomy.py exposes a CLI entrypoint."""

    def test_real_migrate_taxonomy_has_cli_entrypoint(self):
        # The locked decision is to build the CLI on the real script. After GREEN
        # the real migrate_taxonomy.py must report a CLI entrypoint.
        script = _doctor_module._SCRIPTS_DIR / "migrate" / "migrate_taxonomy.py"
        assert _script_has_cli_entrypoint(script), (
            "migrate_taxonomy.py must expose a CLI entrypoint "
            "(argparse + if __name__ == '__main__')"
        )

    def test_taxonomy_prefix_project_emits_runnable_prompted_migration(
        self, tmp_path, fake_home
    ):
        # Uses the REAL _SCRIPTS_DIR so the real migrate_taxonomy.py (with the new
        # CLI) is consulted. Today the finding is downgraded to
        # capability_blocked_migration; after the fix it is a runnable prompted
        # migration that routes to migrate_taxonomy.py / sweetclaude:migrate.
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "STORY-001-old.md", "content": "# Old story"},
                {"name": "BUG-002-old.md", "content": "# Old bug"},
            ],
        })
        state = build_project_state(project_dir)
        result = _scan(state)

        f = next(
            x for x in result["findings"]
            if x["id"] == "migration-currency:taxonomy-drift:old-prefixes"
        )
        recipe = f.get("fix_recipe") or {}
        assert recipe.get("type") != "capability_blocked_migration", (
            f"taxonomy migration must not be capability-blocked, got recipe: {recipe}"
        )
        assert f["fix_type"] == "prompted", (
            f"taxonomy migration must be a prompted (runnable) fix, got: {f['fix_type']}"
        )
        assert recipe.get("type") == "migration", (
            f"taxonomy migration recipe must be type=migration, got: {recipe}"
        )
        assert recipe.get("script") == "migrate_taxonomy.py", (
            f"taxonomy migration recipe must route to migrate_taxonomy.py, got: {recipe}"
        )

    def test_skill_step7_routes_taxonomy_to_migrate_not_blocked(self):
        skill = (
            Path(__file__).parents[1] / "skills" / "doctor" / "SKILL.md"
        ).read_text(encoding="utf-8")
        start = skill.index("## Step 7")
        nxt = skill.find("\n## ", start)
        section = skill[start:nxt] if nxt != -1 else skill[start:]
        # The taxonomy-migration handler must reference the migrate_taxonomy.py
        # script and route to sweetclaude:migrate, no longer blocking it.
        assert "migrate_taxonomy.py" in section, (
            "Step 7 must still describe the taxonomy-migration handler"
        )
        assert "sweetclaude:migrate" in section, (
            "Step 7 must route taxonomy migration to sweetclaude:migrate"
        )
        # The old block-and-route-to-recover language must be gone.
        assert "route the\n  user to `/sweetclaude:recover` or manual review" not in section, (
            "Step 7 must no longer block taxonomy migration to recover/manual review"
        )


class TestF514ScanDedupCrossLocationSupersedes:
    """_scan must drop the same-directory/file duplicate-id finding for an id when
    a cross-location duplicate finding already covers that id; the cross-location
    finding supersedes. Other duplicate findings are untouched."""

    def test_cross_location_dup_suppresses_same_dir_duplicate_id(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-001-test.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "story", "title": "Test", "status": "active",
                }},
            ],
            "roadmap_files": [
                {"name": "ISSUE-001-dup.md", "frontmatter": {
                    "id": "ISSUE-001", "type": "milestone", "title": "Dup", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        result = _scan(state)
        ids = [f["id"] for f in result["findings"]]

        assert "storage-lint:cross-location-duplicate-id:ISSUE-001" in ids, (
            f"cross-location duplicate finding must remain, got: {ids}"
        )
        assert "file-diagnostics:duplicate-id:ISSUE-001" not in ids, (
            f"same-directory duplicate-id must be superseded by the cross-location "
            f"finding for ISSUE-001, got: {ids}"
        )

    def test_same_dir_only_dup_still_fires(self, tmp_path, fake_home):
        # No cross-location collision — a purely same-directory duplicate must
        # still produce its own duplicate-id finding.
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [
                {"name": "ISSUE-005-first.md", "frontmatter": {
                    "id": "ISSUE-005", "type": "story", "title": "First", "status": "active",
                }},
                {"name": "ISSUE-005-second.md", "frontmatter": {
                    "id": "ISSUE-005", "type": "story", "title": "Second", "status": "active",
                }},
            ],
        })
        state = build_project_state(project_dir)
        result = _scan(state)
        ids = [f["id"] for f in result["findings"]]

        assert "file-diagnostics:duplicate-id:ISSUE-005" in ids, (
            f"same-directory-only duplicate-id must still fire, got: {ids}"
        )
        assert "storage-lint:cross-location-duplicate-id:ISSUE-005" not in ids, (
            f"no cross-location finding should exist for a same-dir-only dup, got: {ids}"
        )


class TestT3eStep7RescanAfterDelegation:
    """Each Step-7 prompted-fix delegation handler must carry the
    'run the full scan and continue with fresh findings' instruction that the
    Step 1a delegation handoffs carry."""

    def _step7(self):
        skill = (
            Path(__file__).parents[1] / "skills" / "doctor" / "SKILL.md"
        ).read_text(encoding="utf-8")
        start = skill.index("## Step 7")
        nxt = skill.find("\n## ", start)
        return skill[start:nxt] if nxt != -1 else skill[start:]

    def test_step7_handlers_reference_rescan_after_delegation(self):
        section = self._step7()
        lowered = section.lower()
        # The Step 1a handoffs say "run the full scan and continue with ... findings".
        # Step 7's delegation handlers must carry the same re-scan instruction.
        assert "run the full scan" in lowered or "re-run the scan" in lowered or \
               "rerun the scan" in lowered or "run the scan" in lowered, (
            "Step 7 delegation handlers must instruct running the full scan after "
            "the delegated skill/flow completes"
        )

    def test_each_step7_delegation_handler_has_rescan(self):
        section = self._step7()
        # The four prompted-fix delegations in Step 7: schema migration (runner.py),
        # taxonomy (migrate_taxonomy.py), v3-to-v4 (migrate-v3-to-v4.py), and
        # purge/re-onboard. Each handler bullet must mention rescanning/continuing
        # after the delegated skill completes.
        handlers = ["runner.py", "migrate_taxonomy.py", "migrate-v3-to-v4.py", "Purge"]
        bullets = [b for b in section.split("\n- ") if b.strip()]
        for handler in handlers:
            matching = [b for b in bullets if handler in b]
            assert matching, f"Step 7 must contain a delegation handler for {handler}"
            for b in matching:
                low = b.lower()
                assert ("scan" in low and ("continue" in low or "fresh" in low or "again" in low)), (
                    f"Step 7 handler for {handler} must carry the "
                    f"re-scan-after-delegation instruction; got bullet: {b[:300]!r}"
                )


# ---------------------------------------------------------------------------
# Suppression recovery: finding-id validation + unsuppress (improvement request)
# ---------------------------------------------------------------------------

class TestSuppressionRecovery:
    def test_suppress_rejects_multiline_finding_id(self, tmp_path):
        blob = "a:b:c\nd:e:f\ng:h:i"
        res = suppress_finding(tmp_path, blob)
        assert res["suppressed"] is False
        assert "control characters" in res["error"]
        assert load_suppressions(tmp_path) == []  # nothing written

    def test_suppress_rejects_whitespace_padded_id(self, tmp_path):
        res = suppress_finding(tmp_path, "  cat:check:tgt  ")
        assert res["suppressed"] is False
        assert load_suppressions(tmp_path) == []

    def test_suppress_accepts_valid_id(self, tmp_path):
        fid = "state-integrity:phase-missing:phase.yaml"
        res = suppress_finding(tmp_path, fid)
        assert res["suppressed"] is True
        assert any(e["finding_id"] == fid for e in load_suppressions(tmp_path))

    def test_unsuppress_removes_one_entry(self, tmp_path):
        suppress_finding(tmp_path, "a:b:c")
        suppress_finding(tmp_path, "d:e:f")
        res = unsuppress_finding(tmp_path, finding_id="a:b:c")
        assert res["removed_count"] == 1
        assert {e.get("finding_id") for e in load_suppressions(tmp_path)} == {"d:e:f"}

    def test_unsuppress_absent_id_is_noop_success(self, tmp_path):
        suppress_finding(tmp_path, "a:b:c")
        res = unsuppress_finding(tmp_path, finding_id="zzz:zz:zz")
        assert res["unsuppressed"] is True
        assert res["removed_count"] == 0
        assert {e.get("finding_id") for e in load_suppressions(tmp_path)} == {"a:b:c"}

    def test_unsuppress_prune_malformed_recovers_corrupted_ledger(self, tmp_path):
        # The Gap-1 incident: a corrupted ledger written before validation existed.
        save_suppressions(tmp_path, [
            {"finding_id": "good:check:tgt", "suppressed_at": "x"},
            {"finding_id": "bad1\nbad2", "suppressed_at": "x"},
            {"suppressed_at": "x"},  # missing finding_id
        ])
        res = unsuppress_finding(tmp_path, prune_malformed=True)
        assert res["removed_count"] == 2
        assert [e.get("finding_id") for e in load_suppressions(tmp_path)] == ["good:check:tgt"]

    def test_main_suppress_rejects_and_exits_nonzero(self, tmp_path, capsys):
        rc = main(["suppress", "--project-dir", str(tmp_path), "--finding-id", "a:b:c\nd:e:f"])
        assert rc == 1
        assert load_suppressions(tmp_path) == []

    def test_main_unsuppress_requires_a_target(self, tmp_path, capsys):
        rc = main(["unsuppress", "--project-dir", str(tmp_path)])
        assert rc == 1


# ---------------------------------------------------------------------------
# Byte-identical duplicate work items: resolve_identical_duplicate (Gap 3)
# ---------------------------------------------------------------------------

class TestIdenticalDuplicateResolution:
    def _fixture(self, tmp_path, *, created_differs=False):
        bl = {"id": "ISSUE-044", "type": "story", "title": "Same", "status": "new"}
        rm = dict(bl)
        if created_differs:
            bl["created"] = "2026-01-01"
            rm["created"] = "2026-02-02"
        return build_fixture(tmp_path, overrides={
            "backlog_files": [{"name": "ISSUE-044-x.md", "frontmatter": bl}],
            "roadmap_files": [{"name": "ISSUE-044-x.md", "frontmatter": rm}],
        })

    def _dup_finding(self, project_dir):
        state = build_project_state(project_dir)
        return next(
            x for x in check_storage_lint(state)
            if x.id == "storage-lint:cross-location-duplicate-id:ISSUE-044"
        )

    def test_identical_cross_location_offers_resolve_recipe(self, tmp_path, fake_home):
        project_dir = self._fixture(tmp_path)
        _make_cache_stub(project_dir)
        f = self._dup_finding(project_dir)
        assert f.fix_recipe["type"] == "resolve_identical_duplicate"
        assert "/backlog/" in f.fix_recipe["recommended_keep"]
        assert "/roadmap/" in f.fix_recipe["recommended_remove"]

    def test_identical_ignores_volatile_created(self, tmp_path, fake_home):
        project_dir = self._fixture(tmp_path, created_differs=True)
        _make_cache_stub(project_dir)
        f = self._dup_finding(project_dir)
        assert f.fix_recipe["type"] == "resolve_identical_duplicate"

    def test_divergent_cross_location_keeps_renumber(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "backlog_files": [{"name": "ISSUE-044-x.md", "frontmatter": {
                "id": "ISSUE-044", "type": "story", "title": "One", "status": "new"}}],
            "roadmap_files": [{"name": "ISSUE-044-y.md", "frontmatter": {
                "id": "ISSUE-044", "type": "story", "title": "DIFFERENT", "status": "active"}}],
        })
        _make_cache_stub(project_dir)
        f = self._dup_finding(project_dir)
        assert f.fix_recipe["type"] == "renumber_duplicate"

    def test_resolve_remove_is_deleted_and_backed_up(self, tmp_path, fake_home):
        project_dir = self._fixture(tmp_path)
        _make_cache_stub(project_dir)
        f = self._dup_finding(project_dir)
        remove = f.fix_recipe["recommended_remove"]
        keep = f.fix_recipe["recommended_keep"]
        archive = create_archive(project_dir)
        res = execute_recipe(project_dir, {"action": "delete_file", "file": remove}, archive)
        assert res.success
        assert not Path(remove).exists()      # the duplicate copy is gone
        assert Path(keep).exists()            # the survivor remains
        assert res.backup_path is not None    # before-image archived -> restore-reversible


# ---------------------------------------------------------------------------
# ISSUE-235: orphan resolution through the executor (resolve_orphans)
# ---------------------------------------------------------------------------

class TestResolveOrphansExecutor:
    """Orphan mutations run through doctor's backup pipeline; update's skill
    no longer invokes migrate-v3-to-v4.py. One recipe per orphan file."""

    REGISTRY = ".sweetclaude/state/orphan-registry.yaml"

    def _plant_orphan(self, project_dir, name="BL-010-legacy.md", item_id="BL-010"):
        bl = project_dir / ".sweetclaude" / "product" / "backlog"
        bl.mkdir(parents=True, exist_ok=True)
        p = bl / name
        p.write_text(
            f"---\nid: {item_id}\ntitle: Legacy item {item_id}\n"
            f"status: new\ntype: story\n---\n\nlegacy body\n"
        )
        return p

    def _finding(self, project_dir, orphan_action, abs_path):
        rel = str(Path(abs_path).relative_to(project_dir))
        return {
            "id": f"migration-currency:orphan:{Path(abs_path).name}",
            "category": "migration_currency",
            "summary": f"orphan {Path(abs_path).name}",
            "fix_type": "prompted",
            "fix_recipe": {
                "action": "resolve_orphans",
                "orphan_action": orphan_action,
                "path": rel,
            },
        }

    def test_acknowledge_writes_registry_and_restore_reverses(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        orphan = self._plant_orphan(project_dir)
        rel = str(orphan.relative_to(project_dir))
        archive = create_archive(project_dir)

        result = auto_fix(
            project_dir,
            [self._finding(project_dir, "acknowledge", orphan)],
            archive, include_prompted=True,
        )
        assert result["actions"][0].get("error") is None
        reg = project_dir / self.REGISTRY
        assert reg.exists() and rel in reg.read_text()
        assert orphan.exists(), "acknowledge must not touch the orphan file"

        res = _p0_doctor.restore(project_dir, archive, restore_all=True)
        assert res["restored"], "acknowledge must be restore-reversible"
        assert rel not in (reg.read_text() if reg.exists() else "")

    def test_archive_moves_file_and_restore_reverses_move(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        orphan = self._plant_orphan(project_dir)
        original_bytes = orphan.read_bytes()
        archive = create_archive(project_dir)

        result = auto_fix(
            project_dir,
            [self._finding(project_dir, "archive", orphan)],
            archive, include_prompted=True,
        )
        assert result["actions"][0].get("error") is None
        assert not orphan.exists(), "archive must move the orphan out"
        archived_dir = (
            project_dir / ".sweetclaude" / "product" / "archive" / "orphans"
        )
        archived = list(archived_dir.glob("*.md"))
        assert len(archived) == 1 and archived[0].read_bytes() == original_bytes

        res = _p0_doctor.restore(project_dir, archive, restore_all=True)
        assert res["restored"], "archive must be restore-reversible"
        assert orphan.exists() and orphan.read_bytes() == original_bytes
        assert not list(archived_dir.glob("*.md")), (
            "restore must reverse the move, not duplicate the file"
        )

    def test_reonboard_creates_issue_and_restore_deletes_created(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        orphan = self._plant_orphan(project_dir)
        original_bytes = orphan.read_bytes()
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        before_files = set(backlog.glob("ISSUE-*.md"))
        archive = create_archive(project_dir)

        result = auto_fix(
            project_dir,
            [self._finding(project_dir, "reonboard", orphan)],
            archive, include_prompted=True,
        )
        assert result["actions"][0].get("error") is None
        created = set(backlog.glob("ISSUE-*.md")) - before_files
        assert len(created) == 1, "reonboard must create exactly one ISSUE file"
        new_text = created.pop().read_text()
        assert "reonboarded_from" in new_text
        assert orphan.exists(), "reonboard leaves the source in place"

        res = _p0_doctor.restore(project_dir, archive, restore_all=True)
        assert res["restored"], "reonboard must be restore-reversible"
        assert set(backlog.glob("ISSUE-*.md")) == before_files, (
            "restore must delete the created ISSUE file"
        )
        assert orphan.exists() and orphan.read_bytes() == original_bytes

    def test_unknown_orphan_action_fails_without_mutation(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        orphan = self._plant_orphan(project_dir)
        original_bytes = orphan.read_bytes()
        archive = create_archive(project_dir)

        rel = str(orphan.relative_to(project_dir))
        res = execute_recipe(
            project_dir,
            {"action": "resolve_orphans", "orphan_action": "delete", "path": rel},
            archive,
        )
        assert res.success is False and res.error
        assert orphan.exists() and orphan.read_bytes() == original_bytes
        assert not (project_dir / self.REGISTRY).exists()

    def test_missing_path_fails_cleanly(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path)
        archive = create_archive(project_dir)
        res = execute_recipe(
            project_dir,
            {"action": "resolve_orphans", "orphan_action": "archive",
             "path": ".sweetclaude/product/backlog/BL-404-nope.md"},
            archive,
        )
        assert res.success is False and res.error

    def test_migration_currency_emits_per_file_resolve_orphans_findings(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        self._plant_orphan(project_dir, "BL-010-legacy.md", "BL-010")
        self._plant_orphan(project_dir, "BUG-001-legacy.md", "BUG-001")

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)
        orphan_findings = [
            f for f in findings
            if f.fix_recipe.get("type") == "resolve_orphans"
        ]
        assert len(orphan_findings) == 2, (
            "one prompted resolve_orphans finding per orphan file"
        )
        for f in orphan_findings:
            assert f.fix_type == "prompted"
            assert f.fix_recipe.get("file"), "recipe must carry the orphan path"
