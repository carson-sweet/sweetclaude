---
name: design-architecture
description: "Define system architecture: components, boundaries, communication patterns, data flow, key decisions. Wraps bmad:architecture."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Architecture

Design the system architecture for: $ARGUMENTS

## SweetClaude Context

- Build on the PRD if one exists in `specs/prd.md`
- Record key decisions via `design/manage-decisions`
- Save output to `specs/architecture.md` in `.sweetclaude/`
- Run `design/change-impact-analysis` if modifying an existing architecture

## Execute

Invoke `bmad:architecture` and follow its workflow.
