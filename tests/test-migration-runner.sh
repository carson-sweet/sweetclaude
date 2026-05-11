#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Smoke test for scripts/migrations/runner.py.
# Creates a fixture project with v1 state files, runs the migration runner,
# and verifies the output is correctly v2-shaped.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNNER="$REPO_ROOT/scripts/migrations/runner.py"
REGISTRY="$REPO_ROOT/config/migration-registry.yaml"
MIGRATIONS_DIR="$REPO_ROOT/scripts/migrations"

TEST_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR" EXIT

FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

# ---------------------------------------------------------------------------
# Fixture: v1 phase.yaml + v1 skills.yaml
# ---------------------------------------------------------------------------

mkdir -p "$TEST_TMPDIR/.sweetclaude/state"

cat > "$TEST_TMPDIR/.sweetclaude/state/phase.yaml" << 'YAML'
schema_version: 1
phase: IMPLEMENT
work_type: refactor
deference_level: guided
project_type: existing-code
safety_snapshot: pre-sweetclaude
init_step: complete
YAML

cat > "$TEST_TMPDIR/.sweetclaude/state/skills.yaml" << 'YAML'
schema_version: 1
product-milestones:
  enabled: true
  onboarded_at: "2026-04-15"
product-parking-lot:
  enabled: false
  onboarded_at: "2026-04-10"
  offboarded_at: "2026-04-20"
user-personas:
  enabled: false
  onboarded_at: ~
YAML

# ---------------------------------------------------------------------------
# Test 1: dry-run plan
# ---------------------------------------------------------------------------

echo "[1] dry-run plan"
PLAN_OUTPUT=$(python3 "$RUNNER" --project-dir "$TEST_TMPDIR" --registry "$REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" --dry-run 2>&1)

echo "$PLAN_OUTPUT" | grep -q "phase.yaml: on_disk=v1 target=v2" \
  && pass "phase.yaml plan detected v1→v2" \
  || fail "phase.yaml plan: $PLAN_OUTPUT"

echo "$PLAN_OUTPUT" | grep -q "skills.yaml: on_disk=v1 target=v2" \
  && pass "skills.yaml plan detected v1→v2" \
  || fail "skills.yaml plan: $PLAN_OUTPUT"

echo "$PLAN_OUTPUT" | grep -q "phase_yaml_v1_to_v2" \
  && pass "phase handler name in plan" \
  || fail "phase handler missing from plan"

# ---------------------------------------------------------------------------
# Test 2: execute migration
# ---------------------------------------------------------------------------

echo "[2] execute migration"
RUN_OUTPUT=$(python3 "$RUNNER" --project-dir "$TEST_TMPDIR" --registry "$REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" \
  --param "phase.yaml:version_stage=BETA" 2>&1)

echo "$RUN_OUTPUT" | grep -q "phase.yaml: OK v1->v2\|phase.yaml: OK v1→v2" \
  && pass "phase.yaml migrated" \
  || fail "phase.yaml run: $RUN_OUTPUT"

echo "$RUN_OUTPUT" | grep -q "skills.yaml: OK v1->v2\|skills.yaml: OK v1→v2" \
  && pass "skills.yaml migrated" \
  || fail "skills.yaml run: $RUN_OUTPUT"

# ---------------------------------------------------------------------------
# Test 3: verify phase.yaml v2 shape
# ---------------------------------------------------------------------------

echo "[3] verify phase.yaml v2 shape"
python3 - "$TEST_TMPDIR/.sweetclaude/state/phase.yaml" << 'PY' && pass "phase.yaml v2 valid" || fail "phase.yaml v2 invalid"
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]).read())
assert data.get("schema_version") == 2, f"schema_version: {data.get('schema_version')!r}"
assert data.get("version_stage") == "BETA", f"version_stage: {data.get('version_stage')!r}"
assert data.get("deference_level") == "guided", f"deference_level: {data.get('deference_level')!r}"
assert data.get("project_type") == "existing-code"
assert data.get("safety_snapshot") == "pre-sweetclaude"
awi = data.get("active_work_item") or {}
assert awi.get("type") == "tech-debt", f"work_type remap: {awi.get('type')!r}"
assert awi.get("phase") == "IMPLEMENT", f"phase carried: {awi.get('phase')!r}"
assert awi.get("workflow") == [], f"workflow default: {awi.get('workflow')!r}"
assert "init_step" not in data, "init_step should be dropped"
sys.exit(0)
PY

# ---------------------------------------------------------------------------
# Test 4: verify skills.yaml v2 shape
# ---------------------------------------------------------------------------

echo "[4] verify skills.yaml v2 shape"
python3 - "$TEST_TMPDIR/.sweetclaude/state/skills.yaml" << 'PY' && pass "skills.yaml v2 valid" || fail "skills.yaml v2 invalid"
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]).read())
assert data.get("schema_version") == 2, f"schema_version: {data.get('schema_version')!r}"

# product-milestones was enabled: true → active
m = data.get("product-milestones") or {}
assert m.get("status") == "active", f"product-milestones status: {m.get('status')!r}"
assert m.get("last_changed_by") == "migrated"
assert "enabled" not in m, "enabled should be dropped"
assert "onboarded_at" not in m, "onboarded_at should be dropped"

# product-parking-lot was enabled: false with onboarded_at → paused
p = data.get("product-parking-lot") or {}
assert p.get("status") == "paused", f"product-parking-lot status: {p.get('status')!r}"
assert p.get("last_changed_at") == "2026-04-20", f"paused last_changed_at: {p.get('last_changed_at')!r}"

# user-personas was enabled: false with onboarded_at: ~ → uninitialized
u = data.get("user-personas") or {}
assert u.get("status") == "uninitialized", f"user-personas status: {u.get('status')!r}"
assert u.get("last_changed_at") is None
assert u.get("last_changed_by") is None
sys.exit(0)
PY

# ---------------------------------------------------------------------------
# Test 5: idempotency — re-running is a no-op
# ---------------------------------------------------------------------------

echo "[5] idempotency"
RERUN_OUTPUT=$(python3 "$RUNNER" --project-dir "$TEST_TMPDIR" --registry "$REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" 2>&1)
echo "$RERUN_OUTPUT" | grep -q "phase.yaml: idempotent" \
  && pass "phase.yaml is no-op on re-run" \
  || fail "phase.yaml re-run: $RERUN_OUTPUT"
echo "$RERUN_OUTPUT" | grep -q "skills.yaml: idempotent" \
  && pass "skills.yaml is no-op on re-run" \
  || fail "skills.yaml re-run: $RERUN_OUTPUT"

# ---------------------------------------------------------------------------
# Test 6: chain_broken when a handler is missing
# ---------------------------------------------------------------------------

echo "[6] chain_broken named failure mode"
# Create a registry referencing a non-existent handler.
BAD_REGISTRY="$TEST_TMPDIR/bad-registry.yaml"
cat > "$BAD_REGISTRY" << 'YAML'
schema_version: 1
state_files:
  phase.yaml:
    current_version: 2
    backup_required: false
    migrations:
      - from: 1
        to: 2
        handler: phase_yaml_v1_to_v999
YAML

# Reset phase.yaml back to v1.
cat > "$TEST_TMPDIR/.sweetclaude/state/phase.yaml" << 'YAML'
schema_version: 1
phase: DISCOVER
work_type: net-new
deference_level: collaborative
project_type: new
safety_snapshot: ""
YAML

CHAIN_OUTPUT=$(python3 "$RUNNER" --project-dir "$TEST_TMPDIR" --registry "$BAD_REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" --file phase.yaml 2>&1 || true)
echo "$CHAIN_OUTPUT" | grep -q "chain_broken" \
  && pass "chain_broken failure mode emitted" \
  || fail "chain_broken: $CHAIN_OUTPUT"

# ---------------------------------------------------------------------------

echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "FAILURES: $FAILED"
  exit 1
fi
