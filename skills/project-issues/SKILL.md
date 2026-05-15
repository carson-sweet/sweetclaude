---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Manage project issues — list, view, create, update, and close."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:project-issues" 2>/dev/null || true`

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

```python
import pathlib, yaml, re, datetime, shutil

BACKLOG_BASE = pathlib.Path('docs/product/backlog')
INDEX_PATH = BACKLOG_BASE / 'INDEX.md'
TYPE_DIRS = {'story': 'stories', 'bug': 'bugs', 'debt': 'debt', 'chore': 'chores'}
TYPE_PREFIX = {'story': 'STORY', 'bug': 'BUG', 'debt': 'DEBT', 'chore': 'CHORE'}

def read_index():
    raw = INDEX_PATH.read_text(encoding='utf-8')
    parts = raw.split('---', 2)
    return yaml.safe_load(parts[1]) or {}, parts[2]

def write_index(fm, body):
    content = f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---{body}"
    INDEX_PATH.write_text(content, encoding='utf-8')

def read_story_file(path):
    raw = pathlib.Path(path).read_bytes().decode('utf-8').replace('\r\n', '\n')
    parts = raw.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2] if len(parts) > 2 else ''
    return fm, body

def write_story_file(path, fm, body):
    content = f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---\n{body}"
    pathlib.Path(path).write_text(content, encoding='utf-8')

def find_story_by_id(story_id):
    for p in BACKLOG_BASE.rglob('*.md'):
        if p.name in ('INDEX.md', 'MIGRATION-MAP.md'):
            continue
        stem = p.stem
        if stem == story_id or stem.startswith(story_id + '-'):
            return p
    return None

def make_slug(title):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', title.lower())).strip('-')

def assign_new_id(typ):
    index_fm, index_body = read_index()
    counters = index_fm.setdefault('counters', {'story': 0, 'bug': 0, 'debt': 0, 'chore': 0})
    counters[typ] = counters.get(typ, 0) + 1
    index_fm['updated'] = datetime.date.today().isoformat()
    write_index(index_fm, index_body)
    return f"{TYPE_PREFIX[typ]}-{counters[typ]:03d}"

def all_story_files():
    return [
        p for p in BACKLOG_BASE.rglob('*.md')
        if p.name not in ('INDEX.md', 'MIGRATION-MAP.md')
    ]
```

# Project Issues

Manage project issues. Arguments: `$ARGUMENTS`

---

## MODE CHECK

Read `mode` from pre-loaded session state.

### Shape Up (shape_up) — pitch source enforcement

If `mode` is `shape_up` AND operation is `create` (not `pitch`, `list`, or `update`):

Ask: "Is this issue derived from an approved pitch?"

- **Yes** → Ask for pitch ID (e.g., `PITCH-001`). Include `pitch_id: {PITCH-XXX}` in the frontmatter. Proceed with create.
- **No / I don't have a pitch** → Output and stop:
  > "In Shape Up mode, all issues must come from an approved pitch. The betting table has already decided what's worth building — issues outside approved pitches expand scope without an appetite trade-off.
  >
  > Write a pitch first: `/sweetclaude:project-issues pitch`"

All other modes: proceed with standard create flow. No pitch source required.

---

## Routing

Parse the first word of `$ARGUMENTS` to determine the operation.

| First word | Operation |
|---|---|
| (empty) | → **List** all non-done issues |
| `list` | → **List** all non-done issues |
| `backlog` | → **Backlog** (issues not yet in a sprint) |
| `view <ID>` | → **View** single issue |
| `new` | → **Create** new issue interactively |
| `update <ID>` | → **Update** existing issue |
| `close <ID>` | → **Close** issue (status → done, move to done/) |
| `reopen <ID>` | → **Reopen** issue (status → new) |

---

## List

```python
files = all_story_files()
stories = []
for p in files:
    fm, _ = read_story_file(p)
    if fm.get('status') not in ('done', 'abandoned'):
        stories.append(fm)

# Sort: priority order, then by id
PRIORITY_ORDER = {'now': 1, 'soon': 2, 'later': 3, 'someday': 4, None: 5}
stories.sort(key=lambda fm: (PRIORITY_ORDER.get(fm.get('priority'), 5), fm.get('id', '')))
```

Present as a compact table. Sort: done/abandoned last, then by priority, then by ID.

```
ID         Type    Status      Pri       Eff  Title
STORY-001  story   new         soon      m    Add OAuth login
BUG-001    bug     active      now       s    Crash on empty input
...
```

After the table: `{N} issues  ({done} done, {active} active, {new} new)`

---

## Backlog

Show items with no sprint assignment and status not in done/abandoned:

```python
backlog = [fm for fm in stories if not fm.get('sprint') and fm.get('status') not in ('done', 'abandoned', 'deferred')]
```

Present same table format as List, sorted by priority. Header: `Backlog — {N} unscheduled issues`

After table: suggest `project-sprints` to schedule issues into a sprint, or `project-backlog-triage` if more than 10 issues have no effort estimate.

---

## View

```python
path = find_story_by_id('<ID>')
if not path:
    print(f"Issue `<ID>` not found.")
else:
    fm, body = read_story_file(path)
```

Present as:

```
STORY-001 — Add OAuth login
Type:      story          Status:   new
Priority:  soon           Effort:   m
Epic:      (none)         Sprint:   (none)
Origin:    manual

Description
  ...

Acceptance Criteria
  (if present)

Sprint History
  (if present)
```

If the issue has been in 2+ sprints without completing, add a warning:
`Adrift: carried over {N} sprints without completion.`

---

## Create

Ask one question at a time. Do not present a form.

1. **Title** — "What's the issue? One line."
2. **Type** — "story / bug / debt / chore?" (default: story)
3. **Description** — For stories: "As a [who], they want [what] so that [why]?" For bugs: "Steps to reproduce?" For debt: "What's the structural problem?" For chores: "What needs to be done?"
4. **Acceptance criteria** (story/bug only) — "What conditions make this done? List them one per line, or say none."
5. **Priority** — "now / soon / later / someday?" (default: soon)
6. **Effort** — "s / m / l / xl?" (default: m)
7. **Epic** — "Does this belong to an epic?" List available epics first, or say none.

Once all answers collected:

```python
today = datetime.date.today().isoformat()
typ = '<type>'  # story, bug, debt, or chore
new_id = assign_new_id(typ)
slug = make_slug('<title>')
fm = {
    'id': new_id,
    'type': typ,
    'title': '<title>',
    'status': 'new',
    'priority': '<priority>',
    'effort': '<effort>',
    'epic': '<epic_id or null>',
    'milestone': None,
    'sprint': None,
    'tags': [],
    'origin': 'manual',
    'created': today,
    'updated': today,
    'closed_date': None,
}
dest = BACKLOG_BASE / TYPE_DIRS[typ] / f"{new_id}-{slug}.md"
body = f"\n## Description\n\n<description>\n\n## Acceptance Criteria\n\n<ac>\n"
write_story_file(dest, fm, body)
```

Confirm: `Created {new_id} — {title}`

---

## Update

```python
path = find_story_by_id('<ID>')
fm, body = read_story_file(path)
```

Show the current values. Ask: "What would you like to change?" Accept natural language or field=value pairs.

Map the user's intent to fields:
- "move to sprint SP-003" → `sprint: SP-003`, `status: active`
- "set priority to soon" → `priority: soon`
- "assign to epic EP-001" → `epic: EP-001`
- "remove from sprint" → `sprint: null`
- "add acceptance criteria" → append to body Acceptance Criteria section

Then:

```python
fm['updated'] = datetime.date.today().isoformat()
# apply changed fields
write_story_file(path, fm, body)
```

Confirm: `Updated {ID} — {list of changed fields}`

---

## Close

Set status to done, move file to the `done/` subdirectory, and set `closed_date`.

```python
path = find_story_by_id('<ID>')
fm, body = read_story_file(path)
today = datetime.date.today().isoformat()
fm['status'] = 'done'
fm['closed_date'] = today
fm['updated'] = today

typ = fm.get('type', 'story')
done_dir = BACKLOG_BASE / TYPE_DIRS.get(typ, 'stories') / 'done'
done_dir.mkdir(parents=True, exist_ok=True)
new_path = done_dir / path.name
write_story_file(path, fm, body)  # write first
shutil.move(str(path), str(new_path))  # then move
```

Confirm: `Closed {ID} — {title}`

If the issue was the last open issue in an epic, surface:
`All issues in {EP-NNN} are now done. Run project-epics to close the epic.`

---

## Reopen

```python
path = find_story_by_id('<ID>')
fm, body = read_story_file(path)
today = datetime.date.today().isoformat()
fm['status'] = 'new'
fm['sprint'] = None
fm['closed_date'] = None
fm['updated'] = today

typ = fm.get('type', 'story')
active_dir = BACKLOG_BASE / TYPE_DIRS.get(typ, 'stories')
new_path = active_dir / path.name
write_story_file(path, fm, body)
if '/done/' in str(path):
    shutil.move(str(path), str(new_path))
```

Confirm: `Reopened {ID} — returned to backlog`

---

## Rules

- Never delete an issue — use `close` (status=done, moved to done/) or set status=abandoned for items that won't be done.
- Closing a story moves the file from `<type>s/<ID>-<slug>.md` to `<type>s/done/<ID>-<slug>.md`. The file is never deleted.
- Sprint assignment always goes through `update`, not direct write, so sprint history in the body is maintained.
- If `$ARGUMENTS` contains an ID that doesn't look like a v4 ID (`STORY-NNN`, `BUG-NNN`, `DEBT-NNN`, `CHORE-NNN`), say: "That doesn't look like a v4 issue ID. IDs take the form STORY-NNN, BUG-NNN, DEBT-NNN, or CHORE-NNN."
- All reads and writes go directly to `docs/product/backlog/<type>s/<ID>-<slug>.md` files. Never touch `.sweetclaude/product/backlog/`.
