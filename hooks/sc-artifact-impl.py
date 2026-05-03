#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
sc-artifact-impl.py
SweetClaude storage adapter — Markdown backend.

Invoked by sc-artifact.sh shell functions. Not called directly by users.

Operations:
    _init   <project_root>
    read    <project_root> <product_base> <state_base> <id>
    write   <project_root> <product_base> <state_base> <id> <json>
    create  <project_root> <product_base> <state_base> <type> <json>
    query   <project_root> <product_base> <state_base> <type> [key=value ...]
    delete  <project_root> <product_base> <state_base> <id>
    list    <project_root> <product_base> <state_base> <type>
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

TODAY = datetime.now().strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Entity metadata
# ---------------------------------------------------------------------------

PREFIX_TO_TYPE = {
    "I":     "issue",
    "EP":    "epic",
    "SP":    "sprint",
    "RM":    "roadmap_item",
    "REL":   "release",
    "MS":    "milestone",
    "PITCH": "pitch",
}

TYPE_TO_PREFIX = {v: k for k, v in PREFIX_TO_TYPE.items()}

TYPE_TO_DIR = {
    "issue":        "issues",
    "epic":         "epics",
    "sprint":       "sprints",
    "roadmap_item": "roadmap",
    "release":      "roadmap/releases",
    "milestone":    "milestones",
    "pitch":        "pitches",
}

# Index fields stored per type (subset of all fields — used for fast queries)
INDEX_FIELDS = {
    "issue":        ["id", "type", "title", "status", "priority", "effort",
                     "epic_id", "sprint_id", "roadmap_item_id", "source", "updated_at"],
    "epic":         ["id", "type", "title", "status", "roadmap_item_id", "updated_at"],
    "sprint":       ["id", "type", "title", "status", "start_date", "end_date", "updated_at"],
    "roadmap_item": ["id", "type", "title", "status", "priority", "release_id", "updated_at"],
    "release":      ["id", "type", "title", "status", "version", "milestone_id", "updated_at"],
    "milestone":    ["id", "type", "title", "status", "updated_at"],
    "pitch":        ["id", "type", "title", "status", "appetite", "updated_at"],
}

# Metadata key → field name mapping (handles **Key:** → key normalisation)
def _key_to_field(key: str) -> str:
    return key.lower().replace(" ", "_").replace("-", "_")

# Fields that map to "(none)" sentinel — stored as null in JSON
NONE_SENTINEL = {"(none)", "(sp-nnn when scheduled)", "(date when achieved)", "(rm-nnn when promoted)"}


# ---------------------------------------------------------------------------
# Init — resolve project config, output shell eval-able string
# ---------------------------------------------------------------------------

def op_init(project_root: str) -> None:
    root = Path(project_root)

    # Storage backend
    phase_path = root / ".sweetclaude" / "state" / "phase.yaml"
    backend = "markdown"
    if phase_path.exists():
        try:
            import yaml
            phase = yaml.safe_load(phase_path.read_text()) or {}
            backend = phase.get("storage_backend", "markdown")
        except Exception:
            pass

    # Product base
    privacy_path = root / ".sweetclaude" / "artifact-privacy.yaml"
    product_base = ".sweetclaude/product"
    if privacy_path.exists():
        try:
            import yaml
            privacy = yaml.safe_load(privacy_path.read_text()) or {}
            product_base = (
                privacy.get("categories", {})
                       .get("product", {})
                       .get("base_path", product_base)
            )
        except Exception:
            pass

    state_base = ".sweetclaude/state"

    print(f'SC_BACKEND="{backend}"')
    print(f'SC_PRODUCT_BASE="{root / product_base}"')
    print(f'SC_STATE_BASE="{root / state_base}"')


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

def _id_to_prefix(entity_id: str) -> str:
    """'I-025' → 'I', 'EP-001' → 'EP', 'PITCH-003' → 'PITCH'"""
    return entity_id.split("-")[0]


def _find_file(product_base: Path, entity_id: str) -> Path | None:
    prefix = _id_to_prefix(entity_id)
    entity_type = PREFIX_TO_TYPE.get(prefix)
    if not entity_type:
        return None
    type_dir = product_base / TYPE_TO_DIR[entity_type]
    if not type_dir.exists():
        return None
    pattern = re.compile(rf"^{re.escape(entity_id)}-.*\.md$", re.IGNORECASE)
    for f in type_dir.iterdir():
        if pattern.match(f.name):
            return f
    return None


def _parse_metadata(content: str) -> dict:
    """
    Parse the **Key:** Value metadata block at the top of an artifact file.
    Also handles YAML frontmatter (--- ... ---) for legacy files.
    Returns a dict with snake_case keys and Python-typed values.
    """
    # YAML frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if fm_match:
        try:
            import yaml
            data = yaml.safe_load(fm_match.group(1)) or {}
            return {str(k): (None if str(v) in NONE_SENTINEL else str(v))
                    for k, v in data.items()}
        except Exception:
            pass

    # Bold key-value metadata block
    result = {}

    # Title from heading
    title_match = re.match(r"^#\s+(?:\S+-\d+:\s+)?(.+)", content)
    if title_match:
        result["title"] = title_match.group(1).strip()

    # Metadata lines: **Key:** Value (up to first blank line after heading)
    for line in content.splitlines():
        m = re.match(r"^\*\*([^*]+):\*\*\s*(.*)", line)
        if m:
            key = _key_to_field(m.group(1).strip())
            value = m.group(2).strip()
            result[key] = None if value in NONE_SENTINEL else value

    return result


def _parse_full(entity_id: str, content: str) -> dict:
    """Parse metadata + extract body sections as text fields."""
    data = _parse_metadata(content)
    data["id"] = entity_id

    # Extract body sections (## Heading → snake_case field with _text suffix)
    for m in re.finditer(r"^## (.+?)\n(.*?)(?=^## |\Z)", content, re.MULTILINE | re.DOTALL):
        section_key = _key_to_field(m.group(1).strip()) + "_text"
        data[section_key] = m.group(2).strip()

    return data


def _update_metadata_block(content: str, updates: dict) -> str:
    """
    Apply field updates to the **Key:** Value metadata block in-place.
    Adds new fields if they don't exist. Always updates Updated:.
    """
    updates = dict(updates)
    updates["updated"] = TODAY

    lines = content.splitlines(keepends=True)
    updated_keys = set()

    new_lines = []
    for line in lines:
        m = re.match(r"^\*\*([^*]+):\*\*\s*(.*)", line.rstrip())
        if m:
            key = _key_to_field(m.group(1).strip())
            if key in updates:
                val = updates[key]
                display_val = "(none)" if val is None else str(val)
                # Preserve original key casing
                original_key = m.group(1).strip()
                new_lines.append(f"**{original_key}:** {display_val}\n")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # Append any new fields not already in the file, before first body section
    remaining = {k: v for k, v in updates.items() if k not in updated_keys}
    if remaining:
        # Find insertion point: after last metadata line, before first ##
        insert_at = 0
        for i, line in enumerate(new_lines):
            if re.match(r"^\*\*[^*]+:\*\*", line):
                insert_at = i + 1
        for k, v in remaining.items():
            display_key = k.replace("_", " ").title()
            display_val = "(none)" if v is None else str(v)
            new_lines.insert(insert_at, f"**{display_key}:** {display_val}\n")
            insert_at += 1

    return "".join(new_lines)


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------

def _index_path(state_base: Path) -> Path:
    return state_base / "project-index.json"


def _load_index(state_base: Path) -> dict:
    idx = _index_path(state_base)
    if idx.exists():
        try:
            return json.loads(idx.read_text())
        except Exception:
            pass
    return {"schema_version": 1, "generated_at": TODAY, "entities": []}


def _save_index(state_base: Path, index: dict) -> None:
    index["generated_at"] = TODAY
    _index_path(state_base).write_text(json.dumps(index, indent=2))


def _index_entry(entity_id: str, entity_type: str, data: dict) -> dict:
    fields = INDEX_FIELDS.get(entity_type, ["id", "type", "title", "status", "updated_at"])
    entry = {"id": entity_id, "type": entity_type}
    for f in fields:
        if f not in ("id", "type"):
            entry[f] = data.get(f)
    return entry


def _update_index(state_base: Path, entity_id: str, entity_type: str, data: dict) -> None:
    index = _load_index(state_base)
    entry = _index_entry(entity_id, entity_type, data)
    entities = [e for e in index["entities"] if e.get("id") != entity_id]
    entities.append(entry)
    index["entities"] = entities
    _save_index(state_base, index)


def _remove_from_index(state_base: Path, entity_id: str) -> None:
    index = _load_index(state_base)
    index["entities"] = [e for e in index["entities"] if e.get("id") != entity_id]
    _save_index(state_base, index)


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def op_read(product_base: Path, state_base: Path, entity_id: str) -> None:
    f = _find_file(product_base, entity_id)
    if not f:
        print("{}", end="")
        return
    content = f.read_text(encoding="utf-8")
    data = _parse_full(entity_id, content)
    print(json.dumps(data, indent=2))


def op_write(product_base: Path, state_base: Path, entity_id: str, json_str: str) -> None:
    f = _find_file(product_base, entity_id)
    if not f:
        print(f"ERROR: artifact {entity_id} not found", file=sys.stderr)
        sys.exit(1)

    updates = json.loads(json_str)
    content = f.read_text(encoding="utf-8")
    updated = _update_metadata_block(content, updates)
    f.write_text(updated, encoding="utf-8")

    # Refresh index entry
    prefix = _id_to_prefix(entity_id)
    entity_type = PREFIX_TO_TYPE.get(prefix, "unknown")
    data = _parse_metadata(updated)
    data["id"] = entity_id
    _update_index(state_base, entity_id, entity_type, data)

    print(json.dumps({"ok": True, "id": entity_id}))


def op_create(product_base: Path, state_base: Path, entity_type: str, json_str: str) -> None:
    if entity_type not in TYPE_TO_PREFIX:
        print(f"ERROR: unknown entity type '{entity_type}'", file=sys.stderr)
        sys.exit(1)

    prefix = TYPE_TO_PREFIX[entity_type]
    type_dir = product_base / TYPE_TO_DIR[entity_type]
    type_dir.mkdir(parents=True, exist_ok=True)

    # Find next ID
    existing = [
        int(m.group(1))
        for f in type_dir.glob(f"{prefix}-*.md")
        if (m := re.search(rf"{re.escape(prefix)}-(\d+)", f.name))
    ]
    next_num = max(existing, default=0) + 1
    entity_id = f"{prefix}-{next_num:03d}"

    data = json.loads(json_str)
    data.setdefault("status", "backlog" if entity_type == "issue" else "active")
    data.setdefault("source", "manual")
    data.setdefault("mode_introduced", "agile")

    title = data.get("title", entity_id)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    filename = f"{entity_id}-{slug}.md"
    dest = type_dir / filename

    content = _build_template(entity_id, entity_type, title, data)
    dest.write_text(content, encoding="utf-8")

    # Update index
    data["id"] = entity_id
    _update_index(state_base, entity_id, entity_type, data)

    # Append to type index file
    _append_to_type_index(type_dir, entity_type, entity_id, title, data)

    print(json.dumps({"ok": True, "id": entity_id}))


def op_query(product_base: Path, state_base: Path, entity_type: str, *filters) -> None:
    """
    Query artifacts by type and key=value filters.
    Empty value (key=) matches null/none/"(none)"/empty string.
    """
    # Parse filters
    parsed_filters = {}
    for f in filters:
        if "=" in f:
            k, _, v = f.partition("=")
            parsed_filters[k.strip()] = v.strip()

    # Check if all filter keys are in the index for this type
    index_fields = set(INDEX_FIELDS.get(entity_type, []))
    use_index = all(k in index_fields for k in parsed_filters)

    if use_index:
        index = _load_index(state_base)
        candidates = [e for e in index["entities"] if e.get("type") == entity_type]
        for key, val in parsed_filters.items():
            if val == "":
                # Empty value = match null, None, "(none)", or empty string
                candidates = [
                    e for e in candidates
                    if not e.get(key) or str(e.get(key, "")).lower() in {"none", "(none)", ""}
                ]
            else:
                candidates = [e for e in candidates if str(e.get(key, "")) == val]

        # Exclude cancelled unless status filter explicitly includes it
        if "status" not in parsed_filters:
            candidates = [e for e in candidates if e.get("status") != "cancelled"]

        # Read full artifacts for matching IDs
        results = []
        for entry in candidates:
            f = _find_file(product_base, entry["id"])
            if f:
                content = f.read_text(encoding="utf-8")
                data = _parse_full(entry["id"], content)
                results.append(data)
        print(json.dumps(results, indent=2))
    else:
        # Fallback: full file scan
        type_dir = product_base / TYPE_TO_DIR.get(entity_type, entity_type)
        prefix = TYPE_TO_PREFIX.get(entity_type, "")
        results = []
        if type_dir.exists():
            for f in sorted(type_dir.glob(f"{prefix}-*.md")):
                content = f.read_text(encoding="utf-8")
                id_match = re.match(rf"({re.escape(prefix)}-\d+)", f.name)
                if not id_match:
                    continue
                entity_id = id_match.group(1)
                data = _parse_full(entity_id, content)

                match = True
                for key, val in parsed_filters.items():
                    field_val = data.get(key)
                    if val == "":
                        if field_val and str(field_val).lower() not in {"none", "(none)", ""}:
                            match = False
                            break
                    else:
                        if str(field_val or "") != val:
                            match = False
                            break

                if match and data.get("status") != "cancelled":
                    results.append(data)
        print(json.dumps(results, indent=2))


def op_delete(product_base: Path, state_base: Path, entity_id: str) -> None:
    op_write(product_base, state_base, entity_id, json.dumps({"status": "cancelled"}))


def op_reindex(product_base: Path, state_base: Path) -> None:
    """Walk all artifact directories, rebuild project-index.json from scratch."""
    entities = []
    for entity_type, type_subdir in TYPE_TO_DIR.items():
        prefix = TYPE_TO_PREFIX[entity_type]
        type_dir = product_base / type_subdir
        if not type_dir.exists():
            continue
        for f in sorted(type_dir.glob(f"{prefix}-*.md")):
            id_match = re.search(rf"^({re.escape(prefix)}-\d+)", f.name)
            if not id_match:
                continue
            entity_id = id_match.group(1)
            try:
                content = f.read_text(encoding="utf-8")
                data = _parse_metadata(content)
                data["id"] = entity_id
                entry = _index_entry(entity_id, entity_type, data)
                entities.append(entry)
            except Exception as e:
                print(f"  WARN: could not parse {f.name}: {e}", file=sys.stderr)

    index = {
        "schema_version": 1,
        "generated_at": TODAY,
        "last_full_scan": TODAY,
        "entities": entities,
    }
    state_base.mkdir(parents=True, exist_ok=True)
    _save_index(state_base, index)
    print(json.dumps({"ok": True, "indexed": len(entities)}))


def op_list(product_base: Path, state_base: Path, entity_type: str) -> None:
    index = _load_index(state_base)
    candidates = [
        e for e in index["entities"]
        if e.get("type") == entity_type and e.get("status") != "cancelled"
    ]
    results = []
    for entry in candidates:
        f = _find_file(product_base, entry["id"])
        if f:
            content = f.read_text(encoding="utf-8")
            data = _parse_full(entry["id"], content)
            results.append(data)
    print(json.dumps(results, indent=2))


# ---------------------------------------------------------------------------
# Template builder
# ---------------------------------------------------------------------------

def _build_template(entity_id: str, entity_type: str, title: str, data: dict) -> str:
    def field(key: str, default="(none)") -> str:
        v = data.get(key)
        return str(v) if v and str(v).lower() not in {"none", "(none)"} else default

    if entity_type == "issue":
        issue_type = field("type", "story")
        status = field("status", "backlog")
        body_section = (
            "## Research question\n\n(What is the thing we need to know?)\n\n"
            f"**Appetite:** {field('appetite', 'TBD')}\n"
            f"**Output type:** {field('spike_output_type', 'decision')}\n\n"
            "## Output\n\n(Filled when done)\n"
        ) if issue_type == "spike" else (
            "## Description\n\n"
            + (field("description", "As a [user], I want [capability] so that [outcome]."))
            + "\n\n## Acceptance criteria\n\n- [ ] Condition one is true\n\n## Notes\n\n"
        )
        return (
            f"# {entity_id}: {title}\n\n"
            f"**Type:** {issue_type}\n"
            f"**Status:** {status}\n"
            f"**Priority:** {field('priority', 'soonish')}\n"
            f"**Effort:** {field('effort', 'm')}\n"
            f"**Epic:** {field('epic_id')}\n"
            f"**Sprint:** {field('sprint_id')}\n"
            f"**Roadmap Item:** {field('roadmap_item_id')}\n"
            f"**Source:** {field('source', 'manual')}\n"
            f"**Evidence:** {field('evidence')}\n"
            f"**Sprint history:** {field('sprint_history')}\n"
            f"**mode_introduced:** {field('mode_introduced', 'agile')}\n"
            f"**Created:** {TODAY}\n"
            f"**Updated:** {TODAY}\n\n"
            + body_section
        )

    if entity_type == "epic":
        return (
            f"# {entity_id}: {title}\n\n"
            f"**Status:** {field('status', 'active')}\n"
            f"**Roadmap Item:** {field('roadmap_item_id')}\n"
            f"**Goal:** {field('goal', 'When this ships, [user outcome] becomes possible.')}\n"
            f"**mode_introduced:** {field('mode_introduced', 'agile')}\n"
            f"**Created:** {TODAY}\n"
            f"**Updated:** {TODAY}\n\n"
            "## Description\n\n(What this epic covers and why it is grouped together.)\n\n"
            "## Issues\n\nSee issues with `Epic: " + entity_id + "` in their metadata.\n\n"
            "## Definition of done\n\n(Clear statement of what \"complete\" looks like.)\n"
        )

    if entity_type == "sprint":
        return (
            f"# {entity_id}: {title}\n\n"
            f"**Status:** {field('status', 'planned')}\n"
            f"**Start:** {field('start_date', 'YYYY-MM-DD')}\n"
            f"**End:** {field('end_date', 'YYYY-MM-DD')}\n"
            f"**mode_introduced:** {field('mode_introduced', 'agile')}\n"
            f"**Created:** {TODAY}\n"
            f"**Updated:** {TODAY}\n\n"
            "## Goal\n\nWhen this sprint succeeds, [outcome statement].\n\n"
            "## Issues\n\nSee issues with `Sprint: " + entity_id + "` in their metadata.\n\n"
            "## Capacity notes\n\n(Optional: known interrupts, holidays, reduced availability.)\n\n"
            "---\n\n## Retrospective\n\n(Filled post-sprint.)\n\n**Velocity:** (issue count completed)\n"
        )

    if entity_type == "roadmap_item":
        return (
            f"# {entity_id}: {title}\n\n"
            f"**Type:** {field('type', 'major_feature')}\n"
            f"**Status:** {field('status', 'planned')}\n"
            f"**Priority:** {field('priority', '1')}\n"
            f"**Release:** {field('release_id')}\n"
            f"**mode_introduced:** {field('mode_introduced', 'agile')}\n"
            f"**Created:** {TODAY}\n"
            f"**Updated:** {TODAY}\n\n"
            "## Description\n\n" + field("description", "(What this is.)") + "\n\n"
            "## Rationale\n\n" + field("rationale", "(Why this is on the roadmap at this priority, and why now.)") + "\n\n"
            "## Epics\n\nSee epics with `Roadmap Item: " + entity_id + "` in their metadata.\n\n"
            "## Notes\n\n"
        )

    if entity_type == "milestone":
        return (
            f"# {entity_id}: {title}\n\n"
            f"**Status:** {field('status', 'pending')}\n"
            f"**Release:** {field('release_id')}\n"
            f"**Achieved:** {field('achieved_at')}\n"
            f"**mode_introduced:** {field('mode_introduced', 'agile')}\n"
            f"**Created:** {TODAY}\n"
            f"**Updated:** {TODAY}\n\n"
            "## Criteria\n\n(Binary condition — this happened or it didn't.)\n\n"
            "## Description\n\n(Context, motivation, and why this milestone matters.)\n"
        )

    if entity_type == "release":
        return (
            f"# {entity_id}: {title}\n\n"
            f"**Version:** {field('version')}\n"
            f"**Status:** {field('status', 'planned')}\n"
            f"**Target date:** {field('target_date')}\n"
            f"**Milestone:** {field('milestone_id')}\n"
            f"**mode_introduced:** {field('mode_introduced', 'agile')}\n"
            f"**Created:** {TODAY}\n"
            f"**Updated:** {TODAY}\n\n"
            "## Description\n\n(What this release delivers.)\n\n"
            "## Roadmap items\n\nSee roadmap items with `Release: " + entity_id + "` in their metadata.\n\n"
            "---\n\n## Release notes\n\n(Filled when shipped.)\n"
        )

    if entity_type == "pitch":
        return (
            f"# {entity_id}: {title}\n\n"
            f"**Status:** {field('status', 'draft')}\n"
            f"**Appetite:** {field('appetite', 'six_weeks')}\n"
            f"**mode_introduced:** shape_up\n"
            f"**Created:** {TODAY}\n"
            f"**Updated:** {TODAY}\n\n"
            "## Problem\n\n(Concrete description of the problem. Include a specific scenario.)\n\n"
            "## Solution\n\n(The proposed approach.)\n\n"
            "## Rabbit holes\n\n- (Risk or scope trap to avoid)\n\n"
            "## No-gos\n\n- (Explicitly out of scope)\n"
        )

    # Generic fallback
    return (
        f"# {entity_id}: {title}\n\n"
        f"**Status:** {field('status', 'active')}\n"
        f"**Created:** {TODAY}\n"
        f"**Updated:** {TODAY}\n\n"
        "## Description\n\n(No template defined for this type.)\n"
    )


# ---------------------------------------------------------------------------
# Type index file helpers
# ---------------------------------------------------------------------------

def _append_to_type_index(type_dir: Path, entity_type: str, entity_id: str,
                           title: str, data: dict) -> None:
    index_name = type_dir.name.upper().replace("/", "-").rstrip("S") + "S-INDEX.md"
    index_path = type_dir / f"{type_dir.name.upper()}-INDEX.md"
    if not index_path.exists():
        # Try common naming patterns
        for name in [f"{type_dir.name.upper()}-INDEX.md", "ISSUES-INDEX.md",
                     "EPICS-INDEX.md", "SPRINTS-INDEX.md", "ROADMAP-INDEX.md",
                     "MILESTONES-INDEX.md", "PITCHES-INDEX.md", "RELEASES-INDEX.md"]:
            candidate = type_dir / name
            if candidate.exists():
                index_path = candidate
                break
        else:
            return  # No index file found — skip silently

    content = index_path.read_text(encoding="utf-8")
    filename = f"{entity_id}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:60]}.md"
    status = data.get("status", "")
    new_row = f"| {entity_id} | [{title[:55]}]({filename}) | {status} |"

    # Append before end of file, after the last table row
    last_row = content.rfind("\n|")
    if last_row >= 0:
        insert_at = content.index("\n", last_row + 1)
        content = content[:insert_at] + "\n" + new_row + content[insert_at:]
    else:
        content = content.rstrip() + "\n" + new_row + "\n"

    index_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: sc-artifact-impl.py <operation> [args...]", file=sys.stderr)
        sys.exit(1)

    op = sys.argv[1]

    if op == "_init":
        if len(sys.argv) < 3:
            print("Usage: sc-artifact-impl.py _init <project_root>", file=sys.stderr)
            sys.exit(1)
        op_init(sys.argv[2])
        return

    if len(sys.argv) < 5:
        print(f"Usage: sc-artifact-impl.py {op} <project_root> <product_base> <state_base> [args...]",
              file=sys.stderr)
        sys.exit(1)

    product_base = Path(sys.argv[3])
    state_base = Path(sys.argv[4])
    args = sys.argv[5:]

    if op == "read":
        if not args:
            print("ERROR: read requires <id>", file=sys.stderr); sys.exit(1)
        op_read(product_base, state_base, args[0])

    elif op == "write":
        if len(args) < 2:
            print("ERROR: write requires <id> <json>", file=sys.stderr); sys.exit(1)
        op_write(product_base, state_base, args[0], args[1])

    elif op == "create":
        if len(args) < 2:
            print("ERROR: create requires <type> <json>", file=sys.stderr); sys.exit(1)
        op_create(product_base, state_base, args[0], args[1])

    elif op == "query":
        if not args:
            print("ERROR: query requires <type> [key=value ...]", file=sys.stderr); sys.exit(1)
        op_query(product_base, state_base, args[0], *args[1:])

    elif op == "delete":
        if not args:
            print("ERROR: delete requires <id>", file=sys.stderr); sys.exit(1)
        op_delete(product_base, state_base, args[0])

    elif op == "list":
        if not args:
            print("ERROR: list requires <type>", file=sys.stderr); sys.exit(1)
        op_list(product_base, state_base, args[0])

    elif op == "reindex":
        op_reindex(product_base, state_base)

    else:
        print(f"ERROR: unknown operation '{op}'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
