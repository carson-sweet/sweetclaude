---
closed_date: '2026-05-15'
created: 2026-05-13
effort: s
epic: EP-009
id: CHORE-003
milestone: null
origin: manual
priority: soon
sprint: null
status: done
tags:
- preflight
- health
- hooks
- robustness
title: Fix session-preflight.sh hook-presence check to detect broken/unresolved entries
type: chore
updated: 2026-05-15
---

## Description

`hooks/session-preflight.sh` Step 9 verifies that required global hooks are registered in `~/.claude/settings.json`. It does this with a basename substring grep:

```bash
if ! echo "$_SC_GLOBAL_CMDS" | grep -qF "$_sc_file"; then
```

This false-passes any entry whose command path contains the basename, regardless of whether the path is valid. The 3.68.0/3.68.1 `${CLAUDE_PLUGIN_ROOT}` bug went undetected by SweetClaude's own health check for exactly this reason — the literal `${CLAUDE_PLUGIN_ROOT}/hooks/session-preflight.sh` contains the basename `session-preflight.sh`, so the grep matched and Step 9 reported "all required globals registered" while every skill call errored at runtime.

After 3.68.2, the three preflight hooks are `scope: plugin-native`, so Step 9's `scope == "global"` filter finds zero required globals — the check trivially passes and the false-pass mode is dormant. But the same logic will mask future registration drift: any new `scope: global` hook added in the future, or any manually-broken entry, will not be detected.

**Origin:** Identified by the Opus QA caucus during 3.68.2 review. Filed 2026-05-13 by Carson Sweet.

### Proposed fix

For each required global hook, verify all of:
1. An entry exists in `~/.claude/settings.json` matching the hook basename
2. The entry's command does NOT contain `${CLAUDE_PLUGIN_ROOT}` (which won't resolve in settings.json)
3. The resolved path is executable on disk (`-x "$path"`)

If any check fails, emit a heal message that names the specific failure (`"session-preflight.sh registered but command is unresolved"` vs `"session-preflight.sh missing entirely"`).

## Acceptance Criteria

- [ ] session-preflight.sh Step 9 detects a settings.json entry whose command contains `${CLAUDE_PLUGIN_ROOT}` and fires `emit_heal`
- [ ] session-preflight.sh Step 9 detects a settings.json entry whose command points to a file that doesn't exist on disk
- [ ] When all entries are present and valid, the check passes silently as today
- [ ] Heal message names the specific failure mode (missing / unresolved / non-executable), not just "missing required global hooks"

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
