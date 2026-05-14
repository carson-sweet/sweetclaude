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

# 2. Version-dir repair: if installPath exists but the version-named sibling dir
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

# 3. Resolve runner path.
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

# 5. Emit KEY=VALUE.
printf 'VERSIONLESS_PATH=%s\n'   "$VERSIONLESS"
printf 'SELF_HEAL=%s\n'          "$SELF_HEAL"
printf 'VERSION_DIR_HEALED=%s\n' "$VERSION_DIR_HEALED"
printf 'DECLINE_CLEARED=%s\n'    "$DECLINE_CLEARED"
printf 'RUNNER=%s\n'             "$RUNNER"
