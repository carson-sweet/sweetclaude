---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:adopt
user-invocable: false
description: "Drop SweetClaude into a messy, vibe-coded, or inherited codebase through ASSESS → DIAGNOSE → PLAN → SCAFFOLD → ITERATE. Treats the codebase as an archaeological site — nothing deleted or overwritten without explicit consent. Heavier-weight than sweetclaude:on for complex existing projects."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Adopt

Five-stage guided adoption for existing codebases. Assess what's there, diagnose health, plan remediation, scaffold infrastructure, hand off to the normal pipeline.

---

## Step 1: Guards

Check for `.sweetclaude/disabled`:
```bash
ls .sweetclaude/disabled 2>/dev/null && echo "DISABLED" || echo "OK"
```
If `DISABLED`: warn "SweetClaude is disabled for this project (`.sweetclaude/disabled` exists). Remove it to proceed." Stop.

Check for `.sweetclaude/state/phase.yaml`:
```bash
ls .sweetclaude/state/phase.yaml 2>/dev/null && echo "CONFIGURED" || echo "FRESH"
```
If `CONFIGURED`: stop immediately.
> "SweetClaude is already configured here. Run `/sweetclaude:status` to see progress, or `/sweetclaude:on` to re-run setup."

Check for existing code (rule out empty projects):
```bash
find . -maxdepth 3 -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" -o -name "*.rs" -o -name "*.rb" -o -name "*.java" 2>/dev/null | grep -v node_modules | grep -v ".git" | head -1
```
If no code files found at all, redirect:
> "This looks like an empty project. Use `/sweetclaude:on` instead — it handles new projects."

---

## Step 2: ASSESS — Codebase scan

Run in one block. This is purely read-only — no writes yet.

```bash
echo "=== LANGUAGES + FRAMEWORK ==="
ls package.json pyproject.toml Cargo.toml go.mod pom.xml build.gradle Gemfile requirements.txt 2>/dev/null
find . -maxdepth 4 -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" -o -name "*.rs" -o -name "*.rb" -o -name "*.java" 2>/dev/null | grep -v node_modules | grep -v ".git" | wc -l
find . -maxdepth 3 -name "next.config*" -o -name "vite.config*" -o -name "webpack.config*" -o -name "django*" -o -name "fastapi*" 2>/dev/null | grep -v node_modules | head -5

echo "=== TEST FRAMEWORK ==="
ls jest.config* vitest.config* pytest.ini setup.cfg .pytest.ini Makefile 2>/dev/null
find . -maxdepth 4 \( -name "*.test.*" -o -name "*.spec.*" -o -name "test_*.py" -o -name "*_test.go" \) 2>/dev/null | grep -v node_modules | grep -v ".git" | wc -l
cat package.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); s=d.get('scripts',{}); print({k:v for k,v in s.items() if 'test' in k.lower() or 'spec' in k.lower()})" 2>/dev/null || true

echo "=== CI/CD ==="
ls .github/workflows/ 2>/dev/null | head -5
ls .circleci/ Jenkinsfile .travis.yml 2>/dev/null

echo "=== DOCUMENTATION ==="
ls README.md README.rst README.txt CLAUDE.md 2>/dev/null
ls docs/ 2>/dev/null | head -10
find . -maxdepth 3 -name "ADR-*.md" -o -name "adr-*.md" -o -name "*.adr.md" 2>/dev/null | grep -v node_modules | head -5
find . -maxdepth 3 -name "ARCHITECTURE.md" -o -name "architecture.md" -o -name "DESIGN.md" 2>/dev/null | head -3

echo "=== PROJECT MANAGEMENT ==="
ls .sweetclaude/ docs/backlog/ .github/ISSUE_TEMPLATE/ 2>/dev/null | head -5
git log --oneline -5 2>/dev/null || echo "NO_GIT"
git status --short 2>/dev/null | head -10

echo "=== DEPENDENCIES ==="
cat package.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); deps=d.get('dependencies',{}); dev=d.get('devDependencies',{}); print(f'{len(deps)} runtime deps, {len(dev)} dev deps')" 2>/dev/null || true
cat requirements.txt 2>/dev/null | wc -l || true
grep -c "^[a-zA-Z]" pyproject.toml 2>/dev/null || true

echo "=== SECURITY SURFACE ==="
grep -rn "SECRET\|API_KEY\|PASSWORD\|TOKEN\|PRIVATE_KEY" . --include="*.py" --include="*.ts" --include="*.js" --include="*.go" --include="*.rb" --include="*.java" --include="*.env" 2>/dev/null | grep -v node_modules | grep -v ".git" | grep -v "test\|spec\|mock\|example\|template\|sample" | grep -v "#\|//.*SECRET\|//.*TOKEN" | head -10
ls .env .env.local .env.production 2>/dev/null
cat .gitignore 2>/dev/null | grep -i "\.env\|secret\|key\|cred" | head -5
```

Organize findings into five categories. Present factually — no recommendations yet:

**Code:** language(s), framework(s), file count, test file count, CI/CD scripts present (y/n)
**Documentation:** README present (y/n), docs/ contents, ADRs found, architecture docs
**Project management:** git history (commits), open work tracked (y/n)
**Dependencies:** runtime count, dev count
**Security surface:** any pattern matches (flag as "needs review" — do not assert a vulnerability), .env files present (y/n), .env in .gitignore (y/n)

---

## Step 3: DIAGNOSE — Health report

Categorize findings from Step 2 into four severity buckets. Present to user. Do not write to files yet.

| Severity | Criteria |
|---|---|
| **Critical** | Potential secrets in committed code, .env not gitignored, no git repo |
| **High** | No test framework detected, broken CI, no README |
| **Medium** | < 20% test coverage indicators, inconsistent patterns, undocumented decisions |
| **Low** | Minor debt, style issues, old dependency versions |

**Security findings are always Critical.** If any Critical findings exist, surface them prominently:
> "I found Critical findings that should be addressed before we set up SweetClaude. Here's why: the `pre-sweetclaude` safety branch would snapshot these issues into git. Let's address them first."

List the Critical items and ask:
> "Would you like to address these now before continuing? (Recommended: yes)"

If user declines to address Criticals: warn clearly, then proceed only with explicit user confirmation "I understand the risks, proceed anyway."

Present the full health report: Critical → High → Medium → Low.

Ask exactly one question before proceeding to PLAN:
> "Does this diagnosis look accurate? Anything I got wrong?"

Incorporate corrections. Then:
> "Ready to see the remediation plan?"

Wait for yes.

---

## Step 4: PLAN — Remediation plan

Build a prioritized plan from DIAGNOSE findings. Order is fixed:

1. **Stabilize** — Critical and security findings (addresses first)
2. **Lock behavior** — Write tests for code that will be changed (before touching anything)
3. **Document** — Capture undocumented patterns before knowledge is lost
4. **Refactor** — Tech debt after the above is in place

Each item gets:
- A one-line description
- Severity: Critical / High / Medium / Low
- The SweetClaude skill to invoke: `sweetclaude:code-testing`, `sweetclaude:code-debt`, `sweetclaude:document-corpus`, etc.

If more than 10 items: bucket them:
- **Start this week** — Critical + High items
- **This month** — Medium items
- **Backlog** — Low items

Present plan to user. Ask:
> "Does this plan look right? Anything to add, drop, or reprioritize?"

Incorporate feedback. Ask:
> "Ready to scaffold SweetClaude infrastructure?"

Wait for yes.

---

## Step 5: SCAFFOLD — Infrastructure setup

**Do not write any files until the safety snapshot is in place.**

### 5a: Git check and safety snapshot

```bash
git rev-parse --git-dir 2>/dev/null && echo "GIT_PRESENT" || echo "NO_GIT"
git branch --show-current 2>/dev/null
```

If no git:
> "No git repository found. The safety snapshot is required before I modify anything — it gives you a rollback point. Run `git init && git add -A && git commit -m 'initial commit'` then run `/sweetclaude:adopt` again."
Stop.

If git present, check for existing snapshot:
```bash
git branch --list pre-sweetclaude
```

If no `pre-sweetclaude` branch:
> "I'm going to create a `pre-sweetclaude` branch as a rollback point before writing any files. This is required."

If user declines:
> "The safety snapshot is required before modifying an existing project. Run `/sweetclaude:adopt` again when ready."
Stop.

```bash
git branch pre-sweetclaude
echo "SNAPSHOT_CREATED"
```

### 5b: Create infrastructure

```bash
mkdir -p .sweetclaude/state
mkdir -p .sweetclaude/traceability
mkdir -p strategy/{competitive-analysis,market-messaging,meeting-prep,narrative-arc,academic-research}
```

Create each file only if it does not already exist. Skip and report any that exist.

**`.sweetclaude/state/phase.yaml`** — ask two questions first:

> "What version stage is this project at? (PRE-ALPHA / ALPHA / BETA / GA)"

> "How collaborative should I be? Collaborative (stop after every sub-step), Guided (stop at major decisions), or Autonomous (stop only at phase gates)?"

```yaml
# .sweetclaude/state/phase.yaml
schema_version: 2

version_stage: {user answer}
deference_level: {user answer}
project_type: existing-code
safety_snapshot: pre-sweetclaude
last_work_item_id: ~

active_work_item:
  id: ~
  type: ~
  workflow: []
  phase: ~
  title: ~
  started: ~
  entry_category: ~
```

**`.sweetclaude/state/skills.yaml`:**
```yaml
schema_version: 2
```

**`.sweetclaude/state/decision-log.md`:**
```markdown
# Decision Log

| # | Date | Decision | Rationale | Alternatives considered |
|---|---|---|---|---|
| 1 | {today} | Adopted SweetClaude via sweetclaude:adopt | [retroactive] Existing project; chose adopt over on for full ASSESS+DIAGNOSE | sweetclaude:on (lighter-weight, skips health assessment) |
```

**`.sweetclaude/state/assumption-register.md`:**
```markdown
# Assumption Register

| # | Date | Assumption | Risk if wrong | Validation plan |
|---|---|---|---|---|
```
(Populate from scan findings if any assumptions were surfaced — e.g., "Test suite provides adequate regression coverage")

**`.sweetclaude/state/improvement-register.md`:**
```markdown
# Improvement Register

| # | Date | Type | Learning |
|---|---|---|---|
```

**`.sweetclaude/state/scope-changes.md`:**
```markdown
# Scope Changes

| # | Date | Change | Reason | Impact |
|---|---|---|---|---|
```

**`.sweetclaude/traceability/requirements-map.md`:**
```markdown
# Requirements Traceability Map

| Requirement | User Story | Test | Status |
|---|---|---|---|
```

**`.sweetclaude/traceability/ripple-map.md`:**
```markdown
# Ripple Map

| Change | Affected areas | Risk level |
|---|---|---|
```

### 5c: CLAUDE.md

```bash
ls CLAUDE.md 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

**If EXISTS:**
Present only the SweetClaude section for addition — do not show or overwrite the full file:
> "CLAUDE.md already exists. I'd like to add this SweetClaude section to the bottom. Approve?"

Proposed addition:
```markdown
## SweetClaude

- Read `.sweetclaude/state/phase.yaml` and `.sweetclaude/state/improvement-register.md` at session start if they exist. If `.sweetclaude/state/phase.yaml` exists and `.sweetclaude/disabled` does not exist, invoke `sweetclaude:status` automatically at session start.
- Follow the interaction model in `~/.claude/rules/sweetclaude/interaction-model.md`.
- Respect the current deference level. Ask if not set.
- Never push for phase advancement. The user decides when to move on.
```

Write only after explicit approval.

**If MISSING:**
Use toolchain findings from Step 2 to generate CLAUDE.md. Present before writing.

```markdown
# {project name or directory name}

{one-line description from README or user}

## Key directories

{populated from scan}

## Commands

```bash
# Install
{detected install command or: # TODO: add install command}

# Test
{detected test command or: # TODO: add test command}

# Build
{detected build command or: # TODO: add build command}
```

## Project-specific rules

- {Add your rules here}

## SweetClaude

- Read `.sweetclaude/state/phase.yaml` and `.sweetclaude/state/improvement-register.md` at session start if they exist. If `.sweetclaude/state/phase.yaml` exists and `.sweetclaude/disabled` does not exist, invoke `sweetclaude:status` automatically at session start.
- Follow the interaction model in `~/.claude/rules/sweetclaude/interaction-model.md`.
- Respect the current deference level. Ask if not set.
- Never push for phase advancement. The user decides when to move on.
```

Write only after explicit approval.

### 5d: Run session state

```bash
bash ~/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/hooks/generate-session-state.sh 2>/dev/null || \
bash "$(git rev-parse --show-toplevel 2>/dev/null)/hooks/generate-session-state.sh" 2>/dev/null || \
echo "SESSION_STATE_SKIPPED"
```

---

## Step 6: ITERATE — Handoff

Write remediation plan from Step 4 to `.sweetclaude/state/remediation-plan.md`:

```markdown
# Remediation Plan
Generated: {date}
Source: sweetclaude:adopt — health assessment

## Start this week
{Critical + High items, each linked to skill}

## This month
{Medium items}

## Backlog
{Low items}
```

Create backlog items in `.sweetclaude/product/backlog/` (one per Critical and High item, named `ADOPT-{n}-{slug}.md`):

```markdown
---
id: ADOPT-{n}
title: {item description}
severity: {Critical|High}
type: tech-debt
source: sweetclaude:adopt health assessment
---

{one-paragraph description from the diagnosis}
```

Present final summary:

> "SweetClaude adoption complete.
>
> **Project:** {name}
> **Version stage:** {version_stage}
> **Deference:** {deference_level}
> **Safety branch:** `pre-sweetclaude` (rollback point)
>
> **Remediation plan:**
> - {N} Critical/High items → Start this week
> - {N} Medium items → This month
> - {N} Low items → Backlog
>
> {If Critical items remain unaddressed}
> **⚠ Critical items still open:** {list them}. Address these before making any code changes.
>
> **Next:** Run `/sweetclaude:find-skill` to start your first work item, or `/sweetclaude:status` to review the project state."

---

## Rules

- **Never touch `src/`, `app/`, `lib/`, `tests/`, or any application code directory.** Only create files in `.sweetclaude/`, `strategy/`, and CLAUDE.md.
- **Safety snapshot is mandatory.** If user declines, stop. No exceptions.
- **Secrets block SCAFFOLD.** If Critical security findings exist and user has not addressed them, warn clearly before proceeding. Do not soft-pedal.
- **CLAUDE.md changes require explicit approval.** Present the proposed change; write only on yes.
- **No architectural rewrites.** `adopt` documents what exists; it does not propose starting over.
- **Diagnosis is presented, not auto-written.** The health report is for the user; it is not persisted unless explicitly requested.
- **Never skip stages.** ASSESS → DIAGNOSE → PLAN → SCAFFOLD → ITERATE. No shortcuts.
- **One question at a time** during DIAGNOSE and PLAN stages.
- **If `.sweetclaude/disabled` exists:** warn and stop at Step 1.
