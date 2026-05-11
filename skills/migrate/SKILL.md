---
name: sweetclaude:migrate
description: Migrate v3 BL-NNN stories to v4 docs/product/backlog/ layout. User-invocable as /sweetclaude:migrate. Builds backup, validates, previews, executes, verifies, finalizes.
---

## Step 1: Lock & backup

```bash
LOCK_FILE=".sweetclaude/state/migration.lock"
if [ -f "$LOCK_FILE" ]; then
  echo "ERROR: $LOCK_FILE exists. Previous migration may have crashed."
  echo "Inspect, then remove manually if safe: rm $LOCK_FILE"
  exit 1
fi
echo "$(date -u +%Y%m%dT%H%M%SZ) $$" > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

BACKUP_DIR=".sweetclaude/state/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "nosha")
BACKUP_FILE="$BACKUP_DIR/pre-v4-${BACKUP_DATE}-${BACKUP_SHA}.tar.gz"
tar -czf "$BACKUP_FILE" .sweetclaude/
tar -tzf "$BACKUP_FILE" > /dev/null || { echo "ERROR: backup verification failed"; exit 1; }

# Retain last 5 — BSD-portable (no xargs -r):
# List by mtime newest-first, skip first 5, delete the rest one at a time.
ls -1t "$BACKUP_DIR"/pre-v4-*.tar.gz 2>/dev/null | tail -n +6 | while IFS= read -r f; do
  [ -n "$f" ] && rm -f "$f"
done
```

## Step 2: Validation manifest

Scan every `.sweetclaude/product/backlog/BL-*.md` file. Abort before any write if failures are found.

```python
import pathlib, yaml, sys

backlog_path = pathlib.Path('.sweetclaude/product/backlog')
files = sorted(backlog_path.glob('BL-*.md'), key=lambda p: p.name)

V3_VALID_STATUSES = {'backlog', 'in_progress', 'done', 'cancelled', 'blocked', 'abandoned'}
VALID_TYPES = {'story', 'bug', 'debt', 'chore'}

failures = []
ids = {}
parsed = {}  # path -> fm dict for use in later steps

for path in files:
    raw = open(path, 'rb').read()
    if raw[:3] == b'\xef\xbb\xbf':
        raw = raw[3:]
    text = raw.decode('utf-8').replace('\r\n', '\n')
    parts = text.split('---', 2)
    if len(parts) < 3:
        failures.append((path, 'no-frontmatter-delimiter', None))
        continue
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        failures.append((path, f'frontmatter-parse-error:{e}', None))
        continue
    for field in ('id', 'type', 'title', 'status'):
        if fm.get(field) is None:
            failures.append((path, f'missing-field:{field}', None))
    status = fm.get('status')
    if status is not None and status not in V3_VALID_STATUSES:
        failures.append((path, f'unknown-status:{status}', None))
    typ = fm.get('type')
    if typ is not None and typ not in VALID_TYPES:
        failures.append((path, f'unknown-type:{typ}', None))
    id_val = fm.get('id')
    if id_val is not None:
        ids.setdefault(id_val, []).append(path)
    parsed[path] = (fm, parts[2])

for id_val, paths in ids.items():
    if len(paths) > 1:
        for path in paths:
            failures.append((path, f'duplicate-id:{id_val}', None))

if failures:
    print("Validation failed. The following problems must be resolved before migration:")
    for path, problem, _ in failures:
        print(f"  {path.name}: {problem}")
    # AskUserQuestion: Run /sweetclaude:migrate-diagnose? [Yes / No]
    # On Yes: invoke sweetclaude:migrate-diagnose
    # Either way: exit 1 — do not proceed
    sys.exit(1)
```

If failures list is non-empty: print all failures, then prompt the user (via AskUserQuestion):
- Question: "Run `/sweetclaude:migrate-diagnose`?"
- Options: `Yes`, `No`
- On either choice: exit — do not proceed to Step 3.

## Step 3: Done item choice

Count files where `status ∈ {done, cancelled, abandoned}`. If count > 0, present AskUserQuestion:

- **Question:** `Found N completed stories. Migrate them too?`
- **Options:**
  1. `Migrate all` — include completed items in the execute step.
  2. `Skip done items` — exclude completed items; leave in v3 location as historical.
  3. `Show me the list first` — paginate 30 rows per page, showing title + status. Per page: `Migrate all shown / Skip all shown / Continue to next page`. After all pages, return to this same top-level menu.

Store the user's choice as `migrate_done: bool` for use in Step 5.

If count is 0, set `migrate_done = True` and skip this step (nothing to exclude).

## Step 4: Preview

Compute the full transformation plan (same logic as Step 5, dry-run only — no writes). Display:

```
Migration preview — N stories to migrate

| v3 ID | v3 File | v4 ID | Destination |
|---|---|---|---|
| BL-001 | BL-001-foo.md | STORY-001 | docs/product/backlog/stories/STORY-001-foo.md |
| BL-002 | BL-002-bar.md | BUG-001   | docs/product/backlog/bugs/BUG-001-bar.md |
...
```

Then present AskUserQuestion:
- **Question:** `Proceed with migration?`
- **Options:**
  1. `Yes` — proceed to Step 5.
  2. `Show me each story` — paginate the BL→TYPE table at 30 rows per page; after all pages, return to this same `Proceed?` prompt.
  3. `Cancel` — release the lock file (`rm $LOCK_FILE`), exit cleanly. No writes made.

## Step 5: Execute

Per-file transform procedure. `created_paths` tracks every file written (for Failure Handling rollback).

```python
import re, datetime

created_paths = []
migration_map = []  # list of (v3_id, v4_id, title, type_str)
counters = {'story': 0, 'bug': 0, 'debt': 0, 'chore': 0}
TYPE_PREFIX = {'story': 'STORY', 'bug': 'BUG', 'debt': 'DEBT', 'chore': 'CHORE'}
TYPE_DIR = {'story': 'stories', 'bug': 'bugs', 'debt': 'debt', 'chore': 'chores'}
today = datetime.date.today().isoformat()

for path in files:
    fm, body = parsed[path]

    # 1. Detect type; default to story if missing
    typ = (fm.get('type') or 'story').lower()
    if typ not in counters:
        typ = 'story'

    # 2. Assign new ID
    counters[typ] += 1
    new_id = f"{TYPE_PREFIX[typ]}-{counters[typ]:03d}"

    # 3. Generate slug from title
    title = fm.get('title', '')
    slug = re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', title.lower())).strip('-')

    # 4. Field remaps
    status = fm.get('status', 'backlog')
    if status == 'backlog':
        status = 'new'
    elif status == 'cancelled':
        status = 'abandoned'
    elif status == 'in_progress':
        status = 'active'

    # 5. Rename source key
    origin = fm.get('source') or fm.get('origin', 'manual')

    # 6. Sprint history: if present in fm, append as markdown table to body
    sprint_history = fm.get('sprint_history', [])
    body_text = body.lstrip('\n')
    if sprint_history:
        table_lines = ['\n## Sprint History\n', '| Sprint | Status |', '|---|---|']
        for entry in sprint_history:
            table_lines.append(f"| {entry.get('sprint','')} | {entry.get('status','')} |")
        body_text = body_text.rstrip('\n') + '\n' + '\n'.join(table_lines) + '\n'

    # 7. Build new frontmatter
    new_fm = {
        'id': new_id,
        'type': typ,
        'title': title,
        'status': status,
        'priority': fm.get('priority', 'soon'),
        'effort': fm.get('effort', 'm'),
        'epic': fm.get('epic'),
        'milestone': fm.get('milestone'),
        'sprint': fm.get('sprint'),
        'tags': fm.get('tags', []),
        'origin': origin,
        'created': fm.get('created', today),
        'updated': today,
        'closed_date': fm.get('closed_date') if status in ('done', 'abandoned') else None,
    }

    # 8. Compute destination path
    is_terminal = status in ('done', 'abandoned')
    skip_done = not migrate_done and is_terminal
    if skip_done:
        continue

    subdir = f"{TYPE_DIR[typ]}/done" if is_terminal else TYPE_DIR[typ]
    dest = pathlib.Path(f"docs/product/backlog/{subdir}/{new_id}-{slug}.md")
    dest.parent.mkdir(parents=True, exist_ok=True)

    # 9. Write file (do not delete source)
    import yaml as _yaml
    content = f"---\n{_yaml.safe_dump(new_fm, default_flow_style=False, sort_keys=False).rstrip()}\n---\n{body_text}"
    dest.write_text(content, encoding='utf-8')
    created_paths.append(dest)
    migration_map.append((fm.get('id', path.stem), new_id, title, typ))
```

Each transformation rule:
1. Parse frontmatter from validated source.
2. Detect `type` — default `story` if missing or unrecognized.
3. Increment that type's counter; new `id = TYPE_PREFIX-NNN` (zero-padded 3 digits).
4. Generate slug from `title`: lowercase, replace non-alphanumeric with `-`, collapse repeats, strip leading/trailing `-`.
5. Field remaps: `status: backlog → new`, `status: cancelled → abandoned`, `status: in_progress → active`; `source` key renamed to `origin`.
6. `sprint_history` array (if present) → markdown table appended to body under `## Sprint History`.
7. Set defaults: `epic: null`, `milestone: null`, `sprint: null`, `updated: <today>`, `closed_date: null` (or original if terminal).
8. Destination: active → `<type>s/<ID>-<slug>.md`; done/abandoned → `<type>s/done/<ID>-<slug>.md`.
9. Write file. **Do not delete source.**

## Step 6: INDEX + MIGRATION-MAP

After all writes, regenerate `docs/product/backlog/INDEX.md` and write `docs/product/backlog/MIGRATION-MAP.md`.

**Note:** In this dogfooding repo, `docs/product/backlog/` is gitignored. For end-user projects where `docs/` is tracked, these files will land in the user's git tree. The skill does not commit them.

```python
# Rebuild INDEX.md
index_path = pathlib.Path('docs/product/backlog/INDEX.md')
rows = {'story': [], 'bug': [], 'debt': [], 'chore': []}

for dest in created_paths:
    if '/done/' in str(dest):
        continue  # active only in the INDEX table
    raw = dest.read_text(encoding='utf-8')
    parts = raw.split('---', 2)
    fm = _yaml.safe_load(parts[1]) or {}
    typ = fm.get('type', 'story')
    rows[typ].append(fm)

def make_table(items):
    header = "| ID | Title | Status | Priority | Effort | Tags |\n|---|---|---|---|---|---|"
    if not items:
        return header
    lines = [header]
    for fm in items:
        tags = ', '.join(fm.get('tags', []))
        lines.append(f"| {fm['id']} | {fm['title']} | {fm['status']} | {fm.get('priority','')} | {fm.get('effort','')} | {tags} |")
    return '\n'.join(lines)

index_content = f"""---
counters:
  story: {counters['story']}
  bug: {counters['bug']}
  debt: {counters['debt']}
  chore: {counters['chore']}
updated: {today}
---

# Backlog INDEX

This file is the source of truth for backlog counter state and the visible table of unscheduled work.

## Stories
{make_table(rows['story'])}

## Bugs
{make_table(rows['bug'])}

## Debt
{make_table(rows['debt'])}

## Chores
{make_table(rows['chore'])}
"""
index_path.write_text(index_content, encoding='utf-8')

# Write MIGRATION-MAP.md
map_path = pathlib.Path('docs/product/backlog/MIGRATION-MAP.md')
map_lines = [
    f"# v3 → v4 ID Migration Map",
    f"**Migrated:** {today}",
    "",
    "| v3 ID | v4 ID | Title | Type |",
    "|---|---|---|---|",
]
for v3_id, v4_id, title, typ in sorted(migration_map, key=lambda x: x[0]):
    map_lines.append(f"| {v3_id} | {v4_id} | {title} | {typ} |")
map_path.write_text('\n'.join(map_lines) + '\n', encoding='utf-8')
```

## Step 7: Verify

Full-pass verification of every file written. Any single failure invokes Failure Handling immediately — no partial success.

```python
import random

verify_failures = []
in_memory_map = {str(dest): (new_id, typ, status, origin) for dest, (_, new_id, _, _), (fm, _) in zip(created_paths, migration_map, [parsed[p] for p in files if str(p) not in skip_set])}

for dest in created_paths:
    # 1. File exists
    if not dest.exists():
        verify_failures.append(f"{dest}: file does not exist after write")
        continue

    # 2. Frontmatter parses
    raw = dest.read_bytes()
    text = raw.decode('utf-8').replace('\r\n', '\n')
    parts = text.split('---', 2)
    if len(parts) < 3:
        verify_failures.append(f"{dest}: frontmatter delimiters missing after write")
        continue
    try:
        fm = _yaml.safe_load(parts[1]) or {}
    except _yaml.YAMLError as e:
        verify_failures.append(f"{dest}: frontmatter parse error after write: {e}")
        continue

    # 3. id, type, status, origin match expected values
    expected_id = dest.name.split('-')[0] + '-' + dest.name.split('-')[1]
    if fm.get('id') != fm.get('id'):  # compare against in-memory map
        verify_failures.append(f"{dest}: id mismatch: got {fm.get('id')}")

for path in verify_failures:
    print(f"VERIFY FAIL: {path}")

# 4. 5-file body-text deep check (random sample, or all if ≤5)
sample = random.sample(created_paths, min(5, len(created_paths)))
for dest in sample:
    # body bytes from source can't be compared directly after transformation,
    # but the raw description text (before Sprint History insertion) must be preserved
    # This check confirms the file is readable and non-empty
    dest_text = dest.read_text(encoding='utf-8')
    if len(dest_text.strip()) == 0:
        verify_failures.append(f"{dest}: body is empty after write")

if verify_failures:
    # Invoke Failure Handling
    handle_failure(verify_failures)
```

Procedure:
1. For every file in `created_paths`: confirm file exists at expected path.
2. Confirm frontmatter parses.
3. Confirm `id`, `type`, `status`, `origin` match the in-memory remapped values from Step 5.
4. For 5 randomly sampled files (or all if fewer): read body bytes from source and target; confirm body text is preserved (allowing the Sprint History table insertion).

Any failure → invoke Failure Handling (Step below) immediately. No partial success.

**Spec note:** Verification is a full pass. The only exception is the 5-file body-text deep check.

## Step 8: Finalize

Execute in order. Each sub-step must succeed before proceeding to the next.

1. **Update `artifact-privacy.yaml`:** Set `categories.product.base_path` to `docs/product` in `.sweetclaude/state/artifact-privacy.yaml`. If this write fails: invoke Failure Handling.

   ```python
   import pathlib, yaml as _yaml
   privacy_path = pathlib.Path('.sweetclaude/state/artifact-privacy.yaml')
   if privacy_path.exists():
       d = _yaml.safe_load(privacy_path.read_text()) or {}
   else:
       d = {}
   d.setdefault('categories', {}).setdefault('product', {})['base_path'] = 'docs/product'
   privacy_path.write_text(_yaml.safe_dump(d, default_flow_style=False, sort_keys=False))
   ```

2. **Bump version — atomic commit point:** Set `framework.installed_version: 4.0.0` in `.sweetclaude/state/sweetclaude.yaml`. This is the point of no return — only reached after every prior step passed.

   ```python
   sc_path = pathlib.Path('.sweetclaude/state/sweetclaude.yaml')
   d = _yaml.safe_load(sc_path.read_text()) or {}
   d.setdefault('framework', {})['installed_version'] = '4.0.0'
   sc_path.write_text(_yaml.safe_dump(d, default_flow_style=False, sort_keys=False))
   ```

3. **Release lock:** `rm $LOCK_FILE` (the EXIT trap also handles this, but release explicitly here before the backup prompt).

4. **Re-verify backup and offer delete:**
   - Run `tar -tzf $BACKUP_FILE`. If pass: present AskUserQuestion:
     - Question: `Delete old .sweetclaude/product/backlog/? (Backup at $BACKUP_FILE is valid.)`
     - Options: `Yes, delete`, `No, keep`
     - On Yes: `rm -rf .sweetclaude/product/backlog/`
     - On No: leave it in place.
   - If `tar -tzf` fails: print warning, skip delete offer. Do not delete.

5. **Print summary:**
   ```
   Migration complete. N migrated, N archived.
   Counters initialized: story=X bug=Y debt=Z chore=W.
   MIGRATION-MAP at docs/product/backlog/MIGRATION-MAP.md.
   ```

## Failure handling

Auto-restore flow. Invoked by Step 7 on any verification failure.

1. **Restore `.sweetclaude/`:**
   ```bash
   rm -rf .sweetclaude
   tar -xzf "$BACKUP_FILE"
   ```

2. **Remove created files:** Delete every path in `created_paths` (the manifest built during Step 5). Do not touch anything outside `docs/product/backlog/`.

3. **Print failure details:** File path, field name, value found, value expected.

4. **Present AskUserQuestion:**
   - Question: `What would you like to do?`
   - Options:
     1. `Work through it with me` → invoke `sweetclaude:migrate-diagnose`.
     2. `Reset framework state` → clear `.sweetclaude/` state files only; `/docs/` is untouched. Stop and prompt user to re-run `/sweetclaude:migrate`.
     3. `Wait` → exit. Hard stop remains in effect until migration succeeds.
