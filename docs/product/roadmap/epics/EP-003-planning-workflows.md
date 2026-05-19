---
id: EP-003
type: epic
title: "Planning Workflows"
status: new
release: REL-003
objective: "Planning workflow types (new-feature-area, course-correction, release-planning) are implemented with their own state models and gate requirements."
completion_criteria:
  - "Planning workflow types defined"
  - "Design consensus reached"
  - "Technical spec approved"
  - "Planning workflow state model implemented"
  - "All 3 planning workflow types implemented"
  - "Code and security review complete"
  - "Behavioral regression suite passing"
  - "Docs and changelog updated"
completion_criteria_done: []
depends_on:
  - EP-001
created: 2026-05-15
updated: 2026-05-15
---

## Description

Adds planning workflow types to the workflow engine built in EP-001. Planning workflows produce stories and epics; execution workflows (EP-001) implement them. Shares the workflow state model infrastructure with EP-001 (DEC-27).

## Source milestones

Completion criteria drawn from MS-026 through MS-033. No contributing work items assigned yet.
