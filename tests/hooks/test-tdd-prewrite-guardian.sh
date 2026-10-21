#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Tests for tdd-prewrite-guardian.sh

PASS=0
FAIL=0

pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1 (got: $2)"; FAIL=$((FAIL + 1)); }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/hooks/tdd-prewrite-guardian.sh"

TEST_TMPDIR=$(mktemp -d)
git init "$TEST_TMPDIR" -q
mkdir -p "$TEST_TMPDIR/.sweetclaude/state"
mkdir -p "$TEST_TMPDIR/src"

cleanup() { cd "$REPO_ROOT"; rm -rf "$TEST_TMPDIR"; }
trap cleanup EXIT

HOOK_STDIN="$REPO_ROOT/tests/hook_stdin.py"
ERRFILE="$TEST_TMPDIR/hook-stderr"

run_hook() {
  local file="$1"
  local tool="${2:-Write}"
  local kind="PreToolUse-Write"
  [ "$tool" = "Edit" ] && kind="PreToolUse-Edit"
  local stdin out rc=0
  stdin=$(python3 "$HOOK_STDIN" payload "$kind" "$(cd "$TEST_TMPDIR" && pwd -P)" --tool "$tool" file_path="$file")
  out=$(env -u CLAUDE_TOOL_NAME -u CLAUDE_FILE_PATH -u CLAUDE_TRANSCRIPT_PATH \
    GIT_DIR="$TEST_TMPDIR/.git" GIT_WORK_TREE="$TEST_TMPDIR" \
    bash "$HOOK" <<< "$stdin" 2>"$ERRFILE") || rc=$?
  printf '%s' "$out" | python3 "$HOOK_STDIN" verdict "$rc" "$ERRFILE"
}

# Test 1: guardian not enabled → allow
OUT=$(run_hook "$TEST_TMPDIR/src/app.js" "Write")
[ "$OUT" = "allow" ] && pass "guardian off → allow" || fail "guardian off → allow" "$OUT"

# Test 2: non Write/Edit tool → allow
touch "$TEST_TMPDIR/.sweetclaude/state/guardian-enabled"
echo "phase: implement" > "$TEST_TMPDIR/.sweetclaude/state/phase.yaml"
OUT=$(run_hook "$TEST_TMPDIR/src/app.js" "Read")
[ "$OUT" = "allow" ] && pass "non Write/Edit tool → allow" || fail "non Write/Edit tool → allow" "$OUT"

# Test 3: guardian enabled, non-implement phase → allow
echo "phase: define" > "$TEST_TMPDIR/.sweetclaude/state/phase.yaml"
OUT=$(run_hook "$TEST_TMPDIR/src/app.js" "Write")
[ "$OUT" = "allow" ] && pass "non-implement phase → allow" || fail "non-implement phase → allow" "$OUT"

# Test 4: implement phase, writing a test file → allow
echo "phase: implement" > "$TEST_TMPDIR/.sweetclaude/state/phase.yaml"
echo '{"test_files_written":[]}' > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "$TEST_TMPDIR/src/app.test.js" "Write")
[ "$OUT" = "allow" ] && pass "writing test file → allow" || fail "writing test file → allow" "$OUT"

# Test 5: implement phase, source file, no test evidence → block
OUT=$(run_hook "$TEST_TMPDIR/src/app.js" "Write")
[ "$OUT" = "deny" ] && pass "source write, no tests → block" || fail "source write, no tests → block" "$OUT"

# Test 6: implement phase, source file, test evidence in session state → allow
echo '{"test_files_written":["src/app.test.js"]}' > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "$TEST_TMPDIR/src/app.js" "Write")
[ "$OUT" = "allow" ] && pass "source write, test in session state → allow" || fail "source write, test in session state → allow" "$OUT"

# Test 7: config file (json ext) → allow
echo '{"test_files_written":[]}' > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "$TEST_TMPDIR/.eslintrc.json" "Write")
[ "$OUT" = "allow" ] && pass "config file → allow" || fail "config file → allow" "$OUT"

# Test 8: markdown file → allow
OUT=$(run_hook "$TEST_TMPDIR/docs/readme.md" "Write")
[ "$OUT" = "allow" ] && pass "markdown file → allow" || fail "markdown file → allow" "$OUT"

# Test 9: Makefile in source dir → allow (extensionless build file)
echo '{"test_files_written":[]}' > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "$TEST_TMPDIR/src/Makefile" "Write")
[ "$OUT" = "allow" ] && pass "Makefile → allow" || fail "Makefile → allow" "$OUT"

# Test 10: path with TestimonialService.java (not a test file) → block
OUT=$(run_hook "$TEST_TMPDIR/src/TestimonialService.java" "Write")
[ "$OUT" = "deny" ] && pass "TestimonialService.java → block" || fail "TestimonialService.java → block" "$OUT"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
