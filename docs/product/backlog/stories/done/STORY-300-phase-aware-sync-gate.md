---
id: STORY-300
type: story
title: "Phase-aware sync gate"
status: done
priority: now
effort: m
epic: EP-010
epic_sequence: 1
tags: [self-hosting, hooks, sync]
created: 2026-05-18
updated: 2026-05-18
completed: 2026-05-18
---

# Phase-aware sync gate

As a SweetClaude developer working on hook code during an IMPLEMENT phase, I want the sync-to-installed mechanism to refuse to copy my in-progress work to the installed path so that a broken repo hook can never take down my running session.

## Context

The installed copy at `~/.claude/plugins/cache/sweetclaude/sweetclaude/<version>/` is the "known good" fallback. Its hooks fire on every tool call. Syncing a broken development copy to the installed path during implementation creates an unrecoverable deadlock — the broken hook blocks the Write/Edit needed to fix it. The sync gate prevents this by blocking sync when the active phase is `implement`.

Phase state may live in either `.sweetclaude/state/phase.yaml` (schema v1) or `.sweetclaude/state/sweetclaude.yaml` under `work.active.phase` (schema v2). The sync gate must check both locations — a v2 project may not have `phase.yaml` at all.

This story also creates `scripts/sync-to-installed.sh` — the canonical sync wrapper that STORY-301 and STORY-302 build on. All subsequent sync-related stories add behavior to this script.

## Objective success criteria

| # | Criterion | Verification |
|---|---|---|
| 300-1 | `scripts/sync-to-installed.sh` exists and is executable | `test -x scripts/sync-to-installed.sh` |
| 300-2 | Sync blocked when `phase.yaml` contains `phase: implement` | Exit code non-zero, output contains "IMPLEMENT" |
| 300-3 | Sync blocked when `phase.yaml` contains `phase: IMPLEMENT` (case-insensitive) | Same check with uppercase |
| 300-4 | Sync proceeds when `phase.yaml` is absent and `sweetclaude.yaml` has no active implement phase | Exit code 0 (or dry-run succeeds) |
| 300-5 | Sync proceeds when `phase.yaml` contains `phase: verify` | Exit code 0 |
| 300-6 | `--force` overrides phase check | Exit code 0 even with `phase: implement` |
| 300-7 | `--force` appends entry to decision log (actual sync only) | `grep` for today's date + "force" in decision-log.md after real sync. `--force --dry-run` must NOT append a log entry. |
| 300-8 | `experimental-feature-setup` applies the same phase check | Invoke skill with `phase: implement` active → sync step refused |
| 300-9 | Sync blocked when `sweetclaude.yaml` contains `work.active.phase: implement` and no `phase.yaml` exists | Exit code non-zero, output contains "IMPLEMENT" |
| 300-10 | `--dry-run` runs all checks without syncing | Exit code 0 if all checks pass, no files modified |
| 300-11 | `tests/test-sync.sh` exists and passes | `bash tests/test-sync.sh` exits 0 |
| 300-12 | Unknown argument produces non-zero exit and error message | `--bogus` → non-zero exit, stderr contains "Unknown argument" |
| 300-13 | Missing `installed_plugins.json` produces exit code 5 | No plugins JSON → exit 5 |
| 300-14 | `phase.yaml` takes precedence over `sweetclaude.yaml` | Both files present, `phase.yaml` says verify, `sweetclaude.yaml` says implement → exit 0 (verify wins) |
| 300-15 | `sweetclaude.yaml` with non-implement phase allows sync | `sweetclaude.yaml` has `work.active.phase: verify`, no `phase.yaml` → exit 0 |
| 300-16 | `--force` without `decision-log.md` does not error | `--force` during implement with no decision-log.md → exit 0 |
| 300-17 | `--dry-run` does not create new files at installed path | `--dry-run` with hooks in repo → file count at installed path unchanged |
