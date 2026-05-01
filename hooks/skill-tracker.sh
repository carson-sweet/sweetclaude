#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Skill Tracker Hook
# PostToolUse — records skill invocations to session-guardian.json

TOOL="$CLAUDE_TOOL_NAME"

# Only track Skill tool calls
if [[ "$TOOL" != "Skill" ]]; then
  exit 0
fi

# Find project root
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

STATE_DIR="$PROJECT_DIR/.sweetclaude/state"
GUARDIAN_FLAG="$STATE_DIR/guardian-enabled"
SESSION_FILE="$STATE_DIR/session-guardian.json"

# Guardian not enabled — nothing to do
if [ ! -f "$GUARDIAN_FLAG" ]; then
  exit 0
fi

# Session file missing — nothing to do
if [ ! -f "$SESSION_FILE" ]; then
  exit 0
fi

# Parse skill name from stdin JSON
INPUT=$(cat)
SKILL_NAME=$(echo "$INPUT" | jq -r '.skill' 2>/dev/null)

if [ -z "$SKILL_NAME" ] || [ "$SKILL_NAME" = "null" ]; then
  exit 0
fi

# Append skill name to skills_invoked array
TMPFILE=$(mktemp)
if jq --arg skill "$SKILL_NAME" '.skills_invoked += [$skill]' "$SESSION_FILE" > "$TMPFILE" 2>/dev/null; then
  mv "$TMPFILE" "$SESSION_FILE"
else
  rm -f "$TMPFILE"
fi

exit 0
