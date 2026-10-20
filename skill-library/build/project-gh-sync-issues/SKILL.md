---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Bidirectional status sync between local issue files and GitHub Issues."
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
    fm['updated'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
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

def close_issue_file(path):
    """Close via status CLI — handles status, closed_date, file move, audit log."""
    import json, subprocess
    import os
    fm, _body = read_issue_file(path)
    issue_id = fm.get('id') or path.stem
    gh_number = fm.get('github_issue_number')
    receipt_result = subprocess.run([
        'python3', os.path.expanduser('${CLAUDE_PLUGIN_ROOT}/scripts/evidence.py'), 'write',
        '--project-dir', '.',
        '--subject-id', issue_id,
        '--receipt-type', 'external-close',
        '--check', 'github-closed-state',
        '--status', 'pass',
        '--command', f'gh issue view {gh_number} --json state',
        '--summary', f'GitHub issue {gh_number} is closed'
    ], capture_output=True, text=True, check=True)
    receipt = json.loads(receipt_result.stdout)['receipt']
    subprocess.run(['python3', os.path.expanduser('${CLAUDE_PLUGIN_ROOT}/scripts/status.py'), 'set-terminal',
        '--file', str(path), '--status', 'done',
        '--actor', 'project-gh-sync-issues', '--project-dir', '.',
        '--evidence-receipt', receipt])
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
close_issue_file(path)
# status.py handles: status=done, closed_date, file move to done/, audit log
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
