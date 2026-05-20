---
id: BUG-008
type: bug
title: project-gh-import-issues and project-gh-sync-issues missing v4 migration guards
status: done
priority: soon
effort: s
epic: EP-001
epic_sequence: 7
milestone: null
sprint: null
tags: [v4, skills, migration-guard, ep-008-5]
origin: manual
created: 2026-05-13
updated: 2026-05-19
closed_date: 2026-05-19
---

## Description

The May 11 v4 assessment item B4 required: "every v4 skill rewritten in EP-005 needs an entry guard that surfaces the same hard-stop message if v3 BL files are still present at the configured product_base."

The 37350ed commit added the guard to:
- `skills/project-backlog/SKILL.md` ✓
- `skills/project-issues/SKILL.md` ✓
- `skills/project-backlog-triage/SKILL.md` ✓

But missed:
- `skills/project-gh-import-issues/SKILL.md` ✗
- `skills/project-gh-sync-issues/SKILL.md` ✗

Both jump straight into Python that reads `docs/product/backlog/INDEX.md`. On a pre-migration v3 project, the INDEX doesn't exist — they'd crash with FileNotFoundError or worse, write half-state into a directory the user didn't expect.

**Origin:** Surfaced during EP-008.5 STORY-046 work (cross-skill validation).

## Severity

`soon` priority. Real bug, narrow user population (anyone running the gh skills on a pre-migration v3 project), bounded fix.

## Fix

Fixed in commit `3fb6384` (2026-05-13) — "fix(v4): close BUG-005, BUG-006, DEBT-002, CHORE-008 + standardize artifact-privacy.yaml path". Both `project-gh-import-issues/SKILL.md` and `project-gh-sync-issues/SKILL.md` received the canonical `## MIGRATION GUARD` block identical to the three already-guarded skills.

Verified: `tests/test-ep-008-5-verifications.sh` Scenario F checks all 5 skills for the canonical guard block — all pass.

## Acceptance Criteria

- [x] `project-gh-import-issues/SKILL.md` has the migration guard at the top
- [x] `project-gh-sync-issues/SKILL.md` has the migration guard at the top
- [x] `tests/test-ep-008-5-verifications.sh` Scenario F covers guard presence for all five skills (project-backlog, project-issues, project-backlog-triage, project-gh-import-issues, project-gh-sync-issues)

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
