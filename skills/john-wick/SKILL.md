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

## Autonomous Execution Safety

John Wick runs Claude Code with `--dangerously` flags disabled by default. File writes, shell commands, and git operations are executed directly — no sandbox bypass is assumed. If the project requires elevated permissions (e.g., docker, system-level commands), the user must configure that separately before invoking John Wick.

---
