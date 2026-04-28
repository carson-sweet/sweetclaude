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

**If `status: paused` or `status: active`:** Emit one line: "Last completed: {last step in sessions[].steps_completed}. Resuming from {current_step}." Continue from `current_step`. Before continuing: check `interactive_gate_pending.step`. If it is non-null, treat this resume as `waiting_for_user` — re-present the gate before proceeding.

**If `status: complete`:** Tell the user the pipeline is done. Point to the PR URL stored in `created_artifacts` where type=pr.

**If `status: error`:** Show the recorded error, including the last entry in `sessions[].steps_completed` and the value of `current_step` so the user knows where things broke. Then run the Prerequisites Gate (which will re-check prerequisites and enforce check #7). Do not continue until the gate passes.

**State write discipline:** After every step completes, update `john-wick.yaml` — set `current_step` to the next step — before beginning that next step. State always reflects what comes next, never what just finished. This ensures a resume after interruption skips nothing and repeats nothing.

---

## Prerequisites Gate

Run on first invocation (no `john-wick.yaml`) OR when `status: error` from a previous run. Validate all of the following. On any failure, halt with the specified error message and do not create `john-wick.yaml`.

| # | Check | How | Error if missing |
|---|---|---|---|
| 1 | SweetClaude initialized | `.sweetclaude/state/phase.yaml` exists | "Run `/sweetclaude:init` first." |
| 2 | Personas artifact | `.sweetclaude/` or `docs/` contains a file with "persona" in the name | "Complete product discovery first: `/sweetclaude:product-discovery`" |
| 3 | Task analysis with success + failure criteria | A task analysis artifact exists with "success" and "failure" in its content | "Task analysis incomplete. Rerun `/sweetclaude:product-discovery`." |
| 4 | Constraints analysis | A constraints artifact exists in `.sweetclaude/` or `docs/` | "Constraints analysis missing." |
| 5 | Dangerously-skip-permissions acknowledged | Present the warning below and require the user to type "I understand" exactly | "John Wick mode requires explicit acknowledgment." |
| 6 | GitHub mode (conditional) | If user selects GitHub mode at B1: `gh auth status` must exit 0 | "GitHub CLI not authenticated. John Wick can help you fix this now." |
| 7 | No active run in error state | If `john-wick.yaml` exists AND this is not an error-recovery invocation: `status` must be `complete` or `paused` | "Previous run is in error state. Inspect `.sweetclaude/state/john-wick.yaml` before restarting." |
| 8 | Compliance context | `.sweetclaude/state/compliance-context.yaml` exists | Note: not a hard block — collect at B4 if absent. Log: "Compliance context missing — will collect at B4." |

**Note on check #7:** When the Prerequisites Gate is invoked from the `status: error` path (error recovery), check #7 is automatically satisfied — the error state IS the active error being recovered. The gate proceeds to re-validate checks 1-5 and allow recovery.

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
d1_flags: []

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
6. On response: record the decision, update artifacts. Clear `interactive_gate_pending` — set both `step` and `description` to null — before setting `status: active`. Continue.

---

## Context Checkpoint Protocol

Before each autonomous step, estimate remaining context budget. If within approximately 20% of the context limit:

1. Commit current state: `chore(john-wick): checkpoint at [step]`
2. Update `context_checkpoint` in `john-wick.yaml` with current step and timestamp.
3. Emit: "Context limit approaching. State saved at [step]. Run `/sweetclaude:john-wick` to resume."
4. Stop. Do not attempt to begin the next step.

A clean stop is always better than a corrupted step.

**Mid-step checkpoints:** For long autonomous steps (document generation, caucus runs, cascade updates), also check context budget at natural sub-step boundaries (e.g., after each artifact is generated, after each caucus turn). If context limit is reached mid-step: revert any uncommitted file changes, save a checkpoint at the start of the current step (so it replays cleanly on resume), commit, emit the resume message, and stop. If partial artifacts were already committed mid-step, note them in `context_checkpoint.notes` before stopping. On resume, check `context_checkpoint.notes` for any pre-existing partial artifacts and skip regenerating them to avoid duplication.

---

## Phase 0: Bootstrap

### B1 — Tracking mode (Interactive)

Update `john-wick.yaml`: set `status: waiting_for_user`, `interactive_gate_pending.step: B1`, `interactive_gate_pending.description: Choose tracking mode and phase check-in preference`.

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

Update `john-wick.yaml`: set `status: waiting_for_user`, `interactive_gate_pending.step: B2`, `interactive_gate_pending.description: Choose feature branch name`.

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

If `.sweetclaude/state/compliance-context.yaml` already exists: skip. Log "Compliance context already present — skipping B4." Update `current_phase: DEFINE`, `current_step: D1`.

If it does not exist: invoke the compliance context interview from `sweetclaude:product-discovery` (the three-question section: data categories, user geography, user type). That section writes `.sweetclaude/state/compliance-context.yaml`. After it completes, record the path in `john-wick.yaml compliance_context`. Update `current_phase: DEFINE`, `current_step: D1`.

---

## Phase 1: Define

### D1 — Generate PRD (Autonomous)

**Resume guard:** If `current_step` is `D1-scope-gate` on resume, skip PRD generation entirely. The PRD already exists. Present the scope override prompt directly: 'The PRD has more than 8 epics. Type "override scope limit" to continue, or provide guidance on how to decompose the PRD.' Clear `interactive_gate_pending` (set both fields to null). Set `status: active`. Write `current_step: D2`, then continue.

Invoke `sweetclaude:product-prd` with `--autonomous` flag. The skill reads discovery artifacts and compliance context, generates a complete PRD draft without user interaction, and flags thin sections inline.

The PRD is written to `docs/[feature-name]-prd-draft-v1.0-[YYYYMMDD].md`.

Record in `created_artifacts`: `{step: D1, type: prd, path: ..., version: 1}`.

If the PRD contains any ⚠ flagged sections, write their section names to `john-wick.yaml` as a top-level `d1_flags` list (e.g., `d1_flags: [Problem Statement, Goals and Success Metrics]`). D3 and D4 will read this list to present flags to the user.

**Scope check:** After the PRD is generated, count the epics. If more than 6 epics: surface a warning:
> "⚠ Scope warning: This PRD has {N} epics. John Wick recommends decomposing into smaller services before continuing. Large scope compounds errors in an autonomous pipeline."

After surfacing the warning, continue. Write `current_step: D2`.

If more than 8 epics: halt and require explicit user override:
> "⚠ Hard limit: {N} epics exceeds the maximum for autonomous execution (8). Decompose the PRD into smaller services, or type 'override scope limit' to proceed at your own risk."

Write `current_step: D1-scope-gate` to `john-wick.yaml`. Update `john-wick.yaml`: set `status: paused`. Leave `interactive_gate_pending` null (do not set it). Do not advance `current_step` until the override is accepted.

If the scope check passes (≤ 8 epics): Update `current_step: D2`. (Override-accepted transition is handled exclusively by the D1 resume guard above — it writes `current_step: D2` there and does not return here.)

### D2 — PRD caucus (Autonomous)

Run a 3-turn product design review caucus on the PRD. Pass these four personas inline to the caucus skill — do not rely on a preset file:

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

Write this change summary to `.sweetclaude/caucus/prd-review-[YYYYMMDD]-changes.md`. Record in `caucus_outputs`: `{step: D3, path: .sweetclaude/caucus/prd-review-[YYYYMMDD]-changes.md}`. This persists the summary across context loss so D4 does not need to regenerate it.

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

If result is `significant`: write `current_step: D4` in `john-wick.yaml` before presenting to user:
> "CK1 found a gap: [finding]. Returning to PRD review."
Do not write `current_step: P1` until after the D4 re-review is confirmed and complete.

If result is `none` or `minor`: log and continue. Update `current_step: P1`.

---
