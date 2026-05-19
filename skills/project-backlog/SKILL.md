---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "View and manage the unscheduled issue backlog."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:project-backlog" 2>/dev/null || true`

## MIGRATION GUARD

Before any other work, check for unmigrated v3 BL files:

```bash
PRODUCT_BASE=$(python3 -c "
import yaml, pathlib
p = pathlib.Path('.sweetclaude/artifact-privacy.yaml')
if p.exists():
    d = yaml.safe_load(p.read_text()) or {}
    base = d.get('categories', {}).get('product', {}).get('base_path', '')
    if base:
        print(base.rstrip('/'))
        exit()
print('.sweetclaude/product')
" 2>/dev/null || echo '.sweetclaude/product')
V3_FILES=$(find "${PRODUCT_BASE}/backlog" -maxdepth 1 -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' ')
if [ "$V3_FILES" -gt 0 ]; then
  echo "This project has $V3_FILES v3 stories that need to be migrated first."
  echo "Run: /sweetclaude:migrate"
  exit 1
fi
```

If the guard fires: print the message and stop. Do not proceed.

## MODE CHECK

Read `mode` from pre-loaded session state.

If `mode` is `shape_up`, output and stop:

> "This skill is not active in **Shape Up** mode.
>
> Shape Up has no backlog by design. New work enters through pitches: describe the problem and proposed solution, get it approved at the betting table, then create issues from the approved pitch.
>
> Write a pitch: `/sweetclaude:project-issues pitch`"

All other modes: proceed normally.

```python
import pathlib, yaml, re, datetime

BACKLOG_BASE = pathlib.Path('docs/product/backlog')
TYPE_DIRS = {'story': 'stories', 'bug': 'bugs', 'debt': 'debt', 'chore': 'chores'}

def read_story_file(path):
    raw = pathlib.Path(path).read_bytes().decode('utf-8').replace('\r\n', '\n')
    parts = raw.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2] if len(parts) > 2 else ''
    return fm, body

def find_story_by_id(story_id):
    for p in BACKLOG_BASE.rglob('*.md'):
        if p.stem.startswith(story_id + '-') or p.stem == story_id:
            return p
    return None

def write_story_file(path, fm, body):
    content = f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---\n{body}"
    pathlib.Path(path).write_text(content, encoding='utf-8')

def rebuild_cache():
    import subprocess
    subprocess.run(['python3', 'scripts/cache.py', '--project-dir', '.', '--rebuild'], capture_output=True)

# Load active backlog items (exclude done/ subdirs and metadata files)
active_files = [
    p for p in BACKLOG_BASE.rglob('*.md')
    if p.name not in ('INDEX.md', 'MIGRATION-MAP.md', 'SCHEMA.md') and '/done/' not in str(p)
]
items = []
for p in active_files:
    fm, _ = read_story_file(p)
    if fm.get('status') not in ('done', 'abandoned', 'deferred'):
        items.append((p, fm))
```

# Project Backlog

The backlog is every issue with no sprint assignment. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) | → **View** the full backlog |
| `promote <ID> <SP-NNN>` | → **Promote** issue into a sprint |
| `defer <ID>` | → **Defer** issue (status → deferred) |
| `review-inferred` | → **Review** imported issues needing confirmation |

---

## View (default)

Use the items loaded above. Present backlog grouped by priority bucket:

```
Backlog — {N} unscheduled issues

NOW ({n})
  STORY-001  story  xs  Title of issue

SOON ({n})
  STORY-002  story  m   Title of issue
  BUG-001    bug    s   Title of issue

LATER ({n})
  ...

UNESTIMATED ({n} — no priority or effort set)
  STORY-NNN  story  —   Title of issue
```

Priority buckets: `now`, `soon`, `later`, `someday` (in that order). Items with no priority → UNESTIMATED.

After the list, surface any of these conditions if present:

- **Unestimated count ≥ 10:** "Run `/sweetclaude:project-backlog-triage` — {N} issues have no effort or priority estimate."
- **Any items with `origin: imported`:** "{N} imported issues need review. Run `project-backlog review-inferred`."

---

## Promote

Move issue `<ID>` into sprint `<SP-NNN>`.

```python
path = find_story_by_id('<ID>')
fm, body = read_story_file(path)
```

Verify:
- Issue status is `new`, `ready`, or `active`. If `done` or `abandoned`, say: "Can't promote a {status} issue."

If valid:

```python
today = datetime.date.today().isoformat()
fm['sprint'] = '<SP-NNN>'
fm['status'] = 'ready'
fm['updated'] = today
# Append to Sprint History in body
write_story_file(path, fm, body)
```

Confirm: `Promoted {ID} → {SP-NNN}`

---

## Defer

Set issue status to `deferred`. Hides it from the default backlog view without closing it.

```python
path = find_story_by_id('<ID>')
fm, body = read_story_file(path)
fm['status'] = 'deferred'
fm['updated'] = datetime.date.today().isoformat()
write_story_file(path, fm, body)
```

Confirm: `Deferred <ID> — removed from active backlog`

---

## Review inferred

Load all items with `origin: imported` that haven't been reviewed:

```python
imported = [(p, fm) for p, fm in items if fm.get('origin') == 'imported']
```

If none: "No imported issues to review."

Otherwise, present them one at a time:

```
Imported issue {n} of {total}:

  {ID} — {title}
  Origin: imported
  Type: {type}

  Keep (accept as-is), Edit (change title/type), or Discard?
```

Wait for response per issue.
- **Keep:** `fm['origin'] = 'manual'` → write_story_file → confirm "Kept as {ID}"
- **Edit:** ask for new title and/or type, write both fields + set origin=manual
- **Discard:** delete the file and rebuild cache

After all reviewed: "Reviewed {N} imported issues: {kept} kept, {edited} edited, {discarded} discarded."

---

## Rules

- The backlog view never shows `done`, `abandoned`, or `deferred` issues — those are archived.
- Promoting into a sprint does not start the sprint. Sprint activation is done in `project-sprints`.
- An issue promoted into an active sprint gets status `ready`. An issue promoted into a planned sprint stays `ready`.
- Never auto-promote an entire backlog into a sprint — always promote individual issues deliberately.
- All reads and writes go directly to `docs/product/backlog/<type>s/<ID>-<slug>.md` files. Never touch `.sweetclaude/product/backlog/`.
