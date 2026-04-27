#!/bin/bash
# Tests for skill-tracker.sh

PASS=0
FAIL=0

pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# Setup: create a real temp git repo
TMPDIR=$(mktemp -d)
git init "$TMPDIR" -q
mkdir -p "$TMPDIR/.sweetclaude/state"
ORIGINAL_DIR=$(pwd)
cd "$TMPDIR"

cleanup() { cd "$ORIGINAL_DIR"; rm -rf "$TMPDIR"; }
trap cleanup EXIT

HOOK="$ORIGINAL_DIR/hooks/skill-tracker.sh"

# Test 1: guardian not enabled → exits cleanly, no file written
rm -f .sweetclaude/state/session-guardian.json
OUTPUT=$(echo '{"skill":"sweetclaude:brainstorming"}' | bash "$HOOK" 2>&1)
[ ! -f .sweetclaude/state/session-guardian.json ] && pass "guardian off: no file written" || fail "guardian off: should not write file"

# Test 2: guardian enabled, valid skill → appended to skills_invoked
export CLAUDE_TOOL_NAME="Skill"
touch .sweetclaude/state/guardian-enabled
echo '{"enabled":true,"skills_invoked":[],"test_files_written":[],"artifacts_created":[],"tdd_status":"pending"}' \
  > .sweetclaude/state/session-guardian.json

echo '{"skill":"sweetclaude:brainstorming"}' | bash "$HOOK" 2>&1
INVOKED=$(jq -r '.skills_invoked[0]' .sweetclaude/state/session-guardian.json 2>/dev/null)
[ "$INVOKED" = "sweetclaude:brainstorming" ] && pass "skill name recorded in skills_invoked" || fail "expected sweetclaude:brainstorming, got: $INVOKED"

# Test 3: second invocation appended (not overwritten)
echo '{"skill":"sweetclaude:code-feature"}' | bash "$HOOK" 2>&1
COUNT=$(jq '.skills_invoked | length' .sweetclaude/state/session-guardian.json 2>/dev/null)
[ "$COUNT" = "2" ] && pass "second skill appended (array length 2)" || fail "expected 2 entries, got: $COUNT"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
