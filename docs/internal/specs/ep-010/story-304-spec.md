---
id: SPEC-304
story: STORY-304
epic: EP-010
version: 2.1
date: 2026-05-19
supersedes: SPEC-304 v1.0 (2026-05-18)
amendment: "v2.1 — added --dry-run flag to emergency script and test_dry_run_preview function (Option B resolution, 2026-05-19)"
status: approved
---

# Specification: STORY-304 Bash-based hook repair recovery procedure

## User story

As a SweetClaude developer whose session is blocked by a broken installed hook, I want a documented and optionally automated recovery path using the Bash tool so that I can restore the last known-good hook without leaving Claude Code.

## Why Bash is the recovery channel

`test-guardian.sh` and `auto-test-runner.sh` are registered in `hooks/hooks.json` with `"matcher": "Write|Edit"`. The Bash tool is a different tool name — it is not matched by these hooks. When an installed hook is broken, Write/Edit are blocked but Bash remains available.

This is not a bypass — it is the intended escape hatch. The hook architecture deliberately does not gate Bash because Bash is needed for build commands, test execution, and (as this story codifies) recovery.

`artifact-guardian.sh` matches `Bash` — but it guards artifact file modifications, not arbitrary Bash commands. The `cp` to the hooks path is not within the artifact-protected paths, so it is not blocked.

## Deliverables

1. **`scripts/emergency-hook-restore.sh`** — standalone break-glass recovery script (executable, zero SweetClaude dependencies)
2. **`tests/test-emergency-restore.sh`** — test script with four test functions (see Test plan below)
3. **`docs/user-guide/hook-development.md`** — two new sections: Recovery and Emergency Recovery (Break Glass)
4. **`skills/hook-repair/SKILL.md`** — user-invocable escape skill for automated recovery
5. **README and `skills-reference.md` entries** — list the new skill and reference the break-glass script

---

## Deliverable 1: `scripts/emergency-hook-restore.sh`

A standalone bash script that restores hooks when EVERYTHING else is broken — the hook-repair skill, the sync script, the session-preflight, all of it. This is the absolute last resort.

### Design principles

- Zero dependencies on SweetClaude infrastructure (no skills, no hooks, no YAML parsing)
- Pure bash + `cp` + standard unix tools + a small `python3` one-liner for JSON
- Invokable via the Bash tool from inside a deadlocked Claude Code session
- Invokable directly from a terminal outside Claude Code
- Self-contained: resolves all paths internally, no arguments required (accepts optional hook name)

### `set -e`, not `set -euo pipefail`

The script uses bare `set -e`. The recovery script must tolerate:
- Unset env vars (`${INSTALL_PATH:-}` patterns expand cleanly under `set -u` but the script also uses `${1:-}` in defensive ways where strict `-u` adds friction without value)
- `|| true` clauses in the `find` fallback path resolution
- A `python3` heredoc that may produce empty output

The recovery script's job is to make a best effort under degraded conditions, not to fail fast on tooling oddities. The companion test script does use `set -euo pipefail` (see Deliverable 2) precisely because tests must fail loudly.

### Output contract constants

The script emits a pinned set of output lines that downstream tooling (tests, docs, skill) can match against. These constants are exported at the top of the script and referenced in the body:

```bash
# Output contract — pinned strings. Tests source this script and assert on these.
readonly CONTRACT_LINE_INSTALL="Installed hooks:"
readonly CONTRACT_LINE_BACKUP="Backup dir:"
readonly CONTRACT_LINE_REPO="Repo hooks:"
readonly CONTRACT_LINE_RESTORED_BACKUP_SUFFIX=" from backup"
readonly CONTRACT_LINE_RESTORED_REPO_SUFFIX=" from repo (no backup available)"
readonly CONTRACT_LINE_RESTORED_PREFIX="RESTORED "
readonly CONTRACT_LINE_DONE_PREFIX="Done. Verify with:"
readonly CONTRACT_FATAL_NO_INSTALL="FATAL: Cannot find installed hooks path."
readonly CONTRACT_FATAL_BAD_NAME="FATAL: Hook name must be a bare filename, not a path."
readonly CONTRACT_FATAL_NOT_FOUND_SUFFIX=" not found in backup or repo"
# Dry-run output contract
readonly EHR_RESOLVED_PREFIX="Resolved install path:"
readonly EHR_WOULD_RESTORE_PREFIX="Would restore:"
```

Tests source the script with `INSTALL_PATH` unset and a sentinel guard so the script's main body does not execute on source; instead, the test reads the constants. See Deliverable 2 for the mechanism.

### Dry-run mode and prefix-check back-door

The script enforces a safety check: `INSTALL_PATH` must begin with `$HOME/.claude/plugins/` to prevent the script from writing outside the plugin tree. This prefix check is **bypassed when `INSTALL_PATH` is set explicitly via env var** — the back-door semantics — because tests need to point the script at a sandboxed tmpdir.

```bash
# Prefix check applies only when INSTALL_PATH was resolved from installed_plugins.json
# When the caller sets INSTALL_PATH explicitly (back door for tests), trust it.
if [ -z "${INSTALL_PATH_OVERRIDE:-}" ]; then
  case "$INSTALL_PATH" in
    "$HOME/.claude/plugins/"*) : ;;
    *)
      echo "FATAL: Resolved install path is outside plugin tree: $INSTALL_PATH" >&2
      exit 1
      ;;
  esac
fi
```

The override flag `INSTALL_PATH_OVERRIDE=1` (or equivalently, `INSTALL_PATH` being non-empty at script entry) is the back-door. Tests set it; normal users do not.

### Dry-run mode

`--dry-run` is the first positional argument. When set, the script resolves the install path and enumerates what would be restored, then exits 0 without writing anything. The optional hook name argument (`[hook-name.sh]`) is still honored: in dry-run mode a single `Would restore:` line is emitted for the named hook.

Output contract in dry-run mode:
- `Resolved install path: <absolute-path>` — one line, always
- `Would restore: <hook-filename>` — one line per hook (from backup or repo, in discovery order)

The `EHR_RESOLVED_PREFIX` and `EHR_WOULD_RESTORE_PREFIX` constants carry these prefixes. Tests source the script and assert against these constants.

### Full script body

```bash
#!/bin/bash
# Emergency hook restore — run this when everything else is broken.
# Usage: bash scripts/emergency-hook-restore.sh [hook-name.sh]
# No arguments: restores ALL hooks from backup or repo.

set -e

# --- Output contract (pinned strings; tests source for assertions) ---
readonly CONTRACT_LINE_INSTALL="Installed hooks:"
readonly CONTRACT_LINE_BACKUP="Backup dir:"
readonly CONTRACT_LINE_REPO="Repo hooks:"
readonly CONTRACT_LINE_RESTORED_PREFIX="RESTORED "
readonly CONTRACT_LINE_RESTORED_BACKUP_SUFFIX=" from backup"
readonly CONTRACT_LINE_RESTORED_REPO_SUFFIX=" from repo (no backup available)"
readonly CONTRACT_LINE_DONE_PREFIX="Done. Verify with:"
readonly CONTRACT_FATAL_NO_INSTALL="FATAL: Cannot find installed hooks path."
readonly CONTRACT_FATAL_BAD_NAME="FATAL: Hook name must be a bare filename, not a path."
readonly CONTRACT_FATAL_NOT_FOUND_SUFFIX=" not found in backup or repo"
# Dry-run output contract
readonly EHR_RESOLVED_PREFIX="Resolved install path:"
readonly EHR_WOULD_RESTORE_PREFIX="Would restore:"

# Sentinel for test-source mode: when set, exit after defining constants.
# WARNING: This guard uses `return` to exit the sourced context. Caller MUST
# source this script at top level — sourcing inside a function causes `return`
# to return from the function, not from the source, and the script body will
# execute. Setting this var when executing the script directly (not sourcing)
# produces a silent no-op exit 0; do not set it in normal shell environments.
if [ -n "${EMERGENCY_RESTORE_SOURCE_ONLY:-}" ]; then
  return 0 2>/dev/null || exit 0
fi

# --dry-run: list what would be restored without writing
DRY_RUN=""
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
  shift
fi

# BASH_SOURCE-based repo root resolution (no git dependency)
SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"

# Detect back-door override before resolution
INSTALL_PATH_OVERRIDE=""
if [ -n "${INSTALL_PATH:-}" ]; then
  INSTALL_PATH_OVERRIDE=1
else
  INSTALL_PATH=$(python3 - <<'PYEOF' 2>/dev/null || true
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [e for versions in d.get('plugins', {}).values()
               for e in versions if e.get('scope') == 'user']
    entries.sort(key=lambda e: e.get('lastUpdated', ''), reverse=True)
    for e in entries:
        ip = e.get('installPath', '')
        if ip and os.path.isdir(os.path.join(ip, 'hooks')):
            print(ip); break
except Exception:
    pass
PYEOF
)
  if [ -z "$INSTALL_PATH" ]; then
    # Fallback: find by pattern
    INSTALL_PATH=$(find "$HOME/.claude/plugins/cache" -type d -path "*/sweetclaude/sweetclaude/*" \
      -name hooks -exec dirname {} \; 2>/dev/null | head -1 || true)
  fi
fi

if [ -z "$INSTALL_PATH" ] || [ ! -d "$INSTALL_PATH/hooks" ]; then
  echo "$CONTRACT_FATAL_NO_INSTALL" >&2
  echo "Try manually: ls ~/.claude/plugins/cache/sweetclaude/sweetclaude/" >&2
  exit 1
fi

# Prefix check (skipped for explicit override)
if [ -z "$INSTALL_PATH_OVERRIDE" ]; then
  case "$INSTALL_PATH" in
    "$HOME/.claude/plugins/"*) : ;;
    *)
      echo "FATAL: Resolved install path is outside plugin tree: $INSTALL_PATH" >&2
      exit 1
      ;;
  esac
fi

HOOKS_DIR="$INSTALL_PATH/hooks"
BACKUP_DIR="$INSTALL_PATH/hooks.bak"
TARGET_HOOK="${1:-}"

# Validate target hook is a bare filename
if [ -n "$TARGET_HOOK" ]; then
  case "$TARGET_HOOK" in
    */* | *..*)
      echo "$CONTRACT_FATAL_BAD_NAME" >&2
      exit 1
      ;;
  esac
fi

# Dry-run mode: enumerate what would be restored without writing
if [ -n "$DRY_RUN" ]; then
  echo "$EHR_RESOLVED_PREFIX $INSTALL_PATH"
  if [ -n "$TARGET_HOOK" ]; then
    echo "$EHR_WOULD_RESTORE_PREFIX $TARGET_HOOK"
  else
    DRY_SOURCE=""
    if [ -d "$BACKUP_DIR" ] && [ "$(find "$BACKUP_DIR" -name '*.sh' 2>/dev/null | wc -l | tr -d ' ')" -gt 0 ]; then
      DRY_SOURCE="$BACKUP_DIR"
    else
      DRY_SOURCE="$REPO_ROOT/hooks"
    fi
    for hook in "$DRY_SOURCE"/*.sh; do
      [ -f "$hook" ] || continue
      echo "$EHR_WOULD_RESTORE_PREFIX $(basename "$hook")"
    done
  fi
  exit 0
fi

echo "$CONTRACT_LINE_INSTALL $HOOKS_DIR"
echo "$CONTRACT_LINE_BACKUP      $BACKUP_DIR"
echo "$CONTRACT_LINE_REPO      $REPO_ROOT/hooks/"
echo ""

if [ -n "$TARGET_HOOK" ]; then
  if [ -f "$BACKUP_DIR/$TARGET_HOOK" ]; then
    cp "$BACKUP_DIR/$TARGET_HOOK" "$HOOKS_DIR/$TARGET_HOOK"
    chmod +x "$HOOKS_DIR/$TARGET_HOOK"
    echo "${CONTRACT_LINE_RESTORED_PREFIX}${TARGET_HOOK}${CONTRACT_LINE_RESTORED_BACKUP_SUFFIX}"
  elif [ -f "$REPO_ROOT/hooks/$TARGET_HOOK" ]; then
    cp "$REPO_ROOT/hooks/$TARGET_HOOK" "$HOOKS_DIR/$TARGET_HOOK"
    chmod +x "$HOOKS_DIR/$TARGET_HOOK"
    echo "${CONTRACT_LINE_RESTORED_PREFIX}${TARGET_HOOK}${CONTRACT_LINE_RESTORED_REPO_SUFFIX}"
  else
    echo "FATAL: ${TARGET_HOOK}${CONTRACT_FATAL_NOT_FOUND_SUFFIX}" >&2
    exit 1
  fi
else
  RESTORE_SOURCE=""
  if [ -d "$BACKUP_DIR" ] && [ "$(find "$BACKUP_DIR" -name '*.sh' 2>/dev/null | wc -l | tr -d ' ')" -gt 0 ]; then
    RESTORE_SOURCE="$BACKUP_DIR"
    echo "Restoring ALL hooks from backup..."
  else
    RESTORE_SOURCE="$REPO_ROOT/hooks"
    echo "No backup found. Restoring ALL hooks from repo..."
  fi

  RESTORED_COUNT=0
  for hook in "$RESTORE_SOURCE"/*.sh; do
    [ -f "$hook" ] || continue
    cp "$hook" "$HOOKS_DIR/$(basename "$hook")"
    chmod +x "$HOOKS_DIR/$(basename "$hook")"
    echo "  ${CONTRACT_LINE_RESTORED_PREFIX}$(basename "$hook")"
    RESTORED_COUNT=$((RESTORED_COUNT + 1))
  done

  for meta in hooks.json hooks-manifest.json; do
    if [ -f "$RESTORE_SOURCE/$meta" ]; then
      cp "$RESTORE_SOURCE/$meta" "$HOOKS_DIR/$meta"
      echo "  ${CONTRACT_LINE_RESTORED_PREFIX}$meta"
    fi
  done

  if [ "$RESTORED_COUNT" -eq 0 ]; then
    echo "WARNING: no hooks found in backup or repo — nothing restored" >&2
    exit 1
  fi
fi

echo ""
echo "$CONTRACT_LINE_DONE_PREFIX bash -n $HOOKS_DIR/<hook>.sh"
echo "Write/Edit should be unblocked now."
```

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Restore completed successfully |
| 1 | Fatal error — install path not found, bad hook name, hook not in backup or repo, resolved path outside plugin tree, or zero hooks restored (backup and repo both empty) |

### `hooks.bak/` absence behavior

| Scenario | Behavior |
|---|---|
| `hooks.bak/` missing, repo has hooks/, no target arg | Falls back to copying from `$REPO_ROOT/hooks/`; prints `No backup found. Restoring ALL hooks from repo...` |
| `hooks.bak/` missing, repo has hooks/, target arg given | Per-file fallback: copies named hook from repo; prints `RESTORED <hook> from repo (no backup available)` |
| `hooks.bak/` missing, repo missing, no target arg | Loop body executes zero times; `RESTORED_COUNT` = 0; prints `WARNING: no hooks found in backup or repo — nothing restored` to stderr; exit 1 |
| `hooks.bak/` missing, repo missing, target arg given | `FATAL: <hook> not found in backup or repo` → exit 1 |
| `hooks.bak/` present but empty | Same as missing — `find ... -name '*.sh' \| wc -l` returns 0, falls back to repo |
| `hooks.bak/` present with `.sh` files, no target arg | Copies all `.sh` from backup + `hooks.json` + `hooks-manifest.json` if present |

---

## Deliverable 2: `tests/test-emergency-restore.sh`

A bash test script that exercises the emergency restore script in four scenarios. Runs under `set -euo pipefail` (loud failure mode appropriate for tests, contrasted with the script's `set -e`).

### Test isolation strategy

- **Sandboxed HOME.** Each test gets a fresh tmpdir and a fake `INSTALL_PATH` underneath it. The script's back-door (`INSTALL_PATH` env var set explicitly) bypasses the `$HOME/.claude/plugins/` prefix check, so tests can point the script anywhere.
- **No git.** Path resolution in the script uses `BASH_SOURCE`, not `git rev-parse`. Tests verify the script works without a git repo in the test sandbox.
- **Constant assertions via source.** The test sources the script with `EMERGENCY_RESTORE_SOURCE_ONLY=1` to capture the contract constants without running main logic. Assertions then compare actual output substrings against those constants.

### Test script

```bash
#!/usr/bin/env bash
# tests/test-emergency-restore.sh
# Verifies the emergency hook restore script's contract.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/emergency-hook-restore.sh"
TEST_TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TEST_TMPDIR"' EXIT

# Source the script for its output contract constants
# shellcheck disable=SC1090
EMERGENCY_RESTORE_SOURCE_ONLY=1 source "$SCRIPT"

PASS_COUNT=0
FAIL_COUNT=0

pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# --- Test 1: restores from backup when present ---
test_restore_from_backup() {
  local dir="$TEST_TMPDIR/t1"
  local install="$dir/install"
  mkdir -p "$install/hooks" "$install/hooks.bak"

  printf '#!/bin/bash\necho ok\n' > "$install/hooks.bak/test-guardian.sh"
  chmod +x "$install/hooks.bak/test-guardian.sh"
  printf '#!/bin/bash\nif [[ ; then\n' > "$install/hooks/test-guardian.sh"

  local output
  if output=$(INSTALL_PATH="$install" bash "$SCRIPT" 2>&1); then
    if bash -n "$install/hooks/test-guardian.sh" 2>/dev/null; then
      if printf '%s' "$output" | grep -q "${CONTRACT_LINE_RESTORED_PREFIX}test-guardian.sh"; then
        pass "test_restore_from_backup"
      else
        fail "test_restore_from_backup: output missing RESTORED line"
      fi
    else
      fail "test_restore_from_backup: restored hook still fails bash -n"
    fi
  else
    fail "test_restore_from_backup: script exited non-zero"
  fi
}

# --- Test 2: falls back to repo when no backup ---
test_fallback_to_repo() {
  local dir="$TEST_TMPDIR/t2"
  local install="$dir/install"
  mkdir -p "$install/hooks"
  # No hooks.bak/ created

  printf '#!/bin/bash\nif [[ ; then\n' > "$install/hooks/test-guardian.sh"

  local output
  if output=$(INSTALL_PATH="$install" bash "$SCRIPT" test-guardian.sh 2>&1); then
    if bash -n "$install/hooks/test-guardian.sh" 2>/dev/null; then
      if printf '%s' "$output" | grep -q "${CONTRACT_LINE_RESTORED_REPO_SUFFIX}"; then
        pass "test_fallback_to_repo"
      else
        fail "test_fallback_to_repo: output missing repo-fallback marker"
      fi
    else
      fail "test_fallback_to_repo: restored hook still fails bash -n"
    fi
  else
    fail "test_fallback_to_repo: script exited non-zero"
  fi
}

# --- Test 3: back-door INSTALL_PATH skips the plugin-tree prefix check ---
test_back_door_skips_prefix_check() {
  # Deliberately place the install path OUTSIDE $HOME/.claude/plugins/ to prove
  # the back-door bypasses the prefix guard. A non-back-door run (INSTALL_PATH
  # resolved from installed_plugins.json) would reject any path that does not
  # start with $HOME/.claude/plugins/.
  local dir="$TEST_TMPDIR/outside_home"
  local install="$dir/install"
  mkdir -p "$install/hooks" "$install/hooks.bak"

  printf '#!/bin/bash\necho ok\n' > "$install/hooks.bak/test-guardian.sh"
  chmod +x "$install/hooks.bak/test-guardian.sh"
  printf '#!/bin/bash\nif [[ ; then\n' > "$install/hooks/test-guardian.sh"

  # Confirm path is genuinely outside the plugin tree
  case "$install" in
    "$HOME/.claude/plugins/"*)
      fail "test_back_door_skips_prefix_check: TEST_TMPDIR unexpectedly inside plugin tree"
      return
      ;;
  esac

  local output
  local exit_code=0
  output=$(INSTALL_PATH="$install" bash "$SCRIPT" 2>&1) || exit_code=$?

  if [ "$exit_code" -ne 0 ]; then
    fail "test_back_door_skips_prefix_check: script exited $exit_code (expected 0 — prefix check should have been bypassed)"
    return
  fi

  if printf '%s' "$output" | grep -q "outside plugin tree"; then
    fail "test_back_door_skips_prefix_check: prefix-check rejection fired despite back-door"
    return
  fi

  # Confirm contract output lines still emitted
  if ! printf '%s' "$output" | grep -q "$CONTRACT_LINE_INSTALL"; then
    fail "test_back_door_skips_prefix_check: missing CONTRACT_LINE_INSTALL"
    return
  fi
  if ! printf '%s' "$output" | grep -q "$CONTRACT_LINE_DONE_PREFIX"; then
    fail "test_back_door_skips_prefix_check: missing CONTRACT_LINE_DONE_PREFIX"
    return
  fi

  # Confirm restoration actually happened
  if bash -n "$install/hooks/test-guardian.sh" 2>/dev/null; then
    pass "test_back_door_skips_prefix_check"
  else
    fail "test_back_door_skips_prefix_check: hook was not restored to valid state"
  fi
}

# --- Test 4: --dry-run lists what would be restored without writing ---
test_dry_run_preview() {
  local dir="$TEST_TMPDIR/t4"
  local install="$dir/install"
  mkdir -p "$install/hooks" "$install/hooks.bak"

  printf '#!/bin/bash\necho ok\n' > "$install/hooks.bak/test-guardian.sh"
  chmod +x "$install/hooks.bak/test-guardian.sh"
  # Broken hook — must remain broken after --dry-run
  printf '#!/bin/bash\nif [[ ; then\n' > "$install/hooks/test-guardian.sh"

  local output
  if output=$(INSTALL_PATH="$install" bash "$SCRIPT" --dry-run 2>&1); then
    if ! printf '%s' "$output" | grep -q "$EHR_RESOLVED_PREFIX"; then
      fail "test_dry_run_preview: missing resolved-path line"
      return
    fi
    if ! printf '%s' "$output" | grep -q "$EHR_WOULD_RESTORE_PREFIX"; then
      fail "test_dry_run_preview: missing would-restore line"
      return
    fi
    # Hook must NOT have been restored (still fails bash -n)
    if bash -n "$install/hooks/test-guardian.sh" 2>/dev/null; then
      fail "test_dry_run_preview: hook was modified in dry-run mode"
    else
      pass "test_dry_run_preview"
    fi
  else
    fail "test_dry_run_preview: --dry-run exited non-zero"
  fi
}

# --- Runner ---
test_restore_from_backup
test_fallback_to_repo
test_back_door_skips_prefix_check
test_dry_run_preview

echo ""
echo "Summary: $PASS_COUNT passed, $FAIL_COUNT failed"

if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi
```

---

## Deliverable 3: User guide sections

Added to `docs/user-guide/hook-development.md`. **STORY-304 creates this file as a stub** containing only the Recovery and Emergency Recovery sections. STORY-306 (currently deferred) will expand it with the full hook development workflow when it ships. (Ordering decision: blast-radius OQ2, Option A, 2026-05-19.)

### Section: Recovery

```markdown
## Recovery

When an installed hook has a syntax error or logic bug, Write and Edit
operations are blocked — the broken hook returns `{"ok": false}` for
every call. The Bash tool is unaffected because Write|Edit hooks only
match those two tools.

Three other hooks also match Bash, but none block a recovery `cp`:
`artifact-guardian.sh` (warn-only, gates only `git commit`),
`wip-limit.sh` (blocks only in Kanban mode at WIP limit, not during
recovery), and `preflight-guard.sh` (blocks until first valid invocation;
clears automatically once `phase.yaml` exists). In a normal recovery
scenario all three are either inactive or transparent.

### Automated repair

If the hook-repair skill is available:

    /sweetclaude:hook-repair

The skill diagnoses broken hooks, offers to restore from `hooks.bak/`,
and verifies the restoration.

### Manual repair

If the skill is unavailable, use Bash directly:

    # Identify the broken hook
    bash -n ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh

    # Restore from backup
    cp ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks.bak/<hook>.sh \
       ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh

    # Verify
    bash -n ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh

Replace `<ver>` with the installed version. Find it with:

    ls ~/.claude/plugins/cache/sweetclaude/sweetclaude/
```

### Section: Emergency Recovery (Break Glass)

```markdown
## Emergency Recovery (Break Glass)

If the hook-repair skill is itself broken or unavailable, use the
emergency restore script. This script has zero dependencies on
SweetClaude infrastructure.

### From inside a deadlocked Claude Code session

The Bash tool is never gated by Write/Edit hooks. Run:

    bash scripts/emergency-hook-restore.sh

### From a terminal outside Claude Code

    cd /path/to/sweetclaude-repo
    bash scripts/emergency-hook-restore.sh

### To restore a single hook

    bash scripts/emergency-hook-restore.sh test-guardian.sh

The script tries `hooks.bak/` first (last known-good state). If no
backup exists, it copies directly from the repo.

### If nothing works

If the repo is also broken and no backup exists:

1. Re-install SweetClaude from the plugin marketplace
2. Or: check out a known-good git tag and copy hooks manually:
   `git checkout v3.68.6 -- hooks/ && cp hooks/*.sh ~/.claude/plugins/cache/.../hooks/`

## What to Read Next

- [How It Works](how-it-works.md) — hook architecture and the Write|Edit matcher
- [Skills Reference](skills-reference.md) — full list of available skills including `/sweetclaude:hook-repair`
- [TDD](tdd.md) — the testing discipline that keeps hooks correct before they are synced
```

---

## Deliverable 4: `skills/hook-repair/SKILL.md`

A user-invocable skill that automates the recovery. Uses only the Bash tool (never Write/Edit, since those may be blocked).

```markdown
---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Restore broken installed hooks from backup. Uses Bash only — works when Write/Edit are blocked."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:hook-repair" 2>/dev/null || true`

# Hook Repair

Diagnose and restore broken installed hooks from the `hooks.bak/` backup.

**This skill uses ONLY the Bash tool.** It works when Write/Edit hooks are blocking
because the Bash tool is not gated by Write|Edit hook matchers.

## Step 1: Resolve installed path

Run the same python3 resolver the emergency script uses to find `INSTALL_PATH`.
If unresolved, stop and direct the user to `bash scripts/emergency-hook-restore.sh`.

## Step 2: Check for backup

If `$INSTALL_PATH/hooks.bak/` is missing, report and exit with alternatives:
1. Copy from repo
2. Run emergency script
3. Re-install from marketplace

## Step 3: Diagnose broken hooks

Run `bash -n` on every `$INSTALL_PATH/hooks/*.sh` and classify as OK or BROKEN.

## Step 4: Propose restoration via AskUserQuestion

For each BROKEN hook, ask the user before copying. Use AskUserQuestion with options:
- Restore all broken hooks
- Show details first
- Cancel

## Step 5: Restore and verify

`cp` from `hooks.bak/`, `chmod +x`, then re-run `bash -n`.
If still broken, the backup itself is bad — direct to emergency script.

## Rules

- **Bash only.** Never use Write or Edit tools in this skill.
- **Propose before applying.** Use AskUserQuestion for restoration decisions.
- **Verify after restoration.** Run bash -n on restored hooks to confirm.
```

---

## Deliverable 5: README and skills-reference entries

- `README.md` — add `hook-repair` to the skills index with one-line description and reference the break-glass script under a "Recovery" subsection.
- `docs/user-guide/skills-reference.md` — full entry for `sweetclaude:hook-repair` matching the existing skill-entry format (name, invocation, when to use, what it does, constraints).

---

## Dependencies

- **STORY-301** — creates `hooks.bak/` during sync. Until 301 ships, the skill falls through to the "no backup" branch and the emergency script falls back to repo copy.
- **STORY-306** — will expand `docs/user-guide/hook-development.md` when undeferred. STORY-304 creates that file as a stub (Recovery + Emergency Recovery sections only). The original 306-first ordering is superseded by blast-radius OQ2 Option A (2026-05-19).

---

## Out of scope

- Auto-repair without user confirmation (would violate propose-before-apply contract)
- Backup retention policy (single-generation backup is STORY-301's call)
- Cross-version recovery (restoring hooks from a different installed version than what is currently registered)
- Recovery for non-hook plugin assets (skills, commands, agents) — those are separate concerns
- Telemetry/metrics on recovery events
- A GUI or TUI for selecting hooks

---

## Design verification reference

> **Canonical acceptance criteria for IMPLEMENT and VERIFY are the 13-item table in `docs/product/backlog/stories/STORY-304-hook-repair-recovery.md` (criteria 304-1 through 304-13).** Those grep-based verification commands are what the implementer runs to confirm done. The table below is the spec author's design-intent mapping — useful for tracing criteria to deliverables, but not the authoritative verification list.

| # | Criterion | Verification | Deliverable |
|---|---|---|---|
| 304-1 | `docs/user-guide/hook-development.md` contains Recovery section | `grep -l "## Recovery" docs/user-guide/hook-development.md` | 3 |
| 304-2 | Recovery procedure includes exact `cp` command with path template | `grep "hooks.bak" docs/user-guide/hook-development.md` | 3 |
| 304-3 | Documentation explains why Bash works when Write/Edit is blocked | `grep -i "matcher\|Write.*Edit\|Bash" docs/user-guide/hook-development.md` | 3 |
| 304-4 | `sweetclaude:hook-repair` skill exists with `user-invocable: true` | `test -f skills/hook-repair/SKILL.md && grep -q 'user-invocable: true' skills/hook-repair/SKILL.md` | 4 |
| 304-5 | End-to-end manual test: break test-guardian → Write/Edit blocked → Bash cp → unblocked | Manual test, documented result | 1, 4 |
| 304-6 | `scripts/emergency-hook-restore.sh` exists and is executable | `test -x scripts/emergency-hook-restore.sh` | 1 |
| 304-7 | Emergency script restores hooks with zero SweetClaude dependencies | `bash tests/test-emergency-restore.sh` → all PASS | 1, 2 |
| 304-8 | Break-glass procedure documented with in-session and terminal instructions | `grep -i "break glass\|emergency" docs/user-guide/hook-development.md` | 3 |
| 304-9 | Test script asserts on pinned output contract constants | `grep -E 'CONTRACT_LINE_|CONTRACT_FATAL_' tests/test-emergency-restore.sh` | 2 |
| 304-10 | Back-door `INSTALL_PATH` skips prefix check | `test_back_door_skips_prefix_check` passes | 1, 2 |
| 304-11 | README and skills-reference list `hook-repair` | `grep hook-repair README.md docs/user-guide/skills-reference.md` | 5 |

---

## Known gaps

1. ~~**Circular dependency with STORY-306.**~~ *Resolved (blast-radius OQ2, Option A, 2026-05-19): STORY-304 creates `docs/user-guide/hook-development.md` as a stub with Recovery + Emergency Recovery sections. STORY-306 expands it later. No circular dependency remains.*

2. **In-place rewrite of v1.0 spec.** *Resolved: in-place rewrite.* Previous gap "create new parallel files vs rewrite in place" decided in favor of overwriting v1.0 with `supersedes:` frontmatter to keep one canonical artifact.

3. **Emergency script uses python3 for path resolution.** Script is "zero SweetClaude dependencies" but uses python3 to read `installed_plugins.json`. Python3 is available on macOS and all supported platforms; `find` fallback covers no-python3 case. Pure-bash JSON parsing is not worth the complexity.

4. **`hooks.bak/` may itself be broken.** If the most recent sync captured a broken state, the backup is also broken. The skill detects this (verify step) and directs to the emergency script, which falls back to the repo.

5. **No automatic re-execution of the originally blocked Write/Edit operation.** After repair, the user must re-issue the request. This is acceptable — auto-resume would be a separate, non-trivial feature.

6. **Test for `hooks.bak/`-absent-and-repo-absent corner.** Not covered by the four test functions. Considered: catastrophic-only scenario; the script's behavior (zero `.sh` files restored, no error) is acceptable but untested. Deferred to STORY-309 hardening if needed.

7. **Skill description triggers auto-invocation risk.** The phrase "restore broken hooks" in the description could pattern-match on unrelated user messages. Mitigation: skill is `user-invocable: true` and the description avoids verbs like "automatically" or "whenever".

8. **Third test function for the back-door path.** *Resolved: third test added.* `test_back_door_skips_prefix_check` verifies the `INSTALL_PATH` back-door bypasses the `$HOME/.claude/plugins/` prefix guard and that the script still emits the contract output lines and completes restoration.
