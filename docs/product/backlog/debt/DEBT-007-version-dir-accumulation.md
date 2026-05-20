---
id: DEBT-007
type: debt
title: "Version-dir accumulation without cleanup"
status: new
priority: soon
effort: s
epic: EP-010
tags: [self-hosting, sync, disk-usage]
origin: STORY-300 code-review
created: 2026-05-18
updated: 2026-05-18
---

# Version-dir accumulation without cleanup

Each sync creates a version-named directory under the plugin cache parent. Old version dirs are never cleaned up. Over time this accumulates stale copies. Needs a retention policy or prune step (e.g., keep last 3 versions, matching `experimental-feature-setup`'s backup retention).

## Origin

STORY-300 code review nit N-5.
