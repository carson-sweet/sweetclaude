#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Small-Story Stop Guard Hook (Track C TASK-C4)
# Stop — blocks session end while a small-story workflow is active and
# non-terminal, surfacing a one-line status summary. A deliberate second stop
# (stop_hook_active) confirms an intentional pause and is recorded to disk,
# fingerprinted to the workflow's material state; later turns then stop
# silently until the story progresses (re-arming one reminder) or goes
# terminal. This prevents the block re-firing on every turn of a paused story.
#
# Protocol: block = exit 0 + {"decision":"block","reason":...}; allow = silent.

set -uo pipefail

INPUT_FILE=$(mktemp "${TMPDIR:-/tmp}/sc-ls-hook.XXXXXX")
trap 'rm -f "$INPUT_FILE"' EXIT
cat > "$INPUT_FILE"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
WORKFLOWS_DIR="$PROJECT_DIR/.sweetclaude/state/workflows"

if ! compgen -G "$WORKFLOWS_DIR/*.yaml" > /dev/null 2>&1; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT:-$SCRIPT_DIR/..}/scripts"

STOP_INPUT_FILE="$INPUT_FILE" STOP_PROJECT_DIR="$PROJECT_DIR" STOP_SCRIPTS_DIR="$SCRIPTS_DIR" python3 - <<'PYEOF'
import json
import os
import sys
from pathlib import Path


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


with open(os.environ["STOP_INPUT_FILE"], encoding="utf-8") as handle:
    data = json.load(handle)
stop_hook_active = bool(data.get("stop_hook_active"))

try:
    sys.path.insert(0, os.environ["STOP_SCRIPTS_DIR"])
    from small_story_controller import (
        _active_small_story_workflow,
        render_small_story_status,
    )
    from story_stop_ack import compute_fingerprint, read_ack_fingerprint, write_ack

    project = Path(os.environ.get("STOP_PROJECT_DIR") or data.get("cwd") or os.getcwd())
    project = project.expanduser().resolve(strict=False)

    active = _active_small_story_workflow(project)
    if active is None:
        sys.exit(0)
    workflow_id, state = active

    status = render_small_story_status(project_dir=project, workflow_id=workflow_id)
    if status.get("ok") and status.get("completion_claim_allowed"):
        sys.exit(0)

    phase = str(state.get("phase") or "UNKNOWN")
    fingerprint = compute_fingerprint(phase, status)

    # A deliberate second stop within the same turn = the user confirmed the
    # pause. Record it so later turns stay silent until the story progresses.
    if stop_hook_active:
        try:
            write_ack(project, workflow_id, fingerprint)
        except BaseException:  # noqa: BLE001 — never block a deliberate pause
            pass
        sys.exit(0)

    # Pause already acknowledged and nothing material has changed since.
    if read_ack_fingerprint(project, workflow_id) == fingerprint:
        sys.exit(0)

    block(
        f"Workflow checkpoint — {workflow_id} is paused in {phase}. Progress is saved. "
        "To resume: keep working on this story. "
        "To pause: stop again to confirm (guard stays silent until story progresses). "
        "To save for later: /sweetclaude:configure hibernate. "
        "Relay this to the user as a checkpoint, not an error. Do not paste raw JSON "
        "or claim the story is done."
    )
except SystemExit:
    raise
except BaseException as exc:  # noqa: BLE001 — workflow state exists; fail closed once
    if stop_hook_active:
        # A deliberate pause is always honored, even if evaluation failed.
        sys.exit(0)
    block(
        f"Workflow checkpoint — could not read workflow status ({exc}). "
        "A small-story workflow exists in this project. Stop again to pause. "
        "Tell the user their progress is saved and they can stop again to confirm."
    )
PYEOF
exit 0
