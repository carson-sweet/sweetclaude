---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Import open GitHub Issues into the local issue store as v4 story files."
---

```python
import pathlib, yaml, re, datetime

BACKLOG_BASE = pathlib.Path('docs/product/backlog')
INDEX_PATH = BACKLOG_BASE / 'INDEX.md'
TYPE_PREFIX = {'story': 'STORY', 'bug': 'BUG', 'debt': 'DEBT', 'chore': 'CHORE'}

def read_index():
    raw = INDEX_PATH.read_text(encoding='utf-8')
    parts = raw.split('---', 2)
    return yaml.safe_load(parts[1]) or {}, parts[2]

def write_index(fm, body):
    fm['updated'] = datetime.date.today().isoformat()
    INDEX_PATH.write_text(
        f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---{body}",
        encoding='utf-8'
    )

def assign_new_id(typ):
    index_fm, index_body = read_index()
    counters = index_fm.setdefault('counters', {'story': 0, 'bug': 0, 'debt': 0, 'chore': 0})
    counters[typ] = counters.get(typ, 0) + 1
    write_index(index_fm, index_body)
    return f"{TYPE_PREFIX[typ]}-{counters[typ]:03d}"

def make_slug(title):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', title.lower())).strip('-')

def write_story_file(path, fm, body):
    content = f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---\n{body}"
    pathlib.Path(path).write_text(content, encoding='utf-8')

def github_number_already_imported(gh_number):
    """Check if a GitHub issue number is already in any local story file."""
    for p in BACKLOG_BASE.rglob('*.md'):
        if p.name in ('INDEX.md', 'MIGRATION-MAP.md'):
            continue
        raw = p.read_text(encoding='utf-8')
        parts = raw.split('---', 2)
        if len(parts) < 3:
            continue
        try:
            fm = yaml.safe_load(parts[1]) or {}
            if fm.get('github_issue_number') == gh_number:
                return True
        except Exception:
            pass
    return False
```

# GitHub Issues — Import

Pull open issues from GitHub into the local issue store as v4 story files under `docs/product/backlog/`. Idempotent — issues already imported by GitHub number are skipped. Arguments: `$ARGUMENTS`

---

## Prerequisites

```bash
gh auth status 2>/dev/null && echo "GH_OK" || echo "GH_NOT_AUTH"
git remote get-url origin 2>/dev/null || echo "NO_REMOTE"
```

If `GH_NOT_AUTH`: "GitHub CLI is not authenticated. Run `gh auth login` first." Stop.
If `NO_REMOTE`: "No git remote found. Import requires a GitHub remote." Stop.

---

## Import

Fetch open issues:

```bash
gh issue list --state open --limit 200 --json number,title,body,labels,state,url 2>/dev/null
```

For each GitHub issue:

1. Check whether a local v4 story already has `github_issue_number` matching this issue number (use `github_number_already_imported(number)` above).

2. If a match exists: skip. Import is one-way — do not overwrite local edits.

3. If no match: map fields and create a new v4 story file:

   ```python
   today = datetime.date.today().isoformat()
   typ = 'story'  # default; apply label mapping below to override
   new_id = assign_new_id(typ)
   title = '<gh_issue_title>'
   slug = make_slug(title)

   # Label → effort mapping
   effort = 'm'  # default
   for label in gh_labels:
       name = label.get('name', '').lower()
       if name in ('size:s', 'effort:s'): effort = 's'
       elif name in ('size:m', 'effort:m'): effort = 'm'
       elif name in ('size:l', 'effort:l'): effort = 'l'
       elif name in ('size:xl', 'effort:xl'): effort = 'xl'

   fm = {
       'id': new_id,
       'type': typ,
       'title': title,
       'status': 'new',
       'priority': 'soon',
       'effort': effort,
       'epic': None,
       'milestone': None,
       'sprint': None,
       'tags': [],
       'origin': 'imported',
       'github_issue_number': <gh_number>,
       'github_url': '<gh_url>',
       'created': today,
       'updated': today,
       'closed_date': None,
   }
   body_text = '<gh_issue_body truncated to 500 chars>'
   body = f"\n## Description\n\n{body_text}\n"
   dest = BACKLOG_BASE / 'stories' / f"{new_id}-{slug}.md"
   write_story_file(dest, fm, body)
   ```

   Labels → effort mapping (applied if label present, otherwise default `m`):

   | GitHub label | effort |
   |---|---|
   | `size:s` or `effort:s` | s |
   | `size:m` or `effort:m` | m |
   | `size:l` or `effort:l` | l |
   | `size:xl` or `effort:xl` | xl |

After processing all issues, report:

```
GitHub Issues import complete
  Imported: {N} new issues (origin: imported)
  Skipped:  {N} already present
  Open on GitHub: {N} total
```

If N > 20 imported: "That's a large import. Consider running `/sweetclaude:project-backlog-triage` to groom priorities before the next sprint."

---

## Rules

- All imported issues get `origin: imported` (not `source: github`) to follow the v4 story schema.
- `github_issue_number` and `github_url` are stored as extra frontmatter fields for sync purposes.
- ID assignment reads INDEX.md counters, increments, and writes back atomically before writing the story file.
- All files land under `docs/product/backlog/stories/` (type defaults to `story` on import).
- Never write to `.sweetclaude/product/backlog/`.
