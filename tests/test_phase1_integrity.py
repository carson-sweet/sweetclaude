"""
Success gate tests for the Unified Artifact Integrity System.

Phase 1:
- Bold-format files are ingested by the cache (1A/1B/1C)
- Doctor check_derived_status finds Bold-format parents with stale status (1A)
- Doctor check_format_consistency reports Bold-format files (1E)
- Schema validates all new ID prefixes (1D)
- Expanded scan directories pick up artifacts outside the original 4 dirs (1B)

Phase 2:
- op_create produces YAML frontmatter (2B)
- op_create with parent ref triggers propagation (2D)
- op_write with status change triggers propagation (2C)
- Doctor auto-fix resolves stale parent status (2E)

Phase 3:
- project-index.json is never written by any code path (3B)
- op_query returns correct results from SQLite (3A)
- op_list returns items from SQLite (3A)
- op_reindex rebuilds SQLite cache (3B)
- Doctor detects orphaned project-index.json (3C)
"""
import importlib.util
import json
import os
import sys
import sqlite3

import pytest
import yaml

_SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

_HOOKS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "hooks")
)

from cache import rebuild, get_conn, db_path
from parse_utils import (
    parse_bold_metadata,
    parse_yaml_frontmatter,
    detect_format,
    parse_artifact,
    BOLD_TO_YAML_FIELD_MAP,
    PREFIX_TO_TYPE,
)
from schema import validate_frontmatter, VALID_TYPES, normalize_status


def _load_sc_artifact():
    spec = importlib.util.spec_from_file_location(
        "sc_artifact_impl",
        os.path.join(_HOOKS_DIR, "sc-artifact-impl.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_yaml_file(path, frontmatter, body=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fm_text = yaml.dump(frontmatter, default_flow_style=False)
    with open(path, "w") as f:
        f.write(f"---\n{fm_text}---\n{body}")


def write_bold_file(path, heading, fields, body=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [f"# {heading}", ""]
    for key, val in fields.items():
        lines.append(f"**{key}:** {val}")
    if body:
        lines.append("")
        lines.append(body)
    with open(path, "w") as f:
        f.write("\n".join(lines))


def setup_project(tmp_path):
    sc = tmp_path / ".sweetclaude"
    sc.mkdir(parents=True)
    ap = sc / "artifact-privacy.yaml"
    ap.write_text(yaml.dump({"product": {"base_path": ".sweetclaude/product"}}))
    return str(tmp_path)


def get_item(project_dir, item_id):
    conn = get_conn(project_dir)
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_items(project_dir):
    conn = get_conn(project_dir)
    rows = conn.execute("SELECT * FROM items ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# parse_utils unit tests
# ---------------------------------------------------------------------------

class TestParseUtils:

    def test_detect_yaml_format(self):
        content = "---\nid: ISSUE-001\ntitle: Test\n---\n"
        assert detect_format(content) == "yaml"

    def test_detect_bold_format(self):
        content = "# SP-001: My Sprint\n\n**Status:** active\n**Created:** 2026-01-01\n"
        assert detect_format(content) == "bold"

    def test_detect_unknown_format(self):
        content = "Just some markdown without any format markers.\n"
        assert detect_format(content) == "unknown"

    def test_parse_bold_extracts_id_from_heading(self):
        content = "# SP-001: Sprint One\n\n**Status:** active\n"
        result = parse_bold_metadata(content)
        assert result is not None
        assert result["id"] == "SP-001"
        assert result["title"] == "Sprint One"

    def test_parse_bold_infers_type_from_prefix(self):
        for prefix, expected_type in PREFIX_TO_TYPE.items():
            content = f"# {prefix}-99: Test\n\n**Status:** active\n"
            result = parse_bold_metadata(content)
            assert result is not None
            assert result["type"] == expected_type, f"prefix {prefix} → expected {expected_type}"

    def test_parse_bold_remaps_field_names(self):
        content = (
            "# ISSUE-100: Test Issue\n\n"
            "**Epic ID:** EP-01\n"
            "**Sprint ID:** SP-01\n"
            "**Theme ID:** TH-01\n"
            "**Milestone ID:** MS-01\n"
        )
        result = parse_bold_metadata(content)
        assert result["epic"] == "EP-01"
        assert result["sprint"] == "SP-01"
        assert result["theme"] == "TH-01"
        assert result["milestone"] == "MS-01"

    def test_parse_bold_normalizes_none_sentinels(self):
        content = "# SP-001: Test\n\n**Epic ID:** (none)\n**Status:** active\n"
        result = parse_bold_metadata(content)
        assert result["epic"] is None
        assert result["status"] == "active"

    def test_parse_yaml_returns_dict(self):
        content = "---\nid: ISSUE-001\ntitle: Test\nstatus: active\n---\n"
        result = parse_yaml_frontmatter(content)
        assert result == {"id": "ISSUE-001", "title": "Test", "status": "active"}

    def test_parse_artifact_dispatches_to_bold(self):
        content = "# SP-001: Test\n\n**Status:** active\n"
        result = parse_artifact(content)
        assert result is not None
        assert result["id"] == "SP-001"

    def test_parse_artifact_dispatches_to_yaml(self):
        content = "---\nid: ISSUE-001\ntitle: Test\n---\n"
        result = parse_artifact(content)
        assert result is not None
        assert result["id"] == "ISSUE-001"


# ---------------------------------------------------------------------------
# Bold-format ingestion into cache (Phase 1A + 1B + 1C success gate)
# ---------------------------------------------------------------------------

class TestBoldFormatCacheIngestion:

    def test_bold_sprint_indexed_in_cache(self, tmp_path):
        project_dir = setup_project(tmp_path)
        sprint_dir = os.path.join(project_dir, ".sweetclaude", "product", "sprints")
        write_bold_file(
            os.path.join(sprint_dir, "SP-001-sprint-one.md"),
            "SP-001: Sprint One",
            {"Status": "active", "Created": "2026-01-01"},
        )
        rebuild(project_dir)
        item = get_item(project_dir, "SP-001")
        assert item is not None, "Bold-format SP-001 should be in cache"
        assert item["title"] == "Sprint One"
        assert item["type"] == "sprint"

    def test_bold_theme_indexed_in_cache(self, tmp_path):
        project_dir = setup_project(tmp_path)
        theme_dir = os.path.join(project_dir, ".sweetclaude", "product", "themes")
        write_bold_file(
            os.path.join(theme_dir, "TH-001-theme-one.md"),
            "TH-001: Theme One",
            {"Status": "active", "Created": "2026-01-01"},
        )
        rebuild(project_dir)
        item = get_item(project_dir, "TH-001")
        assert item is not None, "Bold-format TH-001 should be in cache"
        assert item["type"] == "theme"

    def test_bold_issue_with_epic_ref_indexed(self, tmp_path):
        project_dir = setup_project(tmp_path)
        backlog_dir = os.path.join(project_dir, ".sweetclaude", "product", "backlog")
        write_bold_file(
            os.path.join(backlog_dir, "ISSUE-100-test.md"),
            "ISSUE-100: Test Issue",
            {
                "Status": "active",
                "Created": "2026-01-01",
                "Epic ID": "EP-01",
                "Sprint ID": "SP-01",
            },
        )
        rebuild(project_dir)
        item = get_item(project_dir, "ISSUE-100")
        assert item is not None
        assert item["epic"] == "EP-01"
        assert item["sprint"] == "SP-01"

    def test_bold_epic_in_epics_dir_indexed(self, tmp_path):
        project_dir = setup_project(tmp_path)
        epics_dir = os.path.join(project_dir, ".sweetclaude", "product", "epics")
        write_bold_file(
            os.path.join(epics_dir, "EP-01-alpha.md"),
            "EP-01: Alpha Epic",
            {
                "Status": "done",
                "Created": "2026-01-01",
                "Milestone ID": "MS-01",
            },
        )
        rebuild(project_dir)
        item = get_item(project_dir, "EP-01")
        assert item is not None
        assert item["type"] == "epic"
        assert item["milestone"] == "MS-01"

    def test_new_columns_populated_from_bold(self, tmp_path):
        project_dir = setup_project(tmp_path)
        backlog_dir = os.path.join(project_dir, ".sweetclaude", "product", "backlog")
        write_bold_file(
            os.path.join(backlog_dir, "ISSUE-200-full.md"),
            "ISSUE-200: Full Refs",
            {
                "Status": "active",
                "Created": "2026-01-01",
                "Epic ID": "EP-01",
                "Sprint ID": "SP-01",
                "Theme ID": "TH-01",
                "Release ID": "REL-01",
            },
        )
        rebuild(project_dir)
        item = get_item(project_dir, "ISSUE-200")
        assert item is not None
        assert item["sprint"] == "SP-01"
        assert item["theme"] == "TH-01"
        assert item["release"] == "REL-01"

    def test_mixed_format_project_all_items_indexed(self, tmp_path):
        project_dir = setup_project(tmp_path)
        base = os.path.join(project_dir, ".sweetclaude", "product")

        write_yaml_file(
            os.path.join(base, "roadmap", "epics", "EP-01-yaml.md"),
            {"id": "EP-01", "title": "YAML Epic", "type": "epic", "status": "active",
             "created": "2026-01-01", "milestone": "MS-01"},
        )
        write_bold_file(
            os.path.join(base, "epics", "EP-02-bold.md"),
            "EP-02: Bold Epic",
            {"Status": "done", "Created": "2026-01-01", "Milestone ID": "MS-01"},
        )
        write_yaml_file(
            os.path.join(base, "roadmap", "issues", "ISSUE-100-yaml.md"),
            {"id": "ISSUE-100", "title": "YAML Issue", "type": "enhancement",
             "status": "active", "created": "2026-01-01", "epic": "EP-01"},
        )
        write_bold_file(
            os.path.join(base, "backlog", "ISSUE-200-bold.md"),
            "ISSUE-200: Bold Issue",
            {"Status": "active", "Created": "2026-01-01", "Epic ID": "EP-02"},
        )

        rebuild(project_dir)
        items = get_all_items(project_dir)
        ids = {i["id"] for i in items}
        assert "EP-01" in ids, "YAML epic should be indexed"
        assert "EP-02" in ids, "Bold epic should be indexed"
        assert "ISSUE-100" in ids, "YAML issue should be indexed"
        assert "ISSUE-200" in ids, "Bold issue should be indexed"


# ---------------------------------------------------------------------------
# Expanded scan directories (Phase 1B)
# ---------------------------------------------------------------------------

class TestExpandedScanDirs:

    def test_sprints_dir_scanned(self, tmp_path):
        project_dir = setup_project(tmp_path)
        sprint_dir = os.path.join(project_dir, ".sweetclaude", "product", "sprints")
        write_yaml_file(
            os.path.join(sprint_dir, "SP-001-test.md"),
            {"id": "SP-001", "title": "Sprint 1", "type": "sprint", "status": "active",
             "created": "2026-01-01"},
        )
        rebuild(project_dir)
        assert get_item(project_dir, "SP-001") is not None

    def test_themes_dir_scanned(self, tmp_path):
        project_dir = setup_project(tmp_path)
        themes_dir = os.path.join(project_dir, ".sweetclaude", "product", "themes")
        write_yaml_file(
            os.path.join(themes_dir, "TH-001-test.md"),
            {"id": "TH-001", "title": "Theme 1", "type": "theme", "status": "active",
             "created": "2026-01-01"},
        )
        rebuild(project_dir)
        assert get_item(project_dir, "TH-001") is not None

    def test_cycles_dir_scanned(self, tmp_path):
        project_dir = setup_project(tmp_path)
        cycles_dir = os.path.join(project_dir, ".sweetclaude", "product", "cycles")
        write_yaml_file(
            os.path.join(cycles_dir, "CYC-001-test.md"),
            {"id": "CYC-001", "title": "Cycle 1", "type": "cycle", "status": "active",
             "created": "2026-01-01"},
        )
        rebuild(project_dir)
        assert get_item(project_dir, "CYC-001") is not None

    def test_pitches_dir_scanned(self, tmp_path):
        project_dir = setup_project(tmp_path)
        pitches_dir = os.path.join(project_dir, ".sweetclaude", "product", "pitches")
        write_yaml_file(
            os.path.join(pitches_dir, "PITCH-001-test.md"),
            {"id": "PITCH-001", "title": "Pitch 1", "type": "pitch", "status": "new",
             "created": "2026-01-01"},
        )
        rebuild(project_dir)
        assert get_item(project_dir, "PITCH-001") is not None

    def test_releases_dir_scanned(self, tmp_path):
        project_dir = setup_project(tmp_path)
        releases_dir = os.path.join(
            project_dir, ".sweetclaude", "product", "roadmap", "releases"
        )
        write_yaml_file(
            os.path.join(releases_dir, "REL-001-test.md"),
            {"id": "REL-001", "title": "Release 1", "type": "release", "status": "new",
             "created": "2026-01-01"},
        )
        rebuild(project_dir)
        assert get_item(project_dir, "REL-001") is not None

    def test_deduplication_across_dirs(self, tmp_path):
        """Same file reachable via roadmap/ and roadmap/epics/ is not double-counted."""
        project_dir = setup_project(tmp_path)
        epics_dir = os.path.join(
            project_dir, ".sweetclaude", "product", "roadmap", "epics"
        )
        write_yaml_file(
            os.path.join(epics_dir, "EP-01-test.md"),
            {"id": "EP-01", "title": "Epic 1", "type": "epic", "status": "active",
             "created": "2026-01-01", "milestone": "MS-01"},
        )
        rebuild(project_dir)
        conn = get_conn(project_dir)
        count = conn.execute(
            "SELECT COUNT(*) FROM items WHERE id = 'EP-01'"
        ).fetchone()[0]
        conn.close()
        assert count == 1


# ---------------------------------------------------------------------------
# Schema validation for new ID prefixes (Phase 1D)
# ---------------------------------------------------------------------------

class TestSchemaNewPrefixes:

    @pytest.mark.parametrize("artifact_id", [
        "SP-01", "TH-01", "RM-01", "REL-01", "PITCH-01", "CYC-01", "I-01",
    ])
    def test_new_id_prefixes_valid(self, artifact_id):
        fm = {
            "id": artifact_id,
            "title": "Test",
            "type": "sprint",
            "status": "active",
            "created": "2026-01-01",
        }
        violations = validate_frontmatter(fm)
        id_violations = [v for v in violations if "invalid id" in v.lower()]
        assert len(id_violations) == 0, f"{artifact_id} should be a valid ID"

    @pytest.mark.parametrize("artifact_type", [
        "sprint", "theme", "roadmap_item", "release", "pitch", "cycle",
    ])
    def test_new_types_valid(self, artifact_type):
        assert artifact_type in VALID_TYPES


# ---------------------------------------------------------------------------
# Status alias normalization (Phase 1D)
# ---------------------------------------------------------------------------

class TestStatusAliases:

    @pytest.mark.parametrize("alias, canonical", [
        ("complete", "done"),
        ("completed", "done"),
        ("closed", "done"),
        ("cancelled", "declined"),
        ("planned", "new"),
        ("pending", "new"),
        ("backlog", "new"),
        ("in_progress", "active"),
        ("in-progress", "active"),
        ("achieved", "done"),
        ("missed", "declined"),
        ("paused", "on-hold"),
    ])
    def test_alias_resolves_to_canonical(self, alias, canonical):
        assert normalize_status(alias) == canonical

    def test_canonical_status_unchanged(self):
        for status in ("new", "active", "done", "declined", "on-hold", "blocked"):
            assert normalize_status(status) == status


# ---------------------------------------------------------------------------
# Doctor: check_format_consistency (Phase 1E)
# ---------------------------------------------------------------------------

class TestDoctorFormatConsistency:

    @pytest.fixture
    def fake_home(self, tmp_path, monkeypatch):
        fake = tmp_path / "fakehome"
        fake.mkdir()
        monkeypatch.setenv("HOME", str(fake))
        monkeypatch.setattr("pathlib.Path.home", lambda: fake)
        claude_dir = fake / ".claude"
        claude_dir.mkdir()
        return fake

    def _build_project(self, tmp_path):
        from test_doctor import build_fixture, build_project_state
        return build_fixture, build_project_state

    def test_bold_file_flagged(self, tmp_path, fake_home):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from test_doctor import build_fixture, build_project_state
        from doctor import check_format_consistency

        project_dir = build_fixture(tmp_path)
        sprints_dir = project_dir / ".sweetclaude" / "product" / "sprints"
        sprints_dir.mkdir(parents=True, exist_ok=True)
        bold_file = sprints_dir / "SP-001-test.md"
        bold_file.write_text(
            "# SP-001: Test Sprint\n\n**Status:** active\n**Created:** 2026-01-01\n"
        )

        state = build_project_state(project_dir)
        findings = check_format_consistency(state)
        assert len(findings) >= 1
        bold_findings = [f for f in findings if "SP-001" in f.id]
        assert len(bold_findings) == 1
        assert bold_findings[0].severity == "warning"
        assert bold_findings[0].fix_type == "auto"
        assert bold_findings[0].fix_recipe["action"] == "convert_to_yaml"

    def test_bold_backup_artifact_not_flagged(self, tmp_path, fake_home):
        """Regression ISSUE-232: converter backup artifacts are not live work
        items — flagging them re-converts them and spawns a new backup every
        doctor run."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from test_doctor import build_fixture, build_project_state
        from doctor import check_format_consistency

        project_dir = build_fixture(tmp_path)
        archived_dir = project_dir / ".sweetclaude" / "product" / "backlog" / "archived"
        archived_dir.mkdir(parents=True, exist_ok=True)
        for name in (
            "I-001-agentic-skills-spike.bold-backup-20260610-093312.md",
            "I-001-agentic-skills-spike.bold-backup-20260610-093312"
            ".bold-backup-20260621-084233.md",
        ):
            (archived_dir / name).write_text(
                "# I-001: Agentic skills spike\n\n"
                "**Status:** done\n**Created:** 2026-01-01\n"
            )

        state = build_project_state(project_dir)
        findings = check_format_consistency(state)
        backup_findings = [f for f in findings if "bold-backup" in f.id]
        assert backup_findings == []

    def test_backup_like_slug_still_flagged(self, tmp_path, fake_home):
        """The exclusion is suffix-anchored: a real work item whose slug
        contains 'backup' must still be flagged."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from test_doctor import build_fixture, build_project_state
        from doctor import check_format_consistency

        project_dir = build_fixture(tmp_path)
        backlog_dir = project_dir / ".sweetclaude" / "product" / "backlog"
        backlog_dir.mkdir(parents=True, exist_ok=True)
        (backlog_dir / "STORY-041-backup-and-restore.md").write_text(
            "# STORY-041: Backup and restore\n\n"
            "**Status:** new\n**Created:** 2026-01-01\n"
        )

        state = build_project_state(project_dir)
        findings = check_format_consistency(state)
        slug_findings = [f for f in findings if "STORY-041" in f.id]
        assert len(slug_findings) == 1

    def test_yaml_file_not_flagged(self, tmp_path, fake_home):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from test_doctor import build_fixture, build_project_state
        from doctor import check_format_consistency

        project_dir = build_fixture(tmp_path)
        epics_dir = project_dir / ".sweetclaude" / "product" / "roadmap" / "epics"
        epics_dir.mkdir(parents=True, exist_ok=True)
        yaml_file = epics_dir / "EP-01-test.md"
        yaml_file.write_text(
            "---\nid: EP-01\ntitle: Test\ntype: epic\nstatus: active\n"
            "created: 2026-01-01\nmilestone: MS-01\n---\n"
        )

        state = build_project_state(project_dir)
        findings = check_format_consistency(state)
        format_findings = [f for f in findings if "EP-01" in f.id]
        assert len(format_findings) == 0


# ---------------------------------------------------------------------------
# Doctor: check_derived_status with Bold-format parent (Phase 1A success gate)
# ---------------------------------------------------------------------------

class TestDerivedStatusWithBoldParent:

    @pytest.fixture
    def fake_home(self, tmp_path, monkeypatch):
        fake = tmp_path / "fakehome"
        fake.mkdir()
        monkeypatch.setenv("HOME", str(fake))
        monkeypatch.setattr("pathlib.Path.home", lambda: fake)
        claude_dir = fake / ".claude"
        claude_dir.mkdir()
        return fake

    def test_bold_epic_stale_status_detected(self, tmp_path, fake_home):
        """Bold-format epic marked done with active children triggers derived_status finding."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from test_doctor import build_fixture, build_project_state
        from doctor import check_derived_status

        project_dir = build_fixture(tmp_path, overrides={
            "roadmap_files": [
                {
                    "name": "issues/ISSUE-100-test.md",
                    "frontmatter": {
                        "id": "ISSUE-100", "title": "Active Issue", "type": "enhancement",
                        "status": "active", "created": "2026-01-01", "epic": "EP-01",
                    },
                },
                {
                    "name": "issues/ISSUE-101-test.md",
                    "frontmatter": {
                        "id": "ISSUE-101", "title": "Done Issue", "type": "enhancement",
                        "status": "done", "created": "2026-01-01", "epic": "EP-01",
                    },
                },
            ],
        })

        epics_dir = project_dir / ".sweetclaude" / "product" / "epics"
        epics_dir.mkdir(parents=True, exist_ok=True)
        bold_epic = epics_dir / "EP-01-alpha.md"
        bold_epic.write_text(
            "# EP-01: Alpha Epic\n\n"
            "**Status:** done\n"
            "**Created:** 2026-01-01\n"
            "**Milestone ID:** MS-01\n"
        )

        state = build_project_state(project_dir)
        findings = check_derived_status(state)
        ep_findings = [f for f in findings if "EP-01" in f.id]
        assert len(ep_findings) >= 1, (
            "Doctor should detect that Bold-format EP-01 (done) has active children"
        )


# ---------------------------------------------------------------------------
# Phase 2: op_create produces YAML frontmatter (2B)
# ---------------------------------------------------------------------------

class TestCreateProducesYAML:

    def _setup_project(self, tmp_path):
        project_dir = tmp_path / "proj"
        sc = project_dir / ".sweetclaude"
        (sc / "state").mkdir(parents=True)
        (sc / "artifact-privacy.yaml").write_text(
            yaml.dump({"product": {"base_path": ".sweetclaude/product"}})
        )
        product_base = project_dir / ".sweetclaude" / "product"
        state_base = project_dir / ".sweetclaude" / "state"
        for d in ("issues", "epics", "sprints", "themes", "milestones",
                   "roadmap", "roadmap/releases", "pitches", "cycles"):
            (product_base / d).mkdir(parents=True, exist_ok=True)
        return project_dir, product_base, state_base

    @pytest.mark.parametrize("entity_type", [
        "issue", "epic", "sprint", "theme", "roadmap_item",
        "milestone", "release", "pitch", "cycle",
    ])
    def test_create_produces_yaml(self, tmp_path, entity_type):
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_project(tmp_path)
        sa.op_create(product_base, state_base, entity_type,
                     json.dumps({"title": f"Test {entity_type}"}),
                     project_dir=project_dir)
        type_dir = product_base / sa.TYPE_TO_DIR[entity_type]
        files = list(type_dir.glob("*.md"))
        assert len(files) == 1, f"Expected 1 file for {entity_type}, got {len(files)}"
        content = files[0].read_text()
        assert detect_format(content) == "yaml", f"{entity_type} template should be YAML"
        fm = parse_artifact(content)
        assert fm is not None
        assert "id" in fm
        assert "status" in fm

    def test_created_issue_parseable_by_cache(self, tmp_path):
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_project(tmp_path)
        sa.op_create(product_base, state_base, "issue",
                     json.dumps({"title": "Cache test", "epic_id": "EP-001"}),
                     project_dir=project_dir)
        rebuild(str(project_dir))
        items = get_all_items(str(project_dir))
        # ISSUE-, not I-: create emits the current prefix (ISSUE-289). "I-"
        # would not even match it as a substring test, so this read as zero
        # issues rather than as a wrong id.
        issue_items = [i for i in items if i["id"].startswith("ISSUE-")]
        assert len(issue_items) == 1
        assert issue_items[0]["epic"] == "EP-001"


# ---------------------------------------------------------------------------
# Phase 2: Create issue in done epic → epic reopens (2D)
# ---------------------------------------------------------------------------

class TestCreateTriggersPropagation:

    def _setup_project_with_done_epic(self, tmp_path):
        project_dir = tmp_path / "proj"
        sc = project_dir / ".sweetclaude"
        (sc / "state").mkdir(parents=True)
        (sc / "artifact-privacy.yaml").write_text(
            yaml.dump({"product": {"base_path": ".sweetclaude/product"}})
        )
        product_base = project_dir / ".sweetclaude" / "product"
        state_base = project_dir / ".sweetclaude" / "state"
        for d in ("issues", "roadmap/epics", "roadmap/milestones"):
            (product_base / d).mkdir(parents=True, exist_ok=True)

        write_yaml_file(
            os.path.join(str(product_base), "roadmap", "epics", "EP-001-test.md"),
            {"id": "EP-001", "title": "Test Epic", "type": "epic",
             "status": "done", "source": "auto",
             "created": "2026-01-01", "milestone": "MS-01"},
        )
        write_yaml_file(
            os.path.join(str(product_base), "issues", "I-001-existing.md"),
            {"id": "I-001", "title": "Done Issue", "type": "enhancement",
             "status": "done", "created": "2026-01-01", "epic": "EP-001"},
        )
        rebuild(str(project_dir))
        return project_dir, product_base, state_base

    def test_create_issue_in_done_epic_reopens_epic(self, tmp_path):
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_project_with_done_epic(tmp_path)

        epic_file = product_base / "roadmap" / "epics" / "EP-001-test.md"
        fm_before = parse_artifact(epic_file.read_text())
        assert fm_before["status"] == "done"

        sa.op_create(product_base, state_base, "issue",
                     json.dumps({"title": "New active issue", "epic_id": "EP-001"}),
                     project_dir=project_dir)

        rebuild(str(project_dir))
        conn = get_conn(str(project_dir))
        ep_row = conn.execute("SELECT status FROM items WHERE id='EP-001'").fetchone()
        conn.close()

        assert ep_row is not None
        assert ep_row["status"] != "done", (
            f"EP-001 should have reopened after adding a new issue, but status is {ep_row['status']}"
        )


# ---------------------------------------------------------------------------
# Phase 2: Status write propagation — close last issue → epic auto-closes (2C)
# ---------------------------------------------------------------------------

class TestWritePropagation:

    def _setup_project_with_active_epic(self, tmp_path):
        project_dir = tmp_path / "proj"
        sc = project_dir / ".sweetclaude"
        (sc / "state").mkdir(parents=True)
        (sc / "artifact-privacy.yaml").write_text(
            yaml.dump({"product": {"base_path": ".sweetclaude/product"}})
        )
        product_base = project_dir / ".sweetclaude" / "product"
        state_base = project_dir / ".sweetclaude" / "state"
        for d in ("issues", "roadmap/epics", "roadmap/milestones"):
            (product_base / d).mkdir(parents=True, exist_ok=True)

        write_yaml_file(
            os.path.join(str(product_base), "roadmap", "epics", "EP-001-test.md"),
            {"id": "EP-001", "title": "Test Epic", "type": "epic",
             "status": "active", "source": "auto",
             "created": "2026-01-01", "milestone": "MS-01"},
        )
        write_yaml_file(
            os.path.join(str(product_base), "issues", "I-001-done.md"),
            {"id": "I-001", "title": "Done Issue", "type": "enhancement",
             "status": "done", "created": "2026-01-01", "epic": "EP-001"},
        )
        write_yaml_file(
            os.path.join(str(product_base), "issues", "I-002-active.md"),
            {"id": "I-002", "title": "Last Active Issue", "type": "enhancement",
             "status": "active", "created": "2026-01-01", "epic": "EP-001"},
        )
        rebuild(str(project_dir))
        return project_dir, product_base, state_base

    def test_closing_last_issue_auto_closes_epic(self, tmp_path):
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_project_with_active_epic(tmp_path)

        sa.op_write(product_base, state_base, "I-002",
                    json.dumps({"status": "done"}),
                    project_dir=project_dir)

        rebuild(str(project_dir))
        conn = get_conn(str(project_dir))
        ep_row = conn.execute("SELECT status FROM items WHERE id='EP-001'").fetchone()
        conn.close()

        assert ep_row is not None
        assert ep_row["status"] == "done", (
            f"EP-001 should auto-close when all children are done, but status is {ep_row['status']}"
        )


# ---------------------------------------------------------------------------
# Phase 2: Doctor auto-fix resolves stale parent (2E)
# ---------------------------------------------------------------------------

class TestDoctorAutoFix:

    @pytest.fixture
    def fake_home(self, tmp_path, monkeypatch):
        fake = tmp_path / "fakehome"
        fake.mkdir()
        monkeypatch.setenv("HOME", str(fake))
        monkeypatch.setattr("pathlib.Path.home", lambda: fake)
        claude_dir = fake / ".claude"
        claude_dir.mkdir()
        return fake

    def test_sync_parent_status_fix_resolves_finding(self, tmp_path, fake_home):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from test_doctor import build_fixture, build_project_state
        from doctor import check_derived_status, execute_recipe, RecipeResult

        project_dir = build_fixture(tmp_path, overrides={
            "roadmap_files": [
                {
                    "name": "epics/EP-01-test.md",
                    "frontmatter": {
                        "id": "EP-01", "title": "Stale Epic", "type": "epic",
                        "status": "done", "source": "auto",
                        "created": "2026-01-01", "milestone": "MS-01",
                    },
                },
                {
                    "name": "issues/ISSUE-100-test.md",
                    "frontmatter": {
                        "id": "ISSUE-100", "title": "Active Issue", "type": "enhancement",
                        "status": "active", "created": "2026-01-01", "epic": "EP-01",
                    },
                },
                {
                    "name": "issues/ISSUE-101-test.md",
                    "frontmatter": {
                        "id": "ISSUE-101", "title": "Done Issue", "type": "enhancement",
                        "status": "done", "created": "2026-01-01", "epic": "EP-01",
                    },
                },
            ],
        })

        state = build_project_state(project_dir)
        findings = check_derived_status(state)
        ep_findings = [f for f in findings if "EP-01" in f.id]
        assert len(ep_findings) >= 1, "Should detect stale EP-01"

        finding = ep_findings[0]
        assert finding.fix_recipe["action"] == "sync_parent_status"

        archive = project_dir / ".sweetclaude" / "doctor-archive"
        archive.mkdir(parents=True, exist_ok=True)
        result = execute_recipe(project_dir, finding.fix_recipe, archive)
        assert result.success, f"Auto-fix should succeed, error: {result.error}"

        state2 = build_project_state(project_dir)
        findings2 = check_derived_status(state2)
        ep_findings2 = [f for f in findings2 if "EP-01" in f.id]
        assert len(ep_findings2) == 0, (
            f"After auto-fix, EP-01 should have no stale status finding, got: {ep_findings2}"
        )


# ---------------------------------------------------------------------------
# Phase 3: project-index.json is never written (3B)
# ---------------------------------------------------------------------------

class TestNoProjectIndexWrite:

    def _setup_project(self, tmp_path):
        project_dir = tmp_path / "proj"
        sc = project_dir / ".sweetclaude"
        (sc / "state").mkdir(parents=True)
        (sc / "artifact-privacy.yaml").write_text(
            yaml.dump({"product": {"base_path": ".sweetclaude/product"}})
        )
        product_base = project_dir / ".sweetclaude" / "product"
        state_base = project_dir / ".sweetclaude" / "state"
        for d in ("issues", "roadmap/epics", "roadmap/milestones"):
            (product_base / d).mkdir(parents=True, exist_ok=True)
        return project_dir, product_base, state_base

    def test_op_create_does_not_write_index(self, tmp_path):
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_project(tmp_path)
        idx = state_base / "project-index.json"
        sa.op_create(product_base, state_base, "issue",
                     json.dumps({"title": "Test"}), project_dir=project_dir)
        assert not idx.exists(), "op_create should not write project-index.json"

    def test_op_write_does_not_write_index(self, tmp_path):
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_project(tmp_path)
        write_yaml_file(
            str(product_base / "issues" / "I-001-test.md"),
            {"id": "I-001", "title": "T", "type": "enhancement",
             "status": "new", "created": "2026-01-01"},
        )
        rebuild(str(project_dir))
        idx = state_base / "project-index.json"
        sa.op_write(product_base, state_base, "I-001",
                    json.dumps({"priority": "high"}), project_dir=project_dir)
        assert not idx.exists(), "op_write should not write project-index.json"

    def test_op_reindex_does_not_write_index(self, tmp_path):
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_project(tmp_path)
        write_yaml_file(
            str(product_base / "issues" / "I-001-test.md"),
            {"id": "I-001", "title": "T", "type": "enhancement",
             "status": "new", "created": "2026-01-01"},
        )
        idx = state_base / "project-index.json"
        sa.op_reindex(product_base, state_base, project_dir=project_dir)
        assert not idx.exists(), "op_reindex should not write project-index.json"

    def test_no_index_functions_in_source(self):
        hook_path = os.path.join(_HOOKS_DIR, "sc-artifact-impl.py")
        content = open(hook_path).read()
        for name in ("_load_index", "_save_index", "_index_entry",
                      "_update_index", "_remove_from_index", "INDEX_FIELDS"):
            assert name not in content, f"{name} should be removed from sc-artifact-impl.py"


# ---------------------------------------------------------------------------
# Phase 3: op_query via SQLite returns correct results (3A)
# ---------------------------------------------------------------------------

class TestQueryViaSQLite:

    def _setup_project(self, tmp_path):
        project_dir = tmp_path / "proj"
        sc = project_dir / ".sweetclaude"
        (sc / "state").mkdir(parents=True)
        (sc / "artifact-privacy.yaml").write_text(
            yaml.dump({"product": {"base_path": ".sweetclaude/product"}})
        )
        product_base = project_dir / ".sweetclaude" / "product"
        state_base = project_dir / ".sweetclaude" / "state"
        for d in ("issues", "roadmap/epics"):
            (product_base / d).mkdir(parents=True, exist_ok=True)
        write_yaml_file(
            str(product_base / "issues" / "I-001-a.md"),
            {"id": "I-001", "title": "Issue A", "type": "enhancement",
             "status": "active", "created": "2026-01-01", "epic": "EP-001"},
        )
        write_yaml_file(
            str(product_base / "issues" / "I-002-b.md"),
            {"id": "I-002", "title": "Issue B", "type": "bug-fix",
             "status": "done", "created": "2026-01-01", "epic": "EP-001"},
        )
        write_yaml_file(
            str(product_base / "issues" / "I-003-c.md"),
            {"id": "I-003", "title": "Issue C", "type": "enhancement",
             "status": "active", "created": "2026-01-01", "epic": "EP-002"},
        )
        rebuild(str(project_dir))
        return project_dir, product_base, state_base

    def test_query_by_epic_id(self, tmp_path, capsys):
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_project(tmp_path)
        sa.op_query(product_base, state_base, "issue",
                    "epic_id=EP-001", project_dir=project_dir)
        out = capsys.readouterr().out
        result = json.loads(out)
        ids = {r["id"] for r in result}
        assert "I-001" in ids
        assert "I-003" not in ids

    def test_query_by_type(self, tmp_path, capsys):
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_project(tmp_path)
        sa.op_query(product_base, state_base, "issue",
                    "type=bug-fix", project_dir=project_dir)
        out = capsys.readouterr().out
        result = json.loads(out)
        assert len(result) == 1
        assert result[0]["id"] == "I-002"

    def test_query_with_status_filter(self, tmp_path, capsys):
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_project(tmp_path)
        sa.op_query(product_base, state_base, "issue",
                    "status=done", project_dir=project_dir)
        out = capsys.readouterr().out
        result = json.loads(out)
        ids = {r["id"] for r in result}
        assert "I-002" in ids
        assert "I-001" not in ids


# ---------------------------------------------------------------------------
# Phase 3: op_list via SQLite (3A)
# ---------------------------------------------------------------------------

class TestListViaSQLite:

    def test_list_returns_items(self, tmp_path, capsys):
        project_dir = tmp_path / "proj"
        sc = project_dir / ".sweetclaude"
        (sc / "state").mkdir(parents=True)
        (sc / "artifact-privacy.yaml").write_text(
            yaml.dump({"product": {"base_path": ".sweetclaude/product"}})
        )
        product_base = project_dir / ".sweetclaude" / "product"
        state_base = project_dir / ".sweetclaude" / "state"
        (product_base / "sprints").mkdir(parents=True)
        write_yaml_file(
            str(product_base / "sprints" / "SP-001-s1.md"),
            {"id": "SP-001", "title": "Sprint 1", "type": "sprint",
             "status": "active", "created": "2026-01-01"},
        )
        rebuild(str(project_dir))

        sa = _load_sc_artifact()
        sa.op_list(product_base, state_base, "sprint", project_dir=project_dir)
        out = capsys.readouterr().out
        result = json.loads(out)
        assert len(result) >= 1
        assert result[0]["id"] == "SP-001"


# ---------------------------------------------------------------------------
# Phase 3: op_reindex rebuilds SQLite cache (3B)
# ---------------------------------------------------------------------------

class TestReindexRebuildsSQLite:

    def test_reindex_populates_cache(self, tmp_path, capsys):
        project_dir = tmp_path / "proj"
        sc = project_dir / ".sweetclaude"
        (sc / "state").mkdir(parents=True)
        (sc / "artifact-privacy.yaml").write_text(
            yaml.dump({"product": {"base_path": ".sweetclaude/product"}})
        )
        product_base = project_dir / ".sweetclaude" / "product"
        state_base = project_dir / ".sweetclaude" / "state"
        (product_base / "issues").mkdir(parents=True)
        write_yaml_file(
            str(product_base / "issues" / "I-001-test.md"),
            {"id": "I-001", "title": "Test", "type": "enhancement",
             "status": "new", "created": "2026-01-01"},
        )

        sa = _load_sc_artifact()
        sa.op_reindex(product_base, state_base, project_dir=project_dir)

        item = get_item(str(project_dir), "I-001")
        assert item is not None, "reindex should populate SQLite cache"
        assert item["title"] == "Test"


# ---------------------------------------------------------------------------
# Phase 3: Doctor detects orphaned project-index.json (3C)
# ---------------------------------------------------------------------------

class TestOrphanedIndexDetection:

    def test_orphaned_index_detected(self, tmp_path):
        from test_doctor import build_fixture, build_project_state
        from doctor import check_orphaned_index

        project_dir = build_fixture(tmp_path, {"files": []})
        idx = project_dir / ".sweetclaude" / "state" / "project-index.json"
        idx.parent.mkdir(parents=True, exist_ok=True)
        idx.write_text('{"schema_version": 1, "entities": []}')

        state = build_project_state(project_dir)
        findings = check_orphaned_index(state)
        assert len(findings) == 1
        assert findings[0].fix_recipe["action"] == "delete_file"

    def test_no_orphaned_index_when_absent(self, tmp_path):
        from test_doctor import build_fixture, build_project_state
        from doctor import check_orphaned_index

        project_dir = build_fixture(tmp_path, {"files": []})
        state = build_project_state(project_dir)
        findings = check_orphaned_index(state)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# Phase 5: Behavioral regression tests (5E)
# ---------------------------------------------------------------------------

class TestEndToEndPropagationChain:

    def _setup_full_project(self, tmp_path):
        project_dir = tmp_path / "proj"
        sc = project_dir / ".sweetclaude"
        (sc / "state").mkdir(parents=True)
        (sc / "artifact-privacy.yaml").write_text(
            yaml.dump({"product": {"base_path": ".sweetclaude/product"}})
        )
        product_base = project_dir / ".sweetclaude" / "product"
        state_base = project_dir / ".sweetclaude" / "state"
        for d in ("issues", "roadmap/epics", "roadmap/milestones"):
            (product_base / d).mkdir(parents=True, exist_ok=True)
        return project_dir, product_base, state_base

    def test_create_issue_in_done_epic_reopens_then_close_all_recompletes(self, tmp_path):
        """Full chain: create issue in done epic → epic reopens → close issue → epic re-closes."""
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_full_project(tmp_path)

        write_yaml_file(
            str(product_base / "roadmap" / "epics" / "EP-001-test.md"),
            {"id": "EP-001", "title": "Test Epic", "type": "epic",
             "status": "done", "source": "auto",
             "created": "2026-01-01", "milestone": "MS-01"},
        )
        rebuild(str(project_dir))

        sa.op_create(product_base, state_base, "issue",
                     json.dumps({"title": "New story", "epic_id": "EP-001"}),
                     project_dir=project_dir)
        epic_file = product_base / "roadmap" / "epics" / "EP-001-test.md"
        fm = parse_artifact(epic_file.read_text())
        assert fm["status"] != "done", "Epic should reopen after child created"

        # backlog/, not issues/: new issues are created untriaged, and
        # product/issues holds only an index file (ISSUE-289).
        issue_files = list((product_base / "backlog").glob("ISSUE-*.md"))
        assert len(issue_files) == 1
        issue_id = parse_artifact(issue_files[0].read_text())["id"]

        sa.op_write(product_base, state_base, issue_id,
                    json.dumps({"status": "done"}), project_dir=project_dir)

        epic_done = product_base / "roadmap" / "epics" / "done" / "EP-001-test.md"
        final_epic = epic_done if epic_done.exists() else epic_file
        fm2 = parse_artifact(final_epic.read_text())
        assert fm2["status"] == "done", "Epic should auto-close when all children are done"

    def test_bold_format_auto_converted_on_write(self, tmp_path):
        """Phase 5D: writing to a Bold-format file auto-converts it to YAML."""
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_full_project(tmp_path)

        bold_file = product_base / "issues" / "I-001-test.md"
        write_bold_file(
            str(bold_file), "I-001: Test Issue",
            {"ID": "I-001", "Type": "enhancement", "Title": "Test Issue",
             "Status": "active", "Created": "2026-01-01"},
        )
        rebuild(str(project_dir))

        sa.op_write(product_base, state_base, "I-001",
                    json.dumps({"priority": "high"}), project_dir=project_dir)

        content = bold_file.read_text()
        fmt = detect_format(content)
        assert fmt == "yaml", f"Bold file should be auto-converted to YAML, got {fmt}"

    def test_format_converter_handles_all_entity_types(self, tmp_path):
        """Phase 5E: format converter converts Bold files for all entity types."""
        from format_converter import convert_project

        project_dir = tmp_path / "proj"
        sc = project_dir / ".sweetclaude"
        (sc / "state").mkdir(parents=True)
        (sc / "artifact-privacy.yaml").write_text(
            yaml.dump({"product": {"base_path": ".sweetclaude/product"}})
        )
        product_base = project_dir / ".sweetclaude" / "product"
        entity_map = {
            "issues": ("I-001", "enhancement"),
            "roadmap/epics": ("EP-001", "epic"),
            "sprints": ("SP-001", "sprint"),
            "themes": ("TH-001", "theme"),
        }
        for subdir, (eid, etype) in entity_map.items():
            d = product_base / subdir
            d.mkdir(parents=True, exist_ok=True)
            write_bold_file(
                str(d / f"{eid}-test.md"), f"{eid}: Test",
                {"ID": eid, "Type": etype, "Title": "Test",
                 "Status": "active", "Created": "2026-01-01"},
            )

        results = convert_project(project_dir, dry_run=False, backup=False)
        converted = [r for r in results if r["action"] == "converted"]
        assert len(converted) == len(entity_map), (
            f"Expected {len(entity_map)} conversions, got {len(converted)}"
        )

        for subdir in entity_map:
            for f in (product_base / subdir).glob("*.md"):
                assert detect_format(f.read_text()) == "yaml", (
                    f"{f} should be YAML after conversion"
                )

    def test_convert_project_skips_bold_backup_artifacts(self, tmp_path):
        """Regression ISSUE-232: convert_project must not convert converter
        backup artifacts, or each batch run mints a new backup generation."""
        from format_converter import convert_project
        from parse_utils import detect_format

        project_dir = tmp_path / "proj"
        sc = project_dir / ".sweetclaude"
        (sc / "state").mkdir(parents=True)
        (sc / "artifact-privacy.yaml").write_text(
            yaml.dump({"product": {"base_path": ".sweetclaude/product"}})
        )
        backlog = project_dir / ".sweetclaude" / "product" / "backlog"
        backlog.mkdir(parents=True)
        backup_file = backlog / "I-001-spike.bold-backup-20260610-093312.md"
        write_bold_file(
            str(backup_file), "I-001: Spike",
            {"ID": "I-001", "Type": "spike", "Title": "Spike",
             "Status": "done", "Created": "2026-01-01"},
        )
        live_file = backlog / "I-002-live.md"
        write_bold_file(
            str(live_file), "I-002: Live",
            {"ID": "I-002", "Type": "spike", "Title": "Live",
             "Status": "new", "Created": "2026-01-01"},
        )

        results = convert_project(project_dir, dry_run=False, backup=False)
        touched = {r["file"] for r in results}
        assert str(backup_file) not in touched
        assert detect_format(backup_file.read_text()) == "bold", (
            "backup artifact must be left untouched"
        )
        assert detect_format(live_file.read_text()) == "yaml", (
            "live bold file must still be converted"
        )

    def test_no_bold_format_ever_created(self, tmp_path):
        """Regression: op_create never produces Bold format for any entity type."""
        sa = _load_sc_artifact()
        project_dir, product_base, state_base = self._setup_full_project(tmp_path)
        for d in ("sprints", "themes", "milestones", "roadmap",
                   "roadmap/releases", "pitches", "cycles"):
            (product_base / d).mkdir(parents=True, exist_ok=True)

        for entity_type in ("issue", "epic", "sprint", "theme", "roadmap_item",
                            "milestone", "release", "pitch", "cycle"):
            sa.op_create(product_base, state_base, entity_type,
                         json.dumps({"title": f"Test {entity_type}"}),
                         project_dir=project_dir)

        for p in product_base.rglob("*.md"):
            content = p.read_text()
            fmt = detect_format(content)
            assert fmt != "bold", f"{p} was created in Bold format — should be YAML"
