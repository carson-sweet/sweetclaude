---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Manage epics — optional goal lenses that group stories by functional area."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:project-epics" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
```

# Project Epics

## MODE CHECK

Read `mode` from pre-loaded session state.

- **Agile:** Epics are first-class. Proceed normally.
- **Flow, Kanban, Shape Up:** Epics are available but not surfaced by default. If the user explicitly invoked this skill, proceed with a note:
  > "Epics are optional in **{mode}** mode — useful for grouping related issues, but not required."

This skill is never blocked, only unsurfaced in non-Agile routing.

---

Epics are optional goal lenses — classification attributes, not delivery containers. An epic tracks progress toward a named goal that may span multiple sprints. Stories don't "pass through" an epic; they carry an `epic_id` as metadata. The work hierarchy is Milestone → Sprint → Story; epics are an orthogonal view on that data. Arguments: `$ARGUMENTS`

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
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
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
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
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
2. **Goal** — "Complete this sentence: 'When these stories are complete, [user outcome] becomes possible.'"
3. **Roadmap item** (optional) — Load roadmap items first:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_list roadmap_item
```

"Does this epic belong to a roadmap item? List the ID, or say none."

4. **Issues** — "Which existing issues should be grouped under this epic?" Load backlog and in-progress issues without an epic:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query issue epic_id=
```

Present them. Accept a list of IDs or "none" to start empty.

Create the epic:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_create epic '{
  "title": "<title>",
  "goal": "<goal>",
  "roadmap_item_id": "<RM-NNN or null>",
  "status": "active"
}'
```

For each issue the user assigned, update it:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <issue_id> '{"epic_id": "<new_epic_id>"}'
```

Confirm: `Created EP-NNN — {N} issues assigned`

---

## Close

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_read <EP-NNN>
sc_artifact_query issue epic_id=<EP-NNN>
```

Check for incomplete issues (status not `done` or `cancelled`). If any:
"EP-NNN has {N} incomplete issues: {list}. Close them first, or confirm you want to close the epic anyway."

Wait for confirmation, then:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <EP-NNN> '{"status": "complete"}'
```

Confirm: `EP-NNN closed — {title}`

---

## Cancel

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <EP-NNN> '{"status": "cancelled"}'
```

Issues are NOT cancelled — they remain in the backlog without an epic.

Confirm: `EP-NNN cancelled — {N} issues returned to backlog (epic_id cleared)`

Update all issues that had this epic:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query issue epic_id=<EP-NNN>
```

For each: `sc_artifact_write <issue_id> '{"epic_id": null}'`

---

## Rules

- Epics are optional. Never require them. If a user asks to skip epics, that's valid.
- Very large epics (20+ issues, 4+ sprints) often lose coherence as a goal lens. If an epic grows past 20 stories, surface: "EP-NNN has {N} stories across multiple milestones. Consider whether this is one goal or several."
- Issue membership is exclusive — one issue, one epic. If assigning an issue already in another epic, say: "I-NNN is in EP-NNN. Remove it from there first?"
- Closing an epic does not close its issues.
- Cancelling an epic does not cancel its issues.
