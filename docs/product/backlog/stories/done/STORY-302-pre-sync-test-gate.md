---
id: STORY-302
type: story
title: "Pre-sync test validation gate"
status: done
completed: 2026-05-18
priority: now
effort: s
epic: EP-010
epic_sequence: 3
tags: [self-hosting, hooks, sync, testing]
created: 2026-05-18
updated: 2026-05-18
---

# Pre-sync test validation gate

As a SweetClaude developer syncing changes to the installed path, I want the sync script to run the hook test suite before copying so that a hook with failing tests can never reach the installed path.

## Context

`tests/test-hooks.sh` tests hooks in isolation using fixture environments. This gate ensures that only tested hooks are synced. Combined with STORY-300 (phase gate) and STORY-301 (backup), this creates a three-layer defense: don't sync during IMPLEMENT, test before syncing, and back up before overwriting.

The `--force` flag from STORY-300 bypasses the phase check but NOT the test gate. A developer can force a sync outside the IMPLEMENT phase, but cannot sync hooks that fail tests. If tests themselves are wrong, they must be fixed first — this is the one non-overridable gate.

## Objective success criteria

| # | Criterion | Verification |
|---|---|---|
| 302-1 | Sync runs `tests/test-hooks.sh` before copying | Capture sync output → contains test-hooks.sh output |
| 302-2 | Test failure blocks sync | Introduce failing test, run sync → non-zero exit, installed hooks unchanged |
| 302-3 | `--force` does NOT bypass test gate | With `phase: verify` + failing test, `--force` still blocks with test output |
| 302-4 | Test success allows sync to proceed | All tests pass → sync completes, exit code 0 |
