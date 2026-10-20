---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "View and manage the unscheduled issue backlog."
---



## MIGRATION GUARD

Before any other work, check for legacy migration/recovery risk:

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
LEGACY_FILES=$(find "${PRODUCT_BASE}" -maxdepth 4 -type f \( -name 'BL-*.md' -o -name 'STORY-*.md' -o -name 'BUG-*.md' -o -name 'DEBT-*.md' -o -name 'CHORE-*.md' \) 2>/dev/null | wc -l | tr -d ' ')
if [ "$LEGACY_FILES" -gt 0 ]; then
  SCRIPT=${CLAUDE_PLUGIN_ROOT}/scripts/recovery/recover_project.py
  if [ ! -f "$SCRIPT" ]; then
    SCRIPT=$(find "$(dirname "${CLAUDE_PLUGIN_ROOT}")" -type f -path '*/scripts/recovery/recover_project.py' 2>/dev/null | sort -V | tail -1)
  fi
  if [ -n "$SCRIPT" ] && [ -f "$SCRIPT" ]; then
    python3 "$SCRIPT" guard --project-dir . --pretty
  else
    echo '{"status":"guard-unavailable","message":"Recovery guard unavailable. Run /sweetclaude:configure update before migration."}'
  fi
fi
```

If the guard output has `status` `run-recover`, `manual-review`,
`compatibility-mode`, `missing-product-base`, or `guard-unavailable`: print the
guard `message`, tell the user to run `/sweetclaude:configure recover` when recovery is
available, and stop. Do not recommend migration.

If the guard output has `status` `supported-migration-available`: print
"This project has a typed legacy backlog layout that can be migrated. Run
`/sweetclaude:configure migrate` to convert to the unified ISSUE-NNN taxonomy." Then stop.

If the guard output has `status` `migration-may-be-needed`: print the guard
`message`, then stop and tell the user to review `/sweetclaude:configure migrate` before
running it. Do not invoke migration from this skill.

## MODE CHECK

Read `mode` from pre-loaded session state.

If `mode` is `shape_up`, output and stop:

> "This skill is not active in **Shape Up** mode.
>
> Shape Up has no backlog by design. New work enters through pitches: describe the problem and proposed solution, get it approved at the betting table, then create issues from the approved pitch.
>
> Write a pitch: `/sweetclaude:build project-issues pitch`"

All other modes: proceed normally.

```python
import pathlib, yaml, re, datetime

BACKLOG_BASE = pathlib.Path('.sweetclaude/product/backlog')

def read_issue_file(path):
    raw = pathlib.Path(path).read_bytes().decode('utf-8').replace('\r\n', '\n')
    parts = raw.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2] if len(parts) > 2 else ''
    return fm, body

def find_issue_by_id(issue_id):
    for p in BACKLOG_BASE.rglob('*.md'):
        if p.stem.startswith(issue_id + '-') or p.stem == issue_id:
            return p
    return None

def write_issue_file(path, fm, body):
    content = f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---\n{body}"
    pathlib.Path(path).write_text(content, encoding='utf-8')

def rebuild_cache():
    import subprocess, os
    subprocess.run(['python3', os.path.expanduser('${CLAUDE_PLUGIN_ROOT}/scripts/cache.py'), '--project-dir', '.', '--rebuild'], capture_output=True)

# Load active backlog items (exclude done/ subdirs and metadata files)
active_files = [
    p for p in BACKLOG_BASE.rglob('*.md')
    if p.name not in ('INDEX.md', 'MIGRATION-MAP.md', 'SCHEMA.md') and '/done/' not in str(p)
]
items = []
for p in active_files:
    fm, _ = read_issue_file(p)
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

P0 ({n})
  ISSUE-001  story  xs  Title of issue

P1 ({n})
  ISSUE-002  story  m   Title of issue
  ISSUE-003  bug    s   Title of issue

P2 ({n})
  ...

UNESTIMATED ({n} — no priority or effort set)
  ISSUE-NNN  story  —   Title of issue
```

Priority buckets: `P0`, `P1`, `P2`, `P3` (in that order). Items with no priority → UNESTIMATED.

After the list, surface any of these conditions if present:

- **Unestimated count ≥ 10:** "Run `/sweetclaude:build project-backlog-triage` — {N} issues have no effort or priority estimate."
- **Any items with `origin: imported`:** "{N} imported issues need review. Run `project-backlog review-inferred`."

---

## Promote

Move issue `<ID>` into sprint `<SP-NNN>`.

```python
path = find_issue_by_id('<ID>')
fm, body = read_issue_file(path)
```

Verify:
- Issue status is `new`, `ready`, or `active`. If `done` or `abandoned`, say: "Can't promote a {status} issue."

If valid:

```python
fm['sprint'] = '<SP-NNN>'
# Append to Sprint History in body
write_issue_file(path, fm, body)
```

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py set --file {path} --status ready --actor project-backlog --project-dir .
```

Confirm: `Promoted {ID} → {SP-NNN}`

---

## Defer

Set issue status to `deferred`. Hides it from the default backlog view without closing it.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py set --file {path} --status deferred --actor project-backlog --project-dir .
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
- **Keep:** `fm['origin'] = 'manual'` → write_issue_file → confirm "Kept as {ID}"
- **Edit:** ask for new title and/or type, write both fields + set origin=manual
- **Discard:** delete the file and rebuild cache

After all reviewed: "Reviewed {N} imported issues: {kept} kept, {edited} edited, {discarded} discarded."

---

## Rules

- The backlog view never shows `done`, `abandoned`, or `deferred` issues — those are archived.
- Promoting into a sprint does not start the sprint. Sprint activation is done in `project-sprints`.
- An issue promoted into an active sprint gets status `ready`. An issue promoted into a planned sprint stays `ready`.
- Never auto-promote an entire backlog into a sprint — always promote individual issues deliberately.
- All reads and writes go to `.sweetclaude/product/backlog/<ID>-<slug>.md` files.
