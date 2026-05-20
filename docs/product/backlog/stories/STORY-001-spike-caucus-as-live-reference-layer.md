---
id: STORY-001
type: story
title: Spike — caucus as a live reference layer
status: new
priority: soon
effort: m
epic: null
milestone: null
sprint: null
tags: [spike, caucus, knowledge, orchestration]
origin: manual
created: 2026-05-12
updated: 2026-05-15
closed_date: null
---

## Description

**Spike question:** When a caucus is active (running against an in-flight design effort), how should SweetClaude (a) keep the caucus findings synchronized with the underlying docs as those docs evolve, and (b) treat the caucus output as the primary reference layer for any subsequent skill invocation that needs documentation, design information, or context about the area under review?

**Why this matters:** During the v4 design revision work, the caucus produced a structured `v4-caucus-findings-*.md` document that effectively became the single most useful reference for the v4 design state — more useful than re-reading the design and migration specs themselves, because it captured the *deltas, gaps, and resolutions* in a way the source docs do not. If a skill being invoked later (e.g. `find-skill`, `bootstrap`, `fix-sweetclaude`, anything that needs to understand a design area) ignored the caucus and re-read the raw docs, it would miss:
- Issues identified but not yet resolved
- Decisions locked during caucus questions (sprint prefix, schema canonicalization, fallback epic naming)
- The deliberate-and-still-pending status of partial fixes
- Cross-references between findings that the source docs don't carry

The caucus findings doc is currently a static artifact written once and abandoned. If SweetClaude is going to treat caucus as a first-class workflow (and it should, based on how useful this v4 caucus was), the framework needs an answer to "where does the caucus live in the knowledge graph, and how does it stay current?"

**Deliverable:** A short design proposal (≤ 2 pages) covering:
1. **Lifecycle.** When does a caucus become "active" vs "archived"? Who controls the transition? Does an active caucus follow specific docs, specific work items, or specific epics?
2. **Synchronization.** When the underlying docs change after a caucus produces findings, what keeps the findings doc accurate? Manual re-run? Auto-flag stale findings? Diff detection on cited line numbers?
3. **Read precedence.** When `find-skill`, `bootstrap`, `fix-sweetclaude`, or any skill needs context about an area with an active caucus, what's the protocol? Read the caucus first, then the source docs? Or the source docs first, then the caucus as overlay? How does this avoid the caucus going stale and misleading downstream work?
4. **Storage.** Caucus findings currently live at `docs/internal/v4-caucus-findings-2026-05-12.md`. Is that the right shape — one file per caucus session? Or should there be a `caucus/` directory with an INDEX and a status field per caucus (active / archived / superseded)?
5. **Skill changes.** What concrete skill modifications would implement read-precedence? Is this a `find-skill` enhancement, a bootstrap-step enhancement, or a new dedicated skill (`/sweetclaude:caucus-status`)?

The proposal should answer "build it as part of v4.x" vs "wait for v5." Spike output goes to `docs/internal/`; if the proposal is build-now, it spawns implementation stories.

## Acceptance Criteria

- [ ] Design proposal document exists at `docs/internal/caucus-as-live-reference-spike-{date}.md`
- [ ] All five questions above answered with concrete recommendations (not just analysis)
- [ ] Proposal includes a worked example using the v4 caucus as a case study — what would have been different if this mechanism had been in place from the start
- [ ] Proposal includes a "smallest viable version" — what's the minimum behavior change that delivers most of the value (read-precedence might be free; full synchronization is a lot more work)
- [ ] Implementation effort assessed (S/M/L/XL) for the smallest viable version and for the full proposal
- [ ] Build-now vs defer recommendation with rationale
- [ ] If build-now: implementation stories spawned in backlog with links back to this spike

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
