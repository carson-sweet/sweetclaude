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
echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "FAILURES: $FAILED"
  exit 1
fi
