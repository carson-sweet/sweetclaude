#!/usr/bin/env bash
# Tests for mode-phase gate enforcement in the go skill.
# Drives scripts/gate_check.py — the single gate evaluator that the go skill,
# the library loader, and the master pre-flight hook all call.
# Verifies the IMPLEMENT gate set for:
#   - shape_up + betting_table_approved
#   - agile + no_active_sprint
# Sprints and issues live in the canonical artifact store
# (.sweetclaude/product/), matching what the workflow layer writes.

set -euo pipefail
PASS=0; FAIL=0
pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/scripts/gate_check.py"

run_gate_check() {
    local dir="$1"
    (python3 "$SCRIPT" advance --to IMPLEMENT --project-dir "$dir" 2>&1 || true)
}

is_ok()      { grep -q '"allow": true'; }
is_blocked() { grep -q '"allow": false'; }

setup() {
    local dir
    dir=$(mktemp -d)
    mkdir -p "$dir/.sweetclaude/state" "$dir/.sweetclaude/product/backlog" "$dir/.sweetclaude/product/sprints"
    echo "$dir"
}

write_gates() {
    local dir="$1" mode="$2"
    cat > "$dir/.sweetclaude/state/effective-gates.yaml" << YAML
schema_version: 1
mode: $mode
default_tdd_level: 1
wip_limit: null
blocked_skills: []
gates:
YAML
    # Append mode-specific gates
    case "$mode" in
        shape_up)
            cat >> "$dir/.sweetclaude/state/effective-gates.yaml" << YAML
  - phase: IMPLEMENT
    requires: betting_table_approved
    action: block
    message: "Work must be pitched and bet before implementation begins. Run /sweetclaude:project-issues to create issues from a pitch."
YAML
            ;;
        agile)
            cat >> "$dir/.sweetclaude/state/effective-gates.yaml" << YAML
  - phase: IMPLEMENT
    condition: no_active_sprint
    action: block
    message: "No active sprint. Run /sweetclaude:project-sprints start to activate a sprint."
  - phase: IMPLEMENT
    condition: issue_not_in_sprint
    action: warn
    message: "This issue is not assigned to the active sprint. Assign it or start a new sprint."
YAML
            ;;
        *)
            echo "  []" >> "$dir/.sweetclaude/state/effective-gates.yaml"
            ;;
    esac
}

write_sc_yaml() {
    local dir="$1" active_id="${2:-}"
    cat > "$dir/.sweetclaude/state/sweetclaude.yaml" << YAML
schema_version: 2
project:
  name: t
  mode: flow
work:
  active:
    id: ${active_id}
YAML
}

write_issue() {
    local dir="$1" id="$2" approved="$3"
    cat > "$dir/.sweetclaude/product/backlog/${id}-pitch.md" << YAML
---
id: $id
title: Test issue
status: in_progress
betting_table_approved: $approved
---
# $id: Test issue
YAML
}

write_sprint() {
    local dir="$1" id="$2" status="$3"
    cat > "$dir/.sweetclaude/product/sprints/${id}-sprint.md" << YAML
---
id: $id
title: Sprint $id
status: $status
---
# $id: Sprint $id
YAML
}

# ── shape_up tests ────────────────────────────────────────────────────────────

# 1. shape_up, no active work item → blocked
d=$(setup); write_gates "$d" shape_up; write_sc_yaml "$d" ""
run_gate_check "$d" | is_blocked && pass "shape_up: no active item → blocked" || fail "shape_up: no active item should block"
rm -rf "$d"

# 2. shape_up, active item exists but betting_table_approved=false → blocked
d=$(setup); write_gates "$d" shape_up; write_sc_yaml "$d" "ISSUE-001"; write_issue "$d" "ISSUE-001" "false"
run_gate_check "$d" | is_blocked && pass "shape_up: betting_table_approved=false → blocked" || fail "shape_up: unapproved issue should block"
rm -rf "$d"

# 3. shape_up, active item with betting_table_approved=true → ok
d=$(setup); write_gates "$d" shape_up; write_sc_yaml "$d" "ISSUE-001"; write_issue "$d" "ISSUE-001" "true"
run_gate_check "$d" | is_ok && pass "shape_up: betting_table_approved=true → ok" || fail "shape_up: approved issue should allow"
rm -rf "$d"

# 4. shape_up, active item ID but no artifact file → blocked
d=$(setup); write_gates "$d" shape_up; write_sc_yaml "$d" "ISSUE-999"
run_gate_check "$d" | is_blocked && pass "shape_up: missing artifact → blocked" || fail "shape_up: missing artifact should block"
rm -rf "$d"

# 5. block message contains expected text
d=$(setup); write_gates "$d" shape_up; write_sc_yaml "$d" "ISSUE-001"; write_issue "$d" "ISSUE-001" "false"
msg=$(run_gate_check "$d")
echo "$msg" | grep -q "pitched and bet" && pass "shape_up: block message contains expected text" || fail "shape_up: block message wrong"
rm -rf "$d"

# ── agile tests ───────────────────────────────────────────────────────────────

# 6. agile, no sprints directory at all → blocked
d=$(mktemp -d); mkdir -p "$d/.sweetclaude/state"; write_gates "$d" agile; write_sc_yaml "$d" ""
run_gate_check "$d" | is_blocked && pass "agile: no sprints dir → blocked" || fail "agile: missing sprints dir should block"
rm -rf "$d"

# 7. agile, empty sprints dir → blocked
d=$(setup); write_gates "$d" agile; write_sc_yaml "$d" ""
run_gate_check "$d" | is_blocked && pass "agile: empty sprints dir → blocked" || fail "agile: no sprints should block"
rm -rf "$d"

# 8. agile, sprint with status=closed → blocked
d=$(setup); write_gates "$d" agile; write_sc_yaml "$d" ""; write_sprint "$d" "SP-001" "closed"
run_gate_check "$d" | is_blocked && pass "agile: closed sprint → blocked" || fail "agile: closed sprint should block"
rm -rf "$d"

# 9. agile, sprint with status=active in the canonical store → ok
d=$(setup); write_gates "$d" agile; write_sc_yaml "$d" ""; write_sprint "$d" "SP-001" "active"
run_gate_check "$d" | is_ok && pass "agile: active sprint → ok" || fail "agile: active sprint should allow"
rm -rf "$d"

# 10. agile block message contains expected text
d=$(setup); write_gates "$d" agile; write_sc_yaml "$d" ""
msg=$(run_gate_check "$d")
echo "$msg" | grep -q "No active sprint" && pass "agile: block message contains expected text" || fail "agile: block message wrong"
rm -rf "$d"

# 11. agile block reason names the gate id and the criterion
d=$(setup); write_gates "$d" agile; write_sc_yaml "$d" ""
msg=$(run_gate_check "$d")
echo "$msg" | grep -q "Gate no_active_sprint unmet:" && pass "agile: gate reason names the gate id" || fail "agile: gate reason missing gate id"
rm -rf "$d"

# ── non-blocking modes ────────────────────────────────────────────────────────

# 12. flow mode with no gates → ok
d=$(setup); write_gates "$d" flow; write_sc_yaml "$d" ""
run_gate_check "$d" | is_ok && pass "flow: no gates → ok" || fail "flow: should always allow"
rm -rf "$d"

# 13. no effective-gates.yaml → ok
d=$(setup); write_sc_yaml "$d" ""
run_gate_check "$d" | is_ok && pass "no effective-gates.yaml → ok" || fail "missing gates file should allow"
rm -rf "$d"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1