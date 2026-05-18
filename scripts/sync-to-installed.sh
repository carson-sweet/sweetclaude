#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_DIR="$(pwd)"
FORCE=false
DRY_RUN=false

for arg in "$@"; do
  case "$arg" in
    --force)   FORCE=true ;;
    --dry-run) DRY_RUN=true ;;
    *)         echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

# ── Path resolution ──────────────────────────────────────────────────────────

_resolve_install_path() {
  python3 -c "
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [e for versions in d.get('plugins', {}).values()
               for e in versions if e.get('scope') == 'user']
    entries.sort(key=lambda e: e.get('lastUpdated', ''), reverse=True)
    for e in entries:
        ip = e.get('installPath', '')
        if ip and os.path.isdir(os.path.join(ip, 'hooks')):
            print(ip)
            break
except Exception:
    pass
" 2>/dev/null
}

INSTALL_PATH=$(_resolve_install_path)
if [ -z "$INSTALL_PATH" ] || [ ! -d "$INSTALL_PATH" ]; then
  echo "ERROR: Cannot resolve installed plugin path." >&2
  echo "Check ~/.claude/plugins/installed_plugins.json" >&2
  exit 5
fi

case "$INSTALL_PATH" in
  "$HOME/.claude/plugins/"*) ;;
  *)
    echo "ERROR: INSTALL_PATH '$INSTALL_PATH' is outside expected prefix (~/.claude/plugins/)." >&2
    exit 5
    ;;
esac

echo "Repo:      $REPO_ROOT"
echo "Installed: $INSTALL_PATH"

# ── Phase check ──────────────────────────────────────────────────────────────

_read_phase() {
  local project_dir="$1"
  local phase=""

  if [ -f "$project_dir/.sweetclaude/state/phase.yaml" ]; then
    phase=$(grep "^phase:" "$project_dir/.sweetclaude/state/phase.yaml" 2>/dev/null | awk '{print $2}')
  fi

  if [ -z "$phase" ] && [ -f "$project_dir/.sweetclaude/state/sweetclaude.yaml" ]; then
    phase=$(SC_YAML="$project_dir/.sweetclaude/state/sweetclaude.yaml" python3 - <<'PYEOF' 2>/dev/null
import os
try:
    import yaml
    d = yaml.safe_load(open(os.environ['SC_YAML']))
    w = (d or {}).get('work', {}).get('active', {})
    print(w.get('phase', '') if w else '')
except ImportError:
    pass
PYEOF
)
    if [ -z "$phase" ]; then
      phase=$(grep "^ *phase:" "$project_dir/.sweetclaude/state/sweetclaude.yaml" 2>/dev/null \
        | head -1 | awk '{print $2}')
    fi
  fi

  printf '%s' "$phase"
}

PHASE=$(_read_phase "$PROJECT_DIR")
PHASE_LOWER=$(printf '%s' "$PHASE" | tr '[:upper:]' '[:lower:]')

if [ "$PHASE_LOWER" = "implement" ]; then
  if [ "$FORCE" = true ]; then
    echo "WARNING: Forcing sync during IMPLEMENT phase."
  else
    echo "ERROR: Sync blocked — phase is IMPLEMENT." >&2
    echo "The installed hooks are your safety net. Do not overwrite them during implementation." >&2
    echo "Use --force to override (logs to decision-log.md)." >&2
    exit 1
  fi
fi

# ── Test gate (STORY-302 adds implementation here) ───────────────────────────

# ── Dry-run exit ─────────────────────────────────────────────────────────────

if [ "$DRY_RUN" = true ]; then
  echo "Dry run: all checks passed. Would sync to $INSTALL_PATH"
  exit 0
fi

# ── Force decision log (after dry-run exit — only log actual forced syncs) ───

if [ "$FORCE" = true ] && [ "$PHASE_LOWER" = "implement" ]; then
  DECISION_LOG="$PROJECT_DIR/.sweetclaude/state/decision-log.md"
  if [ -f "$DECISION_LOG" ]; then
    LAST_NUM=$(grep -oE '^\| [0-9]+' "$DECISION_LOG" | tr -d '| ' | sort -n | tail -1 || echo "0")
    [ -z "$LAST_NUM" ] && LAST_NUM=0
    NEXT_NUM=$((LAST_NUM + 1))
    DATE=$(date +%Y-%m-%d)
    printf '| %d | %s | IMPLEMENT | Force-synced hooks to installed path during implement phase | Developer override via --force flag |\n' \
      "$NEXT_NUM" "$DATE" >> "$DECISION_LOG"
  else
    echo "WARNING: --force override not logged — decision-log.md not found at $DECISION_LOG" >&2
  fi
fi

# ── Backup (STORY-301 adds implementation here) ──────────────────────────────

# ── Sync hooks ───────────────────────────────────────────────────────────────

echo "Syncing hooks..."
if ! rsync -a "$REPO_ROOT/hooks/" "$INSTALL_PATH/hooks/"; then
  echo "ERROR: Hook sync failed." >&2
  exit 4
fi
chmod +x "$INSTALL_PATH/hooks/"*.sh 2>/dev/null || true

# ── Post-sync checks (STORY-305 adds symlink check here) ────────────────────

# ── Sync non-hook artifacts ──────────────────────────────────────────────────

echo "Syncing skills, scripts, config..."

rsync -a "$REPO_ROOT/skills/" "$INSTALL_PATH/skills/" || echo "WARNING: skills sync failed (non-fatal)" >&2
rsync -a --exclude='__pycache__' --exclude='*.pyc' "$REPO_ROOT/scripts/" "$INSTALL_PATH/scripts/" || echo "WARNING: scripts sync failed (non-fatal)" >&2

mkdir -p ~/.claude/scripts/sweetclaude
rsync -a --exclude='__pycache__' --exclude='*.pyc' "$REPO_ROOT/scripts/" ~/.claude/scripts/sweetclaude/ || echo "WARNING: scripts mirror sync failed (non-fatal)" >&2

if [ -d "$REPO_ROOT/config" ]; then
  mkdir -p ~/.claude/config/sweetclaude
  rsync -a "$REPO_ROOT/config/" ~/.claude/config/sweetclaude/ || echo "WARNING: config sync failed (non-fatal)" >&2
fi

MANIFEST_VER=$(REPO="$REPO_ROOT" python3 - <<'PYEOF' 2>/dev/null || true
import json, os
print(json.load(open(os.environ['REPO'] + '/package.json'))['version'])
PYEOF
)
case "$MANIFEST_VER" in
  */* | *..* | "") MANIFEST_VER="" ;;
esac
if [ -n "$INSTALL_PATH" ] && [ -n "$MANIFEST_VER" ]; then
  PLUGIN_CACHE_PARENT=$(dirname "$INSTALL_PATH")
  VERSION_DIR="$PLUGIN_CACHE_PARENT/$MANIFEST_VER"
  if [ "$VERSION_DIR" != "$INSTALL_PATH" ] && [ -d "$PLUGIN_CACHE_PARENT" ]; then
    mkdir -p "$VERSION_DIR/skills" "$VERSION_DIR/hooks" "$VERSION_DIR/scripts"
    rsync -a "$REPO_ROOT/skills/" "$VERSION_DIR/skills/" || echo "WARNING: version-dir skills sync failed (non-fatal)" >&2
    rsync -a "$REPO_ROOT/hooks/" "$VERSION_DIR/hooks/" || echo "WARNING: version-dir hooks sync failed (non-fatal)" >&2
    rsync -a --exclude='__pycache__' --exclude='*.pyc' "$REPO_ROOT/scripts/" "$VERSION_DIR/scripts/" || echo "WARNING: version-dir scripts sync failed (non-fatal)" >&2
    [ -d "$REPO_ROOT/.claude-plugin" ] && rsync -a "$REPO_ROOT/.claude-plugin/" "$VERSION_DIR/.claude-plugin/" || true
    for f in CLAUDE.md package.json LICENSE; do
      [ -f "$REPO_ROOT/$f" ] && cp "$REPO_ROOT/$f" "$VERSION_DIR/"
    done
  fi
fi

echo "Sync complete."
