#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Auto-Test Runner Hook
# PostToolUse — runs relevant tests after source file edits during implementation.

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"
INPUT=$(cat)
hook_field() { printf '%s' "$INPUT" | python3 "$HOOK_IO" field "$1"; }

FILE=$(hook_field tool_input.file_path)
TOOL=$(hook_field tool_name)

# Only trigger on Write and Edit
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
  exit 0
fi

# Find project root
PROJECT_DIR=$(printf '%s' "$INPUT" | python3 "$HOOK_IO" project-dir)

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
SC_YAML="${STATE_DIR}/sweetclaude.yaml"
PROJECT_CONFIG="${STATE_DIR}/project.yaml"

# No state at all, or no project config — skip
if { [ ! -f "$PHASE_FILE" ] && [ ! -f "$SC_YAML" ]; } || [ ! -f "$PROJECT_CONFIG" ]; then
  exit 0
fi

# Resolve phase and tdd_phase from sweetclaude.yaml, which is canonical, and
# fall back to the phase.yaml mirror for projects mid-migration. Reading only
# the mirror meant this never ran on a v4 project (ISSUE-281), and tdd_phase
# was written by nothing at all (ISSUE-282).
read_tdd_state() {
  SC_YAML="$1" PHASE_YAML="$2" python3 - <<'PYEOF' 2>/dev/null
import os, yaml

def load(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

sc = load(os.environ.get("SC_YAML", ""))
mirror = load(os.environ.get("PHASE_YAML", ""))
active = (sc.get("work") or {}).get("active") or {}
phase = active.get("phase") or mirror.get("phase") or ""
tdd = active.get("tdd_phase") or mirror.get("tdd_phase") or ""
print(f"{phase}\n{tdd}")
PYEOF
}

# Only run during implementation phase, tdd_phase = implementing
TDD_STATE=$(read_tdd_state "$SC_YAML" "$PHASE_FILE")
PHASE=$(printf '%s' "$TDD_STATE" | sed -n '1p')
TDD_PHASE=$(printf '%s' "$TDD_STATE" | sed -n '2p')

if [[ "$PHASE" != "implement" && "$PHASE" != "IMPLEMENT" ]] || [[ "$TDD_PHASE" != "implementing" ]]; then
  exit 0
fi

# Don't run on test files (we only run tests when source changes)
TEST_PATTERNS=("test/" "tests/" "__tests__/" "spec/" "specs/" ".test." ".spec." "_test." "_spec." "test_")
REL_FILE=$(printf '%s' "$INPUT" | python3 "$HOOK_IO" rel-path "$FILE")

IS_TEST=false
for pattern in "${TEST_PATTERNS[@]}"; do
  if [[ "$REL_FILE" == *"$pattern"* ]]; then
    IS_TEST=true
    break
  fi
done

if [[ "$REL_FILE" == *.feature ]]; then
  IS_TEST=true
fi

if [ "$IS_TEST" = true ]; then
  exit 0
fi

# Read test command from project config
TEST_CMD=$(grep "^  test_command:" "$PROJECT_CONFIG" 2>/dev/null | sed 's/^  test_command: //')

if [ -z "$TEST_CMD" ]; then
  exit 0
fi

TIMEOUT_SECONDS=$(grep "^  timeout_seconds:" "$PROJECT_CONFIG" 2>/dev/null | sed 's/^  timeout_seconds: *//' | tr -d ' "')
case "$TIMEOUT_SECONDS" in
  ''|*[!0-9]*) TIMEOUT_SECONDS=120 ;;
esac

# Run tests under a bound and report a failing or timed-out run as additionalContext
python3 "$HOOK_IO" run-tests "$PROJECT_DIR" "$TEST_CMD" "$TIMEOUT_SECONDS"

exit 0
