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
    auto_cleanup_suppressions,
    main,
    _apply_transform,
    _atomic_write,
)


# ---------------------------------------------------------------------------
# E5-S01: Fixture builder
# ---------------------------------------------------------------------------

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

    runner_dir = project_dir / "scripts" / "migrations"
    runner_dir.mkdir(parents=True, exist_ok=True)
    (runner_dir / "runner.py").write_text("#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps([]))\n")

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
        path = project_dir / "hooks" / hf["name"]
        path.write_text(hf["content"])

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
        assert (project / "hooks" / "test-hook.sh").exists()

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
        assert f.fix_type == "report-only"

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
        assert f.fix_type == "report-only"

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
        self, tmp_path, fake_home
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
        self, tmp_path, fake_home
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
    def test_no_drift_when_cache_max_exceeds_file_max(self, tmp_path, fake_home):
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
    def test_counter_drift_exact_boundary_no_finding(self, tmp_path, fake_home):
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
    def test_subprocess_exception_silently_suppresses_drift(self, tmp_path, fake_home):
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
    def test_healthy_project_produces_no_migration_currency_findings(
        self, tmp_path, fake_home
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
    def test_migration_runner_absent_skips_schema_drift_check(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        # Explicitly do NOT create scripts/migrations/runner.py
        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = [f.id for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert schema_ids == [], (
            f"Absent migration runner should skip schema drift check, got: {schema_ids}"
        )

    # Scenario: Migration runner reports schema drift produces warning
    def test_migration_runner_reports_schema_drift_produces_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text(
            'import json; print(json.dumps({"findings": [{"file": "test.yaml", "message": "needs upgrade"}]}))\n'
        )

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_findings = [f for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert len(schema_findings) >= 1, (
            f"Expected at least 1 schema-drift finding, got: {[f.id for f in findings]}"
        )

        first = schema_findings[0]
        assert first.severity == "warning"
        assert first.fix_type == "prompted"

    # Scenario: Migration runner returns empty findings list
    def test_migration_runner_returns_empty_findings_list(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text('import json; print(json.dumps({"findings": []}))\n')

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = [f.id for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert schema_ids == [], (
            f"Empty findings list should produce no schema-drift findings, got: {schema_ids}"
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

    # Scenario: Migration runner returns invalid JSON is silently skipped
    def test_migration_runner_invalid_json_is_silently_skipped(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text('print("not json")\n')

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = [f.id for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert schema_ids == [], (
            f"Invalid JSON from runner should be silently skipped, got: {schema_ids}"
        )

    # Scenario: Migration runner exits non-zero is silently skipped
    def test_migration_runner_exits_nonzero_is_silently_skipped(
        self, tmp_path, fake_home
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

    # Scenario: Migration runner returns JSON list directly
    def test_migration_runner_returns_json_list_directly(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text(
            'import json; print(json.dumps([{"file": "test.yaml", "message": "needs upgrade"}]))\n'
        )

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_findings = [f for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert len(schema_findings) >= 1, (
            f"JSON list format should produce at least 1 schema-drift finding, "
            f"got: {[f.id for f in findings]}"
        )

    # Scenario: Migration runner returns valid JSON of unexpected type is silently skipped
    def test_migration_runner_unexpected_json_type_is_silently_skipped(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text('import json; print(json.dumps("unexpected string"))\n')

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        schema_ids = [f.id for f in findings if f.id.startswith("migration-currency:schema-drift")]
        assert schema_ids == [], (
            f"Unexpected JSON type should be silently skipped, got: {schema_ids}"
        )

    # Scenario: Migration runner OSError is silently skipped
    def test_migration_runner_oserror_is_silently_skipped(
        self, tmp_path, fake_home, monkeypatch
    ):
        project_dir = build_fixture(tmp_path)
        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text('import json; print(json.dumps({"findings": []}))\n')

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
        self, tmp_path, fake_home, monkeypatch
    ):
        project_dir = build_fixture(tmp_path)

        runner_path = project_dir / "scripts" / "migrations" / "runner.py"
        runner_path.parent.mkdir(parents=True, exist_ok=True)
        runner_path.write_text('import time; time.sleep(30)\n')

        orphan_script = project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py"
        orphan_script.parent.mkdir(parents=True, exist_ok=True)
        orphan_script.write_text(
            'import json; print(json.dumps({"orphans": [{"file": "orphan.md"}]}))\n'
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

        orphan_ids = [f.id for f in findings if f.id == "migration-currency:orphans:scan"]
        assert len(orphan_ids) >= 1, (
            f"Runner timeout should not prevent orphan scan, got: {[f.id for f in findings]}"
        )

    # ------------------------------------------------------------------
    # Taxonomy drift (old-prefixed files)
    # ------------------------------------------------------------------

    # Scenario: STORY-prefixed file in backlog produces taxonomy drift warning
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

        orphan_ids = [f.id for f in findings if f.id.startswith("migration-currency:orphans")]
        assert orphan_ids == [], (
            f"Absent orphan script should skip orphan check, got: {orphan_ids}"
        )

    # Scenario: Orphan scan finds orphans produces warning
    def test_orphan_scan_finds_orphans_produces_warning(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        orphan_script = project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py"
        orphan_script.parent.mkdir(parents=True, exist_ok=True)
        orphan_script.write_text(
            'import json; print(json.dumps({"orphans": [{"file": "orphan.md"}]}))\n'
        )

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        ids = [f.id for f in findings]
        assert "migration-currency:orphans:scan" in ids, (
            f"Expected orphans:scan finding, got: {ids}"
        )

        f = next(x for x in findings if x.id == "migration-currency:orphans:scan")
        assert f.severity == "warning"
        assert f.fix_type == "prompted"

    # Scenario: Orphan scan finds no orphans produces no finding
    def test_orphan_scan_finds_no_orphans_produces_no_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path)
        orphan_script = project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py"
        orphan_script.parent.mkdir(parents=True, exist_ok=True)
        orphan_script.write_text(
            'import json; print(json.dumps({"orphans": []}))\n'
        )

        state = build_project_state(project_dir)
        findings = check_migration_currency(state)

        ids = [f.id for f in findings]
        assert "migration-currency:orphans:scan" not in ids, (
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

        orphan_ids = [f.id for f in findings if f.id.startswith("migration-currency:orphans")]
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

        orphan_ids = [f.id for f in findings if f.id.startswith("migration-currency:orphans")]
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

        orphan_ids = [f.id for f in findings if f.id.startswith("migration-currency:orphans")]
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
    # Scenario: skills.yaml missing when state directory exists produces
    #           info finding
    # ------------------------------------------------------------------

    def test_skills_yaml_missing_when_state_dir_exists_produces_info_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={"skills_yaml": None})
        state = build_project_state(project_dir)
        findings = check_onboarding_state(state)

        ids = [f.id for f in findings]
        assert "onboarding-state:missing:skills.yaml" in ids, (
            f"Expected 'onboarding-state:missing:skills.yaml' in {ids}"
        )

        f = next(x for x in findings if x.id == "onboarding-state:missing:skills.yaml")
        assert f.severity == "info", (
            f"Expected severity 'info', got: {f.severity}"
        )
        assert f.fix_type == "prompted", (
            f"Expected fix_type 'prompted', got: {f.fix_type}"
        )
        assert f.fix_recipe["action"] == "prompt", (
            f"Expected fix_recipe action 'prompt', got: {f.fix_recipe.get('action')}"
        )
        assert f.fix_recipe["type"] == "bootstrap", (
            f"Expected fix_recipe type 'bootstrap', got: {f.fix_recipe.get('type')}"
        )

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
        assert f.fix_type == "prompted", (
            f"Expected fix_type 'prompted', got: {f.fix_type}"
        )

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
    # Scenario: skills.yaml that is empty (parsed as None) produces
    #           missing finding
    # ------------------------------------------------------------------

    def test_skills_yaml_empty_parsed_as_none_produces_missing_finding(
        self, tmp_path, fake_home
    ):
        project_dir = build_fixture(tmp_path, overrides={"skills_yaml": None})
        skills_path = project_dir / ".sweetclaude" / "state" / "skills.yaml"
        skills_path.write_text("")

        state = build_project_state(project_dir)
        findings = check_onboarding_state(state)

        ids = [f.id for f in findings]
        assert "onboarding-state:missing:skills.yaml" in ids, (
            f"Empty skills.yaml (parsed as None) should produce missing finding, "
            f"got: {ids}"
        )


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

    def test_rebuild_cache_records_failure_when_cache_missing(self, tmp_path, fake_home):
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

    def test_one_recipe_fails_while_others_succeed(self, tmp_path, fake_home):
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

    def test_resolved_suppression_auto_removed_and_reported(self, tmp_path, fake_home):
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
        # Suppression file should no longer contain that entry
        remaining = load_suppressions(project_dir)
        remaining_ids = [e.get("finding_id") for e in remaining]
        assert "env-wiring:missing:plans-directory" not in remaining_ids, (
            f"Suppression file should no longer contain resolved entry, got: {remaining_ids}"
        )

    # ------------------------------------------------------------------
    # Scenario: Auto-removed suppression ID appears in auto_cleanup result
    # ------------------------------------------------------------------

    def test_auto_cleanup_removes_stale_suppression_and_retains_active(self, tmp_path, fake_home):
        project_dir = build_fixture(tmp_path, overrides={
            "suppressions": [
                {"finding_id": "finding-A"},
                {"finding_id": "finding-B"},
            ],
        })

        resolved = auto_cleanup_suppressions(project_dir, {"finding-B"})

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
        self, tmp_path, fake_home
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

        orphan_ids = [f.id for f in findings if f.id.startswith("migration-currency:orphans")]
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
        self, tmp_path, fake_home
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
            "state_integrity", "hook_health", "storage_lint",
            "migration_currency", "config_compat", "file_diagnostics",
            "onboarding_state", "env_wiring", "derived_status",
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
        assert f.severity == "info"
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
        assert findings[0].fix_type == "report-only"
