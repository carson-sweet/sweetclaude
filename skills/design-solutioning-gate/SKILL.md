---
description: "Validate the proposed solution before implementation. Checks architecture decisions, identifies risks, confirms design addresses requirements. Wraps bmad:solutioning-gate-check."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Solutioning Gate

Validate the proposed solution for: $ARGUMENTS

## SweetClaude Context

- Check architecture and tech spec against PRD requirements
- Find risks and gaps before implementation starts
- Record gate results in decision log
- This is a quality gate. Challenge the design.

## Execute

Invoke `bmad:solutioning-gate-check` and follow its workflow.
