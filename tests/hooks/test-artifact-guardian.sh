#!/bin/bash
# Tests for artifact-guardian.sh

PASS=0
FAIL=0

pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1 (got: $2)"; FAIL=$((FAIL + 1)); }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/hooks/artifact-guardian.sh"

TEST_TMPDIR=$(mktemp -d)
git init "$TEST_TMPDIR" -q
mkdir -p "$TEST_TMPDIR/.sweetclaude/state"

cleanup() { cd "$REPO_ROOT"; rm -rf "$TEST_TMPDIR"; }
trap cleanup EXIT

run_hook() {
  local cmd="$1"
  CLAUDE_TOOL_NAME="Bash" \
    GIT_DIR="$TEST_TMPDIR/.git" GIT_WORK_TREE="$TEST_TMPDIR" \
    bash "$HOOK" <<< "{\"command\": \"$cmd\"}"
}

# Test 1: non-commit command → allow (exit 0, no output)
touch "$TEST_TMPDIR/.sweetclaude/state/guardian-enabled"
echo "phase: implement" > "$TEST_TMPDIR/.sweetclaude/state/phase.yaml"
run_hook "npm test" 2>&1
[ $? -eq 0 ] && pass "non-commit command → exit 0" || fail "non-commit command → exit 0" "exit $?"

# Test 2: guardian not enabled → allow commit (no warning)
rm "$TEST_TMPDIR/.sweetclaude/state/guardian-enabled"
OUT=$(run_hook "git commit -m 'test'" 2>&1)
[ $? -eq 0 ] && pass "guardian off → exit 0" || fail "guardian off → exit 0" "exit $?"
echo "$OUT" | grep -qi "warning" && fail "guardian off → no warning expected" "$OUT" || pass "guardian off → no warning output"

# Test 3: guardian enabled, implement phase, no test files → warning
touch "$TEST_TMPDIR/.sweetclaude/state/guardian-enabled"
echo '{"test_files_written":[],"artifacts_created":[],"tdd_status":"pending"}' \
  > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'wip'" 2>&1)
echo "$OUT" | grep -qi "warning\|WARNING" && pass "no tests → warning printed" || fail "no tests → expected warning" "$OUT"

# Test 4: implement phase, tests present, tdd green → no warning
echo '{"test_files_written":["src/app.test.js"],"artifacts_created":[],"tdd_status":"green"}' \
  > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'feat: done'" 2>&1)
echo "$OUT" | grep -qi "warning\|WARNING" && fail "green tests → no warning expected" "$OUT" || pass "green tests → no warning"

# Test 5: design phase, no artifacts → warning
echo "phase: design" > "$TEST_TMPDIR/.sweetclaude/state/phase.yaml"
echo '{"test_files_written":[],"artifacts_created":[],"tdd_status":"pending"}' \
  > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'wip'" 2>&1)
echo "$OUT" | grep -qi "warning\|WARNING" && pass "design, no artifacts → warning" || fail "design, no artifacts → expected warning" "$OUT"

# Test 6: define phase, no artifacts → warning
echo "phase: define" > "$TEST_TMPDIR/.sweetclaude/state/phase.yaml"
echo '{"test_files_written":[],"artifacts_created":[],"tdd_status":"pending"}' \
  > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'wip'" 2>&1)
echo "$OUT" | grep -qi "warning\|WARNING" && pass "define, no artifacts → warning" || fail "define, no artifacts → expected warning" "$OUT"

# Test 7: design phase, session file missing → warning
echo "phase: design" > "$TEST_TMPDIR/.sweetclaude/state/phase.yaml"
rm -f "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'wip'" 2>&1)
echo "$OUT" | grep -qi "warning\|WARNING" && pass "design, no session file → warning" || fail "design, no session file → expected warning" "$OUT"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
