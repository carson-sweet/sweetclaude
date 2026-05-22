---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Project health dashboard — roadmap, backlog, mode, versions, config. For session continuity use /recap; for the full delivery tree use /big-picture."
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

Session state is pre-loaded above. Use `version_stage`, `improvement_register_count`, and `paths.product_base` from there directly.

Run all of these inline — do NOT spawn a background agent:

```bash
# Working tree (uncommitted count only — detailed git context is recap's job)
git status --short

# Migration guard — check that product dir exists before reading data
if [[ -d .sweetclaude/product/ ]]; then
  echo "PRODUCT_DIR_OK"
else
  echo "PRODUCT_DIR_MISSING"
  echo "This project has not been migrated. Run sweetclaude:migrate to migrate your product files."
fi

# RAG state (lightweight — existence check only)
ls .rag-index/lancedb/ 2>/dev/null | wc -l
find corpus/canonical/ -type f 2>/dev/null | wc -l

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

### Alerts

For each of the following, emit a `-` list item if the condition is true. If none are true, emit `Nothing flagged.`

- UNCOMMITTED_COUNT > 0: `- {N} uncommitted file(s) in working tree`
- MODE=kanban AND WIP_LIMIT is not null AND len(IN_PROGRESS_ITEMS) >= WIP_LIMIT: `- WIP limit reached: {N}/{WIP_LIMIT} items in progress`
- MODE=agile AND HAS_ACTIVE_SPRINT=false: `- No active sprint`
- `KNOWN_CONFLICTS` > 0: `- Config conflicts: {N} known — run /sweetclaude:claude-config-audit`

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

If `improvement_register_count` in pre-loaded state is > 0, output:
> I absorbed {N} new learnings from previous sessions. Feel free to ask about them if you want.

Then always output:
> For session continuity (checkpoint, recent commits), run `/sweetclaude:recap`. For the full delivery tree, run `/sweetclaude:big-picture`.

Output nothing after this. No framework health, no version notes, no skill warnings.
