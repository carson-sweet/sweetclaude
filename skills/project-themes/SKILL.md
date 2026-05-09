---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Manage themes — optional domain-grouping labels on stories."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
```

# Project Themes

Themes are optional domain-grouping labels — classification attributes on stories, not hierarchy nodes. The work hierarchy is Milestone → Sprint → Story; themes are an orthogonal navigation lens on that data, carrying no delivery commitment. A story can carry both an `epic_id` and a `theme_id` simultaneously. Arguments: `$ARGUMENTS`

**When to use themes:** When your project has 50+ issues, multiple services or major components, and the story inventory has become hard to navigate by epics alone.

**When not to use themes:** Small-to-medium projects where a handful of epics covers everything cleanly. Themes add no value below ~50 issues.

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `list` | → **List** all themes grouped by category |
| `view <TH-NNN>` | → **View** theme with its full issue list |
| `new` | → **Create** a new theme |
| `tag <TH-NNN>` | → **Tag** stories with a theme |
| `close <TH-NNN>` | → **Close** theme (status → complete) |

---

## List

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_list theme
sc_artifact_list issue
```

Group output by category. For each theme, count issues by status:

```
Feature Area
  TH-001  active    4/7 done  Stewardship Transfer        [vivarium]
  TH-002  active    0/3 done  Memory Sandbox               [laboratory]

Service
  TH-005  active    2/6 done  Vivarium Service
  TH-006  active    1/4 done  Platform Auth API

Infrastructure
  TH-009  active    0/5 done  Row-Level Security
  TH-010  active    0/3 done  Audit Logging
```

After list: `{N} themes  ({active} active, {complete} complete)  ·  {total_issues} stories tagged`

If no themes: "No themes yet. Run `project-themes new` to create one, or skip themes entirely — they're optional and most useful on projects with 50+ issues."

---

## View

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_read <TH-NNN>
sc_artifact_query issue theme_id=<TH-NNN>
```

Present:

```
TH-NNN — Stewardship Transfer
─────────────────────────────────────────
Category:  feature-area
Service:   vivarium
Status:    active

Issues (4)
  ready        I-012  m   Nominate a new steward
  backlog      I-013  s   Accept stewardship transfer
  backlog      I-014  m   Handle nomination expiry
  backlog      I-015  l   Concurrent transfer race condition

Progress: 0 / 4 done
```

If the theme has no stories: "No stories tagged with TH-NNN yet. Run `project-themes tag TH-NNN` to add some."

---

## New

Ask one question at a time:

1. **Title** — "What's the theme? One phrase — e.g. 'Stewardship Transfer', 'Row-Level Security', 'Platform Auth API'."

2. **Category** — present as a menu:
   - `feature-area` — stories implementing a specific product capability within a service
   - `service` — stories that implement or interact with a specific service boundary
   - `infrastructure` — cross-cutting stories that implement foundational constraints (RLS, audit logging, DB integrity)
   - `devops` — CI/CD, deployment, secret management, observability infrastructure

3. **Service** (optional) — "Which service does this theme belong to? Enter the service name, or leave blank for cross-cutting themes."

4. **Stories** (optional) — "Which existing stories should be tagged with this theme?" Load stories without a theme:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query issue theme_id=
```

Present them (filtered by service if one was specified). Accept a list of IDs or "none" to start empty.

Create the theme:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_create theme '{
  "title": "<title>",
  "category": "<category>",
  "service": "<service or null>",
  "status": "active"
}'
```

For each issue the user assigned, update it:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <issue_id> '{"theme_id": "<new_theme_id>"}'
```

Confirm: `Created TH-NNN — {N} stories tagged`

---

## Tag

Load the theme and currently untagged stories:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_read <TH-NNN>
sc_artifact_query issue theme_id=
```

Present stories without a theme. If the theme has a `service` field, filter to show same-service stories first, then others.

Accept a list of story IDs to tag. For each:

```bash
sc_artifact_write <issue_id> '{"theme_id": "<TH-NNN>"}'
```

Confirm: `{N} stories tagged with TH-NNN`

Note: a story can carry both a theme and an epic simultaneously. Tagging with a theme does not affect `epic_id`.

---

## Close

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query issue theme_id=<TH-NNN>
```

Count incomplete issues. If any:
"TH-NNN has {N} incomplete issues. Close them first, or confirm to close the theme anyway."

Wait for confirmation, then:

```bash
sc_artifact_write <TH-NNN> '{"status": "complete"}'
```

Confirm: `TH-NNN closed — {title}`

---

## Rules

- Themes are optional. Never require them. "Skip themes" is a valid answer.
- An issue can belong to both a theme and an epic — membership is not exclusive.
- A theme has no "definition of done" — it is a label, not a delivery commitment.
- No maximum size. Themes can hold 1 issue or 30. They're navigation aids, not sprint containers.
- Closing a theme does not close its issues.
- If the user tries to tag a story already tagged with another theme, note it: "I-NNN is currently tagged with TH-NNN. Retag it here?" and wait for confirmation.
