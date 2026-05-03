---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:project-issues
description: "Manage project issues — list, view, create, update, and close. The primary interface for individual work items."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh

# Ensure index exists — reindex silently if missing
INDEX="${SC_STATE_BASE}/project-index.json"
if [ ! -f "$INDEX" ]; then
  python3 ~/.claude/hooks/sweetclaude/sc-artifact-impl.py reindex \
    "$SC_PROJECT_ROOT" "$SC_PRODUCT_BASE" "$SC_STATE_BASE" > /dev/null 2>&1
fi
```

# Project Issues

Manage project issues. Arguments: `$ARGUMENTS`

---

## Routing

Parse the first word of `$ARGUMENTS` to determine the operation.

| First word | Operation |
|---|---|
| (empty) | → **List** all non-cancelled issues |
| `list` | → **List** all non-cancelled issues |
| `backlog` | → **Backlog** (issues not yet in a sprint) |
| `view <ID>` | → **View** single issue |
| `new` | → **Create** new issue interactively |
| `update <ID>` | → **Update** existing issue |
| `close <ID>` | → **Close** issue (status → done) |
| `reopen <ID>` | → **Reopen** issue (status → backlog) |
| `import` | → **Import** open issues from GitHub (one-time or incremental) |
| `sync` | → **Sync** status between local issues and GitHub |

---

## List

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_list issue
```

Present as a compact table. Sort by: done/cancelled last, then by priority order (now → sooner → soonish → later → someday), then by ID.

Priority sort order: now=1, sooner=2, soonish=3, later=4, someday=5, null=6.

```
ID       Type    Status      Pri       Eff  Title
──────────────────────────────────────────────────────────────────
I-001    spike   done        later     m    Agentic Skills spike
I-025    story   backlog     soonish   m    CLI UX Improvements
...
```

After the table: `{N} issues  ({done} done, {backlog} backlog, {in_progress} in progress)`

---

## Backlog

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_query issue sprint_id= status=backlog
```

Present same table format as List, sorted by priority. Add header:
`Backlog — {N} unscheduled issues`

After table: suggest `project-sprints` to schedule issues into a sprint, or `project-backlog-triage` if more than 10 issues have no effort estimate.

---

## View

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_read <ID>
```

Replace `<ID>` with the ID from `$ARGUMENTS` (e.g. `I-025`).

If the result is `{}`, say: "Issue `<ID>` not found."

Otherwise present as:

```
I-025 — CLI UX Improvements
─────────────────────────────────────────
Type:      story          Status:   backlog
Priority:  soonish        Effort:   m
Epic:      (none)         Sprint:   (none)
Source:    manual

Description
  SweetClaude skill output is plain text. Improve the CLI experience...

Acceptance criteria
  (if present)

Sprint history
  (if present — list each sprint and outcome)
```

If the issue has `sprint_history` with 2+ `carried_over` entries, add a warning:
`⚠ Adrift: carried over {N} sprints without completion.`

---

## Create

Ask one question at a time. Do not present a form.

1. **Title** — "What's the issue? One line."
2. **Type** — "story / bug / chore / spike?" (default: story)
3. **Description** — For stories: "As a [who], they want [what] so that [why]?" For bugs: "Steps to reproduce?" For chores: "What needs to be done?" For spikes: "What question needs answering?"
4. **Acceptance criteria** (story/bug only) — "What conditions make this done? List them one per line, or say none."
5. **Priority** — "now / sooner / soonish / later / someday?" (default: soonish)
6. **Effort** — "xs / s / m / l / xl / xxl?" (default: m)
7. **Epic** — "Does this belong to an epic?" List available epics first, or say none.

Once all answers collected:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_create issue '{
  "title": "<title>",
  "type": "<type>",
  "description": "<description>",
  "acceptance_criteria": "<ac as JSON array or empty>",
  "priority": "<priority>",
  "effort": "<effort>",
  "epic_id": "<epic_id or null>",
  "status": "backlog",
  "source": "manual"
}'
```

Confirm: `Created <ID> — <title>`

---

## Update

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_read <ID>
```

Show the current values. Ask: "What would you like to change?" Accept natural language or field=value pairs.

Map the user's intent to fields:
- "move to sprint SP-003" → `sprint_id: SP-003`, `status: ready`
- "set priority to sooner" → `priority: sooner`
- "mark in progress" → `status: in_progress`
- "assign to epic EP-001" → `epic_id: EP-001`
- "remove from sprint" → `sprint_id: null`
- "add acceptance criteria" → append to `acceptance_criteria`

Then:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_write <ID> '<json of only changed fields>'
```

Confirm: `Updated <ID> — <list of changed fields>`

If the user moves an issue into a sprint, also append to `sprint_history`:
`{sprint_id: <SP-NNN>, added_date: <today>, outcome: null}`

---

## Close

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_write <ID> '{"status": "done"}'
```

If the issue has a sprint, append to its sprint_history:
`{sprint_id: <sprint_id>, removed_date: <today>, outcome: "completed"}`

Confirm: `Closed <ID> — <title>`

If the issue was the last open issue in an epic, surface:
`All issues in <EP-NNN> are now done. Run project-epics to close the epic.`

---

## Reopen

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_write <ID> '{"status": "backlog", "sprint_id": null}'
```

Confirm: `Reopened <ID> — returned to backlog`

---

## Import

Pull open issues from GitHub into the local issue store. Idempotent — issues already imported by GitHub number are skipped.

**Prerequisites check:**
```bash
gh auth status 2>/dev/null && echo "GH_OK" || echo "GH_NOT_AUTH"
git remote get-url origin 2>/dev/null || echo "NO_REMOTE"
```

If `GH_NOT_AUTH`: "GitHub CLI is not authenticated. Run `gh auth login` first."
If `NO_REMOTE`: "No git remote found. Import requires a GitHub remote."

**Fetch open issues:**
```bash
gh issue list --state open --limit 200 --json number,title,body,labels,state,url 2>/dev/null
```

For each GitHub issue:
1. Check whether an existing local issue has `github_issue_number` matching this issue's number:
   ```bash
   source ~/.claude/hooks/sweetclaude/sc-artifact.sh
   sc_artifact_query issue github_issue_number=<number>
   ```
2. If a match exists: skip (already imported). Do not update — import is one-way.
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
GitHub import complete
  Imported: {N} new issues
  Skipped:  {N} already present
  Total open on GitHub: {N}
```

If N > 20 imported: "That's a large import. Consider running `/sweetclaude:project-backlog-triage` to groom priorities before the next sprint."

---

## Sync

Bidirectional status sync between local issues and GitHub. Run anytime to keep the two in sync.

**Prerequisites check:** same as Import (gh auth + remote).

**Pass 1 — GitHub closed → update local**

```bash
gh issue list --state closed --limit 500 --json number,state 2>/dev/null
```

For each closed GitHub issue, find the matching local issue by `github_issue_number`. If local status is not `done` or `cancelled`, update it:
```bash
sc_artifact_write <ID> '{"status": "done"}'
```

**Pass 2 — Local done → close on GitHub**

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_query issue status=done
```

For each local issue with `status: done` and a `github_issue_number` field, check if the GitHub issue is still open:
```bash
gh issue view <github_issue_number> --json state 2>/dev/null
```

If GitHub state is `open`: close it:
```bash
gh issue close <github_issue_number> 2>/dev/null && echo "closed"
```

After both passes, report:
```
GitHub sync complete
  Local closed from GitHub: {N}
  GitHub issues closed from local: {N}
  No action needed: {N}
```

If any GitHub close fails (e.g., permissions): note the ID and continue. Report failures at the end.

---

## Rules

- Never delete an issue — use `close` (status=done) or `sc_artifact_delete` (status=cancelled) for items that won't be done.
- Sprint assignment always goes through `update`, not direct write, so sprint_history is maintained.
- If `$ARGUMENTS` contains an ID that doesn't start with `I-`, say: "That doesn't look like an issue ID. Issue IDs start with `I-` (e.g. `I-025`)."
- If the index is stale (query returns 0 results when files exist), run reindex silently before presenting results.
