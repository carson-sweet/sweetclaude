---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Session startup skill — pre-flight checks, drift/update offers, and initial routing."
---

!`cat .sweetclaude/state/sweetclaude.yaml 2>/dev/null || echo "SC_YAML_NOT_FOUND"`

# SweetClaude

State pre-loaded above. One read. Make a decision. Delegate.

---

## Step 1: Handle missing or unparseable file

If the pre-loaded content is `SC_YAML_NOT_FOUND`:

```bash
ls .sweetclaude/state/phase.yaml .sweetclaude/state/skills.yaml 2>/dev/null | wc -l
```

- Count > 0 → invoke `sweetclaude:_migrate` then stop (migration tells user to re-run)
- Count = 0 → invoke `sweetclaude:setup` then stop

If the pre-loaded content exists but fails YAML parsing (malformed — check by attempting to interpret it as a YAML structure):
> "Something in my config got scrambled. Let me fix it."
Invoke `sweetclaude:fix-sweetclaude`. Stop.

## Step 2: Schema version check

Read `schema_version` from pre-loaded state.
If `schema_version` is not `1`:
- Invoke `sweetclaude:_migrate --schema-upgrade`
- Stop (migration tells user to re-run)

## Step 3: Check migration status

Read `framework.migration_status`.
- `in_progress` or `failed` → invoke `sweetclaude:_migrate` (retry). Stop.
- `complete` or `null` → continue.

## Step 4: Stale hook check

Read `framework.hook_last_ran`.
If null or more than 2 hours ago:
- Invoke `sweetclaude:_health` to run checks inline
- Re-read updated values from file before continuing

To check if stale:
```bash
python3 -c "
import yaml
from datetime import datetime, timezone, timedelta
d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml')) or {}
ts = d.get('framework', {}).get('hook_last_ran')
if not ts:
    print('STALE')
    exit()
try:
    t = datetime.fromisoformat(str(ts).replace('Z','+00:00'))
    stale = (datetime.now(timezone.utc) - t) > timedelta(hours=2)
    print('STALE' if stale else 'FRESH')
except:
    print('STALE')
"
```

## Step 5: Check setup complete

Read `framework.setup_complete`.
If `false`:
- Invoke `sweetclaude:setup`. Stop.

## Step 5b: v4 hard stop — v3 artifacts present

After confirming setup is complete, check for v3 backlog files. The trigger is a v4 plugin running
against a project that hasn't migrated yet — detected by comparing the plugin version (from
`installed_plugins.json`) against the project's own `installed_version`.

```bash
# Resolve product_base from artifact-privacy.yaml; fall back to .sweetclaude/product
PRODUCT_BASE=$(python3 -c "
import yaml, pathlib
p = pathlib.Path('.sweetclaude/state/artifact-privacy.yaml')
if p.exists():
    d = yaml.safe_load(p.read_text()) or {}
    base = d.get('categories', {}).get('product', {}).get('base_path', '')
    if base:
        print(base.rstrip('/'))
        exit()
print('.sweetclaude/product')
" 2>/dev/null || echo '.sweetclaude/product')

# Detect v4 plugin: plugin version ≥ 4.x, project installed_version < 4.x
PLUGIN_V=$(python3 -c "
import json, os, re
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [e for versions in d.get('plugins', {}).values()
               for e in versions if e.get('scope') == 'user']
    for e in sorted(entries, key=lambda x: x.get('lastUpdated',''), reverse=True):
        v = e.get('version','')
        if re.match(r'^4\.', v) and 'sweetclaude' in str(e.get('installPath','')).lower():
            print(v)
            break
except Exception:
    pass
" 2>/dev/null)

PROJECT_V=$(python3 -c "
import yaml
d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml')) or {}
print(d.get('framework', {}).get('installed_version', ''))
" 2>/dev/null)

V3_FILES=$(find "${PRODUCT_BASE}/backlog" -maxdepth 1 -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' ')

# Fire if: plugin is v4 AND (project is not yet v4 OR v3 BL files exist)
PLUGIN_IS_V4=false
case "$PLUGIN_V" in 4.*) PLUGIN_IS_V4=true ;; esac

PROJECT_NOT_V4=false
case "$PROJECT_V" in 4.*) ;; *) PROJECT_NOT_V4=true ;; esac

if $PLUGIN_IS_V4 && ( $PROJECT_NOT_V4 || [ "$V3_FILES" -gt 0 ] ); then
  echo "SweetClaude v4 is installed but this project hasn't migrated yet."
  echo ""
  if [ "$V3_FILES" -gt 0 ]; then
    echo "Found $V3_FILES v3 stories at ${PRODUCT_BASE}/backlog/."
  fi
  echo ""
  echo "Migration creates a safety backup and moves stories to docs/product/. Your"
  echo "current work is not affected. A clean git working tree is not required."
  echo ""
  echo "Run: /sweetclaude:migrate"
  exit 1
fi
```

If the hard stop fires: print the message above and exit. No further skill execution.

## Step 6: Drift and update offers

Read `framework.consistency.status`.
If `drift_detected`:

```bash
python3 -c "
import yaml
d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml')) or {}
drift = d.get('framework',{}).get('consistency',{}).get('drift',[])
print(', '.join(drift) if drift else 'configuration drift detected')
"
```
> "I found some drift: [drift list]. Fix it now? (Yes / No)"
- Yes → invoke `sweetclaude:fix-sweetclaude`. Stop.
- No → continue.

Read `framework.update.available` and `framework.update.declined`.
If `available` is not null AND `declined` is false:
> "SweetClaude [available version] is out. Update now? (Yes / Not now)"
- Yes → invoke `sweetclaude:update`. Stop.
- Not now → write `declined: true` to file, continue:

```bash
python3 - .sweetclaude/state/sweetclaude.yaml << 'PY'
import sys, yaml, tempfile, os
path = sys.argv[1]
with open(path) as f: d = yaml.safe_load(f)
d.setdefault('framework',{}).setdefault('update',{})['declined'] = True
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
os.replace(tmp_name, path)
PY
```

## Step 7: Route on args

If `$ARGUMENTS` is present and non-empty:
→ invoke `sweetclaude:_route` with `$ARGUMENTS`
Stop.

## Step 8: All-clear status surface

Read from pre-loaded state:

```bash
python3 - << 'PY'
import yaml, sys
sc_path = '.sweetclaude/state/sweetclaude.yaml'
with open(sc_path) as f:
    d = yaml.safe_load(f) or {}

p = d.get('project', {})
w = d.get('work', {})
h = d.get('work_history', [])

name   = p.get('name') or 'this project'
stage  = p.get('version_stage', '')
active = w.get('active', {}) or {}
last3  = h[:3]

print(f"**{name}** · {stage}")
if active.get('title'):
    print(f"Active: {active['title']} [{active.get('phase','')}]")
elif last3:
    print(f"Last completed: {last3[0].get('title','')} ({last3[0].get('outcome','')})")
else:
    print("No work history yet.")
PY
```

Show the output, then ask:
> "Want to work on something, or review the current plan?"
- "Work on something" → prompt for description → `sweetclaude:_route`
- "Review the plan" → "Roadmap · Backlog · Open work · Bugs — which?"
