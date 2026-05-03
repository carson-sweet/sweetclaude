# Plan: GitHub Issues Sync for project-issues
**Status:** planned
**Date:** 2026-05-03
**Priority:** high — team adoption blocker (two sources of truth)

---

## Problem

`project-issues` creates I-NNN artifacts in `.sweetclaude/`. Teams already track issues in GitHub Issues. Without a sync path, adopting `project-issues` means maintaining two systems — and the PM will kill the rollout at the first duplicate.

---

## Scope

**In scope:**
- `project-issues import` — pull open GitHub Issues into I-NNN artifacts (one-directional, idempotent)
- `project-issues sync` — propagate status changes bidirectionally (closed I-NNN → close GH issue; closed GH issue → update I-NNN)

**Out of scope (v1):**
- Linear, Jira, or other PM tools
- Creating GH issues from I-NNN (use `gh issue create` manually)
- Syncing comments or attachments

**Prerequisite:** `gh` CLI installed and authenticated (`gh auth status`).

---

## Data Model Addition

Add two optional fields to the I-NNN artifact frontmatter:

```yaml
github_issue_number: 42
github_url: https://github.com/owner/repo/issues/42
```

No changes to `sc-artifact-impl.py` needed — these are stored as regular metadata fields. The adapter already handles arbitrary metadata.

---

## Implementation

### `project-issues import`

```bash
# Check gh available
command -v gh >/dev/null 2>&1 || { echo "gh CLI not found. Install from https://cli.github.com/"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh not authenticated. Run: gh auth login"; exit 1; }

# Detect repo
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)

# Pull all open issues
gh issue list --state open --json number,title,body,labels,assignees \
  --limit 500 --repo "$REPO"
```

For each GH issue returned:
1. Check if an I-NNN with `github_issue_number: <N>` already exists (query via index or grep). Skip if found.
2. Infer type from labels: `bug` label → `type: bug`; `enhancement` → `type: story`; else → `type: story`.
3. Create artifact:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_create issue '{
  "title": "<gh title>",
  "type": "<inferred type>",
  "status": "backlog",
  "description": "<gh body, first 500 chars>",
  "github_issue_number": <N>,
  "github_url": "https://github.com/<repo>/issues/<N>"
}'
```

Report at end: `Imported: N  Skipped (already imported): N`

### `project-issues sync`

Two passes:

**Pass 1 — GH closed → update local:**
```bash
# Get recently closed GH issues
gh issue list --state closed --json number,closedAt \
  --limit 100 --repo "$REPO"
```
For each closed GH issue: find matching I-NNN by `github_issue_number`, update to `status: done` if not already.

**Pass 2 — local closed → close GH:**
```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_query issue status=done
```
For each I-NNN with `status: done` and `github_issue_number` set: check GH issue state. If still open, close it:
```bash
gh issue close <github_issue_number> --repo "$REPO"
```

Report: `GH→local: N updated  Local→GH: N closed`

---

## SKILL.md Changes

Add two new routing rows to `project-issues/SKILL.md`:

```markdown
| `import` | → **Import** open GitHub Issues as I-NNN artifacts |
| `sync` | → **Sync** status between I-NNN artifacts and GitHub Issues |
```

Add `## Import` and `## Sync` sections following the pattern of existing operations.

---

## Edge Cases

| Case | Handling |
|---|---|
| GH issue has no body | Use title as description |
| Duplicate title (already exists as I-NNN without `github_issue_number`) | Import anyway, user deduplicates manually |
| GH issue closed before import | Skip (only import `--state open`) |
| `gh` rate limit hit | Fail with message: "GitHub API rate limited. Try again in X minutes." |
| No git remote | Fail with message: "No GitHub remote detected. `gh` requires a GitHub repo." |

---

## Files Changed

- `skills/project-issues/SKILL.md` — add import/sync routing and section bodies
- No sc-artifact-impl.py changes needed

## Sequencing

1. Add `import` first — lower risk, no writes to GH
2. Test import against a real repo (this repo)
3. Add `sync` Pass 1 (GH→local) — also read-only to GH
4. Add `sync` Pass 2 (local→GH) — writes to GH, test carefully
5. Sync to plugin cache
6. Commit

## Future

- `project-issues export` — create a new GH issue from an I-NNN that has no `github_issue_number`
- Linear and Jira adapters follow the same pattern (different API, same artifact fields)
