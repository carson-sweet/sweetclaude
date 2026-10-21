#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Artifact Guardian Hook
# PreToolUse Bash — warns (does not block) when committing without required phase artifacts.

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"
INPUT=$(cat)
hook_field() { printf '%s' "$INPUT" | python3 "$HOOK_IO" field "$1"; }

TOOL=$(hook_field tool_name)

# Only check Bash tool calls
if [[ "$TOOL" != "Bash" ]]; then
  exit 0
fi

COMMAND=$(hook_field tool_input.command)

# Only check git commit commands
if ! printf '%s' "$INPUT" | python3 "$HOOK_IO" is-git-commit; then
  exit 0
fi

# Find project root
PROJECT_DIR=$(printf '%s' "$INPUT" | python3 "$HOOK_IO" project-dir)

STATE_DIR="$PROJECT_DIR/.sweetclaude/state"
GUARDIAN_FLAG="$STATE_DIR/guardian-enabled"

# Guardian not enabled — allow
if [ ! -f "$GUARDIAN_FLAG" ]; then
  exit 0
fi

# Read phase from sweetclaude.yaml (v3) or phase.yaml (v2 fallback)
SC_YAML="$STATE_DIR/sweetclaude.yaml"
PHASE_FILE="$STATE_DIR/phase.yaml"

if [ -f "$SC_YAML" ]; then
  PHASE=$(python3 -c "
import sys, yaml
d = yaml.safe_load(open(sys.argv[1])) or {}
print((d.get('work',{}).get('active',{}).get('phase') or '').lower())
" "$SC_YAML" 2>/dev/null)
elif [ -f "$PHASE_FILE" ]; then
  PHASE=$(grep "^phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
else
  exit 0
fi
SESSION_FILE="$STATE_DIR/session-guardian.json"

WARNINGS=""
warn() {
  WARNINGS="${WARNINGS:+$WARNINGS
}[Protocol Guardian] WARNING: $1"
}

case "$PHASE" in
  implement)
    if [ -f "$SESSION_FILE" ]; then
      TEST_COUNT=$(jq '(.test_files_written // []) | length' "$SESSION_FILE" 2>/dev/null)
      TDD_STATUS=$(jq -r '.tdd_status // "unknown"' "$SESSION_FILE" 2>/dev/null)

      if [ -z "$TEST_COUNT" ] || [ "$TEST_COUNT" -eq 0 ]; then
        warn "Committing in IMPLEMENT phase with no test files recorded in session state."
      fi
      if [[ "$TDD_STATUS" != "green" && "$TDD_STATUS" != "implementing" ]]; then
        warn "TDD status is '$TDD_STATUS' — expected 'green' before committing."
      fi
    else
      warn "No session-guardian.json found. Cannot verify test coverage for this commit."
    fi
    ;;
  design)
    if [ -f "$SESSION_FILE" ]; then
      ARTIFACT_COUNT=$(jq '(.artifacts_created // []) | length' "$SESSION_FILE" 2>/dev/null)
      if [ -z "$ARTIFACT_COUNT" ] || [ "$ARTIFACT_COUNT" -eq 0 ]; then
        warn "Committing in DESIGN phase with no design artifacts recorded. Save architecture or tech spec to docs/ first."
      fi
    else
      warn "No session-guardian.json found. Cannot verify artifacts for this commit."
    fi
    ;;
  define)
    if [ -f "$SESSION_FILE" ]; then
      ARTIFACT_COUNT=$(jq '(.artifacts_created // []) | length' "$SESSION_FILE" 2>/dev/null)
      if [ -z "$ARTIFACT_COUNT" ] || [ "$ARTIFACT_COUNT" -eq 0 ]; then
        warn "Committing in DEFINE phase with no artifacts recorded. Save product brief or PRD to docs/ first."
      fi
    else
      warn "No session-guardian.json found. Cannot verify artifacts for this commit."
    fi
    ;;
esac

# Always allow — this hook warns through additionalContext but never blocks commits
if [ -n "$WARNINGS" ]; then
  python3 "$HOOK_IO" context PreToolUse "$WARNINGS"
fi
exit 0
