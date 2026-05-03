#!/bin/bash
set -e
echo "=== E2E Migration Test ==="
TEST_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR" EXIT
mkdir -p "$TEST_TMPDIR/.sweetclaude/state" "$TEST_TMPDIR/.sweetclaude/product"

# Write realistic old-schema files
cat > "$TEST_TMPDIR/.sweetclaude/state/phase.yaml" << 'YAML'
schema_version: 2
version_stage: BETA
deference_level: collaborative
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
product-user-personas:
  status: uninitialized
product-user-stories:
  status: active
  last_changed_at: "2026-05-01"
document-corpus:
  status: uninitialized
YAML

cat > "$TEST_TMPDIR/.sweetclaude/state/improvement-register.md" << 'MD'
- Always sync to installed after editing skills
- Push after every commit
- Don't re-ask questions already answered
MD

# Run migration
python3 scripts/migrate-to-sweetclaude-yaml.py \
  --project-dir "$TEST_TMPDIR" \
  --installed-version "2.40.0"

echo "Migration ran. Verifying output..."

python3 - "$TEST_TMPDIR" << 'PY'
import yaml, os, sys
base = sys.argv[1]
sc = yaml.safe_load(open(f'{base}/.sweetclaude/state/sweetclaude.yaml'))

# Schema
assert sc['schema_version'] == 1,           f"schema_version: {sc['schema_version']}"
assert sc['framework']['migration_status'] == 'complete', f"migration_status: {sc['framework']['migration_status']}"
assert sc['framework']['setup_complete'] == True,         "setup_complete"
assert sc['framework']['installed_version'] == '2.40.0',  f"installed_version: {sc['framework']['installed_version']}"

# Project fields from phase.yaml
assert sc['project']['version_stage'] == 'BETA',           f"version_stage: {sc['project']['version_stage']}"
assert sc['session']['deference_level'] == 'collaborative', f"deference_level: {sc['session']['deference_level']}"
assert sc['project']['type'] == 'existing-code',            f"project_type: {sc['project']['type']}"

# Features from skills.yaml
assert sc['features']['product_milestones']['status'] == 'active',    "milestones"
assert sc['features']['product_backlog']['status']    == 'active',    "backlog"
assert sc['features']['product_personas']['status']   == 'not_offered',"personas"
assert sc['features']['product_stories']['status']    == 'active',    "stories"
assert sc['features']['document_corpus']['status']    == 'not_offered',"corpus"

# Learnings from improvement-register.md
assert len(sc['learnings']) == 3,  f"learnings count: {len(sc['learnings'])}"
assert 'sync' in sc['learnings'][0].lower(), f"learning 0: {sc['learnings'][0]}"

# Archive created (shutil.move — originals gone)
assert os.path.exists(f'{base}/.sweetclaude/state/archive/phase.yaml.bak'),  "phase archive missing"
assert os.path.exists(f'{base}/.sweetclaude/state/archive/skills.yaml.bak'), "skills archive missing"
assert not os.path.exists(f'{base}/.sweetclaude/state/phase.yaml'),   "phase.yaml still present after move"
assert not os.path.exists(f'{base}/.sweetclaude/state/skills.yaml'),  "skills.yaml still present after move"

print("ALL ASSERTIONS PASS")
PY
