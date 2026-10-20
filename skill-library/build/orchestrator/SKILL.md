---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Orchestrator main loop — executes tracked workflow steps via subagents."
---



<preflight-state>
!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh sweetclaude`
</preflight-state>

# Orchestrator

Thin dispatcher for the orchestrator main loop. Delegates all logic to `scripts/orchestrator_loop.py`.

## Step 0: Validate entry

Read the pre-loaded state above. If it shows `STATE_NOT_FOUND` or `work.active` is null/missing, stop:

> No active work item. The orchestrator requires an active work item in `sweetclaude.yaml`. Use `/sweetclaude:go` to pick up work first.

Extract from the pre-loaded state:
- `workflow_id` = `work.active.id`
- `deference_level` = `deference` (default: `collaborative`)

## Step 1: Crash recovery check

```bash
python3 -c "
import json, sys, os
sys.path.insert(0, os.path.join(os.environ.get('CLAUDE_PLUGIN_ROOT', ''), 'scripts'))
from orchestrator import find_active_workflows
result = find_active_workflows('.')
print(json.dumps(result))
" 2>/dev/null
```

If the result contains an active workflow matching `workflow_id`:
- Present via AskUserQuestion:
  - **Resume** (Recommended) — "Continue from checkpoint: {checkpoint}"
  - **Abandon** — "Abort the workflow and clear active work"
  - **Ignore for now** — "Pause the workflow, return to normal mode"
- If Resume: proceed to Step 2
- If Abandon: run the abort flow (Step 4, action=abort) and stop
- If Ignore: output "Workflow paused." and stop

If no active workflow found for this `workflow_id`, this is a new workflow — proceed to Step 2.

## Step 2: Run main loop

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator_loop.py run \
  --workflow-id "{workflow_id}" \
  --project-dir "." \
  --deference-level "{deference_level}" \
  2>/dev/null
```

Parse the JSON output. If the command fails or produces no output, report:
> Orchestrator loop failed unexpectedly. Check `.sweetclaude/state/workflows/{workflow_id}.yaml` for state.

## Step 3: Handle yield

The loop returns a JSON object with `reason`, `step_id`, and `payload`. Handle each reason:

### reason: execute_step

The loop has reached a step whose work must be performed by a subagent. The Python loop cannot spawn one itself — this is where you, the model, are the runtime.

**If `payload.parallel` is present** this is a fan-out step. Spawn every child in the list concurrently (one subagent each, using its `agent`/`subagent_type`/`model`, writing to its `output_path`). Wait for all of them, then resume with `{"action": "executed"}`. The loop validates the `join` policy (`all` = every child artifact present and non-empty; `any` = at least one) and advances or fails accordingly. Skip the single-step instructions below.

**If `payload.verify` is present** this is an adversarial-verify step. Spawn `verify.count` independent verifiers (using `verify.agent`/`subagent_type`/`model` and `verify.instruction`), each writing a `confirmed` or `refuted` verdict to its slot's `output_path`. Relay the verdicts when you resume: `{"action": "executed", "verdicts": ["confirmed", "refuted", "confirmed"]}` (or let each verifier write `signal: confirmed|refuted` frontmatter and resume with just `{"action": "executed"}`). The loop tallies affirm votes against `verify.threshold` (`majority`/`all`/`any`/integer) and emits a `confirmed` or `refuted` signal that your `routing` consumes. Skip the single-step instructions below.

Otherwise (single step):

1. Spawn a subagent using the `payload`:
   - `agent` — the role to assume (maps to an `agents/{agent}.md` definition where one exists)
   - `subagent_type` — the agent type to launch
   - `model` — the model to run it on
   - `input_paths` — files the subagent may read as input
   - `output_path` — where the subagent MUST write its output artifact (if non-null)
   - `prompt` — the assembled instruction to pass through
   - `output_schema` — when non-null, the contract the subagent's result must satisfy (e.g. `signal.enum` lists the only valid signal values)
2. Wait for the subagent to finish and confirm the artifact exists at `output_path` (when one is specified).
3. Resume with `{"action": "executed"}` (Step 4). When `output_schema` is present, relay the subagent's chosen signal: `{"action": "executed", "signal": "<value>"}` — it must be one of the schema's allowed values. A relayed signal takes precedence over scraping the artifact; if you omit it, the loop falls back to reading the signal from the artifact frontmatter. The loop re-enters, validates the artifact and signal, routes, and advances.

Do not skip the subagent and write the artifact yourself — the point is the isolated subagent context. If the user wants to stop instead, resume with `{"action": "abort"}`.

### reason: gate

Present via AskUserQuestion:
- Header: "Gate: {payload.gate_type}"
- **Approve** (Recommended) — "Accept the output and continue"
- **Iterate** — "Route back to the previous step for another pass"
- **Abort** — "Stop the workflow"

Feed the user's choice to Step 4.

### reason: failure

Present via AskUserQuestion:
- Header: "Step failed"
- Show: "Step '{step_id}' failed: {payload.error}"
- **Retry** (Recommended) — "Re-run this step (stale output will be cleaned)"
- **Skip** — "Skip this step and advance"
- **Abort** — "Stop the workflow"

Feed the user's choice to Step 4.

### reason: escalation

Present via AskUserQuestion:
- Header: "Escalation"
- Show: "Step '{step_id}' raised escalation signal '{payload.signal}'"
- **Acknowledge** (Recommended) — "Acknowledge and continue"
- **Abort** — "Stop the workflow"

Feed the user's choice to Step 4.

### reason: max_iterations

Present via AskUserQuestion:
- Header: "Max iterations"
- Show: "Step '{step_id}' has reached the maximum iteration count."
- **Reset** (Recommended) — "Reset the counter and continue the loop"
- **Skip** — "Skip this step and advance"
- **Abort** — "Stop the workflow"

Feed the user's choice to Step 4.

### reason: budget_exhausted

The workflow hit its configured budget (`payload.limit` is `max_steps` or `max_tokens`; `payload.spent` shows the tally).

Present via AskUserQuestion:
- Header: "Budget exhausted"
- Show: "The workflow reached its {payload.limit} budget ({payload.spent})."
- **Reset** (Recommended) — "Clear the budget counters and continue"
- **Abort** — "Stop the workflow"

On Reset, feed `{"action": "reset"}` to Step 4, then return to **Step 2** to run the loop again. On Abort, feed `{"action": "abort"}`.

When relaying step completion you may report spend so the token budget is tracked: `{"action": "executed", "tokens": <output-tokens-spent>}`.

### reason: complete

Output:
> Workflow **{workflow_id}** completed successfully.

Stop. Do not continue to Step 4.

### reason: halted

Output:
> Workflow **{workflow_id}** has been halted.

Stop. Do not continue to Step 4.

## Step 4: Resume loop

Map the user's AskUserQuestion selection to an action:
- "Executed" → `{"action": "executed"}`
- "Approve" → `{"action": "approve"}`
- "Iterate" → `{"action": "iterate"}`
- "Retry" → `{"action": "retry"}`
- "Skip" → `{"action": "skip"}`
- "Abort" → `{"action": "abort"}`
- "Reset" → `{"action": "reset"}`
- "Acknowledge" → `{"action": "acknowledge"}`

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator_loop.py resume \
  --workflow-id "{workflow_id}" \
  --project-dir "." \
  --deference-level "{deference_level}" \
  --decision-json '{"action": "{action}"}' \
  2>/dev/null
```

Parse the JSON output and return to Step 3. Repeat until reason is `complete` or `halted`.
