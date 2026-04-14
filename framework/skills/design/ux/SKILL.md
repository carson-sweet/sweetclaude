---
name: sweetclaude-design-ux
description: "Design the user experience: wireframes, interaction patterns, navigation, user flows. Wraps bmad:create-ux-design."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# UX Design

Design the user experience for: $ARGUMENTS

## SweetClaude Context

- Reference personas from `product/discovery` if they exist
- Reference user workflows from `product/user-workflows` if they exist
- Save output to `specs/ux-design.md` in the working repo

## Execute

Invoke `bmad:create-ux-design` and follow its workflow.
