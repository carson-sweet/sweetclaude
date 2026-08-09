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

import yaml

TODAY = datetime.now().strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Entity metadata
# ---------------------------------------------------------------------------

PREFIX_TO_TYPE = {
    "ISSUE": "issue",
    # Pre-unification ids. 37 of them survive in backlog/archived/; they are
    # terminal, but a lookup by id must still resolve one (ISSUE-289).
    "I":     "issue",
    "EP":    "epic",
    "SP":    "sprint",
    "RM":    "roadmap_item",
    "REL":   "release",
    "MS":    "milestone",
    "PITCH": "pitch",
    "CYC":   "cycle",
    "TH":    "theme",
}

# The prefix `create` assigns. Declared rather than derived by inverting
# PREFIX_TO_TYPE, which would silently hand `issue` whichever alias happened to
# be declared last.
TYPE_TO_PREFIX = {
    "issue": "ISSUE", "epic": "EP", "sprint": "SP", "roadmap_item": "RM",
    "release": "REL", "milestone": "MS", "pitch": "PITCH", "cycle": "CYC",
    "theme": "TH",
}

# Every prefix a type answers to, for listing and querying. Deriving the glob
# from TYPE_TO_PREFIX alone would drop the legacy ids entirely.
TYPE_TO_PREFIXES = {
    t: tuple(p for p, pt in PREFIX_TO_TYPE.items() if pt == t)
    for t in TYPE_TO_PREFIX
}

# Where `create` writes a new artifact of each type. Issues begin life in
# backlog/ and move to roadmap/issues/ at triage, so backlog is the create
# target even though most existing issues are found elsewhere (ISSUE-289).
TYPE_TO_DIR = {
    "issue":        "backlog",
    "epic":         "roadmap/epics",
    "sprint":       "sprints",
    "roadmap_item": "roadmap",
    "release":      "roadmap/releases",
    "milestone":    "roadmap/milestones",
    "pitch":        "pitches",
    "cycle":        "cycles",
    "theme":        "themes",
}

# Where reads, queries and lists look. Issues live across three trees at once
# and move between them over their lifetime; the type map named a fourth
# directory (`issues`) that holds only an index file, so every issue lookup
# returned empty — indistinguishable from "no such issue" (ISSUE-289).
#
# Milestones had the same defect against `milestones/`, which onboarding no
# longer creates. Both legacy directories stay in the search list so a project
# that predates the move still resolves.
TYPE_SEARCH_DIRS = {
    "issue": ("roadmap/issues", "backlog", "issues"),
    "milestone": ("roadmap/milestones", "milestones"),
}


def _prefixes_for(entity_type: str) -> tuple[str, ...]:
    """Every id prefix a type answers to, current first."""
    known = TYPE_TO_PREFIXES.get(entity_type)
    if known:
        return known
    prefix = TYPE_TO_PREFIX.get(entity_type, "")
    return (prefix,) if prefix else ()


def _search_dirs(product_base: Path, entity_type: str) -> list[Path]:
    """Existing roots to search for an entity type, most specific first.

    Searched recursively by the callers: every type has terminal subdirectories
    (done/, archived/) that a single-level glob cannot see.
    """
    rels = TYPE_SEARCH_DIRS.get(entity_type)
    if rels is None:
        rels = (TYPE_TO_DIR.get(entity_type, entity_type),)
    return [product_base / rel for rel in rels if (product_base / rel).is_dir()]


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
    pattern = re.compile(rf"^{re.escape(entity_id)}-.*\.md$", re.IGNORECASE)
    for type_dir in _search_dirs(product_base, entity_type):
        for f in sorted(type_dir.rglob("*.md")):
            if pattern.match(f.name):
                return f
    return None


def _artifact_files(product_base: Path, entity_type: str, prefix: str) -> list[Path]:
    """Every artifact of a type, across all its roots and subdirectories."""
    prefixes = TYPE_TO_PREFIXES.get(entity_type) or ((prefix,) if prefix else ())
    seen: dict[str, Path] = {}
    for type_dir in _search_dirs(product_base, entity_type):
        for p in prefixes:
            for f in sorted(type_dir.rglob(f"{p}-*.md")):
                seen.setdefault(f.name, f)
    return [seen[name] for name in sorted(seen)]


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


_INTEGER_FIELDS = {"story_points", "velocity", "duration_weeks"}


def _parse_full(entity_id: str, content: str) -> dict:
    """Parse metadata + extract body sections as text fields."""
    data = _parse_metadata(content)
    data["id"] = entity_id

    # Coerce known integer fields
    for field_name in _INTEGER_FIELDS:
        if field_name in data and data[field_name] is not None:
            try:
                data[field_name] = int(data[field_name])
            except (TypeError, ValueError):
                pass

    # Extract body sections (## Heading → snake_case field with _text suffix)
    for m in re.finditer(r"^## (.+?)\n(.*?)(?=^## |\Z)", content, re.MULTILINE | re.DOTALL):
        section_key = _key_to_field(m.group(1).strip()) + "_text"
        data[section_key] = m.group(2).strip()

    return data


def _update_yaml_frontmatter(content: str, updates: dict) -> str:
    updates = dict(updates)
    updates["updated"] = TODAY
    fm_match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if not fm_match:
        return content
    fm_data = yaml.safe_load(fm_match.group(1)) or {}
    body = fm_match.group(2)
    fm_data.update(updates)
    fm_text = yaml.dump(fm_data, default_flow_style=False, allow_unicode=True)
    return f"---\n{fm_text}---\n{body}"


def _update_bold_block(content: str, updates: dict) -> str:
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
                original_key = m.group(1).strip()
                new_lines.append(f"**{original_key}:** {display_val}\n")
                updated_keys.add(key)
                continue
        new_lines.append(line)
    remaining = {k: v for k, v in updates.items() if k not in updated_keys}
    if remaining:
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


def _update_metadata_block(content: str, updates: dict) -> str:
    if content.startswith("---\n"):
        return _update_yaml_frontmatter(content, updates)
    return _update_bold_block(content, updates)




# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def op_read(product_base: Path, state_base: Path, entity_id: str) -> None:
    f = _find_file(product_base, entity_id)
    if not f:
        # An empty result is the right answer for an id that does not exist,
        # and the wrong answer for a lookup that had nowhere to look. Those
        # were the same output for every issue in the project until ISSUE-289,
        # so nobody could see the difference. Still {} on stdout so callers
        # parse unchanged; the distinction goes to stderr.
        entity_type = PREFIX_TO_TYPE.get(_id_to_prefix(entity_id))
        if entity_type is None:
            print(f"sc-artifact: unknown id prefix in {entity_id!r}; known "
                  f"prefixes: {', '.join(sorted(PREFIX_TO_TYPE))}", file=sys.stderr)
        elif not _search_dirs(product_base, entity_type):
            searched = TYPE_SEARCH_DIRS.get(
                entity_type, (TYPE_TO_DIR.get(entity_type, entity_type),))
            print(f"sc-artifact: no {entity_type} directory exists under "
                  f"{product_base} (looked for {', '.join(searched)}); this is "
                  f"a layout problem, not a missing {entity_id}", file=sys.stderr)
        print("{}", end="")
        return
    content = f.read_text(encoding="utf-8")
    data = _parse_full(entity_id, content)
    print(json.dumps(data, indent=2))


def _calculate_sprint_velocity(product_base: Path, sprint_id: str) -> int:
    import glob as _glob
    total = 0
    for fname in _artifact_files(product_base, "issue", TYPE_TO_PREFIX["issue"]):
        with open(fname, encoding="utf-8") as fh:
            issue = _parse_metadata(fh.read())
        if issue and (issue.get("sprint") == sprint_id or issue.get("sprint_id") == sprint_id) and issue.get("status") == "done":
            try:
                total += int(issue.get("story_points") or 0)
            except (TypeError, ValueError):
                pass
    return total


def op_write(product_base: Path, state_base: Path, entity_id: str, json_str: str,
             project_dir: Path | None = None) -> None:
    f = _find_file(product_base, entity_id)
    if not f:
        print(f"ERROR: artifact {entity_id} not found", file=sys.stderr)
        sys.exit(1)

    updates = json.loads(json_str)

    prefix = _id_to_prefix(entity_id)
    entity_type = PREFIX_TO_TYPE.get(prefix, "unknown")

    if entity_type == "issue" and updates.get("status") == "done":
        updates.setdefault("completed_at", TODAY)

    if entity_type == "sprint" and updates.get("status") == "closed":
        velocity = _calculate_sprint_velocity(product_base, entity_id)
        updates["velocity"] = velocity

    new_status = updates.pop("status", None)

    if new_status is not None and project_dir is not None:
        _scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
        if str(_scripts_dir) not in sys.path:
            sys.path.insert(0, str(_scripts_dir))

        from parse_utils import detect_format
        from schema import normalize_status
        content = f.read_text(encoding="utf-8")
        if detect_format(content) == "bold":
            from format_converter import convert_file
            convert_file(f, dry_run=False, backup=False)

        if updates:
            content = f.read_text(encoding="utf-8")
            updated = _update_metadata_block(content, updates)
            f.write_text(updated, encoding="utf-8")

        canonical = normalize_status(new_status)
        try:
            from status import TERMINAL_STATUSES, write_status, set_terminal
            if canonical in TERMINAL_STATUSES:
                set_terminal(str(f), canonical, "sc-artifact", project_dir=str(project_dir))
            else:
                write_status(str(f), canonical, "sc-artifact", project_dir=str(project_dir))
        except (ValueError, FileNotFoundError) as e:
            print(f"WARNING: propagation failed, falling back to direct write: {e}", file=sys.stderr)
            content = f.read_text(encoding="utf-8")
            updated = _update_metadata_block(content, {"status": new_status})
            f.write_text(updated, encoding="utf-8")
    else:
        if new_status is not None:
            updates["status"] = new_status
        content = f.read_text(encoding="utf-8")
        if project_dir is not None:
            _scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
            if str(_scripts_dir) not in sys.path:
                sys.path.insert(0, str(_scripts_dir))
            from parse_utils import detect_format
            if detect_format(content) == "bold":
                from format_converter import convert_file
                convert_file(f, dry_run=False, backup=False)
                content = f.read_text(encoding="utf-8")
        updated = _update_metadata_block(content, updates)
        f.write_text(updated, encoding="utf-8")

    if project_dir is not None and new_status is None:
        try:
            _scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
            if str(_scripts_dir) not in sys.path:
                sys.path.insert(0, str(_scripts_dir))
            from cache import rebuild as _rebuild
            _rebuild(str(project_dir))
        except Exception:
            pass

    print(json.dumps({"ok": True, "id": entity_id}))


def op_create(product_base: Path, state_base: Path, entity_type: str, json_str: str,
              project_dir: Path | None = None) -> None:
    if entity_type not in TYPE_TO_PREFIX:
        print(f"ERROR: unknown entity type '{entity_type}'", file=sys.stderr)
        sys.exit(1)

    prefix = TYPE_TO_PREFIX[entity_type]
    type_dir = product_base / TYPE_TO_DIR[entity_type]
    type_dir.mkdir(parents=True, exist_ok=True)

    existing = [
        int(m.group(1))
        for f in type_dir.glob(f"{prefix}-*.md")
        if (m := re.search(rf"{re.escape(prefix)}-(\d+)", f.name))
    ]
    next_num = max(existing, default=0) + 1
    entity_id = f"{prefix}-{next_num:03d}"

    data = json.loads(json_str)
    data.setdefault("status", "new")
    data.setdefault("source", "manual")
    data.setdefault("mode_introduced", "agile")

    if entity_type == "issue" and data.get("status") == "done":
        data.setdefault("completed_at", TODAY)

    title = data.get("title", entity_id)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    filename = f"{entity_id}-{slug}.md"
    dest = type_dir / filename

    content = _build_template(entity_id, entity_type, title, data)
    dest.write_text(content, encoding="utf-8")

    data["id"] = entity_id
    _append_to_type_index(type_dir, entity_type, entity_id, title, data)

    if project_dir is not None:
        _scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
        if str(_scripts_dir) not in sys.path:
            sys.path.insert(0, str(_scripts_dir))

        try:
            from cache import rebuild as _rebuild, get_conn
            _rebuild(str(project_dir))
        except Exception:
            get_conn = None

        epic_ref = data.get("epic") or data.get("epic_id")
        if epic_ref and get_conn and entity_type not in ("epic", "milestone"):
            try:
                from status import sync_parent_status
                conn = get_conn(str(project_dir))
                parent_row = conn.execute(
                    "SELECT source_path FROM items WHERE id=?", (epic_ref,)
                ).fetchone()
                if parent_row:
                    siblings = conn.execute(
                        "SELECT status FROM items WHERE epic=? AND type NOT IN ('epic', 'milestone')",
                        (epic_ref,),
                    ).fetchall()
                    conn.close()
                    parent_path = project_dir / parent_row["source_path"]
                    sync_parent_status(
                        str(parent_path), [r["status"] for r in siblings],
                        "sc-artifact", project_dir=str(project_dir),
                    )
                else:
                    conn.close()
            except Exception as e:
                print(f"WARNING: parent sync after create failed: {e}", file=sys.stderr)

    print(json.dumps({"ok": True, "id": entity_id}))


_FILTER_KEY_REMAP = {
    "epic_id": "epic", "sprint_id": "sprint", "theme_id": "theme",
    "roadmap_item_id": "roadmap_item", "milestone_id": "milestone",
    "release_id": "release",
}

_SQLITE_COLUMNS = frozenset({
    "id", "type", "title", "status", "priority", "effort", "epic",
    "epic_sequence", "milestone", "objective", "source", "source_path",
    "created", "updated", "closed_date", "sprint", "theme", "roadmap_item", "release",
})


def op_query(product_base: Path, state_base: Path, entity_type: str, *filters,
             project_dir: Path | None = None) -> None:
    parsed_filters = {}
    for f in filters:
        if "=" in f:
            k, _, v = f.partition("=")
            parsed_filters[k.strip()] = v.strip()

    remapped = {_FILTER_KEY_REMAP.get(k, k): v for k, v in parsed_filters.items()}

    if project_dir is not None and all(k in _SQLITE_COLUMNS for k in remapped):
        try:
            _scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
            if str(_scripts_dir) not in sys.path:
                sys.path.insert(0, str(_scripts_dir))
            from cache import get_conn
            conn = get_conn(str(project_dir))
            if conn:
                results = _query_sqlite(conn, product_base, entity_type, remapped)
                print(json.dumps(results, indent=2))
                return
        except Exception:
            pass

    prefix = TYPE_TO_PREFIX.get(entity_type, "")
    results = []
    if True:
        for f in _artifact_files(product_base, entity_type, prefix):
            content = f.read_text(encoding="utf-8")
            # Any prefix the type answers to, not just the one `create`
            # assigns — otherwise legacy ids are globbed and then dropped
            # here, which is worse than never finding them (ISSUE-289).
            id_match = re.match(
                rf"((?:{'|'.join(re.escape(p) for p in TYPE_TO_PREFIXES.get(entity_type, (prefix,)))})-\d+)",
                f.name)
            if not id_match:
                continue
            entity_id = id_match.group(1)
            data = _parse_full(entity_id, content)

            match = True
            for key, val in parsed_filters.items():
                field_val = data.get(key) or data.get(_FILTER_KEY_REMAP.get(key, key))
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


def _query_sqlite(conn, product_base: Path, entity_type: str, filters: dict) -> list[dict]:
    # Every prefix the type answers to. Matching only the one `create`
    # assigns silently excludes pre-unification ids from every query
    # (ISSUE-289).
    prefixes = _prefixes_for(entity_type)
    where_parts = ["(" + " OR ".join("id LIKE ?" for _ in prefixes) + ")"]
    params: list = [f"{p}-%" for p in prefixes]

    if "status" not in filters:
        where_parts.append("status != 'declined'")

    for key, val in filters.items():
        if val == "":
            where_parts.append(f"({key} IS NULL OR {key} = '' OR {key} = '(none)')")
        elif "," in val:
            placeholders = ",".join("?" for _ in val.split(","))
            where_parts.append(f"{key} IN ({placeholders})")
            params.extend(val.split(","))
        else:
            where_parts.append(f"{key} = ?")
            params.append(val)

    sql = f"SELECT id FROM items WHERE {' AND '.join(where_parts)} ORDER BY id"
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    results = []
    for row in rows:
        f = _find_file(product_base, row["id"])
        if f:
            content = f.read_text(encoding="utf-8")
            data = _parse_full(row["id"], content)
            results.append(data)
    return results


def op_delete(product_base: Path, state_base: Path, entity_id: str) -> None:
    op_write(product_base, state_base, entity_id, json.dumps({"status": "cancelled"}))


def op_reindex(product_base: Path, state_base: Path,
               project_dir: Path | None = None) -> None:
    """Rebuild the SQLite cache from artifact files on disk."""
    _scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
    if str(_scripts_dir) not in sys.path:
        sys.path.insert(0, str(_scripts_dir))
    from cache import rebuild
    pdir = str(project_dir) if project_dir else str(product_base.parent)
    result = rebuild(pdir)
    count = result.get("items", 0) if isinstance(result, dict) else 0
    print(json.dumps({"ok": True, "indexed": count}))


def op_list(product_base: Path, state_base: Path, entity_type: str,
            project_dir: Path | None = None) -> None:
    if project_dir is not None:
        try:
            _scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
            if str(_scripts_dir) not in sys.path:
                sys.path.insert(0, str(_scripts_dir))
            from cache import get_conn
            conn = get_conn(str(project_dir))
            if conn:
                prefixes = _prefixes_for(entity_type)
                like = " OR ".join("id LIKE ?" for _ in prefixes)
                rows = conn.execute(
                    f"SELECT id FROM items WHERE ({like}) "
                    "AND status != 'declined' ORDER BY id",
                    tuple(f"{p}-%" for p in prefixes),
                ).fetchall()
                conn.close()
                results = []
                for row in rows:
                    f = _find_file(product_base, row["id"])
                    if f:
                        content = f.read_text(encoding="utf-8")
                        data = _parse_full(row["id"], content)
                        results.append(data)
                print(json.dumps(results, indent=2))
                return
        except Exception:
            pass

    prefix = TYPE_TO_PREFIX.get(entity_type, "")
    results = []
    if True:
        for f in _artifact_files(product_base, entity_type, prefix):
            content = f.read_text(encoding="utf-8")
            # Any prefix the type answers to, not just the one `create`
            # assigns — otherwise legacy ids are globbed and then dropped
            # here, which is worse than never finding them (ISSUE-289).
            id_match = re.match(
                rf"((?:{'|'.join(re.escape(p) for p in TYPE_TO_PREFIXES.get(entity_type, (prefix,)))})-\d+)",
                f.name)
            if not id_match:
                continue
            entity_id = id_match.group(1)
            data = _parse_full(entity_id, content)
            if data.get("status") != "cancelled":
                results.append(data)
    print(json.dumps(results, indent=2))


# ---------------------------------------------------------------------------
# Template builder
# ---------------------------------------------------------------------------

def _build_template(entity_id: str, entity_type: str, title: str, data: dict) -> str:
    import yaml as _yaml

    def field(key: str, default=None):
        v = data.get(key)
        if v and str(v).lower() not in {"none", "(none)"}:
            return str(v)
        return default

    def _fm_block(fm: dict, body: str) -> str:
        fm_clean = {k: v for k, v in fm.items() if v is not None}
        fm_text = _yaml.dump(fm_clean, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return f"---\n{fm_text}---\n\n{body}"

    if entity_type == "issue":
        issue_type = field("type", "story")
        status = field("status", "new")
        body = (
            "## Research question\n\n(What is the thing we need to know?)\n\n"
            f"## Appetite\n\n{field('appetite') or 'TBD'}\n\n"
            f"## Output type\n\n{field('spike_output_type') or 'decision'}\n\n"
            "## Output\n\n(Filled when done)\n"
        ) if issue_type == "spike" else (
            "## Description\n\n"
            + (field("description") or "As a [user], I want [capability] so that [outcome].")
            + "\n\n## Acceptance criteria\n\n- [ ] Condition one is true\n\n## Notes\n\n"
        )
        return _fm_block({
            "id": entity_id, "title": title, "type": issue_type,
            "status": status, "priority": field("priority", "soon"),
            "effort": field("effort", "m"), "epic": field("epic_id") or field("epic"),
            "theme": field("theme_id") or field("theme"),
            "sprint": field("sprint_id") or field("sprint"),
            "roadmap_item": field("roadmap_item_id") or field("roadmap_item"),
            "story_points": field("story_points"),
            "source": field("source", "manual"), "evidence": field("evidence"),
            "sprint_history": field("sprint_history"),
            "completed_at": field("completed_at"),
            "mode_introduced": field("mode_introduced", "agile"),
            "created": TODAY, "updated": TODAY,
        }, body)

    if entity_type == "epic":
        return _fm_block({
            "id": entity_id, "title": title, "type": "epic",
            "status": field("status", "active"),
            "milestone": field("milestone_id") or field("milestone"),
            "roadmap_item": field("roadmap_item_id") or field("roadmap_item"),
            "goal": field("goal", "When this ships, [user outcome] becomes possible."),
            "source": field("source", "auto"),
            "mode_introduced": field("mode_introduced", "agile"),
            "created": TODAY, "updated": TODAY,
        }, (
            "## Description\n\n(What this epic covers and why it is grouped together.)\n\n"
            f"## Issues\n\nSee issues with `epic: {entity_id}` in their frontmatter.\n\n"
            "## Definition of done\n\n(Clear statement of what \"complete\" looks like.)\n"
        ))

    if entity_type == "theme":
        return _fm_block({
            "id": entity_id, "title": title, "type": "theme",
            "status": field("status", "active"),
            "category": field("category", "feature-area"),
            "service": field("service"),
            "created": TODAY, "updated": TODAY,
        }, (
            "## Description\n\n(What domain context these issues share — the common implementation surface, "
            "shared state, or conceptual grouping that makes them a theme.)\n\n"
            f"## Issues\n\nSee issues with `theme: {entity_id}` in their frontmatter.\n"
        ))

    if entity_type == "sprint":
        return _fm_block({
            "id": entity_id, "title": title, "type": "sprint",
            "status": field("status", "new"),
            "milestone": field("milestone_id") or field("milestone"),
            "start_date": field("start_date"),
            "end_date": field("end_date"),
            "velocity": None,
            "mode_introduced": field("mode_introduced", "agile"),
            "created": TODAY, "updated": TODAY,
        }, (
            "## Goal\n\nWhen this sprint succeeds, [outcome statement].\n\n"
            f"## Issues\n\nSee issues with `sprint: {entity_id}` in their frontmatter.\n\n"
            "## Capacity notes\n\n(Optional: known interrupts, holidays, reduced availability.)\n\n"
            "---\n\n## Retrospective\n\n(Filled post-sprint.)\n"
        ))

    if entity_type == "roadmap_item":
        return _fm_block({
            "id": entity_id, "title": title, "type": "roadmap_item",
            "status": field("status", "new"),
            "priority": field("priority", "1"),
            "release": field("release_id") or field("release"),
            "mode_introduced": field("mode_introduced", "agile"),
            "created": TODAY, "updated": TODAY,
        }, (
            "## Description\n\n" + (field("description") or "(What this is.)") + "\n\n"
            "## Rationale\n\n" + (field("rationale") or "(Why this is on the roadmap at this priority, and why now.)") + "\n\n"
            f"## Epics\n\nSee epics with `roadmap_item: {entity_id}` in their frontmatter.\n\n"
            "## Notes\n\n"
        ))

    if entity_type == "milestone":
        return _fm_block({
            "id": entity_id, "title": title, "type": "milestone",
            "status": field("status", "new"),
            "target_release": field("release_id") or field("target_release") or field("release"),
            "achieved_at": field("achieved_at"),
            "mode_introduced": field("mode_introduced", "agile"),
            "created": TODAY, "updated": TODAY,
        }, (
            "## Criteria\n\n(Binary condition — this happened or it didn't.)\n\n"
            "## Description\n\n(Context, motivation, and why this milestone matters.)\n"
        ))

    if entity_type == "release":
        return _fm_block({
            "id": entity_id, "title": title, "type": "release",
            "version": field("version"),
            "status": field("status", "new"),
            "target_date": field("target_date"),
            "milestone": field("milestone_id") or field("milestone"),
            "mode_introduced": field("mode_introduced", "agile"),
            "created": TODAY, "updated": TODAY,
        }, (
            "## Description\n\n(What this release delivers.)\n\n"
            f"## Roadmap items\n\nSee roadmap items with `release: {entity_id}` in their frontmatter.\n\n"
            "---\n\n## Release notes\n\n(Filled when shipped.)\n"
        ))

    if entity_type == "pitch":
        return _fm_block({
            "id": entity_id, "title": title, "type": "pitch",
            "status": field("status", "new"),
            "appetite": field("appetite", "six_weeks"),
            "mode_introduced": "shape_up",
            "created": TODAY, "updated": TODAY,
        }, (
            "## Problem\n\n(Concrete description of the problem. Include a specific scenario.)\n\n"
            "## Solution\n\n(The proposed approach.)\n\n"
            "## Rabbit holes\n\n- (Risk or scope trap to avoid)\n\n"
            "## No-gos\n\n- (Explicitly out of scope)\n"
        ))

    if entity_type == "cycle":
        return _fm_block({
            "id": entity_id, "title": title, "type": "cycle",
            "status": field("status", "new"),
            "goal": field("goal"),
            "duration_weeks": field("duration_weeks", "6"),
            "started_at": None,
            "ended_at": None,
            "mode_introduced": field("mode_introduced", "shape_up"),
            "created": TODAY, "updated": TODAY,
        }, (
            "## Shipped items\n\n(Filled when cycle ends.)\n\n"
            "## Retro\n\n(Filled post-cycle.)\n"
        ))

    return _fm_block({
        "id": entity_id, "title": title, "type": entity_type,
        "status": field("status", "active"),
        "created": TODAY, "updated": TODAY,
    }, "## Description\n\n(No template defined for this type.)\n")


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
        op_write(product_base, state_base, args[0], args[1], project_dir=Path(sys.argv[2]))

    elif op == "create":
        if len(args) < 2:
            print("ERROR: create requires <type> <json>", file=sys.stderr); sys.exit(1)
        op_create(product_base, state_base, args[0], args[1], project_dir=Path(sys.argv[2]))

    elif op == "query":
        if not args:
            print("ERROR: query requires <type> [key=value ...]", file=sys.stderr); sys.exit(1)
        op_query(product_base, state_base, args[0], *args[1:], project_dir=Path(sys.argv[2]))

    elif op == "delete":
        if not args:
            print("ERROR: delete requires <id>", file=sys.stderr); sys.exit(1)
        op_delete(product_base, state_base, args[0])

    elif op == "list":
        if not args:
            print("ERROR: list requires <type>", file=sys.stderr); sys.exit(1)
        op_list(product_base, state_base, args[0], project_dir=Path(sys.argv[2]))

    elif op == "reindex":
        op_reindex(product_base, state_base, project_dir=Path(sys.argv[2]))

    else:
        print(f"ERROR: unknown operation '{op}'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
