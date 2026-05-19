---
id: DEBT-010
type: debt
title: "hooks.failed/ artifact not cleaned on subsequent syncs"
status: new
priority: later
effort: xs
epic: EP-010
source: STORY-301 adversarial caucus
tags: [sync, rollback, cleanup]
created: 2026-05-18
updated: 2026-05-18
---

# hooks.failed/ artifact not cleaned on subsequent syncs

When rsync fails and the rollback path fires, `hooks/` is renamed to `hooks.failed/` before restoring from backup. If the restore succeeds, `hooks.failed/` is removed. If the restore fails, `hooks.failed/` is moved back.

The gap: on a subsequent successful sync, any leftover `hooks.failed/` from a prior failed run is never cleaned up. Fix: add `rm -rf "$INSTALL_PATH/hooks.failed" 2>/dev/null || true` at the start of the backup or sync section.
