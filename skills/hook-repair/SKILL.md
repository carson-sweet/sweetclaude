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

Run the same python3 resolver the emergency script uses to find `INSTALL_PATH`.
If unresolved, stop and direct the user to `bash scripts/emergency-hook-restore.sh`.

## Step 2: Check for backup

If `$INSTALL_PATH/hooks.bak/` is missing, report and exit with alternatives:
1. Copy from repo
2. Run emergency script
3. Re-install from marketplace

## Step 3: Diagnose broken hooks

Run `bash -n` on every `$INSTALL_PATH/hooks/*.sh` and classify as OK or BROKEN.

## Step 4: Propose restoration via AskUserQuestion

For each BROKEN hook, ask the user before copying. Use AskUserQuestion with options:
- Restore all broken hooks
- Show details first
- Cancel

## Step 5: Restore and verify

`cp` from `hooks.bak/`, `chmod +x`, then re-run `bash -n`.
If still broken, the backup itself is bad — direct to emergency script.

## Rules

- **Bash only.** Never use Write or Edit tools in this skill.
- **Propose before applying.** Use AskUserQuestion for restoration decisions.
- **Verify after restoration.** Run bash -n on restored hooks to confirm.
