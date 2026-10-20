# Behavioral E2E Failure Register

Version: 1.0.0

Date: 2026-10-19

## BEH-001 — Lifecycle behavioral suite claimed ready before calibration

- Date observed: 2026-10-19
- Last updated: 2026-10-19
- System version/channel/source observed: local SweetClaude checkout; exact runtime version unavailable from the live calibration report.
- Workflow skill or process used: lifecycle behavioral E2E compiler and runner; `record-workflow-failure` reporting skill.
- Workflow phase: behavioral-test design, calibration, and live execution.
- Workflow step, story, or gate: `plan.capture-a-customer-problem`; all four generated variants.
- Actor type: Codex test-harness author; Claude CLI execution runner.
- Session status summary: long-running, compacted/resumed, interrupted after invalid live-run evidence.
- Model/reasoning: Codex / GPT-6; exact reasoning level unavailable from persisted evidence.
- Turns/tools/compressions: exact counts unavailable; filesystem inspection, Python checks, process control, and Claude CLI used; at least one compaction.
- Context state: compacted/resumed.
- Active/stale subagents: none.
- Observability gaps: no reviewed per-case response oracle, route oracle, effect allowlist, or scenario-complete fixture.
- Last update timestamp/result: unavailable.
- Last doctor timestamp/result: unavailable.
- Last fix timestamp/result: no corrective harness implementation after failure reporting was requested.
- Last recovery timestamp/result: no recovery run.
- Last status scan timestamp/result: unavailable.
- Bad-state scan summary: case compiler and runner exist but do not establish valid behavior; live calibration has 0 passes, 2 harness-invalid effect failures, and 2 oracle gaps.
- Story or phase where observed: lifecycle Plan / `plan.capture-a-customer-problem`.
- Failure class: false readiness claim; invalid fixture; uncalibrated oracle; execution before readiness gate.
- What happened: structural checks and generated case counts were reported as behavioral readiness. The completed live calibration ran four cases for one story, cost `$0.4677109`, and yielded 0 valid passes.
- How detected: user challenged readiness; direct inspection of the live calibration report and runner fixture/evaluator confirmed the gap.
- Why existing prep/gates missed it: the plan stated required fixture, decision, containment, and oracle contracts but no executable readiness gate enforced them before `--execute`.
- Corrective action taken: full report and this register entry written; execution stopped; no behavior result claimed.
- Deterministic guard added or changed: none. Required: case-contract completeness, fixture-capability audit, oracle-calibration gate, effect-allowlist gate, driver-protocol gate, live-run freeze gate, and result-classification gate.
- Status: open.
- Recurrence policy: recur if any structural harness result is called behavioral readiness, or any chargeable run begins without a complete calibrated case contract.
- Full report path: `.sweetclaude/failure-reports/FR-047-behavioral-e2e-false-readiness-2026-10-19.md`
