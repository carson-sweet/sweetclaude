# Spike: completion verification and user-selected oversight

**Version:** 1.0

**Date:** 2026-10-21

**Status:** Spike. Six design decisions recorded 2026-10-21 (see Decisions); sub-decisions listed under each remain open.

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

## What SweetClaude's completion criteria judge

The coding harness handles whether the code was written. SweetClaude's completion criteria judge the process and the result against what was agreed. Examples:

- Are all TDD red tests satisfied, as proven by test runs?
- Did the tests keep their integrity through the implementation effort (no edits, skips or weakening after the RED commit, except recorded and approved overrides)?
- Are all user stories functionally satisfied?
- Does the final result match the original design and PRD?

Consequences for the design:

- The first two are largely deterministic. Test results, the RED commit, the diff of test files since that commit, test-guardian denials, and logged override releases are machine evidence. These need receipts, not judges.
- The last two are judgements of the result against documents (user stories, design, PRD). They are text-and-behavior comparisons more than code reasoning, and they can often be broken into per-item yes/no questions (one per user story, one per requirement or design decision). That structure suits a fixed-answer decision model such as Jev, with escalation on low confidence. The correlated-error finding still applies to the escalation target.

## Design concerns

### 1. Same-model blind spots

A reviewer on the same model as the worker can share its mistakes. No public data measures how much a same-model reviewer catches. Directions:

- Minimum: prompt-tuning of the reviewer (sees only the criteria, the receipts and the artifacts; not the worker's reasoning).
- The user can explicitly accept same-model review as a known risk, and that acceptance is recorded.
- A second LLM provider can be configured as the judge.
- A classifier stage: Jev or a similar decision model makes a completion decision with a confidence score. Below a confidence threshold, the decision goes to an LLM judge. See "Jev research" below for what is known and the main risk of this pattern.

### Jev research (2026-10-21)

**What it is.** Jev is a decision model from TypeSafe AI, released in September 2026 and marketed as a "System One" model. It does not generate text. It picks from answers the caller defines and returns probabilities. Three question types: choice (pick from supplied options, with a probability per option and a confidence value), score (a probability-weighted position on a defined scale), and a yes/no probability. Sources: [TechCrunch, 2026-09-18](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/), [OpenRouter: What is Jev](https://openrouter.ai/blog/insights/what-is-jev/), [Apidog](https://apidog.com/blog/what-is-jev/), [innFactory](https://innfactory.ai/en/blog/jev-system-one-model-classifier-not-llm/).

**Availability and cost.** Available through OpenRouter and as a promptfoo provider ([promptfoo](https://www.promptfoo.dev/docs/providers/typesafe/)); a Palo Alto XSOAR integration exists ([xsoar.pan.dev](https://xsoar.pan.dev/docs/reference/integrations/type-safe-jev)). One guide lists $0.042 per million input tokens, free output tokens, a 64,000-token request limit, text-only input, and model version jev-1.13.0 in late September 2026 ([Linas](https://linas.substack.com/p/how-to-use-jev-ai)). Vercel reported use by 35% of its paid teams within two weeks of launch ([TechCrunch, 2026-10-16](https://techcrunch.com/2026/10/16/jev-is-vercels-fastest-adopted-ai-model-ever/)). These figures are not independently verified.

**Evidence for the cascade pattern.** The "accept when confident, escalate when unsure" cascade is the main proposed use ([arXiv 2609.26550](https://arxiv.org/pdf/2609.26550)). On OpenRouter's 88-case faithfulness set, Jev's Brier score was 0.043 against 0.054 for an LLM judge, and verdicts above 0.8 confidence were acceptable 98% of the time ([OpenRouter](https://openrouter.ai/blog/tutorials/jev-vs-llm-as-a-judge/); [Beam](https://beam.ai/agentic-insights/llm-as-a-judge-jev)). These are vendor-run results on a small sample. LLM judges give no comparable native confidence and tend to score near 0 or 1 even when uncertain ([Analytics Vidhya, 2026-10](https://www.analyticsvidhya.com/blog/2026/10/jev-vs-llm-as-a-judge-evals/)).

**Evidence against, relevant to completion judging.**

- Correlated errors: when Jev is wrong with high confidence, about 96% of LLM verdicts repeat the same wrong answer, so an LLM fallback does not reliably catch Jev's confident errors ([arXiv 2609.29769, "Cheaper, Faster, and Wrong in the Same Places"](https://arxiv.org/pdf/2609.29769)). This removes part of the value of the cascade as a guard against same-model blind spots.
- Jev trails a frontier LLM on tasks where the verdict must be derived (math, code, logic) ([arXiv 2609.26550](https://arxiv.org/pdf/2609.26550)). This matters less here than it first appears: SweetClaude's completion criteria are mostly not judgements about code (see "What SweetClaude's completion criteria judge").
- Calibration outside the reported test sets is disputed; one discussion suggests overconfidence on simple cases ([Hacker News](https://news.ycombinator.com/item?id=49933476), anecdotal).

**Implications for this spike.**

- Jev fits fixed-answer decisions with cheap, calibrated routing: "is criterion X met: yes, no, cannot judge", or "which oversight action: accept, send back, escalate to human".
- It should not be the only judge for criteria that need derivation over code or logic. For those, deterministic receipts (tests, checks) stay primary. Few SweetClaude completion criteria are of this kind.
- The cascade does not give independence: Jev and an LLM judge fail in the same places. If independence is the goal, the escalation target must differ in kind (deterministic check or human), not only in model.
- Calibration must be measured on SweetClaude's own completion decisions before thresholds are set. The telemetry in concern 4 provides that data.
- Jev adds an external provider dependency and sends criteria and evidence text to that provider. This needs an explicit user opt-in, like a second LLM provider.

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

## Pilot: large stories

The large-story workflow is the first use case and the test of this process. It already enforces in code: a success-criteria contract generated from a skeleton and frozen with a hash before design starts; rejection of vague and unmeasurable criteria; denial of contract edits after the freeze except through an approval receipt and re-freeze; phase-based tool gating; a stop guard while the story is not finished; and a completion gate on the ledger, its evidence files and a ship closeout.

Gaps to close (verified in code on 2026-10-21):

1. Self-attested verification. `scripts/large_story_controller.py` `enter_verify_phase` writes ledger evidence from criterion results supplied by the caller, and the status defaults to "pass". The contract already declares `evidence_owner: controller` and `measurement_type: command`, but no criterion field holds an executable command, so the controller cannot run the measurement. Fix direction: an executable measurement field per criterion, run by the controller, with the result written as the evidence. No design decision needed beyond the field name.
2. Human acceptance of the criteria is not recorded. `freeze_contract` takes `frozen_by` as a parameter with "user" as the default. Needs a decision: how code proves that a human, not the model, took an action (see open question 7).
3. Amendment approval is documented as human-run, but it is not verified that code stops the model from running `approve-amendment`. Same decision as gap 2.
4. Judged criteria are excluded. The contract rejects human-judged criteria and routes them to backlog, so "all user stories functionally satisfied" and "result matches the design and PRD" cannot be criteria. Needs the reviewer design from this spike (per-item yes/no questions judged by an independent reviewer with recorded confidence).
5. No independent reviewer, no running gap record, no send-back loop with retry limits, no mandatory human review at completion, no oversight levels, no decision telemetry. These are this spike's design items.

## Decisions

1. **How code proves a human action (2026-10-21).** The user types an approval phrase, and a UserPromptSubmit hook records it as an approval bound to the work item and the action. The controller requires that record before it freezes criteria, accepts an amendment, or marks the work complete. A PreToolUse guard protects the approval records from model writes. Capturing the answer to an AskUserQuestion prompt in a PostToolUse hook can be added later, after a live probe confirms that payload. Known limit: a determined model with shell access can still forge a record file; the design goal is no accidental self-approval and a visible trace. Open: the exact phrase format, and what happens in fully autonomous mode where no human is present (depends on the oversight scale).

2. **How judged criteria are written and judged (2026-10-21).** First, traceability makes them deterministic where possible: each user story and each functional requirement links to at least one executable test (a Gherkin scenario or test ID), and the controller checks that every item has a link and every linked test passes. Second, items that tests cannot cover (design and PRD conformance, many non-functional requirements) use a new judged measurement type: one yes/no question per item, with the source document and section, answered by an independent reviewer with a verdict, a confidence score and evidence. Third, a human judges the item through the decision 1 approval record when the verdict confidence is low, and always at the high end of the oversight scale. Open: a stable link convention from feature scenarios to story and requirement IDs; the large-story skill instruction that routes judged criteria to backlog changes.

3. **Who the independent reviewer is (2026-10-21).** A configurable reviewer with one interface and several backends: a prompt-tuned, isolated same-model reviewer subagent as the default (it sees only the criteria, the receipts and the artifacts; the user's acceptance of same-model risk is recorded through decision 1), a second-provider judge on the existing `scripts/behavioral_judge.py` backends, and Jev. Low-confidence verdicts always escalate to a human or a deterministic check, never to a second model alone. Build order: same-model default first, second provider next, Jev after SweetClaude calibration data exists. Open: how LLM judges produce a usable confidence score (for example agreement across repeated judgements); cost per verdict per backend.

4. **Retry limits (2026-10-21).** Two caps: per criterion, default 3, taken from the existing `config/orchestrator-defaults.yaml` `iteration_limits.default_max` and overridable per criterion; and per phase, default 5 (Cursor's default, to be tuned with telemetry). At either cap the work stops and goes to the human with the completion record. When no human is present (autonomous or John Wick mode), John Wick's existing rule applies: save state, record the reason, stop, do not auto-retry. Every send-back and every cap event is logged. Open: whether a criterion amendment resets its counter.

5. **Oversight scale (2026-10-21).** A new setting, "oversight level", separate from the deference level, with four levels: Hands-off (the reviewer decides every gate; no human gate blocks; deterministic receipts still required; the human gets a summary at the end of the work item), Spot-check (the reviewer decides; low-confidence verdicts and the final deliverable go to the human), Checkpoint (the human accepts the criteria at the start and reviews at every phase exit; the reviewer gates in between), and Full review (the human accepts the criteria, judges every judged item and reviews at every phase exit; escalation goes to the human or a second-provider judge). Changeable per phase and mid-phase; each gate can be switched on or off regardless of level. The deference level is unchanged. Open: behavior for contradictory combinations with the deference level; defaults for new projects, for John Wick mode, and per project mode.

6. **Decision telemetry (2026-10-21).** Audit records and analysis telemetry are split. Audit records (approvals, overrides, send-backs, cap events) are always written to the workflow's own evidence, whatever the opt-in, following the TDD override precedent. Analysis telemetry goes to an append-only `.sweetclaude/metrics/verification.jsonl`, one record per decision, written only when usage tracking is on and a new `completion_verification` track is enabled. Full text (criteria wording, user edits, verdict evidence) is recorded only when a separate content flag is also enabled. Everything stays local, consistent with the existing usage-tracking design. Open: whether `verification.jsonl` is excluded from commits by default; the JSONL schema; consent for any future training export.

## Open questions

1. Which decisions, if any, go to Jev or a similar decision model, and what escalation target follows a low-confidence verdict (LLM judge, deterministic check, or human), given the correlated-error finding?
2. Is the oversight scale a new setting, or does it replace or merge with the deference level?
3. Which name and which labels for the scale?
4. Where do criteria, receipts and the completion record live (per work item, per phase)? The existing control receipts live under `.sweetclaude/state/evidence/`.
5. Default retry cap, and its scope (per criterion or per phase)?
6. Telemetry: where it is stored, whether it stays local, and how users opt in. The existing usage-tracking feature and `.sweetclaude/metrics/events.log` are candidates.
7. How does code prove that a human, not the model, took an action (accepting criteria, approving an amendment, completing the final review)? In Claude Code the model runs every command, so a command alone proves nothing. Candidate signals exist in the hook protocol (for example the user's own prompt text at UserPromptSubmit, or the answer to an AskUserQuestion prompt seen at PostToolUse), but none is verified for this use yet.
8. How the spike result affects the parked 5.1.0 rows for phase exit criteria and gate overrides: ship them in 5.1.0 with a minimal version, or move them to the release that implements this design.
