---
id: SPEC-306
story: STORY-306
epic: EP-010
version: 1.0
date: 2026-05-18
status: draft
---

# Specification: STORY-306 Fixture-based hook development workflow documentation

## User story

As a SweetClaude developer working on hooks, I want a documented workflow for developing and testing hooks without syncing to the installed path so that I can iterate safely during implementation.

## Deliverables

1. New file: `docs/user-guide/hook-development.md`

## Technical design

### Document structure

Follows existing user guide conventions: Version/Date header, relative cross-reference links, no ANSI codes.

```markdown
# Hook Development

**Version:** 1.0
**Date:** 2026-05-18

## Overview
## Logic Testing
## Regression Testing
## Sync Timing
## Recovery
## What to Read Next
```

### Section: Overview

Brief explanation of the two-copy architecture and why hook development uses a fixture-based workflow rather than live testing against the installed path. Key point: the installed copy fires on every tool call, so a broken installed hook blocks the session.

### Section: Logic Testing

How to test a hook's logic without installing it. The hook scripts read from environment variables and files, both of which can be set in a fixture.

```bash
# Test test-guardian.sh directly
CLAUDE_FILE_PATH=tests/foo.test.js \
CLAUDE_TOOL_NAME=Write \
bash hooks/test-guardian.sh
```

Cover:
- `CLAUDE_FILE_PATH` — the file being written/edited
- `CLAUDE_TOOL_NAME` — the tool being invoked (Write, Edit, Bash, Skill)
- How to set up a fixture `phase.yaml` for phase-dependent hooks
- How to read the JSON output (`{"ok": true}` or `{"ok": false, "reason": "..."}`)

### Section: Regression Testing

How to run the full test suite:

```bash
bash tests/test-hooks.sh
```

Cover:
- What the test suite covers (which hooks, which code paths)
- How to add new tests (follow the fixture pattern)
- The isolated fixture approach: fake git repo, controlled HOME, temp directories
- How to run a single test (not currently supported — all tests run together)

### Section: Sync Timing

When and how to sync repo hooks to the installed path:

- Sync happens during the SHIP phase only, after all tests pass
- The canonical command: `bash scripts/sync-to-installed.sh`
- The phase gate blocks sync during IMPLEMENT
- The test gate blocks sync if any tests fail
- `--force` overrides the phase gate but not the test gate
- `--dry-run` checks without syncing

### Section: Recovery

Cross-reference to the recovery procedure (content added by STORY-304):

- What happens when an installed hook is broken
- Why Bash works when Write/Edit is blocked
- How to restore from `hooks.bak/`
- The `sweetclaude:hook-repair` skill

### Section: What to Read Next

- [TDD Levels](tdd.md) — how hook enforcement works from the user's perspective
- [How It Works](how-it-works.md) — architectural reasoning behind hook-based enforcement
- [Phases and Workflows](phases-and-workflows.md) — phase gates and sync timing context

## Constraints

- User guide files use Version/Date headers (observed in `tdd.md`, `phases-and-workflows.md`).
- Cross-references use relative markdown links: `[text](filename.md)`.
- The file must be git-tracked (criterion 306-1).
- References `scripts/sync-to-installed.sh` (STORY-300), `hooks.bak/` (STORY-301), test suite (STORY-303), recovery (STORY-304). The doc is most complete when written after those stories, but can be drafted with placeholders.

## Success criteria

| # | Criterion | Verification |
|---|---|---|
| 306-1 | `docs/user-guide/hook-development.md` exists and is tracked by git | `git ls-files docs/user-guide/hook-development.md` returns the path |
| 306-2 | Covers logic testing with `CLAUDE_FILE_PATH` / `CLAUDE_TOOL_NAME` env vars | `grep "CLAUDE_FILE_PATH" docs/user-guide/hook-development.md` |
| 306-3 | Covers regression testing via `tests/test-hooks.sh` | `grep "test-hooks.sh" docs/user-guide/hook-development.md` |
| 306-4 | Covers sync timing (SHIP phase only) | `grep -i "ship" docs/user-guide/hook-development.md` |
| 306-5 | Cross-references recovery procedure from STORY-304 | `grep -i "recovery\|hook-repair" docs/user-guide/hook-development.md` |

## Dependencies

- STORY-300 (sync script — referenced in Sync Timing section)
- STORY-301 (backup — referenced in Recovery section)
- STORY-304 (recovery procedure — referenced in Recovery section)

The doc can be written before these dependencies ship by describing the intended behavior. The descriptions must be updated if the implementations diverge from the specs.

## Known gaps

None. This is a documentation story with well-defined content sections.
