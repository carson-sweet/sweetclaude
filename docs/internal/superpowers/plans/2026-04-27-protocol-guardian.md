# Protocol Guardian Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a two-layer enforcement system that prevents Claude from skipping skill invocations, artifact saves, and TDD discipline — off by default, enabled via `/sweetclaude:guardian-on`.

**Architecture:** A flag file (`.sweetclaude/state/guardian-enabled`) gates three new hooks (tdd-prewrite-guardian, artifact-guardian, skill-tracker) and two new skills (guardian-on, guardian-off). Hooks enforce mechanical violations; the guardian-on skill creates a task obligation chain for reasoning-layer enforcement. Frustration-detection triggers are added to the master skill and interaction model.

**Tech Stack:** Bash shell scripts, JSON (jq), Claude Code hooks (PreToolUse/PostToolUse), SweetClaude SKILL.md format

**Spec:** `docs/superpowers/specs/2026-04-27-protocol-guardian-design.md`

---

## File Map

**New files:**
- `skills/guardian-on/SKILL.md` — guardian-on skill (enables guardian, creates obligation chain)
- `skills/guardian-off/SKILL.md` — guardian-off skill (removes flag)
- `hooks/tdd-prewrite-guardian.sh` — PreToolUse Write|Edit: blocks source writes without test files
- `hooks/artifact-guardian.sh` — PreToolUse Bash: warns on commits with missing artifacts
- `hooks/skill-tracker.sh` — PostToolUse Skill: records skill invocations to session state
- `tests/hooks/test-tdd-prewrite-guardian.sh` — hook test script
- `tests/hooks/test-artifact-guardian.sh` — hook test script
- `tests/hooks/test-skill-tracker.sh` — hook test script

**Modified files:**
- `hooks/hooks.json` — add 3 new hook entries
- `rules/interaction-model.md` — add Protocol Guardian Offer section
- `skills/master/SKILL.md` — add frustration detection trigger

> **Note on subagent enforcement:** The spec references modifying `subagent-driven-development/implementer-prompt.md`, but that file lives in the superpowers plugin cache (not the SweetClaude repo). Subagent protocol enforcement is handled instead via the `guardian-on` skill's "For subagent dispatch" section, which instructs Claude to prepend the protocol block to implementer prompts when the guardian is active.

---

## Task 1: `sweetclaude:guardian-on` and `sweetclaude:guardian-off` skills

**Files:**
- Create: `skills/guardian-on/SKILL.md`
- Create: `skills/guardian-off/SKILL.md`

- [ ] **Step 1: Create `skills/guardian-on/SKILL.md`**

```markdown
---
name: guardian-on
description: Enable the Protocol Guardian — enforces skill invocations, TDD discipline, and artifact saves for the current session
---

# Protocol Guardian — Enable

Activates enforcement for the three most common SweetClaude protocol violations:
- **Skill skipping** (A) — obligation task chain enforces required skill invocations
- **Artifact skipping** (C) — hook warns when committing without required phase artifacts
- **TDD bypass** (D) — hook blocks source file writes until test files exist

Guardian is session-scoped. It does not persist across sessions or commits.

## Steps

**1. Create the guardian flag:**
Run:
```bash
touch .sweetclaude/state/guardian-enabled
```

**2. Prevent the flag from being committed:**
Run:
```bash
grep -qxF "state/guardian-enabled" .sweetclaude/.gitignore 2>/dev/null || echo "state/guardian-enabled" >> .sweetclaude/.gitignore
```

If `.sweetclaude/.gitignore` does not exist, create it first with that single line.

**3. Initialize session state:**
Write `.sweetclaude/state/session-guardian.json` (replace `[ISO_TIMESTAMP]` with current UTC time, e.g. `2026-04-27T14:32:00Z`):
```json
{
  "enabled": true,
  "session_start": "[ISO_TIMESTAMP]",
  "skills_invoked": [],
  "test_files_written": [],
  "artifacts_created": [],
  "tdd_status": "pending"
}
```

**4. Create obligation task chain** based on current phase from `.sweetclaude/state/phase.yaml`:

*IMPLEMENT phase:*
- Task 1: Invoke `sweetclaude:code-feature` or `sweetclaude:code-issue`
- Task 2: Write failing tests — blocked by Task 1
- Task 3: Verify RED (run tests, confirm failure) — blocked by Task 2
- Task 4: Implement to GREEN — blocked by Task 3
- Task 5: Commit with tests — blocked by Task 4

*DESIGN phase:*
- Task 1: Invoke `sweetclaude:design-architecture` or `sweetclaude:design-tech-spec`
- Task 2: Get design approved — blocked by Task 1
- Task 3: Save artifact to `docs/` — blocked by Task 2

*DEFINE phase:*
- Task 1: Invoke `sweetclaude:product-brief` or `sweetclaude:product-prd`
- Task 2: Complete all required sections — blocked by Task 1
- Task 3: Save artifact to `docs/` — blocked by Task 2

*DISCOVER phase:*
- Task 1: Invoke `sweetclaude:product-discovery`
- Task 2: Define at least one persona — blocked by Task 1
- Task 3: Define scope boundary — blocked by Task 2

*Unknown or no phase:* Create a single task: "Determine current phase and invoke the appropriate skill."

**5. For subagent dispatch:**
When guardian is active and you use `superpowers:subagent-driven-development`, prepend this block to every implementer subagent prompt before dispatching:

```
PROTOCOL REQUIREMENTS (guardian active):
- Write failing tests BEFORE writing source code
- Verify RED before implementing
- Do not commit without all tests GREEN
- Do not modify test files
```

**6. Session responsibilities while guardian is active:**
You must keep `session-guardian.json` updated:
- Add to `skills_invoked` each time you invoke a skill (the `skill-tracker.sh` hook does this automatically, but you should also update it if the hook misses any)
- Add to `artifacts_created` when you save a design doc, product brief, architecture doc, etc.
- Update `tdd_status` as TDD progresses: `writing_tests` → `red` → `implementing` → `green`
- Mark obligation tasks complete as you finish them

**7. Confirm:**
> "Protocol Guardian active. Enforcing skill invocations, test-first, and artifact saves."
```

- [ ] **Step 2: Create `skills/guardian-off/SKILL.md`**

```markdown
---
name: guardian-off
description: Disable the Protocol Guardian for the current session
---

# Protocol Guardian — Disable

**1. Remove the guardian flag:**
Run:
```bash
rm -f .sweetclaude/state/guardian-enabled
```

**2. Confirm:**
> "Protocol Guardian disabled."

`session-guardian.json` is left in place for reference. Obligation tasks remain visible but are no longer enforced.
```

- [ ] **Step 3: Verify both skills contain required content**

```bash
grep -q "guardian-enabled" skills/guardian-on/SKILL.md && echo "PASS: guardian-on has flag creation" || echo "FAIL"
grep -q "session-guardian.json" skills/guardian-on/SKILL.md && echo "PASS: guardian-on has session state init" || echo "FAIL"
grep -q "obligation" skills/guardian-on/SKILL.md && echo "PASS: guardian-on has obligation chain" || echo "FAIL"
grep -q "rm -f .sweetclaude/state/guardian-enabled" skills/guardian-off/SKILL.md && echo "PASS: guardian-off removes flag" || echo "FAIL"
```

Expected: 4 × PASS

- [ ] **Step 4: Commit**

```bash
git add skills/guardian-on/SKILL.md skills/guardian-off/SKILL.md
git commit -m "feat: add sweetclaude:guardian-on and guardian-off skills"
```

---

## Task 2: `skill-tracker.sh` hook

**Files:**
- Create: `tests/hooks/test-skill-tracker.sh`
- Create: `hooks/skill-tracker.sh`

- [ ] **Step 1: Create test directory and write failing test**

```bash
mkdir -p tests/hooks
```

Write `tests/hooks/test-skill-tracker.sh`:

```bash
#!/bin/bash
# Tests for skill-tracker.sh

PASS=0
FAIL=0

pass() { echo "PASS: $1"; ((PASS++)); }
fail() { echo "FAIL: $1"; ((FAIL++)); }

# Setup: create a real temp git repo
TMPDIR=$(mktemp -d)
git init "$TMPDIR" -q
mkdir -p "$TMPDIR/.sweetclaude/state"
ORIGINAL_DIR=$(pwd)
cd "$TMPDIR"

cleanup() { cd "$ORIGINAL_DIR"; rm -rf "$TMPDIR"; }
trap cleanup EXIT

HOOK="$ORIGINAL_DIR/hooks/skill-tracker.sh"

# Test 1: guardian not enabled → exits cleanly, no file written
rm -f .sweetclaude/state/session-guardian.json
OUTPUT=$(echo '{"skill":"sweetclaude:brainstorming"}' | bash "$HOOK" 2>&1)
[ ! -f .sweetclaude/state/session-guardian.json ] && pass "guardian off: no file written" || fail "guardian off: should not write file"

# Test 2: guardian enabled, valid skill → appended to skills_invoked
touch .sweetclaude/state/guardian-enabled
echo '{"enabled":true,"skills_invoked":[],"test_files_written":[],"artifacts_created":[],"tdd_status":"pending"}' \
  > .sweetclaude/state/session-guardian.json

echo '{"skill":"sweetclaude:brainstorming"}' | bash "$HOOK" 2>&1
INVOKED=$(jq -r '.skills_invoked[0]' .sweetclaude/state/session-guardian.json 2>/dev/null)
[ "$INVOKED" = "sweetclaude:brainstorming" ] && pass "skill name recorded in skills_invoked" || fail "expected sweetclaude:brainstorming, got: $INVOKED"

# Test 3: second invocation appended (not overwritten)
echo '{"skill":"sweetclaude:code-feature"}' | bash "$HOOK" 2>&1
COUNT=$(jq '.skills_invoked | length' .sweetclaude/state/session-guardian.json 2>/dev/null)
[ "$COUNT" = "2" ] && pass "second skill appended (array length 2)" || fail "expected 2 entries, got: $COUNT"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
```

- [ ] **Step 2: Run test to verify it fails (hook doesn't exist yet)**

```bash
chmod +x tests/hooks/test-skill-tracker.sh
bash tests/hooks/test-skill-tracker.sh
```

Expected: FAIL on all 3 tests (hook script doesn't exist)

> **Verification note:** The `skill-tracker.sh` hook relies on Claude Code firing PostToolUse events for the Skill tool. This is not guaranteed. After Task 7 (sync + smoke test), verify that invoking a skill triggers the hook by checking whether `skills_invoked` is populated in `session-guardian.json`. If it isn't, the guardian's reasoning-layer obligation chain (from `guardian-on`) remains the primary enforcement mechanism — hook-based tracking is best-effort.

- [ ] **Step 3: Write `hooks/skill-tracker.sh`**

```bash
#!/bin/bash
# SweetClaude Skill Tracker Hook
# PostToolUse — records skill invocations to session-guardian.json

TOOL="$CLAUDE_TOOL_NAME"

# Only track Skill tool calls
if [[ "$TOOL" != "Skill" ]]; then
  exit 0
fi

# Find project root
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

STATE_DIR="$PROJECT_DIR/.sweetclaude/state"
GUARDIAN_FLAG="$STATE_DIR/guardian-enabled"
SESSION_FILE="$STATE_DIR/session-guardian.json"

# Guardian not enabled — nothing to do
if [ ! -f "$GUARDIAN_FLAG" ]; then
  exit 0
fi

# Session file missing — nothing to do
if [ ! -f "$SESSION_FILE" ]; then
  exit 0
fi

# Parse skill name from stdin JSON
INPUT=$(cat)
SKILL_NAME=$(echo "$INPUT" | jq -r '.skill // "unknown"' 2>/dev/null)

if [ -z "$SKILL_NAME" ] || [ "$SKILL_NAME" = "null" ]; then
  exit 0
fi

# Append skill name to skills_invoked array
UPDATED=$(jq --arg skill "$SKILL_NAME" '.skills_invoked += [$skill]' "$SESSION_FILE" 2>/dev/null)
if [ -n "$UPDATED" ]; then
  echo "$UPDATED" > "$SESSION_FILE"
fi

exit 0
```

- [ ] **Step 4: Make executable**

```bash
chmod +x hooks/skill-tracker.sh
```

- [ ] **Step 5: Run test to verify it passes**

```bash
bash tests/hooks/test-skill-tracker.sh
```

Expected: 3 × PASS, 0 failed

- [ ] **Step 6: Commit**

```bash
git add hooks/skill-tracker.sh tests/hooks/test-skill-tracker.sh
git commit -m "feat: add skill-tracker hook to record skill invocations"
```

---

## Task 3: `tdd-prewrite-guardian.sh` hook

**Files:**
- Create: `tests/hooks/test-tdd-prewrite-guardian.sh`
- Create: `hooks/tdd-prewrite-guardian.sh`

- [ ] **Step 1: Write failing test**

Write `tests/hooks/test-tdd-prewrite-guardian.sh`:

```bash
#!/bin/bash
# Tests for tdd-prewrite-guardian.sh

PASS=0
FAIL=0

pass() { echo "PASS: $1"; ((PASS++)); }
fail() { echo "FAIL: $1 (got: $2)"; ((FAIL++)); }

TMPDIR=$(mktemp -d)
git init "$TMPDIR" -q
mkdir -p "$TMPDIR/.sweetclaude/state"
mkdir -p "$TMPDIR/src"
ORIGINAL_DIR=$(pwd)

cleanup() { cd "$ORIGINAL_DIR"; rm -rf "$TMPDIR"; }
trap cleanup EXIT

HOOK="$ORIGINAL_DIR/hooks/tdd-prewrite-guardian.sh"

run_hook() {
  local file="$1"
  local tool="${2:-Write}"
  CLAUDE_FILE_PATH="$file" CLAUDE_TOOL_NAME="$tool" \
    GIT_DIR="$TMPDIR/.git" GIT_WORK_TREE="$TMPDIR" \
    bash "$HOOK"
}

# Test 1: guardian not enabled → allow
export CLAUDE_TOOL_NAME="Write"
OUT=$(run_hook "$TMPDIR/src/app.js" "Write")
echo "$OUT" | grep -q '"ok":.*true' && pass "guardian off → allow" || fail "guardian off → allow" "$OUT"

# Test 2: non Write/Edit tool → allow
touch "$TMPDIR/.sweetclaude/state/guardian-enabled"
echo "phase: implement" > "$TMPDIR/.sweetclaude/state/phase.yaml"
OUT=$(run_hook "$TMPDIR/src/app.js" "Read")
echo "$OUT" | grep -q '"ok":.*true' && pass "non Write/Edit tool → allow" || fail "non Write/Edit tool → allow" "$OUT"

# Test 3: guardian enabled, non-implement phase → allow
echo "phase: define" > "$TMPDIR/.sweetclaude/state/phase.yaml"
OUT=$(run_hook "$TMPDIR/src/app.js" "Write")
echo "$OUT" | grep -q '"ok":.*true' && pass "non-implement phase → allow" || fail "non-implement phase → allow" "$OUT"

# Test 4: implement phase, writing a test file → allow
echo "phase: implement" > "$TMPDIR/.sweetclaude/state/phase.yaml"
echo '{"test_files_written":[]}' > "$TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "$TMPDIR/src/app.test.js" "Write")
echo "$OUT" | grep -q '"ok":.*true' && pass "writing test file → allow" || fail "writing test file → allow" "$OUT"

# Test 5: implement phase, source file, no test evidence → block
OUT=$(run_hook "$TMPDIR/src/app.js" "Write")
echo "$OUT" | grep -q '"ok":.*false' && pass "source write, no tests → block" || fail "source write, no tests → block" "$OUT"

# Test 6: implement phase, source file, test evidence in session state → allow
echo '{"test_files_written":["src/app.test.js"]}' > "$TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "$TMPDIR/src/app.js" "Write")
echo "$OUT" | grep -q '"ok":.*true' && pass "source write, test in session state → allow" || fail "source write, test in session state → allow" "$OUT"

# Test 7: config file → allow (not a source file)
echo '{"test_files_written":[]}' > "$TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "$TMPDIR/.eslintrc.json" "Write")
echo "$OUT" | grep -q '"ok":.*true' && pass "config file → allow" || fail "config file → allow" "$OUT"

# Test 8: markdown file → allow
OUT=$(run_hook "$TMPDIR/docs/readme.md" "Write")
echo "$OUT" | grep -q '"ok":.*true' && pass "markdown file → allow" || fail "markdown file → allow" "$OUT"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
chmod +x tests/hooks/test-tdd-prewrite-guardian.sh
bash tests/hooks/test-tdd-prewrite-guardian.sh
```

Expected: multiple FAILs (hook doesn't exist)

- [ ] **Step 3: Write `hooks/tdd-prewrite-guardian.sh`**

```bash
#!/bin/bash
# SweetClaude TDD Prewrite Guardian Hook
# PreToolUse Write|Edit — blocks source file writes when no test files exist.
# Complements test-guardian.sh (which blocks test modifications during implementation).
# This hook blocks source creation before tests are written.

FILE="$CLAUDE_FILE_PATH"
TOOL="$CLAUDE_TOOL_NAME"

# Only check Write and Edit
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
  echo '{"ok": true}'
  exit 0
fi

# Find project root
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$PROJECT_DIR" ]; then
  echo '{"ok": true}'
  exit 0
fi

STATE_DIR="$PROJECT_DIR/.sweetclaude/state"
GUARDIAN_FLAG="$STATE_DIR/guardian-enabled"

# Guardian not enabled — allow
if [ ! -f "$GUARDIAN_FLAG" ]; then
  echo '{"ok": true}'
  exit 0
fi

# No phase file — allow
PHASE_FILE="$STATE_DIR/phase.yaml"
if [ ! -f "$PHASE_FILE" ]; then
  echo '{"ok": true}'
  exit 0
fi

# Only enforce during implement phase
PHASE=$(grep "^phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
if [[ "$PHASE" != "implement" ]]; then
  echo '{"ok": true}'
  exit 0
fi

# Determine if target file is a test file — if so, allow
TEST_PATTERNS=(
  "test/" "tests/" "__tests__/" "spec/" "specs/"
  ".test." ".spec." "_test." "_spec."
  "test_" "/test" "Test"
)
for pattern in "${TEST_PATTERNS[@]}"; do
  if [[ "$FILE" == *"$pattern"* ]]; then
    echo '{"ok": true}'
    exit 0
  fi
done

# Determine if target file is a non-code file — allow configs, docs, yaml, json, md, sh, etc.
NON_CODE_EXTENSIONS=("md" "json" "yaml" "yml" "toml" "ini" "cfg" "conf" "env" "sh" "bash" "txt" "lock" "log" "gitignore" "editorconfig" "prettierrc" "eslintrc" "babelrc")
EXT="${FILE##*.}"
for ext in "${NON_CODE_EXTENSIONS[@]}"; do
  if [[ "$EXT" == "$ext" ]]; then
    echo '{"ok": true}'
    exit 0
  fi
done

# Non-code path patterns — allow docs, config, state dirs
NON_CODE_PATHS=("docs/" ".sweetclaude/" "config/" ".github/" "scripts/" "dist/" "build/" "node_modules/")
for path in "${NON_CODE_PATHS[@]}"; do
  if [[ "$FILE" == *"$path"* ]]; then
    echo '{"ok": true}'
    exit 0
  fi
done

# Check for test evidence: session-guardian.json has test_files_written entries
SESSION_FILE="$STATE_DIR/session-guardian.json"
if [ -f "$SESSION_FILE" ]; then
  TEST_COUNT=$(jq '.test_files_written | length' "$SESSION_FILE" 2>/dev/null)
  if [ -n "$TEST_COUNT" ] && [ "$TEST_COUNT" -gt 0 ]; then
    echo '{"ok": true}'
    exit 0
  fi
fi

# Check for test evidence: git status shows new/modified test files this session
if git -C "$PROJECT_DIR" status --short 2>/dev/null | grep -E "(test|spec)\." | grep -qE "^[AM]"; then
  echo '{"ok": true}'
  exit 0
fi

# No test evidence found — block
echo '{"ok": false, "reason": "No test files written yet. Write failing tests before source code (TDD). Run guardian-off if you need to bypass this check."}'
exit 0
```

- [ ] **Step 4: Make executable**

```bash
chmod +x hooks/tdd-prewrite-guardian.sh
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
bash tests/hooks/test-tdd-prewrite-guardian.sh
```

Expected: 8 × PASS, 0 failed

- [ ] **Step 6: Commit**

```bash
git add hooks/tdd-prewrite-guardian.sh tests/hooks/test-tdd-prewrite-guardian.sh
git commit -m "feat: add tdd-prewrite-guardian hook to enforce test-first"
```

---

## Task 4: `artifact-guardian.sh` hook

**Files:**
- Create: `tests/hooks/test-artifact-guardian.sh`
- Create: `hooks/artifact-guardian.sh`

- [ ] **Step 1: Write failing test**

Write `tests/hooks/test-artifact-guardian.sh`:

```bash
#!/bin/bash
# Tests for artifact-guardian.sh

PASS=0
FAIL=0

pass() { echo "PASS: $1"; ((PASS++)); }
fail() { echo "FAIL: $1 (got: $2)"; ((FAIL++)); }

TMPDIR=$(mktemp -d)
git init "$TMPDIR" -q
mkdir -p "$TMPDIR/.sweetclaude/state"
ORIGINAL_DIR=$(pwd)

cleanup() { cd "$ORIGINAL_DIR"; rm -rf "$TMPDIR"; }
trap cleanup EXIT

HOOK="$ORIGINAL_DIR/hooks/artifact-guardian.sh"

run_hook() {
  local cmd="$1"
  CLAUDE_TOOL_NAME="Bash" \
    GIT_DIR="$TMPDIR/.git" GIT_WORK_TREE="$TMPDIR" \
    bash "$HOOK" <<< "{\"command\": \"$cmd\"}"
}

# Test 1: non-commit command → allow (no output, exit 0)
touch "$TMPDIR/.sweetclaude/state/guardian-enabled"
echo "phase: implement" > "$TMPDIR/.sweetclaude/state/phase.yaml"
OUT=$(run_hook "npm test" 2>&1)
[ $? -eq 0 ] && pass "non-commit command → allow" || fail "non-commit command → allow" "$OUT"

# Test 2: guardian not enabled → allow commit
rm "$TMPDIR/.sweetclaude/state/guardian-enabled"
OUT=$(run_hook "git commit -m 'test'" 2>&1)
[ $? -eq 0 ] && pass "guardian off → allow commit" || fail "guardian off → allow commit" "$OUT"

# Test 3: guardian enabled, commit, implement phase, missing test files → warn
touch "$TMPDIR/.sweetclaude/state/guardian-enabled"
echo '{"test_files_written":[],"artifacts_created":[],"tdd_status":"pending"}' \
  > "$TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'wip'" 2>&1)
echo "$OUT" | grep -qi "warning\|warn\|missing" && pass "no tests → warning printed" || fail "no tests → expected warning" "$OUT"

# Test 4: guardian enabled, commit, test files present, tdd_status green → no warning
echo '{"test_files_written":["src/app.test.js"],"artifacts_created":[],"tdd_status":"green"}' \
  > "$TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'feat: add feature'" 2>&1)
echo "$OUT" | grep -qi "warning\|warn" && fail "tests present → should not warn" "$OUT" || pass "tests present, green → no warning"

# Test 5: design phase, no artifact → warn
echo "phase: design" > "$TMPDIR/.sweetclaude/state/phase.yaml"
echo '{"test_files_written":[],"artifacts_created":[],"tdd_status":"pending"}' \
  > "$TMPDIR/.sweetclaude/state/session-guardian.json"
OUT=$(run_hook "git commit -m 'wip'" 2>&1)
echo "$OUT" | grep -qi "warning\|warn\|artifact\|missing" && pass "design phase, no artifact → warning" || fail "design phase, no artifact → expected warning" "$OUT"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
chmod +x tests/hooks/test-artifact-guardian.sh
bash tests/hooks/test-artifact-guardian.sh
```

Expected: multiple FAILs

- [ ] **Step 3: Write `hooks/artifact-guardian.sh`**

```bash
#!/bin/bash
# SweetClaude Artifact Guardian Hook
# PreToolUse Bash — warns (does not block) when committing without required phase artifacts.

TOOL="$CLAUDE_TOOL_NAME"

# Only check Bash tool calls
if [[ "$TOOL" != "Bash" ]]; then
  exit 0
fi

# Read command from stdin JSON
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.command // ""' 2>/dev/null)

# Only check git commit commands
if ! echo "$COMMAND" | grep -qE '^git commit'; then
  exit 0
fi

# Find project root
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

STATE_DIR="$PROJECT_DIR/.sweetclaude/state"
GUARDIAN_FLAG="$STATE_DIR/guardian-enabled"

# Guardian not enabled — allow
if [ ! -f "$GUARDIAN_FLAG" ]; then
  exit 0
fi

# No phase file — allow
PHASE_FILE="$STATE_DIR/phase.yaml"
if [ ! -f "$PHASE_FILE" ]; then
  exit 0
fi

PHASE=$(grep "^phase:" "$PHASE_FILE" 2>/dev/null | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
SESSION_FILE="$STATE_DIR/session-guardian.json"

warn() {
  echo "[Protocol Guardian] WARNING: $1" >&2
}

case "$PHASE" in
  implement)
    if [ -f "$SESSION_FILE" ]; then
      TEST_COUNT=$(jq '.test_files_written | length' "$SESSION_FILE" 2>/dev/null)
      TDD_STATUS=$(jq -r '.tdd_status // "unknown"' "$SESSION_FILE" 2>/dev/null)

      if [ -z "$TEST_COUNT" ] || [ "$TEST_COUNT" -eq 0 ]; then
        warn "Committing in IMPLEMENT phase with no test files recorded in session state."
      fi
      if [[ "$TDD_STATUS" != "green" && "$TDD_STATUS" != "implementing" ]]; then
        warn "TDD status is '$TDD_STATUS' — expected 'green' before committing."
      fi
    else
      warn "No session-guardian.json found. Cannot verify test coverage for this commit."
    fi
    ;;
  design)
    if [ -f "$SESSION_FILE" ]; then
      ARTIFACT_COUNT=$(jq '.artifacts_created | length' "$SESSION_FILE" 2>/dev/null)
      if [ -z "$ARTIFACT_COUNT" ] || [ "$ARTIFACT_COUNT" -eq 0 ]; then
        warn "Committing in DESIGN phase with no design artifacts recorded. Save architecture or tech spec to docs/ first."
      fi
    else
      warn "No session-guardian.json found. Cannot verify artifacts for this commit."
    fi
    ;;
  define)
    if [ -f "$SESSION_FILE" ]; then
      ARTIFACT_COUNT=$(jq '.artifacts_created | length' "$SESSION_FILE" 2>/dev/null)
      if [ -z "$ARTIFACT_COUNT" ] || [ "$ARTIFACT_COUNT" -eq 0 ]; then
        warn "Committing in DEFINE phase with no artifacts recorded. Save product brief or PRD to docs/ first."
      fi
    fi
    ;;
esac

# Always allow — this hook warns but never blocks commits
exit 0
```

- [ ] **Step 4: Make executable**

```bash
chmod +x hooks/artifact-guardian.sh
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
bash tests/hooks/test-artifact-guardian.sh
```

Expected: 5 × PASS, 0 failed

- [ ] **Step 6: Commit**

```bash
git add hooks/artifact-guardian.sh tests/hooks/test-artifact-guardian.sh
git commit -m "feat: add artifact-guardian hook to warn on commits with missing artifacts"
```

---

## Task 5: Update `hooks/hooks.json`

**Files:**
- Modify: `hooks/hooks.json`

- [ ] **Step 1: Add three new hook entries to `hooks/hooks.json`**

The current `hooks/hooks.json` PreToolUse section ends after the `test-guardian.sh` entry, and PostToolUse ends after `version-bump.sh`. Add:

In `PreToolUse`, after the `test-guardian.sh` entry:
```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/tdd-prewrite-guardian.sh"
    }
  ]
},
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/artifact-guardian.sh"
    }
  ]
}
```

In `PostToolUse`, after the existing entries:
```json
{
  "matcher": "Skill",
  "hooks": [
    {
      "type": "command",
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/skill-tracker.sh"
    }
  ]
}
```

The complete updated `hooks/hooks.json` should be:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-preflight.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/preflight-guard.sh"
          }
        ]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/test-guardian.sh"
          }
        ]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/tdd-prewrite-guardian.sh"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/artifact-guardian.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/auto-test-runner.sh"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/version-bump.sh"
          }
        ]
      },
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/skill-tracker.sh"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Validate JSON is well-formed**

```bash
jq . hooks/hooks.json > /dev/null && echo "PASS: valid JSON" || echo "FAIL: invalid JSON"
```

Expected: PASS

- [ ] **Step 3: Verify all 3 new hooks are present**

```bash
grep -c "tdd-prewrite-guardian" hooks/hooks.json | grep -q "1" && echo "PASS: tdd-prewrite-guardian present" || echo "FAIL"
grep -c "artifact-guardian" hooks/hooks.json | grep -q "1" && echo "PASS: artifact-guardian present" || echo "FAIL"
grep -c "skill-tracker" hooks/hooks.json | grep -q "1" && echo "PASS: skill-tracker present" || echo "FAIL"
```

Expected: 3 × PASS

- [ ] **Step 4: Commit**

```bash
git add hooks/hooks.json
git commit -m "feat: register tdd-prewrite-guardian, artifact-guardian, and skill-tracker hooks"
```

---

## Task 6: Frustration detection

**Files:**
- Modify: `rules/interaction-model.md`
- Modify: `skills/master/SKILL.md`

- [ ] **Step 1: Add Protocol Guardian Offer section to `rules/interaction-model.md`**

Insert the following new section after the `## Continuous Improvement` section (before `## No Time-Based Anxiety`):

```markdown
## Protocol Guardian Offer

Watch for signals that Claude is ignoring SweetClaude protocols. When detected, proactively offer to enable the Protocol Guardian.

**Signals:**
- User says "you skipped X", "you ignored Y", "you're not following the protocol", "you went off the rails"
- User corrects the same protocol violation twice in the same session
- User expresses visible frustration about missing steps or skipped skills
- Claude realizes mid-task it skipped a required step

**When triggered**, offer once — do not auto-enable:
> "It looks like I've been skipping protocol steps. Want me to enable the Protocol Guardian? It enforces skill invocations, TDD discipline, and artifact saves for the rest of this session. Run `/sweetclaude:guardian-on` to enable it."

**Rules:**
- Offer once per trigger event, not repeatedly
- Do not enable the guardian without explicit user consent
- If the user declines, note it and continue without re-offering for that session
- If the user accepts, invoke `sweetclaude:guardian-on`
```

- [ ] **Step 2: Add guardian mention to `skills/master/SKILL.md`**

In the `## Interaction Rules` section of `skills/master/SKILL.md`, add after the existing bullet list:

```markdown
- Protocol guardian — if protocol violations are detected or user expresses frustration with skipped steps, offer `/sweetclaude:guardian-on` (see interaction-model.md for full trigger rules)
```

- [ ] **Step 3: Verify insertions**

```bash
grep -q "Protocol Guardian Offer" rules/interaction-model.md && echo "PASS: section added to interaction-model" || echo "FAIL"
grep -q "guardian-on" skills/master/SKILL.md && echo "PASS: guardian mention added to master" || echo "FAIL"
```

Expected: 2 × PASS

- [ ] **Step 4: Commit**

```bash
git add rules/interaction-model.md skills/master/SKILL.md
git commit -m "feat: add protocol guardian frustration detection triggers"
```

---

## Task 7: Sync to installed location

**Files:**
- No new files — sync repo → `~/.claude/`

- [ ] **Step 1: Run install.sh to sync all changes**

```bash
./install.sh
```

Expected output includes confirmation that skills, hooks, and rules were copied. No errors.

- [ ] **Step 2: Verify installed files match repo**

```bash
diff hooks/tdd-prewrite-guardian.sh ~/.claude/hooks/sweetclaude/tdd-prewrite-guardian.sh && echo "PASS: tdd-prewrite-guardian synced" || echo "FAIL"
diff hooks/artifact-guardian.sh ~/.claude/hooks/sweetclaude/artifact-guardian.sh && echo "PASS: artifact-guardian synced" || echo "FAIL"
diff hooks/skill-tracker.sh ~/.claude/hooks/sweetclaude/skill-tracker.sh && echo "PASS: skill-tracker synced" || echo "FAIL"
diff hooks/hooks.json ~/.claude/hooks/sweetclaude/hooks.json && echo "PASS: hooks.json synced" || echo "FAIL"
diff skills/guardian-on/SKILL.md ~/.claude/skills/sweetclaude/guardian-on/SKILL.md && echo "PASS: guardian-on synced" || echo "FAIL"
diff skills/guardian-off/SKILL.md ~/.claude/skills/sweetclaude/guardian-off/SKILL.md && echo "PASS: guardian-off synced" || echo "FAIL"
diff rules/interaction-model.md ~/.claude/rules/sweetclaude/interaction-model.md && echo "PASS: interaction-model synced" || echo "FAIL"
```

Expected: 7 × PASS

- [ ] **Step 3: Smoke test guardian-on in a configured project**

In a SweetClaude-configured project directory, run:
```bash
/sweetclaude:guardian-on
```

Verify:
- `.sweetclaude/state/guardian-enabled` flag file created
- `.sweetclaude/state/session-guardian.json` initialized
- Obligation tasks created
- Confirmation message printed

- [ ] **Step 4: Smoke test guardian-off**

```bash
/sweetclaude:guardian-off
```

Verify:
- `.sweetclaude/state/guardian-enabled` removed
- `session-guardian.json` still present
- Confirmation message printed

- [ ] **Step 5: Final commit**

```bash
git add -A
git status  # verify only expected files
git commit -m "chore: bump version post-protocol-guardian implementation"
```
