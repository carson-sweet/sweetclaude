# Routing Tables — work-type → skill mapping

**Sections:**
- [strategy/](#strategy--why-it-matters-and-to-whom) — concept, persona, competitive, security planning
- [product/](#product--what-to-build-and-why) — feature/PRD/brief/stories, scope, sprints
- [design/](#design--how-its-structured) — architecture, tech-spec, UX, API, data model
- [code/](#code--writing-and-verifying-code) — feature, bug, hotfix, debt, migration, deps
- [project/](#project--managing-the-work) — issues, epics, sprints, backlog, roadmap
- [testing/](#testing--validating-the-work) — plan, security, compliance, QA, perf, a11y
- [operations/](#operations--keeping-it-running) — incidents, postmortem, break-glass
- [system/](#system--managing-the-framework) — setup, init, off, update, fix, purge, audit
- [Plan 3 fallbacks](#plan-3-fallbacks)

Eight buckets. Each row maps a work type to the skill that handles it, plus the template phases for that work type's workflow. Use these tables in step 4 of the find-skill algorithm.

**Visibility per `version_stage`:**
- **PROTOTYPE:** strategy + product
- **ALPHA:** strategy + product + design + code
- **BETA / GA / SCALED:** all buckets
- **MAINTAINED:** code + operations only
- **system/** is always visible

**Plan 3 marker:** `*(Plan 3)*` means the skill is planned but not built. Use the fallback in step 6.

---

## strategy/ — why it matters and to whom

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Concept articulation / framing | DISCOVER, DEFINE, SHIP | `sweetclaude:product-discovery` *(fallback — `sweetclaude:concept-framing` planned, see ISSUE-008)* |
| Pain analysis | DISCOVER, DEFINE, SHIP | `sweetclaude:product-discovery` |
| Customer profiling | DISCOVER, DEFINE, SHIP | `sweetclaude:user-personas` |
| Synthetic panel research / concept testing | DISCOVER, DEFINE | `sweetclaude:product-user-focus-group` *(requires validated personas — gate enforced)* |
| Competitive landscape | DISCOVER, DEFINE, SHIP | `sweetclaude:product-competition` |
| Research / deep research | DISCOVER, DEFINE, SHIP | `sweetclaude:documents-academic-research` |
| Meeting preparation | DEFINE | `sweetclaude:misc-meeting-prep` |
| Market messaging | DEFINE | `sweetclaude:product-market-messaging` |
| Security planning | DISCOVER, DEFINE, SHIP | `sweetclaude:security-planning` *(Plan 3)* |
| Course correction | DISCOVER, DEFINE, TRIAGE, SHIP | `sweetclaude:course-correction` *(Plan 3)* |

## product/ — what to build and why

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Net-new feature | DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:product-discovery` |
| Large story / high-rigor story | DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:large-story` |
| Enhancement / iteration | DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:product-prd` |
| Product brief | DEFINE | `sweetclaude:product-brief` |
| Requirements / PRD | DEFINE | `sweetclaude:product-prd` |
| User stories | PLAN | `sweetclaude:product-user-stories` |
| Test specs from stories | PLAN | `sweetclaude:product-user-tdd-tests` |
| Scope change | any | `sweetclaude:product-manage-scope` |
| Parking lot / deferred ideas | any | `sweetclaude:product-parking-lot` |
| Sprint / release planning | DEFINE, PLAN, SHIP | `sweetclaude:product-sprint-plan` |
| Market / technical research | DISCOVER | `sweetclaude:product-research` |
| Release planning | DEFINE, PLAN, SHIP | `sweetclaude:release-planning` *(Plan 3)* |

## design/ — how it's structured

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| System architecture | DESIGN | `sweetclaude:design-architecture` |
| Technical specification | DESIGN | `sweetclaude:design-tech-spec` |
| UX/UI design | DESIGN | `sweetclaude:design-ux` |
| Solution validation | DESIGN | `sweetclaude:design-solutioning-gate` |
| Impact analysis | any | `sweetclaude:design-change-impact-analysis` |
| Doc updates | VERIFY | `sweetclaude:documents-update-docs` |
| Data model / schema | DESIGN | `sweetclaude:design-data-model` |
| API design | DESIGN | `sweetclaude:design-api-design` |
| Record a decision | any | `sweetclaude:design-manage-decisions` |
| Onboarding flow design | DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:onboarding-flow-design` *(Plan 3)* |

## code/ — writing and verifying code

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Net-new feature (implement) | IMPLEMENT | `sweetclaude:code-feature` |
| Bug fix | DIAGNOSE, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-issue` |
| Enhancement | IMPLEMENT | `sweetclaude:code-issue` |
| Tech debt / refactor | DEFINE, SCOPE, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-debt` |
| Hotfix | DIAGNOSE, IMPLEMENT, SHIP, POST-MORTEM | `sweetclaude:hotfix` *(Plan 3)* |
| Security patch | DIAGNOSE, IMPLEMENT, VERIFY, SHIP | `sweetclaude:security-patch` *(Plan 3)* |
| Performance optimization | DIAGNOSE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-issue` |
| External integration | DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:external-integration` *(Plan 3)* |
| Technology migration | ASSESS, DESIGN, PLAN, IMPLEMENT, VERIFY, CUTOVER, CLEANUP | `sweetclaude:code-debt` |
| Data migration | ASSESS, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-debt` |
| API deprecation | ASSESS, DEFINE, IMPLEMENT, VERIFY, SHIP, CLEANUP | `sweetclaude:code-feature` |
| Dependency upgrade | ASSESS, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-debt` |
| Infrastructure change | DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-debt` |
| Rollback / revert | DIAGNOSE, SHIP | `sweetclaude:code-issue` |
| Code review | VERIFY | `sweetclaude:code-review` |
| Compliance requirement | ASSESS, DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-feature` |

## project/ — managing the work

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Issue / bug tracking | any | `sweetclaude:project-issues` |
| Import GitHub Issues into local store | any | `sweetclaude:project-gh-import-issues` |
| Sync issue status with GitHub | any | `sweetclaude:project-gh-sync-issues` |
| Epic management | any | `sweetclaude:project-epics` |
| Sprint planning and execution | PLAN, IMPLEMENT | `sweetclaude:project-sprints` |
| Backlog view and promotion | any | `sweetclaude:project-backlog` |
| Backlog grooming / triage | any | `sweetclaude:project-backlog-triage` |
| Roadmap management | any | `sweetclaude:product-roadmap` |
| Roadmap prioritization / RICE analysis | any | `sweetclaude:product-roadmap-analysis` |
| Scope definition and updates | DEFINE, any | `sweetclaude:project-scope` |
| Goal tracking | any | `sweetclaude:project-goals` |
| Project mode (flow/kanban/agile) | any | `sweetclaude:project-mode` |

## testing/ — validating the work

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Test plan / test strategy | PLAN, VERIFY | `sweetclaude:testing-plan` |
| Security review / threat model | VERIFY, any | `sweetclaude:testing-security` |
| Compliance control testing | any | `sweetclaude:testing-compliance` |
| Manual QA session | VERIFY | `sweetclaude:testing-session` |
| Performance / load testing | VERIFY, any | `sweetclaude:testing-performance` |
| Accessibility audit | VERIFY, any | `sweetclaude:testing-accessibility` |

## operations/ — keeping it running

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Something broke | DIAGNOSE, SHIP, POST-MORTEM | `sweetclaude:something-broke` *(Plan 3)* |
| Postmortem | DIAGNOSE, SHIP | `sweetclaude:postmortem` *(Plan 3)* |
| Break-glass notes | DEFINE, SHIP | `sweetclaude:break-glass-notes` *(Plan 3)* |
| Onboarding playbook | DEFINE, IMPLEMENT, SHIP | `sweetclaude:code-feature` |

## system/ — managing the framework

Always visible regardless of `version_stage`. No phases — these are point-in-time management operations.

| Work Type | Skill to invoke |
|---|---|
| Set up SweetClaude on a new or existing project | `sweetclaude:setup` |
| Bootstrap infrastructure only (no product discovery) | `sweetclaude:init` |
| Deactivate SweetClaude for a project | `sweetclaude:off` |
| Update SweetClaude to the latest version | `sweetclaude:update` |
| Audit or repair SweetClaude configuration | `sweetclaude:fix-sweetclaude` |
| Delete all SweetClaude artifacts | `sweetclaude:purge` |
| Validate framework behavioral contracts | `sweetclaude:behavioral-regression` |
| Enable protocol enforcement for the session | `sweetclaude:guardian-on` |
| Disable protocol enforcement | `sweetclaude:guardian-off` |
| Toggle or view usage tracking | `sweetclaude:usage` |
| Get help with SweetClaude | `sweetclaude:help` |

## Plan 3 fallbacks

| Bucket | Plan 3 fallback |
|---|---|
| strategy/ | `sweetclaude:product-discovery` |
| product/ | `sweetclaude:product-sprint-plan` |
| design/ | `sweetclaude:design-ux` |
| code/ — hotfix, security-patch | `sweetclaude:code-issue` |
| code/ — external-integration | `sweetclaude:code-feature` |
| project/ | `sweetclaude:project-issues` |
| testing/ | `sweetclaude:testing-session` |
| operations/ | `sweetclaude:code-issue` |
