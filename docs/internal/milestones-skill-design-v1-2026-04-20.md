---
Version: 1.0
Date: 2026-04-20
Status: Draft
Owner: Carson Sweet
---

# Milestones Skill — Design Spec

## Overview

A new cross-cutting SweetClaude skill, `sweetclaude:milestones`, that manages **roadmap targets** — named strategic outcomes that span strategy and product work. A milestone is not a release, sprint, or epic; it is an outcome the project is driving toward (e.g., "Exit Stealth", "Paid Pilot Live", "Series A Readiness"). The skill provides create/review/link/status/complete operations, bidirectional linking with product work items, and one-way references from milestone criteria to canonical strategy artifacts.

## Placement

- **Skill name:** `sweetclaude:milestones`
- **Directory:** `skills/milestones/SKILL.md`
- **Load scope:** `always_loaded` in `config/phase-skills.yaml` (alongside `sweetclaude`, `sweetclaude:new-task`, `sweetclaude:hibernate`, `hibernate-project`).
- **Rationale:** Milestones are neither strategy-only nor product-only. Strategy defines them, product plans toward them, code delivers toward them. Available in every phase.

## Storage Model

Mirrors the existing `docs/backlog/` pattern (index + per-item files).

```
docs/milestones/
  MILESTONES-INDEX.md        Master index (table of milestones, status, short summary)
  MS-001-exit-stealth.md     One file per milestone
  MS-002-paid-pilot.md
  ...
```

- IDs are `MS-XXX`. Permanent; never renumbered. Gaps allowed.
- No derived state file. Progress is recomputed by scanning when needed. A stale cache is worse than recomputation.

## Milestone File Schema

Each milestone file follows this template:

```markdown
# MS-XXX: Title

**Status:** proposed | active | achieved | dropped | superseded
**Owner:** [name/role]
**Depends on:** (other MS-XXX refs, if any)

## Outcome
One paragraph describing what this milestone represents and why it matters.

## Measuring success
- [ ] Criterion 1 (each must be evaluable as true/false after the milestone ships)
- [ ] Criterion 2
- [ ] Criterion linked to canonical artifact: `strategy/narrative-arc.md` finalized
- [ ] Criterion linked to canonical artifact: `strategy/market-messaging.md` finalized

## Non-goals
- What this milestone is explicitly NOT
- Second explicit exclusion
- Third explicit exclusion

## Contributing work items
- US-012 — Landing page redesign
- US-015 — Press kit generator
- BL-007 — Analytics tracking

## Notes
Free-form log of decisions, scope changes, blockers encountered.

---

## Changelog
| Version | Date       | Change summary                      |
|---------|------------|-------------------------------------|
| 1.0     | 2026-04-20 | Initial draft                       |
```

### Field definitions

- **Status** — one of five values (see Status Taxonomy below).
- **Owner** — single accountable person/role (DACI Approver pattern). Usually the project lead.
- **Depends on** — other milestones that must be achieved before this one becomes active. Not a hard block; advisory.
- **Outcome** — narrative framing. What does "achieved" look like at a high level?
- **Measuring success** — a checklist of concrete, evaluable criteria. Each item may optionally reference a canonical strategy artifact by path (the strategic linking pattern). When the artifact exists and is finalized, the criterion is met.
- **Non-goals** — explicit scope boundary. Load-bearing. Prevents scope creep into the milestone.
- **Contributing work items** — product-side references (US-XXX, BL-XXX). This is one side of the bidirectional link; the work item files carry a matching `Milestone: MS-XXX` header.
- **Notes** — free-form. Decisions, scope changes, blockers. Append-only, dated.
- **Changelog** — living-doc discipline. Every substantive change to the file adds a row.

## Linking Model

Two distinct patterns coexist in a single milestone file:

### Strategy side — one-way artifact references

Milestone criteria reference canonical strategy artifacts by file path. Strategy skills (`strategy/narrative-arc`, `strategy/market-messaging`, `strategy/pain-thesis`, etc.) are **unchanged**. They do not know about milestones.

Example criterion:
```
- [ ] `strategy/narrative-arc.md` finalized
```

When the referenced file exists and (by convention) its front-matter status is `final` or `canonical`, the criterion is met. The milestones skill handles the reading; strategy skills stay focused on their own artifacts.

### Product side — bidirectional via header

Stories and backlog items carry an optional `Milestone: MS-XXX` header. The milestone file lists them in `## Contributing work items`. Both sides must agree. The `link` operation maintains both.

Example in `stories/US-012-landing-page.md`:
```markdown
# US-012: Landing page redesign
**Milestone:** MS-001
...
```

And in `docs/milestones/MS-001-exit-stealth.md`:
```markdown
## Contributing work items
- US-012 — Landing page redesign
```

## Status Taxonomy

| Status       | Meaning                                                                 |
|--------------|-------------------------------------------------------------------------|
| `proposed`   | Drafted, not yet committed. Appears in "Later" view.                    |
| `active`     | Currently being driven. Appears in "Now" view. Can be multiple at once. |
| `achieved`   | All criteria met; user confirmed. Terminal state.                       |
| `dropped`    | Abandoned. Captured with rationale in Notes. Terminal state.            |
| `superseded` | Replaced by a newer milestone. Link to successor in Notes. Terminal.    |

## Operations

### `add`
Create a new milestone. Prompts for title, outcome, initial criteria (with optional artifact paths), non-goals, depends-on, and owner. Assigns next `MS-XXX` ID. Defaults to status `proposed`. Writes the milestone file and updates `MILESTONES-INDEX.md`.

### `review`
List milestones grouped by commitment level (not by date):

```
Now (active):
  MS-001 — Exit Stealth         (3/5 criteria met, 2 contributing items open)
  MS-003 — MVP Shipped          (4/4 criteria met, awaiting completion)

Next (proposed, near-term):
  MS-004 — Paid Pilot Live

Later (proposed, directional):
  MS-005 — Series A Readiness
  MS-006 — Self-serve onboarding
```

Grouping rule: `active` → Now. `proposed` milestones default to Later (directional, not committed). A proposed milestone is promoted to Next only if the user has marked it committed (mechanism: see Open Items). Terminal states are hidden from this view by default; `review --all` shows them.

### `link <work-item> <MS-XXX>`
Attach a product work item (US-XXX or BL-XXX) to a milestone. Updates both sides: sets `Milestone: MS-XXX` header in the work item file, adds the item to the milestone's `Contributing work items` list. If the work item already has a different milestone, prompts before overwriting.

### `status <MS-XXX>`
Detailed view of one milestone: title, status, owner, outcome, criteria with per-criterion completion state (scan referenced artifact files to determine), non-goals, contributing work items with per-item state (pending/in-progress/done), recent notes, changelog.

### `blockers <MS-XXX>`
List everything unfinished on this milestone: unmet criteria, incomplete contributing work items, unmet dependencies. Designed for answering "what's stopping us from achieving MS-XXX?"

### `complete <MS-XXX>`
Mark a milestone as `achieved`. Enforces: all criteria must be checked; if any are unchecked, prompts for explicit waiver with a note. After marking achieved, **chains into follow-up prompt**:

> "Milestone achieved. Any follow-ups to capture?
> - incomplete_scope — parts you deferred
> - next_steps — what users want next
> - tech_debt — shortcuts taken
> - test_gaps — missing test coverage"

Items the user provides are routed through `sweetclaude:product/backlog` with the appropriate category. Updates the changelog.

### `unassigned`
Scan `stories/` and `docs/backlog/`. List any work items without a `Milestone:` header. Output is a prompt, not a forced action:

> "5 work items have no milestone. Either link them to a milestone or confirm they are distractions / out of roadmap."

This is the "every work item traces to a goal" hygiene check. Manual invocation; not automated.

## Integrations with Existing Skills

Four existing skills are updated. The first three product-side skills gain awareness; strategy skills are untouched.

### `product/user-story`
After creating a story, offer milestone assignment:

> "Assign this story to a milestone? [list of active + proposed milestones, or 'none / later']"

Adds `Milestone: MS-XXX` header to the story file. Updates the milestone's contributing-items list.

### `product/sprint-plan`
During sprint planning, after stories are selected for the sprint, show which milestones the sprint advances:

> "This sprint advances: MS-001 Exit Stealth (2 stories), MS-003 MVP Shipped (1 story). Unassigned: 1 story."

Surfaces scope drift — if a sprint contains mostly unassigned work, something is off.

### `status` (the orient view)
Add an "Active milestones" section to the status presentation:

```
Active milestones:
  MS-001 Exit Stealth        3/5 criteria
  MS-003 MVP Shipped         4/4 criteria — ready to complete
```

### `product/backlog`
No direct integration for assignment (per user's explicit choice — not all backlog items should be milestone-tied). However, the `complete` operation of the milestones skill routes follow-ups THROUGH `product/backlog`, so the backlog skill's `add` pathway is invoked indirectly.

## State

None. The skill stores no state outside the `docs/milestones/` files and the headers it writes into story/backlog files. Progress (criterion completion, contributing-item completion, blocker counts) is recomputed on every read by scanning files.

Rationale: caches go stale. Milestones move on human timescales (weeks to months); recomputation cost is negligible. Matches SweetClaude's existing no-cache discipline.

## Config Change

In `config/phase-skills.yaml`, add to `always_loaded.skills`:

```yaml
always_loaded:
  skills:
    - sweetclaude
    - sweetclaude:new-task
    - sweetclaude:hibernate
    - sweetclaude:milestones   # new
    - hibernate-project
  ...
```

No bucket-specific additions needed.

## Patterns Borrowed (Credit)

- **Now / Next / Later roadmap view** — GOV.UK / Replit `product-manager` skill. Commitment-based grouping avoids the roadmap-as-contract trap.
- **Non-goals section** — Linear PRD template via Replit `product-manager`.
- **Status taxonomy (proposed/active/achieved/dropped/superseded)** — adapted from Replit `project_tasks` and living-doc status from `product-manager`.
- **"Measuring success" as checklist** — adapted from "Done looks like" (Replit `project_tasks`), renamed per user preference.
- **Follow-up categorization on completion** — Replit `follow-up-tasks` (incomplete_scope / next_steps / tech_debt / test_gaps).
- **Index + detail file pattern** — existing SweetClaude `product/backlog` convention.

## Rejected Patterns (for the record)

- **RICE / WSJF prioritization** — heavier than SweetClaude's implicit prioritization; user does not score work items numerically.
- **Time-based roadmap buckets (Q1, Q2, dates)** — violates SweetClaude's no-time-estimates rule.
- **DACI full matrix** — single-user project; owner field is sufficient.
- **State cache in `.sweetclaude/state/`** — explicitly rejected in favor of on-demand recomputation.
- **Automatic milestone assignment for every backlog item** — user explicitly excluded `product/backlog` from assignment touch points.

## Open Items for Implementation Plan

1. Canonical-artifact-finalized check: what convention marks a strategy file as "final"? Front-matter field (`status: final`), filename suffix, or separate registry? Needs a pick during implementation planning.
2. Next-bucket promotion mechanism for proposed milestones: a `Commitment: committed` field in the milestone file, a separate `planned` status, or a manual flag in the review call? Needs a pick during implementation planning.
3. Bulk-link operation (attach multiple work items at once) — defer unless the single-item `link` proves tedious.
4. Migration: should existing stories/backlog items be retroactively assigned milestones? Answer: no forced migration; `unassigned` surfaces them when the user wants to do hygiene.
5. Whether `achieved` milestones should be archived to `docs/milestones/archive/` or stay in place. Default: stay in place; terminal states hidden by default in `review`.

## Changelog

| Version | Date       | Change summary                                          |
|---------|------------|---------------------------------------------------------|
| 1.0     | 2026-04-20 | Initial design. Approved after clarifying questions on  |
|         |            | scope (cross-cutting), storage (lean file pattern),     |
|         |            | linking (bidirectional product / one-way strategy), and |
|         |            | touch points (user-story, sprint-plan, status). Eight   |
|         |            | patterns borrowed from corpus review.                   |
