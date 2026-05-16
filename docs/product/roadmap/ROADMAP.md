# SweetClaude Roadmap

**Last updated:** 2026-05-15
**Current version:** 4.0.x-beta

---

## 4.1 — Major improvements to development workflows

1. Discovery complete — workflow gaps catalogued from real sessions, step-skip and quality failure patterns documented
2. Workflow taxonomy finalized — 15 workflow types (3 planning, 12 execution), step sequences and gate requirements agreed for each
3. State model designed — how workflow progress is stored, surfaced, and enforced across sessions agreed
4. Design consensus reached — technical approach reviewed, no unresolved structural questions
5. Technical spec approved
6. Workflow state infrastructure implemented — state tracking, gate enforcement, session continuity
7. All 12 execution workflow types implemented and enforced in skills
8. Code review complete, security review complete, all findings addressed
9. Behavioral regression suite updated and passing
10. Docs and changelog updated — release ready

---

## 4.2 — Major improvements to release and roadmap planning

1. Discovery complete — milestone/roadmap structural gaps catalogued, current user mental model documented
2. Release primitive designed — data model, milestone ownership, status computation approach agreed
3. Design consensus reached — skill interfaces, file structure, canonical status vocabulary agreed
4. Technical spec approved
5. Release primitive implemented — data model and state machine
6. Milestone and roadmap skills updated to reflect new structure
7. Status, big-picture, and recap skills compute from new structure
8. Code review complete, security review complete, all findings addressed
9. Behavioral regression suite updated and passing
10. Docs and changelog updated — release ready

---

## 4.3 — Major improvements to discovery and planning workflows

1. Discovery complete — how planning workflows currently break down, what structured completion looks like for each type
2. Planning workflow types defined — new-feature-area, course-correction, release-planning step sequences and story outputs agreed
3. Design consensus reached — how planning workflows connect to execution workflows and the release model
4. Technical spec approved
5. Planning workflow state model implemented
6. All 3 planning workflow types implemented and enforced in skills
7. Code review complete, security review complete, all findings addressed
8. Behavioral regression suite updated and passing
9. Docs and changelog updated — release ready

---

## 4.4 — Major improvements to operating mode behavior

1. Discovery complete — how each mode (Flow, Kanban, Shape Up, Agile) should differ in workflow availability, step requirements, and gate behavior
2. Mode-workflow mapping designed — which workflow types each mode enables, what mode-specific gates look like
3. Design consensus reached — enforcement model agreed, edge cases resolved
4. Technical spec approved
5. Mode enforcement implemented in workflow state model
6. All 4 modes implemented and enforced across relevant skills
7. Code review complete, security review complete, all findings addressed
8. Behavioral regression suite updated and passing
9. Docs and changelog updated — release ready
