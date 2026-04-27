#!/bin/bash
# SweetClaude TDD Prewrite Guardian Hook
# PreToolUse Write|Edit — blocks source file writes when no test files exist.
# Complements test-guardian.sh (which blocks test modifications during implementation).
# This hook blocks source creation before tests are written.

FILE="$CLAUDE_FILE_PATH"
TOOL="$CLAUDE_TOOL_NAME"

# Only check Write and Edit
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
  echo '{"ok": true}'
  exit 0
fi

# Find project root
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$PROJECT_DIR" ]; then
  echo '{"ok": true}'
  exit 0
fi

STATE_DIR="$PROJECT_DIR/.sweetclaude/state"
GUARDIAN_FLAG="$STATE_DIR/guardian-enabled"

# Guardian not enabled — allow
if [ ! -f "$GUARDIAN_FLAG" ]; then
  echo '{"ok": true}'
  exit 0
fi

# No phase file — allow
PHASE_FILE="$STATE_DIR/phase.yaml"
if [ ! -f "$PHASE_FILE" ]; then
  echo '{"ok": true}'
  exit 0
fi

# Only enforce during implement phase
PHASE=$(grep "^phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
if [[ "$PHASE" != "implement" ]]; then
  echo '{"ok": true}'
  exit 0
fi

# Determine if target file is a test file — if so, allow
TEST_PATTERNS=(
  "test/" "tests/" "__tests__/" "spec/" "specs/"
  ".test." ".spec." "_test." "_spec."
  "test_" "/test" "Test"
)
for pattern in "${TEST_PATTERNS[@]}"; do
  if [[ "$FILE" == *"$pattern"* ]]; then
    echo '{"ok": true}'
    exit 0
  fi
done

# Determine if target file is a non-code file — allow configs, docs, yaml, json, md, sh, etc.
NON_CODE_EXTENSIONS=("md" "json" "yaml" "yml" "toml" "ini" "cfg" "conf" "env" "sh" "bash" "txt" "lock" "log" "gitignore" "editorconfig" "prettierrc" "eslintrc" "babelrc")
EXT="${FILE##*.}"
for ext in "${NON_CODE_EXTENSIONS[@]}"; do
  if [[ "$EXT" == "$ext" ]]; then
    echo '{"ok": true}'
    exit 0
  fi
done

# Non-code path patterns — allow docs, config, state dirs
NON_CODE_PATHS=("docs/" ".sweetclaude/" "config/" ".github/" "scripts/" "dist/" "build/" "node_modules/")
for path in "${NON_CODE_PATHS[@]}"; do
  if [[ "$FILE" == *"$path"* ]]; then
    echo '{"ok": true}'
    exit 0
  fi
done

# Check for test evidence: session-guardian.json has test_files_written entries
SESSION_FILE="$STATE_DIR/session-guardian.json"
if [ -f "$SESSION_FILE" ]; then
  TEST_COUNT=$(/opt/homebrew/bin/jq '.test_files_written | length' "$SESSION_FILE" 2>/dev/null)
  if [ -n "$TEST_COUNT" ] && [ "$TEST_COUNT" -gt 0 ]; then
    echo '{"ok": true}'
    exit 0
  fi
fi

# Check for test evidence: git status shows new/modified test files this session
if git -C "$PROJECT_DIR" status --short 2>/dev/null | grep -E "(test|spec)\." | grep -qE "^[AM]"; then
  echo '{"ok": true}'
  exit 0
fi

# No test evidence found — block
echo '{"ok": false, "reason": "No test files written yet. Write failing tests before source code (TDD). Run /sweetclaude:guardian-off if you need to bypass this check."}'
exit 0
