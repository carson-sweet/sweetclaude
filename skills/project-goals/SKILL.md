---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Manage project goals — binary business goals."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:project-goals" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_list milestone
```

# Project Goals

Goals are binary business goals — they happened or they didn't. Not feature delivery targets (those are roadmap items). Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `list` | → **List** all goals |
| `view <MS-NNN>` | → **View** goal detail |
| `new` | → **Create** goal |
| `achieved <MS-NNN>` | → **Mark** achieved |
| `missed <MS-NNN>` | → **Mark** missed |

---

## List

Use the list output from the shell block above.

```
MS-001  achieved  2026-04-15  Public Launch
MS-002  pending   —           First paying customer
MS-003  pending   —           100 active projects
```

After list: `{N} goals  ({achieved} achieved, {pending} pending, {missed} missed)`

If no goals: "No goals yet. Run `project-goals new` to define a business goal."

---

## View

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_read <MS-NNN>
```

Present:

```
MS-NNN — First paying customer
─────────────────────────────────────────
Status:    pending
Achieved:  —
Release:   REL-001

Criteria
  First paying customer has completed a transaction.

Description
  Context and motivation text.
```

Then load contributing roadmap items:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query roadmap_item status=in_progress,planned
```

Filter for any that might contribute (look for release_id matching the goal's release_id, or surface all active ones as candidates). List them as "Contributing work:" or note "No roadmap items linked."

---

## New

Ask one question at a time:

1. **Title** — "What's the goal? One line."
2. **Criteria** — "What's the binary condition? Complete the sentence: 'This happened when...'"

   Challenge if vague: the criteria must be evaluable as true/false after the fact. If the user says "when users like it," push back: "That's not binary. What specific observable event would you point to?"

3. **Description** — "Context and motivation? (optional)"
4. **Release** (optional) — "Is this goal triggered by a release?":

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_list release
```

List releases. Accept a REL-NNN or "none."

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_create milestone '{
  "title": "<title>",
  "criteria": "<criteria>",
  "description": "<description or null>",
  "release_id": "<REL-NNN or null>",
  "status": "pending"
}'
```

Confirm: `Created MS-NNN — {title}`

---

## Achieved

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_read <MS-NNN>
```

Confirm the criteria: "Criteria: '{criteria}' — confirmed met?"

On confirmation:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <MS-NNN> '{"status": "achieved", "achieved_at": "<today>"}'
```

Confirm: `MS-NNN achieved — {title}`

If any other goals are `pending`, surface them: "Next pending: {MS-NNN} — {title}"

---

## Missed

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <MS-NNN> '{"status": "missed"}'
```

Confirm: `MS-NNN marked missed — {title}`

Ask: "Want to create a new goal with revised criteria, or leave it as missed for the record?"

---

## Rules

- Goal criteria must be binary — true or false after the fact. Challenge vague criteria at creation time.
- Goals are business outcomes, not feature delivery targets. If a user tries to create a goal that sounds like "ship feature X," suggest a roadmap item instead: "That sounds like a delivery target — would a roadmap item fit better? Goals are for business outcomes."
- Never delete a missed goal — the history matters.
- `achieved_at` is always set to today's date when marking achieved, not a future date.
