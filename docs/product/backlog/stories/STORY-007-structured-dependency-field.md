---
id: STORY-007
type: story
title: Structured dependency field on backlog items, epics, and milestones
status: new
priority: later
effort: l
epic: EP-002
sprint: null
tags:
- schema
- dependencies
- foundation
- backlog
- epics
- milestones
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
epic_sequence: 1
---

## Description

As a SweetClaude user planning multi-story epics or multi-epic milestones, I want dependencies between work items to live in a machine-readable structured field, so that tooling can topo-sort, validate, render, and surface "next-ready" items — rather than every dependency-aware operation falling on me to do manually.

**Origin:** Filed 2026-05-13 by Carson Sweet. Third in a series of three enhancement requests filed in one session. The session that produced this hit the gap repeatedly while restructuring EP-1006 (Synth Relationship Role Model) — five-story execution graph BL-188 → BL-189 → BL-190 → {BL-191, BL-192} with correct `**Depends on:**` prose in each BL file, but milestone/epic listings rendered as a flat numeric list because nothing could parse the dependencies.

**The foundational change of this enhancement set.** STORY-008 (sequence/tier field) and STORY-009 (aggregate listings render from structured data) build on this. The original filer noted: "(1) is the highest-leverage single change."

### Today's gap

Dependencies are free-text on the BL file:
```markdown
**Depends on:** BL-188 (EP-1006 — role-aware synth membership) — §Authorization contract amendment text...
```

A human reads this and understands. A skill cannot. Specifically:
- `big-picture` cannot render dependency arrows; falls back to flat list grouped by milestone/epic
- `go` cannot identify "next-ready" items (no open dependencies); surfaces by horizon only
- No validator catches dependency cycles, dangling deps, or impossible orderings
- A multi-story epic with internal sequencing has its execution graph buried in prose

### Proposed: structured `dependencies` block

Add to frontmatter or a dedicated section on every BL, epic, and milestone artifact:

```yaml
dependencies:
  blocks: [BL-189, BL-190, BL-191, BL-192]   # what this item blocks if it is not done
  blocked_by:                                  # what this item is waiting on
    - id: BL-188
      kind: hard            # hard | soft
      reason: "Needs amended schema before contract text can be drafted"
```

Field semantics:
- `blocks` — items that cannot proceed until this one is done. Optional but useful for downstream-impact queries.
- `blocked_by` — items this one is waiting on. Each entry carries `kind` (hard=must complete first, soft=can proceed in parallel but coordinate) and `reason`. Optional `kind` defaults to `hard`.
- Values can reference any artifact ID the framework knows: `BL-NNN`, `EP-NNN`, `MS-NNN`, etc.

Free-text `**Depends on:**` stays for human readability, but the structured field is the source of truth. Tooling reads structured; humans can read either.

## Acceptance Criteria

- [ ] BL, epic, and milestone artifacts accept a `dependencies` block (frontmatter or dedicated section)
- [ ] A validator in `sweetclaude:_health` (or equivalent) catches: dangling dependencies (depends-on points at nonexistent ID), cycles, crossing-tier violations (BL in a milestone depending on a BL in a later milestone)
- [ ] `sweetclaude:big-picture` renders dependency edges between work items within the same milestone (not just flat nested list)
- [ ] `sweetclaude:go` exposes "no open dependencies" as a primary filter for `what to work on next`
- [ ] The structured field is the source of truth; the human-readable `**Depends on:**` prose can be derived from it (or rendered alongside it) for backward compatibility
- [ ] Existing projects with free-text `**Depends on:**` continue to work; migration to structured form is automatic or opt-in (no forced break)

## Out of scope

- Force-ranking the entire backlog into a single linear order
- Replacing the artifact files in projects with hundreds of BLs already authored (migration must be automatic or opt-in)

## Related stories

- STORY-008 (sequence/tier field) — depends on this for the dependency-graph foundation
- STORY-009 (aggregate listings render from structured data) — depends on this for the data model

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
