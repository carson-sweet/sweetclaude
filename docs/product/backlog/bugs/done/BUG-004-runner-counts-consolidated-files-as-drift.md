---
id: BUG-004
type: bug
title: Migration runner counts consolidated-away files (phase.yaml) as drift on every session
status: done
priority: now
effort: m
epic: EP-039
milestone: null
sprint: null
tags: [runner, migration, drift, registry, consolidation]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: 2026-05-15
---

## Description

The migration runner's drift scan counts `phase.yaml` as drifted even though `phase.yaml` was consolidated into `sweetclaude.yaml` years ago and is INTENTIONALLY ABSENT on all unified-state projects. Result: every session in a healthy unified-state project surfaces "1 SweetClaude state file behind framework" → user runs `_migrate` → migration hits `file_missing` on phase.yaml → user gets a "recoverable failure" recovery menu asking them to choose Leave-as-is vs Rollback → user picks Leave-as-is → **next session: same thing fires again.**

The framework never records that the consolidation is the steady state for this project. The runner re-detects it as drift on every scan.

## Real reproduction (2026-05-13, `~/dev/llm-session-harness`)

User ran `/sweetclaude:update` after the 3.68.3 fix landed. The new update flow correctly chains to `_migrate`. Migration ran:

- `phase.yaml`: `file_missing` (expected — unified state)
- `skills.yaml`: already v2
- `sweetclaude.yaml`: confirmed
- `john-wick.yaml`: confirmed
- `corpus-pipeline.yaml`: confirmed

User was shown a recovery menu for the phase.yaml "failure" with three options:
1. Leave as-is and exit
2. Initiate rollback
3. Type something

The framework has been telling this user the same false lie for hours of sessions across multiple `/sweetclaude:update` and `/sweetclaude:fix-sweetclaude` runs. **The fix in 3.68.3 closed the "update lies about success" hole but did not address the underlying cause: the runner's drift definition is wrong.**

## Root cause

In `scripts/migrations/runner.py`, `scan_drift()` increments `DRIFT_COUNT` when a registered file is missing from disk (`file_missing: true`). There is no metadata on the registry entry that distinguishes:

- "this file is missing because it was never set up" (real drift — should count)
- "this file is missing because it was consolidated into another file" (NOT drift — should be silent)

`phase.yaml` is the only file currently in the second category. Its absence on a unified-state project (one with `sweetclaude.yaml`) is the documented, intentional steady state since v3.18.

## Proposed fix — Option A (user-selected)

Registry-level metadata. Two changes:

### Change 1: Registry schema addition

Add an optional field to migration registry entries for files that were consolidated into another file:

```yaml
phase.yaml:
  target_version: 2
  consolidated_into: sweetclaude.yaml
  consolidated_when:
    target_file_exists: sweetclaude.yaml
  handlers: [...]
```

Semantics:
- `consolidated_into` names the file that absorbed this one's responsibility
- `consolidated_when.target_file_exists` is the predicate: if the named file exists on disk, this entry is considered "intentionally absent" rather than "drifted"

### Change 2: `runner.py scan_drift()` honors the metadata

When `scan_drift()` encounters a `file_missing` for an entry that has `consolidated_into` AND the `consolidated_when.target_file_exists` predicate is satisfied:

- Skip from `DRIFT_COUNT`
- Do NOT emit a `MISSING|` line
- Emit a `CONSOLIDATED|<file_key>|absorbed-by=<target>` line for audit (informational, doesn't count toward drift)

For files without `consolidated_into` metadata, behavior unchanged (still counts as drift).

## Acceptance Criteria

- [ ] Migration registry entry for `phase.yaml` has `consolidated_into: sweetclaude.yaml` and a predicate
- [ ] `runner.py scan_drift()` skips consolidated files from `DRIFT_COUNT` when the predicate is satisfied
- [ ] `_migrate` does NOT show a recovery menu for `phase.yaml` `file_missing` on a unified-state project
- [ ] `drift-gate.sh` reports `DRIFT_COUNT=0` on a healthy unified-state project (no recurring "1 file behind framework" prompt)
- [ ] A non-unified-state project (legacy `phase.yaml` exists, no `sweetclaude.yaml`) still detects drift correctly and routes to consolidation
- [ ] The `CONSOLIDATED|` informational line appears in `--report-drift-for-skill` stdout but does NOT count toward `DRIFT_COUNT`

## Out of scope

- Reworking the migration runner's failure-mode taxonomy beyond this one addition
- Implementing the `consolidated_into` pattern for any file besides `phase.yaml` (no other consolidations exist today; add when a second one shows up)

## Related bugs

This is the underlying cause that BUG-002's surface fix did not address. BUG-002 was "update lies about success"; this is "runner lies about drift in the first place."

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
