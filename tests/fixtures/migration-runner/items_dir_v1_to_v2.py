# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Fixture directory-migration handler used by tests/test-migration-runner.sh.

This is NOT a production handler. It simulates a backlog-like artifact
migration to exercise the runner's directory-entry code path.

v1 layout:
    <dir>/ITEM-001-some-slug.md      # frontmatter has type: story|bug
    <dir>/ITEM-002-other-slug.md
    ...

v2 layout:
    <dir>/<type>/THING-NNN-<slug>.md     # NNN renumbered per-type starting at 001
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

FROM_VERSION = 1
TO_VERSION = 2

_ITEM_RE = re.compile(r"^ITEM-(\d+)-(.+)\.md$")
_THING_RE = re.compile(r"^THING-(\d+)-(.+)\.md$")


def detect_version(directory: Path) -> int | None:
    """Pattern inference. Returns 1 if v1 layout, 2 if v2 layout, None if neither."""
    if not directory.exists():
        return None
    # v2: any subdir contains a THING-*.md
    for sub in directory.iterdir():
        if sub.is_dir():
            for f in sub.glob("THING-*.md"):
                if _THING_RE.match(f.name):
                    return 2
    # v1: ITEM-*.md at top level
    for f in directory.glob("ITEM-*.md"):
        if _ITEM_RE.match(f.name):
            return 1
    return None


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Naive YAML frontmatter parser. Returns (fm_dict, body)."""
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    import yaml
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, parts[2]


def up(directory: Path, params: dict | None = None) -> dict:
    """Migrate ITEM-NNN.md files to <type>/THING-NNN.md layout."""
    params = params or {}
    sources = sorted(directory.glob("ITEM-*.md"))
    counters: dict[str, int] = {}
    mapping: list[dict] = []
    warnings: list[str] = []

    for src in sources:
        m = _ITEM_RE.match(src.name)
        if not m:
            continue
        old_id = f"ITEM-{m.group(1)}"
        slug = m.group(2)
        content = src.read_text()
        fm, body = _parse_frontmatter(content)
        item_type = fm.get("type") or "story"
        if item_type not in {"story", "bug", "chore"}:
            warnings.append(f"{src.name}: unknown type {item_type!r}, defaulting to story")
            item_type = "story"
        counters[item_type] = counters.get(item_type, 0) + 1
        new_id = f"THING-{counters[item_type]:03d}"
        title = fm.get("title", "")
        dst_dir = directory / item_type
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"{new_id}-{slug}.md"
        # Rewrite frontmatter id/type stay consistent.
        fm["id"] = new_id
        fm["type"] = item_type
        import yaml
        new_content = f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---{body}"
        dst.write_text(new_content)
        src.unlink()
        mapping.append({
            "v_from_id": old_id,
            "v_to_id": new_id,
            "title": title,
            "type": item_type,
        })

    return {
        "mapping": mapping,
        "warnings": warnings,
        "files_in": len(sources),
        "files_out": len(mapping),
    }


def down(directory: Path, params: dict | None = None) -> dict:
    """Reverse: flatten <type>/THING-NNN.md back to ITEM-NNN.md at top level.

    Loses per-type counter info (THING-001 in two types collapses; the fixture
    re-numbers ITEM-* sequentially in the order they're encountered).
    """
    params = params or {}
    mapping: list[dict] = []
    warnings: list[str] = []
    counter = 0
    for type_dir in sorted(directory.iterdir()):
        if not type_dir.is_dir():
            continue
        for src in sorted(type_dir.glob("THING-*.md")):
            m = _THING_RE.match(src.name)
            if not m:
                continue
            counter += 1
            slug = m.group(2)
            content = src.read_text()
            fm, body = _parse_frontmatter(content)
            new_id = f"ITEM-{counter:03d}"
            fm["id"] = new_id
            import yaml
            new_content = f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---{body}"
            dst = directory / f"{new_id}-{slug}.md"
            dst.write_text(new_content)
            src.unlink()
            mapping.append({
                "v_from_id": src.stem.split("-")[0] + "-" + src.stem.split("-")[1],
                "v_to_id": new_id,
                "title": fm.get("title", ""),
                "type": fm.get("type", ""),
            })
        # Clean up empty type dirs.
        try:
            type_dir.rmdir()
        except OSError:
            pass
    return {"mapping": mapping, "warnings": warnings, "files_in": counter, "files_out": counter}
