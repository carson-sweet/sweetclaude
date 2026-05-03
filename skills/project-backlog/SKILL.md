---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:project-backlog
description: "View and manage the unscheduled issue backlog. Promotes issues into sprints. Surfaces triage needs."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_query issue sprint_id= status=backlog
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
| `review-inferred` | → **Review** Flow-mode inferred issues |

---

## View (default)

Use the query output from the shell block above.

Present backlog grouped by priority bucket:

```
Backlog — {N} unscheduled issues
══════════════════════════════════════════════════════════════

NOW ({n})
  I-NNN  story  xs  Title of issue

SOONER ({n})
  I-NNN  story  m   Title of issue
  I-NNN  bug    s   Title of issue

SOONISH ({n})
  ...

LATER ({n})
  ...

SOMEDAY ({n})
  ...

UNESTIMATED ({n} — no priority or effort set)
  I-NNN  story  —   Title of issue
```

After the list, surface any of these conditions if present:

- **Unestimated count ≥ 10:** "Run `/sweetclaude:project-backlog-triage` — {N} issues have no effort or priority estimate."
- **Any inferred issues (source=inferred):** "{N} Flow-mode inferred issues need review. Run `project-backlog review-inferred`."
- **No active sprint:**

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_query sprint status=active
```

If no active sprint: "No active sprint. Run `/sweetclaude:project-sprints new` to plan one."

---

## Promote

Move issue `<ID>` into sprint `<SP-NNN>`.

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_read <ID>
sc_artifact_read <SP-NNN>
```

Verify:
- Issue status is `backlog` or `ready`. If `done` or `cancelled`, say: "Can't promote a {status} issue."
- Sprint status is `planned` or `active`. If `complete` or `cancelled`, say: "Can't promote into a {status} sprint."

If both valid:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_write <ID> '{"sprint_id": "<SP-NNN>", "status": "ready"}'
```

Then append to sprint_history. Read current sprint_history, add entry:
`{sprint_id: <SP-NNN>, added_date: <today>, removed_date: null, outcome: null}`

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_write <ID> '{"sprint_history": "<updated sprint_history string>"}'
```

Confirm: `Promoted I-NNN → SP-NNN`

---

## Defer

Set issue status to `deferred`. This hides it from the default backlog view without cancelling it.

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_write <ID> '{"status": "deferred"}'
```

Confirm: `Deferred <ID> — removed from active backlog`

---

## Review inferred

Load all inferred issues:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_query issue source=inferred status=backlog
```

If none: "No inferred issues to review."

Otherwise, present them one at a time:

```
Inferred issue {n} of {total}:

  {ID} — {title}
  Evidence: {evidence}
  Inferred type: {type}

  Promote (keep as-is), Edit (change title/type), or Discard?
```

Wait for response per issue.
- **Promote:** `sc_artifact_write <ID> '{"source": "manual"}'` — confirm: "Kept as I-NNN"
- **Edit:** ask for new title and/or type, then write both fields + set source=manual
- **Discard:** `sc_artifact_delete <ID>` — confirm: "Discarded"

After all reviewed: "Reviewed {N} inferred issues: {kept} kept, {edited} edited, {discarded} discarded."

---

## Rules

- The backlog view never shows `done`, `cancelled`, or `deferred` issues — those are archived.
- Promoting into a sprint does not start the sprint. Sprint activation is done in `project-sprints`.
- An issue promoted into an active sprint gets status `ready`. An issue promoted into a planned sprint stays `ready`.
- Never auto-promote an entire backlog into a sprint — always promote individual issues deliberately.
