# SPDX-License-Identifier: AGPL-3.0-or-later
"""
phase.yaml v1 → v2 migration handler.

Source rules: skills/update/project-migration.md Step 8e (the inline migration
that this handler replaces).

v1 fields → v2 destinations:
  phase            → active_work_item.phase (SHIP/DONE collapse to None)
  work_type        → active_work_item.type (via WORK_TYPE_MAP)
  deference_level  → deference_level (carry)
  project_type     → project_type (carry)
  safety_snapshot  → safety_snapshot (carry)
  init_step        → dropped

v2 schema additions:
  schema_version: 2
  version_stage   (taken from params; defaults to 'BETA' if absent)
  last_work_item_id: None
  active_work_item.{id, workflow, title, started, entry_category}: None / [] defaults

down() reverses where possible. version_stage and any v2-only fields are dropped
on down because v1 has no equivalent; preserving them on a future up() requires
a fresh up() invocation rather than a perfect inverse.
"""

from __future__ import annotations

FROM_VERSION = 1
TO_VERSION = 2
FILE_KEY = "phase.yaml"

WORK_TYPE_MAP = {
    "net-new": "net-new-feature",
    "bug-fix": "bug-fix",
    "enhancement": "enhancement",
    "refactor": "tech-debt",
    "security": "security-patch",
    "hotfix": "hotfix",
    "performance": "performance-optimization",
}


def _map_work_type(v1: str | None) -> str | None:
    if v1 is None:
        return None
    return WORK_TYPE_MAP.get(v1, None)


def _map_phase(v1: str | None) -> str | None:
    """SHIP and DONE are terminal in v1; v2 represents 'no active work' as None."""
    if v1 is None:
        return None
    if v1.upper() in ("SHIP", "DONE"):
        return None
    return v1


def up(data: dict, params: dict | None = None) -> dict:
    """Migrate v1 phase.yaml dict to v2.

    params:
        version_stage (optional): the version_stage to set on the v2 doc.
            Defaults to 'BETA'. Calling skill should pass the user's chosen
            value when interactive.
    """
    params = params or {}
    version_stage = params.get("version_stage", "BETA")

    return {
        "schema_version": 2,
        "version_stage": version_stage,
        "deference_level": data.get("deference_level", "collaborative"),
        "project_type": data.get("project_type", "existing-code"),
        "safety_snapshot": data.get("safety_snapshot", ""),
        "last_work_item_id": None,
        "active_work_item": {
            "id": None,
            "type": _map_work_type(data.get("work_type")),
            "workflow": [],
            "phase": _map_phase(data.get("phase")),
            "title": None,
            "started": None,
            "entry_category": None,
        },
    }


def down(data: dict, params: dict | None = None) -> dict:
    """Reverse v2 phase.yaml back to v1 shape.

    Lossy: drops version_stage, last_work_item_id, and the active_work_item
    subfields that v1 didn't have (id, workflow, title, started, entry_category).
    Preserves phase, work_type (reverse-mapped), and the three carry fields.
    """
    reverse_work_type = {v2: v1 for v1, v2 in WORK_TYPE_MAP.items()}
    awi = data.get("active_work_item") or {}

    return {
        "schema_version": 1,
        "phase": awi.get("phase"),
        "work_type": reverse_work_type.get(awi.get("type")),
        "deference_level": data.get("deference_level", "collaborative"),
        "project_type": data.get("project_type", "existing-code"),
        "safety_snapshot": data.get("safety_snapshot", ""),
    }
