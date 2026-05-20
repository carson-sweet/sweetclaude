---
id: SPEC-301
story: STORY-301
epic: EP-010
version: 1.0
date: 2026-05-18
status: done
---

# Specification: STORY-301 Backup-on-sync with rollback support

## User story

As a SweetClaude developer syncing changes to the installed path, I want the sync script to automatically back up the current installed hooks before overwriting so that I can roll back to the last known-good state if the new hooks are broken.

## Deliverables

1. Backup step added to `scripts/sync-to-installed.sh` (created by STORY-300)

## Technical design

### Backup location

```
~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks.bak/
```

Sibling to the `hooks/` directory at the installed path. Single generation — each sync overwrites the previous backup.

### Backup procedure

Runs after the test gate passes, before any hook file is modified.

```bash
HOOKS_DIR="$INSTALL_PATH/hooks"
BACKUP_DIR="$INSTALL_PATH/hooks.bak"
BACKUP_TMP="$INSTALL_PATH/hooks.bak.tmp"

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
```

### Failure behavior

Uses atomic copy-to-temp + rename: copies to `hooks.bak.tmp`, validates, then replaces old `hooks.bak/` via `mv`. If `cp -R` fails, the temp is cleaned up and the old backup survives. If `rm -rf` of the old backup fails, the temp is cleaned up and sync aborts with exit code 3. No hook files are modified until the backup is confirmed complete.

### Interaction with --dry-run

In dry-run mode, the script exits before reaching the backup code. The dry-run message ("Would sync to $INSTALL_PATH") is emitted at the dry-run exit point; no backup-specific message is printed.

## Constraints

- Backup must complete before ANY hook file in `hooks/` is modified. The sync step (rsync) comes strictly after the backup step.
- Single generation only. No timestamped backups, no rotation. One `hooks.bak/` directory that reflects the state immediately before the last sync.
- `hooks.bak/` must contain all `.sh` files. Non-shell files (e.g., `hooks.json`, `hooks-manifest.json`) should also be backed up since they're part of the hook system.

## Success criteria

| # | Criterion | Verification |
|---|---|---|
| 301-1 | `hooks.bak/` created at installed plugin path after sync | `test -d <installed>/hooks.bak/` |
| 301-2 | `hooks.bak/` contains all `.sh` files from pre-sync hooks | File count matches pre-sync count |
| 301-3 | Backup happens before any hook file is modified | Canary file in hooks/ appears in hooks.bak/ but not in post-sync hooks/ |
| 301-4 | Previous backup is overwritten (single generation) | Run sync twice → hooks.bak/ has second-to-last state |
| 301-5 | Backup failure aborts sync with exit code 3 | Read-only parent → exit code 3, hooks unchanged |
| 301-6 | Exit code 3 is specific to backup failure | Distinguish from exit 1 (phase), 2 (tests), 4 (sync), 5 (path) |

## Dependencies

- STORY-300 (sync script exists)

## Known gaps

None.
