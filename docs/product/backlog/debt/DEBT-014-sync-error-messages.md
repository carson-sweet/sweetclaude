---
id: DEBT-014
type: debt
title: "Sync script error messages not actionable"
status: new
priority: later
effort: xs
epic: EP-010
source: STORY-301 adversarial caucus (user judge)
tags: [sync, ux, error-messages]
created: 2026-05-18
updated: 2026-05-18
---

# Sync script error messages not actionable

Current error messages like "Backup failed (cp). Sync aborted." don't include the path that failed, the reason for failure, or what the user should do next. A developer encountering this on a fresh machine wouldn't know whether to check permissions, disk space, or something else.

Fix: include `$INSTALL_PATH` in error messages and add a one-line suggestion (e.g., "Check permissions on $INSTALL_PATH" or "Run with --dry-run to diagnose").
