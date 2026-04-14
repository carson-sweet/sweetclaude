#!/bin/bash
# SweetClaude Auto-Test Runner Hook
# PostToolUse — runs relevant tests after source file edits during implementation.

FILE="$CLAUDE_FILE_PATH"
TOOL="$CLAUDE_TOOL_NAME"

# Only trigger on Write and Edit
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
  exit 0
fi

# Find project root
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

# Resolve state directory — .sweetclaude/ first, legacy fallback
STATE_DIR=""
if [ -d "$PROJECT_DIR/.sweetclaude/state" ]; then
  STATE_DIR="$PROJECT_DIR/.sweetclaude/state"
elif [ -d "${PROJECT_DIR}-sweetclaude/state" ]; then
  STATE_DIR="${PROJECT_DIR}-sweetclaude/state"
fi

if [ -z "$STATE_DIR" ]; then
  exit 0
fi

PHASE_FILE="${STATE_DIR}/phase.yaml"
PROJECT_CONFIG="${STATE_DIR}/project.yaml"

# If no phase file or project config, skip
if [ ! -f "$PHASE_FILE" ] || [ ! -f "$PROJECT_CONFIG" ]; then
  exit 0
fi

# Only run during implementation phase, tdd_phase = implementing
PHASE=$(grep "^phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}')
TDD_PHASE=$(grep "^tdd_phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}')

if [[ "$PHASE" != "implement" && "$PHASE" != "IMPLEMENT" ]] || [[ "$TDD_PHASE" != "implementing" ]]; then
  exit 0
fi

# Don't run on test files (we only run tests when source changes)
TEST_PATTERNS=("test/" "tests/" "__tests__/" "spec/" ".test." ".spec." "_test." "_spec.")
IS_TEST=false
for pattern in "${TEST_PATTERNS[@]}"; do
  if [[ "$FILE" == *"$pattern"* ]]; then
    IS_TEST=true
    break
  fi
done

if [ "$IS_TEST" = true ]; then
  exit 0
fi

# Read test command from project config
TEST_CMD=$(grep "^  test_command:" "$PROJECT_CONFIG" 2>/dev/null | sed 's/^  test_command: //')

if [ -z "$TEST_CMD" ]; then
  exit 0
fi

# Run tests in background — don't block the next edit
echo "Running tests: $TEST_CMD" >&2
cd "$PROJECT_DIR" && eval "$TEST_CMD" 2>&1 | tail -20 >&2 &

exit 0
