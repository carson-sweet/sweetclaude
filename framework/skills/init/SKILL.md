---
name: sweetclaude-init
description: "Project bootstrap supporting three scenarios: code repo with external strategy files, code repo without strategy files, and strategy-only projects (no code). Creates strategy/ directory structure, offers file onboarding via reconciliation, scaffolds working repo, sets up RAG. Use to start any new SweetClaude project."
---

# SweetClaude Project Init

Initialize a new SweetClaude project: `/sweetclaude:init $ARGUMENTS`

**IMPORTANT: Follow these steps exactly as written. Do not skip steps. Do not "fast-track." Do not propose your own modified version of this process. Do not make assumptions about what the user needs — ask them. Every step exists for a reason. If a step doesn't apply, the step itself will tell you to skip it.**

Supports three project scenarios. The init process adapts based on what already exists.

---

## Step 1: Determine Scenario

Ask: **"Do you have an existing code repo for this project?"**

| Answer | Follow-up | Scenario |
|---|---|---|
| Yes | — | A or B (determined in Step 2) |
| No | "Create a new repo, or work without one?" | C |

**Scenario A:** Code repo exists, strategy files exist elsewhere
**Scenario B:** Code repo exists, no separate strategy files
**Scenario C:** Strategy files exist, no code repo yet

---

## Step 2: Establish Project Home

### Scenario A & B: Code repo exists

```bash
cd ~/dev/<project-name>    # User's existing repo
```

Verify it's a git repo. If not, offer to `git init`.

Ask: **"Do you have existing strategic materials to onboard? (positioning docs, research, meeting notes, strategy files — anywhere on your machine, in Claude.ai exports, Google Drive downloads, etc.)"**

- **Yes** → Scenario A. Ask where the files are. Proceed to Step 3.
- **No** → Scenario B. Proceed to Step 3 (skip onboarding).

### Scenario C: No code repo

Ask: **"Create a new repo, or work without one?"**

- **New repo:**
  ```bash
  mkdir -p ~/dev/<project-name>
  cd ~/dev/<project-name>
  git init
  git checkout -b main
  ```
- **No repo:** Create a local project directory only. Warn: "Work will be unversioned."
  ```bash
  mkdir -p ~/dev/<project-name>
  ```

Then ask about existing strategic materials (same as Scenario A/B).

---

## Step 3: Create strategy/ Directory Structure

In the project directory, create:

```
<project>/
  strategy/
    concept/
    pain-thesis/
    ideal-customer-profile/
    competitive-analysis/
    academic-research/
    meeting-prep/
    narrative-arc/
    market-messaging/
    reconciliation/
      archive/
    rag-index/
```

```bash
mkdir -p strategy/{concept,pain-thesis,ideal-customer-profile,competitive-analysis,academic-research,meeting-prep,narrative-arc,market-messaging,reconciliation/archive,rag-index}
```

---

## Step 4: Onboard Existing Strategy Files (Scenario A only)

If the user has files to onboard:

1. Offer to copy them: "I'll copy your files into `strategy/reconciliation/` — originals stay untouched. OK?"
2. On confirmation:
   ```bash
   cp -r <source-path>/* strategy/reconciliation/
   ```
3. Inform the user: "Files copied. Run `/sweetclaude:strategy/reconciliation` to inventory, categorize, and optionally synthesize canonical documents from these files."

Do NOT run reconciliation automatically — it's a separate, user-driven process.

---

## Step 5: Codebase Discovery (Scenarios A & B only)

Skip this step entirely for Scenario C (strategy-only projects).

If the code directory has existing files, scan for:
- **Languages:** File extensions, package files (package.json, pyproject.toml, go.mod, Cargo.toml, pom.xml, build.gradle)
- **Framework:** Imports, config files (next.config.js, vite.config.ts, django settings, etc.)
- **Package manager:** npm/yarn/pnpm (lockfiles), pip/poetry/uv, cargo, go modules
- **Test runner:** package.json scripts, pytest.ini, jest.config, vitest.config, go test
- **Formatter:** .prettierrc, pyproject.toml [tool.black], rustfmt.toml, .editorconfig
- **Build commands:** Scripts in package.json, Makefile, pyproject.toml

If empty code project, ask: "What language/framework will you use?" and scaffold defaults.

Write discovery results to `<project>-sweetclaude/state/project.yaml`:
```yaml
project:
  name: <project-name>
  type: code+strategy | strategy-only
  language: <detected or "none">
  framework: <detected or "none">
  package_manager: <detected or "none">
  test_runner: <detected or "none">
  test_command: <detected or "none">
  formatter: <detected or "none">
  format_command: <detected or "none">
  build_command: <detected or "none">
  src_dir: <detected or "none">
  test_dir: <detected or "none">
```

---

## Step 6: Generate CLAUDE.md (Scenarios A & B)

For projects with code, generate `<project>/CLAUDE.md` with:
- What this project is (ask user for one-line description)
- Repo structure (include strategy/ in the tree)
- Build/test/lint/format commands (from discovery)
- Project-specific rules

For strategy-only projects (Scenario C), generate a minimal CLAUDE.md:
- What this project is
- strategy/ directory purpose and structure
- Note: "This is a strategy-only project. Code directories will be added if/when code work begins."

Target: 60-100 lines. No boilerplate.

---

## Step 7: Scaffold Working Repo

```bash
mkdir -p ~/dev/<project-name>-sweetclaude
cd ~/dev/<project-name>-sweetclaude
git init
git checkout -b main
```

Create directory structure:
```
<project>-sweetclaude/
├── state/
│   ├── phase.yaml
│   ├── project.yaml
│   ├── decision-log.md
│   ├── assumption-register.md
│   ├── improvement-register.md
│   └── scope-changes.md
├── traceability/
│   ├── requirements-map.md
│   └── ripple-map.md
├── specs/
├── stories/
├── brainstorm/
├── rag-index/
│   └── .gitkeep
└── .gitignore
```

Set `phase.yaml`:
```yaml
phase: DISCOVER
work_type: net-new
deference_level: null   # Will be set at session start
project_type: code+strategy | strategy-only
```

---

## Step 8: Initialize RAG Index

If `mcp-local-rag` is available:
- Create `.mcp.json` pointing BASE_DIR at the project directory
- Index existing docs: README, docs/, AND strategy/ (if files were onboarded)
- Add `rag-index/` to `.gitignore` if index files are large

If `mcp-local-rag` is not available, skip with warning.

---

## Step 9: Push to GitHub

```bash
# Code/project repo
cd ~/dev/<project-name>
gh repo create <github-username>/<project-name> --private --source=. --push

# Working repo
cd ~/dev/<project-name>-sweetclaude
gh repo create <github-username>/<project-name>-sweetclaude --private --source=. --push
```

If the repo already exists on GitHub, skip creation and just push.

---

## Step 10: Verify

Confirm:
- Project directory exists with strategy/ structure
- CLAUDE.md is generated and accurate
- Working repo has correct structure
- RAG index initialized (if available)
- GitHub repos exist (if created)

Report:
```
SweetClaude initialized for <project-name>.

Project:      ~/dev/<project-name> → github.com/<user>/<project-name>
Working repo: ~/dev/<project-name>-sweetclaude → github.com/<user>/<project-name>-sweetclaude
Type:         code+strategy | strategy-only
Phase:        DISCOVER
Language:     <detected or "strategy-only">
Framework:    <detected or "n/a">
Test runner:  <detected or "n/a">
Strategy:     strategy/ created, <N> files onboarded | empty
RAG:          <status>
```

If files were onboarded: "Run `/sweetclaude:strategy/reconciliation` to inventory and organize the onboarded files."
