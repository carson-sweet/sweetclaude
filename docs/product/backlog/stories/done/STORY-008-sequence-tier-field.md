---
id: STORY-008
type: story
title: Execution sequence / tier field on epics and stories
status: abandoned
priority: later
effort: m
epic: null
milestone: MS-001
sprint: null
tags: [schema, sequencing, tiers, epics, planning]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
---

## Description

As a SweetClaude user planning multi-story epics, I want an explicit `sequence` field capturing the human-intended execution tier, so that "this is Wave 0 design work" vs "this is Wave 1 implementation" is structured data rather than prose buried in the milestone Notes section.

**Origin:** Filed 2026-05-13 by Carson Sweet. The session that produced this request authored explicit tier groupings for EP-1006 ("Tier 1 — design; Tier 2 — schema; Tier 3 — service; Tier 4 — consumers, parallel") in prose. There was no canonical field to hang this on, so the tier information lives only in the milestone's Notes section and in the epic body's free text.

**Depends on STORY-007** (structured dependency field) — without that foundation, `sequence` can be authored but can't be validated against the dependency graph.

### Today's gap

Even with structured dependencies (STORY-007), the dependency graph alone doesn't capture **the human-intended execution tier**. Sometimes the graph leaves multiple valid topological orderings, and the user has specific intent about which tier each item belongs to (Wave 0 design vs Wave 1 implementation).

Without a structured tier field:
- Rendering tools cannot show "this is Wave 0 work" vs "this is Wave 1 work" automatically
- Tier information must be repeated in every aggregate listing (milestone Contributing Work Items, epic Issues, BACKLOG-INDEX) — and gets out of sync when one is updated and others aren't
- A user reading a single BL file doesn't know which tier it's in unless the prose mentions it

### Proposed: structured `sequence` block

```yaml
sequence:
  tier: 3                  # integer; items in the same tier run in parallel
  wave: "Wave 1 — impl"    # optional human-readable wave label, free text
  parallel_with: [BL-192]  # optional explicit "these two are siblings" hint
```

- `tier` is sortable; integer ordering
- `wave` is descriptive; free-text label
- `parallel_with` is for when the tier number alone doesn't capture "these two are explicitly siblings"

When combined with STORY-007's structured dependencies, the framework can:
- Compute a default tier from the dependency graph (longest path to the root)
- Allow the user to override the computed tier when intent diverges from the minimal-path topology
- Render sequenced views grouped by tier

## Acceptance Criteria

- [ ] Epics and stories accept a `sequence` block (`tier`, optional `wave`, optional `parallel_with`)
- [ ] `sweetclaude:big-picture` and similar renderers group same-tier items visually (e.g. siblings under a `┬` rather than sequentially under `├──`)
- [ ] Validator catches tier inconsistencies (a BL in tier 3 that depends on a BL in tier 5 is impossible)
- [ ] A tier-aware view exists for visualizing the execution plan of a milestone or epic (e.g. `sweetclaude:status --by-tier` or similar)
- [ ] Tier can be computed from the dependency graph when not specified explicitly; user-provided tier overrides the computed value

## Related stories

- STORY-007 (structured dependencies) — required foundation
- STORY-009 (aggregate listings) — will consume both this and STORY-007

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
