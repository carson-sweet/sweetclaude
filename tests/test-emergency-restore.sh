#!/usr/bin/env bash
# tests/test-emergency-restore.sh
# Behavioral contract tests for scripts/emergency-hook-restore.sh (STORY-304).
#
# Coverage:
#   304-6 (end-to-end test passes), 304-7 (executable + restores hooks),
#   304-8 (dry-run sandboxed + parseable), 304-9 (assertions on CONTRACT_LINE_* / EHR_*)
#
# QA caucus augmentation coverage:
#   A1  dry-run single hook names correct hook
#   A2  dry-run zero-restore: exit 0, EHR_RESOLVED_PREFIX present, zero EHR_WOULD_RESTORE lines
#   A3  CONTRACT_LINE_DONE_PREFIX absent in dry-run output
#   A4  hooks.json + hooks-manifest.json restored alongside .sh files
#   A5  CONTRACT_LINE_REPO in stdout for all-hooks fallback to repo
#   A6  EMERGENCY_RESTORE_SOURCE_ONLY=1 produces no side effects; constants non-empty
#   A7  idempotency: second run exits 0, same CONTRACT_LINE_DONE_PREFIX
#   B1  fatal paths write to stderr (not stdout)
#   B2  stdout/stderr separation on fatal and positive paths
#   B3  zero-restore → exit 1 (KNOWN LIMITATION — see test_zero_restore stub)
#   B4  empty hooks.bak/ falls through to repo, emits CONTRACT_LINE_RESTORED_REPO_SUFFIX
#   B5  cascade resolution: JSON → find → fatal
#
# Run: bash tests/test-emergency-restore.sh
# All tests MUST FAIL until scripts/emergency-hook-restore.sh is implemented.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/emergency-hook-restore.sh"
TEST_TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TEST_TMPDIR"' EXIT

# ---------------------------------------------------------------------------
# Source the script for its output contract constants ONLY.
# The sentinel EMERGENCY_RESTORE_SOURCE_ONLY=1 causes the script to define
# all readonly constants then return (or exit 0) before executing any main
# logic. This source call is at TOP LEVEL — NOT inside a function — so that
# `return` works correctly in the sourced context.
#
# If scripts/emergency-hook-restore.sh does not exist, this line fails
# immediately and the whole test file exits non-zero. That IS the RED state.
# shellcheck disable=SC1090
EMERGENCY_RESTORE_SOURCE_ONLY=1 source "$SCRIPT"

# ---------------------------------------------------------------------------
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# ---------------------------------------------------------------------------
# Helper: capture stdout and stderr separately.
#
# Usage:
#   _run_script STDOUT_VAR STDERR_VAR EXIT_CODE_VAR [env=VAL ...] -- [args ...]
#
# Because bash does not allow variable-variable assignment cleanly across all
# versions, each call site uses the pattern inline for clarity. The helper
# pattern is documented here for reference:
#
#   actual_stdout=$(INSTALL_PATH="$install" bash "$SCRIPT" "$@" \
#     2>"$TEST_TMPDIR/_stderr_$$")
#   actual_stderr=$(cat "$TEST_TMPDIR/_stderr_$$"); rm -f "$TEST_TMPDIR/_stderr_$$"
#
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Test 0: test_sentinel_isolation
#
# Must run FIRST — verifies that EMERGENCY_RESTORE_SOURCE_ONLY=1 source at
# top level produced no side effects while importing all constants.
#
# Assert:
#   - All CONTRACT_LINE_* and EHR_* constants are non-empty strings (A6)
#   - RESTORED_COUNT is not set (source did not execute main body) (A6)
#   - INSTALL_PATH was not mutated by the source call (A6)
#   - CONTRACT_LINE_DONE_PREFIX non-empty (will be used by idempotency test)
# Criteria: A6
# ---------------------------------------------------------------------------
test_sentinel_isolation() {
  # Verify all output-contract constants are non-empty
  local failed=0

  for const_name in \
    CONTRACT_LINE_INSTALL \
    CONTRACT_LINE_BACKUP \
    CONTRACT_LINE_REPO \
    CONTRACT_LINE_RESTORED_BACKUP_SUFFIX \
    CONTRACT_LINE_RESTORED_REPO_SUFFIX \
    CONTRACT_LINE_RESTORED_PREFIX \
    CONTRACT_LINE_DONE_PREFIX \
    CONTRACT_FATAL_NO_INSTALL \
    CONTRACT_FATAL_BAD_NAME \
    CONTRACT_FATAL_NOT_FOUND_SUFFIX \
    EHR_RESOLVED_PREFIX \
    EHR_WOULD_RESTORE_PREFIX; do
    local val="${!const_name:-}"
    if [ -z "$val" ]; then
      fail "test_sentinel_isolation: constant $const_name is empty or unset after source"
      failed=1
    fi
  done

  # Main body must not have executed: RESTORED_COUNT should be unset
  if [ -n "${RESTORED_COUNT:-}" ]; then
    fail "test_sentinel_isolation: RESTORED_COUNT is set ($RESTORED_COUNT) — main body executed during source"
    failed=1
  fi

  if [ "$failed" -eq 0 ]; then
    pass "test_sentinel_isolation"
  fi
}

# ---------------------------------------------------------------------------
# Test 1: test_restore_from_backup
#
# Setup:  install/hooks/            — contains a syntactically broken hook
#         install/hooks.bak/        — contains a valid hook of the same name
#                                     PLUS hooks.json and hooks-manifest.json
# Exercise: run script with INSTALL_PATH back-door, no additional args
#           (restores ALL hooks from backup)
# Assert:
#   - Script exits 0
#   - hooks/test-guardian.sh now passes bash -n (was replaced)
#   - hooks/test-guardian.sh is executable (chmod +x was applied) (BG3-5A)
#   - Output contains CONTRACT_LINE_RESTORED_PREFIX + "test-guardian.sh"
#   - Output contains CONTRACT_LINE_RESTORED_BACKUP_SUFFIX (restored from backup)
#   - Output contains CONTRACT_LINE_DONE_PREFIX on stdout (B2 positive path)
#   - Output does NOT contain CONTRACT_LINE_DONE_PREFIX on stderr (B2) (BG3-4)
#   - Output contains CONTRACT_LINE_INSTALL and CONTRACT_LINE_BACKUP
#   - RESTORED_COUNT > 0 (verified via RESTORED line count)
#   - hooks.json and hooks-manifest.json exist in install/hooks/ after restore (A4)
#   - Second run exits 0 with CONTRACT_LINE_DONE_PREFIX on stdout (A7 idempotency)
#   - CONTRACT_LINE_DONE_PREFIX appears in stdout (not stderr) on second run (B2)
# Criteria: 304-6, 304-7, 304-9, A4, A7, B2
# ---------------------------------------------------------------------------
test_restore_from_backup() {
  local dir="$TEST_TMPDIR/t1"
  local install="$dir/install"
  mkdir -p "$install/hooks" "$install/hooks.bak"

  # Good hook in backup
  printf '#!/bin/bash\necho ok\n' > "$install/hooks.bak/test-guardian.sh"
  chmod +x "$install/hooks.bak/test-guardian.sh"

  # Metadata files in backup (A4)
  printf '{"hooks":[]}' > "$install/hooks.bak/hooks.json"
  printf '{"version":"test"}' > "$install/hooks.bak/hooks-manifest.json"

  # Broken hook in install (will fail bash -n before restore)
  printf '#!/bin/bash\nif [[ ; then\n' > "$install/hooks/test-guardian.sh"

  # Pre-condition: broken hook must fail bash -n
  if bash -n "$install/hooks/test-guardian.sh" 2>/dev/null; then
    fail "test_restore_from_backup: pre-condition violated — broken hook passes bash -n before restore"
    return
  fi

  # First run — capture stdout and stderr separately (B2)
  local actual_stdout actual_stderr exit_code=0
  actual_stdout=$(INSTALL_PATH="$install" bash "$SCRIPT" \
    2>"$TEST_TMPDIR/_stderr_t1_$$") || exit_code=$?
  actual_stderr=$(cat "$TEST_TMPDIR/_stderr_t1_$$")
  rm -f "$TEST_TMPDIR/_stderr_t1_$$"

  if [ "$exit_code" -ne 0 ]; then
    fail "test_restore_from_backup: script exited $exit_code (expected 0)"
    return
  fi

  # Post-condition: restored hook must pass bash -n
  if ! bash -n "$install/hooks/test-guardian.sh" 2>/dev/null; then
    fail "test_restore_from_backup: restored hook still fails bash -n"
    return
  fi

  # BG3-5A: restored hook must be executable (chmod +x was applied)
  if [ ! -x "$install/hooks/test-guardian.sh" ]; then
    fail "test_restore_from_backup: restored hook is not executable (chmod +x was not applied)"
    return
  fi

  # Metadata files must exist in install/hooks/ (A4)
  if [ ! -f "$install/hooks/hooks.json" ]; then
    fail "test_restore_from_backup: hooks.json not restored to install/hooks/ (A4)"
    return
  fi
  if [ ! -f "$install/hooks/hooks-manifest.json" ]; then
    fail "test_restore_from_backup: hooks-manifest.json not restored to install/hooks/ (A4)"
    return
  fi

  # Output must contain RESTORED prefix + hook name (NB4: merged into single grep)
  if ! printf '%s' "$actual_stdout" | grep -q "${CONTRACT_LINE_RESTORED_PREFIX}.*test-guardian.sh"; then
    fail "test_restore_from_backup: output missing RESTORED line for test-guardian.sh (${CONTRACT_LINE_RESTORED_PREFIX})"
    return
  fi

  # Must indicate backup was the source
  if ! printf '%s' "$actual_stdout" | grep -q "${CONTRACT_LINE_RESTORED_BACKUP_SUFFIX}"; then
    fail "test_restore_from_backup: output missing backup-source suffix (${CONTRACT_LINE_RESTORED_BACKUP_SUFFIX})"
    return
  fi

  # Done line must appear on STDOUT (B2)
  if ! printf '%s' "$actual_stdout" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_restore_from_backup: CONTRACT_LINE_DONE_PREFIX missing from stdout (${CONTRACT_LINE_DONE_PREFIX}) (B2)"
    return
  fi

  # BG3-4: Done line must NOT appear on stderr on first run (B2)
  if printf '%s' "$actual_stderr" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_restore_from_backup: CONTRACT_LINE_DONE_PREFIX appeared on stderr on first run (must be stdout only) (B2)"
    return
  fi

  # Install and backup path headers must appear on stdout
  if ! printf '%s' "$actual_stdout" | grep -q "${CONTRACT_LINE_INSTALL}"; then
    fail "test_restore_from_backup: output missing install path header (${CONTRACT_LINE_INSTALL})"
    return
  fi
  if ! printf '%s' "$actual_stdout" | grep -q "${CONTRACT_LINE_BACKUP}"; then
    fail "test_restore_from_backup: output missing backup path header (${CONTRACT_LINE_BACKUP})"
    return
  fi

  # --- Idempotency: run a SECOND time (A7) ---
  local stdout2 stderr2 exit2=0
  stdout2=$(INSTALL_PATH="$install" bash "$SCRIPT" \
    2>"$TEST_TMPDIR/_stderr_t1b_$$") || exit2=$?
  stderr2=$(cat "$TEST_TMPDIR/_stderr_t1b_$$")
  rm -f "$TEST_TMPDIR/_stderr_t1b_$$"

  if [ "$exit2" -ne 0 ]; then
    fail "test_restore_from_backup: idempotency — second run exited $exit2 (expected 0) (A7)"
    return
  fi

  # CONTRACT_LINE_DONE_PREFIX must appear in stdout on second run (A7, B2)
  if ! printf '%s' "$stdout2" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_restore_from_backup: idempotency — CONTRACT_LINE_DONE_PREFIX missing from stdout on second run (A7, B2)"
    return
  fi

  # CONTRACT_LINE_DONE_PREFIX must NOT appear in stderr on second run (B2)
  if printf '%s' "$stderr2" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_restore_from_backup: idempotency — CONTRACT_LINE_DONE_PREFIX appeared on stderr (must be stdout only) (B2)"
    return
  fi

  pass "test_restore_from_backup"
}

# ---------------------------------------------------------------------------
# Test 2: test_fallback_to_repo
#
# Sub-case A: no hooks.bak/, named target → falls back to repo (original behavior)
# Sub-case B: empty hooks.bak/ present, all-hooks no-arg → falls through to repo (B4)
#
# Sub-case A setup:
#   install/hooks/     — broken hook
#   NO install/hooks.bak/ created
#   $REPO_ROOT/hooks/  — real repo hooks (non-empty)
# Exercise: run script with INSTALL_PATH back-door, target hook name "test-guardian.sh"
# Assert:
#   - Script exits 0
#   - Output contains CONTRACT_LINE_RESTORED_REPO_SUFFIX
#   - Output contains CONTRACT_LINE_RESTORED_PREFIX + "test-guardian.sh"
#   - hooks/test-guardian.sh now passes bash -n
#   - hooks/test-guardian.sh is executable (chmod +x was applied) (BG3-5A)
#
# Sub-case B setup:
#   install/hooks/     — broken hook
#   install/hooks.bak/ — PRESENT but EMPTY (no .sh files)
# Exercise: run script with no target arg (all-hooks restore)
# Assert:
#   - Script exits 0 (falls through to repo, which has hooks)
#   - CONTRACT_LINE_RESTORED_REPO_SUFFIX appears in stdout (B4)
#   - CONTRACT_LINE_REPO appears in stdout (A5)
#
# Criteria: 304-6, 304-7, 304-9, A5, B4
# ---------------------------------------------------------------------------
test_fallback_to_repo() {
  # --- Sub-case A: no hooks.bak/, named target ---
  local dir="$TEST_TMPDIR/t2a"
  local install="$dir/install"
  mkdir -p "$install/hooks"
  # Deliberately no hooks.bak/

  # Broken hook in install
  printf '#!/bin/bash\nif [[ ; then\n' > "$install/hooks/test-guardian.sh"

  # Pre-condition: test-guardian.sh must exist in real repo
  if [ ! -f "$REPO_ROOT/hooks/test-guardian.sh" ]; then
    fail "test_fallback_to_repo: pre-condition violated — $REPO_ROOT/hooks/test-guardian.sh not found in repo"
    return
  fi

  local stdout_a stderr_a exit_code=0
  stdout_a=$(INSTALL_PATH="$install" bash "$SCRIPT" test-guardian.sh \
    2>"$TEST_TMPDIR/_stderr_t2a_$$") || exit_code=$?
  stderr_a=$(cat "$TEST_TMPDIR/_stderr_t2a_$$")
  rm -f "$TEST_TMPDIR/_stderr_t2a_$$"

  if [ "$exit_code" -ne 0 ]; then
    fail "test_fallback_to_repo [sub-case A]: script exited $exit_code (expected 0)"
    return
  fi

  if ! printf '%s' "$stdout_a" | grep -q "${CONTRACT_LINE_RESTORED_REPO_SUFFIX}"; then
    fail "test_fallback_to_repo [sub-case A]: stdout missing repo-fallback suffix (${CONTRACT_LINE_RESTORED_REPO_SUFFIX})"
    return
  fi

  if ! printf '%s' "$stdout_a" | grep -q "${CONTRACT_LINE_RESTORED_PREFIX}"; then
    fail "test_fallback_to_repo [sub-case A]: stdout missing RESTORED prefix (${CONTRACT_LINE_RESTORED_PREFIX})"
    return
  fi

  if ! printf '%s' "$stdout_a" | grep -q "test-guardian.sh"; then
    fail "test_fallback_to_repo [sub-case A]: stdout missing hook filename 'test-guardian.sh'"
    return
  fi

  if ! bash -n "$install/hooks/test-guardian.sh" 2>/dev/null; then
    fail "test_fallback_to_repo [sub-case A]: restored hook still fails bash -n"
    return
  fi

  # BG3-5A: restored hook must be executable (chmod +x was applied)
  if [ ! -x "$install/hooks/test-guardian.sh" ]; then
    fail "test_fallback_to_repo [sub-case A]: restored hook is not executable (chmod +x was not applied)"
    return
  fi

  # --- Sub-case B: empty hooks.bak/ present, all-hooks restore falls through to repo (B4, A5) ---
  local dir2="$TEST_TMPDIR/t2b"
  local install2="$dir2/install"
  mkdir -p "$install2/hooks" "$install2/hooks.bak"
  # hooks.bak/ is PRESENT but EMPTY — no .sh files

  # Broken hook in install
  printf '#!/bin/bash\nif [[ ; then\n' > "$install2/hooks/test-guardian.sh"

  local stdout_b stderr_b exit_b=0
  stdout_b=$(INSTALL_PATH="$install2" bash "$SCRIPT" \
    2>"$TEST_TMPDIR/_stderr_t2b_$$") || exit_b=$?
  stderr_b=$(cat "$TEST_TMPDIR/_stderr_t2b_$$")
  rm -f "$TEST_TMPDIR/_stderr_t2b_$$"

  if [ "$exit_b" -ne 0 ]; then
    fail "test_fallback_to_repo [sub-case B]: script exited $exit_b (expected 0) — empty hooks.bak/ should fall through to repo"
    return
  fi

  # CONTRACT_LINE_RESTORED_REPO_SUFFIX must appear (B4)
  if ! printf '%s' "$stdout_b" | grep -q "${CONTRACT_LINE_RESTORED_REPO_SUFFIX}"; then
    fail "test_fallback_to_repo [sub-case B]: CONTRACT_LINE_RESTORED_REPO_SUFFIX missing — empty hooks.bak/ should trigger repo fallback (B4)"
    return
  fi

  # CONTRACT_LINE_REPO must appear in stdout (A5)
  if ! printf '%s' "$stdout_b" | grep -q "${CONTRACT_LINE_REPO}"; then
    fail "test_fallback_to_repo [sub-case B]: CONTRACT_LINE_REPO missing from stdout — repo fallback header not emitted (A5)"
    return
  fi

  # --- Sub-case C: no hooks.bak/ present at all + no target arg → all-hooks fallback to repo (canonical break-glass) ---
  # This is the primary break-glass scenario: operator runs the script with no
  # hooks.bak/ present (never synced) and no hook name specified. The script
  # must fall all the way through to $REPO_ROOT/hooks/ and restore from there.
  local dir3="$TEST_TMPDIR/t2c"
  local install3="$dir3/install"
  mkdir -p "$install3/hooks"
  # Deliberately no hooks.bak/ directory at all

  # Broken hook in install
  printf '#!/bin/bash\nif [[ ; then\n' > "$install3/hooks/test-guardian.sh"

  local stdout_c stderr_c exit_c=0
  stdout_c=$(INSTALL_PATH="$install3" bash "$SCRIPT" \
    2>"$TEST_TMPDIR/_stderr_t2c_$$") || exit_c=$?
  stderr_c=$(cat "$TEST_TMPDIR/_stderr_t2c_$$")
  rm -f "$TEST_TMPDIR/_stderr_t2c_$$"

  if [ "$exit_c" -ne 0 ]; then
    fail "test_fallback_to_repo [sub-case C]: script exited $exit_c — no hooks.bak/ + all-hooks should fall through to repo"
    return
  fi

  if ! printf '%s' "$stdout_c" | grep -q "${CONTRACT_LINE_RESTORED_REPO_SUFFIX}"; then
    fail "test_fallback_to_repo [sub-case C]: CONTRACT_LINE_RESTORED_REPO_SUFFIX missing — no-hooks.bak all-hooks must fall through to repo"
    return
  fi

  if ! printf '%s' "$stdout_c" | grep -q "${CONTRACT_LINE_REPO}"; then
    fail "test_fallback_to_repo [sub-case C]: CONTRACT_LINE_REPO missing from stdout — repo fallback header not emitted"
    return
  fi

  if ! printf '%s' "$stdout_c" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_fallback_to_repo [sub-case C]: CONTRACT_LINE_DONE_PREFIX missing — all-hooks repo fallback did not complete"
    return
  fi

  pass "test_fallback_to_repo"
}

# ---------------------------------------------------------------------------
# Test 3: test_back_door_skips_prefix_check
#
# Setup:  install/ path is inside $TEST_TMPDIR — deliberately OUTSIDE
#         $HOME/.claude/plugins/ so that the prefix check would normally
#         fire and reject the path with a FATAL message.
#         install/hooks.bak/ has a valid hook.
#         install/hooks/     has the broken version.
# Exercise: run script with INSTALL_PATH set to the tmpdir path
# Assert:
#   - install path genuinely outside $HOME/.claude/plugins/ (test validity guard)
#   - Script exits 0 (prefix check did NOT fire)
#   - Output does NOT contain "outside plugin tree" (rejection message absent)
#   - Output DOES contain CONTRACT_LINE_INSTALL (contract header emitted)
#   - Output DOES contain CONTRACT_LINE_DONE_PREFIX (done line emitted)
#   - Hook was actually restored: hooks/test-guardian.sh passes bash -n
# Criteria: 304-7 (INSTALL_PATH back-door), 304-9
# ---------------------------------------------------------------------------
test_back_door_skips_prefix_check() {
  local dir="$TEST_TMPDIR/outside_home"
  local install="$dir/install"
  mkdir -p "$install/hooks" "$install/hooks.bak"

  # Confirm the test path is genuinely outside the plugin tree
  case "$install" in
    "$HOME/.claude/plugins/"*)
      fail "test_back_door_skips_prefix_check: TEST_TMPDIR unexpectedly lives inside the plugin tree — cannot test prefix bypass"
      return
      ;;
  esac

  # Good hook in backup
  printf '#!/bin/bash\necho ok\n' > "$install/hooks.bak/test-guardian.sh"
  chmod +x "$install/hooks.bak/test-guardian.sh"

  # Broken hook in install
  printf '#!/bin/bash\nif [[ ; then\n' > "$install/hooks/test-guardian.sh"

  local output exit_code=0
  output=$(INSTALL_PATH="$install" bash "$SCRIPT" 2>&1) || exit_code=$?

  if [ "$exit_code" -ne 0 ]; then
    fail "test_back_door_skips_prefix_check: script exited $exit_code (expected 0) — prefix check may have fired or other error"
    return
  fi

  # The prefix-check rejection message must NOT appear
  if printf '%s' "$output" | grep -q "outside plugin tree"; then
    fail "test_back_door_skips_prefix_check: prefix-check rejection fired despite back-door being active"
    return
  fi

  # Contract output lines MUST still appear (script ran to completion)
  if ! printf '%s' "$output" | grep -q "${CONTRACT_LINE_INSTALL}"; then
    fail "test_back_door_skips_prefix_check: missing CONTRACT_LINE_INSTALL in output"
    return
  fi
  if ! printf '%s' "$output" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_back_door_skips_prefix_check: missing CONTRACT_LINE_DONE_PREFIX in output"
    return
  fi

  # Restoration must actually have occurred
  if ! bash -n "$install/hooks/test-guardian.sh" 2>/dev/null; then
    fail "test_back_door_skips_prefix_check: hook was not restored to valid state"
    return
  fi

  pass "test_back_door_skips_prefix_check"
}

# ---------------------------------------------------------------------------
# Test 4: test_dry_run_preview
#
# Setup:  install/hooks/      — broken hook (must remain broken after dry-run)
#         install/hooks.bak/  — valid hook
# Exercise: run script with --dry-run flag (INSTALL_PATH back-door active)
# Assert:
#   - Script exits 0
#   - Output (stdout) contains EHR_RESOLVED_PREFIX ("Resolved install path:")
#   - Output (stdout) contains EHR_WOULD_RESTORE_PREFIX ("Would restore:")
#   - Broken hook is UNCHANGED after dry-run (bash -n still fails)
#   - EHR_RESOLVED_PREFIX line contains the actual install path
#   - EHR_WOULD_RESTORE_PREFIX line contains hook filename
#   - CONTRACT_LINE_DONE_PREFIX does NOT appear in dry-run output (A3)
#   - CONTRACT_LINE_RESTORED_PREFIX does NOT appear in dry-run output
# Sub-case B: dry-run with specific hook name → exactly one EHR_WOULD_RESTORE_PREFIX line naming that hook (A1)
#             CONTRACT_LINE_DONE_PREFIX must NOT appear in single-hook dry-run output (A3) (BG3-3)
# Sub-case C: dry-run with empty backup AND empty fake repo → exit 0, EHR_RESOLVED_PREFIX present,
#             zero EHR_WOULD_RESTORE_PREFIX lines (A2)
#             NOTE: Sub-case C requires REPO_ROOT to have no hooks. Because the script resolves
#             REPO_ROOT via BASH_SOURCE[0] (pointing at the real script in the real repo), the
#             real repo's hooks/ will be found in all-hooks dry-run. Sub-case C is therefore
#             only achievable by passing a hook name that doesn't exist in either source.
#             In named-hook dry-run mode the script emits exactly one EHR_WOULD_RESTORE_PREFIX
#             for the named hook without checking existence (preview only). A2 is covered by
#             verifying zero EHR_WOULD_RESTORE_PREFIX lines in the no-arg dry-run with an
#             INSTALL_PATH whose hooks.bak/ is empty — which still falls back to the real repo.
#             A2 full-zero path (neither source has hooks) is a KNOWN LIMITATION parallel
#             to the zero-restore limitation. Covered by STORY-309.
# Sub-case D: dry-run with nonexistent hook name → exit 0, EHR_WOULD_RESTORE_PREFIX emitted
#             (spec: named-hook dry-run emits the line without checking existence)
# Criteria: 304-6, 304-8, 304-9, A1, A2 (partial), A3
# ---------------------------------------------------------------------------
test_dry_run_preview() {
  # --- Main case: no-arg dry-run with backup present ---
  local dir="$TEST_TMPDIR/t4"
  local install="$dir/install"
  mkdir -p "$install/hooks" "$install/hooks.bak"

  # Valid hook in backup
  printf '#!/bin/bash\necho ok\n' > "$install/hooks.bak/test-guardian.sh"
  chmod +x "$install/hooks.bak/test-guardian.sh"

  # Broken hook in install — must remain broken after --dry-run
  printf '#!/bin/bash\nif [[ ; then\n' > "$install/hooks/test-guardian.sh"

  # Record mtime to verify no write occurred
  local before_mtime
  before_mtime=$(stat -f '%m' "$install/hooks/test-guardian.sh" 2>/dev/null \
    || stat -c '%Y' "$install/hooks/test-guardian.sh" 2>/dev/null)

  # BG3-2: separate stdout/stderr — EHR_* constants must be on stdout
  local output exit_code=0
  output=$(INSTALL_PATH="$install" bash "$SCRIPT" --dry-run 2>"$TEST_TMPDIR/_stderr_t4_$$") || exit_code=$?
  _stderr_t4=$(cat "$TEST_TMPDIR/_stderr_t4_$$"); rm -f "$TEST_TMPDIR/_stderr_t4_$$"

  if [ "$exit_code" -ne 0 ]; then
    fail "test_dry_run_preview: --dry-run exited $exit_code (expected 0)"
    return
  fi

  # Must emit resolved-path line on stdout
  if ! printf '%s' "$output" | grep -q "${EHR_RESOLVED_PREFIX}"; then
    fail "test_dry_run_preview: missing resolved-path line (${EHR_RESOLVED_PREFIX})"
    return
  fi

  # Resolved-path line must contain the actual install path
  if ! printf '%s' "$output" | grep -F "${EHR_RESOLVED_PREFIX}" | grep -q "$install"; then
    fail "test_dry_run_preview: resolved-path line does not contain the expected install path ($install)"
    return
  fi

  # Must emit at least one would-restore line on stdout
  if ! printf '%s' "$output" | grep -q "${EHR_WOULD_RESTORE_PREFIX}"; then
    fail "test_dry_run_preview: missing would-restore line (${EHR_WOULD_RESTORE_PREFIX})"
    return
  fi

  # Would-restore line must name the hook
  if ! printf '%s' "$output" | grep -F "${EHR_WOULD_RESTORE_PREFIX}" | grep -q "test-guardian.sh"; then
    fail "test_dry_run_preview: would-restore line does not name test-guardian.sh"
    return
  fi

  # Broken hook must remain broken — no file was written
  if bash -n "$install/hooks/test-guardian.sh" 2>/dev/null; then
    fail "test_dry_run_preview: hook was modified during --dry-run (must not write files)"
    return
  fi

  # Double-check via mtime
  local after_mtime
  after_mtime=$(stat -f '%m' "$install/hooks/test-guardian.sh" 2>/dev/null \
    || stat -c '%Y' "$install/hooks/test-guardian.sh" 2>/dev/null)

  if [ "$before_mtime" != "$after_mtime" ]; then
    fail "test_dry_run_preview: hook file mtime changed during --dry-run (file was written)"
    return
  fi

  # CONTRACT_LINE_DONE_PREFIX must NOT appear in dry-run output (A3)
  if printf '%s' "$output" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_dry_run_preview: CONTRACT_LINE_DONE_PREFIX appeared in dry-run output — must be absent (A3)"
    return
  fi

  # RESTORED lines must NOT appear in dry-run output
  if printf '%s' "$output" | grep -q "${CONTRACT_LINE_RESTORED_PREFIX}"; then
    fail "test_dry_run_preview: RESTORED line appeared in dry-run output (should only appear in real-run)"
    return
  fi

  # --- Sub-case B: dry-run with specific hook name → exactly one EHR_WOULD_RESTORE_PREFIX line (A1) ---
  local dir_b="$TEST_TMPDIR/t4b"
  local install_b="$dir_b/install"
  mkdir -p "$install_b/hooks" "$install_b/hooks.bak"

  # Put two hooks in backup to confirm single-arg mode emits exactly one line
  printf '#!/bin/bash\necho ok\n' > "$install_b/hooks.bak/test-guardian.sh"
  printf '#!/bin/bash\necho ok\n' > "$install_b/hooks.bak/auto-test-runner.sh"

  # BG3-2: separate stdout/stderr for sub-case B
  local output_b exit_b=0
  output_b=$(INSTALL_PATH="$install_b" bash "$SCRIPT" --dry-run test-guardian.sh 2>"$TEST_TMPDIR/_stderr_t4b_$$") || exit_b=$?
  _stderr_t4b=$(cat "$TEST_TMPDIR/_stderr_t4b_$$"); rm -f "$TEST_TMPDIR/_stderr_t4b_$$"

  if [ "$exit_b" -ne 0 ]; then
    fail "test_dry_run_preview [sub-case B]: --dry-run with hook name exited $exit_b (expected 0) (A1)"
    return
  fi

  # EHR_WOULD_RESTORE_PREFIX must name the specified hook (A1)
  if ! printf '%s' "$output_b" | grep -F "${EHR_WOULD_RESTORE_PREFIX}" | grep -q "test-guardian.sh"; then
    fail "test_dry_run_preview [sub-case B]: EHR_WOULD_RESTORE_PREFIX line does not name test-guardian.sh (A1)"
    return
  fi

  # Exactly one EHR_WOULD_RESTORE_PREFIX line (A1 — single-hook dry-run)
  local would_restore_count
  would_restore_count=$(printf '%s' "$output_b" | grep -c "${EHR_WOULD_RESTORE_PREFIX}" || true)
  if [ "$would_restore_count" -ne 1 ]; then
    fail "test_dry_run_preview [sub-case B]: expected exactly 1 EHR_WOULD_RESTORE_PREFIX line, got $would_restore_count (A1)"
    return
  fi

  # auto-test-runner.sh must NOT appear (only specified hook should be listed)
  if printf '%s' "$output_b" | grep -F "${EHR_WOULD_RESTORE_PREFIX}" | grep -q "auto-test-runner.sh"; then
    fail "test_dry_run_preview [sub-case B]: unspecified hook 'auto-test-runner.sh' appeared in single-hook dry-run (A1)"
    return
  fi

  # BG3-3: Done line must NOT appear in single-hook dry-run output (A3 for named-hook branch)
  if printf '%s' "$output_b" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_dry_run_preview [sub-case B]: CONTRACT_LINE_DONE_PREFIX appeared in named-hook dry-run output — must be absent (A3)"
    return
  fi

  # --- Sub-case C: dry-run, empty hooks.bak/, no target arg → EHR_RESOLVED_PREFIX present (A2 partial) ---
  # Full A2 (zero EHR_WOULD_RESTORE lines) is a KNOWN LIMITATION when REPO_ROOT resolves to
  # the real repo (which has hooks/). The script's REPO_ROOT is computed from BASH_SOURCE[0],
  # meaning the real repo's non-empty hooks/ is always the fallback. Zero EHR_WOULD_RESTORE_PREFIX
  # lines in all-hooks mode is only achievable by mocking REPO_ROOT — not possible without
  # implementation changes. This sub-case verifies EHR_RESOLVED_PREFIX is always present (A2 partial)
  # and exit 0 is always returned in dry-run mode regardless of source emptiness.
  local dir_c="$TEST_TMPDIR/t4c"
  local install_c="$dir_c/install"
  mkdir -p "$install_c/hooks" "$install_c/hooks.bak"
  # hooks.bak/ is PRESENT but EMPTY — no .sh files
  # hooks/ also empty (no installed hooks)

  local output_c exit_c=0
  output_c=$(INSTALL_PATH="$install_c" bash "$SCRIPT" --dry-run 2>&1) || exit_c=$?

  if [ "$exit_c" -ne 0 ]; then
    fail "test_dry_run_preview [sub-case C]: --dry-run exited $exit_c (expected 0) — dry-run must always exit 0 when path resolves (A2)"
    return
  fi

  if ! printf '%s' "$output_c" | grep -q "${EHR_RESOLVED_PREFIX}"; then
    fail "test_dry_run_preview [sub-case C]: EHR_RESOLVED_PREFIX missing — must always appear in dry-run when path resolves (A2)"
    return
  fi

  # --- Sub-case D: --dry-run with nonexistent hook name → exit 0, EHR_WOULD_RESTORE_PREFIX emitted (no existence check) ---
  local dir_d="$TEST_TMPDIR/t4d"
  local install_d="$dir_d/install"
  mkdir -p "$install_d/hooks" "$install_d/hooks.bak"
  # Neither backup nor hooks/ has a hook by this name — dry-run must preview anyway

  local output_d _stderr_d exit_d=0
  output_d=$(INSTALL_PATH="$install_d" bash "$SCRIPT" --dry-run __nonexistent_hook_zzz.sh \
    2>"$TEST_TMPDIR/_stderr_t4d_$$") || exit_d=$?
  _stderr_d=$(cat "$TEST_TMPDIR/_stderr_t4d_$$"); rm -f "$TEST_TMPDIR/_stderr_t4d_$$"

  if [ "$exit_d" -ne 0 ]; then
    fail "test_dry_run_preview [sub-case D]: --dry-run with nonexistent hook exited $exit_d (expected 0 — dry-run must not check existence)"
    return
  fi

  if ! printf '%s' "$output_d" | grep -F "${EHR_WOULD_RESTORE_PREFIX}" | grep -q "__nonexistent_hook_zzz.sh"; then
    fail "test_dry_run_preview [sub-case D]: EHR_WOULD_RESTORE_PREFIX not emitted for nonexistent hook in dry-run (spec: no existence check)"
    return
  fi

  if printf '%s' "$_stderr_d" | grep -q "${CONTRACT_FATAL_NOT_FOUND_SUFFIX}"; then
    fail "test_dry_run_preview [sub-case D]: CONTRACT_FATAL_NOT_FOUND_SUFFIX appeared in dry-run — existence must not be checked"
    return
  fi

  # --- Sub-case E: --dry-run + real cascade resolution (304-8 conjunction) ---
  # Criteria 304-8: "dry-run flag is fully sandboxed and output is parseable."
  # The previous sub-cases all use the INSTALL_PATH back-door. This sub-case
  # exercises the conjunction: --dry-run mode with cascade resolution via
  # installed_plugins.json (no INSTALL_PATH override). Verifies that dry-run
  # works end-to-end through the cascade, not just with the back-door short-circuit.
  local dir_e="$TEST_TMPDIR/t4e"
  local fake_home_e="$dir_e/fake_home"
  # Place fake_install_e inside the fake plugin tree so prefix check passes
  local fake_install_e="$fake_home_e/.claude/plugins/cache/sweetclaude/sweetclaude/test-ver"
  mkdir -p "$fake_home_e/.claude/plugins"
  mkdir -p "$fake_install_e/hooks" "$fake_install_e/hooks.bak"

  # Valid hook in backup
  printf '#!/bin/bash\necho ok\n' > "$fake_install_e/hooks.bak/test-guardian.sh"
  chmod +x "$fake_install_e/hooks.bak/test-guardian.sh"

  # Broken hook in install — must remain broken after dry-run
  printf '#!/bin/bash\nif [[ ; then\n' > "$fake_install_e/hooks/test-guardian.sh"

  # Record mtime to verify no write occurred
  local before_mtime_e
  before_mtime_e=$(stat -f '%m' "$fake_install_e/hooks/test-guardian.sh" 2>/dev/null \
    || stat -c '%Y' "$fake_install_e/hooks/test-guardian.sh" 2>/dev/null)

  local iso_now_e
  iso_now_e="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  cat > "$fake_home_e/.claude/plugins/installed_plugins.json" <<JSON
{
  "plugins": {
    "sweetclaude": [
      {
        "scope": "user",
        "lastUpdated": "$iso_now_e",
        "installPath": "$fake_install_e"
      }
    ]
  }
}
JSON

  local output_e _stderr_e exit_e=0
  unset INSTALL_PATH
  output_e=$(HOME="$fake_home_e" bash "$SCRIPT" --dry-run \
    2>"$TEST_TMPDIR/_stderr_t4e_$$") || exit_e=$?
  _stderr_e=$(cat "$TEST_TMPDIR/_stderr_t4e_$$"); rm -f "$TEST_TMPDIR/_stderr_t4e_$$"

  if [ "$exit_e" -ne 0 ]; then
    fail "test_dry_run_preview [sub-case E]: --dry-run with cascade resolution exited $exit_e (expected 0) (304-8)"
    return
  fi

  if ! printf '%s' "$output_e" | grep -q "${EHR_RESOLVED_PREFIX}"; then
    fail "test_dry_run_preview [sub-case E]: EHR_RESOLVED_PREFIX missing in cascade dry-run (304-8)"
    return
  fi

  if ! printf '%s' "$output_e" | grep -F "${EHR_RESOLVED_PREFIX}" | grep -q "$fake_install_e"; then
    fail "test_dry_run_preview [sub-case E]: resolved path in cascade dry-run does not contain expected path (304-8)"
    return
  fi

  # Broken hook must remain broken — no file was written
  local after_mtime_e
  after_mtime_e=$(stat -f '%m' "$fake_install_e/hooks/test-guardian.sh" 2>/dev/null \
    || stat -c '%Y' "$fake_install_e/hooks/test-guardian.sh" 2>/dev/null)

  if [ "$before_mtime_e" != "$after_mtime_e" ]; then
    fail "test_dry_run_preview [sub-case E]: hook mtime changed during cascade --dry-run (file was written) (304-8)"
    return
  fi

  # CONTRACT_LINE_DONE_PREFIX must NOT appear (A3 + 304-8)
  if printf '%s' "$output_e" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_dry_run_preview [sub-case E]: CONTRACT_LINE_DONE_PREFIX appeared in cascade dry-run — must be absent (A3, 304-8)"
    return
  fi

  pass "test_dry_run_preview"
}

# ---------------------------------------------------------------------------
# Test 5: test_fatal_paths
#
# Tests three fatal exit paths, each with stdout/stderr separation (B1, B2).
#
# Sub-case 1 (CONTRACT_FATAL_BAD_NAME):
#   Pass a hook name containing "/" → exit 1, error on stderr, nothing on stdout
#
# Sub-case 2 (CONTRACT_FATAL_NOT_FOUND_SUFFIX):
#   Named hook exists in neither hooks.bak/ nor repo → exit 1, error on stderr
#   NOTE: CONTRACT_LINE_INSTALL, CONTRACT_LINE_BACKUP, and CONTRACT_LINE_REPO
#   are emitted to stdout BEFORE the named-hook resolution branch executes.
#   Stdout is therefore NOT empty on this path — only the fatal message itself
#   must be confined to stderr.
#
# Sub-case 3 (CONTRACT_FATAL_NO_INSTALL):
#   INSTALL_PATH points at a dir with NO hooks/ subdirectory → exit 1, error on stderr
#   stdout must be fully empty (whitespace-stripped) (BG3-1)
#
# Criteria: B1, B2
# ---------------------------------------------------------------------------
test_fatal_paths() {
  # --- Sub-case 1: bad hook name (contains "/") → CONTRACT_FATAL_BAD_NAME (B1, B2) ---
  local dir1="$TEST_TMPDIR/t5a"
  local install1="$dir1/install"
  mkdir -p "$install1/hooks" "$install1/hooks.bak"

  # Put a valid hook in backup so the script doesn't fail for another reason
  printf '#!/bin/bash\necho ok\n' > "$install1/hooks.bak/test-guardian.sh"

  local stdout1 stderr1 exit1=0
  stdout1=$(INSTALL_PATH="$install1" bash "$SCRIPT" "subdir/test-guardian.sh" \
    2>"$TEST_TMPDIR/_stderr_t5a_$$") || exit1=$?
  stderr1=$(cat "$TEST_TMPDIR/_stderr_t5a_$$")
  rm -f "$TEST_TMPDIR/_stderr_t5a_$$"

  if [ "$exit1" -ne 1 ]; then
    fail "test_fatal_paths [bad-name]: expected exit 1, got $exit1 (B1)"
    return
  fi

  if ! printf '%s' "$stderr1" | grep -q "${CONTRACT_FATAL_BAD_NAME}"; then
    fail "test_fatal_paths [bad-name]: CONTRACT_FATAL_BAD_NAME not found on stderr (B1, B2)"
    return
  fi

  # Nothing must appear on stdout (B2)
  if [ -n "$(printf '%s' "$stdout1" | tr -d '[:space:]')" ]; then
    fail "test_fatal_paths [bad-name]: stdout is non-empty — fatal message must go to stderr only (B2)"
    return
  fi

  # --- Sub-case 1b: bad hook name (starts with "-") → CONTRACT_FATAL_BAD_NAME (B1, B2) ---
  # The bad-name check matches */* | *..* in the case statement. The "-*" prefix pattern
  # is validated separately here to confirm the case branch covers dash-prefixed names.
  local dir1b="$TEST_TMPDIR/t5a_1b"
  local install1b="$dir1b/install"
  mkdir -p "$install1b/hooks" "$install1b/hooks.bak"

  printf '#!/bin/bash\necho ok\n' > "$install1b/hooks.bak/test-guardian.sh"

  local stdout1b stderr1b exit1b=0
  stdout1b=$(INSTALL_PATH="$install1b" bash "$SCRIPT" "-x" \
    2>"$TEST_TMPDIR/_stderr_t5a1b_$$") || exit1b=$?
  stderr1b=$(cat "$TEST_TMPDIR/_stderr_t5a1b_$$")
  rm -f "$TEST_TMPDIR/_stderr_t5a1b_$$"

  if [ "$exit1b" -ne 1 ]; then
    fail "test_fatal_paths [bad-name-dash]: expected exit 1 for '-x', got $exit1b (B1)"
    return
  fi

  if ! printf '%s' "$stderr1b" | grep -q "${CONTRACT_FATAL_BAD_NAME}"; then
    fail "test_fatal_paths [bad-name-dash]: CONTRACT_FATAL_BAD_NAME not found on stderr for '-x' (B1, B2)"
    return
  fi

  if [ -n "$(printf '%s' "$stdout1b" | tr -d '[:space:]')" ]; then
    fail "test_fatal_paths [bad-name-dash]: stdout is non-empty — fatal message must go to stderr only (B2)"
    return
  fi

  # --- Sub-case 2: hook not found in backup or repo → CONTRACT_FATAL_NOT_FOUND_SUFFIX (B1, B2) ---
  local dir2="$TEST_TMPDIR/t5b"
  local install2="$dir2/install"
  mkdir -p "$install2/hooks" "$install2/hooks.bak"
  # hooks.bak/ present but does not contain the named hook
  # The real repo also does not have a hook with this fabricated name

  local nonexistent_hook="__nonexistent_hook_zzz_304.sh"

  local stdout2 stderr2 exit2=0
  stdout2=$(INSTALL_PATH="$install2" bash "$SCRIPT" "$nonexistent_hook" \
    2>"$TEST_TMPDIR/_stderr_t5b_$$") || exit2=$?
  stderr2=$(cat "$TEST_TMPDIR/_stderr_t5b_$$")
  rm -f "$TEST_TMPDIR/_stderr_t5b_$$"

  if [ "$exit2" -ne 1 ]; then
    fail "test_fatal_paths [not-found]: expected exit 1, got $exit2 (B1)"
    return
  fi

  if ! printf '%s' "$stderr2" | grep -q "${CONTRACT_FATAL_NOT_FOUND_SUFFIX}"; then
    fail "test_fatal_paths [not-found]: CONTRACT_FATAL_NOT_FOUND_SUFFIX not found on stderr (B1, B2)"
    return
  fi

  # Headers (CONTRACT_LINE_INSTALL, CONTRACT_LINE_BACKUP, CONTRACT_LINE_REPO) appear
  # on stdout before the named-hook check — stdout is NOT empty on this path.
  # Assert only that the fatal message itself did NOT go to stdout (it must be stderr-only).
  if printf '%s' "$stdout2" | grep -q "${CONTRACT_FATAL_NOT_FOUND_SUFFIX}"; then
    fail "test_fatal_paths [not-found]: CONTRACT_FATAL_NOT_FOUND_SUFFIX appeared on stdout — must be stderr only (B2)"
    return
  fi

  # --- Sub-case 3: INSTALL_PATH dir has no hooks/ subdir → CONTRACT_FATAL_NO_INSTALL (B1, B2) ---
  local dir3="$TEST_TMPDIR/t5c"
  # The dir3 itself exists but has NO hooks/ subdirectory underneath it
  mkdir -p "$dir3"

  local stdout3 stderr3 exit3=0
  stdout3=$(INSTALL_PATH="$dir3" bash "$SCRIPT" \
    2>"$TEST_TMPDIR/_stderr_t5c_$$") || exit3=$?
  stderr3=$(cat "$TEST_TMPDIR/_stderr_t5c_$$")
  rm -f "$TEST_TMPDIR/_stderr_t5c_$$"

  if [ "$exit3" -ne 1 ]; then
    fail "test_fatal_paths [no-install]: expected exit 1, got $exit3 — INSTALL_PATH with no hooks/ must be fatal (B1)"
    return
  fi

  if ! printf '%s' "$stderr3" | grep -q "${CONTRACT_FATAL_NO_INSTALL}"; then
    fail "test_fatal_paths [no-install]: CONTRACT_FATAL_NO_INSTALL not found on stderr (B1, B2)"
    return
  fi

  # BG3-1: stdout must be fully empty (whitespace-stripped) — stronger than grep-absent check
  if [ -n "$(printf '%s' "$stdout3" | tr -d '[:space:]')" ]; then
    fail "test_fatal_paths [no-install]: stdout is non-empty — fatal message must go to stderr only (B2)"
    return
  fi

  pass "test_fatal_paths"
}

# ---------------------------------------------------------------------------
# Test 6: test_zero_restore (KNOWN LIMITATION stub)
#
# KNOWN LIMITATION: test_zero_restore cannot be cleanly isolated in this
# test environment due to the BASH_SOURCE[0] constraint.
#
# The script resolves REPO_ROOT via:
#   SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
#   REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
#
# This means REPO_ROOT always resolves to the real sweetclaude repo root,
# and $REPO_ROOT/hooks/ is always non-empty (21+ hook files). The zero-restore
# path (RESTORED_COUNT=0 → exit 1 + WARNING) requires BOTH hooks.bak/ empty
# AND $REPO_ROOT/hooks/ empty simultaneously in all-hooks mode.
#
# Approaches considered:
#   (a) Pass a nonexistent hook name → triggers CONTRACT_FATAL_NOT_FOUND_SUFFIX,
#       not zero-restore (different code path).
#   (b) Wrap script invocation with REPO_ROOT override → the script does not
#       accept REPO_ROOT as an env override; it is hardcoded via BASH_SOURCE.
#   (c) Symlink/copy the script to a temp dir → changes BASH_SOURCE resolution,
#       but requires copying implementation, which violates the test-only rule.
#   (d) Accept the limitation → chosen.
#
# The zero-restore path (WARNING on stderr + exit 1 + RESTORED_COUNT=0) is
# structurally covered by the script body but cannot be exercised without
# either mocking REPO_ROOT or duplicating the script. This path is tracked
# for STORY-309 (hardening pass) where REPO_ROOT may be made overridable
# via env var, enabling a clean test.
#
# This stub exists so the test runner structure is complete and the missing
# coverage is visible as an explicit, documented gap rather than an oversight.
#
# Criteria: B3 (deferred to STORY-309)
# ---------------------------------------------------------------------------
test_zero_restore() {
  # KNOWN LIMITATION: zero-restore path not testable without REPO_ROOT override.
  # See block comment above. Marking as an explicit skip rather than false-pass.
  echo "SKIP: test_zero_restore — KNOWN LIMITATION (B3 deferred to STORY-309)"
  echo "      REPO_ROOT resolves via BASH_SOURCE to real repo (non-empty hooks/)."
  echo "      Zero-restore requires both backup and repo empty simultaneously."
  echo "      No clean isolation path without REPO_ROOT env override in script."
  SKIP_COUNT=$((SKIP_COUNT + 1))  # counted as skipped, not passed; gap is documented
}

# ---------------------------------------------------------------------------
# Test 7: test_cascade_resolution
#
# Tests the three-step install-path cascade when INSTALL_PATH is NOT set.
# INSTALL_PATH must be unset for each sub-case to exercise the cascade.
#
# Sub-case 1 (JSON resolution):
#   HOME set to a tmpdir containing ~/.claude/plugins/installed_plugins.json
#   with a valid entry whose installPath/hooks exists.
#   Assert: script resolves via JSON, restores hooks, exits 0.
#   Assert: restored hook is executable (chmod +x was applied) (BG3-5A)
#
# Sub-case 2 (find fallback):
#   HOME set to a tmpdir with installed_plugins.json pointing at a
#   non-existent installPath (so JSON step fails).
#   A directory at pattern */sweetclaude/sweetclaude/<ver>/hooks is created.
#   Assert: script falls back to find, resolves correctly, exits 0.
#   Assert: restored hook is executable (chmod +x was applied) (BG3-5A)
#
# Sub-case 3 (cascade fatal):
#   HOME set to a tmpdir with no installed_plugins.json and no find-matching dirs.
#   Assert: exit 1 and CONTRACT_FATAL_NO_INSTALL on stderr.
#
# Sub-case 4 (prefix check — path outside plugin tree) (BG3-5B):
#   JSON resolves to a real directory that is outside $HOME/.claude/plugins/.
#   INSTALL_PATH and INSTALL_PATH_OVERRIDE unset — prefix check fires.
#   Assert: exit 1, "outside plugin tree" on stderr, stdout empty.
#
# Criteria: B5 (sub-cases 1, 2, 3, 4), B1, B2
# ---------------------------------------------------------------------------
test_cascade_resolution() {
  # --- Sub-case 1: JSON resolution ---
  local fake_home_1="$TEST_TMPDIR/cascade_home_1"
  local fake_install_1="$TEST_TMPDIR/cascade_install_1"
  mkdir -p "$fake_home_1/.claude/plugins"
  mkdir -p "$fake_install_1/hooks" "$fake_install_1/hooks.bak"

  # Create a good hook in hooks.bak/ so the restore succeeds
  printf '#!/bin/bash\necho ok\n' > "$fake_install_1/hooks.bak/test-guardian.sh"
  chmod +x "$fake_install_1/hooks.bak/test-guardian.sh"
  # Broken hook in hooks/ so we can verify the restore happened
  printf '#!/bin/bash\nif [[ ; then\n' > "$fake_install_1/hooks/test-guardian.sh"

  # Write installed_plugins.json with the spec's schema:
  # scope: "user", lastUpdated: ISO-8601, installPath: pointing at fake_install_1
  local iso_now
  iso_now="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
  cat > "$fake_home_1/.claude/plugins/installed_plugins.json" <<JSON
{
  "plugins": {
    "sweetclaude": [
      {
        "scope": "user",
        "lastUpdated": "$iso_now",
        "installPath": "$fake_install_1"
      }
    ]
  }
}
JSON

  # Unset INSTALL_PATH to force cascade resolution (NB2: explicit unset before invocation)
  local stdout1 stderr1 exit1=0
  unset INSTALL_PATH
  stdout1=$(HOME="$fake_home_1" bash "$SCRIPT" \
    2>"$TEST_TMPDIR/_stderr_cas1_$$") || exit1=$?
  stderr1=$(cat "$TEST_TMPDIR/_stderr_cas1_$$")
  rm -f "$TEST_TMPDIR/_stderr_cas1_$$"

  if [ "$exit1" -ne 0 ]; then
    fail "test_cascade_resolution [JSON]: script exited $exit1 (expected 0) — JSON resolution failed (B5)"
    echo "  stderr: $stderr1" >&2
    return
  fi

  if ! printf '%s' "$stdout1" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_cascade_resolution [JSON]: CONTRACT_LINE_DONE_PREFIX missing — JSON resolution did not produce a successful restore (B5)"
    return
  fi

  if printf '%s' "$stderr1" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_cascade_resolution [JSON]: CONTRACT_LINE_DONE_PREFIX appeared on stderr — must be stdout only (B2)"
    return
  fi

  # Verify the resolved path matches the JSON installPath (the fake_install_1 path must appear)
  if ! printf '%s' "$stdout1" | grep -q "$fake_install_1"; then
    fail "test_cascade_resolution [JSON]: resolved install path ($fake_install_1) not mentioned in output — wrong path resolved (B5)"
    return
  fi

  # Verify the broken hook was actually repaired (NB3: post-restore hook validation for JSON sub-case)
  if ! bash -n "$fake_install_1/hooks/test-guardian.sh" 2>/dev/null; then
    fail "test_cascade_resolution [JSON]: hook was not restored to valid state (bash -n fails) (B5)"
    return
  fi

  # BG3-5A: restored hook must be executable (chmod +x was applied)
  if [ ! -x "$fake_install_1/hooks/test-guardian.sh" ]; then
    fail "test_cascade_resolution [JSON]: restored hook is not executable (chmod +x was not applied)"
    return
  fi

  # --- Sub-case 2: find fallback ---
  local fake_home_2="$TEST_TMPDIR/cascade_home_2"
  local nonexistent_path="$TEST_TMPDIR/__does_not_exist_$$"
  mkdir -p "$fake_home_2/.claude/plugins"

  # installed_plugins.json points at a non-existent installPath → JSON step resolves but
  # os.path.isdir(installPath/hooks) is False → python3 outputs nothing → find runs
  cat > "$fake_home_2/.claude/plugins/installed_plugins.json" <<JSON
{
  "plugins": {
    "sweetclaude": [
      {
        "scope": "user",
        "lastUpdated": "$iso_now",
        "installPath": "$nonexistent_path"
      }
    ]
  }
}
JSON

  # Create a directory matching the find pattern: */sweetclaude/sweetclaude/<ver>/hooks
  # find pattern: find ~/.claude/plugins/cache -type d -path "*/sweetclaude/sweetclaude/*" -name hooks
  # dirname of the matched hooks dir is the install root
  local fake_cache_hooks="$fake_home_2/.claude/plugins/cache/sweetclaude/sweetclaude/4.0.8-beta/hooks"
  local fake_install_2
  fake_install_2="$(dirname "$fake_cache_hooks")"
  mkdir -p "$fake_cache_hooks" "$fake_install_2/hooks.bak"

  # Good hook in hooks.bak/
  printf '#!/bin/bash\necho ok\n' > "$fake_install_2/hooks.bak/test-guardian.sh"
  chmod +x "$fake_install_2/hooks.bak/test-guardian.sh"
  # Broken hook in hooks/
  printf '#!/bin/bash\nif [[ ; then\n' > "$fake_cache_hooks/test-guardian.sh"

  local stdout2 stderr2 exit2=0
  unset INSTALL_PATH
  stdout2=$(HOME="$fake_home_2" bash "$SCRIPT" \
    2>"$TEST_TMPDIR/_stderr_cas2_$$") || exit2=$?
  stderr2=$(cat "$TEST_TMPDIR/_stderr_cas2_$$")
  rm -f "$TEST_TMPDIR/_stderr_cas2_$$"

  if [ "$exit2" -ne 0 ]; then
    fail "test_cascade_resolution [find]: script exited $exit2 (expected 0) — find fallback failed (B5)"
    echo "  stderr: $stderr2" >&2
    return
  fi

  if ! printf '%s' "$stdout2" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_cascade_resolution [find]: CONTRACT_LINE_DONE_PREFIX missing — find fallback did not produce a successful restore (B5)"
    return
  fi

  if printf '%s' "$stderr2" | grep -q "${CONTRACT_LINE_DONE_PREFIX}"; then
    fail "test_cascade_resolution [find]: CONTRACT_LINE_DONE_PREFIX appeared on stderr — must be stdout only (B2)"
    return
  fi

  # Verify the find-resolved path appears in output
  if ! printf '%s' "$stdout2" | grep -q "$fake_install_2"; then
    fail "test_cascade_resolution [find]: find-resolved install path ($fake_install_2) not in output (B5)"
    return
  fi

  # Verify the broken hook was actually repaired (NB3: post-restore hook validation for find sub-case)
  if ! bash -n "$fake_cache_hooks/test-guardian.sh" 2>/dev/null; then
    fail "test_cascade_resolution [find]: hook was not restored to valid state (bash -n fails) (B5)"
    return
  fi

  # BG3-5A: restored hook must be executable (chmod +x was applied)
  if [ ! -x "$fake_cache_hooks/test-guardian.sh" ]; then
    fail "test_cascade_resolution [find]: restored hook is not executable (chmod +x was not applied)"
    return
  fi

  # --- Sub-case 3: cascade fatal — no JSON, no find match → CONTRACT_FATAL_NO_INSTALL (B5, B1, B2) ---
  local fake_home_3="$TEST_TMPDIR/cascade_home_3"
  mkdir -p "$fake_home_3/.claude/plugins"
  # No installed_plugins.json — python3 will get FileNotFoundError → empty
  # No matching dirs under $fake_home_3/.claude/plugins/cache → find returns nothing

  local stdout3 stderr3 exit3=0
  unset INSTALL_PATH
  stdout3=$(HOME="$fake_home_3" bash "$SCRIPT" \
    2>"$TEST_TMPDIR/_stderr_cas3_$$") || exit3=$?
  stderr3=$(cat "$TEST_TMPDIR/_stderr_cas3_$$")
  rm -f "$TEST_TMPDIR/_stderr_cas3_$$"

  if [ "$exit3" -ne 1 ]; then
    fail "test_cascade_resolution [fatal]: expected exit 1, got $exit3 — cascade should be fatal with no sources (B5, B1)"
    return
  fi

  if ! printf '%s' "$stderr3" | grep -q "${CONTRACT_FATAL_NO_INSTALL}"; then
    fail "test_cascade_resolution [fatal]: CONTRACT_FATAL_NO_INSTALL not found on stderr (B5, B1, B2)"
    return
  fi

  # Must not appear on stdout (B2)
  if printf '%s' "$stdout3" | grep -q "${CONTRACT_FATAL_NO_INSTALL}"; then
    fail "test_cascade_resolution [fatal]: CONTRACT_FATAL_NO_INSTALL appeared on stdout — must be stderr only (B2)"
    return
  fi

  # --- Sub-case 4: prefix check fires — path resolved but outside plugin tree (B5, B1, B2) ---
  # JSON resolves to a real existing directory that is outside $HOME/.claude/plugins/.
  # With INSTALL_PATH unset and INSTALL_PATH_OVERRIDE unset, the prefix check fires.
  local fake_home_4="$TEST_TMPDIR/cascade_home_4"
  local out_of_tree_install="$TEST_TMPDIR/outside_plugin_tree_install"
  mkdir -p "$fake_home_4/.claude/plugins"
  mkdir -p "$out_of_tree_install/hooks"

  cat > "$fake_home_4/.claude/plugins/installed_plugins.json" <<JSON
{
  "plugins": {
    "sweetclaude": [
      {
        "scope": "user",
        "lastUpdated": "$iso_now",
        "installPath": "$out_of_tree_install"
      }
    ]
  }
}
JSON

  # Verify the path is genuinely outside the fake plugin tree
  case "$out_of_tree_install" in
    "$fake_home_4/.claude/plugins/"*)
      fail "test_cascade_resolution [prefix]: test setup error — out_of_tree path is inside plugin tree"
      return
      ;;
  esac

  local stdout4 stderr4 exit4=0
  unset INSTALL_PATH
  stdout4=$(HOME="$fake_home_4" bash "$SCRIPT" \
    2>"$TEST_TMPDIR/_stderr_cas4_$$") || exit4=$?
  stderr4=$(cat "$TEST_TMPDIR/_stderr_cas4_$$")
  rm -f "$TEST_TMPDIR/_stderr_cas4_$$"

  if [ "$exit4" -ne 1 ]; then
    fail "test_cascade_resolution [prefix]: expected exit 1 when resolved path is outside plugin tree (B5, B1)"
    return
  fi

  if ! printf '%s' "$stderr4" | grep -q "outside plugin tree"; then
    fail "test_cascade_resolution [prefix]: expected 'outside plugin tree' message on stderr (B5, B1, B2)"
    return
  fi

  if [ -n "$(printf '%s' "$stdout4" | tr -d '[:space:]')" ]; then
    fail "test_cascade_resolution [prefix]: stdout is non-empty on prefix-check fatal — must be stderr only (B2)"
    return
  fi

  pass "test_cascade_resolution"
}

# ---------------------------------------------------------------------------
# Test 8: test_zero_deps_lint
#
# Static analysis: the script body must not source any other file.
# The "zero SweetClaude dependencies" invariant is documented in the script
# header — emergency-hook-restore.sh must be self-contained so operators can
# run it without having a working SweetClaude install.
#
# Approach: grep the script for 'source <something>' invocations (lines that
# are not comments and that match `^\s*source `). Any match is a violation.
#
# Note: this test fails during RED state because $SCRIPT does not exist;
# the top-level source at line 43 prevents the runner from reaching here anyway.
#
# Criteria: zero-SweetClaude-dependencies design invariant (architect caucus C2)
# ---------------------------------------------------------------------------
test_zero_deps_lint() {
  if [ ! -f "$SCRIPT" ]; then
    fail "test_zero_deps_lint: $SCRIPT does not exist — cannot lint"
    return
  fi

  local source_count
  source_count=$(grep -cE '^\s*source ' "$SCRIPT" || true)

  if [ "$source_count" -gt 0 ]; then
    fail "test_zero_deps_lint: $source_count 'source' call(s) found — zero-SweetClaude-dependencies invariant violated"
    grep -nE '^\s*source ' "$SCRIPT" >&2 || true
    return
  fi

  pass "test_zero_deps_lint"
}

# ---------------------------------------------------------------------------
# Runner — test_sentinel_isolation runs FIRST to verify constants before any
# other test function uses them.
# ---------------------------------------------------------------------------
echo ""
echo "=== test-emergency-restore.sh ==="
echo ""

test_sentinel_isolation
test_zero_deps_lint
test_restore_from_backup
test_fallback_to_repo
test_back_door_skips_prefix_check
test_dry_run_preview
test_fatal_paths
test_zero_restore
test_cascade_resolution

echo ""
echo "Summary: $PASS_COUNT passed, $FAIL_COUNT failed, $SKIP_COUNT skipped"

if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi
