---
id: CHORE-013
type: chore
title: "Wire tests/hooks/*.sh into the pre-sync test gate"
status: new
priority: later
effort: s
epic: EP-010
tags: [self-hosting, sync, testing, gate]
created: 2026-05-19
updated: 2026-05-19
---

# Wire tests/hooks/*.sh into the pre-sync test gate

## Context

`scripts/sync-to-installed.sh` runs `bash tests/test-hooks.sh` as its pre-sync gate (line 103). The 8 existing scripts in `tests/hooks/` are not invoked by the gate — they run orphaned, manually only. `tests/hooks/test-emergency-restore.sh` (added by STORY-304) has the same problem.

## Work

Update `tests/test-hooks.sh` to invoke all `tests/hooks/*.sh` scripts (or update `sync-to-installed.sh` to glob `tests/hooks/`), so every hook test runs automatically before any sync.

## Acceptance criteria

- `bash tests/test-hooks.sh` invokes all scripts in `tests/hooks/`
- A failure in any `tests/hooks/*.sh` blocks the sync with a non-zero exit
- Existing test output format is preserved
