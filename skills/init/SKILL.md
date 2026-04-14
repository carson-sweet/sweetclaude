---
description: "Set up SweetClaude for a project. Creates .sweetclaude/ state directory, strategy/ structure, discovers the toolchain, generates CLAUDE.md. Supports code repos, strategy-only projects, and migration from legacy working repos."
---

# SweetClaude Project Init

Set up SweetClaude for this project: `/sweetclaude:init $ARGUMENTS`

## Execution Model

YOU (the main agent) handle user interaction. For each execution step, spawn a subagent with ONLY that step's instructions. Verify each subagent's output before moving on. If a subagent deviated from instructions, discard and re-run.

**Follow these steps exactly as written. Do not skip steps. Do not "fast-track."**

---

## Step 0: Migration and Resume Check (YOU check this)

**Check for legacy working repo:**

Does `{project-path}-sweetclaude/` exist as a directory?

If yes:
> "Found an older SweetClaude setup at `{project}-sweetclaude/`. SweetClaude now stores state inside the project at `.sweetclaude/`. Migrate your existing state? The old folder stays untouched."

If user says yes, spawn a subagent:
> ```
> mkdir -p {project-path}/.sweetclaude
> cp -r {project-path}-sweetclaude/state {project-path}/.sweetclaude/ 2>/dev/null
> cp -r {project-path}-sweetclaude/traceability {project-path}/.sweetclaude/ 2>/dev/null
> ```
> Count files migrated. Do nothing else.

Report: "Migrated. Old folder untouched. Delete it when ready." Skip to Step 9 (verify).

**Check for interrupted init:**

Does `.sweetclaude/state/phase.yaml` exist with `phase: INITIALIZING`?

If yes, read `.sweetclaude/state/phase.yaml` and check the `init_step` field. Tell the user:

> "Found an interrupted SweetClaude init. It got through step {init_step}."

Use AskUserQuestion:
- "Resume" — pick up where it left off
- "Start over" — delete .sweetclaude/ and begin fresh

If resume, skip to the step after `init_step`. If start over, delete `.sweetclaude/` and continue.

If no legacy repo and no interrupted init, continue with fresh init.

---

## Step 1: Safety Snapshot (MANDATORY for existing projects)

Before SweetClaude modifies anything in a project that has existing files, create a safety branch.

**Check: is this a git repo with existing commits?**

```bash
git rev-parse --is-inside-work-tree 2>/dev/null && git log --oneline -1 2>/dev/null
```

**If yes (existing git project with history):**

Tell the user: "First, I will save a snapshot of your project by creating a `pre-sweetclaude` branch. This lets you revert everything SweetClaude adds. This step is required."

If the user agrees, spawn a subagent:
> ```
> git stash --include-untracked -m "pre-sweetclaude: stash uncommitted changes" 2>/dev/null
> git branch pre-sweetclaude 2>/dev/null || git branch pre-sweetclaude-{date}
> git stash pop 2>/dev/null
> ```
> Report: branch name created. Do nothing else.

**If the user refuses the safety snapshot, STOP. Do not proceed with init.**
> "The safety snapshot is required before modifying an existing project. Run `/sweetclaude:init` again when ready."

**If no git repo exists:**

Use AskUserQuestion:
- "Initialize git" — set up version control (recommended)
- "Continue without git" — changes cannot be undone

**If user chose "Continue without git":**
Tell the user: "Proceeding without git. All changes are permanent." Move to Step 2.

**If user chose "Initialize git":**

Use AskUserQuestion:
- "main" — use main as the default branch
- "master" — use master as the default branch

Wait for answer. Store the branch name.

Then ask a SEPARATE question:

Use AskUserQuestion with free-text input:
- "List anything that should NOT be tracked (e.g., .env, node_modules, large binaries). Leave blank for sensible defaults."

Wait for answer. Store exclusions.

Then spawn a subagent:
> Run these commands exactly:
> ```
> git init
> git checkout -b {branch_name}
> ```
> Create a .gitignore with these exclusions: {user's exclusions} plus these defaults: .DS_Store, .env, .env.*, node_modules/, dist/, build/, *.pyc, __pycache__/, .venv/, venv/, .rag-index/
> Then:
> ```
> git add -A
> git commit -m "Initial commit (pre-SweetClaude)"
> ```
> Report: branch name and commit hash. Do nothing else.

This initial commit IS the safety snapshot.

---

## Step 2: Create State Directory (SUBAGENT) — THIS HAPPENS FIRST

Before anything else, create the state directory so all subsequent steps can save their progress.

Spawn a subagent:

> Create the SweetClaude state directory at {project-path}/.sweetclaude. Run:
> ```
> mkdir -p {project-path}/.sweetclaude/{state,traceability}
> ```
>
> Create these files:
>
> .sweetclaude/state/phase.yaml:
> ```yaml
> phase: INITIALIZING
> init_step: 2
> work_type: net-new
> deference_level: null
> project_type: unknown
> safety_snapshot: {branch name from Step 1, or "none"}
> ```
>
> .sweetclaude/state/decision-log.md:
> ```
> # Decision Log
>
> | # | Date | Phase | Decision | Rationale |
> |---|---|---|---|---|
> ```
>
> .sweetclaude/state/assumption-register.md:
> ```
> # Assumption Register
>
> | # | Assumption | Status | Evidence |
> |---|---|---|---|
> ```
>
> .sweetclaude/state/improvement-register.md:
> ```
> # Improvement Register
>
> | # | Date | Type | Learning |
> |---|---|---|---|
> ```
>
> .sweetclaude/state/scope-changes.md:
> ```
> # Scope Changes
>
> | Date | Item | Direction | Phase | Rationale |
> |---|---|---|---|---|
> ```
>
> .sweetclaude/traceability/requirements-map.md:
> ```
> # Requirements Traceability
>
> | Requirement | Story | Feature | Test | Implementation |
> |---|---|---|---|---|
> ```
>
> .sweetclaude/traceability/ripple-map.md:
> ```
> # Ripple Map
>
> | Change | Affected Files | Affected Tests | Affected Docs | Risk |
> |---|---|---|---|---|
> ```
>
> Verify all files exist. Do nothing else.

**Verify:** `.sweetclaude/state/phase.yaml` exists and says `phase: INITIALIZING`.

---

## Step 3: Determine Scenario (YOU ask the user)

Use AskUserQuestion:
- "Existing code repo" — there is already code in this directory
- "New project" — starting from scratch
- "Strategy only" — strategic work, no code yet

Store the answer. Update phase.yaml:
> Set `init_step: 3` and `project_type:` based on answer.

---

## Step 4: Check for Strategy Files (YOU ask the user)

Ask: "Do you have existing strategy documents to bring in? These can be positioning docs, research, meeting notes, or strategy files from anywhere."

Wait for the answer.

If yes, ask separately: "Where are the files? Give me the directory path."

Wait for the answer. Store the source path.

Update phase.yaml: set `init_step: 4`.

---

## Step 5: Create strategy/ Directory Structure (SUBAGENT)

Spawn a subagent:

> Create the strategy/ directory structure in {project-path}. Run this exact command:
> ```
> mkdir -p strategy/{concept,pain-thesis,ideal-customer-profile,competitive-analysis,academic-research,meeting-prep,narrative-arc,market-messaging}
> ```
> Verify: list the strategy/ directory tree and confirm all subdirectories exist.
> Do nothing else.

**Verify:** Subagent output shows all subdirectories. No extra work.

Update phase.yaml: set `init_step: 5`.

---

## Step 6: Onboard Existing Strategy Files (SUBAGENT — only if user has files)

Skip if user said no files in Step 4.

Tell the user: "I will copy your files into `corpus/raw/inbox/`. Originals stay where they are."

Use AskUserQuestion:
- "Copy files" — proceed
- "Skip" — do not copy, move on

If copy, spawn a subagent:

> ```
> mkdir -p {project-path}/corpus/raw/inbox
> cp -r {source-path}/* {project-path}/corpus/raw/inbox/
> ```
> Count the files copied. Report the count. Do nothing else.

**Verify:** Subagent copied files and reported count. Did not categorize, rename, or modify anything.

Tell the user: "Files copied. Run `/sweetclaude:consolidate` to organize them."

Update phase.yaml: set `init_step: 6`.

---

## Step 7: Codebase Discovery (SUBAGENT — code projects only)

Skip for strategy-only projects.

Spawn a subagent:

> Scan {project-path} for the development toolchain. Check for:
> - Languages: file extensions, package files (package.json, pyproject.toml, go.mod, Cargo.toml)
> - Framework: imports, config files (next.config.js, vite.config.ts, django settings, etc.)
> - Package manager: npm/yarn/pnpm (lockfiles), pip/poetry/uv, cargo, go modules
> - Test runner: package.json scripts, pytest.ini, jest.config, vitest.config, go test
> - Formatter: .prettierrc, pyproject.toml [tool.black], rustfmt.toml, .editorconfig
> - Build commands: scripts in package.json, Makefile, pyproject.toml
>
> Report findings as a YAML block:
> ```yaml
> project:
>   name: {name}
>   language: {detected}
>   framework: {detected}
>   package_manager: {detected}
>   test_runner: {detected}
>   test_command: {detected}
>   formatter: {detected}
>   format_command: {detected}
>   build_command: {detected}
>   src_dir: {detected}
>   test_dir: {detected}
> ```
> Do nothing else. Do not create files. Just report.

**Verify:** Subagent reported YAML. Did not create any files.

Present findings to user for confirmation. Write confirmed results to `.sweetclaude/state/project.yaml`.

Update phase.yaml: set `init_step: 7`.

---

## Step 8: Generate CLAUDE.md (SUBAGENT)

Ask: "Describe this project in one line."

Wait for the answer.

Then spawn a subagent:

> Generate a CLAUDE.md file for {project-path} with these sections:
> - What this is: {user's one-line description}
> - Repo structure: list key directories including strategy/ and .sweetclaude/
> - Build/test/lint/format commands: from discovery results (or "strategy-only project" if no code)
> - Project-specific rules: leave a placeholder for the user to fill
> - SweetClaude section (append at end):
>   ```
>   ## SweetClaude
>   - If the user asks to do anything involving SweetClaude workflows, invoke the sweetclaude master skill FIRST and run its pre-flight check before doing any work.
>   - Read .sweetclaude/state/phase.yaml and .sweetclaude/state/improvement-register.md at session start.
>   - Follow the interaction model in ~/.claude/rules/sweetclaude/interaction-model.md.
>   - Respect the current deference level. Ask if not set.
>   - Never push for phase advancement.
>   ```
> - Distribution warning (append at end):
>   ```
>   ## Distribution Warning
>   Remove .sweetclaude/, strategy/, and corpus/ before pushing to a public repo or deploying.
>   These directories contain project strategy and internal state.
>   ```
>
> Target: 60-100 lines. Write the file to {project-path}/CLAUDE.md.

**Verify:** File exists. Has SweetClaude section. Has distribution warning.

Present to user for review before moving on.

Update phase.yaml: set `init_step: 8`.

---

## Step 9: Finalize (YOU do this)

Update `.sweetclaude/state/phase.yaml`:
```yaml
phase: DISCOVER
init_step: complete
work_type: net-new
deference_level: null
project_type: {code+strategy or strategy-only}
safety_snapshot: {branch name or "none"}
```

Check everything:

- [ ] `.sweetclaude/state/phase.yaml` exists and says `phase: DISCOVER`
- [ ] `.sweetclaude/state/project.yaml` exists (code projects) or absent (strategy-only)
- [ ] `strategy/` exists with subdirectories
- [ ] CLAUDE.md exists and has SweetClaude section and distribution warning
- [ ] No `{project}-sweetclaude/` directory was created

Report:
```
SweetClaude initialized.

Project:    {project-path}
State:      .sweetclaude/
Phase:      DISCOVER
Language:   {detected or "strategy-only"}
Strategy:   strategy/ created{, N files in corpus/raw/inbox/ | , empty}
```

If files were onboarded: "Run `/sweetclaude:consolidate` to organize them."
