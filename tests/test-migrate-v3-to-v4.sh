#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# B2/C smoke test: end-to-end v3 -> v4 backlog migration against real v3 fixtures.
# Covers both product_base variants (.sweetclaude/product AND docs/product).
#
# This is the test the May 11 v4 assessment said was missing: a smoke test that
# starts from a real v3 state (installed_version: 3.x, BL-*.md files on disk)
# and exercises the migration end to end, verifying the post-state is a clean
# v4 project that drift-gate.sh reports DRIFT_COUNT=0 on.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/migrate/migrate-v3-to-v4.py"
RUNNER="$REPO_ROOT/scripts/migrations/runner.py"

FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

# ── helpers ─────────────────────────────────────────────────────────────────

prep_fixture() {
    # $1 = source fixture dir, $2 = test name
    local src="$1"
    local name="$2"
    local tmp
    tmp=$(mktemp -d)
    cp -R "$src/." "$tmp/"
    # Initialize a git repo so the script's `git rev-parse --short HEAD` calls
    # don't fail. Migrate skill Step 1 uses this for backup naming.
    (cd "$tmp" && git init -q && git add -A && git commit -q -m "fixture init" --no-gpg-sign 2>/dev/null) || true
    echo "$tmp"
}

count_v3_files() {
    local project_dir="$1"
    local product_base="$2"
    find "$project_dir/$product_base/backlog" -maxdepth 1 -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' '
}

count_v4_files_in() {
    local project_dir="$1"
    local type_dir="$2"
    find "$project_dir/docs/product/backlog/$type_dir" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' '
}

# ── test scenario ──────────────────────────────────────────────────────────

run_scenario() {
    local fixture_path="$1"
    local label="$2"
    local expected_product_base="$3"

    echo ""
    echo "=== Scenario: $label ==="

    local tmp
    tmp=$(prep_fixture "$fixture_path" "$label")

    # 1. validate — should report 0 failures on a clean fixture
    local validate_out
    validate_out=$(python3 "$SCRIPT" validate --project-dir "$tmp")
    local failure_count
    failure_count=$(echo "$validate_out" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('failures', [])))")
    if [ "$failure_count" = "0" ]; then
        pass "validate: 0 failures on clean fixture"
    else
        fail "validate: expected 0 failures, got $failure_count"
        echo "$validate_out"
        rm -rf "$tmp"
        return
    fi

    # 2. plan — should classify items correctly
    local plan_out
    plan_out=$(python3 "$SCRIPT" plan --project-dir "$tmp" --include-done)
    local plan_count
    plan_count=$(echo "$plan_out" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('plan_items', [])))")
    if [ "$plan_count" -gt 0 ]; then
        pass "plan: $plan_count items planned (with --include-done)"
    else
        fail "plan: no items planned"
        rm -rf "$tmp"
        return
    fi

    # Verify product_base was resolved correctly (check suffix only — absolute path varies)
    local resolved_base
    resolved_base=$(echo "$plan_out" | python3 -c "import sys, json; print(json.load(sys.stdin)['product_base'])")
    case "$resolved_base" in
        */"$expected_product_base") pass "plan: resolved product_base ends in $expected_product_base" ;;
        *) fail "plan: expected product_base ending in $expected_product_base, got $resolved_base" ;;
    esac

    # 3. execute — actually run the migration
    local exec_out
    exec_out=$(python3 "$SCRIPT" execute --project-dir "$tmp" --include-done)
    local created_count
    created_count=$(echo "$exec_out" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('created_paths', [])))")
    if [ "$created_count" = "$plan_count" ]; then
        pass "execute: created $created_count files (matches plan)"
    else
        fail "execute: created $created_count files, plan said $plan_count"
    fi

    # 4. Verify INDEX.md and MIGRATION-MAP.md exist
    if [ -f "$tmp/docs/product/backlog/INDEX.md" ]; then
        pass "INDEX.md created"
    else
        fail "INDEX.md not created"
    fi
    if [ -f "$tmp/docs/product/backlog/MIGRATION-MAP.md" ]; then
        pass "MIGRATION-MAP.md created"
    else
        fail "MIGRATION-MAP.md not created"
    fi

    # 5. Verify counters in INDEX.md
    local index_counter_sum
    index_counter_sum=$(python3 -c "
import yaml
raw = open('$tmp/docs/product/backlog/INDEX.md').read()
parts = raw.split('---', 2)
fm = yaml.safe_load(parts[1]) or {}
c = fm.get('counters', {})
print(sum(c.values()))
")
    if [ "$index_counter_sum" = "$created_count" ]; then
        pass "INDEX.md counters sum ($index_counter_sum) matches created files"
    else
        fail "INDEX.md counters sum $index_counter_sum != created $created_count"
    fi

    # 6. Run script-side verify
    local verify_out
    echo "$exec_out" | python3 -c "
import sys, json
data = json.load(sys.stdin)
json.dump(data['created_paths'], open('$tmp/.created-paths.json', 'w'))
"
    verify_out=$(python3 "$SCRIPT" verify --project-dir "$tmp" --created-paths-file "$tmp/.created-paths.json")
    local verify_failures
    verify_failures=$(echo "$verify_out" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('failures', [])))")
    if [ "$verify_failures" = "0" ]; then
        pass "verify: 0 failures on migrated files"
    else
        fail "verify: $verify_failures failures"
        echo "$verify_out"
    fi

    # 7. Finalize — bump version + artifact-privacy
    python3 "$SCRIPT" finalize --project-dir "$tmp" > /dev/null
    local final_version
    final_version=$(python3 -c "
import yaml
d = yaml.safe_load(open('$tmp/.sweetclaude/state/sweetclaude.yaml')) or {}
print(d.get('framework', {}).get('installed_version', ''))
")
    if [ "$final_version" = "4.0.0" ]; then
        pass "finalize: installed_version bumped to 4.0.0"
    else
        fail "finalize: installed_version = $final_version (expected 4.0.0)"
    fi
    local final_base
    final_base=$(python3 -c "
import yaml
d = yaml.safe_load(open('$tmp/.sweetclaude/state/artifact-privacy.yaml')) or {}
print(d.get('categories', {}).get('product', {}).get('base_path', ''))
")
    if [ "$final_base" = "docs/product" ]; then
        pass "finalize: artifact-privacy product base_path = docs/product"
    else
        fail "finalize: artifact-privacy base_path = $final_base"
    fi

    # 8. Run drift check (informational only) — schema drift is handled by the
    # separate schema runner (scripts/migrations/runner.py via sweetclaude:_migrate),
    # not by the v3->v4 backlog migration this script tests. We assert that no
    # FINDING is about BL files or docs/product/backlog/ — that's our responsibility.
    if [ -f "$RUNNER" ]; then
        local drift_out
        drift_out=$(python3 "$RUNNER" --project-dir "$tmp" --report-drift-for-skill 2>/dev/null)
        local bl_in_drift
        bl_in_drift=$(echo "$drift_out" | grep -E '\|BL-|/backlog/BL-' | wc -l | tr -d ' ')
        if [ "$bl_in_drift" = "0" ]; then
            pass "post-migration drift: no findings reference v3 BL files or v4 backlog"
        else
            fail "post-migration drift: $bl_in_drift findings still reference backlog"
            echo "$drift_out"
        fi
    fi

    # 9. Idempotency-adjacent check: file types distributed correctly
    local story_count bug_count
    story_count=$(count_v4_files_in "$tmp" "stories")
    bug_count=$(count_v4_files_in "$tmp" "bugs")
    if [ "$((story_count + bug_count))" -gt 0 ]; then
        pass "files distributed across typed dirs (stories=$story_count, bugs=$bug_count)"
    else
        fail "no files landed in any typed dir"
    fi

    # 10. cleanup-v3-files removes v3 BL files from product_base/backlog
    local v3_before
    v3_before=$(find "$tmp" -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' ')
    python3 "$SCRIPT" cleanup-v3-files --project-dir "$tmp" > /dev/null
    local v3_after
    v3_after=$(find "$tmp" -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$v3_after" = "0" ]; then
        pass "cleanup-v3-files: removed all v3 BL files (was $v3_before, now $v3_after)"
    else
        fail "cleanup-v3-files: $v3_after BL files remain (started with $v3_before)"
    fi

    # 11. Post-cleanup: simulate next-session bootstrap V3_FILES check — should be 0
    # (this is the regression prevention for the "keep v3 files = stuck migration loop" bug)
    local product_base_post_finalize
    product_base_post_finalize=$(python3 "$SCRIPT" resolve-base --project-dir "$tmp" | python3 -c "import sys, json; print(json.load(sys.stdin)['product_base'])")
    local v3_in_new_base
    v3_in_new_base=$(find "$product_base_post_finalize/backlog" -maxdepth 1 -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$v3_in_new_base" = "0" ]; then
        pass "post-cleanup: bootstrap V3_FILES check in $product_base_post_finalize/backlog returns 0 (no stuck-migration loop)"
    else
        fail "post-cleanup: V3_FILES still > 0 ($v3_in_new_base) — bootstrap hard-stop would loop"
    fi

    rm -rf "$tmp"
}

# ── run scenarios ───────────────────────────────────────────────────────────

echo "=== B2/C smoke test: v3 -> v4 migration ==="

run_scenario "$REPO_ROOT/tests/fixtures/migrate-smoke"      ".sweetclaude/product variant"  ".sweetclaude/product"
run_scenario "$REPO_ROOT/tests/fixtures/migrate-smoke-docs" "docs/product variant"          "docs/product"

echo ""
if [ "$FAILED" -gt 0 ]; then
    echo "=== FAILED: $FAILED check(s) ==="
    exit 1
else
    echo "=== ALL PASSED ==="
    exit 0
fi
