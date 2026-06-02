# Process Controls For Autonomous Work

These controls apply to any SweetClaude skill path that can spawn subagents,
run caucuses, or enter correction loops.

## Required Ledger

Before spawning a caucus, test writer, implementer, or autonomous reviewer,
create or update a process-control ledger:

- Standard workflows: `.sweetclaude/state/process-control-ledger.yaml`
- John Wick: `process_control` in `.sweetclaude/state/john-wick.yaml`

The ledger must record:

- workflow or story id;
- current step;
- success criteria contract path, if the workflow is large/high-rigor;
- `success_criteria_contract_hash`, if the workflow is large/high-rigor;
- `criterion_ids`, if the workflow is large/high-rigor;
- subagent budget approval;
- maximum caucus rounds in the current budget window;
- maximum reviewer agents in the current budget window;
- caucus rounds used;
- reviewer agents used;
- blocking caucus failures;
- WLF or process-failure count;
- adversarial pass-state bypass count;
- human approvals for extra budget, contract reopen, or resume after stop;
- current stop disposition, if any.

## Large-Story Workflow Routing

Users start complete large/high-rigor story workflows through `/sweetclaude:go`
using natural language. `/sweetclaude:go` routes matching requests to the
internal `sweetclaude:large-story` workflow.

Other skills such as `/sweetclaude:code-feature`, `/sweetclaude:code-issue`,
and `/sweetclaude:code-tdd` may perform bounded implementation work inside a
large-story workflow, but they are not the canonical end-to-end large-story
entrypoint. They must inherit the frozen success criteria contract from the
calling workflow or stop before implementation begins.

The user flow is:

1. Start or resume with `/sweetclaude:go <natural-language request>`.
2. During Define, create and freeze `success_criteria_contract`.
3. Store the contract path, `success_criteria_contract_hash`, `criterion_ids`,
   and terminal ledger path in `.sweetclaude/state/large-story.yaml` or
   `.sweetclaude/state/workflows/{workflow_id}.yaml`.
4. Run `validate-workflow --stage define-exit` before Plan, Design,
   Implementation Prep, Implementation, Verify, review, release, or caucus
   completion evaluation.
5. At completion, write `success-criteria-ledger.json` and run
   `validate-workflow --stage completion` before any `done` transition.

## Success Criteria Contract Controls

Large/high-rigor story workflows must begin with a frozen
`success_criteria_contract` before downstream planning, design, test writing,
implementation, review, release, or caucus completion evaluation starts.

The contract must record:

- a stable story/workflow id;
- binary `criterion_ids`;
- one measurable pass condition and one measurable fail condition per criterion;
- the expected evidence artifact, evidence owner, and evidence freshness rule
  for each criterion;
- a `success_criteria_contract_hash` computed after the contract is frozen.

The contract is not valid if any criterion depends on open-ended judgment such
as "looks good", "adequate", "comprehensive", "SOTA", "properly done", or
"reviewer approved" without a concrete binary measurement.

Runtime validation must use:

```bash
python3 scripts/success_criteria_contracts.py validate-contract --contract .sweetclaude/contracts/success-criteria-contract.yaml
```

The canonical workflow-facing command is:

```bash
python3 scripts/success_criteria_contracts.py validate-workflow --stage define-exit
```

Workflow orchestrator exits for large/high-rigor work must include the
`success_criteria_contract_valid` check before downstream planning or
implementation begins.

Use `--workflow-id` when validating a stored orchestrator workflow, or explicit
`--contract`/`--ledger` paths when validating non-standard artifact locations.

The validator computes `success_criteria_contract_hash` from canonical contract
content excluding the declared hash field, so post-freeze contract edits fail as
stale.

Every downstream phase must preserve the frozen contract path,
`success_criteria_contract_hash`, and `criterion_ids`. A downstream phase may
produce a `criteria-amendment-request.yaml`, but it may not silently change the
contract or treat new concerns as completion blockers.

Implementation completion requires `success-criteria-ledger.json`. The ledger
must evaluate every frozen criterion id against accepted evidence and expose one
binary outcome: `all_success_criteria_passed == true` or `false`.

Runtime completion validation must use:

```bash
python3 scripts/success_criteria_contracts.py validate-ledger --contract .sweetclaude/contracts/success-criteria-contract.yaml --ledger .sweetclaude/reports/success-criteria-ledger.json
```

The canonical workflow-facing completion command is:

```bash
python3 scripts/success_criteria_contracts.py validate-workflow --stage completion
```

Workflow orchestrator completion exits for large/high-rigor work must include
`success_criteria_completion_valid` or `success_criteria_ledger_valid`.
Manual `status.py set-terminal --status done` paths for work flagged with
`requires_success_criteria_contract`, `success_criteria_contract`, or
`success_criteria_contract_path` must fail closed until completion validation
passes; `--allow-missing-evidence` may waive the generic receipt requirement,
but it must not bypass the success-criteria ledger gate.

Each ledger criterion entry must include `status: pass`, the frozen
`success_criteria_contract_hash`, the contract-declared `evidence_artifact` and
`evidence_owner`, and `evidence_fresh: true` or equivalent current freshness.

No review, caucus, verification, release, or completion step may add completion
criteria. If a reviewer finds a real issue outside the frozen criteria, route it
to backlog, a criteria amendment request, a split story, or human escalation.

No completion claim is valid when the contract is missing, the hash is stale,
any frozen criterion is missing from the ledger, any criterion fails, or any
criterion is unevaluated.

## Default Limits

Without explicit user approval, the defaults are:

- one three-reviewer caucus per budget window;
- maximum two caucus rounds for the same story or step;
- maximum one blocking caucus failure before contract reopen or user decision;
- maximum two WLF/process-failure records for the same story or step before
  contract reopen or user decision;
- maximum one adversarial pass-state bypass before human decision;
- no background implementer or reviewer dispatch while a process stop is active.

## Hard Stops

Stop immediately and ask the user before more subagent/caucus/patch work when:

- caucus rounds exceed the approved budget;
- reviewer-agent count exceeds the approved budget;
- a second blocking caucus failure occurs for the same story or step;
- WLF/process-failure count exceeds the approved limit;
- repeated adversarial pass-state bypasses are found;
- the story or step contract keeps expanding during correction;
- failure recording becomes part of a patch-test-recaucus loop;
- the process-control ledger is missing, stale, or contradictory.

## Resume Requirements

Resume after a hard stop requires all of:

- explicit human approval;
- a fresh budget window;
- a revised story/step contract or split-story plan when drift repeated;
- current process-control ledger;
- a recorded stop disposition explaining why continuation is bounded.

## Caucus Rules

Caucus/reviewer agents are read-only judges unless the user explicitly assigns
a separate write task. Their output may not mark work complete. A caucus may
answer only the approved question against the approved contract.

If a caucus finds a blocker, the next correction must either:

- tighten a deterministic guard, fixture, schema, hook, or controller check; or
- classify the issue as human-review-only with rationale; or
- stop for contract reopen.

Do not spawn another caucus merely because the previous caucus found a new
problem. The process-control ledger must show available budget and stop-rule
clearance first.
