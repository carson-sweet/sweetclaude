---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Structured backlog grooming session."
---

## MIGRATION GUARD

Before any other work, check for unmigrated v3 BL files:

```bash
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
V3_FILES=$(find "${PRODUCT_BASE}/backlog" -maxdepth 1 -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' ')
if [ "$V3_FILES" -gt 0 ]; then
  echo "This project has $V3_FILES v3 stories that need to be migrated first."
  echo "Run: /sweetclaude:migrate"
  exit 1
fi
```

If the guard fires: print the message and stop. Do not proceed.

```python
import pathlib, yaml, re, datetime

BACKLOG_BASE = pathlib.Path('docs/product/backlog')
INDEX_PATH = BACKLOG_BASE / 'INDEX.md'
TYPE_DIRS = {'story': 'stories', 'bug': 'bugs', 'debt': 'debt', 'chore': 'chores'}

def read_story_file(path):
    raw = pathlib.Path(path).read_bytes().decode('utf-8').replace('\r\n', '\n')
    parts = raw.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2] if len(parts) > 2 else ''
    return fm, body

def write_story_file(path, fm, body):
    fm['updated'] = datetime.date.today().isoformat()
    content = f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---\n{body}"
    pathlib.Path(path).write_text(content, encoding='utf-8')

def read_index():
    raw = INDEX_PATH.read_text(encoding='utf-8')
    parts = raw.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
    return fm, parts[2]

def write_index(fm, body):
    fm['updated'] = datetime.date.today().isoformat()
    content = f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---{body}"
    INDEX_PATH.write_text(content, encoding='utf-8')

def rebuild_index_table(index_fm, index_body):
    """Rebuild the active tables in INDEX.md from current story files."""
    rows = {'story': [], 'bug': [], 'debt': [], 'chore': []}
    for p in BACKLOG_BASE.rglob('*.md'):
        if p.name in ('INDEX.md', 'MIGRATION-MAP.md') or '/done/' in str(p):
            continue
        fm, _ = read_story_file(p)
        typ = fm.get('type', 'story')
        if typ in rows and fm.get('status') not in ('done', 'abandoned', 'deferred'):
            rows[typ].append(fm)
    # Rebuild body by replacing tables
    # (simple implementation: reconstruct body sections)
    # Keep index_fm counters unchanged — they track IDs, not active count
    return rows

# Load active ungroomed backlog items
active_items = []
for p in BACKLOG_BASE.rglob('*.md'):
    if p.name in ('INDEX.md', 'MIGRATION-MAP.md') or '/done/' in str(p):
        continue
    fm, body = read_story_file(p)
    if fm.get('status') not in ('done', 'abandoned', 'deferred'):
        active_items.append((p, fm, body))

# Sort oldest first (by created date), then by id
active_items.sort(key=lambda x: (x[1].get('created', ''), x[1].get('id', '')))

ungroomed = [(p, fm, body) for p, fm, body in active_items
             if not fm.get('priority') or not fm.get('effort')]
TOTAL_BACKLOG = len(active_items)
UNGROOMED_COUNT = len(ungroomed)
```

# Project Backlog Triage

A focused grooming session. Works through ungroomed issues one at a time using INVEST criteria and t-shirt sizing. Arguments: `$ARGUMENTS`

---

## Step 0: v4 lint check

Before starting the triage session, run the v4 lint rules from `sweetclaude:_health` Step 3 inline. Surface any findings at the top of the output:

```
## v4 Storage Warnings
- counter-drift:bug (stored=2, max_id_seen=4)
```

Proceed to the triage session regardless — findings are informational, not blocking.

---

## Entry check

If `UNGROOMED_COUNT` is 0: "Backlog is fully groomed — all {TOTAL_BACKLOG} issues have priority and effort estimates. Nothing to triage."

Otherwise: "Starting triage — {UNGROOMED_COUNT} issues need grooming."

---

## Triage loop

For each item in `ungroomed`:

### 1. Present the issue

```
Issue {n} of {UNGROOMED_COUNT}: {ID}

  {title}
  Type: {type}

  {description — first 4 lines}

  Current priority: {priority or '—'}
  Current effort:   {effort or '—'}
```

### 2. Run INVEST check silently

Evaluate against the issue's description and acceptance criteria. Flag only genuine concerns.

| Criterion | What to check |
|---|---|
| **Independent** | Does it reference another unscheduled issue as a prerequisite? |
| **Negotiable** | Does the description dictate implementation rather than outcome? |
| **Valuable** | Is there a clear user/business outcome, or just a task? |
| **Estimable** | Is there enough information to size it, or are there unknown unknowns? |
| **Small** | Can this realistically be done in one sprint? |
| **Testable** | Can acceptance criteria be written (or are they already present)? |

### 3. Present recommendation

```
INVEST: {clean | list any flags}

Recommended:
  Priority: {now|soon|later|someday}  — {one-line reason}
  Effort:   {s|m|l|xl}                — {one-line reason}
```

**Effort sizing heuristics:**

| Signals | Effort |
|---|---|
| One AC, trivial change | s |
| 2–3 ACs, clear path | m |
| 4–6 ACs, some unknowns | l |
| Multiple subsystems, architectural change | xl |
| Should probably be split | xl → prompt to split |

### 4. Wait for user response

Accept:
- **`y`** or just Enter → accept recommendation as-is
- **`p=soon e=m`** → override specific fields
- **`skip`** → skip this issue, come back later
- **`split`** → split into two issues (see below)
- **`cancel`** → mark as abandoned, move to done/
- **`done`** → mark as already done, move to done/
- **`q`** → quit triage session, save progress

### 5. Apply decision

On `y` or field overrides:

```python
fm['priority'] = '<priority>'
fm['effort'] = '<effort>'
fm['status'] = 'ready'
write_story_file(path, fm, body)
# Also update INDEX.md active table row for this item
```

On `cancel` (status → abandoned, move to done/):
```python
import shutil
fm['status'] = 'abandoned'
fm['closed_date'] = datetime.date.today().isoformat()
write_story_file(path, fm, body)
done_dir = path.parent / 'done'
done_dir.mkdir(exist_ok=True)
shutil.move(str(path), str(done_dir / path.name))
```

On `done` (status → done, move to done/):
```python
import shutil
fm['status'] = 'done'
fm['closed_date'] = datetime.date.today().isoformat()
write_story_file(path, fm, body)
done_dir = path.parent / 'done'
done_dir.mkdir(exist_ok=True)
shutil.move(str(path), str(done_dir / path.name))
```

After each write: rebuild the relevant section of INDEX.md to reflect current active items.

### 6. Split flow

If the user says `split`:

Ask: "What are the two parts? Give me two titles."

Create two new story files using the same ID assignment logic as `project-issues create`. Delete the original file.

Confirm: "Split into {new_id_1} and {new_id_2}. Original {ID} removed."

Both new issues re-enter the triage queue immediately.

---

## Session summary

After the user exits (all done, `q`, or all issues processed):

```
Triage session complete
Groomed:   {N} issues
Skipped:   {N} issues
Split:     {N} issues → {M} new
Cancelled: {N} issues
Done:      {N} issues

Remaining ungroomed: {N}
```

If `remaining > 0`: "Run `project-backlog-triage` again to continue."

---

## Rules

- Triage one issue at a time. Never batch-present multiple issues.
- INVEST flags are informational. The user decides what to do with them — don't block on INVEST failures.
- If an issue has `xl` effort, always prompt to split. Never silently accept xl as the final estimate without checking.
- Skipped issues stay ungroomed and will reappear next session.
- Status is set to `ready` (not `new`) when groomed — this signals the issue is sprint-eligible.
- Every write updates both the individual story file AND the INDEX.md active table.
- All reads and writes go directly to `docs/product/backlog/<type>s/<ID>-<slug>.md` files. Never touch `.sweetclaude/product/backlog/`.
