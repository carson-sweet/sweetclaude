---
id: DESIGN-306
story: STORY-306
spec: SPEC-306
epic: EP-010
version: 1.0
date: 2026-05-18
status: draft
---

# Design: STORY-306 Hook development workflow documentation

## Overview

Create `docs/user-guide/hook-development.md` — the complete guide to developing and testing SweetClaude hooks safely during self-hosting.

## File: docs/user-guide/hook-development.md

### Full document structure

```markdown
# Hook Development

**Version:** 1.0
**Date:** 2026-05-18

How to develop and test SweetClaude hooks without risking your running session.

---

## The Two-Copy Architecture

SweetClaude hooks exist in two places:

- **Repo copy** (`hooks/` in the SweetClaude repo) — your development copy.
  Editable. Testable. Not live.
- **Installed copy** (`~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/`)
  — the live copy. Fires on every tool call. Changes here affect your session
  immediately.

The installed copy is your safety net. During implementation, you edit the repo
copy and test it there. The installed copy keeps running the last-known-good
version. You sync to installed only after all tests pass, during the SHIP phase.

If you overwrite the installed copy with a broken hook, Write and Edit operations
are blocked and you cannot fix the broken hook using those tools. This is the
deadlock that the entire development workflow is designed to prevent.

---

## Logic Testing

Test a hook's logic by running it directly with the environment variables
Claude Code would set:

    CLAUDE_FILE_PATH=tests/foo.test.js \
    CLAUDE_TOOL_NAME=Write \
    bash hooks/test-guardian.sh

The hook reads these environment variables:

| Variable | Description | Example |
|---|---|---|
| `CLAUDE_FILE_PATH` | Absolute path to the file being written/edited | `/Users/you/project/tests/foo.test.js` |
| `CLAUDE_TOOL_NAME` | The tool being invoked | `Write`, `Edit`, `Bash`, `Skill` |

For phase-dependent hooks (`test-guardian.sh`, `auto-test-runner.sh`), create a
fixture `phase.yaml`:

    mkdir -p /tmp/test-project/.sweetclaude/state
    printf 'phase: implement\ntdd_phase: implementing\n' > \
      /tmp/test-project/.sweetclaude/state/phase.yaml

    cd /tmp/test-project && git init
    CLAUDE_FILE_PATH=/tmp/test-project/tests/foo.test.js \
    CLAUDE_TOOL_NAME=Write \
    bash /path/to/sweetclaude/hooks/test-guardian.sh

The output is JSON:

    {"ok": true}                              # allowed
    {"ok": false, "reason": "..."}            # blocked

---

## Regression Testing

Run the full hook test suite:

    bash tests/test-hooks.sh

The suite tests hook behavior using isolated fixture environments — fake git
repos, controlled HOME directories, temp directories that are cleaned up
automatically. It never touches your real environment.

**What's covered:** session-preflight, drift-gate, master-preflight,
test-guardian, auto-test-runner, and syntax validation.

**How to add tests:** follow the existing pattern in `tests/test-hooks.sh`.
Each test creates its own fixture directory under `$TMPROOT`, sets up the
minimum state the hook needs, runs the hook, and checks the output with
`pass()` / `fail()`.

---

## Sync Timing

Sync repo hooks to the installed path using:

    bash scripts/sync-to-installed.sh

The sync script enforces three safety gates:

1. **Phase gate** — blocks sync when the active phase is IMPLEMENT.
   Override with `--force` (logs to decision-log.md).
2. **Test gate** — blocks sync if `tests/test-hooks.sh` fails.
   Cannot be overridden.
3. **Backup** — copies the current installed hooks to `hooks.bak/` before
   overwriting.

The intended workflow:

    IMPLEMENT phase     → edit repo hooks, run tests, iterate
    VERIFY phase        → code review, final test pass
    SHIP phase          → bash scripts/sync-to-installed.sh

To preview what would happen without syncing:

    bash scripts/sync-to-installed.sh --dry-run

---

## Recovery

[Content added by STORY-304 — see design-304.md for the exact sections]

---

## Emergency Recovery (Break Glass)

[Content added by STORY-304 — see design-304.md for the exact sections]

---

## What to Read Next

- [TDD Levels](tdd.md) — how hook enforcement works from the user's perspective
- [How It Works](how-it-works.md) — architectural reasoning behind hook-based enforcement
- [Phases and Workflows](phases-and-workflows.md) — phase gates and sync timing context
```

### Design notes

1. **Placeholder sections for STORY-304.** The Recovery and Emergency Recovery sections are marked as added by STORY-304. STORY-306 creates the file structure; STORY-304 fills in those sections. Implementation order: 306 first, 304 second.

2. **Concrete examples.** Every section includes an exact command the developer can run. No abstract descriptions without a concrete follow-up.

3. **Version/Date header.** Matches existing user guide convention (from `tdd.md`, `phases-and-workflows.md`).

4. **Cross-references.** Relative markdown links at the bottom, matching the pattern in `tdd.md` lines 172-174.

### Adjacent updates

| File | Change |
|---|---|
| `docs/user-guide/index.md` | Add entry: `- [Hook Development](hook-development.md) — developing and testing hooks safely during self-hosting` |
| `docs/user-guide/tdd.md` | Add to "What to Read Next": `- How to develop and test hooks → [Hook Development](hook-development.md)` |

## Testing strategy

No automated tests (documentation story). Verification is criterion-based:

| Criterion | Verification command |
|---|---|
| 306-1 | `git ls-files docs/user-guide/hook-development.md` |
| 306-2 | `grep "CLAUDE_FILE_PATH" docs/user-guide/hook-development.md` |
| 306-3 | `grep "test-hooks.sh" docs/user-guide/hook-development.md` |
| 306-4 | `grep -i "ship" docs/user-guide/hook-development.md` |
| 306-5 | `grep -i "recovery\|hook-repair" docs/user-guide/hook-development.md` |
