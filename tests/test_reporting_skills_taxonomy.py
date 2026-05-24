"""
Tests for reporting skills taxonomy update (ISSUE-94).

Translates: tests/features/reporting-skills-taxonomy.feature

The three reporting skills (big-picture, status, recap) must work with the
post-migration taxonomy: .sweetclaude/product/ paths, MS/EP/ISSUE prefixes,
cache.py queries, and milestone-based hierarchy.
"""
import os
import sys
import re

import pytest
import yaml

_SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from cache import (
    rebuild,
    query_summary,
)

_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)


# ---------------------------------------------------------------------------
# Helpers (identical to test_cache_taxonomy.py pattern)
# ---------------------------------------------------------------------------

def write_frontmatter_file(path, frontmatter_dict, body=""):
    """Create a markdown file with YAML frontmatter at the given path."""
    path = os.fspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fm_text = yaml.dump(frontmatter_dict, default_flow_style=False)
    content = f"---\n{fm_text}---\n{body}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def setup_project(tmp_path):
    """Create the minimal directory structure and artifact-privacy.yaml."""
    sc_dir = tmp_path / ".sweetclaude"
    sc_dir.mkdir(parents=True, exist_ok=True)
    ap = sc_dir / "artifact-privacy.yaml"
    ap.write_text(yaml.dump({"product": {"base_path": ".sweetclaude/product"}}))
    return str(tmp_path)


def read_skill(skill_name):
    """Read the content of a skill's SKILL.md file."""
    path = os.path.join(_PROJECT_ROOT, "skills", skill_name, "SKILL.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _has_product_guard(content):
    """
    Return True only if the file contains an explicit conditional guard that
    checks for the .sweetclaude/product/ directory before proceeding.

    A guard is a conditional check (if/test/-d/exists) specifically on
    .sweetclaude/product/ used to detect whether migration has run.
    Incidental mentions of .sweetclaude/product in path reads do NOT count.
    """
    guard_patterns = [
        # Bash: [ -d .sweetclaude/product/ ] or [[ -d .sweetclaude/product/ ]]
        r'\[\[?\s*-d\s+["\']?\.sweetclaude/product/',
        # Bash: test -d .sweetclaude/product/
        r'\btest\s+-d\s+["\']?\.sweetclaude/product/',
        # Bash: ls .sweetclaude/product/roadmap ... | wc
        r'ls\s+\.sweetclaude/product/.*\|\s*wc',
        # Python: os.path.exists('.sweetclaude/product/') or os.path.isdir(...)
        # in a conditional context (i.e., preceded by 'if')
        r'\bif\b.*os\.path\.(exists|isdir).*\.sweetclaude/product/',
        r'os\.path\.(exists|isdir)\s*\(\s*["\']\.sweetclaude/product/',
    ]
    for pattern in guard_patterns:
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            return True
    return False


def _extract_step_4a(content):
    """
    Extract the roadmap rendering section from the status SKILL.md.
    Looks for '### Step V-roadmap' (consolidated status skill) or
    '## Step 4a' (legacy big-picture skill).
    Returns the section text or empty string if not found.
    """
    m = re.search(r'### Step V-roadmap(.*?)(?=###\s+Step\s+V-)', content, re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(r'## Step 4a(.*?)(?=## Step 4b)', content, re.DOTALL)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Cache: query_summary milestone status breakdown
# ---------------------------------------------------------------------------

class TestQuerySummaryMilestonesByStatus:
    """Scenario: query_summary returns milestones.by_status breakdown"""

    def test_by_status_key_present_in_milestones(self, tmp_path):
        project_dir = setup_project(tmp_path)
        base = str(tmp_path / ".sweetclaude" / "product")

        write_frontmatter_file(
            os.path.join(base, "roadmap", "milestones", "MS-001-launch.md"),
            {"id": "MS-001", "type": "milestone", "title": "Launch", "status": "active"},
        )
        write_frontmatter_file(
            os.path.join(base, "roadmap", "milestones", "MS-002-done.md"),
            {"id": "MS-002", "type": "milestone", "title": "Done Milestone", "status": "done"},
        )

        rebuild(project_dir)
        summary = query_summary(project_dir)

        assert "milestones" in summary, "summary must have 'milestones' key"
        milestones = summary["milestones"]
        assert "by_status" in milestones, (
            "summary['milestones'] must have 'by_status' key — got: "
            f"{list(milestones.keys())}"
        )

    def test_by_status_counts_active_and_done(self, tmp_path):
        project_dir = setup_project(tmp_path)
        base = str(tmp_path / ".sweetclaude" / "product")

        write_frontmatter_file(
            os.path.join(base, "roadmap", "milestones", "MS-001-launch.md"),
            {"id": "MS-001", "type": "milestone", "title": "Launch", "status": "active"},
        )
        write_frontmatter_file(
            os.path.join(base, "roadmap", "milestones", "MS-002-done.md"),
            {"id": "MS-002", "type": "milestone", "title": "Done Milestone", "status": "done"},
        )

        rebuild(project_dir)
        summary = query_summary(project_dir)

        by_status = summary["milestones"]["by_status"]
        assert by_status == {"active": 1, "done": 1}, (
            f"Expected milestones.by_status == {{'active': 1, 'done': 1}}, got {by_status}"
        )


class TestQuerySummaryMilestonesByStatusEmpty:
    """Scenario: query_summary milestones.by_status is empty when no milestones exist"""

    def test_by_status_is_empty_dict_and_total_is_zero_when_no_milestones(self, tmp_path):
        """
        Covers both Gherkin steps:
          Then the summary contains milestones.by_status as an empty dict
          And milestones.total equals 0
        """
        project_dir = setup_project(tmp_path)
        base = str(tmp_path / ".sweetclaude" / "product")

        write_frontmatter_file(
            os.path.join(base, "backlog", "ISSUE-001-foo.md"),
            {"id": "ISSUE-001", "type": "enhancement", "title": "Foo", "status": "new"},
        )

        rebuild(project_dir)
        summary = query_summary(project_dir)

        assert "milestones" in summary, "summary must have 'milestones' key"
        milestones = summary["milestones"]
        assert "by_status" in milestones, (
            "summary['milestones'] must have 'by_status' key even when no milestones exist"
        )
        assert milestones["by_status"] == {}, (
            f"Expected milestones.by_status == {{}}, got {milestones['by_status']}"
        )
        assert milestones["total"] == 0, (
            f"Expected milestones.total == 0, got {milestones.get('total')}"
        )


# ---------------------------------------------------------------------------
# big-picture: no retired prefixes or old paths
# ---------------------------------------------------------------------------

class TestBigPictureNoDocsProductPath:
    """Scenario: big-picture SKILL.md contains no references to docs/product/"""

    def test_no_docs_product_path(self):
        content = read_skill("big-picture")
        assert "docs/product/" not in content, (
            "big-picture SKILL.md must not reference 'docs/product/' — "
            "all paths must use '.sweetclaude/product/' post-migration"
        )


class TestBigPictureNoRelPrefix:
    """Scenario: big-picture SKILL.md contains no REL- prefix in rendering templates"""

    def test_no_rel_prefix(self):
        content = read_skill("big-picture")
        assert "REL-" not in content, (
            "big-picture SKILL.md must not use 'REL-' prefix — "
            "releases are now milestones with 'MS-' prefix"
        )


class TestBigPictureNoStoryPrefix:
    """Scenario: big-picture SKILL.md contains no STORY- prefix in rendering templates"""

    def test_no_story_prefix(self):
        content = read_skill("big-picture")
        assert "STORY-" not in content, (
            "big-picture SKILL.md must not use 'STORY-' prefix — "
            "work items are now issues with 'ISSUE-' prefix"
        )


class TestBigPictureHasMsPrefix:
    """Scenario: status SKILL.md renders MS- prefix for top-level roadmap nodes"""

    def test_has_ms_prefix_in_rendering_template(self):
        content = read_skill("status")
        # The rendering template must show MS- as an explicit milestone ID placeholder
        # in a code/display block, e.g. "MS-{NNN}", "MS-NNN", or backtick-MS-NNN.
        # A bare MS-*.md file glob in a legacy path does not count.
        has_template_ms = bool(
            re.search(r'MS-\{', content)
            or re.search(r'MS-NNN', content)
            or re.search(r'`MS-\d', content)
            or re.search(r'\bMS-\d{3}\b', content)
        )
        assert has_template_ms, (
            "big-picture SKILL.md must render MS- as a milestone ID prefix in the "
            "roadmap display template (e.g. MS-{NNN} or MS-NNN), not just reference "
            "MS-*.md file globs in legacy sections"
        )


class TestBigPictureHasIssuePrefix:
    """Scenario: status SKILL.md renders ISSUE- prefix for work items"""

    def test_has_issue_prefix(self):
        content = read_skill("status")
        assert "ISSUE-" in content, (
            "big-picture SKILL.md must reference 'ISSUE-' prefix for work item rendering"
        )


class TestBigPictureUsesMilestonesCompactQuery:
    """Scenario: status SKILL.md uses milestones-compact query"""

    def test_uses_milestones_compact(self):
        content = read_skill("status")
        assert "milestones-compact" in content, (
            "big-picture SKILL.md must use the 'milestones-compact' query "
            "instead of 'releases-compact' for the roadmap tree"
        )


class TestBigPictureSummaryLineUsesMilestones:
    """Scenario: status SKILL.md summary line says milestones not releases"""

    def test_step4a_summary_line_references_milestones(self):
        content = read_skill("status")
        # The Step 4a (cache-backed roadmap) section must have a summary line that
        # references milestones. The legacy Step 4b milestone pipeline does NOT count.
        step4a = _extract_step_4a(content)
        assert step4a, (
            "big-picture SKILL.md must have a '## Step 4a' section for cache-backed rendering"
        )
        has_milestone_summary = bool(
            re.search(r'\{total milestones\}', step4a)
            or re.search(r'milestones\s+·', step4a)
            or re.search(r'·\s+milestones', step4a)
            or re.search(r'milestones\b.*active', step4a, re.IGNORECASE)
        )
        assert has_milestone_summary, (
            "big-picture SKILL.md Step 4a summary line must reference milestones "
            "(e.g. '{N} milestones · {active} active · ...') — "
            "the current Step 4a uses 'total releases' which must be replaced"
        )

    def test_no_total_releases_phrase(self):
        content = read_skill("status")
        assert "total releases" not in content, (
            "big-picture SKILL.md must not use the phrase 'total releases' — "
            "the summary line must reference milestones, not releases"
        )


class TestBigPictureRoadmapDetectionChecksSweet:
    """Scenario: status roadmap view checks .sweetclaude path"""

    def test_roadmap_detection_uses_sweetclaude_path(self):
        content = read_skill("status")
        has_sweetclaude_product = (
            ".sweetclaude/product/roadmap/epics/" in content
            or ".sweetclaude/product/roadmap/" in content
        )
        assert has_sweetclaude_product, (
            "status SKILL.md roadmap view must reference "
            "'.sweetclaude/product/roadmap/' not 'docs/product/roadmap/'"
        )


# ---------------------------------------------------------------------------
# status: no retired prefixes or old paths, uses cache queries
# ---------------------------------------------------------------------------

class TestStatusNoRmGlob:
    """Scenario: status SKILL.md contains no RM-* glob pattern"""

    def test_no_rm_glob(self):
        content = read_skill("status")
        assert "RM-*.md" not in content, (
            "status SKILL.md must not reference 'RM-*.md' glob — "
            "RM- (roadmap) prefix is retired"
        )


class TestStatusNoIGlob:
    """Scenario: status SKILL.md contains no I-* glob pattern"""

    def test_no_i_glob(self):
        content = read_skill("status")
        assert "I-*.md" not in content, (
            "status SKILL.md must not reference 'I-*.md' glob — "
            "I- (issue) prefix is retired in favour of ISSUE-"
        )


class TestStatusNoBlGlob:
    """Scenario: status SKILL.md contains no BL-* glob pattern"""

    def test_no_bl_glob(self):
        content = read_skill("status")
        assert "BL-*.md" not in content, (
            "status SKILL.md must not reference 'BL-*.md' glob — "
            "BL- (backlog) prefix is retired"
        )


class TestStatusNoStoryPrefix:
    """Scenario: status SKILL.md contains no STORY- prefix"""

    def test_no_story_prefix(self):
        content = read_skill("status")
        # The STORY subdir scan in _V4_SUBDIRS uses 'STORY' without the dash.
        # The spec requires removal of STORY- prefix work (the whole typed-subdir approach).
        # We check for the STORY subdir entry used in status to scan old v4 typed subdirs.
        assert "'STORY'" not in content, (
            "status SKILL.md must not reference the 'STORY' typed subdirectory — "
            "the v4 typed-subdir backlog scan must be replaced with cache.py queries"
        )


class TestStatusReferencesCachePy:
    """Scenario: status SKILL.md references cache.py for data"""

    def test_references_cache_py(self):
        content = read_skill("status")
        assert "cache.py" in content, (
            "status SKILL.md must reference 'cache.py' for data queries — "
            "it must use the cache layer instead of inline Python glob patterns"
        )


class TestStatusHasMigrationGuard:
    """Scenario: status SKILL.md has migration guard"""

    def test_has_sweetclaude_product_existence_check(self):
        content = read_skill("status")
        assert _has_product_guard(content), (
            "status SKILL.md must contain an explicit conditional guard that checks "
            "for .sweetclaude/product/ existence before reading data — "
            "incidental path reads do not count"
        )

    def test_has_update_or_migrate_reference_in_guard_context(self):
        content = read_skill("status")
        # The guard must direct the user to run migration when .sweetclaude/product/ is
        # absent. The sweetclaude:update or migrate reference must appear within a short
        # window (200 chars) of a "not found" or "not migrated" message that is itself
        # adjacent to the .sweetclaude/product/ path check — not in an unrelated
        # schema version check at the top of the file.
        # We require the pattern: path-check → not-found message → update/migrate directive
        # all within a contiguous block of ≤300 chars.
        has_guard_with_migrate = bool(
            re.search(
                r'\.sweetclaude/product/'
                r'[^#]{0,300}'
                r'(not.*migrated|not.*configured|migration|has not been run|run.*migrate)',
                content, re.DOTALL | re.IGNORECASE
            )
            and (
                "sweetclaude:migrate" in content
                or re.search(r'/sweetclaude:migrate\b', content)
                or re.search(
                    r'(not.*migrated|not.*configured|migration|has not been run)'
                    r'[^#]{0,200}'
                    r'(sweetclaude:update|migrate)',
                    content, re.DOTALL | re.IGNORECASE
                )
            )
        )
        assert has_guard_with_migrate, (
            "status SKILL.md must direct the user to run 'sweetclaude:update' or "
            "'sweetclaude:migrate' when the .sweetclaude/product/ guard fails — "
            "the update reference in the schema version check does not satisfy this"
        )


class TestStatusCorrectTerminalStatuses:
    """Scenario: status SKILL.md uses correct terminal statuses"""

    def test_no_complete_as_done_status(self):
        content = read_skill("status")
        assert "'complete'" not in content, (
            "status SKILL.md must not use 'complete' as a terminal/done status — "
            "the canonical done status is 'done'"
        )

    def test_no_achieved_as_done_status(self):
        content = read_skill("status")
        assert "'achieved'" not in content, (
            "status SKILL.md must not use 'achieved' as a terminal/done status — "
            "the canonical done status is 'done'"
        )

    def test_no_closed_as_done_status(self):
        content = read_skill("status")
        assert "'closed'" not in content, (
            "status SKILL.md must not use 'closed' as a terminal/done status — "
            "the canonical done status is 'done'"
        )

    def test_no_cancelled_as_done_status(self):
        content = read_skill("status")
        assert "'cancelled'" not in content, (
            "status SKILL.md must not use 'cancelled' as a terminal/done status — "
            "canonical terminal statuses are: done, declined, abandoned, superseded"
        )

    def test_no_canceled_as_done_status(self):
        content = read_skill("status")
        assert "'canceled'" not in content, (
            "status SKILL.md must not use 'canceled' as a terminal/done status — "
            "canonical terminal statuses are: done, declined, abandoned, superseded"
        )


# ---------------------------------------------------------------------------
# big-picture: migration guard
# ---------------------------------------------------------------------------

class TestBigPictureHasMigrationGuard:
    """Scenario: status SKILL.md has migration guard"""

    def test_has_sweetclaude_product_existence_check(self):
        content = read_skill("status")
        assert _has_product_guard(content), (
            "status SKILL.md must contain an explicit conditional guard that checks "
            "for .sweetclaude/product/ existence to detect whether migration has been run — "
            "incidental path reads do not count"
        )


# ---------------------------------------------------------------------------
# recap: no retired prefixes
# ---------------------------------------------------------------------------

class TestRecapNoRetiredPrefixes:
    """Scenario: recap SKILL.md contains no retired prefixes"""

    def test_no_rel_prefix(self):
        content = read_skill("recap")
        assert "REL-" not in content, (
            "recap SKILL.md must not use 'REL-' prefix — "
            "releases are now milestones with 'MS-' prefix"
        )

    def test_no_rm_prefix(self):
        content = read_skill("recap")
        assert "RM-" not in content, (
            "recap SKILL.md must not use 'RM-' (roadmap item) prefix — "
            "roadmap items are now milestones with 'MS-' prefix"
        )

    def test_no_bl_prefix(self):
        content = read_skill("recap")
        assert "BL-" not in content, (
            "recap SKILL.md must not use 'BL-' (backlog item) prefix — "
            "backlog items are now issues with 'ISSUE-' prefix"
        )

    def test_no_story_prefix(self):
        content = read_skill("recap")
        assert "STORY-" not in content, (
            "recap SKILL.md must not use 'STORY-' prefix — "
            "work items are now issues with 'ISSUE-' prefix"
        )
