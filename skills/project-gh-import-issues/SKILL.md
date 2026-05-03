---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:project-gh-import-issues
description: "Import open GitHub Issues into the local issue store as I-NNN artifacts. Idempotent — issues already imported by GitHub issue number are skipped."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
```

# GitHub Issues — Import

Pull open issues from GitHub into the local issue store as `I-NNN` artifacts. Idempotent — issues already imported by GitHub number are skipped. Arguments: `$ARGUMENTS`

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

1. Check whether a local issue already has `github_issue_number` matching:
   ```bash
   source ~/.claude/hooks/sweetclaude/sc-artifact.sh
   sc_artifact_query issue github_issue_number=<number>
   ```

2. If a match exists: skip. Import is one-way — do not overwrite local edits.

3. If no match: map fields and create:
   ```bash
   sc_artifact_create issue '{
     "title": "<title>",
     "type": "story",
     "description": "<body truncated to 500 chars>",
     "priority": "soonish",
     "effort": "m",
     "status": "backlog",
     "source": "github",
     "github_issue_number": <number>,
     "github_url": "<url>"
   }'
   ```

   Labels → effort mapping (applied if label present, otherwise default `m`):

   | GitHub label | effort |
   |---|---|
   | `size:xs` or `effort:xs` | xs |
   | `size:s` or `effort:s` | s |
   | `size:m` or `effort:m` | m |
   | `size:l` or `effort:l` | l |
   | `size:xl` or `effort:xl` | xl |

After processing all issues, report:

```
GitHub Issues import complete
  Imported: {N} new issues
  Skipped:  {N} already present
  Open on GitHub: {N} total
```

If N > 20 imported: "That's a large import. Consider running `/sweetclaude:project-backlog-triage` to groom priorities before the next sprint."
