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

# _make_302_fixture ROOT HOME_DIR INSTALL_DIR TESTS_EXIT_CODE
#
# Sets up a self-contained fake-repo directory at ROOT/fake-repo/ whose
# scripts/sync-to-installed.sh is a copy of the real script, and whose
# tests/test-hooks.sh exits with TESTS_EXIT_CODE (0 = all pass, 1 = failure).
# Also populates ROOT/fake-repo/hooks/ with a minimal .sh file and stubs for
# skills/, config/, and package.json so the non-hook sync section does not
# error.
#
# After calling this, the script to run is: bash "$1/fake-repo/scripts/sync-to-installed.sh"
# with cwd=some project dir and HOME=HOME_DIR.
_make_302_fixture() {
  local root="$1"
  local home_dir="$2"
  local install_dir="$3"
  local tests_exit_code="$4"

  local fake_repo="$root/fake-repo"
  mkdir -p "$fake_repo/scripts"
  mkdir -p "$fake_repo/tests"
  mkdir -p "$fake_repo/hooks"
  mkdir -p "$fake_repo/skills"
  mkdir -p "$fake_repo/config"

  cp "$REPO_ROOT/scripts/sync-to-installed.sh" "$fake_repo/scripts/sync-to-installed.sh"
  chmod +x "$fake_repo/scripts/sync-to-installed.sh"

  printf '#!/bin/bash\necho stub-hook\n' > "$fake_repo/hooks/stub-hook.sh"
  chmod +x "$fake_repo/hooks/stub-hook.sh"

  printf '{"name":"sweetclaude","version":"0.0.0-test"}\n' > "$fake_repo/package.json"

  if [ "$tests_exit_code" -eq 0 ]; then
    cat > "$fake_repo/tests/test-hooks.sh" << 'HOOKEOF'
#!/bin/bash
echo "ALL TESTS PASSED"
exit 0
HOOKEOF
  else
    cat > "$fake_repo/tests/test-hooks.sh" << 'HOOKEOF'
#!/bin/bash
echo "  FAIL: stub test always fails"
echo "FAILURES: 1"
exit 1
HOOKEOF
  fi
  chmod +x "$fake_repo/tests/test-hooks.sh"

  _make_install_fixture "$home_dir" "$install_dir"
  printf '#!/bin/bash\necho pre-existing-hook\n' > "$install_dir/hooks/pre-existing.sh"
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
printf '#!/bin/bash\necho placeholder\n' > "$FX7_INSTALL/hooks/placeholder.sh"
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
printf '#!/bin/bash\necho placeholder\n' > "$FX8_INSTALL/hooks/placeholder.sh"
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
printf '#!/bin/bash\necho placeholder\n' > "$FX16_INSTALL/hooks/placeholder.sh"
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

# ===========================================================================
# STORY-301: Backup-on-sync with rollback support
# ===========================================================================

# ---------------------------------------------------------------------------
# Test 18 (301-1): hooks.bak/ created at installed path after sync
# ---------------------------------------------------------------------------
echo "[18] hooks.bak/ created at installed path after sync"

FX18_HOME="$TMPROOT/home18"
FX18_INSTALL="$FX18_HOME/.claude/plugins/cache/test-install"
FX18_PROJ="$TMPROOT/proj18"

_make_git_repo "$FX18_PROJ"
_make_install_fixture "$FX18_HOME" "$FX18_INSTALL"
mkdir -p "$FX18_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX18_PROJ/.sweetclaude/state/phase.yaml"

printf '#!/bin/bash\necho existing\n' > "$FX18_INSTALL/hooks/existing-hook.sh"

EXIT18=0
(cd "$FX18_PROJ" && HOME="$FX18_HOME" bash "$SCRIPT" >/dev/null 2>&1) || EXIT18=$?

if [ -d "$FX18_INSTALL/hooks.bak" ]; then
  pass "hooks.bak/ exists at installed path after sync"
else
  fail "hooks.bak/ not found at installed path after sync"
fi

# ---------------------------------------------------------------------------
# Test 19 (301-2): hooks.bak/ contains all .sh files from pre-sync hooks
# ---------------------------------------------------------------------------
echo "[19] hooks.bak/ contains all .sh files from pre-sync hooks"

FX19_HOME="$TMPROOT/home19"
FX19_INSTALL="$FX19_HOME/.claude/plugins/cache/test-install"
FX19_PROJ="$TMPROOT/proj19"

_make_git_repo "$FX19_PROJ"
_make_install_fixture "$FX19_HOME" "$FX19_INSTALL"
mkdir -p "$FX19_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX19_PROJ/.sweetclaude/state/phase.yaml"

for i in 1 2 3 4 5; do
  printf '#!/bin/bash\necho hook%d\n' "$i" > "$FX19_INSTALL/hooks/hook-$i.sh"
done

EXIT19=0
(cd "$FX19_PROJ" && HOME="$FX19_HOME" bash "$SCRIPT" >/dev/null 2>&1) || EXIT19=$?

BACKUP_SH_COUNT=$(find "$FX19_INSTALL/hooks.bak" -name "*.sh" -type f 2>/dev/null | wc -l | tr -d ' ')

if [ "$BACKUP_SH_COUNT" -eq 5 ]; then
  pass "hooks.bak/ contains 5 .sh files (matches pre-sync count)"
else
  fail "hooks.bak/ has $BACKUP_SH_COUNT .sh files, expected 5"
fi

# ---------------------------------------------------------------------------
# Test 20 (301-2b): hooks.bak/ includes non-shell files
# ---------------------------------------------------------------------------
echo "[20] hooks.bak/ includes non-shell files (hooks.json)"

FX20_HOME="$TMPROOT/home20"
FX20_INSTALL="$FX20_HOME/.claude/plugins/cache/test-install"
FX20_PROJ="$TMPROOT/proj20"

_make_git_repo "$FX20_PROJ"
_make_install_fixture "$FX20_HOME" "$FX20_INSTALL"
mkdir -p "$FX20_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX20_PROJ/.sweetclaude/state/phase.yaml"

printf '#!/bin/bash\necho h\n' > "$FX20_INSTALL/hooks/placeholder.sh"
printf '{"hooks": []}\n' > "$FX20_INSTALL/hooks/hooks.json"

EXIT20=0
(cd "$FX20_PROJ" && HOME="$FX20_HOME" bash "$SCRIPT" >/dev/null 2>&1) || EXIT20=$?

if [ -f "$FX20_INSTALL/hooks.bak/hooks.json" ]; then
  pass "hooks.bak/ contains hooks.json"
else
  fail "hooks.bak/ missing hooks.json"
fi

# ---------------------------------------------------------------------------
# Test 21 (301-3): backup happens before any hook file is modified (canary)
# ---------------------------------------------------------------------------
echo "[21] backup happens before hooks are modified (canary test)"

FX21_HOME="$TMPROOT/home21"
FX21_INSTALL="$FX21_HOME/.claude/plugins/cache/test-install"
FX21_PROJ="$TMPROOT/proj21"

_make_git_repo "$FX21_PROJ"
_make_install_fixture "$FX21_HOME" "$FX21_INSTALL"
mkdir -p "$FX21_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX21_PROJ/.sweetclaude/state/phase.yaml"

printf '#!/bin/bash\necho h\n' > "$FX21_INSTALL/hooks/placeholder.sh"
printf 'canary-data\n' > "$FX21_INSTALL/hooks/canary.txt"

EXIT21=0
(cd "$FX21_PROJ" && HOME="$FX21_HOME" bash "$SCRIPT" >/dev/null 2>&1) || EXIT21=$?

CANARY_IN_BACKUP=false
CANARY_IN_HOOKS=false
[ -f "$FX21_INSTALL/hooks.bak/canary.txt" ] && CANARY_IN_BACKUP=true
[ -f "$FX21_INSTALL/hooks/canary.txt" ] && CANARY_IN_HOOKS=true

if [ "$CANARY_IN_BACKUP" = true ] && [ "$CANARY_IN_HOOKS" = false ]; then
  pass "canary in hooks.bak/ but not in hooks/ (backup before overwrite confirmed)"
else
  fail "canary: in backup=$CANARY_IN_BACKUP, in hooks=$CANARY_IN_HOOKS (expected true/false)"
fi

# ---------------------------------------------------------------------------
# Test 22 (301-4): previous backup overwritten (single generation)
# ---------------------------------------------------------------------------
echo "[22] previous backup overwritten (single generation)"

FX22_HOME="$TMPROOT/home22"
FX22_INSTALL="$FX22_HOME/.claude/plugins/cache/test-install"
FX22_PROJ="$TMPROOT/proj22"

_make_git_repo "$FX22_PROJ"
_make_install_fixture "$FX22_HOME" "$FX22_INSTALL"
mkdir -p "$FX22_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX22_PROJ/.sweetclaude/state/phase.yaml"

printf '#!/bin/bash\necho h\n' > "$FX22_INSTALL/hooks/placeholder.sh"
printf 'first-canary\n' > "$FX22_INSTALL/hooks/canary-1.txt"

EXIT22a=0
(cd "$FX22_PROJ" && HOME="$FX22_HOME" bash "$SCRIPT" >/dev/null 2>&1) || EXIT22a=$?

printf 'second-canary\n' > "$FX22_INSTALL/hooks/canary-2.txt"

EXIT22b=0
(cd "$FX22_PROJ" && HOME="$FX22_HOME" bash "$SCRIPT" >/dev/null 2>&1) || EXIT22b=$?

HAS_CANARY2=false
HAS_CANARY1=false
[ -f "$FX22_INSTALL/hooks.bak/canary-2.txt" ] && HAS_CANARY2=true
[ -f "$FX22_INSTALL/hooks.bak/canary-1.txt" ] && HAS_CANARY1=true

if [ "$HAS_CANARY2" = true ] && [ "$HAS_CANARY1" = false ]; then
  pass "hooks.bak/ has second-sync state only (single generation)"
else
  fail "hooks.bak/ canary-2=$HAS_CANARY2, canary-1=$HAS_CANARY1 (expected true/false)"
fi

# ---------------------------------------------------------------------------
# Test 23 (301-5): backup failure aborts sync with exit code 3
# ---------------------------------------------------------------------------
echo "[23] backup failure aborts sync with exit code 3"

FX23_HOME="$TMPROOT/home23"
FX23_INSTALL="$FX23_HOME/.claude/plugins/cache/test-install"
FX23_PROJ="$TMPROOT/proj23"

_make_git_repo "$FX23_PROJ"
_make_install_fixture "$FX23_HOME" "$FX23_INSTALL"
mkdir -p "$FX23_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX23_PROJ/.sweetclaude/state/phase.yaml"

printf '#!/bin/bash\necho h\n' > "$FX23_INSTALL/hooks/original.sh"

HOOKS_BEFORE_23=$(find "$FX23_INSTALL/hooks" -type f 2>/dev/null | sort | md5 -q 2>/dev/null || find "$FX23_INSTALL/hooks" -type f 2>/dev/null | sort | md5sum 2>/dev/null | cut -d' ' -f1)

chmod 555 "$FX23_INSTALL"

EXIT23=0
STDERR23=$(cd "$FX23_PROJ" && HOME="$FX23_HOME" bash "$SCRIPT" 2>&1 >/dev/null) || EXIT23=$?

chmod 755 "$FX23_INSTALL"

if [ "$EXIT23" -eq 3 ]; then
  pass "exit code is 3 on backup failure"
else
  fail "exit code is $EXIT23, expected 3"
fi

HOOKS_AFTER_23=$(find "$FX23_INSTALL/hooks" -type f 2>/dev/null | sort | md5 -q 2>/dev/null || find "$FX23_INSTALL/hooks" -type f 2>/dev/null | sort | md5sum 2>/dev/null | cut -d' ' -f1)

if [ "$HOOKS_BEFORE_23" = "$HOOKS_AFTER_23" ]; then
  pass "installed hooks unchanged after backup failure"
else
  fail "installed hooks were modified despite backup failure"
fi

if printf '%s' "$STDERR23" | grep -qiE "Backup failed|Cannot remove"; then
  pass "stderr contains backup failure message"
else
  fail "stderr missing backup failure message (got: $(printf '%s' "$STDERR23" | head -c 200))"
fi

# ---------------------------------------------------------------------------
# Test 24 (301-empty): hooks/ with no .sh files → exit 3, hooks.bak.tmp cleaned up
# ---------------------------------------------------------------------------
echo "[24] hooks/ with no .sh files exits 3 and cleans up hooks.bak.tmp"

FX24_HOME="$TMPROOT/home24"
FX24_INSTALL="$FX24_HOME/.claude/plugins/cache/test-install"
FX24_PROJ="$TMPROOT/proj24"

_make_git_repo "$FX24_PROJ"
_make_install_fixture "$FX24_HOME" "$FX24_INSTALL"
mkdir -p "$FX24_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX24_PROJ/.sweetclaude/state/phase.yaml"

printf '{"hooks": []}\n' > "$FX24_INSTALL/hooks/hooks.json"

EXIT24=0
STDERR24=$(cd "$FX24_PROJ" && HOME="$FX24_HOME" bash "$SCRIPT" 2>&1 >/dev/null) || EXIT24=$?

if [ "$EXIT24" -eq 3 ]; then
  pass "exit code is 3 when hooks/ has no .sh files"
else
  fail "expected exit code 3 for hooks/ with no .sh files, got $EXIT24"
fi

if [ ! -d "$FX24_INSTALL/hooks.bak.tmp" ]; then
  pass "hooks.bak.tmp cleaned up after validation failure"
else
  fail "hooks.bak.tmp still exists after validation failure"
fi

# ---------------------------------------------------------------------------
# Test 25 (301-tmp-success): hooks.bak.tmp absent after successful sync
# ---------------------------------------------------------------------------
echo "[25] hooks.bak.tmp absent after successful sync"

FX25_HOME="$TMPROOT/home25"
FX25_INSTALL="$FX25_HOME/.claude/plugins/cache/test-install"
FX25_PROJ="$TMPROOT/proj25"

_make_git_repo "$FX25_PROJ"
_make_install_fixture "$FX25_HOME" "$FX25_INSTALL"
mkdir -p "$FX25_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX25_PROJ/.sweetclaude/state/phase.yaml"

printf '#!/bin/bash\necho h\n' > "$FX25_INSTALL/hooks/placeholder.sh"

EXIT25=0
(cd "$FX25_PROJ" && HOME="$FX25_HOME" bash "$SCRIPT" >/dev/null 2>&1) || EXIT25=$?

if [ ! -d "$FX25_INSTALL/hooks.bak.tmp" ]; then
  pass "hooks.bak.tmp absent after successful sync"
else
  fail "hooks.bak.tmp still exists after successful sync"
fi

# ---------------------------------------------------------------------------
# Test 26 (301-dry-run): --dry-run does not create hooks.bak/
# ---------------------------------------------------------------------------
echo "[26] --dry-run does not create hooks.bak/"

FX26_HOME="$TMPROOT/home26"
FX26_INSTALL="$FX26_HOME/.claude/plugins/cache/test-install"
FX26_PROJ="$TMPROOT/proj26"

_make_git_repo "$FX26_PROJ"
_make_install_fixture "$FX26_HOME" "$FX26_INSTALL"
mkdir -p "$FX26_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX26_PROJ/.sweetclaude/state/phase.yaml"

printf '#!/bin/bash\necho h\n' > "$FX26_INSTALL/hooks/placeholder.sh"

EXIT26=0
(cd "$FX26_PROJ" && HOME="$FX26_HOME" bash "$SCRIPT" --dry-run >/dev/null 2>&1) || EXIT26=$?

if [ ! -d "$FX26_INSTALL/hooks.bak" ]; then
  pass "hooks.bak/ not created during --dry-run"
else
  fail "hooks.bak/ created during --dry-run (should not be)"
fi

# ---------------------------------------------------------------------------
# Test 27 (301-force-backup): --force does not bypass backup failure
# ---------------------------------------------------------------------------
echo "[27] --force does not bypass backup failure (exit 3)"

FX27_HOME="$TMPROOT/home27"
FX27_INSTALL="$FX27_HOME/.claude/plugins/cache/test-install"
FX27_PROJ="$TMPROOT/proj27"

_make_git_repo "$FX27_PROJ"
_make_install_fixture "$FX27_HOME" "$FX27_INSTALL"
mkdir -p "$FX27_PROJ/.sweetclaude/state"
printf 'phase: implement\n' > "$FX27_PROJ/.sweetclaude/state/phase.yaml"
printf '| # | Date | Phase | Decision | Rationale |\n| --- | --- | --- | --- | --- |\n' \
  > "$FX27_PROJ/.sweetclaude/state/decision-log.md"

printf '#!/bin/bash\necho h\n' > "$FX27_INSTALL/hooks/original.sh"

chmod 555 "$FX27_INSTALL"

EXIT27=0
(cd "$FX27_PROJ" && HOME="$FX27_HOME" bash "$SCRIPT" --force >/dev/null 2>&1) || EXIT27=$?

chmod 755 "$FX27_INSTALL"

if [ "$EXIT27" -eq 3 ]; then
  pass "--force does not bypass backup failure (exit 3)"
else
  fail "expected exit code 3 with --force + backup failure, got $EXIT27"
fi

# ---------------------------------------------------------------------------
# Test 28 (301-content): backed-up file content matches originals
# ---------------------------------------------------------------------------
echo "[28] backed-up file content matches originals"

FX28_HOME="$TMPROOT/home28"
FX28_INSTALL="$FX28_HOME/.claude/plugins/cache/test-install"
FX28_PROJ="$TMPROOT/proj28"

_make_git_repo "$FX28_PROJ"
_make_install_fixture "$FX28_HOME" "$FX28_INSTALL"
mkdir -p "$FX28_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX28_PROJ/.sweetclaude/state/phase.yaml"

printf '#!/bin/bash\necho unique-content-12345\n' > "$FX28_INSTALL/hooks/verifiable.sh"
CHECKSUM28_BEFORE=$(md5 -q "$FX28_INSTALL/hooks/verifiable.sh" 2>/dev/null \
  || md5sum "$FX28_INSTALL/hooks/verifiable.sh" 2>/dev/null | cut -d' ' -f1)

EXIT28=0
(cd "$FX28_PROJ" && HOME="$FX28_HOME" bash "$SCRIPT" >/dev/null 2>&1) || EXIT28=$?

if [ -f "$FX28_INSTALL/hooks.bak/verifiable.sh" ]; then
  CHECKSUM28_AFTER=$(md5 -q "$FX28_INSTALL/hooks.bak/verifiable.sh" 2>/dev/null \
    || md5sum "$FX28_INSTALL/hooks.bak/verifiable.sh" 2>/dev/null | cut -d' ' -f1)
  if [ "$CHECKSUM28_BEFORE" = "$CHECKSUM28_AFTER" ] && [ -n "$CHECKSUM28_BEFORE" ]; then
    pass "backed-up file checksum matches original"
  else
    fail "checksum mismatch: original=$CHECKSUM28_BEFORE, backup=$CHECKSUM28_AFTER"
  fi
else
  fail "hooks.bak/verifiable.sh does not exist"
fi

# ---------------------------------------------------------------------------
# Test 29 (301-6): exit code 3 is distinct — used only in backup section
# ---------------------------------------------------------------------------
echo "[29] exit code 3 used exclusively in backup section"

EXIT3_TOTAL=$(grep -c 'exit 3' "$SCRIPT" || true)
EXIT3_IN_BACKUP=$(sed -n '/# ── Backup/,/# ── Sync hooks/p' "$SCRIPT" | grep -c 'exit 3' || true)

if [ "$EXIT3_TOTAL" -eq "$EXIT3_IN_BACKUP" ] && [ "$EXIT3_TOTAL" -gt 0 ]; then
  pass "exit code 3 used exclusively in backup section ($EXIT3_TOTAL occurrences)"
else
  fail "exit 3: total=$EXIT3_TOTAL, in backup section=$EXIT3_IN_BACKUP (expected equal and >0)"
fi

# ---------------------------------------------------------------------------
# Test 30 (301-rollback): sync failure triggers rollback from hooks.bak
# ---------------------------------------------------------------------------
echo "[30] sync failure (exit 4) triggers rollback from hooks.bak"

FX30_HOME="$TMPROOT/home30"
FX30_INSTALL="$FX30_HOME/.claude/plugins/cache/test-install"
FX30_PROJ="$TMPROOT/proj30"

_make_git_repo "$FX30_PROJ"
_make_install_fixture "$FX30_HOME" "$FX30_INSTALL"
mkdir -p "$FX30_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX30_PROJ/.sweetclaude/state/phase.yaml"

printf '#!/bin/bash\necho original-content\n' > "$FX30_INSTALL/hooks/my-hook.sh"

FAKE_BIN="$TMPROOT/fake-bin-30"
mkdir -p "$FAKE_BIN"
cat > "$FAKE_BIN/rsync" << 'FAKEEOF'
#!/bin/bash
rm -rf "${@: -1}"/* 2>/dev/null
exit 1
FAKEEOF
chmod +x "$FAKE_BIN/rsync"

EXIT30=0
(cd "$FX30_PROJ" && HOME="$FX30_HOME" PATH="$FAKE_BIN:$PATH" bash "$SCRIPT" >/dev/null 2>&1) || EXIT30=$?

if [ "$EXIT30" -eq 4 ]; then
  pass "exit code is 4 on sync failure"
else
  fail "expected exit code 4 on sync failure, got $EXIT30"
fi

if [ -f "$FX30_INSTALL/hooks/my-hook.sh" ]; then
  if grep -q "original-content" "$FX30_INSTALL/hooks/my-hook.sh"; then
    pass "hooks restored from backup after sync failure"
  else
    fail "hooks/my-hook.sh content changed after sync failure"
  fi
else
  fail "hooks/my-hook.sh missing after sync failure (not restored)"
fi

# ---------------------------------------------------------------------------
# Test 31 (301-rm-backup): rm of old hooks.bak fails → exit 3
# ---------------------------------------------------------------------------
echo "[31] rm of old hooks.bak fails exits 3"

FX31_HOME="$TMPROOT/home31"
FX31_INSTALL="$FX31_HOME/.claude/plugins/cache/test-install"
FX31_PROJ="$TMPROOT/proj31"

_make_git_repo "$FX31_PROJ"
_make_install_fixture "$FX31_HOME" "$FX31_INSTALL"
mkdir -p "$FX31_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX31_PROJ/.sweetclaude/state/phase.yaml"

printf '#!/bin/bash\necho h\n' > "$FX31_INSTALL/hooks/placeholder.sh"

mkdir -p "$FX31_INSTALL/hooks.bak"
touch "$FX31_INSTALL/hooks.bak/old-file"
chmod 555 "$FX31_INSTALL/hooks.bak"

EXIT31=0
(cd "$FX31_PROJ" && HOME="$FX31_HOME" bash "$SCRIPT" >/dev/null 2>&1) || EXIT31=$?

chmod 755 "$FX31_INSTALL/hooks.bak" 2>/dev/null || true

if [ "$EXIT31" -eq 3 ]; then
  pass "exit code is 3 when old hooks.bak cannot be removed"
else
  fail "expected exit code 3 when old hooks.bak cannot be removed, got $EXIT31"
fi

if [ ! -d "$FX31_INSTALL/hooks.bak.tmp" ]; then
  pass "hooks.bak.tmp cleaned up after rm failure"
else
  fail "hooks.bak.tmp still exists after rm failure"
fi

# ===========================================================================
# STORY-302: Pre-sync test validation gate
# ===========================================================================

# ---------------------------------------------------------------------------
# Test 32 (302-1): Sync runs test suite before copying — passing tests
# ---------------------------------------------------------------------------
echo "[32] test gate runs test-hooks.sh before sync and reports pass"

FX32_ROOT="$TMPROOT/fx32"
FX32_HOME="$FX32_ROOT/home"
FX32_INSTALL="$FX32_HOME/.claude/plugins/cache/test-install"
FX32_PROJ="$FX32_ROOT/proj"

_make_git_repo "$FX32_PROJ"
_make_302_fixture "$FX32_ROOT" "$FX32_HOME" "$FX32_INSTALL" 0
mkdir -p "$FX32_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX32_PROJ/.sweetclaude/state/phase.yaml"

FX32_SCRIPT="$FX32_ROOT/fake-repo/scripts/sync-to-installed.sh"

EXIT32=0
STDOUT32=$(cd "$FX32_PROJ" && HOME="$FX32_HOME" bash "$FX32_SCRIPT" 2>/dev/null) || EXIT32=$?

if printf '%s' "$STDOUT32" | grep -qiE "test-hooks|hook test|All hook tests passed|ALL TESTS PASSED"; then
  pass "stdout contains evidence that test-hooks.sh was executed"
else
  fail "stdout missing evidence of test-hooks.sh execution (got: $(printf '%s' "$STDOUT32" | head -c 300))"
fi

if printf '%s' "$STDOUT32" | grep -qiE "All hook tests passed|ALL TESTS PASSED|tests passed"; then
  pass "stdout contains 'All hook tests passed' or equivalent"
else
  fail "stdout missing test-pass confirmation (got: $(printf '%s' "$STDOUT32" | head -c 300))"
fi

if [ "$EXIT32" -eq 0 ]; then
  pass "sync exits 0 when tests pass"
else
  fail "expected exit code 0 when tests pass, got $EXIT32"
fi

# ---------------------------------------------------------------------------
# Test 33 (302-2): Failing tests block sync — exit 2, stderr message, hooks unchanged
# ---------------------------------------------------------------------------
echo "[33] failing tests block sync: exit 2, stderr message, hooks unchanged"

FX33_ROOT="$TMPROOT/fx33"
FX33_HOME="$FX33_ROOT/home"
FX33_INSTALL="$FX33_HOME/.claude/plugins/cache/test-install"
FX33_PROJ="$FX33_ROOT/proj"

_make_git_repo "$FX33_PROJ"
_make_302_fixture "$FX33_ROOT" "$FX33_HOME" "$FX33_INSTALL" 1
mkdir -p "$FX33_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX33_PROJ/.sweetclaude/state/phase.yaml"

FX33_SCRIPT="$FX33_ROOT/fake-repo/scripts/sync-to-installed.sh"

HOOKS_BEFORE_33=$(find "$FX33_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5 -q 2>/dev/null || find "$FX33_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | cut -d' ' -f1 | tr '\n' ':')

EXIT33=0
STDERR33=$(cd "$FX33_PROJ" && HOME="$FX33_HOME" bash "$FX33_SCRIPT" 2>&1 >/dev/null) || EXIT33=$?

if [ "$EXIT33" -eq 2 ]; then
  pass "exit code is 2 when tests fail"
else
  fail "expected exit code 2 when tests fail, got $EXIT33"
fi

if printf '%s' "$STDERR33" | grep -qiE "tests failed|Sync blocked"; then
  pass "stderr contains 'tests failed' or 'Sync blocked'"
else
  fail "stderr missing expected message (got: $(printf '%s' "$STDERR33" | head -c 300))"
fi

HOOKS_AFTER_33=$(find "$FX33_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5 -q 2>/dev/null || find "$FX33_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | cut -d' ' -f1 | tr '\n' ':')

if [ "$HOOKS_BEFORE_33" = "$HOOKS_AFTER_33" ]; then
  pass "installed hooks/ unchanged after test gate blocked sync"
else
  fail "installed hooks/ were modified despite test gate blocking sync"
fi

# ---------------------------------------------------------------------------
# Test 34 (302-3): --force does NOT bypass test gate
# ---------------------------------------------------------------------------
echo "[34] --force does not bypass test gate when tests fail"

FX34_ROOT="$TMPROOT/fx34"
FX34_HOME="$FX34_ROOT/home"
FX34_INSTALL="$FX34_HOME/.claude/plugins/cache/test-install"
FX34_PROJ="$FX34_ROOT/proj"

_make_git_repo "$FX34_PROJ"
_make_302_fixture "$FX34_ROOT" "$FX34_HOME" "$FX34_INSTALL" 1
mkdir -p "$FX34_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX34_PROJ/.sweetclaude/state/phase.yaml"
printf '| # | Date | Phase | Decision | Rationale |\n| --- | --- | --- | --- | --- |\n| 1 | 2026-01-01 | plan | initial | setup |\n' \
  > "$FX34_PROJ/.sweetclaude/state/decision-log.md"

FX34_SCRIPT="$FX34_ROOT/fake-repo/scripts/sync-to-installed.sh"

HOOKS_BEFORE_34=$(find "$FX34_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5 -q 2>/dev/null || find "$FX34_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | cut -d' ' -f1 | tr '\n' ':')

EXIT34=0
STDERR34=$(cd "$FX34_PROJ" && HOME="$FX34_HOME" bash "$FX34_SCRIPT" --force 2>&1 >/dev/null) || EXIT34=$?

if [ "$EXIT34" -eq 2 ]; then
  pass "--force does not bypass test gate (exit 2)"
else
  fail "expected exit code 2 with --force + failing tests, got $EXIT34"
fi

if printf '%s' "$STDERR34" | grep -qiE "tests failed|Sync blocked"; then
  pass "stderr contains 'tests failed' or 'Sync blocked' with --force"
else
  fail "stderr missing expected message with --force (got: $(printf '%s' "$STDERR34" | head -c 300))"
fi

HOOKS_AFTER_34=$(find "$FX34_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5 -q 2>/dev/null || find "$FX34_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | cut -d' ' -f1 | tr '\n' ':')

if [ "$HOOKS_BEFORE_34" = "$HOOKS_AFTER_34" ]; then
  pass "installed hooks/ unchanged after --force + failing tests"
else
  fail "installed hooks/ were modified despite --force + failing tests"
fi

# ---------------------------------------------------------------------------
# Test 35 (302-4): Test success allows sync — exit 0, hooks actually synced
# ---------------------------------------------------------------------------
echo "[35] passing tests allow sync to proceed and hooks are copied"

FX35_ROOT="$TMPROOT/fx35"
FX35_HOME="$FX35_ROOT/home"
FX35_INSTALL="$FX35_HOME/.claude/plugins/cache/test-install"
FX35_PROJ="$FX35_ROOT/proj"

_make_git_repo "$FX35_PROJ"
_make_302_fixture "$FX35_ROOT" "$FX35_HOME" "$FX35_INSTALL" 0
mkdir -p "$FX35_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX35_PROJ/.sweetclaude/state/phase.yaml"

FX35_SCRIPT="$FX35_ROOT/fake-repo/scripts/sync-to-installed.sh"

printf '#!/bin/bash\necho pre-existing\n' > "$FX35_INSTALL/hooks/pre-existing.sh"

EXIT35=0
(cd "$FX35_PROJ" && HOME="$FX35_HOME" bash "$FX35_SCRIPT" >/dev/null 2>&1) || EXIT35=$?

if [ "$EXIT35" -eq 0 ]; then
  pass "exit code 0 when tests pass and sync proceeds"
else
  fail "expected exit code 0, got $EXIT35"
fi

SYNCED_COUNT=$(find "$FX35_INSTALL/hooks" -name "*.sh" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$SYNCED_COUNT" -gt 0 ]; then
  pass "installed hooks/ contains synced .sh files after passing tests ($SYNCED_COUNT files)"
else
  fail "no .sh files found in installed hooks/ after sync with passing tests"
fi

if [ -f "$FX35_INSTALL/hooks/stub-hook.sh" ]; then
  pass "stub-hook.sh from fake-repo/hooks/ is present at installed path"
else
  fail "stub-hook.sh not found at installed path (sync did not copy repo hooks)"
fi

# ---------------------------------------------------------------------------
# Test 36 (302-dry-run): Tests still run in dry-run mode — passing tests
# ---------------------------------------------------------------------------
echo "[36] dry-run still executes test-hooks.sh, hooks unchanged after"

FX36_ROOT="$TMPROOT/fx36"
FX36_HOME="$FX36_ROOT/home"
FX36_INSTALL="$FX36_HOME/.claude/plugins/cache/test-install"
FX36_PROJ="$FX36_ROOT/proj"

_make_git_repo "$FX36_PROJ"
_make_302_fixture "$FX36_ROOT" "$FX36_HOME" "$FX36_INSTALL" 0
mkdir -p "$FX36_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX36_PROJ/.sweetclaude/state/phase.yaml"

FX36_SCRIPT="$FX36_ROOT/fake-repo/scripts/sync-to-installed.sh"

HOOKS_BEFORE_36=$(find "$FX36_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5 -q 2>/dev/null || find "$FX36_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | cut -d' ' -f1 | tr '\n' ':')

EXIT36=0
STDOUT36=$(cd "$FX36_PROJ" && HOME="$FX36_HOME" bash "$FX36_SCRIPT" --dry-run 2>/dev/null) || EXIT36=$?

if printf '%s' "$STDOUT36" | grep -qiE "test-hooks|hook test|All hook tests passed|ALL TESTS PASSED|tests passed"; then
  pass "dry-run stdout contains evidence that test-hooks.sh was executed"
else
  fail "dry-run stdout missing evidence of test-hooks.sh execution (got: $(printf '%s' "$STDOUT36" | head -c 300))"
fi

if [ "$EXIT36" -eq 0 ]; then
  pass "dry-run exits 0 when tests pass"
else
  fail "expected exit code 0 for dry-run with passing tests, got $EXIT36"
fi

HOOKS_AFTER_36=$(find "$FX36_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5 -q 2>/dev/null || find "$FX36_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | cut -d' ' -f1 | tr '\n' ':')

if [ "$HOOKS_BEFORE_36" = "$HOOKS_AFTER_36" ]; then
  pass "installed hooks/ unchanged after dry-run (dry-run did not copy)"
else
  fail "installed hooks/ changed during dry-run (should not copy)"
fi

# ---------------------------------------------------------------------------
# Test 37 (302-dry-run-fail): Dry-run with failing tests — exit 2, stderr, hooks unchanged
# ---------------------------------------------------------------------------
echo "[37] dry-run with failing tests exits 2, stderr message, hooks unchanged"

FX37_ROOT="$TMPROOT/fx37"
FX37_HOME="$FX37_ROOT/home"
FX37_INSTALL="$FX37_HOME/.claude/plugins/cache/test-install"
FX37_PROJ="$FX37_ROOT/proj"

_make_git_repo "$FX37_PROJ"
_make_302_fixture "$FX37_ROOT" "$FX37_HOME" "$FX37_INSTALL" 1
mkdir -p "$FX37_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX37_PROJ/.sweetclaude/state/phase.yaml"

FX37_SCRIPT="$FX37_ROOT/fake-repo/scripts/sync-to-installed.sh"

HOOKS_BEFORE_37=$(find "$FX37_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5 -q 2>/dev/null || find "$FX37_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | cut -d' ' -f1 | tr '\n' ':')

EXIT37=0
STDERR37=$(cd "$FX37_PROJ" && HOME="$FX37_HOME" bash "$FX37_SCRIPT" --dry-run 2>&1 >/dev/null) || EXIT37=$?

if [ "$EXIT37" -eq 2 ]; then
  pass "dry-run exits 2 when tests fail"
else
  fail "expected exit code 2 for dry-run with failing tests, got $EXIT37"
fi

if printf '%s' "$STDERR37" | grep -qiE "tests failed|Sync blocked"; then
  pass "dry-run stderr contains 'tests failed' or 'Sync blocked'"
else
  fail "dry-run stderr missing expected message (got: $(printf '%s' "$STDERR37" | head -c 300))"
fi

HOOKS_AFTER_37=$(find "$FX37_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | cut -d' ' -f1 | tr '\n' ':')

if [ "$HOOKS_BEFORE_37" = "$HOOKS_AFTER_37" ]; then
  pass "installed hooks/ unchanged after dry-run with failing tests"
else
  fail "installed hooks/ changed after dry-run with failing tests (should not copy)"
fi

# ---------------------------------------------------------------------------
# Test 38 (302-missing): test-hooks.sh does not exist → exit 2, stderr message
# ---------------------------------------------------------------------------
echo "[38] missing test-hooks.sh exits 2 with error message"

FX38_ROOT="$TMPROOT/fx38"
FX38_HOME="$FX38_ROOT/home"
FX38_INSTALL="$FX38_HOME/.claude/plugins/cache/test-install"
FX38_PROJ="$FX38_ROOT/proj"

_make_git_repo "$FX38_PROJ"
_make_302_fixture "$FX38_ROOT" "$FX38_HOME" "$FX38_INSTALL" 0
mkdir -p "$FX38_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX38_PROJ/.sweetclaude/state/phase.yaml"

FX38_SCRIPT="$FX38_ROOT/fake-repo/scripts/sync-to-installed.sh"
rm -f "$FX38_ROOT/fake-repo/tests/test-hooks.sh"

EXIT38=0
STDERR38=$(cd "$FX38_PROJ" && HOME="$FX38_HOME" bash "$FX38_SCRIPT" 2>&1 >/dev/null) || EXIT38=$?

if [ "$EXIT38" -eq 2 ]; then
  pass "exit code is 2 when test-hooks.sh is missing"
else
  fail "expected exit code 2 for missing test-hooks.sh, got $EXIT38"
fi

if printf '%s' "$STDERR38" | grep -qiE "tests failed|Sync blocked|test-hooks.sh|not found"; then
  pass "stderr contains error message about missing tests"
else
  fail "stderr missing expected message for missing test-hooks.sh (got: $(printf '%s' "$STDERR38" | head -c 300))"
fi

# ---------------------------------------------------------------------------
# Test 39 (302-no-backup): test gate blocks before backup is created
# ---------------------------------------------------------------------------
echo "[39] test gate blocks before backup — hooks.bak/ not created"

FX39_ROOT="$TMPROOT/fx39"
FX39_HOME="$FX39_ROOT/home"
FX39_INSTALL="$FX39_HOME/.claude/plugins/cache/test-install"
FX39_PROJ="$FX39_ROOT/proj"

_make_git_repo "$FX39_PROJ"
_make_302_fixture "$FX39_ROOT" "$FX39_HOME" "$FX39_INSTALL" 1
mkdir -p "$FX39_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX39_PROJ/.sweetclaude/state/phase.yaml"

FX39_SCRIPT="$FX39_ROOT/fake-repo/scripts/sync-to-installed.sh"

rm -rf "$FX39_INSTALL/hooks.bak" 2>/dev/null || true

EXIT39=0
(cd "$FX39_PROJ" && HOME="$FX39_HOME" bash "$FX39_SCRIPT" >/dev/null 2>&1) || EXIT39=$?

if [ ! -d "$FX39_INSTALL/hooks.bak" ]; then
  pass "hooks.bak/ not created when test gate blocks sync"
else
  fail "hooks.bak/ was created despite test gate blocking (gate runs after backup?)"
fi

# ---------------------------------------------------------------------------
# Test 40 (302-force-dry-run-fail): --force --dry-run with failing tests → exit 2
# ---------------------------------------------------------------------------
echo "[40] --force --dry-run with failing tests exits 2"

FX40_ROOT="$TMPROOT/fx40"
FX40_HOME="$FX40_ROOT/home"
FX40_INSTALL="$FX40_HOME/.claude/plugins/cache/test-install"
FX40_PROJ="$FX40_ROOT/proj"

_make_git_repo "$FX40_PROJ"
_make_302_fixture "$FX40_ROOT" "$FX40_HOME" "$FX40_INSTALL" 1
mkdir -p "$FX40_PROJ/.sweetclaude/state"
printf 'phase: implement\n' > "$FX40_PROJ/.sweetclaude/state/phase.yaml"
printf '| # | Date | Phase | Decision | Rationale |\n| --- | --- | --- | --- | --- |\n' \
  > "$FX40_PROJ/.sweetclaude/state/decision-log.md"

FX40_SCRIPT="$FX40_ROOT/fake-repo/scripts/sync-to-installed.sh"

EXIT40=0
STDERR40=$(cd "$FX40_PROJ" && HOME="$FX40_HOME" bash "$FX40_SCRIPT" --force --dry-run 2>&1 >/dev/null) || EXIT40=$?

if [ "$EXIT40" -eq 2 ]; then
  pass "--force --dry-run exits 2 when tests fail"
else
  fail "expected exit code 2 for --force --dry-run + failing tests, got $EXIT40"
fi

if printf '%s' "$STDERR40" | grep -qiE "tests failed|Sync blocked"; then
  pass "--force --dry-run stderr contains test failure message"
else
  fail "--force --dry-run stderr missing expected message (got: $(printf '%s' "$STDERR40" | head -c 300))"
fi

# ---------------------------------------------------------------------------
# Test 41 (302-force-implement-fail): --force + IMPLEMENT + failing tests → exit 2
# ---------------------------------------------------------------------------
echo "[41] --force during IMPLEMENT with failing tests exits 2 (test gate not bypassed)"

FX41_ROOT="$TMPROOT/fx41"
FX41_HOME="$FX41_ROOT/home"
FX41_INSTALL="$FX41_HOME/.claude/plugins/cache/test-install"
FX41_PROJ="$FX41_ROOT/proj"

_make_git_repo "$FX41_PROJ"
_make_302_fixture "$FX41_ROOT" "$FX41_HOME" "$FX41_INSTALL" 1
mkdir -p "$FX41_PROJ/.sweetclaude/state"
printf 'phase: implement\n' > "$FX41_PROJ/.sweetclaude/state/phase.yaml"
printf '| # | Date | Phase | Decision | Rationale |\n| --- | --- | --- | --- | --- |\n' \
  > "$FX41_PROJ/.sweetclaude/state/decision-log.md"

FX41_SCRIPT="$FX41_ROOT/fake-repo/scripts/sync-to-installed.sh"

HOOKS_BEFORE_41=$(find "$FX41_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5 -q 2>/dev/null || find "$FX41_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | cut -d' ' -f1 | tr '\n' ':')

EXIT41=0
STDERR41=$(cd "$FX41_PROJ" && HOME="$FX41_HOME" bash "$FX41_SCRIPT" --force 2>&1 >/dev/null) || EXIT41=$?

if [ "$EXIT41" -eq 2 ]; then
  pass "--force + IMPLEMENT + failing tests exits 2"
else
  fail "expected exit code 2 for --force + IMPLEMENT + failing tests, got $EXIT41"
fi

HOOKS_AFTER_41=$(find "$FX41_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5 -q 2>/dev/null || find "$FX41_INSTALL/hooks" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | cut -d' ' -f1 | tr '\n' ':')

if [ "$HOOKS_BEFORE_41" = "$HOOKS_AFTER_41" ]; then
  pass "installed hooks/ unchanged after --force + IMPLEMENT + failing tests"
else
  fail "installed hooks/ modified despite --force + IMPLEMENT + failing tests"
fi

# ---------------------------------------------------------------------------
# Test 42 (302-exit127): test-hooks.sh exits 127 → gate still produces exit 2
# ---------------------------------------------------------------------------
echo "[42] test-hooks.sh exiting 127 still produces exit 2 from gate"

FX42_ROOT="$TMPROOT/fx42"
FX42_HOME="$FX42_ROOT/home"
FX42_INSTALL="$FX42_HOME/.claude/plugins/cache/test-install"
FX42_PROJ="$FX42_ROOT/proj"

_make_git_repo "$FX42_PROJ"
_make_302_fixture "$FX42_ROOT" "$FX42_HOME" "$FX42_INSTALL" 0
mkdir -p "$FX42_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX42_PROJ/.sweetclaude/state/phase.yaml"

FX42_SCRIPT="$FX42_ROOT/fake-repo/scripts/sync-to-installed.sh"
cat > "$FX42_ROOT/fake-repo/tests/test-hooks.sh" << 'HOOKEOF'
#!/bin/bash
exit 127
HOOKEOF
chmod +x "$FX42_ROOT/fake-repo/tests/test-hooks.sh"

EXIT42=0
STDERR42=$(cd "$FX42_PROJ" && HOME="$FX42_HOME" bash "$FX42_SCRIPT" 2>&1 >/dev/null) || EXIT42=$?

if [ "$EXIT42" -eq 2 ]; then
  pass "exit 127 from test-hooks.sh produces gate exit code 2"
else
  fail "expected exit code 2 when test-hooks.sh exits 127, got $EXIT42"
fi

# ---------------------------------------------------------------------------
# Test 43 (302-not-executable): test-hooks.sh exists but is not executable → exit 2
# ---------------------------------------------------------------------------
echo "[43] non-executable test-hooks.sh produces exit 2"

FX43_ROOT="$TMPROOT/fx43"
FX43_HOME="$FX43_ROOT/home"
FX43_INSTALL="$FX43_HOME/.claude/plugins/cache/test-install"
FX43_PROJ="$FX43_ROOT/proj"

_make_git_repo "$FX43_PROJ"
_make_302_fixture "$FX43_ROOT" "$FX43_HOME" "$FX43_INSTALL" 0
mkdir -p "$FX43_PROJ/.sweetclaude/state"
printf 'phase: verify\n' > "$FX43_PROJ/.sweetclaude/state/phase.yaml"

FX43_SCRIPT="$FX43_ROOT/fake-repo/scripts/sync-to-installed.sh"
chmod -x "$FX43_ROOT/fake-repo/tests/test-hooks.sh"

EXIT43=0
STDERR43=$(cd "$FX43_PROJ" && HOME="$FX43_HOME" bash "$FX43_SCRIPT" 2>&1 >/dev/null) || EXIT43=$?

if [ "$EXIT43" -eq 2 ]; then
  pass "non-executable test-hooks.sh produces exit 2"
else
  fail "expected exit code 2 for non-executable test-hooks.sh, got $EXIT43"
fi

if printf '%s' "$STDERR43" | grep -qiE "tests failed|Sync blocked|not found|Permission"; then
  pass "stderr contains error message for non-executable test-hooks.sh"
else
  fail "stderr missing expected message for non-executable test-hooks.sh (got: $(printf '%s' "$STDERR43" | head -c 300))"
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
