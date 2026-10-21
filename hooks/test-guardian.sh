#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Test Guardian Hook
# PreToolUse — blocks Write/Edit to test files during implementation phase.

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"
INPUT=$(cat)
hook_field() { printf '%s' "$INPUT" | python3 "$HOOK_IO" field "$1"; }

FILE=$(hook_field tool_input.file_path)
TOOL=$(hook_field tool_name)

# Only check Write and Edit operations
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
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
    python3 "$HOOK_IO" deny "This file is locked by John Wick mode (locked at pipeline step IP5). Test files are immutable for the remainder of the pipeline. To unlock: inspect .sweetclaude/state/john-wick.yaml locked_test_files and get explicit user approval."
    exit 0
  fi
fi

# Check if we're in implementation phase
TDD_STATE=$(read_tdd_state "$SC_YAML" "$PHASE_FILE")
PHASE=$(printf '%s' "$TDD_STATE" | sed -n '1p')
TDD_PHASE=$(printf '%s' "$TDD_STATE" | sed -n '2p')

# Only block during implementation phase when tdd_phase is "implementing"
if [[ "$PHASE" != "implement" && "$PHASE" != "IMPLEMENT" ]] || [[ "$TDD_PHASE" != "implementing" ]]; then
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

# Match against the path *within the project*, not the absolute path. A
# project checked out under a directory whose name contains "test_" or
# "tests/" would otherwise have every source file treated as a test file and
# refused during implementation (ISSUE-282). Whether a file is a test is a
# property of where it sits in the project, not where the project sits on disk.
REL_FILE=$(printf '%s' "$INPUT" | python3 "$HOOK_IO" rel-path "$FILE")

IS_TEST=false
for pattern in "${TEST_PATTERNS[@]}"; do
  if [[ "$REL_FILE" == *"$pattern"* ]]; then
    IS_TEST=true
    break
  fi
done

# Also check .feature files (Gherkin specs are immutable during implementation)
if [[ "$REL_FILE" == *.feature ]]; then
  IS_TEST=true
fi

if [ "$IS_TEST" = true ]; then
  RECORD_SCRIPT="$(dirname "$0")/../scripts/record-event.sh"
  [ -x "$RECORD_SCRIPT" ] && bash "$RECORD_SCRIPT" tdd_guardian_block "file=$FILE" "tool=$TOOL"
  python3 "$HOOK_IO" deny "Test files are immutable during implementation. Fix your code, not the tests. If the test is genuinely wrong, ask the user for explicit approval to modify it."
  exit 0
fi

exit 0
