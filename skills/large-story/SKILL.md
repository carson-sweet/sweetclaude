---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Internal bounded, evidence-gated large-story workflow."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:large-story" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Large Story

Internal SweetClaude 4.x workflow for complete large/high-rigor story
workflows. Users start this through `/sweetclaude:go` using natural language.

This workflow is bounded, evidence-gated, and human-approved at explicit gates.
It must not delegate entrypoint authority to any other workflow.

## Scope

Use this workflow when a work item is too large or high-risk for a single
bounded `/sweetclaude:code-feature`, `/sweetclaude:code-issue`, or
`/sweetclaude:code-tdd` pass.

## Current Product Surface

This Slice 0 surface defines the production start/resume contract. Later slices
will implement the full downstream workflow.

On start or resume, maintain large-story state in
`.sweetclaude/state/large-story.yaml` or
`.sweetclaude/state/workflows/{workflow_id}.yaml`.

Required state fields:

- `workflow_id`
- `requires_success_criteria_contract: true`
- `success_criteria_contract_path`
- `success_criteria_contract_hash`
- `criterion_ids`
- `success_criteria_ledger_path`

## Entry Gate

Before planning, design, implementation, review, release, or caucus completion
evaluation starts:

1. Define the story objective.
2. Define expected outcomes.
3. Define non-goals.
4. Create or locate a frozen `success_criteria_contract`.
5. Run `python3 scripts/success_criteria_contracts.py validate-workflow --stage define-exit`.
6. If validation fails, stop. Do not continue downstream.
7. If validation passes, store the required state fields and stop until the
   next productized slice is implemented.

## Completion Authority

Completion is valid only when `success-criteria-ledger.json` evaluates every
frozen criterion and reports `all_success_criteria_passed == true`.

No review, caucus, verification, release, or completion step may add completion
criteria. New concerns route to backlog, amendment request, split story, or
human escalation.
