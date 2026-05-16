---
id: STORY-003
type: story
title: "New skill: sweetclaude:plan-wave-sequencing — design-first milestone resequencing"
status: new
priority: later
effort: xl
epic: null
milestone: null
sprint: null
tags: [skill, planning, milestones, epics, backlog, dependency-graph, design-first]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
---

## Description

As a user running a nontrivial milestone, I want a skill that reads all backlog items bound to that milestone, classifies them as design-heavy vs implementation-heavy, finds unbound success criteria, builds a dependency graph, and proposes a wave-ordered execution plan — so that I don't spend multiple hours doing this manually with a high-reasoning model on every planning cycle.

**Origin:** Filed 2026-05-13 by Carson Sweet. Derived from a real MS-003 replanning session in `~/dev/syncog` that took multiple hours and produced: milestone split (MS-003 local-alpha, MS-006 cloud-alpha), 9 unbound-criterion BLs identified, 3 new epics created, 14 new BLs, 3 priority bumps. All generic project-management work that a skill should automate.

**The gap today:** No existing skill does this.
- `product-sprint-plan` — sprint scoping, not wave/design separation
- `epic-design` — single-epic story breakdown, not cross-epic sequencing
- `ultraplan` — one-shot artifact ingestion, not continuous milestone resequencer
- `design-change-impact-analysis` — affects-what analysis, not forward-sequence planning

### Proposed skill: `sweetclaude:plan-wave-sequencing`

**Inputs:**
- A target milestone (MS-NNN)
- Optional: model-tier hint (e.g. "design wave = Opus, impl wave = Sonnet")

**Process:**
1. Read milestone success criteria; identify which criteria have no BL bound (the unbound-criteria scan)
2. Read every BL bound to the milestone; classify each:
   - Pure design (ADR, spec, contract, UX flow)
   - Pure implementation (TDD against a spec that already exists)
   - Mixed (currently combines design + implementation in one BL)
3. For mixed BLs, propose splitting into design + impl halves with new BL IDs
4. Build a dependency graph across BLs and epics: explicit `Depends on` fields, implicit dependencies inferred from referenced ADRs / contracts / shared services
5. Topologically sort into waves: Wave 0 (no upstream design dependencies), Wave 1 (depends only on Wave 0 design), Wave 2+ as needed
6. Within each wave, identify parallelizable groups vs sequential chains
7. Present the proposed plan via AskUserQuestion: accept / accept-with-edits / something-else
8. On accept: bump priorities, create new BLs for unbound criteria and split impl halves, update epic issue lists, update milestone contributing work items list, update BACKLOG-INDEX.md
9. Stamp a milestone changelog entry recording the wave structure

**Output artifacts:**
- Updated milestone file with Wave 0 / Wave 1 contributing-work-items sections
- New BL files for previously-unbound criteria
- New BL files for split impl halves
- Updated epic files with Wave 0 / Wave 1 issue lists
- Updated BACKLOG-INDEX.md
- A one-screen wave-sequence summary saved to the milestone or to a planning artifact

**Relationship to STORY-004/005:** If per-skill model declarations (STORY-004) ship first, this skill should be classified `reasoning: high` (dependency-graph reasoning + classification + sequencing).

## Acceptance Criteria

- [ ] Running the skill against an existing milestone with mixed-scope BLs and unbound criteria produces, in one invocation, the exact set of file edits a human would make over a multi-hour planning session — without manual file-by-file editing
- [ ] The skill is idempotent: running it twice does not duplicate BL IDs or shuffle already-wave-sorted items
- [ ] The skill respects existing priorities except where wave-entry (Wave 0) items must rise to P0
- [ ] The dependency graph handles at minimum: explicit `Depends on` field references and BLs that reference the same ADR or contract document
- [ ] The skill presents its proposed plan for user approval before writing any files (no silent file creation)

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
