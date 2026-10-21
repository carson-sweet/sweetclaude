# Phases and Workflows

**Version:** 1.1
**Date:** 2026-10-21

This page is reference. If you want to understand *why* phases work the way they do, read [How It Works](how-it-works.md) first. This page lists the phases, the work types, the workflow shapes, and the gates.

---

## The Seven Standard Phases

A phase is a quality gate, not a time box. It is done when its exit criteria are met. The framework will not advance you past a phase whose criteria are unmet — but it also will not nag you to advance. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.)

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
| **ASSESS** | technology-migration, data-migration, api-deprecation, dependency-upgrade, compliance-requirement | Map scope and risk. Rollback plan exists before design starts. |
| **SCOPE** | tech-debt | Lock existing behavior with tests before refactoring. Tests must fail if any locked behavior changes. |
| **TRIAGE** | course-correction | Review every in-flight work item: keep / drop / repurpose / defer. Nothing silently abandoned. |
| **CUTOVER** | technology-migration | (Not currently enforced: the gate is not checked by code yet; Claude applies it as an instruction.) Switch traffic from old to new system. Hard gate — human decision required. |
| **CLEANUP** | technology-migration, api-deprecation | Remove old system after cutover or sunset date. |
| **POST-MORTEM** | hotfix, rollback | Required follow-on. Timeline, root cause, action items. |

---

## The Six Workflow Shapes

A shape is a phase sequence. Work types follow a shape exactly, or carry their own sequence where they differ. Routing does not pick a shape: `/sweetclaude:go` hands your request to the router, which selects one of six categories (plan, design, build, maintain, configure, utils) and invokes that category command. The shapes and sequences on this page apply where a phase or a hard gate depends on them.

| Shape | Phases | Followed exactly by |
|---|---|---|
| `full-pipeline` | DISCOVER → DEFINE → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP | net-new-feature, external-integration |
| `abbreviated` | DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP | enhancement, infrastructure-change, onboarding-flow-design |
| `extended-abbreviated` | ASSESS → DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP | compliance-requirement |
| `diagnostic` | DIAGNOSE → IMPLEMENT → VERIFY → SHIP | bug-fix, security-patch |
| `migration` | ASSESS → DESIGN → PLAN → IMPLEMENT → VERIFY → CUTOVER → CLEANUP | technology-migration |
| `compressed` | DIAGNOSE → IMPLEMENT → SHIP → POST-MORTEM | hotfix |

---

## All 19 Work Types

Each work type has a phase sequence defined in `config/workflow-templates.yaml`. The sequence tells you which phases the work passes through and which hard gates apply.

### Build new

| Work type | Phases | Notes |
|---|---|---|
| `net-new-feature` | DISCOVER → DEFINE → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP | Full SDLC. Use when the problem space is unknown or unvalidated. |
| `external-integration` | DISCOVER → DEFINE → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP | DISCOVER means understanding the external API: auth, rate limits, contracts, failure modes. |
| `enhancement` | DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP | Use when problem space is known. Skip discovery. |

### Pivot

| Work type | Phases | Notes |
|---|---|---|
| `course-correction` | DISCOVER → DEFINE → TRIAGE → SHIP | TRIAGE reviews in-flight work (keep/drop/repurpose). Triggered by aggregated signals or post-incident. |

### Strategy

| Work type | Phases | Notes |
|---|---|---|
| `security-planning` | DISCOVER → DEFINE → SHIP | SHIP publishes a roadmap document. No code produced. |
| `release-planning` | DEFINE → PLAN → SHIP | SHIP publishes the release artifact and changelog. |

### Reactive

| Work type | Phases | Notes |
|---|---|---|
| `bug-fix` | DIAGNOSE → IMPLEMENT → VERIFY → SHIP | DIAGNOSE = reproduction case + root cause. Fix targets root cause. |
| `security-patch` | DIAGNOSE → IMPLEMENT → VERIFY → SHIP | VERIFY is a hard gate (security review mandatory). Expedited ship. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.) |
| `hotfix` | DIAGNOSE → IMPLEMENT → SHIP → POST-MORTEM | Speed over ceremony. POST-MORTEM is required, not optional. |
| `rollback-revert` | DIAGNOSE → SHIP | Spawns POST-MORTEM automatically. |
| `performance-optimization` | DIAGNOSE → DESIGN → IMPLEMENT → VERIFY → SHIP | DIAGNOSE = baseline benchmark. VERIFY = benchmark again. |

### Cleanup

| Work type | Phases | Notes |
|---|---|---|
| `tech-debt` | DEFINE → SCOPE → IMPLEMENT → VERIFY → SHIP | SCOPE takes the place of DESIGN: lock existing behavior in tests before any refactor. |
| `dependency-upgrade` | ASSESS → IMPLEMENT → VERIFY → SHIP | ASSESS = review changelog for breaking changes. |
| `api-deprecation` | ASSESS → DEFINE → IMPLEMENT → VERIFY → SHIP → CLEANUP | CLEANUP fires at sunset date, not immediately after SHIP. |

### Migration

| Work type | Phases | Notes |
|---|---|---|
| `technology-migration` | ASSESS → DESIGN → PLAN → IMPLEMENT → VERIFY → CUTOVER → CLEANUP | CUTOVER is a hard gate — human decision required. Old and new run in parallel until cutover. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.) |
| `data-migration` | ASSESS → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP | No CUTOVER. VERIFY is a hard gate — integrity checks (row counts, checksums, sample records) mandatory. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.) |

### Compliance and infrastructure

| Work type | Phases | Notes |
|---|---|---|
| `compliance-requirement` | ASSESS → DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP | VERIFY includes audit evidence generation. Triggered externally (customer ask, legal) or proactively from security-planning. |
| `infrastructure-change` | DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP | Hard gate at DESIGN for GA+ projects. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.) |

### Onboarding

| Work type | Phases | Notes |
|---|---|---|
| `onboarding-flow-design` | DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP | Produces onboarding flow + playbook update. |

---

## Soft Gates and Hard Gates

Phase gates have exit criteria. Most criteria are advisory.

**Soft gates** can be bypassed with: *"I've addressed this informally — proceed."* The override is logged. SweetClaude continues. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.)

**Hard gates** cannot be soft-bypassed. They apply to high-blast-radius work at GA+ stages. Override requires explicit risk acceptance, logged to the decision log. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.)

The full list of hard gates, with the prerequisites listed in `config/workflow-templates.yaml`:

| Work type | Phase | What is required |
|---|---|---|
| `data-migration` | ASSESS | Solutioning gate and change impact analysis |
| `data-migration` | VERIFY | Integrity checks (row counts, checksums, sample records) |
| `infrastructure-change` | DESIGN | Solutioning gate, change impact analysis and rollback plan |
| `technology-migration` | DESIGN | Solutioning gate, change impact analysis and parallel run plan |
| `technology-migration` | CUTOVER | Human decision, explicit confirmation logged |
| `security-patch` | VERIFY | Security review post-fix |

The friction these gates add is deliberate. A data migration that ships without integrity checks can corrupt production data. A security patch that ships without review can introduce a new vulnerability while fixing the old one. The gates exist for situations where the worst case justifies the friction.

---

## Entry Category Field

The active work item carries an `entry_category` field. The small-story and large-story controllers write it: `small-story` or `large-story` identifies which controller owns the item in flight. Nothing classifies work into other entry categories.

---

## The Solutioning Gate

For high-risk work (infrastructure changes, technology migrations, data migrations at GA+), DESIGN cannot complete until the solutioning gate passes. The gate confirms three things:

1. The problem is real and the proposed solution is the right one — not the first one that came to mind.
2. At least one alternative was considered and explicitly rejected with rationale.
3. A rollback plan is documented in detail. Step-by-step. Not "revert the commit."

You can run the gate explicitly with `/sweetclaude:design` and ask to validate the solution, or it triggers automatically when a hard-gate work type reaches DESIGN. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.)

---

## Where Phase State Lives

`sweetclaude.yaml` is the source of truth. The relevant fields:

```yaml
project:
  version_stage: BETA

session:
  deference_level: collaborative

work:
  last_item_id: ISSUE-013
  active:
    id: ISSUE-014
    phase: IMPLEMENT
    title: "OAuth login flow"
    started: 2026-04-29T14:00:00+00:00
    entry_category: small-story
```

`work.last_item_id` records the most recently closed work item. Closeout sets it to the ID of the item just closed, and new IDs come from the next free `ISSUE-NNN` in the roadmap cache.

---

## What to Read Next

- Why phases work this way → [How It Works](how-it-works.md)
- Concrete walkthroughs through specific phase sequences → [Walkthroughs](walkthroughs.md)
- The skills that operate within each phase → [Skills Reference](skills-reference.md)
