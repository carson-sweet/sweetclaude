#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude State Regenerator
# PostToolUse (Write|Edit) — regenerates session-state.yaml when a constituent state file changes.

FILE="${CLAUDE_FILE_PATH:-}"
TOOL="${CLAUDE_TOOL_NAME:-}"

if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
  exit 0
fi

# The watch list must cover every file generate-session-state.sh reads. It
# missed sweetclaude.yaml — the canonical state file — so on a v4 project, where
# phase.yaml is a lazily-written mirror most projects never have, no state change
# regenerated anything and session-state.yaml went quietly stale (ISSUE-281).
# tests/test_state_regenerator_watch_list.py asserts the two stay in step.
case "$FILE" in
  */.sweetclaude/state/sweetclaude.yaml|\
  */.sweetclaude/state/phase.yaml|\
  */.sweetclaude/state/improvement-register.md|\
  */.sweetclaude/state/improvement-register.jsonl|\
  */.sweetclaude/state/checkpoint.md|\
  */.sweetclaude/state/skills.yaml|\
  */.sweetclaude/artifact-privacy.yaml|\
  */milestones/MS-*.md)
    HOOK_DIR="$(dirname "$0")"
    "$HOOK_DIR/generate-session-state.sh" 2>/dev/null &
    ;;
esac

exit 0
