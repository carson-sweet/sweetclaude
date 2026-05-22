---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Bidirectional status sync between local issue files and GitHub Issues."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:project-gh-sync-issues" 2>/dev/null || true`

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
import pathlib, yaml, datetime, shutil

BACKLOG_BASE = pathlib.Path('.sweetclaude/product/backlog')

def read_issue_file(path):
    raw = pathlib.Path(path).read_bytes().decode('utf-8').replace('\r\n', '\n')
    parts = raw.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2] if len(parts) > 2 else ''
    return fm, body

def write_issue_file(path, fm, body):
    fm['updated'] = datetime.date.today().isoformat()
    content = f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---\n{body}"
    pathlib.Path(path).write_text(content, encoding='utf-8')

def all_backlog_issue_files():
    """Enumerate issue files under .sweetclaude/product/backlog/ only.
    Explicitly excludes .sweetclaude/product/roadmap/ (out of scope — Phase 2).
    """
    roadmap_base = BACKLOG_BASE.parent / 'roadmap'
    result = []
    for p in BACKLOG_BASE.rglob('*.md'):
        if p.name in ('INDEX.md', 'MIGRATION-MAP.md', 'SCHEMA.md'):
            continue
        # Guard: skip any file that somehow resolves under roadmap/
        if roadmap_base.exists() and roadmap_base in p.parents:
            continue
        result.append(p)
    return result

def find_issue_by_gh_number(gh_number):
    for p in all_backlog_issue_files():
        fm, body = read_issue_file(p)
        if fm.get('github_issue_number') == gh_number:
            return p, fm, body
    return None, None, None

def close_issue_file(path, fm, body):
    """Set status=done, closed_date=today, move to done/ subdir."""
    today = datetime.date.today().isoformat()
    fm['status'] = 'done'
    fm['closed_date'] = today
    write_issue_file(path, fm, body)
    done_dir = path.parent / 'done'
    done_dir.mkdir(parents=True, exist_ok=True)
    new_path = done_dir / path.name
    shutil.move(str(path), str(new_path))
    return new_path
```

# GitHub Issues — Sync

Bidirectional status sync between local issue files and GitHub Issues. Operates on `.sweetclaude/product/backlog/` issue files only. Roadmap sync is out of scope. Arguments: `$ARGUMENTS`

---

## Prerequisites

```bash
gh auth status 2>/dev/null && echo "GH_OK" || echo "GH_NOT_AUTH"
git remote get-url origin 2>/dev/null || echo "NO_REMOTE"
```

If `GH_NOT_AUTH`: "GitHub CLI is not authenticated. Run `gh auth login` first." Stop.
If `NO_REMOTE`: "No git remote found. Sync requires a GitHub remote." Stop.

---

## Pass 1 — GitHub closed → update local

```bash
gh issue list --state closed --limit 500 --json number,state 2>/dev/null
```

For each closed GitHub issue, find the matching local story by `github_issue_number` using `find_issue_by_gh_number(number)`.

If the local issue's status is not `done` or `abandoned`, close it:

```python
new_path = close_issue_file(path, fm, body)
# File is now at .sweetclaude/product/backlog/done/<ID>-<slug>.md
```

**Guard:** `.sweetclaude/product/roadmap/` is explicitly out of scope. The `all_backlog_issue_files()` function above silently skips any file under that directory if it exists.

---

## Pass 2 — Local done → close on GitHub

Enumerate all issue files with `status: done` or `status: abandoned` that have a `github_issue_number` field:

```python
done_stories = []
for p in all_backlog_issue_files():
    fm, body = read_issue_file(p)
    if fm.get('status') in ('done', 'abandoned') and fm.get('github_issue_number'):
        done_stories.append((p, fm))
```

For each such issue, check if the GitHub issue is still open:

```bash
gh issue view <github_issue_number> --json state 2>/dev/null
```

If GitHub state is `open`, close it:

```bash
gh issue close <github_issue_number> 2>/dev/null && echo "closed"
```

---

## Report

```
GitHub Issues sync complete
  Local closed from GitHub: {N}
  GitHub issues closed from local: {N}
  No action needed: {N}
```

If any `gh issue close` fails (e.g., permissions): note the ID and continue. List all failures at the end. Do not stop on individual failures.

---

## Rules

- Only syncs `.sweetclaude/product/backlog/` issue files. Files under `.sweetclaude/product/roadmap/` (Phase 2) are silently ignored.
- Closing a local issue via sync moves it to `done/` exactly as `project-issues close` does.
- Import is one-way only (Pass 1 direction for new issues — handled by `project-gh-import-issues`).
