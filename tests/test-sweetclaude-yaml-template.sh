#!/bin/bash
set -e
TEST_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR" EXIT

python3 scripts/sweetclaude-yaml-template.py \
  --name "test-project" \
  --type "existing-code" \
  --version-stage "BETA" \
  --output "$TEST_TMPDIR/sweetclaude.yaml"

# Verify file was written
[ -f "$TEST_TMPDIR/sweetclaude.yaml" ] || { echo "FAIL: file not written"; exit 1; }

# Verify it parses as valid YAML
python3 -c "
import yaml
with open('$TEST_TMPDIR/sweetclaude.yaml') as f:
    d = yaml.safe_load(f)
assert d['schema_version'] == 1, 'schema_version must be 1'
assert d['project']['name'] == 'test-project'
assert d['project']['type'] == 'existing-code'
assert d['framework']['setup_complete'] == False
assert d['framework']['migration_status'] is None, f"fresh install should have None migration_status"
assert 'features' in d
assert 'work_history' in d
assert 'learnings' in d
for feat in ['product_milestones','product_backlog','product_personas','product_stories','document_corpus','usage_tracking','behavioral_regression']:
    assert feat in d['features'], f'missing feature: {feat}'
    assert d['features'][feat]['status'] == 'not_offered'
    assert d['features'][feat]['defer_until'] is None
    assert d['features'][feat]['offered_at'] is None
    assert d['features'][feat]['decided_at'] is None
assert 'session' in d, 'missing key: session'
assert 'work' in d, 'missing key: work'

# Also test migrated-from path
import subprocess, tempfile, os
with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as tmp:
    tmp_path = tmp.name
subprocess.run(['python3', 'scripts/sweetclaude-yaml-template.py',
    '--name', 'migrated-proj', '--migrated-from', '2.39.0',
    '--output', tmp_path], check=True)
dm = yaml.safe_load(open(tmp_path))
os.unlink(tmp_path)
assert dm['framework']['migrated_from'] == '2.39.0', 'migrated_from not set'
assert dm['framework']['migrated_at'] is not None, 'migrated_at should be set'
print('PASS')
"
