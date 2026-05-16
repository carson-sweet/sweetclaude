# Phase/Workflow Separation — Plan 1: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the core data layer for phase/workflow separation — workflow templates config, updated phase gates, renamed task config, and phase.yaml v2 schema template.

**Architecture:** Three config files drive the new model: `workflow-templates.yaml` defines the phase sequence per work type, `phase-gates.md` defines exit criteria per phase × work type, and `phase-skills.yaml` reflects renames and new tasks. These are consumed by the orchestration skills (Plan 2) and new skills (Plan 3).

**Tech Stack:** Markdown, YAML. No build step. Sync to `~/.claude/` after changes via `./install.sh` or manual copy.

**Spec:** `docs/superpowers/specs/2026-04-29-phase-workflow-separation-design.md`

**Depends on:** Nothing — this is Plan 1.
**Blocks:** Plan 2 (orchestration skills), Plan 3 (new and renamed skills).

---

## File Map

| Action | File | Purpose |
|---|---|---|
| Create | `config/workflow-templates.yaml` | Phase sequence per work type (19 templates) |
| Modify | `config/phase-skills.yaml` | Add new task names, apply renames |
| Overwrite | `rules/sweetclaude/phase-gates.md` | Full phase × work type exit criteria |
| Create | `config/templates/phase-v2.yaml` | Schema template for new projects |
| Modify | `docs/architecture-sweetclaude-v1-2026-04-13.md` | Document new model in architecture |
| Sync | `~/.claude/` | Copy all changed files to installed location |

---

## Task 1: Create workflow-templates.yaml

**Files:**
- Create: `config/workflow-templates.yaml`

- [ ] **Step 1: Create the file**

```yaml
# config/workflow-templates.yaml
# Defines the ordered phase sequence for each work type.
# Five shapes: full-pipeline, abbreviated, diagnostic, migration, compressed.
# Phase names: DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP,
#              DIAGNOSE, ASSESS, SCOPE, TRIAGE, CUTOVER, CLEANUP, POST-MORTEM
schema_version: 1

shapes:
  full-pipeline:
    phases: [DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP]
  abbreviated:
    phases: [DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP]
  diagnostic:
    phases: [DIAGNOSE, IMPLEMENT, VERIFY, SHIP]
  migration:
    phases: [ASSESS, DESIGN, PLAN, IMPLEMENT, VERIFY, CUTOVER, CLEANUP]
  compressed:
    phases: [DIAGNOSE, IMPLEMENT, SHIP, POST-MORTEM]

work_types:

  net-new-feature:
    shape: full-pipeline
    phases: [DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [cold-start, mid-project-planned]
    notes: "Full SDLC. Use when problem space is unknown or unvalidated."

  external-integration:
    shape: full-pipeline
    phases: [DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [cold-start, mid-project-planned]
    notes: "DISCOVER = understand external API, auth model, rate limits, data contracts, failure modes."

  course-correction:
    shape: full-pipeline
    phases: [DISCOVER, DEFINE, TRIAGE]
    entry_categories: [mid-project-planned, mid-project-reactive]
    notes: "Ends at TRIAGE instead of SHIP. TRIAGE spawns new work items. Can be triggered deliberately (accumulated signals) or reactively (post-incident)."

  security-planning:
    shape: full-pipeline
    phases: [DISCOVER, DEFINE, SHIP]
    entry_categories: [cold-start, mid-project-planned]
    notes: "SHIP = publish roadmap document. No code produced."

  enhancement:
    shape: abbreviated
    phases: [DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [mid-project-planned]
    notes: "Use when problem space is known. Skip discovery."

  tech-debt:
    shape: abbreviated
    phases: [DEFINE, SCOPE, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [mid-project-planned]
    notes: "SCOPE = lock existing behavior with tests before touching code."

  compliance-requirement:
    shape: extended-abbreviated
    phases: [ASSESS, DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [mid-project-planned, mid-project-reactive]
    notes: "VERIFY includes audit evidence generation. Can be triggered externally (customer ask, legal) or proactively from security-planning."

  infrastructure-change:
    shape: abbreviated
    phases: [DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [mid-project-planned]
    hard_gates:
      DESIGN: "Solutioning gate required at GA+. Rollback plan must exist before DESIGN completes."
    notes: "Hard gate at DESIGN for GA+ projects."

  onboarding-flow-design:
    shape: abbreviated
    phases: [DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [mid-project-planned]
    notes: "Produces onboarding flow + playbook update."

  release-planning:
    shape: abbreviated
    phases: [DEFINE, PLAN, SHIP]
    entry_categories: [mid-project-planned]
    notes: "Collapses to three phases. SHIP = publish release artifact and changelog."

  bug-fix:
    shape: diagnostic
    phases: [DIAGNOSE, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [mid-project-planned, mid-project-reactive]
    notes: "DIAGNOSE = reproduction case + root cause. Fix targets root cause, not symptom."

  security-patch:
    shape: diagnostic
    phases: [DIAGNOSE, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [mid-project-planned, mid-project-reactive]
    hard_gates:
      VERIFY: "Security review mandatory before SHIP. No soft bypass."
    notes: "Expedited ship. VERIFY is a hard gate. Coordinated disclosure deadline may apply."

  performance-optimization:
    shape: diagnostic
    phases: [DIAGNOSE, DESIGN, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [mid-project-planned]
    notes: "DIAGNOSE = establish baseline benchmark and identify bottleneck. VERIFY = benchmark again."

  rollback-revert:
    shape: diagnostic
    phases: [DIAGNOSE, SHIP]
    entry_categories: [mid-project-reactive]
    post_ship_spawn: POST-MORTEM
    notes: "Collapses to two phases. No implementation — reverting an artifact. Spawns POST-MORTEM."

  technology-migration:
    shape: migration
    phases: [ASSESS, DESIGN, PLAN, IMPLEMENT, VERIFY, CUTOVER, CLEANUP]
    entry_categories: [mid-project-planned]
    hard_gates:
      DESIGN: "Solutioning gate required at GA+."
      CUTOVER: "Human decision required. Explicit confirmation logged to decision log. No soft bypass."
    notes: "Old and new systems run in parallel until CUTOVER. CLEANUP removes old system."

  data-migration:
    shape: migration
    phases: [ASSESS, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [mid-project-planned]
    hard_gates:
      VERIFY: "Integrity checks mandatory (row counts, checksums, sample records). No soft bypass."
      ASSESS: "Solutioning gate + Change impact analysis required at GA+."
    notes: "No CUTOVER phase. VERIFY = data integrity reconciliation."

  api-deprecation:
    shape: migration
    phases: [ASSESS, DEFINE, IMPLEMENT, VERIFY, SHIP, CLEANUP]
    entry_categories: [mid-project-planned]
    notes: "CLEANUP fires at sunset date, not immediately after SHIP."

  dependency-upgrade:
    shape: migration
    phases: [ASSESS, IMPLEMENT, VERIFY, SHIP]
    entry_categories: [mid-project-planned, mid-project-reactive]
    notes: "Compressed migration. ASSESS = review changelog for breaking changes."

  hotfix:
    shape: compressed
    phases: [DIAGNOSE, IMPLEMENT, SHIP, POST-MORTEM]
    entry_categories: [mid-project-reactive]
    post_ship_spawn: POST-MORTEM
    notes: "Speed over ceremony. POST-MORTEM is required after SHIP, not optional."

hard_gate_policy:
  soft_gate_escape: "I've addressed this informally [optional note] — proceed."
  hard_gate_override: "User must explicitly confirm risk acceptance. Override logged to decision log."
  hard_gates_apply_at: [GA, SCALED, MAINTAINED]
  hard_gate_tasks:
    - task: data-migration
      prerequisites: [solutioning-gate, change-impact-analysis, rollback-plan]
      reason: "Blast radius: production data loss"
    - task: infrastructure-change
      prerequisites: [solutioning-gate, change-impact-analysis, rollback-plan]
      reason: "Blast radius: outage, data loss"
    - task: technology-migration
      prerequisites: [solutioning-gate, change-impact-analysis, parallel-run-plan]
      reason: "Blast radius: production instability"
    - task: security-patch
      prerequisites: [security-review-post-fix]
      reason: "Cannot ship an unreviewed security fix"

entry_categories:
  cold-start:
    description: "New project, no prior context."
    behavior: "Run full discovery pipeline. No prerequisites checked."
    entry_tasks: [net-new-feature, external-integration, security-planning, course-correction]

  mid-project-planned:
    description: "Continuing work, following the pipeline."
    behavior: "Classify → check prerequisites → flag gaps as advisory → offer to create missing artifacts → proceed."
    entry_tasks:
      - net-new-feature
      - enhancement
      - sprint-planning
      - backlog-management
      - user-feedback-triage
      - release-planning
      - tech-debt
      - security-patch
      - performance-optimization
      - external-integration
      - technology-migration
      - api-deprecation
      - data-migration
      - infrastructure-change
      - compliance-requirement
      - course-correction

  mid-project-reactive:
    description: "Something happened that demands immediate response."
    behavior: "Skip all prerequisite checks. Triage questions only. Proceed immediately. Offer missing prerequisites as optional parallel work."
    entry_tasks:
      - bug-fix
      - hotfix
      - something-broke
      - rollback-revert
      - security-patch
      - user-feedback-triage
      - course-correction

progressive_disclosure:
  PROTOTYPE:
    visible_domains: [discovery, definition]
  ALPHA:
    visible_domains: [discovery, definition, design, planning, core-implementation]
    core_implementation: [net-new-feature, bug-fix, external-integration]
  BETA:
    visible_domains: [discovery, definition, design, planning, implementation, verification, documentation, release-planning]
  GA:
    visible_domains: [all]
  SCALED:
    visible_domains: [all]
    surface_prominently: [operations]
  MAINTAINED:
    visible_domains: [bug-fix, security-patch, dependency-upgrade, compliance-requirement, break-glass-notes, documentation]
    de_emphasize: [feature-work]
```

- [ ] **Step 2: Verify the file**

Read `config/workflow-templates.yaml`. Confirm:
- All 19 work types are present
- Each has `phases`, `entry_categories`, and `notes`
- Hard gate tasks match the spec (data-migration, infrastructure-change, technology-migration, security-patch)
- Entry categories are populated correctly
- Progressive disclosure stages match the spec

- [ ] **Step 3: Commit**

```bash
git add config/workflow-templates.yaml
git commit -m "feat: add workflow-templates.yaml — phase sequences per work type"
```

---

## Task 2: Update phase-skills.yaml

**Files:**
- Modify: `config/phase-skills.yaml`

Current file has domain buckets (`product:`, `design:`, `code:`). We need to add new task names and reflect the renames.

- [ ] **Step 1: Read the current file**

Read `config/phase-skills.yaml` to see the full current content before modifying.

- [ ] **Step 2: Add new task entries and renames to the product bucket**

In the `product:` skills list, apply these changes:
- Remove: `sweetclaude:strategy/narrative-arc` → replace with `sweetclaude:concept-framing`
- Add: `sweetclaude:course-correction`
- Add: `sweetclaude:signal-aggregation`
- Add: `sweetclaude:release-planning`
- Add: `sweetclaude:security-planning`

- [ ] **Step 3: Add new task entries to the code bucket**

In the `code:` skills list, add:
- `sweetclaude:hotfix`
- `sweetclaude:security-patch`
- `sweetclaude:performance-optimization`
- `sweetclaude:external-integration`
- `sweetclaude:technology-migration`
- `sweetclaude:api-deprecation`
- `sweetclaude:data-migration`
- `sweetclaude:dependency-upgrade`
- `sweetclaude:infrastructure-change`
- `sweetclaude:feature-flag-management`
- `sweetclaude:rollback-revert`
- `sweetclaude:onboarding-flow-design`

- [ ] **Step 4: Add new task entries to the operations bucket (new bucket)**

Add a new `operations:` bucket after `code:`:

```yaml
operations:
  skills:
    - sweetclaude:something-broke
    - sweetclaude:postmortem
    - sweetclaude:break-glass-notes
    - sweetclaude:sla-error-budget-review
    - sweetclaude:monitoring-alerting
    - sweetclaude:onboarding-playbook
  agents: []
  hooks: []
```

- [ ] **Step 5: Verify the file**

Read `config/phase-skills.yaml`. Confirm:
- No duplicate entries
- New operations bucket is present
- All new skills from Plan 3 are listed (even though the skills don't exist yet — the config is forward-declared)
- Renames are applied

- [ ] **Step 6: Commit**

```bash
git add config/phase-skills.yaml
git commit -m "feat: update phase-skills.yaml — new tasks, renames, operations bucket"
```

---

## Task 3: Create phase.yaml v2 schema template

**Files:**
- Create: `config/templates/phase-v2.yaml`

This is the template new projects get when initialized. It shows the v2 schema.

- [ ] **Step 1: Create the template**

```yaml
# .sweetclaude/state/phase.yaml
# SweetClaude phase state — schema version 2
# version_stage: where this major version is in its release lifecycle
# active_work_item: what specific work is in progress right now
schema_version: 2

# Slow-moving. Declared by user. Rarely updated.
# Values: PROTOTYPE | ALPHA | BETA | GA | SCALED | MAINTAINED
version_stage: PROTOTYPE

deference_level: collaborative  # collaborative | guided | autonomous
project_type: net-new           # net-new | existing-code
safety_snapshot: ~              # set by init if applicable

# The work item currently in progress.
# Set by find-skill when work begins. Cleared on SHIP.
active_work_item:
  id: ~                         # e.g. WI-001
  type: ~                       # see config/workflow-templates.yaml for valid types
  workflow: []                  # ordered phase list for this work type
  phase: ~                      # current phase within the workflow
  title: ~                      # short description of the work
  started: ~                    # YYYY-MM-DD
  entry_category: ~             # cold-start | mid-project-planned | mid-project-reactive
```

- [ ] **Step 2: Verify the template**

Read `config/templates/phase-v2.yaml`. Confirm:
- `schema_version: 2` is present
- `version_stage` field replaces the old `phase` field
- `active_work_item` object is present with all required fields
- All fields have comments explaining valid values
- No old `phase` field remains (that was schema_version: 1)

- [ ] **Step 3: Commit**

```bash
git add config/templates/phase-v2.yaml
git commit -m "feat: add phase.yaml v2 schema template"
```

---

## Task 4: Overhaul phase-gates.md

**Files:**
- Overwrite: `rules/sweetclaude/phase-gates.md`

This is the most substantial change. The current file has exit criteria for the 7-phase pipeline only. We're replacing it with the full phase × work type matrix from the spec.

- [ ] **Step 1: Read the current file**

Read `rules/sweetclaude/phase-gates.md` to understand what's being replaced.

- [ ] **Step 2: Write the new file**

The new file content is derived directly from the Phase Gate Exit Criteria section of the spec at `docs/superpowers/specs/2026-04-29-phase-workflow-separation-design.md`.

Write `rules/sweetclaude/phase-gates.md` with this structure:

```markdown
# SweetClaude Phase Gates
# Schema version: 2
# Generated from: docs/superpowers/specs/2026-04-29-phase-workflow-separation-design.md

Entry and exit criteria for each work type × phase combination.
A phase cannot advance until exit criteria are met.
User can override with "I've addressed this informally — proceed" (soft gate).
Hard gates are marked ⚠️ and cannot be soft-bypassed at GA+.

> See config/workflow-templates.yaml for the phase sequence per work type.
> See config/workflow-templates.yaml hard_gate_policy for the full gate policy.

## Phase Definitions

### Standard phases (all work types)
- **DISCOVER** — understand the problem space before committing to a solution
- **DEFINE** — specify what will be built and how success is measured
- **DESIGN** — decide the technical approach before writing code
- **PLAN** — break work into stories, tests, and tasks
- **IMPLEMENT** — write the code, making tests go from RED to GREEN
- **VERIFY** — review, test, and validate the implementation
- **SHIP** — merge, deploy, and confirm in production

### New phases (specific work types)
- **DIAGNOSE** — understand root cause before fixing. Reproduction case, baseline benchmark, or incident triage.
- **ASSESS** — map scope and risk before committing. What's affected? What's the rollback plan?
- **SCOPE** — lock existing behavior with tests before refactoring. Defines what changes and what must not.
- **TRIAGE** — review all in-flight work after a course correction: keep / drop / repurpose.
- **CUTOVER** — switch traffic or data from old system to new. Both have been running in parallel.
- **CLEANUP** — remove old system artifacts after cutover or deprecation sunset.
- **POST-MORTEM** — required follow-on after hotfix or rollback. What happened, why, what changes.

---
```

Then copy the full exit criteria section from the spec for all 19 work types. The spec section is titled "Phase Gate Exit Criteria" and contains the complete content.

- [ ] **Step 3: Verify the file**

Read `rules/sweetclaude/phase-gates.md`. Confirm:
- All 19 work types are present
- Hard gates are marked ⚠️
- New phase definitions (DIAGNOSE, ASSESS, SCOPE, TRIAGE, CUTOVER, CLEANUP, POST-MORTEM) are defined
- Hotfix SHIP gate says "async notification OR self-review checklist" (not "one other person")
- Compliance requirement workflow has ASSESS → DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP
- Data migration VERIFY has integrity checks as a hard gate

- [ ] **Step 4: Commit**

```bash
git add rules/sweetclaude/phase-gates.md
git commit -m "feat: overhaul phase-gates.md — full phase x work type exit criteria matrix"
```

---

## Task 5: Update architecture document

**Files:**
- Modify: `docs/architecture-sweetclaude-v1-2026-04-13.md`

The architecture doc references the old single-`phase` model. Update the relevant sections.

- [ ] **Step 1: Read the current architecture doc**

Read `docs/architecture-sweetclaude-v1-2026-04-13.md`, sections covering phase state and `phase.yaml`.

- [ ] **Step 2: Update the phase model description**

Find the section describing `phase.yaml` and the phase pipeline. Update it to describe:
- Two dimensions: `version_stage` (slow-moving, declared) and `active_work_item.phase` (fast-moving, type-driven)
- Five workflow shapes with 19 work type templates
- Three entry point categories (cold-start, mid-project-planned, mid-project-reactive)
- Soft gate / hard gate policy

Add a cross-reference to `config/workflow-templates.yaml` and the updated `rules/sweetclaude/phase-gates.md`.

- [ ] **Step 3: Update the revised date in the architecture doc header**

Change `**Revised:**` to `2026-04-29 — reflects phase/workflow separation (schema v2)`.

- [ ] **Step 4: Verify**

Read the updated sections. Confirm no references to the old single-`phase` model remain. Confirm `version_stage` and `active_work_item` are mentioned.

- [ ] **Step 5: Commit**

```bash
git add docs/architecture-sweetclaude-v1-2026-04-13.md
git commit -m "docs: update architecture doc for phase/workflow separation (schema v2)"
```

---

## Task 6: Sync to installed location

**Files:**
- Sync: `~/.claude/rules/sweetclaude/phase-gates.md`
- Sync: `~/.claude/` (all changed config files)

Per the SweetClaude sync requirement: after editing framework files in the repo, copy to `~/.claude/` to keep both in sync.

- [ ] **Step 1: Check what install.sh does**

```bash
cat install.sh | head -50
```

Understand the sync mechanism before running it.

- [ ] **Step 2: Run install or manual copy**

If `install.sh` handles syncing:
```bash
./install.sh
```

If manual copy is needed:
```bash
cp rules/sweetclaude/phase-gates.md ~/.claude/rules/sweetclaude/phase-gates.md
cp config/workflow-templates.yaml ~/.claude/config/sweetclaude/workflow-templates.yaml
cp config/phase-skills.yaml ~/.claude/config/sweetclaude/phase-skills.yaml
cp config/templates/phase-v2.yaml ~/.claude/config/sweetclaude/templates/phase-v2.yaml
```

- [ ] **Step 3: Verify the installed files match the repo**

```bash
diff rules/sweetclaude/phase-gates.md ~/.claude/rules/sweetclaude/phase-gates.md
diff config/workflow-templates.yaml ~/.claude/config/sweetclaude/workflow-templates.yaml
```

Expected: no diff output (files are identical).

- [ ] **Step 4: Commit the sync (if install.sh produces any generated files)**

```bash
git status
# If any generated files were created by install.sh, add and commit them
git add -p  # review carefully before staging
git commit -m "chore: sync installed files after phase/workflow separation foundation"
```

---

## Self-Review Checklist

- [ ] `config/workflow-templates.yaml` — all 19 work types present, hard gate policy defined, entry categories correct, progressive disclosure stages match spec
- [ ] `config/phase-skills.yaml` — new operations bucket, all new skill names forward-declared, renames applied, no duplicates
- [ ] `config/templates/phase-v2.yaml` — schema_version: 2, version_stage field present, active_work_item object present
- [ ] `rules/sweetclaude/phase-gates.md` — all 19 work types, hard gates marked ⚠️, new phase definitions present, Hotfix SHIP gate softened for solo devs
- [ ] Architecture doc — old single-phase references updated, cross-references added
- [ ] Installed files sync'd and verified via diff

---

## What Comes Next

**Plan 2 — Orchestration skills:** `find-skill`, `master`, `status` updates for three-category routing and progressive disclosure. Depends on this plan being complete.

**Plan 3 — New and renamed skills:** `hotfix`, `security-patch`, `external-integration`, `course-correction`, `postmortem`, `release-planning`, `break-glass-notes`, `something-broke`, `security-planning`. Can start after Plan 1.
