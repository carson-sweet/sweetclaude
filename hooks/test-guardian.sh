#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Test Guardian Hook
# PreToolUse — blocks Write, Edit, NotebookEdit and Bash writes to test files during implementation phase.

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"
INPUT=$(cat)
hook_field() { printf '%s' "$INPUT" | python3 "$HOOK_IO" field "$1"; }

FILE=$(hook_field tool_input.file_path)
if [ -z "$FILE" ]; then
  FILE=$(hook_field tool_input.notebook_path)
fi
TOOL=$(hook_field tool_name)

# Only check operations that can write a file
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" && "$TOOL" != "NotebookEdit" && "$TOOL" != "Bash" ]]; then
  exit 0
fi

# Find project root and state file
PROJECT_DIR=$(printf '%s' "$INPUT" | python3 "$HOOK_IO" project-dir)

# Resolve state files — .sweetclaude/ first, legacy fallback
SC_YAML=""
PHASE_FILE=""
if [ -f "$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" ]; then
  SC_YAML="$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml"
elif [ -f "${PROJECT_DIR}-sweetclaude/state/sweetclaude.yaml" ]; then
  SC_YAML="${PROJECT_DIR}-sweetclaude/state/sweetclaude.yaml"
fi
if [ -f "$PROJECT_DIR/.sweetclaude/state/phase.yaml" ]; then
  PHASE_FILE="$PROJECT_DIR/.sweetclaude/state/phase.yaml"
elif [ -f "${PROJECT_DIR}-sweetclaude/state/phase.yaml" ]; then
  PHASE_FILE="${PROJECT_DIR}-sweetclaude/state/phase.yaml"
fi

# Neither state file — SweetClaude isn't active, allow
if [ -z "$SC_YAML" ] && [ -z "$PHASE_FILE" ]; then
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
  if [ -n "$FILE" ] && [ "$IS_JW_LOCKED" = "true" ]; then
    python3 "$HOOK_IO" deny "This file is locked by John Wick mode (locked at pipeline step IP5). Test files are immutable for the remainder of the pipeline. To unlock: inspect .sweetclaude/state/john-wick.yaml locked_test_files and get explicit user approval."
    exit 0
  fi
fi

# Project-relative test files this call would write. Whether a file is a test is
# a property of where it sits in the project, not where the project sits on disk
# (ISSUE-282).
TEST_TARGETS=$(printf '%s' "$INPUT" | python3 "$HOOK_IO" test-targets)
if [ -z "$TEST_TARGETS" ]; then
  exit 0
fi

# Resolve phase and tdd_phase from sweetclaude.yaml, which is canonical, and
# fall back to the phase.yaml mirror for projects mid-migration.
TDD_STATE_RC=0
TDD_STATE=$(python3 "$HOOK_IO" tdd-state "$SC_YAML" "$PHASE_FILE" 2>/dev/null) || TDD_STATE_RC=$?
if [ "$TDD_STATE_RC" -ne 0 ]; then
  exit 0
fi
PHASE=$(printf '%s\n' "$TDD_STATE" | sed -n '1p')
TDD_PHASE=$(printf '%s\n' "$TDD_STATE" | sed -n '2p')
RELEASED_FILES=$(printf '%s\n' "$TDD_STATE" | sed -n '3,$p')

# Only block during implementation phase when tdd_phase is "implementing"
if [[ "$PHASE" != "implement" && "$PHASE" != "IMPLEMENT" ]] || [[ "$TDD_PHASE" != "implementing" ]]; then
  exit 0
fi

BLOCKED_TARGETS=""
while IFS= read -r target; do
  [ -z "$target" ] && continue
  if [ -n "$RELEASED_FILES" ] && printf '%s\n' "$RELEASED_FILES" | grep -qFx -- "$target"; then
    continue
  fi
  BLOCKED_TARGETS="${BLOCKED_TARGETS}${target}"$'\n'
done <<< "$TEST_TARGETS"

if [ -n "$BLOCKED_TARGETS" ]; then
  FIRST_TARGET="${BLOCKED_TARGETS%%$'\n'*}"
  RECORD_SCRIPT="$(dirname "$0")/../scripts/record-event.sh"
  [ -x "$RECORD_SCRIPT" ] && bash "$RECORD_SCRIPT" tdd_guardian_block "file=$FIRST_TARGET" "tool=$TOOL"
  python3 "$HOOK_IO" deny "Test files are immutable during implementation. Fix your code, not the tests. If the test is genuinely wrong, ask the user for explicit approval to modify it."
  exit 0
fi

exit 0
