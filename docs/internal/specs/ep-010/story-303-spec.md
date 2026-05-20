---
id: SPEC-303
story: STORY-303
epic: EP-010
version: 1.0
date: 2026-05-18
status: draft
---

# Specification: STORY-303 Extend test-hooks.sh coverage to TDD-sensitive hooks

## User story

As a SweetClaude developer modifying TDD enforcement hooks, I want `test-hooks.sh` to cover `test-guardian.sh` and `auto-test-runner.sh` so that the pre-sync test gate (STORY-302) can catch regressions in the hooks most likely to cause a self-hosting deadlock.

## Deliverables

1. New test cases appended to `tests/test-hooks.sh`

## Technical design

### Fixture pattern

All new tests follow the existing pattern in `test-hooks.sh`:

- Isolated temp dir via `$TMPROOT` (already set up with `mktemp -d` and `trap` cleanup)
- Per-test HOME directory (`FX<N>_HOME`) to prevent touching real config
- Per-test project directory (`FX<N>_PROJ`) with `_make_git_repo` for git init
- Fixture `phase.yaml` with controlled phase/tdd_phase values
- `pass()` / `fail()` assertion functions, `FAILED` counter
- No `john-wick.yaml` in any fixture (avoids triggering the John Wick code path in test-guardian unless explicitly testing it)

### test-guardian.sh tests

The hook reads `CLAUDE_FILE_PATH`, `CLAUDE_TOOL_NAME` from environment and `phase.yaml` from the project directory. Tests set these directly.

**Test 11: phase inactive → ok**

```
phase.yaml: phase: discover, tdd_phase: ""
CLAUDE_TOOL_NAME=Write, CLAUDE_FILE_PATH=tests/foo.test.js
Expected: {"ok": true}
```

**Test 12: phase active + implementing + test file → blocked**

```
phase.yaml: phase: implement, tdd_phase: implementing
CLAUDE_TOOL_NAME=Edit, CLAUDE_FILE_PATH=tests/foo.test.js
Expected: {"ok": false}, reason contains "immutable"
```

**Test 13: phase active + implementing + non-test file → ok**

```
phase.yaml: phase: implement, tdd_phase: implementing
CLAUDE_TOOL_NAME=Write, CLAUDE_FILE_PATH=src/main.js
Expected: {"ok": true}
```

**Test 14: phase active + non-implementing tdd_phase → ok**

```
phase.yaml: phase: implement, tdd_phase: writing_tests
CLAUDE_TOOL_NAME=Write, CLAUDE_FILE_PATH=tests/foo.test.js
Expected: {"ok": true}
```

**Test 15: non-Write/Edit tool → ok (regardless of phase)**

```
phase.yaml: phase: implement, tdd_phase: implementing
CLAUDE_TOOL_NAME=Bash, CLAUDE_FILE_PATH=tests/foo.test.js
Expected: {"ok": true}
```

**Test 16: IMPLEMENT uppercase → blocked (case sensitivity)**

```
phase.yaml: phase: IMPLEMENT, tdd_phase: implementing
CLAUDE_TOOL_NAME=Write, CLAUDE_FILE_PATH=tests/foo.test.js
Expected: {"ok": false}
```

### auto-test-runner.sh tests

The hook reads `CLAUDE_FILE_PATH`, `CLAUDE_TOOL_NAME`, `phase.yaml`, and `project.yaml` (for `test_command`). It runs the test command in background.

**Fixture requirement:** `project.yaml` must exist with a `test_command` field. For testing, use a command that writes a marker file: `touch $MARKER_PATH`.

**Test 17: phase inactive → no test execution**

```
phase.yaml: phase: discover, tdd_phase: ""
project.yaml: exists with test_command
CLAUDE_TOOL_NAME=Write, CLAUDE_FILE_PATH=src/main.js
Expected: exit 0, marker file NOT created
```

**Test 18: phase active + implementing + source file → runs test command**

```
phase.yaml: phase: implement, tdd_phase: implementing
project.yaml: "  test_command: touch $MARKER_PATH"
CLAUDE_TOOL_NAME=Write, CLAUDE_FILE_PATH=src/main.js
Expected: exit 0, marker file created (after brief wait for background process)
```

The background execution challenge: `auto-test-runner.sh` runs the test command with `&`. The test uses a retry loop to wait for the marker file:

```bash
# Wait for background process (max 1 second)
for _i in 1 2 3 4 5; do
  [ -f "$MARKER_PATH" ] && break
  sleep 0.2
done
```

This is robust for a `touch` command on a local machine. The 1-second total wait is generous. Decision: marker-file approach chosen over stderr-checking because it proves the command actually executed, not just that the hook decided to run it (decided 2026-05-18).

**Test 19: phase active + implementing + test file → no test execution**

```
phase.yaml: phase: implement, tdd_phase: implementing
project.yaml: exists with test_command
CLAUDE_TOOL_NAME=Edit, CLAUDE_FILE_PATH=tests/foo.test.js
Expected: exit 0, marker file NOT created
```

**Test 20: non-Write/Edit tool → no test execution**

```
phase.yaml: phase: implement, tdd_phase: implementing
CLAUDE_TOOL_NAME=Bash, CLAUDE_FILE_PATH=src/main.js
Expected: exit 0, marker file NOT created
```

### Syntax validation test

**Test 21: hook with syntax error exits non-zero**

Create a copy of `test-guardian.sh` with a deliberate syntax error (e.g., unclosed `if`). Run `bash -n` on it. Verify non-zero exit. This confirms hooks fail closed on syntax errors.

```bash
cp "$REPO_ROOT/hooks/test-guardian.sh" "$TMPROOT/broken-hook.sh"
echo 'if [[ ; then' >> "$TMPROOT/broken-hook.sh"
bash -n "$TMPROOT/broken-hook.sh" 2>/dev/null && fail "..." || pass "..."
```

### Test numbering

Existing tests are numbered 1-10. New tests start at 11. The FAILED counter at the end reports total failures across all tests.

## Constraints

- `auto-test-runner.sh` requires `project.yaml` to exist with `test_command` field (line 63: `grep "^  test_command:"` — note the leading spaces, matching YAML indentation under a parent key).
- `auto-test-runner.sh` runs tests in background (`eval "$TEST_CMD" ... &`). Tests must account for async execution.
- `test-guardian.sh` has a John Wick mode check (lines 38-70) that reads `john-wick.yaml`. Test fixtures must NOT create this file to avoid unexpected behavior.
- `test-guardian.sh` phase check is case-insensitive: matches both `implement` and `IMPLEMENT` (line 77).
- All test patterns for "is this a test file" are hardcoded in both hooks. Tests should exercise at least one pattern from the list (e.g., `tests/` path prefix).

## Success criteria

| # | Criterion | Verification |
|---|---|---|
| 303-1 | test-guardian: phase inactive → ok | Test exists and passes |
| 303-2 | test-guardian: phase active + implementing + test file → blocked | Test exists and passes |
| 303-3 | test-guardian: phase active + implementing + non-test file → ok | Test exists and passes |
| 303-4 | test-guardian: phase active + non-implementing tdd_phase → ok | Test exists and passes |
| 303-5 | auto-test-runner: phase inactive → no test execution | Test exists and passes |
| 303-6 | auto-test-runner: phase active + implementing + source file → runs test command | Test exists and passes |
| 303-7 | Syntax validation: hook with syntax error exits non-zero | Test exists and passes |
| 303-8 | All new tests use isolated fixtures | No reference to real HOME or project paths |
| 303-9 | `bash tests/test-hooks.sh` passes with zero failures | Exit code 0 |

## Dependencies

- None (extends existing test file)

## Known gaps

1. **project.yaml indentation sensitivity.** `auto-test-runner.sh` greps for `"^  test_command:"` with two leading spaces. The fixture must match this exact indentation. If the hook's grep pattern changes, the test breaks. This is acceptable — the test should match the hook's actual behavior.
