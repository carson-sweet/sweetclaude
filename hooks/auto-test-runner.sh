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

# No state at all — skip
if [ ! -f "$PHASE_FILE" ] && [ ! -f "$SC_YAML" ]; then
  exit 0
fi

# Only run during implementation phase, tdd_phase = implementing
TDD_STATE=$(python3 "$HOOK_IO" tdd-state "$SC_YAML" "$PHASE_FILE" 2>/dev/null) || exit 0
PHASE=$(printf '%s' "$TDD_STATE" | sed -n '1p')
TDD_PHASE=$(printf '%s' "$TDD_STATE" | sed -n '2p')

if [[ "$PHASE" != "implement" && "$PHASE" != "IMPLEMENT" ]] || [[ "$TDD_PHASE" != "implementing" ]]; then
  exit 0
fi

# Run only when a project source file changed: not tests, docs, config or files outside the project
if ! printf '%s' "$INPUT" | python3 "$HOOK_IO" is-source-file "$FILE"; then
  exit 0
fi

# An explicit test command in project config wins; otherwise detect one from the project
TEST_CMD=""
if [ -f "$PROJECT_CONFIG" ]; then
  TEST_CMD=$(python3 "$HOOK_IO" configured-test-command "$PROJECT_CONFIG")
fi
if [ -z "$TEST_CMD" ]; then
  TEST_CMD=$(python3 "$HOOK_IO" detect-test-command "$PROJECT_DIR")
fi

if [ -z "$TEST_CMD" ]; then
  exit 0
fi

TIMEOUT_SECONDS=$([ -f "$PROJECT_CONFIG" ] && grep "^  timeout_seconds:" "$PROJECT_CONFIG" 2>/dev/null | sed 's/^  timeout_seconds: *//' | tr -d ' "')
case "$TIMEOUT_SECONDS" in
  ''|*[!0-9]*) TIMEOUT_SECONDS=120 ;;
esac

# Run tests under a bound and report a failing or timed-out run as additionalContext
python3 "$HOOK_IO" run-tests "$PROJECT_DIR" "$TEST_CMD" "$TIMEOUT_SECONDS"

exit 0
