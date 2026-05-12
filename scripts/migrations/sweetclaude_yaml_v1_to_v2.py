# SPDX-License-Identifier: AGPL-3.0-or-later
"""
sweetclaude.yaml v1 → v2 migration handler.

Ships in v3.67.0 as the first real migration that exercises the v3.66.0
runner end-to-end. Also fixes one real user-visible bug: the v3.66.0
version-aware decline rule retroactively reinterpreted pre-3.66 boolean
"Not now" clicks as "decline the entire current major," which silently
suppressed legitimate update prompts.

Three field-level fixes in one schema bump:

1. framework.update.declined:
     true (legacy) → null   (one-time amnesty — let users see new prompts)
     false         → null
     other         → unchanged

2. framework.update.available:
     value older than framework.installed_version → null
     (clears stale discovery results from the pre-3.66 broken hybrid)

3. framework.update.check_error:
     stale value → null  (any non-null check_error gets cleared on this
     migration; the next 24h health check repopulates if the error is
     still real)

Everything else carries forward unchanged. schema_version bumps 1 → 2.
"""

from __future__ import annotations

import re

FROM_VERSION = 1
TO_VERSION = 2
FILE_KEY = "sweetclaude.yaml"


def _semver_tuple(v):
    """Return (major, minor, patch) for a version string, or None if unparseable."""
    if not isinstance(v, str):
        return None
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", v)
    if not m:
        return None
    return tuple(int(p) for p in m.groups())


def up(data: dict, params: dict | None = None) -> dict:
    """Migrate v1 sweetclaude.yaml to v2. Pure function — does not mutate input."""
    out = dict(data)
    out["schema_version"] = 2

    framework = dict(out.get("framework") or {})
    update = dict(framework.get("update") or {})

    # 1. Decline-state amnesty: legacy booleans get cleared so users see one
    # fresh round of prompts under the version-aware rule.
    declined = update.get("declined")
    if isinstance(declined, bool):
        update["declined"] = None
    # If declined is already a version string or None, leave it alone.

    # 2. Stale update.available: clear anything older than the installed version.
    available = update.get("available")
    installed_v = framework.get("installed_version")
    avail_tup = _semver_tuple(available) if isinstance(available, str) else None
    inst_tup = _semver_tuple(installed_v) if isinstance(installed_v, str) else None
    if avail_tup is not None and inst_tup is not None and avail_tup <= inst_tup:
        update["available"] = None

    # 3. Stale check_error: clear (next health check repopulates if real).
    if update.get("check_error"):
        update["check_error"] = None

    framework["update"] = update
    out["framework"] = framework
    return out


def down(data: dict, params: dict | None = None) -> dict:
    """Reverse v2 sweetclaude.yaml back to v1 shape.

    Lossy: cleared fields stay cleared (we don't reconstruct the old boolean
    decline state or the stale available/check_error values). Only the
    schema_version reverts.
    """
    out = dict(data)
    out["schema_version"] = 1
    return out
