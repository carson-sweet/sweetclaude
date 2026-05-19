---
id: STORY-304
type: story
title: "Bash-based hook repair recovery procedure"
status: active
priority: now
effort: s
epic: EP-010
epic_sequence: 5
tags: [self-hosting, hooks, recovery]
created: 2026-05-18
updated: 2026-05-19
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
| 304-3 | Documentation explains why Bash works when Write/Edit is blocked | `grep -iE "matcher|Write.*Edit|Bash" docs/user-guide/hook-development.md` |
| 304-4 | `sweetclaude:hook-repair` skill exists | `test -f skills/hook-repair/SKILL.md` |
| 304-5 | Skill description mentions the broken-hook recovery use case | `grep -iE "broken hook|recovery|restore" skills/hook-repair/SKILL.md` |
| 304-6 | End-to-end recovery test passes and result is recorded in the story's Implementation History section | `grep -E '^Result: PASS' docs/product/backlog/stories/STORY-304-hook-repair-recovery.md` |
| 304-7 | `scripts/emergency-hook-restore.sh` exists and is executable | `test -x scripts/emergency-hook-restore.sh` |
| 304-8 | Emergency script restores hooks with zero SweetClaude dependencies | `bash -c 'unset SWEETCLAUDE_HOME; scripts/emergency-hook-restore.sh --dry-run'` |
| 304-9 | Break-glass procedure documented with both in-session and terminal instructions | `grep -iE "break.?glass|emergency" docs/user-guide/hook-development.md` |
| 304-10 | Recovery path verified against both `test-guardian.sh` and `auto-test-runner.sh` failure modes | `grep -E "test-guardian|auto-test-runner" docs/user-guide/hook-development.md` |
| 304-11 | Story documents the SweetClaude version stamp at which recovery was validated | `grep -E '^Validated against SweetClaude v[0-9]+\.[0-9]+\.[0-9]+' docs/product/backlog/stories/STORY-304-hook-repair-recovery.md` |
| 304-12 | `README.md` lists `sweetclaude:hook-repair` in the skills reference section | `grep -F 'hook-repair' README.md` |
| 304-13 | `docs/user-guide/skills-reference.md` has an entry for `sweetclaude:hook-repair` | `grep -F 'hook-repair' docs/user-guide/skills-reference.md` |

## Implementation Notes

- `scripts/emergency-hook-restore.sh` accepts `--dry-run` flag: resolves install path, lists hooks that would be restored, exits 0 without writing.
- `INSTALL_PATH` env var is a test-only back door for `emergency-hook-restore.sh`. It bypasses `installed_plugins.json` resolution. The script does not enforce a `$HOME/.claude/plugins/` prefix check when this var is set — this is intentional for testing. A code comment in the script marks this clearly.

## Implementation History
