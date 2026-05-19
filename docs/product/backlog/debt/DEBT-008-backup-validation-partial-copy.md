---
id: DEBT-008
type: debt
title: "Backup validation should compare source and destination file counts"
status: new
priority: later
effort: xs
epic: EP-010
source: STORY-301 code review
tags: [sync, backup, validation]
created: 2026-05-18
updated: 2026-05-18
---

# Backup validation should compare source and destination file counts

The backup step in `scripts/sync-to-installed.sh` validates by counting `.sh` files in the copy (`hooks.bak.tmp`). If the count is > 0, validation passes. A partial copy (e.g., disk full mid-copy where `cp -R` still returns 0) could leave fewer files in the backup than the source without being detected.

Fix: count files in source (`$HOOKS_DIR`) before copy, compare against destination count after copy. Also consider counting total files (not just `.sh`) to catch partial copies of non-shell files like `hooks.json`.
