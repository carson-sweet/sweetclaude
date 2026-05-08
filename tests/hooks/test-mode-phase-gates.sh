#!/usr/bin/env bash
# Tests for mode-phase gate enforcement in the go skill.
# Verifies the inline bash gate-check snippet behaves correctly for:
#   - shape_up + betting_table_approved
#   - agile + no_active_sprint

set -euo pipefail
PASS=0; FAIL=0
pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# The gate-check snippet extracted from go/SKILL.md — kept in sync manually.
run_gate_check() {
    local dir="$1"
    PROJECT_DIR="$dir" python3 -c "
import yaml, os, glob, sys
PROJECT_DIR = os.environ.get('PROJECT_DIR', os.getcwd())
gates_path = os.path.join(PROJECT_DIR, '.sweetclaude/state/effective-gates.yaml')
if not os.path.exists(gates_path):
    print('GATES_OK'); sys.exit()
d = yaml.safe_load(open(gates_path)) or {}
mode = d.get('mode', '')
gates = [g for g in d.get('gates', []) if g.get('phase') == 'IMPLEMENT' and g.get('action') == 'block']
for gate in gates:
    cond = gate.get('condition', '')
    req = gate.get('requires', '')
    msg = gate.get('message', 'Gate condition not met.')
    if req == 'betting_table_approved' and mode == 'shape_up':
        sc = yaml.safe_load(open(os.path.join(PROJECT_DIR, '.sweetclaude/state/sweetclaude.yaml'))) or {}
        active_id = ((sc.get('work') or {}).get('active') or {}).get('id') or ''
        issue_path = os.path.join(PROJECT_DIR, '.sweetclaude/artifacts/issues', f'{active_id}.yaml')
        approved = bool(active_id and os.path.exists(issue_path) and (yaml.safe_load(open(issue_path)) or {}).get('betting_table_approved'))
        if not approved:
            print('BLOCKED:' + msg); sys.exit()
    if cond == 'no_active_sprint' and mode == 'agile':
        sprints_dir = os.path.join(PROJECT_DIR, '.sweetclaude/artifacts/sprints')
        has_active = os.path.exists(sprints_dir) and any(
            (yaml.safe_load(open(f)) or {}).get('status') == 'active'
            for f in glob.glob(os.path.join(sprints_dir, '*.yaml'))
        )
        if not has_active:
            print('BLOCKED:' + msg); sys.exit()
print('GATES_OK')
" 2>&1
}

is_ok()      { grep -q '^GATES_OK$'; }
is_blocked() { grep -q '^BLOCKED:'; }

setup() {
    local dir
    dir=$(mktemp -d)
    mkdir -p "$dir/.sweetclaude/state" "$dir/.sweetclaude/artifacts/issues" "$dir/.sweetclaude/artifacts/sprints"
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
YAML
    # Append mode-specific gates
    case "$mode" in
        shape_up)
            cat >> "$dir/.sweetclaude/state/effective-gates.yaml" << YAML
gates:
  - phase: IMPLEMENT
    requires: betting_table_approved
    action: block
    message: "Work must be pitched and bet before implementation begins."
YAML
            ;;
        agile)
            cat >> "$dir/.sweetclaude/state/effective-gates.yaml" << YAML
gates:
  - phase: IMPLEMENT
    condition: no_active_sprint
    action: block
    message: "No active sprint. Run /sweetclaude:project-sprints start to activate a sprint."
YAML
            ;;
        *)
            echo "gates: []" >> "$dir/.sweetclaude/state/effective-gates.yaml"
            ;;
    esac
}

write_sc_yaml() {
    local dir="$1" active_id="${2:-}"
    cat > "$dir/.sweetclaude/state/sweetclaude.yaml" << YAML
schema_version: 1
work:
  active:
    id: ${active_id}
YAML
}

write_issue() {
    local dir="$1" id="$2" approved="$3"
    cat > "$dir/.sweetclaude/artifacts/issues/${id}.yaml" << YAML
id: $id
title: Test issue
status: in_progress
betting_table_approved: $approved
YAML
}

write_sprint() {
    local dir="$1" id="$2" status="$3"
    cat > "$dir/.sweetclaude/artifacts/sprints/${id}.yaml" << YAML
id: $id
title: Sprint $id
status: $status
YAML
}

# ── shape_up tests ────────────────────────────────────────────────────────────

# 1. shape_up, no active work item → blocked
d=$(setup); write_gates "$d" shape_up; write_sc_yaml "$d" ""
run_gate_check "$d" | is_blocked && pass "shape_up: no active item → blocked" || fail "shape_up: no active item should block"
rm -rf "$d"

# 2. shape_up, active item exists but betting_table_approved=false → blocked
d=$(setup); write_gates "$d" shape_up; write_sc_yaml "$d" "I-001"; write_issue "$d" "I-001" "false"
run_gate_check "$d" | is_blocked && pass "shape_up: betting_table_approved=false → blocked" || fail "shape_up: unapproved issue should block"
rm -rf "$d"

# 3. shape_up, active item with betting_table_approved=true → ok
d=$(setup); write_gates "$d" shape_up; write_sc_yaml "$d" "I-001"; write_issue "$d" "I-001" "true"
run_gate_check "$d" | is_ok && pass "shape_up: betting_table_approved=true → ok" || fail "shape_up: approved issue should allow"
rm -rf "$d"

# 4. shape_up, active item ID but no artifact file → blocked
d=$(setup); write_gates "$d" shape_up; write_sc_yaml "$d" "I-999"
run_gate_check "$d" | is_blocked && pass "shape_up: missing artifact → blocked" || fail "shape_up: missing artifact should block"
rm -rf "$d"

# 5. block message contains expected text
d=$(setup); write_gates "$d" shape_up; write_sc_yaml "$d" "I-001"; write_issue "$d" "I-001" "false"
msg=$(run_gate_check "$d")
echo "$msg" | grep -q "pitched and bet" && pass "shape_up: block message contains expected text" || fail "shape_up: block message wrong"
rm -rf "$d"

# ── agile tests ───────────────────────────────────────────────────────────────

# 6. agile, no sprints directory → blocked
d=$(setup); write_gates "$d" agile; write_sc_yaml "$d" ""; rmdir "$d/.sweetclaude/artifacts/sprints"
run_gate_check "$d" | is_blocked && pass "agile: no sprints dir → blocked" || fail "agile: missing sprints dir should block"
rm -rf "$d"

# 7. agile, no sprint artifacts → blocked
d=$(setup); write_gates "$d" agile; write_sc_yaml "$d" ""
run_gate_check "$d" | is_blocked && pass "agile: empty sprints dir → blocked" || fail "agile: no sprints should block"
rm -rf "$d"

# 8. agile, sprint with status=closed → blocked
d=$(setup); write_gates "$d" agile; write_sc_yaml "$d" ""; write_sprint "$d" "SP-001" "closed"
run_gate_check "$d" | is_blocked && pass "agile: closed sprint → blocked" || fail "agile: closed sprint should block"
rm -rf "$d"

# 9. agile, sprint with status=active → ok
d=$(setup); write_gates "$d" agile; write_sc_yaml "$d" ""; write_sprint "$d" "SP-001" "active"
run_gate_check "$d" | is_ok && pass "agile: active sprint → ok" || fail "agile: active sprint should allow"
rm -rf "$d"

# 10. agile block message contains expected text
d=$(setup); write_gates "$d" agile; write_sc_yaml "$d" ""
msg=$(run_gate_check "$d")
echo "$msg" | grep -q "No active sprint" && pass "agile: block message contains expected text" || fail "agile: block message wrong"
rm -rf "$d"

# ── non-blocking modes ────────────────────────────────────────────────────────

# 11. flow mode with no gates → ok
d=$(setup); write_gates "$d" flow; write_sc_yaml "$d" ""
run_gate_check "$d" | is_ok && pass "flow: no gates → ok" || fail "flow: should always allow"
rm -rf "$d"

# 12. no effective-gates.yaml → ok
d=$(setup); write_sc_yaml "$d" ""
run_gate_check "$d" | is_ok && pass "no effective-gates.yaml → ok" || fail "missing gates file should allow"
rm -rf "$d"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
