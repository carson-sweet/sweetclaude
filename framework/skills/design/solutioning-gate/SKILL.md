---
name: sweetclaude-design-solutioning-gate
description: "Validate the proposed solution before implementation. Checks architecture decisions, identifies risks, confirms design addresses requirements. Wraps bmad:solutioning-gate-check."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Solutioning Gate

Validate the proposed solution for: $ARGUMENTS

## SweetClaude Context

- Check architecture and tech spec against PRD requirements
- Identify risks and gaps before implementation begins
- Record gate results in decision log
- This is a quality gate — do not rubber-stamp. Challenge the design.

## Execute

Invoke `bmad:solutioning-gate-check` and follow its workflow.
