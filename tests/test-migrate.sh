#!/bin/bash
set -e
TEST_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR" EXIT

# Create mock old-schema state files
mkdir -p "$TEST_TMPDIR/.sweetclaude/state"

cat > "$TEST_TMPDIR/.sweetclaude/state/phase.yaml" << 'YAML'
schema_version: 2
version_stage: BETA
deference_level: guided
project_type: existing-code
safety_snapshot: pre-sweetclaude
last_work_item_id: BL-047
active_work_item:
  id: ~
  type: ~
  workflow: []
  phase: ~
  title: ~
  started: ~
  entry_category: ~
YAML

cat > "$TEST_TMPDIR/.sweetclaude/state/skills.yaml" << 'YAML'
schema_version: 2
product-milestones:
  status: active
  last_changed_at: "2026-05-01"
product-backlog:
  status: active
  last_changed_at: "2026-05-01"
product-user-stories:
  status: active
  last_changed_at: "2026-05-01"
YAML

# Run migration script
python3 scripts/migrate-to-sweetclaude-yaml.py \
  --project-dir "$TEST_TMPDIR" \
  --installed-version "2.40.0"

# Verify output
python3 -c "
import yaml, os, sys
sc = yaml.safe_load(open('$TEST_TMPDIR/.sweetclaude/state/sweetclaude.yaml'))
assert sc['schema_version'] == 1, 'schema_version'
assert sc['project']['version_stage'] == 'BETA', 'version_stage'
assert sc['session']['deference_level'] == 'guided', 'deference_level'
assert sc['project']['type'] == 'existing-code', 'project_type'
assert sc['framework']['migration_status'] == 'complete', 'migration_status'
assert sc['framework']['migrated_from'] is not None, 'migrated_from'
assert sc['features']['product_milestones']['status'] == 'active', 'milestones'
assert sc['features']['product_backlog']['status'] == 'active', 'backlog'
assert sc['features']['product_personas']['status'] == 'not_offered', 'personas'
assert sc['features']['product_stories']['status'] == 'active', 'stories'
# Old files archived
assert os.path.exists('$TEST_TMPDIR/.sweetclaude/state/archive/phase.yaml.bak'), 'phase archive'
assert os.path.exists('$TEST_TMPDIR/.sweetclaude/state/archive/skills.yaml.bak'), 'skills archive'
print('MIGRATION_PASS')
"

# Test idempotency: re-running should be a no-op
OUTPUT=$(python3 scripts/migrate-to-sweetclaude-yaml.py \
  --project-dir "$TEST_TMPDIR" \
  --installed-version "2.40.0" 2>&1)
echo "$OUTPUT" | grep -q "Already migrated" || { echo "FAIL: idempotency check failed, output: $OUTPUT"; exit 1; }
echo "IDEMPOTENCY_PASS"

echo "ALL PASS"
