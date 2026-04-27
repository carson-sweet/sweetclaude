#!/bin/bash
# SweetClaude Artifact Guardian Hook
# PreToolUse Bash — warns (does not block) when committing without required phase artifacts.

TOOL="$CLAUDE_TOOL_NAME"

# Only check Bash tool calls
if [[ "$TOOL" != "Bash" ]]; then
  exit 0
fi

# Read command from stdin JSON
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.command // ""' 2>/dev/null)

# Only check git commit commands
if ! echo "$COMMAND" | grep -qE '^git commit'; then
  exit 0
fi

# Find project root
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

STATE_DIR="$PROJECT_DIR/.sweetclaude/state"
GUARDIAN_FLAG="$STATE_DIR/guardian-enabled"

# Guardian not enabled — allow
if [ ! -f "$GUARDIAN_FLAG" ]; then
  exit 0
fi

# No phase file — allow
PHASE_FILE="$STATE_DIR/phase.yaml"
if [ ! -f "$PHASE_FILE" ]; then
  exit 0
fi

PHASE=$(grep "^phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
SESSION_FILE="$STATE_DIR/session-guardian.json"

warn() {
  echo "[Protocol Guardian] WARNING: $1" >&2
}

case "$PHASE" in
  implement)
    if [ -f "$SESSION_FILE" ]; then
      TEST_COUNT=$(jq '.test_files_written | length' "$SESSION_FILE" 2>/dev/null)
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
      ARTIFACT_COUNT=$(jq '.artifacts_created | length' "$SESSION_FILE" 2>/dev/null)
      if [ -z "$ARTIFACT_COUNT" ] || [ "$ARTIFACT_COUNT" -eq 0 ]; then
        warn "Committing in DESIGN phase with no design artifacts recorded. Save architecture or tech spec to docs/ first."
      fi
    else
      warn "No session-guardian.json found. Cannot verify artifacts for this commit."
    fi
    ;;
  define)
    if [ -f "$SESSION_FILE" ]; then
      ARTIFACT_COUNT=$(jq '.artifacts_created | length' "$SESSION_FILE" 2>/dev/null)
      if [ -z "$ARTIFACT_COUNT" ] || [ "$ARTIFACT_COUNT" -eq 0 ]; then
        warn "Committing in DEFINE phase with no artifacts recorded. Save product brief or PRD to docs/ first."
      fi
    fi
    ;;
esac

# Always allow — this hook warns but never blocks commits
exit 0
