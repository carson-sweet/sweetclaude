---
id: STORY-306
type: story
title: "Fixture-based hook development workflow documentation"
status: deferred
priority: now
effort: s
epic: EP-010
epic_sequence: 7
tags: [self-hosting, hooks, documentation]
created: 2026-05-18
updated: 2026-05-18
---

# Fixture-based hook development workflow documentation

As a SweetClaude developer working on hooks, I want a documented workflow for developing and testing hooks without syncing to the installed path so that I can iterate safely during implementation.

## Context

The primary hook development workflow avoids the self-hosting deadlock entirely by never syncing during implementation. Hooks are tested against fixture environments (the same approach `test-hooks.sh` uses) and against real inputs via manual invocation. The sync to installed happens only during the SHIP phase, after all tests pass. This workflow exists implicitly today — this story makes it explicit and documented.

## Objective success criteria

| # | Criterion | Verification |
|---|---|---|
| 306-1 | `docs/user-guide/hook-development.md` exists and is tracked by git | `git ls-files docs/user-guide/hook-development.md` returns the path |
| 306-2 | Covers logic testing with `CLAUDE_FILE_PATH` / `CLAUDE_TOOL_NAME` env vars | `grep "CLAUDE_FILE_PATH" docs/user-guide/hook-development.md` |
| 306-3 | Covers regression testing via `tests/test-hooks.sh` | `grep "test-hooks.sh" docs/user-guide/hook-development.md` |
| 306-4 | Covers sync timing (SHIP phase only) | `grep -i "ship" docs/user-guide/hook-development.md` |
| 306-5 | Cross-references recovery procedure from STORY-304 | `grep -i "recovery\|hook-repair" docs/user-guide/hook-development.md` |
