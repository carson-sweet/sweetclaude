---
id: DESIGN-305
story: STORY-305
spec: SPEC-305
epic: EP-010
version: 1.0
date: 2026-05-18
status: draft
---

# Design: STORY-305 Session-start symlink detection

## Overview

Three small changes: (1) symlink check in session-preflight.sh, (2) symlink repair in fix-sweetclaude, (3) post-sync symlink verification in sync-to-installed.sh.

## File: hooks/session-preflight.sh

### Change

Replace the comment at line 203:

```bash
# ── Step 10: (removed — all hooks are now plugin-native; see fix #61) ────────
```

With:

```bash
# ── Step 10: Health Check — symlink detection ────────────────────────────────

_SC_SYMLINKED=""
for _sc_hook in "$HOOK_DIR"/*.sh; do
  [ -e "$_sc_hook" ] || [ -L "$_sc_hook" ] || continue
  if [ -L "$_sc_hook" ]; then
    _SC_SYMLINKED="${_SC_SYMLINKED}$(basename "$_sc_hook") "
  fi
done

if [ -n "$_SC_SYMLINKED" ]; then
  emit_heal \
    "Installed hooks contain symlinks — self-hosting safety compromised." \
    "Symlinked hooks: $_SC_SYMLINKED. Symlinks to the repo bypass the two-copy safety buffer — edits to the repo immediately affect running hooks. A syntax error could deadlock the session with no backup to restore from. Run /sweetclaude:fix-sweetclaude to replace symlinks with regular file copies."
  exit 0
fi
```

### Design notes

1. **`$HOOK_DIR` is already resolved.** Session-preflight Step 5 (lines 87-97) resolves `HOOK_DIR` by following symlinks to find the real directory. But this resolves the *directory* path — individual *files* within it can still be symlinks even if the directory itself is real. The `[ -L "$_sc_hook" ]` check catches file-level symlinks.

2. **`[ -e "$_sc_hook" ] || [ -L "$_sc_hook" ] || continue` guard.** Prevents the glob from matching nothing. Uses `[ -e ] || [ -L ]` instead of `[ -f ]` because `[ -f ]` follows symlinks — a dangling symlink (target deleted) would be silently skipped. The double guard catches both regular files and dangling symlinks.

3. **`emit_heal` not `emit_block`.** The session can proceed. Symlinks are a safety concern (broken safety buffer) but not a crash (the hooks themselves may work fine). The user is directed to fix-sweetclaude for repair.

4. **Early exit.** After `emit_heal`, the script exits 0. Steps 12-14 (state generation, state emission) are skipped. This is intentional: the session is in a degraded state. The heal message takes priority.

5. **All .sh files checked, not just registered hooks.** A symlinked utility script (e.g., `generate-session-state.sh`) is equally dangerous. The check is comprehensive.

### Blast radius mitigation

This is the **highest-risk change in EP-010** (session-preflight fires every session start).

Mitigations:
- The check is defensive: if the glob matches nothing, the loop body never executes, `_SC_SYMLINKED` stays empty, and the check is a no-op.
- The check uses basic shell operations (`[ -L ]`, `basename`) — no external commands, no Python, no YAML parsing.
- If the check itself has a bug (e.g., bad variable expansion), `set -e` at the script level would cause an exit — but session-preflight does NOT use `set -e`. An error in the check would produce a garbage `_SC_SYMLINKED` string, which would trigger `emit_heal` (false positive). False positive is safe — it directs the user to fix-sweetclaude, which would then find no symlinks and report all clear.
- **Testing:** Existing tests 8-10 create regular files (not symlinks) in their fixtures. They will continue to pass because the symlink check finds nothing and is a no-op. New test added for the symlink-detected case.

## File: skills/fix-sweetclaude/SKILL.md

### Change

Add Step 7e after Step 7d (version reconciliation). Insert before `## Step 8`:

```markdown
**7e: Check for symlinked hooks**

All installed hooks should be regular files, not symlinks. Symlinks bypass the
two-copy safety buffer.

\`\`\`bash
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
\`\`\`

If `SYMLINKS_FOUND`: present via AskUserQuestion:
> "These installed hooks are symlinks (breaks self-hosting safety):
> {list with targets}
>
> Replace with regular file copies of their targets?"
- **Replace all** — copy target content, remove symlink
- **Show me first** — list each symlink and its target
- **Leave them** — I know what I'm doing

If **Replace all**:

\`\`\`bash
for _h in "$_SC_HOOK_DIR"/*.sh; do
  if [ -L "$_h" ]; then
    _link_dir=$(dirname "$_h")
    _raw_target=$(readlink "$_h")
    # Resolve relative targets against the symlink's directory
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
\`\`\`

If `NO_SYMLINKS`: silent (no output for this step in the report).
If `HOOK_DIR_NOT_FOUND`: skip with warning.
```

### Design notes

1. **`readlink` without `-f` + relative path resolution.** Uses single-level `readlink` (BSD-compatible, available on macOS). Relative targets are resolved against the symlink's directory. After copy, the result is verified to not be a symlink itself (catches chained symlinks). Uses atomic copy-to-temp + `mv` pattern so a failed copy never leaves the hook missing.

2. **`CLAUDE_PLUGIN_ROOT` first.** If the environment variable is set (it is for plugin-native hooks), use it directly. Fall back to `installed_plugins.json` resolution if not.

3. **Proposal contract.** Consistent with fix-sweetclaude rules: propose before applying. The AskUserQuestion presents the symlinks and targets before any modification.

## File: scripts/sync-to-installed.sh

### Change

Replace `# ── Post-sync checks (STORY-305 adds symlink check here)` with:

```bash
# ── Post-sync checks ─────────────────────────────────────────────────────────

echo "Verifying no symlinks in synced hooks..."
for _hook in "$INSTALL_PATH/hooks/"*.sh; do
  [ -e "$_hook" ] || [ -L "$_hook" ] || continue
  if [ -L "$_hook" ]; then
    echo "ERROR: Post-sync symlink detected: $(basename "$_hook")" >&2
    echo "This should not happen with rsync. The installed path may be corrupted." >&2
    exit 6
  fi
done
```

### Design notes

This check is a safety net. `rsync -a` copies files, not symlinks-as-symlinks (unless the source contains symlinks, which it shouldn't). If a symlink appears post-sync, something unexpected happened. The exit code 6 signals a corrupted state.

The same check should also cover `$VERSION_DIR/hooks/` when the version-named dir sync (design-300.md) populates it. If a symlink passes through the primary install path check, it would also land in the version dir. The implementer should extend the loop to iterate both paths when `$VERSION_DIR` is set and differs from `$INSTALL_PATH`.

## Testing strategy

Tests added to `tests/test-hooks.sh`:

### Test 22: session-preflight — no warning when no symlinks

```bash
echo "[22] session-preflight.sh: no symlink warning for regular files"

FX22_HOME="$TMPROOT/home22"
FX22_PROJ="$TMPROOT/proj22"
FX22_DIR="$TMPROOT/hooks22"
mkdir -p "$FX22_HOME/.claude" "$FX22_DIR"
_make_git_repo "$FX22_PROJ"
mkdir -p "$FX22_PROJ/.sweetclaude/state"
printf 'schema_version: 2\nsetup_complete: true\n' > "$FX22_PROJ/.sweetclaude/state/sweetclaude.yaml"

# Copy session-preflight to fixture hooks dir
cp "$REPO_ROOT/hooks/session-preflight.sh" "$FX22_DIR/"
cp "$REPO_ROOT/hooks/hooks-manifest.json" "$FX22_DIR/"
# Create regular (non-symlink) .sh files
printf '#!/bin/bash\necho ok\n' > "$FX22_DIR/test-guardian.sh"
printf '#!/bin/bash\necho ok\n' > "$FX22_DIR/auto-test-runner.sh"
chmod +x "$FX22_DIR/"*.sh

OUTPUT22=$(cd "$FX22_PROJ" && HOME="$FX22_HOME" bash "$FX22_DIR/session-preflight.sh" 2>/dev/null) || true

if printf '%s' "$OUTPUT22" | grep -qi "symlink"; then
  fail "should not warn about symlinks when none exist"
else
  pass "no symlink warning for regular files"
fi
```

### Test 23: session-preflight — warning when symlink detected

```bash
echo "[23] session-preflight.sh: symlink warning when hook is symlinked"

FX23_HOME="$TMPROOT/home23"
FX23_PROJ="$TMPROOT/proj23"
FX23_DIR="$TMPROOT/hooks23"
mkdir -p "$FX23_HOME/.claude" "$FX23_DIR"
_make_git_repo "$FX23_PROJ"
mkdir -p "$FX23_PROJ/.sweetclaude/state"
printf 'schema_version: 2\nsetup_complete: true\n' > "$FX23_PROJ/.sweetclaude/state/sweetclaude.yaml"

# Copy session-preflight to fixture hooks dir
cp "$REPO_ROOT/hooks/session-preflight.sh" "$FX23_DIR/"
cp "$REPO_ROOT/hooks/hooks-manifest.json" "$FX23_DIR/"
# Create a real .sh file
printf '#!/bin/bash\necho ok\n' > "$FX23_DIR/real-hook.sh"
chmod +x "$FX23_DIR/real-hook.sh"
# Create a symlinked .sh file
ln -s "$FX23_DIR/real-hook.sh" "$FX23_DIR/symlinked-hook.sh"

OUTPUT23=$(cd "$FX23_PROJ" && HOME="$FX23_HOME" bash "$FX23_DIR/session-preflight.sh" 2>/dev/null) || true

if printf '%s' "$OUTPUT23" | grep -qi "symlink" \
   && printf '%s' "$OUTPUT23" | grep -qi "fix-sweetclaude"; then
  pass "symlink warning contains 'symlink' and 'fix-sweetclaude'"
else
  fail "should warn about symlinked hooks (got: $OUTPUT23)"
fi
```

### Design notes on tests 22-23

1. **HOOK_DIR resolution.** session-preflight resolves `HOOK_DIR` from `$0`'s directory. By copying the script to a fixture hooks dir and invoking it from there, `HOOK_DIR` points to the fixture — not the real repo hooks.

2. **Fixture completeness.** The fixture must include `hooks-manifest.json` (Step 8 checks for it), a `sweetclaude.yaml` with `schema_version: 2` and `setup_complete: true` (Steps 2-3 check for these), and a git repo (Step 1 checks `git rev-parse`). Missing any of these causes session-preflight to exit before reaching the Step 10 symlink check.

3. **HOME isolation.** `FX22_HOME` and `FX23_HOME` prevent session-preflight from reading real `~/.claude/` state (Step 9 checks `settings.json`).
