# John Wick Mode — Plan 1: Building Blocks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify all individual capabilities required by John Wick mode — compliance context, autonomous PRD generation, phase check-in subagent, compliance-aware code review, and cross-session test locking — before the orchestrator that calls them is written.

**Architecture:** Five targeted modifications/additions to existing skills and hooks. Each task produces working, testable output in isolation. Plan 2 (the orchestrator) must not start until this plan is complete and committed.

**Tech Stack:** Markdown (SKILL.md authoring), Bash (hook script), Python 3 (YAML validation and test scripts), rsync (sync repo → installed plugin), git.

**Repo:** `/Users/carsonsweet/dev/sweetclaude`
**Installed:** `/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0`
**Spec:** `/Users/carsonsweet/dev/sweetclaude/docs/john-wick-mode-spec-v1-2026-04-28.md`

---

## Pre-flight

```bash
# Confirm on the right branch
git -C /Users/carsonsweet/dev/sweetclaude branch --show-current
# Expected: john-wick-mode

# Confirm Python3 available
python3 --version
# Expected: Python 3.x.x

# Confirm skills exist that we'll be modifying
ls /Users/carsonsweet/dev/sweetclaude/skills/ | grep -E "product-discovery|product-prd|code-review"
# Expected: all three listed
```

---

## Task 1: Extend product-discovery with compliance interview

**Files:**
- Modify: `skills/product-discovery/SKILL.md`

The compliance interview section is added between the last discovery section (L3 exit or whatever level the user chose) and `## Exit`. It asks three questions and writes `.sweetclaude/state/compliance-context.yaml`.

- [ ] **Step 1: Write the verification test**

```python
# /tmp/test_task1.py
with open('/Users/carsonsweet/dev/sweetclaude/skills/product-discovery/SKILL.md') as f:
    content = f.read()

assert '## Compliance Context' in content, "FAIL: Missing Compliance Context section"
assert 'compliance-context.yaml' in content, "FAIL: Missing compliance-context.yaml"
assert 'derived_frameworks' in content, "FAIL: Missing derived_frameworks field"
assert 'eu_uk' in content, "FAIL: Missing eu_uk geography option"
assert 'gdpr_floor' in content, "FAIL: Missing gdpr_floor fallback"
assert 'HIPAA' in content or 'hipaa' in content, "FAIL: Missing HIPAA framework"
print("PASS")
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python3 /tmp/test_task1.py
# Expected: AssertionError on "Missing Compliance Context section"
```

- [ ] **Step 3: Add the Compliance Context section**

In `skills/product-discovery/SKILL.md`, locate the line `## Exit`. Insert the following block immediately before it:

```markdown
## Compliance Context

Ask these three questions before writing state. One at a time.

**A. Data categories:**
> "What data will this service handle? Select all that apply:
> - **PII** — names, emails, addresses, government IDs
> - **Financial** — payment methods, transaction records, account balances
> - **Health / medical** — diagnoses, prescriptions, health records
> - **Behavioral / tracking** — usage logs, location data, clickstreams
> - **None of the above**"

**B. User geography:**
> "Where are your users? Select all that apply:
> - **United States**
> - **European Union or UK**
> - **Global or unknown**
> - **Other** (specify)"

**C. User type:**
> "Who are your users? Select all that apply:
> - **Consumers (B2C)**
> - **Enterprise / business users (B2B)**
> - **Minors or potentially mixed-age audience**
> - **Healthcare providers or patients**
> - **Financial services users**"

Derive applicable frameworks from answers:

| Condition | Framework |
|---|---|
| EU or UK geography AND PII data | `gdpr` (required) |
| US geography AND health data | `hipaa` (required) |
| Financial data present | `pci_dss` (required) |
| Minors in user type | `coppa` (required) |
| No specific framework triggered | `gdpr_floor` |

Write `.sweetclaude/state/compliance-context.yaml`:

```yaml
schema_version: 1
collected_at: {ISO datetime}
data_categories:
  - {pii | financial | health | behavioral | none}
user_geography:
  - {us | eu_uk | global | other}
user_type:
  - {b2c | b2b | minors | healthcare | financial}
derived_frameworks:
  - {gdpr | hipaa | pci_dss | coppa | gdpr_floor}
notes: null
```
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
python3 /tmp/test_task1.py
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/carsonsweet/dev/sweetclaude add skills/product-discovery/SKILL.md
git -C /Users/carsonsweet/dev/sweetclaude commit -m "feat(john-wick): add compliance context interview to product-discovery"
```

---

## Task 2: Extend product-prd with autonomous generation mode

**Files:**
- Modify: `skills/product-prd/SKILL.md`

An autonomous execution path is added after `## Entry` and before `## Pre-Write Flow`. When `--autonomous` is present in `$ARGUMENTS`, the skill reads discovery artifacts, generates the PRD without user interaction, flags thin sections, and stops — it never reaches Pre-Write Flow.

- [ ] **Step 1: Write the verification test**

```python
# /tmp/test_task2.py
with open('/Users/carsonsweet/dev/sweetclaude/skills/product-prd/SKILL.md') as f:
    content = f.read()

assert '## Autonomous Mode' in content, "FAIL: Missing Autonomous Mode section"
assert '--autonomous' in content, "FAIL: Missing --autonomous flag"
assert 'compliance-context.yaml' in content, "FAIL: Missing compliance-context.yaml reference"
assert 'Flagged for review' in content, "FAIL: Missing flagged section pattern"
assert 'derived_frameworks' in content, "FAIL: Missing derived_frameworks reference"
assert '## Autonomous Mode' in content[:content.index('## Pre-Write Flow')], \
    "FAIL: Autonomous Mode must appear before Pre-Write Flow"
print("PASS")
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python3 /tmp/test_task2.py
# Expected: AssertionError on "Missing Autonomous Mode section"
```

- [ ] **Step 3: Add the Autonomous Mode section**

In `skills/product-prd/SKILL.md`, locate the line `## Pre-Write Flow`. Insert the following block immediately before it:

```markdown
## Autonomous Mode

If `$ARGUMENTS` contains `--autonomous` or `--from-artifacts`, skip all user interaction and generate the PRD from available artifacts.

**Step 1: Read available artifacts**

Load the following files if they exist:
- `.sweetclaude/state/discovery.yaml` — project intent, scope, problem, not_scope
- `.sweetclaude/state/compliance-context.yaml` — data categories, derived frameworks
- `.sweetclaude/state/personas.yaml` — target users
- `.sweetclaude/state/brief.yaml` — product brief content
- Any `.md` docs in `docs/` matching: personas, task-analysis, constraints, discovery

**Step 2: Generate PRD using the standard outline**

Sections (in order):
1. Executive Summary — synthesize from discovery intent + problem_summary
2. Problem Statement — use the concrete scenario from L2/L3; if absent, flag
3. Goals and Success Metrics — derive from task success criteria; must be binary (true/false after ship)
4. Functional Requirements — numbered `FR-001`, `FR-002`… one requirement per testable behavior
5. Non-Functional Requirements — include compliance NFRs derived from `compliance-context.yaml derived_frameworks`:
   - `gdpr` → NFR: All PII must be encrypted at rest and in transit; users must be able to request deletion
   - `hipaa` → NFR: PHI access must be logged with user ID, timestamp, and action
   - `pci_dss` → NFR: Cardholder data must never be stored in plaintext
   - `coppa` → NFR: No personal data collected from users under 13 without verifiable parental consent
   - `gdpr_floor` → NFR: Data minimization; collect only what is necessary for the stated purpose
6. Epics and User Story Summary — derive from personas and task analysis
7. Out of Scope — use `not_scope` from `discovery.yaml`
8. Assumptions and Constraints — use constraints artifacts
9. Open Questions
10. Additional Development

**Step 3: Flag thin sections**

For each section where source artifacts provided insufficient signal, append inline:
> `⚠️ Flagged for review: [specific gap — what information was missing and what the user should provide at PRD review]`

Do not halt. Complete the full PRD with all flags inline, then continue to Step 4.

**Step 4: Write output**

Write to `docs/prd-[feature-name]-v1-[YYYY-MM-DD].md`. Use the standard front matter:

```yaml
---
title: {feature} PRD
version: 1.0
status: draft
author: {git user}
assisted_by: Claude Code + SweetClaude John Wick
date: {YYYY-MM-DD}
generated: autonomous
---
```

**Step 5: Report flags**

Output:
```
Autonomous PRD generation complete.
File: docs/prd-[feature]-v1-[date].md

Flagged sections for D4 review gate:
- [Section name]: [gap description]
```

If no sections flagged: "All sections populated from discovery artifacts."

**Stop here.** Do not proceed to Pre-Write Flow.

```

- [ ] **Step 4: Run test to confirm it passes**

```bash
python3 /tmp/test_task2.py
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/carsonsweet/dev/sweetclaude add skills/product-prd/SKILL.md
git -C /Users/carsonsweet/dev/sweetclaude commit -m "feat(john-wick): add autonomous PRD generation mode to product-prd"
```

---

## Task 3: Create john-wick-checkin subagent skill

**Files:**
- Create: `skills/john-wick-checkin/SKILL.md`

A narrow, single-purpose subagent. It receives a specific phase-transition question, reads the relevant artifacts, and returns a classified finding: `none`, `minor`, or `significant`. It does not produce recommendations, suggestions, or general commentary — one finding, classified, done.

- [ ] **Step 1: Write the verification test**

```python
# /tmp/test_task3.py
import os

skill_path = '/Users/carsonsweet/dev/sweetclaude/skills/john-wick-checkin/SKILL.md'
assert os.path.exists(skill_path), "FAIL: Skill file does not exist"

with open(skill_path) as f:
    content = f.read()

# Frontmatter
assert 'name: sweetclaude:john-wick-checkin' in content, "FAIL: Missing skill name"

# Required sections
assert '## Input' in content, "FAIL: Missing Input section"
assert '## Process' in content, "FAIL: Missing Process section"
assert 'post_lock' in content, "FAIL: Missing post_lock parameter"
assert 'none | minor | significant' in content, "FAIL: Missing classification options"

# IP5 boundary rule
assert 'test files' in content.lower() and 'locked' in content.lower(), \
    "FAIL: Missing post-lock test file rule"

# Output constraint
assert 'One finding maximum' in content or 'one finding' in content.lower(), \
    "FAIL: Missing single-finding constraint"

print("PASS")
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python3 /tmp/test_task3.py
# Expected: AssertionError on "Skill file does not exist"
```

- [ ] **Step 3: Create the skill file**

```bash
mkdir -p /Users/carsonsweet/dev/sweetclaude/skills/john-wick-checkin
```

Write `/Users/carsonsweet/dev/sweetclaude/skills/john-wick-checkin/SKILL.md`:

```markdown
---
name: sweetclaude:john-wick-checkin
description: Internal John Wick phase check-in subagent. Receives phase context and a single question, reviews artifacts for drift, returns none/minor/significant. Not a user-facing skill — invoked by the john-wick orchestrator only.
---

# John Wick Phase Check-in

Internal subagent invoked by the john-wick orchestrator at phase transitions.

## Input

Parse from `$ARGUMENTS` (space-separated key=value pairs):

| Parameter | Required | Description |
|---|---|---|
| `phase` | Yes | Phase being reviewed: `DEFINE`, `PLAN`, `DESIGN`, `IMPLEMENT` |
| `question` | Yes | The specific drift-detection question to answer |
| `discovery_artifacts` | Yes | Comma-separated file paths: the original discovery docs |
| `phase_artifacts` | Yes | Comma-separated file paths: artifacts produced in the completed phase |
| `post_lock` | Yes | `true` or `false` — whether IP5 has already executed |

## Process

**Step 1: Read artifacts**

Read every file listed in `discovery_artifacts` and `phase_artifacts`. These are your only context. Do not search the codebase or read other files.

**Step 2: Answer the question**

Answer the specific `question` directly from the artifact content. Do not address anything outside the question scope. Do not produce alternative suggestions, improvement lists, or general commentary.

**Step 3: Classify**

Classify as exactly one of:

- **none** — artifacts are consistent; no issue found relevant to the question
- **minor** — a small inconsistency or gap exists but does not block the next phase; note it and continue
- **significant** — a specific inconsistency or gap that, if unaddressed, will cause a concrete problem in the next phase (missed requirement, contradictory acceptance criteria, design/story mismatch, etc.)

When uncertain between `minor` and `significant`: classify `significant`. Unnecessary interruptions are better than undetected drift.

**Step 4: Output**

```
CHECK-IN: {phase} → {next_phase}
Question: {question}
Result: {none | minor | significant}
```

If `minor` or `significant`, add:
```
Finding: {artifact name} — {section or requirement} — {specific inconsistency in one sentence}
Action: {return to gate X | log and continue}
```

If `post_lock=true` and result is `significant`, add:
```
NOTE: Test files are locked (IP5 complete). This finding escalates to the IM2 human
gate. The check-in cannot recommend changes to locked test files.
```

## Rules

- One finding maximum. If multiple issues exist, report the most significant one.
- Do not produce recommendation lists, alternative approaches, or suggestions beyond the single finding.
- `post_lock: true` changes the action for significant findings: always escalate to IM2, never self-correct.
- Significant findings before IP5 → return to nearest interactive gate.
- Significant findings after IP5 → IM2 escalation only.
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
python3 /tmp/test_task3.py
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/carsonsweet/dev/sweetclaude add skills/john-wick-checkin/SKILL.md
git -C /Users/carsonsweet/dev/sweetclaude commit -m "feat(john-wick): add john-wick-checkin phase check-in subagent skill"
```

---

## Task 4: Update code-review to read compliance-context.yaml

**Files:**
- Modify: `skills/code-review/SKILL.md`

The current compliance review asks the user which frameworks apply. Update it to first check for `.sweetclaude/state/compliance-context.yaml`. If found, use `derived_frameworks` directly. If not found, ask (unchanged existing behavior).

- [ ] **Step 1: Write the verification test**

```python
# /tmp/test_task4.py
with open('/Users/carsonsweet/dev/sweetclaude/skills/code-review/SKILL.md') as f:
    content = f.read()

# Find the compliance review section
compliance_idx = content.index('## Compliance Review')
compliance_section = content[compliance_idx:compliance_idx + 800]

assert 'compliance-context.yaml' in compliance_section, \
    "FAIL: compliance-context.yaml check missing from Compliance Review section"
assert 'derived_frameworks' in compliance_section, \
    "FAIL: derived_frameworks reference missing"
assert 'If the file does not exist' in compliance_section or \
    'If not found' in compliance_section or \
    'does not exist' in compliance_section, \
    "FAIL: Missing fallback to asking user when file is absent"
print("PASS")
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python3 /tmp/test_task4.py
# Expected: AssertionError on "compliance-context.yaml check missing"
```

- [ ] **Step 3: Update the Compliance Review section**

In `skills/code-review/SKILL.md`, locate the `## Compliance Review` section. Replace the opening paragraph (the one starting "Begin by asking:") with:

```markdown
## Compliance Review

**Check for compliance context first:**

Look for `.sweetclaude/state/compliance-context.yaml`. If it exists, read `derived_frameworks` from it and use those frameworks directly — do not ask the user:
> "Using compliance context from discovery: [{frameworks listed}]. Running compliance review against these frameworks."

If the file does not exist, ask:
> "What compliance frameworks apply to this project? (e.g. GDPR, HIPAA, SOC 2, PCI-DSS, CCPA, open source licenses — or 'general')"

```

Then leave the rest of the section (Focus areas, Output format) unchanged.

- [ ] **Step 4: Run test to confirm it passes**

```bash
python3 /tmp/test_task4.py
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/carsonsweet/dev/sweetclaude add skills/code-review/SKILL.md
git -C /Users/carsonsweet/dev/sweetclaude commit -m "feat(john-wick): code-review compliance section reads compliance-context.yaml when present"
```

---

## Task 5: Extend test-guardian.sh for john-wick locked files

**Files:**
- Modify: `hooks/test-guardian.sh`

The existing hook blocks writes to test files during `tdd_phase: implementing`. John Wick mode needs it to additionally block writes to any file listed in `john-wick.yaml` `locked_test_files` — this is a persistent cross-session lock that applies from IP5 through the end of the pipeline, regardless of `tdd_phase`.

The new check runs after the existing IS_TEST pattern check. If the file being written appears in `locked_test_files`, block it with a John Wick-specific message.

- [ ] **Step 1: Write the verification test**

```bash
# /tmp/test_task5.sh
set -e
REPO=/Users/carsonsweet/dev/sweetclaude

# Create a temporary project structure
TMP=$(mktemp -d)
cd "$TMP"
git init -q
mkdir -p .sweetclaude/state

# Write a john-wick.yaml with a locked file
cat > .sweetclaude/state/john-wick.yaml << 'EOF'
schema_version: 1
status: active
locked_test_files:
  - tests/test_payments.py
EOF

# Write a phase.yaml (non-implementing phase, to ensure john-wick lock takes precedence)
cat > .sweetclaude/state/phase.yaml << 'EOF'
schema_version: 1
phase: IMPLEMENT
EOF

# Simulate the hook: set env vars as Claude Code would
export CLAUDE_TOOL_NAME=Write
export CLAUDE_FILE_PATH="$TMP/tests/test_payments.py"

# Run the hook
RESULT=$(bash "$REPO/hooks/test-guardian.sh")
echo "Hook output: $RESULT"

# Verify it blocks
if echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if not d.get('ok') else 1)"; then
  echo "PASS: Hook blocked write to locked file"
else
  echo "FAIL: Hook did not block write to locked file"
  rm -rf "$TMP"
  exit 1
fi

# Verify a non-locked file is allowed
export CLAUDE_FILE_PATH="$TMP/src/payments.py"
RESULT=$(bash "$REPO/hooks/test-guardian.sh")
if echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') else 1)"; then
  echo "PASS: Hook allowed write to non-locked file"
else
  echo "FAIL: Hook blocked write to non-locked file"
  rm -rf "$TMP"
  exit 1
fi

rm -rf "$TMP"
echo "ALL PASS"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
bash /tmp/test_task5.sh
# Expected: FAIL — hook does not yet block based on john-wick.yaml
```

- [ ] **Step 3: Add the john-wick locked files check to test-guardian.sh**

In `hooks/test-guardian.sh`, locate the line:
```bash
echo '{"ok": true}'
exit 0
```
at the very end of the file (the final exit). Insert the following block immediately before the final `echo '{"ok": true}'`:

```bash
# Check john-wick mode locked files
if command -v python3 &>/dev/null; then
  JW_STATE="$PROJECT_DIR/.sweetclaude/state/john-wick.yaml"
  if [ -f "$JW_STATE" ]; then
    IS_JW_LOCKED=$(python3 - <<PYEOF 2>/dev/null || echo "false"
import yaml, os
with open('$JW_STATE') as f:
    state = yaml.safe_load(f) or {}
locked = state.get('locked_test_files') or []
target = os.path.abspath('$FILE') if '$FILE' else ''
print('true' if target in [os.path.abspath(p) for p in locked] else 'false')
PYEOF
)
    if [ "$IS_JW_LOCKED" = "true" ]; then
      echo '{"ok": false, "reason": "This file is locked by John Wick mode (locked at pipeline step IP5). Test files are immutable for the remainder of the pipeline. To unlock: inspect .sweetclaude/state/john-wick.yaml locked_test_files and get explicit user approval."}'
      exit 0
    fi
  fi
fi
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
bash /tmp/test_task5.sh
# Expected: PASS: Hook blocked write to locked file
#           PASS: Hook allowed write to non-locked file
#           ALL PASS
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/carsonsweet/dev/sweetclaude add hooks/test-guardian.sh
git -C /Users/carsonsweet/dev/sweetclaude commit -m "feat(john-wick): extend test-guardian to enforce john-wick.yaml locked_test_files"
```

---

## Task 6: Sync all changes to installed location and verify

**Files:** Sync repo → installed plugin cache.

- [ ] **Step 1: Sync skills directory**

```bash
rsync -a --delete \
  /Users/carsonsweet/dev/sweetclaude/skills/ \
  /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/
```

- [ ] **Step 2: Sync hooks directory**

```bash
rsync -a \
  /Users/carsonsweet/dev/sweetclaude/hooks/ \
  /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/hooks/
```

- [ ] **Step 3: Verify new skill appears in installed location**

```bash
ls /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/ \
  | grep john-wick-checkin
# Expected: john-wick-checkin
```

- [ ] **Step 4: Verify modified skills are in sync**

```bash
diff \
  /Users/carsonsweet/dev/sweetclaude/skills/product-discovery/SKILL.md \
  /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/product-discovery/SKILL.md
# Expected: no output (files identical)

diff \
  /Users/carsonsweet/dev/sweetclaude/skills/product-prd/SKILL.md \
  /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/product-prd/SKILL.md
# Expected: no output

diff \
  /Users/carsonsweet/dev/sweetclaude/skills/code-review/SKILL.md \
  /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/code-review/SKILL.md
# Expected: no output
```

- [ ] **Step 5: Verify hook is in sync**

```bash
diff \
  /Users/carsonsweet/dev/sweetclaude/hooks/test-guardian.sh \
  /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/hooks/test-guardian.sh
# Expected: no output
```

- [ ] **Step 6: Smoke-test the check-in skill frontmatter**

```bash
python3 - << 'EOF'
import re
with open('/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/john-wick-checkin/SKILL.md') as f:
    content = f.read()
match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
assert match, "No frontmatter found"
assert 'name: sweetclaude:john-wick-checkin' in match.group(1)
print("Frontmatter valid")
EOF
# Expected: Frontmatter valid
```

- [ ] **Step 7: Commit sync confirmation**

```bash
git -C /Users/carsonsweet/dev/sweetclaude commit --allow-empty \
  -m "chore(john-wick): verify plan 1 building blocks synced to installed location"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by task |
|---|---|
| §7.9 Compliance context collection | Task 1 (product-discovery extension) |
| §7.1 Autonomous PRD generation mode | Task 2 (product-prd extension) |
| §7.10 Phase check-in subagent | Task 3 (john-wick-checkin skill) |
| §7.7 Compliance review — reads compliance-context.yaml | Task 4 (code-review update) |
| §8 Test file lock — cross-session locked_test_files | Task 5 (test-guardian extension) |
| Sync + verify | Task 6 |

**What this plan does NOT cover (Plan 2):**

- `skills/john-wick/SKILL.md` — the main orchestrator skill
- State machine (john-wick.yaml) — created by the orchestrator at runtime
- Prerequisites gate — embedded in the orchestrator
- §7.2 Cascade document update — embedded in orchestrator
- §7.3 Service contract analysis — embedded in orchestrator
- §7.4 GitHub Issues creation — embedded in orchestrator
- §7.5 MD test report generation — embedded in orchestrator
- §7.6 Test failure severity classifier — embedded in orchestrator
- §7.8 Caucus persona presets — defined inline in the orchestrator (passed as parameters to the caucus skill call; no separate preset file needed)
- §14 Multi-service documentation

Plan 2 must not start until every task in this plan is committed and the post-plan tests pass.

---

*Next: Plan 2 — john-wick-mode-plan2-orchestrator-2026-04-28.md (write after Plan 1 is complete)*
