# State File Schema

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

success_criteria_contract:
  path: string | null
  success_criteria_contract_hash: string | null
  criterion_ids:
    - string
  criteria_amendment_requests:
    - path: string
      status: proposed | approved | rejected | routed

success_criteria_ledger:
  path: string | null
  evaluated_contract_hash: string | null
  all_success_criteria_passed: boolean | null
  missing_or_failed_criterion_ids:
    - string

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

process_control:
  budget_approved: boolean
  max_caucus_rounds_per_step: integer
  max_reviewer_agents_per_budget: integer
  max_blocking_caucus_failures_per_step: integer
  max_process_failures_before_gate: integer
  active_stop_disposition: string | null
  human_resume_approved: boolean
  steps:
    STEP_ID:
      caucus_rounds_used: integer
      reviewer_agents_used: integer
      blocking_caucus_failures: integer
      process_failure_count: integer
      adversarial_pass_state_bypasses: integer

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
