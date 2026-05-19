---
id: STORY-304
type: story
title: "Bash-based hook repair recovery procedure"
status: deferred
priority: now
effort: s
epic: EP-010
epic_sequence: 5
tags: [self-hosting, hooks, recovery]
created: 2026-05-18
updated: 2026-05-18
---

# Bash-based hook repair recovery procedure

As a SweetClaude developer whose session is blocked by a broken installed hook, I want a documented and optionally automated recovery path using the Bash tool so that I can restore the last known-good hook without leaving Claude Code.

## Context

When an installed hook is broken (syntax error, logic error that returns `{"ok": false}` unconditionally), all `Write`/`Edit` operations are blocked. But the `Bash` tool is NOT gated by `test-guardian.sh` or `auto-test-runner.sh` — their matcher is `Write|Edit`, not `Bash`. This means `Bash` can copy the backup hook (from STORY-301's `hooks.bak/`) over the broken installed hook, restoring the session.

This is the last-resort recovery mechanism. The sync gate (STORY-300), test gate (STORY-302), and backup (STORY-301) are prevention. This story is the cure when prevention fails.

## Objective success criteria

| # | Criterion | Verification |
|---|---|---|
| 304-1 | `docs/user-guide/hook-development.md` contains recovery procedure section | `grep -l "recovery" docs/user-guide/hook-development.md` |
| 304-2 | Recovery procedure includes exact `cp` command with path template | `grep "hooks.bak" docs/user-guide/hook-development.md` |
| 304-3 | Documentation explains why Bash works when Write/Edit is blocked | `grep -i "matcher\|Write.*Edit\|Bash" docs/user-guide/hook-development.md` |
| 304-4 | `sweetclaude:hook-repair` skill exists | `test -f skills/hook-repair/SKILL.md` |
| 304-5 | End-to-end: break test-guardian → Write/Edit blocked → Bash cp from hooks.bak → Write/Edit unblocked | Manual test, documented result |
| 304-6 | `scripts/emergency-hook-restore.sh` exists and is executable | `test -x scripts/emergency-hook-restore.sh` |
| 304-7 | Emergency script restores hooks with zero SweetClaude dependencies | Run from clean bash → hooks restored |
| 304-8 | Break-glass procedure documented with both in-session and terminal instructions | `grep -i "break glass\|emergency" docs/user-guide/hook-development.md` |
