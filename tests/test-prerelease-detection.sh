#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Tests for scripts/maintenance/check-prerelease.py — the STORY-050 prerelease
# detection helper that gates whether /sweetclaude:update prompts the user
# about an available prerelease.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/maintenance/check-prerelease.py"
FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

run_check() {
    local installed="$1"; local declined="$2"; local tags="$3"
    local tags_file
    tags_file=$(mktemp)
    printf '%s' "$tags" > "$tags_file"
    python3 "$SCRIPT" --installed-version "$installed" --declined "$declined" --tags-file "$tags_file"
    rm -f "$tags_file"
}

assert_field() {
    local label="$1"; local result="$2"; local field="$3"; local expected="$4"
    local actual
    actual=$(echo "$result" | python3 -c "import sys,json; v=json.load(sys.stdin).get('$field'); print('null' if v is None else (str(v).lower() if isinstance(v, bool) else str(v)))")
    if [ "$actual" = "$expected" ]; then
        pass "$label → $field=$expected"
    else
        fail "$label → $field=$actual (expected $expected)"
    fi
}

echo "=== check-prerelease.py tests ==="

# 1. No prerelease tags exist
echo ""
echo "Case 1: tags list is empty"
result=$(run_check "3.68.4" "" "")
assert_field "empty tags" "$result" "prerelease_available" "null"
assert_field "empty tags" "$result" "should_prompt" "false"

# 2. Only stable tags
echo ""
echo "Case 2: only stable tags"
result=$(run_check "3.68.4" "" $'v3.68.0\nv3.68.1\nv3.68.4')
assert_field "only stable" "$result" "prerelease_available" "null"
assert_field "only stable" "$result" "should_prompt" "false"

# 3. Beta available, user on stable, never declined
echo ""
echo "Case 3: beta available, user on stable"
result=$(run_check "3.68.4" "" $'v3.68.4\nv4.0.0-beta')
assert_field "beta avail" "$result" "prerelease_available" "v4.0.0-beta"
assert_field "beta avail" "$result" "should_prompt" "true"

# 4. Beta available, but user previously declined that specific tag
echo ""
echo "Case 4: beta available but already declined"
result=$(run_check "3.68.4" "v4.0.0-beta" $'v3.68.4\nv4.0.0-beta')
assert_field "declined same" "$result" "prerelease_available" "v4.0.0-beta"
assert_field "declined same" "$result" "should_prompt" "false"

# 5. Beta available, user declined an OLDER prerelease — should prompt
echo ""
echo "Case 5: declined older beta, newer beta now available"
result=$(run_check "3.68.4" "v4.0.0-beta" $'v4.0.0-beta\nv4.0.0-beta2')
assert_field "newer beta" "$result" "prerelease_available" "v4.0.0-beta2"
assert_field "newer beta" "$result" "should_prompt" "true"

# 6. User already on the beta — same tag is "available", should not prompt
# (because they have it installed; check is against installed_version)
echo ""
echo "Case 6: user installed the beta — no newer prerelease available"
result=$(run_check "4.0.0-beta" "" $'v3.68.4\nv4.0.0-beta')
assert_field "on beta, no newer" "$result" "prerelease_available" "null"
assert_field "on beta, no newer" "$result" "should_prompt" "false"

# 7. User on beta, newer beta released — should prompt
echo ""
echo "Case 7: user on beta, newer beta exists"
result=$(run_check "4.0.0-beta" "" $'v4.0.0-beta\nv4.0.0-beta2')
assert_field "beta → newer beta" "$result" "prerelease_available" "v4.0.0-beta2"
assert_field "beta → newer beta" "$result" "should_prompt" "true"

# 8. Beta and RC both available — RC wins (higher channel)
echo ""
echo "Case 8: beta and rc both available — rc wins"
result=$(run_check "3.68.4" "" $'v4.0.0-beta\nv4.0.0-rc1')
assert_field "rc beats beta" "$result" "prerelease_available" "v4.0.0-rc1"
assert_field "rc beats beta" "$result" "should_prompt" "true"

# 9. Alpha < beta < rc — beta wins over alpha
echo ""
echo "Case 9: alpha and beta — beta wins"
result=$(run_check "3.68.4" "" $'v4.0.0-alpha\nv4.0.0-beta')
assert_field "beta beats alpha" "$result" "prerelease_available" "v4.0.0-beta"

# 10. Malformed installed_version
echo ""
echo "Case 10: unknown installed version"
result=$(run_check "" "" $'v4.0.0-beta')
assert_field "empty installed" "$result" "should_prompt" "false"

# 11. Prerelease tag for a LOWER version than installed — should not prompt
echo ""
echo "Case 11: prerelease for older version — no prompt"
result=$(run_check "5.0.0" "" $'v4.0.0-beta')
assert_field "old prerelease" "$result" "prerelease_available" "null"
assert_field "old prerelease" "$result" "should_prompt" "false"

# 12. Tag without leading 'v' is rejected (not a recognized prerelease)
echo ""
echo "Case 12: tag without 'v' prefix is ignored"
result=$(run_check "3.68.4" "" $'4.0.0-beta')
assert_field "no v prefix" "$result" "prerelease_available" "null"

echo ""
if [ "$FAILED" -gt 0 ]; then
    echo "=== FAILED: $FAILED check(s) ==="
    exit 1
else
    echo "=== ALL PASSED ==="
    exit 0
fi
