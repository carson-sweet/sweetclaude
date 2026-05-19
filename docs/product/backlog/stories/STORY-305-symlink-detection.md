---
id: STORY-305
type: story
title: "Session-start symlink detection"
status: new
priority: now
effort: s
epic: EP-010
epic_sequence: 6
tags: [self-hosting, hooks, safety]
created: 2026-05-18
updated: 2026-05-18
---

# Session-start symlink detection

As a SweetClaude developer, I want the system to detect at session start if any installed hooks are symlinks to the repo so that the two-copy safety buffer is never silently compromised.

## Context

The two-copy architecture (installed vs repo) is the foundation that makes self-hosting safe. If installed hooks are symlinked to repo hooks, edits to the repo immediately affect running hooks — eliminating the safety buffer. A syntax error in the repo would instantly deadlock the session with no backup to restore from. This is the one self-hosting invariant that cannot be engineered away (per the second caucus) — it can only be detected and prevented.

## Implementation notes

Both `session-preflight.sh` and `fix-sweetclaude/SKILL.md` were modified in PR #61 (commit `3e5df42`, 2026-05-18): Step 10 removed from session-preflight, Step 7b rewritten in fix-sweetclaude. Read the current versions before implementing — do not assume pre-#61 structure.

All 13 hooks are registered as `plugin-native` in `hooks/hooks.json` — use this as the authoritative list of hooks to check for symlinks.

## Objective success criteria

| # | Criterion | Verification |
|---|---|---|
| 305-1 | `session-preflight.sh` checks installed hooks for symlinks | `grep "\-L" hooks/session-preflight.sh` |
| 305-2 | Symlink detected → warning contains "symlink" and "fix-sweetclaude" | Replace installed hook with symlink, trigger preflight → output contains both strings |
| 305-3 | No symlinks → no warning | All hooks are regular files → preflight produces no symlink warning |
| 305-4 | `fix-sweetclaude` replaces symlinked hook with regular file copy | Symlink exists → invoke fix → `[ -L hook ]` returns false, content matches original target |
| 305-5 | `sync-to-installed.sh` verifies no symlinks post-sync | Run sync → post-sync check confirms `[ ! -L hook ]` for all hooks |
