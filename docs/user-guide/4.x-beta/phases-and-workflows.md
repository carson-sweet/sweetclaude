# Phases and Workflows

**Version:** 1.0
**Date:** 2026-05-01

This page is reference. If you want to understand *why* phases work the way they do, read [How It Works](how-it-works.md) first. This page lists the phases, the work types, the workflow shapes, the gates, and the progressive disclosure rules.

---

## The Seven Standard Phases

A phase is a quality gate, not a time box. It is done when its exit criteria are met. The framework will not advance you past a phase whose criteria are unmet — but it also will not nag you to advance.

| Phase | What "done" means |
|---|---|
| **DISCOVER** | At least one persona with a real scenario. Concept challenged or alternative framing raised. Core feature set established. At least one explicit out-of-scope item. Key decisions in the decision log. |
| **DEFINE** | Product brief with all sections substantively populated. Problem statement includes a real example. Three or more out-of-scope items. Every success criterion measurable. PRD written. |
| **DESIGN** | Architecture document. Tech spec. Data model. API contracts. UX flows. Solutioning gate passed. Key design decisions recorded. |
| **PLAN** | User stories with acceptance criteria. Gherkin specs or test specs generated. Traceability map started. |
| **IMPLEMENT** | All tests passing (RED → GREEN). Acceptance criteria satisfied. Change impact analysis if modifying existing code. Code committed. |
| **VERIFY** | Code review with no critical findings open. Security review if security-sensitive. Tests passing in CI. Documentation updated. Traceability map complete. |
| **SHIP** | PR merged or code deployed. Smoke test passing in production. Changelog updated. |

---

## Specialized Phases

These appear in specific workflows for work that does not fit the standard pipeline.

| Phase | Used in | Purpose |
|---|---|---|
| **DIAGNOSE** | bug-fix, hotfix, performance, security-patch, rollback | Establish reproduction case and root cause before touching code. Fix targets root cause, not symptom. |
| **ASSESS** | migrations, compliance, dependency-upgrade | Map scope and risk. Rollback plan exists before design starts. |
| **SCOPE** | tech-debt | Lock existing behavior with tests before refactoring. Tests must fail if any locked behavior changes. |
| **TRIAGE** | course-correction | Review every in-flight work item: keep / drop / repurpose / defer. Nothing silently abandoned. |
| **CUTOVER** | technology-migration | Switch traffic from old to new system. Hard gate — human decision required. |
| **CLEANUP** | technology-migration, api-deprecation | Remove old system after cutover or sunset date. |
| **POST-MORTEM** | hotfix, rollback | Required follow-on. Timeline, root cause, action items. |

---

## The Six Workflow Shapes

The shape determines the phase sequence. The work type determines the shape.

| Shape | Phases | Used by |
|---|---|---|
| `full-pipeline` | DISCOVER → DEFINE → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP | net-new-feature, external-integration, course-correction (with TRIAGE), security-planning |
| `abbreviated` | DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP | enhancement, infrastructure-change, onboarding-flow-design, release-planning, tech-debt (with SCOPE) |
| `extended-abbreviated` | ASSESS → DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP | compliance-requirement |
| `diagnostic` | DIAGNOSE → IMPLEMENT → VERIFY → SHIP | bug-fix, security-patch, performance-optimization, rollback-revert |
| `migration` | ASSESS → DESIGN → PLAN → IMPLEMENT → VERIFY → CUTOVER → CLEANUP | technology-migration, data-migration, api-deprecation, dependency-upgrade |
| `compressed` | DIAGNOSE → IMPLEMENT → SHIP → POST-MORTEM | hotfix |

---

## All 19 Work Types

When you tell `/sweetclaude:find-skill` what you want to do, it classifies the work into one of these. The classification determines the workflow shape, the entry category, and which phases apply.

### Build new

| Work type | Shape | Notes |
|---|---|---|
| `net-new-feature` | full-pipeline | Full SDLC. Use when the problem space is unknown or unvalidated. |
| `external-integration` | full-pipeline | DISCOVER means understanding the external API: auth, rate limits, contracts, failure modes. |
| `enhancement` | abbreviated | Use when problem space is known. Skip discovery. |

### Pivot

| Work type | Shape | Notes |
|---|---|---|
| `course-correction` | full-pipeline + TRIAGE | TRIAGE reviews in-flight work (keep/drop/repurpose). Triggered by aggregated signals or post-incident. |

### Strategy

| Work type | Shape | Notes |
|---|---|---|
| `security-planning` | full-pipeline (3-phase) | SHIP publishes a roadmap document. No code produced. |
| `release-planning` | abbreviated (3-phase) | SHIP publishes the release artifact and changelog. |

### Reactive

| Work type | Shape | Notes |
|---|---|---|
| `bug-fix` | diagnostic | DIAGNOSE = reproduction case + root cause. Fix targets root cause. |
| `security-patch` | diagnostic | VERIFY is a hard gate (security review mandatory). Expedited ship. |
| `hotfix` | compressed | Speed over ceremony. POST-MORTEM is required, not optional. |
| `rollback-revert` | diagnostic (2-phase) | Spawns POST-MORTEM automatically. |
| `performance-optimization` | diagnostic + DESIGN | DIAGNOSE = baseline benchmark. VERIFY = benchmark again. |

### Cleanup

| Work type | Shape | Notes |
|---|---|---|
| `tech-debt` | abbreviated + SCOPE | Lock existing behavior in tests before any refactor. |
| `dependency-upgrade` | migration (compressed) | ASSESS = review changelog for breaking changes. |
| `api-deprecation` | migration | CLEANUP fires at sunset date, not immediately after SHIP. |

### Migration

| Work type | Shape | Notes |
|---|---|---|
| `technology-migration` | migration | CUTOVER is a hard gate — human decision required. Old and new run in parallel until cutover. |
| `data-migration` | migration (no CUTOVER) | VERIFY is a hard gate — integrity checks (row counts, checksums, sample records) mandatory. |

### Compliance and infrastructure

| Work type | Shape | Notes |
|---|---|---|
| `compliance-requirement` | extended-abbreviated | VERIFY includes audit evidence generation. Triggered externally (customer ask, legal) or proactively from security-planning. |
| `infrastructure-change` | abbreviated | Hard gate at DESIGN for GA+ projects. |

### Onboarding

| Work type | Shape | Notes |
|---|---|---|
| `onboarding-flow-design` | abbreviated | Produces onboarding flow + playbook update. |

---

## Soft Gates and Hard Gates

Phase gates have exit criteria. Most criteria are advisory.

**Soft gates** can be bypassed with: *"I've addressed this informally — proceed."* The override is logged. SweetClaude continues.

**Hard gates** (⚠️) cannot be soft-bypassed. They apply to high-blast-radius work at GA+ stages. Override requires explicit risk acceptance, logged to the decision log.

The full list of hard gates:

| Work type | Phase | What is required |
|---|---|---|
| `data-migration` | ASSESS | Solutioning gate + change impact analysis |
| `data-migration` | VERIFY | Integrity checks (row counts, checksums, sample records) |
| `infrastructure-change` | DESIGN | Solutioning gate + rollback plan |
| `technology-migration` | DESIGN | Solutioning gate |
| `technology-migration` | CUTOVER | Human decision, explicit confirmation logged |
| `security-patch` | VERIFY | Security review post-fix |

The friction these gates add is deliberate. A data migration that ships without integrity checks can corrupt production data. A security patch that ships without review can introduce a new vulnerability while fixing the old one. The gates exist for situations where the worst case justifies the friction.

---

## Entry Categories

Every work item is classified into one of three entry categories. The category controls how strict prerequisite checking is.

| Category | What it means | Behavior |
|---|---|---|
| `cold-start` | New project, no prior context | Full discovery pipeline. No prerequisites checked. |
| `mid-project-planned` | Continuing work, following the pipeline | Classify → check prerequisites → flag gaps as advisory → offer to create missing artifacts → proceed. |
| `mid-project-reactive` | Something happened, immediate response needed | Skip prerequisite checks. Triage questions only. Proceed immediately. Missing prerequisites offered as optional parallel work. |

The `reactive` category is what makes hotfixes work. You cannot stop in the middle of a production incident to ask if your discovery artifacts are populated. The reactive category short-circuits the bureaucracy without disabling the safety mechanisms.

---

## Progressive Disclosure by Version Stage

The work types you see depend on the `version_stage` in `sweetclaude.yaml`. This prevents early-stage projects from being overwhelmed by work types they do not need yet.

| Stage | Visible buckets | Notes |
|---|---|---|
| `PROTOTYPE` | strategy, product | Early ideation. Code work is hidden. |
| `ALPHA` | strategy, product, design, code | Core implementation work types only. |
| `BETA` | strategy, product, design, code, operations | Operations capabilities surface. |
| `GA` | all | Full catalog including compliance. |
| `SCALED` | all | Operations surfaced prominently. |
| `MAINTAINED` | code, operations | Feature work de-emphasized. Bug fixes, security patches, dependency upgrades, compliance. |

You declare the stage. SweetClaude does not auto-advance it. A v2 rewrite resets it.

---

## The Solutioning Gate

For high-risk work (infrastructure changes, technology migrations, data migrations at GA+), DESIGN cannot complete until the solutioning gate passes. The gate confirms three things:

1. The problem is real and the proposed solution is the right one — not the first one that came to mind.
2. At least one alternative was considered and explicitly rejected with rationale.
3. A rollback plan is documented in detail. Step-by-step. Not "revert the commit."

You can run the gate explicitly with `/sweetclaude:design-solutioning-gate`, or it triggers automatically when a hard-gate work type reaches DESIGN.

---

## Where Phase State Lives

`sweetclaude.yaml` is the source of truth. The relevant fields:

```yaml
project:
  version_stage: BETA

session:
  deference_level: collaborative

work:
  last_item_id: WI-013
  active:
    id: WI-014
    type: net-new-feature
    workflow: [DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP]
    phase: IMPLEMENT
    title: "OAuth login flow"
    started: 2026-04-29T14:00:00+00:00
    entry_category: mid-project-planned
```

`work.last_item_id` is the monotonic counter — it persists across work item completions so IDs do not repeat.

---

## What to Read Next

- Why phases work this way → [How It Works](how-it-works.md)
- Concrete walkthroughs through specific phase sequences → [Walkthroughs](walkthroughs.md)
- The skills that operate within each phase → [Skills Reference](skills-reference.md)
