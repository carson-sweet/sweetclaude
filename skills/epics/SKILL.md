---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Manage epics and objectives — add, review, link, status, complete. Always loaded."
category: product
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:epics" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Epics

Manage epics: $ARGUMENTS

An epic is a **capability area** — a named body of work that delivers a distinct capability. Each epic has one objective (its success statement) and a set of completion criteria (phase-gate checklist). Version/release is metadata on the epic, not its organizing principle (DEC-29).

Epics live in `docs/product/roadmap/epics/EP-NNN-slug.md`. The SQLite cache at `.sweetclaude/cache/roadmap.db` provides fast queries; markdown files are the source of truth.

## Cache Helper

Before any operation, ensure the cache is current:

```bash
python3 scripts/cache.py --project-dir . --rebuild 2>/dev/null
```

After any mutation (add, link, complete), rebuild:

```bash
python3 scripts/cache.py --project-dir . --rebuild 2>/dev/null
```

## Routing

Parse `$ARGUMENTS` to determine the operation:

| Pattern | Operation |
|---|---|
| `add` or `add ...` | → Add |
| `review` or `review --all` | → Review |
| `link <ITEM-ID> <EP-NNN>` | → Link |
| `status <EP-NNN>` | → Status |
| `complete <EP-NNN>` | → Complete |
| empty or unrecognized | → Review (default) |

---

## Operation: Add

Create a new epic.

### Step 1: Gather inputs

Prompt for each field. Propose defaults where possible.

Required:
- **Title** — short capability name (e.g. "Workflow Engine")
- **Objective** — one sentence: what done looks like
- **Completion criteria** — ordered checklist (minimum 2 items)

Optional (with defaults):
- **Target release** — `REL-NNN` or null. List available releases from cache: `python3 scripts/cache.py --project-dir . --query releases`
- **Depends on** — list of `EP-NNN` IDs. List existing epics for reference.
- **Status** — defaults to `new`

### Step 2: Assign ID

```bash
python3 scripts/cache.py --project-dir . --query next-id --prefix EP
```

### Step 3: Write epic file

Derive slug from title: lowercase, replace non-alphanumeric with hyphens, collapse consecutive hyphens, trim trailing hyphens, truncate to 40 characters.

Write to `docs/product/roadmap/epics/EP-{NNN}-{slug}.md`:

```yaml
---
id: EP-{NNN}
type: epic
title: "{title}"
status: {status}
release: {REL-NNN or null}
objective: "{objective}"
completion_criteria:
  - "{criterion 1}"
  - "{criterion 2}"
completion_criteria_done: []
depends_on: [{dependencies}]
created: {today}
updated: {today}
---

## Description

{Brief description — 1-2 sentences summarizing the capability this epic delivers.}
```

### Step 4: Rebuild cache and confirm

```bash
python3 scripts/cache.py --project-dir . --rebuild 2>/dev/null
python3 scripts/cache.py --project-dir . --query active-epic 2>/dev/null
```

Output: `Created EP-{NNN}: {title}` with a one-line summary.

---

## Operation: Review

List epics grouped by status.

### Step 1: Query

```bash
python3 scripts/cache.py --project-dir . --query releases 2>/dev/null
```

### Step 2: Render

Group epics by status:

**Now** (status: active)
**Upcoming** (status: new)
**Shipped** (status: done) — hidden by default; shown with `review --all`
**Paused** (status: paused) — shown if any exist

For each epic, show:

```
EP-{NNN}  {title}  [{status}]
  Objective: {objective}
  Release: {release or "unassigned"}
  Criteria: {done_count}/{total_count} complete
  Stories: {open_count} open, {done_count} done
```

Story counts come from the `epic-stories` query:

```bash
python3 scripts/cache.py --project-dir . --query epic-stories --epic EP-{NNN} 2>/dev/null
python3 scripts/cache.py --project-dir . --query epic-stories --epic EP-{NNN} --include-done 2>/dev/null
```

Open stories = total (with done) - total (without done).

---

## Operation: Link

Bidirectional link between a work item and an epic.

### Step 1: Validate inputs

Parse: `link {ITEM-ID} {EP-NNN}`

Verify both exist:

```bash
python3 scripts/cache.py --project-dir . --query backlog --include-done 2>/dev/null
```

Find the item by ID in the result. If not found, error: "Item {ITEM-ID} not found in backlog."

Verify the epic exists by checking `docs/product/roadmap/epics/EP-{NNN}-*.md` via glob.

### Step 2: Check existing link

Read the item's source file. If it already has an `epic:` field with a different value, prompt before overwriting:

> "{ITEM-ID} is currently linked to {existing-epic}. Move it to {EP-NNN}?"

Use AskUserQuestion with options: **Move it** / **Cancel**.

### Step 3: Update item frontmatter

Read the item's markdown file. Update or add these frontmatter fields:
- `epic: EP-{NNN}`
- `epic_sequence: {next sequence number}`

To determine the next sequence number:

```bash
python3 scripts/cache.py --project-dir . --query epic-stories --epic EP-{NNN} --include-done 2>/dev/null
```

Count the results + 1.

Write the updated file.

### Step 4: Rebuild and confirm

```bash
python3 scripts/cache.py --project-dir . --rebuild 2>/dev/null
```

Output: `Linked {ITEM-ID} → EP-{NNN} (sequence {N})`

---

## Operation: Status

Detailed view of a single epic.

### Step 1: Read epic data

```bash
python3 scripts/cache.py --project-dir . --query releases 2>/dev/null
```

Find the epic in the releases hierarchy. Also query its stories:

```bash
python3 scripts/cache.py --project-dir . --query epic-stories --epic EP-{NNN} --include-done 2>/dev/null
```

### Step 2: Read completion criteria from file

Read the epic's markdown file directly to get `completion_criteria` and `completion_criteria_done` lists.

### Step 3: Render

```
EP-{NNN}: {title}
═══════════════════

Status:    {status}
Release:   {release or "unassigned"}
Objective: {objective}
Depends on: {depends_on list or "none"}

Completion Criteria ({done}/{total}):
  ✓ {criterion — if in completion_criteria_done}
  · {criterion — if not done}

Stories ({open}/{total}):
  {ITEM-ID}  {title}  [{status}]  (seq {N})
  ...
```

---

## Operation: Complete

Mark an epic as done.

### Step 1: Check completion criteria

Read the epic file. Compare `completion_criteria` against `completion_criteria_done`.

If not all criteria are satisfied, present the gaps:

> "EP-{NNN} has {N} unmet completion criteria:"
> - {criterion 1}
> - {criterion 2}

Use AskUserQuestion:
- **Complete anyway** — I acknowledge the unmet criteria
- **Cancel** — I'll address the gaps first

### Step 2: Update epic file

If proceeding:
- Set `status: done`
- Add `closed_date: {today}`
- Set `updated: {today}`
- Set `completion_criteria_done` to match `completion_criteria` (all done)

Write the updated file.

### Step 3: Move to done directory

```bash
mv docs/product/roadmap/epics/EP-{NNN}-{slug}.md docs/product/roadmap/epics/done/
```

Ensure `docs/product/roadmap/epics/done/` exists first.

### Step 4: Rebuild and confirm

```bash
python3 scripts/cache.py --project-dir . --rebuild 2>/dev/null
```

Output: `Completed EP-{NNN}: {title}`

---

## Rules

- Markdown files are source of truth. Cache is derived.
- Always rebuild cache after mutations.
- Never modify cache directly.
- One active epic at a time. If `add` is called with `status: active` and another epic is already active, warn and require explicit confirmation.
- Use AskUserQuestion for all bounded decisions per interaction model.
