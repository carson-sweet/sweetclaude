# SweetClaude Deliverables Inventory

Version 1 — 2026-04-14

User-facing deliverables only — no state files, traceability infrastructure, or internal pipeline artifacts. **Bold** items are always produced for that phase. Regular items are conditional on project type or user choice.

---

## Phase 1: DISCOVER

| File | When produced | Description |
|------|---------------|-------------|
| **`strategy/concept.md`** | Always | One-sentence description, problem statement, key assumptions, boundaries |
| **`.sweetclaude/brainstorm/personas.md`** | Always (net-new) | User personas with job title, tasks, and success criteria per task |
| **`.sweetclaude/brainstorm/feature-list.md`** | Always (net-new) | Core features with include/exclude rationale |
| `strategy/pain-thesis.md` | If user accepts offer | 11-section narrative diagnostic of whether the problem is worth solving |
| `strategy/ideal-customer-profile.md` | If user accepts offer | Demographics, behaviors, triggers, deal-breakers, anti-profile |
| `strategy/competitive-analysis.md` | If user accepts offer | Landscape scan, SWOT, market dynamics, differentiation opportunities |
| `.sweetclaude/brainstorm/competitive-analysis.md` | If competitive analysis done during discovery | Competitor list and deep-dive analysis from discovery interviews |
| `strategy/feature-competitive.md` | If product-level feature comparison requested | Feature matrix vs. competitors, table-stakes, differentiator gaps |
| `strategy/narrative-arc/arc.md` | If strategy-heavy project needs claim tracking | Knowledge graph connecting objectives, claims, proof points, evidence |
| `strategy/meeting-prep/{stakeholder}-{date}-debrief.md` | If meeting prep requested | Agenda, talking points with confidence levels, key asks, debrief notes |
| `strategy/academic/{paper-slug}-submission-tracker.md` | If academic research project | Six-phase academic pipeline tracker from thesis through submission |

---

## Phase 2: DEFINE

| File | When produced | Description |
|------|---------------|-------------|
| **`.sweetclaude/specs/product-brief.md`** | Always (net-new) | 11-section brief: problem, audience, solution, scope, risks, success criteria |
| **`.sweetclaude/specs/user-success-criteria.md`** | Always (net-new) | Binary pass/fail success criteria per persona and task |
| `.sweetclaude/specs/prd.md` | Larger work requiring FRs/NFRs/epics | Functional requirements, non-functional requirements, epics, traceability |
| `strategy/positioning-statement.md` | If positioning work done | For/Who/Product/That/Unlike/We positioning with supporting claims |

---

## Phase 3: DESIGN

| File | When produced | Description |
|------|---------------|-------------|
| **`.sweetclaude/specs/architecture.md`** | Features requiring architecture | Components, boundaries, communication patterns, data flow |
| **`.sweetclaude/specs/tech-spec.md`** | Features requiring technical design | Data structures, algorithms, error handling, edge cases |
| `.sweetclaude/specs/ux-design.md` | If UI/UX involved | Wireframes, interaction patterns, navigation, user flows |
| `.sweetclaude/specs/data-model.md` | If database changes | Entities, relationships, schema, constraints, indexes, migration strategy |
| `.sweetclaude/specs/api-design.md` | If API endpoints | Routes, request/response shapes, auth, pagination, error responses |
| `.sweetclaude/specs/services-design.md` | If microservices | Service inventory, ownership, communication patterns, boundaries |
| `.sweetclaude/specs/infra-design.md` | If new infrastructure | Deployment targets, environments, CI/CD, monitoring, scaling, rollback |

---

## Phase 4: PLAN

| File | When produced | Description |
|------|---------------|-------------|
| **`.sweetclaude/stories/EPIC-XXX/story-XXX.md`** | Always | User story with acceptance criteria, linked to epic and PRD |
| `.sweetclaude/stories/EPIC-XXX/story-XXX.feature` | TDD Level 3 only | Gherkin scenarios: Given/When/Then for happy path, errors, edge cases |
| `.sweetclaude/specs/workflows/{story-title}.md` | If user workflows requested | Step-by-step user path through the interface per story |

---

## Phase 5: IMPLEMENT

| File | When produced | Description |
|------|---------------|-------------|
| **Test files** (language-native, project convention) | Always | Behavioral specs: happy path, validation, edge cases, side effects |
| **Source code** | Always | Implementation satisfying acceptance criteria and passing all tests |

---

## Phase 6: VERIFY

| File | When produced | Description |
|------|---------------|-------------|
| **Pull request** (filled template) | Always | What, why, scope, how to verify, rollout plan, security checklist |

---

## Phase 7: SHIP

| File | When produced | Description |
|------|---------------|-------------|
| **Pull request** (merged) | Always | Merged PR with linked issues and approval |
