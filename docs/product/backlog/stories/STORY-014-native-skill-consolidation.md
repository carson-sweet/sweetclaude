---
id: STORY-014
type: story
title: Native skill consolidation — replace wrapper-skills with v4-native implementations
status: new
priority: later
effort: xl
epic: null
milestone: MS-001
sprint: null
tags: [skills, native, wrapper, consolidation, refactor, v4-phase2]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
---

## Description

As a SweetClaude developer, I want skills that currently wrap v3 BMAD/legacy patterns to be replaced with v4-native implementations that read and write typed frontmatter directly, so that the v4 data model is the actual source of truth — not a layer behind a compatibility shim.

**Design reference:** `docs/internal/native-skills-redesign-draft-v1.0-20260426.md` contains the full redesign spec for the 10 skills targeted.

**The problem with wrappers:** Phase 1 introduced typed storage (`docs/product/backlog/`) and migration tooling. But several skills still construct their data by parsing legacy-format markdown headers (`**Status:**`, `**Horizon:**`) or by writing to `.sweetclaude/artifacts/` paths from v3. These skills work, but they bypass the v4 schema — meaning the frontmatter added by Phase 1 is never read by the skills the user actually invokes. The v4 data model is inert until skills consume it natively.

### Target skills (from the redesign doc)

The 10 wrapper-skills to replace with native v4 implementations. Each reads/writes from `docs/product/backlog/` (stories, bugs, debt, chores), `docs/product/roadmap/` (epics, sprints), and `docs/product/milestones/` — using PyYAML frontmatter round-trips, never regex-on-markdown.

Skills (confirm exact list against native-skills-redesign-draft at implementation time):
1. `product-parking-lot` → reads/writes `docs/product/backlog/` natively
2. `project-issues` → reads from typed bug/debt/chore files
3. `project-epics` → reads/writes `docs/product/roadmap/epics/`
4. `project-sprints` → reads/writes `docs/product/roadmap/sprints/`
5. `product-milestones` → reads/writes `docs/product/milestones/` (aligns with STORY-012)
6. `big-picture` → aggregates from all typed sources; no inline state
7. `go` → routing reads typed frontmatter (phase, status, mode) — no string parsing
8. `code-feature` → creates typed story files in `docs/product/backlog/stories/`
9. `code-issue` → creates typed bug/debt files; links to epics by ID
10. `new-task` → creates backlog items with correct type, ID, and frontmatter

### Sequencing

Each skill is independently replaceable. Suggested order: `code-feature` and `new-task` first (smallest surface), `big-picture` and `go` last (largest, highest risk). Each skill gets its own commit.

## Acceptance Criteria

- [ ] All 10 target skills read backlog/roadmap/milestone data from typed frontmatter files — no regex parsing of `**Status:**` or `**Horizon:**` style headers
- [ ] All 10 target skills write new items to the correct v4 typed path with correct frontmatter
- [ ] `sweetclaude:big-picture` renders exclusively from `docs/product/backlog/`, `docs/product/roadmap/`, and `docs/product/milestones/` — no fallback to v3 artifact paths
- [ ] `sweetclaude:go` routing logic reads `status:` from typed frontmatter, not markdown body text
- [ ] Installed mirrors are in sync for all 10 skills
- [ ] No regression in behavior for users running the skills on a v4-migrated project

## Out of scope

- Skills not in the 10-skill target list from the redesign doc
- v3 → v4 migration tooling (already shipped in Phase 1)
- Shape Up / betting table skill rewrites (Phase 3)

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
