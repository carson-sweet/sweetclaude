#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Tests for artifact-guardian.sh

PASS=0
FAIL=0

pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1 (got: $2)"; FAIL=$((FAIL + 1)); }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/hooks/artifact-guardian.sh"
HOOK_STDIN="$REPO_ROOT/tests/hook_stdin.py"

TEST_TMPDIR=$(mktemp -d)
git init "$TEST_TMPDIR" -q
mkdir -p "$TEST_TMPDIR/.sweetclaude/state"

cleanup() { cd "$REPO_ROOT"; rm -rf "$TEST_TMPDIR"; }
trap cleanup EXIT

SC_YAML="$TEST_TMPDIR/.sweetclaude/state/sweetclaude.yaml"

write_phase() {
  local phase="$1"
  python3 -c "
import yaml, sys
d = {
    'schema_version': 1,
    'project': {'name': 'test', 'type': 'existing-code', 'version_stage': 'BETA', 'safety_snapshot': ''},
    'session': {'deference_level': 'collaborative', 'default_action': None},
    'work': {
        'last_item_id': None,
        'active': {
            'id': 'WI-001', 'type': 'net-new-feature',
            'workflow': [], 'phase': sys.argv[1],
            'title': 'test', 'started': None, 'entry_category': None,
        },
    },
    'features': {},
    'framework': {'installed_version': '3.0.0', 'setup_complete': True,
                  'hook_last_ran': None, 'consistency': {'last_checked': None, 'status': 'ok', 'drift': [], 'check_error': None},
                  'update': {'available': None, 'last_checked': None, 'declined': False, 'check_error': None}},
    'work_history': [], 'learnings': [],
}
yaml.dump(d, open(sys.argv[2], 'w'), default_flow_style=False)
" "$phase" "$SC_YAML"
}

run_hook() {
  local cmd="$1"
  local stdin
  stdin=$(python3 "$HOOK_STDIN" payload PreToolUse-Bash "$(cd "$TEST_TMPDIR" && pwd -P)" command="$cmd")
  env -u CLAUDE_TOOL_NAME -u CLAUDE_FILE_PATH -u CLAUDE_TRANSCRIPT_PATH \
    GIT_DIR="$TEST_TMPDIR/.git" GIT_WORK_TREE="$TEST_TMPDIR" \
    bash "$HOOK" <<< "$stdin"
}

# Test 1: non-commit command → allow (exit 0, no output)
touch "$TEST_TMPDIR/.sweetclaude/state/guardian-enabled"
write_phase "IMPLEMENT"
run_hook "npm test" 2>&1
[ $? -eq 0 ] && pass "non-commit command → exit 0" || fail "non-commit command → exit 0" "exit $?"

# Test 2: guardian not enabled → allow commit (no warning)
rm "$TEST_TMPDIR/.sweetclaude/state/guardian-enabled"
OUT=$(run_hook "git commit -m 'test'" 2>&1)
[ $? -eq 0 ] && pass "guardian off → exit 0" || fail "guardian off → exit 0" "exit $?"
echo "$OUT" | grep -qi "warning" && fail "guardian off → no warning expected" "$OUT" || pass "guardian off → no warning output"

# Test 3: guardian enabled, implement phase, no test files → warning
touch "$TEST_TMPDIR/.sweetclaude/state/guardian-enabled"
write_phase "IMPLEMENT"
echo '{"test_files_written":[],"artifacts_created":[],"tdd_status":"pending"}' \
  > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'wip'" 2>/dev/null)
echo "$OUT" | grep -qi "warning\|WARNING" && pass "no tests → warning printed" || fail "no tests → expected warning" "$OUT"
echo "$OUT" | grep -q '"additionalContext"' && pass "warning delivered as additionalContext" || fail "warning must be additionalContext on stdout" "$OUT"
echo "$OUT" | grep -q '"permissionDecision": *"deny"\|"decision": *"block"' && fail "warning must not block" "$OUT" || pass "warning does not block"

# Test 4: implement phase, tests present, tdd green → no warning
echo '{"test_files_written":["src/app.test.js"],"artifacts_created":[],"tdd_status":"green"}' \
  > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'feat: done'" 2>&1)
echo "$OUT" | grep -qi "warning\|WARNING" && fail "green tests → no warning expected" "$OUT" || pass "green tests → no warning"

# Test 5: design phase, no artifacts → warning
write_phase "DESIGN"
echo '{"test_files_written":[],"artifacts_created":[],"tdd_status":"pending"}' \
  > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'wip'" 2>/dev/null)
echo "$OUT" | grep -qi "warning\|WARNING" && pass "design, no artifacts → warning" || fail "design, no artifacts → expected warning" "$OUT"

# Test 6: define phase, no artifacts → warning
write_phase "DEFINE"
echo '{"test_files_written":[],"artifacts_created":[],"tdd_status":"pending"}' \
  > "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'wip'" 2>/dev/null)
echo "$OUT" | grep -qi "warning\|WARNING" && pass "define, no artifacts → warning" || fail "define, no artifacts → expected warning" "$OUT"

# Test 7: design phase, session file missing → warning
write_phase "DESIGN"
rm -f "$TEST_TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'wip'" 2>/dev/null)
echo "$OUT" | grep -qi "warning\|WARNING" && pass "design, no session file → warning" || fail "design, no session file → expected warning" "$OUT"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
