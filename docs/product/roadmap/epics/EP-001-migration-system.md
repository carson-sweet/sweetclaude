---
id: EP-001
type: epic
title: Migration System
status: paused
release: REL-001
objective: "Migration system handles v3-to-v4 upgrades safely with atomic finalize and complete guard coverage."
completion_criteria:
  - "Finalize step is atomic (BUG-007)"
  - "All GitHub skills have v4 migration guards (BUG-008)"
completion_criteria_done: [0, 1]
epic_sequence: 1
created: 2026-05-18
updated: 2026-05-19
---

# EP-001: Migration System

State schema migration infrastructure — handlers, guards, and atomicity guarantees for upgrading `.sweetclaude/` state files between versions.
