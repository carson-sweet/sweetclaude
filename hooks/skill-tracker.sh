#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Skill Tracker Hook
# PostToolUse — records skill invocations to session-guardian.json and via record-event.sh

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"
INPUT=$(cat)
hook_field() { printf '%s' "$INPUT" | python3 "$HOOK_IO" field "$1"; }

TOOL=$(hook_field tool_name)

# Only track Skill tool calls
if [[ "$TOOL" != "Skill" ]]; then
  exit 0
fi

# Find project root
PROJECT_DIR=$(printf '%s' "$INPUT" | python3 "$HOOK_IO" project-dir)

STATE_DIR="$PROJECT_DIR/.sweetclaude/state"
GUARDIAN_FLAG="$STATE_DIR/guardian-enabled"
SESSION_FILE="$STATE_DIR/session-guardian.json"
SKILL_NAME=$(hook_field tool_input.skill)

if [ -z "$SKILL_NAME" ]; then
  exit 0
fi

# ── Guardian tracking ─────────────────────────────────────────────────────────
if [ -f "$GUARDIAN_FLAG" ] && [ -f "$SESSION_FILE" ]; then
  TMPFILE=$(mktemp)
  if jq --arg skill "$SKILL_NAME" '.skills_invoked += [$skill]' "$SESSION_FILE" > "$TMPFILE" 2>/dev/null; then
    mv "$TMPFILE" "$SESSION_FILE"
  else
    rm -f "$TMPFILE"
  fi
fi

# ── Metrics recording ─────────────────────────────────────────────────────────
RECORD_SCRIPT="$(dirname "$(dirname "$0")")/scripts/record-event.sh"
if [ -x "$RECORD_SCRIPT" ]; then
  PHASE=$(python3 -c "
import yaml
try:
    d = yaml.safe_load(open('$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml')) or {}
    print(d.get('work', {}).get('active', {}).get('phase') or 'none')
except Exception:
    print('none')
" 2>/dev/null || echo "none")
  bash "$RECORD_SCRIPT" skill_invoked "skill=$SKILL_NAME" "phase=$PHASE"
fi

exit 0
