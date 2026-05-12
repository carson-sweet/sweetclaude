# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Fixture handler that always raises RecoverableMigrationError. Used by
tests/test-migration-runner.sh to verify the recoverable-error protocol.

The class `RecoverableMigrationError` is injected into this module's namespace
by the runner's _load_handler() before the module body executes — handlers do
not need to import anything.
"""

from __future__ import annotations

from pathlib import Path

FROM_VERSION = 1
TO_VERSION = 2


def detect_version(directory: Path) -> int | None:
    return 1 if directory.exists() else None


def up(directory: Path, params: dict | None = None) -> dict:
    raise RecoverableMigrationError(  # noqa: F821 — injected by runner
        message="ITEM-007 is missing required field 'type'",
        options=[
            {"label": "Set type to story (default)", "action": "set_type", "value": "story"},
            {"label": "Set type to bug", "action": "set_type", "value": "bug"},
            {"label": "Open the file so I can fix it manually, then retry", "action": "open_for_manual_edit"},
        ],
        current_file=directory / "ITEM-007-something.md",
        current_id="ITEM-007",
    )


def down(directory: Path, params: dict | None = None) -> dict:
    return {"mapping": [], "warnings": [], "files_in": 0, "files_out": 0}
