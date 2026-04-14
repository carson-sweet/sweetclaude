---
description: "Plan a sprint by selecting stories from the backlog, estimating scope, and producing a sprint commitment. Wraps bmad:sprint-planning."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Sprint Plan

Plan a sprint for: $ARGUMENTS

## SweetClaude Context

- Pull candidate stories from `stories/` and `product/backlog`.
- Respect scope boundaries from `product/manage-scope`.
- No time estimates. Scope by artifact count and complexity, not calendar days.

## Execute

Invoke `bmad:sprint-planning` and follow its workflow.
