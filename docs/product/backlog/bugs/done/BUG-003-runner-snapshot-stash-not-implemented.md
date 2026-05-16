---
id: BUG-003
type: bug
title: runner.py snapshot stash is documented but not implemented — rollback destroys uncommitted user code
status: done
priority: soon
effort: m
epic: EP-006
milestone: null
sprint: null
tags: [runner, snapshot, rollback, data-loss, migration]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: 2026-05-15
---

## Description

`scripts/migrations/runner.py` `create_snapshot()` docstring promises that uncommitted changes are stashed and the stash ref is recorded on `SnapshotInfo` for restoration. The reality: `stash_ref = None` is hardcoded; no `git stash` call exists.

The rollback path (`run_rollback.py` → runner's rollback logic) calls `git reset --hard <tag>`, which discards working-tree changes. If a user has uncommitted source code changes when they run `_migrate` and pick "Initiate rollback" from the recovery menu, **their uncommitted code is silently destroyed.**

**Origin:** Identified by the Opus QA integration agent during the BUG-002 caucus. The agent's note:

> "In the original `_migrate` flow (session start, from bootstrap), the user has just opened the project — working tree is usually clean. In the proposed `update` Step 6b flow, the user's working tree may have arbitrary uncommitted changes. The snapshot will tarball `.sweetclaude/` and artifact base_paths but **not** the user's source code in non-artifact paths. If the user later picks 'Initiate rollback', `git reset --hard` will obliterate their uncommitted code changes silently."

Pre-existing, but `update` Step 6b's inline `_migrate` chain (shipped in 3.68.3) widens the blast radius because update runs more often and from more diverse working-tree states than bootstrap.

## Severity

`soon` priority. The data-loss path requires:
1. User has uncommitted source code
2. Drift exists in their project
3. They invoke `_migrate` (via update, fix-sweetclaude, or directly)
4. They pick "Initiate rollback" from a recovery menu

This is a real but uncommon combination. When it hits, the consequence is irrecoverable user code loss — which is severe enough to fix soon even at low probability.

## Proposed fix

Three viable options, in order of preference:

1. **Implement the stash that the docstring promises.** Before snapshot: `git stash push -m "pre-migration-stash-{snapshot_id}"`. Record `stash_ref` on SnapshotInfo. On rollback after `git reset --hard <tag>`: `git stash pop <stash_ref>` to restore the working tree.

2. **Refuse to snapshot a dirty working tree.** Detect `git diff --quiet HEAD` exit code. If non-zero, abort `_migrate` with a clear message: "Working tree is dirty. Commit or stash your changes before migrating, or run with `--allow-dirty` to acknowledge that rollback will discard uncommitted work."

3. **Warn before chaining `_migrate` from update Step 6b.** If working tree is dirty, prompt: "You have uncommitted changes. If you choose rollback in `_migrate`, those changes will be lost. Proceed?"

Option 1 is the cleanest (matches the existing docstring contract). Option 2 is the safest (refuses to take the action that creates risk). Option 3 is the smallest scope but only protects the update flow, not direct `_migrate` invocations.

## Acceptance Criteria

- [x] Uncommitted changes in the user's working tree survive a `_migrate` → Rollback flow
- [x] The behavior matches what the existing docstring describes (or the docstring is updated to match the chosen approach)
- [x] Tests cover: clean working tree + rollback (existing behavior preserved); dirty working tree + rollback (no data loss)
- [x] If Option 2 is chosen: dirty-tree rejection has a clear user-facing message with the path to resolution

## Out of scope

- Snapshotting framework files in `~/.claude/` (update flow handles its own framework sync)
- Snapshotting files outside the user's git working tree

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
