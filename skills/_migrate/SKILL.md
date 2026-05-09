---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "One-time migration from phase.yaml/skills.yaml to sweetclaude.yaml."
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
INSTALLED=$(python3 -c "
import json
try:
    d = json.load(open('$HOME/.claude/plugins/installed_plugins.json'))
    e = [v for k,v in d.get('plugins',{}).items() if 'sweetclaude' in k.lower()]
    print(e[0][0].get('version','unknown') if e and e[0] else 'unknown')
except: print('unknown')
" 2>/dev/null)

SCRIPT=$(find ~/.claude -name "migrate-to-sweetclaude-yaml.py" 2>/dev/null | head -1)
if [ -z "$SCRIPT" ]; then
  echo "Migration script not found. Please run sweetclaude:update to ensure the latest framework version is installed, then try again."
  exit 1
fi

python3 "$SCRIPT" --project-dir . --installed-version "$INSTALLED"
```

If the script exits with error, report:
> "Migration failed. Your original files are untouched. Run `/sweetclaude` again to retry, or run `/sweetclaude:fix-sweetclaude` to debug."

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
