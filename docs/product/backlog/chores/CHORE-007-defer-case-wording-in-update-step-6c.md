---
id: CHORE-007
type: chore
title: Distinguish Defer-case wording in update Step 6c from clean-state success
status: new
priority: later
effort: s
epic: null
milestone: null
sprint: null
tags: [update, _migrate, ux, wording, defer]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
---

## Description

When a user runs `/sweetclaude:update`, drift is detected, they pick "Migrate now", and then in `_migrate` Step 4 they pick **Defer** (only available if BL-068 `migration-decision-reminder.sh` is installed): the migration ran successfully, but the user explicitly chose not to "accept" it yet. `pending-migration-decision.yaml` is written; drift marker is untouched.

Control returns to update Step 6b. The post-migrate drift check shows `POST_MIGRATE_COUNT=0` (migration applied), so Step 6c prints "✓ Project: clean (verified post-migrate)". But on the next prompt, `migration-decision-reminder.sh` injects "you have a pending decision" — and at turn 10, the user is hard-blocked.

The success report and the reminder behavior are contradictory in the same turn: "all clean!" + "you have a pending decision, decide or get blocked at turn 10."

**Origin:** Identified by the Opus QA integration agent during the BUG-002 caucus. Ship advocates pushed back on treating this as a BUG-002 blocker — Defer is opt-in user choice, not a framework lie. Filed as a follow-up wording polish.

## Severity

`later` priority. The system functions correctly (markers do their job, reminder hook surfaces state). The complaint is purely cosmetic — the wording in Step 6c doesn't reflect the deferred-decision state.

## Proposed fix

In update Step 6b's post-migrate verification, detect the presence of `.sweetclaude/state/pending-migration-decision.yaml` after `_migrate` returns. If present, the `✓ Project:` line in the Step 6c success report should read:

```
✓ Project:    migration decision deferred (reminder active; decide before turn 10)
```

Instead of `clean (verified post-migrate)`.

## Acceptance Criteria

- [ ] update Step 6b detects `pending-migration-decision.yaml` after `_migrate` returns
- [ ] Step 6c success report shows distinct wording when a Defer decision is active (vs Accept)
- [ ] When the user then accepts or rolls back in a later session, the wording reflects the resolved state on next update

## Out of scope

- Blocking the success report entirely on Defer (the framework state is consistent; the user chose this)
- Changing the BL-068 hook behavior

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
