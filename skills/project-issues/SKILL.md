---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Manage project issues — list, view, create, update, and close."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"

# Ensure index exists — reindex silently if missing
INDEX="${SC_STATE_BASE}/project-index.json"
if [ ! -f "$INDEX" ]; then
  python3 "${_sc_hooks}/sc-artifact-impl.py" reindex \
    "$SC_PROJECT_ROOT" "$SC_PRODUCT_BASE" "$SC_STATE_BASE" > /dev/null 2>&1
fi
```

# Project Issues

Manage project issues. Arguments: `$ARGUMENTS`

---

## MODE CHECK

Read `mode` from pre-loaded session state.

### Shape Up (shape_up) — pitch source enforcement

If `mode` is `shape_up` AND operation is `create` (not `pitch`, `list`, or `update`):

Ask: "Is this issue derived from an approved pitch?"

- **Yes** → Ask for pitch ID (e.g., `PITCH-001`). Link it by including `pitch_id: {PITCH-XXX}` in the artifact. Proceed with create.
- **No / I don't have a pitch** → Output and stop:
  > "In Shape Up mode, all issues must come from an approved pitch. The betting table has already decided what's worth building — issues outside approved pitches expand scope without an appetite trade-off.
  >
  > Write a pitch first: `/sweetclaude:project-issues pitch`"

All other modes: proceed with standard create flow. No pitch source required.

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

---

## List

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_list issue
```

Present as a compact table. Sort by: done/cancelled last, then by priority order (next → sooner → soon → later → someday), then by ID.

Priority sort order: next=1, sooner=2, soon=3, later=4, someday=5, null=6.

```
ID       Type    Status      Pri       Eff  Title
──────────────────────────────────────────────────────────────────
I-001    spike   done        later     m    Agentic Skills spike
I-025    story   backlog     soon      m    CLI UX Improvements
...
```

After the table: `{N} issues  ({done} done, {backlog} backlog, {in_progress} in progress)`

---

## Backlog

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query issue sprint_id= status=backlog
```

Present same table format as List, sorted by priority. Add header:
`Backlog — {N} unscheduled issues`

After table: suggest `project-sprints` to schedule issues into a sprint, or `project-backlog-triage` if more than 10 issues have no effort estimate.

---

## View

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_read <ID>
```

Replace `<ID>` with the ID from `$ARGUMENTS` (e.g. `I-025`).

If the result is `{}`, say: "Issue `<ID>` not found."

Otherwise present as:

```
I-025 — CLI UX Improvements
─────────────────────────────────────────
Type:      story          Status:   backlog
Priority:  soon           Effort:   m
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
5. **Priority** — "next / sooner / soon / later / someday?" (default: soon)
6. **Effort** — "xs / s / m / l / xl / xxl?" (default: m)
7. **Epic** — "Does this belong to an epic?" List available epics first, or say none.

Once all answers collected:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
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
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
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
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <ID> '<json of only changed fields>'
```

Confirm: `Updated <ID> — <list of changed fields>`

If the user moves an issue into a sprint, also append to `sprint_history`:
`{sprint_id: <SP-NNN>, added_date: <today>, outcome: null}`

---

## Close

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
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
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <ID> '{"status": "backlog", "sprint_id": null}'
```

Confirm: `Reopened <ID> — returned to backlog`

---

## Rules

- Never delete an issue — use `close` (status=done) or `sc_artifact_delete` (status=cancelled) for items that won't be done.
- Sprint assignment always goes through `update`, not direct write, so sprint_history is maintained.
- If `$ARGUMENTS` contains an ID that doesn't start with `I-`, say: "That doesn't look like an issue ID. Issue IDs start with `I-` (e.g. `I-025`)."
- If the index is stale (query returns 0 results when files exist), run reindex silently before presenting results.
