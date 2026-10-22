#!/usr/bin/env bash
set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/scripts/generate-effective-gates.sh"
PASS=0; FAIL=0
pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
mkdir -p "$tmpdir/.sweetclaude/state"

# --- kanban ---
cat > "$tmpdir/.sweetclaude/state/sweetclaude.yaml" << 'YAML'
schema_version: 2
mode: kanban
wip_limit: 4
YAML

PROJECT_DIR="$tmpdir" bash "$SCRIPT"

if [ -f "$tmpdir/.sweetclaude/state/effective-gates.yaml" ]; then
    pass "kanban: effective-gates.yaml created"
else
    fail "kanban: effective-gates.yaml not created"; fi

grep -q "mode: kanban" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "kanban: mode field correct" || fail "kanban: mode field wrong"

grep -q "default_tdd_level: 1" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "kanban: default_tdd_level=1" || fail "kanban: default_tdd_level wrong"

grep -q "wip_limit: 4" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "kanban: wip_limit override applied" || fail "kanban: wip_limit not written"

grep -q "project-sprints" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "kanban: project-sprints in blocked_skills" || fail "kanban: blocked_skills missing project-sprints"

grep -q "product-sprint-plan" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "kanban: product-sprint-plan in blocked_skills" || fail "kanban: blocked_skills missing product-sprint-plan"

# --- shape_up ---
cat > "$tmpdir/.sweetclaude/state/sweetclaude.yaml" << 'YAML'
schema_version: 2
mode: shape_up
cycle_duration_weeks: 4
YAML

PROJECT_DIR="$tmpdir" bash "$SCRIPT"

grep -q "cycle_duration_weeks: 4" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "shape_up: cycle_duration_weeks override applied" || fail "shape_up: cycle_duration_weeks wrong"

grep -q "project-backlog" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "shape_up: project-backlog in blocked_skills" || fail "shape_up: project-backlog not blocked"

grep -q "default_tdd_level: 2" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "shape_up: default_tdd_level=2" || fail "shape_up: default_tdd_level wrong"

# --- flow ---
cat > "$tmpdir/.sweetclaude/state/sweetclaude.yaml" << 'YAML'
schema_version: 2
mode: flow
YAML

PROJECT_DIR="$tmpdir" bash "$SCRIPT"

grep -q "mode: flow" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "flow: mode field correct" || fail "flow: mode field wrong"

# --- kanban without wip_limit override (test mode default propagation) ---
cat > "$tmpdir/.sweetclaude/state/sweetclaude.yaml" << 'YAML'
schema_version: 2
mode: kanban
YAML

PROJECT_DIR="$tmpdir" bash "$SCRIPT"

grep -q "wip_limit: 3" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "kanban no-override: wip_limit defaults to 3" || fail "kanban no-override: wip_limit default not applied"

# --- agile mode ---
cat > "$tmpdir/.sweetclaude/state/sweetclaude.yaml" << 'YAML'
schema_version: 2
mode: agile
YAML

PROJECT_DIR="$tmpdir" bash "$SCRIPT"

grep -q "mode: agile" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "agile: mode field correct" || fail "agile: mode field wrong"

grep -q "default_tdd_level: 2" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "agile: default_tdd_level=2" || fail "agile: default_tdd_level wrong"

grep -q "no_active_sprint" "$tmpdir/.sweetclaude/state/effective-gates.yaml" 2>/dev/null \
    && pass "agile: no_active_sprint gate present" || fail "agile: no_active_sprint gate missing"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
