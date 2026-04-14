---
name: product/prd
description: "Produce a full PRD with functional requirements, non-functional requirements, epics, and traceability. Wraps bmad:prd with SweetClaude context."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# PRD

Produce a Product Requirements Document for: $ARGUMENTS

## SweetClaude Context

- Build on the product brief if one exists in `specs/product-brief.md`
- Each FR must have testable acceptance criteria
- Each success criterion must be evaluable as true/false post-ship
- Save output to `specs/prd.md` in `.sweetclaude/`

## Execute

Invoke `bmad:prd` and follow its workflow.
