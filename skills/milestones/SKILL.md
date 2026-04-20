---
description: "Manage roadmap targets (milestones) that span strategy and product work. Create, review, link work items to, and track completion of outcome-driven milestones like 'Exit Stealth' or 'Paid Pilot Live'."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Milestones

Manage milestones: $ARGUMENTS

A milestone is a **roadmap target** — a named strategic outcome the project is driving toward. Not a release, not a sprint, not an epic. Examples: "Exit Stealth", "Paid Pilot Live", "Series A Readiness", "MVP Shipped".

## Routing

Classify the invocation by the first word of `$ARGUMENTS`:

| First word | Operation |
|------------|-----------|
| `add` | Create a new milestone |
| `review` | List milestones grouped by Now / Next / Later |
| `link <item> <MS-XXX>` | Attach a product work item to a milestone |
| `status <MS-XXX>` | Detail view of one milestone |
| `blockers <MS-XXX>` | List what's unfinished on a milestone |
| `complete <MS-XXX>` | Mark a milestone achieved + chain follow-ups |
| `unassigned` | Find work items with no milestone |

If `$ARGUMENTS` is empty or doesn't match, default to `review`.

## Storage

```
docs/milestones/
  MILESTONES-INDEX.md       Master index (one row per milestone)
  MS-001-short-name.md      One file per milestone
  MS-002-short-name.md
  ...
```

- IDs are `MS-XXX`. Read the index, find the highest number, increment by 1.
- IDs are permanent. Never renumber. Gaps are fine.

## Milestone file template

```markdown
# MS-XXX: Title

**Status:** proposed | active | achieved | dropped | superseded
**Owner:** [name/role]
**Depends on:** (other MS-XXX refs, if any)

## Outcome
One paragraph describing what this milestone represents and why it matters.

## Measuring success
- [ ] Criterion 1 (each evaluable as true/false)
- [ ] Criterion 2
- [ ] Criterion linked to artifact: `strategy/narrative-arc.md` finalized

## Non-goals
- What this milestone is explicitly NOT
- Second explicit exclusion

## Contributing work items
- US-012 — Landing page redesign
- BL-007 — Analytics tracking

## Notes
Free-form log of decisions, scope changes, blockers encountered.

---

## Changelog
| Version | Date       | Change summary       |
|---------|------------|----------------------|
| 1.0     | YYYY-MM-DD | Initial draft        |
```

## Status taxonomy

| Status       | Meaning                                                                  |
|--------------|--------------------------------------------------------------------------|
| `proposed`   | Drafted, not yet committed. Appears in "Later".                          |
| `active`     | Currently being driven. Appears in "Now". Can be multiple.               |
| `achieved`   | All criteria met; user confirmed. Terminal state.                        |
| `dropped`    | Abandoned with rationale in Notes. Terminal state.                       |
| `superseded` | Replaced by a newer milestone. Links to successor in Notes. Terminal.    |

## Operations

### `add` — Create a new milestone

1. Read `docs/milestones/MILESTONES-INDEX.md`. If it does not exist, create it with this header:

```markdown
# Milestones Index

| ID | Title | Status | Owner | Short summary |
|----|-------|--------|-------|---------------|
```

2. Find the highest existing `MS-XXX` in the index. Increment by 1. If the index is empty, start at `MS-001`.
3. Ask the user (one question at a time, per SweetClaude interaction model):
   - Title (short, descriptive, 2-5 words)
   - Outcome (one paragraph — what "achieved" looks like)
   - Measuring success criteria: ask for a list. For each criterion, offer: "Link this to a canonical artifact path? (optional, e.g. `strategy/narrative-arc.md`)"
   - Non-goals: require at least one. If the user offers none, prompt: "What is this milestone explicitly NOT? A non-goals list with zero items is a scope red flag."
   - Depends on: list of other MS-XXX refs (optional)
   - Owner: default to the value of `owner` in `.sweetclaude/state/phase.yaml` if present; otherwise prompt.
4. Default `Status:` to `proposed`. Ask the user only if they indicate otherwise.
5. Write the file at `docs/milestones/MS-XXX-<slug>.md` using the milestone template from the previous section, filling in all fields. `<slug>` is a dash-lowercased version of the title (e.g., "Exit Stealth" → `exit-stealth`).
6. Append a row to `MILESTONES-INDEX.md`:

```
| MS-XXX | [Title](MS-XXX-slug.md) | proposed | Owner | One-sentence outcome summary |
```

7. Tell the user: "Added MS-XXX: {title}. Status: proposed. File: docs/milestones/MS-XXX-{slug}.md"

### `review` — List milestones by commitment level

1. Scan `docs/milestones/` for all files matching `MS-*.md` (exclude `MILESTONES-INDEX.md`).
2. Read each file's `**Status:**` field.
3. Group:
   - **Now**: `active`
   - **Next**: (see Open Items — default empty; promotion mechanism is an open design question in the spec)
   - **Later**: `proposed`
   - Terminal states (`achieved`, `dropped`, `superseded`): hidden unless `review --all` was invoked.
4. For each displayed milestone, compute a progress snapshot:
   - Count `- [x]` and `- [ ]` lines under the `## Measuring success` heading.
   - For criteria that reference an artifact path, note whether the path is populated vs. a bare text criterion. (Artifact finalization check — see Open Items for the canonical convention.)
5. Present in this format:

```
Milestones

Now (active):
  MS-001 Exit Stealth         3/5 criteria met
  MS-003 MVP Shipped          4/4 criteria met — ready to complete

Later (proposed):
  MS-004 Paid Pilot Live
  MS-005 Series A Readiness
```

6. If `--all` was passed, append terminal-state milestones after Later:

```
Achieved:
  MS-002 Private Alpha        (2026-03-15)

Dropped:
  MS-006 Desktop App          (2026-02-01 — rationale: see Notes)
```

7. If no milestones exist, say: "No milestones yet. Run `/sweetclaude:milestones add` to create one."

### `link <work-item> <MS-XXX>` — Bidirectional attach

1. Validate the work-item ref: must match `^(US|BL)-\d+$`. If not, tell the user the expected format and stop.
2. Locate the work-item file:
   - `US-XXX` → search `stories/**/US-XXX-*.md` then `.sweetclaude/stories/**/US-XXX-*.md`.
   - `BL-XXX` → search `docs/backlog/BL-XXX-*.md`.
   - If not found, tell the user and stop.
3. Validate `docs/milestones/MS-XXX-*.md` exists. If not, tell the user and stop.
4. Read the work item. Check for an existing `**Milestone:**` header (exact match: line starting with `**Milestone:**`).
   - If present and equals the requested MS: no-op. Say "Already linked."
   - If present but different: ask "This work item is currently linked to {old MS}. Replace with {new MS}? (yes/no)" — require explicit yes. If no, stop.
5. Write/update the work item's `**Milestone:**` header:
   - If no header exists, insert `**Milestone:** MS-XXX` immediately after the H1 title line.
   - If a header exists, replace its value.
6. Read `docs/milestones/MS-XXX-*.md`. In the `## Contributing work items` section:
   - If the item is not already listed, add `- {work-item-ref} — {title from work item's H1}`.
   - If the section does not exist, create it before `## Notes`.
7. If the work item was previously linked to a different milestone:
   - Read that old milestone file.
   - Remove the work item from its Contributing work items section.
   - Append a Changelog row: "{date} — Removed {work-item-ref} (relinked to {new MS})."
8. Append a Changelog row to the new milestone file: "{date} — Linked {work-item-ref}."
9. Tell the user: "Linked {work-item-ref} to MS-XXX. {if relinked: 'Removed from {old MS}.'}"

### `status <MS-XXX>` — Detail view

1. Read `docs/milestones/MS-XXX-*.md`. If missing, tell user and stop.
2. For each item in `## Measuring success`:
   - If the item references an artifact path (pattern: backtick-wrapped path like `` `strategy/narrative-arc.md` ``), read that file. Determine "met" using the finalization convention (see Open Items — default: file exists and its first heading is not `# DRAFT`).
   - Otherwise, use the checkbox state directly (`- [x]` met, `- [ ]` not met).
3. For each item in `## Contributing work items`, read the work-item file and classify:
   - **done**: work item's own status marker says completed/done/merged.
   - **in-progress**: marker says active/in-progress.
   - **pending**: no active marker.
   - **unknown**: file missing or no marker — flag with `?`.
4. Render:

```
MS-001: Exit Stealth
Status: active  |  Owner: Carson
Depends on: (none)

Outcome:
One paragraph...

Measuring success:
  [x] Criterion 1
  [ ] Criterion 2
  [x] strategy/narrative-arc.md finalized
  [ ] strategy/market-messaging.md finalized

Non-goals:
  - Not a self-serve launch
  - Not a pricing change

Contributing work items:
  US-012  (done)        Landing page redesign
  US-015  (in-progress) Press kit generator
  BL-007  (pending)     Analytics tracking

Recent notes:
  2026-04-18 — Narrative arc finalized.
  2026-04-10 — Decided to split press kit from landing page.
```

5. "Recent notes" shows the last 3 Notes entries (by date if dated, otherwise by file order).

### `blockers <MS-XXX>` — What is stopping us

1. Read the milestone file. If missing, tell user and stop.
2. Compute:
   - **Unmet criteria:** each `- [ ]` line under Measuring success, and each artifact-reference criterion where the artifact is not finalized.
   - **Open work items:** each item under Contributing work items that is not in `done` state (same classification as `status`).
   - **Unmet dependencies:** each MS-XXX in Depends on whose Status is not `achieved`.
3. Render:

```
Blockers for MS-001 Exit Stealth:

Unmet criteria (2):
  - Criterion 2
  - strategy/market-messaging.md finalized

Open work items (2):
  US-015  (in-progress) Press kit generator
  BL-007  (pending)     Analytics tracking

Dependencies not met (1):
  MS-000  Company name finalized  (status: proposed)
```

4. If nothing is blocking, say: "Nothing is blocking MS-XXX. All criteria met, all contributing work items done, all dependencies achieved. Run `/sweetclaude:milestones complete MS-XXX` to mark it achieved."

### `complete <MS-XXX>` — Mark achieved and chain follow-ups

1. Read the milestone file. If missing, tell user and stop.
2. If current Status is already terminal (`achieved`, `dropped`, `superseded`), tell the user and stop. Do not transition from a terminal state.
3. Evaluate criteria (same logic as `status`):
   - If any criterion is unmet, list them.
   - Ask: "These criteria are not met: {list}. Proceed with explicit waiver?"
   - If the user declines, stop without changes.
   - If the user accepts, prompt: "Waiver rationale?" Append to `## Notes`: `{date} — Completion waiver: {rationale}. Unmet at completion: {list}.`
4. Evaluate contributing work items:
   - If any are not in `done` state, list them.
   - Ask: "These contributing work items are not done: {list}. Continue?"
   - If no, stop. If yes, proceed.
5. Set `**Status:**` to `achieved`.
6. Append Changelog row: `{date} — Marked achieved. {if waived: 'Waived N criteria — see Notes.'}`
7. Update `MILESTONES-INDEX.md`: change the status column for this milestone to `achieved`.
8. **Follow-up chain.** Ask the user:

```
Milestone achieved. Any follow-ups to capture?

Categories:
  - incomplete_scope — parts deferred from this milestone
  - next_steps      — what users will want next
  - tech_debt       — shortcuts taken that should be paid back
  - test_gaps       — missing test coverage uncovered during the work

List each follow-up as: "<category>: <short title>". Enter blank line when done.
```

9. For each follow-up entered, invoke `sweetclaude:product/backlog` with arguments that route to its `add` flow. Pass the category as context. Do not inline the backlog-add logic — delegate. If the user indicated a strategic item, the backlog skill's existing router will redirect to `strategy/`.
10. Tell the user: "MS-XXX marked achieved. {N} follow-ups filed."

### `unassigned` — Hygiene check

1. Scan work-item files:
   - Stories: `stories/**/US-*.md` and `.sweetclaude/stories/**/US-*.md`.
   - Backlog: `docs/backlog/BL-*.md`.
2. For each file, check for a `**Milestone:**` header line.
3. Group items with no header by type:

```
Unassigned work items (5):

Stories (2):
  US-008  Onboarding email flow
  US-011  Usage dashboard

Backlog (3):
  BL-003  Migrate to Postgres
  BL-005  Add rate limiting
  BL-009  Vendor management page
```

4. Tell the user: "These have no milestone. Either link them to a milestone (`/sweetclaude:milestones link <item> <MS-XXX>`) or confirm they are distractions / out of roadmap. Not doing anything is also fine — this check is advisory."
5. Do not force action. Do not modify files. Surface only.
