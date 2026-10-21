# Spike: completion verification and user-selected oversight

**Version:** 0.1

**Date:** 2026-10-21

**Status:** Spike. Design direction and considerations only; nothing here is decided or scheduled.

**Related:** issue #161 (phase 3 mode and phase-gate decisions), ledger rows for phase exit criteria and soft and hard gate overrides in `docs/design/remediation-ledger.yaml`, `.sweetclaude/plans/phase3-gates-design-note-2026-10-21.md` (local).

## Problem

SweetClaude's documents say a phase cannot advance until its exit criteria are met, and that soft and hard gate overrides are logged. No code checks exit criteria or records overrides. Today the model judges its own work against prose criteria in `rules/phase-gates.md`. Research from 2026 reports that agents often claim completion falsely (for example, one study found agents skipped requested files in 67.9% of runs and misreported most incomplete runs). A model's own "done" claim needs a separate check.

## Market research summary (October 2026)

No single product runs a full criteria-to-human verification sequence. The parts exist separately:

| Part | Where it exists | Evidence |
|---|---|---|
| Model proposes criteria; human adjusts before work starts | Kiro, GitHub Spec Kit, Augment Intent, Factory Missions | Strong; the most common real gate |
| Deterministic checks that block or send work back | Aider (tests, lint), CrewAI guardrails, Stop hooks in Claude Code, Codex and Gemini CLI | Good for code; none tie receipts to prose criteria |
| Independent reviewer agent | Factory validators, Augment Verifier, superpowers review subagents, Claude Code agent hooks | Mechanism exists; little public accuracy data |
| Running record of criteria satisfaction and gaps | Not found | New |
| Send back for correction with logging | Stop hooks send back; BMAD logs dated decisions | Send-back common; logging rare |
| Human review at completion | Plan-mode approval; BMAD (a human or orchestrator marks done, never the coding agent) | Common, mostly at the start |
| End-to-end evaluation at boundaries | Factory (validators at milestone end against the running app) | One clear example |

Retry caps in the market: Cursor `loop_limit` (default 5), CrewAI `guardrail_max_retries`. Not verified: internal enforcement in Kiro and Spec Kit, and whether BMAD enforces its FAIL verdict in code.

## Design direction

1. **Criteria before work.** At phase start, the model proposes completion criteria for the phase, each with the receipt that will prove it (a deterministic check where possible, otherwise named evidence). The user adjusts and accepts them. The accepted set is frozen; no later step may add or remove criteria without a recorded amendment. This extends the existing large-story success-criteria contract (criterion IDs, frozen at the define exit, ledger at completion) to every phase.
2. **Receipts as work proceeds.** Each criterion collects receipts. Deterministic receipts (tests, lint, file and schema checks, CI results) are produced by code, not by the model. The existing control-receipt types (phase-exit, objective-criteria, finding-disposition) are the starting schema.
3. **Running completion record.** An independent reviewer maintains a record per criterion: met, partly met, unmet, or not judgeable, with the gap and the evidence. The worker and the user can read it at any time.
4. **Send-back with logging.** When the reviewer finds an obvious gap, or finds a criterion incomplete or incorrect, the work goes back to the worker with the gap named. Each send-back is logged.
5. **Human review.** When the reviewer is satisfied as far as it can judge, a human reviews the completion record and the receipts.
6. **End-to-end evaluation at key boundaries.** When a complete phase or a complete deliverable is proposed to the reviewer, run an end-to-end evaluation of the criteria (for example against the running application or the full test suite), not only per-criterion receipts.

## Design concerns

### 1. Same-model blind spots

A reviewer on the same model as the worker can share its mistakes. No public data measures how much a same-model reviewer catches. Directions:

- Minimum: prompt-tuning of the reviewer (sees only the criteria, the receipts and the artifacts; not the worker's reasoning).
- The user can explicitly accept same-model review as a known risk, and that acceptance is recorded.
- A second LLM provider can be configured as the judge.
- A classifier stage: a classifier (the user named "Jev or a similar classifier"; the term needs confirmation) makes a completion decision with a confidence score. Below a confidence threshold, the decision goes to an LLM judge.

### 2. Cost and time

The largest risk. Each review pass and each end-to-end evaluation adds model spend and waiting time. The answer is user options: the user decides how autonomous or how supervised the process is, and can turn any single gate's enforcement on or off. These choices combine. For example, a user can run fully autonomous John Wick mode and still have the model make the completion judgements. Requirement: build the full enforcement capability so every option is available, then let configuration select it.

### 3. Retry limits

The reviewer and the worker can loop. Use a retry cap per criterion or per phase, following the Cursor and CrewAI models. At the cap, the work stops and goes to the human with the completion record.

### 4. Criteria quality, captured as telemetry

The whole sequence depends on the quality of the criteria. Prose criteria that a reviewer cannot judge weaken every later step; the user's adjustment at the start is the main control. Capture every decision as telemetry for later analysis and as potential training data: proposed criteria, user edits, receipts, reviewer verdicts with confidence, send-backs, retry counts, human overrides, and final outcomes.

### 5. Oversight options as a spectrum

Design a set of incremental options:

- One end: full autonomy. Least human effort, highest risk, higher LLM cost from additional judging.
- Other end: full discipline. For high-stakes projects. Highest human effort, lower but not zero judge risk, least risk that the machine misses something.
- At least two levels in between.
- The user can change the level per phase, at phase start or in the middle of a phase.
- Level labels must be self-explanatory.

The name "discipline level" needs a better replacement. Candidates for discussion (not decided): "oversight level", "assurance level", "review level", "supervision level". Candidate labels for an oversight scale (not decided): Hands-off, Spot-check, Checkpoint, Full review.

Existing related settings that the design must reconcile:

- Deference level (`rules/interaction-model.md`): Collaborative, Guided, Autonomous. It controls how often SweetClaude stops to talk with the user, and Autonomous already pauses at phase gates.
- TDD levels 0 to 3.
- John Wick mode: fully autonomous pipeline with hard gates at PRD approval, design review and final PR.
- Project mode (Flow, Kanban, Shape Up, Agile) and its gates in `config/mode-gates.yaml`.

### 6. QA and CI feedback loop (separate angle)

QA and CI results can feed the sequence in two ways: as real-time input to completion decisions (a failing CI run or QA finding reopens a criterion), and as data for later training (linking criteria, verdicts and downstream test outcomes shows which verdicts were wrong).

## Open questions

1. What is "Jev"? The term does not appear in the repository or in the October 2026 research.
2. Is the oversight scale a new setting, or does it replace or merge with the deference level?
3. Which name and which labels for the scale?
4. Where do criteria, receipts and the completion record live (per work item, per phase)? The existing control receipts live under `.sweetclaude/state/evidence/`.
5. Default retry cap, and its scope (per criterion or per phase)?
6. Telemetry: where it is stored, whether it stays local, and how users opt in. The existing usage-tracking feature and `.sweetclaude/metrics/events.log` are candidates.
7. How the spike result affects the parked 5.1.0 rows for phase exit criteria and gate overrides: ship them in 5.1.0 with a minimal version, or move them to the release that implements this design.
