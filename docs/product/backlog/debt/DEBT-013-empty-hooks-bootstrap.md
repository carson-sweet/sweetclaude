---
id: DEBT-013
type: debt
title: "First sync to fresh install fails on empty hooks/ validation"
status: new
priority: soon
effort: xs
epic: EP-010
source: STORY-301 adversarial caucus
tags: [sync, backup, bootstrap]
created: 2026-05-18
updated: 2026-05-18
---

# First sync to fresh install fails on empty hooks/ validation

The backup step validates that `hooks.bak.tmp` contains at least one `.sh` file. If the installed `hooks/` directory exists but is empty (or contains only non-shell files), the backup validation exits 3 and blocks the sync.

This means `sync-to-installed.sh` cannot be used for the initial install into an empty hooks/ directory. The path resolution already filters for directories with a `hooks/` subdirectory, so this scenario requires hooks/ to exist but be empty — which happens on a fresh plugin install before the first sync.

Fix: skip the backup step entirely when hooks/ contains no `.sh` files (there's nothing to back up). Only validate when there are files to preserve.
