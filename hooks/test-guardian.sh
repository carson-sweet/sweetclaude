#!/bin/bash
# SweetClaude Test Guardian Hook
# PreToolUse — blocks Write/Edit to test files during implementation phase.

FILE="$CLAUDE_FILE_PATH"
TOOL="$CLAUDE_TOOL_NAME"

# Only check Write and Edit operations
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
  echo '{"ok": true}'
  exit 0
fi

# Find project root and state file
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

if [ -z "$PROJECT_DIR" ]; then
  echo '{"ok": true}'
  exit 0
fi

# Resolve phase file — .sweetclaude/ first, legacy fallback
PHASE_FILE=""
if [ -f "$PROJECT_DIR/.sweetclaude/state/phase.yaml" ]; then
  PHASE_FILE="$PROJECT_DIR/.sweetclaude/state/phase.yaml"
elif [ -f "${PROJECT_DIR}-sweetclaude/state/phase.yaml" ]; then
  PHASE_FILE="${PROJECT_DIR}-sweetclaude/state/phase.yaml"
fi

# If no phase file, SweetClaude isn't active — allow
if [ -z "$PHASE_FILE" ]; then
  echo '{"ok": true}'
  exit 0
fi

# Check if we're in implementation phase
PHASE=$(grep "^phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}')
TDD_PHASE=$(grep "^tdd_phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}')

# Only block during implementation phase when tdd_phase is "implementing"
if [[ "$PHASE" != "implement" && "$PHASE" != "IMPLEMENT" ]] || [[ "$TDD_PHASE" != "implementing" ]]; then
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
