#!/bin/bash
# Emergency hook restore — run this when everything else is broken.
# Usage: bash scripts/emergency-hook-restore.sh [--dry-run] [hook-name.sh]
# No arguments: restores ALL hooks from backup or repo.
#
# Install-path resolution assumptions:
#   - installed_plugins.json uses scope="user" for user-scoped installs
#   - lastUpdated field is present and ISO-8601 sortable
#   - Plugin cache layout: ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/
#   - find fallback pattern: */sweetclaude/sweetclaude/*/hooks (dirname = install root)
# If your install does not match these assumptions, set INSTALL_PATH explicitly.
#
# ZERO sweetclaude dependencies — no skills, no hooks, no YAML parsing.
# Self-contained: pure bash + cp + standard unix tools + python3 for JSON.

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
readonly CONTRACT_FATAL_NOT_FOUND_PREFIX="FATAL: "
readonly EHR_RESOLVED_PREFIX="Resolved install path:"
readonly EHR_WOULD_RESTORE_PREFIX="Would restore:"

# Sentinel for test-source mode: when set, exit after defining constants.
# WARNING: This guard uses `return` to exit the sourced context. Caller MUST
# source this script at top level — sourcing inside a function causes `return`
# to return from the function, not from the source, and the script body will
# execute. Setting this var when executing the script directly (not sourcing)
# produces a silent no-op exit 0; do not set it in normal shell environments.
[ "${EMERGENCY_RESTORE_SOURCE_ONLY:-0}" = "1" ] && {
  [ "${BASH_SOURCE[0]:-}" = "$0" ] && \
    printf 'WARNING: EMERGENCY_RESTORE_SOURCE_ONLY is set — script is a no-op. Unset it to run normally.\n' >&2
  return 0 2>/dev/null || exit 0
}

# --dry-run: list what would be restored without writing
DRY_RUN=""
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
  shift
fi

# BASH_SOURCE-based repo root resolution (no git dependency)
SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"

# Detect back-door override before resolution.
# When INSTALL_PATH is set by caller, trust it verbatim — skip JSON resolution
# and prefix check. This is intentional for tests using tmpdir paths outside
# the plugin tree.
# DO NOT re-enable the prefix check unconditionally — tests rely on the bypass.
INSTALL_PATH_OVERRIDE=""
if [ -n "${INSTALL_PATH:-}" ]; then
  INSTALL_PATH_OVERRIDE=1
else
  if [ -z "${HOME:-}" ]; then
    printf 'FATAL: HOME is not set — cannot resolve install path\n' >&2
    exit 1
  fi
  # Step 1: JSON resolution via python3
  INSTALL_PATH=""
  if command -v python3 >/dev/null 2>&1; then
    _py_code=$(cat <<'PYEOF'
import json, sys, os
try:
    path = os.path.join(os.path.expanduser('~'), '.claude', 'plugins', 'installed_plugins.json')
    d = json.load(open(path))
    entries = []
    for plugin_name, versions in d.get('plugins', {}).items():
        if plugin_name == 'sweetclaude':
            for e in versions:
                if e.get('scope') == 'user':
                    entries.append(e)
    entries.sort(key=lambda e: e.get('lastUpdated', ''), reverse=True)
    for e in entries:
        ip = e.get('installPath', '')
        if ip and os.path.isdir(os.path.join(ip, 'hooks')):
            print(ip)
            break
except Exception:
    pass
PYEOF
)
    INSTALL_PATH=$(python3 -c "$_py_code" 2>/dev/null) || true
  else
    printf 'python3 not found — skipping JSON resolution, using find fallback\n' >&2
  fi

  # Step 2: find fallback if JSON gave nothing
  if [ -z "$INSTALL_PATH" ]; then
    INSTALL_PATH=$(find "$HOME/.claude/plugins/cache" -type d -path "*/sweetclaude/sweetclaude/*" -name hooks 2>/dev/null \
      | while IFS= read -r d; do
          printf '%s\t%s\n' "$(stat -f '%m' "$d" 2>/dev/null || stat -c '%Y' "$d" 2>/dev/null)" "$d"
        done \
      | sort -rn | head -1 | cut -f2- || true)
    if [ -n "$INSTALL_PATH" ]; then
      INSTALL_PATH="$(dirname "$INSTALL_PATH")"
    fi
  fi
fi

# Step 3: fatal if still no path or hooks/ directory missing
if [ -z "$INSTALL_PATH" ] || [ ! -d "$INSTALL_PATH/hooks" ]; then
  printf '%s\n' "$CONTRACT_FATAL_NO_INSTALL" >&2
  printf '%s\n' "Try manually: ls ~/.claude/plugins/cache/sweetclaude/sweetclaude/" >&2
  exit 1
fi

# Prefix check applies only when INSTALL_PATH was resolved via cascade (not back-door)
# AND only when the resolved path lacks a hooks.bak/ directory (which would indicate
# a legitimate SweetClaude installation created by the sync process).
# A path with a valid hooks.bak/ is treated as a trusted installation even if outside
# the expected plugin tree prefix (covers legitimate non-standard installs).
# When the caller sets INSTALL_PATH explicitly (test back-door), trust it entirely.
# DO NOT re-enable this check unconditionally — tests rely on the bypass to use
# tmpdir paths outside the plugin tree.
if [ -z "$INSTALL_PATH_OVERRIDE" ] && [ ! -d "$INSTALL_PATH/hooks.bak" ]; then
  case "$INSTALL_PATH" in
    "$HOME/.claude/plugins/"*) : ;;
    *)
      printf 'FATAL: Resolved install path is outside plugin tree: %s\n' "$INSTALL_PATH" >&2
      exit 1
      ;;
  esac
fi

HOOKS_DIR="$INSTALL_PATH/hooks"
BACKUP_DIR="$INSTALL_PATH/hooks.bak"
TARGET_HOOK="${1:-}"

# Validate target hook is a bare filename (no path separators) — before any output
if [ -n "$TARGET_HOOK" ]; then
  case "$TARGET_HOOK" in
    */*|-*)
      printf '%s\n' "$CONTRACT_FATAL_BAD_NAME" >&2
      exit 1
      ;;
  esac
fi

# Dry-run mode: enumerate what would be restored without writing anything
if [ -n "$DRY_RUN" ]; then
  printf '%s %s\n' "$EHR_RESOLVED_PREFIX" "$INSTALL_PATH"
  if [ -n "$TARGET_HOOK" ]; then
    printf '%s %s\n' "$EHR_WOULD_RESTORE_PREFIX" "$TARGET_HOOK"
  else
    DRY_SOURCE=""
    _sh_count=0
    if [ -d "$BACKUP_DIR" ]; then
      _sh_count=$(find "$BACKUP_DIR" -maxdepth 1 -name '*.sh' 2>/dev/null | wc -l | tr -d ' ')
    fi
    if [ "$_sh_count" -gt 0 ]; then
      DRY_SOURCE="$BACKUP_DIR"
    else
      DRY_SOURCE="$REPO_ROOT/hooks"
    fi
    for _hook in "$DRY_SOURCE"/*.sh; do
      # Guard is load-bearing: if glob matches nothing, bash passes the literal pattern as the loop variable.
      [ -f "$_hook" ] || continue
      printf '%s %s\n' "$EHR_WOULD_RESTORE_PREFIX" "$(basename "$_hook")"
    done
  fi
  exit 0
fi

# Non-dry-run: emit headers to stdout
printf '%s %s\n' "$CONTRACT_LINE_INSTALL" "$HOOKS_DIR"
printf '%s %s\n' "$CONTRACT_LINE_BACKUP" "$BACKUP_DIR"
printf '%s %s\n' "$CONTRACT_LINE_REPO" "$REPO_ROOT/hooks/"
printf '\n'

if [ -n "$TARGET_HOOK" ]; then
  # Named-hook restore: look in backup first, then repo.
  # Validate backup syntax before accepting it; fall through to repo on invalid backup.
  _backup_accepted=""
  if [ -f "$BACKUP_DIR/$TARGET_HOOK" ]; then
    if bash -n "$BACKUP_DIR/$TARGET_HOOK" 2>/dev/null; then
      _backup_accepted=1
    else
      printf 'backup copy invalid syntax — falling back to repo\n' >&2
    fi
  fi
  if [ -n "$_backup_accepted" ]; then
    cp -- "$BACKUP_DIR/$TARGET_HOOK" "$HOOKS_DIR/$TARGET_HOOK"
    chmod +x "$HOOKS_DIR/$TARGET_HOOK"
    printf '%s%s%s\n' "$CONTRACT_LINE_RESTORED_PREFIX" "$TARGET_HOOK" "$CONTRACT_LINE_RESTORED_BACKUP_SUFFIX"
  elif [ -f "$REPO_ROOT/hooks/$TARGET_HOOK" ]; then
    cp -- "$REPO_ROOT/hooks/$TARGET_HOOK" "$HOOKS_DIR/$TARGET_HOOK"
    chmod +x "$HOOKS_DIR/$TARGET_HOOK"
    printf '%s%s%s\n' "$CONTRACT_LINE_RESTORED_PREFIX" "$TARGET_HOOK" "$CONTRACT_LINE_RESTORED_REPO_SUFFIX"
  else
    printf '%s%s%s\n' "$CONTRACT_FATAL_NOT_FOUND_PREFIX" "$TARGET_HOOK" "$CONTRACT_FATAL_NOT_FOUND_SUFFIX" >&2
    exit 1
  fi
else
  # All-hooks restore: prefer backup if it has .sh files, else fall to repo
  RESTORE_SOURCE=""
  _sh_count=0
  if [ -d "$BACKUP_DIR" ]; then
    _sh_count=$(find "$BACKUP_DIR" -maxdepth 1 -name '*.sh' 2>/dev/null | wc -l | tr -d ' ')
  fi
  if [ "$_sh_count" -gt 0 ]; then
    RESTORE_SOURCE="$BACKUP_DIR"
    _restore_suffix="$CONTRACT_LINE_RESTORED_BACKUP_SUFFIX"
    printf '%s\n' "Restoring ALL hooks from backup..."
  else
    RESTORE_SOURCE="$REPO_ROOT/hooks"
    _restore_suffix="$CONTRACT_LINE_RESTORED_REPO_SUFFIX"
    printf '%s\n' "No backup found. Restoring ALL hooks from repo..."
  fi

  RESTORED_COUNT=0
  for _hook in "$RESTORE_SOURCE"/*.sh; do
    # Guard is load-bearing: if glob matches nothing, bash passes the literal pattern as the loop variable.
    [ -f "$_hook" ] || continue
    _hookname="$(basename "$_hook")"
    # In all-hooks backup mode, validate syntax; on failure fall through to repo copy for this hook.
    if [ "$RESTORE_SOURCE" = "$BACKUP_DIR" ] && ! bash -n "$_hook" 2>/dev/null; then
      printf 'backup copy invalid syntax — falling back to repo for %s\n' "$_hookname" >&2
      if [ -f "$REPO_ROOT/hooks/$_hookname" ]; then
        cp -- "$REPO_ROOT/hooks/$_hookname" "$HOOKS_DIR/$_hookname"
        chmod +x "$HOOKS_DIR/$_hookname"
        printf '%s%s%s\n' "$CONTRACT_LINE_RESTORED_PREFIX" "$_hookname" "$CONTRACT_LINE_RESTORED_REPO_SUFFIX"
        RESTORED_COUNT=$((RESTORED_COUNT + 1))
      fi
      continue
    fi
    cp -- "$_hook" "$HOOKS_DIR/$_hookname"
    chmod +x "$HOOKS_DIR/$_hookname"
    printf '%s%s%s\n' "$CONTRACT_LINE_RESTORED_PREFIX" "$_hookname" "$_restore_suffix"
    RESTORED_COUNT=$((RESTORED_COUNT + 1))
  done

  # Copy metadata files from RESTORE_SOURCE (backup or repo) and emit RESTORED lines
  for _meta in hooks.json hooks-manifest.json; do
    if [ -f "$RESTORE_SOURCE/$_meta" ]; then
      cp -- "$RESTORE_SOURCE/$_meta" "$HOOKS_DIR/$_meta"
      printf '%s%s%s\n' "$CONTRACT_LINE_RESTORED_PREFIX" "$_meta" "$_restore_suffix"
    fi
  done

  if [ "$RESTORED_COUNT" -eq 0 ]; then
    printf '%s\n' "WARNING: no hooks found in backup or repo — nothing restored" >&2
    exit 1
  fi
fi

printf '\n'
printf '%s %s\n' "$CONTRACT_LINE_DONE_PREFIX" "bash -n $HOOKS_DIR/<hook>.sh"
printf '%s\n' "Write/Edit should be unblocked now."
