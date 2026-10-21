"""
WI-017 S3 — Execute the migration plan safely.

Covers every scenario described in the S3 acceptance criteria. All tests run
real execute() / run_migration(dry_run=False) against real on-disk temp trees.
NO mocks.

What does NOT exist yet:
  run_migration(dry_run=False) currently calls build_plan() (old engine) which
  does NOT recognize typed-backlog dirs, top-level old-prefix files at product
  base root, or the bespoke EPIC-NNN/US-* tree (those were added to
  _build_dry_run_plan only). Executing today migrates NOTHING from those
  patterns. S3 must make execution apply the S2 plan with:
    - snapshot + rollback
    - Tier B frontmatter synthesis
    - reference edits applied to body/frontmatter
    - .feature file moves alongside stories
    - MIGRATION-MAP.md written to product base
    - post-condition: characterize_project reports clean state
    - conflict refusal with no-write guarantee
    - idempotency on already-v4 projects
    - structural integrity invariants
"""
from __future__ import annotations

import hashlib
import re
import sys
import os

_SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from pathlib import Path
import pytest
import yaml

try:
    from migrate.migrate_taxonomy import (
        run_migration as _run_migration,
        create_snapshot,
        verify_snapshot,
        rollback,
        _backups_dir,
        MigrationResult,
    )
    _IMPORTS_MISSING = False
except ImportError:
    _run_migration = None
    create_snapshot = None
    verify_snapshot = None
    rollback = None
    _backups_dir = None
    MigrationResult = None
    _IMPORTS_MISSING = True

try:
    from recovery.characterize_project import characterize_project
    _CHARACTERIZE_MISSING = False
except ImportError:
    characterize_project = None
    _CHARACTERIZE_MISSING = True


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

ISSUE_RE = re.compile(r"^ISSUE-\d+$")
EP_RE = re.compile(r"^EP-\d+$")


def _make_project(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal project with docs/product as the product base."""
    project = tmp_path / "project"
    product = project / "docs" / "product"
    product.mkdir(parents=True)
    sc = project / ".sweetclaude"
    sc.mkdir(parents=True)
    privacy = {"product": {"base_path": "docs/product"}}
    (sc / "artifact-privacy.yaml").write_text(yaml.safe_dump(privacy))
    return project, product


def _write_md(
    product_base: Path,
    rel: str,
    frontmatter: dict | None = None,
    body: str = "",
) -> Path:
    target = product_base / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if frontmatter is not None:
        fm_yaml = yaml.safe_dump(frontmatter, default_flow_style=False).strip()
        content = f"---\n{fm_yaml}\n---\n\n{body}"
    else:
        content = f"# No frontmatter\n\n{body}" if not body else f"# File\n\n{body}"
    target.write_text(content, encoding="utf-8")
    return target


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    """Capture every file path -> content under root."""
    snap: dict[str, bytes] = {}
    for p in root.rglob("*"):
        if p.is_file():
            snap[str(p)] = p.read_bytes()
    return snap


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3 and parts[1].strip():
            try:
                fm = yaml.safe_load(parts[1])
                if isinstance(fm, dict):
                    return fm
            except yaml.YAMLError:
                pass
    return {}


def _execute(project: Path, **kwargs) -> dict:
    """Run run_migration(dry_run=False) and return the result dict."""
    if _IMPORTS_MISSING or _run_migration is None:
        pytest.fail(
            "run_migration is not exported from migrate.migrate_taxonomy — "
            "this is the missing behavior being tested (S3 implementation does not exist yet)"
        )
    return _run_migration(str(project), dry_run=False, **kwargs)


def _assert_bespoke_migration_ran(product: Path) -> None:
    """
    Assert that S3 actually executed bespoke pattern migration.
    The old engine never migrates EPIC-003/US-DM-002 items. If EP-003 does not
    exist after execute, S3 has not run and any subsequent assertions would be
    vacuously true (no migration occurred). Fail explicitly.
    """
    all_md = list(product.rglob("*.md"))
    ep_files = [f for f in all_md if _read_frontmatter(f).get("id") == "EP-003"]
    if not ep_files:
        pytest.fail(
            "S3 execute did not migrate the bespoke EPIC-003 item to EP-003. "
            "The old engine is still running (it is blind to bespoke patterns). "
            "This guard prevents vacuous pass — S3 implementation is required."
        )


def _assert_typed_backlog_migration_ran(product: Path) -> None:
    """
    Assert that S3 actually migrated typed-backlog items (STORY-024 -> ISSUE-*).
    """
    old_path = product / "backlog" / "stories" / "STORY-024-parallel-run.md"
    if old_path.exists():
        pytest.fail(
            "S3 execute did not migrate typed-backlog item STORY-024 — "
            "old path still exists at {old_path}. "
            "The old engine is still running. S3 implementation is required."
        )


def _make_typed_legacy_project(tmp_path: Path) -> tuple[Path, Path]:
    """
    A project with typed-backlog items (the S2 patterns that the old execute
    does NOT handle). Returns (project, product_base).
    """
    project, product = _make_project(tmp_path)
    # Typed backlog: STORY-024 with status "backlog"
    _write_md(
        product,
        "backlog/stories/STORY-024-parallel-run.md",
        frontmatter={
            "id": "STORY-024",
            "title": "Parallel run",
            "status": "backlog",
            "type": "story",
        },
    )
    return project, product


def _make_bespoke_project(tmp_path: Path) -> tuple[Path, Path]:
    """
    A project with bespoke EPIC-NNN/US-* layout.
    """
    project, product = _make_project(tmp_path)
    # Bespoke epic — no frontmatter
    epic_dir = product / "stories" / "EPIC-003"
    epic_dir.mkdir(parents=True)
    (epic_dir / "EPIC-003.md").write_text(
        "# EPIC-003: Data Model\n\nEpic content.\n", encoding="utf-8"
    )
    # Bespoke user story — no frontmatter, with .feature paired
    (epic_dir / "US-DM-002.md").write_text(
        "# US-DM-002: Data mapping\n\nBody references EPIC-003.\n", encoding="utf-8"
    )
    (epic_dir / "US-DM-002.feature").write_text(
        "Feature: US-DM-002 Data mapping\n"
        "  Scenario: basic mapping\n"
        "    Given the system has US-DM-002\n",
        encoding="utf-8",
    )
    return project, product


def _make_full_mixed_project(tmp_path: Path) -> tuple[Path, Path]:
    """
    Project combining typed-backlog, bespoke epics, MS-001 and SP-001 (must not move).
    """
    project, product = _make_project(tmp_path)
    # Typed backlog
    _write_md(
        product,
        "backlog/stories/STORY-024-parallel-run.md",
        frontmatter={
            "id": "STORY-024",
            "title": "Parallel run",
            "status": "backlog",
            "type": "story",
        },
    )
    # Bespoke
    epic_dir = product / "stories" / "EPIC-003"
    epic_dir.mkdir(parents=True)
    (epic_dir / "EPIC-003.md").write_text(
        "# EPIC-003: Data Model\n\nEpic body.\n", encoding="utf-8"
    )
    (epic_dir / "US-DM-002.md").write_text(
        "# US-DM-002: Data mapping\n\nBody epic: EPIC-003\n", encoding="utf-8"
    )
    (epic_dir / "US-DM-002.feature").write_text(
        "Feature: US-DM-002\n  Scenario: test\n    Given US-DM-002 works\n",
        encoding="utf-8",
    )
    # MS-001 — must not change
    _write_md(
        product,
        "milestones/MS-001-core.md",
        frontmatter={
            "id": "MS-001",
            "title": "Core milestone",
            "status": "active",
            "type": "milestone",
        },
    )
    # SP-001 — must not change
    _write_md(
        product,
        "sprints/SP-001-hardening.md",
        frontmatter={
            "id": "SP-001",
            "title": "Hardening sprint",
            "status": "active",
            "type": "sprint",
        },
    )
    return project, product


# ===========================================================================
# Scenario: Snapshot created and verified before any file moves
# ===========================================================================

class TestSnapshotCreated:
    """
    After run_migration(dry_run=False) on a project with migratable items, a
    snapshot archive exists under _backups_dir(project) and verify_snapshot is True.
    """

    def test_snapshot_file_exists_after_execute(self, tmp_path):
        project, _ = _make_typed_legacy_project(tmp_path)
        _execute(project)

        if _IMPORTS_MISSING:
            pytest.fail("_backups_dir not importable")

        backups = _backups_dir(project)
        snaps = list(backups.glob("*.tar.gz"))
        assert snaps, (
            "after execute, at least one snapshot .tar.gz must exist under "
            f"{backups}; got none"
        )

    def test_snapshot_is_valid_tar(self, tmp_path):
        project, _ = _make_typed_legacy_project(tmp_path)
        _execute(project)

        backups = _backups_dir(project)
        snaps = list(backups.glob("*.tar.gz"))
        assert snaps, "no snapshot found"
        assert verify_snapshot(str(snaps[-1])), (
            f"verify_snapshot must return True for the snapshot at {snaps[-1]}; "
            "snapshot is corrupt or empty"
        )

    def test_result_dict_contains_snapshot_path(self, tmp_path):
        project, _ = _make_typed_legacy_project(tmp_path)
        result = _execute(project)

        assert "snapshot" in result, (
            f"result dict must contain 'snapshot' key; got keys: {list(result.keys())}"
        )
        snap_path = Path(result["snapshot"])
        assert snap_path.exists(), (
            f"result['snapshot'] must point to an existing file; got {snap_path}"
        )


# ===========================================================================
# Scenario: Typed-backlog dirs are migrated — old path gone, new frontmatter correct
# ===========================================================================

class TestTypedBacklogMigrated:
    """
    backlog/stories/STORY-024 (status "backlog") -> old path gone;
    a file under backlog/ has frontmatter id matching ISSUE-\\d+,
    legacy_id "STORY-024", status remapped (not "backlog");
    no backlog/{stories,bugs,debt,chores} dir remains.
    """

    def test_old_typed_backlog_path_gone_after_execute(self, tmp_path):
        project, product = _make_typed_legacy_project(tmp_path)
        old_path = product / "backlog" / "stories" / "STORY-024-parallel-run.md"
        assert old_path.exists(), "precondition: source file must exist before execute"

        _execute(project)

        assert not old_path.exists(), (
            f"STORY-024 source file must be removed after execute; "
            f"still present at {old_path}"
        )

    def test_migrated_file_exists_with_issue_id(self, tmp_path):
        project, product = _make_typed_legacy_project(tmp_path)
        _execute(project)

        # Find any file whose frontmatter id matches ISSUE-\d+
        all_md = list(product.rglob("*.md"))
        issue_files = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
        ]
        assert issue_files, (
            "after execute, at least one file with frontmatter id matching ISSUE-\\d+ "
            "must exist in the product base; got none"
        )

    def test_migrated_file_has_legacy_id_in_frontmatter(self, tmp_path):
        project, product = _make_typed_legacy_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
        ]
        assert migrated, "no migrated ISSUE-* file found"
        fm = _read_frontmatter(migrated[0])
        legacy_field = fm.get("legacy_id") or fm.get("migrated_from")
        assert legacy_field == "STORY-024", (
            f"migrated file must have legacy_id/migrated_from == 'STORY-024'; "
            f"got frontmatter: {fm!r}"
        )

    def test_status_remapped_not_backlog(self, tmp_path):
        project, product = _make_typed_legacy_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
        ]
        assert migrated, "no migrated ISSUE-* file found"
        fm = _read_frontmatter(migrated[0])
        assert fm.get("status") != "backlog", (
            f"migrated file status must not be 'backlog' (STATUS_REMAP: backlog->new); "
            f"got status={fm.get('status')!r}"
        )
        assert fm.get("status") == "new", (
            f"status 'backlog' must remap to 'new'; got {fm.get('status')!r}"
        )

    def test_typed_subdir_does_not_remain(self, tmp_path):
        project, product = _make_typed_legacy_project(tmp_path)
        _execute(project)

        for subdir in ("stories", "bugs", "debt", "chores"):
            typed_dir = product / "backlog" / subdir
            # The dir must not exist OR must be empty
            if typed_dir.exists():
                md_files = [f for f in typed_dir.rglob("*.md") if f.is_file()]
                assert not md_files, (
                    f"backlog/{subdir}/ must have no .md files after migration; "
                    f"found: {[str(f) for f in md_files]}"
                )


# ===========================================================================
# Scenario: Bespoke epic migrated — EPIC-003 -> EP-003 under roadmap/epics/
# ===========================================================================

class TestBespokeEpicMigrated:
    """
    stories/EPIC-003/EPIC-003.md (no frontmatter) -> a file with id "EP-003"
    under roadmap/epics/.
    """

    def test_bespoke_epic_file_has_ep_003_id(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        ep_files = [
            f for f in all_md
            if _read_frontmatter(f).get("id") == "EP-003"
        ]
        assert ep_files, (
            "after execute, a file with frontmatter id='EP-003' must exist; "
            "bespoke EPIC-003 must be migrated to EP-003"
        )

    def test_bespoke_epic_dest_under_roadmap_epics(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        ep_files = [
            f for f in all_md
            if _read_frontmatter(f).get("id") == "EP-003"
        ]
        assert ep_files, "EP-003 file must exist"
        ep_path = ep_files[0]
        assert "roadmap" in str(ep_path) and "epics" in str(ep_path), (
            f"EP-003 file must be under roadmap/epics/; got {ep_path}"
        )

    def test_bespoke_epic_old_path_gone(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        old_path = product / "stories" / "EPIC-003" / "EPIC-003.md"
        assert old_path.exists(), "precondition: EPIC-003.md must exist before execute"

        _execute(project)

        assert not old_path.exists(), (
            f"EPIC-003.md at old path must be gone after migration; "
            f"still present: {old_path}"
        )

    def test_bespoke_epic_synthesized_frontmatter_has_required_fields(self, tmp_path):
        """Tier B: EPIC-003.md had no frontmatter; execute must synthesize id/type/title/status."""
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        ep_files = [
            f for f in all_md
            if _read_frontmatter(f).get("id") == "EP-003"
        ]
        assert ep_files, "EP-003 file must exist"
        fm = _read_frontmatter(ep_files[0])
        for field in ("id", "type", "title", "status"):
            assert fm.get(field), (
                f"synthesized frontmatter for EP-003 must have non-empty field '{field}'; "
                f"got frontmatter: {fm!r}"
            )


# ===========================================================================
# Scenario: Bespoke user story migrated — US-DM-002 -> ISSUE-NNN with epic link
# ===========================================================================

class TestBespokeUserStoryMigrated:
    """
    US-DM-002 (no frontmatter) -> migrated story id ISSUE-\\d+,
    frontmatter epic == "EP-003", and synthesized frontmatter has id+type+title+status.
    """

    def test_us_dm_002_migrated_to_issue_id(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        issue_files = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert issue_files, (
            "US-DM-002 must be migrated to a file with ISSUE-* id and "
            "legacy_id/migrated_from == 'US-DM-002'"
        )

    def test_us_dm_002_frontmatter_epic_is_ep_003(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        us_dm_002_migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert us_dm_002_migrated, "US-DM-002 migrated file must exist"
        fm = _read_frontmatter(us_dm_002_migrated[0])
        assert fm.get("epic") == "EP-003", (
            f"migrated US-DM-002 must have frontmatter epic='EP-003'; "
            f"got epic={fm.get('epic')!r}, frontmatter: {fm!r}"
        )

    def test_us_dm_002_synthesized_frontmatter_has_required_fields(self, tmp_path):
        """Tier B: US-DM-002.md had no frontmatter; execute must synthesize id/type/title/status."""
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        us_dm_002_migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert us_dm_002_migrated, "US-DM-002 migrated file must exist"
        fm = _read_frontmatter(us_dm_002_migrated[0])
        for field in ("id", "type", "title", "status"):
            assert fm.get(field), (
                f"synthesized frontmatter for US-DM-002 must have non-empty '{field}'; "
                f"got frontmatter: {fm!r}"
            )


# ===========================================================================
# Scenario: .feature file moves alongside migrated story
# ===========================================================================

class TestFeatureFileMoved:
    """
    US-DM-002.feature -> old path gone; a .feature exists alongside the migrated
    story sharing its new id stem.
    """

    def test_old_feature_path_gone(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        old_feature = product / "stories" / "EPIC-003" / "US-DM-002.feature"
        assert old_feature.exists(), "precondition: .feature file must exist before execute"

        _execute(project)

        assert not old_feature.exists(), (
            f"US-DM-002.feature at old path must be gone after migration; "
            f"still present: {old_feature}"
        )

    def test_new_feature_file_exists_with_story_new_id(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        # Find the migrated story for US-DM-002
        all_md = list(product.rglob("*.md"))
        us_files = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert us_files, "US-DM-002 migrated .md must exist"
        story_stem = us_files[0].stem  # e.g. "ISSUE-001"
        story_id = _read_frontmatter(us_files[0])["id"]

        # Find .feature files
        all_features = list(product.rglob("*.feature"))
        matching = [
            f for f in all_features
            if story_id in f.name or story_stem in f.name
        ]
        assert matching, (
            f"a .feature file containing the story's new id {story_id!r} must exist; "
            f"found .feature files: {[str(f) for f in all_features]}"
        )

    def test_feature_file_not_still_in_bespoke_epic_dir(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        old_feature = product / "stories" / "EPIC-003" / "US-DM-002.feature"
        assert not old_feature.exists(), (
            "US-DM-002.feature must not remain in the bespoke epic dir after migration"
        )


# ===========================================================================
# Scenario: Reference edits applied — old ids replaced in bodies and frontmatter
# ===========================================================================

class TestReferenceEditsApplied:
    """
    A body mentioning US-DM-002 and a frontmatter epic: EPIC-003 ->
    after execute, no migrated file contains the old id outside legacy_id;
    the epic reference uses the new id.
    """

    def _make_cross_ref_project(self, tmp_path: Path) -> tuple[Path, Path]:
        project, product = _make_project(tmp_path)
        # Epic that mentions the story
        epic_dir = product / "stories" / "EPIC-003"
        epic_dir.mkdir(parents=True)
        (epic_dir / "EPIC-003.md").write_text(
            "# EPIC-003: Epic\n\nSee US-DM-002 for details.\n",
            encoding="utf-8",
        )
        # Story with frontmatter epic referencing old id
        _write_md(
            product,
            "stories/EPIC-003/US-DM-002.md",
            frontmatter={
                "id": "US-DM-002",
                "title": "Data mapping",
                "status": "new",
                "type": "story",
                "epic": "EPIC-003",
            },
            body="This implements US-DM-002 as part of EPIC-003.\n",
        )
        return project, product

    def test_migrated_files_do_not_contain_us_dm_002_outside_legacy_id(self, tmp_path):
        project, product = self._make_cross_ref_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        for f in all_md:
            text = f.read_text(encoding="utf-8")
            # The old id US-DM-002 must only appear inside legacy_id/migrated_from field values,
            # not as a standalone reference in body text or other frontmatter
            fm = _read_frontmatter(f)
            legacy_val = fm.get("legacy_id") or fm.get("migrated_from") or ""
            # Strip the frontmatter block for body check
            if text.startswith("---"):
                parts = text.split("---", 2)
                body_text = parts[2] if len(parts) >= 3 else ""
            else:
                body_text = text
            # US-DM-002 must not appear as a standalone token in the body
            assert not re.search(r"(?<![A-Za-z0-9\-])US-DM-002(?![A-Za-z0-9\-])", body_text), (
                f"file {f.name} body must not contain old id 'US-DM-002' after reference "
                f"rewrite; found in body. File content snippet: {body_text[:200]!r}"
            )

    def test_migrated_epic_field_uses_new_id_not_old(self, tmp_path):
        project, product = self._make_cross_ref_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        # Find the migrated US-DM-002 story
        us_migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert us_migrated, "migrated US-DM-002 story must exist"
        fm = _read_frontmatter(us_migrated[0])
        epic_val = fm.get("epic", "")
        assert epic_val != "EPIC-003", (
            f"migrated story's epic field must be the new id 'EP-003', not old 'EPIC-003'; "
            f"got epic={epic_val!r}"
        )
        assert epic_val == "EP-003", (
            f"migrated story's epic field must be 'EP-003'; got {epic_val!r}"
        )


# ===========================================================================
# Scenario: MIGRATION-MAP.md written listing all old->new mappings
# ===========================================================================

class TestMigrationMapWritten:
    """
    MIGRATION-MAP.md exists under product base listing old->new for every migrated item.
    """

    def test_migration_map_file_exists_after_execute(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        migration_map = product / "MIGRATION-MAP.md"
        assert migration_map.exists(), (
            f"MIGRATION-MAP.md must exist under the product base after execute; "
            f"not found at {migration_map}"
        )

    def test_migration_map_contains_us_dm_002(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        migration_map = product / "MIGRATION-MAP.md"
        assert migration_map.exists(), "MIGRATION-MAP.md must exist"
        content = migration_map.read_text(encoding="utf-8")
        assert "US-DM-002" in content, (
            "MIGRATION-MAP.md must mention the migrated id 'US-DM-002'"
        )

    def test_migration_map_contains_epic_003(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        migration_map = product / "MIGRATION-MAP.md"
        assert migration_map.exists(), "MIGRATION-MAP.md must exist"
        content = migration_map.read_text(encoding="utf-8")
        assert "EPIC-003" in content, (
            "MIGRATION-MAP.md must mention the migrated epic 'EPIC-003'"
        )

    def test_migration_map_maps_old_to_new(self, tmp_path):
        """MIGRATION-MAP.md must contain the new id (EP-003 or ISSUE-*) alongside old id."""
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        migration_map = product / "MIGRATION-MAP.md"
        assert migration_map.exists(), "MIGRATION-MAP.md must exist"
        content = migration_map.read_text(encoding="utf-8")
        # Must have EP-003 as the new id for EPIC-003
        assert "EP-003" in content, (
            "MIGRATION-MAP.md must list the new id 'EP-003' for EPIC-003"
        )
        # Must have at least one ISSUE-* id for US-DM-002
        assert re.search(r"ISSUE-\d+", content), (
            "MIGRATION-MAP.md must list at least one ISSUE-* id for the migrated story"
        )

    def test_migration_map_has_entry_for_every_migrated_item(self, tmp_path):
        """Every old id in MIGRATION-MAP must resolve to exactly one migrated file."""
        project, product = _make_full_mixed_project(tmp_path)
        _execute(project)

        migration_map = product / "MIGRATION-MAP.md"
        assert migration_map.exists(), "MIGRATION-MAP.md must exist"
        content = migration_map.read_text(encoding="utf-8")

        # Items we know were migrated
        for old_id in ("STORY-024", "EPIC-003", "US-DM-002"):
            assert old_id in content, (
                f"MIGRATION-MAP.md must contain entry for '{old_id}'; "
                f"content snippet: {content[:500]!r}"
            )


# ===========================================================================
# Scenario: MS-001 and SP-001 unchanged after execute
# ===========================================================================

class TestPassThroughFilesUnchanged:
    """
    MS-001 and SP-001 files still exist unchanged (compare content hash before/after).
    """

    def test_ms_001_content_unchanged(self, tmp_path):
        project, product = _make_full_mixed_project(tmp_path)
        ms_path = product / "milestones" / "MS-001-core.md"
        assert ms_path.exists(), "precondition: MS-001 must exist"
        before_hash = _sha256(ms_path.read_bytes())

        _execute(project)

        assert ms_path.exists(), (
            f"MS-001 file must still exist after migration; gone from {ms_path}"
        )
        after_hash = _sha256(ms_path.read_bytes())
        assert before_hash == after_hash, (
            "MS-001 file content must be byte-for-byte identical before and after execute"
        )

    def test_sp_001_content_unchanged(self, tmp_path):
        project, product = _make_full_mixed_project(tmp_path)
        sp_path = product / "sprints" / "SP-001-hardening.md"
        assert sp_path.exists(), "precondition: SP-001 must exist"
        before_hash = _sha256(sp_path.read_bytes())

        _execute(project)

        _assert_bespoke_migration_ran(product)
        assert sp_path.exists(), (
            f"SP-001 file must still exist after migration; gone from {sp_path}"
        )
        after_hash = _sha256(sp_path.read_bytes())
        assert before_hash == after_hash, (
            "SP-001 file content must be byte-for-byte identical before and after execute"
        )


# ===========================================================================
# Scenario: Post-condition — characterize_project reports clean state
# ===========================================================================

class TestPostConditionClean:
    """
    characterize_project(project) after execute reports:
      has_typed_backlog_dirs == False
      taxonomy_candidate_count == 0 (old prefixes gone)
      duplicate_count == 0
    """

    def test_has_typed_backlog_dirs_false_after_execute(self, tmp_path):
        if _CHARACTERIZE_MISSING:
            pytest.fail("characterize_project not importable")
        project, product = _make_full_mixed_project(tmp_path)
        _execute(project)

        report = characterize_project(project)
        assert report["layout"]["has_typed_backlog_dirs"] is False, (
            "characterize_project must report has_typed_backlog_dirs=False after execute; "
            f"got {report['layout']['has_typed_backlog_dirs']!r}"
        )

    def test_taxonomy_candidate_count_zero_after_execute(self, tmp_path):
        if _CHARACTERIZE_MISSING:
            pytest.fail("characterize_project not importable")
        project, product = _make_full_mixed_project(tmp_path)
        _execute(project)

        report = characterize_project(project)
        count = report["migration_risk"]["taxonomy_candidate_count"]
        assert count == 0, (
            f"taxonomy_candidate_count must be 0 after execute (all old prefixes gone); "
            f"got {count}"
        )

    def test_duplicate_count_zero_after_execute(self, tmp_path):
        if _CHARACTERIZE_MISSING:
            pytest.fail("characterize_project not importable")
        project, product = _make_full_mixed_project(tmp_path)
        _execute(project)

        _assert_bespoke_migration_ran(product)
        report = characterize_project(project)
        dup_count = report["ids"]["duplicate_count"]
        assert dup_count == 0, (
            f"duplicate_count must be 0 after execute; got {dup_count}. "
            f"Duplicates: {report['ids']['duplicates']!r}"
        )


# ===========================================================================
# Scenario: Rollback restores pre-migration state exactly
# ===========================================================================

class TestRollback:
    """
    Snapshot every file's content hash before execute; run execute; then
    rollback(snapshot, project); assert every pre-existing file matches its
    prior hash and no migration-created file remains.
    """

    def test_rollback_restores_all_original_files(self, tmp_path):
        project, product = _make_full_mixed_project(tmp_path)
        before = _snapshot_tree(product)

        result = _execute(project)
        snap_path = result.get("snapshot")
        assert snap_path, "execute must return a snapshot path for rollback test"

        # S3 guard: verify bespoke migration ran before rollback is meaningful
        _assert_bespoke_migration_ran(product)
        rollback(snap_path, str(project))

        after = _snapshot_tree(product)
        # Every file present before must be present after rollback
        for path_str, before_bytes in before.items():
            assert path_str in after, (
                f"rollback must restore file {path_str!r}; it is missing after rollback"
            )
            assert before_bytes == after[path_str], (
                f"rollback must restore byte-for-byte content of {path_str!r}"
            )

    def test_rollback_removes_migration_created_files(self, tmp_path):
        """Files created by migration (ISSUE-*, EP-*, MIGRATION-MAP.md) must be gone after rollback."""
        project, product = _make_full_mixed_project(tmp_path)
        before = _snapshot_tree(product)

        result = _execute(project)
        snap_path = result.get("snapshot")
        assert snap_path, "execute must return snapshot path"

        # S3 guard: verify bespoke migration ran before rollback is meaningful
        _assert_bespoke_migration_ran(product)
        rollback(snap_path, str(project))

        after = _snapshot_tree(product)
        new_files = set(after.keys()) - set(before.keys())
        assert not new_files, (
            f"after rollback, no migration-created files must remain; "
            f"found: {new_files!r}"
        )


# ===========================================================================
# Scenario: Conflict causes refusal — no product file changed
# ===========================================================================

class TestRefuseOnConflict:
    """
    Two real files both id STORY-007 -> run_migration(dry_run=False) returns
    ok False, reports STORY-007 as unresolved duplicate, and NO product file
    changed (hash-compare whole tree before/after).
    """

    def _make_conflict_project(self, tmp_path: Path) -> tuple[Path, Path]:
        project, product = _make_project(tmp_path)
        _write_md(
            product,
            "backlog/stories/STORY-007-a.md",
            frontmatter={"id": "STORY-007", "title": "Seven a", "status": "new", "type": "story"},
        )
        _write_md(
            product,
            "backlog/stories/STORY-007-b.md",
            frontmatter={"id": "STORY-007", "title": "Seven b", "status": "new", "type": "story"},
        )
        return project, product

    def test_conflict_returns_ok_false(self, tmp_path):
        project, _ = self._make_conflict_project(tmp_path)
        result = _execute(project)

        assert result.get("ok") is False, (
            f"run_migration must return ok=False when unresolved duplicates exist; "
            f"got ok={result.get('ok')!r}, result: {result!r}"
        )

    def test_conflict_reports_story_007(self, tmp_path):
        project, _ = self._make_conflict_project(tmp_path)
        result = _execute(project)

        # The error or errors must mention STORY-007
        error_str = str(result.get("errors", "")) + str(result.get("error", "")) + str(result)
        assert "STORY-007" in error_str, (
            f"result must report STORY-007 as the unresolved duplicate; "
            f"got result: {result!r}"
        )

    def test_conflict_no_product_file_changed(self, tmp_path):
        project, product = self._make_conflict_project(tmp_path)
        before = _snapshot_tree(product)

        result = _execute(project)
        # S3 guard: this test is only meaningful when S3 recognized the conflict
        # via the _build_dry_run_plan engine (S2 duplicate detection).
        # The old engine also happens to not change files (but for different reasons).
        # We require that ok=False is specifically about the unresolved duplicate.
        assert result.get("ok") is False, (
            "conflict project must make run_migration return ok=False; "
            "this is the S3 behavior gate"
        )

        after = _snapshot_tree(product)
        # No files added, removed, or modified in product base
        assert set(before.keys()) == set(after.keys()), (
            f"conflict must not add or remove files; "
            f"added: {set(after) - set(before)!r}, "
            f"removed: {set(before) - set(after)!r}"
        )
        for path_str in before:
            assert before[path_str] == after[path_str], (
                f"conflict must not modify file {path_str!r}"
            )


# ===========================================================================
# Scenario: Idempotent — already-v4 project is a no-op
# ===========================================================================

class TestIdempotent:
    """
    A project already in v4 (only ISSUE/EP/MS/SP ids, no typed dirs) ->
    execute again moves/modifies nothing, ok True.
    """

    def _make_v4_project(self, tmp_path: Path) -> tuple[Path, Path]:
        project, product = _make_project(tmp_path)
        _write_md(
            product,
            "backlog/ISSUE-001-existing.md",
            frontmatter={
                "id": "ISSUE-001",
                "title": "Existing story",
                "status": "active",
                "type": "enhancement",
            },
        )
        _write_md(
            product,
            "milestones/MS-001-core.md",
            frontmatter={
                "id": "MS-001",
                "title": "Core milestone",
                "status": "active",
                "type": "milestone",
            },
        )
        return project, product

    def test_v4_project_execute_returns_ok_true(self, tmp_path):
        project, _ = self._make_v4_project(tmp_path)
        result = _execute(project)

        assert result.get("ok") is True, (
            f"execute on an already-v4 project must return ok=True; "
            f"got {result!r}"
        )

    def test_v4_project_no_files_changed(self, tmp_path):
        project, product = self._make_v4_project(tmp_path)
        before = _snapshot_tree(product)

        _execute(project)

        after = _snapshot_tree(product)
        # Allow MIGRATION-MAP.md or state files but no existing file must change
        for path_str, before_bytes in before.items():
            assert path_str in after, (
                f"already-v4 execute must not remove file {path_str!r}"
            )
            assert before_bytes == after[path_str], (
                f"already-v4 execute must not modify file {path_str!r}"
            )


# ===========================================================================
# Scenario: Structural integrity — MIGRATION-MAP resolves one-to-one
# ===========================================================================

class TestStructuralIntegrity:
    """
    Every old id in MIGRATION-MAP resolves to exactly one migrated file on disk;
    migrated ids unique; each migrated work item has present canonical frontmatter
    (id/type/title/status).
    """

    def test_every_migrated_id_resolves_to_exactly_one_file(self, tmp_path):
        project, product = _make_full_mixed_project(tmp_path)
        _execute(project)

        _assert_bespoke_migration_ran(product)
        all_md = list(product.rglob("*.md"))
        # Build id -> list of files
        id_to_files: dict[str, list[Path]] = {}
        for f in all_md:
            fm = _read_frontmatter(f)
            fid = fm.get("id", "")
            if fid:
                id_to_files.setdefault(fid, []).append(f)

        for fid, files in id_to_files.items():
            assert len(files) == 1, (
                f"id '{fid}' must appear in exactly one file after migration; "
                f"found in {len(files)}: {[str(f) for f in files]}"
            )

    def test_migrated_ids_unique(self, tmp_path):
        project, product = _make_full_mixed_project(tmp_path)
        _execute(project)

        _assert_bespoke_migration_ran(product)
        all_md = list(product.rglob("*.md"))
        ids_seen: list[str] = []
        for f in all_md:
            fm = _read_frontmatter(f)
            fid = fm.get("id")
            if fid:
                ids_seen.append(fid)

        assert len(ids_seen) == len(set(ids_seen)), (
            f"all frontmatter ids must be unique after migration; "
            f"duplicates: {[i for i in ids_seen if ids_seen.count(i) > 1]!r}"
        )

    def test_migrated_work_items_have_canonical_frontmatter(self, tmp_path):
        """Every migrated ISSUE-* and EP-* file must have id, type, title, status."""
        project, product = _make_full_mixed_project(tmp_path)
        _execute(project)

        _assert_bespoke_migration_ran(product)
        all_md = list(product.rglob("*.md"))
        for f in all_md:
            fm = _read_frontmatter(f)
            fid = fm.get("id", "")
            if ISSUE_RE.match(fid) or EP_RE.match(fid):
                for field in ("id", "type", "title", "status"):
                    assert fm.get(field), (
                        f"migrated file {f.name} must have non-empty frontmatter field "
                        f"'{field}'; got frontmatter: {fm!r}"
                    )

    def test_migration_map_old_id_resolves_to_one_disk_file(self, tmp_path):
        """Each old id in MIGRATION-MAP.md corresponds to exactly one file on disk."""
        project, product = _make_full_mixed_project(tmp_path)
        _execute(project)

        migration_map = product / "MIGRATION-MAP.md"
        assert migration_map.exists(), "MIGRATION-MAP.md must exist for integrity check"
        content = migration_map.read_text(encoding="utf-8")

        # Extract old->new pairs by looking for ISSUE-* and EP-* new ids in the map
        new_ids_in_map = re.findall(r"\b(ISSUE-\d+|EP-\d+)\b", content)

        all_md = list(product.rglob("*.md"))
        for new_id in set(new_ids_in_map):
            matching = [
                f for f in all_md
                if _read_frontmatter(f).get("id") == new_id
            ]
            assert len(matching) == 1, (
                f"new id '{new_id}' from MIGRATION-MAP must resolve to exactly one "
                f"file on disk; found {len(matching)}: {[str(f) for f in matching]}"
            )


# ===========================================================================
# NEW SAFETY / EDGE TESTS (WI-017 S3 augmentation)
# ===========================================================================

# ---------------------------------------------------------------------------
# Test 1 (R1) MS-001 not relocated to roadmap/milestones/ — S2 plan applied, not old engine
# ---------------------------------------------------------------------------

class TestMilestoneNotRelocatedByOldEngine:
    """
    R1: After execute on a project that has milestones/MS-001, the file remains at
    milestones/MS-001 (it is a v4 pass-through). The S2 plan must have run —
    proved by the fact that the bespoke EPIC-003 IS migrated. This distinguishes
    S2-plan execution from the old engine (which would also move MS-NNN to
    roadmap/milestones/).
    """

    def test_ms_001_remains_in_milestones_not_roadmap(self, tmp_path):
        project, product = _make_full_mixed_project(tmp_path)
        ms_path = product / "milestones" / "MS-001-core.md"
        assert ms_path.exists(), "precondition: MS-001 must exist"

        _execute(project)

        _assert_bespoke_migration_ran(product)

        assert ms_path.exists(), (
            f"MS-001 must remain at milestones/MS-001-core.md after S2-plan execution; "
            f"it is a v4 pass-through. File gone from {ms_path}"
        )
        wrong_path = product / "roadmap" / "milestones"
        if wrong_path.exists():
            relocated_ms = [
                f for f in wrong_path.rglob("*.md")
                if _read_frontmatter(f).get("id") == "MS-001"
            ]
            assert not relocated_ms, (
                f"MS-001 must NOT appear under roadmap/milestones/ — "
                f"that is what the OLD engine does. S2 plan leaves it in place. "
                f"Found: {[str(f) for f in relocated_ms]}"
            )


# ---------------------------------------------------------------------------
# Test 2 (R2) Moved file's body has cross-ref to another migrated id rewritten
# ---------------------------------------------------------------------------

class TestMovedFileCrossRefRewritten:
    """
    R2: A file that is ITSELF moved AND whose body mentions another migrated old id
    must have that reference rewritten to the new id, readable at the NEW path.
    """

    def _make_cross_ref_move_project(self, tmp_path):
        project, product = _make_project(tmp_path)
        epic_dir = product / "stories" / "EPIC-003"
        epic_dir.mkdir(parents=True)
        (epic_dir / "EPIC-003.md").write_text(
            "# EPIC-003: Data Model\n\nThis epic includes US-DM-002.\n",
            encoding="utf-8",
        )
        (epic_dir / "US-DM-002.md").write_text(
            "# US-DM-002: Data mapping\n\nSee EPIC-003 for context.\n",
            encoding="utf-8",
        )
        return project, product

    def test_moved_file_body_ref_rewritten_at_new_path(self, tmp_path):
        project, product = self._make_cross_ref_move_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        us_migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert us_migrated, (
            "US-DM-002 must be migrated to an ISSUE-* file to assert reference rewrite"
        )
        migrated_file = us_migrated[0]
        text = migrated_file.read_text(encoding="utf-8")
        assert "EPIC-003" not in text or (
            "migrated_from" in text and text.count("EPIC-003") <= text.count("migrated_from")
        ), (
            f"moved file at {migrated_file} must not contain old 'EPIC-003' reference in body; "
            f"content snippet: {text[:400]!r}"
        )
        assert "EP-003" in text, (
            f"moved US-DM-002 file at {migrated_file} must reference 'EP-003' (new id) in its "
            f"body/frontmatter after reference rewrite; content snippet: {text[:400]!r}"
        )


# ---------------------------------------------------------------------------
# Test 3 (R2) Body mentioning a DEBT/EPIC old id rewritten after execute
# ---------------------------------------------------------------------------

class TestDebtEpicRefRewrittenInBody:
    """
    R2 extension: A body mentioning a DEBT/EPIC-style old id (not just BL/STORY)
    must be rewritten after execute.
    """

    def _make_debt_ref_project(self, tmp_path):
        project, product = _make_project(tmp_path)
        epic_dir = product / "stories" / "EPIC-003"
        epic_dir.mkdir(parents=True)
        (epic_dir / "EPIC-003.md").write_text(
            "# EPIC-003: Data Model\n\nCore epic.\n",
            encoding="utf-8",
        )
        (epic_dir / "US-DM-002.md").write_text(
            "# US-DM-002: Data mapping\n\nRelated to EPIC-003 data work.\n",
            encoding="utf-8",
        )
        return project, product

    def test_epic_old_id_rewritten_in_body(self, tmp_path):
        project, product = self._make_debt_ref_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        ep_files = [
            f for f in all_md
            if _read_frontmatter(f).get("id") == "EP-003"
        ]
        assert ep_files, (
            "EPIC-003 must be migrated to EP-003 for this reference-rewrite test"
        )
        ep_file = ep_files[0]
        body_text = ep_file.read_text(encoding="utf-8")
        assert re.search(r"(?<![A-Za-z0-9\-])EPIC-003(?![A-Za-z0-9\-])", body_text) is None, (
            f"EP-003 file body must not contain old 'EPIC-003' id after reference rewrite; "
            f"content snippet: {body_text[:400]!r}"
        )

        us_files = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert us_files, "US-DM-002 must be migrated"
        us_body = us_files[0].read_text(encoding="utf-8")
        assert re.search(r"(?<![A-Za-z0-9\-])EPIC-003(?![A-Za-z0-9\-])", us_body) is None, (
            f"migrated US-DM-002 file body must not contain old 'EPIC-003' id; "
            f"content snippet: {us_body[:400]!r}"
        )


# ---------------------------------------------------------------------------
# Test 4 (R3) Pre-existing dest collision: refuse with no overwrite + content unchanged
# ---------------------------------------------------------------------------

class TestDestCollisionRefusedNoOverwrite:
    """
    R3: A pre-existing backlog/ISSUE-001.md with unrelated content + a plan that
    would assign ISSUE-001 -> run_migration(dry_run=False) returns ok False,
    and the pre-existing file is byte-for-byte unchanged.
    """

    def _make_dest_collision_project(self, tmp_path):
        project, product = _make_project(tmp_path)
        # Pre-existing ISSUE-001 at the exact dest path the migrator would write
        pre_existing = product / "backlog" / "ISSUE-001.md"
        pre_existing.parent.mkdir(parents=True, exist_ok=True)
        pre_existing.write_text(
            "---\nid: ISSUE-001\ntitle: Unrelated existing\nstatus: active\ntype: enhancement\n---\n\nPre-existing content.\n",
            encoding="utf-8",
        )
        # A typed-backlog item that would be assigned ISSUE-001 by the counter
        _write_md(
            product,
            "backlog/stories/STORY-001-first.md",
            frontmatter={
                "id": "STORY-001",
                "title": "First story",
                "status": "backlog",
                "type": "story",
            },
        )
        return project, product, pre_existing

    def test_dest_collision_returns_ok_false(self, tmp_path):
        project, product, pre_existing = self._make_dest_collision_project(tmp_path)
        result = _execute(project)

        assert result.get("ok") is False, (
            f"run_migration must return ok=False when a destination path (ISSUE-001) "
            f"already exists with unrelated content and overwrite is not set; "
            f"got result: {result!r}"
        )

    def test_dest_collision_pre_existing_file_unchanged(self, tmp_path):
        project, product, pre_existing = self._make_dest_collision_project(tmp_path)
        before_hash = _sha256(pre_existing.read_bytes())
        before_content = pre_existing.read_bytes()

        result = _execute(project)

        assert result.get("ok") is False, (
            "collision must be detected and refused (ok=False)"
        )
        assert pre_existing.exists(), (
            f"pre-existing {pre_existing.name} must still exist after refused migration"
        )
        after_content = pre_existing.read_bytes()
        assert before_content == after_content, (
            "pre-existing ISSUE-001.md must be byte-for-byte unchanged after a refused "
            "migration; content changed unexpectedly"
        )


# ---------------------------------------------------------------------------
# Test 5 (R4) Mid-execution failure triggers auto-rollback — tree matches pre-exec
# ---------------------------------------------------------------------------

class TestAutoRollbackOnFailure:
    """
    R4: Force a mid-execution failure (directory planted at a dest file path) ->
    run_migration(dry_run=False) returns ok False, result includes snapshot,
    and product tree matches pre-execution content hashes (auto-rolled-back).
    """

    def _make_failure_project(self, tmp_path):
        project, product = _make_project(tmp_path)
        epic_dir = product / "stories" / "EPIC-003"
        epic_dir.mkdir(parents=True)
        (epic_dir / "EPIC-003.md").write_text(
            "# EPIC-003: Data Model\n\nEpic content.\n",
            encoding="utf-8",
        )
        (epic_dir / "US-DM-002.md").write_text(
            "# US-DM-002: Data mapping\n\nBody.\n",
            encoding="utf-8",
        )
        return project, product

    def test_auto_rollback_on_failure_ok_false(self, tmp_path):
        import stat
        project, product = self._make_failure_project(tmp_path)

        # Plant a directory at a path the migrator would try to write a file to.
        # The S2 plan puts bespoke epics under roadmap/epics/EP-003/EP-003.md.
        # Planting roadmap/epics/EP-003/EP-003.md as a DIRECTORY prevents the write.
        blocker_dir = product / "roadmap" / "epics" / "EP-003" / "EP-003.md"
        blocker_dir.mkdir(parents=True, exist_ok=True)

        result = _execute(project)

        # Remove the blocker so cleanup works
        import shutil
        try:
            shutil.rmtree(str(product / "roadmap" / "epics" / "EP-003"))
        except Exception:
            pass

        assert result.get("ok") is False, (
            f"run_migration must return ok=False when a mid-execution write fails "
            f"(directory planted at dest path); got result: {result!r}"
        )

    def test_auto_rollback_on_failure_includes_snapshot(self, tmp_path):
        import shutil
        project, product = self._make_failure_project(tmp_path)

        blocker_dir = product / "roadmap" / "epics" / "EP-003" / "EP-003.md"
        blocker_dir.mkdir(parents=True, exist_ok=True)

        result = _execute(project)

        try:
            shutil.rmtree(str(product / "roadmap" / "epics" / "EP-003"))
        except Exception:
            pass

        assert result.get("ok") is False, "failure must be reported"
        assert "snapshot" in result, (
            f"result must contain 'snapshot' key even on failure so rollback is possible; "
            f"got keys: {list(result.keys())}"
        )
        snap = result.get("snapshot")
        if snap:
            assert Path(snap).exists(), (
                f"snapshot path {snap!r} from failed run must exist on disk"
            )

    def test_auto_rollback_on_failure_tree_restored(self, tmp_path):
        import shutil
        project, product = self._make_failure_project(tmp_path)
        before = _snapshot_tree(product)

        blocker_dir = product / "roadmap" / "epics" / "EP-003" / "EP-003.md"
        blocker_dir.mkdir(parents=True, exist_ok=True)

        result = _execute(project)

        try:
            shutil.rmtree(str(product / "roadmap" / "epics" / "EP-003"))
        except Exception:
            pass

        assert result.get("ok") is False, "failure must be reported"

        after = _snapshot_tree(product)
        for path_str, before_bytes in before.items():
            assert path_str in after, (
                f"auto-rollback must restore file {path_str!r}; missing after failed execute"
            )
            assert before_bytes == after[path_str], (
                f"auto-rollback must restore byte-for-byte content of {path_str!r}"
            )
        new_files = set(after.keys()) - set(before.keys())
        migration_artifacts = {
            p for p in new_files
            if "ISSUE-" in p or "EP-" in p or "MIGRATION-MAP" in p
        }
        assert not migration_artifacts, (
            f"after auto-rollback, no migration-created files must remain; "
            f"found: {migration_artifacts!r}"
        )


# ---------------------------------------------------------------------------
# Test 6 (R5) Rollback removes MIGRATION-MAP + new dirs; restores pre-existing file
# ---------------------------------------------------------------------------

class TestRollbackRestoresExactSnapshot:
    """
    R5: MIGRATION-MAP.md absent before migration -> after execute+rollback it does NOT
    exist. A pre-existing roadmap/epics/PRE-EXISTING.md is restored by rollback.
    """

    def _make_rollback_exact_project(self, tmp_path):
        project, product = _make_project(tmp_path)
        epic_dir = product / "stories" / "EPIC-003"
        epic_dir.mkdir(parents=True)
        (epic_dir / "EPIC-003.md").write_text(
            "# EPIC-003: Data Model\n\nEpic content.\n", encoding="utf-8"
        )
        (epic_dir / "US-DM-002.md").write_text(
            "# US-DM-002: Data mapping\n\nBody.\n", encoding="utf-8"
        )
        pre_existing_dir = product / "roadmap" / "epics"
        pre_existing_dir.mkdir(parents=True, exist_ok=True)
        pre_existing = pre_existing_dir / "PRE-EXISTING.md"
        pre_existing.write_text(
            "---\nid: EP-999\ntitle: Pre-existing epic\nstatus: active\ntype: epic\n---\n\nThis was here before.\n",
            encoding="utf-8",
        )
        return project, product, pre_existing

    def test_migration_map_absent_after_rollback(self, tmp_path):
        project, product, pre_existing = self._make_rollback_exact_project(tmp_path)
        migration_map = product / "MIGRATION-MAP.md"
        assert not migration_map.exists(), "precondition: MIGRATION-MAP.md must not exist before execute"

        result = _execute(project)
        snap_path = result.get("snapshot")
        assert snap_path, "execute must return a snapshot path"

        _assert_bespoke_migration_ran(product)
        assert migration_map.exists(), "MIGRATION-MAP.md must be created by execute (test precondition)"

        rollback(snap_path, str(project))

        assert not migration_map.exists(), (
            f"MIGRATION-MAP.md must be ABSENT after rollback (it did not exist before execute); "
            f"found at {migration_map}"
        )

    def test_pre_existing_file_restored_by_rollback(self, tmp_path):
        project, product, pre_existing = self._make_rollback_exact_project(tmp_path)
        before_content = pre_existing.read_bytes()

        result = _execute(project)
        snap_path = result.get("snapshot")
        assert snap_path, "execute must return a snapshot path"

        _assert_bespoke_migration_ran(product)
        rollback(snap_path, str(project))

        assert pre_existing.exists(), (
            f"pre-existing roadmap/epics/PRE-EXISTING.md must be restored after rollback; "
            f"missing at {pre_existing}"
        )
        assert pre_existing.read_bytes() == before_content, (
            "pre-existing file must be byte-for-byte identical after rollback"
        )


# ---------------------------------------------------------------------------
# Test 7 (R6 Tier B) Bespoke EPIC-003.md: synthesized title strips prefix, body preserved
# ---------------------------------------------------------------------------

class TestTierBEpicFrontmatterSynthesis:
    """
    R6 Tier B: EPIC-003.md with only `# EPIC-003: Data Model\n\nEpic prose here.`
    -> after execute, EP-003 frontmatter title == "Data Model" (not "EPIC-003",
    not empty) AND body still contains "Epic prose here.".
    """

    def _make_tier_b_epic_project(self, tmp_path):
        project, product = _make_project(tmp_path)
        epic_dir = product / "stories" / "EPIC-003"
        epic_dir.mkdir(parents=True)
        (epic_dir / "EPIC-003.md").write_text(
            "# EPIC-003: Data Model\n\nEpic prose here.\n",
            encoding="utf-8",
        )
        return project, product

    def test_tier_b_title_strips_prefix(self, tmp_path):
        project, product = self._make_tier_b_epic_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        ep_files = [f for f in all_md if _read_frontmatter(f).get("id") == "EP-003"]
        assert ep_files, "EP-003 must be migrated"
        fm = _read_frontmatter(ep_files[0])
        title = fm.get("title", "")
        assert title == "Data Model", (
            f"Tier B synthesized title must be 'Data Model' (H1 minus 'EPIC-003:' prefix); "
            f"got title={title!r}, frontmatter: {fm!r}"
        )
        assert title != "EPIC-003", (
            "title must not be the bare legacy id 'EPIC-003'"
        )
        assert title, "title must not be empty"

    def test_tier_b_body_preserved(self, tmp_path):
        project, product = self._make_tier_b_epic_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        ep_files = [f for f in all_md if _read_frontmatter(f).get("id") == "EP-003"]
        assert ep_files, "EP-003 must be migrated"
        file_text = ep_files[0].read_text(encoding="utf-8")
        assert "Epic prose here." in file_text, (
            f"Tier B migrated EP-003 file must preserve body prose 'Epic prose here.'; "
            f"content snippet: {file_text[:400]!r}"
        )


# ---------------------------------------------------------------------------
# Test 8 (R6 Tier A) Bespoke file WITH frontmatter: title/status/body preserved verbatim
# ---------------------------------------------------------------------------

class TestTierAFrontmatterPreserved:
    """
    R6 Tier A: US-DM-002.md WITH frontmatter (title "Data mapping", status "active")
    -> migrated file keeps title "Data mapping" and status "active" (not remapped)
    and body preserved.
    """

    def _make_tier_a_project(self, tmp_path):
        project, product = _make_project(tmp_path)
        epic_dir = product / "stories" / "EPIC-003"
        epic_dir.mkdir(parents=True)
        (epic_dir / "EPIC-003.md").write_text(
            "# EPIC-003: Data Model\n\nEpic.\n", encoding="utf-8"
        )
        _write_md(
            product,
            "stories/EPIC-003/US-DM-002.md",
            frontmatter={
                "id": "US-DM-002",
                "title": "Data mapping",
                "status": "active",
                "type": "story",
            },
            body="This is the data mapping story body.\n",
        )
        return project, product

    def test_tier_a_title_preserved(self, tmp_path):
        project, product = self._make_tier_a_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert migrated, "US-DM-002 must be migrated to ISSUE-*"
        fm = _read_frontmatter(migrated[0])
        assert fm.get("title") == "Data mapping", (
            f"Tier A migrated file must keep original title 'Data mapping'; "
            f"got title={fm.get('title')!r}"
        )

    def test_tier_a_status_preserved(self, tmp_path):
        project, product = self._make_tier_a_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert migrated, "US-DM-002 must be migrated"
        fm = _read_frontmatter(migrated[0])
        assert fm.get("status") == "active", (
            f"Tier A migrated file must keep status 'active' (already canonical — no remap); "
            f"got status={fm.get('status')!r}"
        )

    def test_tier_a_body_preserved(self, tmp_path):
        project, product = self._make_tier_a_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert migrated, "US-DM-002 must be migrated"
        file_text = migrated[0].read_text(encoding="utf-8")
        assert "This is the data mapping story body." in file_text, (
            f"Tier A migrated file must preserve original body; "
            f"content snippet: {file_text[:400]!r}"
        )


# ---------------------------------------------------------------------------
# Test 9 (R7) .feature file moves without spurious hash error + internal refs rewritten
# ---------------------------------------------------------------------------

class TestFeatureInternalRefsRewritten:
    """
    R7: US-DM-002.feature with scenario text mentioning US-DM-002 ->
    after execute: moved .feature exists at new id stem, no spurious error occurred
    (run completed ok or with only expected errors), internal text references
    new id (old id absent from the feature file).
    """

    def _make_feature_ref_project(self, tmp_path):
        project, product = _make_project(tmp_path)
        epic_dir = product / "stories" / "EPIC-003"
        epic_dir.mkdir(parents=True)
        (epic_dir / "EPIC-003.md").write_text(
            "# EPIC-003: Data Model\n\nEpic.\n", encoding="utf-8"
        )
        (epic_dir / "US-DM-002.md").write_text(
            "# US-DM-002: Data mapping\n\nBody.\n", encoding="utf-8"
        )
        (epic_dir / "US-DM-002.feature").write_text(
            "Feature: US-DM-002 Data mapping\n"
            "  Scenario: mapping works\n"
            "    Given the system implements US-DM-002\n"
            "    When data is submitted\n"
            "    Then US-DM-002 processes it\n",
            encoding="utf-8",
        )
        return project, product

    def test_feature_moved_exists_at_new_stem(self, tmp_path):
        project, product = self._make_feature_ref_project(tmp_path)
        _execute(project)

        all_features = list(product.rglob("*.feature"))
        all_md = list(product.rglob("*.md"))
        us_migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert us_migrated, "US-DM-002 must be migrated to ISSUE-*"
        story_id = _read_frontmatter(us_migrated[0])["id"]

        matching_features = [f for f in all_features if story_id in f.name]
        assert matching_features, (
            f"a .feature file with the new story id {story_id!r} must exist after migration; "
            f"found .feature files: {[str(f) for f in all_features]}"
        )

    def test_feature_internal_old_id_absent(self, tmp_path):
        project, product = self._make_feature_ref_project(tmp_path)
        result = _execute(project)

        all_features = list(product.rglob("*.feature"))
        all_md = list(product.rglob("*.md"))
        us_migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (_read_frontmatter(f).get("legacy_id") == "US-DM-002"
                 or _read_frontmatter(f).get("migrated_from") == "US-DM-002")
        ]
        assert us_migrated, "US-DM-002 must be migrated"
        story_id = _read_frontmatter(us_migrated[0])["id"]

        matching_features = [f for f in all_features if story_id in f.name]
        assert matching_features, f"moved .feature with {story_id!r} must exist"

        feature_text = matching_features[0].read_text(encoding="utf-8")
        assert re.search(r"(?<![A-Za-z0-9\-])US-DM-002(?![A-Za-z0-9\-])", feature_text) is None, (
            f"moved .feature file must not contain old id 'US-DM-002' after internal ref rewrite; "
            f"content: {feature_text!r}"
        )
        assert story_id in feature_text, (
            f"moved .feature file must contain the new story id {story_id!r} in its text; "
            f"content: {feature_text!r}"
        )


# ---------------------------------------------------------------------------
# Test 10 (R8) MIGRATION-MAP.md: each entry parseable as (old, new) on a single line
# ---------------------------------------------------------------------------

class TestMigrationMapMachineParseable:
    """
    R8: MIGRATION-MAP.md — each old->new pair is parseable on a single line via regex.
    At least one entry round-trips to (old_id, new_id).
    """

    _PAIR_RE = re.compile(
        r"(?P<old>(?:EPIC|US-[A-Z]+|STORY|BL|BUG|DEBT|CHORE|US)-[\w-]+)"
        r".{0,20}?"
        r"(?P<new>(?:ISSUE|EP|MS)-\d+)"
    )

    def test_migration_map_at_least_one_parseable_pair(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        migration_map = product / "MIGRATION-MAP.md"
        assert migration_map.exists(), "MIGRATION-MAP.md must exist"
        content = migration_map.read_text(encoding="utf-8")

        parsed_pairs = []
        for line in content.splitlines():
            m = self._PAIR_RE.search(line)
            if m:
                parsed_pairs.append((m.group("old"), m.group("new")))

        assert parsed_pairs, (
            f"MIGRATION-MAP.md must have at least one line parseable as (old_id -> new_id) "
            f"via regex {self._PAIR_RE.pattern!r}; "
            f"content:\n{content}"
        )

    def test_migration_map_migrated_from_field_present(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        ep_files = [f for f in all_md if _read_frontmatter(f).get("id") == "EP-003"]
        assert ep_files, "EP-003 must exist to check migrated_from"
        fm = _read_frontmatter(ep_files[0])
        migrated_from = fm.get("migrated_from") or fm.get("legacy_id")
        assert migrated_from, (
            f"EP-003 frontmatter must have 'migrated_from' or 'legacy_id' field; "
            f"got frontmatter: {fm!r}"
        )
        assert "EPIC-003" in str(migrated_from), (
            f"migrated_from must record old id 'EPIC-003'; got {migrated_from!r}"
        )


# ---------------------------------------------------------------------------
# Test 11 Frontmatter id wins over filename when they disagree
# ---------------------------------------------------------------------------

class TestFrontmatterIdWinsOverFilename:
    """
    STORY-024-x.md whose frontmatter id is STORY-999 ->
    migrated file's migrated_from / legacy_id == "STORY-999" (frontmatter id wins).
    """

    def _make_id_disagree_project(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(
            product,
            "backlog/stories/STORY-024-x.md",
            frontmatter={
                "id": "STORY-999",
                "title": "Id mismatch story",
                "status": "backlog",
                "type": "story",
            },
        )
        return project, product

    def test_frontmatter_id_used_as_legacy_id(self, tmp_path):
        project, product = self._make_id_disagree_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
        ]
        assert migrated, "At least one ISSUE-* file must be produced from the typed backlog"

        legacy_values = []
        for f in migrated:
            fm = _read_frontmatter(f)
            lv = fm.get("migrated_from") or fm.get("legacy_id")
            if lv:
                legacy_values.append(lv)

        assert any("STORY-999" in str(v) for v in legacy_values), (
            f"migrated file must record legacy id as 'STORY-999' (frontmatter id wins over "
            f"filename STORY-024); found legacy values: {legacy_values!r}"
        )


# ---------------------------------------------------------------------------
# Test 12 Frontmatter-only file (no body) migrates to valid parseable file
# ---------------------------------------------------------------------------

class TestFrontmatterOnlyFileMigrates:
    """
    A file with only frontmatter (no body content after the closing ---) must
    migrate to a valid file that is parseable (frontmatter intact, no crash).
    """

    def _make_frontmatter_only_project(self, tmp_path):
        project, product = _make_project(tmp_path)
        target = product / "backlog" / "stories" / "STORY-077-empty-body.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "---\nid: STORY-077\ntitle: Empty body story\nstatus: backlog\ntype: story\n---\n",
            encoding="utf-8",
        )
        return project, product

    def test_frontmatter_only_file_produces_valid_migrated_file(self, tmp_path):
        project, product = self._make_frontmatter_only_project(tmp_path)
        result = _execute(project)

        all_md = list(product.rglob("*.md"))
        migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and ("STORY-077" in (
                _read_frontmatter(f).get("migrated_from", "")
                + _read_frontmatter(f).get("legacy_id", "")
            ))
        ]
        assert migrated, (
            f"STORY-077 (frontmatter-only) must produce a migrated ISSUE-* file; "
            f"result: {result!r}"
        )
        fm = _read_frontmatter(migrated[0])
        assert fm.get("id"), (
            f"migrated frontmatter-only file must have a valid 'id' field; "
            f"got frontmatter: {fm!r}"
        )
        assert fm.get("title") == "Empty body story", (
            f"migrated frontmatter-only file must keep original title; "
            f"got title={fm.get('title')!r}"
        )

    def test_frontmatter_only_file_is_parseable_yaml(self, tmp_path):
        project, product = self._make_frontmatter_only_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and ("STORY-077" in (
                _read_frontmatter(f).get("migrated_from", "")
                + _read_frontmatter(f).get("legacy_id", "")
            ))
        ]
        assert migrated, "STORY-077 must produce a migrated file"
        migrated_file = migrated[0]
        text = migrated_file.read_text(encoding="utf-8")
        assert text.startswith("---"), (
            f"migrated file must begin with frontmatter marker '---'; "
            f"got: {text[:80]!r}"
        )
        fm = _read_frontmatter(migrated_file)
        assert isinstance(fm, dict) and fm, (
            f"migrated file frontmatter must parse as a non-empty dict; got: {fm!r}"
        )


# ---------------------------------------------------------------------------
# Test 13 Namespaced legacy id recorded without .md extension in migrated_from
# ---------------------------------------------------------------------------

class TestLegacyIdNoExtensionInMigratedFrom:
    """
    migrated_from (or legacy_id) field must store the id string without
    the .md extension. US-DM-002 -> migrated_from == "US-DM-002", not "US-DM-002.md".
    """

    def test_migrated_from_excludes_md_extension(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        us_migrated = [
            f for f in all_md
            if ISSUE_RE.match(_read_frontmatter(f).get("id", ""))
            and (
                "US-DM-002" in str(_read_frontmatter(f).get("migrated_from", ""))
                or "US-DM-002" in str(_read_frontmatter(f).get("legacy_id", ""))
            )
        ]
        assert us_migrated, "US-DM-002 must be migrated to ISSUE-*"
        fm = _read_frontmatter(us_migrated[0])
        legacy_val = fm.get("migrated_from") or fm.get("legacy_id")
        assert legacy_val is not None, (
            f"migrated US-DM-002 file must have migrated_from or legacy_id field; "
            f"got frontmatter: {fm!r}"
        )
        assert str(legacy_val) == "US-DM-002", (
            f"migrated_from must be exactly 'US-DM-002' (no .md extension); "
            f"got {legacy_val!r}"
        )

    def test_epic_migrated_from_excludes_md_extension(self, tmp_path):
        project, product = _make_bespoke_project(tmp_path)
        _execute(project)

        all_md = list(product.rglob("*.md"))
        ep_files = [f for f in all_md if _read_frontmatter(f).get("id") == "EP-003"]
        assert ep_files, "EPIC-003 must be migrated to EP-003"
        fm = _read_frontmatter(ep_files[0])
        legacy_val = fm.get("migrated_from") or fm.get("legacy_id")
        assert legacy_val is not None, (
            f"EP-003 must have migrated_from or legacy_id; got frontmatter: {fm!r}"
        )
        assert ".md" not in str(legacy_val), (
            f"migrated_from must not include .md extension; got {legacy_val!r}"
        )
        assert "EPIC-003" in str(legacy_val), (
            f"migrated_from must record the original id 'EPIC-003'; got {legacy_val!r}"
        )
