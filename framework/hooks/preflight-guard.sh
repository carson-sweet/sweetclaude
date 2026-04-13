#!/bin/bash
# SweetClaude Pre-Flight Guard
# PreToolUse — blocks ALL tool calls if the SessionStart hook flagged this
# project as needing configuration. The flag persists until the project is
# configured (state/phase.yaml exists) or opted out (.sweetclaude-skip).
#
# This hook does NOT set or clear the flag — SessionStart does that.
# This hook only reads the flag and blocks if present.

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

# No git repo — allow
if [ -z "$PROJECT_DIR" ]; then
  echo '{"ok": true}'
  exit 0
fi

PROJECT_HASH=$(echo -n "$PROJECT_DIR" | md5 2>/dev/null || echo -n "$PROJECT_DIR" | md5sum 2>/dev/null | cut -d' ' -f1)
FLAG="/tmp/.sweetclaude-needs-preflight-${PROJECT_HASH}"

# No flag — allow
if [ ! -f "$FLAG" ]; then
  echo '{"ok": true}'
  exit 0
fi

# Flag exists — but maybe the project was configured since it was planted
# Re-check before blocking (covers the case where init just ran)
WORKING_REPO="${PROJECT_DIR}-sweetclaude"
if [ -f "$WORKING_REPO/state/phase.yaml" ] || [ -f "$PROJECT_DIR/state/phase.yaml" ] || [ -f "$PROJECT_DIR/.sweetclaude-skip" ]; then
  rm -f "$FLAG"
  echo '{"ok": true}'
  exit 0
fi

# Flag exists, project still not configured — BLOCK
echo '{"ok": false, "reason": "BLOCKED: SweetClaude is not configured for this project. Run the sweetclaude pre-flight check (invoke the sweetclaude skill) to set up the project, or create .sweetclaude-skip in the project root to opt out. ALL tool calls are blocked until this is resolved."}'
exit 0
