---
id: BUG-007
type: bug
title: Migrate Step 8 (finalize) is not atomic — crash mid-finalize can leave half-state
status: done
priority: soon
effort: m
epic: EP-001
epic_sequence: 6
milestone: null
sprint: null
tags: [migrate, atomicity, data-integrity, recovery]
origin: manual
created: 2026-05-13
updated: 2026-05-19
closed_date: 2026-05-19
---

## Description

`scripts/migrate/migrate-v3-to-v4.py finalize()` writes two state files in sequence:
1. `.sweetclaude/state/artifact-privacy.yaml` (sets `categories.product.base_path: docs/product`)
2. `.sweetclaude/state/sweetclaude.yaml` (sets `framework.installed_version: 4.0.0`)

A crash, SIGKILL, or filesystem error between the two writes leaves a half-migrated state:
- artifact-privacy says docs/product (post-migration layout)
- sweetclaude.yaml still says installed_version: 3.x (pre-migration)
- v4 STORY/BUG files exist at docs/product/backlog/
- v3 BL files may or may not still be at .sweetclaude/product/backlog/ (cleanup-v3-files runs after finalize in the skill)

**Origin:** May 11 v4 assessment items D1 + D2. Carried forward through 2026-05-13. Same atomicity concern noted by the design caucus on `feat/v4-phase1-backlog`.

## User-visible consequence

Next session's bootstrap Step 5b fires the v4 hard-stop because PROJECT_NOT_V4 (installed_version is still 3.x). User runs `/sweetclaude:migrate` again. The re-run finds 0 v3 files in docs/product/backlog (because the post-finalize product_base now points there), executes a no-op migration, and **overwrites INDEX.md and MIGRATION-MAP.md with empty counters** — losing the record of the first run's migration.

User's STORY/BUG files survive, but they're orphaned from the INDEX. Backlog appears empty.

## Severity

`soon` priority. The crash window is small (two yaml writes, ~100ms total) and requires a specific OS/process failure during that window. But the consequence is data-integrity-adjacent (empty INDEX after recovery) and not obvious to the user how to fix.

## Fix

Fixed prior to BUG-007 being filed — the fix was implemented as part of the BUG-005 resolution:

1. **Reorder implemented**: `finalize()` already writes `sweetclaude.yaml` first, then `artifact-privacy.yaml` (lines 572-584), with comment "BUG-005 reordering: write sweetclaude.yaml FIRST, then artifact-privacy.yaml".

2. **Idempotency guard implemented**: `_check_already_migrated()` (lines 331-374) checks `installed_version: 4.x` AND non-empty INDEX, refuses to regenerate with `error: already-migrated`. Called as first operation in `execute()` (line 379).

Verified: `tests/test-migrate-v3-to-v4.sh` scenarios `run_bug_005_reorder` and `run_bug_005_idempotency` both pass (all checks green).

## Acceptance Criteria

- [x] `finalize()` write order is: sweetclaude.yaml → artifact-privacy.yaml (sweetclaude.yaml is the source of truth for "are we at v4")
- [x] `execute()` detects "already migrated" state (`installed_version: 4.0.0` AND non-empty INDEX) and refuses to regenerate INDEX/MAP, with clear user-facing message
- [x] Test covers: simulated crash between finalize writes, then re-run of migrate → INDEX preserved
- [x] Test covers: re-run of migrate on already-migrated project → no-op, exits cleanly, INDEX untouched

## Out of scope

- True multi-file atomicity (would require a transaction-log pattern — over-engineering for this risk)
- Auto-recovery from partial state (the user should be told what's wrong and given a path forward, not silently healed)

## Related

This is the underlying concern that the May 11 assessment D1 + D2 raised. Was deferred while higher-priority blockers (A1/A3/A4, B2/C) were resolved.

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
