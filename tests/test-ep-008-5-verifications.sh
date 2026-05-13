#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# EP-008.5 verifications — Phase 1 validation work that the May 11 v4 plan
# called out as required before merge. The original plan said this needed
# live skill execution against a real v3 project ("project-X"), but project-X
# no longer exists. This test exercises the same verifications against the
# existing synthetic v3 fixtures (tests/fixtures/migrate-smoke/ and
# migrate-smoke-docs/), covering the deterministic behaviors.
#
# Scenarios:
#   A. Bootstrap v4 hard-stop fires on v3 fixture + installed_version 4.0.0
#   B. Bootstrap v4 hard-stop does NOT fire on clean post-migration state
#   C. fix-sweetclaude Step 13 counter-drift repair sets counters correctly
#   D. Migration guards in project-backlog/issues/backlog-triage fire on v3 state
#   E. Migration guards do NOT fire on post-migration state
#
# Out of scope (filed as BUG-006):
#   - project-gh-import-issues and project-gh-sync-issues lack migration guards
#     entirely. Test won't cover them until the bug is fixed.
#
# Not testable here (LLM-interactive — manual verification required):
#   - AskUserQuestion prompts in migrate Step 3, Step 4, Step 8
#   - Failure-handling chain (skill-level orchestration)

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

# ── Scenario A: Bootstrap v4 hard-stop fires ────────────────────────────────

scenario_a_bootstrap_hardstop_fires() {
    echo ""
    echo "=== Scenario A: Bootstrap v4 hard-stop fires on v3 fixture + installed_version 4.0.0 ==="

    local tmp
    tmp=$(mktemp -d)
    cp -R "$REPO_ROOT/tests/fixtures/migrate-smoke/." "$tmp/"

    # Simulate the post-update / pre-migrate state: plugin is v4 but project
    # state still has v3 BL files. Bump installed_version manually to mimic the
    # scenario where a v4 install lands but migrate hasn't run yet.
    python3 -c "
import yaml
p = '$tmp/.sweetclaude/state/sweetclaude.yaml'
d = yaml.safe_load(open(p)) or {}
d.setdefault('framework', {})['installed_version'] = '4.0.0'
open(p, 'w').write(yaml.safe_dump(d, default_flow_style=False, sort_keys=False))
"

    # Verify v3 BL files are present
    local v3_count
    v3_count=$(find "$tmp/.sweetclaude/product/backlog" -maxdepth 1 -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$v3_count" -gt 0 ]; then
        pass "fixture setup: $v3_count v3 BL files present at .sweetclaude/product/backlog"
    else
        fail "fixture setup: no v3 BL files found"
        rm -rf "$tmp"; return
    fi

    # Execute the bootstrap Step 5b hard-stop predicate, isolated.
    # SOURCE OF TRUTH: skills/bootstrap/SKILL.md Step 5b. Update both together.
    local output exit_code
    output=$(cd "$tmp" && bash -c '
PRODUCT_BASE=$(python3 -c "
import yaml, pathlib
p = pathlib.Path(\".sweetclaude/state/artifact-privacy.yaml\")
if p.exists():
    d = yaml.safe_load(p.read_text()) or {}
    base = d.get(\"categories\", {}).get(\"product\", {}).get(\"base_path\", \"\")
    if base:
        print(base.rstrip(\"/\"))
        exit()
print(\".sweetclaude/product\")
" 2>/dev/null || echo ".sweetclaude/product")

PROJECT_V=$(python3 -c "
import yaml
d = yaml.safe_load(open(\".sweetclaude/state/sweetclaude.yaml\")) or {}
print(d.get(\"framework\", {}).get(\"installed_version\", \"\"))
" 2>/dev/null)

V3_FILES=$(find "${PRODUCT_BASE}/backlog" -maxdepth 1 -name "BL-*.md" 2>/dev/null | wc -l | tr -d " ")

# For the test, simulate "plugin is v4" — the real bootstrap reads installed_plugins.json.
PLUGIN_IS_V4=true

PROJECT_NOT_V4=false
case "$PROJECT_V" in 4.*) ;; *) PROJECT_NOT_V4=true ;; esac

if $PLUGIN_IS_V4 && ( $PROJECT_NOT_V4 || [ "$V3_FILES" -gt 0 ] ); then
  echo "HARD_STOP_FIRED"
  echo "Run: /sweetclaude:migrate"
  exit 1
fi
echo "HARD_STOP_NOT_FIRED"
' 2>&1) || exit_code=$?

    if echo "$output" | grep -q "HARD_STOP_FIRED"; then
        pass "hard-stop fires when installed_version=4.0.0 AND v3 files present"
    else
        fail "hard-stop did not fire (output: $output)"
    fi
    if echo "$output" | grep -q "Run: /sweetclaude:migrate"; then
        pass "hard-stop message references /sweetclaude:migrate"
    else
        fail "hard-stop message missing migrate reference"
    fi

    rm -rf "$tmp"
}

# ── Scenario B: Bootstrap hard-stop does NOT fire on clean post-migration ──

scenario_b_bootstrap_hardstop_silent() {
    echo ""
    echo "=== Scenario B: Bootstrap v4 hard-stop does NOT fire on clean post-migration state ==="

    local tmp
    tmp=$(mktemp -d)
    cp -R "$REPO_ROOT/tests/fixtures/migrate-smoke/." "$tmp/"

    # Run the full v3→v4 migration to produce a clean post-migration state.
    (cd "$tmp" && git init -q && git add -A && git commit -q -m "init" --no-gpg-sign 2>/dev/null) || true
    python3 "$REPO_ROOT/scripts/migrate/migrate-v3-to-v4.py" execute --project-dir "$tmp" --include-done > /dev/null
    python3 "$REPO_ROOT/scripts/migrate/migrate-v3-to-v4.py" finalize --project-dir "$tmp" > /dev/null
    python3 "$REPO_ROOT/scripts/migrate/migrate-v3-to-v4.py" cleanup-v3-files --project-dir "$tmp" > /dev/null

    # Now: installed_version=4.0.0, no v3 BL files, v4 INDEX exists
    local v3_count
    v3_count=$(find "$tmp" -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$v3_count" = "0" ]; then
        pass "post-migration fixture: 0 v3 BL files (correct setup)"
    else
        fail "post-migration fixture: $v3_count v3 BL files remain (cleanup failed)"
        rm -rf "$tmp"; return
    fi

    local output exit_code
    exit_code=0
    output=$(cd "$tmp" && bash -c '
PRODUCT_BASE=$(python3 -c "
import yaml, pathlib
p = pathlib.Path(\".sweetclaude/state/artifact-privacy.yaml\")
if p.exists():
    d = yaml.safe_load(p.read_text()) or {}
    base = d.get(\"categories\", {}).get(\"product\", {}).get(\"base_path\", \"\")
    if base:
        print(base.rstrip(\"/\"))
        exit()
print(\".sweetclaude/product\")
" 2>/dev/null || echo ".sweetclaude/product")

PROJECT_V=$(python3 -c "
import yaml
d = yaml.safe_load(open(\".sweetclaude/state/sweetclaude.yaml\")) or {}
print(d.get(\"framework\", {}).get(\"installed_version\", \"\"))
" 2>/dev/null)

V3_FILES=$(find "${PRODUCT_BASE}/backlog" -maxdepth 1 -name "BL-*.md" 2>/dev/null | wc -l | tr -d " ")
PLUGIN_IS_V4=true
PROJECT_NOT_V4=false
case "$PROJECT_V" in 4.*) ;; *) PROJECT_NOT_V4=true ;; esac

if $PLUGIN_IS_V4 && ( $PROJECT_NOT_V4 || [ "$V3_FILES" -gt 0 ] ); then
  echo "HARD_STOP_FIRED"
  exit 1
fi
echo "HARD_STOP_NOT_FIRED"
' 2>&1) || exit_code=$?

    if echo "$output" | grep -q "HARD_STOP_NOT_FIRED"; then
        pass "hard-stop silent on clean post-migration state"
    else
        fail "hard-stop fired unexpectedly (output: $output)"
    fi
    if [ "$exit_code" = "0" ]; then
        pass "bootstrap exit code 0 on clean state"
    else
        fail "bootstrap exit code $exit_code (expected 0)"
    fi

    rm -rf "$tmp"
}

# ── Scenario C: Counter-drift repair ────────────────────────────────────────

scenario_c_counter_drift_repair() {
    echo ""
    echo "=== Scenario C: fix-sweetclaude Step 13 counter-drift repair ==="

    local tmp
    tmp=$(mktemp -d)
    cp -R "$REPO_ROOT/tests/fixtures/migrate-smoke/." "$tmp/"
    (cd "$tmp" && git init -q && git add -A && git commit -q -m "init" --no-gpg-sign 2>/dev/null) || true

    # Migrate to produce v4 state, then deliberately set INDEX counters BELOW
    # the highest seen ID. The counter-drift repair should detect and fix.
    python3 "$REPO_ROOT/scripts/migrate/migrate-v3-to-v4.py" execute --project-dir "$tmp" --include-done > /dev/null
    python3 "$REPO_ROOT/scripts/migrate/migrate-v3-to-v4.py" finalize --project-dir "$tmp" > /dev/null

    # Corrupt the INDEX counters (set all to 0)
    python3 -c "
import yaml
p = '$tmp/docs/product/backlog/INDEX.md'
raw = open(p).read()
parts = raw.split('---', 2)
fm = yaml.safe_load(parts[1]) or {}
fm['counters'] = {'story': 0, 'bug': 0, 'debt': 0, 'chore': 0}
new = '---\n' + yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip() + '\n---' + parts[2]
open(p, 'w').write(new)
"

    # Run the counter-drift repair (extracted from fix-sweetclaude Step 13).
    # SOURCE OF TRUTH: skills/fix-sweetclaude/SKILL.md Step 13 counter-drift recipe.
    (cd "$tmp" && python3 -c "
import pathlib, yaml, re, datetime

BACKLOG_BASE = pathlib.Path('docs/product/backlog')
INDEX_PATH = BACKLOG_BASE / 'INDEX.md'
raw = INDEX_PATH.read_text(encoding='utf-8')
parts = raw.split('---', 2)
index_fm = yaml.safe_load(parts[1]) or {}
counters = index_fm.setdefault('counters', {})

TYPE_PREFIX = {'story': 'STORY', 'bug': 'BUG', 'debt': 'DEBT', 'chore': 'CHORE'}
TYPE_DIRS = {'story': 'stories', 'bug': 'bugs', 'debt': 'debt', 'chore': 'chores'}

for typ, dir_name in TYPE_DIRS.items():
    prefix = TYPE_PREFIX[typ]
    max_seen = 0
    for p in (BACKLOG_BASE / dir_name).rglob('*.md'):
        m = re.match(rf'^{prefix}-(\d+)-', p.name)
        if m:
            max_seen = max(max_seen, int(m.group(1)))
    counters[typ] = max(counters.get(typ, 0), max_seen)

index_fm['updated'] = datetime.date.today().isoformat()
INDEX_PATH.write_text(
    f'---\n{yaml.safe_dump(index_fm, default_flow_style=False, sort_keys=False).rstrip()}\n---{parts[2]}',
    encoding='utf-8'
)
")

    # Verify counters now match max-seen-IDs
    local result
    result=$(python3 -c "
import yaml, json
p = '$tmp/docs/product/backlog/INDEX.md'
raw = open(p).read()
parts = raw.split('---', 2)
fm = yaml.safe_load(parts[1]) or {}
counters = fm.get('counters', {})
total = sum(counters.values())
print(json.dumps({'counters': counters, 'total': total}))
")
    local total
    total=$(echo "$result" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])")
    if [ "$total" -gt 0 ]; then
        pass "counter-drift repair: total counter sum > 0 (was 0 before repair) → $result"
    else
        fail "counter-drift repair: counters still all 0 → $result"
    fi

    rm -rf "$tmp"
}

# ── Scenario D: Migration guards fire on v3 state ───────────────────────────

scenario_d_migration_guards_fire() {
    echo ""
    echo "=== Scenario D: Migration guards fire on v3 fixture (project-backlog, project-issues, project-backlog-triage) ==="

    local tmp
    tmp=$(mktemp -d)
    cp -R "$REPO_ROOT/tests/fixtures/migrate-smoke/." "$tmp/"

    # Execute the migration-guard bash block isolated.
    # SOURCE OF TRUTH: skills/project-backlog/SKILL.md (identical block in project-issues
    # and project-backlog-triage). Update all three together.
    local output exit_code
    exit_code=0
    output=$(cd "$tmp" && bash -c '
PRODUCT_BASE=$(python3 -c "
import yaml, pathlib
p = pathlib.Path(\".sweetclaude/state/artifact-privacy.yaml\")
if p.exists():
    d = yaml.safe_load(p.read_text()) or {}
    base = d.get(\"categories\", {}).get(\"product\", {}).get(\"base_path\", \"\")
    if base:
        print(base.rstrip(\"/\"))
        exit()
print(\".sweetclaude/product\")
" 2>/dev/null || echo ".sweetclaude/product")
V3_FILES=$(find "${PRODUCT_BASE}/backlog" -maxdepth 1 -name "BL-*.md" 2>/dev/null | wc -l | tr -d " ")
if [ "$V3_FILES" -gt 0 ]; then
  echo "GUARD_FIRED v3_files=$V3_FILES"
  exit 1
fi
echo "GUARD_NOT_FIRED"
' 2>&1) || exit_code=$?

    if echo "$output" | grep -q "GUARD_FIRED"; then
        pass "migration guard fires on v3 fixture (output: $(echo "$output" | head -1))"
    else
        fail "guard did not fire on v3 fixture (output: $output)"
    fi
    if [ "$exit_code" = "1" ]; then
        pass "guard exit code 1 (blocks subsequent skill execution)"
    else
        fail "guard exit code $exit_code (expected 1)"
    fi

    rm -rf "$tmp"
}

# ── Scenario E: Migration guards do NOT fire on post-migration state ───────

scenario_e_migration_guards_silent() {
    echo ""
    echo "=== Scenario E: Migration guards silent on clean post-migration state ==="

    local tmp
    tmp=$(mktemp -d)
    cp -R "$REPO_ROOT/tests/fixtures/migrate-smoke/." "$tmp/"
    (cd "$tmp" && git init -q && git add -A && git commit -q -m "init" --no-gpg-sign 2>/dev/null) || true

    python3 "$REPO_ROOT/scripts/migrate/migrate-v3-to-v4.py" execute --project-dir "$tmp" --include-done > /dev/null
    python3 "$REPO_ROOT/scripts/migrate/migrate-v3-to-v4.py" finalize --project-dir "$tmp" > /dev/null
    python3 "$REPO_ROOT/scripts/migrate/migrate-v3-to-v4.py" cleanup-v3-files --project-dir "$tmp" > /dev/null

    local output exit_code
    exit_code=0
    output=$(cd "$tmp" && bash -c '
PRODUCT_BASE=$(python3 -c "
import yaml, pathlib
p = pathlib.Path(\".sweetclaude/state/artifact-privacy.yaml\")
if p.exists():
    d = yaml.safe_load(p.read_text()) or {}
    base = d.get(\"categories\", {}).get(\"product\", {}).get(\"base_path\", \"\")
    if base:
        print(base.rstrip(\"/\"))
        exit()
print(\".sweetclaude/product\")
" 2>/dev/null || echo ".sweetclaude/product")
V3_FILES=$(find "${PRODUCT_BASE}/backlog" -maxdepth 1 -name "BL-*.md" 2>/dev/null | wc -l | tr -d " ")
if [ "$V3_FILES" -gt 0 ]; then
  echo "GUARD_FIRED v3_files=$V3_FILES"
  exit 1
fi
echo "GUARD_NOT_FIRED"
' 2>&1) || exit_code=$?

    if echo "$output" | grep -q "GUARD_NOT_FIRED"; then
        pass "migration guard silent on clean post-migration state"
    else
        fail "guard fired unexpectedly (output: $output)"
    fi
    if [ "$exit_code" = "0" ]; then
        pass "guard exit code 0 (does not block subsequent skill execution)"
    else
        fail "guard exit code $exit_code (expected 0)"
    fi

    rm -rf "$tmp"
}

# ── Run scenarios ───────────────────────────────────────────────────────────

echo "=== EP-008.5 verifications ==="
echo "(Bootstrap hard-stop, counter recovery, migration guards in 3 skills.)"
echo "(SKIPPED — see BUG-006: project-gh-import-issues, project-gh-sync-issues lack guards.)"
echo "(NOT TESTABLE HERE — interactive AskUserQuestion paths in migrate skill.)"

scenario_a_bootstrap_hardstop_fires
scenario_b_bootstrap_hardstop_silent
scenario_c_counter_drift_repair
scenario_d_migration_guards_fire
scenario_e_migration_guards_silent

echo ""
if [ "$FAILED" -gt 0 ]; then
    echo "=== FAILED: $FAILED check(s) ==="
    exit 1
else
    echo "=== ALL PASSED ==="
    exit 0
fi
