# Unified Front Door Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 73-skill slash-command picker with `/sweetclaude` as the single natural-language entry point backed by a consolidated `sweetclaude.yaml` state file.

**Architecture:** A thin `/sweetclaude` orchestrator reads one YAML file and delegates to five focused internal sub-skills (`_migrate`, `_health`, `_offer`, `_route`, `setup`). A `session-preflight.sh` extension runs 24h checks at session start so the orchestrator reads cached results only. All previously visible skills except `/sweetclaude` and `/sweetclaude:help` become `user-invocable: false`.

**Tech Stack:** Bash (hooks), YAML (state), Claude Skill markdown (skills), Python 3 (YAML parsing in hooks), yq or python3-yaml (YAML writes in hook scripts)

**Design doc:** `docs/plans/design-unified-front-door-2026-05-03.md`

---

## File Map

### New files
| File | Purpose |
|------|---------|
| `skills/sweetclaude-root/SKILL.md` | `/sweetclaude` orchestrator — reads file, checks flags, delegates |
| `skills/_migrate/SKILL.md` | One-time migration from phase.yaml/skills.yaml → sweetclaude.yaml |
| `skills/_health/SKILL.md` | Consistency scan + version check (called by hook) |
| `skills/_offer/SKILL.md` | Feature offer loop — one offer per session |
| `skills/_route/SKILL.md` | NL classifier — maps user text to workflow skill |
| `skills/setup/SKILL.md` | Consolidated on+adopt — 3 branches: new/clean/messy |
| `hooks/sweetclaude-health-check.sh` | 24h check logic extracted to shell, called by session-preflight.sh |

### Modified files
| File | Change |
|------|--------|
| `hooks/session-preflight.sh` | Detect `sweetclaude.yaml` instead of `phase.yaml`; call health check script |
| `hooks/generate-session-state.sh` | Read from `sweetclaude.yaml` instead of `phase.yaml` |
| `skills/help/SKILL.md` | Rewrite as progressive onboarding chat |
| `skills/fix-sweetclaude/SKILL.md` | Add YAML parse failure handling |
| `skills/on/SKILL.md` | Add `user-invocable: false` |
| `skills/adopt/SKILL.md` | Add `user-invocable: false` |
| `skills/go/SKILL.md` | Add `user-invocable: false` |
| `skills/find-skill/SKILL.md` | Add `user-invocable: false` |
| `skills/next-steps/SKILL.md` | Add `user-invocable: false` |
| `skills/status/SKILL.md` | Add `user-invocable: false` |

### Naming convention prerequisite
The `/sweetclaude` root skill needs `name: sweetclaude` in its frontmatter. Before starting Task 8, verify this overrides path-based naming by testing with a throwaway skill. If it does not, the skill may need to live at `~/.claude/skills/sweetclaude.md` instead — check the update/install script for how namespace roots are handled.

---

## Task 0: Verify root skill naming

**Files:**
- Read: `skills/update/SKILL.md` (understand install mechanism)
- Read: `~/.claude/plugins/installed_plugins.json`

- [ ] **Step 1: Check how skills are installed**

```bash
cat ~/.claude/plugins/installed_plugins.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
for k, v in d.get('plugins', {}).items():
    if 'sweetclaude' in k.lower():
        print(k, v[0].get('version') if v else 'empty')
"
```

Expected: shows sweetclaude plugin entry with version path.

- [ ] **Step 2: Check installed skill directory structure**

```bash
ls ~/.claude/skills/sweetclaude/ | head -20
ls ~/.claude/skills/ | grep -v sweetclaude | head -10
```

Expected: `sweetclaude/` directory contains subdirs for each skill. Other skills like `init`, `review` are peer directories.

- [ ] **Step 3: Test if a SKILL.md at the namespace directory root is recognized**

```bash
# Check if a SKILL.md directly inside the sweetclaude/ dir already exists
ls ~/.claude/skills/sweetclaude/SKILL.md 2>/dev/null && echo "EXISTS" || echo "NOT_EXISTS"
```

- [ ] **Step 4: Check update.sh or equivalent install script**

```bash
cat ~/dev/sweetclaude/skills/update/SKILL.md | grep -A 20 "copy\|install\|sync\|cp " | head -30
```

- [ ] **Step 5: Document finding**

Based on steps above, record in a comment at the top of `skills/sweetclaude-root/SKILL.md`:
- If `name: sweetclaude` overrides path: proceed as planned, skill name in frontmatter
- If it does not: the install step for Task 8 must copy to `~/.claude/skills/sweetclaude/SKILL.md` directly

---

## Task 1: `sweetclaude.yaml` schema template

**Files:**
- Create: `scripts/sweetclaude-yaml-template.py` — generates a fresh `sweetclaude.yaml`
- Create: `tests/test-sweetclaude-yaml-template.sh`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/test-sweetclaude-yaml-template.sh << 'EOF'
#!/bin/bash
set -e
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

python3 scripts/sweetclaude-yaml-template.py \
  --name "test-project" \
  --type "existing-code" \
  --version-stage "BETA" \
  --output "$TMPDIR/sweetclaude.yaml"

# Verify file was written
[ -f "$TMPDIR/sweetclaude.yaml" ] || { echo "FAIL: file not written"; exit 1; }

# Verify it parses as valid YAML
python3 -c "
import yaml
with open('$TMPDIR/sweetclaude.yaml') as f:
    d = yaml.safe_load(f)
assert d['schema_version'] == 1, 'schema_version must be 1'
assert d['project']['name'] == 'test-project'
assert d['project']['type'] == 'existing-code'
assert d['framework']['setup_complete'] == False
assert d['framework']['migration_status'] == 'complete'
assert 'features' in d
assert 'work_history' in d
assert 'learnings' in d
for feat in ['product_milestones','product_backlog','product_personas','product_stories','document_corpus','usage_tracking','behavioral_regression']:
    assert feat in d['features'], f'missing feature: {feat}'
    assert d['features'][feat]['status'] == 'not_offered'
    assert d['features'][feat]['defer_until'] is None
print('PASS')
"
EOF
chmod +x tests/test-sweetclaude-yaml-template.sh
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
bash tests/test-sweetclaude-yaml-template.sh
```

Expected: error — `scripts/sweetclaude-yaml-template.py` does not exist.

- [ ] **Step 3: Write the template generator**

```python
#!/usr/bin/env python3
# scripts/sweetclaude-yaml-template.py
# Generates a fresh sweetclaude.yaml for new projects or migration target.
import argparse, yaml, sys
from datetime import datetime, timezone

def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def build_template(name, project_type, version_stage, installed_version='unknown',
                   migrated_from=None):
    feat = lambda: {'status': 'not_offered', 'offered_at': None,
                    'decided_at': None, 'defer_until': None}
    return {
        'schema_version': 1,
        'project': {
            'name': name,
            'type': project_type,
            'version_stage': version_stage,
            'safety_snapshot': '',
        },
        'framework': {
            'installed_version': installed_version,
            'setup_complete': False,
            'migrated_at': now_iso() if migrated_from else None,
            'migrated_from': migrated_from,
            'migration_status': 'complete',
            'hook_last_ran': None,
            'consistency': {
                'last_checked': None,
                'status': 'ok',
                'drift': [],
                'check_error': None,
            },
            'update': {
                'available': None,
                'last_checked': None,
                'declined': False,
                'check_error': None,
            },
        },
        'session': {
            'deference_level': 'collaborative',
            'default_action': None,
        },
        'work': {
            'last_item_id': None,
            'active': {
                'id': None, 'type': None, 'workflow': [],
                'phase': None, 'title': None,
                'started': None, 'entry_category': None,
            },
        },
        'features': {
            'product_milestones': feat(),
            'product_backlog':    feat(),
            'product_personas':   feat(),
            'product_stories':    feat(),
            'document_corpus':    feat(),
            'usage_tracking':     feat(),
            'behavioral_regression': feat(),
        },
        'health': {
            'last_checked': None,
            'artifacts': {
                'milestones': 'not_configured',
                'backlog':    'not_configured',
                'personas':   'not_configured',
                'stories':    'not_configured',
                'corpus':     'not_configured',
            },
        },
        'work_history': [],
        'learnings': [],
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--name', required=True)
    p.add_argument('--type', dest='project_type', default='existing-code')
    p.add_argument('--version-stage', default='IDEA')
    p.add_argument('--installed-version', default='unknown')
    p.add_argument('--migrated-from', default=None)
    p.add_argument('--output', default='-')
    args = p.parse_args()

    data = build_template(
        name=args.name,
        project_type=args.project_type,
        version_stage=args.version_stage,
        installed_version=args.installed_version,
        migrated_from=args.migrated_from,
    )

    content = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    if args.output == '-':
        print(content)
    else:
        with open(args.output, 'w') as f:
            f.write(content)

if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
bash tests/test-sweetclaude-yaml-template.sh
```

Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add scripts/sweetclaude-yaml-template.py tests/test-sweetclaude-yaml-template.sh
git commit -m "feat(schema): add sweetclaude.yaml template generator"
```

---

## Task 2: `sweetclaude:_migrate` sub-skill

**Files:**
- Create: `skills/_migrate/SKILL.md`
- Create: `tests/test-migrate.sh`

- [ ] **Step 1: Write the migration test**

```bash
cat > tests/test-migrate.sh << 'EOF'
#!/bin/bash
set -e
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Create mock old-schema state files
mkdir -p "$TMPDIR/.sweetclaude/state"

cat > "$TMPDIR/.sweetclaude/state/phase.yaml" << 'YAML'
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

cat > "$TMPDIR/.sweetclaude/state/skills.yaml" << 'YAML'
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
  --project-dir "$TMPDIR" \
  --installed-version "2.40.0"

# Verify output
python3 -c "
import yaml, os
sc = yaml.safe_load(open('$TMPDIR/.sweetclaude/state/sweetclaude.yaml'))
assert sc['schema_version'] == 1
assert sc['project']['version_stage'] == 'BETA'
assert sc['session']['deference_level'] == 'guided'
assert sc['project']['type'] == 'existing-code'
assert sc['framework']['migration_status'] == 'complete'
assert sc['framework']['migrated_from'] is not None
assert sc['features']['product_milestones']['status'] == 'active'
assert sc['features']['product_backlog']['status'] == 'active'
assert sc['features']['product_personas']['status'] == 'not_offered'
# Old files archived
assert os.path.exists('$TMPDIR/.sweetclaude/state/archive/phase.yaml.bak')
assert os.path.exists('$TMPDIR/.sweetclaude/state/archive/skills.yaml.bak')
print('PASS')
"
EOF
chmod +x tests/test-migrate.sh
```

- [ ] **Step 2: Run test to confirm failure**

```bash
bash tests/test-migrate.sh
```

Expected: error — `scripts/migrate-to-sweetclaude-yaml.py` does not exist.

- [ ] **Step 3: Write the migration script**

```python
#!/usr/bin/env python3
# scripts/migrate-to-sweetclaude-yaml.py
# One-time migration: phase.yaml + skills.yaml → sweetclaude.yaml
# Idempotent: safe to re-run (uses migration_status field).
import argparse, yaml, os, sys, shutil
from datetime import datetime, timezone
from pathlib import Path

def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# Map skills.yaml field names → sweetclaude.yaml feature keys
SKILL_KEY_MAP = {
    'product-milestones':    'product_milestones',
    'product-backlog':       'product_backlog',
    'product-user-personas': 'product_personas',
    'product-user-stories':  'product_stories',
    'document-corpus':       'document_corpus',
    'usage':                 'usage_tracking',
    'behavioral-regression': 'behavioral_regression',
    'product-sprint-plan':   None,  # no equivalent — skip
}

def blank_feature():
    return {'status': 'not_offered', 'offered_at': None,
            'decided_at': None, 'defer_until': None}

def migrate(project_dir, installed_version):
    state_dir = Path(project_dir) / '.sweetclaude' / 'state'
    sc_yaml   = state_dir / 'sweetclaude.yaml'
    phase_f   = state_dir / 'phase.yaml'
    skills_f  = state_dir / 'skills.yaml'
    ir_f      = state_dir / 'improvement-register.md'
    archive   = state_dir / 'archive'

    # Guard: already migrated and complete
    if sc_yaml.exists():
        existing = yaml.safe_load(sc_yaml.read_text()) or {}
        if existing.get('framework', {}).get('migration_status') == 'complete':
            print("Already migrated — nothing to do.")
            return

    # Step 1: write in_progress sentinel immediately
    sentinel = {'schema_version': 1,
                'framework': {'migration_status': 'in_progress'}}
    sc_yaml.write_text(yaml.dump(sentinel))

    # Step 2: read phase.yaml
    phase = yaml.safe_load(phase_f.read_text()) if phase_f.exists() else {}

    # Step 3: read skills.yaml
    skills_raw = yaml.safe_load(skills_f.read_text()) if skills_f.exists() else {}
    skills_raw.pop('schema_version', None)

    # Step 4: read improvement-register.md (extract bullet lines, max 15)
    learnings = []
    if ir_f.exists():
        for line in ir_f.read_text().splitlines():
            line = line.strip()
            if line.startswith('- ') and len(line) > 10:
                learnings.append(line[2:])
                if len(learnings) >= 15:
                    break

    # Step 5: build features map
    features = {}
    all_keys = ['product_milestones','product_backlog','product_personas',
                'product_stories','document_corpus','usage_tracking','behavioral_regression']
    for key in all_keys:
        features[key] = blank_feature()

    for old_key, new_key in SKILL_KEY_MAP.items():
        if new_key and old_key in skills_raw:
            entry = skills_raw[old_key]
            old_status = entry.get('status', 'uninitialized')
            if old_status == 'active':
                features[new_key] = {
                    'status': 'active',
                    'offered_at': entry.get('last_changed_at'),
                    'decided_at': entry.get('last_changed_at'),
                    'defer_until': None,
                }
            elif old_status == 'uninitialized':
                features[new_key] = blank_feature()

    # Step 6: active work item
    awi = phase.get('active_work_item', {}) or {}

    # Step 7: build complete sweetclaude.yaml
    data = {
        'schema_version': 1,
        'project': {
            'name': '',
            'type': phase.get('project_type', 'existing-code'),
            'version_stage': phase.get('version_stage', 'BETA'),
            'safety_snapshot': phase.get('safety_snapshot', ''),
        },
        'framework': {
            'installed_version': installed_version,
            'setup_complete': True,
            'migrated_at': now_iso(),
            'migrated_from': installed_version,
            'migration_status': 'complete',
            'hook_last_ran': None,
            'consistency': {
                'last_checked': None, 'status': 'ok',
                'drift': [], 'check_error': None,
            },
            'update': {
                'available': None, 'last_checked': None,
                'declined': False, 'check_error': None,
            },
        },
        'session': {
            'deference_level': phase.get('deference_level', 'collaborative'),
            'default_action': None,
        },
        'work': {
            'last_item_id': phase.get('last_work_item_id'),
            'active': {
                'id':             awi.get('id'),
                'type':           awi.get('type'),
                'workflow':       awi.get('workflow', []),
                'phase':          awi.get('phase'),
                'title':          awi.get('title'),
                'started':        awi.get('started'),
                'entry_category': awi.get('entry_category'),
            },
        },
        'features': features,
        'health': {
            'last_checked': None,
            'artifacts': {k: 'not_configured' for k in
                          ['milestones','backlog','personas','stories','corpus']},
        },
        'work_history': [],
        'learnings': learnings,
    }

    # Step 8: write final file
    sc_yaml.write_text(yaml.dump(data, default_flow_style=False,
                                 allow_unicode=True, sort_keys=False))

    # Step 9: archive old files
    archive.mkdir(exist_ok=True)
    date_suffix = datetime.now().strftime('%Y-%m-%d')
    for src, name in [(phase_f, f'phase.yaml.bak'),
                      (skills_f, f'skills.yaml.bak')]:
        if src.exists():
            shutil.copy2(src, archive / name)

    print(f"Migration complete. Old files archived to {archive}/")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--project-dir', required=True)
    p.add_argument('--installed-version', default='unknown')
    args = p.parse_args()
    migrate(args.project_dir, args.installed_version)

if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
bash tests/test-migrate.sh
```

Expected: `PASS`

- [ ] **Step 5: Write the `sweetclaude:_migrate` skill**

Create `skills/_migrate/SKILL.md` with this complete content:

```markdown
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:_migrate
user-invocable: false
description: One-time migration from phase.yaml/skills.yaml to sweetclaude.yaml. Also handles schema version upgrades. Idempotent — safe to re-run.
---

# SweetClaude Migration

Internal skill. Called by `/sweetclaude` when `sweetclaude.yaml` is missing or has `migration_status: in_progress/failed`.

## Arguments

- No args = old-schema migration (phase.yaml + skills.yaml → sweetclaude.yaml)
- `--schema-upgrade` = future schema version upgrade (v1 → v2+)

## Step 1: Detect migration type

Check `$ARGUMENTS`:
- Contains `--schema-upgrade` → run schema upgrade path (see Step 4)
- Empty → run old-schema migration (Step 2)

## Step 2: Old-schema migration

Run:

```bash
# Detect installed version
INSTALLED=$(python3 -c "
import json
try:
    d = json.load(open('$HOME/.claude/plugins/installed_plugins.json'))
    e = [v for k,v in d.get('plugins',{}).items() if 'sweetclaude' in k.lower()]
    print(e[0][0].get('version','unknown') if e and e[0] else 'unknown')
except: print('unknown')
" 2>/dev/null)

python3 $(find ~/.claude -name "migrate-to-sweetclaude-yaml.py" 2>/dev/null | head -1) \
  --project-dir . \
  --installed-version "$INSTALLED"
```

If the script is not found at the expected path, report:
> "Migration script not found. Please run `sweetclaude:update` to ensure the latest framework version is installed, then try again."

If the script exits with error, set `migration_status: failed` in `sweetclaude.yaml` (if partially written) and report:
> "Migration failed: [error]. Your original files are untouched. Run `/sweetclaude` again to retry, or run `/sweetclaude:fix-sweetclaude` to debug."

On success, report:
> "All set — migrated to unified state format. Your old files are archived in `.sweetclaude/state/archive/` in case you need them."

Then tell the caller to re-invoke `/sweetclaude` so the orchestrator continues with the freshly written file.

## Step 3: Verify migration result

After migration completes, run:

```bash
python3 -c "
import yaml
d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml'))
assert d.get('framework',{}).get('migration_status') == 'complete', 'migration_status not complete'
print('Migration verified OK')
"
```

If assertion fails, report the error and halt.

## Step 4: Schema upgrade path (--schema-upgrade)

Not yet implemented — reserved for v1 → v2+ schema changes. Report:
> "Schema upgrade path not yet needed — you are on schema v1, which is current."
```

- [ ] **Step 6: Commit**

```bash
git add scripts/migrate-to-sweetclaude-yaml.py tests/test-migrate.sh skills/_migrate/SKILL.md
git commit -m "feat(migrate): add sweetclaude.yaml migration script and _migrate skill"
```

---

## Task 3: Extend `session-preflight.sh` with 24h health checks

**Files:**
- Create: `hooks/sweetclaude-health-check.sh`
- Modify: `hooks/session-preflight.sh`
- Create: `tests/test-health-check.sh`

- [ ] **Step 1: Write the test**

```bash
cat > tests/test-health-check.sh << 'EOF'
#!/bin/bash
set -e
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT
mkdir -p "$TMPDIR/.sweetclaude/state"

# Write sweetclaude.yaml with stale timestamps (25 hours ago)
STALE=$(python3 -c "
from datetime import datetime, timezone, timedelta
print((datetime.now(timezone.utc) - timedelta(hours=25)).strftime('%Y-%m-%dT%H:%M:%SZ'))
")

python3 -c "
import yaml
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
open('$TMPDIR/.sweetclaude/state/sweetclaude.yaml','w').write(yaml.dump(d))
"

PROJECT_DIR="$TMPDIR" bash hooks/sweetclaude-health-check.sh

# Verify timestamps were updated
python3 -c "
import yaml
from datetime import datetime, timezone
d = yaml.safe_load(open('$TMPDIR/.sweetclaude/state/sweetclaude.yaml'))
cons_ts = d['framework']['consistency']['last_checked']
upd_ts  = d['framework']['update']['last_checked']
hook_ts = d['framework']['hook_last_ran']
assert cons_ts != '$STALE', f'consistency.last_checked not updated: {cons_ts}'
assert upd_ts  != '$STALE', f'update.last_checked not updated: {upd_ts}'
assert hook_ts is not None, 'hook_last_ran not written'
print('PASS')
"
EOF
chmod +x tests/test-health-check.sh
```

- [ ] **Step 2: Run test to confirm failure**

```bash
bash tests/test-health-check.sh
```

Expected: error — `hooks/sweetclaude-health-check.sh` does not exist.

- [ ] **Step 3: Write `hooks/sweetclaude-health-check.sh`**

```bash
cat > hooks/sweetclaude-health-check.sh << 'SCRIPT'
#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude 24h health check — consistency scan + version check.
# Called by session-preflight.sh. Reads/writes sweetclaude.yaml.
# PROJECT_DIR must be set in environment.

set -euo pipefail

SC_YAML="${PROJECT_DIR}/.sweetclaude/state/sweetclaude.yaml"

[ -f "$SC_YAML" ] || exit 0   # file not yet created — skip (first run handled by skill)

NOW_ISO=$(python3 -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))")

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

update_yaml() {
  local key="$1" val="$2"
  python3 - "$SC_YAML" "$key" "$val" << 'PY'
import sys, yaml
path, key, val = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f: d = yaml.safe_load(f) or {}
# Navigate dot-path key
parts = key.split('.')
node = d
for p in parts[:-1]:
    node = node.setdefault(p, {})
node[parts[-1]] = None if val == 'null' else val
with open(path, 'w') as f: yaml.dump(d, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
PY
}

# Always stamp hook_last_ran
update_yaml "framework.hook_last_ran" "$NOW_ISO"

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

  # Check hooks.json exists and key hooks are present
  HOOKS_JSON="${PROJECT_DIR}/.claude/hooks/sweetclaude/hooks.json"
  if [ ! -f "$HOOKS_JSON" ]; then
    DRIFT="hooks.json missing"
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

  if [ -n "$DRIFT" ]; then
    update_yaml "framework.consistency.status" "drift_detected"
    python3 - "$SC_YAML" "$DRIFT" << 'PY'
import sys, yaml
path, drift_str = sys.argv[1], sys.argv[2]
with open(path) as f: d = yaml.safe_load(f) or {}
d.setdefault('framework',{}).setdefault('consistency',{})['drift'] = drift_str.split()
d['framework']['consistency']['check_error'] = None
with open(path, 'w') as f: yaml.dump(d, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
PY
  else
    update_yaml "framework.consistency.status" "ok"
    update_yaml "framework.consistency.check_error" "null"
  fi
  update_yaml "framework.consistency.last_checked" "$NOW_ISO"
fi

# --- Version check (every 24h) ---
if [ "$(hours_since "$LAST_UPDATE")" -gt 24 ]; then
  # Get installed version from plugin registry
  INSTALLED=$(python3 -c "
import json
try:
    d = json.load(open('$HOME/.claude/plugins/installed_plugins.json'))
    e = [v for k,v in d.get('plugins',{}).items() if 'sweetclaude' in k.lower()]
    print(e[0][0].get('version','unknown') if e and e[0] else 'unknown')
except: print('unknown')
" 2>/dev/null)

  # Get latest from repo package.json (local check — no network call)
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
    update_yaml "framework.update.available" "null"
    update_yaml "framework.update.check_error" "null"
  fi
  update_yaml "framework.update.last_checked" "$NOW_ISO"
fi

exit 0
SCRIPT
chmod +x hooks/sweetclaude-health-check.sh
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
bash tests/test-health-check.sh
```

Expected: `PASS`

- [ ] **Step 5: Update `session-preflight.sh` to use `sweetclaude.yaml`**

Replace the detection block (currently checks for `phase.yaml`, line 48) with a block that checks for `sweetclaude.yaml` first, then falls back to `phase.yaml` for backwards compatibility during transition:

In `hooks/session-preflight.sh`, replace this block:
```bash
# Check if configured — .sweetclaude/ inside project
if [ -f "$PROJECT_DIR/.sweetclaude/state/phase.yaml" ]; then
```

With:
```bash
# Check if configured — prefer sweetclaude.yaml (new), fall back to phase.yaml (legacy)
SC_YAML="$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml"
PHASE_YAML="$PROJECT_DIR/.sweetclaude/state/phase.yaml"
if [ -f "$SC_YAML" ] || [ -f "$PHASE_YAML" ]; then
```

Also add the health check call inside the `if not disabled` block, after the `generate-session-state.sh` call:

```bash
# Run 24h health checks
PROJECT_DIR="$PROJECT_DIR" "$HOOK_DIR/sweetclaude-health-check.sh" 2>/dev/null || true
```

And update the state injection to prefer `sweetclaude.yaml`:
```bash
STATE_FILE="$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml"
# Fall back to session-state.yaml if sweetclaude.yaml not yet written
[ -f "$STATE_FILE" ] || STATE_FILE="$PROJECT_DIR/.sweetclaude/state/session-state.yaml"
```

- [ ] **Step 6: Commit**

```bash
git add hooks/sweetclaude-health-check.sh hooks/session-preflight.sh tests/test-health-check.sh
git commit -m "feat(hooks): add 24h health check script and update session-preflight for sweetclaude.yaml"
```

---

## Task 4: `sweetclaude:_offer` sub-skill

**Files:**
- Create: `skills/_offer/SKILL.md`

- [ ] **Step 1: Write `skills/_offer/SKILL.md`**

```markdown
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:_offer
user-invocable: false
description: Feature offer loop — surfaces one not_offered feature per session with human-language copy. Writes decision back to sweetclaude.yaml.
---

!`cat .sweetclaude/state/sweetclaude.yaml 2>/dev/null || echo "SC_YAML_NOT_FOUND"`

# Feature Offer

State is pre-loaded above. Read `features` map from it.

## Step 1: Find the first eligible feature

Check features in this order:
`product_milestones` → `product_backlog` → `product_personas` → `product_stories` → `document_corpus` → `usage_tracking` → `behavioral_regression`

For each feature, skip if:
- `status` is `active`, `declined`, or `offered`
- `status` is `deferred` AND `defer_until` is a future timestamp (compare to now)

The first feature where none of the skip conditions apply is the **candidate**.

If no candidate exists, return `NO_OFFER_NEEDED` to the caller — all features are handled.

## Step 2: Surface the offer

Use this copy table — exact wording, no schema field names in user output:

| Feature | Offer |
|---------|-------|
| `product_milestones` | "Want to set up some milestones? They give you a target to aim at and make it easy to see how far you've come." |
| `product_backlog` | "Want to start a backlog? It's the running list of everything you want to build — keeps ideas from falling through the cracks." |
| `product_personas` | "Want to define who your users are? Clear personas make every product decision easier — you'll refer back to them constantly." |
| `product_stories` | "Ready to write user stories? They turn your ideas into concrete, testable behavior — the input to writing code." |
| `document_corpus` | "Want to connect your docs to SweetClaude? I can search and reference them automatically so you don't have to re-explain context." |
| `usage_tracking` | "Want to turn on usage tracking? It helps surface what's working and what's slowing you down." |
| `behavioral_regression` | "Want to wire up behavioral regression testing? It checks that SweetClaude is still following the framework rules after model updates." |

Present the offer, then ask:
> "[Offer copy] (Yes / Not yet / No)"

## Step 3: Write the decision

**"Yes":**
```bash
python3 - .sweetclaude/state/sweetclaude.yaml << 'PY'
import sys, yaml
from datetime import datetime, timezone
path = sys.argv[1]
feature = 'FEATURE_KEY'   # replace with actual feature key
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
with open(path) as f: d = yaml.safe_load(f)
d['features'][feature].update({'status':'offered','offered_at':now,'decided_at':now})
with open(path,'w') as f: yaml.dump(d,f,default_flow_style=False,allow_unicode=True,sort_keys=False)
PY
```
Then invoke the appropriate setup skill:
- `product_milestones`    → `sweetclaude:product-milestones`
- `product_backlog`       → `sweetclaude:project-backlog`
- `product_personas`      → `sweetclaude:product-user-personas`
- `product_stories`       → `sweetclaude:product-user-stories`
- `document_corpus`       → `sweetclaude:document-corpus`
- `usage_tracking`        → `sweetclaude:usage`
- `behavioral_regression` → `sweetclaude:behavioral-regression`

**"Not yet":**
```bash
python3 - .sweetclaude/state/sweetclaude.yaml << 'PY'
import sys, yaml
from datetime import datetime, timezone, timedelta
path = sys.argv[1]
feature = 'FEATURE_KEY'
now = datetime.now(timezone.utc)
defer = (now + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
with open(path) as f: d = yaml.safe_load(f)
d['features'][feature].update({'status':'deferred','offered_at':now.strftime('%Y-%m-%dT%H:%M:%SZ'),'defer_until':defer})
with open(path,'w') as f: yaml.dump(d,f,default_flow_style=False,allow_unicode=True,sort_keys=False)
PY
```

**"No":**
```bash
python3 - .sweetclaude/state/sweetclaude.yaml << 'PY'
import sys, yaml
from datetime import datetime, timezone
path = sys.argv[1]
feature = 'FEATURE_KEY'
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
with open(path) as f: d = yaml.safe_load(f)
d['features'][feature].update({'status':'declined','offered_at':now,'decided_at':now})
with open(path,'w') as f: yaml.dump(d,f,default_flow_style=False,allow_unicode=True,sort_keys=False)
PY
```
```

- [ ] **Step 2: Verify frontmatter**

```bash
head -6 skills/_offer/SKILL.md | grep "user-invocable: false"
```

Expected: line found.

- [ ] **Step 3: Commit**

```bash
git add skills/_offer/SKILL.md
git commit -m "feat(skills): add sweetclaude:_offer feature offer sub-skill"
```

---

## Task 5: `sweetclaude:_route` sub-skill

**Files:**
- Create: `skills/_route/SKILL.md`

- [ ] **Step 1: Write `skills/_route/SKILL.md`**

```markdown
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:_route
user-invocable: false
description: Natural language classifier — maps user text to the right internal skill. Called by the /sweetclaude orchestrator when args are present.
---

# Route

Classify `$ARGUMENTS` and invoke the matched skill. Do not ask the user for clarification first — make a call, then confirm if the match is non-obvious.

## Explicit override (check first)

If `$ARGUMENTS` begins with `use ` followed by a known workflow name, bypass classification and route directly:

Known workflow names (case-insensitive):
`code-feature`, `code-issue`, `code-debt`, `code-review`, `code-testing`,
`something-broke`, `deploy-ship`, `design-architecture`, `design-tech-spec`,
`design-api-design`, `design-data-model`, `design-ux`, `design-wireframes`,
`design-user-flows`, `product-discovery`, `product-brief`, `product-prd`,
`product-user-personas`, `product-user-stories`, `product-milestones`,
`product-backlog`, `project-issues`, `project-sprints`, `testing-plan`,
`testing-security`, `testing-accessibility`, `john-wick`, `adopt`

Example: `use code-feature` → invoke `sweetclaude:code-feature`

## Classification table

If no explicit override, classify by dominant signal in `$ARGUMENTS`:

| Signal | Examples | Route to |
|--------|----------|---------|
| Incident / broken | "broke", "error", "crash", "down", "not working", "exception", "failing in prod" | `sweetclaude:something-broke` |
| Status / review | "where are we", "what's done", "show me status", "what's next", "what have we done" | Surface status from `sweetclaude.yaml` inline (no extra reads) — show project · version_stage · active work · last 3 history items |
| Help / explain | "how do I", "explain", "what is", "help me understand", "show me how" | `sweetclaude:help` |
| Build / feature | "build", "add", "implement", "create", "new feature", "I want to" | `sweetclaude:code-feature` |
| Bug / fix | "bug", "fix", "broken", "wrong", "regression", "not working as expected" | `sweetclaude:code-issue` |
| Refactor / debt | "refactor", "clean up", "restructure", "tech debt", "messy", "untangle" | `sweetclaude:code-debt` |
| Review | "review", "check my code", "look at this PR", "feedback on" | `sweetclaude:code-review` |
| Deploy / ship | "deploy", "ship", "release", "go live", "push to prod" | `sweetclaude:deploy-ship` |
| Design | "design", "architecture", "spec", "API", "schema", "data model", "wireframe" | `sweetclaude:design-architecture` (default) — refine to specific design skill based on context |
| Product | "product brief", "PRD", "personas", "user stories", "roadmap", "milestones" | `sweetclaude:find-skill` with `$ARGUMENTS` (product skills need more context) |
| Testing | "test", "QA", "accessibility", "security audit", "performance" | `sweetclaude:testing-plan` (default) |
| Default | anything else | `sweetclaude:find-skill` with `$ARGUMENTS` |

## Confirmation

For non-obvious matches (i.e., anything that doesn't have a strong single signal), confirm before invoking:
> "That sounds like [work type]. Starting [skill name description]? (Yes / tell me more)"

For strong single-signal matches (`build X`, `fix Y`, `deploy`, `something broke`), invoke directly without confirmation.

## After routing

Invoke the matched skill. Pass `$ARGUMENTS` as context. The matched skill handles its own flow from there.
```

- [ ] **Step 2: Verify frontmatter**

```bash
head -6 skills/_route/SKILL.md | grep "user-invocable: false"
```

Expected: line found.

- [ ] **Step 3: Commit**

```bash
git add skills/_route/SKILL.md
git commit -m "feat(skills): add sweetclaude:_route NL classifier sub-skill"
```

---

## Task 6: `sweetclaude:setup` sub-skill

**Files:**
- Create: `skills/setup/SKILL.md`
- Read first: `skills/on/SKILL.md`, `skills/adopt/SKILL.md` (absorb their logic)

- [ ] **Step 1: Read both skills being consolidated**

```bash
wc -l skills/on/SKILL.md skills/adopt/SKILL.md
```

Read both files fully to extract the key steps before writing the consolidated version.

- [ ] **Step 2: Write `skills/setup/SKILL.md`**

```markdown
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:setup
user-invocable: false
description: Consolidated setup skill — absorbs sweetclaude:on and sweetclaude:adopt. Detects project context and runs the appropriate onboarding branch. Called by /sweetclaude when setup_complete = false.
---

# SweetClaude Setup

Three branches. Detection is automatic.

## Step 0: Detect context

Run:
```bash
ls package.json pyproject.toml go.mod Cargo.toml Makefile 2>/dev/null | head -5
ls src/ lib/ app/ 2>/dev/null | head -5
git log --oneline -3 2>/dev/null || echo "NO_GIT_HISTORY"
find . -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" \
  2>/dev/null | grep -v node_modules | grep -v ".sweetclaude" | head -10
du -sh . 2>/dev/null | cut -f1
```

**Decision:**
- No code files, no git history → **Branch A: New Project**
- Code present, project feels organized (< 50 unstructured files, consistent naming) → **Branch B: Existing Codebase**
- Code present, signs of disorganization (mixed conventions, no clear structure, many TODO/FIXME, large untracked files) → **Branch C: Messy/Inherited**

Signs of Branch C: `grep -r "TODO\|FIXME\|HACK\|XXX" --include="*.py" --include="*.ts" --include="*.js" . 2>/dev/null | wc -l` > 20, or no consistent file naming, or zero tests.

## Branch A: New Project

> "Hi — I'm SweetClaude. I'll help you build this project with a structured workflow. Let me ask a couple of quick questions."

Ask one at a time:
1. "What's the project name?"
2. "What are you building? (one sentence)"

Then:
```bash
# Create directory structure
mkdir -p .sweetclaude/state .sweetclaude/product/milestones \
         .sweetclaude/product/backlog .sweetclaude/product/stories \
         .sweetclaude/state/archive

# Write sweetclaude.yaml
INSTALLED=$(python3 -c "
import json
try:
    d=json.load(open('$HOME/.claude/plugins/installed_plugins.json'))
    e=[v for k,v in d.get('plugins',{}).items() if 'sweetclaude' in k.lower()]
    print(e[0][0].get('version','unknown') if e and e[0] else 'unknown')
except: print('unknown')
" 2>/dev/null)

python3 $(find ~/.claude -name "sweetclaude-yaml-template.py" 2>/dev/null | head -1) \
  --name "[USER_PROVIDED_NAME]" \
  --type "new" \
  --version-stage "IDEA" \
  --installed-version "$INSTALLED" \
  --output .sweetclaude/state/sweetclaude.yaml
```

Set `setup_complete: true` in the written file:
```bash
python3 - .sweetclaude/state/sweetclaude.yaml << 'PY'
import sys, yaml
with open(sys.argv[1]) as f: d = yaml.safe_load(f)
d['framework']['setup_complete'] = True
d['project']['name'] = 'USER_PROVIDED_NAME'
with open(sys.argv[1],'w') as f: yaml.dump(d,f,default_flow_style=False,allow_unicode=True,sort_keys=False)
PY
```

Generate CLAUDE.md from project description (use the description the user provided):
> "Setting up your project... done. Here's where things stand: [show project name, version_stage: IDEA]. What do you want to work on first?"

## Branch B: Existing Codebase

> "Hi — I'm SweetClaude. I'll help bring some structure to this project. Let me take a quick look..."

```bash
# Scan for existing patterns
ls -la
cat README.md 2>/dev/null | head -20 || echo "No README"
cat package.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('name',''),d.get('description','')[:80])" 2>/dev/null || true
git log --oneline -10 2>/dev/null || echo "No git history"
```

Ask:
1. "What's the project name?" (pre-fill from package.json/README if found)
2. "What stage is this at? (Early prototype / Active development / Approaching launch / In production)"

Map stage answer to version_stage:
- Early prototype → IDEA
- Active development → ALPHA  
- Approaching launch → BETA
- In production → GA

Then run the same directory setup and `sweetclaude.yaml` write as Branch A, with `type: existing-code`.

> "All set. [Project name] is configured. Here's where things stand: [status summary]. What do you want to work on first?"

## Branch C: Messy/Inherited Codebase

> "This looks like an inherited or organically grown codebase. I'll run a full assessment before setting things up — this takes a few minutes but makes everything that follows much smoother."

Run the full ASSESS → DIAGNOSE → PLAN → SCAFFOLD flow from the original `sweetclaude:adopt` skill. Key phases:

**ASSESS:** Understand what exists — architecture, dependencies, test coverage, naming conventions, tech debt surface area.
**DIAGNOSE:** Identify the highest-impact problems. Prioritize by: broken builds > no tests > no structure > style issues.
**PLAN:** Propose a scaffolding plan. Show the user what will be created/changed before touching anything.
**SCAFFOLD:** With user approval, create `.sweetclaude/` structure, generate CLAUDE.md reflecting actual codebase patterns, write `sweetclaude.yaml`.

Then handoff: "SweetClaude is set up. Given what I found, here's what I'd suggest tackling first: [top recommendation from DIAGNOSE]."
```

- [ ] **Step 3: Verify**

```bash
head -6 skills/setup/SKILL.md | grep "user-invocable: false"
grep -c "## Branch" skills/setup/SKILL.md
```

Expected: `user-invocable: false` found; `3` branches.

- [ ] **Step 4: Commit**

```bash
git add skills/setup/SKILL.md
git commit -m "feat(skills): add sweetclaude:setup consolidated on+adopt sub-skill"
```

---

## Task 7: `sweetclaude:_health` sub-skill

**Files:**
- Create: `skills/_health/SKILL.md`

- [ ] **Step 1: Write `skills/_health/SKILL.md`**

```markdown
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:_health
user-invocable: false
description: Consistency scan and version check. Normally called by session-preflight.sh hook. Called inline by /sweetclaude when hook_last_ran is stale (> 2h).
---

# Health Check

Run the health check script inline. Called when `hook_last_ran` is stale — covers the case where the skill is invoked outside a normal session start.

## Step 1: Run the check

```bash
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
PROJECT_DIR="$PROJECT_DIR" ~/.claude/hooks/sweetclaude/sweetclaude-health-check.sh 2>/dev/null \
  && echo "HEALTH_CHECK_COMPLETE" \
  || echo "HEALTH_CHECK_FAILED"
```

If the script is not found at that path, check:
```bash
find ~/.claude -name "sweetclaude-health-check.sh" 2>/dev/null | head -1
```

If not found anywhere, report:
> "Health check script missing. Run `/sweetclaude:update` to reinstall."

## Step 2: Re-read sweetclaude.yaml

After the script runs, report the result to the caller (the orchestrator):
- Return `consistency.status` and `update.available` from the freshly-written file
- The orchestrator will act on these values
```

- [ ] **Step 2: Verify**

```bash
head -6 skills/_health/SKILL.md | grep "user-invocable: false"
```

- [ ] **Step 3: Commit**

```bash
git add skills/_health/SKILL.md
git commit -m "feat(skills): add sweetclaude:_health inline fallback sub-skill"
```

---

## Task 8: `/sweetclaude` orchestrator

**Files:**
- Create: `skills/sweetclaude-root/SKILL.md`

**Prerequisites:** Complete Task 0 (naming convention verification) before this task. The `name:` field in the frontmatter may need adjustment based on those findings.

- [ ] **Step 1: Write `skills/sweetclaude-root/SKILL.md`**

```markdown
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude
user-invocable: true
description: "Your SweetClaude entry point. Describe what you want to do in plain English, or press enter to see where things stand."
---

!`cat .sweetclaude/state/sweetclaude.yaml 2>/dev/null || echo "SC_YAML_NOT_FOUND"`

# SweetClaude

State pre-loaded above. One read. Make a decision. Delegate.

---

## Step 1: Handle missing or unparseable file

If the pre-loaded content is `SC_YAML_NOT_FOUND`:
- Check for old state files:
  ```bash
  ls .sweetclaude/state/phase.yaml .sweetclaude/state/skills.yaml 2>/dev/null | wc -l
  ```
  - If any found → invoke `sweetclaude:_migrate` then stop (migration will tell user to re-run)
  - If none found → invoke `sweetclaude:setup` then stop

If the pre-loaded content exists but fails YAML parsing (malformed):
> "Something in my config got scrambled. Let me fix it."
Invoke `sweetclaude:fix-sweetclaude`.
Stop.

## Step 2: Schema version check

Read `schema_version` from pre-loaded state.
If `schema_version` is not `1`:
- Invoke `sweetclaude:_migrate --schema-upgrade`
- Stop (migration will tell user to re-run)

## Step 3: Check migration status

Read `framework.migration_status`.
- `in_progress` or `failed` → invoke `sweetclaude:_migrate` (retry). Stop.
- `complete` → continue.

## Step 4: Stale hook check

Read `framework.hook_last_ran`.
If null or more than 2 hours ago (compare to now):
- Invoke `sweetclaude:_health` to run checks inline
- Re-read updated values from file before continuing

## Step 5: Check setup complete

Read `framework.setup_complete`.
If `false`:
- Invoke `sweetclaude:setup`. Stop.

## Step 6: Drift and update offers

Read `framework.consistency.status`.
If `drift_detected`:
```bash
cat .sweetclaude/state/sweetclaude.yaml | python3 -c "
import yaml,sys
d=yaml.safe_load(sys.stdin)
drift=d.get('framework',{}).get('consistency',{}).get('drift',[])
print(', '.join(drift) if drift else 'configuration drift detected')
"
```
> "I found some drift: [drift list]. Fix it now? (Yes / No)"
- Yes → `sweetclaude:fix-sweetclaude`. Stop.
- No → continue.

Read `framework.update.available` and `framework.update.declined`.
If `available` is not null AND `declined` is false:
> "SweetClaude [available version] is out. Update now? (Yes / Not now)"
- Yes → `sweetclaude:update`. Stop.
- Not now → write `declined: true` to file, continue.

## Step 7: Route on args

If `$ARGUMENTS` is present and non-empty:
→ invoke `sweetclaude:_route` with `$ARGUMENTS`
Stop.

## Step 8: Feature offer loop

Invoke `sweetclaude:_offer`.
If it returns `NO_OFFER_NEEDED`, continue to Step 9.
Otherwise `sweetclaude:_offer` handles the offer and response. Stop after one offer.

## Step 9: All-clear status surface

Read from pre-loaded state (no additional file reads):

```bash
python3 - << 'PY'
import yaml, sys

# Read from pre-loaded content (piped via the !` block above)
# In practice the shell command above already loaded the content — 
# parse it from the environment or re-read the file.
import os
sc_path = '.sweetclaude/state/sweetclaude.yaml'
with open(sc_path) as f:
    d = yaml.safe_load(f)

p = d.get('project', {})
w = d.get('work', {})
h = d.get('work_history', [])
da = d.get('session', {}).get('default_action')

name   = p.get('name') or 'this project'
stage  = p.get('version_stage', '')
active = w.get('active', {})
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

Show the output, then propose next action.

If `session.default_action` is set:
- `work` → prompt: "What do you want to work on?" and route via `sweetclaude:_route`
- `review` → ask: "Roadmap · Backlog · Open work · Bugs — which?" and route accordingly

If `default_action` is null:
> "Want to work on something, or review the current plan?"
- "Work on something" → prompt for description → `sweetclaude:_route`
- "Review the plan" → "Roadmap · Backlog · Open work · Bugs — which?"

Track answer. After 3 consecutive same answers, write `session.default_action` to file.
```

- [ ] **Step 2: Verify**

```bash
grep "name: sweetclaude$" skills/sweetclaude-root/SKILL.md
grep "user-invocable: true" skills/sweetclaude-root/SKILL.md
grep -c "## Step" skills/sweetclaude-root/SKILL.md
```

Expected: name and user-invocable found; 9 steps.

- [ ] **Step 3: Commit**

```bash
git add skills/sweetclaude-root/SKILL.md
git commit -m "feat(skills): add /sweetclaude unified orchestrator"
```

---

## Task 9: Rewrite `sweetclaude:help`

**Files:**
- Modify: `skills/help/SKILL.md`

- [ ] **Step 1: Read current help skill**

```bash
cat skills/help/SKILL.md
```

- [ ] **Step 2: Replace with progressive chat version**

Overwrite `skills/help/SKILL.md` with:

```markdown
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:help
user-invocable: true
description: Interactive help for SweetClaude. Explains free-language usage, walks through setup, shows available features, and explains project modes. Conversation flows from the user's question.
---

# SweetClaude Help

SweetClaude works through conversation. You don't need to know any commands.

## Step 1: Set the frame

Tell the user:

> "SweetClaude works through plain English — you describe what you want, and I figure out the right process. You don't need to know any skill names or commands.
>
> What would you like help with?"

Then offer these options (as a short menu or conversationally based on context):

1. **Set up SweetClaude** — for a new project or an existing codebase
2. **See what's available** — browse the features: product planning, coding workflows, design, testing, and more
3. **Understand project modes** — Flow, Kanban, Shape Up, Agile
4. **Learn how to use SweetClaude** — examples of what to type
5. **Something else** — ask freely

## Step 2: Follow the user's choice

**"Set up SweetClaude":**
> "Just type `/sweetclaude` and I'll walk you through it — I'll detect whether this is a new project or an existing codebase and ask a couple of questions."

**"See what's available":**
Present a plain-language feature tour (grouped by area, no skill names):

*Building things*
- Plan a new feature from scratch (discovery → stories → code → ship)
- Fix a bug end-to-end with a proper diagnosis
- Review code before merging
- Deploy and run a smoke test

*Product work*
- Write a product brief or PRD
- Define your users (personas)
- Prioritize your backlog (RICE scoring, roadmap)
- Plan a sprint

*Design*
- Define your architecture
- Design an API
- Create wireframes and user flows

*Testing*
- Plan your test strategy
- Run a security review (STRIDE / OWASP)
- Accessibility audit (WCAG 2.1)

*Day-to-day*
- See where things stand (`/sweetclaude` with no text)
- Prepare for a meeting
- Export a session

**"Understand project modes":**
Explain each mode in 2 sentences:
- **Flow** — unstructured creative work, minimal process overhead
- **Kanban** — visual board, continuous flow, limit WIP
- **Shape Up** — fixed time, variable scope, 6-week cycles with appetite-based bets
- **Agile** — sprints, ceremonies, velocity tracking

> "To switch modes, just tell me: 'Switch to Kanban mode' or 'I want to use Shape Up.'"

**"Learn how to use SweetClaude":**
Show examples of what to type:
```
/sweetclaude                          → see where things stand
/sweetclaude build a login page       → start a new feature
/sweetclaude fix the auth bug         → diagnose and fix a bug
/sweetclaude review my PR             → code review
/sweetclaude something broke in prod  → incident response
/sweetclaude use code-review          → explicit skill routing
```

**"Something else":**
Answer the user's question directly and offer to continue exploring.

## Step 3: Continue the conversation

After answering, ask:
> "Anything else you'd like to know, or ready to dive in?"

If they're ready: "Just type `/sweetclaude` and tell me what you want to build."

## Learnings visibility

If the user asks "what have you learned about me?" or "show my preferences":
```bash
python3 - << 'PY'
import yaml
try:
    d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml'))
    learnings = d.get('learnings', [])
    if learnings:
        print("Here's what I've learned from our sessions:\n")
        for i, l in enumerate(learnings, 1):
            print(f"{i}. {l}")
    else:
        print("No learnings recorded yet.")
except:
    print("Can't read learnings right now.")
PY
```

Offer: "Want to remove any of these? Just tell me which number."
If they specify one, remove it:
```bash
python3 - .sweetclaude/state/sweetclaude.yaml [INDEX] << 'PY'
import sys, yaml
path, idx = sys.argv[1], int(sys.argv[2]) - 1
with open(path) as f: d = yaml.safe_load(f)
learnings = d.get('learnings', [])
if 0 <= idx < len(learnings):
    removed = learnings.pop(idx)
    with open(path,'w') as f: yaml.dump(d,f,default_flow_style=False,allow_unicode=True,sort_keys=False)
    print(f"Removed: {removed}")
else:
    print("Index out of range.")
PY
```
```

- [ ] **Step 3: Verify**

```bash
grep "user-invocable: true" skills/help/SKILL.md
grep -c "## Step" skills/help/SKILL.md
```

- [ ] **Step 4: Commit**

```bash
git add skills/help/SKILL.md
git commit -m "feat(skills): rewrite sweetclaude:help as progressive onboarding chat"
```

---

## Task 10: Update `sweetclaude:fix-sweetclaude` for YAML parse failures

**Files:**
- Modify: `skills/fix-sweetclaude/SKILL.md`

- [ ] **Step 1: Read current skill**

```bash
head -40 skills/fix-sweetclaude/SKILL.md
```

- [ ] **Step 2: Add YAML parse failure handling at the top of the skill**

After the existing frontmatter and state injection line, add a new first section before any existing steps:

```markdown
## Step 0: Check for parse failure

If called because `sweetclaude.yaml` failed to parse (the `/sweetclaude` orchestrator routes here on parse error), run:

```bash
python3 -c "
import yaml
try:
    yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml'))
    print('YAML_OK')
except yaml.YAMLError as e:
    print(f'YAML_ERROR: {e}')
" 2>/dev/null
```

If `YAML_ERROR`:
> "Your `sweetclaude.yaml` has a syntax error. Here's what I see: [error message]
>
> Most common causes: a manual edit introduced bad indentation or special characters. Here's how to fix it in 30 seconds:"

Then run:
```bash
# Show the problematic area
python3 -c "
import yaml
try:
    yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml'))
except yaml.YAMLError as e:
    if hasattr(e, 'problem_mark'):
        m = e.problem_mark
        lines = open('.sweetclaude/state/sweetclaude.yaml').readlines()
        start = max(0, m.line - 2)
        end = min(len(lines), m.line + 3)
        for i, l in enumerate(lines[start:end], start+1):
            marker = ' <<<' if i == m.line+1 else ''
            print(f'{i:3}: {l.rstrip()}{marker}')
" 2>/dev/null
```

Options for the user:
1. "Fix it for me" → attempt auto-repair by re-running `sweetclaude:_migrate` (will rebuild from archived files if present)
2. "Show me the file" → `cat .sweetclaude/state/sweetclaude.yaml`
3. "Restore from archive" → `cp .sweetclaude/state/archive/phase.yaml.bak .sweetclaude/state/phase.yaml && sweetclaude:_migrate`
```

- [ ] **Step 3: Verify**

```bash
grep "Step 0" skills/fix-sweetclaude/SKILL.md
grep "YAML_ERROR" skills/fix-sweetclaude/SKILL.md
```

- [ ] **Step 4: Commit**

```bash
git add skills/fix-sweetclaude/SKILL.md
git commit -m "feat(skills): add YAML parse failure handling to fix-sweetclaude"
```

---

## Task 11: Retire old user-facing skills

**Files:**
- Modify: `skills/on/SKILL.md`, `skills/adopt/SKILL.md`, `skills/go/SKILL.md`, `skills/find-skill/SKILL.md`, `skills/next-steps/SKILL.md`, `skills/status/SKILL.md`

- [ ] **Step 1: Add `user-invocable: false` to each**

For each skill, the first few lines currently look like:
```yaml
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:X
description: "..."
---
```

Add `user-invocable: false` after the `name:` line in each. Run:

```bash
for skill in on adopt go find-skill next-steps status; do
  # Verify current state
  head -5 skills/$skill/SKILL.md
  echo "---"
done
```

Then edit each file to add the line. After editing, verify:

```bash
for skill in on adopt go find-skill next-steps status; do
  grep "user-invocable: false" skills/$skill/SKILL.md \
    && echo "$skill: OK" \
    || echo "$skill: MISSING"
done
```

Expected: all 6 show `OK`.

- [ ] **Step 2: Commit**

```bash
git add skills/on/SKILL.md skills/adopt/SKILL.md skills/go/SKILL.md \
        skills/find-skill/SKILL.md skills/next-steps/SKILL.md skills/status/SKILL.md
git commit -m "feat(skills): retire on, adopt, go, find-skill, next-steps, status from picker"
```

---

## Task 12: End-to-end migration test

**Files:**
- Create: `tests/test-e2e-migration.sh`

- [ ] **Step 1: Write the test**

```bash
cat > tests/test-e2e-migration.sh << 'EOF'
#!/bin/bash
set -e
echo "=== E2E Migration Test ==="
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT
mkdir -p "$TMPDIR/.sweetclaude/state" "$TMPDIR/.sweetclaude/product"

# Write realistic old-schema files
cat > "$TMPDIR/.sweetclaude/state/phase.yaml" << 'YAML'
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

cat > "$TMPDIR/.sweetclaude/state/skills.yaml" << 'YAML'
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

cat > "$TMPDIR/.sweetclaude/state/improvement-register.md" << 'MD'
- Always sync to installed after editing skills
- Push after every commit
- Don't re-ask questions already answered
MD

# Run migration
python3 scripts/migrate-to-sweetclaude-yaml.py \
  --project-dir "$TMPDIR" \
  --installed-version "2.40.0"

echo "Migration ran. Verifying output..."

python3 - "$TMPDIR" << 'PY'
import yaml, os, sys
base = sys.argv[1]
sc = yaml.safe_load(open(f'{base}/.sweetclaude/state/sweetclaude.yaml'))

# Schema
assert sc['schema_version'] == 1,           "schema_version"
assert sc['framework']['migration_status'] == 'complete', "migration_status"
assert sc['framework']['setup_complete'] == True,         "setup_complete"
assert sc['framework']['installed_version'] == '2.40.0',  "installed_version"

# Project fields from phase.yaml
assert sc['project']['version_stage'] == 'BETA',          "version_stage"
assert sc['session']['deference_level'] == 'collaborative',"deference_level"
assert sc['project']['type'] == 'existing-code',           "project_type"

# Features from skills.yaml
assert sc['features']['product_milestones']['status'] == 'active',    "milestones"
assert sc['features']['product_backlog']['status']    == 'active',    "backlog"
assert sc['features']['product_personas']['status']   == 'not_offered',"personas"
assert sc['features']['product_stories']['status']    == 'active',    "stories"
assert sc['features']['document_corpus']['status']    == 'not_offered',"corpus"

# Learnings from improvement-register.md
assert len(sc['learnings']) == 3,  f"learnings count: {len(sc['learnings'])}"
assert 'sync' in sc['learnings'][0].lower(), "learning 0 content"

# Archive created
assert os.path.exists(f'{base}/.sweetclaude/state/archive/phase.yaml.bak'),  "phase archive"
assert os.path.exists(f'{base}/.sweetclaude/state/archive/skills.yaml.bak'), "skills archive"

print("ALL ASSERTIONS PASS")
PY
EOF
chmod +x tests/test-e2e-migration.sh
```

- [ ] **Step 2: Run the test**

```bash
bash tests/test-e2e-migration.sh
```

Expected: `ALL ASSERTIONS PASS`

- [ ] **Step 3: Commit**

```bash
git add tests/test-e2e-migration.sh
git commit -m "test: add end-to-end migration test for sweetclaude.yaml"
```

---

## Task 13: Sync all changes to installed

- [ ] **Step 1: Copy new and modified skills to installed**

```bash
INSTALLED=~/.claude/skills/sweetclaude
REPO=~/dev/sweetclaude/skills

# New sub-skills
for skill in _migrate _health _offer _route setup sweetclaude-root; do
  mkdir -p "$INSTALLED/$skill"
  cp "$REPO/$skill/SKILL.md" "$INSTALLED/$skill/SKILL.md"
  echo "synced: $skill"
done

# Modified skills
for skill in help fix-sweetclaude on adopt go find-skill next-steps status; do
  cp "$REPO/$skill/SKILL.md" "$INSTALLED/$skill/SKILL.md"
  echo "synced: $skill"
done
```

- [ ] **Step 2: Copy hook scripts to installed hooks directory**

```bash
HOOK_DEST=~/.claude/hooks/sweetclaude
cp ~/dev/sweetclaude/hooks/sweetclaude-health-check.sh "$HOOK_DEST/"
cp ~/dev/sweetclaude/hooks/session-preflight.sh "$HOOK_DEST/"
chmod +x "$HOOK_DEST/sweetclaude-health-check.sh"
echo "hooks synced"
```

- [ ] **Step 3: Copy migration scripts to installed path**

```bash
# Scripts need to be findable by the skills — put them alongside hooks
cp ~/dev/sweetclaude/scripts/migrate-to-sweetclaude-yaml.py "$HOOK_DEST/"
cp ~/dev/sweetclaude/scripts/sweetclaude-yaml-template.py "$HOOK_DEST/"
echo "scripts synced"
```

- [ ] **Step 4: Verify installed versions match repo**

```bash
for skill in _migrate _health _offer _route setup sweetclaude-root help fix-sweetclaude; do
  diff "$REPO/$skill/SKILL.md" "$INSTALLED/$skill/SKILL.md" \
    && echo "$skill: in sync" \
    || echo "$skill: OUT OF SYNC"
done
```

Expected: all `in sync`.

- [ ] **Step 5: Verify `/sweetclaude` appears in skill list and retired skills do not**

Start a new Claude Code session and check the available skills list includes `sweetclaude` and does NOT include `sweetclaude:go`, `sweetclaude:on`, `sweetclaude:find-skill`, `sweetclaude:next-steps`, `sweetclaude:status`.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore(release): sync unified front door to installed — /sweetclaude v1"
```
