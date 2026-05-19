---
id: DESIGN-300
story: STORY-300
spec: SPEC-300
epic: EP-010
version: 1.0
date: 2026-05-18
status: done
---

# Design: STORY-300 Phase-aware sync gate

## Overview

Create `scripts/sync-to-installed.sh` — the canonical mechanism for syncing the repo to the installed plugin path. This script is the foundation that STORY-301, 302, and 305 extend. It also integrates a phase check into `experimental-feature-setup`.

## File: scripts/sync-to-installed.sh

### Structure

```bash
#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Sync repo to installed plugin path with safety gates.
# Usage: bash scripts/sync-to-installed.sh [--force] [--dry-run]

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
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
  # [shared convention: see shared-conventions.md]
}

INSTALL_PATH=$(_resolve_install_path)
if [ -z "$INSTALL_PATH" ] || [ ! -d "$INSTALL_PATH" ]; then
  echo "ERROR: Cannot resolve installed plugin path." >&2
  echo "Check ~/.claude/plugins/installed_plugins.json" >&2
  exit 5
fi

# Sanity check: installed path must be under ~/.claude/plugins/
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
  # [shared convention: see shared-conventions.md]
}

PROJECT_DIR="$(pwd)"
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
rsync -a "$REPO_ROOT/scripts/" "$INSTALL_PATH/scripts/" || echo "WARNING: scripts sync failed (non-fatal)" >&2

mkdir -p ~/.claude/scripts/sweetclaude
rsync -a "$REPO_ROOT/scripts/" ~/.claude/scripts/sweetclaude/ || echo "WARNING: scripts mirror sync failed (non-fatal)" >&2

if [ -d "$REPO_ROOT/config" ]; then
  mkdir -p ~/.claude/config/sweetclaude
  rsync -a "$REPO_ROOT/config/" ~/.claude/config/sweetclaude/ || echo "WARNING: config sync failed (non-fatal)" >&2
fi

# Version-named dir (matches experimental-feature-setup behavior)
MANIFEST_VER=$(REPO="$REPO_ROOT" python3 - <<'PYEOF' 2>/dev/null || true
import json, os
print(json.load(open(os.environ['REPO'] + '/package.json'))['version'])
PYEOF
)
if [ -n "$INSTALL_PATH" ] && [ -n "$MANIFEST_VER" ]; then
  PLUGIN_CACHE_PARENT=$(dirname "$INSTALL_PATH")
  VERSION_DIR="$PLUGIN_CACHE_PARENT/$MANIFEST_VER"
  if [ "$VERSION_DIR" != "$INSTALL_PATH" ] && [ -d "$PLUGIN_CACHE_PARENT" ]; then
    mkdir -p "$VERSION_DIR/skills" "$VERSION_DIR/hooks" "$VERSION_DIR/scripts"
    rsync -a "$REPO_ROOT/skills/" "$VERSION_DIR/skills/"
    rsync -a "$REPO_ROOT/hooks/" "$VERSION_DIR/hooks/"
    rsync -a "$REPO_ROOT/scripts/" "$VERSION_DIR/scripts/"
    [ -d "$REPO_ROOT/.claude-plugin" ] && rsync -a "$REPO_ROOT/.claude-plugin/" "$VERSION_DIR/.claude-plugin/"
    for f in CLAUDE.md package.json LICENSE; do
      [ -f "$REPO_ROOT/$f" ] && cp "$REPO_ROOT/$f" "$VERSION_DIR/"
    done
  fi
fi

echo "Sync complete."
```

### Design notes

1. **Placeholder comments for future stories.** The script includes `# (STORY-NNN adds implementation here)` markers where 301, 302, and 305 will insert their steps. This makes the implementation order clear without creating stubs.

2. **Decision log entry numbering.** The script scans all rows with `grep -oE '^\| [0-9]+'`, sorts numerically, and takes the maximum. Robust against trailing separator rows, empty lines, and manual edits.

3. **rsync flags.** Uses `rsync -a` (archive mode, additive). No `--delete` — stale files are acceptable in development. The production `update` skill handles `--delete`.

4. **Version-named dir sync.** Replicated from `experimental-feature-setup` Step 4. This ensures the version-specific cache directory stays in sync.

## File: skills/experimental-feature-setup/SKILL.md

### Change

Add phase check to Step 3 (before the sync commands), between the `SYNC_ABORT` check and the rsync block:

```markdown
## Step 3b: Phase check

\`\`\`bash
PHASE=""
if [ -f "$PROJECT_DIR/.sweetclaude/state/phase.yaml" ]; then
  PHASE=$(grep "^phase:" "$PROJECT_DIR/.sweetclaude/state/phase.yaml" 2>/dev/null | awk '{print $2}')
fi
if [ -z "$PHASE" ] && [ -f "$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" ]; then
  PHASE=$(SC_YAML="$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" python3 - <<'PYEOF' 2>/dev/null
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
  # Fallback if PyYAML not installed
  if [ -z "$PHASE" ]; then
    PHASE=$(grep "^ *phase:" "$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" 2>/dev/null \
      | head -1 | awk '{print $2}')
  fi
fi
PHASE_LOWER=$(printf '%s' "$PHASE" | tr '[:upper:]' '[:lower:]')
if [ "$PHASE_LOWER" = "implement" ]; then
  echo "PHASE_BLOCKED"
else
  echo "PHASE_OK"
fi
\`\`\`

If `PHASE_BLOCKED`: stop with:
> "Sync blocked — the active phase is IMPLEMENT. The installed hooks are your safety net during implementation. Sync after IMPLEMENT completes, or use `bash scripts/sync-to-installed.sh --force` if you understand the risk."
```

### Blast radius mitigation

- `experimental-feature-setup` is an untracked local-only skill. Changes don't propagate through git. This limits the blast radius but also means the change must be manually re-applied if the skill is regenerated.
- The phase check is read-only and cannot cause data loss. Worst case: a false positive blocks a sync that would have been safe.

## Testing strategy

New test file: `tests/test-sync.sh` (or appended to `test-hooks.sh` — either works, but a separate file keeps the sync tests cleanly separated from hook behavior tests).

Test cases for STORY-300:

| Test | Setup | Action | Expected |
|---|---|---|---|
| Phase implement blocks sync | `phase.yaml` with `phase: implement` | Run sync | Exit 1, output contains "IMPLEMENT" |
| Phase IMPLEMENT (uppercase) blocks | `phase.yaml` with `phase: IMPLEMENT` | Run sync | Exit 1 |
| Phase verify allows sync | `phase.yaml` with `phase: verify` | Run sync --dry-run | Exit 0 |
| No phase file allows sync | No `phase.yaml`, no `sweetclaude.yaml` | Run sync --dry-run | Exit 0 |
| sweetclaude.yaml v2 phase blocks | `sweetclaude.yaml` with `work.active.phase: implement`, no `phase.yaml` | Run sync | Exit 1 |
| --force overrides phase check | `phase.yaml` with `phase: implement` | Run sync --force --dry-run | Exit 0 |
| --force logs to decision log | `phase.yaml` with `phase: implement`, decision-log.md exists with ≥1 row | Run sync --force (real sync, not --dry-run) | New row in decision-log.md with incremented entry number |
| --force --dry-run does NOT log | `phase.yaml` with `phase: implement`, decision-log.md exists | Run sync --force --dry-run | Exit 0, no new row in decision-log.md |
| --dry-run does not modify files | Normal state | Run sync --dry-run | Exit 0, no files changed at installed path |

Tests use fixture directories with fake `installed_plugins.json` pointing to a temp install path.

**Additional test file criterion:** `tests/test-sync.sh` must exist and pass. This file holds all sync-related tests for STORY-300, 301, 302, and 305. See criterion 300-11.
