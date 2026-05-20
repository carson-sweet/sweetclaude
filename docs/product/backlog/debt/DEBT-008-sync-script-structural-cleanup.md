---
id: DEBT-008
type: debt
title: "Sync script structural cleanup"
status: new
priority: later
effort: s
epic: EP-010
tags: [self-hosting, sync, code-quality]
origin: STORY-300 code-review
created: 2026-05-18
updated: 2026-05-18
---

# Sync script structural cleanup

`PROJECT_DIR` is declared at line 6 (before arg parsing) instead of after. Also, `_resolve_install_path` and `_read_phase` are inlined functions that are duplicated in `experimental-feature-setup`. Consider extracting to a shared library once the sync script stabilizes after STORY-301/302/305.

## Origin

STORY-300 code review nits N-6 and N-7.
