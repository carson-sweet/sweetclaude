---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "View and manage the unscheduled issue backlog."
---

## MODE CHECK

Read `mode` from pre-loaded session state.

If `mode` is `shape_up`, output and stop:

> "This skill is not active in **Shape Up** mode.
>
> Shape Up has no backlog by design. New work enters through pitches: describe the problem and proposed solution, get it approved at the betting table, then create issues from the approved pitch.
>
> Write a pitch: `/sweetclaude:project-issues pitch`"

All other modes: proceed normally.

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
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

\033[1;34mNEXT\033[0m ({n})
  I-NNN  story  xs  Title of issue

\033[1;34mSOONER\033[0m ({n})
  I-NNN  story  m   Title of issue
  I-NNN  bug    s   Title of issue

\033[1;34mSOON\033[0m ({n})
  ...

\033[1;34mLATER\033[0m ({n})
  ...

\033[1;34mSOMEDAY\033[0m ({n})
  ...

\033[1;34mUNESTIMATED\033[0m ({n} — no priority or effort set)
  I-NNN  story  —   Title of issue
```

After the list, surface any of these conditions if present:

- **Unestimated count ≥ 10:** "Run `/sweetclaude:project-backlog-triage` — {N} issues have no effort or priority estimate."
- **Any inferred issues (source=inferred):** "{N} Flow-mode inferred issues need review. Run `project-backlog review-inferred`."
- **No active sprint:**

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query sprint status=active
```

If no active sprint: "No active sprint. Run `/sweetclaude:project-sprints new` to plan one."

---

## Promote

Move issue `<ID>` into sprint `<SP-NNN>`.

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_read <ID>
sc_artifact_read <SP-NNN>
```

Verify:
- Issue status is `backlog` or `ready`. If `done` or `cancelled`, say: "Can't promote a {status} issue."
- Sprint status is `planned` or `active`. If `complete` or `cancelled`, say: "Can't promote into a {status} sprint."

If both valid:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <ID> '{"sprint_id": "<SP-NNN>", "status": "ready"}'
```

Then append to sprint_history. Read current sprint_history, add entry:
`{sprint_id: <SP-NNN>, added_date: <today>, removed_date: null, outcome: null}`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <ID> '{"sprint_history": "<updated sprint_history string>"}'
```

Confirm: `Promoted I-NNN → SP-NNN`

---

## Defer

Set issue status to `deferred`. This hides it from the default backlog view without cancelling it.

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <ID> '{"status": "deferred"}'
```

Confirm: `Deferred <ID> — removed from active backlog`

---

## Review inferred

Load all inferred issues:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
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
