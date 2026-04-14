---
description: "Design the user experience: wireframes, interaction patterns, navigation, user flows. Wraps bmad:create-ux-design."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# UX Design

Design the user experience for: $ARGUMENTS

## SweetClaude Context

- Reference personas from `product/discovery` if they exist
- Reference user workflows from `product/user-workflows` if they exist
- Save output to `specs/ux-design.md` in `.sweetclaude/`

## Execute

Invoke `bmad:create-ux-design` and follow its workflow.
