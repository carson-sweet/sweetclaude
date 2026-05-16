---
id: STORY-009
type: story
title: Roadmap and aggregate listings consume sequence and dependency data
status: new
priority: later
effort: xl
epic: EP-002
sprint: null
tags:
- rendering
- aggregate-views
- source-of-truth
- big-picture
- milestones
- epics
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
epic_sequence: 5
---

## Description

As a SweetClaude user, I want milestone, epic, and backlog-index listings to render automatically from the structured data on individual BL files, so that I don't have to update three files (epic body, milestone Notes, milestone Contributing Work Items) every time I bump a BL's priority or add a dependency — and so the listings can't fall out of sync with the BLs.

**Origin:** Filed 2026-05-13 by Carson Sweet. The session that produced this request restructured EP-1006 into a tier view and had to update the same listing in three places to keep them in sync. The filer notes: "(3) is the highest-impact user-visible change."

**Depends on STORY-007** (structured dependencies) **and STORY-008** (sequence/tier field) — those provide the source-of-truth data this story renders from.

### Today's gap

Milestone, epic, and backlog-index files each maintain their own hand-authored listings of which work items they contain:
- Hand-ordered (by ID, by hand-chosen sequence, or by happenstance)
- Easy to fall out of sync with the underlying BL files
- Unable to show parallelism, dependency tiers, or "blocked vs ready" state because the listings are flat

When the EP-1006 restructure happened, the human-authored prose lived in three places (epic body, milestone Notes, milestone Contributing Work Items section). Updating one and not the others is the failure mode.

### Two proposed paths

**Path A — generated sections (smaller change):**
Designated sections in milestone/epic files are auto-generated. Header marker `<!-- BEGIN GENERATED: contributing-items -->` opens and a footer marker closes the block. A skill (`sweetclaude:_regenerate` or part of `_health`) refreshes these blocks from the structured field source of truth.

**Path B — single source of truth in structured store (cleaner end-state):**
Milestone, epic, and BL identity lives in one structured store (could be YAML in `.sweetclaude/state/`, could be BL frontmatter). Markdown documents are rendered from that store via a generator. Edits go to the structured store. Markdown is read-only for tooling.

Path A is the smaller change; Path B is the cleaner end-state. Path A is likely the right v1; Path B is the long-term direction.

## Acceptance Criteria

- [ ] Milestone Contributing Work Items section is generated from BL-side data (not hand-authored)
- [ ] Epic Issues section is generated from BL-side data
- [ ] BACKLOG-INDEX (or v4 equivalent) MS-NNN sections are generated from BL-side data
- [ ] A user updating a BL's priority, dependency, or tier does NOT have to update aggregate listings — they refresh on demand or automatically
- [ ] Drift between aggregates and underlying BLs is impossible (Path B) or caught by `_health` (Path A)
- [ ] Aggregate views render parallelism (same-tier items grouped) and dependency edges, not just flat lists
- [ ] Existing hand-authored aggregate sections migrate cleanly (one-time conversion or marker-injection)

## Out of scope

- A full project-management UI
- Replacing existing artifact files in projects that have already authored hundreds of BLs in the current format

## Related stories

- STORY-007 (structured dependencies) — required source-of-truth data
- STORY-008 (sequence/tier field) — required source-of-truth data

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
