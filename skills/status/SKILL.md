---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Orient to the current project."
---

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

# Roadmap (milestones) — path from pre-loaded session state
product_base=$(cat .sweetclaude/state/session-state.yaml 2>/dev/null | python3 -c "import yaml,sys; d=yaml.safe_load(sys.stdin); print(d.get('paths',{}).get('product_base','.sweetclaude/product'))" 2>/dev/null || echo "MANIFEST_MISSING")
if [ "$product_base" != "MANIFEST_MISSING" ]; then
  ls ${product_base}/milestones/MS-*.md 2>/dev/null | head -10
  grep -rh "\*\*Status:\*\*" ${product_base}/milestones/ 2>/dev/null | head -10
else
  echo "ARTIFACT_PRIVACY_NOT_CONFIGURED"
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

# Roadmap, issues, and backlog details
product_base=$(cat .sweetclaude/state/session-state.yaml 2>/dev/null | python3 -c "import yaml,sys; d=yaml.safe_load(sys.stdin); print(d.get('paths',{}).get('product_base','.sweetclaude/product'))" 2>/dev/null || echo ".sweetclaude/product")

python3 - <<'PYEOF'
import os, re, glob, json

base = os.environ.get('product_base', '.sweetclaude/product')

def field(content, name):
    m = re.search(rf'\*\*{name}:\*\*\s*(.+)', content)
    return m.group(1).strip() if m else ''

def title(content):
    m = re.search(r'^# (.+)', content, re.MULTILINE)
    return m.group(1).strip() if m else ''

DONE = {'done', 'complete', 'achieved', 'closed', 'complete'}

# --- Roadmap ---
roadmap = []
for f in sorted(glob.glob(f'{base}/roadmap/RM-*.md')):
    c = open(f).read()
    roadmap.append({'id': os.path.basename(f).split('.')[0], 'title': title(c),
                    'status': field(c, 'Status').lower(), 'type': field(c, 'Type')})
print('ROADMAP_START')
print(json.dumps(roadmap))
print('ROADMAP_END')

# --- Issues ---
issues = []
for f in sorted(glob.glob(f'{base}/issues/I-*.md')):
    c = open(f).read()
    s = field(c, 'Status').lower()
    issues.append({'id': os.path.basename(f).split('.')[0], 'title': title(c),
                   'status': s, 'roadmap': field(c, 'Roadmap Item'), 'epic': field(c, 'Epic'),
                   'priority': field(c, 'Priority'), 'open': s not in DONE})
print('ISSUES_START')
print(json.dumps(issues))
print('ISSUES_END')

# --- Backlog ---
backlog = []
_HORIZON_ORDER = {'now': 0, 'next': 1, 'sooner': 2, 'soon': 3, 'later': 4, 'someday': 5}
_DONE_STATUSES = {'done', 'complete', 'achieved', 'closed', 'cancelled', 'canceled'}

def _item_title(c):
    # YAML frontmatter title: takes precedence over H1
    fm = re.match(r'^---\s*\n(.*?)\n---', c, re.DOTALL)
    if fm:
        tm = re.search(r'^title:\s*(.+)', fm.group(1), re.MULTILINE)
        if tm:
            return tm.group(1).strip().strip('"\'')
    return title(c)

# v4: typed subdirs — priority field serves as horizon
_V4_SUBDIRS = [('stories', 'STORY'), ('bugs', 'BUG'), ('debt', 'DEBT'), ('chores', 'CHORE')]
for _subdir, _prefix in _V4_SUBDIRS:
    for f in sorted(glob.glob(f'{base}/backlog/{_subdir}/{_prefix}-*.md')):
        c = open(f).read()
        s = (field(c, 'status') or field(c, 'Status')).lower()
        if s in _DONE_STATUSES:
            continue
        h_raw = (field(c, 'priority') or field(c, 'Priority') or '').lower()
        h = h_raw if h_raw in _HORIZON_ORDER else 'unscheduled'
        m = re.match(rf'({_prefix}-\d+)', os.path.basename(f))
        item_id = m.group(1) if m else os.path.basename(f).split('.')[0]
        backlog.append({'id': item_id, 'title': _item_title(c), 'priority': h_raw.upper(),
                        'status': s, 'horizon': h, 'horizon_order': _HORIZON_ORDER.get(h, 6)})

# v3 backwards compat: BL-*.md in backlog/
for f in sorted(glob.glob(f'{base}/backlog/BL-*.md')):
    c = open(f).read()
    s = field(c, 'Status').lower()
    p = field(c, 'Priority').upper()
    h_raw = field(c, 'Horizon').lower()
    h = h_raw if h_raw in _HORIZON_ORDER else 'unscheduled'
    if 'DONE' not in s.upper() and 'COMPLETE' not in s.upper():
        backlog.append({'id': os.path.basename(f).split('.')[0],
                        'title': title(c), 'priority': p, 'status': s,
                        'horizon': h, 'horizon_order': _HORIZON_ORDER.get(h, 6)})
print('BACKLOG_START')
print(json.dumps(backlog))
print('BACKLOG_END')
PYEOF
```

## Step 3: Present status

Parse the JSON blocks from Step 2 output (between `*_START` / `*_END` markers). Use all data gathered. No further reads or commands.

Compute derived values:
- **UNCOMMITTED_COUNT** = number of lines in `git status --short` output
- **OPEN_ISSUES** = issues where `open: true`
- **IN_PROGRESS_ISSUES** = open issues where status = `in_progress`
- **ROADMAP_ACHIEVED** = roadmap items where status ∈ {complete, achieved}
- **ROADMAP_ACTIVE** = roadmap items where status ∈ {in_progress, active}
- **ROADMAP_PLANNED** = all others (not achieved/complete)
- **BACKLOG_BY_HORIZON** = backlog items grouped by horizon: next, sooner, soon, later, someday, unscheduled (items where `horizon` field is absent or unrecognized)

Output in this format. Use clean markdown — no box-drawing characters, no ANSI codes.

## {project name} · {version_stage}

### Unfinished Work

For each of the following, emit a `-` list item if the condition is true. If none are true, emit `Nothing open.`

- UNCOMMITTED_COUNT > 0: `- {N} uncommitted file(s) in working tree`
- checkpoint_next is set (non-null, non-empty): `- Checkpoint: {checkpoint_next}`
- scratch files found: `- Scratch: {filenames}`
- IN_PROGRESS_ISSUES non-empty: `- {N} issue(s) in progress: {comma-separated IDs}`
- MODE=kanban AND WIP_LIMIT is not null AND len(IN_PROGRESS_ISSUES) >= WIP_LIMIT: `- ⚠ WIP limit reached: {N}/{WIP_LIMIT} items in progress`
- MODE=agile AND HAS_ACTIVE_SPRINT=false: `- ⚠ No active sprint`

Then:

### Roadmap


If no roadmap files exist:
```
No roadmap configured. Ask me to build one with `/sweetclaude:product-roadmap`.
```

Otherwise: `{total} items · {ROADMAP_ACHIEVED} achieved · {ROADMAP_ACTIVE} active · {ROADMAP_PLANNED} planned`

Then, if ROADMAP_ACTIVE > 0, list active items one per line:

`**Active:** {id} — {title}`

Else if ROADMAP_PLANNED > 0, list up to 3 planned items one per line:

`**Up next:** {id} — {title}`

Then:

### Epics

Group OPEN_ISSUES by their `roadmap` field. For each active or planned roadmap item that has open issues, show:

**{roadmap-id} — {roadmap title}**
- {issue-id}: {title} [{status}]

After linked issues, if any open issues have `roadmap` = "(none)" or empty:

**Unlinked**
- {issue-id}: {title} [{status}]

If no open issues at all: `No open epics.`

Then:

### Backlog

For each horizon bucket that is non-empty, in order: next, sooner, soon, later, someday, unscheduled. Use `horizon_order` from the JSON to determine sort order (next=1 sorts first, unscheduled=6 sorts last).

Output the bucket heading as bold markdown followed by the item count:
`**{Bucket_Label}** ({N}{suffix})`

Where `{Bucket_Label}` is the bucket name in title case (e.g. `Next`, `Sooner`, `Unscheduled`), and `{suffix}` is ` — no horizon set` for the unscheduled bucket and empty string for all others.

Under each heading, show up to 5 items:
`- {id}  [{priority_badge}]  {title}`

Where `{priority_badge}` is the item's **Priority:** value (e.g. `P1`, `SPIKE`) or `—` if unset.

After all buckets: if total open backlog > 10, append:
`({total} total — run a backlog triage if it's getting unwieldy)`

If backlog is empty: `Backlog is clear.`

## Step 4: Closing

If `KNOWN_CONFLICTS` from Step 2 is > 0, output:
> Config conflicts: {N} known — run `/sweetclaude:claude-config-audit` to review or resolve.

If `improvement_register_count` in pre-loaded state is > 0, output:
> I absorbed {N} new learnings from previous sessions. Feel free to ask about them if you want.

Then always output:
> Anything you want to look at more closely, or is there something above you'd like to work on — or something else entirely?

Output nothing after this. No framework health, no version notes, no skill warnings.
