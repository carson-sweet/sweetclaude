---
id: STORY-011
type: story
title: Roadmap system — docs/product/roadmap/ structure and routing in go/big-picture/code-issue
status: new
priority: now
effort: xl
epic: EP-002
sprint: null
tags:
- roadmap
- epics
- objectives
- big-picture
- go
- v4-phase2
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
epic_sequence: 2
---

## Description

As a SweetClaude user on v4, I want `docs/product/roadmap/` to hold structured epic files so that skills can render and navigate the roadmap from typed data — rather than from the `.sweetclaude/product/milestones/` markdown files that are now the source material, not the primary structure.

**Design decisions (DEC-24, DEC-25, DEC-29):** Epics are capability areas, not version containers. Each epic has one objective (its success criteria). Version (target release) is metadata on the epic. The planning hierarchy is Release → Epic (with Objective) → Stories. There is no separate milestone layer. The existing MS-007 through MS-042 files are source material for populating epic objectives — they define the phase-gate completion criteria that will become objectives when epics are created.

### Storage model to create

```
docs/product/roadmap/
  ROADMAP-INDEX.md               Master index (table of epics, status, target release)
  epics/
    EP-001-slug.md               One file per epic (typed frontmatter)
    done/
```

Epic file frontmatter:
```yaml
---
id: EP-NNN
type: epic
title: "..."
status: new | active | done | paused
target_release: "4.1" | null
objective: "One sentence — what done looks like for this epic"
completion_criteria:
  - "Discovery complete"
  - "Design consensus reached"
  - "Implementation complete and passing regression suite"
  - "Docs and changelog updated"
depends_on: [EP-NNN, ...]
stories: [STORY-NNN, ...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

**Note on completion_criteria:** These are drawn from the current MS-007 through MS-042 milestone chains. Each milestone in a version chain (discovery → taxonomy → state model → spec → implementation → review → regression → release) becomes a completion criterion on the corresponding epic. The four initial epics and their source milestone ranges:
- Workflow Engine (EP-001): MS-007 through MS-015
- Release Primitive (EP-002): MS-016 through MS-025
- Planning Workflows (EP-003): MS-026 through MS-033
- Mode Enforcement (EP-004): MS-034 through MS-042

### Skills to update

- `sweetclaude:go` — roadmap routing reads `docs/product/roadmap/epics/` for epic context; routes by capability not by milestone
- `sweetclaude:big-picture` — renders roadmap from epic files; shows completion criteria progress instead of milestone chain
- `sweetclaude:code-issue` — links work items to epics by ID, reads epic status from files

### Relationship to other stories

- Depends on STORY-007 (structured dependency field) for the `depends_on` field
- Required by STORY-009 (aggregate listings) — STORY-009 is the rendering layer; this story is the schema layer
- Required by STORY-012 (epic/objective management skill) — skill writes to the schema this story defines

## Acceptance Criteria

- [ ] `docs/product/roadmap/epics/` directory exists with typed frontmatter schema documented in SCHEMA.md
- [ ] Four initial epic files created (Workflow Engine, Release Primitive, Planning Workflows, Mode Enforcement) with `completion_criteria` drawn from corresponding MS-007–MS-042 milestone chains
- [ ] `sweetclaude:big-picture` reads epic status and completion criteria from `docs/product/roadmap/epics/EP-*.md` files; no longer renders the MS-007+ proposed milestone chain
- [ ] `sweetclaude:go` routes to the right epic context from `docs/product/roadmap/` state
- [ ] `docs/product/roadmap/SCHEMA.md` documents epic frontmatter fields, valid status values, and the link model between epics and stories
- [ ] `ROADMAP-INDEX.md` renders epics grouped by status, showing objective and completion progress per epic

## Out of scope

- Sprint planning ceremonies
- Shape Up betting table
- Automated sequencing recommendations
- Removing or archiving MS-007 through MS-042 — they remain as historical source material

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
