---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Orchestrator main loop — executes tracked workflow steps via subagents."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:orchestrator" 2>/dev/null || true`

<preflight-state>
!`cat .sweetclaude/state/sweetclaude.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`
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
sys.path.insert(0, os.path.expanduser('~/.claude/scripts/sweetclaude'))
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
python3 ~/.claude/scripts/sweetclaude/orchestrator_loop.py run \
  --workflow-id "{workflow_id}" \
  --project-dir "." \
  --deference-level "{deference_level}" \
  2>/dev/null
```

Parse the JSON output. If the command fails or produces no output, report:
> Orchestrator loop failed unexpectedly. Check `.sweetclaude/state/workflows/{workflow_id}.yaml` for state.

## Step 3: Handle yield

The loop returns a JSON object with `reason`, `step_id`, and `payload`. Handle each reason:

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
- "Approve" → `{"action": "approve"}`
- "Iterate" → `{"action": "iterate"}`
- "Retry" → `{"action": "retry"}`
- "Skip" → `{"action": "skip"}`
- "Abort" → `{"action": "abort"}`
- "Reset" → `{"action": "reset"}`
- "Acknowledge" → `{"action": "acknowledge"}`

```bash
python3 ~/.claude/scripts/sweetclaude/orchestrator_loop.py resume \
  --workflow-id "{workflow_id}" \
  --project-dir "." \
  --deference-level "{deference_level}" \
  --decision-json '{"action": "{action}"}' \
  2>/dev/null
```

Parse the JSON output and return to Step 3. Repeat until reason is `complete` or `halted`.
