# Design: Phase / Workflow Separation
**Version:** 0.3 (brainstorm output — not yet approved)
**Created:** 2026-04-29
**Status:** Draft — pending user review

## Changelog

| Version | Date | Summary |
|---|---|---|
| 0.1 | 2026-04-29 | Initial brainstorm output — two-dimension model, task catalog, dependency graph, entry point categories, soft/hard gate policy, progressive disclosure, GA pre-flight, change management matrix |
| 0.2 | 2026-04-29 | Workflow templates — five shapes, 19 work type mappings, 7 new phase definitions, Claude Code appropriateness split |
| 0.3 | 2026-04-29 | Phase gate exit criteria — full phase × work type matrix |

> **Versioning convention:** `0.x` = active brainstorm (not yet approved). `1.0` = first approved version. `1.x` = approved with incremental changes. `2.0`+ = next major structural revision (e.g., adding workflow templates). Bump minor version at the start of each editing session, before making changes.

---

## Problem

SweetClaude's current `phase.yaml` uses a single `phase` field that conflates two orthogonal concerns:

1. **Version stage** — where is this major version in its release lifecycle? (maturity, blast radius of changes, what work is appropriate)
2. **Work item phase** — where is this specific piece of work right now? (discover → implement → ship)

Result: "Phase: SHIPPING" while doing design work on a new feature. The field means two things and satisfies neither.

---

## Two Dimensions

### Dimension 1: Version Stage

Where is this major version in its release lifecycle? This is **slow-moving, declared by the user, rarely updated**. It answers: "what change cost profile applies right now?"

```
PROTOTYPE → ALPHA → BETA → GA → SCALED → MAINTAINED
```

Stages apply **per major version**, not per product lifetime. A v2 rewrite resets the clock. Multi-version concurrency (v1 MAINTAINED while v2 is in ALPHA) is **backlogged** (BL-004) — current model assumes one active version.

The field is named `version_stage` (not `product_stage`) so a future `versions:` list extension requires no structural breaking change.

**Change cost matrix** (see: change-management-matrix below) — each stage defines the effort/risk score for modifying any foundational artifact. This is not a rigor dial; it's a **lock profile**. As version_stage advances, more decisions become expensive to change.

### Dimension 2: Work Item Phase

Where is **this specific piece of work** right now? This is **fast-moving, type-driven**. Work type selects a workflow template that defines the ordered phases for that item.

The existing 7-phase pipeline (DISCOVER → DEFINE → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP) is one workflow template — appropriate for net-new features — not the universal pipeline.

---

## phase.yaml v2

```yaml
schema_version: 2
version_stage: BETA           # slow-moving, declared
deference_level: guided
project_type: existing-code

active_work_item:
  id: WI-007
  type: enhancement
  workflow: [DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP]
  phase: DESIGN
  title: "Add CSV export to reports"
  started: 2026-04-29
  entry_category: mid-project-planned  # cold-start | mid-project-planned | mid-project-reactive
```

---

## Task Catalog

Tasks organized by domain. `*` = not yet implemented in SweetClaude.

### Discovery / Strategy

| Task | PROTO | ALPHA | BETA | GA | SCALED | MAINT |
|---|---|---|---|---|---|---|
| Product research | ✓ | ~ | | | | |
| Competitive analysis | ✓ | ~ | | | | |
| Concept framing *(was: Narrative arc)* | ✓ | | | | | |
| Persona definition | ✓ | ~ | | | | |
| *Deep research *(was: Academic research)* | ✓ | ~ | | | | |
| *Course correction *(was: Strategic pivot)* | | ✓ | ~ | | | |
| User feedback triage | | ~ | ✓ | ✓ | ~ | ~ |
| *Signal aggregation / pattern analysis | | | ✓ | ✓ | ~ | |

> **Deep research note:** Domain-specific. Relevant for technical founders in developer tools, data infrastructure, API products, or research-adjacent markets. Not surfaced by default for general SaaS / app products.

### Definition

| Task | PROTO | ALPHA | BETA | GA | SCALED | MAINT |
|---|---|---|---|---|---|---|
| Product brief | ✓ | ~ | | | | |
| PRD / requirements | ~ | ✓ | | | | |
| Market messaging / positioning | | ~ | ✓ | ~ | | |
| Scope management | | ✓ | ✓ | ✓ | | |
| *Compliance requirement | | | ~ | ✓ | ✓ | ~ |

### Design

| Task | PROTO | ALPHA | BETA | GA | SCALED | MAINT |
|---|---|---|---|---|---|---|
| User flows | | ✓ | ~ | ~ | | |
| Architecture | | ✓ | ~ | ~ | | |
| Technical specification | | ✓ | ~ | ~ | | |
| Data model | | ✓ | ~ | | | |
| API design | | ✓ | ~ | ✓ | | |
| UX / UI design | | ✓ | ✓ | ~ | | |
| *Observability design *(reclassified from monitoring setup)* | | ~ | ✓ | ~ | | |
| Solutioning gate | | ✓ | ✓ | ✓ | | |
| Change impact analysis | | | ✓ | ✓ | ✓ | ~ |
| Decision management | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

> **Observability design note:** Designing *for* observability — what to instrument, what SLOs to target, how to structure logs and traces. Feeds Architecture. Not the same as setting up monitoring tooling (which is Monitoring & alerting in Operations).

### Planning

| Task | PROTO | ALPHA | BETA | GA | SCALED | MAINT |
|---|---|---|---|---|---|---|
| User stories | | ✓ | ~ | ~ | | |
| TDD test specs | | ✓ | ~ | ~ | | |
| Sprint planning | | ✓ | ✓ | ✓ | | |
| Backlog management | | ✓ | ✓ | ✓ | ✓ | |
| Milestone tracking | | ✓ | ✓ | ✓ | ✓ | |
| *Release planning | | ~ | ✓ | ✓ | ✓ | |

### Implementation

| Task | PROTO | ALPHA | BETA | GA | SCALED | MAINT |
|---|---|---|---|---|---|---|
| Net-new feature | | ✓ | ✓ | ✓ | | |
| Enhancement / iteration | | | ✓ | ✓ | ✓ | |
| Bug fix | | ✓ | ✓ | ✓ | ✓ | ✓ |
| Tech debt / refactor | | | ✓ | ✓ | ✓ | ~ |
| *Hotfix | | | ~ | ✓ | ✓ | ✓ |
| *Security patch | | | ~ | ✓ | ✓ | ✓ |
| *Performance optimization | | | ~ | ✓ | ✓ | |
| *External integration | | ✓ | ✓ | ✓ | | |
| *Technology migration | | | ~ | ✓ | ✓ | |
| *API deprecation | | | | ✓ | ✓ | |
| *Data migration | | | ~ | ✓ | ✓ | |
| *Dependency upgrade | | ~ | ✓ | ✓ | ✓ | ✓ |
| *Infrastructure change | | ~ | ✓ | ✓ | ✓ | |
| *Feature flag management | | | ✓ | ✓ | ✓ | |
| *Rollback / revert | | | ~ | ✓ | ✓ | ✓ |
| *Onboarding flow design | | ~ | ✓ | ✓ | | |

### Verification

| Task | PROTO | ALPHA | BETA | GA | SCALED | MAINT |
|---|---|---|---|---|---|---|
| Code review | | ~ | ✓ | ✓ | ✓ | ✓ |
| Security review | | ~ | ✓ | ✓ | ✓ | ✓ |
| Testing | | ✓ | ✓ | ✓ | ✓ | ✓ |
| *License audit | | | ~ | ✓ | ✓ | ✓ |

### Operations

| Task | PROTO | ALPHA | BETA | GA | SCALED | MAINT |
|---|---|---|---|---|---|---|
| *Something broke *(was: Incident response)* | | | | ✓ | ✓ | ✓ |
| *Postmortem / retrospective | | | ~ | ✓ | ✓ | ✓ |
| *Break-glass notes *(was: Runbook)* | | | | ✓ | ✓ | ✓ |
| *SLA / error budget review | | | | ✓ | ✓ | ✓ |
| *Security planning | | ~ | ✓ | ✓ | ✓ | ~ |
| *Monitoring & alerting *(reclassified — also a GA gate)* | | | ~ | ✓ | ✓ | ~ |
| *Onboarding playbook | | | ✓ | ✓ | ✓ | ~ |

### Documentation

| Task | PROTO | ALPHA | BETA | GA | SCALED | MAINT |
|---|---|---|---|---|---|---|
| Update docs | | | ✓ | ✓ | ✓ | ✓ |
| Document corpus | | ~ | ✓ | ✓ | ✓ | ✓ |
| *Changelog / release notes | | | ✓ | ✓ | ✓ | ✓ |

### Cross-cutting

| Task | PROTO | ALPHA | BETA | GA | SCALED | MAINT |
|---|---|---|---|---|---|---|
| Meeting prep | | ~ | ✓ | ✓ | ✓ | ✓ |
| Decision management | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## Dependency Graph

Format: `upstream1, upstream2 -> [TARGET TASK] -> downstream1, downstream2`

### Discovery / Strategy

```
(entry point) -> [Product research] -> Competitive analysis, Persona definition, Concept framing
(entry point) -> [Concept framing] -> Product brief, Product research
(entry point) -> [Deep research] -> Concept framing, Product brief
  (domain note: surface only for dev tools / research-adjacent / API products)
Product research -> [Competitive analysis] -> Persona definition, Product brief
Product research, Concept framing -> [Persona definition] -> Product brief, User flows, UX/UI design, User stories
Direct user contact, NPS/CSAT, Testing, Something broke, Postmortem -> [User feedback triage] -> Signal aggregation / pattern analysis, Bug fix, Enhancement/iteration, Backlog management
User feedback triage -> [Signal aggregation / pattern analysis] -> Course correction, Backlog management, Enhancement/iteration
Something broke, Postmortem -> [Course correction] -> Persona definition, Product brief, Scope management, Backlog management
```

### Definition

```
Persona definition, Competitive analysis, Concept framing -> [Product brief] -> PRD/requirements, Architecture, Security planning, Market messaging
Product brief -> [PRD/requirements] -> User stories, Architecture, Technical specification, Data model, Market messaging, Security planning
PRD/requirements, Persona definition -> [Market messaging / positioning] -> Changelog/release notes
PRD/requirements, Backlog management -> [Scope management] -> Sprint planning, Milestone tracking

# Compliance requirement — two valid entry paths:
(external trigger: customer ask, legal, regulatory) -> [Compliance requirement] -> Security planning, Architecture, Data model, API design, Break-glass notes
Security planning -> [Compliance requirement] -> Architecture, Data model, API design, Break-glass notes
```

### Design

```
PRD/requirements, Persona definition -> [User flows] -> UX/UI design, User stories
PRD/requirements, Observability design -> [Architecture] -> Technical specification, Data model, API design, Infrastructure change, Monitoring & alerting
Architecture, PRD/requirements -> [Technical specification] -> Data model, API design, User stories, TDD test specs, External integration
Architecture, Technical specification -> [Data model] -> API design, Data migration, Technical specification (feedback loop)
Technical specification, Data model -> [API design] -> External integration, API deprecation, TDD test specs
User flows, Persona definition -> [UX/UI design] -> User stories, TDD test specs, Onboarding flow design
PRD/requirements -> [Observability design] -> Architecture (feedback), Monitoring & alerting
Architecture, Technical specification -> [Solutioning gate] -> Net-new feature, External integration, Technology migration, Data migration, Infrastructure change
  (note: Data migration and Infrastructure change added per caucus finding)
(any change trigger) -> [Change impact analysis] -> Technology migration, API deprecation, Data migration, Scope management
(any decision point) -> [Decision management] -> (artifact the decision affects)
```

### Planning

```
PRD/requirements, User flows, UX/UI design -> [User stories] -> TDD test specs, Sprint planning, Backlog management
User stories -> [TDD test specs] -> Net-new feature, Bug fix, Enhancement/iteration
User stories, Backlog management, Milestone tracking -> [Sprint planning] -> Net-new feature, Bug fix, Enhancement/iteration, Tech debt
User feedback triage, Postmortem, Bug fix, Course correction -> [Backlog management] -> Sprint planning, Milestone tracking
Product brief, PRD/requirements, Sprint planning -> [Milestone tracking] -> Release planning, Changelog/release notes
Milestone tracking, Sprint planning, Backlog management, Feature flag management -> [Release planning] -> Changelog/release notes, API deprecation, Data migration, Feature flag management
  (note: Feature flag management is bidirectional with Release planning)
```

### Implementation

```
TDD test specs, Solutioning gate -> [Net-new feature] -> Code review, Testing, Update docs, Feature flag management
User feedback triage, User stories -> [Enhancement/iteration] -> Code review, Testing, Update docs
User feedback triage, Testing, Postmortem -> [Bug fix] -> Code review, Testing, Dependency upgrade (if root cause)
Code review, Postmortem -> [Tech debt / refactor] -> Code review, Testing, Architecture (if significant)
Something broke -> [Hotfix] -> Postmortem, Tech debt/refactor (follow-on)
Security review, Something broke -> [Security patch] -> Security review, Testing, Dependency upgrade
SLA/error budget review, Monitoring & alerting -> [Performance optimization] -> Testing, SLA/error budget review
API design, Technical specification -> [External integration] -> Code review, Testing, Update docs, License audit
Architecture, Change impact analysis -> [Technology migration] -> Code review, Testing, Data migration, Infrastructure change, Update docs
API design, Release planning, Change impact analysis -> [API deprecation] -> Changelog/release notes, Update docs, Data migration
Data model, Change impact analysis, Release planning -> [Data migration] -> Testing, Rollback/revert
  (note: Change impact analysis added upstream per caucus finding)
Security review, License audit -> [Dependency upgrade] -> Code review, Testing
Architecture, Technical specification, Solutioning gate -> [Infrastructure change] -> Break-glass notes, Testing, Monitoring & alerting
  (note: Solutioning gate added upstream per caucus finding)
Net-new feature, Release planning -> [Feature flag management] -> Release planning (feedback), Enhancement/iteration
  (note: bidirectional with Release planning)
Something broke -> [Rollback / revert] -> Postmortem, Bug fix
User flows, UX/UI design -> [Onboarding flow design] -> Onboarding playbook, Testing, Feature flag management, User feedback triage
```

### Verification

```
Any implementation task -> [Code review] -> Update docs, Security review (if flagged), Architecture (if structural issue found — feedback loop)
Code review, Compliance requirement -> [Security review] -> Security patch, Update docs, Change impact analysis (if architectural vulnerability)
  (note: failed security review triggers change impact analysis — feedback loop added per caucus)
TDD test specs, any implementation -> [Testing] -> Code review, Bug fix (if fails)
Dependency upgrade, External integration -> [License audit] -> Security patch, Compliance requirement
```

### Operations

```
Monitoring & alerting -> [Something broke] -> Hotfix, Rollback/revert, Postmortem
Something broke, Hotfix -> [Postmortem / retrospective] -> Bug fix, Tech debt, Backlog management, Security planning (if security incident)
  (note: Postmortem → Security planning feedback loop added per caucus)
Infrastructure change, Compliance requirement -> [Break-glass notes] -> Something broke (consumes it), SLA/error budget review
Monitoring & alerting, Break-glass notes -> [SLA / error budget review] -> Performance optimization, Infrastructure change, Something broke
Product brief, PRD/requirements -> [Security planning] -> Compliance requirement (proactive path), Architecture (security constraints), Data model
Observability design, Infrastructure change -> [Monitoring & alerting] -> Something broke, SLA/error budget review, Performance optimization
  (note: also a GA quality gate — see GA Pre-flight)
Onboarding flow design, Market messaging, User stories -> [Onboarding playbook] -> User feedback triage, Break-glass notes, Update docs
```

### Documentation

```
Any implementation, Code review -> [Update docs] -> Changelog/release notes
(any significant artifact) -> [Document corpus] -> (feeds search/RAG)
Release planning, Update docs -> [Changelog / release notes] -> Market messaging (for major releases)
```

### Cross-cutting

```
(any meeting need) -> [Meeting prep] -> (relevant work items or decisions)
```

---

## Entry Point Categories

Three distinct categories with different routing behavior in `find-skill`.

### Cold Start
**When:** New project, no prior context.
**Entry tasks:** Product research, Concept framing, Deep research
**Behavior:** Run full discovery pipeline. No prerequisites to check.

### Mid-Project Planned
**When:** Continuing work, following the pipeline.
**Entry tasks:** Net-new feature, Enhancement/iteration, Sprint planning, Backlog management, User feedback triage, Release planning, Tech debt, Security patch, Performance optimization, External integration, Technology migration, API deprecation, Data migration, Infrastructure change, Compliance requirement, Course correction (when triggered deliberately by accumulated signals)
**Behavior:**
1. Classify work type
2. Check prerequisites
3. Flag gaps as **advisory only** (soft gate)
4. Offer to create missing artifacts on the spot
5. Proceed

**Hard gate exceptions at GA+ (Vasquez minority report):** Migration-class work at GA or later requires documented prerequisites — not soft-bypassable. See Soft Gate Policy for the full list. Override requires explicit confirmation of risk logged to the decision log.

### Mid-Project Reactive
**When:** Something happened that demands immediate response.
**Entry tasks:** Bug fix, Hotfix, Something broke, Rollback/revert, Security patch (urgent), User feedback triage, Course correction (when triggered reactively by an incident or postmortem)
**Behavior:**
1. Skip all prerequisite checks
2. Triage questions only (what broke? is there a reproduction case?)
3. Proceed immediately
4. Offer missing prerequisites as **optional parallel work**, never blocking

---

## Soft Gate Policy

**Default:** All prerequisite checks are advisory. Every check accepts:
> "I've addressed this informally [optional note] — proceed."

No friction. No artifact required. The system flags and moves on.

**Hard gate carve-outs (GA+ only):**

| Task | Hard prerequisite | Why |
|---|---|---|
| Data migration | Solutioning gate + Change impact analysis + Rollback plan | Blast radius: production data loss |
| Infrastructure change | Solutioning gate + Change impact analysis + Rollback plan | Blast radius: outage, data loss |
| Technology migration | Solutioning gate + Change impact analysis + Parallel-run plan | Blast radius: production instability |
| Security patch (CVE) | Security review post-fix | Cannot ship an unreviewed security fix |

Hard gate override: user must explicitly confirm risk acceptance with a written note. The system records the override in the decision log.

---

## Progressive Disclosure by version_stage

`find-skill` and `status` surface only the task subset relevant to the current version_stage.

| Version Stage | Visible task groups |
|---|---|
| PROTOTYPE | Discovery, Definition |
| ALPHA | + Design, Planning, Core implementation (net-new feature, bug fix, external integration) |
| BETA | + Full implementation suite, Verification, Documentation, Release planning |
| GA | Full catalog |
| SCALED | Full catalog with Operations surfaced prominently |
| MAINTAINED | Bug fix, Security patch, Dependency upgrade, Compliance, Break-glass notes, Documentation — feature work de-emphasized |

---

## GA Pre-flight Checklist

Required before transitioning from BETA to GA. All items must be confirmed (or hard-overridden with documented rationale).

1. **Monitoring & alerting active** — production traffic is instrumented; alerts are configured and tested
2. **Break-glass notes exist** — at minimum: how to roll back a bad deploy, how to restore from backup
3. **Rollback plan documented** — a runnable procedure exists for the last deploy
4. **Security review passed** — no open P0/P1 security findings
5. **P0/P1 bug count is zero** — no known critical or blocker bugs in the build
6. **Documentation complete** — core user workflows are documented and accurate
7. **Support path defined** — user knows how to reach you (email, GitHub issues, etc.)

---

## Change Management Matrix

Version stage × change factor. `—` = not yet relevant, `L` = low impact, `M` = medium, `H` = high (change-impact analysis required), `X` = extreme (requires formal plan and justification).

| Change Factor | PROTO | ALPHA | BETA | GA | SCALED | MAINT |
|---|---|---|---|---|---|---|
| Product strategy / positioning | — | L | M | H | X | X |
| Target persona / ICP | — | L | M | H | X | X |
| Core user workflows | — | L | M | H | X | X |
| Feature scope / roadmap | — | L | M | M | H | H |
| Data model / schema | — | L | M | H | X | H |
| Public API contracts | — | — | L | H | X | H |
| Internal API contracts | — | L | L | M | H | M |
| Auth / access model | — | L | M | H | X | M |
| UX patterns / design language | — | L | M | M | H | M |
| Technology stack | L | M | M | H | X | H |
| Infrastructure / deployment | L | L | M | H | X | H |
| Third-party integrations | L | L | M | H | H | M |
| Pricing / business model | — | — | M | H | X | H |
| Compliance posture | — | L | M | H | X | H |
| Performance SLOs | — | — | L | H | X | M |
| Onboarding flow | — | L | M | H | H | M |

---

## Renames Summary

| Old name | New name | Reason |
|---|---|---|
| Narrative arc | Concept framing | More concrete; "narrative arc" sounds literary |
| Academic research | Deep research | Broader framing; applicable to technical competitive research |
| Strategic pivot | Course correction | Less dramatic; "pivot" implies irreversibility |
| Runbook / operational procedure | Break-glass notes | Approachable; solo devs write these, they just don't call them runbooks |
| Incident response | Something broke | Matches how a solo dev thinks about it at 2am |
| Observability / monitoring setup | Split: Observability design (Design) + Monitoring & alerting (Operations) | Design concern ≠ operational concern |

---

## Workflow Templates

### Five Shapes

All work types map to one of five shapes. Variations are noted per type.

| Shape | Phase Sequence |
|---|---|
| **Full pipeline** | DISCOVER → DEFINE → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP |
| **Abbreviated forward** | DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP |
| **Diagnostic** | DIAGNOSE → IMPLEMENT → VERIFY → SHIP |
| **Migration** | ASSESS → DESIGN → PLAN → IMPLEMENT → VERIFY → CUTOVER → CLEANUP |
| **Compressed / urgent** | DIAGNOSE → IMPLEMENT → SHIP → POST-MORTEM |

### New Phase Definitions

| Phase | Meaning | Used in |
|---|---|---|
| `DIAGNOSE` | Understand root cause before touching code. Reproduction case, baseline benchmark, or incident triage. | Bug fix, Security patch, Performance optimization, Hotfix, Rollback |
| `ASSESS` | Map scope and risk before committing. What's affected? What's the rollback plan? Go/no-go decision. | Technology migration, Data migration, Dependency upgrade, Infrastructure change, Compliance |
| `SCOPE` | Lock existing behavior with tests before refactoring. Defines what changes and what must not. | Tech debt / refactor |
| `TRIAGE` | After a course correction, review all in-flight work: keep / drop / repurpose. Updates backlog. | Course correction |
| `CUTOVER` | Switch traffic or data from old system to new. Both have been running in parallel to this point. | Technology migration |
| `CLEANUP` | Remove old system artifacts after successful cutover or deprecation sunset. | Technology migration, API deprecation |
| `POST-MORTEM` | Required follow-on after a hotfix or rollback. What happened, why, what changes. Spawns follow-on work items. | Hotfix, Rollback |

### Work Type → Template Mapping

| Work Type | Shape | Variations |
|---|---|---|
| Net-new feature | Full pipeline | — |
| External integration | Full pipeline | DISCOVER = understand external API, auth model, rate limits, data contracts |
| Course correction | Full pipeline | Ends at TRIAGE instead of SHIP; spawns new work items |
| Security planning | Full pipeline | SHIP = publish roadmap document (no code) |
| Enhancement / iteration | Abbreviated | — |
| Tech debt / refactor | Abbreviated | DEFINE → SCOPE (lock behavior with tests) before IMPLEMENT |
| Compliance requirement | Extended abbreviated | ASSESS → DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP; VERIFY includes audit evidence generation |
| Infrastructure change | Abbreviated | Hard gate at DESIGN: solutioning gate required at GA+ |
| Onboarding flow design | Abbreviated | — |
| Release planning | Abbreviated | Collapses to DEFINE → PLAN → SHIP |
| Bug fix | Diagnostic | — |
| Security patch | Diagnostic | VERIFY is a hard gate: security review mandatory before SHIP |
| Performance optimization | Diagnostic | DIAGNOSE = establish baseline benchmarks; VERIFY = benchmark again, confirm improvement |
| Rollback / revert | Diagnostic | Collapses to DIAGNOSE → SHIP (no implementation); spawns POST-MORTEM |
| Technology migration | Migration | Full shape |
| Data migration | Migration | No CUTOVER phase; VERIFY = data integrity reconciliation |
| API deprecation | Migration | ASSESS → DEFINE → IMPLEMENT → VERIFY → SHIP → CLEANUP; CLEANUP fires at sunset date |
| Dependency upgrade | Migration | Collapses to ASSESS → IMPLEMENT → VERIFY → SHIP |
| Hotfix | Compressed | — |

### Claude Code Appropriateness

**Claude owns end-to-end** (whole workflow lives in IDE context):
Net-new feature, Enhancement/iteration, Bug fix, Tech debt/refactor, Hotfix, Security patch, External integration, API deprecation, Dependency upgrade, Course correction, Compliance requirement, Security planning, Release planning, Postmortem, Break-glass notes, Onboarding flow design, Changelog/release notes, all discovery/definition/design/planning tasks.

**Claude guides, human executes** (Claude handles thinking/planning/scripting; critical steps happen outside the IDE):
Performance optimization (benchmarking), Technology migration (CUTOVER decision), Data migration (execution against live data), Infrastructure change (provisioning), Monitoring & alerting (platform configuration), Something broke (real-time log access).

**Not worth a standalone skill** (too brief, too external, or better as a checklist within another workflow):
Rollback/revert (one command — checklist item in Hotfix), Feature flag management (lifecycle belongs in flag tool), SLA/error budget review (data from external monitoring).

---

## Phase Gate Exit Criteria

> ⚠️ = hard gate — soft bypass ("I've addressed this informally") is not accepted. Override requires explicit risk confirmation logged to decision log.

---

### Net-new feature

**DISCOVER**
- At least one persona defined: role, primary tasks, success criteria per task
- At least one concrete real-world scenario per persona
- Core feature set established
- At least one thing explicitly out of scope
- At least one assumption challenged or alternative framing raised
- Competitive landscape assessed or explicitly declined
- Key decisions in decision log

**DEFINE**
- Product brief: all 11 sections substantively populated (no TBD, no single-sentence sections)
- Problem statement includes a specific scenario or real-world example
- Scope section has 3+ explicit out-of-scope items
- Every success criterion is measurable (true/false evaluable post-ship)
- PRD written: functional requirements, non-functional requirements, epics

**DESIGN**
- Architecture document written and reviewed
- Tech spec written and reviewed
- Data model designed
- API contracts defined (if applicable)
- UX flows documented
- Solutioning gate passed
- Key design decisions recorded

**PLAN**
- User stories written with acceptance criteria for all epics
- Gherkin .feature files or test specs generated
- Traceability map started (stories → requirements)

**IMPLEMENT**
- All tests passing (RED → GREEN complete)
- All acceptance criteria satisfied
- Change impact analysis complete (if modifying existing code)
- Code committed

**VERIFY**
- Code review complete — no critical findings open
- Security review complete (if security-sensitive)
- All tests passing in CI
- Documentation updated
- Traceability map complete

**SHIP**
- PR merged or code deployed
- Smoke test passing in production
- Changelog / release notes updated

---

### External integration

**DISCOVER**
- External service purpose confirmed and justified
- API documentation reviewed: auth model, rate limits, data contracts, error handling, quotas
- Integration approach decided: webhook vs. polling, SDK vs. raw HTTP
- Sandbox/test environment confirmed available (or unavailability documented)
- External service cost/pricing confirmed
- Failure modes and fallback strategy identified

**DEFINE**
- Integration scope defined: what data flows in/out, under what conditions
- Error handling strategy defined: degraded behavior when external service is unavailable
- SLA of external service noted (becomes a ceiling on your own SLA)
- Blocking dependencies identified

**DESIGN**
- External service abstracted behind a clean interface (not called directly throughout codebase)
- Contract tests designed: what behavior must the external service exhibit
- Data mapping documented: external schema → internal schema
- Auth flow designed and reviewed
- Retry, timeout, and circuit-breaker strategy designed

**PLAN**
- Task breakdown complete
- Contract tests written (test external service behavior, not your code)
- Integration tests designed

**IMPLEMENT**
- Adapter implemented behind interface
- Contract tests passing against sandbox
- Integration tests passing
- Error/fallback paths implemented and tested
- Auth flow implemented and tested

**VERIFY**
- Code review complete
- Security review complete: credentials stored correctly, no secrets in code
- Contract tests passing
- Integration tested against real external service (not just sandbox)
- Failure/fallback scenarios tested end-to-end

**SHIP**
- Deployed and verified against production external service
- Monitoring configured for integration health
- Documentation updated
- Break-glass notes updated with integration failure procedure

---

### Course correction

**DISCOVER**
- Signal that triggered the correction documented
- Signal aggregation confirmed: this is a pattern, not a single data point
- New direction clearly articulated
- Old direction clearly stated (for comparison and traceability)
- Assumptions being invalidated identified

**DEFINE**
- Revised direction document or updated product brief written
- Updated personas (if the target user is changing)
- New scope established
- Old scope formally retired and documented

**TRIAGE**
- All in-flight work items reviewed and each tagged: keep / drop / repurpose / defer
- Impact on existing users assessed: what breaks, what changes
- Data migration needs identified (if user-facing changes require it)
- New backlog items created from repurposed work
- Dropped items closed with documented rationale

**SHIP**
- Revised direction committed to project state
- Backlog updated and clean — no zombie items from old direction
- Decision log updated with the course correction and rationale
- Follow-on work items created

---

### Security planning

**DISCOVER**
- User interviewed on: business model, customer types, data handled (PII, health, financial), current and target markets
- Regulatory environment assessed: which standards apply now, which will apply at scale
- Current security posture assessed: existing controls documented

**DEFINE**
- Applicable standards mapped with rationale and business trigger:
  - GDPR: required if EU users handle personal data
  - SOC 2 Type 1: 6–12 months before SOC 2 Type 2 is needed
  - SOC 2 Type 2: required when approaching larger B2B customers
  - HIPAA: required if handling protected health information
  - PCI-DSS: required if processing payment card data
- Phased roadmap written: what to achieve by when, tied to version_stage milestones
- Quick wins identified: controls to implement now regardless of stage

**SHIP**
- Security roadmap document committed to project
- Quick-win controls added to backlog with priority
- Any currently overdue items flagged against current version_stage

---

### Enhancement / iteration

**DEFINE**
- Change scoped: what is being improved and how
- Existing behavior documented: what changes, what stays the same
- Success criteria defined: how will we know the enhancement worked
- Change impact analysis complete: what else might be affected

**DESIGN**
- Approach decided and documented
- If UX change: updated flows reviewed
- If API change: contracts reviewed, backward compatibility assessed
- Edge cases identified

**IMPLEMENT**
- Tests written for new/changed behavior (RED → GREEN)
- Existing tests still passing (no regressions)
- Code committed

**VERIFY**
- Code review complete
- All tests passing
- Enhancement behaves as specified in success criteria

**SHIP**
- Deployed and smoke tested
- Documentation updated if behavior changed
- Changelog entry added

---

### Tech debt / refactor

**DEFINE**
- Scope defined: what code is changing, what patterns are being introduced or removed
- Motivation documented: why is this debt, what problem does it cause
- Risk assessed: what could break

**SCOPE**
- Existing behavior locked with tests — suite covers all behavior that must be preserved
- Tests confirmed to fail if any locked behavior changes (verified against a deliberate break)
- Refactor boundaries defined: what's in scope for this session, what's deferred
- Rollback plan documented

**IMPLEMENT**
- Refactored code passes all existing tests
- No new test failures
- No behavior changes — only structural changes
- Code is measurably cleaner than before

**VERIFY**
- Code review confirms: behavior unchanged, structure improved, no new complexity introduced
- All tests passing
- No performance regression

**SHIP**
- Deployed and smoke tested
- No incidents in first deployment window
- Decision log updated with what changed and why

---

### Compliance requirement

**ASSESS**
- Requirement identified precisely: which standard, which control, which clause
- Gap analysis complete: what exists, what is missing
- Evidence requirements understood: what must be produced to prove compliance
- Timeline established: is there an audit date or certification deadline
- External dependencies identified: auditor, legal review, third-party tools

**DEFINE**
- Controls to implement documented
- Acceptance criteria for each control defined (what does "compliant" look like)

**DESIGN**
- Technical approach for each control designed
- Impact on existing architecture assessed
- Data handling changes reviewed (retention, encryption, access controls)

**IMPLEMENT**
- All controls implemented
- Evidence artifacts generated (logs, policies, access records)
- Documentation written

**VERIFY**
- Security review complete
- Each control tested against its acceptance criteria
- Evidence package assembled and reviewed
- Legal/compliance review complete (if required by the standard)

**SHIP**
- Controls deployed to production
- Evidence archived in the designated location
- Audit trail established
- Next review date scheduled and added to backlog

---

### Infrastructure change

**DEFINE**
- Change scoped: what infrastructure is changing and why
- Risk level assessed: downtime possible? data risk? performance impact?
- Rollback plan exists before any design begins

**DESIGN** ⚠️ HARD GATE at GA+: solutioning gate required, no soft bypass
- Solutioning gate passed
- Architecture reviewed for the change
- Rollback procedure documented in detail — not just "revert the commit," step-by-step
- Monitoring plan defined: what signals confirm healthy state after change
- Change window planned if downtime is required

**IMPLEMENT**
- Change implemented and verified in staging first
- Runbook written: step-by-step execution with rollback steps at each stage

**VERIFY**
- Staging smoke test passing
- Performance verified: no regression
- Security posture verified: no new exposure introduced
- Rollback tested in staging if possible

**SHIP**
- Change deployed to production
- Monitoring confirming healthy signals
- Rollback procedure on standby for first 24 hours
- Break-glass notes updated

---

### Onboarding flow design

**DEFINE**
- Target persona confirmed: who is being onboarded
- Success metric defined: what does a successfully onboarded user do or know
- Current drop-off points identified (if product is live)
- Explicit out-of-scope: what this onboarding flow will not try to do

**DESIGN**
- Flow mapped step-by-step
- UX for each step designed: screens, copy, interactions
- Edge cases handled: incomplete onboarding, re-entry, skipping steps
- At least one real user has reviewed the flow (even informally)

**IMPLEMENT**
- Flow implemented and testable end-to-end
- Analytics events instrumented at each step
- Edge cases implemented

**VERIFY**
- End-to-end test passing
- Analytics events confirmed firing correctly
- Code review complete

**SHIP**
- Deployed and walked through by at least one real user
- Completion rate baseline established
- Onboarding playbook updated to reflect new flow

---

### Release planning

**DEFINE**
- Release scope locked: exactly what's in, what's deferred
- Version number assigned
- Breaking changes identified
- Migration requirements identified
- Communication plan decided: who needs to know, when, how

**PLAN**
- Changelog / release notes drafted
- Pre-release checklist assembled and confirmed
- Migration guides written (if applicable)
- Deployment order planned (if multi-step)
- Rollback plan confirmed viable

**SHIP**
- All pre-release checklist items confirmed
- Release artifact built and tagged
- Changelog published
- Communication sent
- Post-release monitoring confirmed active

---

### Bug fix

**DIAGNOSE**
- Reproduction case established and documented: exact steps to reproduce
- Root cause identified: not just the symptom, the underlying reason
- Scope of impact assessed: how many users affected, how severe
- Affected code identified: files, functions, lines
- Missing test identified: what test should have caught this (absence noted if none)

**IMPLEMENT**
- Fix targets root cause (not just symptom)
- Regression test written that fails on the bug and passes after the fix
- No unrelated changes in the same commit

**VERIFY**
- Regression test passing
- No new test failures introduced
- Bug confirmed fixed against original reproduction case

**SHIP**
- Deployed
- Fix confirmed working in production
- Changelog entry added if user-visible

---

### Security patch

**DIAGNOSE**
- Vulnerability identified and described: CVE or internal report, affected versions, affected systems
- Blast radius assessed: what data or systems are exposed, who is affected
- Severity classified: P0 (immediate), P1 (urgent), P2 (important)
- Disclosure timeline established: is there a coordinated disclosure deadline
- Temporary mitigation identified: can exposure be reduced while patch is built

**IMPLEMENT**
- Patch is minimal: fixes only the vulnerability, no refactoring
- Patch does not introduce new attack surface
- Regression test written proving the vulnerability is closed

**VERIFY** ⚠️ HARD GATE: security review is mandatory before SHIP, no soft bypass
- Security review complete: independent review of the patch
- Patch confirmed not introducing new vulnerabilities
- Regression test passing
- Affected dependency updated if root cause was a dependency

**SHIP**
- Deployed, in an expedited window if P0/P1
- Coordinated disclosure published if deadline applies
- Changelog entry published
- Affected users notified if data was exposed
- Follow-on task created for any deferred work (broader audit, related systems)

---

### Performance optimization

**DIAGNOSE**
- Baseline benchmark established: current performance measured under realistic conditions
- Bottleneck identified: specific function, query, or operation that is the constraint
- Target defined: what does "good enough" performance look like
- Root cause understood: why is this slow

**DESIGN**
- Optimization approach decided and documented
- Expected improvement estimated
- Risk assessed: could this change behavior or introduce instability
- Alternative approaches considered

**IMPLEMENT**
- Optimization implemented
- No behavior changes — only performance changes
- All existing tests still passing

**VERIFY**
- Benchmark re-run: improvement confirmed against baseline
- No correctness regressions (all tests passing)
- No new bottleneck introduced elsewhere (profiled after, not just the target area)

**SHIP**
- Deployed
- Production monitoring confirming improvement
- Baseline updated with new benchmark numbers

---

### Rollback / revert

**DIAGNOSE**
- Specific deploy or change identified as the cause
- Impact confirmed: this is the right thing to roll back
- Rollback method decided: git revert, deploy previous artifact, feature flag off
- Data impact assessed: will rolling back leave data in an inconsistent state
- Stakeholders informed

**SHIP**
- Rollback executed
- Production confirmed healthy after rollback
- Monitoring showing recovery
- Incident declared resolved
- POST-MORTEM work item spawned (required — not optional)

---

### Technology migration

**ASSESS**
- Current state documented: what is being replaced and why
- Migration scope defined: what systems, services, and code paths are affected
- Risk assessed: what could go wrong, what is the blast radius
- Migration strategy decided: big bang vs. incremental vs. parallel-run
- Rollback plan documented: how to return to the old system if migration fails

**DESIGN**
- Target architecture designed
- Migration path designed: how to move from current to target
- Parallel-run strategy designed (if incremental): how old and new coexist during transition
- Data compatibility assessed: does old data work in the new system
- Solutioning gate passed ⚠️ HARD GATE at GA+

**PLAN**
- Migration broken into phases, each with its own rollback point
- Test strategy defined for each phase
- Cutover criteria defined: what signals confirm it is safe to cut over

**IMPLEMENT**
- New system built alongside old (parallel-run)
- Data compatibility verified
- Each phase implemented and verified before proceeding to the next

**VERIFY**
- New system verified under realistic load
- Parity verified: new system produces equivalent results to old system for the same inputs
- Rollback confirmed viable: tested return to old system

**CUTOVER** ⚠️ HARD GATE: human decision required, explicit confirmation logged, no soft bypass
- Cutover criteria met (as defined in PLAN)
- Monitoring active on new system
- Rollback procedure on standby
- Cutover executed
- New system confirmed healthy under production load
- Old system traffic at zero

**CLEANUP**
- Old system code removed
- Old system infrastructure decommissioned
- Old data migrated or archived per retention policy
- Documentation updated: no references to old system in active docs
- Break-glass notes updated

---

### Data migration

**ASSESS**
- Data to migrate identified: tables, collections, files, volume
- Schema mapping defined: old → new
- Data quality issues identified: nulls, invalid values, encoding problems
- Rollback plan: how to restore from backup if migration fails
- Downtime requirement assessed: live migration or maintenance window

**DESIGN**
- Migration script designed and peer reviewed
- Dry-run strategy defined: how to test without touching production
- Integrity checks defined: row counts, checksums, sample record verification
- Rollback script designed and tested

**PLAN**
- Migration steps sequenced
- Maintenance window planned (if required)
- Backup confirmed before any migration begins

**IMPLEMENT**
- Migration script implemented
- Dry run executed against a copy of production data
- Dry run results verified: correct output, acceptable duration

**VERIFY** ⚠️ HARD GATE: integrity checks mandatory before SHIP, no soft bypass
- Migration executed against production data
- Integrity checks pass: row counts match, checksums match, sample records verified manually
- Application behavior verified against migrated data
- Rollback plan confirmed still viable post-migration

**SHIP**
- Migration confirmed complete and healthy
- Old schema marked deprecated or removed
- Application fully running on new schema
- Documentation updated

---

### API deprecation

**ASSESS**
- API being deprecated identified precisely: endpoint, version, specific fields
- Consumer impact assessed: who calls this, how often, what do they depend on
- Migration path for consumers defined: what to use instead
- Sunset date established

**DEFINE**
- Deprecation notice written: what is being removed, when, what to use instead
- Migration guide written for consumers
- Changelog entry written

**IMPLEMENT**
- Compatibility layer implemented to keep deprecated API working during migration window
- Migration helpers built if assisting consumers
- Deprecation warnings added to API responses (headers or response body)

**VERIFY**
- Migration guide reviewed (by at least one consumer if possible)
- Compatibility layer tested
- Deprecation warnings confirmed firing in all relevant paths

**SHIP**
- Deprecation notice published
- Migration guide published and linked from API documentation
- Sunset date communicated to all known consumers

**CLEANUP** (fires at sunset date)
- Consumer traffic confirmed at zero or negligible
- Deprecated API removed from codebase
- Compatibility layer removed
- All documentation updated to remove references

---

### Dependency upgrade

**ASSESS**
- Changelog reviewed for breaking changes between current and target version
- Breaking changes identified and impact on the codebase assessed
- Test coverage of affected areas confirmed
- Transitive dependency changes noted

**IMPLEMENT**
- Dependency updated in package manifest
- Breaking changes addressed in application code
- Tests updated where API changed (to reflect new API, not to make them pass artificially)

**VERIFY**
- All tests passing
- No unexpected behavior changes
- No performance regression

**SHIP**
- Deployed and smoke tested
- Security advisory resolved (if upgrade was security-driven)
- Changelog entry added

---

### Hotfix

**DIAGNOSE**
- Production impact confirmed: what is broken, who is affected, severity
- Root cause identified to the degree possible under time pressure
- Fix approach decided: simplest possible fix that resolves the production issue
- Scope minimized: fix only what is breaking, nothing else
- Rollback assessed: is rollback faster than patching

**IMPLEMENT**
- Minimal fix only — no refactoring, no cleanup, no related improvements
- Smoke test written confirming the fix works against the production issue
- Existing tests still passing (no regressions introduced by the fix)

**SHIP** (expedited — normal code review gate is relaxed, but not eliminated)
- At minimum: async notification sent to a stakeholder OR self-review checklist completed and logged (solo devs: document your own review)
- Deployed to production
- Fix confirmed resolving the production issue
- Incident declared resolved
- POST-MORTEM work item created (required, not optional)

**POST-MORTEM** (follow-on work item, spawned from SHIP)
- Timeline of events documented
- Root cause analysis complete (5 whys or equivalent)
- Contributing factors identified
- Action items defined: what changes to prevent recurrence
- Action items added to backlog with priority
- Follow-on tech debt item created if the hotfix was a workaround rather than a real fix

---

## Open Items

- [x] Workflow templates per work type (ordered phase sequences)
- [x] Phase gate exit criteria — full phase × work type matrix
- [ ] `find-skill` implementation changes for three-category entry routing
- [ ] `phase-gates.md` updates for new phases (DIAGNOSE, ASSESS, SCOPE, CUTOVER, CLEANUP)
- [ ] `workflow-templates.yaml` new config file
- [ ] Backlog: multi-version concurrency (BL-004)
