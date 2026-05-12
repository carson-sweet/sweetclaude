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
# Test 7: directory-entry migration (artifact dirs)
# ---------------------------------------------------------------------------

echo "[7] directory-entry migration"

DIR_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR $DIR_TMPDIR" EXIT

# v1 layout: ITEM-NNN-slug.md at top level with frontmatter type field
mkdir -p "$DIR_TMPDIR/.sweetclaude/product/backlog"
cat > "$DIR_TMPDIR/.sweetclaude/product/backlog/ITEM-001-add-oauth.md" << 'MD'
---
id: ITEM-001
title: Add OAuth login
type: story
---
Body content for OAuth login.
MD
cat > "$DIR_TMPDIR/.sweetclaude/product/backlog/ITEM-002-crash-empty.md" << 'MD'
---
id: ITEM-002
title: Crash on empty input
type: bug
---
Body content for crash bug.
MD

# Registry that references the fixture handler.
DIR_REGISTRY="$DIR_TMPDIR/registry.yaml"
cat > "$DIR_REGISTRY" << 'YAML'
schema_version: 1
state_files:
  backlog:
    type: directory
    description: "Fixture artifact directory"
    path_template: "{product_base}/backlog"
    current_version: 2
    backup_required: false
    migrations:
      - from: 1
        to: 2
        handler: items_dir_v1_to_v2
YAML

DIR_HANDLER_DIR="$REPO_ROOT/tests/fixtures/migration-runner"

# Dry-run plan should detect v1.
DIR_PLAN=$(python3 "$RUNNER" --project-dir "$DIR_TMPDIR" --registry "$DIR_REGISTRY" \
  --migrations-dir "$DIR_HANDLER_DIR" --dry-run 2>&1)
echo "$DIR_PLAN" | grep -q "backlog: on_disk=v1 target=v2" \
  && pass "directory plan detected v1->v2 via pattern inference" \
  || fail "directory plan: $DIR_PLAN"

# Execute.
DIR_RUN=$(python3 "$RUNNER" --project-dir "$DIR_TMPDIR" --registry "$DIR_REGISTRY" \
  --migrations-dir "$DIR_HANDLER_DIR" 2>&1)
echo "$DIR_RUN" | grep -qE "backlog: OK v1.>v2|backlog: OK v1.v2" \
  && pass "directory migration executed" \
  || fail "directory run: $DIR_RUN"

# Verify v2 layout.
if [ -f "$DIR_TMPDIR/.sweetclaude/product/backlog/story/THING-001-add-oauth.md" ] \
  && [ -f "$DIR_TMPDIR/.sweetclaude/product/backlog/bug/THING-001-crash-empty.md" ] \
  && [ ! -f "$DIR_TMPDIR/.sweetclaude/product/backlog/ITEM-001-add-oauth.md" ]; then
  pass "directory v2 layout correct (per-type subdirs, originals removed)"
else
  fail "directory v2 layout wrong"
  ls -laR "$DIR_TMPDIR/.sweetclaude/product/backlog"
fi

# Verify MIGRATION-MAP.md written.
MAP="$DIR_TMPDIR/.sweetclaude/product/backlog/MIGRATION-MAP.md"
if [ -f "$MAP" ] && grep -q "ITEM-001" "$MAP" && grep -q "THING-001" "$MAP"; then
  pass "MIGRATION-MAP.md written next to artifacts"
else
  fail "MIGRATION-MAP.md missing or malformed"
  [ -f "$MAP" ] && cat "$MAP"
fi

# Verify idempotency for directory entry.
DIR_RERUN=$(python3 "$RUNNER" --project-dir "$DIR_TMPDIR" --registry "$DIR_REGISTRY" \
  --migrations-dir "$DIR_HANDLER_DIR" 2>&1)
echo "$DIR_RERUN" | grep -q "backlog: idempotent" \
  && pass "directory migration is idempotent on re-run" \
  || fail "directory re-run: $DIR_RERUN"

# ---------------------------------------------------------------------------
# Test 8: path_template variable resolution from artifact-privacy.yaml
# ---------------------------------------------------------------------------

echo "[8] path_template resolution from artifact-privacy.yaml"

VAR_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR $DIR_TMPDIR $VAR_TMPDIR" EXIT

# Use docs/product as product_base instead of the default .sweetclaude/product.
mkdir -p "$VAR_TMPDIR/.sweetclaude" "$VAR_TMPDIR/docs/product/backlog"
cat > "$VAR_TMPDIR/.sweetclaude/artifact-privacy.yaml" << 'YAML'
categories:
  product:
    base_path: docs/product
YAML
cat > "$VAR_TMPDIR/docs/product/backlog/ITEM-001-thing.md" << 'MD'
---
id: ITEM-001
title: A thing
type: story
---
body
MD

VAR_PLAN=$(python3 "$RUNNER" --project-dir "$VAR_TMPDIR" --registry "$DIR_REGISTRY" \
  --migrations-dir "$DIR_HANDLER_DIR" --dry-run 2>&1)
echo "$VAR_PLAN" | grep -q "backlog: on_disk=v1 target=v2" \
  && pass "path_template resolved {product_base} -> docs/product" \
  || fail "var plan: $VAR_PLAN"

VAR_RUN=$(python3 "$RUNNER" --project-dir "$VAR_TMPDIR" --registry "$DIR_REGISTRY" \
  --migrations-dir "$DIR_HANDLER_DIR" 2>&1)
if [ -f "$VAR_TMPDIR/docs/product/backlog/story/THING-001-thing.md" ]; then
  pass "migration ran against custom product_base (docs/product)"
else
  fail "expected file at docs/product/backlog/story/THING-001-thing.md not found; run output: $VAR_RUN"
fi

# ---------------------------------------------------------------------------
# Test 9: drift scan (Gap #4)
# ---------------------------------------------------------------------------

echo "[9] drift scan"

SCAN_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR $DIR_TMPDIR $VAR_TMPDIR $SCAN_TMPDIR" EXIT

mkdir -p "$SCAN_TMPDIR/.sweetclaude/state"
cat > "$SCAN_TMPDIR/.sweetclaude/state/phase.yaml" << 'YAML'
schema_version: 1
phase: IMPLEMENT
work_type: enhancement
deference_level: collaborative
project_type: existing-code
safety_snapshot: ""
YAML
cat > "$SCAN_TMPDIR/.sweetclaude/state/skills.yaml" << 'YAML'
schema_version: 1
product-milestones:
  enabled: true
  onboarded_at: "2026-04-01"
YAML

# 9a. Bare scan (no persist) reports drift.
SCAN1=$(python3 "$RUNNER" --project-dir "$SCAN_TMPDIR" --registry "$REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" --scan-drift 2>&1)
echo "$SCAN1" | grep -qE "drift_count|2 finding" \
  && pass "scan reports findings count" \
  || true
echo "$SCAN1" | grep -q "\[DRIFT\] phase.yaml" \
  && pass "scan flags phase.yaml as DRIFT" \
  || fail "scan output: $SCAN1"
echo "$SCAN1" | grep -q "\[DRIFT\] skills.yaml" \
  && pass "scan flags skills.yaml as DRIFT" \
  || fail "scan output: $SCAN1"

# 9b. --persist writes to sweetclaude.yaml.
python3 "$RUNNER" --project-dir "$SCAN_TMPDIR" --registry "$REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" --scan-drift --persist >/dev/null 2>&1

if [ -f "$SCAN_TMPDIR/.sweetclaude/state/sweetclaude.yaml" ]; then
  pass "sweetclaude.yaml created on --persist"
else
  fail "sweetclaude.yaml not created"
fi

python3 - "$SCAN_TMPDIR/.sweetclaude/state/sweetclaude.yaml" << 'PY' \
  && pass "persisted drift block has expected shape" \
  || fail "persisted drift shape wrong"
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]).read()) or {}
drift = (data.get("framework") or {}).get("drift") or {}
assert "last_checked" in drift, f"no last_checked: {drift}"
assert drift.get("drift_count", 0) >= 2, f"drift_count: {drift.get('drift_count')!r}"
findings = drift.get("findings") or []
keys = {f.get("file_key") for f in findings}
assert "phase.yaml" in keys and "skills.yaml" in keys, f"missing keys: {keys}"
for f in findings:
    if f.get("file_key") in {"phase.yaml", "skills.yaml"}:
        assert f.get("needs_migration") is True
        assert f.get("chain_valid") is True
sys.exit(0)
PY

# 9c. After migration runs, re-scan reports zero drift for those files.
python3 "$RUNNER" --project-dir "$SCAN_TMPDIR" --registry "$REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" \
  --param "phase.yaml:version_stage=BETA" >/dev/null 2>&1

SCAN2=$(python3 "$RUNNER" --project-dir "$SCAN_TMPDIR" --registry "$REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" --scan-drift 2>&1)
echo "$SCAN2" | grep -q "\[DRIFT\] phase.yaml" \
  && fail "scan still flags phase.yaml after migration: $SCAN2" \
  || pass "post-migration scan: phase.yaml no longer DRIFT"

# 9d. Scan against a missing-handler registry → chain_broken (chain_valid=false).
BROKEN_REGISTRY="$SCAN_TMPDIR/broken.yaml"
cat > "$BROKEN_REGISTRY" << 'YAML'
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
# Reset phase.yaml to v1.
cat > "$SCAN_TMPDIR/.sweetclaude/state/phase.yaml" << 'YAML'
schema_version: 1
phase: DISCOVER
work_type: net-new
deference_level: collaborative
project_type: new
safety_snapshot: ""
YAML

SCAN3=$(python3 "$RUNNER" --project-dir "$SCAN_TMPDIR" --registry "$BROKEN_REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" --scan-drift --file phase.yaml 2>&1)
echo "$SCAN3" | grep -q "chain_broken" \
  && pass "scan surfaces chain_broken when handler missing" \
  || fail "broken scan: $SCAN3"

# ---------------------------------------------------------------------------

echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "FAILURES: $FAILED"
  exit 1
fi
