---
name: sweetclaude:migrate-diagnose
description: Internal subskill — diagnoses v3 BL-NNN file problems before migration. NOT user-invocable. Called only by sweetclaude:migrate (failure menu option 1) and sweetclaude:bootstrap (offer at hard stop).
---

This skill is internal-only. It is not accessible via slash command by the user. It is invoked exclusively by `sweetclaude:migrate` when migration fails (failure menu option 1) and by `sweetclaude:bootstrap` when a v3-files hard stop is detected.

## Procedure

### Helper: patch_frontmatter

Use this helper for all apply-fix recipes. Do not invent your own.

```python
def patch_frontmatter(path, mutate):
    import yaml
    raw = open(path, 'rb').read()
    if raw[:3] == b'\xEF\xBB\xBF':
        raw = raw[3:]
    text = raw.decode('utf-8').replace('\r\n', '\n')
    parts = text.split('---', 2)
    if len(parts) < 3:
        raise RuntimeError(f'no frontmatter in {path}')
    fm = yaml.safe_load(parts[1]) or {}
    mutate(fm)
    new_fm = yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip() + '\n'
    open(path, 'w', encoding='utf-8').write(f'---\n{new_fm}---{parts[2]}')
```

### Step 1: Enumerate v3 files

```python
import pathlib, yaml, sys

backlog_path = pathlib.Path('.sweetclaude/product/backlog')
files = sorted(backlog_path.glob('BL-*.md'), key=lambda p: p.name)

if not files:
    print("no v3 artifacts found")
    sys.exit(0)
```

### Step 2: Scan each file

For each file, in alphanumeric order by filename:

```python
findings = {}  # path -> list of problem strings
ids = {}        # id_value -> list of paths

V3_VALID_STATUSES = {'backlog', 'in_progress', 'done', 'cancelled', 'blocked', 'abandoned'}
VALID_TYPES = {'story', 'bug', 'debt', 'chore'}

for path in files:
    problems = []
    raw = open(path, 'rb').read()
    if raw[:3] == b'\xEF\xBB\xBF':
        raw = raw[3:]
    text = raw.decode('utf-8').replace('\r\n', '\n')

    parts = text.split('---', 2)
    if len(parts) < 3:
        problems.append('no-frontmatter-delimiter')
        findings[path] = problems
        continue

    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        problems.append(f'frontmatter-parse-error:{e}')
        findings[path] = problems
        continue

    for field in ('id', 'type', 'title', 'status'):
        if fm.get(field) is None:
            problems.append(f'missing-field:{field}')

    status = fm.get('status')
    if status is not None and status not in V3_VALID_STATUSES:
        problems.append(f'unknown-status:{status}')

    typ = fm.get('type')
    if typ is not None and typ not in VALID_TYPES:
        problems.append(f'unknown-type:{typ}')

    id_val = fm.get('id')
    if id_val is not None:
        ids.setdefault(id_val, []).append(path)

    findings[path] = problems
```

### Step 3: Detect duplicate IDs

```python
for id_val, paths in ids.items():
    if len(paths) > 1:
        for path in paths:
            findings[path].append(f'duplicate-id:{id_val}')
```

### Step 4: Output Markdown report

```python
print("# Diagnose Report\n")
for path in files:
    problems = findings.get(path, [])
    print(f"## {path.name}")
    if problems:
        for p in problems:
            print(f"- {p}")
    else:
        print("- (no findings)")
    print()

# Summary table
from collections import Counter
all_problems = [p for probs in findings.values() for p in probs]
classes = Counter(p.split(':')[0] for p in all_problems)
print("## Summary\n")
print("| problem class | count |")
print("|---|---|")
for cls, count in sorted(classes.items()):
    print(f"| {cls} | {count} |")
if not classes:
    print("| (none) | 0 |")
```

### Fix proposals

After producing the report, for each problem class found, present the fix proposal and (where available) apply the recipe using `patch_frontmatter`:

| Problem class | Proposal | Auto-fix? |
|---|---|---|
| `no-frontmatter-delimiter` | Cannot auto-fix. Manual edit required. | No |
| `frontmatter-parse-error` | Show first 20 lines, ask user to fix manually. | No |
| `missing-field:type` | Set `type: story`. | Yes: `patch_frontmatter(path, lambda fm: fm.update(type='story'))` |
| `missing-field:status` | Set `status: new`. | Yes: `patch_frontmatter(path, lambda fm: fm.update(status='new'))` |
| `unknown-status:cancelled` | Remap to `abandoned`. | Yes: `patch_frontmatter(path, lambda fm: fm.update(status='abandoned'))` |
| `unknown-status:backlog` | Remap to `new`. | Yes: `patch_frontmatter(path, lambda fm: fm.update(status='new'))` |
| `unknown-status:<other>` | Cannot auto-fix. Show value, ask user. | No |
| `unknown-type:<v>` | Cannot auto-fix. Show value, ask user which of `{story, bug, debt, chore}` to use. | No |
| `missing-field:id` | Cannot auto-fix. Show file, ask user to supply id. | No |
| `missing-field:title` | Cannot auto-fix. Show file, ask user to supply title. | No |
| `duplicate-id:<id>` | Cannot auto-fix. Show all files holding this id, ask user which to rename. | No |

After all chosen fixes have been applied, re-scan. If zero remaining problems: output `"Diagnose complete. Re-run /sweetclaude:migrate."` Otherwise output the remaining problems and stop.
