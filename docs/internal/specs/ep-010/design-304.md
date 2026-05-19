---
id: DESIGN-304
story: STORY-304
spec: SPEC-304
epic: EP-010
version: 1.0
date: 2026-05-18
status: draft
---

# Design: STORY-304 Bash-based hook repair recovery

## Overview

Three deliverables: (1) the `hook-repair` skill for automated recovery, (2) the `emergency-hook-restore.sh` standalone script for break-glass recovery, (3) recovery and break-glass sections in the hook development docs.

## File: skills/hook-repair/SKILL.md

### Structure

```markdown
---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Restore broken installed hooks from backup. Uses Bash only — works when Write/Edit are blocked."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:hook-repair" 2>/dev/null || true`

# Hook Repair

Diagnose and restore broken installed hooks from the `hooks.bak/` backup.

**This skill uses ONLY the Bash tool.** It works when Write/Edit hooks are blocking
because the Bash tool is not gated by Write|Edit hook matchers.

## Step 1: Resolve installed path

\`\`\`bash
INSTALL_PATH=$(python3 -c "
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [e for versions in d.get('plugins', {}).values()
               for e in versions if e.get('scope') == 'user']
    entries.sort(key=lambda e: e.get('lastUpdated', ''), reverse=True)
    for e in entries:
        ip = e.get('installPath', '')
        if ip and os.path.isdir(os.path.join(ip, 'hooks')):
            print(ip); break
except Exception:
    pass
" 2>/dev/null)

if [ -z "$INSTALL_PATH" ]; then
  echo "INSTALL_NOT_FOUND"
else
  echo "INSTALL_PATH=$INSTALL_PATH"
  ls "$INSTALL_PATH/hooks/"*.sh 2>/dev/null | wc -l | tr -d ' '
fi
\`\`\`

If `INSTALL_NOT_FOUND`: stop with:
> "Cannot find installed plugin path. Try the emergency script instead:
> `bash scripts/emergency-hook-restore.sh`"

## Step 2: Check for backup

\`\`\`bash
BACKUP_DIR="$INSTALL_PATH/hooks.bak"
if [ -d "$BACKUP_DIR" ]; then
  BACKUP_COUNT=$(find "$BACKUP_DIR" -name "*.sh" -type f | wc -l | tr -d ' ')
  echo "BACKUP_EXISTS=$BACKUP_COUNT"
else
  echo "NO_BACKUP"
fi
\`\`\`

If `NO_BACKUP`: report:
> "No `hooks.bak/` found at the installed path. This means no sync has been
> run since the backup system was added (STORY-301).
>
> **Alternative recovery options:**
> 1. Copy from the repo: `cp hooks/<hook>.sh $INSTALL_PATH/hooks/<hook>.sh`
> 2. Run the emergency script: `bash scripts/emergency-hook-restore.sh`
> 3. Re-install from marketplace"

Stop.

## Step 3: Diagnose broken hooks

\`\`\`bash
HOOKS_DIR="$INSTALL_PATH/hooks"
echo "Checking installed hooks for syntax errors..."
for hook in "$HOOKS_DIR"/*.sh; do
  [ -f "$hook" ] || continue
  if ! bash -n "$hook" 2>/dev/null; then
    echo "BROKEN:$(basename "$hook")"
  else
    echo "OK:$(basename "$hook")"
  fi
done
\`\`\`

Parse output. If no BROKEN hooks found:
> "All installed hooks pass syntax validation. If you're still experiencing
> issues, the problem may be a logic error rather than a syntax error. Check
> the hook output manually:
> `CLAUDE_FILE_PATH=test.js CLAUDE_TOOL_NAME=Write bash $INSTALL_PATH/hooks/<hook>.sh`"

If BROKEN hooks found, present each via **AskUserQuestion**:
> "Found broken hooks: {list}. Restore from backup?"
- **Restore all broken hooks** — copy each from hooks.bak/
- **Show me the details first** — run bash -n with error output for each
- **Cancel**

## Step 4: Restore

For each broken hook approved for restoration:

\`\`\`bash
HOOK_NAME="<hook>.sh"
cp "$INSTALL_PATH/hooks.bak/$HOOK_NAME" "$INSTALL_PATH/hooks/$HOOK_NAME"
chmod +x "$INSTALL_PATH/hooks/$HOOK_NAME"
bash -n "$INSTALL_PATH/hooks/$HOOK_NAME" 2>/dev/null && echo "RESTORED:$HOOK_NAME" || echo "STILL_BROKEN:$HOOK_NAME"
\`\`\`

If `STILL_BROKEN`: the backup itself is bad. Report:
> "Backup copy of {hook} also fails syntax validation. The backup was taken
> from a state that was already broken. Try the emergency script instead:
> `bash scripts/emergency-hook-restore.sh`
> (It falls back to copying from the repo.)"

## Step 5: Verify

\`\`\`bash
echo "Verifying all hooks..."
ALL_OK=true
for hook in "$INSTALL_PATH/hooks/"*.sh; do
  [ -f "$hook" ] || continue
  if ! bash -n "$hook" 2>/dev/null; then
    echo "STILL_BROKEN:$(basename "$hook")"
    ALL_OK=false
  fi
done
[ "$ALL_OK" = true ] && echo "ALL_HOOKS_OK"
\`\`\`

If `ALL_HOOKS_OK`:
> "All installed hooks pass syntax validation. Write/Edit should be unblocked."

## Rules

- **Bash only.** Never use Write or Edit tools in this skill.
- **Propose before applying.** Use AskUserQuestion for restoration decisions.
- **Verify after restoration.** Run bash -n on restored hooks to confirm.
```

### Design notes

1. **Bash-only contract.** Every file operation is done via Bash tool (`cp`, `chmod`, `bash -n`, `ls`). The skill never invokes Write or Edit because those may be blocked by the very hooks we're trying to fix.

2. **Diagnosis before restoration.** The skill runs `bash -n` on all installed hooks to identify which ones are broken. This prevents blind restoration and gives the user visibility into what's wrong.

3. **Graceful degradation.** If `hooks.bak/` doesn't exist, the skill provides alternative paths. If the backup is also broken, it directs to the emergency script. Each failure mode has a clear next step.

## File: scripts/emergency-hook-restore.sh

Full script as specified in SPEC-304. Key design points:

1. **Shebang and set -e.** Script is strict and self-contained.
2. **Path resolution.** Uses the shared convention (python3 + installed_plugins.json) with a `find` fallback.
3. **Restore strategy.** Backup first, repo fallback. Single hook or all hooks.
4. **Restores metadata files.** `hooks.json` and `hooks-manifest.json` are also copied, not just `.sh` files.
5. **chmod +x on every restored file.** Ensures executability.
6. **No SweetClaude dependencies.** No YAML parsing, no skill invocation, no phase checking. Pure bash + python3 one-liner for JSON.

## File: docs/user-guide/hook-development.md (sections added by this story)

### Section: Recovery

```markdown
## Recovery

When an installed hook has a syntax error or logic bug, Write and Edit
operations are blocked — the broken hook returns `{"ok": false}` for
every call. The Bash tool is unaffected because Write|Edit hooks only
match those two tools.

### Automated repair

If the hook-repair skill is available:

    /sweetclaude:hook-repair

The skill diagnoses broken hooks, offers to restore from `hooks.bak/`,
and verifies the restoration.

### Manual repair

If the skill is unavailable, use Bash directly:

    # Identify the broken hook
    bash -n ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh

    # Restore from backup
    cp ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks.bak/<hook>.sh \
       ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh

    # Verify
    bash -n ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh

Replace `<ver>` with the installed version. Find it with:

    ls ~/.claude/plugins/cache/sweetclaude/sweetclaude/
```

### Section: Emergency Recovery (Break Glass)

```markdown
## Emergency Recovery (Break Glass)

If the hook-repair skill is itself broken or unavailable, use the
emergency restore script. This script has zero dependencies on
SweetClaude infrastructure.

### From inside a deadlocked Claude Code session

The Bash tool is never gated by Write/Edit hooks. Run:

    bash scripts/emergency-hook-restore.sh

### From a terminal outside Claude Code

    cd /path/to/sweetclaude-repo
    bash scripts/emergency-hook-restore.sh

### To restore a single hook

    bash scripts/emergency-hook-restore.sh test-guardian.sh

The script tries `hooks.bak/` first (last known-good state). If no
backup exists, it copies directly from the repo.

### If nothing works

If the repo is also broken and no backup exists:

1. Re-install SweetClaude from the plugin marketplace
2. Or: check out a known-good git tag and copy hooks manually:
   `git checkout v3.68.6 -- hooks/ && cp hooks/*.sh ~/.claude/plugins/cache/.../hooks/`
```

## Blast radius mitigation

- `test-skill-bash-blocks.sh` will automatically validate `skills/hook-repair/SKILL.md` bash blocks. All fenced bash in the skill must pass `bash -n`.
- The emergency script is tested by the test cases below (criterion 304-7).

## Emergency script tests

Added to `tests/test-sync.sh` (or a dedicated `tests/test-recovery.sh`):

### Test: emergency script restores all from backup

```bash
echo "[ER-1] emergency-hook-restore.sh: restores all hooks from backup"

ER1_DIR="$TMPROOT/er1"
ER1_INSTALL="$ER1_DIR/install"
mkdir -p "$ER1_INSTALL/hooks" "$ER1_INSTALL/hooks.bak"

# Good backup
printf '#!/bin/bash\necho ok\n' > "$ER1_INSTALL/hooks.bak/test-guardian.sh"
printf '{"hooks":[]}' > "$ER1_INSTALL/hooks.bak/hooks.json"
chmod +x "$ER1_INSTALL/hooks.bak/test-guardian.sh"

# Broken installed hook
printf '#!/bin/bash\nif [[ ; then\n' > "$ER1_INSTALL/hooks/test-guardian.sh"

# Override path resolution for the script
OUTPUT_ER1=$(INSTALL_PATH="$ER1_INSTALL" bash "$REPO_ROOT/scripts/emergency-hook-restore.sh" 2>/dev/null) || true

if bash -n "$ER1_INSTALL/hooks/test-guardian.sh" 2>/dev/null; then
  pass "emergency script restores from backup"
else
  fail "emergency script did not restore valid hook from backup"
fi
```

### Test: emergency script falls back to repo

```bash
echo "[ER-2] emergency-hook-restore.sh: falls back to repo when no backup"

ER2_DIR="$TMPROOT/er2"
ER2_INSTALL="$ER2_DIR/install"
mkdir -p "$ER2_INSTALL/hooks"
# No hooks.bak/ directory

# Broken installed hook
printf '#!/bin/bash\nif [[ ; then\n' > "$ER2_INSTALL/hooks/test-guardian.sh"

OUTPUT_ER2=$(INSTALL_PATH="$ER2_INSTALL" bash "$REPO_ROOT/scripts/emergency-hook-restore.sh" 2>/dev/null) || true

if bash -n "$ER2_INSTALL/hooks/test-guardian.sh" 2>/dev/null; then
  pass "emergency script falls back to repo copy"
else
  fail "emergency script did not restore from repo when no backup"
fi
```

### Test: emergency script restores single hook

```bash
echo "[ER-3] emergency-hook-restore.sh: restores single named hook"

ER3_DIR="$TMPROOT/er3"
ER3_INSTALL="$ER3_DIR/install"
mkdir -p "$ER3_INSTALL/hooks" "$ER3_INSTALL/hooks.bak"

printf '#!/bin/bash\necho ok\n' > "$ER3_INSTALL/hooks.bak/test-guardian.sh"
printf '#!/bin/bash\necho ok\n' > "$ER3_INSTALL/hooks.bak/auto-test-runner.sh"
chmod +x "$ER3_INSTALL/hooks.bak/"*.sh

# Break both
printf '#!/bin/bash\nif [[\n' > "$ER3_INSTALL/hooks/test-guardian.sh"
printf '#!/bin/bash\nif [[\n' > "$ER3_INSTALL/hooks/auto-test-runner.sh"

# Restore only test-guardian
OUTPUT_ER3=$(INSTALL_PATH="$ER3_INSTALL" bash "$REPO_ROOT/scripts/emergency-hook-restore.sh" test-guardian.sh 2>/dev/null) || true

if bash -n "$ER3_INSTALL/hooks/test-guardian.sh" 2>/dev/null \
   && ! bash -n "$ER3_INSTALL/hooks/auto-test-runner.sh" 2>/dev/null; then
  pass "single hook restore targets only named hook"
else
  fail "single hook restore affected wrong hooks"
fi
```

### Test: emergency script rejects path-traversal argument

```bash
echo "[ER-4] emergency-hook-restore.sh: rejects path traversal in argument"

ER4_DIR="$TMPROOT/er4"
ER4_INSTALL="$ER4_DIR/install"
mkdir -p "$ER4_INSTALL/hooks" "$ER4_INSTALL/hooks.bak"

OUTPUT_ER4=$(INSTALL_PATH="$ER4_INSTALL" bash "$REPO_ROOT/scripts/emergency-hook-restore.sh" "../../etc/passwd" 2>&1)
ER4_EXIT=$?

if [ "$ER4_EXIT" -ne 0 ] && printf '%s' "$OUTPUT_ER4" | grep -qi "bare filename\|invalid"; then
  pass "rejects path traversal argument with non-zero exit"
else
  fail "should reject argument with path separators and exit non-zero (exit=$ER4_EXIT, got: $OUTPUT_ER4)"
fi
```

### Design note on emergency script testability

The emergency script resolves `INSTALL_PATH` internally. For testing, the script accepts `INSTALL_PATH` as an environment variable override — if set, it skips the `installed_plugins.json` resolution and uses the provided path. This allows fixture-based testing without a real plugin installation.

## Testing strategy

| Test | Action | Expected |
|---|---|---|
| Skill detects broken hook | Break an installed hook with syntax error | Skill reports it as BROKEN |
| Skill restores from backup | Break hook, backup has good copy | cp succeeds, bash -n passes |
| Skill handles missing backup | Remove hooks.bak/ | Reports NO_BACKUP with alternatives |
| Emergency script restores all | Break multiple hooks, run script | All restored, bash -n passes |
| Emergency script falls back to repo | Remove hooks.bak/, run script | Copies from repo, bash -n passes |
| Emergency script restores single hook | Break one hook, run with arg | Only that hook restored |
| test-skill-bash-blocks.sh passes | Run existing test suite | hook-repair skill bash blocks pass validation |
