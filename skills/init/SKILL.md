---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Bootstrap the SweetClaude infrastructure for any project — new or existing."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:init" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Init

Infrastructure bootstrap. One job: create the `.sweetclaude/` state directory, strategy structure, and CLAUDE.md. Nothing more.

---

## Step 1: Already configured?

Check whether `.sweetclaude/state/phase.yaml` exists.

**If it exists:**
```bash
cat .sweetclaude/state/phase.yaml | grep -E "schema_version|version_stage|phase:" | head -5
```
Report:
> "This project is already configured for SweetClaude (phase.yaml exists). Nothing to do.
> Run `/sweetclaude:status` to see where things stand, or `/sweetclaude:setup` to re-run the full setup."

Stop.

**If it does not exist:** proceed to Step 2.

---

## Step 2: Interrupted init?

Check for a partial init:
```bash
ls .sweetclaude/state/ 2>/dev/null | head -10
```

If `.sweetclaude/state/` exists but `phase.yaml` is missing, say:
> "Found a partial `.sweetclaude/state/` directory — looks like a previous init was interrupted. Resuming from where it left off."

Note which files already exist (skip creating them in Step 4).

---

## Step 3: Project type

Ask exactly one question:

> "New project or existing project?
> - **New:** Starting from scratch — I'll create state files, strategy structure, and a CLAUDE.md.
> - **Existing:** Code already exists — I'll also scan for your toolchain and add it to CLAUDE.md."

Wait for answer. Accept: "new", "existing", "n", "e", or any clear variant.

---

## Step 4: Create infrastructure

Run in one bash block:

```bash
# State directory
mkdir -p .sweetclaude/state
mkdir -p .sweetclaude/traceability

# Strategy structure
mkdir -p strategy/{competitive-analysis,market-messaging,meeting-prep,narrative-arc,academic-research}
```

Create these files if they do not already exist (skip any that were found in Step 2):

**`.sweetclaude/state/phase.yaml`:**
```yaml
# .sweetclaude/state/phase.yaml
# SweetClaude phase state — schema version 2
schema_version: 2

version_stage: PRE-ALPHA
deference_level: collaborative
project_type: ~
safety_snapshot: ~
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
# .sweetclaude/state/skills.yaml
# SweetClaude skills state — schema version 2
schema_version: 2
```

**`.sweetclaude/state/decision-log.md`:**
```markdown
# Decision Log

| # | Date | Decision | Rationale | Alternatives considered |
|---|---|---|---|---|
```

**`.sweetclaude/state/assumption-register.md`:**
```markdown
# Assumption Register

| # | Date | Assumption | Risk if wrong | Validation plan |
|---|---|---|---|---|
```

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

Report each file as created or skipped (already existed).

---

## Step 5: Toolchain detection (existing projects only)

Skip this step for new projects.

Run:
```bash
# Language / runtime detection
ls package.json pyproject.toml Cargo.toml go.mod pom.xml build.gradle Gemfile 2>/dev/null
# Test runner
cat package.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('scripts',{}))" 2>/dev/null || true
ls pytest.ini setup.cfg .pytest.ini Makefile 2>/dev/null
# Build commands
grep -r "\"test\"\|\"build\"\|\"dev\"\|\"start\"" package.json 2>/dev/null | head -5 || true
```

Use findings to populate CLAUDE.md with real commands instead of placeholders.

---

## Step 6: Generate CLAUDE.md

Check if `CLAUDE.md` already exists:
```bash
ls CLAUDE.md 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

**If EXISTS:** skip generation. Tell user: "CLAUDE.md already exists — leaving it untouched."

**If MISSING:** generate and present before writing.

For **new projects** — ask one question first:
> "One line about the project (used in CLAUDE.md):"

For **existing projects** — use toolchain findings from Step 5.

CLAUDE.md template:
```markdown
# {Project name or directory name}

{One-line description}

## Key directories

- `src/` — source code
- `tests/` — test suite

## Commands

```bash
# Install
{install command or: # TODO: add install command}

# Test
{test command or: # TODO: add test command}

# Build
{build command or: # TODO: add build command}
```

## Project-specific rules

- {Add your rules here}

## SweetClaude

- Read `.sweetclaude/state/phase.yaml` and `.sweetclaude/state/improvement-register.md` at session start if they exist. If `.sweetclaude/state/phase.yaml` exists and `.sweetclaude/disabled` does not exist, invoke `sweetclaude:status` automatically at session start.
- Follow the interaction model in `~/.claude/rules/sweetclaude/interaction-model.md`.
- Respect the current deference level. Ask if not set.
- Never push for phase advancement. The user decides when to move on.
```

Present to user. Write only after confirmation (or immediately if deference is `autonomous`).

---

## Step 7: Git safety snapshot (existing projects only)

Skip for new projects.

```bash
git rev-parse --git-dir 2>/dev/null && echo "GIT_PRESENT" || echo "NO_GIT"
git branch --show-current 2>/dev/null
```

If git is present and no `pre-sweetclaude` branch exists:
```bash
git branch pre-sweetclaude 2>/dev/null && echo "SNAPSHOT_CREATED" || echo "SNAPSHOT_EXISTS"
```

Tell user: "Created `pre-sweetclaude` branch as a rollback point."

If no git: "No git repository found. Consider running `git init` to get version control before going further."

---

## Step 7b: Claude config audit (existing projects only)

Skip for new projects (no CLAUDE.md to scan yet).

For existing projects, scan for instructions in the existing CLAUDE.md that conflict with SweetClaude, before SweetClaude starts relying on those files:

Invoke `sweetclaude:claude-config-audit` via the Skill tool.

If no conflicts are found, proceed immediately. If FATAL conflicts are found, resolve them before proceeding to Step 8 — a FATAL conflict will prevent SweetClaude hooks from functioning.

---

## Step 8: Run generate-session-state

```bash
bash ~/.claude/hooks/sweetclaude/generate-session-state.sh 2>/dev/null || \
bash "$(git rev-parse --show-toplevel 2>/dev/null)/hooks/generate-session-state.sh" 2>/dev/null || \
echo "SESSION_STATE_SKIPPED"
```

---

## Step 9: Close

Report:

```
════════════════════════════════════
SweetClaude Initialized
════════════════════════════════════
```

> "SweetClaude initialized.
>
> Created:
> - `.sweetclaude/state/` — phase, skills, decision log, assumption register, improvement register, scope changes
> - `.sweetclaude/traceability/` — requirements map, ripple map
> - `strategy/` — competitive-analysis, market-messaging, meeting-prep, narrative-arc, academic-research
> {- CLAUDE.md (if created)}
> {- `pre-sweetclaude` git branch (if existing project)}
>
> Next: Run `/sweetclaude:setup` to start a product discovery session, or jump straight to `/sweetclaude:go` if you already know what you're building."

---

## Rules

- Never overwrite files that already exist — skip and report.
- Never run product discovery — that is `sweetclaude:setup`'s job.
- Ask project type once; do not re-ask.
- For CLAUDE.md: present before writing (unless autonomous deference).
- If `.sweetclaude/disabled` exists: warn "SweetClaude is disabled for this project (`.sweetclaude/disabled` exists). Remove it to proceed." Stop.
