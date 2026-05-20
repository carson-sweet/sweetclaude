---
id: STORY-309
type: story
title: "Hardening pass for emergency-hook-restore.sh — REPO_ROOT override, prefix-check design note, coverage gaps"
status: new
priority: soon
effort: s
tags: [self-hosting, hooks, emergency-restore, hardening, testing]
created: 2026-05-19
updated: 2026-05-19
---

# Hardening pass for emergency-hook-restore.sh

## Context

STORY-304 shipped `scripts/emergency-hook-restore.sh` with a complete TDD Level 3 test suite
(`tests/test-emergency-restore.sh`). Three known gaps were deferred from that implementation:

1. **REPO_ROOT is not overridable via env var** — the script resolves REPO_ROOT via
   `BASH_SOURCE[0]`, which always points to the real repo. This makes `test_zero_restore`
   impossible to exercise cleanly: the zero-restore path (both backup and repo empty → WARNING
   + exit 1) requires an empty `$REPO_ROOT/hooks/`, but the real repo always has 21+ hooks.
   The test is currently a documented SKIP stub.

2. **Prefix-check / hooks.bak/ trust signal is undocumented** ~~— during STORY-304
   implementation, the tests revealed a design nuance not captured in DESIGN-304: the prefix
   check (path must be inside `$HOME/.claude/plugins/`) is skipped when the resolved install
   path has a `hooks.bak/` directory. That directory's presence is a trust signal — it is
   created only by the sync process (`sync-to-installed.sh`), so its existence proves the path
   is a legitimate SweetClaude installation. This logic is correct but not written down anywhere
   except as a code comment in the script body (lines 100–107). It should be Decision 14 in
   DESIGN-304.~~ **Completed during STORY-304 closeout.** Decision 14 was added to
   `docs/internal/specs/ep-010/design-304.md` (§14, lines 271–294) before STORY-309 was opened.
   Work item 3 below is removed; acceptance criterion "Decision 14 is documented" is already met.

3. **`set -e` requirement is not behaviorally testable** — the architectural caucus noted that
   `set -e` cannot be verified by behavioral tests. Accepted as a known limitation; the lint
   equivalent (checking `set -e` appears in the script header) could be added to
   `test_zero_deps_lint` as a static assertion.

## Work

1. Add `REPO_ROOT` env-var override to `scripts/emergency-hook-restore.sh`:
   ```bash
   REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)}"
   ```
   This preserves existing behavior when the env var is absent while enabling test isolation.

2. Uncomment `test_zero_restore` in `tests/test-emergency-restore.sh` — replace the SKIP stub
   with a real test that sets `REPO_ROOT` to a tmpdir with an empty `hooks/` and an empty (or
   absent) `hooks.bak/`, then asserts exit 1 and WARNING on stderr.

3. Optionally: add a static `set -e` assertion to `test_zero_deps_lint`:
   ```bash
   if ! grep -qE '^set -e' "$SCRIPT"; then
     fail "test_zero_deps_lint: 'set -e' not present in script header"
     return
   fi
   ```

## Acceptance criteria

- `test_zero_restore` is no longer a SKIP — it fails on a broken implementation and passes on a
  correct one
- `REPO_ROOT` env override does not change behavior when unset
- ~~Decision 14 is documented in DESIGN-304~~ — already completed during STORY-304 closeout
- All existing tests still pass (no regressions)
- Script remains zero-dependency (no new `source` calls)
