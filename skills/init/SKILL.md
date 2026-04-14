---
description: "Set up SweetClaude for a project. Creates .sweetclaude/ state directory, strategy/ structure, discovers the toolchain, generates CLAUDE.md. Supports code repos, strategy-only projects, and migration from legacy working repos."
---

# SweetClaude Project Init

Set up SweetClaude for this project: `/sweetclaude:init $ARGUMENTS`

## Execution Model

YOU (the main agent) handle user interaction. For each execution step, spawn a subagent with ONLY that step's instructions. Verify each subagent's output before moving on. If a subagent deviated from instructions, discard and re-run.

**Follow these steps exactly as written. Do not skip steps. Do not "fast-track."**

---

## Step 0: Migration Check (YOU check this)

Before anything else, check if a legacy working repo exists:

```
Does {project-path}-sweetclaude/ exist as a directory?
```

If yes:
> "Found an older SweetClaude setup at `{project}-sweetclaude/`. SweetClaude now stores state inside the project at `.sweetclaude/`. Migrate your existing state? The old folder stays untouched."

If user says yes, spawn a subagent:
> ```
> mkdir -p {project-path}/.sweetclaude
> cp -r {project-path}-sweetclaude/state {project-path}/.sweetclaude/ 2>/dev/null
> cp -r {project-path}-sweetclaude/traceability {project-path}/.sweetclaude/ 2>/dev/null
> cp -r {project-path}-sweetclaude/specs {project-path}/.sweetclaude/ 2>/dev/null
> cp -r {project-path}-sweetclaude/stories {project-path}/.sweetclaude/ 2>/dev/null
> cp -r {project-path}-sweetclaude/brainstorm {project-path}/.sweetclaude/ 2>/dev/null
> ```
> Count files migrated. Do nothing else.

Report: "Migrated. Old folder untouched. Delete it when ready." Skip to Step 10 (verify).

If no legacy repo, continue with fresh init.

---

## Step 0.5: Safety Snapshot (YOU handle this — MANDATORY for existing projects)

Before SweetClaude modifies anything in a project that has existing files, create a safety branch so the user can revert completely.

**Check: is this a git repo with existing commits?**

```bash
git rev-parse --is-inside-work-tree 2>/dev/null && git log --oneline -1 2>/dev/null
```

**If yes (existing git project with history):**

> "First, I will save a snapshot of your project by creating a `pre-sweetclaude` branch. This lets you revert everything SweetClaude adds. This step is required."

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

> "This directory does not have git. SweetClaude works best with version control. Initialize a git repo here?"

If yes:
> - Ask: "What should the default branch be called?" (suggest `main`)
> - Then ask: "Anything in this directory that should NOT be tracked? (Examples: .env files, large binaries, node_modules)"
> - Spawn a subagent to: `git init`, `git checkout -b {branch}`, create `.gitignore` with user's exclusions + sensible defaults, `git add -A`, `git commit -m "Initial commit (pre-SweetClaude)"`
> - This initial commit IS the safety snapshot.

If no (user does not want git):
> "SweetClaude can work without git. But there is no way to undo changes. All SweetClaude modifications will be permanent. Continue without git?"
> If they confirm, proceed without snapshot. Flag in phase.yaml: `safety_snapshot: none`.

---

## Step 1: Determine Scenario (YOU ask the user)

Use AskUserQuestion: **"Does this project have an existing code repo?"**

| Answer | Follow-up | Scenario |
|---|---|---|
| Yes | — | A or B (determined in Step 2) |
| No | "Create a new repo, or work without one?" | C |

**Scenario A:** Code repo exists, strategy files exist elsewhere
**Scenario B:** Code repo exists, no separate strategy files
**Scenario C:** Strategy files exist, no code repo yet

---

## Step 2: Establish Project Home (YOU ask the user)

### Scenario A & B: Code repo exists

Confirm the project directory path. Verify it is a git repo.

Ask: **"Do you have existing strategy documents to bring in? These can be positioning docs, research, meeting notes, or strategy files from anywhere — your machine, Claude.ai exports, Google Drive downloads."**

- **Yes** → Scenario A. Ask where the files are.
- **No** → Scenario B.

### Scenario C: No code repo

Use AskUserQuestion with these options:
- "Create a new repo" — start with a fresh git repository
- "Work without one" — no version control

Record the answer. If new repo, the subagent in Step 3 will create it.

Then ask about existing strategy documents (same as A/B).

---

## Step 3: Create strategy/ Directory Structure (SUBAGENT)

Spawn a subagent with these exact instructions:

> Create the strategy/ directory structure in {project-path}. Run this exact command:
> ```
> mkdir -p strategy/{concept,pain-thesis,ideal-customer-profile,competitive-analysis,academic-research,meeting-prep,narrative-arc,market-messaging,reconciliation/archive,rag-index}
> ```
> If Scenario C and user wants a new repo, first create the repo:
> ```
> mkdir -p {project-path} && cd {project-path} && git init && git checkout -b main
> ```
> Verify: list the strategy/ directory tree and confirm all subdirectories exist.
> Do nothing else.

**Verify:** Subagent output shows all subdirectories. No extra work was done.

---

## Step 4: Onboard Existing Strategy Files (SUBAGENT — Scenario A only)

Skip if Scenario B or C with no files.

Ask the user: **"I will copy your files into `strategy/reconciliation/`. Originals stay where they are. OK?"**

On confirmation, spawn a subagent:

> Copy all files from {source-path} into {project-path}/strategy/reconciliation/. Use:
> ```
> cp -r {source-path}/* {project-path}/strategy/reconciliation/
> ```
> Count the files copied. Report the count. Do nothing else.

**Verify:** Subagent copied files and reported count. Did not categorize, rename, or modify anything.

Tell the user: "Files copied. Run `/sweetclaude:strategy/reconciliation` to organize them."

Do NOT run reconciliation automatically.

---

## Step 5: Codebase Discovery (SUBAGENT — Scenarios A & B only)

Skip entirely for Scenario C.

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

**Verify:** Subagent reported YAML with discovery results. Did not create any files.

Present findings to user for confirmation.

---

## Step 6: Generate CLAUDE.md (SUBAGENT — Scenarios A & B)

Ask: **"Describe this project in one line."**

Then spawn a subagent:

> Generate a CLAUDE.md file for {project-path} with these sections:
> - What this is: {user's one-line description}
> - Repo structure: list key directories including strategy/ and .sweetclaude/
> - Build/test/lint/format commands: from discovery results
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
>
> Target: 60-100 lines. Write the file to {project-path}/CLAUDE.md.

For Scenario C, instruct the subagent to generate a minimal CLAUDE.md noting this is a strategy-only project.

**Verify:** File is 60-100 lines. Has all required sections. SweetClaude section present.

Present to user for review before moving on.

---

## Step 7: Create .sweetclaude/ State Directory (SUBAGENT)

Spawn a subagent:

> Create the SweetClaude state directory at {project-path}/.sweetclaude. Run:
> ```
> mkdir -p {project-path}/.sweetclaude/{state,traceability,specs,stories,brainstorm}
> ```
>
> Create these files:
>
> .sweetclaude/state/phase.yaml:
> ```yaml
> phase: DISCOVER
> work_type: net-new
> deference_level: null
> project_type: {code+strategy or strategy-only}
> ```
>
> .sweetclaude/state/project.yaml: {paste discovery results from Step 5, or minimal for Scenario C}
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

**Verify:** .sweetclaude/ has state/, traceability/, specs/, stories/, brainstorm/ and all state files.

---

## Step 8: Initialize RAG Index (SUBAGENT)

Spawn a subagent:

> Check if mcp-local-rag is available:
> ```
> npm list -g mcp-local-rag 2>/dev/null || echo "NOT_INSTALLED"
> ```
>
> If available, create {project-path}/.mcp.json (or merge into existing):
> ```json
> {
>   "mcpServers": {
>     "local-rag": {
>       "command": "npx",
>       "args": ["-y", "mcp-local-rag"],
>       "env": {
>         "BASE_DIR": ".",
>         "DB_PATH": "./.rag-index/lancedb",
>         "CACHE_DIR": "./.rag-index/models"
>       }
>     }
>   }
> }
> ```
>
> Add `.rag-index/` to .gitignore if not already present.
>
> If NOT available, report: "mcp-local-rag not installed. RAG skipped."
> Do nothing else.

**Verify:** Either .mcp.json created correctly, or skip reported. No extra work.

---

## Step 9: Push to GitHub (SUBAGENT)

Ask: **"Push to GitHub as a private repo?"**

If yes, spawn a subagent:

> Push the project repo to GitHub:
> ```
> cd {project-path}
> git add -A
> git commit -m "SweetClaude init: project scaffolding
>
> Co-Authored-By: SweetClaude <noreply@sweetclaude.dev>"
> gh repo create {username}/{project-name} --private --source=. --push 2>/dev/null || git push
> ```
>
> If repo already exists on GitHub, just push. Report what happened. Do nothing else.

**Verify:** One repo pushed. No second repo created.

---

## Step 10: Verify (YOU do this)

Check everything yourself:

- [ ] `.sweetclaude/` exists with state/, traceability/, specs/, stories/, brainstorm/
- [ ] `.sweetclaude/state/phase.yaml` exists with correct values
- [ ] `.sweetclaude/state/project.yaml` exists
- [ ] `strategy/` exists with subdirectories
- [ ] CLAUDE.md exists and has SweetClaude section
- [ ] RAG initialized or skipped with reason
- [ ] GitHub pushed or skipped with reason
- [ ] No `{project}-sweetclaude/` directory was created (unless migration)

Report:
```
SweetClaude initialized for {project-name}.

Project:    {project-path} → {github-url or "local only"}
State:      {project-path}/.sweetclaude/
Phase:      DISCOVER
Language:   {detected or "strategy-only"}
Framework:  {detected or "n/a"}
Test runner: {detected or "n/a"}
Strategy:   strategy/ created, {N} files onboarded | empty
RAG:        {initialized | skipped — reason}
```

If files were onboarded: "Run `/sweetclaude:strategy/reconciliation` to organize them."
