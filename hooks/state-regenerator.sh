#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude State Regenerator
# PostToolUse (Write|Edit) — regenerates session-state.yaml when a constituent state file changes.

FILE="${CLAUDE_FILE_PATH:-}"
TOOL="${CLAUDE_TOOL_NAME:-}"

if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
  exit 0
fi

case "$FILE" in
  */.sweetclaude/state/phase.yaml|\
  */.sweetclaude/state/improvement-register.md|\
  */.sweetclaude/state/checkpoint.md|\
  */.sweetclaude/state/skills.yaml|\
  */.sweetclaude/artifact-privacy.yaml|\
  */milestones/MS-*.md)
    HOOK_DIR="$(dirname "$0")"
    "$HOOK_DIR/generate-session-state.sh" 2>/dev/null &
    ;;
esac

exit 0
