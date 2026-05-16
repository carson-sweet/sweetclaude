---
id: EP-004
type: epic
title: "Mode Enforcement"
status: new
release: REL-004
objective: "Flow, kanban, shape up, and agile modes enforce distinct behavioral rules across all skills, with mode-appropriate routing, gating, and artifact management."
completion_criteria:
  - "Discovery complete"
  - "Mode-workflow mapping designed"
  - "Design consensus reached"
  - "Technical spec approved"
  - "Mode enforcement implemented in workflow state model"
  - "All 4 modes implemented"
  - "Code and security review complete"
  - "Behavioral regression suite passing"
  - "Docs and changelog updated"
completion_criteria_done: []
depends_on:
  - EP-001
  - EP-003
created: 2026-05-15
updated: 2026-05-15
---

## Description

The constraint layer for SweetClaude v4.4. Each mode (flow, kanban, shape up, agile) defines which skills are available, which gates apply, and how routing works. Requires both the execution workflow engine (EP-001) and planning workflows (EP-003) to exist first.

## Source milestones

Completion criteria drawn from MS-034 through MS-042. Contributing work items: STORY-013.
