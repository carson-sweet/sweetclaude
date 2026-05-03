---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:project-epics
description: "Manage epics — optional planning containers for 4–12 related issues. Create, view, list, and close."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
```

# Project Epics

Epics are optional grouping containers. Not every project needs them — add them when a cluster of issues shares a clear outcome that's worth naming. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `list` | → **List** all active epics with issue counts |
| `view <EP-NNN>` | → **View** epic with full issue list |
| `new` | → **Create** new epic |
| `close <EP-NNN>` | → **Close** epic (status → complete) |
| `cancel <EP-NNN>` | → **Cancel** epic |

---

## List

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_list epic
sc_artifact_list issue
```

For each epic, count how many issues have `epic_id` matching it, broken down by status.

```
EP-NNN  active    3/7 done  Auth refactor
EP-NNN  active    0/4 done  Onboarding flow
EP-NNN  complete  8/8 done  Initial release
```

After list: `{N} epics  ({active} active, {complete} complete)`

If no epics: "No epics. Run `project-epics new` to create one, or skip epics entirely — they're optional."

---

## View

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_read <EP-NNN>
sc_artifact_query issue epic_id=<EP-NNN>
```

Present:

```
EP-NNN — Auth refactor
─────────────────────────────────────────
Status:       active
Roadmap item: RM-001
Goal:         When this ships, users can log in with SSO.

Issues (7)
  ready        I-001  s   Login form validation
  in_progress  I-002  m   OAuth callback handler
  done         I-003  xs  Remove legacy session code
  backlog      I-004  l   Audit log for auth events
  ...

Progress: 3 / 7 done
```

If all issues are done but epic is still `active`: "All issues complete. Run `project-epics close EP-NNN` to mark the epic done."

---

## New

Ask one question at a time:

1. **Title** — "What's the epic? One line."
2. **Goal** — "Complete this sentence: 'When this ships, [user outcome] becomes possible.'"
3. **Roadmap item** (optional) — Load roadmap items first:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_list roadmap_item
```

"Does this epic belong to a roadmap item? List the ID, or say none."

4. **Issues** — "Which existing issues should be grouped under this epic?" Load backlog and in-progress issues without an epic:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_query issue epic_id=
```

Present them. Accept a list of IDs or "none" to start empty.

Create the epic:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_create epic '{
  "title": "<title>",
  "goal": "<goal>",
  "roadmap_item_id": "<RM-NNN or null>",
  "status": "active"
}'
```

For each issue the user assigned, update it:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_write <issue_id> '{"epic_id": "<new_epic_id>"}'
```

Confirm: `Created EP-NNN — {N} issues assigned`

---

## Close

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_read <EP-NNN>
sc_artifact_query issue epic_id=<EP-NNN>
```

Check for incomplete issues (status not `done` or `cancelled`). If any:
"EP-NNN has {N} incomplete issues: {list}. Close them first, or confirm you want to close the epic anyway."

Wait for confirmation, then:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_write <EP-NNN> '{"status": "complete"}'
```

Confirm: `EP-NNN closed — {title}`

---

## Cancel

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_write <EP-NNN> '{"status": "cancelled"}'
```

Issues are NOT cancelled — they remain in the backlog without an epic.

Confirm: `EP-NNN cancelled — {N} issues returned to backlog (epic_id cleared)`

Update all issues that had this epic:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_query issue epic_id=<EP-NNN>
```

For each: `sc_artifact_write <issue_id> '{"epic_id": null}'`

---

## Rules

- Epics are optional. Never require them. If a user asks to skip epics, that's valid.
- Maximum meaningful size is 4–12 issues. If a user tries to create an epic with 13+ issues, surface: "That's a large epic ({N} issues). Consider splitting it into two focused epics."
- Issue membership is exclusive — one issue, one epic. If assigning an issue already in another epic, say: "I-NNN is in EP-NNN. Remove it from there first?"
- Closing an epic does not close its issues.
- Cancelling an epic does not cancel its issues.
