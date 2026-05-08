---
spdx-license: AGPL-3.0-or-later
name: john-wick
user-invocable: true
description: Fully autonomous, resumable, multi-session SDLC pipeline. Given completed discovery artifacts, runs product-definition → design → TDD → implementation → review → PR with minimal human involvement. Interactive gates are explicit, pre-defined, and rare.
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# John Wick Mode

Fully autonomous, resumable SDLC pipeline. Runs from discovery artifacts to merged PR with minimal human involvement. Interactive gates are pre-defined and infrequent.

**Phase contents (read on demand — see Phase Router below):**
- [phase-0-bootstrap.md](phase-0-bootstrap.md) — B1, B2, B3, B4
- [phase-1-define.md](phase-1-define.md) — D1, D2, D3, D4, CK1
- [phase-2-plan.md](phase-2-plan.md) — P1, P2, P3, P4, CK2
- [phase-3-design.md](phase-3-design.md) — DS1, DS2, DS3, DS4, DS5, DS6, DS7, CK3
- [phase-4-implement-prep.md](phase-4-implement-prep.md) — IP1, IP2, IP3, IP4, IP5, IP6
- [phase-5-implement.md](phase-5-implement.md) — IM1, IM2
- [phase-6-verify.md](phase-6-verify.md) — V1, V2, V3, V4, V5

**Cross-cutting reference:**
- [state-schema.md](state-schema.md) — `john-wick.yaml` schema
- [report-format.md](report-format.md) — Test report template
- [severity-classifier.md](severity-classifier.md) — Significant vs not-significant decision rules

---

## Entry and Resume

On invocation, read `.sweetclaude/state/john-wick.yaml`.

**If the file does not exist:** Run the Prerequisites Gate, then start at B1.

**If `status: waiting_for_user`:** Present the pending interactive gate from `interactive_gate_pending`. Collect user input. Update `status: active`. Continue from `current_step`.

**If `status: paused` or `status: active`:** Emit one line: "Last completed: {last step in sessions[].steps_completed}. Resuming from {current_step}." Continue from `current_step`. Before continuing: check `interactive_gate_pending.step`. If it is non-null, treat this resume as `waiting_for_user` — re-present the gate before proceeding.

**If `status: complete`:** Tell the user the pipeline is done. Point to the PR URL stored in `created_artifacts` where type=pr.

**If `status: error`:** Show the recorded error, including the last entry in `sessions[].steps_completed` and the value of `current_step` so the user knows where things broke. Then run the Prerequisites Gate (which will re-check prerequisites and enforce check #7). Do not continue until the gate passes.

**State write discipline:** After every step completes, update `john-wick.yaml`: (1) append the just-completed step name to `sessions[-1].steps_completed`, (2) set `current_step` to the next step — before beginning that next step. State always reflects what comes next, never what just finished. This ensures a resume after interruption skips nothing and repeats nothing.

---

## Phase Router

Map `current_step` → phase file → execute step:

| `current_step` prefix | File to read |
|---|---|
| `B*` | `phase-0-bootstrap.md` |
| `D*`, `CK1` | `phase-1-define.md` |
| `P*`, `CK2` | `phase-2-plan.md` |
| `DS*`, `CK3` | `phase-3-design.md` |
| `IP*` | `phase-4-implement-prep.md` |
| `IM*` | `phase-5-implement.md` |
| `V*` | `phase-6-verify.md` |

When entering a phase for the first time, read the entire phase file. When resuming mid-phase, scroll to the `## {step_id}` section.

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

**After prerequisites pass:** Initialize `john-wick.yaml` with `status: active`, `current_step: B1`, and the discovery artifact paths found during checks. The full schema is in [state-schema.md](state-schema.md).

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

## Error Handling

If any step produces an unrecoverable error — including but not limited to: skill invocation fails, git command fails, required file missing, YAML parse error in `compliance-context.yaml` or other state files, caucus subagent returns empty or malformed output, `gh issue close` fails silently, or test runner crashes before producing output:

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

**d1_flags field.** The `d1_flags` list in `john-wick.yaml` records thin-section flag names from D1. These are surfaced by D3 and D4 during PRD review. After D4 completes (all sections approved), D4 clears `d1_flags` to empty list.
