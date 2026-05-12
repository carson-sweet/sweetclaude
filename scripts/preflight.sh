#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude preflight helper
#
# Unified helper invoked by bootstrap (Step 0) and update (Step -1).
# Replaces the inline self-heal + decline-clear bash blocks in SKILL.md files.
#
# Usage:
#   bash ~/.claude/scripts/sweetclaude/preflight.sh [--from-update] [PROJECT_DIR]
#
#   --from-update   Also clears framework.update.declined (running /sweetclaude:update
#                   is explicit re-engagement; bootstrap should NOT pass this flag).
#   PROJECT_DIR     Project root (default: git rev-parse --show-toplevel or $PWD).
#
# Emits KEY=VALUE lines to stdout (always exits 0):
#   VERSIONLESS_PATH=<path>     Absolute path to ~/.claude/scripts/sweetclaude
#   SELF_HEAL=true|false        Whether versionless path was just populated
#   DECLINE_CLEARED=true|false  Whether update.declined was cleared
#   RUNNER=<path>               Resolved runner.py (empty string if not found)

set -u

VERSIONLESS="$HOME/.claude/scripts/sweetclaude"
FROM_UPDATE=false
PROJECT_DIR=""

for arg in "$@"; do
  case "$arg" in
    --from-update) FROM_UPDATE=true ;;
    *)             PROJECT_DIR="$arg" ;;
  esac
done

if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || true)
fi

SELF_HEAL=false
DECLINE_CLEARED=false

# 1. Self-heal: populate versionless path if absent.
#    Uses rsync for atomicity and dotfile safety (T11b fix).
#    Filters installed_plugins.json by scope=user + most-recent lastUpdated (T11a fix).
if [ ! -d "$VERSIONLESS" ]; then
  INSTALL_PATH=$(python3 -c "
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [e for versions in d.get('plugins', {}).values()
               for e in versions if e.get('scope') == 'user']
    entries.sort(key=lambda e: e.get('lastUpdated', ''), reverse=True)
    for e in entries:
        ip = e.get('installPath', '')
        if ip and os.path.isdir(os.path.join(ip, 'scripts')):
            print(ip)
            break
except Exception:
    pass
" 2>/dev/null)

  if [ -n "$INSTALL_PATH" ] && [ -d "$INSTALL_PATH/scripts" ]; then
    mkdir -p "$VERSIONLESS"
    if rsync -a "$INSTALL_PATH/scripts/" "$VERSIONLESS/" 2>/dev/null; then
      SELF_HEAL=true
    fi
  fi
fi

# 2. Resolve runner path.
RUNNER=""
if [ -f "$VERSIONLESS/migrations/runner.py" ]; then
  RUNNER="$VERSIONLESS/migrations/runner.py"
fi

# 3. Clear legacy decline — only when invoked from update context.
if [ "$FROM_UPDATE" = "true" ] && [ -n "$PROJECT_DIR" ] && \
   [ -f "$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" ]; then
  CLEAR_DECLINE="$VERSIONLESS/maintenance/clear-decline.py"
  if [ -f "$CLEAR_DECLINE" ]; then
    CLEAR_OUTPUT=$(python3 "$CLEAR_DECLINE" "$PROJECT_DIR" 2>/dev/null || true)
    printf '%s\n' "$CLEAR_OUTPUT" | grep -q 'cleared' && DECLINE_CLEARED=true
  fi
fi

# 4. Emit KEY=VALUE.
printf 'VERSIONLESS_PATH=%s\n' "$VERSIONLESS"
printf 'SELF_HEAL=%s\n'        "$SELF_HEAL"
printf 'DECLINE_CLEARED=%s\n'  "$DECLINE_CLEARED"
printf 'RUNNER=%s\n'           "$RUNNER"
