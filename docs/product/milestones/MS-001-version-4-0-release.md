# MS-001: Version 4.0 release

**Status:** active
**Owner:** Carson Sweet
**Depends on:** v4.0.0-beta (Phase 1) fully validated and tagged on feat/v4-phase1-backlog

## Outcome

Version 4.0 is the first SweetClaude release where the planning model is a first-class system citizen — not just documentation. Milestones, epics, backlog items, and roadmap views all speak the same typed vocabulary, enforce the same status state machine, and are served by native skills that read and write structured data rather than wrapping legacy text patterns.

A user on v4.0.0 (full release) gets:
- A roadmap system that mirrors the backlog structure and surfaces "what's next" without manual file maintenance
- A working `sweetclaude:milestones` skill that creates, tracks, and links milestones to product work
- Mode-aware skill behavior: Flow, Kanban, Shape Up, and Agile operating modes enforced in skills, not just documented
- Native skill rewrites that consume and produce typed v4 data (no wrapper indirection)
- A user guide that explains all of the above, including migration from v3

This milestone is **not** about shipping new product features to users' projects — it is about making SweetClaude itself reliable as a planning system.

## Measuring success

- [ ] `sweetclaude:milestones` skill exists and supports add/review/link/status/complete operations
- [ ] `docs/product/roadmap/` structure exists and is served by updated project-epics and project-sprints skills
- [ ] All four operating modes (Flow, Kanban, Shape Up, Agile) enforce their rules in relevant skills — not just described in docs
- [ ] Skills that create or update backlog items write v4-typed frontmatter natively (no wrapper conversion step)
- [ ] Status vocabulary is canonical and consistent: `big-picture`, `status`, and `recap` all agree on what "done" means
- [ ] Horizon taxonomy is documented, validated on authoring, and consistent with what skills render
- [ ] `docs/user-guide/planning-concepts.md` is current and accurate for all v4 behaviors
- [ ] `docs/user-guide/skills-reference.md` reflects all new and updated skills
- [ ] No stories scoped to MS-001 remain open at ship time

## Non-goals

- New product features for users' projects (personas, focus groups, corpus management, etc.) — those are post-4.0
- Shape Up betting table implementation (EP-010) — Phase 3
- Token efficiency or model-routing optimizations (STORY-004/005/006) — optimization, not blocking
- Cleanup skill (EP-011) — Phase 3
- Changing the v4 beta's Phase 1 behavior (migration, diagnose, migrate skill) — already shipped; fix-forward only

## Contributing work items

Existing stories:
- STORY-002 — Status consistency — canonical vocabulary, roll-up lint, and propagation prompts
- STORY-007 — Structured dependency field on backlog items, epics, and milestones
- STORY-008 — Execution sequence / tier field on epics and stories
- STORY-009 — Roadmap and aggregate listings consume sequence and dependency data
- STORY-010 — Document and refine horizon taxonomy (rename `next` → `now`, add docs and validation)

Phase 2 stories (new):
- STORY-011 — Roadmap system: docs/product/roadmap/ structure and routing skills
- STORY-012 — sweetclaude:milestones skill implementation
- STORY-013 — Mode-aware behavior enforcement (Flow / Kanban / Shape Up / Agile)
- STORY-014 — Native skill consolidation: wrapper-skills → native v4 implementations
- STORY-015 — planning-concepts.md model enforcement in skills (status state machine)
- STORY-016 — User guide for 4.0: planning-concepts.md, skills-reference.md, migration guide

## Notes

2026-05-13: Milestone created. Phase 1 (typed storage + migration tooling) is complete and tagged as v4.0.0-beta on feat/v4-phase1-backlog. This milestone tracks the Phase 2+ work needed to graduate from beta to full release. Stories 011–016 were written in this session to capture the work that has no stories yet.

## Changelog

| Version | Date | Change summary |
|---|---|---|
| 1.0 | 2026-05-13 | Initial draft — Phase 2 scope defined after Phase 1 beta |
