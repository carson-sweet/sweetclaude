---
id: STORY-303
type: story
title: "Extend test-hooks.sh coverage to TDD-sensitive hooks"
status: done
priority: now
effort: m
epic: EP-010
epic_sequence: 4
tags: [self-hosting, hooks, testing]
created: 2026-05-18
updated: 2026-05-19
---

# Extend test-hooks.sh coverage to TDD-sensitive hooks

As a SweetClaude developer modifying TDD enforcement hooks, I want `test-hooks.sh` to cover `test-guardian.sh` and `auto-test-runner.sh` so that the pre-sync test gate (STORY-302) can catch regressions in the hooks most likely to cause a self-hosting deadlock.

## Context

`tests/test-hooks.sh` currently tests only `drift-gate.sh` and `master-preflight.sh` (277 lines, fixture-based with isolated HOME and git repo). The two hooks that create the self-hosting deadlock risk — `test-guardian.sh` (blocks test file edits during TDD) and `auto-test-runner.sh` (runs tests after source edits during TDD) — have no automated test coverage. Without this, the pre-sync test gate from STORY-302 cannot catch regressions in the most critical hooks.

## Objective success criteria

| # | Criterion | Verification |
|---|---|---|
| 303-1 | test-guardian: phase inactive → `{"ok": true}` | Test case exists and passes |
| 303-2 | test-guardian: phase active + implementing + test file → `{"ok": false}` | Test case exists and passes |
| 303-3 | test-guardian: phase active + implementing + non-test file → `{"ok": true}` | Test case exists and passes |
| 303-4 | test-guardian: phase active + non-implementing tdd_phase → `{"ok": true}` | Test case exists and passes |
| 303-5 | auto-test-runner: phase inactive → no test execution (exit 0, no output) | Test case exists and passes |
| 303-6 | auto-test-runner: phase active + implementing + source file → runs test command | Test case exists and passes |
| 303-7 | Syntax validation: hook with syntax error exits non-zero | Test case exists and passes |
| 303-8 | All new tests use isolated fixtures (`$TMPROOT`, `_make_git_repo`, controlled `HOME`) | Code review — no reference to real HOME or project paths |
| 303-9 | `bash tests/test-hooks.sh` passes with zero failures on current codebase | Exit code 0, output shows all tests passed |
