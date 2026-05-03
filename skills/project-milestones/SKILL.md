---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:project-milestones
description: "Manage milestones — binary business goals. Create, view, mark achieved or missed."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_list milestone
```

# Project Milestones

Milestones are binary business goals — they happened or they didn't. Not feature delivery targets (those are roadmap items). Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `list` | → **List** all milestones |
| `view <MS-NNN>` | → **View** milestone detail |
| `new` | → **Create** milestone |
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

After list: `{N} milestones  ({achieved} achieved, {pending} pending, {missed} missed)`

If no milestones: "No milestones yet. Run `project-milestones new` to define a business goal."

---

## View

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
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
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_query roadmap_item status=in_progress,planned
```

Filter for any that might contribute (look for release_id matching the milestone's release_id, or surface all active ones as candidates). List them as "Contributing work:" or note "No roadmap items linked."

---

## New

Ask one question at a time:

1. **Title** — "What's the milestone? One line."
2. **Criteria** — "What's the binary condition? Complete the sentence: 'This happened when...'"

   Challenge if vague: the criteria must be evaluable as true/false after the fact. If the user says "when users like it," push back: "That's not binary. What specific observable event would you point to?"

3. **Description** — "Context and motivation? (optional)"
4. **Release** (optional) — "Is this milestone triggered by a release?":

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_list release
```

List releases. Accept a REL-NNN or "none."

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
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
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_read <MS-NNN>
```

Confirm the criteria: "Criteria: '{criteria}' — confirmed met?"

On confirmation:

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_write <MS-NNN> '{"status": "achieved", "achieved_at": "<today>"}'
```

Confirm: `MS-NNN achieved — {title}`

If any other milestones are `pending`, surface them: "Next pending: {MS-NNN} — {title}"

---

## Missed

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_write <MS-NNN> '{"status": "missed"}'
```

Confirm: `MS-NNN marked missed — {title}`

Ask: "Want to create a new milestone with revised criteria, or leave it as missed for the record?"

---

## Rules

- Milestone criteria must be binary — true or false after the fact. Challenge vague criteria at creation time.
- Milestones are business goals, not feature delivery targets. If a user tries to create a milestone that sounds like "ship feature X," suggest a roadmap item instead: "That sounds like a delivery target — would a roadmap item fit better? Milestones are for business outcomes."
- Never delete a missed milestone — the history matters.
- `achieved_at` is always set to today's date when marking achieved, not a future date.
