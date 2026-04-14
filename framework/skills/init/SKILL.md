---
name: sweetclaude:init
description: "Project bootstrap supporting three scenarios: code repo with external strategy files, code repo without strategy files, and strategy-only projects (no code). Creates strategy/ directory structure, offers file onboarding via reconciliation, scaffolds working repo, sets up RAG. Use to start any new SweetClaude project."
---

# SweetClaude Project Init

Initialize a new SweetClaude project: `/sweetclaude:init $ARGUMENTS`

## Execution Model

This skill uses supervised step execution. YOU (the main agent) handle user interaction and decision-making. For each execution step, you spawn a subagent to do the work, then verify the subagent followed the instructions before presenting results to the user.

**Your role as supervisor:**
1. Ask the user questions (Steps 1-2)
2. For each execution step (3-10), spawn a subagent with ONLY that step's instructions
3. After each subagent completes, verify: did it do exactly what the step says? Nothing more, nothing less?
4. If the subagent deviated, discard its work and re-run with corrected instructions
5. Present the verified result to the user before moving to the next step

**You do NOT execute steps yourself.** You collect user input, delegate execution, and verify results.

---

## Step 1: Determine Scenario (YOU ask the user)

Ask: **"Do you have an existing code repo for this project?"**

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

Confirm the project directory path. Verify it's a git repo.

Ask: **"Do you have existing strategic materials to onboard? (positioning docs, research, meeting notes, strategy files — anywhere on your machine, in Claude.ai exports, Google Drive downloads, etc.)"**

- **Yes** → Scenario A. Ask where the files are.
- **No** → Scenario B.

### Scenario C: No code repo

Ask: **"Create a new repo, or work without one?"**

Record the answer. If new repo, the subagent in Step 3 will create it.

Then ask about existing strategic materials (same as A/B).

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
> Verify: list the strategy/ directory tree and confirm all 10 subdirectories exist.
> Do nothing else.

**Verify:** Subagent output shows all 10 subdirectories. No extra work was done.

---

## Step 4: Onboard Existing Strategy Files (SUBAGENT — Scenario A only)

Skip if Scenario B or C with no files.

Ask the user: **"I'll copy your files into `strategy/reconciliation/` — originals stay untouched. OK?"**

On confirmation, spawn a subagent:

> Copy all files from {source-path} into {project-path}/strategy/reconciliation/. Use:
> ```
> cp -r {source-path}/* {project-path}/strategy/reconciliation/
> ```
> Count the files copied. Report the count. Do nothing else.

**Verify:** Subagent copied files and reported count. Did not categorize, rename, or modify anything.

Tell the user: "Files copied. Run `/sweetclaude:strategy/reconciliation` to inventory and organize them."

Do NOT run reconciliation automatically.

---

## Step 5: Codebase Discovery (SUBAGENT — Scenarios A & B only)

Skip entirely for Scenario C.

Spawn a subagent:

> Scan {project-path} for the development toolchain. Check for:
> - Languages: file extensions, package files (package.json, pyproject.toml, go.mod, Cargo.toml, pom.xml, build.gradle)
> - Framework: imports, config files (next.config.js, vite.config.ts, django settings, etc.)
> - Package manager: npm/yarn/pnpm (lockfiles), pip/poetry/uv, cargo, go modules
> - Test runner: package.json scripts, pytest.ini, jest.config, vitest.config, go test
> - Formatter: .prettierrc, pyproject.toml [tool.black], rustfmt.toml, .editorconfig
> - Build commands: scripts in package.json, Makefile, pyproject.toml
>
> Report findings as a YAML block matching this schema:
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

**Verify:** Subagent reported YAML with discovery results. Did not create any files or modify anything.

Present findings to user for confirmation. If empty project, ask what language/framework they'll use.

---

## Step 6: Generate CLAUDE.md (SUBAGENT — Scenarios A & B)

Ask the user: **"One-line description of this project?"**

Then spawn a subagent:

> Generate a CLAUDE.md file for {project-path} with these sections:
> - What this is: {user's one-line description}
> - Repo structure: list key directories including strategy/
> - Build/test/lint/format commands: from these discovery results: {paste project.yaml}
> - Project-specific rules: leave a placeholder section for the user to fill
> - SweetClaude section (append at end):
>   ```
>   ## SweetClaude
>   - If the user asks to do anything involving SweetClaude workflows, invoke the sweetclaude master skill FIRST and run its pre-flight check before doing any work.
>   - If a SweetClaude working repo exists, read state/phase.yaml and state/improvement-register.md at session start.
>   - Follow the interaction model in ~/.claude/rules/sweetclaude/interaction-model.md.
>   - Respect the current deference level. Ask if not set.
>   - Never push for phase advancement.
>   ```
>
> Target: 60-100 lines. No boilerplate. Write the file to {project-path}/CLAUDE.md.

For Scenario C, instruct the subagent to generate a minimal CLAUDE.md noting this is a strategy-only project.

**Verify:** File is 60-100 lines. Has all required sections. SweetClaude section present.

Present to user for review before moving on.

---

## Step 7: Scaffold Working Repo (SUBAGENT)

Spawn a subagent:

> Create the SweetClaude working repo at {project-path}-sweetclaude. Run:
> ```
> mkdir -p {project-path}-sweetclaude
> cd {project-path}-sweetclaude
> git init
> git checkout -b main
> mkdir -p state traceability specs stories brainstorm rag-index
> touch rag-index/.gitkeep
> ```
>
> Create these files:
>
> state/phase.yaml:
> ```yaml
> phase: DISCOVER
> work_type: net-new
> deference_level: null
> project_type: {code+strategy or strategy-only}
> ```
>
> state/project.yaml: {paste discovery results from Step 5, or minimal for Scenario C}
>
> state/decision-log.md: `# Decision Log\n\n| # | Date | Phase | Decision | Rationale |\n|---|---|---|---|---|`
>
> state/assumption-register.md: `# Assumption Register\n\n| # | Assumption | Status | Evidence |\n|---|---|---|---|`
>
> state/improvement-register.md: `# Improvement Register\n\n| # | Date | Type | Learning |\n|---|---|---|---|`
>
> state/scope-changes.md: `# Scope Changes\n\n| Date | Item | Direction | Phase | Rationale |\n|---|---|---|---|---|`
>
> traceability/requirements-map.md: `# Requirements Traceability\n\n| Requirement | Story | Feature | Test | Implementation |\n|---|---|---|---|---|`
>
> traceability/ripple-map.md: `# Ripple Map\n\n| Change | Affected Files | Affected Tests | Affected Docs | Risk |\n|---|---|---|---|---|`
>
> .gitignore: `rag-index/\n.DS_Store`
>
> Verify all files exist. Do nothing else.

**Verify:** Working repo has correct directory structure and all state files.

---

## Step 8: Initialize RAG Index (SUBAGENT)

Spawn a subagent:

> Check if mcp-local-rag is available:
> ```
> npm list -g mcp-local-rag 2>/dev/null || echo "NOT_INSTALLED"
> ```
>
> If available, create {project-path}/.mcp.json:
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

Ask user: **"Push both repos to GitHub as private repos? (y/n)"**

If yes, spawn a subagent:

> Push repos to GitHub:
> ```
> cd {project-path}
> gh repo create {username}/{project-name} --private --source=. --push 2>/dev/null || git push
>
> cd {project-path}-sweetclaude
> gh repo create {username}/{project-name}-sweetclaude --private --source=. --push 2>/dev/null || git push
> ```
>
> If repos already exist on GitHub, just push. Report what happened. Do nothing else.

**Verify:** Repos pushed or already existed. No extra work.

---

## Step 10: Verify (YOU do this)

Check everything yourself — do not delegate verification:

- [ ] Project directory exists with strategy/ structure (10 subdirectories)
- [ ] CLAUDE.md exists and has SweetClaude section
- [ ] Working repo has state/, traceability/, specs/, stories/, brainstorm/, rag-index/
- [ ] state/phase.yaml exists with correct values
- [ ] state/project.yaml exists
- [ ] RAG initialized or skipped with reason
- [ ] GitHub repos exist or push skipped with reason

Report:
```
SweetClaude initialized for {project-name}.

Project:      {project-path} → {github-url or "local only"}
Working repo: {project-path}-sweetclaude → {github-url or "local only"}
Type:         {code+strategy | strategy-only}
Phase:        DISCOVER
Language:     {detected or "strategy-only"}
Framework:    {detected or "n/a"}
Test runner:  {detected or "n/a"}
Strategy:     strategy/ created, {N} files onboarded | empty
RAG:          {initialized | skipped — reason}
```

If files were onboarded: "Run `/sweetclaude:strategy/reconciliation` to inventory and organize the onboarded files."
