---
id: DESIGN-301
story: STORY-301
spec: SPEC-301
epic: EP-010
version: 1.0
date: 2026-05-18
status: done
---

# Design: STORY-301 Backup-on-sync

## Overview

Add a backup step to `scripts/sync-to-installed.sh` that copies the current installed hooks to `hooks.bak/` before any hook is overwritten.

## File: scripts/sync-to-installed.sh

### Change

Replace the `# ── Backup (STORY-301 adds implementation here)` placeholder with:

```bash
# ── Backup installed hooks ───────────────────────────────────────────────────

HOOKS_DIR="$INSTALL_PATH/hooks"
BACKUP_DIR="$INSTALL_PATH/hooks.bak"
BACKUP_TMP="$INSTALL_PATH/hooks.bak.tmp"

echo "Backing up installed hooks to hooks.bak/..."

rm -rf "$BACKUP_TMP"
if ! cp -R "$HOOKS_DIR" "$BACKUP_TMP"; then
  echo "ERROR: Backup failed (cp). Sync aborted." >&2
  rm -rf "$BACKUP_TMP"
  exit 3
fi

BACKUP_COUNT=$(find "$BACKUP_TMP" -name "*.sh" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -eq 0 ]; then
  echo "ERROR: Backup is empty (no .sh files). Sync aborted." >&2
  rm -rf "$BACKUP_TMP"
  exit 3
fi

if ! rm -rf "$BACKUP_DIR"; then
  echo "ERROR: Cannot remove old backup. Sync aborted." >&2
  rm -rf "$BACKUP_TMP"
  exit 3
fi
mv "$BACKUP_TMP" "$BACKUP_DIR"

echo "Backed up $BACKUP_COUNT hook scripts."
```

### Design notes

1. **Copy-to-temp + rename (atomic swap).** The backup copies to `hooks.bak.tmp` first, validates it, then atomically replaces the old `hooks.bak/` via `mv`. If `cp` fails mid-flight, the old backup survives. The previous design (rm-then-cp) risked losing both old and new backup on a partial copy failure.

2. **Validation after copy.** The script counts `.sh` files in the backup. If zero, something went wrong (empty hooks dir, copy failure, permissions). The backup is removed and sync is aborted.

3. **Non-shell files included.** `cp -R` copies everything in `hooks/` — including `hooks.json`, `hooks-manifest.json`, and any other non-shell files. This is intentional: the emergency restore script (STORY-304) needs these files to fully restore the hook system.

4. **Dry-run behavior.** The backup step is after the dry-run exit (see shared-conventions.md pipeline sequence, step 6). In dry-run mode, the script exits before reaching this code. The dry-run output in STORY-300 prints "Would sync to $INSTALL_PATH" — the backup step is implicit in that message.

5. **`--delete` flag on rsync.** The hook sync uses `rsync -a --delete` to ensure installed hooks exactly mirror the repo. Without `--delete`, stale files accumulate at the installed path across syncs. The backup (created before rsync runs) provides the safety net for any files removed by `--delete`. Required by success criterion 301-3: post-sync hooks/ must not contain files absent from the repo.

6. **Rollback on sync failure.** If rsync fails (exit 4), the script attempts to restore hooks from the backup. The failed hooks/ directory is moved aside via `mv` before restoring, so if the restore also fails, the failed state is preserved rather than lost. This ensures hooks/ is never left empty due to a failed restore attempt.

### Position in pipeline

```
Phase check → Test gate → [dry-run exit] → **Backup** → Sync hooks → Post-sync → Sync non-hooks
```

The backup runs after all checks pass and after the dry-run exit. This means a dry run does NOT create a backup (correct behavior — dry run should have zero side effects).

## Testing strategy

Test cases added to `tests/test-sync.sh`:

| Test | Setup | Action | Expected |
|---|---|---|---|
| Backup created after sync | Fixture installed hooks | Run sync | `hooks.bak/` exists at installed path |
| Backup contains all .sh files | 5 .sh files in installed hooks | Run sync | 5 .sh files in `hooks.bak/` |
| Backup includes non-shell files | `hooks.json` in installed hooks | Run sync | `hooks.json` exists in `hooks.bak/` |
| Canary file preserved in backup | Add `canary.txt` to installed hooks, not in repo | Run sync | `canary.txt` in `hooks.bak/` but not in `hooks/` |
| Previous backup overwritten | Run sync twice with different canary | Check `hooks.bak/` | Contains second canary, not first |
| Backup failure aborts sync | Make installed path read-only | Run sync | Exit 3, installed hooks unchanged |
