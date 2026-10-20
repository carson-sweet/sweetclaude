---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Manage the product roadmap — feature delivery targets, releases, and priority stack."
---


!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
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
| `view <MS-NNN>` | → **View** single item |
| `new` | → **Create** roadmap item |
| `activate <MS-NNN>` | → **Activate** — kick off the correct downstream workflow |
| `defer <MS-NNN>` | → **Defer** item |
| `complete <MS-NNN>` | → **Mark** complete |
| `cancel <MS-NNN>` | → **Cancel** item |
| `release new` | → **Create** a release |
| `release view <MS-NNN>` | → **View** release and its items |

---

## View (full stack)

Use output from shell block above.

Present roadmap items sorted by priority (force-ranked integer, 1 = top), grouped by status:

```
Roadmap — {N} items
══════════════════════════════════════════════════════════════

IN PROGRESS
  #1  MS-001  major_feature   Auth SSO support            MS-002
  #3  MS-005  enhancement     Bulk export                 —

PLANNED
  #2  MS-002  minor_feature   Webhook integrations        MS-002
  #4  MS-003  enhancement     Dark mode                   —
  #5  MS-004  sunset          Legacy API v1               MS-003

IDEAS
  #6  MS-006  major_feature   Mobile app                  —
```

After the stack: `{N} items  ({in_progress} active, {planned} planned, {idea} ideas)`

If `release` list is non-empty, group planned/active items by release under the main stack:
```
Releases
  MS-002  v2.1.0  target: 2026-06-01  MS-001, MS-002
  MS-003  v2.2.0  target: 2026-07-01  MS-004
```

---

## View (single item)

```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_read <MS-NNN>
```

Present:

```
MS-NNN — Auth SSO support
─────────────────────────────────────────
Type:      major_feature    Priority:  1
Status:    in_progress      Release:   MS-002

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
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_query epic roadmap_item_id=<MS-NNN>
```

Load direct issues (no epic):

```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_query issue roadmap_item_id=<MS-NNN> epic_id=
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
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_list release
```

"Does this belong to a release? List the ID or say none."

6. **Priority** — Load current items sorted by priority. Show the stack and ask: "Where does this sit in the priority order? Give a number (1 = highest) or say 'bottom'."

If the user inserts at an existing priority, shift all items at that position and below down by 1:

```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_list roadmap_item
```

Update each displaced item: `sc_artifact_write <MS-NNN> '{"priority": <new_number>}'`

Then create:

```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_create roadmap_item '{
  "title": "<title>",
  "type": "<type>",
  "description": "<description>",
  "rationale": "<rationale>",
  "release_id": "<MS-NNN or null>",
  "priority": <N>,
  "status": "planned"
}'
```

Confirm: `Created MS-NNN at priority #{N} — {title}`

---

## Activate

Activating a roadmap item kicks off the downstream workflow appropriate for its type.

```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_read <MS-NNN>
```

**Workflow routing by type:**

| Type | Downstream action |
|---|---|
| `major_feature` | "This kicks off a full feature workflow: discovery → design → plan → implement → verify → ship. Tell me to start discovery, or create epics and issues directly if discovery is done." |
| `minor_feature` | "This is a smaller feature — design → plan → implement. Create issues directly or run `/sweetclaude:build project-epics new` to group them." |
| `enhancement` | "Enhancement workflow: scope the change, create issues, implement. Run `project-issues new` to start." |
| `sunset` | "Sunset workflow: assess consumer impact, communicate deprecation, implement removal. Ask me to start an API deprecation workflow." |

Set status to `in_progress`:

```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_write <MS-NNN> '{"status": "in_progress"}'
```

Confirm: `MS-NNN activated — {workflow guidance}`

---

## Defer / Complete / Cancel

**Defer:**
```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_write <MS-NNN> '{"status": "deferred"}'
```

**Complete:**
```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_write <MS-NNN> '{"status": "complete"}'
```

Check if this item's release has all items complete:

```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_query roadmap_item release_id=<MS-NNN>
```

If all complete: "All items in MS-NNN are complete. Run `product-roadmap release view MS-NNN` to ship the release."

**Cancel:**
```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_write <MS-NNN> '{"status": "cancelled"}'
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
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_query milestone status=pending
```

List pending milestones. Accept MS-NNN or "none."

```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_create release '{
  "title": "<title>",
  "version": "<version or null>",
  "target_date": "<date or null>",
  "milestone_id": "<MS-NNN or null>",
  "status": "planned"
}'
```

Confirm: `Created MS-NNN — {title}`

---

## Release view

```bash
source "${CLAUDE_PLUGIN_ROOT}/hooks/sc-artifact.sh"
sc_artifact_read <MS-NNN>
sc_artifact_query roadmap_item release_id=<MS-NNN>
```

Present:

```
MS-NNN — v2.1.0
─────────────────────────────────────────
Status:       planned
Target date:  2026-06-01
Milestone:    MS-002

Items (3)
  MS-001  in_progress  #1  Auth SSO support
  MS-002  planned      #2  Webhook integrations
  MS-003  complete     #4  Dark mode
```

Progress: `{complete} / {total} items done`

---

## Rules

- Priority is a force-ranked integer. No two items should share the same number. Enforce this on create and restack.
- Chores, bugs, and spikes do not belong on the roadmap — they are issues in the backlog. If a user tries to add one, say: "Bugs and chores are tracked as issues, not roadmap items. Run `project-issues new` instead."
- A roadmap item with `status: in_progress` should have at least one epic or issue — surface a warning if it has none after 24 hours.
- Activating a roadmap item does not create issues automatically — it routes to the appropriate workflow.
