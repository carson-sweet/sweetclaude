---
id: DEBT-006
type: debt
title: "Replace Python spawn for version extraction"
status: new
priority: someday
effort: s
epic: EP-010
tags: [self-hosting, sync, performance]
origin: STORY-300 code-review
created: 2026-05-18
updated: 2026-05-18
---

# Replace Python spawn for version extraction

`sync-to-installed.sh` spawns `python3` just to read the `version` field from `package.json`. A `grep`/`sed` one-liner would avoid the Python startup cost.

## Origin

STORY-300 code review nit N-4.
