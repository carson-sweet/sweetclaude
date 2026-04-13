#!/bin/bash
# SweetClaude Pre-Flight Guard
# PreToolUse — on first tool use per session, checks if SweetClaude is
# configured for the current project. Blocks if not, with instructions.
#
# Per-project opt-out: create .sweetclaude-skip in the project root.
# Once the pre-flight has run (or been skipped), a session flag prevents
# re-checking on every subsequent tool use.

# Find project root
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

# No git repo — not a project, allow
if [ -z "$PROJECT_DIR" ]; then
  echo '{"ok": true}'
  exit 0
fi

# Session dedup: only check once per project per session
# Uses /tmp with a hash of the project path
PROJECT_HASH=$(echo -n "$PROJECT_DIR" | md5 2>/dev/null || echo -n "$PROJECT_DIR" | md5sum 2>/dev/null | cut -d' ' -f1)
SESSION_FLAG="/tmp/.sweetclaude-preflight-${PROJECT_HASH}"

if [ -f "$SESSION_FLAG" ]; then
  echo '{"ok": true}'
  exit 0
fi

# Project explicitly opts out of SweetClaude
if [ -f "$PROJECT_DIR/.sweetclaude-skip" ]; then
  touch "$SESSION_FLAG"
  echo '{"ok": true}'
  exit 0
fi

# Check if SweetClaude is configured for this project
WORKING_REPO="${PROJECT_DIR}-sweetclaude"
HAS_WORKING_REPO=false
HAS_PHASE_STATE=false

# Check for working repo with phase state
if [ -f "$WORKING_REPO/state/phase.yaml" ]; then
  HAS_WORKING_REPO=true
  HAS_PHASE_STATE=true
fi

# Check for in-repo strategy state (single-repo projects)
if [ -f "$PROJECT_DIR/state/phase.yaml" ]; then
  HAS_PHASE_STATE=true
fi

if [ "$HAS_PHASE_STATE" = true ]; then
  # Configured — mark session as checked, allow
  touch "$SESSION_FLAG"
  echo '{"ok": true}'
  exit 0
fi

# Not configured, not skipped — block once and set flag so we don't nag
touch "$SESSION_FLAG"
echo '{"ok": false, "reason": "SweetClaude is installed but not configured for this project. Invoke the sweetclaude master skill to run the pre-flight check and set up the project. To permanently skip SweetClaude for this project, create a .sweetclaude-skip file in the project root."}'
exit 0
