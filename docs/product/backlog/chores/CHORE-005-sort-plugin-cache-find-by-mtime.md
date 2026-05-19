---
id: CHORE-005
type: chore
title: Sort plugin-cache find results by mtime in fix-sweetclaude Step 7a
status: new
priority: later
effort: s
epic: null
milestone: null
sprint: null
tags: [fix-sweetclaude, hooks, defensive]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
---

## Description

`skills/fix-sweetclaude/SKILL.md` Step 7a falls back to searching the plugin cache when the versionless script path is missing:

```bash
SCRIPT=$(find ~/.claude/plugins/cache/sweetclaude -type f -name 'ensure-global-hooks.py' 2>/dev/null | head -1)
```

`find` traverses in directory-entry order (filesystem-dependent, not guaranteed alphabetical or chronological). If a user has multiple cached plugin versions (e.g., `3.67.0/` and `3.68.2/`), `head -1` could pick either. If it picks an older version, the cleanup runs older buggy logic.

**Origin:** Identified by the Opus QA caucus during 3.68.2 review. Filed 2026-05-13 by Carson Sweet.

**Severity:** edge case. Plugin caches are typically pruned to one version after update. The bad-pick only matters during a window where multiple versions coexist.

### Proposed fix

Sort by modification time, newest first:

```bash
SCRIPT=$(find ~/.claude/plugins/cache/sweetclaude -type f -name 'ensure-global-hooks.py' -print0 2>/dev/null | xargs -0 ls -t 2>/dev/null | head -1)
```

Or use `stat` + sort for portability.

## Acceptance Criteria

- [ ] When multiple plugin-cache versions contain `ensure-global-hooks.py`, the newest one (by mtime) is selected
- [ ] When only one version is cached, the same one is selected (no regression)
- [ ] Works on macOS BSD `ls` and Linux GNU `ls`

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
