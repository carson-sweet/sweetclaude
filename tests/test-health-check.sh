#!/bin/bash
set -e
TEST_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_TMPDIR" EXIT
mkdir -p "$TEST_TMPDIR/.sweetclaude/state"

# Write sweetclaude.yaml with stale timestamps (25 hours ago)
STALE=$(python3 -c "
from datetime import datetime, timezone, timedelta
print((datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(timespec='seconds'))
")

python3 -c "
import yaml, sys
d = {
  'schema_version': 1,
  'framework': {
    'installed_version': '2.40.0',
    'setup_complete': True,
    'hook_last_ran': None,
    'consistency': {'last_checked': '$STALE', 'status': 'ok', 'drift': [], 'check_error': None},
    'update': {'available': None, 'last_checked': '$STALE', 'declined': False, 'check_error': None},
  }
}
open('$TEST_TMPDIR/.sweetclaude/state/sweetclaude.yaml','w').write(yaml.dump(d))
"

PROJECT_DIR="$TEST_TMPDIR" bash hooks/sweetclaude-health-check.sh

# Verify timestamps were updated
python3 -c "
import yaml
from datetime import datetime, timezone
d = yaml.safe_load(open('$TEST_TMPDIR/.sweetclaude/state/sweetclaude.yaml'))
stale = '$STALE'
cons_ts = str(d['framework']['consistency']['last_checked'] or '')
upd_ts  = str(d['framework']['update']['last_checked'] or '')
hook_ts = d['framework']['hook_last_ran']
assert cons_ts != stale, f'consistency.last_checked not updated: {cons_ts}'
assert upd_ts  != stale, f'update.last_checked not updated: {upd_ts}'
assert hook_ts is not None, 'hook_last_ran not written'
print('PASS')
"

# Test 2: drift cleared in ok-path
python3 -c "
import yaml
d = yaml.safe_load(open('$TEST_TMPDIR/.sweetclaude/state/sweetclaude.yaml'))
d['framework']['consistency']['status'] = 'drift_detected'
d['framework']['consistency']['drift'] = ['fake_drift']
d['framework']['consistency']['last_checked'] = '$STALE'
open('$TEST_TMPDIR/.sweetclaude/state/sweetclaude.yaml','w').write(yaml.dump(d))
"

PROJECT_DIR="$TEST_TMPDIR" bash hooks/sweetclaude-health-check.sh

python3 -c "
import yaml
d = yaml.safe_load(open('$TEST_TMPDIR/.sweetclaude/state/sweetclaude.yaml'))
assert d['framework']['consistency']['status'] == 'ok', f\"drift not cleared: {d['framework']['consistency']['status']}\"
assert d['framework']['consistency']['drift'] == [], f\"drift list not empty: {d['framework']['consistency']['drift']}\"
print('DRIFT_CLEAR_PASS')
"
