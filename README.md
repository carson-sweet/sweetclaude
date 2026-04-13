# SweetClaude

A Claude Code framework for solo developers who want disciplined, end-to-end development — from concept to deployed, tested code — with AI as a creative partner, not a passive tool.

SweetClaude combines the best of [Superpowers](https://github.com/obra/superpowers) (dev mechanics), [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) (product lifecycle), and purpose-built skills into a single phase-gated pipeline with hook-enforced TDD, Gherkin-based test contracts, and an interaction model designed around human-AI creative partnership.

## What It Does

- **7-phase pipeline:** Discover, Define, Design, Plan, Implement, Verify, Ship — with quality gates, not time gates
- **Work-type routing:** Bug fixes, enhancements, iterations, and net-new features each enter the pipeline at the right phase
- **Hook-enforced TDD:** Four levels (Hotfix, Light, Standard, Full). Test files are physically blocked from modification during implementation. Tests run automatically after every source edit.
- **Gherkin bridge:** BMAD user stories become `.feature` files that drive test generation via isolated subagents
- **Context-isolated subagents:** Test writer and implementer work in separate contexts — the implementer never sees the spec, only the tests
- **Dual context window management:** Manages Claude's token limits AND your cognitive load — deference levels, detour tracking, re-orientation, decision logs
- **Creative partnership:** Proposes and challenges rather than asking and waiting. Follows your lead. Never pushes for phase advancement.
- **Ripple-effect analysis:** Before changing anything, traces what's affected across code, tests, docs, and specs
- **RAG-powered knowledge:** Per-project semantic search over your document corpus
- **One-command bootstrap:** `sweetclaude init` creates code repo + working repo, GitHub remotes, CLAUDE.md from codebase discovery, and RAG index

## Prerequisites

| Dependency | Minimum Version | Check | Install |
|---|---|---|---|
| [Claude Code CLI](https://claude.ai/code) | any | `claude --version` | [Install guide](https://docs.anthropic.com/en/docs/claude-code/getting-started) |
| Git | any | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| [GitHub CLI](https://cli.github.com/) | any | `gh --version` | `brew install gh` or [cli.github.com](https://cli.github.com/) |
| [Superpowers](https://github.com/obra/superpowers) | 5.0.7+ | `/plugins` in Claude Code | `/install superpowers` in Claude Code |
| [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) | 6.0.0+ | Check `~/.claude/skills/bmad/` exists | See [BMAD install docs](https://github.com/bmad-code-org/BMAD-METHOD#installation) |

The installer checks all of the above and warns if anything is missing or outdated.

## Install

### macOS (automated)

The install script is macOS only. It handles prereq checks, backups, conflict cleanup, and generates an uninstaller.

```bash
git clone https://github.com/carson-sweet/sweetclaude.git
cd sweetclaude
./install.sh
```

The installer:
- Validates all prerequisites and versions
- Copies framework files to `~/.claude/skills/sweetclaude/`, `hooks/`, `agents/`, `rules/`, `config/`
- Appends a SweetClaude section to `~/CLAUDE.md` (or creates it from a template if none exists)
- Prints hook configuration to add to `~/.claude/settings.json`
- Backs up superseded skills and offers to remove them
- Generates `restore-config.sh` to undo all changes and `uninstall.sh` to remove SweetClaude

Your existing `~/CLAUDE.md` and `~/.claude/settings.json` are backed up before any modifications.

### Linux (manual)

Claude Code on Linux uses the same `~/.claude/` config path as macOS. The install script may work but is untested — manual install is recommended.

```bash
git clone https://github.com/carson-sweet/sweetclaude.git
cd sweetclaude

# Copy framework files
cp -r framework/skills/* ~/.claude/skills/sweetclaude/
cp -r framework/hooks/* ~/.claude/hooks/sweetclaude/
cp -r framework/agents/* ~/.claude/agents/sweetclaude/
cp -r framework/rules/* ~/.claude/rules/sweetclaude/
cp -r framework/config/* ~/.claude/config/sweetclaude/
chmod +x ~/.claude/hooks/sweetclaude/*.sh
```

Then add the SweetClaude section to your `~/CLAUDE.md` (create the file if it doesn't exist):

```markdown
## SweetClaude

- If a SweetClaude working repo exists for the current project, read `state/phase.yaml` and `state/improvement-register.md` at session start.
- Follow the interaction model in `~/.claude/rules/sweetclaude/interaction-model.md`.
- Respect the current deference level. Ask if not set.
- Never push for phase advancement. The user decides when to move on.
```

### Windows (manual)

Claude Code on Windows uses `%USERPROFILE%\.claude\` (typically `C:\Users\<you>\.claude\`).

```powershell
git clone https://github.com/carson-sweet/sweetclaude.git
cd sweetclaude

# Copy framework files
Copy-Item -Recurse framework\skills\* $env:USERPROFILE\.claude\skills\sweetclaude\
Copy-Item -Recurse framework\hooks\* $env:USERPROFILE\.claude\hooks\sweetclaude\
Copy-Item -Recurse framework\agents\* $env:USERPROFILE\.claude\agents\sweetclaude\
Copy-Item -Recurse framework\rules\* $env:USERPROFILE\.claude\rules\sweetclaude\
Copy-Item -Recurse framework\config\* $env:USERPROFILE\.claude\config\sweetclaude\
```

Then add the same SweetClaude section (shown above under Linux) to your `%USERPROFILE%\CLAUDE.md`.

**Note:** The `.sh` hook scripts in `hooks/sweetclaude/` require a bash-compatible shell (Git Bash, WSL). If you run Claude Code from PowerShell or cmd without WSL, the hooks will not execute — SweetClaude will still work but without TDD enforcement hooks.

### All platforms — hook configuration

After copying files, add the following to your Claude Code `settings.json` (global: `~/.claude/settings.json` on macOS/Linux, `%USERPROFILE%\.claude\settings.json` on Windows) under the `"hooks"` key:

```json
"PreToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [{ "type": "command", "command": "~/.claude/hooks/sweetclaude/test-guardian.sh" }]
  }
],
"PostToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [{ "type": "command", "command": "~/.claude/hooks/sweetclaude/auto-test-runner.sh" }]
  }
]
```

## Usage

SweetClaude is used inside Claude Code, not from the terminal. Start Claude Code first, then interact with SweetClaude through the Claude Code prompt.

```bash
# In your terminal — start Claude Code
claude

# Then in the Claude Code prompt — start a new project
sweetclaude init my-project

# SweetClaude detects the project, asks your deference level, and you're working
```

### Deference Levels

At session start, SweetClaude asks how collaborative you want it to be:

- **Level 1 — Collaborative:** Stops after every sub-step. Best for early phases.
- **Level 2 — Guided:** Stops at phase gates and major decisions. Best for mid-project.
- **Level 3 — Autonomous:** Stops only at phase gates. Best for implementation.

Change mid-stream anytime.

### TDD Levels

| Level | When | What Happens |
|---|---|---|
| 0: Hotfix | Emergency | Fix first, regression test same session |
| 1: Light | Simple work | Single-context RED-GREEN-REFACTOR |
| 2: Standard | Features, bugs | Subagent separation, tests committed before impl |
| 3: Full | From Gherkin | Full pipeline with QA caucus and context isolation |

### Phase Pipeline

```
DISCOVER → DEFINE → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP
```

Net-new features enter at Discover. Bug fixes, enhancements, and iterations enter at Define. Any work type can escalate to Discover if deeper issues surface. Phase re-entry is normal and expected.

## What's in the Box

```
framework/
  skills/         12 skills (phase router, TDD, Gherkin bridge, ripple analysis, etc.)
  hooks/           4 hooks (test guardian, auto-test runner, git checkpoint, auto-reindex)
  agents/          8 subagents (test writer, implementer, QA caucus x3, security, workflow, code review)
  rules/           3 rules files (interaction model, phase gates, TDD levels)
  config/          6 config files (defaults, phase-skill mapping, model routing, templates)
```

## Design Principles

- **Quality gates, not time gates.** SweetClaude never generates time estimates. Progress is measured in artifacts produced and criteria met.
- **Enforcement beats guidance.** TDD discipline is enforced by hooks, not advisory text. Tests are physically blocked from modification during implementation.
- **Dual context windows.** The system manages Claude's token limits AND your cognitive load simultaneously.
- **Phase dwelling.** The system stays present in the current phase. It never pushes advancement. You decide when to move on.
- **Creative partnership.** SweetClaude proposes and challenges. It thinks with you, not just for you.
- **Language agnostic.** Works with any language and framework. Codebase discovery drives configuration.

## Upstream Dependencies

SweetClaude orchestrates Superpowers and BMAD — it does not fork or modify them.

| Dependency | Min Version | License | Role |
|---|---|---|---|
| [Superpowers](https://github.com/obra/superpowers) | 5.0.7 | MIT | Dev mechanics (plans, worktrees, debugging, code review) |
| [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) | 6.0.0 | MIT | Product lifecycle (brainstorm, PRD, architecture, stories) |
| [Gherkin](https://github.com/cucumber/gherkin) | — | MIT | Specification language for acceptance criteria |

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — free for personal use, research, education, nonprofits, and government. Not for commercial use.

## Contributing

Contributions welcome. SweetClaude is built by solo developers, for solo developers. If you have ideas, skills, or improvements — open an issue or PR.
