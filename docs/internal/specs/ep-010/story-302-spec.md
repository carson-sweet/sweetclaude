---
id: SPEC-302
story: STORY-302
epic: EP-010
version: 1.0
date: 2026-05-18
status: done
---

# Specification: STORY-302 Pre-sync test validation gate

## User story

As a SweetClaude developer syncing changes to the installed path, I want the sync script to run the hook test suite before copying so that a hook with failing tests can never reach the installed path.

## Deliverables

1. Test gate step added to `scripts/sync-to-installed.sh` (created by STORY-300)

## Technical design

### Position in sync pipeline

Runs after the phase check, before the backup. If tests fail, neither backup nor sync executes.

```
Phase check → **Test gate** → [dry-run exit] → Backup → Sync → Post-sync checks
```

### Implementation

```bash
echo "Running hook test suite..."
if ! bash "$REPO_ROOT/tests/test-hooks.sh"; then
  echo "ERROR: Hook tests failed. Sync blocked. Fix the tests before syncing." >&2
  exit 2
fi
echo "All hook tests passed."
```

### Non-bypassable

The `--force` flag bypasses the phase check but does NOT bypass the test gate. This is deliberate: a developer can consciously force a sync outside the IMPLEMENT phase, but cannot sync hooks that fail their own tests. If the tests are wrong, fix the tests first.

There is no `--skip-tests` flag. This gate is the one non-overridable safety mechanism in the sync pipeline.

### Interaction with --dry-run

In dry-run mode, the test gate STILL RUNS. Tests are read-only (they use isolated fixtures) and their pass/fail status is useful information even in a dry run. If tests fail in dry-run mode, the output says: "Dry run: hook tests failed. Sync would be blocked."

## Constraints

- `tests/test-hooks.sh` must exit 0 for all tests passing, non-zero for any failure. The existing script already follows this convention (`exit $FAILED` equivalent via `set -e` and the `FAILED` counter).
- The test gate runs tests from the REPO copy, not the installed copy. This validates what is about to be synced.

## Success criteria

| # | Criterion | Verification |
|---|---|---|
| 302-1 | Sync runs `tests/test-hooks.sh` before copying | Sync output contains test-hooks.sh output |
| 302-2 | Test failure blocks sync with exit code 2 | Failing test → exit code 2, installed hooks unchanged |
| 302-3 | `--force` does NOT bypass test gate | `--force` with failing test → exit code 2 (not 0) |
| 302-4 | Test success allows sync to proceed | All tests pass → sync completes, exit 0 |

## Dependencies

- STORY-300 (sync script exists)
- STORY-303 (extended test coverage — not strictly required, but the gate is more valuable with broader coverage)

## Known gaps

- When STORY-302 adds the test gate, the dry-run success message in STORY-300's code (`"Dry run: all checks passed."`) should be updated to reflect that test checks also passed. The current message is accurate for STORY-300 alone but will understate what was validated once the test gate exists.
