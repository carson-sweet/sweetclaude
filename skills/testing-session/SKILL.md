---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:testing-session
description: "Run a manual QA session. Charter-based or scripted. Pass/fail tracking per test case. File bugs directly to project-issues."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh

# Active test plans
ls .sweetclaude/testing/plans/TP-*.md 2>/dev/null | head -5

# Recent sessions
ls .sweetclaude/testing/sessions/QA-*.md 2>/dev/null | tail -5 | xargs -I{} basename {}

# Count open sessions
python3 -c "
import os, glob, re
sessions = glob.glob('.sweetclaude/testing/sessions/QA-*.md')
open_s = []
for s in sessions:
    try:
        content = open(s).read()
        if 'status: open' in content:
            open_s.append(os.path.basename(s))
    except: pass
print(f'OPEN_SESSIONS={len(open_s)}')
print('OPEN_LIST=' + ','.join(open_s))
" 2>/dev/null || echo "OPEN_SESSIONS=0"
```

# Testing Session

Run a manual QA session — scripted test cases or exploratory charter. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `new` | → **Start** a new QA session |
| `resume <QA-NNN>` | → **Resume** an open session |
| `list` | → **List** past sessions |
| `view <QA-NNN>` | → **View** session summary |

---

## New

### Step 1: Session setup

**Session type:**

"What kind of QA session is this?"
- `scripted` — working through a defined list of test cases
- `exploratory` — charter-based: a goal and time box, no fixed scripts

**Scope:**

"What are you testing?" Show active test plans from shell output. Accept:
- A test plan ID (`TP-NNN`) — load its scope and exit criteria
- A roadmap item or epic ID
- A freeform description ("auth flow end to end", "file upload on mobile")

**Environment:**

"Which environment?" (local, staging, production)

**Device/context** (for web and mobile):

"Any specific device, browser, or context to note?"

---

### Step 2: Test cases (scripted mode)

Ask: "List the test cases, one per line. Format: title | expected result"

Example:
```
Log in with valid credentials | Dashboard loads, no errors
Log in with wrong password | Error message shown, account not locked
Reset password flow | Email received, link works, password updated
```

If tied to a test plan with exit criteria, surface them: "These exit criteria apply — I'll flag them when we're done."

If no test cases provided, switch to exploratory: "No test cases — switching to exploratory mode. What's the charter?"

---

### Step 3: Charter (exploratory mode)

"Complete this charter: 'Explore [area] to discover [what you're looking for] using [approach].'"

Example: "Explore the file upload flow to discover edge cases in large file handling using varying file sizes and network conditions."

Time box: "How long? (e.g., 30 min, 1 hour)"

---

### Step 4: Create session file

Assign QA-NNN (next sequential from existing sessions).

```bash
mkdir -p .sweetclaude/testing/sessions/
```

Write `.sweetclaude/testing/sessions/QA-NNN.md`:

```markdown
---
id: QA-NNN
type: scripted | exploratory
scope: TP-NNN | RM-NNN | description
environment: staging
context: Chrome 124, MacOS
status: open
started_at: YYYY-MM-DD HH:MM
tester: me
---

# QA-NNN — {scope description}

## Charter
{charter text — exploratory only}

## Test Cases
| # | Test Case | Expected | Result | Notes |
|---|---|---|---|---|
| 1 | Log in with valid credentials | Dashboard loads | — | — |
| 2 | ... | ... | — | — |

## Bugs Filed
{list as they are filed}

## Session Notes
{running notes}
```

Confirm: `Session QA-NNN open — {N} test cases | {environment}`

---

### Step 5: Run loop

Present each test case in sequence:

```
─────────────────────────────────────────
Test {n} of {N}: {title}

  Expected: {expected result}

  Result? (pass / fail / skip / note)
```

Accept:
- **`pass`** or Enter → mark pass, move to next
- **`fail`** → prompt for bug details (see Step 6)
- **`skip`** → mark skipped with optional reason, move to next
- **`note <text>`** → add a note without changing result, re-prompt
- **`q`** → pause session, save state

For exploratory sessions — present the charter and accept running notes. Use `bug` to file a finding, `done` to close.

---

### Step 6: Bug filing

On `fail` for a scripted test case, or `bug` in exploratory mode:

Prompt:
1. "Title?" (pre-fill from test case name if available)
2. "Steps to reproduce?" (one per line)
3. "Expected vs actual?"
4. "Severity?" — P0 (crash/data loss), P1 (broken feature), P2 (degraded UX), P3 (cosmetic)

```bash
source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_create issue '{
  "title": "<bug title>",
  "type": "bug",
  "status": "backlog",
  "priority": "<now|sooner|soonish|later>",
  "description": "Steps to reproduce:\n<steps>\n\nExpected: <expected>\nActual: <actual>",
  "tags": ["qa", "QA-NNN"]
}'
```

Confirm: `Filed <I-NNN> — {title}` and append to session file Bugs Filed section.

Severity → priority mapping:
- P0 → `now`
- P1 → `sooner`
- P2 → `soonish`
- P3 → `later`

---

### Step 7: Session close

After all cases (or `q`), present summary:

```
QA-NNN — Session Summary
─────────────────────────────────────────
Scope:       {scope}
Environment: {environment}

Test cases:  {N} total
  Pass:      {N}
  Fail:      {N}
  Skip:      {N}

Bugs filed:  {N}
  {I-NNN}  P0  Crash on file upload > 100MB
  {I-NNN}  P2  Button misaligned on mobile

Duration:    {elapsed}
```

If tied to a test plan — check exit criteria:

```
Exit criteria check
  [x] All test cases executed
  [x] No open P0 bugs
  [ ] Performance within thresholds — NOT TESTED THIS SESSION
  [x] Accessibility WCAG 2.1 AA — not in scope
```

Mark criteria met/not met. Note: "Run `testing-plan update TP-NNN` to record these results against the plan."

Update session file `status: closed`, `closed_at: {datetime}`.

---

## Resume

Arguments: `resume <QA-NNN>`

Load session file. Show remaining test cases (those without a result). Continue from Step 5.

---

## List

```bash
ls .sweetclaude/testing/sessions/QA-*.md 2>/dev/null
```

Present each with type, scope, status, and bug count:

```
QA-001  scripted    RM-001 Auth flow       closed  2 bugs
QA-002  exploratory file upload            open    1 bug
```

---

## Rules

- File bugs during the session, not after. Memory degrades — log it when you see it.
- A skipped test case is not a passed test case. Skips reduce coverage — surface them in the summary.
- P0 bugs should be flagged immediately: "This is a P0 — it should block shipping until resolved."
- Session notes are yours — write what helps you. They are not reviewed.
- Closing a session does not mean the scope is tested — it means this session is done. Multiple sessions may cover one scope.
