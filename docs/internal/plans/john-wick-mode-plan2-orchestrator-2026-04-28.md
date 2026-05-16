# John Wick Mode — Plan 2: Orchestrator

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write `skills/john-wick/SKILL.md` — the full pipeline orchestrator that drives all six phases from Bootstrap through Verify.

**Architecture:** Single dispatcher skill. Reads `john-wick.yaml` for state, calls existing skills for skill-backed steps, embeds new capabilities (cascade update, contract analysis, issue creation, test report, severity classifier) directly, manages interactive gates and context checkpoints.

**Tech Stack:** Markdown (SKILL.md authoring), Python 3 (verification tests), git.

**Repo:** `/Users/carsonsweet/dev/sweetclaude`
**Installed:** `/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0`
**Spec:** `/Users/carsonsweet/dev/sweetclaude/docs/john-wick-mode-spec-v1-2026-04-28.md`
**Plan 1 must be complete before starting this plan.**

---

## Pre-flight

```bash
# Confirm on right branch
git -C /Users/carsonsweet/dev/sweetclaude branch --show-current
# Expected: john-wick-mode

# Confirm Plan 1 building blocks are present
ls /Users/carsonsweet/dev/sweetclaude/skills/john-wick-checkin/SKILL.md
grep -l 'Compliance Context' /Users/carsonsweet/dev/sweetclaude/skills/product-discovery/SKILL.md
grep -l 'Autonomous Mode' /Users/carsonsweet/dev/sweetclaude/skills/product-prd/SKILL.md
grep -l 'compliance-context.yaml' /Users/carsonsweet/dev/sweetclaude/skills/code-review/SKILL.md
grep -l 'john-wick.yaml' /Users/carsonsweet/dev/sweetclaude/hooks/test-guardian.sh
# Expected: all five lines return paths (no errors)

# Confirm skills/ dir exists
ls /Users/carsonsweet/dev/sweetclaude/skills/ | grep -c .
# Expected: number > 0
```

---

## Task 1: Orchestrator skeleton — entry, resume, prerequisites gate

**Files:**
- Create: `skills/john-wick/SKILL.md`

Write the structural skeleton: frontmatter, entry/resume logic, prerequisites gate (all 8 checks), state file schema, interactive gate format definition, and context checkpoint protocol. No phase content yet.

- [ ] **Step 1: Write verification test**

```python
# /tmp/test_jwplan2_task1.py
import os, re

skill_path = '/Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md'
assert os.path.exists(skill_path), "FAIL: Skill file does not exist"

with open(skill_path) as f:
    content = f.read()

# Frontmatter
assert 'name: sweetclaude:john-wick' in content, "FAIL: Missing skill name"

# Resume protocol — all 5 states
for state in ['waiting_for_user', 'paused', 'active', 'complete', 'error']:
    assert state in content, f"FAIL: Missing resume state: {state}"

# Prerequisites gate — all 8 checks
for check in [
    'phase.yaml',
    'personas',
    'task analysis',
    'constraints',
    'dangerously',
    'gh auth status',
    'error state',
    'compliance-context.yaml',
]:
    assert check.lower() in content.lower(), f"FAIL: Missing prerequisite check: {check}"

# Interactive gate format
assert 'JOHN WICK —' in content, "FAIL: Missing interactive gate header format"
assert 'waiting_for_user' in content, "FAIL: Missing waiting_for_user state set in gate"

# Context checkpoint
assert 'context_checkpoint' in content, "FAIL: Missing context checkpoint"
assert '20%' in content or 'context limit' in content.lower(), "FAIL: Missing context limit check"

# john-wick.yaml state fields
for field in ['feature_name', 'feature_branch', 'current_step', 'locked_test_files', 'issue_list']:
    assert field in content, f"FAIL: Missing state field: {field}"

print("PASS")
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python3 /tmp/test_jwplan2_task1.py
# Expected: AssertionError on "Skill file does not exist"
```

- [ ] **Step 3: Create skill directory and write skeleton**

```bash
mkdir -p /Users/carsonsweet/dev/sweetclaude/skills/john-wick
```

Write `/Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md` with this exact content:

```markdown
---
name: sweetclaude:john-wick
description: Fully autonomous, resumable, multi-session SDLC pipeline. Given completed discovery artifacts, runs product-definition → design → TDD → implementation → review → PR with minimal human involvement. Interactive gates are explicit, pre-defined, and rare.
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# John Wick Mode

Fully autonomous, resumable SDLC pipeline. Runs from discovery artifacts to merged PR with minimal human involvement. Interactive gates are pre-defined and infrequent.

---

## Entry and Resume

On invocation, read `.sweetclaude/state/john-wick.yaml`.

**If the file does not exist:** Run the Prerequisites Gate, then start at B1.

**If `status: waiting_for_user`:** Present the pending interactive gate from `interactive_gate_pending`. Collect user input. Update `status: active`. Continue from `current_step`.

**If `status: paused` or `status: active`:** Emit one line: "Last completed: {last step in sessions[].steps_completed}. Resuming from {current_step}." Continue from `current_step`.

**If `status: complete`:** Tell the user the pipeline is done. Point to the PR URL stored in `created_artifacts` where type=pr.

**If `status: error`:** Show the recorded error. Do not auto-resume. Tell the user: "Inspect `.sweetclaude/state/john-wick.yaml` and clear the error state before restarting."

**State write discipline:** After every step completes, update `john-wick.yaml` — set `current_step` to the next step — before beginning that next step. State always reflects what comes next, never what just finished. This ensures a resume after interruption skips nothing and repeats nothing.

---

## Prerequisites Gate

Run on first invocation (no `john-wick.yaml`). Validate all of the following. On any failure, halt with the specified error message and do not create `john-wick.yaml`.

| # | Check | How | Error if missing |
|---|---|---|---|
| 1 | SweetClaude initialized | `.sweetclaude/state/phase.yaml` exists | "Run `/sweetclaude:init` first." |
| 2 | Personas artifact | `.sweetclaude/` or `docs/` contains a file with "persona" in the name | "Complete product discovery first: `/sweetclaude:product-discovery`" |
| 3 | Task analysis with success + failure criteria | A task analysis artifact exists with "success" and "failure" in its content | "Task analysis incomplete. Rerun `/sweetclaude:product-discovery`." |
| 4 | Constraints analysis | A constraints artifact exists in `.sweetclaude/` or `docs/` | "Constraints analysis missing." |
| 5 | Explicit acknowledgment | Present the warning below and require the user to type "I understand" exactly | "John Wick mode requires explicit acknowledgment." |
| 6 | GitHub mode (conditional) | If user selects GitHub mode at B1: `gh auth status` must exit 0 | "GitHub CLI not authenticated. John Wick can help you fix this now." |
| 7 | No active run in error state | If `john-wick.yaml` exists: `status` must be `complete` or `paused` | "Previous run is in error state. Inspect `.sweetclaude/state/john-wick.yaml` before restarting." |
| 8 | Compliance context | `.sweetclaude/state/compliance-context.yaml` exists | Note: not a hard block — collect at B4 if absent. Log: "Compliance context missing — will collect at B4." |

**Acknowledgment warning (prerequisite 5):**

```
⚠ JOHN WICK MODE

This pipeline runs autonomously through the full SDLC — PRD, design,
TDD, implementation, and PR — with minimal human interaction. It will
create branches, write files, run tests, and open a pull request.

Interactive gates are at: B1, B2, B4 (if needed), D4, DS6, V5, and
conditional IM2. Outside these gates, John Wick does not ask permission.

Type "I understand" to proceed.
```

If the user types anything other than "I understand" (case-insensitive): halt.

**After prerequisites pass:** Initialize `john-wick.yaml` with `status: active`, `current_step: B1`, and the discovery artifact paths found during checks.

---

## State File Schema

Maintain `.sweetclaude/state/john-wick.yaml` throughout the pipeline:

```yaml
schema_version: 1
status: active | paused | waiting_for_user | complete | error
feature_name: string
feature_branch: string
github_mode: boolean
phase_checkins: boolean

current_phase: BOOTSTRAP | DEFINE | PLAN | DESIGN | IMPLEMENT_PREP | IMPLEMENT | VERIFY
current_step: string

discovery_artifacts:
  personas: string | null
  task_analysis: string | null
  constraints: string | null
compliance_context: string | null

created_artifacts:
  - step: string
    type: prd | stories | gherkin | architecture | tech_spec | contract_analysis | tests | report | pr
    path: string
    version: integer

issue_list:
  - number: integer
    title: string
    branch: string
    status: pending | in_progress | complete | escalated | skipped

caucus_outputs:
  - step: string
    path: string

checkin_outputs:
  - step: string
    path: string
    findings: none | minor | significant
    escalated: boolean

interactive_gate_pending:
  step: string | null
  description: string | null

locked_test_files:
  - string

context_checkpoint:
  step: string
  timestamp: string
  notes: string

sessions:
  - started: string
    ended: string | null
    steps_completed: [string]
```

---

## Interactive Gate Format

When an I-type step is reached:

1. Complete any autonomous work that precedes the gate.
2. Update `john-wick.yaml`: set `status: waiting_for_user`, populate `interactive_gate_pending.step` and `interactive_gate_pending.description`.
3. Commit any new artifacts produced: `chore(john-wick): artifacts at [step] — awaiting gate`.
4. Present the gate:

```
JOHN WICK — [Phase Name] Gate
══════════════════════════════
[What was done since the last gate — 2-4 bullets]

[Content requiring review — in sections if long]

[Specific question(s) requiring user decision]

Approve, edit, or respond. John Wick will continue once confirmed.
```

5. Wait. Do not continue until the user responds.
6. On response: record the decision, update artifacts, set `status: active`, continue.

---

## Context Checkpoint Protocol

Before each autonomous step, estimate remaining context budget. If within approximately 20% of the context limit:

1. Commit current state: `chore(john-wick): checkpoint at [step]`
2. Update `context_checkpoint` in `john-wick.yaml` with current step and timestamp.
3. Emit: "Context limit approaching. State saved at [step]. Run `/sweetclaude:john-wick` to resume."
4. Stop. Do not attempt to begin the next step.

A clean stop is always better than a corrupted step.

---
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
python3 /tmp/test_jwplan2_task1.py
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/carsonsweet/dev/sweetclaude add skills/john-wick/SKILL.md
git -C /Users/carsonsweet/dev/sweetclaude commit -m "feat(john-wick): orchestrator skeleton — entry, resume, prerequisites, gate format"
```

---

## Task 2: Phase 0 (Bootstrap) + Phase 1 (Define)

**Files:**
- Modify: `skills/john-wick/SKILL.md` (append content)

Append the Bootstrap and Define phase step handlers.

- [ ] **Step 1: Write verification test**

```python
# /tmp/test_jwplan2_task2.py
with open('/Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md') as f:
    content = f.read()

# Bootstrap steps
for step in ['B1', 'B2', 'B3', 'B4']:
    assert f'### {step}' in content or f'**{step}**' in content or f'\n{step} ' in content or f'| {step} |' in content, \
        f"FAIL: Missing Bootstrap step {step}"

# B1 — GitHub mode question
assert 'github' in content.lower() and ('local' in content.lower() or 'tracking' in content.lower()), \
    "FAIL: B1 missing GitHub vs local tracking question"

# B3 — feature branch creation
assert 'chore: initialize john-wick pipeline' in content, \
    "FAIL: B3 missing initialization commit message"

# B4 — compliance context collection
assert 'B4' in content and 'compliance' in content.lower(), \
    "FAIL: B4 missing compliance context collection"

# Define steps
for step in ['D1', 'D2', 'D3', 'D4', 'CK1']:
    assert step in content, f"FAIL: Missing Define step {step}"

# D1 — autonomous PRD
assert '--autonomous' in content or 'autonomous' in content.lower(), \
    "FAIL: D1 missing autonomous PRD generation"

# D2 — product-design-review caucus preset inline
assert 'product-design-review' in content or 'PM' in content, \
    "FAIL: D2 missing product-design-review caucus persona preset"

# D4 — section-by-section review
assert 'section' in content.lower() and 'D4' in content, \
    "FAIL: D4 missing section-by-section review"

# CK1 — conditional check-in
assert 'CK1' in content and 'phase_checkins' in content, \
    "FAIL: CK1 missing phase_checkins gate"

print("PASS")
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python3 /tmp/test_jwplan2_task2.py
# Expected: AssertionError (steps not yet present)
```

- [ ] **Step 3: Append Phase 0 and Phase 1 content**

Append to `/Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md`:

```markdown
## Phase 0: Bootstrap

### B1 — Tracking mode (Interactive)

Ask:
> "Should John Wick track issues in GitHub or locally?
> - **GitHub** — creates real GitHub issues, requires `gh` auth
> - **Local** — creates a local issue list in `.sweetclaude/state/issue-list.md`"

If GitHub selected: run `gh auth status`. If it exits non-zero, offer:
> "GitHub CLI is not authenticated. Want me to walk you through `gh auth login` now?"
Help the user authenticate before continuing. Do not advance until `gh auth status` succeeds.

Record `github_mode: true/false` in `john-wick.yaml`.

Ask: "Should phase check-ins be enabled? Recommended if the PRD will have more than 4 epics or if you expect more than 2 external service dependencies. Check-ins add lightweight drift detection at each phase transition."

Record `phase_checkins: true/false`.

Update `current_step: B2`.

### B2 — Feature branch name (Interactive)

Ask:
> "What should the feature branch be named? (e.g. `payment-retry-logic`, `user-profile-v2`)"

Validate: lowercase, hyphens only, no spaces. If invalid format, ask again.

Record `feature_name` and `feature_branch` in `john-wick.yaml`. Update `current_step: B3`.

### B3 — Initialize branch (Autonomous)

```bash
git checkout -b {feature_branch}
```

Copy all discovery artifacts found during prerequisites into `docs/` on the branch. Commit:
```
chore: initialize john-wick pipeline for {feature_name}
```

Update `john-wick.yaml`: record discovery artifact paths in `discovery_artifacts`. Update `current_step: B4`.

### B4 — Compliance context (Interactive, conditional)

If `.sweetclaude/state/compliance-context.yaml` already exists: skip. Log "Compliance context already present — skipping B4." Update `current_step: D1`.

If it does not exist: invoke `sweetclaude:product-discovery` compliance context interview (the three-question section from that skill: data categories, user geography, user type). The skill writes `.sweetclaude/state/compliance-context.yaml`. After it completes, record the path in `john-wick.yaml compliance_context`. Update `current_step: D1`.

---

## Phase 1: Define

### D1 — Generate PRD (Autonomous)

Invoke `sweetclaude:product-prd` with `--autonomous` flag. The skill reads discovery artifacts and compliance context, generates a complete PRD draft without user interaction, and flags thin sections.

The PRD is written to `docs/[feature-name]-prd-draft-v1.0-[YYYYMMDD].md`.

Record in `created_artifacts`: `{step: D1, type: prd, path: ..., version: 1}`.

**Scope check:** After the PRD is generated, count the epics. If more than 6 epics: surface a warning:
> "⚠ Scope warning: This PRD has {N} epics. John Wick recommends decomposing into smaller services before continuing. Large scope compounds errors in an autonomous pipeline."

If more than 8 epics: halt and require explicit user override:
> "⚠ Hard limit: {N} epics exceeds the maximum for autonomous execution (8). Decompose the PRD into smaller services, or type 'override scope limit' to proceed at your own risk."

Update `current_step: D2`.

### D2 — PRD caucus (Autonomous)

Run a 3-turn product design review caucus on the PRD. The caucus uses these four personas (pass inline to the caucus skill — do not rely on a preset file):

**Personas for product-design-review:**
- **PM — "the pragmatist"**: 10 years B2B SaaS, former engineer. Scope creep detector; believes features die from complexity, not ambition. Challenges every "nice to have."
- **UX researcher**: Mixed methods, 8 years. Advocates for the user who isn't in the room; skeptical of assumption-based personas. Probes for real user evidence.
- **Domain expert**: Deep subject matter knowledge in the service's domain. Flags technical accuracy issues; biased toward correctness over shipping speed.
- **Devil's advocate — "the skeptic"**: Strategy/venture background. Questions whether the problem is real; argues for doing less. Challenges scope, not execution.

Invoke the caucus skill with: PRD path, personas above, 3 turns, question: "Does this PRD define a product that solves the stated problem for the stated user, with scope that is achievable and justified?"

Write caucus output to `.sweetclaude/caucus/prd-review-[YYYYMMDD].md`.
Record in `caucus_outputs`: `{step: D2, path: ...}`.
Update `current_step: D3`.

### D3 — Apply uncontested findings (Autonomous)

Read the D2 caucus output. Classify each finding:

- **Uncontested**: all four personas agree, or three agree and one is silent
- **Contested**: personas disagree, or the finding requires a product decision the orchestrator cannot make

Apply uncontested findings directly to the PRD — targeted edits, not a rewrite. Prepare a structured change summary:
```
Applied (uncontested):
- [finding] → [change made]

Pending user decision (contested):
- [finding] — [what the personas disagreed on]
- [flagged section from D1] — [what information was missing]
```

Update `current_step: D4`.

### D4 — PRD approval (Interactive)

Present the PRD section by section. For each section:
1. Show the section content
2. Show any contested caucus findings for that section
3. Show any D1 flags (⚠ markers) for that section
4. Wait for: approval ("ok", "looks good", or similar), or edits

Do not advance to the next section until the current section is confirmed. After all sections are approved, apply any user edits and commit:
```
docs: approved PRD for {feature_name} at D4
```

Update `created_artifacts` version to final. Update `current_step: CK1`.

### CK1 — Define phase check-in (Conditional)

If `phase_checkins: false`: skip. Update `current_step: P1`.

If `phase_checkins: true`: invoke `sweetclaude:john-wick-checkin` with:
- `phase=DEFINE`
- `question=Does the approved PRD have sufficient coverage to generate user stories? Are any epics or acceptance criteria underspecified to the point where story writing would require guessing?`
- `discovery_artifacts={paths from discovery_artifacts in john-wick.yaml}`
- `phase_artifacts={PRD path}`
- `post_lock=false`

Record output in `checkin_outputs`.

If result is `significant`: return to D4 gate with the finding. Present to user:
> "CK1 found a gap: [finding]. Returning to PRD review."

If result is `none` or `minor`: log and continue. Update `current_step: P1`.

---
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
python3 /tmp/test_jwplan2_task2.py
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/carsonsweet/dev/sweetclaude add skills/john-wick/SKILL.md
git -C /Users/carsonsweet/dev/sweetclaude commit -m "feat(john-wick): add Phase 0 Bootstrap and Phase 1 Define steps"
```

---

## Task 3: Phase 2 (Plan) + Phase 3 (Design) + embedded capabilities

**Files:**
- Modify: `skills/john-wick/SKILL.md` (append content)

Append Plan and Design phases, inline caucus persona presets for story-review and architecture-impact, cascade document update protocol, and service contract analysis.

- [ ] **Step 1: Write verification test**

```python
# /tmp/test_jwplan2_task3.py
with open('/Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md') as f:
    content = f.read()

# Plan steps
for step in ['P1', 'P2', 'P3', 'P4', 'CK2']:
    assert step in content, f"FAIL: Missing Plan step {step}"

# P4 — Gherkin generation
assert 'gherkin' in content.lower() or '.feature' in content, \
    "FAIL: P4 missing Gherkin generation"

# Story-review caucus personas
assert 'story-review' in content or 'product owner' in content.lower(), \
    "FAIL: Missing story-review caucus personas"

# Design steps
for step in ['DS1', 'DS2', 'DS3', 'DS4', 'DS5', 'DS6', 'DS7', 'CK3']:
    assert step in content, f"FAIL: Missing Design step {step}"

# CK3 — mandatory
assert 'CK3' in content and ('mandatory' in content.lower() or 'always runs' in content.lower()), \
    "FAIL: CK3 missing mandatory flag"

# Architecture-impact caucus personas
assert 'architecture-impact' in content or 'senior architect' in content.lower(), \
    "FAIL: Missing architecture-impact caucus personas"

# Cascade document update
assert 'cascade' in content.lower(), "FAIL: Missing cascade document update"
assert 'DS6' in content and 'DS7' in content, "FAIL: Missing DS6/DS7 cascade apply step"

# Service contract analysis — 5 sections
for section in ['outbound', 'inbound', 'implicit', 'compliance obligation', 'risk surface']:
    assert section.lower() in content.lower(), f"FAIL: Missing contract analysis section: {section}"

# contract-analysis output file
assert 'contract-analysis' in content, "FAIL: Missing contract analysis output filename"

print("PASS")
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python3 /tmp/test_jwplan2_task3.py
# Expected: AssertionError (steps not yet present)
```

- [ ] **Step 3: Append Phase 2, Phase 3, and embedded capabilities**

Append to `/Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md`:

```markdown
## Phase 2: Plan

### P1 — Generate user stories (Autonomous)

Invoke `sweetclaude:product-user-stories` with the approved PRD as input. Generate human-readable stories with acceptance criteria. Write to `.sweetclaude/stories/[feature-name]-stories-v1.md`.

Record in `created_artifacts`: `{step: P1, type: stories, path: ..., version: 1}`.
Update `current_step: P2`.

### P2 — Story review caucus (Autonomous)

Run a 2-turn story review caucus with these four personas (pass inline):

**Personas for story-review:**
- **Product owner**: Acceptance criteria writer for 200+ stories. Flags unmeasurable criteria immediately; biased toward specificity. Rewrites vague criteria as concrete pass/fail tests.
- **Senior engineer**: Full-stack, 12 years. Translates story intent into implementation risk; flags stories that assume impossible interfaces or underspecified data shapes.
- **QA lead**: Test design and exploratory testing. Reads acceptance criteria as test cases; finds the ambiguous cases that will cause test failures.
- **Accessibility reviewer**: WCAG, inclusive design. Ensures stories include accessibility requirements as first-class criteria, not afterthoughts.

Invoke caucus with: stories path, personas above, 2 turns, question: "Are these stories specific enough to write deterministic acceptance tests? Are any acceptance criteria ambiguous, unmeasurable, or missing?"

Write caucus output to `.sweetclaude/caucus/story-review-[YYYYMMDD].md`.
Record in `caucus_outputs`. Update `current_step: P3`.

### P3 — Apply uncontested story adjustments (Autonomous)

Classify caucus findings (same uncontested/contested logic as D3). Apply uncontested adjustments to the stories document. Update `current_step: P4`.

### P4 — Generate Gherkin (Autonomous)

For each story in the stories document, invoke `sweetclaude:product-user-tdd-tests` to generate Gherkin `.feature` files. Write to `.sweetclaude/features/[story-slug].feature`. Commit:
```
test: Gherkin specs for {feature_name} stories
```

Record in `created_artifacts`: `{step: P4, type: gherkin, path: .sweetclaude/features/, version: 1}`.
Update `current_step: CK2`.

### CK2 — Plan phase check-in (Conditional)

If `phase_checkins: false`: skip. Update `current_step: DS1`.

If `phase_checkins: true`: invoke `sweetclaude:john-wick-checkin` with:
- `phase=PLAN`
- `question=Is the Gherkin internally consistent and does it cover all PRD success criteria? Are there stories with no Gherkin coverage?`
- `discovery_artifacts={paths from john-wick.yaml}`
- `phase_artifacts={stories path, .feature files}`
- `post_lock=false`

Record output. If significant: revise Gherkin before advancing (return to P4). Update `current_step: DS1`.

---

## Phase 3: Design

### DS1 — Architecture document (Autonomous)

Invoke `sweetclaude:design-architecture` with: PRD path, stories path, compliance context path. The compliance context informs: data residency requirements, encryption at rest/in transit, and audit logging requirements.

Write architecture document to `docs/architecture-[feature-name]-v1-[YYYYMMDD].md`.
Record in `created_artifacts`. Update `current_step: DS2`.

### DS2 — Tech spec (Autonomous)

Invoke `sweetclaude:design-tech-spec` with: architecture document, PRD, stories. Write tech spec to `docs/tech-spec-[feature-name]-v1-[YYYYMMDD].md`.
Record in `created_artifacts`. Update `current_step: DS3`.

### DS3 — Service contract analysis (Autonomous)

Run the embedded service contract analysis. Read: architecture document, tech spec, compliance context. Scan `docs/` and any available READMEs for specs of services this service depends on.

Produce `docs/contract-analysis-[feature-name]-v1-[YYYYMMDD].md` with these five sections:

**1. Outbound contracts** — What this service promises to consumers: API endpoints, event schemas, response shapes, implied SLAs.

**2. Inbound contracts** — What this service requires from providers: APIs it calls, data it expects, timing assumptions.

**3. Implicit contracts** — What this service assumes about the environment that isn't explicitly documented: ordering guarantees, idempotency assumptions, data consistency expectations.

**4. Compliance obligations** — What compliance requirements flow through to consumers. Derived from `compliance-context.yaml derived_frameworks`:
- `gdpr`: downstream consumers must handle PII under GDPR data processing agreements
- `hipaa`: PHI must not be stored by downstream consumers without BAAs
- `pci_dss`: cardholder data must not be cached downstream
- `coppa`/`gdpr_floor`: data minimization requirements apply to consumers

**5. Risk surface** — Where contracts are fragile: under-specified boundaries, assumed but unverified behavior, dependencies whose specs are absent or marked in-progress.

End with a risk table:
```markdown
| Contract | Type | Spec Available? | Risk |
|---|---|---|---|
| {name} | outbound/inbound | yes/no | low/medium/high |
```

If any dependency's spec is absent or marked in-progress, flag explicitly:
> "⚠ Dependency spec unavailable: [{service}]. Contract analysis for this dependency is based on assumptions. Verify before IP5."

Record in `created_artifacts`. Update `current_step: DS4`.

**Scope check:** Count external service dependencies identified. If more than 4: surface a warning. If more than 6: halt with same override mechanism as D1 epic limit.

### DS4 — Architecture and impact caucus (Autonomous)

Run a 3-turn architecture review caucus with these four personas (pass inline):

**Personas for architecture-impact:**
- **Senior architect**: Distributed systems, 15 years. Strong opinions on interface contracts; biased toward over-specifying rather than under-specifying boundaries. Challenges every "we'll figure it out" in the design.
- **Security engineer**: AppSec, threat modeling. Reads every design for attack surface; sees trust boundaries others miss. Flags auth gaps, injection surfaces, and data leakage paths.
- **SRE**: Reliability, observability. Asks "what does this look like at 3am when it's broken?" for every component. Flags missing metrics, missing circuit breakers, missing runbooks.
- **Upstream service owner**: Persona representing whoever owns the service this one depends on most. Questions every assumption about upstream behavior; knows all the undocumented behaviors and breaking changes.

Invoke caucus with: architecture doc, tech spec, contract analysis, compliance context, 3 turns, question: "Does this architecture correctly handle the service's compliance obligations, service contracts, and failure modes? What will break first in production?"

Write output to `.sweetclaude/caucus/architecture-review-[YYYYMMDD].md`.
Record in `caucus_outputs`. Update `current_step: DS5`.

### DS5 — Classify design findings (Autonomous)

Classify caucus findings as uncontested or contested (same logic as D3/P3). Prepare a change summary:
```
Will apply automatically (uncontested):
- [finding] → [proposed change]

Requires your decision (contested):
- [finding] — [what the change would be and what it affects downstream]
```

Update `current_step: DS6`.

### DS6 — Design change approval (Interactive)

Present the change summary. For each contested item:
- Show the finding
- Show the proposed change
- Show what downstream artifacts would be affected (PRD, stories, Gherkin)
- Wait for: approve, reject, or modify

Record all decisions. Apply approved changes immediately. Update `current_step: DS7`.

### DS7 — Cascade document update (Autonomous)

Apply all approved changes from DS6. For each downstream artifact in the chain — architecture → tech spec → contract analysis → PRD (if impacted) → stories (if impacted) → Gherkin (if impacted) — determine whether any approved change touches that artifact.

**Cascade protocol:**
1. For each artifact in the chain, determine if the approved change affects its content.
2. If yes: generate a targeted diff (specific section changes, not a full rewrite). Show what will change.
3. If a proposed diff would invalidate a previously approved artifact (e.g., an API shape change invalidates a story's acceptance criteria), flag it explicitly before applying.
4. Collect all diffs and apply in sequence. Commit:
```
docs: cascade approved design changes to {list of affected artifacts}
```

**Hard stop:** The cascade never touches test files. If an approved change would require test changes, flag it and note: "Test file changes require returning to IP1 after IP5 executes."

Update all affected `created_artifacts` entries (increment version). Update `current_step: CK3`.

### CK3 — Pre-lock check-in (MANDATORY — always runs)

This check-in always runs regardless of `phase_checkins` setting. It is the last point at which design artifacts can be adjusted without unlocking tests.

Invoke `sweetclaude:john-wick-checkin` with:
- `phase=DESIGN`
- `question=Does the approved design (architecture, tech spec, contract analysis) still match the PRD and stories? Has the cascade update introduced any inconsistencies? Are there open design questions that will surface as implementation surprises?`
- `discovery_artifacts={paths from john-wick.yaml}`
- `phase_artifacts={architecture path, tech spec path, contract analysis path, PRD path, stories path}`
- `post_lock=false`

Record output.

If result is `significant`: return to DS6 gate. Present to user:
> "CK3 (pre-lock check) found a gap: [finding]. Returning to design review before tests are written."

Do **not** advance to IP1 until CK3 passes with `none` or `minor`.

If `none` or `minor`: log and continue. Update `current_step: IP1`.

---
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
python3 /tmp/test_jwplan2_task3.py
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/carsonsweet/dev/sweetclaude add skills/john-wick/SKILL.md
git -C /Users/carsonsweet/dev/sweetclaude commit -m "feat(john-wick): add Phase 2 Plan and Phase 3 Design with embedded capabilities"
```

---

## Task 4: Phase 4 (Implement Prep) + Phase 5 (Implement)

**Files:**
- Modify: `skills/john-wick/SKILL.md` (append content)

Append Implement Prep and Implement phases including test locking, issue iteration loop, GitHub Issues creation, MD test report generation, and severity classifier.

- [ ] **Step 1: Write verification test**

```python
# /tmp/test_jwplan2_task4.py
with open('/Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md') as f:
    content = f.read()

# Implement Prep steps
for step in ['IP1', 'IP2', 'IP3', 'IP4', 'IP5', 'IP6']:
    assert step in content, f"FAIL: Missing Implement Prep step {step}"

# IP5 — test lock
assert 'IP5' in content and 'lock' in content.lower(), "FAIL: IP5 missing test lock"
assert 'locked_test_files' in content, "FAIL: IP5 missing locked_test_files write"

# IP3 — RED validation
assert 'RED' in content, "FAIL: IP3 missing RED validation"

# IP6 — conditional GitHub vs local
assert 'IP6' in content and ('github' in content.lower()), "FAIL: IP6 missing GitHub conditional"
assert 'issue-list.md' in content, "FAIL: IP6-local missing local issue list"

# Implement steps
for step in ['IM1', 'IM2']:
    assert step in content, f"FAIL: Missing Implement step {step}"

# Issue iteration loop
assert 'for each issue' in content.lower() or 'issue iteration' in content.lower(), \
    "FAIL: Missing issue iteration loop"

# Issue branch naming
assert '{issue-number}' in content or 'issue-number' in content, \
    "FAIL: Missing issue branch naming pattern"

# Severity classifier
assert '30%' in content, "FAIL: Missing 30% threshold in severity classifier"
assert 'happy path' in content.lower(), "FAIL: Missing happy path escalation in severity classifier"
assert 'compile' in content.lower() or 'import error' in content.lower(), \
    "FAIL: Missing compile error escalation in severity classifier"

# Test report
assert 'test-report' in content, "FAIL: Missing test report filename pattern"
assert 'Pass:' in content or '## Failures' in content, "FAIL: Missing test report format"

print("PASS")
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python3 /tmp/test_jwplan2_task4.py
# Expected: AssertionError
```

- [ ] **Step 3: Append Phase 4 and Phase 5 content**

Append to `/Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md`:

```markdown
## Phase 4: Implement Prep

### IP1 — Spawn test writer (Autonomous)

Spawn a test writer subagent (TDD Level 3). Subagent receives: all `.feature` files from `.sweetclaude/features/`, existing codebase for patterns. The subagent has no implementation knowledge.

The subagent writes test files and commits them. Record all test file paths in `john-wick.yaml created_artifacts` with type=tests. Update `current_step: IP2`.

### IP2 — QA caucus on test coverage (Autonomous)

Spawn three QA caucus subagents in parallel:
- `sweetclaude:qa-caucus-service`
- `sweetclaude:qa-caucus-component`
- `sweetclaude:qa-caucus-integration`

Input for each: test files, Gherkin specs, stories, PRD.

Consolidate gaps from all three outputs. Apply uncontested gaps to test files (these are still pre-lock; edits are permitted). Update `current_step: IP3`.

### IP3 — RED validation (Autonomous)

Run the full test suite. All tests must fail (RED). If any tests pass unexpectedly:
1. Investigate: is the test trivially true? Is there existing code satisfying it?
2. Correct the test or the test setup until all tests fail for the right reasons.
3. Do not advance until every test is RED.

Update `current_step: IP4`.

### IP4 — Post-RED QA pass (Autonomous)

Run a single-turn focused QA review: "Did anything slip through the RED validation? Are there any test cases that are trivially satisfiable or that don't actually test the stated behavior?"

Apply any final adjustments to test files. Commit:
```
test: RED — {feature_name} failing tests committed
```

Update `current_step: IP5`.

### IP5 — Test lock (Autonomous)

Collect all test file paths from `created_artifacts` where type=tests. Write them to `locked_test_files` in `john-wick.yaml`.

The `test-guardian` hook now enforces these locks across all subsequent file writes — any attempt to modify a locked test file will be blocked.

Emit: "Test files locked. From this point, test modifications require explicit user unlock and return to IP1."

Commit: `chore(john-wick): IP5 test lock — {N} files locked`

Update `current_step: IP6`.

### IP6 — Create issues (Conditional)

**If `github_mode: true`:**

For each story in the stories document, create a GitHub issue:
```bash
gh issue create \
  --title "{story title}" \
  --body "{acceptance criteria in markdown}" \
  --label "john-wick" \
  --label "{feature_name}"
```

On failure (rate limit, auth error): wait 5 seconds and retry once. If retry fails, log the error and continue — do not halt the pipeline for issue creation failures.

Record each issue number in `john-wick.yaml issue_list`. Update `current_step: IM1`.

**If `github_mode: false`:**

Write `.sweetclaude/state/issue-list.md`:
```markdown
# Issue List — {feature_name}

| # | Title | Status |
|---|---|---|
| 1 | {story title} | pending |
| 2 | {story title} | pending |
...
```

Record in `john-wick.yaml issue_list` with sequential numbers. Update `current_step: IM1`.

---

## Phase 5: Implement

### IM1 — Issue iteration loop (Autonomous)

Execute the following loop until all issues are complete or an IM2 escalation fires:

```
For each issue in issue_list where status = pending:

  1. Update issue status to in_progress in john-wick.yaml.

  2. Create branch:
     git checkout -b {issue-number}-{slugified-title}

  3. Invoke sweetclaude:code-issue with issue context:
     - Issue title and acceptance criteria
     - Architecture doc and tech spec
     - Locked test files (read-only — cannot be modified)
     - Compliance context

  4. Run the full test suite. Generate a test report (see Test Report Format below).
     Append to aggregate report at .sweetclaude/reports/test-report-{feature_name}.md.

  5. Evaluate failure severity (see Severity Classifier below).
     - If significant: pause loop, update issue status to escalated,
       set john-wick.yaml status=waiting_for_user, advance to IM2 gate.
     - If not significant: attempt bug fixes (up to 3 iterations).
       Re-run tests after each fix. Re-evaluate severity.
       If still failing after 3 iterations: escalate to IM2.

  6. If phase_checkins=true: invoke sweetclaude:john-wick-checkin with:
     - phase=IMPLEMENT
     - question=Is this implementation drifting from the approved design? Does the code match the architecture and tech spec?
     - discovery_artifacts={paths from john-wick.yaml}
     - phase_artifacts={architecture path, tech spec path, current issue branch diff}
     - post_lock=true
     If significant: escalate to IM2 (cannot modify locked tests).

  7. If all tests green: merge branch to feature branch.
     git checkout {feature_branch} && git merge {issue-branch} --no-ff
     Commit message: "feat({feature_name}): close issue #{number} — {title}"
     Update issue status to complete in john-wick.yaml.

  8. Advance to next issue.
```

When all issues are complete: update `current_phase: VERIFY`, `current_step: V1`.

### IM2 — Escalation gate (Interactive, conditional)

Fires when severity classifier returns significant, or when a post-IP5 check-in finds significant drift.

Present:
```
JOHN WICK — Implementation Escalation
══════════════════════════════════════
Issue: #{number} — {title}

Problem:
{finding or severity classifier output}

Options:
1. Fix and continue — describe what you want changed; John Wick will apply it and resume
2. Skip this issue — mark as skipped, continue to next issue
3. Abort — stop the pipeline here; state is saved

Your decision:
```

On user decision:
- **Fix and continue**: apply the user's described fix, re-run tests, re-enter the issue loop.
- **Skip**: update issue status to skipped, continue loop.
- **Abort**: set `john-wick.yaml status: paused`. Stop.

---

## Test Report Format

After each test run (IP3, IP4, and each IM1 iteration), generate:

```markdown
# Test Report — {feature_name} — {timestamp}

## Summary
- Total: N | Pass: N | Fail: N | Skip: N
- Coverage: N% (if available)
- Run time: N seconds

## Failures
### {test name}
- File: {path:line}
- Expected: {value}
- Actual: {value}
- Stack: {first relevant frame}

## Passed
{collapsed list of passing test names}
```

Write to `.sweetclaude/reports/test-report-{issue-or-phase}-{timestamp}.md`. Append to aggregate report.

---

## Severity Classifier

After each test run, classify the result as **significant** (escalate) or **not significant** (continue):

**Escalate to IM2 if:**
- More than 30% of tests are failing after a bug fix attempt
- Any test with "happy path", "core flow", "main flow", or "critical" in its name is failing
- Compile errors or import errors prevent the suite from running at all
- A security review finding has severity High or Critical

**Continue if:**
- Isolated edge case failures with a clear, identified root cause
- Failures in features explicitly marked as optional or enhancement-only
- Test infrastructure issues (missing fixture, wrong env var) with a known workaround

When uncertain between escalate and continue: **escalate**. A false positive (unnecessary interruption) is better than a false negative (silent bad state).

---
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
python3 /tmp/test_jwplan2_task4.py
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/carsonsweet/dev/sweetclaude add skills/john-wick/SKILL.md
git -C /Users/carsonsweet/dev/sweetclaude commit -m "feat(john-wick): add Phase 4 Implement Prep and Phase 5 Implement with issue loop"
```

---

## Task 5: Phase 6 (Verify) + cross-cutting rules

**Files:**
- Modify: `skills/john-wick/SKILL.md` (append content)

Append the Verify phase and all cross-cutting rules: error handling, scope guards, multi-service notes.

- [ ] **Step 1: Write verification test**

```python
# /tmp/test_jwplan2_task5.py
with open('/Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md') as f:
    content = f.read()

# Verify steps
for step in ['V1', 'V2', 'V3', 'V4', 'V5']:
    assert step in content, f"FAIL: Missing Verify step {step}"

# V1 — test run + report
assert 'V1' in content and 'test' in content.lower(), "FAIL: V1 missing test run"

# V2 — code review with compliance
assert 'V2' in content and 'code-review' in content.lower(), "FAIL: V2 missing code-review"
assert 'compliance' in content.lower() and 'V2' in content, "FAIL: V2 missing compliance review"

# V5 — PR creation
assert 'V5' in content and ('gh pr create' in content or 'pull request' in content.lower()), \
    "FAIL: V5 missing PR creation"
assert 'prd' in content.lower() and 'gherkin' in content.lower() and 'V5' in content, \
    "FAIL: V5 PR description missing required references"

# Error handling
assert 'status: error' in content, "FAIL: Missing error state handling"

# Multi-service note
assert 'multi-service' in content.lower() or 'concurrent' in content.lower() or 'DS3' in content, \
    "FAIL: Missing multi-service guidance"

print("PASS")
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python3 /tmp/test_jwplan2_task5.py
# Expected: AssertionError
```

- [ ] **Step 3: Append Phase 6 and cross-cutting content**

Append to `/Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md`:

```markdown
## Phase 6: Verify

### V1 — Full test run + report (Autonomous)

Run the complete test suite on the feature branch. Generate a final MD test report and append to the aggregate report. If any tests fail: run the severity classifier. If significant failures: escalate to IM2 before continuing. If not significant: log and continue.

Update `current_step: V2`.

### V2 — Code, security, and compliance review (Autonomous)

Invoke `sweetclaude:code-review` with all three review types: code, security, and compliance.

The compliance review reads `.sweetclaude/state/compliance-context.yaml` automatically (updated in Plan 1). No manual framework specification needed.

Write review output to `.sweetclaude/reports/code-review-[YYYYMMDD].md`.
Record in `created_artifacts`.

If any Critical findings in code or security review: pause and present to user before continuing. Update `current_step: V3`.

### V3 — Update user-facing documentation (Autonomous)

Invoke `sweetclaude:documents-update-docs` for all user-facing documentation affected by the feature. Update `current_step: V4`.

### V4 — Update design documents (Autonomous)

Update all design documents (architecture, tech spec, contract analysis) to reflect the final implementation. These are now post-implementation records, not pre-implementation plans. Commit:
```
docs: update design documents to reflect final {feature_name} implementation
```

Update `current_step: V5`.

### V5 — Cut PR (Interactive)

Create the final pull request:

```bash
gh pr create \
  --title "{feature_name}: {one-line description from PRD}" \
  --base main \
  --head {feature_branch} \
  --body "..."
```

PR description must reference (in order):
1. Approved PRD path and version
2. User stories document path
3. Gherkin specs path
4. Test report (aggregate) path
5. Code review findings path
6. Compliance context summary (frameworks applied)
7. Any IM2 escalations that occurred and how they were resolved

Present the PR URL to the user:
```
JOHN WICK — Pipeline Complete
══════════════════════════════
PR: {url}

Pipeline summary:
- Phases completed: Bootstrap → Define → Plan → Design → Implement Prep → Implement → Verify
- Issues resolved: {N}
- Tests: {pass}/{total}
- Check-ins: {N} (significant findings: {N})
- Review findings: {N critical/warning}

Compliance frameworks applied: {list from compliance-context.yaml}
```

Update `john-wick.yaml status: complete`. Record PR URL in `created_artifacts`.

---

## Error Handling

If any step produces an unrecoverable error (skill invocation fails, git command fails, required file missing):

1. Set `john-wick.yaml status: error`.
2. Record the error in `context_checkpoint.notes`.
3. Commit current state: `chore(john-wick): error state at [step] — [brief description]`
4. Present to user:
   > "John Wick encountered an error at [step]: [description]. State saved. Inspect `.sweetclaude/state/john-wick.yaml` and fix the issue, then run `/sweetclaude:john-wick` to resume."
5. Stop. Do not auto-retry.

---

## Cross-Cutting Rules

**No time estimates.** John Wick never estimates how long a phase or step will take. Progress is measured in completed steps and passing tests, not elapsed time.

**Skill invocations are transparent.** When invoking an existing skill (product-prd, design-architecture, etc.), John Wick uses the `Skill` tool exactly as a user would. It does not bypass preflight guards, skip sections, or pass undocumented flags (except `--autonomous` which is an explicit extension added in Plan 1).

**State before steps.** `john-wick.yaml current_step` is updated to the next step before that step begins. A resume after any interruption will re-enter the correct step without duplication.

**Multi-service warning.** John Wick is designed for one service at a time. If the service contract analysis (DS3) identifies that a dependency's spec is absent or marked in-progress (another John Wick run), flag explicitly:
> "⚠ Dependency in-flight: [{service}] appears to be under active development. Contract analysis for this dependency may be stale by the time implementation begins. Consider sequencing: finish the upstream service's John Wick pipeline through DS7 before continuing."

**Test immutability after IP5 is absolute.** No step, no subagent, and no check-in may modify locked test files. If any step would require a test change (e.g., a V4 documentation update that touches test fixtures), halt and present to user.

---
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
python3 /tmp/test_jwplan2_task5.py
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/carsonsweet/dev/sweetclaude add skills/john-wick/SKILL.md
git -C /Users/carsonsweet/dev/sweetclaude commit -m "feat(john-wick): add Phase 6 Verify and cross-cutting rules"
```

---

## Task 6: Integration test + sync

**Files:** No new file content — validate complete skill and sync to installed location.

- [ ] **Step 1: Write integration test**

```python
# /tmp/test_jwplan2_integration.py
import os, re

skill_path = '/Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md'
assert os.path.exists(skill_path), "FAIL: Skill file does not exist"

with open(skill_path) as f:
    content = f.read()

# Frontmatter
match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
assert match, "FAIL: No frontmatter"
assert 'name: sweetclaude:john-wick' in match.group(1), "FAIL: Wrong skill name"

# All pipeline steps present
all_steps = [
    'B1', 'B2', 'B3', 'B4',
    'D1', 'D2', 'D3', 'D4', 'CK1',
    'P1', 'P2', 'P3', 'P4', 'CK2',
    'DS1', 'DS2', 'DS3', 'DS4', 'DS5', 'DS6', 'DS7', 'CK3',
    'IP1', 'IP2', 'IP3', 'IP4', 'IP5', 'IP6',
    'IM1', 'IM2',
    'V1', 'V2', 'V3', 'V4', 'V5',
]
for step in all_steps:
    assert step in content, f"FAIL: Missing step {step}"

# Resume protocol covers all 5 states
for state in ['waiting_for_user', 'paused', 'active', 'complete', 'error']:
    assert state in content, f"FAIL: Missing resume state: {state}"

# All 8 prerequisites
for check in ['phase.yaml', 'personas', 'task analysis', 'constraints',
              'I understand', 'gh auth status', 'error state', 'compliance-context.yaml']:
    assert check.lower() in content.lower(), f"FAIL: Missing prerequisite: {check}"

# IP5 boundary
assert 'locked_test_files' in content, "FAIL: Missing locked_test_files"
assert 'post_lock' in content, "FAIL: Missing post_lock in check-in calls"

# All three caucus preset inline definitions
assert 'pragmatist' in content.lower(), "FAIL: Missing product-design-review personas"
assert 'product owner' in content.lower(), "FAIL: Missing story-review personas"
assert 'senior architect' in content.lower(), "FAIL: Missing architecture-impact personas"

# Scope guards
assert '8 epics' in content or 'hard limit' in content.lower(), "FAIL: Missing epic hard limit"
assert '30%' in content, "FAIL: Missing severity classifier threshold"

# State write discipline
assert 'current_step' in content, "FAIL: Missing current_step updates"

# PR traceability
assert 'gh pr create' in content, "FAIL: Missing PR creation command"

print(f"PASS — {len(all_steps)} steps verified, all checks present")
```

- [ ] **Step 2: Run integration test**

```bash
python3 /tmp/test_jwplan2_integration.py
# Expected: PASS — 34 steps verified, all checks present
```

- [ ] **Step 3: Sync to installed location**

```bash
rsync -a --delete \
  /Users/carsonsweet/dev/sweetclaude/skills/ \
  /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/

# Verify john-wick skill is present in installed location
ls /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/ | grep john-wick
# Expected: john-wick and john-wick-checkin

diff /Users/carsonsweet/dev/sweetclaude/skills/john-wick/SKILL.md \
  /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/john-wick/SKILL.md
# Expected: no output (files identical)
```

- [ ] **Step 4: Commit sync confirmation**

```bash
git -C /Users/carsonsweet/dev/sweetclaude commit --allow-empty \
  -m "chore(john-wick): verify plan 2 orchestrator synced to installed location"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by task |
|---|---|
| §3 Prerequisites Gate (8 checks) | Task 1 |
| §4 Pipeline — all 34 steps | Tasks 2-5 |
| §5 Issue Iteration Loop | Task 4 |
| §6 State Machine (john-wick.yaml schema) | Task 1 |
| §6 Resume protocol | Task 1 |
| §6 Context window management | Task 1 |
| §7.2 Cascade document update | Task 3 (DS7) |
| §7.3 Service contract analysis | Task 3 (DS3) |
| §7.4 GitHub Issues creation | Task 4 (IP6) |
| §7.5 MD test report | Task 4 |
| §7.6 Severity classifier | Task 4 |
| §7.7 Compliance review via code-review | Task 5 (V2) |
| §7.8 Caucus persona presets (inline) | Tasks 2-3 |
| §7.9 Compliance context at B4 | Task 2 |
| §7.10 Phase check-ins (CK1, CK2, CK3) | Tasks 2-3 |
| §9 Orchestrator architecture | All tasks |
| §10 Interactive gate format | Task 1 |
| §14 Multi-service guidance | Task 5 |

**What this plan does NOT cover:**
- Plan 3 (future): `sweetclaude:documents-update-docs` if it doesn't exist — check before V3 runs
- Plan 3 (future): mutation testing post-V1 (explicitly out of scope per §12)
- Plan 3 (future): automated rollback (explicitly out of scope per §12)

**Plan 2 must be fully committed and the integration test passing before the first real John Wick pipeline run.**
