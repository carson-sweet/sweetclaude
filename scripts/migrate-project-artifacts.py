#!/usr/bin/env python3
"""
migrate-project-artifacts.py
Migrates SweetClaude's legacy MS-NNN and BL-NNN files to the v1.2 Project
category data model.

Usage:
    python3 scripts/migrate-project-artifacts.py [--dry-run] [--repo-root PATH]

Options:
    --dry-run       Print all intended operations without writing any files.
    --repo-root     Path to the repo root. Defaults to the directory containing
                    this script's parent directory.
"""

import argparse
import os
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TODAY = datetime.now().strftime("%Y-%m-%d")

PRIORITY_MAP = {
    "P1": "sooner",
    "P2": "soonish",
    "P3": "later",
    "SPIKE": "later",
}

# Roadmap items derived from MS-002, MS-003, MS-004 in order
MILESTONE_TO_ROADMAP = [
    ("MS-002-skills-2-phase-1.md",               "RM-001", "skills-2-phase-1"),
    ("MS-003-skills-2-phase-2.md",               "RM-002", "skills-2-phase-2"),
    ("MS-004-ecosystem-integration-skill-expansion.md", "RM-003", "ecosystem-integration-skill-expansion"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_file(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"  [DRY-RUN] Would write: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"  Written:  {path}")


def extract_meta(content: str, key: str) -> str:
    """Extract value from **Key:** Value metadata line. Returns '' if not found."""
    pattern = rf"\*\*{re.escape(key)}:\*\*\s*(.+)"
    m = re.search(pattern, content)
    return m.group(1).strip() if m else ""


def extract_section(content: str, heading: str) -> str:
    """Extract the body of a ## Heading section (up to the next ## or end of file)."""
    pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
    m = re.search(pattern, content, re.DOTALL)
    return m.group(1).strip() if m else ""


def slugify(text: str) -> str:
    """Convert title text to a filename-safe slug."""
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:60]


def infer_issue_type(filename: str, title: str, priority_raw: str, summary: str) -> str:
    """Infer issue type from available signals."""
    if "SPIKE" in priority_raw.upper() or re.search(r"\bspike\b", title, re.IGNORECASE):
        return "spike"
    combined = (title + " " + summary).lower()
    if re.search(r"\b(bug|fix|broken|crash|error|regression)\b", combined):
        return "bug"
    if re.search(r"\b(refactor|chore|cleanup|rename|remove|delete|deprecat)\b", combined):
        return "chore"
    return "story"


def map_priority(raw: str) -> str:
    raw = raw.upper().strip()
    for key, val in PRIORITY_MAP.items():
        if key in raw:
            return val
    return "soonish"


def map_status_bl(raw: str) -> str:
    raw_upper = raw.upper().strip()
    if raw_upper.startswith("DONE"):
        return "done"
    return "backlog"


# ---------------------------------------------------------------------------
# Phase 1: Reformat MS-001 as a proper Milestone
# ---------------------------------------------------------------------------

def migrate_ms001(milestones_dir: Path, dry_run: bool) -> str:
    src = milestones_dir / "MS-001-public-launch.md"
    if not src.exists():
        return "  SKIP MS-001: file not found\n"

    content = read_file(src)

    if "**Criteria:**" in content:
        return "  SKIP MS-001: already migrated (Criteria field present)\n"

    status = extract_meta(content, "Status")

    # Derive a one-line criteria from the Measuring success section
    criteria_section = extract_section(content, "Measuring success")
    first_criterion = ""
    for line in criteria_section.splitlines():
        line = line.strip()
        if line.startswith("- [ ]") or line.startswith("- [x]"):
            first_criterion = line.lstrip("- [x] ").lstrip("- [ ] ").strip()
            break
    criteria_summary = (
        first_criterion if first_criterion
        else "All success criteria in the Criteria section are met."
    )

    # Insert metadata fields after the existing ones
    new_meta = (
        f"**Status:** {status}\n"
        f"**Criteria:** {criteria_summary}\n"
        f"**mode_introduced:** agile\n"
        f"**Created:** 2026-04-01\n"
        f"**Updated:** {TODAY}\n"
    )

    # Replace the existing metadata block (lines starting with ** up to blank line)
    updated = re.sub(
        r"(# MS-001[^\n]*\n\n?)(\*\*.*?\n)+",
        lambda m: m.group(1) + new_meta + "\n",
        content,
        count=1,
        flags=re.DOTALL,
    )

    # Rename ## Measuring success → ## Criteria
    updated = updated.replace("## Measuring success", "## Criteria")

    write_file(src, updated, dry_run)
    return f"  MS-001: reformatted as Milestone v1.2 ({src.name})\n"


# ---------------------------------------------------------------------------
# Phase 2: Convert MS-002, MS-003, MS-004 → Roadmap Items
# ---------------------------------------------------------------------------

def migrate_milestone_to_roadmap(
    ms_file: Path,
    rm_id: str,
    rm_slug: str,
    roadmap_dir: Path,
    dry_run: bool,
) -> str:
    if not ms_file.exists():
        return f"  SKIP {ms_file.name}: file not found\n"

    dest = roadmap_dir / f"{rm_id}-{rm_slug}.md"
    if dest.exists():
        return f"  SKIP {ms_file.name} → {dest.name}: target already exists\n"

    content = read_file(ms_file)

    # Extract title from first heading
    title_match = re.match(r"#\s+MS-\d+:\s+(.+)", content)
    title = title_match.group(1).strip() if title_match else rm_slug.replace("-", " ").title()

    # Extract description from ## Outcome section
    description = extract_section(content, "Outcome") or "See original milestone file for full outcome description."

    # Determine status: achieved → complete, else planned
    ms_status = extract_meta(content, "Status").lower()
    rm_status = "complete" if "achieved" in ms_status else "planned"

    # Priority: RM-001=1, RM-002=2, RM-003=3 based on slug order
    priority_num = int(rm_id.replace("RM-", ""))

    roadmap_content = textwrap.dedent(f"""\
        # {rm_id}: {title}

        **Type:** major_feature
        **Status:** {rm_status}
        **Priority:** {priority_num}
        **Release:** (none)
        **mode_introduced:** agile
        **Created:** 2026-05-03
        **Updated:** {TODAY}

        ## Description

        {description}

        ## Rationale

        (Derived from original milestone — fill in the "why now, at this priority" reasoning.)

        ## Epics

        See epics with `Roadmap Item: {rm_id}` in their metadata.

        ## Notes

        Migrated from {ms_file.name} on {TODAY}.
        Original milestone contributing work items and changelog are preserved in the source file.
    """)

    write_file(dest, roadmap_content, dry_run)
    return f"  {ms_file.name} → {dest.name}\n"


# ---------------------------------------------------------------------------
# Phase 3: Convert BL-NNN → I-NNN Issues
# ---------------------------------------------------------------------------

def parse_bl_frontmatter(content: str) -> dict:
    """Parse YAML-style frontmatter (--- ... ---) from a BL file. Returns {} if absent."""
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    result = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip()] = v.strip()
    return result


def extract_bl_title_and_body(content: str) -> tuple[str, str]:
    """Return (title, body_without_frontmatter_or_heading)."""
    # YAML frontmatter format
    fm = parse_bl_frontmatter(content)
    if fm.get("title"):
        body = re.sub(r"^---\n.*?\n---\n*", "", content, flags=re.DOTALL)
        return fm["title"], body

    # Markdown heading format: # BL-NNN: Title
    m = re.match(r"#\s+BL-\d+:\s+(.+)\n", content)
    if m:
        body = content[m.end():]
        return m.group(1).strip(), body

    return "", content


def migrate_backlog_items(
    backlog_dir: Path,
    issues_dir: Path,
    dry_run: bool,
) -> tuple[list[dict], str]:
    """Returns (list of issue metadata dicts for index, log string)."""
    log = ""
    issues = []

    bl_files = sorted(
        [f for f in backlog_dir.glob("BL-*.md") if f.name != "BACKLOG-INDEX.md"],
        key=lambda f: int(re.search(r"BL-(\d+)", f.name).group(1)),
    )

    issue_counter = 1

    for bl_file in bl_files:
        content = read_file(bl_file)

        title, body = extract_bl_title_and_body(content)
        if not title:
            log += f"  SKIP {bl_file.name}: could not parse title\n"
            continue

        bl_num = int(re.search(r"BL-(\d+)", bl_file.name).group(1))
        slug = "-".join(bl_file.stem.split("-")[2:]) or slugify(title)

        # Try frontmatter fields first, fall back to inline **Key:** metadata
        fm = parse_bl_frontmatter(content)
        priority_raw = fm.get("priority") or extract_meta(content, "Priority") or ""
        status_raw = fm.get("status") or extract_meta(content, "Status") or "OPEN"
        created = fm.get("created") or extract_meta(content, "Created") or TODAY

        new_priority = map_priority(priority_raw)
        new_status = map_status_bl(status_raw)
        issue_type = infer_issue_type(bl_file.name, title, priority_raw, content[:500])

        issue_id = f"I-{issue_counter:03d}"
        dest = issues_dir / f"{issue_id}-{slug}.md"

        if dest.exists():
            log += f"  SKIP {bl_file.name}: target {dest.name} already exists\n"
            # Still count it for the index
            issues.append({
                "id": issue_id,
                "title": title,
                "type": issue_type,
                "status": new_status,
                "priority": new_priority,
                "effort": "m",
                "source_file": dest.name,
                "migrated_from": bl_file.name,
            })
            issue_counter += 1
            continue

        # body already has frontmatter/heading stripped by extract_bl_title_and_body
        # Strip any remaining inline metadata lines (**Key:** Value) at the top
        body = re.sub(r"^(\*\*[^\n]+\n)+\n?", "", body, flags=re.MULTILINE)

        # Rename ## Summary → ## Description
        body = re.sub(r"^## Summary\b", "## Description", body, flags=re.MULTILINE)

        # Build sprint history note for spike output section
        spike_section = ""
        if issue_type == "spike":
            spike_section = "\n## Output\n\n(Filled when done)\n"

        new_content = textwrap.dedent(f"""\
            # {issue_id}: {title}

            **Type:** {issue_type}
            **Status:** {new_status}
            **Priority:** {new_priority}
            **Effort:** m
            **Epic:** (none)
            **Sprint:** (none)
            **Roadmap Item:** (none)
            **Source:** manual
            **Evidence:** (none)
            **Sprint history:** (none)
            **Migrated from:** {bl_file.name}
            **Created:** {created}
            **Updated:** {TODAY}
        """) + "\n" + body.lstrip("\n") + spike_section

        write_file(dest, new_content, dry_run)
        log += f"  {bl_file.name} (BL-{bl_num:03d}) → {dest.name}  [{issue_type}, {new_priority}, {new_status}]\n"

        issues.append({
            "id": issue_id,
            "title": title,
            "type": issue_type,
            "status": new_status,
            "priority": new_priority,
            "effort": "m",
            "source_file": dest.name,
            "migrated_from": bl_file.name,
        })
        issue_counter += 1

    return issues, log


# ---------------------------------------------------------------------------
# Phase 4: Create / update index files
# ---------------------------------------------------------------------------

def write_roadmap_index(roadmap_dir: Path, dry_run: bool) -> str:
    dest = roadmap_dir / "ROADMAP-INDEX.md"
    if dest.exists():
        return f"  SKIP ROADMAP-INDEX.md: already exists\n"

    rm_files = sorted(roadmap_dir.glob("RM-*.md"))
    rows = []
    for f in rm_files:
        content = read_file(f) if f.exists() else ""
        title_m = re.match(r"#\s+(RM-\d+):\s+(.+)", content)
        rm_id = title_m.group(1) if title_m else f.stem.split("-")[0]
        title = title_m.group(2) if title_m else f.stem
        status = extract_meta(content, "Status") or "planned"
        type_ = extract_meta(content, "Type") or "major_feature"
        rows.append(f"| {rm_id} | [{title}]({f.name}) | {status} | {type_} |")

    table = "\n".join(rows) if rows else "| (none) | | | |"
    index_content = textwrap.dedent(f"""\
        # Roadmap Index

        Managed by `project-roadmap`. Paths resolved via `.sweetclaude/artifact-privacy.yaml`.

        | ID | Title | Status | Type |
        |----|-------|--------|------|
        {table}
    """)

    write_file(dest, index_content, dry_run)
    return f"  Created ROADMAP-INDEX.md ({len(rm_files)} items)\n"


def write_issues_index(issues_dir: Path, issues: list[dict], dry_run: bool) -> str:
    dest = issues_dir / "ISSUES-INDEX.md"
    if dest.exists():
        return f"  SKIP ISSUES-INDEX.md: already exists\n"

    rows = []
    for issue in issues:
        rows.append(
            f"| {issue['id']} | [{issue['title'][:55]}]({issue['source_file']}) "
            f"| {issue['type']} | {issue['status']} | {issue['priority']} | {issue['effort']} |"
        )

    table = "\n".join(rows) if rows else "| (none) | | | | | |"
    index_content = textwrap.dedent(f"""\
        # Issues Index

        Managed by `project-issues` and `project-backlog`. Paths resolved via `.sweetclaude/artifact-privacy.yaml`.

        | ID | Title | Type | Status | Priority | Effort |
        |----|-------|------|--------|----------|--------|
        {table}
    """)

    write_file(dest, index_content, dry_run)
    return f"  Created ISSUES-INDEX.md ({len(issues)} issues)\n"


def update_milestones_index(milestones_dir: Path, dry_run: bool) -> str:
    dest = milestones_dir / "MILESTONES-INDEX.md"
    if not dest.exists():
        return f"  SKIP MILESTONES-INDEX.md: file not found\n"

    content = read_file(dest)
    updated = content

    for ms_file, rm_id, _ in MILESTONE_TO_ROADMAP:
        ms_id = ms_file.split("-")[0] + "-" + ms_file.split("-")[1]
        if ms_id in updated:
            updated = re.sub(
                rf"\|[^\|]*{re.escape(ms_id)}[^\|]*\|[^\n]*\n",
                "",
                updated,
            )

    if updated == content:
        return f"  MILESTONES-INDEX.md: no changes needed\n"

    # Append a note
    updated = updated.rstrip() + (
        f"\n\n<!-- MS-002, MS-003, MS-004 migrated to Roadmap Items "
        f"(RM-001, RM-002, RM-003) on {TODAY} -->\n"
    )

    write_file(dest, updated, dry_run)
    return f"  MILESTONES-INDEX.md: removed MS-002, MS-003, MS-004 rows\n"


# ---------------------------------------------------------------------------
# Migration report
# ---------------------------------------------------------------------------

def write_report(repo_root: Path, log_lines: str, issues: list[dict], dry_run: bool) -> None:
    report_path = repo_root / "scripts" / "migration-report.md"
    status = "DRY RUN" if dry_run else "COMPLETED"
    report = textwrap.dedent(f"""\
        # Project Artifact Migration Report
        **Date:** {TODAY}
        **Status:** {status}
        **Script:** scripts/migrate-project-artifacts.py

        ## Operations log

        ```
        {log_lines}
        ```

        ## Issues migrated ({len(issues)} total)

        | New ID | Original | Type | Status | Priority |
        |--------|----------|------|--------|----------|
    """)
    for issue in issues:
        report += (
            f"| {issue['id']} | {issue['migrated_from']} "
            f"| {issue['type']} | {issue['status']} | {issue['priority']} |\n"
        )

    report += textwrap.dedent(f"""
        ## Manual follow-up required

        1. **Roadmap rationale sections** — each RM-NNN has a stub rationale. Fill in the "why now" reasoning.
        2. **Issue type review** — type inference is heuristic. Review issues where type=story to confirm none should be chore or bug.
        3. **Effort estimates** — all migrated issues have effort=m (default). Run `project-backlog-triage` to set real estimates.
        4. **Priority calibration** — P1→sooner, P2→soonish, P3→later mapping may need adjustment for specific items.
        5. **Cross-references** — search all .md files for `BL-NNN` and `MS-002/003/004` references and update to new IDs.
    """)

    if dry_run:
        print(f"\n  [DRY-RUN] Would write report: {report_path}")
    else:
        report_path.write_text(report, encoding="utf-8")
        print(f"\n  Report written: {report_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Migrate SweetClaude project artifacts to v1.2 data model.")
    parser.add_argument("--dry-run", action="store_true", help="Print operations without writing files.")
    parser.add_argument("--repo-root", type=Path, default=None, help="Path to repo root.")
    args = parser.parse_args()

    repo_root = args.repo_root or Path(__file__).parent.parent
    dry_run = args.dry_run

    product_base = repo_root / ".sweetclaude" / "product"
    milestones_dir = product_base / "milestones"
    backlog_dir = product_base / "backlog"
    roadmap_dir = product_base / "roadmap"
    issues_dir = product_base / "issues"

    if not milestones_dir.exists():
        print(f"ERROR: milestones directory not found at {milestones_dir}", file=sys.stderr)
        sys.exit(1)
    if not backlog_dir.exists():
        print(f"ERROR: backlog directory not found at {backlog_dir}", file=sys.stderr)
        sys.exit(1)

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"\nSweetClaude Project Artifact Migration — {mode}")
    print("=" * 55)

    log = ""

    # Phase 1
    print("\nPhase 1: Reformat MS-001 as Milestone v1.2")
    result = migrate_ms001(milestones_dir, dry_run)
    print(result, end="")
    log += result

    # Phase 2
    print("Phase 2: Convert MS-002, MS-003, MS-004 → Roadmap Items")
    if not dry_run:
        roadmap_dir.mkdir(parents=True, exist_ok=True)

    for ms_filename, rm_id, rm_slug in MILESTONE_TO_ROADMAP:
        ms_file = milestones_dir / ms_filename
        result = migrate_milestone_to_roadmap(ms_file, rm_id, rm_slug, roadmap_dir, dry_run)
        print(result, end="")
        log += result

    # Phase 3
    print("Phase 3: Convert BL-*.md → I-NNN Issues")
    if not dry_run:
        issues_dir.mkdir(parents=True, exist_ok=True)

    issues, bl_log = migrate_backlog_items(backlog_dir, issues_dir, dry_run)
    print(bl_log, end="")
    log += bl_log

    # Phase 4
    print("Phase 4: Create index files")
    for fn, result in [
        ("ROADMAP-INDEX.md", write_roadmap_index(roadmap_dir, dry_run)),
        ("ISSUES-INDEX.md", write_issues_index(issues_dir, issues, dry_run)),
        ("MILESTONES-INDEX.md", update_milestones_index(milestones_dir, dry_run)),
    ]:
        print(result, end="")
        log += result

    # Report
    write_report(repo_root, log, issues, dry_run)

    print(f"\nDone. {len(issues)} issues migrated, 3 roadmap items created.")
    if dry_run:
        print("Re-run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
