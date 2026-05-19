---
id: STORY-018
type: story
title: Story phase-status table — per-phase status, blocking reason, and primary workfile
status: new
priority: soon
effort: m
epic: EP-001
sprint: null
tags:
- stories
- status
- phases
- traceability
- developer-ux
origin: manual
created: 2026-05-14
updated: 2026-05-15
closed_date: null
epic_sequence: 2
---

## Description

As a developer using SweetClaude, I want to ask about the current status of any story across all applicable phases, so that I can see at a glance what has been done, what is in progress, what is blocked, and what has been skipped — without manually hunting across files and directories.

The output is a markdown table with one row per phase applicable to the story's work type. For phases the story's workflow template does not include, the status is `n/a`.

## Acceptance Criteria

- [ ] A `sweetclaude:story-status <STORY-ID>` invocation (or equivalent routing via `sweetclaude:go`) produces a markdown table
- [ ] Table columns: `Phase`, `Status`, `Notes`, `Primary Workfile`
- [ ] Valid phase status values: `not started` / `open` / `blocked` / `on hold` / `complete` / `deferred` / `abandoned` / `n/a`
- [ ] `n/a` is used when the story's workflow template does not include that phase
- [ ] `Primary Workfile` is the full path to the main artifact for that phase (e.g., ADR file, design doc, feature file, PR link), or `—` if none exists yet
- [ ] Phase list covers all phases defined in `config/workflow-templates.yaml` for the story's work type
- [ ] Status is derived from file existence and frontmatter — not from free-form notes
- [ ] If the story file itself cannot be located, the skill returns a clear error (not a silent empty table)
- [ ] Output is valid GitHub-flavored markdown renderable inline in the terminal

## Out of Scope

- Bulk status tables across multiple stories (separate roadmap/health skill)
- Editing phase status directly from this command

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
