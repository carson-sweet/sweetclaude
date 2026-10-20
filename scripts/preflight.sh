#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude preflight helper
#
# Unified helper invoked by bootstrap (Step 0) and update (Step -1).
# Replaces the inline self-heal + decline-clear bash blocks in SKILL.md files.
#
# Usage:
#   bash "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.sh" [--from-update] [PROJECT_DIR]
#
#   --from-update   Also clears framework.update.declined (running /sweetclaude:configure update
#                   is explicit re-engagement; bootstrap should NOT pass this flag).
#   PROJECT_DIR     Project root (default: git rev-parse --show-toplevel or $PWD).
#
# Emits KEY=VALUE lines to stdout (always exits 0):
#   RUNNER=<path>               Resolved runner.py (empty string if not found)
#   VERSION_DIR_HEALED=true|false Whether plugin cache version dir was repaired
#   DECLINE_CLEARED=true|false  Whether update.declined was cleared

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

DECLINE_CLEARED=false

# 1. Version-dir repair: if installPath exists but the version-named sibling dir
#    does not, create it and update installed_plugins.json to point there.
#    This fixes the one-time mismatch that occurs when the old update skill (pre-4.0.7)
#    synced files to the old dir name without creating a version-aligned directory.
_HEAL_OUT=$(python3 - << 'PY' 2>/dev/null
import json, os, subprocess, tempfile

path = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
try:
    with open(path) as f: d = json.load(f)
except Exception:
    raise SystemExit(0)

for k, versions in d.get('plugins', {}).items():
    if 'sweetclaude' not in k.lower():
        continue
    for entry in versions:
        if entry.get('scope') != 'user':
            continue
        install_path = entry.get('installPath', '').rstrip('/')
        version     = entry.get('version', '')
        if not install_path or not version or not os.path.isdir(install_path):
            continue
        parent      = os.path.dirname(install_path)
        version_dir = os.path.join(parent, version)
        if version_dir == install_path or os.path.isdir(version_dir):
            raise SystemExit(0)
        # Version-named dir is missing — create it from the existing installPath.
        os.makedirs(version_dir, exist_ok=True)
        ret = subprocess.run(['rsync', '-a', install_path + '/', version_dir + '/'],
                             capture_output=True)
        if ret.returncode != 0:
            raise SystemExit(1)
        entry['installPath'] = version_dir
        tmp = tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path),
                                         suffix='.tmp', delete=False)
        json.dump(d, tmp, indent=2)
        tmp.close()
        os.replace(tmp.name, path)
        print('healed')
        raise SystemExit(0)
PY
)
VERSION_DIR_HEALED=false
[ "$_HEAL_OUT" = "healed" ] && VERSION_DIR_HEALED=true

# 2. Resolve runner path from this script's directory.
RUNNER=""
if [ -f "$SCRIPT_DIR/migrations/runner.py" ]; then
  RUNNER="$SCRIPT_DIR/migrations/runner.py"
fi

# 3. Resolve SweetClaude plugin install/channel state.
SC_PLUGIN_OK=false
SC_PLUGIN_KEY=""
SC_PLUGIN_MARKETPLACE=""
SC_PLUGIN_LEGACY_MARKETPLACE=false
SC_PLUGIN_CHANNEL=""
SC_PLUGIN_EXPECTED_REF=""
SC_PLUGIN_EXPECTED_MARKETPLACE=""
SC_PLUGIN_INSTALL_PATH=""
SC_PLUGIN_VERSION=""
SC_PLUGIN_GIT_SHA=""
SC_PLUGIN_SCOPE=""
SC_PLUGIN_INSTALL_EXISTS=false
SC_PLUGIN_STALE_BETA=false
SC_PLUGIN_CHANNEL_RETIRED=false
SC_PLUGIN_RETIREMENT_TARGET_CHANNEL=""
SC_PLUGIN_MIN_SAFE_BETA_VERSION=""
SC_PLUGIN_UPDATE_COMMAND=""
SC_PLUGIN_RESTART_REQUIRED_AFTER_UPDATE=false
SC_PLUGIN_REASON=""
PLUGIN_STATE_SCRIPT="$SCRIPT_DIR/maintenance/plugin-state.py"
if [ -f "$PLUGIN_STATE_SCRIPT" ]; then
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    PLUGIN_STATE_OUT=$(python3 "$PLUGIN_STATE_SCRIPT" --project-dir "${PROJECT_DIR:-$PWD}" inspect --current-root "$CLAUDE_PLUGIN_ROOT" --shell 2>/dev/null || true)
  else
    PLUGIN_STATE_OUT=$(python3 "$PLUGIN_STATE_SCRIPT" --project-dir "${PROJECT_DIR:-$PWD}" inspect --shell 2>/dev/null || true)
  fi
  [ -n "$PLUGIN_STATE_OUT" ] && eval "$PLUGIN_STATE_OUT"
fi

# 4. Clear legacy decline — only when invoked from update context.
if [ "$FROM_UPDATE" = "true" ] && [ -n "$PROJECT_DIR" ] && \
   [ -f "$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" ]; then
  CLEAR_DECLINE="$SCRIPT_DIR/maintenance/clear-decline.py"
  if [ -f "$CLEAR_DECLINE" ]; then
    CLEAR_OUTPUT=$(python3 "$CLEAR_DECLINE" "$PROJECT_DIR" 2>/dev/null || true)
    printf '%s\n' "$CLEAR_OUTPUT" | grep -q 'cleared' && DECLINE_CLEARED=true
  fi
fi

# 5. Emit KEY=VALUE.
printf 'VERSION_DIR_HEALED=%s\n' "$VERSION_DIR_HEALED"
printf 'DECLINE_CLEARED=%s\n'    "$DECLINE_CLEARED"
printf 'RUNNER=%s\n'             "$RUNNER"
printf 'SC_PLUGIN_OK=%s\n'       "$SC_PLUGIN_OK"
printf 'SC_PLUGIN_KEY=%s\n'      "$SC_PLUGIN_KEY"
printf 'SC_PLUGIN_MARKETPLACE=%s\n' "$SC_PLUGIN_MARKETPLACE"
printf 'SC_PLUGIN_LEGACY_MARKETPLACE=%s\n' "$SC_PLUGIN_LEGACY_MARKETPLACE"
printf 'SC_PLUGIN_CHANNEL=%s\n'  "$SC_PLUGIN_CHANNEL"
printf 'SC_PLUGIN_EXPECTED_REF=%s\n' "$SC_PLUGIN_EXPECTED_REF"
printf 'SC_PLUGIN_EXPECTED_MARKETPLACE=%s\n' "$SC_PLUGIN_EXPECTED_MARKETPLACE"
printf 'SC_PLUGIN_INSTALL_PATH=%s\n' "$SC_PLUGIN_INSTALL_PATH"
printf 'SC_PLUGIN_VERSION=%s\n' "$SC_PLUGIN_VERSION"
printf 'SC_PLUGIN_GIT_SHA=%s\n' "$SC_PLUGIN_GIT_SHA"
printf 'SC_PLUGIN_SCOPE=%s\n' "$SC_PLUGIN_SCOPE"
printf 'SC_PLUGIN_INSTALL_EXISTS=%s\n' "$SC_PLUGIN_INSTALL_EXISTS"
printf 'SC_PLUGIN_STALE_BETA=%s\n' "$SC_PLUGIN_STALE_BETA"
printf 'SC_PLUGIN_CHANNEL_RETIRED=%s\n' "$SC_PLUGIN_CHANNEL_RETIRED"
printf 'SC_PLUGIN_RETIREMENT_TARGET_CHANNEL=%s\n' "$SC_PLUGIN_RETIREMENT_TARGET_CHANNEL"
printf 'SC_PLUGIN_MIN_SAFE_BETA_VERSION=%s\n' "$SC_PLUGIN_MIN_SAFE_BETA_VERSION"
printf 'SC_PLUGIN_UPDATE_COMMAND=%s\n' "$SC_PLUGIN_UPDATE_COMMAND"
printf 'SC_PLUGIN_RESTART_REQUIRED_AFTER_UPDATE=%s\n' "$SC_PLUGIN_RESTART_REQUIRED_AFTER_UPDATE"
printf 'SC_PLUGIN_REASON=%s\n' "$SC_PLUGIN_REASON"
