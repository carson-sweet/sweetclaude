#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
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

# Check john-wick mode locked files
JW_STATE="$PROJECT_DIR/.sweetclaude/state/john-wick.yaml"
if [ -f "$JW_STATE" ]; then
  IS_JW_LOCKED=""
  if command -v python3 &>/dev/null; then
    IS_JW_LOCKED=$(JW_STATE="$JW_STATE" TARGET_FILE="$FILE" PROJECT_DIR="$PROJECT_DIR" python3 - <<'PYEOF' 2>/dev/null || echo "error"
import yaml, os
jw_state = os.environ['JW_STATE']
target_file = os.environ.get('TARGET_FILE', '')
project_dir = os.environ.get('PROJECT_DIR', '')
with open(jw_state) as f:
    state = yaml.safe_load(f) or {}
locked = state.get('locked_test_files') or []
target = os.path.realpath(os.path.abspath(target_file)) if target_file else ''
resolved_locked = [os.path.realpath(os.path.join(project_dir, p) if not os.path.isabs(p) else p) for p in locked]
print('true' if target in resolved_locked else 'false')
PYEOF
)
  fi
  # If python3/yaml failed, fall back to grep-based check
  if [ "$IS_JW_LOCKED" = "error" ] || [ -z "$IS_JW_LOCKED" ]; then
    # Normalize FILE to repo-relative path for grep comparison
    REAL_PROJECT_DIR=$(realpath "$PROJECT_DIR" 2>/dev/null || echo "$PROJECT_DIR")
    REAL_FILE=$(realpath "$FILE" 2>/dev/null || echo "$FILE")
    REL_FILE="${REAL_FILE#$REAL_PROJECT_DIR/}"
    if [ "$REL_FILE" != "$REAL_FILE" ] && grep -qF -- "- $REL_FILE" "$JW_STATE" 2>/dev/null; then
      IS_JW_LOCKED=true
    fi
  fi
  if [ "$IS_JW_LOCKED" = "true" ]; then
    echo '{"ok": false, "reason": "This file is locked by John Wick mode (locked at pipeline step IP5). Test files are immutable for the remainder of the pipeline. To unlock: inspect .sweetclaude/state/john-wick.yaml locked_test_files and get explicit user approval."}'
    exit 0
  fi
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
