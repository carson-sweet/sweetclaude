---
id: STORY-015
type: story
title: planning-concepts.md model enforcement — status state machine and hierarchy
  in skills
status: new
priority: soon
effort: m
epic: EP-001
sprint: null
tags:
- planning-concepts
- status
- state-machine
- hierarchy
- enforcement
- v4-phase2
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
epic_sequence: 3
---

## Description

As a SweetClaude user, I want skills to enforce the planning hierarchy and status state machine documented in `planning-concepts.md`, so that invalid state transitions are caught at authoring time rather than discovered when `big-picture` produces incoherent output.

**Reference:** `docs/user-guide/planning-concepts.md` defines:
- The planning hierarchy: strategy → milestones → epics → stories/backlog
- Valid status values per artifact type (milestone: proposed/active/achieved/dropped/superseded; story: new/active/done/abandoned)
- State machine transitions: what changes are valid from each state
- The rule that an item can only move to `active` if its parent is `active`

**The gap today:** `planning-concepts.md` is authoritative documentation but is not enforced by any skill. A user can set a story to `done` while its parent epic is `proposed`. A user can create an active milestone with no stories. These are not errors that crash anything — they are silent incoherence that causes `big-picture` to display meaningless roll-ups.

### Enforcement points

1. **Status transition validation** — when a skill updates a story/epic/milestone status, validate the transition against the state machine. Invalid transition: warn with the valid next states; do not silently apply it.

2. **Hierarchy coherence check** — when marking an item `active`, check that its parent is also `active` (or that it has no parent). If parent is not active, surface a prompt: "Epic EP-003 is not active — mark it active first, or confirm you want to proceed."

3. **Done-propagation prompt** (from STORY-002, coordinated) — when closing the last open story in an epic, prompt to close the epic. When closing the last epic in a milestone, prompt to close the milestone.

4. **`_health` lint rule** — add a lint check that flags: active epics with all stories done, active milestones with all epics done, stories with status not in the canonical set for their type.

### Relationship to STORY-002

STORY-002 covers canonical vocabulary and renderer hardening. This story covers state machine enforcement at write-time. They are complementary: STORY-002 fixes how the system reads and displays status; this story fixes how the system prevents invalid status from being written.

## Acceptance Criteria

- [ ] Attempting to set a story to `done` via a skill while in `new` state (skipping `active`) produces a warning with valid transitions listed
- [ ] Attempting to set a story to `active` while its parent epic is `proposed` produces a prompt asking to activate the epic first
- [ ] Closing the last open story in an epic prompts the user to close the epic in the same turn
- [ ] `sweetclaude:_health` flags: active epics with 100% done stories; active milestones with 100% done epics; unknown status values
- [ ] All enforcement points are documented in `docs/user-guide/planning-concepts.md` in a "Enforcement" section

## Out of scope

- Hard blocking (transitions that are merely warned on today can be blocked in a future release after user feedback)
- Retroactive correction of existing project state (lint flags, but does not auto-fix without user direction)

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
