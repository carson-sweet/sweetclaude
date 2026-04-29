# SweetClaude Artifact Inventory

Version 1 — 2026-04-14

Every artifact the SweetClaude pipeline produces. Work items follow different workflows depending on type (bug-fix, net-new-feature, tech-debt, hotfix, etc.) — phases vary by work type. **Bold** items are always produced for that phase. Regular items are conditional on project type or user choice.

---

## Cross-Phase (always present)

| File | Format | Description |
|------|--------|-------------|
| **`.sweetclaude/state/phase.yaml`** | YAML | Schema v2: `version_stage` (lifecycle stage), `last_work_item_id` (monotonic ID counter), `active_work_item` (id, type, workflow, phase, title, started, entry_category), deference level, project type |
| **`.sweetclaude/state/decision-log.md`** | Markdown | Numbered decisions with context, options considered, rationale |
| **`.sweetclaude/state/assumption-register.md`** | Markdown | Active, confirmed, and rejected assumptions with evidence |
| **`.sweetclaude/state/improvement-register.md`** | Markdown | Process feedback — what's working, what to change, check-in log |
| **`CLAUDE.md`** (generated/updated by init) | Markdown | Project rules, build commands, repo structure, SweetClaude config |
| `.sweetclaude/state/john-wick.yaml` | YAML | John Wick mode pipeline state: current phase, step, gate status, session tracking, locked test files. Created on first John Wick run. |
| `.sweetclaude/state/compliance-context.yaml` | YAML | Compliance requirements derived from product discovery (regulatory, security, accessibility). Created during John Wick Bootstrap phase (step B4). |

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
| **`.sweetclaude/state/scope-changes.md`** | Always (3+ out-of-scope items required) | Scope moves with direction, phase, rationale, date |
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
| Solutioning gate results in decision log | Complex work | Validates design against PRD, identifies risks, records gate pass/fail |

---

## Phase 4: PLAN

| File | When produced | Description |
|------|---------------|-------------|
| **`.sweetclaude/stories/EPIC-XXX/story-XXX.md`** | Always | User story with acceptance criteria, linked to epic and PRD |
| **`.sweetclaude/traceability/requirements-map.md`** (started) | Always | Requirement to story to test to implementation mapping |
| `.sweetclaude/stories/EPIC-XXX/story-XXX.feature` | TDD Level 3 only | Gherkin scenarios: Given/When/Then for happy path, errors, edge cases |
| `.sweetclaude/specs/workflows/{story-title}.md` | If user workflows requested | Step-by-step user path through the interface per story |
| Sprint plan (via bmad) | Team projects only | Selected stories, scope estimate, team capacity, sprint commitment |

---

## Phase 5: IMPLEMENT

| File | When produced | Description |
|------|---------------|-------------|
| **Test files** (language-native, project convention) | Always | Behavioral specs: happy path, validation, edge cases, side effects |
| **Source code** | Always | Implementation satisfying acceptance criteria and passing all tests |
| **Git commits** (conventional format) | Always | RED commits (failing tests), then GREEN commits (implementation) |
| `.sweetclaude/traceability/ripple-map.md` | Changes to existing code | Change-impact analysis: affected files, tests, docs, risk level |

---

## Phase 6: VERIFY

| File | When produced | Description |
|------|---------------|-------------|
| **Code review findings** (presented, not persisted as file) | Always | Logic errors, edge cases, regressions, performance, error handling |
| **`.sweetclaude/traceability/requirements-map.md`** (completed) | Always | All columns filled, full requirement-to-implementation tracing |
| **Documentation updates** (README, CLAUDE.md, etc.) | Always | Stale docs identified and updated to reflect implementation |
| **PR template filled** | Always | What, why, scope, how to verify, rollout plan, security checklist |
| Security review findings | If security-relevant changes | Auth, injection, secrets, tenant boundaries, dependency vulnerabilities |
| Mutation testing report | If TDD Level 3 or requested | Mutation score, surviving mutants with location and type |
| QA test report | If requested | Pass/fail summary with failure details (file, line, assertion) |

---

## Phase 7: SHIP

| File | When produced | Description |
|------|---------------|-------------|
| **Pull request** (GitHub/GitLab) | Always | Merged PR with linked issues and approval |
| Post-deploy verification report | If deployed service | Health checks, user-facing behavior verification, rollback readiness |

---

## Summary

- **Always produced** (net-new project, full run): ~20 artifacts
- **Conditionally produced**: ~15-20 more depending on project type (API, DB, UI, microservices, academic)
- **Formats**: ~85% Markdown, plus YAML (state), Gherkin (.feature), and language-native code (tests/implementation)
- **Storage**: Everything lives under `.sweetclaude/`, `strategy/`, or the project source tree
