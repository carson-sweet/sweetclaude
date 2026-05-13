#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Tests the BL-068 UserPromptSubmit hook: hooks/migration-decision-reminder.sh.
#
# Verifies:
#   - Silent (no JSON beyond {"ok": true}) when marker file is absent.
#   - Increments turn_count and emits a reminder under 10 turns.
#   - Hard-blocks (continue:false) at turn 10+.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$REPO_ROOT/hooks/migration-decision-reminder.sh"

FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

TEST_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR" EXIT

(
  cd "$TEST_TMPDIR"
  git init -q -b main 2>/dev/null
)

# ---------------------------------------------------------------------------
# Test 1: no marker → silent ({"ok": true})
# ---------------------------------------------------------------------------

echo "[1] no marker → silent"
OUT=$(cd "$TEST_TMPDIR" && bash "$HOOK" 2>/dev/null)
echo "$OUT" | grep -q '"ok": true' \
  && pass "hook emits {\"ok\": true} when no marker present" \
  || fail "expected ok:true, got: $OUT"

# ---------------------------------------------------------------------------
# Test 2: marker present, first turn → reminder, turn_count incremented
# ---------------------------------------------------------------------------

echo "[2] turn 1 — reminder, no hard-block"

mkdir -p "$TEST_TMPDIR/.sweetclaude/state"
cat > "$TEST_TMPDIR/.sweetclaude/state/pending-migration-decision.yaml" << 'YAML'
created_at: "2026-05-11T13:42:00Z"
snapshot:
  tarball_path: ".sweetclaude/state/backups/pre-migration-test.tar.gz"
  git_tag: "pre-migration-test"
  paths_in_tarball:
    - ".sweetclaude"
turn_count: 0
YAML

OUT=$(cd "$TEST_TMPDIR" && bash "$HOOK" 2>/dev/null)

echo "$OUT" | grep -q '"continue":false' \
  && fail "hook should NOT hard-block on turn 1: $OUT" \
  || pass "hook does not hard-block on turn 1"

echo "$OUT" | grep -q 'Pending migration decision (turn 1/10)' \
  && pass "reminder message shows 'turn 1/10'" \
  || fail "reminder text wrong: $OUT"

# Verify turn_count was incremented to 1.
COUNT=$(python3 -c "
import yaml
d = yaml.safe_load(open('$TEST_TMPDIR/.sweetclaude/state/pending-migration-decision.yaml'))
print(d.get('turn_count'))
")
[ "$COUNT" = "1" ] && pass "turn_count incremented to 1" || fail "turn_count: $COUNT"

# ---------------------------------------------------------------------------
# Test 3: bump to turn 9 → still reminder
# ---------------------------------------------------------------------------

echo "[3] turn 9 — still reminder"
python3 -c "
import yaml
with open('$TEST_TMPDIR/.sweetclaude/state/pending-migration-decision.yaml') as f:
    d = yaml.safe_load(f)
d['turn_count'] = 8
with open('$TEST_TMPDIR/.sweetclaude/state/pending-migration-decision.yaml', 'w') as f:
    yaml.safe_dump(d, f)
"

OUT=$(cd "$TEST_TMPDIR" && bash "$HOOK" 2>/dev/null)
echo "$OUT" | grep -q '"continue":false' \
  && fail "hook hard-blocks at turn 9: $OUT" \
  || pass "no hard-block at turn 9"
echo "$OUT" | grep -q 'turn 9/10' && pass "shows 'turn 9/10'" || fail "msg: $OUT"

# ---------------------------------------------------------------------------
# Test 4: turn 10 → hard-block (continue:false)
# ---------------------------------------------------------------------------

echo "[4] turn 10 — hard-block"
OUT=$(cd "$TEST_TMPDIR" && bash "$HOOK" 2>/dev/null)
echo "$OUT" | grep -q '"continue":false' \
  && pass "hook hard-blocks at turn 10" \
  || fail "expected continue:false at turn 10, got: $OUT"
echo "$OUT" | grep -q 'limit reached' && pass "block message says 'limit reached'" || fail "msg: $OUT"

# ---------------------------------------------------------------------------

echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "FAILURES: $FAILED"
  exit 1
fi
