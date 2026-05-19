---
id: EP-010
type: epic
title: Self-Hosting Infrastructure
status: active
release: REL-002
milestones: []
source: caucus-2026-05-18-self-hosting
created: 2026-05-18
updated: 2026-05-18
completion_criteria:
  - "Sync script exists and works (300)"
  - "Phase gate blocks sync during IMPLEMENT (300)"
  - "Test gate blocks sync on test failure (302)"
  - "Backup created on every sync (301)"
  - "Broken hook recoverable via Bash (304)"
  - "TDD-sensitive hooks have test coverage (303)"
  - "Symlinks detected at session start (305)"
  - "fix-sweetclaude repairs symlinks (305)"
  - "Hook dev workflow documented (306)"
  - "Zero manual rules — all carve-outs machine-enforced"
completion_criteria_done: [0, 1, 2, 3]
---

# EP-010: Self-Hosting Infrastructure

**Release:** REL-002 (Self-Hosting Infrastructure)
**Source:** Four-architect caucus on SweetClaude self-hosting (2026-05-18)

## Summary

Enable SweetClaude to fully manage its own development with zero manual rules. Implement sync gates, backup/recovery mechanisms, symlink detection, and extended hook test coverage so that all three self-hosting carve-outs are either eliminated or reduced to machine-enforced invariants.

## Context

SweetClaude was previously not used to manage its own development due to circular dependency concerns. A caucus of four plugin architects determined that self-hosting is safe and beneficial with specific infrastructure in place. Two of three identified carve-outs are fully solvable; the third is reducible to a machine-checked invariant with automated recovery.

This epic is a prerequisite for EP-009 (Workflow Orchestration Runbooks) being used on SweetClaude itself — without this infrastructure, the orchestrated pipeline cannot safely run on its own codebase.

## Stories

### STORY-300: Phase-aware sync gate

**Type:** feature
**Addresses:** Carve-outs 1 and 2

Modify all sync paths to check `phase.yaml` before executing. If `phase: implement` is active, block the sync with a clear error message.

**Acceptance criteria:**
- `sweetclaude:experimental-feature-setup` reads `phase.yaml` and refuses sync during `phase: implement`
- A new `scripts/sync-to-installed.sh` wrapper enforces the same gate for manual syncs
- Override requires `--force` flag, which logs to `.sweetclaude/state/decision-log.md`
- Documentation of manual `rsync` updated to reference the wrapper script instead

---

### STORY-301: Backup-on-sync with rollback support

**Type:** feature
**Addresses:** Carve-outs 1 and 2

Every sync to the installed path creates a backup of the current installed hooks before overwriting.

**Acceptance criteria:**
- Sync creates `~/.claude/plugins/cache/sweetclaude/sweetclaude/<version>/hooks.bak/` before overwriting `hooks/`
- Backup is a full copy, not a diff
- Previous backup is overwritten (only one backup generation retained)
- `scripts/sync-to-installed.sh` creates the backup as its first step

---

### STORY-302: Pre-sync test validation gate

**Type:** feature
**Addresses:** Carve-out 1

All sync paths run `bash tests/test-hooks.sh` before copying hooks to the installed path. Sync is blocked on any test failure.

**Acceptance criteria:**
- `sweetclaude:experimental-feature-setup` runs `bash tests/test-hooks.sh` before sync
- `scripts/sync-to-installed.sh` runs `bash tests/test-hooks.sh` before sync
- Any test failure blocks the sync with output showing which tests failed
- No override — fix the tests first

---

### STORY-303: Extend test-hooks.sh coverage to TDD-sensitive hooks

**Type:** feature
**Addresses:** Carve-out 1

Add test cases for `test-guardian.sh` and `auto-test-runner.sh` to the existing `tests/test-hooks.sh` fixture-based test suite.

**Acceptance criteria:**
- `test-guardian.sh` tested: correct JSON output for each code path (phase active, phase inactive, test file edit, non-test file edit)
- `auto-test-runner.sh` tested: correct behavior for each code path
- Syntax validation: a hook with a deliberate syntax error exits non-zero (verifying fail-closed)
- All tests run in isolated fixture environments (fake git repo, controlled HOME)

---

### STORY-304: Bash-based hook repair recovery procedure

**Type:** feature
**Addresses:** Carve-outs 1 and 3

Document and optionally codify the recovery path for a broken installed hook: use `Bash` tool (not gated by Write/Edit hooks) to restore from `hooks.bak/`.

**Acceptance criteria:**
- Recovery procedure documented in the hook development section of the user guide
- Recovery command: `cp ~/.claude/plugins/cache/.../hooks.bak/<hook>.sh ~/.claude/plugins/cache/.../hooks/<hook>.sh`
- Optionally: a `sweetclaude:hook-repair` escape skill that performs the restore automatically
- The procedure is verified to work when `test-guardian.sh` is in a broken state (the Bash tool is not blocked)

---

### STORY-305: Session-start symlink detection

**Type:** feature
**Addresses:** Carve-out 3

`session-preflight.sh` checks all installed hooks for symlinks at session start and warns immediately if any are found.

**Acceptance criteria:**
- At session start, every `.sh` file in the installed hooks directory is checked with `[ -L "$hook" ]`
- If any symlink is found, `emit_heal` warns: "Installed hook is a symlink: {path}. This breaks self-hosting safety. Run /sweetclaude:fix-sweetclaude to resolve."
- `sweetclaude:fix-sweetclaude` detects symlinked hooks and replaces them with copies of the symlink targets
- Sync scripts verify no symlinks exist post-sync

---

### STORY-306: Fixture-based hook development workflow documentation

**Type:** chore
**Addresses:** Carve-out 2

Document the primary hook development workflow that avoids syncing during implementation: test hooks against fixture environments and real inputs without installing them.

**Acceptance criteria:**
- Hook development guide covers: `CLAUDE_FILE_PATH=... CLAUDE_TOOL_NAME=... bash hooks/<hook>.sh` for logic testing
- Guide covers: `bash tests/test-hooks.sh` for regression testing
- Guide covers: when and how to sync (SHIP phase only, via `scripts/sync-to-installed.sh`)
- Guide covers: the integration test wrapper pattern for hooks that need real Claude Code dispatch testing

## Epic-Level Success Criteria

All criteria are binary pass/fail. Verification method is listed for each.

1. **Sync script exists and works.** `scripts/sync-to-installed.sh` exists, is executable, and performs the full sync. Verify: `test -x scripts/sync-to-installed.sh && bash scripts/sync-to-installed.sh --dry-run` succeeds.
2. **Phase gate blocks sync during IMPLEMENT.** Sync refuses when `phase.yaml` has `phase: implement`. Verify: set phase, run sync → non-zero exit, message contains "IMPLEMENT".
3. **Test gate blocks sync on test failure.** Sync runs `tests/test-hooks.sh` and blocks on failure; `--force` does NOT bypass this. Verify: introduce failing test, run sync → non-zero exit with test output.
4. **Backup created on every sync.** `hooks.bak/` at installed path contains all pre-sync `.sh` files. Verify: run sync → `hooks.bak/` exists with correct file count.
5. **Broken hook recoverable via Bash.** A broken installed hook can be repaired using `cp` from `hooks.bak/` through the Bash tool. Verify: break hook, confirm Write/Edit blocked, Bash cp, confirm Write/Edit unblocked.
6. **TDD-sensitive hooks have test coverage.** `test-hooks.sh` covers `test-guardian.sh` and `auto-test-runner.sh` code paths. Verify: `bash tests/test-hooks.sh` runs and reports per-hook results.
7. **Symlinks detected at session start.** Symlinked installed hooks produce a warning. Verify: symlink a hook, start session → output contains "symlink".
8. **fix-sweetclaude repairs symlinks.** Symlinked hooks replaced with regular file copies. Verify: symlink exists → invoke fix → `[ -L hook ]` returns false.
9. **Hook dev workflow documented.** `docs/user-guide/hook-development.md` covers logic testing, regression testing, sync timing, recovery. Verify: file exists and is git-tracked.
10. **Zero manual rules.** All three carve-outs are machine-enforced or machine-detected. Verify: no step in the documented workflow requires the developer to remember a safety rule.

## Release Scope

Stories 300-303 ship in 4.0.9-beta (REL-002). Stories 304-306 are deferred to 4.0.10 — the schema assigns the epic to one release, so deferred stories are tracked here by convention.

## Dependency

EP-010 should be completed before EP-009 stories enter IMPLEMENT phase, since EP-009's workflows will be used on SweetClaude itself.
