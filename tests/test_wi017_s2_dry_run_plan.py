"""
WI-017 S2 — Dry-run plan engine tests.

Covers every scenario in tests/features/wi-017-s2-dry-run-plan.feature.
All tests call run_migration(project_dir, dry_run=True) with real on-disk
file trees; NO mocks.

Implementer contract — new keys added to the dry-run result dict:
  result["moves"]              — list of planned work-item move dicts, each with:
    move["legacy_id"]          — original id (e.g. "STORY-024", "EPIC-003", "US-DM-002")
    move["new_id"]             — assigned v4 id (e.g. "ISSUE-NNN", "EP-003")
    move["source"]             — product-base-relative source path string
    move["dest"]               — product-base-relative destination path string
    move["action"]             — action string (e.g. "migrate", "restructure")
    move["tier"]               — "A" (high confidence) or "B" (low confidence)
    move["epic"]               — (optional) new epic id for stories that have a parent epic

  result["id_map"]             — dict mapping every remapped legacy_id -> {"new_id": str, "source": str}
                                  MS-* and SP-* ids must NOT appear here (unchanged)

  result["reference_edits"]    — list of dicts, each:
    edit["file"]               — product-base-relative path of the file containing the reference
    edit["old_id"]             — the old id string found in the body/frontmatter
    edit["new_id"]             — the replacement id string

  result["conflicts"]          — list of conflict dicts, each:
    conflict["id"]             — the legacy id with a real duplicate (e.g. "STORY-007")
    conflict["files"]          — list of product-base-relative paths involved
    conflict["status"]         — "decision required"

  result["flags"]              — list of flag dicts, each:
    flag["id"]                 — the legacy id with low confidence
    flag["reason"]             — human-readable reason string
    flag["tier"]               — "B"
"""
import re
import sys
import os

# Make scripts/ importable — mirrors conftest.py convention
_SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from pathlib import Path
import pytest
import yaml

# ---------------------------------------------------------------------------
# Deferred import: run_migration does not exist yet in the worktree.
# We import at module load so collection succeeds; individual test calls
# will raise AttributeError/ImportError when they invoke _dry_run(), which
# is the genuine MISSING BEHAVIOR failure — not a setup error.
# ---------------------------------------------------------------------------
try:
    from migrate.migrate_taxonomy import run_migration as _run_migration
    _RUN_MIGRATION_MISSING = False
except ImportError:
    _run_migration = None
    _RUN_MIGRATION_MISSING = True


# ---------------------------------------------------------------------------
# Helpers — shared by all test classes
# ---------------------------------------------------------------------------

def _make_project(tmp_path: Path) -> tuple[Path, Path]:
    """
    Create a minimal project where docs/product is the product base.
    Returns (project_root, product_base).
    Uses artifact-privacy.yaml so _get_product_base() finds docs/product.
    """
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
    """Write a Markdown file at <product_base>/<rel>."""
    target = product_base / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if frontmatter is not None:
        fm_yaml = yaml.safe_dump(frontmatter, default_flow_style=False).strip()
        content = f"---\n{fm_yaml}\n---\n\n{body}"
    else:
        content = f"# No frontmatter\n\n{body}" if not body else f"# File\n\n{body}"
    target.write_text(content, encoding="utf-8")
    return target


def _snapshot(root: Path) -> dict[str, bytes]:
    """Snapshot all file paths and content under root."""
    snap = {}
    for p in root.rglob("*"):
        if p.is_file():
            snap[str(p)] = p.read_bytes()
    return snap


def _dry_run(project: Path, **kwargs) -> dict:
    """
    Call run_migration with dry_run=True and return the result dict.
    Raises pytest.fail with a clear message if run_migration is missing.
    """
    if _RUN_MIGRATION_MISSING or _run_migration is None:
        pytest.fail(
            "run_migration is not exported from migrate.migrate_taxonomy — "
            "this is the missing behavior being tested (S2 implementation does not exist yet)"
        )
    return _run_migration(str(project), dry_run=True, **kwargs)


def _find_move(result: dict, legacy_id: str) -> dict | None:
    """Return the first move dict matching the given legacy_id, or None."""
    for m in result.get("moves", []):
        if m.get("legacy_id") == legacy_id:
            return m
    return None


def _find_id_map_entry(result: dict, legacy_id: str) -> dict | None:
    """Return the id_map entry for legacy_id, or None."""
    return result.get("id_map", {}).get(legacy_id)


ISSUE_RE = re.compile(r"^ISSUE-\d+$")
EP_RE = re.compile(r"^EP-\d+$")


# ===========================================================================
# Scenario: Typed backlog dirs are planned for migration
# ===========================================================================

class TestTypedBacklogDirsMigration:
    """
    Gherkin: typed-dir STORY and DEBT files get a new ISSUE-NNN id,
    legacy_id is preserved, dest is under flat standard backlog (NOT a typed subdir).
    """

    def test_typed_story_gets_issue_id(self, tmp_path):
        # Given "backlog/stories/STORY-024-parallel-run.md" with frontmatter id "STORY-024"
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-024-parallel-run.md",
                  frontmatter={"id": "STORY-024", "title": "Parallel run", "status": "new", "type": "story"})

        result = _dry_run(project)

        # result["moves"] must exist with an entry for STORY-024
        assert "moves" in result, "dry-run result must contain a 'moves' key"
        move = _find_move(result, "STORY-024")
        assert move is not None, "plan must contain a move for STORY-024"
        assert ISSUE_RE.match(move["new_id"]), (
            f"STORY-024 new_id must match ISSUE-\\d+, got {move['new_id']!r}"
        )

    def test_typed_story_preserves_legacy_id(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-024-parallel-run.md",
                  frontmatter={"id": "STORY-024", "title": "Parallel run", "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "STORY-024")
        assert move is not None, "plan must contain a move for STORY-024"
        # legacy_id is the original id before remapping
        assert move["legacy_id"] == "STORY-024", (
            f"move.legacy_id must be 'STORY-024', got {move.get('legacy_id')!r}"
        )

    def test_typed_story_dest_not_in_typed_subdir(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-024-parallel-run.md",
                  frontmatter={"id": "STORY-024", "title": "Parallel run", "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "STORY-024")
        assert move is not None, "plan must contain a move for STORY-024"
        # dest must be under backlog/ (flat standard) not backlog/stories/
        dest = move.get("dest", "")
        assert "backlog/stories/" not in dest, (
            f"STORY-024 dest must not be under a typed subdir, got {dest!r}"
        )
        assert "backlog" in dest or "roadmap" in dest, (
            f"STORY-024 dest must be under standard backlog layout, got {dest!r}"
        )

    def test_typed_debt_gets_issue_id(self, tmp_path):
        # Given "backlog/debt/DEBT-001-creds.md" with frontmatter id "DEBT-001" type "tech-debt"
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/debt/DEBT-001-creds.md",
                  frontmatter={"id": "DEBT-001", "title": "Remove creds", "status": "new", "type": "tech-debt"})

        result = _dry_run(project)

        assert "moves" in result, "dry-run result must contain a 'moves' key"
        move = _find_move(result, "DEBT-001")
        assert move is not None, "plan must contain a move for DEBT-001"
        assert ISSUE_RE.match(move["new_id"]), (
            f"DEBT-001 new_id must match ISSUE-\\d+, got {move['new_id']!r}"
        )

    def test_typed_debt_preserves_legacy_id(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/debt/DEBT-001-creds.md",
                  frontmatter={"id": "DEBT-001", "title": "Remove creds", "status": "new", "type": "tech-debt"})

        result = _dry_run(project)

        move = _find_move(result, "DEBT-001")
        assert move is not None, "plan must contain a move for DEBT-001"
        assert move["legacy_id"] == "DEBT-001", (
            f"move.legacy_id must be 'DEBT-001', got {move.get('legacy_id')!r}"
        )

    def test_typed_debt_dest_not_in_typed_subdir(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/debt/DEBT-001-creds.md",
                  frontmatter={"id": "DEBT-001", "title": "Remove creds", "status": "new", "type": "tech-debt"})

        result = _dry_run(project)

        move = _find_move(result, "DEBT-001")
        assert move is not None, "plan must contain a move for DEBT-001"
        dest = move.get("dest", "")
        assert "backlog/debt/" not in dest, (
            f"DEBT-001 dest must not be under a typed subdir, got {dest!r}"
        )

    def test_moves_key_has_required_fields(self, tmp_path):
        # Each move must expose: legacy_id, new_id, source, dest, action, tier
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-024-parallel-run.md",
                  frontmatter={"id": "STORY-024", "title": "Parallel run", "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "STORY-024")
        assert move is not None, "plan must contain a move for STORY-024"
        for field in ("legacy_id", "new_id", "source", "dest", "action", "tier"):
            assert field in move, (
                f"move dict must contain field '{field}', got keys: {list(move.keys())}"
            )

    def test_moves_tier_is_a_or_b(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-024-parallel-run.md",
                  frontmatter={"id": "STORY-024", "title": "Parallel run", "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "STORY-024")
        assert move is not None, "plan must contain a move for STORY-024"
        assert move.get("tier") in ("A", "B"), (
            f"move.tier must be 'A' or 'B', got {move.get('tier')!r}"
        )


# ===========================================================================
# Scenario: Top-level old-prefix files are planned for migration
# ===========================================================================

class TestTopLevelOldPrefixMigration:
    """
    Gherkin: top-level BL-* files at the product base root get a new ISSUE-NNN id.
    """

    def test_top_level_bl_gets_issue_id(self, tmp_path):
        # Given "BL-005-product-brief.md" with frontmatter id "BL-005" at the product base root
        project, product = _make_project(tmp_path)
        _write_md(product, "BL-005-product-brief.md",
                  frontmatter={"id": "BL-005", "title": "Product brief", "status": "new", "type": "story"})

        result = _dry_run(project)

        assert "moves" in result, "dry-run result must contain a 'moves' key"
        move = _find_move(result, "BL-005")
        assert move is not None, "plan must contain a move for BL-005"
        assert ISSUE_RE.match(move["new_id"]), (
            f"BL-005 new_id must match ISSUE-\\d+, got {move['new_id']!r}"
        )

    def test_top_level_bl_legacy_id_preserved(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "BL-005-product-brief.md",
                  frontmatter={"id": "BL-005", "title": "Product brief", "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "BL-005")
        assert move is not None, "plan must contain a move for BL-005"
        assert move["legacy_id"] == "BL-005", (
            f"move.legacy_id must be 'BL-005', got {move.get('legacy_id')!r}"
        )


# ===========================================================================
# Scenario: Bespoke epics map to EP with number preserved
# ===========================================================================

class TestBespokeEpicMapping:
    """
    Gherkin: EPIC-003/EPIC-003.md (no frontmatter) -> EP-003, legacy_id "EPIC-003".
    """

    def test_bespoke_epic_maps_to_ep_003(self, tmp_path):
        # Given "stories/EPIC-003/EPIC-003.md" with no frontmatter
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")

        result = _dry_run(project)

        assert "moves" in result, "dry-run result must contain a 'moves' key"
        move = _find_move(result, "EPIC-003")
        assert move is not None, "plan must contain a move for EPIC-003"
        assert move["new_id"] == "EP-003", (
            f"EPIC-003 must map to 'EP-003' (number preserved), got {move['new_id']!r}"
        )

    def test_bespoke_epic_legacy_id_recorded(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")

        result = _dry_run(project)

        move = _find_move(result, "EPIC-003")
        assert move is not None, "plan must contain a move for EPIC-003"
        assert move["legacy_id"] == "EPIC-003", (
            f"move.legacy_id must be 'EPIC-003', got {move.get('legacy_id')!r}"
        )


# ===========================================================================
# Scenario: Bespoke user stories map to ISSUE and re-link to their epic's new id
# ===========================================================================

class TestBespokeUserStoryMapping:
    """
    Gherkin: US-DM-002 -> ISSUE-NNN; its planned epic field == the epic's new id (EP-003).
    """

    def _make_epic_tree(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-DM-002.md")
        return project, product

    def test_bespoke_story_maps_to_issue(self, tmp_path):
        project, _ = self._make_epic_tree(tmp_path)

        result = _dry_run(project)

        assert "moves" in result, "dry-run result must contain a 'moves' key"
        move = _find_move(result, "US-DM-002")
        assert move is not None, "plan must contain a move for US-DM-002"
        assert ISSUE_RE.match(move["new_id"]), (
            f"US-DM-002 new_id must match ISSUE-\\d+, got {move['new_id']!r}"
        )

    def test_bespoke_story_epic_set_to_new_ep_003(self, tmp_path):
        # The planned frontmatter for US-DM-002 sets epic to the new epic id "EP-003"
        project, _ = self._make_epic_tree(tmp_path)

        result = _dry_run(project)

        move = _find_move(result, "US-DM-002")
        assert move is not None, "plan must contain a move for US-DM-002"
        # The move must expose the planned epic link as the new id of the parent
        assert "epic" in move, (
            f"move for US-DM-002 must contain an 'epic' field; got keys: {list(move.keys())}"
        )
        assert move["epic"] == "EP-003", (
            f"US-DM-002 planned epic must be 'EP-003', got {move.get('epic')!r}"
        )


# ===========================================================================
# Scenario: Milestones and sprints are left unchanged
# ===========================================================================

class TestMilestonesAndSprintsUnchanged:
    """
    Gherkin: MS-001 and SP-001 must NOT appear in the id remap (id_map).
    """

    def test_ms_not_in_id_map(self, tmp_path):
        # Given "milestones/MS-001-core.md" with frontmatter id "MS-001"
        project, product = _make_project(tmp_path)
        _write_md(product, "milestones/MS-001-core.md",
                  frontmatter={"id": "MS-001", "title": "Core milestone", "status": "active", "type": "milestone"})

        result = _dry_run(project)

        # MS-001 must NOT appear in the id_map (no remapping)
        assert "id_map" in result, "dry-run result must contain an 'id_map' key"
        id_map = result["id_map"]
        assert "MS-001" not in id_map, (
            "MS-001 must NOT appear in id_map — milestones are unchanged"
        )

    def test_sp_not_in_id_map(self, tmp_path):
        # Given "sprints/SP-001-hardening.md" with frontmatter id "SP-001"
        project, product = _make_project(tmp_path)
        _write_md(product, "sprints/SP-001-hardening.md",
                  frontmatter={"id": "SP-001", "title": "Hardening sprint", "status": "active", "type": "sprint"})

        result = _dry_run(project)

        assert "id_map" in result, "dry-run result must contain an 'id_map' key"
        id_map = result["id_map"]
        assert "SP-001" not in id_map, (
            "SP-001 must NOT appear in id_map — sprints are unchanged"
        )


# ===========================================================================
# Scenario: The id remap is bijective and deterministic
# ===========================================================================

class TestIdRemapBijectiveDeterministic:
    """
    Gherkin: two runs produce identical id remaps; all new ids unique;
    no two legacy ids share a new id.
    """

    def _make_mixed_tree(self, tmp_path) -> Path:
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-010-alpha.md",
                  frontmatter={"id": "STORY-010", "title": "Alpha", "status": "new", "type": "story"})
        _write_md(product, "backlog/debt/DEBT-002-legacy-auth.md",
                  frontmatter={"id": "DEBT-002", "title": "Legacy auth", "status": "new", "type": "tech-debt"})
        _write_md(product, "BL-007-feature.md",
                  frontmatter={"id": "BL-007", "title": "Feature", "status": "new", "type": "story"})
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-DM-002.md")
        return project

    def test_two_runs_produce_identical_id_remaps(self, tmp_path):
        project = self._make_mixed_tree(tmp_path)

        r1 = _dry_run(project)
        r2 = _dry_run(project)

        assert "id_map" in r1, "first run must have id_map"
        assert "id_map" in r2, "second run must have id_map"
        assert r1["id_map"] == r2["id_map"], (
            "id_map must be identical across two dry-run calls (deterministic)"
        )

    def test_all_new_ids_unique(self, tmp_path):
        project = self._make_mixed_tree(tmp_path)

        result = _dry_run(project)

        assert "id_map" in result, "dry-run result must have id_map"
        new_ids = [entry["new_id"] for entry in result["id_map"].values()]
        assert len(new_ids) == len(set(new_ids)), (
            f"all new ids must be unique across the plan; duplicates found: "
            f"{[nid for nid in new_ids if new_ids.count(nid) > 1]}"
        )

    def test_no_two_legacy_ids_share_a_new_id(self, tmp_path):
        project = self._make_mixed_tree(tmp_path)

        result = _dry_run(project)

        assert "id_map" in result, "dry-run result must have id_map"
        # Build reverse map: new_id -> list of legacy_ids
        reverse: dict[str, list[str]] = {}
        for legacy_id, entry in result["id_map"].items():
            nid = entry["new_id"]
            reverse.setdefault(nid, []).append(legacy_id)

        collisions = {nid: legs for nid, legs in reverse.items() if len(legs) > 1}
        assert not collisions, (
            f"no two legacy ids may share a new id; found collisions: {collisions}"
        )

    def test_moves_list_deterministic(self, tmp_path):
        project = self._make_mixed_tree(tmp_path)

        r1 = _dry_run(project)
        r2 = _dry_run(project)

        assert "moves" in r1 and "moves" in r2, "both runs must have moves"
        ids1 = sorted(m["legacy_id"] for m in r1["moves"])
        ids2 = sorted(m["legacy_id"] for m in r2["moves"])
        assert ids1 == ids2, (
            "moves set must be identical across two dry-run calls"
        )


# ===========================================================================
# Scenario: New ISSUE numbers continue past existing ISSUE ids
# ===========================================================================

class TestIssueNumbersContinuePastExisting:
    """
    Gherkin: existing ISSUE-050-existing.md means STORY-001's new_id number > 50;
    ISSUE-050 itself is NOT remapped.
    """

    def test_story_new_id_number_greater_than_fifty(self, tmp_path):
        # Given an existing "backlog/ISSUE-050-existing.md" with frontmatter id "ISSUE-050"
        # And a typed-dir "backlog/stories/STORY-001-x.md" with id "STORY-001"
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/ISSUE-050-existing.md",
                  frontmatter={"id": "ISSUE-050", "title": "Existing", "status": "active", "type": "story"})
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "Story one", "status": "new", "type": "story"})

        result = _dry_run(project)

        assert "moves" in result, "dry-run result must have moves"
        move = _find_move(result, "STORY-001")
        assert move is not None, "plan must contain a move for STORY-001"
        new_id_num = int(re.match(r"ISSUE-(\d+)", move["new_id"]).group(1))
        assert new_id_num > 50, (
            f"STORY-001 new id number must be > 50 (past existing ISSUE-050); "
            f"got {move['new_id']!r} (number={new_id_num})"
        )

    def test_existing_issue_050_not_remapped(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/ISSUE-050-existing.md",
                  frontmatter={"id": "ISSUE-050", "title": "Existing", "status": "active", "type": "story"})
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "Story one", "status": "new", "type": "story"})

        result = _dry_run(project)

        assert "id_map" in result, "dry-run result must have id_map"
        assert "ISSUE-050" not in result["id_map"], (
            "ISSUE-050 (already v4) must NOT appear in id_map — it is not remapped"
        )


# ===========================================================================
# Scenario: Reference edits are listed for old-id mentions
# ===========================================================================

class TestReferenceEditsListed:
    """
    Gherkin: EPIC-003.md body mentions "US-DM-002"; plan lists a reference-edit
    entry for that file replacing "US-DM-002" with its new id.
    """

    def test_reference_edit_entry_for_epic_mentioning_story(self, tmp_path):
        # Given "stories/EPIC-003/EPIC-003.md" whose body mentions "US-DM-002"
        # And "stories/EPIC-003/US-DM-002.md" with no frontmatter
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md",
                  body="See US-DM-002 for implementation details.\n")
        _write_md(product, "stories/EPIC-003/US-DM-002.md")

        result = _dry_run(project)

        assert "reference_edits" in result, (
            "dry-run result must contain a 'reference_edits' key"
        )

    def test_reference_edit_names_correct_file(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md",
                  body="See US-DM-002 for implementation details.\n")
        _write_md(product, "stories/EPIC-003/US-DM-002.md")

        result = _dry_run(project)

        edits = result.get("reference_edits", [])
        # There must be an edit entry for EPIC-003.md
        matching_edits = [
            e for e in edits
            if "EPIC-003.md" in e.get("file", "") and e.get("old_id") == "US-DM-002"
        ]
        assert matching_edits, (
            f"reference_edits must include an entry for 'stories/EPIC-003/EPIC-003.md' "
            f"replacing 'US-DM-002'; got reference_edits: {edits!r}"
        )

    def test_reference_edit_specifies_new_id(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md",
                  body="See US-DM-002 for implementation details.\n")
        _write_md(product, "stories/EPIC-003/US-DM-002.md")

        result = _dry_run(project)

        edits = result.get("reference_edits", [])
        matching_edits = [
            e for e in edits
            if "EPIC-003.md" in e.get("file", "") and e.get("old_id") == "US-DM-002"
        ]
        assert matching_edits, "must have edit entry for US-DM-002 mention in EPIC-003.md"
        edit = matching_edits[0]
        # The replacement new_id must be the ISSUE-NNN assigned to US-DM-002
        assert "new_id" in edit, f"reference_edit must contain 'new_id'; got keys: {list(edit.keys())}"
        assert ISSUE_RE.match(edit["new_id"]), (
            f"reference_edit new_id must match ISSUE-\\d+; got {edit.get('new_id')!r}"
        )

    def test_reference_edit_has_required_fields(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md",
                  body="See US-DM-002 for details.\n")
        _write_md(product, "stories/EPIC-003/US-DM-002.md")

        result = _dry_run(project)

        edits = result.get("reference_edits", [])
        assert len(edits) > 0, (
            "reference_edits must be non-empty when a file body mentions a remapped id"
        )
        for edit in edits:
            for field in ("file", "old_id", "new_id"):
                assert field in edit, (
                    f"each reference_edit must have field '{field}'; got keys: {list(edit.keys())}"
                )


# ===========================================================================
# Scenario: A migration map (old -> new) is included in the plan
# ===========================================================================

class TestMigrationMapIncluded:
    """
    Gherkin: id_map has an entry for every remapped item with original_id, new_id, source.
    """

    def test_id_map_key_exists(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-010-alpha.md",
                  frontmatter={"id": "STORY-010", "title": "Alpha", "status": "new", "type": "story"})

        result = _dry_run(project)

        assert "id_map" in result, "dry-run result must contain an 'id_map' key"

    def test_id_map_entry_has_required_fields(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-010-alpha.md",
                  frontmatter={"id": "STORY-010", "title": "Alpha", "status": "new", "type": "story"})

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        assert "STORY-010" in id_map, "id_map must contain entry for STORY-010"
        entry = id_map["STORY-010"]
        # Each entry must have: new_id, source
        for field in ("new_id", "source"):
            assert field in entry, (
                f"id_map entry must have field '{field}'; got keys: {list(entry.keys())}"
            )

    def test_id_map_covers_all_remapped_items(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-010-alpha.md",
                  frontmatter={"id": "STORY-010", "title": "Alpha", "status": "new", "type": "story"})
        _write_md(product, "backlog/debt/DEBT-002-legacy-auth.md",
                  frontmatter={"id": "DEBT-002", "title": "Legacy auth", "status": "new", "type": "tech-debt"})
        _write_md(product, "BL-007-feature.md",
                  frontmatter={"id": "BL-007", "title": "Feature", "status": "new", "type": "story"})
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-DM-002.md")

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        assert len(id_map) >= 5, (
            f"id_map must contain entries for all 5 remapped items "
            f"(STORY-010, DEBT-002, BL-007, EPIC-003, US-DM-002); "
            f"got {len(id_map)} entries: {id_map!r}"
        )
        # Every item in moves that has a new_id different from legacy_id should be in id_map
        for move in result.get("moves", []):
            leg = move["legacy_id"]
            if move["new_id"] != leg:
                assert leg in id_map, (
                    f"id_map must contain entry for every remapped legacy_id; "
                    f"missing: {leg!r}"
                )

    def test_id_map_entry_source_path_correct(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-010-alpha.md",
                  frontmatter={"id": "STORY-010", "title": "Alpha", "status": "new", "type": "story"})

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        assert "STORY-010" in id_map, "id_map must contain STORY-010"
        source = id_map["STORY-010"].get("source", "")
        # Source must reference the original file (product-base-relative or project-relative)
        assert "STORY-010" in source, (
            f"id_map['STORY-010']['source'] must reference the source file; got {source!r}"
        )


# ===========================================================================
# Scenario: Real duplicates are surfaced, backups are not blockers
# ===========================================================================

class TestRealDuplicatesSurfacedBackupsExcluded:
    """
    Gherkin: two real STORY-007 files flagged "decision required";
    backup file .bold-backup-* is absent from the plan.
    """

    def _make_duplicate_tree(self, tmp_path):
        project, product = _make_project(tmp_path)
        # Two real STORY-007 files
        _write_md(product, "backlog/stories/STORY-007-a.md",
                  frontmatter={"id": "STORY-007", "title": "Story seven a", "status": "new", "type": "story"})
        _write_md(product, "backlog/stories/STORY-007-b.md",
                  frontmatter={"id": "STORY-007", "title": "Story seven b", "status": "new", "type": "story"})
        # One bold-backup file (must not count)
        _write_md(product, "backlog/stories/STORY-007-a.bold-backup-1.md",
                  frontmatter={"id": "STORY-007", "title": "Story seven a", "status": "new", "type": "story"})
        return project, product

    def test_conflicts_key_exists(self, tmp_path):
        project, _ = self._make_duplicate_tree(tmp_path)

        result = _dry_run(project)

        assert "conflicts" in result, "dry-run result must contain a 'conflicts' key"

    def test_story_007_flagged_decision_required(self, tmp_path):
        project, _ = self._make_duplicate_tree(tmp_path)

        result = _dry_run(project)

        conflicts = result.get("conflicts", [])
        story_007_conflict = [c for c in conflicts if c.get("id") == "STORY-007"]
        assert story_007_conflict, (
            "STORY-007 must appear in conflicts as a real duplicate"
        )
        assert story_007_conflict[0].get("status") == "decision required", (
            f"STORY-007 conflict status must be 'decision required'; "
            f"got {story_007_conflict[0].get('status')!r}"
        )

    def test_backup_not_in_plan_moves(self, tmp_path):
        project, product = self._make_duplicate_tree(tmp_path)

        result = _dry_run(project)

        # The bold-backup file must not be in the plan's moves
        backup_path = "backlog/stories/STORY-007-a.bold-backup-1.md"
        for move in result.get("moves", []):
            assert backup_path not in move.get("source", ""), (
                f"backup file '{backup_path}' must NOT be part of the plan's moves"
            )

    def test_backup_not_in_conflicts_files_list(self, tmp_path):
        project, product = self._make_duplicate_tree(tmp_path)

        result = _dry_run(project)

        conflicts = result.get("conflicts", [])
        story_007_conflict = [c for c in conflicts if c.get("id") == "STORY-007"]
        if story_007_conflict:
            files = story_007_conflict[0].get("files", [])
            backup_path = "backlog/stories/STORY-007-a.bold-backup-1.md"
            assert not any(backup_path in f for f in files), (
                f"backup file must NOT appear in conflict files list; got {files!r}"
            )

    def test_conflict_entry_has_required_fields(self, tmp_path):
        project, _ = self._make_duplicate_tree(tmp_path)

        result = _dry_run(project)

        conflicts = result.get("conflicts", [])
        story_007_conflict = [c for c in conflicts if c.get("id") == "STORY-007"]
        assert story_007_conflict, "STORY-007 must be in conflicts"
        c = story_007_conflict[0]
        for field in ("id", "files", "status"):
            assert field in c, (
                f"conflict entry must have field '{field}'; got keys: {list(c.keys())}"
            )


# ===========================================================================
# Scenario: Low-confidence Tier B inferences are flagged
# ===========================================================================

class TestLowConfidenceTierBFlagged:
    """
    Gherkin: US-XX-005.md with no frontmatter and no H1 title ->
    flagged as low-confidence (tier B) in flags section.
    """

    def test_flags_key_exists(self, tmp_path):
        project, product = _make_project(tmp_path)
        # A US file with no frontmatter AND no H1 title
        target = product / "stories" / "EPIC-009" / "US-XX-005.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Some body text with no heading.\n", encoding="utf-8")

        result = _dry_run(project)

        assert "flags" in result, "dry-run result must contain a 'flags' key"

    def test_no_frontmatter_no_h1_flagged_low_confidence(self, tmp_path):
        # Given "stories/EPIC-009/US-XX-005.md" with no frontmatter and no H1 title
        project, product = _make_project(tmp_path)
        target = product / "stories" / "EPIC-009" / "US-XX-005.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("No heading here. Just raw text.\n", encoding="utf-8")

        result = _dry_run(project)

        flags = result.get("flags", [])
        us_flag = [f for f in flags if "US-XX-005" in f.get("id", "")]
        assert us_flag, (
            f"US-XX-005 (no frontmatter, no H1) must appear in flags; got flags: {flags!r}"
        )

    def test_low_confidence_entry_has_tier_b(self, tmp_path):
        project, product = _make_project(tmp_path)
        target = product / "stories" / "EPIC-009" / "US-XX-005.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("No heading here. Just raw text.\n", encoding="utf-8")

        result = _dry_run(project)

        flags = result.get("flags", [])
        us_flag = [f for f in flags if "US-XX-005" in f.get("id", "")]
        assert us_flag, "US-XX-005 must appear in flags"
        assert us_flag[0].get("tier") == "B", (
            f"low-confidence flag must have tier='B'; got {us_flag[0].get('tier')!r}"
        )

    def test_low_confidence_move_entry_has_tier_b(self, tmp_path):
        # Also: the corresponding move entry must have tier="B"
        project, product = _make_project(tmp_path)
        target = product / "stories" / "EPIC-009" / "US-XX-005.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("No heading here. Just raw text.\n", encoding="utf-8")

        result = _dry_run(project)

        move = _find_move(result, "US-XX-005")
        assert move is not None, "plan must contain a move for US-XX-005"
        assert move.get("tier") == "B", (
            f"US-XX-005 move.tier must be 'B' (low confidence); got {move.get('tier')!r}"
        )

    def test_flag_entry_has_required_fields(self, tmp_path):
        project, product = _make_project(tmp_path)
        target = product / "stories" / "EPIC-009" / "US-XX-005.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("No heading.\n", encoding="utf-8")

        result = _dry_run(project)

        flags = result.get("flags", [])
        us_flag = [f for f in flags if "US-XX-005" in f.get("id", "")]
        assert us_flag, "US-XX-005 must appear in flags"
        f = us_flag[0]
        for field in ("id", "reason", "tier"):
            assert field in f, (
                f"flag entry must have field '{field}'; got keys: {list(f.keys())}"
            )


# ===========================================================================
# Scenario: The dry-run writes nothing to the project tree
# ===========================================================================

class TestDryRunWritesNothing:
    """
    Gherkin: after the dry-run call, the product base is byte-for-byte identical
    to the snapshot taken before the call; no new files under the project
    except optionally under .sweetclaude/.
    """

    def _make_full_tree(self, tmp_path) -> tuple[Path, Path]:
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-024-parallel-run.md",
                  frontmatter={"id": "STORY-024", "title": "Parallel run", "status": "new", "type": "story"})
        _write_md(product, "backlog/debt/DEBT-001-creds.md",
                  frontmatter={"id": "DEBT-001", "title": "Remove creds", "status": "new", "type": "tech-debt"})
        _write_md(product, "BL-005-product-brief.md",
                  frontmatter={"id": "BL-005", "title": "Product brief", "status": "new", "type": "story"})
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-DM-002.md",
                  body="See US-DM-002 for details.\n")
        _write_md(product, "milestones/MS-001-core.md",
                  frontmatter={"id": "MS-001", "title": "Core", "status": "active", "type": "milestone"})
        return project, product

    def test_product_base_unchanged_after_dry_run(self, tmp_path):
        project, product = self._make_full_tree(tmp_path)

        # Snapshot every file under product base before
        before = _snapshot(product)

        _dry_run(project)

        # Snapshot every file under product base after
        after = _snapshot(product)

        # Check no files added or removed
        assert set(before.keys()) == set(after.keys()), (
            f"dry-run must not add or remove files in product base; "
            f"added: {set(after) - set(before)!r}, "
            f"removed: {set(before) - set(after)!r}"
        )

        # Check no file content changed
        for path in before:
            assert before[path] == after[path], (
                f"dry-run must not modify file {path!r}"
            )

    def test_no_new_files_outside_sweetclaude(self, tmp_path):
        project, product = self._make_full_tree(tmp_path)

        # Snapshot all files in project before
        before = _snapshot(project)

        _dry_run(project)

        after = _snapshot(project)

        sweetclaude_dir = str(project / ".sweetclaude")
        new_files = set(after.keys()) - set(before.keys())
        outside_sc = [f for f in new_files if not f.startswith(sweetclaude_dir)]
        assert not outside_sc, (
            f"dry-run must not create new files outside .sweetclaude/; "
            f"found: {outside_sc!r}"
        )

    def test_product_base_files_not_modified(self, tmp_path):
        project, product = self._make_full_tree(tmp_path)

        before = _snapshot(product)
        _dry_run(project)
        after = _snapshot(product)

        for path in set(before.keys()) & set(after.keys()):
            assert before[path] == after[path], (
                f"dry-run must leave all product-base files byte-for-byte identical; "
                f"changed: {path!r}"
            )


# ===========================================================================
# Additional contract tests — id_map structure
# ===========================================================================

class TestIdMapStructure:
    """
    Additional assertions on the shape and completeness of id_map.
    """

    def test_id_map_new_id_for_epic_preserved_number(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        assert "EPIC-003" in id_map, "id_map must contain EPIC-003"
        assert id_map["EPIC-003"]["new_id"] == "EP-003", (
            f"id_map['EPIC-003']['new_id'] must be 'EP-003'; got {id_map['EPIC-003'].get('new_id')!r}"
        )

    def test_id_map_story_new_id_matches_move_new_id(self, tmp_path):
        # The id_map and the moves list must be consistent
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-024-parallel-run.md",
                  frontmatter={"id": "STORY-024", "title": "Parallel run", "status": "new", "type": "story"})

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        move = _find_move(result, "STORY-024")
        assert move is not None, "must have move for STORY-024"
        assert "STORY-024" in id_map, "id_map must have STORY-024"
        assert id_map["STORY-024"]["new_id"] == move["new_id"], (
            "id_map new_id and move new_id must agree for STORY-024"
        )

    def test_ok_and_dry_run_flags_present(self, tmp_path):
        # run_migration must return ok=True, dry_run=True in the result
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-024-parallel-run.md",
                  frontmatter={"id": "STORY-024", "title": "Parallel run", "status": "new", "type": "story"})

        result = _dry_run(project)

        assert result.get("ok") is True, "run_migration dry-run must return ok=True"
        assert result.get("dry_run") is True, "run_migration must return dry_run=True"


# ===========================================================================
# NEW: Schema — old keys removed, new keys present
# ===========================================================================

class TestSchemaOldKeysRemoved:
    """
    Contract: the dry-run result dict must NOT contain the old keys
    `planned_moves` (int) or top-level `collision_map`.
    It MUST contain moves/id_map/reference_edits/conflicts/flags.
    """

    def _make_simple_tree(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-001-foo.md",
                  frontmatter={"id": "STORY-001", "title": "Foo", "status": "new", "type": "story"})
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "backlog/BL-001-x.md",
                  frontmatter={"id": "BL-001", "title": "X", "status": "new", "type": "story"})
        return project, product

    def test_planned_moves_key_absent(self, tmp_path):
        project, _ = self._make_simple_tree(tmp_path)
        result = _dry_run(project)
        assert "planned_moves" not in result, (
            "dry-run result must NOT contain old key 'planned_moves' (int); "
            f"got result keys: {list(result.keys())}"
        )

    def test_top_level_collision_map_key_absent(self, tmp_path):
        project, _ = self._make_simple_tree(tmp_path)
        result = _dry_run(project)
        assert "collision_map" not in result, (
            "dry-run result must NOT contain old top-level key 'collision_map'; "
            f"got result keys: {list(result.keys())}"
        )

    def test_moves_key_present(self, tmp_path):
        project, _ = self._make_simple_tree(tmp_path)
        result = _dry_run(project)
        assert "moves" in result, (
            "dry-run result must contain 'moves' key; "
            f"got result keys: {list(result.keys())}"
        )

    def test_id_map_key_present(self, tmp_path):
        project, _ = self._make_simple_tree(tmp_path)
        result = _dry_run(project)
        assert "id_map" in result, (
            "dry-run result must contain 'id_map' key; "
            f"got result keys: {list(result.keys())}"
        )

    def test_reference_edits_key_present(self, tmp_path):
        project, _ = self._make_simple_tree(tmp_path)
        result = _dry_run(project)
        assert "reference_edits" in result, (
            "dry-run result must contain 'reference_edits' key; "
            f"got result keys: {list(result.keys())}"
        )

    def test_conflicts_key_present(self, tmp_path):
        project, _ = self._make_simple_tree(tmp_path)
        result = _dry_run(project)
        assert "conflicts" in result, (
            "dry-run result must contain 'conflicts' key; "
            f"got result keys: {list(result.keys())}"
        )

    def test_flags_key_present(self, tmp_path):
        project, _ = self._make_simple_tree(tmp_path)
        result = _dry_run(project)
        assert "flags" in result, (
            "dry-run result must contain 'flags' key; "
            f"got result keys: {list(result.keys())}"
        )


# ===========================================================================
# NEW: ISSUE numbering — global counter rules
# ===========================================================================

class TestIssueNumberingGlobalCounter:
    """
    Contract: ISSUE ids are assigned from a single global counter starting at
    (max existing ISSUE number)+1, using deterministic source order, zero-padded
    to 3 digits. EP keeps its number (EPIC-003 -> EP-003, EPIC-9 -> EP-009).
    """

    def test_no_existing_issue_first_id_is_001(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-005-x.md",
                  frontmatter={"id": "STORY-005", "title": "X", "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "STORY-005")
        assert move is not None, "plan must contain a move for STORY-005"
        assert move["new_id"] == "ISSUE-001", (
            f"with no existing ISSUE-*, first assigned id must be ISSUE-001; "
            f"got {move['new_id']!r}"
        )

    def test_existing_issue_001_and_050_next_is_051(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/ISSUE-001-alpha.md",
                  frontmatter={"id": "ISSUE-001", "title": "Alpha", "status": "active", "type": "story"})
        _write_md(product, "backlog/ISSUE-050-beta.md",
                  frontmatter={"id": "ISSUE-050", "title": "Beta", "status": "active", "type": "story"})
        _write_md(product, "backlog/stories/STORY-002-gamma.md",
                  frontmatter={"id": "STORY-002", "title": "Gamma", "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "STORY-002")
        assert move is not None, "plan must contain a move for STORY-002"
        assert move["new_id"] == "ISSUE-051", (
            f"with existing ISSUE-001 and ISSUE-050, next must be ISSUE-051 (max+1); "
            f"got {move['new_id']!r}"
        )

    def test_story_050_and_bl_050_get_distinct_new_ids(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-050-s.md",
                  frontmatter={"id": "STORY-050", "title": "S", "status": "new", "type": "story"})
        _write_md(product, "backlog/BL-050-b.md",
                  frontmatter={"id": "BL-050", "title": "B", "status": "new", "type": "story"})

        result = _dry_run(project)

        move_story = _find_move(result, "STORY-050")
        move_bl = _find_move(result, "BL-050")
        assert move_story is not None, "plan must contain move for STORY-050"
        assert move_bl is not None, "plan must contain move for BL-050"
        assert move_story["new_id"] != move_bl["new_id"], (
            f"STORY-050 and BL-050 must receive distinct new ISSUE ids; "
            f"got {move_story['new_id']!r} and {move_bl['new_id']!r}"
        )

    def test_story_042_and_us_xy_042_get_distinct_new_ids(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-042-s.md",
                  frontmatter={"id": "STORY-042", "title": "S", "status": "new", "type": "story"})
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-XY-042.md",
                  body="A user story with numeric suffix 042.\n")

        result = _dry_run(project)

        move_story = _find_move(result, "STORY-042")
        move_us = _find_move(result, "US-XY-042")
        assert move_story is not None, "plan must contain move for STORY-042"
        assert move_us is not None, "plan must contain move for US-XY-042"
        assert move_story["new_id"] != move_us["new_id"], (
            f"STORY-042 and US-XY-042 must receive distinct new ids; "
            f"got {move_story['new_id']!r} and {move_us['new_id']!r}"
        )

    def test_two_us_dm_002_in_different_epics_get_distinct_ids(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-DM-002.md",
                  body="Story in EPIC-003.\n")
        _write_md(product, "stories/EPIC-005/EPIC-005.md")
        _write_md(product, "stories/EPIC-005/US-DM-002.md",
                  body="Story in EPIC-005.\n")

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        all_us_dm_002_entries = {
            k: v for k, v in id_map.items()
            if k == "US-DM-002" or k.startswith("US-DM-002")
        }
        moves_for_us_dm_002 = [
            m for m in result.get("moves", [])
            if m.get("legacy_id") == "US-DM-002"
        ]
        assert len(moves_for_us_dm_002) == 2, (
            f"two files both named US-DM-002.md in different epics must each appear "
            f"as a separate move; got {len(moves_for_us_dm_002)} moves"
        )
        new_ids_assigned = [m["new_id"] for m in moves_for_us_dm_002]
        assert len(set(new_ids_assigned)) == 2, (
            f"the two US-DM-002 files must get distinct new ids; got {new_ids_assigned!r}"
        )

    def test_issue_id_zero_padded_to_three_digits(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-005-x.md",
                  frontmatter={"id": "STORY-005", "title": "X", "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "STORY-005")
        assert move is not None
        assert re.match(r"^ISSUE-\d{3,}$", move["new_id"]), (
            f"ISSUE ids must be zero-padded to at least 3 digits; got {move['new_id']!r}"
        )
        assert "ISSUE-51" not in move["new_id"] or move["new_id"] == "ISSUE-051", (
            "ISSUE-51 is not a valid id; must be ISSUE-051"
        )

    def test_ep_id_zero_padded_to_three_digits(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-9/EPIC-9.md")

        result = _dry_run(project)

        move = _find_move(result, "EPIC-9")
        assert move is not None, "plan must contain move for EPIC-9"
        assert move["new_id"] == "EP-009", (
            f"EPIC-9 must map to EP-009 (3-digit zero-padded); got {move['new_id']!r}"
        )

    def test_ep_003_not_ep_3(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")

        result = _dry_run(project)

        move = _find_move(result, "EPIC-003")
        assert move is not None, "plan must contain move for EPIC-003"
        assert move["new_id"] == "EP-003", (
            f"EPIC-003 must map to EP-003, not EP-3; got {move['new_id']!r}"
        )


# ===========================================================================
# NEW: dest/type/status rules
# ===========================================================================

class TestDestTypeStatusRules:
    """
    Contract: dest paths and migrated frontmatter follow defined rules.
    """

    def test_debt_move_frontmatter_type_is_tech_debt(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/debt/DEBT-001-creds.md",
                  frontmatter={"id": "DEBT-001", "title": "Remove creds", "status": "new", "type": "debt"})

        result = _dry_run(project)

        move = _find_move(result, "DEBT-001")
        assert move is not None, "plan must contain move for DEBT-001"
        planned_type = move.get("planned_type") or move.get("type")
        assert planned_type == "tech-debt", (
            f"DEBT-001 migrated frontmatter type must be 'tech-debt' "
            f"(WORKFLOW_TYPE_MAP: debt->tech-debt); got {planned_type!r}"
        )

    def test_story_status_backlog_remapped_not_preserved(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "X", "status": "backlog", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "STORY-001")
        assert move is not None, "plan must contain move for STORY-001"
        planned_status = move.get("planned_status") or move.get("status")
        assert planned_status != "backlog", (
            f"status 'backlog' must be remapped per STATUS_REMAP (backlog->new), "
            f"not preserved verbatim; got {planned_status!r}"
        )
        assert planned_status == "new", (
            f"status 'backlog' must remap to 'new' per STATUS_REMAP; got {planned_status!r}"
        )

    def test_epic_dest_under_roadmap_epics(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")

        result = _dry_run(project)

        move = _find_move(result, "EPIC-003")
        assert move is not None, "plan must contain move for EPIC-003"
        dest = move.get("dest", "")
        assert "roadmap/epics" in dest, (
            f"EPIC-003 dest must be under roadmap/epics/; got {dest!r}"
        )
        assert "EP-003" in dest, (
            f"EPIC-003 dest must contain 'EP-003'; got {dest!r}"
        )

    def test_issue_item_dest_under_flat_backlog(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-010-x.md",
                  frontmatter={"id": "STORY-010", "title": "X", "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "STORY-010")
        assert move is not None, "plan must contain move for STORY-010"
        dest = move.get("dest", "")
        assert "backlog/stories" not in dest, (
            f"ISSUE item dest must NOT be in typed subdir; got {dest!r}"
        )
        assert "backlog/" in dest or dest.startswith("backlog/"), (
            f"ISSUE item dest must be under flat backlog/; got {dest!r}"
        )

    def test_source_round_trips_to_real_file(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-010-x.md",
                  frontmatter={"id": "STORY-010", "title": "X", "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "STORY-010")
        assert move is not None, "plan must contain move for STORY-010"
        source = move.get("source", "")
        resolved = project / source
        assert resolved.exists(), (
            f"project_root/source must resolve to a real existing file; "
            f"project={project}, source={source!r}, resolved={resolved}"
        )

    def test_feature_file_moves_alongside_story(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-DM-002.md",
                  frontmatter={"id": "US-DM-002", "title": "Story", "status": "new", "type": "story"})
        feature_path = product / "stories" / "EPIC-003" / "US-DM-002.feature"
        feature_path.write_text("Feature: US-DM-002 behavior\n  Scenario: something\n",
                                encoding="utf-8")

        result = _dry_run(project)

        story_move = _find_move(result, "US-DM-002")
        assert story_move is not None, "plan must contain move for US-DM-002"
        story_new_id = story_move["new_id"]

        all_moves = result.get("moves", [])
        feature_moves = [
            m for m in all_moves
            if ".feature" in m.get("dest", "") and story_new_id in m.get("dest", "")
        ]
        assert feature_moves, (
            f"the .feature file for US-DM-002 must be planned to move alongside "
            f"the story's new id {story_new_id!r}; moves: {all_moves!r}"
        )


# ===========================================================================
# NEW: Reference rewriting rules
# ===========================================================================

class TestReferenceRewritingRules:
    """
    Contract: reference edits cover all id_map keys, apply to body AND
    frontmatter ref fields, apply to .feature text, and use word-boundary
    matching (partial tokens must not be rewritten).
    """

    def test_frontmatter_epic_field_generates_reference_edit(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-DM-002.md",
                  frontmatter={"id": "US-DM-002", "epic": "EPIC-003",
                               "title": "Story", "status": "new", "type": "story"})

        result = _dry_run(project)

        edits = result.get("reference_edits", [])
        matching = [
            e for e in edits
            if e.get("old_id") == "EPIC-003" and "US-DM-002" in e.get("file", "")
        ]
        assert matching, (
            f"a file whose frontmatter epic=='EPIC-003' must generate a reference_edit "
            f"for EPIC-003->EP-003; got edits: {edits!r}"
        )
        assert matching[0]["new_id"] == "EP-003", (
            f"reference_edit new_id must be 'EP-003'; got {matching[0]['new_id']!r}"
        )

    def test_body_mention_of_debt_id_generates_reference_edit(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/debt/DEBT-001-creds.md",
                  frontmatter={"id": "DEBT-001", "title": "Remove creds",
                               "status": "new", "type": "debt"})
        _write_md(product, "backlog/stories/STORY-005-x.md",
                  frontmatter={"id": "STORY-005", "title": "X", "status": "new", "type": "story"},
                  body="Depends on DEBT-001 being resolved first.\n")

        result = _dry_run(project)

        edits = result.get("reference_edits", [])
        matching = [
            e for e in edits
            if e.get("old_id") == "DEBT-001" and "STORY-005" in e.get("file", "")
        ]
        assert matching, (
            f"a file body mentioning DEBT-001 must generate a reference_edit; "
            f"got edits: {edits!r}"
        )

    def test_feature_scenario_text_generates_reference_edit(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-DM-002.md",
                  frontmatter={"id": "US-DM-002", "title": "Story",
                               "status": "new", "type": "story"})
        feature_path = product / "stories" / "EPIC-003" / "US-DM-002.feature"
        feature_path.write_text(
            "Feature: US-DM-002 scenario\n"
            "  Scenario: Implementation\n"
            "    Given US-DM-002 is planned\n",
            encoding="utf-8"
        )

        result = _dry_run(project)

        story_move = _find_move(result, "US-DM-002")
        assert story_move is not None
        story_new_id = story_move["new_id"]

        edits = result.get("reference_edits", [])
        feature_edits = [
            e for e in edits
            if ".feature" in e.get("file", "") and e.get("old_id") == "US-DM-002"
        ]
        assert feature_edits, (
            f".feature text mentioning US-DM-002 must generate a reference_edit; "
            f"got edits: {edits!r}"
        )
        assert feature_edits[0]["new_id"] == story_new_id, (
            f".feature reference edit new_id must match story's new id {story_new_id!r}; "
            f"got {feature_edits[0]['new_id']!r}"
        )

    def test_partial_token_not_rewritten(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-DM-001.md",
                  frontmatter={"id": "US-DM-001", "title": "Story",
                               "status": "new", "type": "story"})
        _write_md(product, "backlog/stories/STORY-005-x.md",
                  frontmatter={"id": "STORY-005", "title": "X", "status": "new", "type": "story"},
                  body="See US-DM-001-extra for context but not US-DM-001 alone.\n")

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        assert "US-DM-001" in id_map, (
            "US-DM-001 must be in id_map for word-boundary rewrite test to be meaningful"
        )
        edits = result.get("reference_edits", [])
        story_edits = [
            e for e in edits
            if e.get("old_id") == "US-DM-001" and "STORY-005" in e.get("file", "")
        ]
        assert len(story_edits) > 0, (
            "STORY-005 body contains 'US-DM-001' as a word-boundary token; "
            "a reference_edit must be planned for it"
        )
        for edit in story_edits:
            assert edit.get("old_id") == "US-DM-001", (
                "reference_edit old_id must be the exact token US-DM-001, not a partial"
            )

        body_file = product / "backlog" / "stories" / "STORY-005-x.md"
        raw_content = body_file.read_text(encoding="utf-8")
        assert "US-DM-001-extra" in raw_content, (
            "dry-run must not modify files; US-DM-001-extra token must remain intact"
        )
        no_extra_edit = [
            e for e in edits
            if e.get("old_id") == "US-DM-001-extra"
        ]
        assert not no_extra_edit, (
            "US-DM-001-extra must NOT generate a reference_edit; "
            "word-boundary matching must prevent partial rewrites"
        )

    def test_reference_edit_new_id_matches_id_map(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md",
                  body="Story US-DM-002 mentioned here.\n")
        _write_md(product, "stories/EPIC-003/US-DM-002.md")

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        edits = result.get("reference_edits", [])

        assert len(id_map) > 0, (
            "id_map must be non-empty when remappable items exist"
        )
        assert len(edits) > 0, (
            "reference_edits must be non-empty when a body mentions a remapped id"
        )
        for edit in edits:
            old_id = edit.get("old_id")
            if old_id in id_map:
                assert edit["new_id"] == id_map[old_id]["new_id"], (
                    f"reference_edit new_id must equal id_map[{old_id!r}].new_id; "
                    f"got edit new_id={edit['new_id']!r}, "
                    f"id_map new_id={id_map[old_id]['new_id']!r}"
                )

    def test_bug_id_in_id_map_and_reference_edits(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/bugs/BUG-003-crash.md",
                  frontmatter={"id": "BUG-003", "title": "Crash", "status": "new", "type": "bug"})
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "X", "status": "new", "type": "story"},
                  body="Blocked by BUG-003.\n")

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        assert "BUG-003" in id_map, (
            "BUG-003 must appear in id_map; reference rewrite is driven by ALL id_map keys"
        )
        edits = result.get("reference_edits", [])
        bug_edits = [e for e in edits if e.get("old_id") == "BUG-003"]
        assert bug_edits, (
            f"body mentioning BUG-003 must generate a reference_edit; "
            f"BUG-003 must be in id_map keys for reference rewriting; got edits: {edits!r}"
        )

    def test_chore_id_in_id_map(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/chores/CHORE-002-lint.md",
                  frontmatter={"id": "CHORE-002", "title": "Lint", "status": "new", "type": "chore"})

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        assert "CHORE-002" in id_map, (
            "CHORE-002 must appear in id_map; reference rewrite covers CHORE prefix"
        )


# ===========================================================================
# NEW: Scan exclusions — derived files and index files never in moves
# ===========================================================================

class TestScanExclusions:
    """
    Contract: backup files (any prefix) are never in moves/reference_edits;
    EPIC-NNN-index.md is never planned as a move; existing v4 ids are not
    placed in id_map.
    """

    def test_flat_backlog_backup_not_in_moves(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/BL-007-a.bold-backup-1.md",
                  frontmatter={"id": "BL-007", "title": "B", "status": "new", "type": "story"})
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "X", "status": "new", "type": "story"})

        result = _dry_run(project)

        story_move = _find_move(result, "STORY-001")
        assert story_move is not None, (
            "STORY-001 must appear in moves for the backup exclusion test to be meaningful"
        )
        for move in result.get("moves", []):
            assert "BL-007-a.bold-backup-1.md" not in move.get("source", ""), (
                f"backup file BL-007-a.bold-backup-1.md must NOT appear in moves; "
                f"got source: {move.get('source')!r}"
            )

    def test_flat_backlog_backup_not_in_reference_edits(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/BL-007-a.bold-backup-1.md",
                  frontmatter={"id": "BL-007", "title": "B", "status": "new", "type": "story"})
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "X", "status": "new", "type": "story"},
                  body="Related to BL-007 item.\n")

        result = _dry_run(project)

        story_move = _find_move(result, "STORY-001")
        assert story_move is not None, (
            "STORY-001 must appear in moves for the backup exclusion test to be meaningful"
        )
        for edit in result.get("reference_edits", []):
            assert "BL-007-a.bold-backup-1.md" not in edit.get("file", ""), (
                f"backup file must NOT appear in reference_edits; got: {edit!r}"
            )

    def test_epic_index_file_not_in_moves(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        index_path = product / "stories" / "EPIC-003" / "EPIC-003-index.md"
        index_path.write_text("# EPIC-003 index\n\nContents.\n", encoding="utf-8")

        result = _dry_run(project)

        epic_move = _find_move(result, "EPIC-003")
        assert epic_move is not None, (
            "EPIC-003 must appear in moves for the index-exclusion test to be meaningful"
        )
        for move in result.get("moves", []):
            assert "EPIC-003-index.md" not in move.get("source", ""), (
                f"EPIC-003-index.md must NOT appear in moves; "
                f"got source: {move.get('source')!r}"
            )

    def test_existing_v4_ep_003_relocated_from_backlog(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/EP-003-existing.md",
                  frontmatter={"id": "EP-003", "title": "Existing epic", "status": "active", "type": "epic"})
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "X", "status": "new", "type": "story"})

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        assert "STORY-001" in id_map, (
            "STORY-001 must be in id_map (confirms scan ran, not just empty result)"
        )
        assert "EP-003" in id_map, (
            "EP-003 in backlog/ is a legacy placement — must be relocated to roadmap/epics/"
        )
        moves = result.get("moves", [])
        ep_moves = [m for m in moves if m.get("new_id") == "EP-003"]
        assert ep_moves, "EP-003 must have a move entry"
        assert "roadmap/epics" in ep_moves[0]["dest"], (
            f"EP-003 must be relocated to roadmap/epics/, got {ep_moves[0]['dest']}"
        )

    def test_issue_050_not_in_id_map_when_present(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/ISSUE-050-x.md",
                  frontmatter={"id": "ISSUE-050", "title": "X", "status": "active", "type": "story"})
        _write_md(product, "backlog/stories/STORY-001-y.md",
                  frontmatter={"id": "STORY-001", "title": "Y", "status": "new", "type": "story"})

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        assert "STORY-001" in id_map, (
            "STORY-001 must be in id_map for this exclusion test to be meaningful"
        )
        assert "ISSUE-050" not in id_map, (
            "An already-v4 ISSUE-050 file must NOT appear in id_map"
        )

    def test_milestones_not_in_id_map(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "milestones/MS-001-core.md",
                  frontmatter={"id": "MS-001", "title": "Core", "status": "active", "type": "milestone"})
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "X", "status": "new", "type": "story"})

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        assert "STORY-001" in id_map, (
            "STORY-001 must be in id_map for this exclusion test to be meaningful"
        )
        assert "MS-001" not in id_map, (
            "milestones/MS-* must NOT appear in id_map"
        )

    def test_sprints_not_in_id_map(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "sprints/SP-001-sprint.md",
                  frontmatter={"id": "SP-001", "title": "Sprint", "status": "active", "type": "sprint"})
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "X", "status": "new", "type": "story"})

        result = _dry_run(project)

        id_map = result.get("id_map", {})
        assert "STORY-001" in id_map, (
            "STORY-001 must be in id_map for this exclusion test to be meaningful"
        )
        assert "SP-001" not in id_map, (
            "sprints/SP-* must NOT appear in id_map"
        )


# ===========================================================================
# NEW: Shape/prefix coverage — bugs, chores, stories, spikes
# ===========================================================================

class TestShapePrefixCoverage:
    """
    Contract: BUG-*, CHORE-*, typed-backlog STORY-*, spike-reports, US-* inside
    epic dirs are all discovered and planned.
    """

    def test_bug_003_planned_with_issue_id(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/bugs/BUG-003-crash.md",
                  frontmatter={"id": "BUG-003", "title": "Crash", "status": "new", "type": "bug"})

        result = _dry_run(project)

        move = _find_move(result, "BUG-003")
        assert move is not None, "plan must contain a move for BUG-003"
        assert ISSUE_RE.match(move["new_id"]), (
            f"BUG-003 new_id must match ISSUE-\\d+; got {move['new_id']!r}"
        )

    def test_chore_002_planned_with_issue_id(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/chores/CHORE-002-lint.md",
                  frontmatter={"id": "CHORE-002", "title": "Lint", "status": "new", "type": "chore"})

        result = _dry_run(project)

        move = _find_move(result, "CHORE-002")
        assert move is not None, "plan must contain a move for CHORE-002"
        assert ISSUE_RE.match(move["new_id"]), (
            f"CHORE-002 new_id must match ISSUE-\\d+; got {move['new_id']!r}"
        )

    def test_story_in_bl_dir_planned_with_epic_mapping(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-XX-001.md",
                  frontmatter={"id": "US-XX-001", "title": "Story",
                               "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "US-XX-001")
        assert move is not None, "plan must contain move for US-XX-001"
        assert ISSUE_RE.match(move["new_id"]), (
            f"US-XX-001 new_id must be ISSUE-*; got {move['new_id']!r}"
        )
        assert move.get("epic") == "EP-003", (
            f"US-XX-001 must link to parent epic EP-003; got {move.get('epic')!r}"
        )

    def test_spike_report_planned_in_moves(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/spike-reports/spike-BL-002-research.md",
                  frontmatter={"id": "spike-BL-002", "title": "Research",
                               "status": "new", "type": "spike"})

        result = _dry_run(project)

        all_sources = [m.get("source", "") for m in result.get("moves", [])]
        spike_in_moves = any("spike-BL-002" in s for s in all_sources)
        assert spike_in_moves, (
            f"spike-BL-002-research.md must appear in moves; got sources: {all_sources!r}"
        )


# ===========================================================================
# NEW: Tier and flags — confidence classification
# ===========================================================================

class TestTierAndFlagsClassification:
    """
    Contract: frontmatter present -> tier A, not flagged; no frontmatter but H1
    present -> tier B, NOT low-confidence flagged; no frontmatter no H1 -> tier B
    AND flagged.
    """

    def test_us_with_full_frontmatter_is_tier_a_not_flagged(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-DM-001.md",
                  frontmatter={"id": "US-DM-001", "title": "Story",
                               "status": "new", "type": "story"})

        result = _dry_run(project)

        move = _find_move(result, "US-DM-001")
        assert move is not None, "plan must contain move for US-DM-001"
        assert move.get("tier") == "A", (
            f"US with full frontmatter must be tier A; got {move.get('tier')!r}"
        )
        flags = result.get("flags", [])
        flagged_ids = [f.get("id") for f in flags]
        assert "US-DM-001" not in flagged_ids, (
            "US-DM-001 with full frontmatter must NOT appear in flags"
        )

    def test_no_frontmatter_with_h1_is_tier_b_not_low_confidence_flagged(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-009/EPIC-009.md")
        target = product / "stories" / "EPIC-009" / "US-YY-007.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# US-YY-007: The story title\n\nBody text.\n", encoding="utf-8")

        result = _dry_run(project)

        move = _find_move(result, "US-YY-007")
        assert move is not None, "plan must contain move for US-YY-007"
        assert move.get("tier") == "B", (
            f"US with no frontmatter but with H1 must be tier B; got {move.get('tier')!r}"
        )
        flags = result.get("flags", [])
        flagged_ids = [f.get("id") for f in flags]
        assert "US-YY-007" not in flagged_ids, (
            "US with no frontmatter BUT with H1 must NOT be low-confidence flagged "
            "(tier B but not flagged is the contract)"
        )

    def test_no_frontmatter_no_h1_is_tier_b_and_flagged(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-009/EPIC-009.md")
        target = product / "stories" / "EPIC-009" / "US-ZZ-008.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("No frontmatter and no heading at all.\n", encoding="utf-8")

        result = _dry_run(project)

        move = _find_move(result, "US-ZZ-008")
        assert move is not None, "plan must contain move for US-ZZ-008"
        assert move.get("tier") == "B", (
            f"US with no frontmatter and no H1 must be tier B; got {move.get('tier')!r}"
        )
        flags = result.get("flags", [])
        flagged_ids = [f.get("id") for f in flags]
        assert "US-ZZ-008" in flagged_ids, (
            "US with no frontmatter AND no H1 must appear in flags (low-confidence)"
        )

    def test_clean_project_conflicts_and_flags_empty(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "X", "status": "new", "type": "story"})
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "stories/EPIC-003/US-DM-001.md",
                  frontmatter={"id": "US-DM-001", "title": "Story",
                               "status": "new", "type": "story"})

        result = _dry_run(project)

        assert result.get("conflicts") == [], (
            f"clean project (no duplicates) must have conflicts==[]; "
            f"got {result.get('conflicts')!r}"
        )
        assert result.get("flags") == [], (
            f"clean project (all tier A) must have flags==[]; "
            f"got {result.get('flags')!r}"
        )

    def test_story_007_conflict_files_lists_all_three_real_files(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-007-a.md",
                  frontmatter={"id": "STORY-007", "title": "A", "status": "new", "type": "story"})
        _write_md(product, "backlog/stories/STORY-007-b.md",
                  frontmatter={"id": "STORY-007", "title": "B", "status": "new", "type": "story"})
        _write_md(product, "backlog/stories/STORY-007-c.md",
                  frontmatter={"id": "STORY-007", "title": "C", "status": "new", "type": "story"})
        _write_md(product, "backlog/stories/STORY-007-a.bold-backup-1.md",
                  frontmatter={"id": "STORY-007", "title": "A backup",
                               "status": "new", "type": "story"})

        result = _dry_run(project)

        conflicts = result.get("conflicts", [])
        s7 = [c for c in conflicts if c.get("id") == "STORY-007"]
        assert s7, "STORY-007 must appear in conflicts"
        files = s7[0].get("files", [])
        assert len(files) == 3, (
            f"STORY-007 conflict.files must list all 3 real (non-backup) files; "
            f"got {len(files)}: {files!r}"
        )


# ===========================================================================
# NEW: Collisions with existing v4 ids
# ===========================================================================

class TestCollisionsWithExistingV4Ids:
    """
    Contract: a bespoke EPIC-003 when backlog/EP-003 already exists ->
    conflicts entry for EP-003, no overwrite.
    """

    def test_bespoke_epic_003_conflicts_with_existing_ep_003(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "backlog/EP-003-existing.md",
                  frontmatter={"id": "EP-003", "title": "Existing v4 epic",
                               "status": "active", "type": "epic"})

        result = _dry_run(project)

        conflicts = result.get("conflicts", [])
        ep003_conflict = [c for c in conflicts if c.get("id") == "EP-003"]
        assert ep003_conflict, (
            f"EPIC-003 -> EP-003 when backlog/EP-003 already exists must create a "
            f"conflicts entry for EP-003; got conflicts: {conflicts!r}"
        )

    def test_collision_does_not_produce_a_write(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "stories/EPIC-003/EPIC-003.md")
        _write_md(product, "backlog/EP-003-existing.md",
                  frontmatter={"id": "EP-003", "title": "Existing v4 epic",
                               "status": "active", "type": "epic"})

        before = _snapshot(product)
        _dry_run(project)
        after = _snapshot(product)

        assert set(before.keys()) == set(after.keys()), (
            "collision must not produce any written files in the product base"
        )
        for path in before:
            assert before[path] == after[path], (
                f"collision must not overwrite {path!r}"
            )


# ===========================================================================
# NEW: Robustness — artifact-privacy.yaml base_path escape
# ===========================================================================

class TestRobustness:
    """
    Contract: artifact-privacy.yaml base_path pointing outside the project
    (e.g. '/etc/passwd') causes run_migration to return ok=False with an
    error, with no unhandled exception.
    """

    def test_escape_base_path_returns_ok_false_no_exception(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        sc = project / ".sweetclaude"
        sc.mkdir()
        evil_privacy = {"product": {"base_path": "/etc/passwd"}}
        (sc / "artifact-privacy.yaml").write_text(yaml.safe_dump(evil_privacy))

        if _RUN_MIGRATION_MISSING or _run_migration is None:
            pytest.fail(
                "run_migration is not exported from migrate.migrate_taxonomy — "
                "missing behavior"
            )

        try:
            result = _run_migration(str(project), dry_run=True)
        except Exception as exc:
            pytest.fail(
                f"run_migration must not raise an unhandled exception for a path-escape "
                f"base_path; got {type(exc).__name__}: {exc}"
            )

        assert result.get("ok") is False, (
            f"result['ok'] must be False when base_path escapes project root; "
            f"got result: {result!r}"
        )
        assert "error" in result or "errors" in result, (
            f"result must contain 'error' or 'errors' key; got: {list(result.keys())}"
        )


# ===========================================================================
# NEW: Plan output — only .sweetclaude/state/migration-plan.yaml written
# ===========================================================================

class TestPlanOutputLocation:
    """
    Contract: after a dry-run, the only new file under .sweetclaude/ must
    match .sweetclaude/state/migration-plan.(yaml|json). No other new files
    outside .sweetclaude/ may be created.
    """

    def test_dry_run_new_file_under_sweetclaude_is_migration_plan(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "X", "status": "new", "type": "story"})

        before = _snapshot(project)
        _dry_run(project)
        after = _snapshot(project)

        new_files = set(after.keys()) - set(before.keys())
        sweetclaude_dir = str(project / ".sweetclaude")

        for nf in new_files:
            assert nf.startswith(sweetclaude_dir), (
                f"new file {nf!r} is outside .sweetclaude/ — forbidden in dry-run"
            )

        assert new_files, (
            "dry-run must write migration-plan.yaml under .sweetclaude/state/; "
            "no new files were created at all"
        )
        for nf in new_files:
            assert re.search(r"migration-plan\.(yaml|json)$", nf), (
                f"any new file under .sweetclaude/ must be migration-plan.(yaml|json); "
                f"got {nf!r}"
            )

    def test_migration_plan_yaml_written_under_state(self, tmp_path):
        project, product = _make_project(tmp_path)
        _write_md(product, "backlog/stories/STORY-001-x.md",
                  frontmatter={"id": "STORY-001", "title": "X", "status": "new", "type": "story"})

        _dry_run(project)

        plan_path = project / ".sweetclaude" / "state" / "migration-plan.yaml"
        plan_path_json = project / ".sweetclaude" / "state" / "migration-plan.json"
        assert plan_path.exists() or plan_path_json.exists(), (
            "after a dry-run, .sweetclaude/state/migration-plan.yaml (or .json) "
            "must exist; neither was found"
        )
