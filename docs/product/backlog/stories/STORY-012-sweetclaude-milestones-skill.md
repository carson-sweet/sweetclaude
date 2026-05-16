---
id: STORY-012
type: story
title: Epic and objective management skill — add/review/link/status/complete operations
status: new
priority: now
effort: l
epic: EP-002
sprint: null
tags:
- skill
- epics
- objectives
- roadmap
- always-loaded
- v4-phase2
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
epic_sequence: 3
---

## Description

As a SweetClaude user, I want a `sweetclaude:epics` skill that I can use to create, review, and track epics and their completion criteria (objectives), so that I have a single command for epic lifecycle management rather than hand-editing markdown files.

**Design decisions (DEC-24, DEC-25, DEC-29):** Epics are capability areas. Each epic has one objective (a success statement) and a set of completion criteria (phase-gate checklist). Version is metadata. There is no separate milestone layer — what were previously called milestones are now completion criteria on epics. The skill writes to the `docs/product/roadmap/epics/` schema defined by STORY-011.

**Note on prior design reference:** `docs/internal/milestones-skill-design-v1-2026-04-20.md` was written before DEC-24/25/29. It describes a milestone-centric model that has since been superseded. Use it as background only; the schema and operations below are authoritative.

### What the skill does

`sweetclaude:epics` is an always-loaded cross-cutting skill (present in every phase, every mode). It provides:

- **`add`** — create a new epic (prompts for title, objective/success statement, completion criteria, target release, depends-on). Assigns next EP-NNN ID. Defaults to status `new`. Writes to `docs/product/roadmap/epics/EP-NNN-slug.md` and updates `ROADMAP-INDEX.md`.
- **`review`** — list epics grouped by status (active → now, new → upcoming, done → shipped). Shows completion criteria met / total and open linked stories per epic. Hides done by default; `review --all` shows them.
- **`link <work-item> <EP-NNN>`** — bidirectional link: sets `epic: EP-NNN` in the work item frontmatter, adds item to epic's `stories:` list. Prompts before overwriting an existing epic link.
- **`status <EP-NNN>`** — detailed view: title, objective, target release, completion criteria with per-criterion done state (derived from linked story status), linked stories with per-story status.
- **`complete <EP-NNN>`** — marks epic done. Checks that all completion criteria are satisfied (user can override with explicit acknowledgement). Writes `done` status and `closed_date`.

### Storage schema

Follows the epic frontmatter schema defined in STORY-011. Depends on STORY-011 being implemented first.

### Phase-skills registration

Add to `config/phase-skills.yaml` under `always_loaded`:
```yaml
- sweetclaude:epics
```

## Acceptance Criteria

- [ ] `skills/epics/SKILL.md` exists with all five operations documented and implemented
- [ ] `sweetclaude:epics add` creates a well-formed EP-NNN file in `docs/product/roadmap/epics/` and updates `ROADMAP-INDEX.md`
- [ ] `sweetclaude:epics review` correctly renders active epics in "Now" group and new in "Upcoming" group, with completion criteria progress shown
- [ ] `sweetclaude:epics link STORY-002 EP-001` sets `epic: EP-001` in STORY-002 frontmatter AND adds STORY-002 to EP-001's `stories:` list (bidirectional)
- [ ] `sweetclaude:epics status EP-001` shows correct completion criteria state derived from linked story statuses
- [ ] Skill is registered in `config/phase-skills.yaml` as `always_loaded`
- [ ] Installed mirror synced after implementation

## Out of scope

- Automated completion-criteria inference from CI or external tools
- Multi-owner or RACI modeling
- Epic-to-epic dependency visualization
- Sprint planning (separate concern)

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
