---
id: CHORE-001
type: chore
title: Fix session-preflight.sh on feat/v4-phase1-backlog to use [12]$ schema check
status: done
priority: soon
effort: s
epic: null
milestone: null
sprint: null
tags: [v4, preflight, merge-blocker]
origin: manual
created: 2026-05-13
updated: 2026-05-13
closed_date: 2026-05-13
resolved_by: "Merge main into feat/v4-phase1-backlog (2026-05-13). The [12]$ pattern from 3.68.1 replaced the broken 2-only check that v4 had carried."
---

## Description

`feat/v4-phase1-backlog` contains a copy of `session-preflight.sh` that has the wrong schema_version check: it checks for `schema_version: 2` only (the broken intermediate fix from the v4 session). The correct fix (`[12]$`) shipped in 3.68.1 via `fix/session-preflight-schema-version`.

This chore must be resolved before `feat/v4-phase1-backlog` merges to main. If it merges without this fix, the `2`-only check re-enters main and breaks all users on schema_version: 1 again.

## Acceptance Criteria

- [ ] `feat/v4-phase1-backlog` session-preflight.sh line 127 uses `^schema_version:[[:space:]]*[12]$` (matching main's 3.68.1 fix)
- [ ] No other Step in that branch's preflight adds a new schema_version-version-specific check that would need updating

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
