#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Behavioral tests for drift-gate.sh and master-preflight.sh.
# Uses isolated fixture environments with fake git repos and controlled
# HOME directories to avoid touching the real environment.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

TMPROOT=$(mktemp -d)
trap "rm -rf $TMPROOT" EXIT

_make_git_repo() {
  local dir="$1"
  mkdir -p "$dir"
  git -C "$dir" init -q 2>/dev/null
}

# ---------------------------------------------------------------------------
# Test 1: drift-gate.sh writes marker and emits AskUserQuestion JSON on drift
# ---------------------------------------------------------------------------
echo "[1] drift-gate.sh: writes marker and emits AskUserQuestion when drift found"

FX1_HOME="$TMPROOT/home1"
FX1_PROJ="$TMPROOT/proj1"
mkdir -p "$FX1_HOME/.claude/scripts/sweetclaude/migrations"
cat > "$FX1_HOME/.claude/scripts/sweetclaude/migrations/runner.py" << 'PYEOF'
import sys
print("DRIFT_COUNT=1")
print("FINDING|sweetclaude.yaml|v1->v2|chain=ok")
PYEOF

_make_git_repo "$FX1_PROJ"
mkdir -p "$FX1_PROJ/.sweetclaude/state"
printf 'schema_version: 1\n' > "$FX1_PROJ/.sweetclaude/state/sweetclaude.yaml"

OUTPUT1=$(cd "$FX1_PROJ" && HOME="$FX1_HOME" bash "$REPO_ROOT/hooks/drift-gate.sh" 2>/dev/null) || true
MARKER1="$FX1_PROJ/.sweetclaude/state/pending-drift-decision.yaml"

if [ -f "$MARKER1" ]; then
  pass "marker written at .sweetclaude/state/pending-drift-decision.yaml"
else
  fail "marker not written"
fi

if printf '%s' "$OUTPUT1" | python3 -c "
import sys, json
raw = sys.stdin.read().strip()
if not raw: sys.exit(1)
d = json.loads(raw)
ctx = d.get('hookSpecificOutput', {}).get('additionalContext', '')
sys.exit(0 if 'AskUserQuestion' in ctx else 1)
" 2>/dev/null; then
  pass "stdout JSON contains AskUserQuestion instruction"
else
  fail "stdout JSON missing AskUserQuestion (got: $(printf '%s' "$OUTPUT1" | head -c 200))"
fi

# ---------------------------------------------------------------------------
# Test 2: drift-gate.sh is silent for non-SweetClaude project
# ---------------------------------------------------------------------------
echo "[2] drift-gate.sh: silent for non-SweetClaude project"

FX2_PROJ="$TMPROOT/proj2"
FX2_HOME="$TMPROOT/home2"
mkdir -p "$FX2_HOME/.claude"
_make_git_repo "$FX2_PROJ"

OUTPUT2=$(cd "$FX2_PROJ" && HOME="$FX2_HOME" bash "$REPO_ROOT/hooks/drift-gate.sh" 2>/dev/null) || true
if [ -z "$OUTPUT2" ]; then
  pass "silent for non-SweetClaude project"
else
  fail "unexpected output for non-SC project: $(printf '%s' "$OUTPUT2" | head -c 100)"
fi

# ---------------------------------------------------------------------------
# Test 3: drift-gate.sh re-surfaces pre-existing marker without running runner
# ---------------------------------------------------------------------------
echo "[3] drift-gate.sh: re-surfaces pre-existing marker without runner"

FX3_PROJ="$TMPROOT/proj3"
FX3_HOME="$TMPROOT/home3"
mkdir -p "$FX3_HOME/.claude"
_make_git_repo "$FX3_PROJ"
mkdir -p "$FX3_PROJ/.sweetclaude/state"
printf 'schema_version: 2\n' > "$FX3_PROJ/.sweetclaude/state/sweetclaude.yaml"
printf 'case: A\ndrift_count: 2\nfindings: []\n' \
  > "$FX3_PROJ/.sweetclaude/state/pending-drift-decision.yaml"

OUTPUT3=$(cd "$FX3_PROJ" && HOME="$FX3_HOME" bash "$REPO_ROOT/hooks/drift-gate.sh" 2>/dev/null) || true
if printf '%s' "$OUTPUT3" | python3 -c "
import sys, json
raw = sys.stdin.read().strip()
if not raw: sys.exit(1)
d = json.loads(raw)
ctx = d.get('hookSpecificOutput', {}).get('additionalContext', '')
sys.exit(0 if 'AskUserQuestion' in ctx else 1)
" 2>/dev/null; then
  pass "re-surfaced pre-existing marker without runner"
else
  fail "did not re-surface pre-existing marker (got: $(printf '%s' "$OUTPUT3" | head -c 200))"
fi

# ---------------------------------------------------------------------------
# Test 4: master-preflight.sh blocks sweetclaude:* when bootstrap has not run
# ---------------------------------------------------------------------------
echo "[4] master-preflight.sh: blocks sweetclaude:* without bootstrap session flag"

FX4_PROJ="$TMPROOT/proj4"
_make_git_repo "$FX4_PROJ"
mkdir -p "$FX4_PROJ/.sweetclaude/state"
printf 'schema_version: 2\n' > "$FX4_PROJ/.sweetclaude/state/sweetclaude.yaml"

RESULT4=$(cd "$FX4_PROJ" && \
  printf '%s' '{"tool_input": {"skill": "sweetclaude:status"}}' \
  | env CLAUDE_TOOL_NAME=Skill bash "$REPO_ROOT/hooks/master-preflight.sh" 2>/dev/null) || true

if printf '%s' "$RESULT4" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
sys.exit(0 if d.get('ok') == False else 1)
" 2>/dev/null; then
  pass "blocks sweetclaude:status without bootstrap flag"
else
  fail "should block without bootstrap flag (got: $RESULT4)"
fi

# ---------------------------------------------------------------------------
# Test 5: master-preflight.sh allows sweetclaude:* when bootstrap flag exists
# ---------------------------------------------------------------------------
echo "[5] master-preflight.sh: allows sweetclaude:* when bootstrap session flag present"

FX5_PROJ="$TMPROOT/proj5"
_make_git_repo "$FX5_PROJ"
mkdir -p "$FX5_PROJ/.sweetclaude/state"
printf 'schema_version: 2\n' > "$FX5_PROJ/.sweetclaude/state/sweetclaude.yaml"

FX5_ROOT=$(cd "$FX5_PROJ" && git rev-parse --show-toplevel)
PROJ5_HASH=$(printf '%s' "$FX5_ROOT" | md5 2>/dev/null \
  || printf '%s' "$FX5_ROOT" | md5sum 2>/dev/null | cut -d' ' -f1)
touch "/tmp/.sweetclaude-bootstrap-ran-${PROJ5_HASH}"

RESULT5=$(cd "$FX5_PROJ" && \
  printf '%s' '{"tool_input": {"skill": "sweetclaude:status"}}' \
  | env CLAUDE_TOOL_NAME=Skill bash "$REPO_ROOT/hooks/master-preflight.sh" 2>/dev/null) || true

rm -f "/tmp/.sweetclaude-bootstrap-ran-${PROJ5_HASH}"

if printf '%s' "$RESULT5" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
  pass "allows sweetclaude:status with bootstrap flag"
else
  fail "should allow with bootstrap flag (got: $RESULT5)"
fi

# ---------------------------------------------------------------------------
# Test 6: master-preflight.sh exempts lifecycle skills unconditionally
# ---------------------------------------------------------------------------
echo "[6] master-preflight.sh: lifecycle skills exempt (no bootstrap flag needed)"

FX6_PROJ="$TMPROOT/proj6"
_make_git_repo "$FX6_PROJ"
mkdir -p "$FX6_PROJ/.sweetclaude/state"
printf 'schema_version: 2\n' > "$FX6_PROJ/.sweetclaude/state/sweetclaude.yaml"

EXEMPT_FAIL=0
for exempted in \
  sweetclaude:bootstrap sweetclaude:update sweetclaude:_migrate \
  sweetclaude:purge sweetclaude:setup sweetclaude:adopt; do
  RES=$(cd "$FX6_PROJ" && \
    printf '%s' "{\"tool_input\": {\"skill\": \"$exempted\"}}" \
    | env CLAUDE_TOOL_NAME=Skill bash "$REPO_ROOT/hooks/master-preflight.sh" 2>/dev/null) || true
  if printf '%s' "$RES" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
    :
  else
    fail "$exempted should be exempt but was blocked (got: $RES)"
    EXEMPT_FAIL=$((EXEMPT_FAIL + 1))
  fi
done
[ "$EXEMPT_FAIL" -eq 0 ] && pass "all lifecycle skills exempt without bootstrap flag"

# ---------------------------------------------------------------------------
# Test 7: master-preflight.sh passes non-sweetclaude:* skills through
# ---------------------------------------------------------------------------
echo "[7] master-preflight.sh: non-sweetclaude:* skills pass through unconditionally"

RESULT7=$(printf '%s' '{"tool_input": {"skill": "other-plugin:do-something"}}' \
  | env CLAUDE_TOOL_NAME=Skill bash "$REPO_ROOT/hooks/master-preflight.sh" 2>/dev/null) || true

if printf '%s' "$RESULT7" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
  pass "non-sweetclaude skill passes through"
else
  fail "non-sweetclaude skill should pass through (got: $RESULT7)"
fi

# ---------------------------------------------------------------------------
# Test 8: session-preflight.sh does NOT heal for schema_version: 1
# ---------------------------------------------------------------------------
echo "[8] session-preflight.sh: no schema-version heal for schema_version: 1"

FX8_HOME="$TMPROOT/home8"
FX8_PROJ="$TMPROOT/proj8"
mkdir -p "$FX8_HOME/.claude"
_make_git_repo "$FX8_PROJ"
mkdir -p "$FX8_PROJ/.sweetclaude/state"
printf 'schema_version: 1\nsetup_complete: true\n' > "$FX8_PROJ/.sweetclaude/state/sweetclaude.yaml"

OUTPUT8=$(cd "$FX8_PROJ" && HOME="$FX8_HOME" bash "$REPO_ROOT/hooks/session-preflight.sh" 2>/dev/null) || true
if printf '%s' "$OUTPUT8" | grep -q "unsupported schema version"; then
  fail "schema_version: 1 triggered unsupported-schema-version heal"
else
  pass "schema_version: 1 — no unsupported-schema-version heal"
fi

# ---------------------------------------------------------------------------
# Test 9: session-preflight.sh does NOT heal for schema_version: 2
# ---------------------------------------------------------------------------
echo "[9] session-preflight.sh: no schema-version heal for schema_version: 2"

FX9_HOME="$TMPROOT/home9"
FX9_PROJ="$TMPROOT/proj9"
mkdir -p "$FX9_HOME/.claude"
_make_git_repo "$FX9_PROJ"
mkdir -p "$FX9_PROJ/.sweetclaude/state"
printf 'schema_version: 2\nsetup_complete: true\n' > "$FX9_PROJ/.sweetclaude/state/sweetclaude.yaml"

OUTPUT9=$(cd "$FX9_PROJ" && HOME="$FX9_HOME" bash "$REPO_ROOT/hooks/session-preflight.sh" 2>/dev/null) || true
if printf '%s' "$OUTPUT9" | grep -q "unsupported schema version"; then
  fail "schema_version: 2 triggered unsupported-schema-version heal"
else
  pass "schema_version: 2 — no unsupported-schema-version heal"
fi

# ---------------------------------------------------------------------------
# Test 10: session-preflight.sh DOES heal for schema_version: 3
# ---------------------------------------------------------------------------
echo "[10] session-preflight.sh: heals for unsupported schema_version: 3"

FX10_HOME="$TMPROOT/home10"
FX10_PROJ="$TMPROOT/proj10"
mkdir -p "$FX10_HOME/.claude"
_make_git_repo "$FX10_PROJ"
mkdir -p "$FX10_PROJ/.sweetclaude/state"
printf 'schema_version: 3\nsetup_complete: true\n' > "$FX10_PROJ/.sweetclaude/state/sweetclaude.yaml"

OUTPUT10=$(cd "$FX10_PROJ" && HOME="$FX10_HOME" bash "$REPO_ROOT/hooks/session-preflight.sh" 2>/dev/null) || true
if printf '%s' "$OUTPUT10" | grep -q "unsupported schema version"; then
  pass "schema_version: 3 triggers unsupported-schema-version heal"
else
  fail "schema_version: 3 should trigger heal (got: $(printf '%s' "$OUTPUT10" | head -c 200))"
fi

# ---------------------------------------------------------------------------
# Test 11: test-guardian.sh — phase inactive → ok
# ---------------------------------------------------------------------------
echo "[11] test-guardian.sh: allows test file edit when phase is not implement"

FX11_HOME="$TMPROOT/home11"
FX11_PROJ="$TMPROOT/proj11"
mkdir -p "$FX11_HOME/.claude"
_make_git_repo "$FX11_PROJ"
mkdir -p "$FX11_PROJ/.sweetclaude/state"
printf 'phase: discover\ntdd_phase:\n' > "$FX11_PROJ/.sweetclaude/state/phase.yaml"

RESULT11=$(cd "$FX11_PROJ" && \
  env HOME="$FX11_HOME" CLAUDE_FILE_PATH="$FX11_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT11" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
  pass "phase inactive → ok for test file edit"
else
  fail "should allow test file edit when phase is not implement (got: $RESULT11)"
fi

# ---------------------------------------------------------------------------
# Test 12: test-guardian.sh — phase active + implementing + test file → blocked
# ---------------------------------------------------------------------------
echo "[12] test-guardian.sh: blocks test file edit during implement/implementing"

FX12_HOME="$TMPROOT/home12"
FX12_PROJ="$TMPROOT/proj12"
mkdir -p "$FX12_HOME/.claude"
_make_git_repo "$FX12_PROJ"
mkdir -p "$FX12_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX12_PROJ/.sweetclaude/state/phase.yaml"

RESULT12=$(cd "$FX12_PROJ" && \
  env HOME="$FX12_HOME" CLAUDE_FILE_PATH="$FX12_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Edit \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT12" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == False else 1)
" 2>/dev/null; then
  pass "blocks test file edit during implement/implementing"
else
  fail "should block test file edit (got: $RESULT12)"
fi

# ---------------------------------------------------------------------------
# Test 13: test-guardian.sh — phase active + implementing + non-test file → ok
# ---------------------------------------------------------------------------
echo "[13] test-guardian.sh: allows non-test file edit during implement/implementing"

FX13_HOME="$TMPROOT/home13"
FX13_PROJ="$TMPROOT/proj13"
mkdir -p "$FX13_HOME/.claude"
_make_git_repo "$FX13_PROJ"
mkdir -p "$FX13_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX13_PROJ/.sweetclaude/state/phase.yaml"

RESULT13=$(cd "$FX13_PROJ" && \
  env HOME="$FX13_HOME" CLAUDE_FILE_PATH="$FX13_PROJ/src/main.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT13" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
  pass "allows non-test file during implement/implementing"
else
  fail "should allow non-test file (got: $RESULT13)"
fi

# ---------------------------------------------------------------------------
# Test 14: test-guardian.sh — phase active + non-implementing tdd_phase → ok
# ---------------------------------------------------------------------------
echo "[14] test-guardian.sh: allows test file edit when tdd_phase is not implementing"

FX14_HOME="$TMPROOT/home14"
FX14_PROJ="$TMPROOT/proj14"
mkdir -p "$FX14_HOME/.claude"
_make_git_repo "$FX14_PROJ"
mkdir -p "$FX14_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: writing_tests\n' > "$FX14_PROJ/.sweetclaude/state/phase.yaml"

RESULT14=$(cd "$FX14_PROJ" && \
  env HOME="$FX14_HOME" CLAUDE_FILE_PATH="$FX14_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT14" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
  pass "allows test file when tdd_phase is writing_tests"
else
  fail "should allow test file when tdd_phase is not implementing (got: $RESULT14)"
fi

# ---------------------------------------------------------------------------
# Test 15: test-guardian.sh — non-Write/Edit tool → ok
# ---------------------------------------------------------------------------
echo "[15] test-guardian.sh: passes through non-Write/Edit tools"

FX15_HOME="$TMPROOT/home15"
FX15_PROJ="$TMPROOT/proj15"
mkdir -p "$FX15_HOME/.claude"
_make_git_repo "$FX15_PROJ"
mkdir -p "$FX15_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX15_PROJ/.sweetclaude/state/phase.yaml"

RESULT15=$(cd "$FX15_PROJ" && \
  env HOME="$FX15_HOME" CLAUDE_FILE_PATH="$FX15_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Bash \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT15" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
  pass "non-Write/Edit tool passes through"
else
  fail "Bash tool should pass through even during implement (got: $RESULT15)"
fi

# ---------------------------------------------------------------------------
# Test 16: test-guardian.sh — IMPLEMENT uppercase → blocked
# ---------------------------------------------------------------------------
echo "[16] test-guardian.sh: blocks on uppercase IMPLEMENT"

FX16_HOME="$TMPROOT/home16"
FX16_PROJ="$TMPROOT/proj16"
mkdir -p "$FX16_HOME/.claude"
_make_git_repo "$FX16_PROJ"
mkdir -p "$FX16_PROJ/.sweetclaude/state"
printf 'phase: IMPLEMENT\ntdd_phase: implementing\n' > "$FX16_PROJ/.sweetclaude/state/phase.yaml"

RESULT16=$(cd "$FX16_PROJ" && \
  env HOME="$FX16_HOME" CLAUDE_FILE_PATH="$FX16_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT16" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == False else 1)
" 2>/dev/null; then
  pass "blocks on uppercase IMPLEMENT"
else
  fail "should block on uppercase IMPLEMENT (got: $RESULT16)"
fi

# ---------------------------------------------------------------------------
# Test 17: auto-test-runner.sh — phase inactive → no test execution
# ---------------------------------------------------------------------------
echo "[17] auto-test-runner.sh: no test execution when phase is not implement"

FX17_HOME="$TMPROOT/home17"
FX17_PROJ="$TMPROOT/proj17"
FX17_MARKER="$TMPROOT/marker17"
mkdir -p "$FX17_HOME/.claude"
_make_git_repo "$FX17_PROJ"
mkdir -p "$FX17_PROJ/.sweetclaude/state"
printf 'phase: discover\ntdd_phase: writing_tests\n' > "$FX17_PROJ/.sweetclaude/state/phase.yaml"
printf 'test:\n  test_command: touch %s\n' "$FX17_MARKER" > "$FX17_PROJ/.sweetclaude/state/project.yaml"

(cd "$FX17_PROJ" && \
  env HOME="$FX17_HOME" CLAUDE_FILE_PATH="$FX17_PROJ/src/main.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/auto-test-runner.sh" 2>/dev/null) || true

sleep 0.5
if [ ! -f "$FX17_MARKER" ]; then
  pass "no test execution when phase inactive"
else
  fail "test command should not run when phase is not implement"
fi

# ---------------------------------------------------------------------------
# Test 18: auto-test-runner.sh — phase active + source file → runs test command
# ---------------------------------------------------------------------------
echo "[18] auto-test-runner.sh: runs test command for source file edit during implement"

FX18_HOME="$TMPROOT/home18"
FX18_PROJ="$TMPROOT/proj18"
FX18_MARKER="$TMPROOT/marker18"
mkdir -p "$FX18_HOME/.claude"
_make_git_repo "$FX18_PROJ"
mkdir -p "$FX18_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX18_PROJ/.sweetclaude/state/phase.yaml"
printf 'test:\n  test_command: touch %s\n' "$FX18_MARKER" > "$FX18_PROJ/.sweetclaude/state/project.yaml"

(cd "$FX18_PROJ" && \
  env HOME="$FX18_HOME" CLAUDE_FILE_PATH="$FX18_PROJ/src/main.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/auto-test-runner.sh" 2>/dev/null) || true

for _i in 1 2 3 4 5; do
  [ -f "$FX18_MARKER" ] && break
  sleep 0.2 || true
done

if [ -f "$FX18_MARKER" ]; then
  pass "runs test command for source file during implement"
else
  fail "test command should run for source file edit during implement/implementing"
fi

# ---------------------------------------------------------------------------
# Test 19: auto-test-runner.sh — test file → no execution
# ---------------------------------------------------------------------------
echo "[19] auto-test-runner.sh: no test execution for test file edit"

FX19_HOME="$TMPROOT/home19"
FX19_PROJ="$TMPROOT/proj19"
FX19_MARKER="$TMPROOT/marker19"
mkdir -p "$FX19_HOME/.claude"
_make_git_repo "$FX19_PROJ"
mkdir -p "$FX19_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX19_PROJ/.sweetclaude/state/phase.yaml"
printf 'test:\n  test_command: touch %s\n' "$FX19_MARKER" > "$FX19_PROJ/.sweetclaude/state/project.yaml"

(cd "$FX19_PROJ" && \
  env HOME="$FX19_HOME" CLAUDE_FILE_PATH="$FX19_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Edit \
  bash "$REPO_ROOT/hooks/auto-test-runner.sh" 2>/dev/null) || true

sleep 0.5
if [ ! -f "$FX19_MARKER" ]; then
  pass "no test execution for test file edit"
else
  fail "test command should not run for test file edits"
fi

# ---------------------------------------------------------------------------
# Test 20: auto-test-runner.sh — non-Write/Edit tool → no execution
# ---------------------------------------------------------------------------
echo "[20] auto-test-runner.sh: no test execution for non-Write/Edit tools"

FX20_HOME="$TMPROOT/home20"
FX20_PROJ="$TMPROOT/proj20"
FX20_MARKER="$TMPROOT/marker20"
mkdir -p "$FX20_HOME/.claude"
_make_git_repo "$FX20_PROJ"
mkdir -p "$FX20_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX20_PROJ/.sweetclaude/state/phase.yaml"
printf 'test:\n  test_command: touch %s\n' "$FX20_MARKER" > "$FX20_PROJ/.sweetclaude/state/project.yaml"

(cd "$FX20_PROJ" && \
  env HOME="$FX20_HOME" CLAUDE_FILE_PATH="$FX20_PROJ/src/main.js" CLAUDE_TOOL_NAME=Bash \
  bash "$REPO_ROOT/hooks/auto-test-runner.sh" 2>/dev/null) || true

sleep 0.5
if [ ! -f "$FX20_MARKER" ]; then
  pass "no test execution for Bash tool"
else
  fail "test command should not run for non-Write/Edit tools"
fi

# ---------------------------------------------------------------------------
# Test 22: test-guardian.sh — implement phase + blank tdd_phase → ok
# ---------------------------------------------------------------------------
echo "[22] test-guardian.sh: allows edit when phase is implement but tdd_phase is blank"

FX22_HOME="$TMPROOT/home22"
FX22_PROJ="$TMPROOT/proj22"
mkdir -p "$FX22_HOME/.claude"
_make_git_repo "$FX22_PROJ"
mkdir -p "$FX22_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase:\n' > "$FX22_PROJ/.sweetclaude/state/phase.yaml"

RESULT22=$(cd "$FX22_PROJ" && \
  env HOME="$FX22_HOME" CLAUDE_FILE_PATH="$FX22_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT22" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
  pass "allows edit when phase is implement but tdd_phase is blank"
else
  fail "should allow edit when tdd_phase is blank even in implement phase (got: $RESULT22)"
fi

# ---------------------------------------------------------------------------
# Test 21: syntax validation — hook with syntax error fails bash -n
# ---------------------------------------------------------------------------
echo "[21] syntax validation: hook with syntax error fails bash -n"

BROKEN_HOOK="$TMPROOT/broken-hook.sh"
cp "$REPO_ROOT/hooks/test-guardian.sh" "$BROKEN_HOOK"
printf '\nif [[ ; then\n' >> "$BROKEN_HOOK"

if bash -n "$BROKEN_HOOK" 2>/dev/null; then
  fail "broken hook should fail bash -n syntax check"
else
  pass "broken hook fails bash -n (fail-closed)"
fi

# ---------------------------------------------------------------------------
echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "FAILURES: $FAILED"
  exit 1
fi
