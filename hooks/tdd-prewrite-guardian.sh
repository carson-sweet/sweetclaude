#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude TDD Prewrite Guardian Hook
# PreToolUse Write|Edit — blocks source file writes when no test files exist.
# Complements test-guardian.sh (which blocks test modifications during implementation).
# This hook blocks source creation before tests are written.

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"
INPUT=$(cat)
hook_field() { printf '%s' "$INPUT" | python3 "$HOOK_IO" field "$1"; }

FILE=$(hook_field tool_input.file_path)
TOOL=$(hook_field tool_name)

# Only check Write and Edit
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
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

# No phase file — allow
PHASE_FILE="$STATE_DIR/phase.yaml"
if [ ! -f "$PHASE_FILE" ]; then
  exit 0
fi

# Only enforce during implement phase
PHASE=$(grep "^phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
if [[ "$PHASE" != "implement" ]]; then
  exit 0
fi

# Determine if target file is a test file — if so, allow
TEST_PATTERNS=(
  "/test/" "/tests/" "/__tests__/" "/spec/" "/specs/"
  ".test." ".spec." "_test." "_spec."
  "test_"
)
for pattern in "${TEST_PATTERNS[@]}"; do
  if [[ "$FILE" == *"$pattern"* ]]; then
    exit 0
  fi
done

# Determine if target file is a non-code file — allow configs, docs, yaml, json, md, sh, etc.
BASENAME="${FILE##*/}"
if [[ "$BASENAME" == *.* ]]; then
  EXT="${BASENAME##*.}"
else
  EXT=""
fi

NON_CODE_EXTENSIONS=("md" "json" "yaml" "yml" "toml" "ini" "cfg" "conf" "env" "sh" "bash" "txt" "lock" "log" "gitignore" "editorconfig" "prettierrc" "eslintrc" "babelrc")
for ext in "${NON_CODE_EXTENSIONS[@]}"; do
  if [[ "$EXT" == "$ext" ]]; then
    exit 0
  fi
done

# Extensionless files that are build/config files — allow
NON_CODE_BASENAMES=("Makefile" "Dockerfile" "Rakefile" "Gemfile" "Procfile" "Vagrantfile" "Brewfile" "Justfile" "CMakeLists.txt")
for name in "${NON_CODE_BASENAMES[@]}"; do
  if [[ "$BASENAME" == "$name" ]]; then
    exit 0
  fi
done

# Non-code path patterns — allow docs, config, state dirs
NON_CODE_PATHS=("docs/" ".sweetclaude/" "config/" ".github/" "scripts/" "dist/" "build/" "node_modules/")
for path in "${NON_CODE_PATHS[@]}"; do
  if [[ "$FILE" == *"$path"* ]]; then
    exit 0
  fi
done

# Check for test evidence: session-guardian.json has test_files_written entries
SESSION_FILE="$STATE_DIR/session-guardian.json"
if [ -f "$SESSION_FILE" ]; then
  TEST_COUNT=$(jq '.test_files_written | length' "$SESSION_FILE" 2>/dev/null)
  if [ -n "$TEST_COUNT" ] && [ "$TEST_COUNT" -gt 0 ]; then
    exit 0
  fi
fi

# Check for test evidence: git status shows new/modified test files this session
if git -C "$PROJECT_DIR" status --short 2>/dev/null | \
   awk '{print $NF}' | \
   grep -qE "(test|spec)\.(js|ts|py|rb|go|java|rs|cpp|c|cs|swift|kt|php|sh)$"; then
  exit 0
fi

# No test evidence found — block
python3 "$HOOK_IO" deny "No test files written yet. Write failing tests before source code (TDD). Run /sweetclaude:configure guardian-off if you need to bypass this check."
exit 0
