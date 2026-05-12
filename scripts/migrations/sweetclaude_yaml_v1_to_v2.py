# SPDX-License-Identifier: AGPL-3.0-or-later
"""
sweetclaude.yaml v1 → v2 migration handler.

Introduced in v3.67.0 to validate the new update/migration system shipped
in v3.66.0. This handler is also the explicit migration for the
`framework.update.declined` field-shape change that Gap #1 / Gap #8
introduced defensively.

What changes between v1 and v2:

- `schema_version` bumps from 1 to 2.
- `framework.update.declined`:
    - v1 used a boolean (`true` = silenced; `false`/missing = active).
    - v2 uses a version string (the specific version the user declined),
      or null (no decline). Bootstrap interprets this version-aware.
    - Migration rule:
        declined: true  → declined: framework.installed_version  (best-effort
                           guess of the version they were on when they declined)
        declined: false → declined: null
        declined: null/missing → declined: null
        declined: <string> → unchanged (already in v2 shape)

Everything else carries forward unchanged.
"""

from __future__ import annotations

FROM_VERSION = 1
TO_VERSION = 2
FILE_KEY = "sweetclaude.yaml"


def up(data: dict, params: dict | None = None) -> dict:
    """Migrate v1 sweetclaude.yaml to v2.

    Pure function. Returns the new dict; does not mutate the input.
    """
    out = dict(data)  # shallow copy; nested dicts replaced as needed below
    out["schema_version"] = 2

    framework = dict(out.get("framework") or {})
    update = dict(framework.get("update") or {})

    declined = update.get("declined")
    if declined is True:
        # Legacy boolean — substitute the version they were on when they declined.
        update["declined"] = framework.get("installed_version") or None
    elif declined is False:
        update["declined"] = None
    elif declined is None:
        update["declined"] = None
    # else: declined is already a version string (or some non-bool), leave it.

    framework["update"] = update
    out["framework"] = framework
    return out


def down(data: dict, params: dict | None = None) -> dict:
    """Reverse v2 sweetclaude.yaml back to v1 shape.

    Lossy: a declined version string collapses back to `True` (we can't
    recover whether the user originally declined with a boolean or a
    specific version).
    """
    out = dict(data)
    out["schema_version"] = 1

    framework = dict(out.get("framework") or {})
    update = dict(framework.get("update") or {})

    declined = update.get("declined")
    if isinstance(declined, str):
        update["declined"] = True
    elif declined is None:
        update["declined"] = False
    # else: True/False stays as-is

    framework["update"] = update
    out["framework"] = framework
    return out
