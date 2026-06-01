# Large Story State Schema

Maintain state in `.sweetclaude/state/large-story.yaml` or
`.sweetclaude/state/workflows/{workflow_id}.yaml`.

```yaml
schema_version: 1
workflow_id: string
status: defining | waiting_for_user | ready_for_downstream | active | blocked | complete
current_stage: define-exit | downstream-not-productized | completion

requires_success_criteria_contract: true
success_criteria_contract_path: string | null
success_criteria_contract_hash: string | null
criterion_ids:
  - string
success_criteria_ledger_path: string | null

human_gate:
  required: boolean
  reason: string | null
```
