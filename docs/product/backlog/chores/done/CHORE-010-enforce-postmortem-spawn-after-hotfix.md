---
closed_date: '2026-05-15'
created: 2026-05-15
effort: s
epic: null
id: CHORE-010
milestone: null
origin: discovery
priority: soon
sprint: null
status: done
tags:
- hotfix
- postmortem
- workflow
- enforcement
- something-broke
- deploy-ship
title: Enforce POST-MORTEM spawn after hotfix SHIP
type: chore
updated: 2026-05-15
---

## Description

`phase-gates.md` marks POST-MORTEM as required (not optional) after `hotfix` SHIP. Neither `something-broke` nor `deploy-ship` currently create or surface a POST-MORTEM work item after a hotfix closes. The omission means post-incident analysis silently doesn't happen.

## Done when

- `something-broke` and/or `deploy-ship`, when completing a hotfix flow, prompt the user to create a POST-MORTEM backlog item
- If the user confirms, a new `BUG` or `CHORE` item is written with type `post-mortem` and linked to the originating hotfix
- If the user declines, the skip is logged to the story's decision log section

## Source

Identified in `docs/internal/41-discovery-2026-05-15.md` §3.5 during MS-006 discovery.
