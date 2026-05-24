"""
migrate_taxonomy.py — Migrate project artifacts from legacy multi-prefix
system to unified ISSUE-NNN taxonomy.
"""
from __future__ import annotations

import hashlib
import os
import re
import tarfile
import tempfile
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PRODUCT_BASE = ".sweetclaude/product"

# Legacy source entity types mapped to directories relative to product base
# (path pattern, entity_type, subdirectory)
SOURCE_SPECS = [
    # (glob_dir_relative_to_product_base, entity_type, filename_prefix_regex)
    ("backlog",          "BL",       r"^BL-(\d+)(?:-|\.md$)"),
    ("backlog",          "EP",       r"^EP-(\d+)(?:-|\.md$)"),
    ("backlog/done",     "STORY",    r"^STORY-(\d+)(?:-|\.md$)"),
    ("backlog/spike-reports", "spike-BL", r"^spike-BL-(\d+)(?:-|\.md$)"),
    ("issues",           "I",        r"^I-(\d+)(?:-|\.md$)"),
    ("roadmap",          "RM",       r"^RM-(\d+)(?:-|\.md$)"),
    ("milestones",       "MS",       r"^MS-(\d+)(?:-|\.md$)"),
]

# Terminal statuses (after remap)
TERMINAL_STATUSES = {"done", "abandoned", "superseded", "declined", "deferred"}

# Standard priority values
STANDARD_PRIORITIES = {"P0", "P1", "P2", "P3", "P4"}

# Legacy status → new status
STATUS_REMAP = {
    "backlog": "new",
    "open": "active",
    "in_progress": "active",
    "in progress": "active",
    "cancelled": "abandoned",
    "canceled": "abandoned",
    "complete": "done",
    "achieved": "done",
    "closed": "done",
    "promoted": "superseded",
    "proposed": "new",
}

# Statuses that are already correct
CANONICAL_STATUSES = {
    "new", "ready", "active", "in-review", "blocked",
    "on-hold", "deferred", "done", "declined", "abandoned", "superseded",
}

# Priority remap
PRIORITY_REMAP = {
    "spike":   "P3",
    "next":    "P0",
    "now":     "P0",
    "sooner":  "P1",
    "soon":    "P2",
    "later":   "P3",
    "someday": "P4",
    "high":    "P1",
    "medium":  "P2",
    "low":     "P3",
    "p0":      "P0",
    "p1":      "P1",
    "p2":      "P2",
    "p3":      "P3",
    "p4":      "P4",
}

# Workflow type mapping from type field
WORKFLOW_TYPE_MAP = {
    "story":    "enhancement",
    "bug":      "bug-fix",
    "debt":     "tech-debt",
    "chore":    "tech-debt",
    "spike":    "spike",
    "refactor": "tech-debt",
}

MAX_SNAPSHOTS = 5


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SourceFile:
    path: Path
    entity_type: str
    raw_id: str


@dataclass
class PlannedMove:
    source: Path
    dest: Path
    new_id: str
    action: str
    frontmatter: dict
    body: str
    source_hash: str
    supersedes: Path = None


@dataclass
class MigrationPlan:
    moves: List[PlannedMove]
    collision_map: Dict[str, str]


@dataclass
class MigrationResult:
    migrated: int = 0
    archived: int = 0
    retired: int = 0
    restructured: int = 0
    rewritten: int = 0
    spike_archived: int = 0


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _get_product_base(project_dir: Path) -> Path:
    ap = project_dir / ".sweetclaude" / "artifact-privacy.yaml"
    if ap.exists():
        raw = ap.read_bytes()
        if raw.strip():
            try:
                data = yaml.safe_load(raw)
                if isinstance(data, dict):
                    base_path_str = (
                        data.get("product", {}).get("base_path", DEFAULT_PRODUCT_BASE)
                        if isinstance(data.get("product"), dict)
                        else DEFAULT_PRODUCT_BASE
                    )
                else:
                    base_path_str = DEFAULT_PRODUCT_BASE
            except yaml.YAMLError:
                base_path_str = DEFAULT_PRODUCT_BASE
        else:
            base_path_str = DEFAULT_PRODUCT_BASE
    else:
        base_path_str = DEFAULT_PRODUCT_BASE

    if os.path.isabs(base_path_str):
        raise ValueError(
            f"product base_path '{base_path_str}' escapes project root"
        )

    resolved = (project_dir / base_path_str).resolve()
    if not str(resolved).startswith(str(project_dir.resolve())):
        raise ValueError(
            f"product base_path '{base_path_str}' escapes project root"
        )

    return project_dir / base_path_str


def _state_dir(project_dir: Path) -> Path:
    return project_dir / ".sweetclaude" / "state"


def _migration_state_path(project_dir: Path) -> Path:
    return _state_dir(project_dir) / "migration-state.yaml"


def _collision_map_path(project_dir: Path) -> Path:
    return _state_dir(project_dir) / "taxonomy-collision-map.yaml"


def _backups_dir(project_dir: Path) -> Path:
    return _state_dir(project_dir) / "backups"


def _atomic_write_yaml(path: Path, data) -> None:
    content = yaml.safe_dump(data).encode("utf-8")
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=str(path.parent), suffix=".tmp", delete=False
    ) as f:
        f.write(content)
        tmp = f.name
    os.replace(tmp, str(path))


# ---------------------------------------------------------------------------
# Status / Priority / Workflow helpers
# ---------------------------------------------------------------------------

def remap_status(status: str) -> str:
    lower = status.lower()
    if lower in CANONICAL_STATUSES:
        return lower
    if lower in STATUS_REMAP:
        return STATUS_REMAP[lower]
    warnings.warn(f"Unknown status value: {status!r}", UserWarning, stacklevel=2)
    return lower


def remap_priority(priority: Optional[str]) -> Optional[str]:
    if priority is None or priority == "":
        return None
    lower = priority.lower()
    if lower in PRIORITY_REMAP:
        return PRIORITY_REMAP[lower]
    warnings.warn(f"Unknown priority value: {priority!r}", UserWarning, stacklevel=2)
    return priority


def infer_workflow_type(
    workflow_type: str = None,
    type_field: str = None,
    title: str = None,
) -> str:
    if workflow_type:
        return workflow_type
    if type_field:
        lower = type_field.lower()
        if lower in WORKFLOW_TYPE_MAP:
            return WORKFLOW_TYPE_MAP[lower]
        return lower
    if title:
        lower_title = title.lower()
        spike_keywords = {"spike", "research", "evaluate", "evaluation", "investigation", "investigate"}
        bug_keywords = {"fix", "bug"}
        first_word = lower_title.split(":")[0].split()[0] if lower_title.split() else ""
        if first_word in spike_keywords or any(k in lower_title for k in spike_keywords):
            return "spike"
        if any(k in lower_title for k in bug_keywords):
            return "bug-fix"
    return "enhancement"


# ---------------------------------------------------------------------------
# File parsing
# ---------------------------------------------------------------------------

_DEPENDS_ON_SENTINELS = {"none", "n/a", "", "-", "null"}


_DEPENDS_ON_ID_RE = re.compile(
    r"^((?:BL|STORY|ISSUE|EP|MS|spike-BL|CHORE|BUG|DEBT)-\d+)"
)


def _extract_id(raw: str) -> str | None:
    bare = re.sub(r"\s*\(.*?\)\s*$", "", raw).strip()
    if not bare or bare.lower() in _DEPENDS_ON_SENTINELS:
        return None
    m = _DEPENDS_ON_ID_RE.match(bare)
    if m:
        return m.group(1)
    if bare.lower() not in _DEPENDS_ON_SENTINELS:
        bare_no_trail = re.sub(r"\s*\(.*", "", raw).strip()
        m2 = _DEPENDS_ON_ID_RE.match(bare_no_trail)
        if m2:
            return m2.group(1)
    return None


def _normalize_depends_on(value):
    if value is None:
        return None
    if isinstance(value, str):
        if value.strip().lower() in _DEPENDS_ON_SENTINELS:
            return None
        parts = [p.strip() for p in value.split(",")]
        cleaned = []
        for part in parts:
            extracted = _extract_id(part)
            if extracted:
                cleaned.append(extracted)
        return cleaned if cleaned else None
    if isinstance(value, list):
        cleaned = []
        for item in value:
            extracted = _extract_id(str(item).strip())
            if extracted:
                cleaned.append(extracted)
        return cleaned if cleaned else None
    return None


def parse_file(path) -> dict:
    p = Path(path)
    raw_bytes = p.read_bytes()
    raw_text = raw_bytes.decode("utf-8", errors="replace")
    source_hash = hashlib.sha256(raw_bytes).hexdigest()

    result = {
        "source_hash": source_hash,
        "body": "",
        "status": None,
        "priority": None,
        "title": None,
        "id": None,
        "depends_on": None,
        "promoted_to": None,
        "closed_date": None,
        "deferred_reason": None,
    }

    yaml_data = None
    body_text = raw_text

    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            fm_str = parts[1]
            body_text = parts[2].strip()
            if fm_str.strip():
                try:
                    yaml_data = yaml.safe_load(fm_str)
                    if not isinstance(yaml_data, dict) or not yaml_data:
                        yaml_data = None
                except yaml.YAMLError:
                    warnings.warn(
                        f"YAML parse error in {p.name}, falling back to bold parsing",
                        UserWarning,
                        stacklevel=2,
                    )
                    yaml_data = None
                    body_text = raw_text

    if yaml_data:
        for k, v in yaml_data.items():
            result[k] = v

        if result.get("status") is not None:
            result["status"] = str(result["status"]).lower()

        result["body"] = body_text
    else:
        parsed = _parse_bold_format(raw_text if yaml_data is None and not raw_text.startswith("---") else body_text)
        if not parsed and raw_text.startswith("---"):
            parsed = _parse_bold_format(raw_text)

        for k, v in parsed.items():
            result[k] = v

        if result.get("status") is not None:
            raw_status = str(result["status"]).lower()
            em_dash_match = re.match(r"^(\w+)\s*[—–-]+\s*(\S.*)$", raw_status)
            if em_dash_match:
                status_part = em_dash_match.group(1)
                extra_part = em_dash_match.group(2).strip()
                result["status"] = status_part
                date_match = re.match(r"^\d{4}-\d{2}-\d{2}$", extra_part)
                if date_match:
                    result["closed_date"] = extra_part
                else:
                    result["deferred_reason"] = extra_part
            else:
                result["status"] = raw_status

        if result.get("priority") is not None:
            p_lower = str(result["priority"]).lower()
            if re.match(r"^p[0-4]$", p_lower):
                result["priority"] = p_lower.upper()
            else:
                result["priority"] = p_lower

    if result.get("status") is None and result.get("id") is None and yaml_data is None:
        if result.get("title") is None:
            heading_match = re.search(r"^#\s+(?:\S+-\d+:\s+)?(.+)$", raw_text, re.MULTILINE)
            if heading_match:
                result["title"] = heading_match.group(1).strip()
        warnings.warn(
            f"No metadata found in {p.name}",
            UserWarning,
            stacklevel=2,
        )

    result["depends_on"] = _normalize_depends_on(result.get("depends_on"))

    return result


def _parse_bold_format(text: str) -> dict:
    result = {}
    lines = text.split("\n")

    title = None
    for line in lines:
        h1 = re.match(r"^#\s+(?:[A-Za-z]+-\d+[a-z]*:\s+)?(.+)$", line)
        if h1:
            title = h1.group(1).strip()
            break

    if title:
        result["title"] = title

    in_code_block = False
    meta_found = False
    blank_lines_since_last_meta = 0
    body_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block

        if in_code_block:
            body_lines.append(line)
            continue

        if stripped.startswith("#"):
            body_lines.append(line)
            continue

        if stripped == "":
            if meta_found:
                blank_lines_since_last_meta += 1
            body_lines.append(line)
            continue

        bold_match = re.match(r"^\*\*([^*:]+):\*\*\s*(.*)$", stripped)
        if bold_match and blank_lines_since_last_meta == 0:
            key_raw = bold_match.group(1).strip()
            value = bold_match.group(2).strip()
            key = key_raw.lower().replace(" ", "_").replace("-", "_")
            result[key] = value
            meta_found = True
            blank_lines_since_last_meta = 0
            body_lines.append(line)
            continue

        if meta_found and blank_lines_since_last_meta > 0:
            body_lines.append(line)
        elif not meta_found:
            body_lines.append(line)
        else:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    result["body"] = body

    raw_status = result.get("status", "")
    if raw_status:
        em_match = re.match(r"^(.+?)\s*[—–]\s*(.+)$", raw_status)
        if em_match:
            result["status"] = em_match.group(1).strip()
            extra = em_match.group(2).strip()
            if re.match(r"^\d{4}-\d{2}-\d{2}$", extra):
                result["closed_date"] = extra
            else:
                result["deferred_reason"] = extra

    if "promoted_to" in result:
        result["promoted_to"] = result["promoted_to"]
    elif result.get("status", "").lower() == "promoted":
        result["promoted_to"] = None

    return result


# ---------------------------------------------------------------------------
# Source scanning
# ---------------------------------------------------------------------------

def scan_sources(project_dir: str) -> List[SourceFile]:
    pd = Path(project_dir)
    product_base = _get_product_base(pd)
    sources = []

    for rel_dir, entity_type, prefix_regex in SOURCE_SPECS:
        scan_path = product_base / rel_dir
        if not scan_path.exists():
            continue
        for f in scan_path.iterdir():
            if not f.is_file():
                continue
            if not f.name.endswith(".md"):
                continue
            m = re.match(prefix_regex, f.name)
            if not m:
                continue
            raw_id = m.group(1)
            sources.append(SourceFile(path=f, entity_type=entity_type, raw_id=raw_id))

    return sources


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------

def detect_collisions(project_dir: str, persist: bool = False) -> dict:
    pd = Path(project_dir)
    product_base = _get_product_base(pd)

    bl_dir = product_base / "backlog"
    done_dir = product_base / "backlog" / "done"

    bl_numbers = set()
    if bl_dir.exists():
        for f in bl_dir.iterdir():
            if not f.is_file():
                continue
            m = re.match(r"^BL-(\d+)(?:-|\.md$)", f.name)
            if m:
                bl_numbers.add(int(m.group(1)))

    story_numbers = {}
    if done_dir.exists():
        for f in done_dir.iterdir():
            if not f.is_file():
                continue
            m = re.match(r"^STORY-(\d+)(?:-|\.md$)", f.name)
            if m:
                n = int(m.group(1))
                if n in story_numbers:
                    raise ValueError(
                        f"Duplicate STORY number {n}: found both "
                        f"{story_numbers[n].name} and {f.name}"
                    )
                story_numbers[n] = f

    collision_map = {}
    if bl_numbers and story_numbers:
        max_bl = max(bl_numbers)
        len_bl = len(bl_numbers)
        if len_bl < max_bl:
            next_available = max_bl + len_bl
        else:
            next_available = max_bl + 1
        for n in sorted(story_numbers.keys()):
            if n in bl_numbers:
                collision_map[f"STORY-{n}"] = f"ISSUE-{next_available}"
                next_available += 1

    if persist:
        state = _state_dir(pd)
        state.mkdir(parents=True, exist_ok=True)
        _atomic_write_yaml(_collision_map_path(pd), collision_map)

    return collision_map


def load_collision_map(project_dir: str) -> Optional[dict]:
    pd = Path(project_dir)
    cmp = _collision_map_path(pd)
    if not cmp.exists():
        return None
    raw = cmp.read_bytes()
    if not raw.strip():
        return None
    try:
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            return None
        return data
    except yaml.YAMLError:
        warnings.warn(
            f"Could not parse collision map at {cmp}",
            UserWarning,
            stacklevel=2,
        )
        return None


# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------

def _make_slug(title: str, new_id: str, max_len: int = 60) -> str:
    if not title:
        return new_id.lower()
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", " ", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    if not slug:
        return new_id.lower()
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    if not slug:
        return new_id.lower()
    return slug


# ---------------------------------------------------------------------------
# Ref rewriting
# ---------------------------------------------------------------------------

def _build_id_map(sources: List[SourceFile], collision_map: dict) -> dict:
    id_map = {}
    for src in sources:
        if src.entity_type == "BL":
            old_id = f"BL-{src.raw_id}"
            padded = f"{int(src.raw_id):03d}"
            new_id = f"ISSUE-{padded}"
            id_map[old_id] = new_id
            id_map[f"BL-{int(src.raw_id)}"] = new_id
        elif src.entity_type == "STORY":
            n = int(src.raw_id)
            ckey = f"STORY-{n}"
            if ckey in collision_map:
                new_id_for_body = collision_map[ckey]
            else:
                new_id_for_body = f"ISSUE-{n:03d}"
            id_map[f"STORY-{src.raw_id}"] = new_id_for_body
            id_map[ckey] = new_id_for_body
        elif src.entity_type == "spike-BL":
            pass
        elif src.entity_type == "EP":
            old_id = f"EP-{src.raw_id}"
            id_map[old_id] = f"EP-{int(src.raw_id):03d}"
        elif src.entity_type == "MS":
            old_id = f"MS-{src.raw_id}"
            id_map[old_id] = f"MS-{int(src.raw_id):03d}"
        elif src.entity_type == "RM":
            old_id = f"RM-{src.raw_id}"
            id_map[old_id] = f"RM-{int(src.raw_id):03d}"

    return id_map


def _rewrite_refs_in_text(text: str, id_map: dict) -> Tuple[str, List[str]]:
    unknown_refs = []
    result = text

    all_legacy = re.findall(r"\b(BL-\d+|STORY-\d+)\b", text)

    for ref in sorted(set(all_legacy), key=lambda x: -len(x)):
        canonical_key = None
        m = re.match(r"^(BL|STORY)-(\d+)$", ref)
        if m:
            prefix = m.group(1)
            num_str = m.group(2)
            n = int(num_str)
            candidate_keys = [
                f"{prefix}-{num_str}",
                f"{prefix}-{n}",
            ]
            for k in candidate_keys:
                if k in id_map:
                    canonical_key = k
                    break

        if canonical_key:
            new_ref = id_map[canonical_key]
            result = re.sub(r"\b" + re.escape(ref) + r"\b", new_ref, result)
        else:
            unknown_refs.append(ref)
            warnings.warn(
                f"Reference {ref} not found in id_map — leaving as-is",
                UserWarning,
                stacklevel=3,
            )

    all_other_ids = re.findall(r"\b([A-Z][A-Z0-9]*-\d+)\b", text)
    legacy_prefixes_checked = {"BL", "STORY", "spike", "ISSUE", "EP", "MS", "RM"}
    for ref in set(all_other_ids):
        prefix_m = re.match(r"^([A-Za-z][A-Za-z0-9]*)-", ref)
        if prefix_m:
            prefix = prefix_m.group(1)
            if prefix not in legacy_prefixes_checked and ref not in id_map:
                warnings.warn(
                    f"Reference {ref} not found in id_map — leaving as-is",
                    UserWarning,
                    stacklevel=3,
                )
                unknown_refs.append(ref)

    return result, unknown_refs


# ---------------------------------------------------------------------------
# Plan building
# ---------------------------------------------------------------------------

def build_plan(project_dir: str, skip_conflicting: bool = False) -> MigrationPlan:
    pd = Path(project_dir)
    product_base = _get_product_base(pd)

    sources = scan_sources(project_dir)

    existing_map = load_collision_map(project_dir)
    if existing_map is not None and existing_map.get("locked"):
        collision_map = {k: v for k, v in existing_map.items() if k != "locked"}
        bl_count = sum(1 for s in sources if s.entity_type == "BL")
        story_count = sum(1 for s in sources if s.entity_type == "STORY")
        warnings.warn(
            f"Using locked collision map. Current source count may be reduced "
            f"(BL: {bl_count}, STORY: {story_count})",
            UserWarning,
            stacklevel=2,
        )
    elif existing_map is not None and not existing_map.get("locked"):
        collision_map = {k: v for k, v in existing_map.items() if k != "locked"}
    else:
        collision_map = detect_collisions(project_dir, persist=True)

    id_map = _build_id_map(sources, collision_map)

    restructure_moves = []
    migrate_archive_retire_moves = []

    spike_archive_map = {}
    spike_parsed_cache = {}
    archive_dir = product_base / "archive" / "spikes"
    for src in sources:
        if src.entity_type == "spike-BL":
            n = int(src.raw_id)
            parsed = parse_file(str(src.path))
            spike_parsed_cache[str(src.path)] = parsed
            slug = _make_slug(parsed.get("title", ""), f"spike-{n:03d}")
            archive_rel = archive_dir.relative_to(pd) / f"spike-{n:03d}-{slug}.md"
            archive_path = str(archive_rel)
            old_id = f"spike-BL-{src.raw_id}"
            spike_archive_map[old_id] = archive_path
            spike_archive_map[f"spike-BL-{n}"] = archive_path

    for src in sources:
        entity_type = src.entity_type
        raw_id = src.raw_id
        n = int(raw_id)

        if entity_type == "spike-BL":
            parsed = spike_parsed_cache[str(src.path)]
        else:
            parsed = parse_file(str(src.path))

        if entity_type == "BL":
            padded = f"{n:03d}"
            new_id = f"ISSUE-{padded}"
            status_raw = parsed.get("status") or "new"
            status = remap_status(status_raw)
            priority_raw = parsed.get("priority")
            priority = remap_priority(priority_raw) if priority_raw else None

            fm = _build_issue_frontmatter(parsed, new_id, f"BL-{raw_id}", status, priority, id_map, collision_map, spike_archive_map)
            body = parsed.get("body", "")

            if status in TERMINAL_STATUSES or status_raw.lower() in ("done", "complete", "achieved", "closed", "cancelled", "canceled", "abandoned", "superseded", "promoted"):
                dest_dir = product_base / "roadmap" / "issues" / "done"
            elif parsed.get("epic") or parsed.get("milestone"):
                dest_dir = product_base / "roadmap" / "issues"
            else:
                dest_dir = product_base / "backlog"

            slug = _make_slug(parsed.get("title", ""), new_id)
            dest = dest_dir / f"{new_id}-{slug}.md"
            source_rel = src.path.relative_to(pd) if src.path.is_relative_to(pd) else src.path

            supersedes_path = None
            if dest_dir.exists():
                for existing in dest_dir.iterdir():
                    if existing.is_file() and re.match(rf"^{re.escape(new_id)}-", existing.name):
                        supersedes_path = existing.relative_to(pd) if existing.is_relative_to(pd) else existing
                        break

            if skip_conflicting and supersedes_path:
                continue

            move = PlannedMove(
                source=source_rel,
                dest=dest.relative_to(pd),
                new_id=new_id,
                action="migrate",
                frontmatter=fm,
                body=body,
                source_hash=parsed["source_hash"],
                supersedes=supersedes_path,
            )
            migrate_archive_retire_moves.append(move)

        elif entity_type == "STORY":
            ckey = f"STORY-{n}"
            if ckey in collision_map:
                new_id = collision_map[ckey]
            else:
                padded = f"{n:03d}"
                new_id = f"ISSUE-{padded}"

            status_raw = parsed.get("status") or "done"
            status = remap_status(status_raw)
            priority_raw = parsed.get("priority")
            priority = remap_priority(priority_raw) if priority_raw else None

            fm = _build_issue_frontmatter(parsed, new_id, f"STORY-{n}", status, priority, id_map, collision_map, spike_archive_map)
            fm["migrated_from"] = ckey
            body = parsed.get("body", "")

            dest_dir = product_base / "roadmap" / "issues" / "done"
            slug = _make_slug(parsed.get("title", ""), new_id)
            dest = dest_dir / f"{new_id}-{slug}.md"
            source_rel = src.path.relative_to(pd) if src.path.is_relative_to(pd) else src.path

            supersedes_path = None
            if dest_dir.exists():
                for existing in dest_dir.iterdir():
                    if existing.is_file() and re.match(rf"^{re.escape(new_id)}-", existing.name):
                        supersedes_path = existing.relative_to(pd) if existing.is_relative_to(pd) else existing
                        break

            if skip_conflicting and supersedes_path:
                continue

            move = PlannedMove(
                source=source_rel,
                dest=dest.relative_to(pd),
                new_id=new_id,
                action="migrate",
                frontmatter=fm,
                body=body,
                source_hash=parsed["source_hash"],
                supersedes=supersedes_path,
            )
            migrate_archive_retire_moves.append(move)

        elif entity_type == "spike-BL":
            old_id = f"spike-BL-{raw_id}"
            archive_path = spike_archive_map.get(old_id, spike_archive_map.get(f"spike-BL-{n}"))
            source_rel = src.path.relative_to(pd) if src.path.is_relative_to(pd) else src.path

            move = PlannedMove(
                source=source_rel,
                dest=Path(archive_path),
                new_id=old_id,
                action="spike_archive",
                frontmatter={},
                body=parsed.get("body", ""),
                source_hash=parsed["source_hash"],
            )
            migrate_archive_retire_moves.append(move)

        elif entity_type == "I":
            dest_dir = product_base / "backlog" / "archived"
            dest = dest_dir / src.path.name
            source_rel = src.path.relative_to(pd) if src.path.is_relative_to(pd) else src.path

            move = PlannedMove(
                source=source_rel,
                dest=dest.relative_to(pd),
                new_id=src.path.stem,
                action="archive",
                frontmatter={},
                body="",
                source_hash=parsed["source_hash"],
            )
            migrate_archive_retire_moves.append(move)

        elif entity_type == "RM":
            source_rel = src.path.relative_to(pd) if src.path.is_relative_to(pd) else src.path
            move = PlannedMove(
                source=source_rel,
                dest=source_rel,
                new_id=f"RM-{raw_id}",
                action="retire",
                frontmatter={},
                body="",
                source_hash=parsed["source_hash"],
            )
            migrate_archive_retire_moves.append(move)

        elif entity_type == "MS":
            padded = f"{n:03d}"
            new_id = f"MS-{padded}"
            status_raw = parsed.get("status") or "new"
            status = remap_status(status_raw)
            priority_raw = parsed.get("priority")
            priority = remap_priority(priority_raw) if priority_raw else None

            fm = {}
            fm["id"] = new_id
            title = parsed.get("title") or ""
            fm["title"] = title
            fm["type"] = "milestone"
            fm["status"] = status
            if priority:
                fm["priority"] = priority
            fm["migrated_from"] = f"MS-{raw_id}"
            _copy_extra_fields(parsed, fm)
            if parsed.get("created"):
                fm["created"] = parsed["created"]
            else:
                fm["created"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

            body = parsed.get("body", "")
            dest_dir = product_base / "roadmap" / "milestones"
            slug = _make_slug(title, new_id)
            dest = dest_dir / f"{new_id}-{slug}.md"
            source_rel = src.path.relative_to(pd) if src.path.is_relative_to(pd) else src.path

            move = PlannedMove(
                source=source_rel,
                dest=dest.relative_to(pd),
                new_id=new_id,
                action="restructure",
                frontmatter=fm,
                body=body,
                source_hash=parsed["source_hash"],
            )
            restructure_moves.append(move)

            all_possible_refs = re.findall(r"\b([A-Z][A-Z0-9]*-\d+|spike-BL-\d+|BL-\d+|STORY-\d+)\b", body)
            if all_possible_refs:
                new_body, _ = _rewrite_refs_in_text(body, id_map)
                rewrite_move = PlannedMove(
                    source=source_rel,
                    dest=dest.relative_to(pd),
                    new_id=new_id,
                    action="rewrite-refs",
                    frontmatter=fm,
                    body=new_body,
                    source_hash=parsed["source_hash"],
                )
                restructure_moves.append(rewrite_move)

        elif entity_type == "EP":
            padded = f"{n:03d}"
            new_id = f"EP-{padded}"
            status_raw = parsed.get("status") or "active"
            status = remap_status(status_raw)

            fm = {}
            fm["id"] = new_id
            title = parsed.get("title") or ""
            fm["title"] = title
            fm["type"] = "epic"
            fm["status"] = status
            fm["migrated_from"] = f"EP-{raw_id}"
            _copy_extra_fields(parsed, fm)
            if parsed.get("created"):
                fm["created"] = parsed["created"]
            else:
                fm["created"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

            body = parsed.get("body", "")
            dest_dir = product_base / "roadmap" / "epics"
            slug = _make_slug(title, new_id)
            dest = dest_dir / f"{new_id}-{slug}.md"
            source_rel = src.path.relative_to(pd) if src.path.is_relative_to(pd) else src.path

            move = PlannedMove(
                source=source_rel,
                dest=dest.relative_to(pd),
                new_id=new_id,
                action="restructure",
                frontmatter=fm,
                body=body,
                source_hash=parsed["source_hash"],
            )
            restructure_moves.append(move)

            all_possible_refs_ep = re.findall(r"\b([A-Z][A-Z0-9]*-\d+|spike-BL-\d+|BL-\d+|STORY-\d+)\b", body)
            if all_possible_refs_ep:
                new_body, unknown = _rewrite_refs_in_text(body, id_map)
                rewrite_move = PlannedMove(
                    source=source_rel,
                    dest=dest.relative_to(pd),
                    new_id=new_id,
                    action="rewrite-refs",
                    frontmatter=fm,
                    body=new_body,
                    source_hash=parsed["source_hash"],
                )
                restructure_moves.append(rewrite_move)

    all_moves = migrate_archive_retire_moves + restructure_moves

    new_id_to_primary = {}
    for move in all_moves:
        if move.action in ("migrate", "restructure", "archive"):
            if move.new_id in new_id_to_primary:
                raise ValueError(
                    f"Duplicate new_id {move.new_id}: conflict between "
                    f"{new_id_to_primary[move.new_id].source} and {move.source}"
                )
            new_id_to_primary[move.new_id] = move

    dest_to_move = {}
    slug_dir_to_move = {}
    for move in all_moves:
        if move.action in ("migrate", "restructure", "archive", "spike_archive"):
            dest_key = str(move.dest)
            if dest_key in dest_to_move:
                existing = dest_to_move[dest_key]
                raise ValueError(
                    f"Duplicate dest path {move.dest}: "
                    f"{existing.new_id} and {move.new_id}"
                )
            dest_to_move[dest_key] = move

            dest_path = Path(str(move.dest))
            fname = dest_path.name
            parts = fname.split("-", 2)
            if len(parts) >= 3:
                slug_part = parts[2]
                slug_dir_key = (str(dest_path.parent), slug_part)
                if slug_dir_key in slug_dir_to_move:
                    existing = slug_dir_to_move[slug_dir_key]
                    raise ValueError(
                        f"Duplicate slug in same directory for "
                        f"{existing.new_id} and {move.new_id}: slug={slug_part}"
                    )
                slug_dir_to_move[slug_dir_key] = move

    return MigrationPlan(moves=all_moves, collision_map=collision_map)


_EXCLUDED_KEYS = {
    "id", "title", "status", "priority", "type", "epic", "milestone",
    "depends_on", "promoted_to", "closed_date", "deferred_reason",
    "body", "source_hash",
}


def _copy_extra_fields(parsed: dict, fm: dict):
    for k, v in parsed.items():
        if k not in _EXCLUDED_KEYS and k not in fm and v is not None:
            fm[k] = v


def _build_issue_frontmatter(
    parsed: dict,
    new_id: str,
    original_id: str,
    status: str,
    priority: Optional[str],
    id_map: dict,
    collision_map: dict,
    spike_archive_map: Optional[dict] = None,
) -> dict:
    fm = {}
    fm["id"] = new_id

    title = parsed.get("title") or ""
    fm["title"] = title
    fm["type"] = infer_workflow_type(
        workflow_type=parsed.get("workflow_type"),
        type_field=parsed.get("type"),
        title=title,
    )
    fm["status"] = status
    if priority:
        fm["priority"] = priority

    if parsed.get("epic"):
        fm["epic"] = parsed["epic"]
    if parsed.get("milestone"):
        fm["milestone"] = parsed["milestone"]

    depends_on = parsed.get("depends_on")
    if depends_on:
        new_deps = []
        for dep in depends_on:
            dep_str = str(dep).strip()
            if re.match(r"^spike-BL-\d+$", dep_str):
                continue
            m = re.match(r"^(BL|STORY)-(\d+)$", dep_str)
            if m:
                prefix = m.group(1)
                num_str = m.group(2)
                n = int(num_str)
                candidate_keys = [f"{prefix}-{num_str}", f"{prefix}-{n}"]
                found = None
                for k in candidate_keys:
                    if k in id_map:
                        found = id_map[k]
                        break
                if found:
                    _pad_m = re.match(r"^ISSUE-(\d+)$", found)
                    if _pad_m:
                        new_deps.append(f"ISSUE-{int(_pad_m.group(1)):03d}")
                    else:
                        new_deps.append(found)
                else:
                    new_deps.append(dep_str)
            else:
                new_deps.append(dep_str)
        fm["depends_on"] = new_deps if new_deps else None

    fm["migrated_from"] = original_id

    if parsed.get("closed_date"):
        fm["closed_date"] = parsed["closed_date"]

    raw_status_val = parsed.get("status") or ""
    if status == "superseded" or str(raw_status_val).lower() == "promoted":
        fm["status"] = "superseded"
        promoted_to = parsed.get("promoted_to")
        if promoted_to:
            bare_id_match = re.match(r"^([A-Z]+-\d+)", promoted_to)
            if bare_id_match:
                fm["superseded_by"] = bare_id_match.group(1)
            else:
                warnings.warn(
                    f"superseded_by value {promoted_to!r} could not be parsed to bare ID",
                    UserWarning,
                    stacklevel=4,
                )
                fm["superseded_by"] = promoted_to

    if spike_archive_map:
        num_match = re.match(r"ISSUE-(\d+)", new_id)
        if num_match:
            n = int(num_match.group(1))
            spike_key = f"spike-BL-{n}"
            if spike_key in spike_archive_map:
                fm["spike_report"] = spike_archive_map[spike_key]

    _copy_extra_fields(parsed, fm)

    if parsed.get("created"):
        fm["created"] = parsed["created"]
    else:
        fm["created"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return fm


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(project_dir: str, allow_overwrite: bool = False) -> list:
    pd = Path(project_dir)
    errors = []

    try:
        product_base = _get_product_base(pd)
    except ValueError as e:
        raise

    state_path = _migration_state_path(pd)
    if state_path.exists():
        try:
            state_data = yaml.safe_load(state_path.read_text())
            if isinstance(state_data, dict):
                status = state_data.get("status", "")
                if status == "failed":
                    errors.append(
                        "Previous migration failed. Please rollback before re-running."
                    )
                elif status == "in_progress":
                    errors.append(
                        "Migration already in progress. Resume or rollback."
                    )
        except yaml.YAMLError:
            errors.append(
                "migration-state.yaml is corrupt — rollback before re-running."
            )

    sources = scan_sources(str(pd))
    source_files = [s.path for s in sources]

    for src_file in source_files:
        try:
            resolved = src_file.resolve()
            if not str(resolved).startswith(str(pd.resolve())):
                errors.append(
                    f"Source path {src_file.name} escapes project root (outside)"
                )
        except OSError:
            errors.append(
                f"Source path {src_file.name} escapes project root"
            )

    if not source_files and not errors:
        errors.append("No source files found in project.")
        return errors

    if errors and any("previous migration failed" in str(e).lower() or "already in progress" in str(e).lower() for e in errors):
        return errors

    source_numbers = set()
    for src in sources:
        m = re.match(r"^(?:BL|STORY)-(\d+)", src.path.name)
        if m:
            source_numbers.add(int(m.group(1)))

    if not allow_overwrite:
        dest_dirs_to_check = [
            product_base / "roadmap" / "issues",
            product_base / "backlog",
        ]
        for dest_dir in dest_dirs_to_check:
            if not dest_dir.exists():
                continue
            for f in dest_dir.rglob("ISSUE-*.md") if dest_dir.name != "backlog" else (
                ff for ff in dest_dir.iterdir() if ff.is_file() and ff.name.startswith("ISSUE-")
            ):
                m = re.match(r"^ISSUE-(\d+)", f.name)
                if m:
                    n = int(m.group(1))
                    if n in source_numbers:
                        errors.append(
                            f"ISSUE-{n:03d} already exists at {f.parent.name}/{f.name}. "
                            f"Use overwrite to replace, or keep existing."
                        )

    return errors


# ---------------------------------------------------------------------------
# Snapshot / Rollback
# ---------------------------------------------------------------------------

def create_snapshot(project_dir: str, base_paths: list) -> Path:
    pd = Path(project_dir)
    backups = _backups_dir(pd)
    backups.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    snap_name = f"snap-{ts}.tar.gz"
    snap_path = backups / snap_name

    try:
        with tarfile.open(str(snap_path), "w:gz") as tf:
            for bp_str in base_paths:
                bp = Path(bp_str)
                if not bp.exists():
                    warnings.warn(
                        f"Skipping non-existent base_path: {bp.name}",
                        UserWarning,
                        stacklevel=2,
                    )
                    continue
                if bp.is_dir():
                    for f in bp.rglob("*"):
                        if f.is_file():
                            tf.add(str(f), arcname=str(f.relative_to(pd)))
                elif bp.is_file():
                    tf.add(str(bp), arcname=str(bp.relative_to(pd)))
    except Exception:
        if snap_path.exists():
            snap_path.unlink()
        raise

    _prune_snapshots(backups)

    return snap_path


def _prune_snapshots(backups_dir: Path, keep: int = MAX_SNAPSHOTS):
    snaps = sorted(backups_dir.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime)
    while len(snaps) > keep:
        snaps[0].unlink()
        snaps = snaps[1:]


def verify_snapshot(snapshot_path) -> bool:
    try:
        with tarfile.open(str(snapshot_path), "r:gz") as tf:
            names = tf.getnames()
            if not names:
                return False
        return True
    except Exception:
        return False


def _validate_tar_members(tf: tarfile.TarFile) -> None:
    for member in tf.getmembers():
        if member.name.startswith("/") or ".." in member.name.split("/"):
            raise ValueError(f"Unsafe tar member path: {member.name}")


def rollback(snapshot_path: str, project_dir: str = None) -> bool:
    if not verify_snapshot(snapshot_path):
        return False

    pd = Path(project_dir) if project_dir else Path(".")

    try:
        product_base = _get_product_base(pd)
    except (ValueError, FileNotFoundError):
        product_base = pd / ".sweetclaude" / "product"

    migration_dirs = [
        product_base / "roadmap" / "issues",
        product_base / "roadmap" / "epics",
        product_base / "roadmap" / "milestones",
        product_base / "backlog" / "archived",
        product_base / "archive" / "spikes",
    ]

    try:
        for d in migration_dirs:
            if d.exists():
                import shutil
                shutil.rmtree(d)

        for f in (product_base / "backlog").iterdir() if (product_base / "backlog").exists() else []:
            if f.is_file() and re.match(r"^ISSUE-\d+", f.name):
                f.unlink()

        state_path = _migration_state_path(pd)
        if state_path.exists():
            state_path.unlink()
        cmap = _collision_map_path(pd)
        if cmap.exists():
            cmap.unlink()

        with tarfile.open(str(snapshot_path), "r:gz") as tf:
            _validate_tar_members(tf)
            tf.extractall(str(pd))
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------

def execute(
    plan: MigrationPlan,
    project_dir: str,
    snapshot_path: str = None,
    dry_run: bool = False,
    overwrite_existing: bool = False,
) -> MigrationResult:
    pd = Path(project_dir)

    if dry_run:
        return MigrationResult()

    cmp = _collision_map_path(pd)
    if not cmp.exists():
        raise FileNotFoundError(
            "collision map not found — cannot execute without collision map"
        )

    cmap_data = load_collision_map(project_dir)
    if cmap_data is None:
        raise ValueError("collision map is invalid or empty")

    cmap_data["locked"] = True
    _state_dir(pd).mkdir(parents=True, exist_ok=True)
    _atomic_write_yaml(cmp, cmap_data)

    dest_set = set()
    for move in plan.moves:
        dest_full = pd / move.dest
        if not str(dest_full.resolve()).startswith(str(pd.resolve())):
            raise ValueError(
                f"Move dest {move.dest} is outside project root — "
                f"this plan was built for a different project"
            )
        dest_set.add(str(dest_full.resolve()))

    state_path = _migration_state_path(pd)
    completed_dests = set()
    if state_path.exists():
        try:
            sd = yaml.safe_load(state_path.read_text())
            if isinstance(sd, dict):
                completed_dests = set(sd.get("completed_dests", []))
        except yaml.YAMLError:
            pass

    result = MigrationResult()

    state_data = {
        "status": "in_progress",
        "completed_dests": list(completed_dests),
        "snapshot_path": snapshot_path or "",
    }
    _atomic_write_yaml(state_path, state_data)

    try:
        for move in plan.moves:
            dest_full = pd / move.dest

            if str(move.dest) in completed_dests:
                if move.action == "migrate":
                    result.migrated += 1
                elif move.action == "archive":
                    result.archived += 1
                elif move.action == "spike_archive":
                    result.spike_archived += 1
                elif move.action == "restructure":
                    result.restructured += 1
                elif move.action == "rewritten" or move.action == "rewrite-refs":
                    result.rewritten += 1
                continue

            src_full = pd / move.source

            if move.action == "retire":
                if src_full.exists():
                    src_full.unlink()
                result.retired += 1
                continue

            if move.action == "archive":
                if src_full.exists():
                    raw = src_full.read_bytes()
                    if move.source_hash:
                        actual_hash = hashlib.sha256(raw).hexdigest()
                        if actual_hash != move.source_hash:
                            state_data["status"] = "failed"
                            _atomic_write_yaml(state_path, state_data)
                            raise ValueError(
                                f"Source file {src_full.name} changed since plan was built"
                            )
                    dest_full.parent.mkdir(parents=True, exist_ok=True)
                    dest_full.write_bytes(raw)
                    src_full.unlink()
                    completed_dests.add(str(move.dest))
                    state_data["completed_dests"] = list(completed_dests)
                    _atomic_write_yaml(state_path, state_data)
                result.archived += 1
                continue

            if move.action == "spike_archive":
                if src_full.exists():
                    raw = src_full.read_bytes()
                    if move.source_hash:
                        actual_hash = hashlib.sha256(raw).hexdigest()
                        if actual_hash != move.source_hash:
                            state_data["status"] = "failed"
                            _atomic_write_yaml(state_path, state_data)
                            raise ValueError(
                                f"Source file {src_full.name} changed since plan was built"
                            )
                    dest_full.parent.mkdir(parents=True, exist_ok=True)
                    dest_full.write_bytes(raw)
                    src_full.unlink()
                    completed_dests.add(str(move.dest))
                    state_data["completed_dests"] = list(completed_dests)
                    _atomic_write_yaml(state_path, state_data)
                result.spike_archived += 1
                continue

            if move.action in ("migrate", "restructure", "rewrite-refs"):
                if move.action in ("migrate", "restructure"):
                    if src_full.exists():
                        raw = src_full.read_bytes()
                        actual_hash = hashlib.sha256(raw).hexdigest()
                        if actual_hash != move.source_hash:
                            state_data["status"] = "failed"
                            _atomic_write_yaml(state_path, state_data)
                            raise ValueError(
                                f"Source file {src_full.name} changed since plan was built"
                            )

                if move.supersedes and overwrite_existing:
                    old_file = pd / move.supersedes
                    if old_file.exists() and old_file.resolve() != dest_full.resolve():
                        old_file.unlink()

                dest_full.parent.mkdir(parents=True, exist_ok=True)

                if move.frontmatter:
                    fm_yaml = yaml.safe_dump(move.frontmatter, default_flow_style=False).strip()
                    body = move.body or ""
                    if body:
                        content = f"---\n{fm_yaml}\n---\n\n{body}\n"
                    else:
                        content = f"---\n{fm_yaml}\n---\n"
                else:
                    content = (move.body or "")

                dest_full.write_text(content)

                if move.action in ("migrate", "restructure"):
                    if src_full.exists():
                        src_full.unlink()

                completed_dests.add(str(move.dest))
                state_data["completed_dests"] = list(completed_dests)
                _atomic_write_yaml(state_path, state_data)

                if move.action == "migrate":
                    result.migrated += 1
                elif move.action == "restructure":
                    result.restructured += 1
                elif move.action == "rewrite-refs":
                    result.rewritten += 1

    except Exception:
        if state_data.get("status") != "failed":
            state_data["status"] = "failed"
            _atomic_write_yaml(state_path, state_data)
        raise

    state_data["status"] = "complete"
    state_data["completed_dests"] = list(completed_dests)
    state_data["expected_dest_count"] = (
        result.migrated + result.archived + result.restructured + result.spike_archived
    )
    _atomic_write_yaml(state_path, state_data)

    return result


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

def verify(project_dir: str) -> list:
    pd = Path(project_dir)
    errors = []

    try:
        product_base = _get_product_base(pd)
    except ValueError as e:
        return [str(e)]

    required_fields = ["id", "title", "type", "status", "created"]

    dest_dirs = [
        product_base / "roadmap" / "issues",
        product_base / "roadmap" / "epics",
        product_base / "roadmap" / "milestones",
        product_base / "backlog",
        product_base / "backlog" / "archived",
    ]

    known_ids = {}
    all_dest_files = []

    for dest_dir in dest_dirs:
        if not dest_dir.exists():
            continue
        for f in dest_dir.rglob("*.md"):
            if not f.is_file():
                continue
            if re.match(r"^(ISSUE|EP|MS)-", f.name):
                all_dest_files.append(f)

    for f in all_dest_files:
        parsed = _parse_dest_file(f)
        file_id = parsed.get("id")
        if not file_id:
            m = re.match(r"^((?:ISSUE|EP|MS)-\d+)", f.name)
            if m:
                file_id = m.group(1)

        if file_id:
            if file_id in known_ids:
                errors.append(
                    f"Duplicate ID {file_id}: found in {known_ids[file_id]} and {f}"
                )
            else:
                known_ids[file_id] = f

    for f in all_dest_files:
        parsed = _parse_dest_file(f)
        file_id = parsed.get("id")
        if not file_id:
            m = re.match(r"^((?:ISSUE|EP|MS)-\d+)", f.name)
            if m:
                file_id = m.group(1)

        if not file_id:
            continue

        for req in required_fields:
            val = parsed.get(req)
            if val is None or val == "":
                errors.append(
                    f"{file_id} missing required field: {req}"
                )

        fname_prefix_m = re.match(r"^((?:ISSUE|EP|MS)-\d+)", f.name)
        if fname_prefix_m:
            fname_id_str = fname_prefix_m.group(1)
            if file_id and file_id != fname_id_str:
                errors.append(
                    f"{fname_id_str} frontmatter id mismatch: "
                    f"filename has {fname_id_str} but frontmatter has {file_id}"
                )

        priority = parsed.get("priority")
        if priority and priority not in STANDARD_PRIORITIES:
            warnings.warn(
                f"{file_id} has non-standard priority value: {priority!r}",
                UserWarning,
                stacklevel=2,
            )

        depends_on = parsed.get("depends_on") or []
        if isinstance(depends_on, str):
            depends_on = [depends_on]
        for dep in depends_on:
            if re.match(r"^(BL|STORY|spike-BL)-\d+", dep):
                errors.append(
                    f"{file_id} has legacy reference in depends_on: {dep}"
                )
            elif dep not in known_ids:
                errors.append(
                    f"{file_id} depends_on unresolved reference: {dep}"
                )

        epic = parsed.get("epic")
        if epic and epic not in known_ids:
            errors.append(f"{file_id} epic reference not found: {epic}")

        milestone = parsed.get("milestone")
        if milestone and milestone not in known_ids:
            errors.append(f"{file_id} milestone reference not found: {milestone}")

        superseded_by = parsed.get("superseded_by")
        if superseded_by and superseded_by not in known_ids:
            errors.append(
                f"{file_id} superseded_by reference not found: {superseded_by}"
            )

    legacy_prefixes_re = re.compile(r"^(BL|STORY|EP|RM|CHORE|BUG|DEBT|spike-BL)-\d+")
    legacy_scan_dirs = [
        product_base / "backlog",
        product_base / "backlog" / "done",
        product_base / "backlog" / "spike-reports",
        product_base / "roadmap",
    ]
    archived_dir = product_base / "backlog" / "archived"
    new_dest_dirs = [
        product_base / "roadmap" / "issues",
        product_base / "roadmap" / "epics",
        product_base / "roadmap" / "milestones",
    ]

    for scan_dir in legacy_scan_dirs:
        if not scan_dir.exists():
            continue
        for f in scan_dir.rglob("*.md"):
            if not f.is_file():
                continue
            try:
                if archived_dir.exists() and f.is_relative_to(archived_dir):
                    continue
                skip = False
                for nd in new_dest_dirs:
                    if nd.exists() and f.is_relative_to(nd):
                        skip = True
                        break
                if skip:
                    continue
            except Exception:
                if str(f).startswith(str(archived_dir)):
                    continue
                skip = any(str(f).startswith(str(nd)) for nd in new_dest_dirs)
                if skip:
                    continue
            if legacy_prefixes_re.match(f.name):
                stem = f.stem
                errors.append(
                    f"Legacy file still present: {stem}"
                )

    issues_dir = product_base / "issues"
    if issues_dir.exists():
        for f in issues_dir.rglob("*.md"):
            if f.is_file():
                errors.append(
                    f"issues/ directory is not empty after archival — found {f.name}"
                )
                break

    state_path = _migration_state_path(pd)
    if state_path.exists():
        try:
            sd = yaml.safe_load(state_path.read_text())
            if isinstance(sd, dict) and "expected_dest_count" in sd:
                expected = sd["expected_dest_count"]
                if expected == 0:
                    warnings.warn(
                        "zero migrated files expected — corpus may be all-retire",
                        UserWarning,
                        stacklevel=2,
                    )
                    return errors

                actual_count = len(all_dest_files)
                archived_count = 0
                if archived_dir.exists():
                    for f in archived_dir.rglob("*.md"):
                        if f.is_file():
                            archived_count += 1

                spike_archive_dir = product_base / "archive" / "spikes"
                spike_archive_count = 0
                if spike_archive_dir.exists():
                    for f in spike_archive_dir.iterdir():
                        if f.is_file() and f.suffix == ".md":
                            spike_archive_count += 1

                total_count = actual_count + archived_count + spike_archive_count

                if total_count != expected:
                    errors.append(
                        f"File count mismatch: expected {expected}, found {total_count}"
                    )
        except yaml.YAMLError:
            pass

    return errors


def _parse_dest_file(path: Path) -> dict:
    raw_bytes = path.read_bytes()
    raw_text = raw_bytes.decode("utf-8", errors="replace")

    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            fm_str = parts[1]
            if fm_str.strip():
                try:
                    data = yaml.safe_load(fm_str)
                    if isinstance(data, dict):
                        return data
                except yaml.YAMLError:
                    pass

    return {}
