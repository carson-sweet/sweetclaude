---
id: BUG-002
type: bug
title: sweetclaude:update completes without ensuring _migrate is fully complete for the current project
status: done
priority: now
effort: m
epic: EP-039
milestone: null
sprint: null
tags: [update, migrate, workflow, drift, orchestration]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: 2026-05-15
---

## Description

`sweetclaude:update` finishes and reports success while leaving the current project in a state where the *very next session* reports artifact drift. The update flow does not run `_migrate` and does not verify the project's post-update drift state before returning success.

### Real reproduction (2026-05-13)

User session at `~/dev/llm-session-harness`:

1. **Session 1 start.** Drift gate fires: "2 file(s) behind framework — migration required."
2. User runs `/sweetclaude:fix-sweetclaude` → migration runs → sweetclaude.yaml v1→v2 migrates → other files confirmed → markers cleared. Health check refreshes state. Health surfaces 3.68.2 available.
3. User runs `/sweetclaude:update`. Sync 3.68.1 → 3.68.2 succeeds. Step 6b drift check reports `DRIFT_COUNT=0`. Update returns success.
4. **Session 2 start (new Claude Code session, immediately after).** Drift gate fires: "1 file(s) behind framework — migration required."

Two structural problems revealed by this sequence:
- `update` does not run `_migrate` as part of its flow at all
- `update`'s Step 6b reports `DRIFT_COUNT=0` but the next session's `drift-gate.sh` reports `DRIFT_COUNT=1`. The two checks are not equivalent — `update` can return success while `drift-gate.sh` would block the next session

The framework's two drift-detection paths are not in agreement. `update` declares "done" while the next session-start considers the same project not-done. That contradiction is the bug.

## Root cause

Two coupled gaps:

1. **`update` and `_migrate` are decoupled by design.** The thinking was "user might update the framework but defer applying migrations." In practice this creates a UX trap: update succeeds, next session immediately complains.
2. **`update` Step 6b's drift check is not authoritative.** It uses `--report-drift-for-skill` against the runner; `drift-gate.sh` at session start runs a related but not identical check. The two can disagree.

The result: the framework's own statement "update is complete" is not equivalent to "the project will boot cleanly next session."

## Required fix

`sweetclaude:update` MUST own the post-update state of the current project and MUST block until verified clean. Specifically:

1. After Step 6 (framework sync + plugin metadata):
   - Run the SAME drift check that `drift-gate.sh` runs at session start. Not the `--report-drift-for-skill` path — the authoritative check.
   - If drift > 0: invoke `_migrate` inline (with snapshot + acceptance prompt, same UX as fix-sweetclaude path).
2. After `_migrate` completes:
   - Re-run the authoritative drift check. Must report 0.
   - If still > 0: HALT update. Do not report success. Surface what remains drifted and the next required action (likely a runner bug — requires investigation, not just rerun).
3. The success report must include drift status: `✓ Project: clean (verified)` or it must not say success at all.

The session-start `drift-gate.sh` and update's Step 6b must use a SINGLE shared check function/script. Maintaining two near-identical drift checks that can disagree is itself a defect.

### Why this severity

- Users currently update, get told "✓ Drift: none in this project", restart, and immediately see a drift error. That contradiction erodes trust in the update flow.
- The workaround (run fix-sweetclaude after every update) is friction that should not exist.
- This is the third bug in the family "different parts of the framework disagree about state" (after the schema_version check divergence and the global hook registration divergence). The pattern needs to be retired.

## Acceptance Criteria

- [ ] `sweetclaude:update` does not return success while the current project has unresolved artifact drift
- [ ] `update` invokes `_migrate` (with snapshot + acceptance prompt) when post-sync drift is detected, without requiring the user to run a second command
- [ ] `update` and `drift-gate.sh` share a single drift-check implementation (one script or one function) — no two divergent paths
- [ ] When `_migrate` runs inline and completes successfully, `update`'s final report includes a `✓ Project: clean (verified)` line
- [ ] When `_migrate` runs inline and the post-state still shows drift, `update` halts and surfaces the unresolved drift with an explicit instruction (do not silently complete)
- [ ] A new session opened immediately after `update` reports success sees `drift_count: 0` from `drift-gate.sh`

## Out of scope

- Refactoring the migration runner itself (separate concern — if `_migrate` runs but doesn't fully resolve drift, that's a runner bug requiring its own ticket)
- Auto-applying migrations across multiple projects (this fix is scoped to the current project only)

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
