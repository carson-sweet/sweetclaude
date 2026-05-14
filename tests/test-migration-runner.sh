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
  --migrations-dir "$MIGRATIONS_DIR" \
  --file phase.yaml --file skills.yaml \
  --dry-run 2>&1)

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
  --file phase.yaml --file skills.yaml \
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
  --migrations-dir "$MIGRATIONS_DIR" \
  --file phase.yaml --file skills.yaml 2>&1)
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
  --file phase.yaml --file skills.yaml \
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
# Test 10: recoverable migration error (Gap #5)
# ---------------------------------------------------------------------------

echo "[10] recoverable migration error"

REC_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR $DIR_TMPDIR $VAR_TMPDIR $SCAN_TMPDIR $REC_TMPDIR" EXIT

mkdir -p "$REC_TMPDIR/.sweetclaude/product/recoverable"

REC_REGISTRY="$REC_TMPDIR/registry.yaml"
cat > "$REC_REGISTRY" << 'YAML'
schema_version: 1
state_files:
  recoverable:
    type: directory
    description: "Fixture that always raises a recoverable error"
    path_template: "{product_base}/recoverable"
    current_version: 2
    backup_required: false
    migrations:
      - from: 1
        to: 2
        handler: recoverable_v1_to_v2
YAML

REC_HANDLER_DIR="$REPO_ROOT/tests/fixtures/migration-runner"

# Library-level test (the CLI doesn't surface recovery_menu in plain-text output).
python3 - "$REC_TMPDIR" "$REC_REGISTRY" "$REC_HANDLER_DIR" \
  "$REPO_ROOT/scripts/migrations" << 'PY' \
  && pass "recoverable error caught; recovery_menu populated with handler + universal options" \
  || fail "recoverable error path broken"
import sys
sys.path.insert(0, sys.argv[4])
from runner import MigrationRunner, FAILURE_RECOVERABLE

project_dir, registry, handler_dir, _ = sys.argv[1:]
runner = MigrationRunner(project_dir=project_dir, registry_path=registry, migrations_dir=handler_dir)
results = runner.run()
assert len(results) == 1, f"expected 1 result, got {len(results)}"
r = results[0]
assert r.failure_mode == FAILURE_RECOVERABLE, f"failure_mode: {r.failure_mode!r}"
assert r.recovery_menu is not None, "recovery_menu not populated"
menu = r.recovery_menu
assert menu["message"].startswith("ITEM-007"), f"message: {menu['message']!r}"
assert menu["current_id"] == "ITEM-007", f"current_id: {menu['current_id']!r}"
labels = [o["label"] for o in menu["options"]]
assert len(menu["options"]) == 5, f"expected 5 options, got {len(menu['options'])}: {labels}"
actions = [o["action"] for o in menu["options"]]
assert "skip" in actions, f"missing skip in actions: {actions}"
assert "rollback" in actions, f"missing rollback in actions: {actions}"
assert "set_type" in actions
assert "open_for_manual_edit" in actions
sys.exit(0)
PY

# ---------------------------------------------------------------------------
# Test 11: snapshot + rollback round-trip (Gap #6)
# ---------------------------------------------------------------------------

echo "[11] snapshot + rollback"

SNAP_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR $DIR_TMPDIR $VAR_TMPDIR $SCAN_TMPDIR $REC_TMPDIR $SNAP_TMPDIR" EXIT

(
  cd "$SNAP_TMPDIR"
  git init -q -b main 2>/dev/null
  git config user.email "test@example.com"
  git config user.name "Test"
  mkdir -p .sweetclaude/state
  cat > .sweetclaude/state/phase.yaml << 'YAML'
schema_version: 1
phase: IMPLEMENT
deference_level: collaborative
project_type: existing-code
safety_snapshot: ""
YAML
  echo "initial" > README.md
  git add README.md
  git -c commit.gpgsign=false commit -q -m "initial" 2>/dev/null
) || { fail "git init/commit failed"; }

python3 - "$SNAP_TMPDIR" "$REPO_ROOT/scripts/migrations" << 'PY' \
  && pass "snapshot + rollback round-trip" \
  || fail "snapshot/rollback round-trip broken"
import sys, os, yaml
sys.path.insert(0, sys.argv[2])
from runner import MigrationRunner

project_dir, _ = sys.argv[1:]
phase_path = os.path.join(project_dir, ".sweetclaude/state/phase.yaml")

# Minimal empty registry — snapshot/rollback don't read it for state files.
reg_path = os.path.join(project_dir, "registry.yaml")
with open(reg_path, "w") as f:
    f.write("schema_version: 1\nstate_files: {}\n")
runner = MigrationRunner(project_dir=project_dir, registry_path=reg_path)

snap = runner.create_snapshot()
assert snap.tarball_verified, "tarball not verified"
assert snap.git_tag_created, "git tag not created"
assert os.path.exists(snap.tarball_path), f"tarball missing: {snap.tarball_path}"
assert ".sweetclaude" in snap.paths_in_tarball, f"paths: {snap.paths_in_tarball}"

# Mutate.
with open(phase_path, "w") as f:
    f.write("schema_version: 99\nphase: BROKEN\n")

ok, reason = runner.verify_snapshot(snap)
assert ok, f"verify failed: {reason}"

ok, reason = runner.rollback(snap)
assert ok, f"rollback failed: {reason}"

restored = yaml.safe_load(open(phase_path).read())
assert restored["schema_version"] == 1, f"post-rollback: {restored}"
assert restored["phase"] == "IMPLEMENT", f"post-rollback: {restored}"

sys.exit(0)
PY

# Retention: create more snapshots, expect 5 retained.
for i in 1 2 3 4 5 6; do
  sleep 1
  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/scripts/migrations')
from runner import MigrationRunner
runner = MigrationRunner(project_dir='$SNAP_TMPDIR', registry_path='$SNAP_TMPDIR/registry.yaml')
runner.create_snapshot()
" 2>/dev/null
done
RETAINED=$(ls "$SNAP_TMPDIR/.sweetclaude/state/backups/pre-migration-"*.tar.gz 2>/dev/null | wc -l | tr -d ' ')
if [ "$RETAINED" = "5" ]; then
  pass "snapshot retention: 5 kept after multiple creations"
else
  fail "retention: expected 5, got $RETAINED"
fi

# ---------------------------------------------------------------------------
# Test 12: sweetclaude.yaml v1 -> v2 (decline amnesty + stale cleanup)
# ---------------------------------------------------------------------------

echo "[12] sweetclaude.yaml v1->v2"

SC_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR $DIR_TMPDIR $VAR_TMPDIR $SCAN_TMPDIR $REC_TMPDIR $SNAP_TMPDIR $SC_TMPDIR" EXIT

mkdir -p "$SC_TMPDIR/.sweetclaude/state"

# 12a. declined: true (legacy boolean) gets cleared to null.
cat > "$SC_TMPDIR/.sweetclaude/state/sweetclaude.yaml" << 'YAML'
schema_version: 1
framework:
  installed_version: 3.66.0
  update:
    available: 3.67.0
    declined: true
    check_error: "transient gh api 502"
YAML

python3 "$RUNNER" --project-dir "$SC_TMPDIR" --registry "$REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" --file sweetclaude.yaml >/dev/null 2>&1

python3 - "$SC_TMPDIR/.sweetclaude/state/sweetclaude.yaml" << 'PY' \
  && pass "declined: true -> null; check_error cleared; schema_version bumped" \
  || fail "amnesty case failed"
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]).read()) or {}
assert data.get("schema_version") == 2, f"schema_version: {data.get('schema_version')!r}"
upd = (data.get("framework") or {}).get("update") or {}
assert upd.get("declined") is None, f"declined: {upd.get('declined')!r}"
assert upd.get("check_error") is None, f"check_error: {upd.get('check_error')!r}"
assert upd.get("available") == "3.67.0", f"available preserved: {upd.get('available')!r}"
sys.exit(0)
PY

# 12b. Stale available (older than installed) gets cleared.
cat > "$SC_TMPDIR/.sweetclaude/state/sweetclaude.yaml" << 'YAML'
schema_version: 1
framework:
  installed_version: 3.66.0
  update:
    available: 3.65.0
    declined: 3.65.0
YAML

python3 "$RUNNER" --project-dir "$SC_TMPDIR" --registry "$REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" --file sweetclaude.yaml >/dev/null 2>&1

python3 - "$SC_TMPDIR/.sweetclaude/state/sweetclaude.yaml" << 'PY' \
  && pass "stale available cleared; version-string declined preserved" \
  || fail "stale available case failed"
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]).read()) or {}
upd = (data.get("framework") or {}).get("update") or {}
assert upd.get("available") is None, f"stale available: {upd.get('available')!r}"
assert upd.get("declined") == "3.65.0", f"declined preserved: {upd.get('declined')!r}"
sys.exit(0)
PY

# 12c. Real pending update (available > installed) survives unchanged.
cat > "$SC_TMPDIR/.sweetclaude/state/sweetclaude.yaml" << 'YAML'
schema_version: 1
framework:
  installed_version: 3.66.0
  update:
    available: 3.67.0
    declined: null
YAML

python3 "$RUNNER" --project-dir "$SC_TMPDIR" --registry "$REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" --file sweetclaude.yaml >/dev/null 2>&1

python3 - "$SC_TMPDIR/.sweetclaude/state/sweetclaude.yaml" << 'PY' \
  && pass "real pending update preserved" \
  || fail "pending update preservation failed"
import sys, yaml
data = yaml.safe_load(open(sys.argv[1]).read()) or {}
upd = (data.get("framework") or {}).get("update") or {}
assert upd.get("available") == "3.67.0", f"available: {upd.get('available')!r}"
assert upd.get("declined") is None
sys.exit(0)
PY

# 12d. Idempotency: re-run is a no-op once at v2.
RERUN_SC=$(python3 "$RUNNER" --project-dir "$SC_TMPDIR" --registry "$REGISTRY" \
  --migrations-dir "$MIGRATIONS_DIR" --file sweetclaude.yaml 2>&1)
echo "$RERUN_SC" | grep -q "sweetclaude.yaml: idempotent" \
  && pass "sweetclaude.yaml is no-op on re-run at v2" \
  || fail "sweetclaude.yaml re-run: $RERUN_SC"

# ---------------------------------------------------------------------------
# Test 13: optional: true — missing optional file is not flagged as drift
# Regression for BUG-008: skills.yaml absent in projects that never activated
# the data-owning skills caused file_missing → Step 3c failure in _migrate.
# ---------------------------------------------------------------------------

echo "[13] optional file absent → no drift, no failure"

OPT_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR $DIR_TMPDIR $VAR_TMPDIR $SCAN_TMPDIR $REC_TMPDIR $SNAP_TMPDIR $SC_TMPDIR $OPT_TMPDIR" EXIT

mkdir -p "$OPT_TMPDIR/.sweetclaude/state"

# Registry with one required and one optional file, both absent.
OPT_REGISTRY="$OPT_TMPDIR/registry.yaml"
cat > "$OPT_REGISTRY" << 'YAML'
schema_version: 1
state_files:
  required.yaml:
    description: "A required file"
    current_version: 2
    backup_required: false
    migrations:
      - from: 1
        to: 2
        handler: phase_yaml_v1_to_v2
  optional.yaml:
    description: "An optional file"
    current_version: 2
    backup_required: false
    optional: true
    migrations:
      - from: 1
        to: 2
        handler: phase_yaml_v1_to_v2
YAML

python3 - "$OPT_TMPDIR" "$OPT_REGISTRY" "$MIGRATIONS_DIR" << 'PY' \
  && pass "optional: absent optional file not in drift_count" \
  || fail "optional: absent optional file wrongly flagged as drift"
import sys
sys.path.insert(0, sys.argv[3])
from runner import MigrationRunner
runner = MigrationRunner(project_dir=sys.argv[1], registry_path=sys.argv[2], migrations_dir=sys.argv[3])
result = runner.scan_drift()
# required.yaml missing → flagged; optional.yaml missing → not flagged
findings = {f["file_key"]: f for f in result["findings"]}
assert findings.get("optional.yaml", {}).get("needs_migration") is False, \
    f"optional.yaml should not need migration: {findings.get('optional.yaml')}"
assert findings.get("required.yaml", {}).get("needs_migration") is True, \
    f"required.yaml should need migration: {findings.get('required.yaml')}"
assert result["drift_count"] == 1, f"drift_count should be 1, got {result['drift_count']}"
sys.exit(0)
PY

python3 - "$OPT_TMPDIR" "$OPT_REGISTRY" "$MIGRATIONS_DIR" << 'PY' \
  && pass "optional: run() on absent optional file returns success (not file_missing)" \
  || fail "optional: run() returned unexpected failure for absent optional file"
import sys
sys.path.insert(0, sys.argv[3])
from runner import MigrationRunner, FAILURE_FILE_MISSING
runner = MigrationRunner(project_dir=sys.argv[1], registry_path=sys.argv[2], migrations_dir=sys.argv[3])
results = {r.file_key: r for r in runner.run(["optional.yaml"])}
r = results.get("optional.yaml")
assert r is not None, "no result for optional.yaml"
assert r.success is True, f"expected success, got failure_mode={r.failure_mode!r}"
assert r.failure_mode != FAILURE_FILE_MISSING, f"unexpected file_missing on optional file"
sys.exit(0)
PY

# ---------------------------------------------------------------------------

echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "FAILURES: $FAILED"
  exit 1
fi
