#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_DIR="$(pwd)"
FORCE=false
DRY_RUN=false

REQUESTED_SCOPE=""
REQUESTED_KEY=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --force) FORCE=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --scope) [ "$#" -ge 2 ] || { echo "Missing --scope value" >&2; exit 1; }; REQUESTED_SCOPE="$2"; shift 2 ;;
    --plugin-key) [ "$#" -ge 2 ] || { echo "Missing --plugin-key value" >&2; exit 1; }; REQUESTED_KEY="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# Resolve only a single identified SweetClaude installation before any writes.
INSTALL_PATH=$(python3 - "$PROJECT_DIR" "$REQUESTED_SCOPE" "$REQUESTED_KEY" "$REPO_ROOT" <<'PYRESOLVE'
import json, os, pathlib, re, subprocess, sys
project, requested_scope, requested_key, repo_root = sys.argv[1:]
config = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or pathlib.Path.home() / ".claude").expanduser()
plugins = config / "plugins"
try:
    if requested_scope and requested_scope not in {"local", "project", "user"}:
        raise ValueError("Invalid scope; choose local, project, or user")
    data = json.loads((plugins / "installed_plugins.json").read_text())
    entries = data["plugins"]
    if not isinstance(entries, dict):
        raise ValueError("Plugin registry is invalid")
    root = subprocess.run(["git", "-C", project, "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True).stdout.strip() or project
    candidates = []
    for key, versions in entries.items():
        if not isinstance(key, str) or key.split("@", 1)[0] != "sweetclaude":
            continue
        if requested_key and key != requested_key:
            continue
        if not isinstance(versions, list):
            raise ValueError(f"Invalid registry entry: {key}")
        for entry in versions:
            if not isinstance(entry, dict):
                raise ValueError(f"Invalid registry entry: {key}")
            scope = entry.get("scope")
            if scope not in {"local", "project", "user"} or (requested_scope and scope != requested_scope):
                continue
            if scope in {"local", "project"}:
                project_path = entry.get("projectPath")
                if not project_path or pathlib.Path(project_path).resolve() != pathlib.Path(root).resolve():
                    continue
            value = entry.get("installPath")
            if not isinstance(value, str) or not value:
                raise ValueError(f"Missing installation path for {key}")
            target = pathlib.Path(value)
            if not target.is_absolute():
                raise ValueError("Installation path must be absolute")
            try:
                relative = target.relative_to(plugins)
            except ValueError:
                raise ValueError("Installation is outside the Claude plugin directory")
            current = plugins
            for part in relative.parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError(f"Symlinked installation path: {current}")
            if not target.resolve().is_relative_to(plugins.resolve()) or not (target / "hooks").is_dir():
                raise ValueError("Invalid plugin installation path")
            for name in ("hooks", "skills", "skill-library", "scripts", "config", ".claude-plugin"):
                destination = target / name
                if destination.is_symlink() or (destination.is_dir() and any(p.is_symlink() for p in destination.rglob("*"))):
                    raise ValueError(f"Symlinked plugin destination: {destination}")
            manifest = target / ".claude-plugin/plugin.json"
            if manifest.is_symlink() or not manifest.is_file() or json.loads(manifest.read_text()).get("name") != "sweetclaude":
                raise ValueError("Plugin bundle identity is not SweetClaude")
            candidates.append(target)
    if len(candidates) != 1:
        raise ValueError(f"Expected exactly one matching SweetClaude installation; found {len(candidates)}. Specify --scope and --plugin-key.")
    target = candidates[0]
    package = pathlib.Path(repo_root) / "package.json"
    if package.exists():
        version = json.loads(package.read_text()).get("version", "")
        if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", version):
            raise ValueError("Invalid source version")
        version_target = target.parent / version
        if version_target.is_symlink():
            raise ValueError("Symlinked version destination")
        if version_target.is_dir() and version_target != target:
            if any(p.is_symlink() for p in version_target.rglob("*")):
                raise ValueError("Symlink in version destination")
    print(target)
except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(1)
PYRESOLVE
) || exit 5

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

# ── Test gate ────────────────────────────────────────────────────────────────

TEST_HOOKS="$REPO_ROOT/tests/test-hooks.sh"

if [ ! -f "$TEST_HOOKS" ]; then
  echo "ERROR: Sync blocked — tests/test-hooks.sh not found." >&2
  exit 2
fi

if [ ! -x "$TEST_HOOKS" ]; then
  echo "ERROR: Sync blocked — tests/test-hooks.sh is not executable." >&2
  exit 2
fi

if ! bash "$TEST_HOOKS"; then
  if [ "$DRY_RUN" = true ]; then
    echo "Dry run: hook tests failed. Sync would be blocked." >&2
  else
    echo "ERROR: Sync blocked — tests failed. Fix failing tests before syncing." >&2
  fi
  exit 2
fi

echo "All hook tests passed."

# ── Dry-run exit ─────────────────────────────────────────────────────────────

if [ "$DRY_RUN" = true ]; then
  echo "Dry run: all checks passed (phase, tests). Would sync to $INSTALL_PATH"
  exit 0
fi

# ── Backup installed hooks ──────────────────────────────────────────────────

HOOKS_DIR="$INSTALL_PATH/hooks"
BACKUP_DIR="$INSTALL_PATH/hooks.bak"
BACKUP_TMP="$INSTALL_PATH/hooks.bak.tmp"

echo "Backing up installed hooks to hooks.bak/..."

rm -rf "$BACKUP_TMP" || true
if ! cp -R "$HOOKS_DIR" "$BACKUP_TMP"; then
  echo "ERROR: Backup failed (cp). Sync aborted." >&2
  rm -rf "$BACKUP_TMP" || true
  exit 3
fi

BACKUP_COUNT=$(find "$BACKUP_TMP" -name "*.sh" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -eq 0 ]; then
  echo "ERROR: Backup is empty (no .sh files). Sync aborted." >&2
  rm -rf "$BACKUP_TMP" || true
  exit 3
fi

if ! rm -rf "$BACKUP_DIR"; then
  echo "ERROR: Cannot remove old backup. Sync aborted." >&2
  rm -rf "$BACKUP_TMP" || true
  exit 3
fi
mv "$BACKUP_TMP" "$BACKUP_DIR"

echo "Backed up $BACKUP_COUNT hook scripts."

# ── Force decision log (after backup — only log syncs that pass all gates) ──

if [ "$FORCE" = true ] && [ "$PHASE_LOWER" = "implement" ]; then
  DECISION_LOG="$PROJECT_DIR/.sweetclaude/state/decision-log.md"
  if [ -f "$DECISION_LOG" ]; then
    DATE=$(date +%Y-%m-%d)
    printf '\n| — | %s | IMPLEMENT | Force-synced hooks to installed path during implement phase | Developer override via --force flag |\n' \
      "$DATE" >> "$DECISION_LOG"
  else
    echo "WARNING: --force override not logged — decision-log.md not found at $DECISION_LOG" >&2
  fi
fi

# ── Sync hooks ───────────────────────────────────────────────────────────────

echo "Syncing hooks..."
if ! rsync -a --delete "$REPO_ROOT/hooks/" "$INSTALL_PATH/hooks/"; then
  echo "ERROR: Hook sync failed. Restoring from backup..." >&2
  if [ -d "$BACKUP_DIR" ]; then
    mv "$INSTALL_PATH/hooks" "$INSTALL_PATH/hooks.failed" 2>/dev/null || true
    if cp -R "$BACKUP_DIR" "$INSTALL_PATH/hooks" 2>/dev/null; then
      rm -rf "$INSTALL_PATH/hooks.failed" 2>/dev/null || true
      echo "Restored hooks from backup." >&2
    else
      mv "$INSTALL_PATH/hooks.failed" "$INSTALL_PATH/hooks" 2>/dev/null || true
      echo "WARNING: Could not restore hooks from backup." >&2
    fi
  else
    echo "WARNING: No backup available to restore from." >&2
  fi
  exit 4
fi
chmod +x "$INSTALL_PATH/hooks/"*.sh 2>/dev/null || true

# ── Post-sync checks (STORY-305 adds symlink check here) ────────────────────

# ── Sync non-hook artifacts ──────────────────────────────────────────────────

echo "Syncing Tier 1 skills, Tier 2 library, scripts, config..."

rsync -a "$REPO_ROOT/skills/" "$INSTALL_PATH/skills/" || echo "WARNING: skills sync failed (non-fatal)" >&2
rsync -a "$REPO_ROOT/skill-library/" "$INSTALL_PATH/skill-library/" || echo "WARNING: skill library sync failed (non-fatal)" >&2
rsync -a --exclude='__pycache__' --exclude='*.pyc' "$REPO_ROOT/scripts/" "$INSTALL_PATH/scripts/" || echo "WARNING: scripts sync failed (non-fatal)" >&2

if [ -d "$REPO_ROOT/config" ]; then
  rsync -a "$REPO_ROOT/config/" "$INSTALL_PATH/config/" || echo "WARNING: config sync failed (non-fatal)" >&2
fi

MANIFEST_VER=$(REPO="$REPO_ROOT" python3 - <<'PYEOF' 2>/dev/null || true
import json, os
print(json.load(open(os.environ['REPO'] + '/package.json'))['version'])
PYEOF
)
case "$MANIFEST_VER" in
  */* | *..* | *[[:space:]]* | *\$* | *\`* | "") MANIFEST_VER="" ;;
esac
if [ -n "$INSTALL_PATH" ] && [ -n "$MANIFEST_VER" ]; then
  PLUGIN_CACHE_PARENT=$(dirname "$INSTALL_PATH")
  VERSION_DIR="$PLUGIN_CACHE_PARENT/$MANIFEST_VER"
  if [ "$VERSION_DIR" != "$INSTALL_PATH" ] && [ -d "$PLUGIN_CACHE_PARENT" ]; then
    mkdir -p "$VERSION_DIR/skills" "$VERSION_DIR/skill-library" "$VERSION_DIR/hooks" "$VERSION_DIR/scripts"
    rsync -a "$REPO_ROOT/skills/" "$VERSION_DIR/skills/" || echo "WARNING: version-dir skills sync failed (non-fatal)" >&2
    rsync -a "$REPO_ROOT/skill-library/" "$VERSION_DIR/skill-library/" || echo "WARNING: version-dir skill library sync failed (non-fatal)" >&2
    rsync -a "$REPO_ROOT/hooks/" "$VERSION_DIR/hooks/" || echo "WARNING: version-dir hooks sync failed (non-fatal)" >&2
    rsync -a --exclude='__pycache__' --exclude='*.pyc' "$REPO_ROOT/scripts/" "$VERSION_DIR/scripts/" || echo "WARNING: version-dir scripts sync failed (non-fatal)" >&2
    [ -d "$REPO_ROOT/.claude-plugin" ] && rsync -a "$REPO_ROOT/.claude-plugin/" "$VERSION_DIR/.claude-plugin/" || true
    for f in CLAUDE.md package.json LICENSE; do
      [ -f "$REPO_ROOT/$f" ] && cp "$REPO_ROOT/$f" "$VERSION_DIR/"
    done
  fi
fi

echo "Sync complete."
