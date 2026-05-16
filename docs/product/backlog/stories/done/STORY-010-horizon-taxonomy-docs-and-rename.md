---
closed_date: '2026-05-15'
created: 2026-05-13
effort: s
epic: EP-010
id: STORY-010
milestone: MS-001
origin: manual
priority: soon
sprint: null
status: done
tags:
- taxonomy
- documentation
- backlog
- validation
- big-picture
- naming
title: Document and refine horizon taxonomy (rename `next` → `now`, add docs and validation)
type: story
updated: 2026-05-15
---

## Description

As a SweetClaude user authoring backlog items, I want the valid `Horizon:` values to be documented in the framework, named consistently with my natural-language mental model, and validated on authoring, so that I don't have to read the `big-picture` skill's source code to discover what's accepted.

**Origin:** Filed 2026-05-13 by Carson Sweet. Independently shippable from STORY-007/008/009 — this is a documentation, naming, and validation cleanup on an adjacent taxonomy that's already nearly correct.

### Today's state

Backlog items have two ordering signals:
- **`Priority:`** — values `P0 | P1 | P2 | P3 | SPIKE | low | medium`. Semantics: urgency/severity.
- **`Horizon:`** — values `next | sooner | soon | later | someday | unscheduled` (only confirmable by reading `big-picture` skill source). Semantics: when do we expect to work on this?

The horizon taxonomy is the right shape for "backlog ordering without force-ranking" — buckets like "now-ish" / "soon-ish" / "eventually" without requiring global linear order. Matches the user's mental model exactly.

### Gaps

- Horizon taxonomy is **not documented in any user-visible part of the framework**. Valid values appear only in `big-picture`'s `HORIZON_ORDER` dict
- `next` is the highest-priority bucket but reads as descriptive ("the next thing") rather than time-positioned ("right now"). User's natural-language mental model is "now, sooner, soon" — `now` matches better than `next`
- No validator catches a BL with `**Horizon:** asap` or `**Horizon:** P1` (someone confusing priority with horizon)
- Aggregate views (BACKLOG-INDEX) show `Priority` only; `Horizon` is invisible unless you open the individual BL file

### Proposed changes

1. **Document the horizon taxonomy** in user-visible framework docs (e.g. `sweetclaude:help` for backlog, or per-skill schema docs)
2. **Rename `next` to `now`** with `next` accepted as alias during a transition window. Final canonical set: `now | sooner | soon | later | someday | unscheduled`
3. **Validate horizon values** on BL creation. Reject unrecognized values; show the valid set
4. **Render horizon alongside priority** in `big-picture` and BACKLOG-INDEX aggregate views

## Acceptance Criteria

- [ ] Horizon taxonomy is documented in framework user-facing docs (discoverable via `sweetclaude:help` or equivalent)
- [ ] Canonical set is `now | sooner | soon | later | someday | unscheduled`; `next` accepted as alias for `now` during a transition window
- [ ] Validator rejects unknown horizon values on BL creation/update; shows the valid set
- [ ] `sweetclaude:big-picture` and BACKLOG-INDEX renderers display both `Priority` and `Horizon` columns
- [ ] Existing BLs with `**Horizon:** next` continue to work (alias accepted); no forced migration

## Out of scope

- Replacing the priority taxonomy
- Force-ranking the backlog into a single linear order

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
