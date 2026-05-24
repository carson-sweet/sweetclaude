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

Multi-view project orientation. One command, dynamic views. No background agents.

Source spec: `docs/internal/specs/status-view-scopes.md` (v3.1, ISSUE-186/ISSUE-187)

## Step 1: Schema check

Use `phase_schema_version` from pre-loaded session state:
- If absent or `1`: warn — "Your config is on schema v1. Run `/sweetclaude:update` to upgrade." Stop.
- If `2`: proceed.

## Step 2: Migration guard

```bash
[[ -d .sweetclaude/product/ ]] && echo "PRODUCT_DIR_OK" || echo "PRODUCT_DIR_MISSING"
```

If `PRODUCT_DIR_MISSING`: output "`.sweetclaude/product/` not found — run `/sweetclaude:migrate` first." Stop.

## Step 3: Parse argument

The argument passed to this skill is: ``

If blank/empty → **no-arg mode**: continue to Step 4.
If non-empty → **arg mode**: skip to Step 5.

---

## Step 4: No-arg flow — rebuild, session view, menu

### Step 4a: Rebuild cache

```bash
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --rebuild 2>/dev/null
```

Save the JSON result (scanned/ingested/skipped) for use in views that check cache health. This is the single rebuild for the entire invocation — do not re-run.

### Step 4b: Gather session data

```bash
git log --oneline -3 2>/dev/null || echo "NO_GIT"
git status --short 2>/dev/null | wc -l | tr -d ' '
git branch --show-current 2>/dev/null || echo ""
tail -10 .sweetclaude/state/checkpoint.md 2>/dev/null || echo "NO_CHECKPOINT"

python3 -c "
import json, os
from datetime import datetime, timezone
path = '.sweetclaude/state/last-doctor-run.json'
if not os.path.exists(path):
    print('DOCTOR=none')
else:
    try:
        d = json.load(open(path))
        ts = d.get('timestamp','')
        s = d.get('summary',{})
        errors, warnings = s.get('errors',0), s.get('warnings',0)
        t = datetime.fromisoformat(ts.replace('Z','+00:00'))
        days = (datetime.now(timezone.utc) - t).days
        age = 'today' if days == 0 else ('yesterday' if days == 1 else f'{days} days ago')
        clean = errors == 0 and warnings == 0
        suffix = 'all clear' if clean else f'{errors}E/{warnings}W'
        print(f'DOCTOR={age} — {suffix}')
    except Exception:
        print('DOCTOR=unknown')
" 2>/dev/null || echo "DOCTOR=none"
```

### Step 4c: Render session view

**Auto-trigger: checkpoint.** If `checkpoint_next` in pre-loaded session state is set (non-null, non-empty), output ONLY this line and then proceed to Step 4d (do not render the full view):
```
Last session ended mid-task: {checkpoint_next}. Pick up here?
```

**Auto-trigger: detour conclusion.** After a detour of 5+ turns resolves, output only:
```
We were on {X} — {brief summary}. Ready to pick back up?
```
Then stop — do not render the full view or present the menu.

**Normal session view.** Output (5-7 lines max):

If `active_work_item.id` is non-null:
```
{id}  {title}  [{status} / {phase}]
  branch: {current-branch}  ({N} uncommitted)
  last: {hash}  {message}
        {hash}  {message}
  checkpoint: "{checkpoint_next}"
  deference: {deference}
```
- `id`, `title`, `status`, `phase` from `active_work_item` in pre-loaded state
- `current-branch` and uncommitted count from git output above
- `last` shows 2 most recent commits (abbreviated hash + message)
- `checkpoint` line: omit entirely if `checkpoint_next` is null/empty
- `deference` from pre-loaded session state

Notes line — append only when either condition is true:
- `improvement_register_count` > 0 in session state
- Doctor result is NOT "all clear"

```
  notes: {N} learnings from prior sessions · last checkup {doctor_age} ({result})
```

Omit the notes line entirely when improvement register is empty AND last checkup was all clear or doesn't exist.

If `active_work_item.id` is null, run:
```bash
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query summary 2>/dev/null
```
Then output:
```
No active work item.

Your project has {epics.total} epics and {total_items - epics.total - milestones.total} issues. Run /sweetclaude:go to pick one up.
```

### Step 4d: Detect available views

```bash
python3 -c "
import sys, os, glob, yaml, json, subprocess
sys.path.insert(0, os.path.expanduser('~/.claude/scripts/sweetclaude'))
from cache import get_conn

conn = get_conn('.')

# Epics (all, including done, for count)
epic_count = conn.execute('SELECT COUNT(*) as c FROM items WHERE type=\"epic\"').fetchone()['c']

# Milestones
ms_count = conn.execute('SELECT COUNT(*) as c FROM items WHERE type=\"milestone\"').fetchone()['c']

# Backlog (excludes done/abandoned/deferred)
bl_count = conn.execute(
    'SELECT COUNT(*) as c FROM items WHERE type NOT IN (\"epic\",\"milestone\") AND status NOT IN (\"done\",\"abandoned\",\"deferred\")'
).fetchone()['c']

# Dependencies — count items with non-empty depends_on (field lives in frontmatter, not cache)
import glob, yaml
dep_count = 0
for _f in (glob.glob('.sweetclaude/product/roadmap/issues/*.md') +
           glob.glob('.sweetclaude/product/roadmap/issues/done/*.md') +
           glob.glob('.sweetclaude/product/backlog/*.md')):
    try:
        _parts = open(_f).read().split('---', 2)
        if len(_parts) >= 3:
            _fm = yaml.safe_load(_parts[1]) or {}
            _deps = _fm.get('depends_on')
            if _deps and (_deps if isinstance(_deps, list) else [_deps]):
                dep_count += 1
    except Exception:
        pass

conn.close()

# Sprint
sprint_dir = '.sweetclaude/artifacts/sprints'
has_sprint = False
sprint_name = ''
if os.path.exists(sprint_dir):
    for f in glob.glob(os.path.join(sprint_dir, '*.yaml')):
        try:
            d = yaml.safe_load(open(f)) or {}
            if d.get('status') == 'active':
                has_sprint = True
                sprint_name = d.get('name', '')
                break
        except Exception:
            pass

print(f'EPIC_COUNT={epic_count}')
print(f'MS_COUNT={ms_count}')
print(f'BL_COUNT={bl_count}')
print(f'DEP_COUNT={dep_count}')
print(f'HAS_SPRINT={has_sprint}')
print(f'SPRINT_NAME={sprint_name}')
" 2>/dev/null
```

### Step 4e: Present drill-down menu

Build menu options — include a row **only if** the corresponding data exists:

| Condition | Label |
|-----------|-------|
| EPIC_COUNT > 0 | `Epic ({EPIC_COUNT} epics)` |
| MS_COUNT > 0 | `Release ({MS_COUNT} milestones)` |
| always | `Roadmap` |
| BL_COUNT > 0 | `Backlog ({BL_COUNT} items)` |
| DEP_COUNT > 0 | `Dependencies ({DEP_COUNT} items)` |
| HAS_SPRINT=True | `Sprint: "{SPRINT_NAME}"` |
| active_work_item.type is an issue type | `Current issue — {id}: {title}` |
| always | `Something else` |

Present via **AskUserQuestion** with question "Which view?" and the constructed option list.

After the user selects, proceed to the corresponding view step. The menu is one-shot — after a view renders, the user may ask for another view conversationally or re-run `/sweetclaude:status`.

---

## Step 5: Arg mode — direct routing

Rebuild cache first (same as Step 4a). Then parse ``:

| Pattern | Route |
|---------|-------|
| Matches `ISSUE-\d+` | Issue view → Step V-issue |
| Matches `EP-\d+` | Epic view for that ID → Step V-epic |
| Matches `MS-\d+` | Release view for that ID → Step V-release |
| `roadmap` (case-insensitive) | Roadmap view → Step V-roadmap |
| Starts with `backlog` | Backlog view → Step V-backlog; parse trailing filter (`P0`, `P1`, `P2`, `P3`, `--epic EP-NNN`) |
| `dependencies` | Dependencies view → Step V-deps |
| `sprint` | Sprint view → Step V-sprint |
| No match | Print: "`{arg}` not recognized. Valid: `roadmap`, `backlog [P0/P1/P2/P3]`, `backlog --epic EP-NNN`, `dependencies`, `sprint`, or an item ID." Then fall back to Step 4 (session view + menu). |

No session view, no menu in arg mode — go directly to the view.

---

## View steps

### Step V-roadmap: Roadmap view

**Consistency checks** — run before rendering, output warnings if found:

```bash
python3 -c "
import sys, os, glob, re, yaml
sys.path.insert(0, os.path.expanduser('~/.claude/scripts/sweetclaude'))
from cache import get_conn, query_next_id
warnings = []

# counter-drift
conn = get_conn('.')
cache_next = query_next_id('.', 'ISSUE')
cache_max = int(cache_next['next_id'].split('-')[1]) - 1
all_issue_files = (glob.glob('.sweetclaude/product/roadmap/issues/**/*.md', recursive=True) +
                   glob.glob('.sweetclaude/product/backlog/**/*.md', recursive=True))
disk_max = max((int(m.group(1)) for f in all_issue_files
                for m in [re.search(r'ISSUE-(\d+)', os.path.basename(f))] if m), default=0)
if disk_max > cache_max:
    warnings.append(f'counter-drift: disk max ISSUE-{disk_max:03d}, cache max ISSUE-{cache_max:03d} — run /sweetclaude:doctor')

# cross-location-dup
backlog_ids = {m.group(1) for f in (glob.glob('.sweetclaude/product/backlog/*.md') +
               glob.glob('.sweetclaude/product/backlog/**/*.md', recursive=True))
               for m in [re.search(r'((?:ISSUE|EP|MS)-\d+)', os.path.basename(f))] if m}
roadmap_ids = {m.group(1) for f in (glob.glob('.sweetclaude/product/roadmap/*.md') +
               glob.glob('.sweetclaude/product/roadmap/**/*.md', recursive=True))
               for m in [re.search(r'((?:ISSUE|EP|MS)-\d+)', os.path.basename(f))] if m}
dups = backlog_ids & roadmap_ids
if dups:
    warnings.append(f'cross-location-dup: {sorted(dups)} appear in both backlog/ and roadmap/')

conn.close()
for w in warnings:
    print(w)
" 2>/dev/null
```

If warnings were printed, prepend:
```
Warnings:
  - {warning}

---
```

**Data:**

```bash
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query milestones-compact 2>/dev/null
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query summary 2>/dev/null
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query backlog --unlinked-only 2>/dev/null
```

**Render** (milestones ordered by ID, with `↓` separator between consecutive milestones):

```
MS-NNN  {title}  [{status}]
├── EP-NNN  {title}  [{status}]  {criteria_done}/{criteria_total} criteria
│   ├── ISSUE-NNN  {title ≤50 chars}  [{status}]
│   ├── ISSUE-NNN  {title}  ✓
│   └── (+N more)
└── EP-NNN  {title}  ✓ done
↓
MS-NNN  {title}  [{status}]
...
```

Rules:
- If stored status ≠ derived_status: append `⚠ children suggest [{derived_status}]` after `[{status}]`
- Per epic: show up to 5 non-done issues, then `(+N done)` for collapsed done issues; `✓` marks done items
- Use `├──` / `└──` connectors; `│   ` for continuation lines; `↓` between milestones
- Epics with no children: show `(no issues)` inline

After the tree, summary line from `summary` query data:
```
{milestones.total} milestones · {epics.by_status.active or 0} epics active · {total_issues} issues
Unlinked: {unlinked.open} items not assigned to an epic
```

If rebuild from Step 4a/5 had `skipped` count > 0:
```
{scanned} scanned, {ingested} indexed, {skipped} skipped — run /sweetclaude:doctor for details
```

---

### Step V-epic: Epic view

**Determine which epic:**
- If a specific EP-NNN was given (arg mode): use that ID.
- If no ID (selected from menu): run `python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query epics 2>/dev/null`. If one non-done epic: use it. If multiple: present **AskUserQuestion** with epics as options (ID + title as label), plus "Something else".

**Data:**

```bash
# Full epic with all child issues
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query epic-issues --epic {epic_id} --include-done 2>/dev/null
# Epics list to get the epic's own record (title, objective, criteria, stored status)
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query epics --include-done 2>/dev/null
```

**Consistency checks:**

```bash
python3 -c "
import sys, os, re
sys.path.insert(0, os.path.expanduser('~/.claude/scripts/sweetclaude'))
from cache import get_conn
warnings = []
conn = get_conn('.')
EPIC_ID = '{epic_id}'

ep = conn.execute('SELECT * FROM items WHERE id=? AND type=\"epic\"', (EPIC_ID,)).fetchone()
if ep:
    stories = conn.execute('SELECT status FROM items WHERE epic=? AND type NOT IN (\"epic\",\"milestone\")', (EPIC_ID,)).fetchall()
    child_statuses = [s['status'] for s in stories]
    terminal = {'done','abandoned','deferred'}
    active_set = {'active','in-progress','in-review','blocked'}
    if not child_statuses:
        derived = 'new'
    elif all(s in terminal for s in child_statuses):
        derived = 'done'
    elif any(s in active_set for s in child_statuses):
        derived = 'active'
    else:
        derived = 'new'
    if ep['status'] != derived:
        warnings.append(f'derived-mismatch: {EPIC_ID} stored={ep[\"status\"]!r} but children suggest {derived!r}')

    criteria = conn.execute('SELECT done FROM completion_criteria WHERE epic_id=?', (EPIC_ID,)).fetchall()
    if criteria and child_statuses and all(s in terminal for s in child_statuses):
        if not any(c['done'] for c in criteria):
            warnings.append(f'criteria-agreement: all children terminal but no completion criteria marked done')

conn.close()
for w in warnings:
    print(w)
" 2>/dev/null
```

If warnings, prepend the `Warnings:` section. Then render:

```
EP-NNN  {title}  [{status}]  (derived: {derived} — {"matches" or "MISMATCH"})
  Objective: {objective, truncated to 120 chars}

  Criteria:  {done}/{total} complete
    [x] {criterion}
    [ ] {criterion}

  Issues:  {done_count}/{total_count} done
    ISSUE-NNN  {title ≤50 chars}   {status}  {"**" if this is the active work item}  {"⚠ " + blocked_reason if blocked}
    ISSUE-NNN  ...
    (+N done, not shown)

  Blockers:
    ISSUE-NNN — {blocked_reason}
```

Caps:
- Non-done issues: up to 20. If more: `(+M more — run /sweetclaude:status backlog --epic {epic_id})`
- Done issues collapsed to `(+N done, not shown)`
- Blockers: items with `status=blocked` and non-empty `blocked_reason` only. Omit "Blockers" section if none.

---

### Step V-release: Release view

**Determine which milestone:**
- Specific MS-NNN from arg: use that ID.
- From menu: run `python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query milestones-compact 2>/dev/null`. If one milestone: use it. If multiple: **AskUserQuestion** with milestone ID + title options.

**Consistency checks:**

```bash
python3 -c "
import sys, os, glob, yaml
sys.path.insert(0, os.path.expanduser('~/.claude/scripts/sweetclaude'))
from cache import get_conn
warnings = []
conn = get_conn('.')
MS_ID = '{ms_id}'

ms = conn.execute('SELECT * FROM items WHERE id=? AND type=\"milestone\"', (MS_ID,)).fetchone()
if ms:
    epics = conn.execute('SELECT id, status FROM items WHERE milestone=? AND type=\"epic\"', (MS_ID,)).fetchall()
    epic_statuses = [e['status'] for e in epics]
    terminal = {'done','abandoned'}
    active_set = {'active','in-progress','in-review','blocked'}
    if not epic_statuses:
        derived = 'new'
    elif all(s in terminal for s in epic_statuses):
        derived = 'done'
    elif any(s in active_set for s in epic_statuses):
        derived = 'active'
    else:
        derived = 'new'
    if ms['status'] != derived:
        warnings.append(f'derived-mismatch: {MS_ID} stored={ms[\"status\"]!r} but epics suggest {derived!r}')

# done-location (check all files, cap output at 5 warnings)
product_base = '.sweetclaude/product'
loc_warnings = []
for fpath in (glob.glob(f'{product_base}/roadmap/**/*.md', recursive=True) +
              glob.glob(f'{product_base}/backlog/**/*.md', recursive=True)):
    try:
        content = open(fpath).read()
        if not content.startswith('---'): continue
        parts = content.split('---', 2)
        if len(parts) < 3: continue
        fm = yaml.safe_load(parts[1]) or {}
        status = fm.get('status','')
        in_done = '/done/' in fpath
        fname = os.path.basename(fpath)
        if status in ('done','abandoned','deferred') and not in_done:
            loc_warnings.append(f'done-location: {fname} has status={status!r} but is not in done/')
        elif status not in ('done','abandoned','deferred','') and in_done:
            loc_warnings.append(f'done-location: {fname} is in done/ but has status={status!r}')
    except Exception:
        pass
warnings.extend(loc_warnings[:3])

conn.close()
for w in warnings[:5]:
    print(w)
" 2>/dev/null
```

If warnings, prepend the `Warnings:` section. Then render:

```
MS-NNN  {title}  [{status}]  target: {target_release or "—"}

  EP-NNN  {epic_title}                done  ({criteria_done}/{criteria_total})
  EP-NNN  {epic_title}    active ({criteria_done}/{criteria_total} criteria)  ** {N} blocked
  EP-NNN  {epic_title}       new  (0/{criteria_total})

  Blockers:
    ISSUE-NNN  {title}  (EP-NNN, {priority})

  Progress: {done_epics}/{total_epics} epics done · {done_issues}/{total_issues} issues done
```

Caps: all epics shown (no cap). Blockers: all blocked/on-hold items across epics, max 10. If more: `(+N more blockers)`.

---

### Step V-issue: Issue view

**Locate the file:**

```bash
python3 -c "
import sys, os, glob, yaml, json
issue_id = '{issue_id}'
product_base = '.sweetclaude/product'
found = None
for pattern in [
    f'{product_base}/roadmap/issues/{issue_id}-*.md',
    f'{product_base}/roadmap/issues/done/{issue_id}-*.md',
    f'{product_base}/backlog/{issue_id}-*.md',
    f'{product_base}/backlog/done/{issue_id}-*.md',
]:
    matches = glob.glob(pattern)
    if matches:
        found = matches[0]
        break
if not found:
    print('NOT_FOUND'); sys.exit()
content = open(found).read()
parts = content.split('---', 2)
if len(parts) < 3:
    print('PARSE_ERROR'); sys.exit()
fm = yaml.safe_load(parts[1]) or {}
print(json.dumps(fm, default=str))
" 2>/dev/null
```

If `NOT_FOUND`: output `{issue_id} not found. It may have been moved to done/ or archived.` Stop.

**Consistency checks** (against source frontmatter, not cache):

```bash
python3 -c "
import sys, os, glob, json
sys.path.insert(0, os.path.expanduser('~/.claude/scripts/sweetclaude'))
from schema import validate_frontmatter, normalize_status
from status import CANONICAL_STATUSES
import argparse

fm_str = open('/dev/stdin').read()  # fm JSON from above
try:
    fm = json.loads(fm_str)
except Exception:
    sys.exit()

warnings = []

violations = validate_frontmatter(fm)
if violations:
    warnings.extend(violations)

status_val = normalize_status(str(fm.get('status','')))
if status_val not in CANONICAL_STATUSES:
    warnings.append(f'status-canonical: {fm.get(\"status\")!r} is not a canonical status')

epic = fm.get('epic','')
if epic:
    product_base = '.sweetclaude/product'
    found = (glob.glob(f'{product_base}/roadmap/epics/{epic}-*.md') or
             glob.glob(f'{product_base}/roadmap/epics/done/{epic}-*.md'))
    if not found:
        warnings.append(f'epic-ref-resolves: epic {epic!r} not found on disk')

for w in warnings:
    print(w)
" 2>/dev/null
```

If warnings, prepend the `Warnings:` section. Then render:

```
ISSUE-NNN  {title}
  type: {type}  status: {status}  priority: {priority or "—"}
  epic: {epic_id} — {epic_title} [{epic_status}]
  branch: {branch}  phase: {phase}
  blocked_reason: {blocked_reason or "—"}
  depends_on: {ISSUE-NNN (status), ISSUE-NNN (status)}
```

Omit `branch`/`phase` line if both unset. Omit `depends_on` line if empty/absent. For `epic`, show `none` if unset. Resolve epic title and status from cache if epic is set.

---

### Step V-backlog: Backlog view

**Parse filter from the arg** (or from no filter if invoked from menu):
- `P0`, `P1`, `P2`, `P3` → priority filter
- `--epic EP-NNN` → epic filter
- nothing → no filter

**Consistency checks:**

```bash
python3 -c "
import sys, os, glob, re, yaml
sys.path.insert(0, os.path.expanduser('~/.claude/scripts/sweetclaude'))
from cache import get_conn, query_next_id
warnings = []
conn = get_conn('.')

# counter-drift
cache_next = query_next_id('.', 'ISSUE')
cache_max = int(cache_next['next_id'].split('-')[1]) - 1
all_files = (glob.glob('.sweetclaude/product/roadmap/issues/**/*.md', recursive=True) +
             glob.glob('.sweetclaude/product/backlog/**/*.md', recursive=True))
disk_max = max((int(m.group(1)) for f in all_files
                for m in [re.search(r'ISSUE-(\d+)', os.path.basename(f))] if m), default=0)
if disk_max > cache_max:
    warnings.append(f'counter-drift: disk max ISSUE-{disk_max:03d}, cache max ISSUE-{cache_max:03d}')

# done-location (backlog items only, cap at 3)
loc = []
for fpath in glob.glob('.sweetclaude/product/backlog/*.md'):
    try:
        parts = open(fpath).read().split('---', 2)
        if len(parts) < 3: continue
        import yaml
        fm = yaml.safe_load(parts[1]) or {}
        status = fm.get('status','')
        in_done = '/done/' in fpath
        if status in ('done','abandoned') and not in_done:
            loc.append(f'done-location: {os.path.basename(fpath)} has status={status!r} but not in done/')
    except Exception:
        pass
warnings.extend(loc[:3])

# epic-ref-resolves (first 5 violations only)
rows = conn.execute(
    'SELECT id, epic FROM items WHERE epic IS NOT NULL AND epic != \"\" AND type NOT IN (\"epic\",\"milestone\")'
).fetchall()
ref_warnings = []
for row in rows:
    if not conn.execute('SELECT id FROM items WHERE id=? AND type=\"epic\"', (row['epic'],)).fetchone():
        ref_warnings.append(f'epic-ref-resolves: {row[\"id\"]} references epic {row[\"epic\"]!r} which does not exist')
        if len(ref_warnings) >= 5: break
warnings.extend(ref_warnings)

conn.close()
for w in warnings[:5]:
    print(w)
" 2>/dev/null
```

**Fetch items:**

For no filter or priority filter:
```bash
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query backlog 2>/dev/null
```

For epic filter:
```bash
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query backlog --epic {epic_id} 2>/dev/null
```

If priority filter is set (e.g., P0), filter the JSON results client-side: keep only items where `priority` matches the filter value (case-insensitive, treating both `P0` and `now` as P0, `P1`/`sooner` as P1, etc.).

**Render:**

Group by horizon bucket in this order: Now (P0/now), Sooner (P1/sooner), Soon (P2/soon), Later (P3/later), Someday, Unscheduled. Omit empty buckets.

```
Now (P0) — {N} items
  ISSUE-NNN  [P0]  {title}  ({epic_id if set or "no epic"}, {status})
  ISSUE-NNN  [P0]  {title}  (no epic, blocked)
  (+N more)

Sooner (P1) — {N} items
  ...

Unscheduled — {N} items (no priority set)
  ...

Total: {total} items · {unlinked_count} unlinked (no epic)
```

Caps:
- Unfiltered: up to 5 items per bucket, then `(+N more)`
- Filtered (priority or epic): up to 50 items total, then `(+N more — narrow the filter)`
- Zero matches: `No items match filter '{filter}'. Total backlog: {N} items.`

If warnings, prepend the `Warnings:` section before the bucket output.

---

### Step V-deps: Dependencies view

```bash
python3 -c "
import sys, os, re, json
sys.path.insert(0, os.path.expanduser('~/.claude/scripts/sweetclaude'))
from cache import get_conn
conn = get_conn('.')

warnings = []
dep_map = {}  # id -> {'deps': [...], 'status': ..., 'epic': ...}
unresolved = []

# depends_on lives in frontmatter, not the cache — scan source files
import glob, yaml
scan_dirs = (glob.glob('.sweetclaude/product/roadmap/issues/*.md') +
             glob.glob('.sweetclaude/product/roadmap/issues/done/*.md') +
             glob.glob('.sweetclaude/product/backlog/*.md'))
for _f in scan_dirs:
    try:
        _parts = open(_f).read().split('---', 2)
        if len(_parts) < 3: continue
        _fm = yaml.safe_load(_parts[1]) or {}
        _deps_raw = _fm.get('depends_on') or []
        if isinstance(_deps_raw, str):
            _deps_raw = re.findall(r'(?:ISSUE|EP|MS|STORY)-\d+', _deps_raw)
        if not _deps_raw: continue
        _id = _fm.get('id', '')
        if not _id: continue
        # Look up status and epic from cache
        _row = conn.execute('SELECT status, epic FROM items WHERE id=?', (_id,)).fetchone()
        dep_map[_id] = {
            'deps': list(_deps_raw),
            'status': _row['status'] if _row else _fm.get('status', 'unknown'),
            'epic': (_row['epic'] if _row else _fm.get('epic', '')) or '',
        }
        for dep_id in _deps_raw:
            if not conn.execute('SELECT id FROM items WHERE id=?', (dep_id,)).fetchone():
                warnings.append(f'dep-targets-resolve: {_id} depends_on {dep_id!r} which does not exist')
                unresolved.append({'from': _id, 'to': dep_id})
    except Exception:
        pass

conn.close()
print('WARNINGS=' + json.dumps(warnings))
print('DEP_MAP=' + json.dumps(dep_map))
print('UNRESOLVED=' + json.dumps(unresolved))
" 2>/dev/null
```

If warnings found, prepend the `Warnings:` section.

**Build chains:** From dep_map, build adjacency chains — for each item that has dependencies, trace forward until no more. Show chains of length ≥ 2, longest first, max 15. Cycle detection: note `Cycle detection not yet available.`

**Render:**

```
Blocked chains:
  ISSUE-NNN → ISSUE-NNN → ISSUE-NNN  (EP-NNN, all active)
  ISSUE-NNN → ISSUE-NNN              (EP-NNN, ISSUE-NNN blocked)
  (+N more chains)

Unresolved references:
  ISSUE-NNN depends_on ISSUE-NNN  (ISSUE-NNN does not exist)

Circular dependencies:
  Cycle detection not yet available.

{N} items have dependencies · {M} chains · {K} unresolved refs
```

Omit "Unresolved references" section if none. Omit "Circular dependencies" section only if cycle detection is available and finds nothing (not yet the case — include the note).

---

### Step V-sprint: Sprint view

```bash
python3 -c "
import sys, os, glob, yaml, json
sprint_dir = '.sweetclaude/artifacts/sprints'
if not os.path.exists(sprint_dir):
    print('NO_SPRINT'); sys.exit()
active = None
for f in sorted(glob.glob(os.path.join(sprint_dir, '*.yaml'))):
    try:
        d = yaml.safe_load(open(f)) or {}
        if d.get('status') == 'active':
            active = d; break
    except Exception:
        pass
if not active:
    print('NO_ACTIVE_SPRINT'); sys.exit()
print(json.dumps(active, default=str))
" 2>/dev/null
```

If `NO_SPRINT` or `NO_ACTIVE_SPRINT`: output `No active sprint.` Stop.

**Consistency checks:**

```bash
python3 -c "
import sys, os, json
sys.path.insert(0, os.path.expanduser('~/.claude/scripts/sweetclaude'))
from cache import get_conn

sprint_json = open('/dev/stdin').read()  # from above
sprint = json.loads(sprint_json)
warnings = []

# sprint-dates-valid
start = sprint.get('start_date','')
end = sprint.get('end_date','')
if start and end and str(start) > str(end):
    warnings.append(f'sprint-dates-valid: start_date {start!r} is after end_date {end!r}')

# sprint-items-resolve
conn = get_conn('.')
items = sprint.get('items', [])
for item_id in items:
    if isinstance(item_id, dict):
        item_id = item_id.get('id', '')
    if item_id and not conn.execute('SELECT id FROM items WHERE id=?', (str(item_id),)).fetchone():
        warnings.append(f'sprint-items-resolve: {item_id!r} in sprint not found in cache')
conn.close()
for w in warnings:
    print(w)
" 2>/dev/null
```

If warnings, prepend the `Warnings:` section.

**Compute status counts** from the sprint's items list by querying each item's current status from cache.

**Render:**

```
Sprint {number}: "{name}"  [{status}]  {start_date} – {end_date}

  done:        {done}/{total} items ({pct}%)
  in-progress: {in_progress}
  to-do:       {todo}

  ISSUE-NNN  {title}  {status}
  ISSUE-NNN  {title}  {status}  (blocked by ISSUE-NNN)
  ... (+N done, not shown)
```

Show non-done items first, then collapse done items to `(+N done, not shown)`. Velocity = done/total × 100.
