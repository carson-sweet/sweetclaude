---
spdx-license: AGPL-3.0-or-later
name: product-roadmap
user-invocable: true
description: "Manage the product roadmap — feature delivery targets, releases, and priority stack. Routes to the correct workflow on activation."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_list roadmap_item
sc_artifact_list release
```

# Project Roadmap

The roadmap tracks what gets built and when — major features, enhancements, and sunsets. Priority-stacked, type-aware, release-grouped. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `list` | → **View** full roadmap stack |
| `view <RM-NNN>` | → **View** single item |
| `new` | → **Create** roadmap item |
| `activate <RM-NNN>` | → **Activate** — kick off the correct downstream workflow |
| `defer <RM-NNN>` | → **Defer** item |
| `complete <RM-NNN>` | → **Mark** complete |
| `cancel <RM-NNN>` | → **Cancel** item |
| `release new` | → **Create** a release |
| `release view <REL-NNN>` | → **View** release and its items |

---

## View (full stack)

Use output from shell block above.

Present roadmap items sorted by priority (force-ranked integer, 1 = top), grouped by status:

```
Roadmap — {N} items
══════════════════════════════════════════════════════════════

IN PROGRESS
  #1  RM-001  major_feature   Auth SSO support            REL-002
  #3  RM-005  enhancement     Bulk export                 —

PLANNED
  #2  RM-002  minor_feature   Webhook integrations        REL-002
  #4  RM-003  enhancement     Dark mode                   —
  #5  RM-004  sunset          Legacy API v1               REL-003

IDEAS
  #6  RM-006  major_feature   Mobile app                  —
```

After the stack: `{N} items  ({in_progress} active, {planned} planned, {idea} ideas)`

If `release` list is non-empty, group planned/active items by release under the main stack:
```
Releases
  REL-002  v2.1.0  target: 2026-06-01  RM-001, RM-002
  REL-003  v2.2.0  target: 2026-07-01  RM-004
```

---

## View (single item)

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_read <RM-NNN>
```

Present:

```
RM-NNN — Auth SSO support
─────────────────────────────────────────
Type:      major_feature    Priority:  1
Status:    in_progress      Release:   REL-002

Description
  ...

Rationale
  ...

Epics
  EP-001  active   3/7 done  SSO backend
  EP-002  active   0/3 done  SSO UI
```

Load contributing epics:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query epic roadmap_item_id=<RM-NNN>
```

Load direct issues (no epic):

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query issue roadmap_item_id=<RM-NNN> epic_id=
```

---

## New

Ask one question at a time:

1. **Title** — "What's going on the roadmap?"
2. **Type** — "What kind of item?
   - `major_feature` — significant new capability
   - `minor_feature` — smaller new capability
   - `enhancement` — improving something that exists
   - `sunset` — removing or deprecating something"
3. **Description** — "What is it in two to three sentences?"
4. **Rationale** — "Why does this belong on the roadmap now, at this priority?"
5. **Release** (optional):

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_list release
```

"Does this belong to a release? List the ID or say none."

6. **Priority** — Load current items sorted by priority. Show the stack and ask: "Where does this sit in the priority order? Give a number (1 = highest) or say 'bottom'."

If the user inserts at an existing priority, shift all items at that position and below down by 1:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_list roadmap_item
```

Update each displaced item: `sc_artifact_write <RM-NNN> '{"priority": <new_number>}'`

Then create:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_create roadmap_item '{
  "title": "<title>",
  "type": "<type>",
  "description": "<description>",
  "rationale": "<rationale>",
  "release_id": "<REL-NNN or null>",
  "priority": <N>,
  "status": "planned"
}'
```

Confirm: `Created RM-NNN at priority #{N} — {title}`

---

## Activate

Activating a roadmap item kicks off the downstream workflow appropriate for its type.

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_read <RM-NNN>
```

**Workflow routing by type:**

| Type | Downstream action |
|---|---|
| `major_feature` | "This kicks off a full feature workflow: discovery → design → plan → implement → verify → ship. Tell me to start discovery, or create epics and issues directly if discovery is done." |
| `minor_feature` | "This is a smaller feature — design → plan → implement. Create issues directly or run `/sweetclaude:project-epics new` to group them." |
| `enhancement` | "Enhancement workflow: scope the change, create issues, implement. Run `project-issues new` to start." |
| `sunset` | "Sunset workflow: assess consumer impact, communicate deprecation, implement removal. Ask me to start an API deprecation workflow." |

Set status to `in_progress`:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <RM-NNN> '{"status": "in_progress"}'
```

Confirm: `RM-NNN activated — {workflow guidance}`

---

## Defer / Complete / Cancel

**Defer:**
```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <RM-NNN> '{"status": "deferred"}'
```

**Complete:**
```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <RM-NNN> '{"status": "complete"}'
```

Check if this item's release has all items complete:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query roadmap_item release_id=<REL-NNN>
```

If all complete: "All items in REL-NNN are complete. Run `product-roadmap release view REL-NNN` to ship the release."

**Cancel:**
```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <RM-NNN> '{"status": "cancelled"}'
```

Ask: "Any contributing epics or issues to cancel as well, or leave them in the backlog?"

---

## Release new

Ask:

1. **Title** — version string or name (e.g. "v2.1.0" or "Spring 2026")
2. **Version** — semver if applicable, or "none"
3. **Target date** — "YYYY-MM-DD or 'when it's ready'"
4. **Milestone** — "Does shipping this release achieve a milestone?":

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query milestone status=pending
```

List pending milestones. Accept MS-NNN or "none."

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_create release '{
  "title": "<title>",
  "version": "<version or null>",
  "target_date": "<date or null>",
  "milestone_id": "<MS-NNN or null>",
  "status": "planned"
}'
```

Confirm: `Created REL-NNN — {title}`

---

## Release view

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_read <REL-NNN>
sc_artifact_query roadmap_item release_id=<REL-NNN>
```

Present:

```
REL-NNN — v2.1.0
─────────────────────────────────────────
Status:       planned
Target date:  2026-06-01
Milestone:    MS-002

Items (3)
  RM-001  in_progress  #1  Auth SSO support
  RM-002  planned      #2  Webhook integrations
  RM-003  complete     #4  Dark mode
```

Progress: `{complete} / {total} items done`

---

## Rules

- Priority is a force-ranked integer. No two items should share the same number. Enforce this on create and restack.
- Chores, bugs, and spikes do not belong on the roadmap — they are issues in the backlog. If a user tries to add one, say: "Bugs and chores are tracked as issues, not roadmap items. Run `project-issues new` instead."
- A roadmap item with `status: in_progress` should have at least one epic or issue — surface a warning if it has none after 24 hours.
- Activating a roadmap item does not create issues automatically — it routes to the appropriate workflow.
