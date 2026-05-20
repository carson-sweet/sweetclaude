---
id: STORY-013
type: story
title: Mode-aware behavior enforcement — Flow / Kanban / Shape Up / Agile rules in
  skills
status: new
priority: soon
effort: l
epic: EP-004
sprint: null
tags:
- modes
- flow
- kanban
- shape-up
- agile
- enforcement
- planning-concepts
- v4-phase2
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
epic_sequence: 1
---

## Description

As a SweetClaude user on a project in Kanban mode, I want the framework's skills to actually enforce Kanban rules (WIP limit, no sprints, continuous delivery) — not just describe them in a doc — so that the operating mode I chose is a real behavioral constraint, not a label.

**The gap today:** `docs/user-guide/planning-concepts.md` documents all four operating modes with their rules. `effective-gates.yaml` provides some mode-based gating at the bootstrap layer. But most skills that create, list, or update work items (`go`, `big-picture`, `project-sprints`, `product-milestones`, `code-feature`) do not consult the active mode when deciding what actions to offer or block. A user on Kanban mode can still be offered sprint-planning actions. A user on Shape Up mode can still be pushed toward a velocity chart.

### Mode rules to enforce (per planning-concepts.md)

**Flow:**
- No sprints surfaced or created
- No velocity tracking
- `go` does not route to sprint-planning skills
- `big-picture` does not show sprint burn-down

**Kanban:**
- WIP limit enforced: `go` and `code-feature` warn when active item count ≥ 3 before starting new work
- No sprints surfaced or created
- `project-issues` surfaces blocked items in the leading position

**Shape Up:**
- `go` routes through pitch → betting table gate → 6-week cycle container (cycle container is a stub for Phase 3; gate behavior ships in this story)
- `product-milestones` and `project-epics` do not offer sprint planning
- Cycle length is fixed at 6 weeks (no override without explicit user acknowledgement)

**Agile:**
- `go` blocks IMPLEMENT phase work if no active sprint exists (already in effective-gates.yaml; this story confirms it's wired in skills too)
- `project-sprints` is the entry point for sprint management — surfaced in `go` routing
- Velocity is tracked on sprint close

### Implementation approach

Read `active_mode` from `.sweetclaude/state/sweetclaude.yaml` at the top of each affected skill. Existing `effective-gates.yaml` `blocked_skills` mechanism can carry some of this. For skills that need more nuanced behavior (offering or hiding specific actions), inline the mode check in the skill's routing logic.

## Acceptance Criteria

- [ ] A project in Kanban mode: `sweetclaude:go` does not offer sprint-related actions; warns before starting a 4th concurrent item
- [ ] A project in Flow mode: `sweetclaude:big-picture` output has no sprint column or velocity row
- [ ] A project in Shape Up mode: `sweetclaude:go` routes through pitch context before IMPLEMENT, and blocks a second simultaneous cycle without explicit user override
- [ ] A project in Agile mode: `sweetclaude:go` blocks IMPLEMENT if no sprint is active (confirmed in skill, not just in effective-gates.yaml)
- [ ] All mode rules from `docs/user-guide/planning-concepts.md` are accounted for — either enforced in a skill or explicitly marked "Phase 3" in a non-goal

## Out of scope

- Shape Up 6-week cycle container implementation (Phase 3 / EP-010)
- Velocity chart UI
- Mode migration tooling (users switch modes via `/sweetclaude:project-mode`; this story does not change that flow)

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
