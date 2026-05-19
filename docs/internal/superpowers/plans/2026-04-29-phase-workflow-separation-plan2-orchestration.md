# Phase/Workflow Separation — Plan 2: Orchestration Skills

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `find-skill`, `master`, and `status` skills to read and write the v2 two-dimension phase model (`version_stage` + `active_work_item`).

**Architecture:** Three skill files consume `.sweetclaude/state/phase.yaml`. Plan 1 introduced the v2 schema; this plan makes the orchestration layer use it. `find-skill` gains three-category entry routing and writes `active_work_item` on classification. `master` reads `version_stage` and `active_work_item.phase` at session start and gains an operations bucket. `status` displays both dimensions and shows workflow progress.

**Tech Stack:** Markdown skill files. No build step. Sync to `~/.claude/` after changes.

**Spec:** `docs/superpowers/specs/2026-04-29-phase-workflow-separation-design.md`

**Depends on:** Plan 1 complete (`config/workflow-templates.yaml` and `config/templates/phase-v2.yaml` exist).
**Blocks:** Plan 3 (new skills invoke find-skill routing logic).

---

## File Map

| Action | File | Purpose |
|---|---|---|
| Modify | `skills/find-skill/SKILL.md` | Three-category routing, v2 state write, new work type rows, progressive disclosure |
| Modify | `skills/master/SKILL.md` | Two-dimension state read, operations bucket, v2 phase transition references |
| Modify | `skills/status/SKILL.md` | Two-dimension display, workflow progress |
| Sync | `~/.claude/skills/sweetclaude/` | Copy find-skill, master, status to installed location |

---

## Task 1: Update find-skill/SKILL.md

**Files:**
- Modify: `skills/find-skill/SKILL.md`

The current skill classifies work into 4 domain buckets and writes old `phase`/`work_type`/`bucket` to state. It needs: (1) three entry categories that change routing behavior, (2) v2 state write, (3) new work type rows for Plan 3 skills, (4) progressive disclosure filtering by `version_stage`.

- [ ] **Step 1: Read the current file**

Read `skills/find-skill/SKILL.md` to understand the full current content before editing.

- [ ] **Step 2: Replace the Process section (steps 1–5)**

Find the `## Process` section. It currently starts at line 14 with `1. **Ask or detect.**` and ends at line 87 with the Invoke step. Replace the content from `1. **Ask or detect.**` through the end of step 4 (the Invoke step, currently `4. **Invoke.**`) with:

```markdown
1. **Read version stage.** Read `.sweetclaude/state/phase.yaml`. Extract `version_stage` (default: PROTOTYPE if not set). This controls which work types are surfaced.

2. **Determine entry category** from context before asking anything:
   - `cold-start` — project has no prior `active_work_item` OR user is explicitly starting something new from scratch
   - `mid-project-reactive` — user describes something broken, failing, urgent, or in-progress emergency ("it's down", "something broke", "production issue", "need to hotfix")
   - `mid-project-planned` — all other cases: continuing work, planning next steps, choosing from backlog

3. **Ask or detect.** If the user has not stated the work type, ask:
   > "What do you want to work on?"

   If the user has described something, classify it and propose:
   > "This looks like {work-type} — I'll set up the {workflow-shape} pipeline and start `sweetclaude:{skill}`. Correct?"

   Wait for confirmation before proceeding.

4. **Classify into a work type.** Use the tables below. Only surface work types appropriate for the current `version_stage`:
   - **PROTOTYPE**: discovery and definition work only (net-new-feature, security-planning)
   - **ALPHA**: add design, planning, core implementation (net-new-feature, bug-fix, external-integration, enhancement)
   - **BETA+**: full catalog

### strategy/ — why it matters and to whom

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Concept articulation | DISCOVER, DEFINE, SHIP | `sweetclaude:documents-narrative-arc` |
| Pain analysis | DISCOVER, DEFINE, SHIP | `sweetclaude:product-discovery` |
| Customer profiling | DISCOVER, DEFINE, SHIP | `sweetclaude:product-user-personas` |
| Competitive landscape | DISCOVER, DEFINE, SHIP | `sweetclaude:product-competition` |
| Research / deep research | DISCOVER, DEFINE, SHIP | `sweetclaude:documents-academic-research` |
| Meeting preparation | DEFINE | `sweetclaude:misc-meeting-prep` |
| Market messaging | DEFINE | `sweetclaude:product-market-messaging` |
| Security planning | DISCOVER, DEFINE, SHIP | `sweetclaude:security-planning` *(Plan 3)* |
| Course correction | DISCOVER, DEFINE, TRIAGE, SHIP | `sweetclaude:course-correction` *(Plan 3)* |

### product/ — what to build and why

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Net-new feature | DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:product-discovery` |
| Enhancement / iteration | DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:product-prd` |
| Product brief | DEFINE | `sweetclaude:product-brief` |
| Requirements / PRD | DEFINE | `sweetclaude:product-prd` |
| User stories | PLAN | `sweetclaude:product-user-stories` |
| Test specs from stories | PLAN | `sweetclaude:product-user-tdd-tests` |
| Scope change | any | `sweetclaude:product-manage-scope` |
| Backlog management | any | `sweetclaude:product-backlog` |
| Sprint / release planning | DEFINE, PLAN, SHIP | `sweetclaude:product-sprint-plan` |
| Market / technical research | DISCOVER | `sweetclaude:product-research` |
| Release planning | DEFINE, PLAN, SHIP | `sweetclaude:release-planning` *(Plan 3)* |

### design/ — how it's structured

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

### code/ — writing and verifying code

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
| Testing | any | `sweetclaude:code-testing` |
| Code / security / compliance review | VERIFY | `sweetclaude:code-review` |
| Compliance requirement | ASSESS, DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-feature` |

### operations/ — keeping it running

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Something broke | DIAGNOSE, SHIP, POST-MORTEM | `sweetclaude:something-broke` *(Plan 3)* |
| Postmortem | DIAGNOSE, SHIP | `sweetclaude:postmortem` *(Plan 3)* |
| Break-glass notes | DEFINE, SHIP | `sweetclaude:break-glass-notes` *(Plan 3)* |
| Onboarding playbook | DEFINE, IMPLEMENT, SHIP | `sweetclaude:code-feature` |

5. **Apply entry category behavior:**

   **cold-start:**
   > "Starting fresh — full discovery pipeline. No prerequisites to check. Let's go."
   Proceed to invoke without any prerequisite checks.

   **mid-project-planned:**
   Check whether the work type has documented prerequisites in `config/workflow-templates.yaml` (look in `hard_gate_policy.hard_gate_tasks`). If any prerequisites are missing:
   > "Before starting {work-type}, the usual prerequisites are: {list}. These look incomplete or missing. I've addressed this informally — or would you like to create any of them first?"
   This is advisory only (soft gate). The user can proceed regardless.

   **mid-project-reactive:**
   > "Got it — moving fast. Tell me: {triage question specific to work type, e.g. 'what exactly is broken?' for bug/hotfix, or 'which version is affected?' for security patch}."
   Skip all prerequisite checks. One triage question max before starting.

6. **Update state.** Determine the `id` by reading `phase.yaml` for the last `active_work_item.id` and incrementing (WI-001 if none). Write `active_work_item` to `.sweetclaude/state/phase.yaml`:

   ```yaml
   active_work_item:
     id: WI-{NNN}
     type: {work_type_key}
     workflow: [{phases from table above, comma-separated}]
     phase: {first phase in workflow}
     title: "{one-sentence description from user's request}"
     started: {YYYY-MM-DD today}
     entry_category: {cold-start|mid-project-planned|mid-project-reactive}
   ```

   Example for a bug fix entered reactively:
   ```yaml
   active_work_item:
     id: WI-003
     type: bug-fix
     workflow: [DIAGNOSE, IMPLEMENT, VERIFY, SHIP]
     phase: DIAGNOSE
     title: "Login fails when email contains uppercase letters"
     started: 2026-04-29
     entry_category: mid-project-reactive
   ```

7. **Invoke.** Use the Skill tool to start the matched skill. Pass any relevant context from the user's description as the skill's starting input so the user does not have to repeat themselves.
```

- [ ] **Step 3: Verify the Process section**

Read `skills/find-skill/SKILL.md`. Confirm:
- Three entry categories are present (cold-start, mid-project-planned, mid-project-reactive)
- `version_stage` is read at step 1
- An `operations/` table section is present
- `active_work_item` v2 state write is present with all 7 fields (id, type, workflow, phase, title, started, entry_category)
- The example shows `bug-fix` with `workflow: [DIAGNOSE, IMPLEMENT, VERIFY, SHIP]`
- Steps 8–9 (Escalation, Backlog Guard, Cross-Bucket Detection) from the original are still present

- [ ] **Step 4: Commit**

```bash
git add skills/find-skill/SKILL.md
git commit -m "feat: find-skill — three-category routing, v2 state write, operations work types"
```

---

## Task 2: Update master/SKILL.md

**Files:**
- Modify: `skills/master/SKILL.md`

The master skill currently references the "7-phase pipeline" and reads old `phase`/`work_type`/`track` fields. It needs to read `version_stage` and `active_work_item`, gain an operations bucket, and direct exit criteria lookups to `phase-gates.md` for all work types.

- [ ] **Step 1: Read the current file**

Read `skills/master/SKILL.md` to understand the full current content.

- [ ] **Step 2: Update the frontmatter description and opening line**

Find line 2 (frontmatter description):
```
description: SweetClaude master skill — phase router, interaction model, and session entry point. Manages the 7-phase pipeline, deference levels, conversation branch tracking, and creative partnership. Use at session start or when the user invokes SweetClaude directly.
```

Replace with:
```
description: SweetClaude master skill — phase router, interaction model, and session entry point. Manages the two-dimension lifecycle model (version_stage + active work item), deference levels, conversation branch tracking, and creative partnership. Use at session start or when the user invokes SweetClaude directly.
```

Find line 7 (opening line after the heading):
```
You are SweetClaude, a creative development partner. You manage a 7-phase pipeline, enforce discipline through hooks and process, and think with the user — not just for them.
```

Replace with:
```
You are SweetClaude, a creative development partner. You manage a two-dimension lifecycle model — `version_stage` (where the product is) and `active_work_item` (what's being worked on now) — enforce discipline through hooks and process, and think with the user — not just for them.
```

- [ ] **Step 3: Update Session Start — Step 1**

Find the Session Start section. Step 1 currently reads:
```markdown
1. **Read phase state.** Read `.sweetclaude/state/phase.yaml` to determine:
   - Current phase
   - Current work type
   - Track (code or strategy)
   - Deference level
   - Any pending detour to circle back to
```

Replace with:
```markdown
1. **Read phase state.** Read `.sweetclaude/state/phase.yaml` to determine:
   - `version_stage` — lifecycle stage (PROTOTYPE / ALPHA / BETA / GA / SCALED / MAINTAINED)
   - `active_work_item.type` — the work type (e.g. bug-fix, net-new-feature, hotfix)
   - `active_work_item.phase` — current step within the work item's workflow
   - `active_work_item.workflow` — ordered phase sequence for this work item
   - `deference_level`
   - Any pending detour to circle back to
```

- [ ] **Step 4: Update Domain Buckets section**

Find the Domain Buckets section. The current code block lists 5 buckets ending with `deploy/`. Replace the code block content with:

```
strategy/    — Why does this matter and to whom? Concept, pain, ICP, competitive, research, messaging.
product/     — What to build and why? Discovery, brief, PRD, stories, scope, backlog, release planning.
design/      — How is it structured? Architecture, tech spec, UX, data model, API, services, infra.
code/        — Writing and verifying code. TDD, issues, debt, testing, review, migration, hotfix, security patch.
operations/  — Keeping it running. Something broke, postmortem, break-glass notes, SLA review, security planning.
deploy/      — Shipping it. (Deferred — not yet scoped.)
```

Also update the work-type routing paragraph below the code block. Find:
```
*code/* — bug fixes, feature implementation, tech debt, TDD, testing, code review, PR preparation
```

Append after it:
```
*operations/* — something broke, postmortem, break-glass notes, SLA/error budget review, security planning, monitoring setup
```

- [ ] **Step 5: Update Phase Transitions — exit criteria reference**

In the Phase Transitions section, the DISCOVER and DEFINE exit checks are hardcoded. Add a general note before the Step 1 block. Find the line:

```
**Step 1: Pre-transition validation (Discover and Define only).**
```

Insert before it:
```markdown
**Exit criteria reference.** For any work type and phase, read exit criteria from `rules/phase-gates.md` — find the section matching `active_work_item.type`, then the subsection for the current `active_work_item.phase`. The DISCOVER and DEFINE checks below are the full criteria for net-new-feature; use them directly for that work type. For all others, read `phase-gates.md`.

```

- [ ] **Step 6: Update Skill Surfacing section**

Find the Skill Surfacing section. The line that says:
```
- **`strategy:`** — strategic positioning, competitive analysis, research, messaging
```
...through...
```
- **`deploy:`** — shipping (deferred)
```

Add after `- **`deploy:`** — shipping (deferred)`:
```
- **`operations:`** — operations skills (something-broke, postmortem, break-glass-notes, sla-error-budget-review, monitoring-alerting, onboarding-playbook)
```

Also find the line:
```
When the user asks to do something, the `find-skill` skill classifies it into the right bucket and surfaces relevant skills. Skills from other buckets are available on request.
```

Replace with:
```
When the user asks to do something, the `find-skill` skill classifies it into the right bucket and surfaces relevant skills. Skills from other buckets are available on request. Progressive disclosure: only surface work types appropriate for the current `version_stage` (see `config/workflow-templates.yaml` → `progressive_disclosure`).
```

- [ ] **Step 7: Verify the changes**

Read `skills/master/SKILL.md`. Confirm:
- Description and opening line no longer say "7-phase pipeline"
- Session Start Step 1 reads `version_stage` and `active_work_item.phase`
- Domain Buckets code block includes `operations/`
- "Exit criteria reference" paragraph appears before the DISCOVER pre-transition block
- Skill Surfacing mentions `operations:` and progressive disclosure
- All other sections (Pre-Flight Check, Session Start steps 2-5, Interaction Rules, State Directory) are unchanged

- [ ] **Step 8: Commit**

```bash
git add skills/master/SKILL.md
git commit -m "feat: master — two-dimension model, operations bucket, v2 state reading, phase-gates reference"
```

---

## Task 3: Update status/SKILL.md

**Files:**
- Modify: `skills/status/SKILL.md`

The status skill reads old `phase`/`work_type`/`active_bucket` fields and displays them flat. It needs to display both dimensions (version_stage + active_work_item) and show workflow progress.

- [ ] **Step 1: Read the current file**

Read `skills/status/SKILL.md` to understand the full current content.

- [ ] **Step 2: Update Step 1 — Read project state**

Find Step 1 which currently says:
```markdown
### Step 1: Read project state

Read `.sweetclaude/state/phase.yaml` from `.sweetclaude/`. Extract:
- Current phase
- Current work type
- Deference level
- Active bucket (strategy/product/design/code)
- Any pending detour
```

Replace with:
```markdown
### Step 1: Read project state

Read `.sweetclaude/state/phase.yaml` from `.sweetclaude/`. Extract:
- `version_stage` — lifecycle stage (PROTOTYPE / ALPHA / BETA / GA / SCALED / MAINTAINED). Default: PROTOTYPE if not set.
- `active_work_item.type` — work type (e.g. bug-fix, net-new-feature). May be `~` if no active work item.
- `active_work_item.phase` — current phase within this work item's workflow
- `active_work_item.workflow` — ordered list of phases for this work item (e.g. [DIAGNOSE, IMPLEMENT, VERIFY, SHIP])
- `active_work_item.title` — short description of the work
- `active_work_item.entry_category` — how work was initiated
- `deference_level`
- Any pending detour
```

- [ ] **Step 3: Update Step 3 — Present status display template**

Find Step 3 which contains the status display template:
```
SweetClaude Status — {project name}
═══════════════════════════════════

Phase:       {phase} ({bucket})
Work type:   {type}
Deference:   {level}
```

Replace the display template block with:
```
SweetClaude Status — {project name}
═══════════════════════════════════

Version stage:  {version_stage}
Work item:      {active_work_item.title} [{active_work_item.type}]
Phase:          {active_work_item.phase}  ({current step N of M in workflow})
Workflow:       {active_work_item.workflow[0]} → {active_work_item.workflow[1]} → ... → {active_work_item.workflow[-1]}
                (current: {active_work_item.phase highlighted})
Deference:      {deference_level}

Done:
  - {completed artifact or milestone}
  - {completed artifact or milestone}
  - ...

In progress:
  - {artifact or task currently open}
  - ...

Active milestones:
  - {MS-XXX Title        n/N criteria met}
  - {MS-XXX Title        n/N criteria met — ready to complete if all met}
  (omit this section if no milestones are active)

Next:
  → {the logical next step based on phase, open artifacts, and exit criteria}

Recent activity:
  {last 3-5 commits, one line each}
```

If `active_work_item` fields are all `~` (no active work item):
```
Version stage:  {version_stage}
Work item:      (none — run /sweetclaude:find-skill to start one)
Deference:      {deference_level}
```

- [ ] **Step 4: Verify the changes**

Read `skills/status/SKILL.md`. Confirm:
- Step 1 extracts `version_stage` and `active_work_item.*` fields
- Display template shows `Version stage:` and `Work item:` lines
- Workflow progress line is present (shows N of M and current phase)
- Idle state (no active_work_item) is handled with a prompt to run find-skill
- Steps 2 and 4 (read recent activity, suggest action) are unchanged

- [ ] **Step 5: Commit**

```bash
git add skills/status/SKILL.md
git commit -m "feat: status — two-dimension display, workflow progress, idle state handling"
```

---

## Task 4: Sync to installed location

**Files:**
- Sync: `~/.claude/skills/sweetclaude/find-skill/SKILL.md`
- Sync: `~/.claude/skills/sweetclaude/master/SKILL.md`
- Sync: `~/.claude/skills/sweetclaude/status/SKILL.md`

- [ ] **Step 1: Copy the 3 changed skill files**

```bash
cp /Users/carsonsweet/dev/sweetclaude/skills/find-skill/SKILL.md ~/.claude/skills/sweetclaude/find-skill/SKILL.md
cp /Users/carsonsweet/dev/sweetclaude/skills/master/SKILL.md ~/.claude/skills/sweetclaude/master/SKILL.md
cp /Users/carsonsweet/dev/sweetclaude/skills/status/SKILL.md ~/.claude/skills/sweetclaude/status/SKILL.md
```

- [ ] **Step 2: Verify diffs are clean**

```bash
diff /Users/carsonsweet/dev/sweetclaude/skills/find-skill/SKILL.md ~/.claude/skills/sweetclaude/find-skill/SKILL.md
diff /Users/carsonsweet/dev/sweetclaude/skills/master/SKILL.md ~/.claude/skills/sweetclaude/master/SKILL.md
diff /Users/carsonsweet/dev/sweetclaude/skills/status/SKILL.md ~/.claude/skills/sweetclaude/status/SKILL.md
```

Expected: no output for each (files identical).

- [ ] **Step 3: No git commit needed**

The `~/.claude/` directory is outside the repo. No commit required for this step.

---

## Self-Review Checklist

- [ ] `find-skill` — three entry categories present, v2 state write (7 fields), operations table present, version_stage filtering note present
- [ ] `master` — no "7-phase pipeline" references, reads `version_stage` + `active_work_item.*`, operations bucket in domain list, exit criteria reference to phase-gates.md present
- [ ] `status` — extracts v2 fields, displays both dimensions, shows workflow progress, handles idle state
- [ ] All installed files match repo (diffs clean)

---

## What Comes Next

**Plan 3 — New and renamed skills:** `hotfix`, `security-patch`, `external-integration`, `course-correction`, `postmortem`, `release-planning`, `break-glass-notes`, `something-broke`, `security-planning`. Skills referenced as "*(Plan 3)*" in find-skill's routing tables will resolve once this plan is complete.
