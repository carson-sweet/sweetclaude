---
description: "Write user stories with acceptance criteria from features or epics. Wraps bmad:create-story with SweetClaude context."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# User Story

Write a user story for: $ARGUMENTS

## SweetClaude Context

- Stories follow As-a/I-want/So-that format with testable acceptance criteria.
- Each acceptance criterion converts to a Gherkin Given/When/Then scenario.
- Save to `stories/EPIC-XXX/` in `.sweetclaude/`.
- Update `traceability/requirements-map.md`.

## Execute

1. Invoke `bmad:create-story` and follow its workflow.
2. After the story file is written, prompt for milestone assignment:

   > "Assign this story to a milestone? Current milestones:
   > - {list active + proposed milestones from `docs/milestones/`}
   > - none / later (skip for now)"

   If the user selects a milestone, invoke `sweetclaude:milestones link <US-XXX> <MS-XXX>` — do not write the `**Milestone:**` header directly; delegate to keep the bidirectional link consistent.

   If no milestones exist, skip this step and mention: "No milestones yet. Run `/sweetclaude:milestones add` to create one."
