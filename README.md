<p align="center">
  <img src="sweetclaude.png" alt="SweetClaude" width="200">
</p>

# SweetClaude

A Claude Code framework for solo developers who want disciplined, end-to-end development — from concept to deployed, tested code — with AI as a creative partner, not a passive tool.

SweetClaude combines the best of [Superpowers](https://github.com/obra/superpowers) (dev mechanics), [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) (product lifecycle), and purpose-built skills into a single phase-gated pipeline with hook-enforced TDD, Gherkin-based test contracts, and an interaction model designed around human-AI creative partnership.

## What It Does

- **7-phase pipeline:** Discover, Define, Design, Plan, Implement, Verify, Ship — with quality gates, not time gates
- **Five-bucket architecture:** Strategy, product, design, code, deploy — skills organized by domain, not phase
- **Auto-flow and status:** `sweetclaude auto` runs the full pipeline hands-free at current deference level; `sweetclaude status` shows phase state and pending gates
- **Work-type routing:** Bug fixes, enhancements, iterations, and net-new features each enter the pipeline at the right phase
- **Hook-enforced TDD:** Four levels (Hotfix, Light, Standard, Full). Test files are physically blocked from modification during implementation. Tests run automatically after every source edit.
- **Pre-flight guard:** Deterministic hook blocks on first tool use if SweetClaude isn't configured for the project. Per-project opt-out via `.sweetclaude-skip`.
- **Gherkin bridge:** BMAD user stories become `.feature` files that drive test generation via isolated subagents
- **Context-isolated subagents:** Test writer and implementer work in separate contexts — the implementer never sees the spec, only the tests
- **Dual context window management:** Manages Claude's token limits AND your cognitive load — deference levels, detour tracking, re-orientation, decision logs
- **Creative partnership:** Proposes and challenges rather than asking and waiting. Follows your lead. Never pushes for phase advancement.
- **Ripple-effect analysis:** Before changing anything, traces what's affected across code, tests, docs, and specs
- **Hibernate:** Freeze and thaw projects mid-phase — captures full phase state for seamless resumption
- **RAG-powered knowledge:** Per-project semantic search over your document corpus (opt-in after file reconciliation)
- **One-command bootstrap:** `/sweetclaude:init` creates `.sweetclaude/` state directory, `strategy/` structure, CLAUDE.md from codebase discovery, and RAG index

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

- Read `.sweetclaude/state/phase.yaml` and `.sweetclaude/state/improvement-register.md` at session start if they exist.
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
    "matcher": "",
    "hooks": [{ "type": "command", "command": "~/.claude/hooks/sweetclaude/preflight-guard.sh" }]
  },
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

SweetClaude is used inside Claude Code, not from the terminal.

```bash
# Option 1: start Claude Code and pass the command directly
claude "sweetclaude init my-project"

# Option 2: start Claude Code first, then type in the prompt
claude
> sweetclaude init my-project
```

SweetClaude detects the project, asks your deference level, and you're working.

### Deference Levels

At session start, SweetClaude asks how collaborative you want it to be:

- **Collaborative:** Stops after every sub-step. Best for early phases.
- **Guided:** Stops at phase gates and major decisions. Best for mid-project.
- **Autonomous:** Stops only at phase gates. Best for implementation.

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

### Skill Domains

Skills are organized into five domain buckets, each usable from any phase:

- **strategy/** (8 skills) — concept, pain thesis, ICP, competitive analysis, academic research, meeting prep, narrative arc, market messaging
- **product/** (12 skills) — discovery, positioning, product brief, PRD, user stories, Gherkin tests, success criteria, workflows, scope management, backlog, sprint planning, feature competitive
- **design/** (11 skills) — architecture, tech spec, UX, solutioning gate, change impact analysis, doc updates, data model, API design, services design, infra design, decision management
- **code/** (8 skills) — TDD, issue implementation, tech debt, PR precheck, QA testing, mutation testing, security testing, code review
- **deploy/** — deferred

All buckets share utilities from `skills/shared/`.

## What's in the Box

```
framework/
  skills/         46 skills across strategy/ (8), product/ (12), design/ (11), code/ (8), orchestration (7)
  hooks/           6 hooks (test guardian, auto-test runner, git checkpoint, auto-reindex, pre-flight guard, session preflight)
  agents/          8 subagents
  rules/           3 rules files
  config/          6 config files
```

## Design Principles

- **Quality gates, not time gates.** SweetClaude never generates time estimates. Progress is measured in artifacts produced and criteria met.
- **Enforcement beats guidance.** TDD discipline is enforced by hooks, not advisory text. Tests are physically blocked from modification during implementation.
- **Dual context windows.** The system manages Claude's token limits AND your cognitive load simultaneously.
- **Five buckets, shared spine.** Strategy, product, design, code, and deploy share the same phase-gate pipeline, deference model, and interaction rules — but use different skills. The architecture extends without forking.
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

## Known Issues

- **"Unhandled node type: string" in Claude Code** — Cosmetic bug in Claude Code's bash command renderer ([#42085](https://github.com/anthropics/claude-code/issues/42085), [#43246](https://github.com/anthropics/claude-code/issues/43246)). Appears when shell commands contain quoted string literals in test expressions (e.g., `[ -f "docs/$name" ]`). Commands execute fine — only the display is affected. Regression in v2.1.89, no fix merged yet.

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — free for personal use, research, education, nonprofits, and government. Not for commercial use.

## Contributing

<p align="center">
  <img src="sweetclaude-workshop.png" alt="SweetClaude Workshop" width="600">
</p>

Contributions welcome. SweetClaude is built by solo developers, for solo developers. If you have ideas, skills, or improvements — open an issue or PR.
