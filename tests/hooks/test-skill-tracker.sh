#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Tests for skill-tracker.sh

PASS=0
FAIL=0

pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# Setup: create a real temp git repo
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/hooks/skill-tracker.sh"
HOOK_STDIN="$REPO_ROOT/tests/hook_stdin.py"

skill_payload() {
  python3 "$HOOK_STDIN" payload PostToolUse-Skill "$(pwd -P)" skill="$1"
}

run_hook() {
  env -u CLAUDE_TOOL_NAME -u CLAUDE_FILE_PATH -u CLAUDE_TRANSCRIPT_PATH bash "$HOOK" <<< "$(skill_payload "$1")" 2>&1
}

TEST_TMPDIR=$(mktemp -d)
git init "$TEST_TMPDIR" -q
mkdir -p "$TEST_TMPDIR/.sweetclaude/state"
cd "$TEST_TMPDIR"

cleanup() { cd "$REPO_ROOT"; rm -rf "$TEST_TMPDIR"; }
trap cleanup EXIT

# Test 1: guardian not enabled → exits cleanly, no file written
rm -f .sweetclaude/state/session-guardian.json
OUTPUT=$(run_hook "sweetclaude:brainstorming")
[ ! -f .sweetclaude/state/session-guardian.json ] && pass "guardian off: no file written" || fail "guardian off: should not write file"

# Test 2: guardian enabled, valid skill → appended to skills_invoked
touch .sweetclaude/state/guardian-enabled
echo '{"enabled":true,"skills_invoked":[],"test_files_written":[],"artifacts_created":[],"tdd_status":"pending"}' \
  > .sweetclaude/state/session-guardian.json

run_hook "sweetclaude:brainstorming"
INVOKED=$(jq -r '.skills_invoked[0]' .sweetclaude/state/session-guardian.json 2>/dev/null)
[ "$INVOKED" = "sweetclaude:brainstorming" ] && pass "skill name recorded in skills_invoked" || fail "expected sweetclaude:brainstorming, got: $INVOKED"

# Test 3: second invocation appended (not overwritten)
run_hook "sweetclaude:code-feature"
COUNT=$(jq '.skills_invoked | length' .sweetclaude/state/session-guardian.json 2>/dev/null)
[ "$COUNT" = "2" ] && pass "second skill appended (array length 2)" || fail "expected 2 entries, got: $COUNT"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
