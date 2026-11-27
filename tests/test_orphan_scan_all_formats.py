"""Comprehensive format matrix for update's orphan scan.

Every work-item format the framework has ever used (per migrate_taxonomy.py's
SOURCE_SPECS + scanners + passthrough set) is pushed through scan_orphans, and
we assert it is classified correctly:

  - current / passthrough / draft  -> NOT flagged
  - legacy needing migration       -> flagged

This is the spec for "update and migrate account for ALL previous formats."
Failures here are the gaps.
"""
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "migrate" / "migrate-v3-to-v4.py"


def _scan(project_dir):
    out = subprocess.run(
        ["python3", str(SCRIPT), "scan-orphans", "--project-dir", str(project_dir)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _w(path: Path, item_id: str, status="new"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nid: {item_id}\ntitle: {item_id}\nstatus: {status}\n---\n\nbody\n")


def _project(tmp_path):
    """One file of every known format, each in its canonical/legacy location."""
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"

    # --- current / passthrough / draft: must NOT be flagged ---
    _w(bl / "ISSUE-001-current.md", "ISSUE-001")
    _w(bl / "done" / "ISSUE-002-done.md", "ISSUE-002", status="done")
    _w(bl / "archived" / "ISSUE-003-arch.md", "ISSUE-003", status="superseded")
    _w(base / "milestones" / "MS-001-m.md", "MS-001")
    _w(base / "roadmap" / "RM-001-r.md", "RM-001")
    _w(base / "issues" / "I-001-i.md", "I-001")
    # --- legacy: must be flagged as needing migration ---
    _w(base / "BL-005-product-brief-draft-v1.0-20260511.md", "BL-005")  # product root, still legacy prefix
    _w(bl / "BL-010-legacy.md", "BL-010")
    _w(bl / "EP-001-legacy-epic.md", "EP-001")
    _w(bl / "done" / "STORY-001-done.md", "STORY-001", status="done")
    _w(bl / "BUG-001-legacy.md", "BUG-001")
    _w(bl / "DEBT-001-legacy.md", "DEBT-001")
    _w(bl / "CHORE-001-legacy.md", "CHORE-001")
    _w(bl / "stories" / "STORY-050-typed.md", "STORY-050")          # typed subdir
    _w(bl / "bugs" / "BUG-050-typed.md", "BUG-050")
    _w(bl / "spike-reports" / "spike-BL-001-s.md", "spike-BL-001")  # spike
    _w(base / "stories" / "EPIC-001" / "EPIC-001.md", "EPIC-001")       # bespoke epic container
    _w(base / "stories" / "EPIC-001" / "US-001-bespoke.md", "US-001")  # bespoke epic tree
    _w(base / "stories" / "BL-077" / "US-002-bespoke.md", "US-002")    # bespoke BL story tree
    return tmp_path


MUST_NOT_FLAG = {"ISSUE-001", "ISSUE-002", "ISSUE-003", "MS-001", "RM-001", "I-001"}
MUST_FLAG = {
    "BL-005", "BL-010", "EP-001", "EPIC-001", "STORY-001", "BUG-001", "DEBT-001",
    "CHORE-001", "STORY-050", "BUG-050", "spike-BL-001", "US-001", "US-002",
}


def test_no_current_or_passthrough_or_draft_is_flagged(tmp_path):
    findings = _scan(_project(tmp_path))["findings"]
    flagged = {f["id"] for f in findings} | {Path(f["file"]).stem for f in findings}
    wrongly = {i for i in MUST_NOT_FLAG if i in flagged or any(i in s for s in flagged)}
    assert not wrongly, f"current/passthrough/draft formats wrongly flagged as orphans: {sorted(wrongly)}"


def test_every_legacy_format_is_flagged(tmp_path):
    findings = _scan(_project(tmp_path))["findings"]
    flagged = {f["id"] for f in findings} | {Path(f["file"]).stem.split("-")[0] for f in findings}
    flagged_ids = {f["id"] for f in findings}
    missing = []
    for item in MUST_FLAG:
        if item in flagged_ids:
            continue
        # bespoke US-*/spike files may report by stem rather than frontmatter id
        if any(item in (f["id"], Path(f["file"]).stem) or item.split("-")[0] in Path(f["file"]).stem
               for f in findings):
            continue
        missing.append(item)
    assert not missing, f"legacy formats NOT detected by orphan scan (gap): {sorted(missing)}"


def test_unknown_prefix_with_frontmatter_flagged_as_martian(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "ISSUE-001-normal.md", "ISSUE-001")
    _w(bl / "FEAT-001-alien.md", "FEAT-001")
    _w(bl / "REQ-042-spec.md", "REQ-042")
    findings = _scan(tmp_path)["findings"]
    martians = [f for f in findings if f["category"] == "martian"]
    martian_ids = {f["id"] for f in martians}
    assert "FEAT-001" in martian_ids, "unknown prefix FEAT- must be flagged as martian"
    assert "REQ-042" in martian_ids, "unknown prefix REQ- must be flagged as martian"
    assert "ISSUE-001" not in {f["id"] for f in findings}, "ISSUE-001 must not be flagged"


def test_plain_markdown_without_frontmatter_not_flagged(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "ISSUE-001-normal.md", "ISSUE-001")
    no_fm = bl / "README.md"
    no_fm.parent.mkdir(parents=True, exist_ok=True)
    no_fm.write_text("# Just a readme\n\nNo frontmatter here.\n")
    findings = _scan(tmp_path)["findings"]
    flagged_files = {f["file"] for f in findings}
    assert not any("README" in f for f in flagged_files), "plain markdown without frontmatter must not be flagged"


def test_acknowledged_martian_not_reflagged(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "ISSUE-001-normal.md", "ISSUE-001")
    _w(bl / "FEAT-001-alien.md", "FEAT-001")
    _w(bl / "FEAT-002-also-alien.md", "FEAT-002")

    reg = tmp_path / ".sweetclaude" / "state" / "martian-registry.yaml"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(
        "version: 1\nacknowledged:\n"
        f"  - path: {'.sweetclaude/product/backlog/FEAT-001-alien.md'}\n"
        "    acknowledged_at: '2026-06-17T00:00:00+00:00'\n"
    )

    findings = _scan(tmp_path)["findings"]
    martian_ids = {f["id"] for f in findings if f["category"] == "martian"}
    assert "FEAT-001" not in martian_ids, "acknowledged martian must not be re-flagged"
    assert "FEAT-002" in martian_ids, "non-acknowledged martian must still be flagged"


def test_archive_martians_moves_files(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "FEAT-001-alien.md", "FEAT-001")

    out = subprocess.run(
        ["python3", str(SCRIPT), "archive-orphans", "--project-dir", str(tmp_path),
         "--paths", json.dumps([".sweetclaude/product/backlog/FEAT-001-alien.md"])],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    result = json.loads(out.stdout)
    assert len(result["archived"]) == 1
    assert not (bl / "FEAT-001-alien.md").exists(), "source file must be moved"
    assert (base / "archive" / "orphans" / "FEAT-001-alien.md").exists(), "file must land in archive/orphans/"


def test_acknowledge_martians_writes_registry(tmp_path):
    (tmp_path / ".sweetclaude" / "state").mkdir(parents=True, exist_ok=True)
    out = subprocess.run(
        ["python3", str(SCRIPT), "acknowledge-orphans", "--project-dir", str(tmp_path),
         "--paths", json.dumps([".sweetclaude/product/backlog/FEAT-001-alien.md"])],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    result = json.loads(out.stdout)
    assert "FEAT-001-alien.md" in result["acknowledged"][0]

    import yaml
    reg = yaml.safe_load((tmp_path / ".sweetclaude" / "state" / "orphan-registry.yaml").read_text())
    assert len(reg["acknowledged"]) == 1


# --- Action 1: Re-onboard (batch) ---


def test_reonboard_orphans_creates_issue_files(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "ISSUE-001-existing.md", "ISSUE-001")
    _w(bl / "stories" / "STORY-050-typed.md", "STORY-050")
    _w(bl / "bugs" / "BUG-050-typed.md", "BUG-050")

    out = subprocess.run(
        ["python3", str(SCRIPT), "reonboard-orphans", "--project-dir", str(tmp_path),
         "--paths", json.dumps([
             ".sweetclaude/product/backlog/stories/STORY-050-typed.md",
             ".sweetclaude/product/backlog/bugs/BUG-050-typed.md",
         ])],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    result = json.loads(out.stdout)
    assert len(result["reonboarded"]) == 2
    assert result["reonboarded"][0]["new_id"] == "ISSUE-002"
    assert result["reonboarded"][1]["new_id"] == "ISSUE-003"
    assert (bl / "ISSUE-002-story-050.md").exists() or any(
        p.name.startswith("ISSUE-002") for p in bl.glob("ISSUE-002*.md")
    )

    import yaml
    for entry in result["reonboarded"]:
        dest = tmp_path / entry["dest"]
        fm = yaml.safe_load(dest.read_text().split("---", 2)[1])
        assert "reonboarded_from" in fm


# --- Action 2: Group orphans ---


def test_group_orphans_groups_by_category_prefix_and_directory(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "ISSUE-001-normal.md", "ISSUE-001")
    _w(base / "stray/BL-010-legacy.md", "BL-010")
    _w(base / "stray/BL-011-legacy.md", "BL-011")
    _w(bl / "stories" / "STORY-050-typed.md", "STORY-050")

    out = subprocess.run(
        ["python3", str(SCRIPT), "group-orphans", "--project-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    result = json.loads(out.stdout)
    assert result["group_count"] >= 2
    assert result["has_grouping"] is True
    labels = [g["label"] for g in result["groups"]]
    assert any("BL-" in l for l in labels)
    assert any("directory" in g for g in result["groups"])


def test_group_orphans_single_file_has_grouping_false(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "ISSUE-001-normal.md", "ISSUE-001")
    _w(bl / "FEAT-001-alien.md", "FEAT-001")

    out = subprocess.run(
        ["python3", str(SCRIPT), "group-orphans", "--project-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    result = json.loads(out.stdout)
    assert result["total_files"] == 1
    assert result["has_grouping"] is False


# --- Action 3: Review one by one (resolve-orphan dispatcher) ---


def test_resolve_orphan_reonboard(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "FEAT-001-alien.md", "FEAT-001")

    out = subprocess.run(
        ["python3", str(SCRIPT), "resolve-orphan", "--project-dir", str(tmp_path),
         "--path", ".sweetclaude/product/backlog/FEAT-001-alien.md",
         "--action", "reonboard"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    result = json.loads(out.stdout)
    assert result["action"] == "reonboarded"
    assert result["new_id"] == "ISSUE-001"
    assert (tmp_path / result["dest"]).exists()


def test_resolve_orphan_archive(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "FEAT-001-alien.md", "FEAT-001")

    out = subprocess.run(
        ["python3", str(SCRIPT), "resolve-orphan", "--project-dir", str(tmp_path),
         "--path", ".sweetclaude/product/backlog/FEAT-001-alien.md",
         "--action", "archive"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    result = json.loads(out.stdout)
    assert result["action"] == "archived"
    assert not (bl / "FEAT-001-alien.md").exists()
    assert (base / "archive" / "orphans" / "FEAT-001-alien.md").exists()


def test_resolve_orphan_acknowledge(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "ISSUE-001-normal.md", "ISSUE-001")
    _w(bl / "FEAT-001-alien.md", "FEAT-001")
    (tmp_path / ".sweetclaude" / "state").mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["python3", str(SCRIPT), "resolve-orphan", "--project-dir", str(tmp_path),
         "--path", ".sweetclaude/product/backlog/FEAT-001-alien.md",
         "--action", "acknowledge"],
        capture_output=True, text=True, check=True,
    )

    rescan = _scan(tmp_path)
    assert not any(
        f["id"] == "FEAT-001" for f in rescan["findings"]
    ), "acknowledged file must not appear in subsequent scan"


def test_resolve_orphan_skip(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "FEAT-001-alien.md", "FEAT-001")

    out = subprocess.run(
        ["python3", str(SCRIPT), "resolve-orphan", "--project-dir", str(tmp_path),
         "--path", ".sweetclaude/product/backlog/FEAT-001-alien.md",
         "--action", "skip"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    result = json.loads(out.stdout)
    assert result["action"] == "skipped"
    assert (bl / "FEAT-001-alien.md").exists()


# --- Action 4: Archive round-trip verification ---


def test_archived_orphan_not_in_subsequent_scan(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "ISSUE-001-normal.md", "ISSUE-001")
    _w(bl / "FEAT-001-alien.md", "FEAT-001")

    subprocess.run(
        ["python3", str(SCRIPT), "archive-orphans", "--project-dir", str(tmp_path),
         "--paths", json.dumps([".sweetclaude/product/backlog/FEAT-001-alien.md"])],
        capture_output=True, text=True, check=True,
    )

    rescan = _scan(tmp_path)
    assert not any(
        f["id"] == "FEAT-001" for f in rescan["findings"]
    ), "archived file must not appear in subsequent scan"


def test_archived_legacy_prefix_orphan_not_in_subsequent_scan(tmp_path):
    # Legacy-prefix files (US-, BL-, STORY-, ...) are caught by the whole-tree
    # rglob in scan step 2, which descends into the scanner's own archive/orphans/
    # directory. Archiving such a file must still make it stick across scans.
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "ISSUE-001-normal.md", "ISSUE-001")
    _w(bl / "US-BL011-observability.md", "US-BL011")

    subprocess.run(
        ["python3", str(SCRIPT), "archive-orphans", "--project-dir", str(tmp_path),
         "--paths", json.dumps([".sweetclaude/product/backlog/US-BL011-observability.md"])],
        capture_output=True, text=True, check=True,
    )

    assert (base / "archive" / "orphans" / "US-BL011-observability.md").exists()

    rescan = _scan(tmp_path)
    assert not any(
        "archive/orphans" in f["file"] for f in rescan["findings"]
    ), "archived legacy-prefix file must not be re-flagged from archive/orphans/"
    assert not any(
        f["id"] == "US-BL011" for f in rescan["findings"]
    ), "archived legacy-prefix file must not appear in subsequent scan"


# --- Action 5: Acknowledge round-trip verification ---


def test_acknowledge_orphan_roundtrip_scan(tmp_path):
    base = tmp_path / ".sweetclaude" / "product"
    bl = base / "backlog"
    _w(bl / "ISSUE-001-normal.md", "ISSUE-001")
    _w(bl / "FEAT-001-alien.md", "FEAT-001")
    (tmp_path / ".sweetclaude" / "state").mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["python3", str(SCRIPT), "acknowledge-orphans", "--project-dir", str(tmp_path),
         "--paths", json.dumps([".sweetclaude/product/backlog/FEAT-001-alien.md"])],
        capture_output=True, text=True, check=True,
    )

    assert (bl / "FEAT-001-alien.md").exists(), "acknowledged file must remain in place"

    rescan = _scan(tmp_path)
    assert not any(
        f["id"] == "FEAT-001" for f in rescan["findings"]
    ), "acknowledged file must not appear in subsequent scan"
