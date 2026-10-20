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
| Concept articulation / framing | DISCOVER, DEFINE, SHIP | `sweetclaude:library-load product-discovery` *(fallback — `sweetclaude:concept-framing` planned, see ISSUE-008)* |
| Pain analysis | DISCOVER, DEFINE, SHIP | `sweetclaude:library-load product-discovery` |
| Customer profiling | DISCOVER, DEFINE, SHIP | `sweetclaude:library-load user-personas` |
| Synthetic panel research / concept testing | DISCOVER, DEFINE | `sweetclaude:library-load product-user-focus-group` *(requires validated personas — gate enforced)* |
| Competitive landscape | DISCOVER, DEFINE, SHIP | `sweetclaude:library-load product-competition` |
| Research / deep research | DISCOVER, DEFINE, SHIP | `sweetclaude:library-load documents-academic-research` |
| Meeting preparation | DEFINE | `sweetclaude:library-load misc-meeting-prep` |
| Market messaging | DEFINE | `sweetclaude:library-load product-market-messaging` |
| Security planning | DISCOVER, DEFINE, SHIP | `sweetclaude:security-planning` *(Plan 3)* |
| Course correction | DISCOVER, DEFINE, TRIAGE, SHIP | `sweetclaude:library-load course-correction` |

## product/ — what to build and why

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Net-new feature | DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:library-load product-discovery` |
| Large story / high-rigor story | DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP/closeout; controller-enforced phase gates, hook-verified enforcement | `sweetclaude:library-load large-story` |
| Small story / bounded story | DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP/closeout; controller-enforced phase gates, hook-verified enforcement | `sweetclaude:library-load small-story` |
| Enhancement / iteration | DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:library-load product-prd` |
| Product brief | DEFINE | `sweetclaude:library-load product-brief` |
| Requirements / PRD | DEFINE | `sweetclaude:library-load product-prd` |
| User stories | PLAN | `sweetclaude:library-load product-user-stories` |
| Test specs from stories | PLAN | `sweetclaude:library-load product-user-tdd-tests` |
| Scope change | any | `sweetclaude:library-load product-manage-scope` |
| Parking lot / deferred ideas | any | `sweetclaude:library-load product-parking-lot` |
| Sprint / release planning | DEFINE, PLAN, SHIP | `sweetclaude:library-load product-sprint-plan` |
| Market / technical research | DISCOVER | `sweetclaude:library-load product-research` |
| Release planning | DEFINE, PLAN, SHIP | `sweetclaude:release-planning` *(Plan 3)* |

## design/ — how it's structured

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| System architecture | DESIGN | `sweetclaude:library-load design-architecture` |
| Technical specification | DESIGN | `sweetclaude:library-load design-tech-spec` |
| UX/UI design | DESIGN | `sweetclaude:library-load design-ux` |
| Solution validation | DESIGN | `sweetclaude:library-load design-solutioning-gate` |
| Impact analysis | any | `sweetclaude:library-load design-change-impact-analysis` |
| Doc updates | VERIFY | `sweetclaude:library-load documents-update-docs` |
| Data model / schema | DESIGN | `sweetclaude:library-load design-data-model` |
| API design | DESIGN | `sweetclaude:library-load design-api-design` |
| Record a decision | any | `sweetclaude:library-load design-manage-decisions` |
| Onboarding flow design | DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:onboarding-flow-design` *(Plan 3)* |

## code/ — writing and verifying code

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Net-new feature (implement) | IMPLEMENT | `sweetclaude:library-load code-feature` |
| Bug fix | DIAGNOSE, IMPLEMENT, VERIFY, SHIP | `sweetclaude:library-load code-issue` |
| Enhancement | IMPLEMENT | `sweetclaude:library-load code-issue` |
| Tech debt / refactor | DEFINE, SCOPE, IMPLEMENT, VERIFY, SHIP | `sweetclaude:library-load code-debt` |
| Hotfix | DIAGNOSE, IMPLEMENT, SHIP, POST-MORTEM | `sweetclaude:library-load hotfix` |
| Security patch | DIAGNOSE, IMPLEMENT, VERIFY, SHIP | `sweetclaude:library-load security-patch` |
| Performance optimization | DIAGNOSE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:library-load code-issue` |
| External integration | DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:external-integration` *(Plan 3)* |
| Technology migration | ASSESS, DESIGN, PLAN, IMPLEMENT, VERIFY, CUTOVER, CLEANUP | `sweetclaude:library-load code-debt` |
| Data migration | ASSESS, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:library-load code-debt` |
| API deprecation | ASSESS, DEFINE, IMPLEMENT, VERIFY, SHIP, CLEANUP | `sweetclaude:library-load code-feature` |
| Dependency upgrade | ASSESS, IMPLEMENT, VERIFY, SHIP | `sweetclaude:library-load code-debt` |
| Infrastructure change | DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:library-load code-debt` |
| Rollback / revert | DIAGNOSE, SHIP | `sweetclaude:library-load rollback-revert` |
| Code review | VERIFY | `sweetclaude:library-load code-review` |
| Compliance requirement | ASSESS, DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:library-load code-feature` |

## project/ — managing the work

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Issue / bug tracking | any | `sweetclaude:library-load project-issues` |
| Use GitHub instead of local project issues | any | `sweetclaude:build tracker github` |
| Import GitHub Issues into local store | any | `sweetclaude:library-load project-gh-import-issues` |
| Sync issue status with GitHub | any | `sweetclaude:library-load project-gh-sync-issues` |
| Epic management | any | `sweetclaude:library-load project-epics` |
| Sprint planning and execution | PLAN, IMPLEMENT | `sweetclaude:library-load project-sprints` |
| Backlog view and promotion | any | `sweetclaude:library-load project-backlog` |
| Backlog grooming / triage | any | `sweetclaude:library-load project-backlog-triage` |
| Roadmap management | any | `sweetclaude:library-load product-roadmap` |
| Roadmap prioritization / RICE analysis | any | `sweetclaude:library-load product-roadmap-analysis` |
| Scope definition and updates | DEFINE, any | `sweetclaude:library-load project-scope` |
| Goal tracking | any | `sweetclaude:library-load project-goals` |
| Project mode (flow/kanban/agile) | any | `sweetclaude:library-load project-mode` |

## testing/ — validating the work

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Test plan / test strategy | PLAN, VERIFY | `sweetclaude:library-load testing-plan` |
| Security review / threat model | VERIFY, any | `sweetclaude:library-load testing-security` |
| Compliance control testing | any | `sweetclaude:library-load testing-compliance` |
| Manual QA session | VERIFY | `sweetclaude:library-load testing-session` |
| Performance / load testing | VERIFY, any | `sweetclaude:library-load testing-performance` |
| Accessibility audit | VERIFY, any | `sweetclaude:library-load testing-accessibility` |

## operations/ — keeping it running

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Something broke | DIAGNOSE, SHIP, POST-MORTEM | `sweetclaude:library-load something-broke` |
| Postmortem | POST-MORTEM | `sweetclaude:library-load postmortem` |
| Break-glass notes | DEFINE, SHIP | `sweetclaude:break-glass-notes` *(Plan 3)* |
| Onboarding playbook | DEFINE, IMPLEMENT, SHIP | `sweetclaude:library-load code-feature` |

## system/ — managing the framework

Always visible regardless of `version_stage`. No phases — these are point-in-time management operations.

| Work Type | Skill to invoke |
|---|---|
| Set up SweetClaude on a new or existing project | `sweetclaude:library-load setup` |
| Onboard a project, unsure which entry point applies | `sweetclaude:library-load init` |
| Deactivate SweetClaude for a project | `sweetclaude:library-load off` |
| Update SweetClaude to the latest version | `sweetclaude:library-load update` |
| Audit or repair SweetClaude configuration | `sweetclaude:library-load fix-sweetclaude` |
| Delete all SweetClaude artifacts | `sweetclaude:library-load purge` |
| Validate framework behavioral contracts | `sweetclaude:library-load behavioral-regression` |
| Enable protocol enforcement for the session | `sweetclaude:library-load guardian-on` |
| Disable protocol enforcement | `sweetclaude:library-load guardian-off` |
| Toggle or view usage tracking | `sweetclaude:library-load usage` |
| Get help with SweetClaude | `sweetclaude:help` |

## Plan 3 fallbacks

| Bucket | Plan 3 fallback |
|---|---|
| strategy/ | `sweetclaude:library-load product-discovery` |
| product/ | `sweetclaude:library-load product-sprint-plan` |
| design/ | `sweetclaude:library-load design-ux` |
| code/ — hotfix, security-patch | `sweetclaude:library-load code-issue` |
| code/ — external-integration | `sweetclaude:library-load code-feature` |
| project/ | `sweetclaude:library-load project-issues` |
| testing/ | `sweetclaude:library-load testing-session` |
| operations/ | `sweetclaude:library-load code-issue` |
