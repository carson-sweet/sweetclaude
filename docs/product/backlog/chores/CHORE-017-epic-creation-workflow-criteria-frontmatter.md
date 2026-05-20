---
id: CHORE-017
type: chore
title: Epic creation workflow produces completion_criteria in frontmatter
status: new
priority: later
effort: xs
epic: null
epic_sequence: null
milestone: null
sprint: null
tags: [roadmap, epics, creation-workflow, frontmatter, cache]
origin: BUG-009
created: 2026-05-19
updated: 2026-05-19
closed_date: null
---

## Description

When an epic is created (via caucus output, manual draft, or any creation workflow), its `completion_criteria` and `completion_criteria_done` fields should be present in frontmatter. The cache only reads frontmatter — success criteria in the markdown body are invisible to it and produce `Criteria: 0/0` in big-picture output.

## Context

BUG-009 fixed the immediate problem by adding `completion_criteria` frontmatter to EP-009 and adding a Rule 6 health lint to warn when frontmatter is missing. This chore addresses the root cause: the creation workflow itself does not produce the required frontmatter.

Rule 6 provides sufficient mitigation for existing epics. This chore ensures new epics are created correctly in the first place.

## Acceptance criteria

- [ ] Epic creation workflow (caucus prompt or skill) includes `completion_criteria: []` and `completion_criteria_done: []` in the frontmatter template
- [ ] A note in the epic schema or creation docs explains that criteria must be in frontmatter, not the body
