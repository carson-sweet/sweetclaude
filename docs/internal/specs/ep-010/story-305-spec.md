---
id: SPEC-305
story: STORY-305
epic: EP-010
version: 1.0
date: 2026-05-18
status: draft
---

# Specification: STORY-305 Session-start symlink detection

## User story

As a SweetClaude developer, I want the system to detect at session start if any installed hooks are symlinks to the repo so that the two-copy safety buffer is never silently compromised.

## Deliverables

1. New step in `hooks/session-preflight.sh` — symlink check
2. New sub-step in `skills/fix-sweetclaude/SKILL.md` — symlink repair
3. Post-sync symlink verification in `scripts/sync-to-installed.sh` (created by STORY-300)

## Technical design

### session-preflight.sh: symlink detection

New step inserted after Step 11 (executable check) and before Step 12 (state generation). Step 10 was removed in PR #61, so the new step uses Step 10's slot (reusing the removed number is cleaner than adding Step 11b).

`session-preflight.sh` runs FROM the installed path as a plugin-native hook. `$HOOK_DIR` (resolved in Step 5, lines 87-97) is already the installed hooks directory. The check iterates all `.sh` files in `$HOOK_DIR`:

```bash
# ── Step 10: Health Check — symlink detection ────────────────────────────────

_SC_SYMLINKED=""
for _sc_hook in "$HOOK_DIR"/*.sh; do
  [ -e "$_sc_hook" ] || [ -L "$_sc_hook" ] || continue
  [ -L "$_sc_hook" ] && _SC_SYMLINKED="${_SC_SYMLINKED}$(basename "$_sc_hook") "
done

if [ -n "$_SC_SYMLINKED" ]; then
  emit_heal \
    "Installed hooks contain symlinks — self-hosting safety compromised." \
    "Symlinked hooks: $_SC_SYMLINKED. Symlinks bypass the two-copy safety buffer: edits to the repo immediately affect running hooks. Run /sweetclaude:fix-sweetclaude to replace symlinks with regular file copies."
  exit 0
fi
```

**Design decisions:**
- Uses `emit_heal` (not `emit_block`). The session can proceed — symlinks are a safety concern, not a crash. The user is directed to `fix-sweetclaude` for repair.
- Checks ALL `.sh` files, not just the 13 registered in `hooks.json`. A symlinked utility hook (e.g., `generate-session-state.sh`) is equally dangerous.
- Reports all symlinked hooks in one message, not one per hook.
- Early exit after `emit_heal` — if symlinks exist, skip state generation (Step 12) since the session is in a degraded state.

### fix-sweetclaude: symlink repair

New sub-step 7e in the hook audit section (after 7d, version reconciliation). Two phases: detection, then repair.

**Detection phase:** Resolves the installed hooks directory via `CLAUDE_PLUGIN_ROOT` (if set, append `/hooks`) or falls back to `installed_plugins.json` resolution (same pattern as shared-conventions.md `_resolve_install_path`). Iterates all `.sh` files, reports any that are symlinks with their targets.

```bash
_SC_HOOK_DIR="${CLAUDE_PLUGIN_ROOT:-}"
if [ -z "$_SC_HOOK_DIR" ]; then
  _SC_HOOK_DIR=$(python3 -c "
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    for versions in d.get('plugins', {}).values():
        for e in versions:
            ip = e.get('installPath', '')
            if ip and 'sweetclaude' in ip.lower() and os.path.isdir(os.path.join(ip, 'hooks')):
                print(os.path.join(ip, 'hooks')); break
except Exception:
    pass
" 2>/dev/null)
else
  _SC_HOOK_DIR="$_SC_HOOK_DIR/hooks"
fi

if [ -n "$_SC_HOOK_DIR" ] && [ -d "$_SC_HOOK_DIR" ]; then
  _SYMLINKS=""
  for _h in "$_SC_HOOK_DIR"/*.sh; do
    [ -L "$_h" ] && _SYMLINKS="${_SYMLINKS}$(basename "$_h"): -> $(readlink "$_h")\n"
  done
  if [ -n "$_SYMLINKS" ]; then
    printf "SYMLINKS_FOUND\n%b" "$_SYMLINKS"
  else
    echo "NO_SYMLINKS"
  fi
else
  echo "HOOK_DIR_NOT_FOUND"
fi
```

**Proposal contract:** If `SYMLINKS_FOUND`, present via AskUserQuestion before executing any repair. The user sees which hooks are symlinked and where they point, then approves the replacement.

**Repair phase** (after user approval): For each symlinked hook, resolves the target using `readlink` (BSD-compatible, single-level), resolves relative paths against the symlink's directory, validates the target is a regular file, and atomically replaces the symlink via `mktemp`/`cp`/`mv`.

```bash
for _h in "$_SC_HOOK_DIR"/*.sh; do
  if [ -L "$_h" ]; then
    _link_dir=$(dirname "$_h")
    _raw_target=$(readlink "$_h")
    if [ "${_raw_target#/}" = "$_raw_target" ]; then
      _target="$_link_dir/$_raw_target"
    else
      _target="$_raw_target"
    fi
    if [ ! -f "$_target" ] || [ -L "$_target" ]; then
      echo "SKIPPED: $(basename "$_h") — target '$_raw_target' is not a regular file"
      continue
    fi
    _tmp=$(mktemp "${_h}.XXXXXX")
    cp "$_target" "$_tmp"
    chmod +x "$_tmp"
    mv "$_tmp" "$_h"
    echo "REPLACED: $(basename "$_h")"
  fi
done
```

### sync-to-installed.sh: post-sync verification

Added to the post-sync checks (Step 7 in the sync pipeline, after the rsync). Verifies that no hooks became symlinks during sync (shouldn't happen with `rsync -a` but guards against it):

```bash
for _hook in "$INSTALL_PATH/hooks/"*.sh; do
  if [ -L "$_hook" ]; then
    echo "ERROR: Post-sync symlink detected: $(basename "$_hook"). Sync may be corrupted." >&2
    exit 6
  fi
done
```

## Constraints

- `session-preflight.sh` Step 10 was removed in PR #61 (commit `3e5df42`). The new symlink check reuses this step number. Read the current file before implementing — the PR #61 changes are already reflected in the codebase.
- `HOOK_DIR` resolution (lines 87-97 of session-preflight.sh) handles both `realpath` and manual symlink resolution. The resolved `HOOK_DIR` is already the real path, not a symlink itself.
- `fix-sweetclaude` Step 7b already verifies no project-scope hooks exist. The symlink repair (7e) is a natural extension of the hook audit section.
- `readlink -f` may not be available on all macOS versions. Fallback: `readlink` (without `-f`) followed by manual resolution, or use the Python `os.path.realpath()` fallback.

## Success criteria

| # | Criterion | Verification |
|---|---|---|
| 305-1 | `session-preflight.sh` checks installed hooks for symlinks | `grep "\-L" hooks/session-preflight.sh` |
| 305-2 | Symlink detected → warning contains "symlink" and "fix-sweetclaude" | Replace installed hook with symlink, trigger preflight → output contains both strings |
| 305-3 | No symlinks → no warning | All hooks are regular files → preflight produces no symlink warning |
| 305-4 | `fix-sweetclaude` replaces symlinked hook with regular file copy | Symlink exists → invoke fix → `[ -L hook ]` returns false, content matches original target |
| 305-5 | `sync-to-installed.sh` verifies no symlinks post-sync with exit code 6 | Inject symlink at install path → run sync → exit code 6, stderr contains "symlink" |

## Dependencies

- STORY-300 (sync script exists, for the post-sync check)

## Known gaps

1. **`readlink -f` portability.** macOS ships with BSD `readlink` which does not support `-f` by default. GNU coreutils `readlink -f` works if installed via Homebrew. The implementation should use `readlink` (single-level, sufficient for our case since we only need the immediate target) or fall back to Python `os.path.realpath()`. This is an implementation detail, not a spec gap — noting it for the implementer.
