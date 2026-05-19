---
id: DEBT-009
type: debt
title: "Version-dir hooks sync bypasses backup and rollback"
status: new
priority: later
effort: s
epic: EP-010
source: STORY-301 code review + adversarial caucus
tags: [sync, backup, version-dir]
created: 2026-05-18
updated: 2026-05-18
---

# Version-dir hooks sync bypasses backup and rollback

`scripts/sync-to-installed.sh` syncs hooks to both `$INSTALL_PATH/hooks/` and `$VERSION_DIR/hooks/`. The backup and rollback mechanisms only protect the primary install path. The version-dir sync (lines ~208-209) has no backup, no rollback, and no `--delete` flag.

The version-dir is a secondary target for version-pinned caching, so the risk is lower. But if the version-dir hooks diverge from the primary install, it creates a confusing state.
