---
id: DEBT-005
type: debt
title: "Dry-run output completeness"
status: new
priority: later
effort: s
epic: EP-010
tags: [self-hosting, sync]
origin: STORY-300 code-review
created: 2026-05-18
updated: 2026-05-18
---

# Dry-run output completeness

The `--dry-run` success message only mentions `$INSTALL_PATH`. It should list all 6 sync targets so the developer knows the full blast radius before running a real sync.

## Origin

STORY-300 code review nit N-3.
