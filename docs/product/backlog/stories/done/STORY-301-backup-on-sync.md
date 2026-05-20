---
id: STORY-301
type: story
title: "Backup-on-sync with rollback support"
status: done
priority: now
effort: s
epic: EP-010
epic_sequence: 2
tags: [self-hosting, hooks, sync, recovery]
created: 2026-05-18
updated: 2026-05-19
completed: 2026-05-18
---

# Backup-on-sync with rollback support

As a SweetClaude developer syncing changes to the installed path, I want the sync script to automatically back up the current installed hooks before overwriting so that I can roll back to the last known-good state if the new hooks are broken.

## Context

The backup serves as the recovery source for STORY-304 (Bash-based hook repair). Without a backup, a broken installed hook requires manually reconstructing the previous version from git history or a release artifact. With a backup at `hooks.bak/`, recovery is a single `cp` command via the Bash tool.

## Objective success criteria

| # | Criterion | Verification |
|---|---|---|
| 301-1 | `hooks.bak/` created at the installed plugin path after sync | `test -d ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks.bak/` |
| 301-2 | `hooks.bak/` contains all `.sh` files from the pre-sync installed hooks | File count in `hooks.bak/` matches pre-sync hook count |
| 301-3 | Backup happens before any hook file is modified | Add canary file to installed `hooks/`, run sync → canary exists in `hooks.bak/` but not in `hooks/` |
| 301-4 | Previous backup is overwritten (single generation) | Run sync twice → `hooks.bak/` contains files from the second-to-last sync only |
| 301-5 | Backup failure aborts sync | Make `hooks.bak/` parent read-only, run sync → non-zero exit, installed hooks unchanged |
