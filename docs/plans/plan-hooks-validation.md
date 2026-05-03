# Plan: Hooks Validation at Session Start
**Status:** planned
**Date:** 2026-05-03
**Priority:** high — silent failure of TDD enforcement destroys trust

---

## Problem

Hooks are the behavioral enforcement layer. If a hook file exists on disk but isn't registered in `hooks.json`, it silently doesn't run. If it's registered but deleted from disk, Claude Code emits an error but only at the moment the hook fires — not at session start. There is no proactive check that the hook system is intact.

Audit of `hooks/` directory vs `hooks.json`:

| Hook file | Registered | Notes |
|---|---|---|
| `session-preflight.sh` | ✓ SessionStart | |
| `preflight-guard.sh` | ✓ PreToolUse | |
| `test-guardian.sh` | ✓ PreToolUse Write\|Edit | crown jewel |
| `tdd-prewrite-guardian.sh` | ✓ PreToolUse Write\|Edit | |
| `artifact-guardian.sh` | ✓ PreToolUse Bash | |
| `auto-test-runner.sh` | ✓ PostToolUse Write\|Edit | |
| `state-regenerator.sh` | ✓ PostToolUse Write\|Edit | |
| `version-bump.sh` | ✓ PostToolUse Bash | |
| `skill-tracker.sh` | ✓ PostToolUse Skill | |
| `phase-dwelling-guard.sh` | ✗ not registered | intentional — guardian-only |
| `auto-reindex.sh` | ✗ not registered | intentional — optional RAG feature |
| `git-checkpoint.sh` | ✗ not registered | unclear — needs investigation |
| `generate-session-state.sh` | ✗ not registered | library, called by session-preflight |

**Immediate gaps:** None of the core hooks are missing. The risk is future drift — a hook gets deleted during refactoring, or a new skill needs a hook that doesn't get registered.

**One gap to investigate:** `git-checkpoint.sh` is not registered and its intended trigger is unclear. Investigate before closing this plan.

---

## Solution

### Step 1: Hooks manifest

Create `hooks/hooks-manifest.json` — canonical list of every hook file, its purpose, registration status, and required vs. optional designation.

```json
{
  "schema_version": 1,
  "hooks": [
    {
      "file": "test-guardian.sh",
      "event": "PreToolUse",
      "matcher": "Write|Edit",
      "purpose": "Block edits to test files during TDD implementation phase",
      "required": true,
      "guardian_only": false
    },
    {
      "file": "phase-dwelling-guard.sh",
      "event": "PostToolUse",
      "matcher": "Skill",
      "purpose": "Scan responses for phase-advancement language",
      "required": false,
      "guardian_only": true
    },
    {
      "file": "auto-reindex.sh",
      "event": "PostToolUse",
      "matcher": "Bash",
      "purpose": "Trigger RAG reindex when indexed corpus files change",
      "required": false,
      "guardian_only": false,
      "condition": "mcp-local-rag installed"
    }
    // ... all hooks
  ]
}
```

### Step 2: Validation function in session-preflight.sh

Add at the end of `session-preflight.sh` (which runs on every SessionStart):

```bash
# Validate required hooks
MANIFEST="$(dirname "$0")/hooks-manifest.json"
if [ -f "$MANIFEST" ]; then
  python3 - "$MANIFEST" "$(dirname "$0")" "$PLUGIN_ROOT/hooks.json" <<'PYEOF'
import json, sys, os

manifest_path, hooks_dir, hooks_json_path = sys.argv[1], sys.argv[2], sys.argv[3]
manifest = json.load(open(manifest_path))
try:
    registered = json.load(open(hooks_json_path))
except:
    registered = {}

warnings = []
for hook in manifest['hooks']:
    if not hook.get('required') or hook.get('guardian_only'):
        continue
    hook_file = os.path.join(hooks_dir, hook['file'])
    if not os.path.exists(hook_file):
        warnings.append(f"MISSING FILE: {hook['file']} ({hook['purpose']})")
    # Check registration by scanning hooks.json commands
    hook_registered = False
    for event, entries in registered.get('hooks', {}).items():
        for entry in entries:
            for h in entry.get('hooks', []):
                if hook['file'] in h.get('command', ''):
                    hook_registered = True
    if not hook_registered:
        warnings.append(f"NOT REGISTERED: {hook['file']} ({hook['purpose']})")

if warnings:
    print("⚠ SweetClaude hooks warning:")
    for w in warnings:
        print(f"  {w}")
    print("  Run /sweetclaude:fix-sweetclaude to repair.")
PYEOF
fi
```

### Step 3: fix-sweetclaude skill update

Add a "hooks" section to the fix-sweetclaude skill that:
- Runs the same manifest validation
- Offers to re-register any missing hooks in hooks.json
- Offers to re-download missing hook files from the repo

### Step 4: Investigate git-checkpoint.sh

Read the file, determine its intended trigger event, decide: register it or document why it's intentionally unregistered. Update the manifest accordingly.

---

## Files Changed

- `hooks/hooks-manifest.json` (new)
- `hooks/session-preflight.sh` (add validation block)
- `skills/fix-sweetclaude/SKILL.md` (add hooks section)

## Sequencing

1. Write `hooks-manifest.json` with all current hooks
2. Investigate `git-checkpoint.sh`
3. Update `session-preflight.sh`
4. Update `fix-sweetclaude`
5. Test: temporarily remove a hook from hooks.json, verify warning fires at session start
6. Commit
