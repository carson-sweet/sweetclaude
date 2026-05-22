---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Orient to the current project."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:status" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: if pre-loaded state above shows STATE_NOT_FOUND, or neither .sweetclaude/state/sweetclaude.yaml nor .sweetclaude/state/phase.yaml exists, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Status

Show where the project stands. Reads state files directly — no background agent.

## Step 1: Schema check

Use `phase_schema_version` from pre-loaded session state above:
- If absent or `1`: warn — "Your `phase.yaml` is on schema v1. Run `/sweetclaude:update` to upgrade." Stop.
- If `2`: proceed.

## Step 2: Read state directly

Session state is pre-loaded above. Use `active_work_item`, `version_stage`, `deference`, `active_milestone`, `improvement_register_count`, `checkpoint_next`, and `paths.product_base` from there directly.

Run all of these inline — do NOT spawn a background agent:

```bash
# Git context
git log --oneline -5
git status --short

# Checkpoint (last session handoff)
tail -25 .sweetclaude/state/checkpoint.md 2>/dev/null || echo "NO_CHECKPOINT"

# Scratch directory (continuation files)
ls scratch/ 2>/dev/null | grep -iE "checkpoint|continue|resume|handoff" | head -5

# RAG state (lightweight — existence check only)
ls .rag-index/lancedb/ 2>/dev/null | wc -l
find corpus/canonical/ -type f 2>/dev/null | wc -l

# Migration guard — check that product dir exists before reading data
if [[ -d .sweetclaude/product/ ]]; then
  echo "PRODUCT_DIR_OK"
else
  echo "PRODUCT_DIR_MISSING"
  echo "This project has not been migrated. Run sweetclaude:migrate to migrate your product files."
fi

# Versions
python3 -c "import json; d=json.load(open('$HOME/.claude/plugins/installed_plugins.json')); e=[v[0] for k,v in d.get('plugins',{}).items() if 'sweetclaude' in k.lower() and v]; print(e[0].get('version','?') if e else '?')" 2>/dev/null
python3 -c "import json; print(json.load(open('$HOME/dev/sweetclaude/package.json')).get('version','?'))" 2>/dev/null

# Mode and WIP state
cat .sweetclaude/state/effective-gates.yaml 2>/dev/null | python3 -c "
import yaml,sys
d=yaml.safe_load(sys.stdin) or {}
print('MODE=' + d.get('mode','unset'))
print('WIP_LIMIT=' + str(d.get('wip_limit','null')))
print('TDD_DEFAULT=' + str(d.get('default_tdd_level','1')))
" 2>/dev/null || echo -e "MODE=unset\nWIP_LIMIT=null\nTDD_DEFAULT=1"

# Active sprint check (agile drift warning)
python3 -c "
import glob, yaml, os
d = '.sweetclaude/artifacts/sprints'
if not os.path.exists(d):
    print('HAS_ACTIVE_SPRINT=false')
else:
    has = any((yaml.safe_load(open(f)) or {}).get('status') == 'active' for f in glob.glob(os.path.join(d, '*.yaml')))
    print('HAS_ACTIVE_SPRINT=' + ('true' if has else 'false'))
" 2>/dev/null || echo "HAS_ACTIVE_SPRINT=false"

# Known config conflicts
python3 -c "
import re, os
path = '.sweetclaude/state/known-conflicts.md'
if os.path.exists(path):
    content = open(path).read()
    count = len(re.findall(r'^## Known Conflict', content, re.MULTILINE))
    print(f'KNOWN_CONFLICTS={count}')
else:
    print('KNOWN_CONFLICTS=0')
" 2>/dev/null || echo "KNOWN_CONFLICTS=0"

# Last doctor checkup
python3 -c "
import json, os
from datetime import datetime, timezone
path = '.sweetclaude/state/last-doctor-run.json'
if not os.path.exists(path):
    print('DOCTOR_CHECKUP=none')
else:
    try:
        d = json.load(open(path))
        ts = d.get('timestamp', '')
        summary = d.get('summary', {})
        errors = summary.get('errors', 0)
        warnings = summary.get('warnings', 0)
        t = datetime.fromisoformat(ts.replace('Z','+00:00'))
        delta = datetime.now(timezone.utc) - t
        days = delta.days
        if days == 0:
            age = 'today'
        elif days == 1:
            age = 'yesterday'
        else:
            age = f'{days} days ago'
        if errors == 0 and warnings == 0:
            print(f'DOCTOR_CHECKUP={age} — all clear')
        else:
            parts = []
            if errors: parts.append(f'{errors} error{\"s\" if errors != 1 else \"\"}')
            if warnings: parts.append(f'{warnings} warning{\"s\" if warnings != 1 else \"\"}')
            print(f'DOCTOR_CHECKUP={age} — {\", \".join(parts)}')
    except Exception:
        print('DOCTOR_CHECKUP=unknown')
" 2>/dev/null || echo "DOCTOR_CHECKUP=none"

# Rebuild cache and query for roadmap/backlog data using cache.py
python3 scripts/cache.py --project-dir . --rebuild 2>/dev/null
echo "SUMMARY_START"
python3 scripts/cache.py --project-dir . --query summary 2>/dev/null
echo "SUMMARY_END"
echo "BACKLOG_START"
python3 scripts/cache.py --project-dir . --query backlog 2>/dev/null
echo "BACKLOG_END"
```

## Step 3: Present status

If Step 2 output contains `PRODUCT_DIR_MISSING`, output:
> `.sweetclaude/product/` directory not found — this project has not been migrated. Run `/sweetclaude:migrate` to migrate your product files before running status.

Stop.

Otherwise, parse the JSON blocks from Step 2 output (between `*_START` / `*_END` markers). Use all data gathered. No further reads or commands.

Compute derived values:
- **UNCOMMITTED_COUNT** = number of lines in `git status --short` output
- **ROADMAP_ACHIEVED** = `summary.milestones.by_status.done` (milestones where status = 'done')
- **ROADMAP_ACTIVE** = `summary.milestones.by_status.active` (milestones where status = 'active')
- **ROADMAP_PLANNED** = `summary.milestones.total` - ROADMAP_ACHIEVED - ROADMAP_ACTIVE
- **OPEN_ITEMS** = backlog items from the backlog query (all are open — done/abandoned/deferred are excluded by cache.py)
- **IN_PROGRESS_ITEMS** = backlog items where status = `in_progress`
- **BACKLOG_BY_HORIZON** = backlog items grouped by horizon bucket, derived from priority field:
  - P0 or 'now' → Now
  - P1 or 'sooner' → Sooner
  - P2 or 'soon' → Soon
  - P3 or 'later' → Later
  - 'someday' → Someday
  - anything else → Unscheduled

Output in this format. Use clean markdown — no box-drawing characters, no ANSI codes.

## {project name} · {version_stage}

### Unfinished Work

For each of the following, emit a `-` list item if the condition is true. If none are true, emit `Nothing open.`

- UNCOMMITTED_COUNT > 0: `- {N} uncommitted file(s) in working tree`
- checkpoint_next is set (non-null, non-empty): `- Checkpoint: {checkpoint_next}`
- scratch files found: `- Scratch: {filenames}`
- IN_PROGRESS_ITEMS non-empty: `- {N} item(s) in progress: {comma-separated IDs}`
- MODE=kanban AND WIP_LIMIT is not null AND len(IN_PROGRESS_ITEMS) >= WIP_LIMIT: `- ⚠ WIP limit reached: {N}/{WIP_LIMIT} items in progress`
- MODE=agile AND HAS_ACTIVE_SPRINT=false: `- ⚠ No active sprint`

Then:

### Roadmap

If `summary.milestones.total` is 0:
```
No roadmap configured. Ask me to build one with `/sweetclaude:product-roadmap`.
```

Otherwise: `{total} milestones · {ROADMAP_ACHIEVED} done · {ROADMAP_ACTIVE} active · {ROADMAP_PLANNED} planned`

Then:

### Backlog

For each horizon bucket that is non-empty, in order: Now, Sooner, Soon, Later, Someday, Unscheduled.

Output the bucket heading as bold markdown followed by the item count:
`**{Bucket_Label}** ({N}{suffix})`

Where `{Bucket_Label}` is the bucket name in title case (e.g. `Now`, `Sooner`, `Unscheduled`), and `{suffix}` is ` — no horizon set` for the unscheduled bucket and empty string for all others.

Under each heading, show up to 5 items:
`- {id}  [{priority_badge}]  {title}`

Where `{priority_badge}` is the item's priority value (e.g. `P1`, `SPIKE`) or `—` if unset.

After all buckets: if total open backlog > 10, append:
`({total} total — run a backlog triage if it's getting unwieldy)`

If backlog is empty: `Backlog is clear.`

## Step 4: Closing

Parse `DOCTOR_CHECKUP` from Step 2:
- If `DOCTOR_CHECKUP=none`: output `Last checkup: No checkup on record.`
- Otherwise: output `Last checkup: {value}` (e.g., "Last checkup: 2 days ago — all clear" or "Last checkup: 5 days ago — 2 warnings")

If `KNOWN_CONFLICTS` from Step 2 is > 0, output:
> Config conflicts: {N} known — run `/sweetclaude:claude-config-audit` to review or resolve.

If `improvement_register_count` in pre-loaded state is > 0, output:
> I absorbed {N} new learnings from previous sessions. Feel free to ask about them if you want.

Then always output:
> Anything you want to look at more closely, or is there something above you'd like to work on — or something else entirely?

Output nothing after this. No framework health, no version notes, no skill warnings.
