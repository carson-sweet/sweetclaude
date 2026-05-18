#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Behavioral tests for scripts/sync-to-installed.sh (STORY-300).
# Phase-aware sync gate: blocks sync during IMPLEMENT, allows otherwise.
# Uses isolated fixture environments with controlled HOME directories.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

TMPROOT=$(mktemp -d)
trap "rm -rf $TMPROOT" EXIT

_make_git_repo() {
  local dir="$1"
  mkdir -p "$dir"
  git -C "$dir" init -q 2>/dev/null
}

_make_install_fixture() {
  local home_dir="$1"
  local install_dir="$2"
  mkdir -p "$install_dir/hooks"
  mkdir -p "$home_dir/.claude/plugins"
  printf '%s\n' "{\"plugins\": {\"sweetclaude\": [{\"installPath\": \"$install_dir\", \"scope\": \"user\", \"lastUpdated\": \"2026-01-01T00:00:00Z\"}]}}" \
    > "$home_dir/.claude/plugins/installed_plugins.json"
}

SCRIPT="$REPO_ROOT/scripts/sync-to-installed.sh"

# ---------------------------------------------------------------------------
# Test 1 (300-1): script exists
# ---------------------------------------------------------------------------
echo "[1] scripts/sync-to-installed.sh exists"

if [ -f "$SCRIPT" ]; then
  pass "script exists at scripts/sync-to-installed.sh"
else
  fail "scripts/sync-to-installed.sh does not exist"
fi

# ---------------------------------------------------------------------------
# Test 2 (300-1): script is executable
# ---------------------------------------------------------------------------
echo "[2] scripts/sync-to-installed.sh is executable"

if [ -x "$SCRIPT" ]; then
  pass "script is executable"
else
  fail "scripts/sync-to-installed.sh is not executable"
fi

# ---------------------------------------------------------------------------
# Test 3 (300-2): sync blocked when phase.yaml contains "phase: implement"
# ---------------------------------------------------------------------------
echo "[3] sync blocked when phase.yaml contains phase: implement"

FX3_HOME="$TMPROOT/home3"
FX3_INSTALL="$FX3_HOME/.claude/plugins/cache/test-install"
FX3_PROJ="$TMPROOT/proj3"

_make_git_repo "$FX3_PROJ"
_make_install_fixture "$FX3_HOME" "$FX3_INSTALL"
mkdir -p "$FX3_PROJ/.sweetclaude/state"
printf 'phase: implement\n' > "$FX3_PROJ/.sweetclaude/state/phase.yaml"

EXIT3=0
STDERR3=$(cd "$FX3_PROJ" && HOME="$FX3_HOME" bash "$SCRIPT" 2>&1 >/dev/null) || EXIT3=$?

if [ "$EXIT3" -eq 1 ]; then
  pass "exit code is 1 when phase is implement"
else
  fail "expected exit code 1 when phase is implement, got $EXIT3"
fi

if printf '%s' "$STDERR3" | grep -qi "IMPLEMENT"; then
  pass "stderr contains IMPLEMENT"
else
  fail "stderr does not contain IMPLEMENT (got: $(printf '%s' "$STDERR3" | head -c 200))"
fi

# ---------------------------------------------------------------------------
# Test 4 (300-3): sync blocked when phase.yaml contains "phase: IMPLEMENT" (uppercase)
# ---------------------------------------------------------------------------
echo "[4] sync blocked when phase.yaml contains phase: IMPLEMENT (uppercase)"

FX4_HOME="$TMPROOT/home4"
FX4_INSTALL="$FX4_HOME/.claude/plugins/cache/test-install"
FX4_PROJ="$TMPROOT/proj4"

_make_git_repo "$FX4_PROJ"
_make_install_fixture "$FX4_HOME" "$FX4_INSTALL"
mkdir -p "$FX4_PROJ/.sweetclaude/state"
printf 'phase: IMPLEMENT\n' > "$FX4_PROJ/.sweetclaude/state/phase.yaml"

EXIT4=0
STDERR4=$(cd "$FX4_PROJ" && HOME="$FX4_HOME" bash "$SCRIPT" 2>&1 >/dev/null) || EXIT4=$?

if [ "$EXIT4" -eq 1 ]; then
  pass "exit code is 1 when phase is IMPLEMENT (uppercase)"
else
  fail "expected exit code 1 when phase is IMPLEMENT (uppercase), got $EXIT4"
fi

if printf '%s' "$STDERR4" | grep -qi "IMPLEMENT"; then
  pass "stderr contains IMPLEMENT (uppercase case)"
else
  fail "stderr does not contain IMPLEMENT (got: $(printf '%s' "$STDERR4" | head -c 200))"
fi

# ---------------------------------------------------------------------------
# Test 5 (300-4): sync proceeds when no phase file exists
# ---------------------------------------------------------------------------
echo "[5] sync proceeds when no phase file exists (--dry-run)"

FX5_HOME="$TMPROOT/home5"
FX5_INSTALL="$FX5_HOME/.claude/plugins/cache/test-install"
FX5_PROJ="$TMPROOT/proj5"

_make_git_repo "$FX5_PROJ"
_make_install_fixture "$FX5_HOME" "$FX5_INSTALL"
mkdir -p "$FX5_PROJ/.sweetclaude/state"

EXIT5=0
(cd "$FX5_PROJ" && HOME="$FX5_HOME" bash "$SCRIPT" --dry-run >/dev/null 2>&1) || EXIT5=$?

if [ "$EXIT5" -eq 0 ]; then
  pass "exit code is 0 when no phase file exists"
else
  fail "expected exit code 0 with no phase file, got $EXIT5"
fi

# ---------------------------------------------------------------------------
# Test 6 (300-5): sync proceeds when phase is "verify"
# ---------------------------------------------------------------------------
echo "[6] sync proceeds when phase is verify (--dry-run)"

FX6_HOME="$TMPROOT/home6"
FX6_INSTALL="$FX6_HOME/.claude/plugins/cache/test-install"
FX6_PROJ="$TMPROOT/proj6"

_make_git_repo "$FX6_PROJ"
_make_install_fixture "$FX6_HOME" "$FX6_INSTALL"
mkdir -p "$FX6_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX6_PROJ/.sweetclaude/state/phase.yaml"

EXIT6=0
(cd "$FX6_PROJ" && HOME="$FX6_HOME" bash "$SCRIPT" --dry-run >/dev/null 2>&1) || EXIT6=$?

if [ "$EXIT6" -eq 0 ]; then
  pass "exit code is 0 when phase is verify"
else
  fail "expected exit code 0 when phase is verify, got $EXIT6"
fi

# ---------------------------------------------------------------------------
# Test 7 (300-6): --force overrides phase check
# ---------------------------------------------------------------------------
echo "[7] --force overrides phase check"

FX7_HOME="$TMPROOT/home7"
FX7_INSTALL="$FX7_HOME/.claude/plugins/cache/test-install"
FX7_PROJ="$TMPROOT/proj7"

_make_git_repo "$FX7_PROJ"
_make_install_fixture "$FX7_HOME" "$FX7_INSTALL"
mkdir -p "$FX7_PROJ/.sweetclaude/state"
printf 'phase: implement\n' > "$FX7_PROJ/.sweetclaude/state/phase.yaml"
printf '| # | Date | Phase | Decision | Rationale |\n| --- | --- | --- | --- | --- |\n| 1 | 2026-01-01 | plan | initial | setup |\n' \
  > "$FX7_PROJ/.sweetclaude/state/decision-log.md"

EXIT7=0
(cd "$FX7_PROJ" && HOME="$FX7_HOME" bash "$SCRIPT" --force >/dev/null 2>&1) || EXIT7=$?

if [ "$EXIT7" -eq 0 ]; then
  pass "--force exit code is 0 even when phase is implement"
else
  fail "expected exit code 0 with --force during implement, got $EXIT7"
fi

HOOK_COUNT_7=$(find "$FX7_INSTALL/hooks" -name "*.sh" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$HOOK_COUNT_7" -gt 0 ]; then
  pass "--force actually synced hook files to installed path ($HOOK_COUNT_7 .sh files)"
else
  fail "no .sh files found at installed path after --force sync"
fi

# ---------------------------------------------------------------------------
# Test 8 (300-7a): --force appends entry to decision log on actual sync
# ---------------------------------------------------------------------------
echo "[8] --force appends entry to decision-log.md with today's date"

FX8_HOME="$TMPROOT/home8"
FX8_INSTALL="$FX8_HOME/.claude/plugins/cache/test-install"
FX8_PROJ="$TMPROOT/proj8"

_make_git_repo "$FX8_PROJ"
_make_install_fixture "$FX8_HOME" "$FX8_INSTALL"
mkdir -p "$FX8_PROJ/.sweetclaude/state"
printf 'phase: implement\n' > "$FX8_PROJ/.sweetclaude/state/phase.yaml"
printf '| # | Date | Phase | Decision | Rationale |\n| --- | --- | --- | --- | --- |\n| 1 | 2026-01-01 | plan | initial | setup |\n' \
  > "$FX8_PROJ/.sweetclaude/state/decision-log.md"

ROWS_BEFORE=$(grep -c '^|' "$FX8_PROJ/.sweetclaude/state/decision-log.md" || true)

(cd "$FX8_PROJ" && HOME="$FX8_HOME" bash "$SCRIPT" --force >/dev/null 2>&1) || true

ROWS_AFTER=$(grep -c '^|' "$FX8_PROJ/.sweetclaude/state/decision-log.md" || true)
TODAY=$(date +%Y-%m-%d)

if [ "$ROWS_AFTER" -gt "$ROWS_BEFORE" ]; then
  pass "decision-log.md has a new row after --force"
else
  fail "decision-log.md row count did not increase (before: $ROWS_BEFORE, after: $ROWS_AFTER)"
fi

if grep -q "$TODAY" "$FX8_PROJ/.sweetclaude/state/decision-log.md"; then
  pass "new row contains today's date ($TODAY)"
else
  fail "new row does not contain today's date ($TODAY)"
fi

if grep -qi "force" "$FX8_PROJ/.sweetclaude/state/decision-log.md"; then
  pass "new row contains force or Force"
else
  fail "new row does not contain force/Force"
fi

# ---------------------------------------------------------------------------
# Test 9 (300-7b): --force --dry-run does NOT append to decision log
# ---------------------------------------------------------------------------
echo "[9] --force --dry-run does NOT append to decision-log.md"

FX9_HOME="$TMPROOT/home9"
FX9_INSTALL="$FX9_HOME/.claude/plugins/cache/test-install"
FX9_PROJ="$TMPROOT/proj9"

_make_git_repo "$FX9_PROJ"
_make_install_fixture "$FX9_HOME" "$FX9_INSTALL"
mkdir -p "$FX9_PROJ/.sweetclaude/state"
printf 'phase: implement\n' > "$FX9_PROJ/.sweetclaude/state/phase.yaml"
printf '| # | Date | Phase | Decision | Rationale |\n| --- | --- | --- | --- | --- |\n| 1 | 2026-01-01 | plan | initial | setup |\n' \
  > "$FX9_PROJ/.sweetclaude/state/decision-log.md"

CHECKSUM9_BEFORE=$(md5 -q "$FX9_PROJ/.sweetclaude/state/decision-log.md" 2>/dev/null \
  || md5sum "$FX9_PROJ/.sweetclaude/state/decision-log.md" 2>/dev/null | cut -d' ' -f1)

EXIT9=0
(cd "$FX9_PROJ" && HOME="$FX9_HOME" bash "$SCRIPT" --force --dry-run >/dev/null 2>&1) || EXIT9=$?

if [ "$EXIT9" -eq 0 ]; then
  pass "--force --dry-run exit code is 0"
else
  fail "expected exit code 0 with --force --dry-run, got $EXIT9"
fi

CHECKSUM9_AFTER=$(md5 -q "$FX9_PROJ/.sweetclaude/state/decision-log.md" 2>/dev/null \
  || md5sum "$FX9_PROJ/.sweetclaude/state/decision-log.md" 2>/dev/null | cut -d' ' -f1)

if [ "$CHECKSUM9_BEFORE" = "$CHECKSUM9_AFTER" ]; then
  pass "decision-log.md unchanged with --force --dry-run"
else
  fail "decision-log.md was modified with --force --dry-run (should not be)"
fi

# ---------------------------------------------------------------------------
# Test 10 (300-9): sync blocked when sweetclaude.yaml has work.active.phase implement
# ---------------------------------------------------------------------------
echo "[10] sync blocked when sweetclaude.yaml has work.active.phase: implement"

FX10_HOME="$TMPROOT/home10"
FX10_INSTALL="$FX10_HOME/.claude/plugins/cache/test-install"
FX10_PROJ="$TMPROOT/proj10"

_make_git_repo "$FX10_PROJ"
_make_install_fixture "$FX10_HOME" "$FX10_INSTALL"
mkdir -p "$FX10_PROJ/.sweetclaude/state"
printf 'schema_version: 2\nwork:\n  active:\n    phase: implement\n' \
  > "$FX10_PROJ/.sweetclaude/state/sweetclaude.yaml"

EXIT10=0
STDERR10=$(cd "$FX10_PROJ" && HOME="$FX10_HOME" bash "$SCRIPT" 2>&1 >/dev/null) || EXIT10=$?

if [ "$EXIT10" -eq 1 ]; then
  pass "exit code is 1 when sweetclaude.yaml has work.active.phase: implement"
else
  fail "expected exit code 1 for sweetclaude.yaml implement phase, got $EXIT10"
fi

if printf '%s' "$STDERR10" | grep -qi "IMPLEMENT"; then
  pass "stderr contains IMPLEMENT (sweetclaude.yaml path)"
else
  fail "stderr does not contain IMPLEMENT (got: $(printf '%s' "$STDERR10" | head -c 200))"
fi

# ---------------------------------------------------------------------------
# Test 11 (300-10): --dry-run runs checks without syncing
# ---------------------------------------------------------------------------
echo "[11] --dry-run runs checks without syncing, stdout contains 'Dry run'"

FX11_HOME="$TMPROOT/home11"
FX11_INSTALL="$FX11_HOME/.claude/plugins/cache/test-install"
FX11_PROJ="$TMPROOT/proj11"

_make_git_repo "$FX11_PROJ"
_make_install_fixture "$FX11_HOME" "$FX11_INSTALL"
mkdir -p "$FX11_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX11_PROJ/.sweetclaude/state/phase.yaml"

printf 'placeholder-hook.sh' > "$FX11_INSTALL/hooks/old-hook.sh"
CHECKSUM11_BEFORE=$(md5 -q "$FX11_INSTALL/hooks/old-hook.sh" 2>/dev/null \
  || md5sum "$FX11_INSTALL/hooks/old-hook.sh" 2>/dev/null | cut -d' ' -f1)

EXIT11=0
STDOUT11=$(cd "$FX11_PROJ" && HOME="$FX11_HOME" bash "$SCRIPT" --dry-run 2>/dev/null) || EXIT11=$?

if [ "$EXIT11" -eq 0 ]; then
  pass "--dry-run exit code is 0"
else
  fail "expected exit code 0 with --dry-run, got $EXIT11"
fi

if printf '%s' "$STDOUT11" | grep -qi "dry run"; then
  pass "stdout contains 'Dry run'"
else
  fail "stdout does not contain 'Dry run' (got: $(printf '%s' "$STDOUT11" | head -c 200))"
fi

CHECKSUM11_AFTER=$(md5 -q "$FX11_INSTALL/hooks/old-hook.sh" 2>/dev/null \
  || md5sum "$FX11_INSTALL/hooks/old-hook.sh" 2>/dev/null | cut -d' ' -f1)

if [ "$CHECKSUM11_BEFORE" = "$CHECKSUM11_AFTER" ]; then
  pass "no files at installed path were modified by --dry-run"
else
  fail "files at installed path were modified during --dry-run (should not be)"
fi

# ---------------------------------------------------------------------------
# Test 12 (300-12): unknown argument produces error
# ---------------------------------------------------------------------------
echo "[12] unknown argument --bogus produces non-zero exit and stderr 'Unknown argument'"

FX12_HOME="$TMPROOT/home12"
FX12_INSTALL="$FX12_HOME/.claude/plugins/cache/test-install"
FX12_PROJ="$TMPROOT/proj12"

_make_git_repo "$FX12_PROJ"
_make_install_fixture "$FX12_HOME" "$FX12_INSTALL"
mkdir -p "$FX12_PROJ/.sweetclaude/state"

EXIT12=0
STDERR12=$(cd "$FX12_PROJ" && HOME="$FX12_HOME" bash "$SCRIPT" --bogus 2>&1 >/dev/null) || EXIT12=$?

if [ "$EXIT12" -ne 0 ]; then
  pass "exit code is non-zero for unknown argument --bogus"
else
  fail "expected non-zero exit code for --bogus, got 0"
fi

if printf '%s' "$STDERR12" | grep -qi "Unknown argument"; then
  pass "stderr contains 'Unknown argument'"
else
  fail "stderr does not contain 'Unknown argument' (got: $(printf '%s' "$STDERR12" | head -c 200))"
fi

# ---------------------------------------------------------------------------
# Test 13 (300-13): path resolution failure produces exit code 5
# ---------------------------------------------------------------------------
echo "[13] missing installed_plugins.json produces exit code 5"

FX13_HOME="$TMPROOT/home13"
FX13_PROJ="$TMPROOT/proj13"

_make_git_repo "$FX13_PROJ"
mkdir -p "$FX13_HOME/.claude"

EXIT13=0
(cd "$FX13_PROJ" && HOME="$FX13_HOME" bash "$SCRIPT" --dry-run >/dev/null 2>&1) || EXIT13=$?

if [ "$EXIT13" -eq 5 ]; then
  pass "exit code is 5 when installed_plugins.json does not exist"
else
  fail "expected exit code 5 for missing installed_plugins.json, got $EXIT13"
fi

# ---------------------------------------------------------------------------
# Test 14 (300-14): phase.yaml takes precedence over sweetclaude.yaml
# ---------------------------------------------------------------------------
echo "[14] phase.yaml (verify) takes precedence over sweetclaude.yaml (implement)"

FX14_HOME="$TMPROOT/home14"
FX14_INSTALL="$FX14_HOME/.claude/plugins/cache/test-install"
FX14_PROJ="$TMPROOT/proj14"

_make_git_repo "$FX14_PROJ"
_make_install_fixture "$FX14_HOME" "$FX14_INSTALL"
mkdir -p "$FX14_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX14_PROJ/.sweetclaude/state/phase.yaml"
printf 'schema_version: 2\nwork:\n  active:\n    phase: implement\n' \
  > "$FX14_PROJ/.sweetclaude/state/sweetclaude.yaml"

EXIT14=0
(cd "$FX14_PROJ" && HOME="$FX14_HOME" bash "$SCRIPT" --dry-run >/dev/null 2>&1) || EXIT14=$?

if [ "$EXIT14" -eq 0 ]; then
  pass "exit code is 0 — phase.yaml (verify) wins over sweetclaude.yaml (implement)"
else
  fail "expected exit code 0 when phase.yaml says verify, got $EXIT14 (sweetclaude.yaml implement leaked through)"
fi

# ---------------------------------------------------------------------------
# Test 15 (300-15): sweetclaude.yaml with non-implement phase allows sync
# ---------------------------------------------------------------------------
echo "[15] sweetclaude.yaml with phase: verify allows sync (--dry-run)"

FX15_HOME="$TMPROOT/home15"
FX15_INSTALL="$FX15_HOME/.claude/plugins/cache/test-install"
FX15_PROJ="$TMPROOT/proj15"

_make_git_repo "$FX15_PROJ"
_make_install_fixture "$FX15_HOME" "$FX15_INSTALL"
mkdir -p "$FX15_PROJ/.sweetclaude/state"
printf 'schema_version: 2\nwork:\n  active:\n    phase: verify\n' \
  > "$FX15_PROJ/.sweetclaude/state/sweetclaude.yaml"

EXIT15=0
(cd "$FX15_PROJ" && HOME="$FX15_HOME" bash "$SCRIPT" --dry-run >/dev/null 2>&1) || EXIT15=$?

if [ "$EXIT15" -eq 0 ]; then
  pass "exit code is 0 when sweetclaude.yaml phase is verify"
else
  fail "expected exit code 0 for sweetclaude.yaml verify phase, got $EXIT15"
fi

# ---------------------------------------------------------------------------
# Test 16 (300-16): --force without decision-log.md does not error
# ---------------------------------------------------------------------------
echo "[16] --force without decision-log.md does not error"

FX16_HOME="$TMPROOT/home16"
FX16_INSTALL="$FX16_HOME/.claude/plugins/cache/test-install"
FX16_PROJ="$TMPROOT/proj16"

_make_git_repo "$FX16_PROJ"
_make_install_fixture "$FX16_HOME" "$FX16_INSTALL"
mkdir -p "$FX16_PROJ/.sweetclaude/state"
printf 'phase: implement\n' > "$FX16_PROJ/.sweetclaude/state/phase.yaml"

EXIT16=0
(cd "$FX16_PROJ" && HOME="$FX16_HOME" bash "$SCRIPT" --force >/dev/null 2>&1) || EXIT16=$?

if [ "$EXIT16" -eq 0 ]; then
  pass "--force works without decision-log.md present"
else
  fail "expected exit code 0 with --force and no decision-log.md, got $EXIT16"
fi

# ---------------------------------------------------------------------------
# Test 17 (300-17): --dry-run does not create new files at installed path
# ---------------------------------------------------------------------------
echo "[17] --dry-run does not create new files at installed path"

FX17_HOME="$TMPROOT/home17"
FX17_INSTALL="$FX17_HOME/.claude/plugins/cache/test-install"
FX17_PROJ="$TMPROOT/proj17"

_make_git_repo "$FX17_PROJ"
_make_install_fixture "$FX17_HOME" "$FX17_INSTALL"
mkdir -p "$FX17_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX17_PROJ/.sweetclaude/state/phase.yaml"

COUNT17_BEFORE=$(find "$FX17_INSTALL" -type f 2>/dev/null | wc -l | tr -d ' ')

EXIT17=0
(cd "$FX17_PROJ" && HOME="$FX17_HOME" bash "$SCRIPT" --dry-run >/dev/null 2>&1) || EXIT17=$?

COUNT17_AFTER=$(find "$FX17_INSTALL" -type f 2>/dev/null | wc -l | tr -d ' ')

if [ "$COUNT17_BEFORE" = "$COUNT17_AFTER" ]; then
  pass "no new files created at installed path during --dry-run"
else
  fail "file count changed at installed path during --dry-run (before: $COUNT17_BEFORE, after: $COUNT17_AFTER)"
fi

# ---------------------------------------------------------------------------
echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "FAILURES: $FAILED"
  exit 1
fi
