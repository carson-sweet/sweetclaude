# SPDX-License-Identifier: AGPL-3.0-or-later
"""
skills.yaml v1 → v2 migration handler.

Source rules: identical algorithm currently inlined in three places —
  skills/update/project-migration.md     Step 8f
  skills/update/capability-surface.md    Step 7a (Step 1)
  skills/fix-sweetclaude/SKILL.md        Step 5b

Per-entry mapping:
  enabled: true                                  → status: active
                                                   last_changed_at: onboarded_at or today
                                                   last_changed_by: migrated
  enabled: false AND onboarded_at set            → status: paused
                                                   last_changed_at: offboarded_at or onboarded_at or today
                                                   last_changed_by: migrated
  enabled: false AND onboarded_at: ~ (or missing)→ status: uninitialized
                                                   last_changed_at: None
                                                   last_changed_by: None

Drop onboarded_at and offboarded_at. Set schema_version: 2 at top level.
"""

from __future__ import annotations

from datetime import date

FROM_VERSION = 1
TO_VERSION = 2
FILE_KEY = "skills.yaml"


def _today() -> str:
    return date.today().isoformat()


def up(data: dict, params: dict | None = None) -> dict:
    """Migrate v1 skills.yaml dict to v2.

    params:
        today (optional): override 'today' for deterministic testing.
            Defaults to date.today().isoformat().
    """
    params = params or {}
    today = params.get("today") or _today()

    out: dict = {"schema_version": 2}

    for key, value in data.items():
        if key == "schema_version":
            continue
        if not isinstance(value, dict):
            # Pass through non-dict top-level values unchanged (rare/unexpected).
            out[key] = value
            continue

        enabled = value.get("enabled")
        onboarded_at = value.get("onboarded_at")
        offboarded_at = value.get("offboarded_at")

        if enabled is True:
            entry = {
                "status": "active",
                "last_changed_at": onboarded_at or today,
                "last_changed_by": "migrated",
            }
        elif enabled is False and onboarded_at is not None:
            entry = {
                "status": "paused",
                "last_changed_at": offboarded_at or onboarded_at or today,
                "last_changed_by": "migrated",
            }
        else:
            entry = {
                "status": "uninitialized",
                "last_changed_at": None,
                "last_changed_by": None,
            }

        # Preserve any unrelated keys on the entry (e.g. project-specific notes).
        preserved = {
            k: v
            for k, v in value.items()
            if k not in {"enabled", "onboarded_at", "offboarded_at"}
        }
        entry.update(preserved)
        out[key] = entry

    return out


def down(data: dict, params: dict | None = None) -> dict:
    """Reverse v2 skills.yaml back to v1 shape.

    Lossy: last_changed_at and last_changed_by are dropped. The three v2 statuses
    collapse back to:
      active        → enabled: true,  onboarded_at = last_changed_at
      paused        → enabled: false, onboarded_at = last_changed_at
      uninitialized → enabled: false, onboarded_at: None
    """
    out: dict = {"schema_version": 1}

    for key, value in data.items():
        if key == "schema_version":
            continue
        if not isinstance(value, dict):
            out[key] = value
            continue

        status = value.get("status")
        last_changed_at = value.get("last_changed_at")

        if status == "active":
            entry = {"enabled": True, "onboarded_at": last_changed_at, "offboarded_at": None}
        elif status == "paused":
            entry = {"enabled": False, "onboarded_at": last_changed_at, "offboarded_at": last_changed_at}
        else:
            entry = {"enabled": False, "onboarded_at": None, "offboarded_at": None}

        preserved = {
            k: v
            for k, v in value.items()
            if k not in {"status", "last_changed_at", "last_changed_by"}
        }
        entry.update(preserved)
        out[key] = entry

    return out
