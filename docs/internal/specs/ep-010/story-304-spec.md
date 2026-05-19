---
id: SPEC-304
story: STORY-304
epic: EP-010
version: 1.0
date: 2026-05-18
status: draft
---

# Specification: STORY-304 Bash-based hook repair recovery procedure

## User story

As a SweetClaude developer whose session is blocked by a broken installed hook, I want a documented and optionally automated recovery path using the Bash tool so that I can restore the last known-good hook without leaving Claude Code.

## Deliverables

1. Recovery procedure section in `docs/user-guide/hook-development.md` (file created by STORY-306)
2. `skills/hook-repair/SKILL.md` — escape skill for automated recovery

## Technical design

### Why Bash works when Write/Edit is blocked

`test-guardian.sh` and `auto-test-runner.sh` match `Write|Edit` only (registered in `hooks/hooks.json` with `"matcher": "Write|Edit"`). The Bash tool is a different tool name — it is not matched by these hooks. When an installed hook is broken, Write/Edit are blocked but Bash remains available.

This is not a bypass — it is the intended escape hatch. The hook architecture deliberately does not gate Bash because Bash is needed for build commands, test execution, and (as this story codifies) recovery.

### Recovery procedure (manual)

Documented in the user guide. The exact command template:

```bash
# 1. Identify the broken hook
bash -n ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh

# 2. Restore from backup
cp ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks.bak/<hook>.sh \
   ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh

# 3. Verify the restored hook
bash -n ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh
```

The `<ver>` placeholder is resolved by checking `installed_plugins.json` or listing the cache directory.

### skills/hook-repair/SKILL.md

A user-invocable skill that automates the recovery. It uses only the Bash tool (never Write/Edit, since those may be blocked).

**Behavior:**

1. Resolve installed hooks path from `installed_plugins.json`
2. Check if `hooks.bak/` exists at the installed path
3. If no backup exists, report error and provide manual instructions
4. Run `bash -n` on each installed `.sh` file to identify broken hooks
5. For each broken hook, present the repair via AskUserQuestion:
   - "Restore `<hook>.sh` from backup?" → Yes / No / Show diff first
6. On approval, `cp hooks.bak/<hook>.sh hooks/<hook>.sh` via Bash
7. Verify restored hook with `bash -n`
8. Report result

**If hooks.bak/ does not exist:**

This happens on first use before any sync has run. The skill reports:

> "No backup found at `hooks.bak/`. This means no sync has been run yet (the backup is created during sync). Recovery options:
> 1. If the repo has the correct version: `cp hooks/<hook>.sh` from the repo to the installed path
> 2. If you know the installed version: re-install from the plugin marketplace"

**Skill constraints:**
- Must use ONLY Bash tool for all file operations
- Must not assume Write/Edit are available
- Must propose before applying (consistent with fix-sweetclaude contract)

### Break-glass emergency recovery script

A standalone bash script at `scripts/emergency-hook-restore.sh` that works when EVERYTHING is broken — the hook-repair skill, the sync script, the session-preflight, all of it. This is the absolute last resort.

**Design principles:**
- Zero dependencies on SweetClaude infrastructure (no skills, no hooks, no Python, no YAML parsing)
- Pure bash + cp + standard unix tools
- Can be invoked via the Bash tool from inside a deadlocked Claude Code session
- Can also be run directly from a terminal outside Claude Code
- Self-contained: resolves all paths internally, no arguments required (but accepts optional hook name)

**Script behavior:**

```bash
#!/bin/bash
# Emergency hook restore — run this when everything else is broken.
# Usage: bash scripts/emergency-hook-restore.sh [hook-name.sh]
# No arguments: restores ALL hooks from backup or repo.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Resolve installed path (pure bash + python3 one-liner — no yaml, no sweetclaude)
# Allow override for testing
if [ -n "${INSTALL_PATH:-}" ]; then
  : # Use provided INSTALL_PATH
else
  INSTALL_PATH=$(python3 - <<'PYEOF' 2>/dev/null
import json, os
d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
entries = [e for versions in d.get('plugins', {}).values()
           for e in versions if e.get('scope') == 'user']
entries.sort(key=lambda e: e.get('lastUpdated', ''), reverse=True)
for e in entries:
    ip = e.get('installPath', '')
    if ip and os.path.isdir(os.path.join(ip, 'hooks')):
        print(ip); break
PYEOF
)
fi

if [ -z "$INSTALL_PATH" ]; then
  # Fallback: find it by pattern
  INSTALL_PATH=$(find ~/.claude/plugins/cache -type d -path "*/sweetclaude/sweetclaude/*" \
    -name hooks -exec dirname {} \; 2>/dev/null | head -1)
fi

if [ -z "$INSTALL_PATH" ] || [ ! -d "$INSTALL_PATH/hooks" ]; then
  echo "FATAL: Cannot find installed hooks path." >&2
  echo "Try manually: ls ~/.claude/plugins/cache/sweetclaude/sweetclaude/" >&2
  exit 1
fi

HOOKS_DIR="$INSTALL_PATH/hooks"
BACKUP_DIR="$INSTALL_PATH/hooks.bak"
TARGET_HOOK="${1:-}"  # Optional: specific hook to restore

# Validate target hook is a bare filename (no path traversal)
if [ -n "$TARGET_HOOK" ]; then
  case "$TARGET_HOOK" in
    */* | *..*)
      echo "FATAL: Hook name must be a bare filename, not a path." >&2
      exit 1
      ;;
  esac
fi

echo "Installed hooks: $HOOKS_DIR"
echo "Backup dir:      $BACKUP_DIR"
echo "Repo hooks:      $REPO_ROOT/hooks/"
echo ""

# Strategy: try backup first, fall back to repo copy
if [ -n "$TARGET_HOOK" ]; then
  # Restore a specific hook
  if [ -f "$BACKUP_DIR/$TARGET_HOOK" ]; then
    cp "$BACKUP_DIR/$TARGET_HOOK" "$HOOKS_DIR/$TARGET_HOOK"
    chmod +x "$HOOKS_DIR/$TARGET_HOOK"
    echo "RESTORED $TARGET_HOOK from backup"
  elif [ -f "$REPO_ROOT/hooks/$TARGET_HOOK" ]; then
    cp "$REPO_ROOT/hooks/$TARGET_HOOK" "$HOOKS_DIR/$TARGET_HOOK"
    chmod +x "$HOOKS_DIR/$TARGET_HOOK"
    echo "RESTORED $TARGET_HOOK from repo (no backup available)"
  else
    echo "FATAL: $TARGET_HOOK not found in backup or repo" >&2
    exit 1
  fi
else
  # Restore ALL hooks
  RESTORE_SOURCE=""
  if [ -d "$BACKUP_DIR" ] && [ "$(find "$BACKUP_DIR" -name '*.sh' | wc -l)" -gt 0 ]; then
    RESTORE_SOURCE="$BACKUP_DIR"
    echo "Restoring ALL hooks from backup..."
  else
    RESTORE_SOURCE="$REPO_ROOT/hooks"
    echo "No backup found. Restoring ALL hooks from repo..."
  fi

  for hook in "$RESTORE_SOURCE"/*.sh; do
    [ -f "$hook" ] || continue
    cp "$hook" "$HOOKS_DIR/$(basename "$hook")"
    chmod +x "$HOOKS_DIR/$(basename "$hook")"
    echo "  RESTORED $(basename "$hook")"
  done

  # Also restore hooks.json and hooks-manifest.json
  for meta in hooks.json hooks-manifest.json; do
    if [ -f "$RESTORE_SOURCE/$meta" ]; then
      cp "$RESTORE_SOURCE/$meta" "$HOOKS_DIR/$meta"
      echo "  RESTORED $meta"
    fi
  done
fi

echo ""
echo "Done. Verify with: bash -n $HOOKS_DIR/<hook>.sh"
echo "Write/Edit should be unblocked now."
```

**Documentation in user guide:**

The break-glass procedure gets its own clearly-marked section in `docs/user-guide/hook-development.md`:

```
## Emergency Recovery (Break Glass)

If the hook-repair skill is broken or unavailable, use the emergency
restore script. This script has zero dependencies on SweetClaude — it
works when everything else is down.

### From inside a deadlocked Claude Code session:

The Bash tool is never gated by Write/Edit hooks. Paste this:

    bash scripts/emergency-hook-restore.sh

### From a terminal outside Claude Code:

    cd /path/to/sweetclaude-repo
    bash scripts/emergency-hook-restore.sh

### To restore a single hook:

    bash scripts/emergency-hook-restore.sh test-guardian.sh

The script tries hooks.bak/ first (last known-good from before the
most recent sync). If no backup exists, it copies from the repo.
```

## Constraints

- The recovery source (`hooks.bak/`) is created by STORY-301. If 301 has not shipped, there is no backup to restore from.
- The skill file itself lives at the repo path (`skills/hook-repair/SKILL.md`) and is synced to the installed path. If the skill file itself is broken at the installed path, the user must use the manual procedure.
- `artifact-guardian.sh` matches `Bash` — but it guards artifact file modifications, not arbitrary Bash commands. The `cp` to the hooks path is not within the artifact-protected paths, so it is not blocked.

## Success criteria

| # | Criterion | Verification |
|---|---|---|
| 304-1 | `docs/user-guide/hook-development.md` contains recovery procedure section | `grep -l "recovery" docs/user-guide/hook-development.md` |
| 304-2 | Recovery procedure includes exact `cp` command with path template | `grep "hooks.bak" docs/user-guide/hook-development.md` |
| 304-3 | Documentation explains why Bash works when Write/Edit is blocked | `grep -i "matcher\|Write.*Edit\|Bash" docs/user-guide/hook-development.md` |
| 304-4 | `sweetclaude:hook-repair` skill exists | `test -f skills/hook-repair/SKILL.md` |
| 304-5 | End-to-end: break test-guardian → Write/Edit blocked → Bash cp from hooks.bak → Write/Edit unblocked | Manual test, documented result |
| 304-6 | `scripts/emergency-hook-restore.sh` exists and is executable | `test -x scripts/emergency-hook-restore.sh` |
| 304-7 | Emergency script restores hooks with zero SweetClaude dependencies | Run from clean bash with no SweetClaude state → hooks restored |
| 304-8 | Break-glass procedure documented with both in-session and terminal instructions | `grep -i "break glass\|emergency" docs/user-guide/hook-development.md` |

## Dependencies

- STORY-301 (backup must exist for automated recovery to work; emergency script falls back to repo copy if no backup)
- STORY-306 (creates the doc file this story adds a section to)

## Known gaps

1. **Circular dependency with STORY-306.** This story adds content to a file that STORY-306 creates. Implementation order: 306 first (creates the file), then 304 (adds the recovery section). Alternatively, 304 creates a standalone doc and 306 integrates it. The story files imply 306 creates the file and 304 adds to it, which is the cleaner approach but requires sequencing.

2. **Emergency script uses python3 for path resolution.** The script is "zero SweetClaude dependencies" but uses python3 to read `installed_plugins.json`. Python3 is available on macOS and all supported platforms, and the fallback `find` path works without it. This is acceptable — pure-bash JSON parsing is not worth the complexity.
