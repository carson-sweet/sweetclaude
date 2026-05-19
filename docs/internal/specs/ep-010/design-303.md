---
id: DESIGN-303
story: STORY-303
spec: SPEC-303
epic: EP-010
version: 1.0
date: 2026-05-18
status: draft
---

# Design: STORY-303 Extend test-hooks.sh coverage

## Overview

Add 11 new test cases to `tests/test-hooks.sh` covering `test-guardian.sh` and `auto-test-runner.sh`, plus a syntax validation test. Tests follow the existing fixture pattern exactly.

## File: tests/test-hooks.sh

### Insertion point

New tests are appended after the existing Test 10 block and before the final summary block. The summary block (`echo; if [ "$FAILED" -eq 0 ]; then ...`) remains at the end, unchanged.

**HOME isolation required for all tests.** Every test invocation must use `HOME="$TMPROOT/homeN"` (where N is the test number) to prevent hooks from writing to the developer's real `~/.claude/` directory. Test 11 demonstrates the pattern. Tests 12-21 must follow the same convention — the implementer must add `FX{N}_HOME="$TMPROOT/home{N}"` and pass `HOME="$FX{N}_HOME"` in each `env` invocation.

### Test 11: test-guardian — phase inactive → ok

```bash
echo "[11] test-guardian.sh: allows test file edit when phase is not implement"

FX11_HOME="$TMPROOT/home11"
FX11_PROJ="$TMPROOT/proj11"
mkdir -p "$FX11_HOME/.claude"
_make_git_repo "$FX11_PROJ"
mkdir -p "$FX11_PROJ/.sweetclaude/state"
printf 'phase: discover\ntdd_phase: writing_tests\n' > "$FX11_PROJ/.sweetclaude/state/phase.yaml"

RESULT11=$(cd "$FX11_PROJ" && \
  env HOME="$FX11_HOME" CLAUDE_FILE_PATH="$FX11_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT11" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
  pass "phase inactive → ok for test file edit"
else
  fail "should allow test file edit when phase is not implement (got: $RESULT11)"
fi
```

### Test 12: test-guardian — phase active + implementing + test file → blocked

```bash
echo "[12] test-guardian.sh: blocks test file edit during implement/implementing"

FX12_HOME="$TMPROOT/home12"
FX12_PROJ="$TMPROOT/proj12"
mkdir -p "$FX12_HOME/.claude"
_make_git_repo "$FX12_PROJ"
mkdir -p "$FX12_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX12_PROJ/.sweetclaude/state/phase.yaml"

RESULT12=$(cd "$FX12_PROJ" && \
  env HOME="$FX12_HOME" CLAUDE_FILE_PATH="$FX12_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Edit \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT12" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == False else 1)
" 2>/dev/null; then
  pass "blocks test file edit during implement/implementing"
else
  fail "should block test file edit (got: $RESULT12)"
fi
```

### Test 13: test-guardian — phase active + implementing + non-test file → ok

```bash
echo "[13] test-guardian.sh: allows non-test file edit during implement/implementing"

FX13_HOME="$TMPROOT/home13"
FX13_PROJ="$TMPROOT/proj13"
mkdir -p "$FX13_HOME/.claude"
_make_git_repo "$FX13_PROJ"
mkdir -p "$FX13_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX13_PROJ/.sweetclaude/state/phase.yaml"

RESULT13=$(cd "$FX13_PROJ" && \
  env HOME="$FX13_HOME" CLAUDE_FILE_PATH="$FX13_PROJ/src/main.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT13" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
  pass "allows non-test file during implement/implementing"
else
  fail "should allow non-test file (got: $RESULT13)"
fi
```

### Test 14: test-guardian — phase active + non-implementing tdd_phase → ok

```bash
echo "[14] test-guardian.sh: allows test file edit when tdd_phase is not implementing"

FX14_HOME="$TMPROOT/home14"
FX14_PROJ="$TMPROOT/proj14"
mkdir -p "$FX14_HOME/.claude"
_make_git_repo "$FX14_PROJ"
mkdir -p "$FX14_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: writing_tests\n' > "$FX14_PROJ/.sweetclaude/state/phase.yaml"

RESULT14=$(cd "$FX14_PROJ" && \
  env HOME="$FX14_HOME" CLAUDE_FILE_PATH="$FX14_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT14" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
  pass "allows test file when tdd_phase is writing_tests"
else
  fail "should allow test file when tdd_phase is not implementing (got: $RESULT14)"
fi
```

### Test 15: test-guardian — non-Write/Edit tool → ok

```bash
echo "[15] test-guardian.sh: passes through non-Write/Edit tools"

FX15_HOME="$TMPROOT/home15"
FX15_PROJ="$TMPROOT/proj15"
mkdir -p "$FX15_HOME/.claude"
_make_git_repo "$FX15_PROJ"
mkdir -p "$FX15_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX15_PROJ/.sweetclaude/state/phase.yaml"

RESULT15=$(cd "$FX15_PROJ" && \
  env HOME="$FX15_HOME" CLAUDE_FILE_PATH="$FX15_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Bash \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT15" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == True else 1)
" 2>/dev/null; then
  pass "non-Write/Edit tool passes through"
else
  fail "Bash tool should pass through even during implement (got: $RESULT15)"
fi
```

### Test 16: test-guardian — IMPLEMENT uppercase → blocked

```bash
echo "[16] test-guardian.sh: blocks on uppercase IMPLEMENT"

FX16_HOME="$TMPROOT/home16"
FX16_PROJ="$TMPROOT/proj16"
mkdir -p "$FX16_HOME/.claude"
_make_git_repo "$FX16_PROJ"
mkdir -p "$FX16_PROJ/.sweetclaude/state"
printf 'phase: IMPLEMENT\ntdd_phase: implementing\n' > "$FX16_PROJ/.sweetclaude/state/phase.yaml"

RESULT16=$(cd "$FX16_PROJ" && \
  env HOME="$FX16_HOME" CLAUDE_FILE_PATH="$FX16_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/test-guardian.sh" 2>/dev/null) || true

if printf '%s' "$RESULT16" | python3 -c "
import sys, json; d = json.loads(sys.stdin.read()); sys.exit(0 if d.get('ok') == False else 1)
" 2>/dev/null; then
  pass "blocks on uppercase IMPLEMENT"
else
  fail "should block on uppercase IMPLEMENT (got: $RESULT16)"
fi
```

### Test 17: auto-test-runner — phase inactive → no execution

```bash
echo "[17] auto-test-runner.sh: no test execution when phase is not implement"

FX17_HOME="$TMPROOT/home17"
FX17_PROJ="$TMPROOT/proj17"
FX17_MARKER="$TMPROOT/marker17"
mkdir -p "$FX17_HOME/.claude"
_make_git_repo "$FX17_PROJ"
mkdir -p "$FX17_PROJ/.sweetclaude/state"
printf 'phase: discover\ntdd_phase: writing_tests\n' > "$FX17_PROJ/.sweetclaude/state/phase.yaml"
printf 'test:\n  test_command: touch %s\n' "$FX17_MARKER" > "$FX17_PROJ/.sweetclaude/state/project.yaml"

(cd "$FX17_PROJ" && \
  env HOME="$FX17_HOME" CLAUDE_FILE_PATH="$FX17_PROJ/src/main.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/auto-test-runner.sh" 2>/dev/null) || true

sleep 0.5
if [ ! -f "$FX17_MARKER" ]; then
  pass "no test execution when phase inactive"
else
  fail "test command should not run when phase is not implement"
fi
```

### Test 18: auto-test-runner — phase active + source file → runs test command

```bash
echo "[18] auto-test-runner.sh: runs test command for source file edit during implement"

FX18_HOME="$TMPROOT/home18"
FX18_PROJ="$TMPROOT/proj18"
FX18_MARKER="$TMPROOT/marker18"
mkdir -p "$FX18_HOME/.claude"
_make_git_repo "$FX18_PROJ"
mkdir -p "$FX18_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX18_PROJ/.sweetclaude/state/phase.yaml"
printf 'test:\n  test_command: touch %s\n' "$FX18_MARKER" > "$FX18_PROJ/.sweetclaude/state/project.yaml"

(cd "$FX18_PROJ" && \
  env HOME="$FX18_HOME" CLAUDE_FILE_PATH="$FX18_PROJ/src/main.js" CLAUDE_TOOL_NAME=Write \
  bash "$REPO_ROOT/hooks/auto-test-runner.sh" 2>/dev/null) || true

# Retry loop for background process
for _i in 1 2 3 4 5; do
  [ -f "$FX18_MARKER" ] && break
  sleep 0.2
done

if [ -f "$FX18_MARKER" ]; then
  pass "runs test command for source file during implement"
else
  fail "test command should run for source file edit during implement/implementing"
fi
```

### Test 19: auto-test-runner — test file → no execution

```bash
echo "[19] auto-test-runner.sh: no test execution for test file edit"

FX19_HOME="$TMPROOT/home19"
FX19_PROJ="$TMPROOT/proj19"
FX19_MARKER="$TMPROOT/marker19"
mkdir -p "$FX19_HOME/.claude"
_make_git_repo "$FX19_PROJ"
mkdir -p "$FX19_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX19_PROJ/.sweetclaude/state/phase.yaml"
printf 'test:\n  test_command: touch %s\n' "$FX19_MARKER" > "$FX19_PROJ/.sweetclaude/state/project.yaml"

(cd "$FX19_PROJ" && \
  env HOME="$FX19_HOME" CLAUDE_FILE_PATH="$FX19_PROJ/tests/foo.test.js" CLAUDE_TOOL_NAME=Edit \
  bash "$REPO_ROOT/hooks/auto-test-runner.sh" 2>/dev/null) || true

sleep 0.5
if [ ! -f "$FX19_MARKER" ]; then
  pass "no test execution for test file edit"
else
  fail "test command should not run for test file edits"
fi
```

### Test 20: auto-test-runner — non-Write/Edit tool → no execution

```bash
echo "[20] auto-test-runner.sh: no test execution for non-Write/Edit tools"

FX20_HOME="$TMPROOT/home20"
FX20_PROJ="$TMPROOT/proj20"
FX20_MARKER="$TMPROOT/marker20"
mkdir -p "$FX20_HOME/.claude"
_make_git_repo "$FX20_PROJ"
mkdir -p "$FX20_PROJ/.sweetclaude/state"
printf 'phase: implement\ntdd_phase: implementing\n' > "$FX20_PROJ/.sweetclaude/state/phase.yaml"
printf 'test:\n  test_command: touch %s\n' "$FX20_MARKER" > "$FX20_PROJ/.sweetclaude/state/project.yaml"

(cd "$FX20_PROJ" && \
  env HOME="$FX20_HOME" CLAUDE_FILE_PATH="$FX20_PROJ/src/main.js" CLAUDE_TOOL_NAME=Bash \
  bash "$REPO_ROOT/hooks/auto-test-runner.sh" 2>/dev/null) || true

sleep 0.5
if [ ! -f "$FX20_MARKER" ]; then
  pass "no test execution for Bash tool"
else
  fail "test command should not run for non-Write/Edit tools"
fi
```

### Test 21: syntax validation — broken hook exits non-zero

```bash
echo "[21] syntax validation: hook with syntax error fails bash -n"

BROKEN_HOOK="$TMPROOT/broken-hook.sh"
cp "$REPO_ROOT/hooks/test-guardian.sh" "$BROKEN_HOOK"
printf '\nif [[ ; then\n' >> "$BROKEN_HOOK"

if bash -n "$BROKEN_HOOK" 2>/dev/null; then
  fail "broken hook should fail bash -n syntax check"
else
  pass "broken hook fails bash -n (fail-closed)"
fi
```

## Design notes

1. **project.yaml indentation.** `auto-test-runner.sh` line 63 greps for `"^  test_command:"` (two leading spaces). The fixture writes `test:\n  test_command: ...` to match this indentation. If the hook's grep pattern changes, these tests will correctly fail and signal the regression.

2. **John Wick avoidance.** No fixture creates `.sweetclaude/state/john-wick.yaml`. The John Wick code path in test-guardian (lines 38-70) is not triggered. This is intentional — John Wick mode is a separate feature and not in scope for EP-010.

3. **Background process timing.** Tests 17, 19, 20 use `sleep 0.5` (fixed) to wait for a background process that should NOT have spawned. This confirms absence. Test 18 uses the retry loop (5 × 0.2s = 1s max) to wait for a process that SHOULD have spawned. The asymmetry is intentional: absence is cheap to verify (one short wait), presence needs patience.

4. **HOME isolation.** test-guardian and auto-test-runner read `CLAUDE_FILE_PATH`, `CLAUDE_TOOL_NAME`, and `phase.yaml` — none of which reference HOME. However, hooks may call `record-event.sh` which writes to `~/.claude/`. For safety, all test invocations should use `HOME="$TMPROOT/homeN"` to prevent test runs from writing to the developer's real `~/.claude/` directory. All tests (11-20) now include this.

## Blast radius mitigation

- Run `bash tests/test-hooks.sh` 10× in a loop after implementation to verify no flakiness before STORY-302 makes it a gate.
- The marker-file retry loop is the only timing-sensitive assertion. If it proves flaky, increase attempts to 10 × 0.3s.
