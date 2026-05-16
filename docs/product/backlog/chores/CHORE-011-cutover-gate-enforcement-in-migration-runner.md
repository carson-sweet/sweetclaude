---
id: CHORE-011
type: chore
title: CUTOVER gate enforcement in migration runner
status: new
priority: later
effort: s
epic: null
milestone: null
sprint: null
tags: [migration, cutover, gate, enforcement, runner]
origin: discovery
created: 2026-05-15
updated: 2026-05-15
closed_date: null
---

## Description

The `technology-migration` work type has a hard gate at CUTOVER requiring an explicit human decision logged to the decision log before traffic or data switches from old system to new. The migration runner (`scripts/migrations/runner.py`) currently executes cutover mechanics without requiring this confirmation. The gate is defined in `phase-gates.md` but not enforced in code.

## Done when

- The migration runner, before executing any cutover step, checks for a logged cutover decision (in decision log or passed as CLI flag)
- If no logged decision exists, the runner stops and prompts for explicit confirmation before continuing
- The confirmation and timestamp are written to the decision log or to a runner-managed record

## Source

Identified in `docs/internal/41-discovery-2026-05-15.md` §3.6 during MS-006 discovery.
