---
description: "Produce a technical specification: detailed design, data structures, algorithms, error handling, edge cases. Wraps bmad:tech-spec."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Tech Spec

Produce a technical specification for: $ARGUMENTS

## SweetClaude Context

- Build on architecture doc if one exists in `specs/architecture.md`
- Save output to `specs/tech-spec.md` in `.sweetclaude/`
- Record key decisions via `design/manage-decisions`

## Execute

Invoke `bmad:tech-spec` and follow its workflow.
