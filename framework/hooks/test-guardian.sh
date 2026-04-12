#!/bin/bash
# SweetClaude Test Guardian Hook
# PreToolUse — blocks Write/Edit to test files during implementation phase.
#
# Reads phase state to determine if we're in implementation.
# If so, blocks edits to test directories.

FILE="$CLAUDE_FILE_PATH"
TOOL="$CLAUDE_TOOL_NAME"

# Only check Write and Edit operations
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
  echo '{"ok": true}'
  exit 0
fi

# Find the SweetClaude working repo for this project
# Look for state/phase.yaml in common locations
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
WORKING_REPO="${PROJECT_DIR}-sweetclaude"
PHASE_FILE="${WORKING_REPO}/state/phase.yaml"

# If no phase file, SweetClaude isn't active — allow
if [ ! -f "$PHASE_FILE" ]; then
  echo '{"ok": true}'
  exit 0
fi

# Check if we're in implementation phase
PHASE=$(grep "^phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}')
TDD_PHASE=$(grep "^tdd_phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}')

# Only block during implementation phase when tdd_phase is "implementing"
if [[ "$PHASE" != "implement" || "$TDD_PHASE" != "implementing" ]]; then
  echo '{"ok": true}'
  exit 0
fi

# Check if the file is in a test directory
TEST_PATTERNS=(
  "test/"
  "tests/"
  "__tests__/"
  "spec/"
  "specs/"
  ".test."
  ".spec."
  "_test."
  "_spec."
  "test_"
)

IS_TEST=false
for pattern in "${TEST_PATTERNS[@]}"; do
  if [[ "$FILE" == *"$pattern"* ]]; then
    IS_TEST=true
    break
  fi
done

# Also check .feature files (Gherkin specs are immutable during implementation)
if [[ "$FILE" == *.feature ]]; then
  IS_TEST=true
fi

if [ "$IS_TEST" = true ]; then
  echo '{"ok": false, "reason": "Test files are immutable during implementation. Fix your code, not the tests. If the test is genuinely wrong, ask the user for explicit approval to modify it."}'
  exit 0
fi

echo '{"ok": true}'
exit 0
