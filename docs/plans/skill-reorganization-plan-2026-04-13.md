# Skill Reorganization Plan — 2026-04-13

**Goal:** Restructure SweetClaude from the current code/strategy two-track model into a five-bucket architecture: strategy/, product/, design/, code/, deploy/ plus orchestration skills at root.

**Supersedes:** The code/strategy split from `docs/strategy-split-design-v1-2026-04-13.md`. That design introduced dual tracks. This plan replaces those two tracks with five domain buckets.

---

## Target Skill Map (45 skills)

### Orchestration (root) — 5 skills
| Skill | Status | Source |
|---|---|---|
| sweetclaude | Exists | Master router — needs update for 5-bucket routing |
| help | Exists | Needs updated command list |
| init | Exists | Needs updated directory scaffolding |
| new-task | Exists | Was work-router/start-task — needs updated classification |
| hibernate | Exists | No change |

### strategy/ — 8 skills
| Skill | Status | Source |
|---|---|---|
| strategy/concept | New | Articulate what this is and why it exists |
| strategy/pain-thesis | New | Structured pain analysis (user has guide) |
| strategy/ideal-customer-profile | New | Who has this pain and will pay/use |
| strategy/competitive-analysis | New | Strategic-level landscape, alternatives, differentiation |
| strategy/academic-research | Exists | Was strategy/academic — rename |
| strategy/meeting-prep | Designed | Interface contract in strategy-split-design |
| strategy/narrative-arc | Designed | Interface contract in strategy-split-design |
| strategy/market-messaging | New | External communications and positioning |

### product/ — 13 skills
| Skill | Status | Source |
|---|---|---|
| product/discovery | Exists | Was discover (root) — move into product/ |
| product/positioning-statement | New | How the product is positioned |
| product/product-brief | New wrapper | Delegates to bmad:product-brief |
| product/prd | New wrapper | Delegates to bmad:prd |
| product/user-story | New wrapper | Delegates to bmad:create-story |
| product/user-tdd-tests | Exists | Was code/gherkin-bridge — move + rename |
| product/user-success-criteria | New | Measurable success definitions per persona/task |
| product/user-workflows | New | Convert user stories to UX/UI flows |
| product/manage-scope | Exists | Was code/scope-tracker — move + rename |
| product/backlog | Exists | Was standalone backlog-management — move |
| product/sprint-plan | New wrapper | Delegates to bmad:sprint-planning |
| product/research | New wrapper | Delegates to bmad:research |
| product/feature-competitive | New | Product-level competitive feature analysis |

### design/ — 11 skills
| Skill | Status | Source |
|---|---|---|
| design/architecture | New wrapper | Delegates to bmad:architecture |
| design/tech-spec | New wrapper | Delegates to bmad:tech-spec |
| design/ux | New wrapper | Delegates to bmad:create-ux-design |
| design/solutioning-gate | New wrapper | Delegates to bmad:solutioning-gate-check |
| design/change-impact-analysis | Exists | Was code/ripple — move + rename |
| design/update-docs | Exists | Was code/auto-docs — move + rename |
| design/data-model | New | Schema design, entity relationships, migrations |
| design/api-design | New | Endpoint contracts, request/response, versioning |
| design/services-design | New | Service boundaries, communication patterns |
| design/infra-design | New | Infrastructure, deployment targets, environments |
| design/manage-decisions | New | Track design/architecture decisions with rationale (replaces ADR) |

### code/ — 8 skills
| Skill | Status | Source |
|---|---|---|
| code/tdd | Exists | No change |
| code/work-issue | Exists | Was code/fix-issue — rename |
| code/work-debt | New | Tech debt cleanup, lock behavior with tests first |
| code/pr-precheck | Exists | Was code/pr-ready — rename |
| code/qa-testing | New | Run test suites, report failures concisely |
| code/mutation-testing | Exists | No change |
| code/security-testing | New | Security review of code changes (was agent-only) |
| code/code-review | New | Adversarial code review (was agent-only) |

### deploy/ — deferred
Not scoped yet. Will cover PR finishing, CI/CD gates, verification, shipping.

---

## What Moves Where

### From current code/ (8 skills):
| Current | Destination |
|---|---|
| code/tdd | code/tdd (stays) |
| code/fix-issue | code/work-issue (rename) |
| code/pr-ready | code/pr-precheck (rename) |
| code/mutation-testing | code/mutation-testing (stays) |
| code/gherkin-bridge | product/user-tdd-tests (move + rename) |
| code/scope-tracker | product/manage-scope (move + rename) |
| code/ripple | design/change-impact-analysis (move + rename) |
| code/auto-docs | design/update-docs (move + rename) |

### From current strategy/ (2 skills):
| Current | Destination |
|---|---|
| strategy/reconciliation | **removed** — reconciliation becomes part of init workflow |
| strategy/academic | strategy/academic-research (rename) |

### From current root orchestration (5 skills):
| Current | Destination |
|---|---|
| sweetclaude | sweetclaude (stays) |
| help | help (stays) |
| init | init (stays) |
| new-task | new-task (stays) |
| discover | product/discovery (move) |
| hibernate | hibernate (stays) |

### From standalone skills:
| Current | Destination |
|---|---|
| backlog-management | product/backlog (move) |

---

## Summary

| Category | Exists | New | New Wrapper | Designed | Total |
|---|---|---|---|---|---|
| Orchestration | 5 | 0 | 0 | 0 | 5 |
| strategy/ | 1 | 5 | 0 | 2 | 8 |
| product/ | 4 | 3 | 4 | 0 | 11 |
| design/ | 2 | 5 | 4 | 0 | 11 |
| code/ | 4 | 4 | 0 | 0 | 8 |
| **Total** | **16** | **17** | **8** | **2** | **43** |

Note: Product total shows 11 not 13 — product/user-success-criteria and product/user-workflows are new, bringing it to 13. Table corrected below.

| Category | Total |
|---|---|
| Orchestration | 5 |
| strategy/ | 8 |
| product/ | 13 |
| design/ | 11 |
| code/ | 8 |
| **Total** | **45** |

---

## Execution Phases

### Phase 1: Directory restructure
- Create strategy/, product/, design/, code/ directories under framework/skills/
- Move existing skills to new locations with new names
- Update all frontmatter name fields
- Update phase-skills.yaml for 5-bucket model
- Update phase-gates.md
- Update master SKILL.md routing
- Update help skill with new command list
- Update preflight guards in all moved skills
- Remove old directories (code/, strategy/ from current structure)
- Sync to installed

### Phase 2: Rename existing skills
- code/fix-issue → code/work-issue
- code/pr-ready → code/pr-precheck
- code/gherkin-bridge → product/user-tdd-tests
- code/scope-tracker → product/manage-scope
- code/ripple → design/change-impact-analysis
- code/auto-docs → design/update-docs
- strategy/academic → strategy/academic-research
- discover → product/discovery

### Phase 3: Build BMAD wrappers
- product/product-brief (wraps bmad:product-brief + preflight guard)
- product/prd (wraps bmad:prd)
- product/user-story (wraps bmad:create-story)
- product/sprint-plan (wraps bmad:sprint-planning)
- product/research (wraps bmad:research)
- design/architecture (wraps bmad:architecture)
- design/tech-spec (wraps bmad:tech-spec)
- design/ux (wraps bmad:create-ux-design)
- design/solutioning-gate (wraps bmad:solutioning-gate-check)

### Phase 4: Build new skills (priority order)
1. strategy/concept — foundational, everything else references it
2. strategy/pain-thesis — user has a guide ready
3. strategy/ideal-customer-profile — feeds product/discovery
4. code/work-debt — common workflow, straightforward
5. code/qa-testing — common workflow
6. code/security-testing — promote from agent to skill
7. code/code-review — promote from agent to skill
8. product/positioning-statement
9. product/user-success-criteria
10. product/user-workflows
11. product/feature-competitive
12. design/data-model
13. design/api-design
14. design/services-design
15. design/infra-design
16. design/manage-decisions
17. strategy/market-messaging

### Phase 5: Update docs
- README.md — new bucket structure, updated command list, user help
- Architecture doc — new skill map, component list, phase-skill mapping
- PRD — new epics for product/, design/ buckets
- Strategy-split design — mark as superseded by this plan
- Reconciliation plan — update to reference new structure

---

## Config Changes

### phase-skills.yaml
Replace `code:` and `strategy:` tracks with five bucket keys. The new-task skill classifies into one of the five buckets and surfaces appropriate skills.

### phase-gates.md
Update available skills per phase to reference new paths.

### model-routing.yaml
Add routing for new skills.

### defaults.yaml
No change expected.
