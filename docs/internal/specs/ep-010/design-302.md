---
id: DESIGN-302
story: STORY-302
spec: SPEC-302
epic: EP-010
version: 1.0
date: 2026-05-18
status: done
---

# Design: STORY-302 Pre-sync test gate

## Overview

Add a test gate step to `scripts/sync-to-installed.sh` that runs the hook test suite before any sync proceeds. This gate is non-bypassable — `--force` does NOT override it.

## File: scripts/sync-to-installed.sh

### Change

Replace the `# ── Test gate (STORY-302 adds implementation here)` placeholder with:

```bash
# ── Test gate ────────────────────────────────────────────────────────────────

TEST_HOOKS="$REPO_ROOT/tests/test-hooks.sh"

if [ ! -f "$TEST_HOOKS" ]; then
  echo "ERROR: Sync blocked — tests/test-hooks.sh not found." >&2
  exit 2
fi

if [ ! -x "$TEST_HOOKS" ]; then
  echo "ERROR: Sync blocked — tests/test-hooks.sh is not executable." >&2
  exit 2
fi

if ! bash "$TEST_HOOKS"; then
  if [ "$DRY_RUN" = true ]; then
    echo "Dry run: hook tests failed. Sync would be blocked." >&2
  else
    echo "ERROR: Sync blocked — tests failed. Fix failing tests before syncing." >&2
  fi
  exit 2
fi

echo "All hook tests passed."
```

Three guard paths, all exit 2: missing file, non-executable file, test failure. The dry-run path emits a dry-run-specific message per the spec.

### Design notes

1. **Non-bypassable.** The `--force` flag handling is above this block (in the phase check section). There is no `--skip-tests` flag. The test gate always runs.

2. **Runs repo tests.** The test suite runs from `$REPO_ROOT/tests/test-hooks.sh` — it tests the repo copy of hooks, which is what's about to be synced.

3. **Dry-run behavior.** The test gate runs in dry-run mode too. Tests are read-only (isolated fixtures, temp directories) so running them has no side effects. A dry run that shows passing tests gives confidence that a real sync would succeed.

4. **Position in pipeline.** After phase check, before dry-run exit. This means:
   - Phase blocked → no tests run (saves time when blocked)
   - Phase OK → tests run → if fail, no backup, no sync
   - Phase OK → tests pass → dry-run exits or continues to backup

```
Phase check → **Test gate** → [dry-run exit] → Backup → Sync hooks → Post-sync → Sync non-hooks
```

5. **Execution time.** Current `test-hooks.sh` has 10 tests, each ~0.1s. STORY-303 adds ~11 more with a marker-file retry loop (max 1s per test). Total: ~3-5 seconds. Acceptable overhead for a sync operation.

### Blast radius mitigation

The key risk from the blast radius analysis: a flaky test blocks all syncs. Mitigations:

- STORY-303 tests use deterministic fixtures (no network, no real database, no timing-dependent assertions except the marker-file retry loop).
- The marker-file retry loop (STORY-303) uses 5 attempts at 0.2s intervals for a trivial `touch` command — generous margin.
- If a test becomes flaky: fix the test. The gate is non-bypassable by design.

## Testing strategy

12 tests added to `tests/test-sync.sh` (tests 32-43):

| Test | Scenario | Expected |
|---|---|---|
| 32 (302-1) | Passing test-hooks.sh | stdout has test evidence + "All hook tests passed", exit 0 |
| 33 (302-2) | Failing test-hooks.sh | Exit 2, stderr message, hooks unchanged |
| 34 (302-3) | Failing tests + --force (verify phase) | Exit 2 — force does not bypass |
| 35 (302-4) | Passing tests, normal sync | Exit 0, hooks synced, stub-hook.sh present |
| 36 (302-dry-run) | Passing tests + --dry-run | stdout has test evidence, exit 0, hooks unchanged |
| 37 (302-dry-run-fail) | Failing tests + --dry-run | Exit 2, dry-run-specific stderr message, hooks unchanged |
| 38 (302-missing) | test-hooks.sh doesn't exist | Exit 2, stderr message |
| 39 (302-no-backup) | Failing tests | hooks.bak/ NOT created (ordering verification) |
| 40 (302-force-dry-run-fail) | Failing tests + --force --dry-run | Exit 2, stderr message |
| 41 (302-force-implement-fail) | Failing tests + --force + IMPLEMENT phase | Exit 2, hooks unchanged |
| 42 (302-exit127) | test-hooks.sh exits 127 | Gate still produces exit 2 |
| 43 (302-not-executable) | test-hooks.sh chmod -x | Exit 2, stderr message |
