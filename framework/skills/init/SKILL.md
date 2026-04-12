---
name: sweetclaude-init
description: One-command project bootstrap. Creates code repo + SweetClaude working repo, GitHub remotes, CLAUDE.md from codebase discovery, RAG index, and working repo scaffold. Use to start any new SweetClaude project.
---

# SweetClaude Project Init

Initialize a new SweetClaude project: `sweetclaude init $ARGUMENTS`

## Process

### Step 1: Create directories
```
~/dev/<project-name>/           # Code repo
~/dev/<project-name>-sweetclaude/  # Working repo
```

### Step 2: Initialize git repos
Initialize git in both directories. Set default branch to `main`.

### Step 3: Codebase discovery
If the code directory has existing files, scan for:
- **Languages:** Check file extensions, package files (package.json, pyproject.toml, go.mod, Cargo.toml, pom.xml, build.gradle)
- **Framework:** Check imports, config files (next.config.js, vite.config.ts, django settings, etc.)
- **Package manager:** npm/yarn/pnpm (check lockfiles), pip/poetry/uv, cargo, go modules
- **Test runner:** Check package.json scripts, pytest.ini, jest.config, vitest.config, go test
- **Formatter:** Check .prettierrc, pyproject.toml [tool.black], rustfmt.toml, .editorconfig
- **Build commands:** Check scripts in package.json, Makefile, pyproject.toml

If empty project, ask: "What language/framework will you use?" and scaffold defaults.

Write discovery results to `<project>-sweetclaude/state/project.yaml`:
```yaml
project:
  name: <project-name>
  language: <detected>
  framework: <detected>
  package_manager: <detected>
  test_runner: <detected>
  test_command: <detected>
  formatter: <detected>
  format_command: <detected>
  build_command: <detected>
  src_dir: <detected>
  test_dir: <detected>
```

### Step 4: Generate project CLAUDE.md
Using discovery results, generate `<project>/CLAUDE.md` with:
- What this project is (ask user for one-line description)
- Repo structure
- Build/test/lint/format commands (from discovery)
- Project-specific rules (ask user or leave placeholder)

Target: 60-100 lines. No boilerplate.

### Step 5: Scaffold working repo
Create directory structure:
```
<project>-sweetclaude/
├── state/
│   ├── phase.yaml              # Set phase to DISCOVER, work type to net-new
│   ├── project.yaml            # From codebase discovery
│   ├── decision-log.md         # Empty, with header
│   ├── assumption-register.md  # Empty, from template
│   ├── improvement-register.md # Empty, from template
│   └── scope-changes.md        # Empty, with header
├── traceability/
│   ├── requirements-map.md     # Empty, with header
│   └── ripple-map.md           # Empty, with header
├── specs/
├── stories/
├── brainstorm/
├── rag-index/
│   └── .gitkeep
└── .gitignore                  # Ignore rag-index/ if large
```

### Step 6: Initialize RAG index
If `mcp-local-rag` is available:
- Create `.mcp.json` in the working repo pointing BASE_DIR at the code repo
- Run initial index of any existing docs (README, docs/, etc.)
- Add `rag-index/` to `.gitignore` if index files are large

If `mcp-local-rag` is not available, skip with warning.

### Step 7: Push to GitHub
```bash
# Code repo
cd ~/dev/<project-name>
gh repo create <github-username>/<project-name> --private --source=. --push

# Working repo
cd ~/dev/<project-name>-sweetclaude
gh repo create <github-username>/<project-name>-sweetclaude --private --source=. --push
```

### Step 8: Optional Notion scaffold
Ask: "Want to set up a Notion workspace for this project? (y/n)"
If yes, invoke `sweetclaude:notion-scaffold`.

### Step 9: Verify
- Confirm both repos exist on GitHub
- Confirm CLAUDE.md is generated and accurate
- Confirm working repo has correct structure
- Confirm RAG index initialized (if available)

Report:
```
SweetClaude initialized for <project-name>.

Code repo:    ~/dev/<project-name> → github.com/<user>/<project-name>
Working repo: ~/dev/<project-name>-sweetclaude → github.com/<user>/<project-name>-sweetclaude
Phase:        DISCOVER
Language:     <detected>
Framework:    <detected>
Test runner:  <detected>
RAG:          <status>
Notion:       <status>
```
