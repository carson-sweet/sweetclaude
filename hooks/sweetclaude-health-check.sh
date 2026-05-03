#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude 24h health check — consistency scan + version check.
# Called by session-preflight.sh. Reads/writes sweetclaude.yaml.
# Requires: PROJECT_DIR env var set to project root.

set -euo pipefail

SC_YAML="${PROJECT_DIR}/.sweetclaude/state/sweetclaude.yaml"

[ -f "$SC_YAML" ] || exit 0

NOW_ISO=$(python3 -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat(timespec='seconds'))")

hours_since() {
  python3 -c "
from datetime import datetime, timezone
ts = '$1'
if not ts or ts == 'None': print(9999); exit()
try:
    t = datetime.fromisoformat(ts.replace('Z','+00:00'))
    diff = (datetime.now(timezone.utc) - t).total_seconds() / 3600
    print(int(diff))
except: print(9999)
"
}

update_yaml_field() {
  local key="$1" val="$2"
  python3 - "$SC_YAML" "$key" "$val" << 'PY'
import sys, yaml
path, key, val = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f: d = yaml.safe_load(f) or {}
parts = key.split('.')
node = d
for p in parts[:-1]:
    node = node.setdefault(p, {})
node[parts[-1]] = None if val == 'null' else val
with open(path, 'w') as f: yaml.dump(d, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
PY
}

# Always stamp hook_last_ran
update_yaml_field "framework.hook_last_ran" "$NOW_ISO"

# Read timestamps
LAST_CONSISTENCY=$(python3 -c "
import yaml
d = yaml.safe_load(open('$SC_YAML')) or {}
print(d.get('framework',{}).get('consistency',{}).get('last_checked') or 'None')
" 2>/dev/null)

LAST_UPDATE=$(python3 -c "
import yaml
d = yaml.safe_load(open('$SC_YAML')) or {}
print(d.get('framework',{}).get('update',{}).get('last_checked') or 'None')
" 2>/dev/null)

# --- Consistency check (every 24h) ---
if [ "$(hours_since "$LAST_CONSISTENCY")" -gt 24 ]; then
  DRIFT=""

  # Check hooks.json exists
  HOOKS_JSON="${HOME}/.claude/hooks/sweetclaude/hooks.json"
  if [ ! -f "$HOOKS_JSON" ]; then
    DRIFT="hooks.json_missing"
  else
    for required_hook in session-preflight.sh preflight-guard.sh; do
      if ! grep -q "$required_hook" "$HOOKS_JSON" 2>/dev/null; then
        DRIFT="${DRIFT} hook:${required_hook}"
      fi
    done
  fi

  # Check sweetclaude rules files
  RULES_DIR="$HOME/.claude/rules/sweetclaude"
  for rules_file in interaction-model.md phase-gates.md tdd-levels.md; do
    if [ ! -f "$RULES_DIR/$rules_file" ]; then
      DRIFT="${DRIFT} rules:${rules_file}"
    fi
  done

  DRIFT="${DRIFT# }"  # trim leading space

  if [ -n "$DRIFT" ]; then
    python3 - "$SC_YAML" "$DRIFT" << 'PY'
import sys, yaml
path, drift_str = sys.argv[1], sys.argv[2]
with open(path) as f: d = yaml.safe_load(f) or {}
d.setdefault('framework',{}).setdefault('consistency',{})['status'] = 'drift_detected'
d['framework']['consistency']['drift'] = drift_str.split()
d['framework']['consistency']['check_error'] = None
with open(path, 'w') as f: yaml.dump(d, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
PY
  else
    python3 - "$SC_YAML" << 'PY'
import sys, yaml
path = sys.argv[1]
with open(path) as f: d = yaml.safe_load(f) or {}
d.setdefault('framework',{}).setdefault('consistency',{})['status'] = 'ok'
d['framework']['consistency']['check_error'] = None
with open(path, 'w') as f: yaml.dump(d, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
PY
  fi
  update_yaml_field "framework.consistency.last_checked" "$NOW_ISO"
fi

# --- Version check (every 24h) ---
if [ "$(hours_since "$LAST_UPDATE")" -gt 24 ]; then
  INSTALLED=$(python3 -c "
import json
try:
    d = json.load(open('$HOME/.claude/plugins/installed_plugins.json'))
    e = [v for k,v in d.get('plugins',{}).items() if 'sweetclaude' in k.lower()]
    print(e[0][0].get('version','unknown') if e and e[0] else 'unknown')
except: print('unknown')
" 2>/dev/null)

  REPO_VERSION=$(python3 -c "
import json
try: print(json.load(open('$HOME/dev/sweetclaude/package.json')).get('version',''))
except: print('')
" 2>/dev/null)

  if [ -n "$REPO_VERSION" ] && [ "$REPO_VERSION" != "$INSTALLED" ] && [ "$REPO_VERSION" != "unknown" ]; then
    python3 - "$SC_YAML" "$REPO_VERSION" << 'PY'
import sys, yaml
path, ver = sys.argv[1], sys.argv[2]
with open(path) as f: d = yaml.safe_load(f) or {}
d.setdefault('framework',{}).setdefault('update',{})['available'] = ver
d['framework']['update']['check_error'] = None
with open(path, 'w') as f: yaml.dump(d, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
PY
  else
    python3 - "$SC_YAML" << 'PY'
import sys, yaml
path = sys.argv[1]
with open(path) as f: d = yaml.safe_load(f) or {}
d.setdefault('framework',{}).setdefault('update',{})['available'] = None
d['framework']['update']['check_error'] = None
with open(path, 'w') as f: yaml.dump(d, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
PY
  fi
  update_yaml_field "framework.update.last_checked" "$NOW_ISO"
fi

exit 0
