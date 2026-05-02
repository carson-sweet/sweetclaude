#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Session Pre-Flight
# SessionStart hook — checks SweetClaude state for the current project.
# Outputs JSON with hookSpecificOutput.additionalContext (Claude Code format).
# Per-project opt-out: create .sweetclaude-skip in the project root.

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

# No git repo — nothing to do
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

PROJECT_HASH=$(echo -n "$PROJECT_DIR" | md5 2>/dev/null || echo -n "$PROJECT_DIR" | md5sum 2>/dev/null | cut -d' ' -f1)
FLAG="/tmp/.sweetclaude-needs-preflight-${PROJECT_HASH}"

emit_json() {
  local content="$1"
  # Escape for JSON string embedding
  content="${content//\\/\\\\}"
  content="${content//\"/\\\"}"
  content="${content//$'\n'/\\n}"
  content="${content//$'\r'/\\r}"
  content="${content//$'\t'/\\t}"
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$content"
}

# Project explicitly opts out
if [ -f "$PROJECT_DIR/.sweetclaude-skip" ]; then
  rm -f "$FLAG"
  exit 0
fi

# Check if configured — .sweetclaude/ inside project
if [ -f "$PROJECT_DIR/.sweetclaude/state/phase.yaml" ]; then
  rm -f "$FLAG"
  # Auto-fire status if active (not disabled)
  if [ ! -f "$PROJECT_DIR/.sweetclaude/disabled" ]; then
    # Refresh session-state.yaml synchronously so injected state is current
    HOOK_DIR="$(dirname "$0")"
    "$HOOK_DIR/generate-session-state.sh" 2>/dev/null

    STATE_FILE="$PROJECT_DIR/.sweetclaude/state/session-state.yaml"
    if [ -f "$STATE_FILE" ]; then
      STATE_CONTENT=$(cat "$STATE_FILE")
      emit_json "SweetClaude is active. Pre-loaded session state:

${STATE_CONTENT}

Invoke sweetclaude:status now before responding to the user."
    else
      emit_json "SweetClaude is active. Invoke sweetclaude:status now before responding to the user."
    fi
  fi
  exit 0
fi

# Legacy fallback: separate working repo
LEGACY_REPO="${PROJECT_DIR}-sweetclaude"
if [ -f "$LEGACY_REPO/state/phase.yaml" ]; then
  rm -f "$FLAG"
  exit 0
fi

# Not configured — plant the flag and tell Claude
touch "$FLAG"
emit_json "STOP. SweetClaude is installed but this project is not configured. You MUST run the sweetclaude pre-flight check before doing any work. Invoke the sweetclaude:master skill now. Every tool call will be blocked until this is resolved."
