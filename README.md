<img src="sweetclaude.png" alt="SweetClaude" width="180" align="left">
<br clear="all"/>

# SweetClaude

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![GitHub contributors](https://img.shields.io/github/contributors/carson-sweet/sweetclaude)](https://github.com/carson-sweet/sweetclaude/graphs/contributors)
[![GitHub last commit](https://img.shields.io/github/last-commit/carson-sweet/sweetclaude)](https://github.com/carson-sweet/sweetclaude/commits/main)

**Not the right tool for everyone.** If you want fast, frictionless code completion, [Cursor](https://cursor.sh) is a better fit. SweetClaude is for a different job: taking a project from idea through discovery, architecture, test-driven implementation, and shipped code as a single coherent workflow — with discipline enforced, not suggested.

**Built for:** Early-stage founders, technical solopreneurs, and senior ICs who want structure from strategy to code. Projects where what you build and why matters as much as how fast you write it.

**Requires:** [Claude Code](https://claude.ai/code).

## What SweetClaude Is

A Claude Code plugin covering the full product lifecycle across 77 skills. Works with any language or framework.

**Major features:**

- **Discovery-first pipeline** — Product discovery derives compliance requirements (GDPR, HIPAA, PCI DSS) from your actual users and data. That context flows automatically into architecture, tech spec, data model, and final code review — not a checkbox at the end.
- **Enforced TDD at four levels** — At the highest level, test writer and implementer are separate AI agents in isolated contexts. Test files are physically blocked from modification during implementation by PostToolUse hooks. Tests run after every source edit.
- **Persistent phase state** — `.sweetclaude/` tracks phase, decisions, assumptions, and scope changes in git. Return after weeks and `/sweetclaude:go` re-orients without you re-explaining anything.
- **Mockup pipeline** — Design UI components in an isolated Vite + React sandbox before touching production code. Graduate approved mockups with acceptance criteria extracted automatically.
- **Corpus management** — Four-step pipeline (consolidate → triage → reconcile → promote) for messy document collections, with local RAG indexing for semantic search. No external services.
- **Behavioral contracts** — 15 behavioral properties tested against each Claude model version. Hook-enforced properties are deterministic; instruction-guided properties are validated by a regression suite after every model upgrade.

**Key architectural decisions:**

- **Skills, not chat** — Every capability is a slash command with defined entry criteria, deference levels, and exit gates. Structured contracts replace freeform prompting.
- **Hooks for enforcement** — TDD rules and session discipline are enforced by shell hooks (PreToolUse/PostToolUse), not instructions. Instructions can drift; hooks cannot.
- **Agent isolation** — Test writer and implementer run in separate AI contexts with restricted tool sets (`tools:` frontmatter). The implementer never sees the spec — only failing tests.
- **State as git history** — `.sweetclaude/state/` is committed, not gitignored. Phase progression, decisions, and assumptions are project history, not session memory.
- **Deference levels** — Collaborative (stop after every sub-step), Guided (stop at major decisions), Autonomous (stop only at phase gates). Set in state, changeable mid-session.

## Quick Start

```bash
git clone https://github.com/carson-sweet/sweetclaude.git
cd sweetclaude && ./install.sh
```

Then go to your project and run:

```
/sweetclaude:on
```

`:on` detects whether you're starting from a new idea or an existing codebase, walks through setup, and leaves you at `/sweetclaude:go` ready to work.

→ [Full install options, updating, uninstalling](INSTALL.md)
→ [First session walkthrough](QUICKSTART.md)
→ [All 77 skills by category](docs/user-guide/skills-reference.md)

## All Commands

### Core Commands
| Command | What it does |
|---|---|
| `/sweetclaude:on` | Activate SweetClaude — new or existing project, detects context and walks through setup. Also reactivates a suspended project. |
| `/sweetclaude:off` | Suspend SweetClaude — preserves all artifacts, reactivate with `:on` |
| `/sweetclaude:purge` | Delete all SweetClaude artifacts — recommends a backup branch, shows all files, requires "I understand" |
| `/sweetclaude:go` | Pick up where you left off — reads state, checks phase exit criteria, routes to the right skill. No menu. |
| `/sweetclaude:status` | Full project picture: phase, work item, SweetClaude version, RAG corpus state. Auto-fires at session start. |
| `/sweetclaude:update` | Fetch latest SweetClaude from GitHub and sync to all projects |
| `/sweetclaude:help` | Conversational help — describe what you want to do, learn how to work through prompting |

### Advanced
| Command | What it does |
|---|---|
| `/sweetclaude:fix-sweetclaude` | Audit and repair SweetClaude configuration |
| `/sweetclaude:behavioral-regression` | Run the 15-contract behavioral test suite — validates that the current model version honors SweetClaude's behavioral contracts. Run after any Claude model upgrade. **15/15 passing on claude-sonnet-4-6 (2026-05-01).** [Contract status by model version →](docs/user-guide/behavioral-contracts.md) |
| `/sweetclaude:guardian-on` | Enable Protocol Guardian — enforces skill invocations and protocol steps for the session |
| `/sweetclaude:guardian-off` | Disable Protocol Guardian |
| `/sweetclaude:session-export` | Export a Claude.ai session as a structured document |
| `/sweetclaude:usage` | View, enable, or disable local usage tracking |

→ [Full command reference — product, design, code, project management, testing, corpus, and autonomous pipeline skills](COMMANDS.md)

## How It Works

SweetClaude is a Claude Code plugin. After install, all skills are available as slash commands in every Claude Code session. You can also load it for a single session with `--plugin-dir` without a global install.

**State tracking.** SweetClaude creates a `.sweetclaude/` directory in your project to track progress, decisions, assumptions, and scope changes. Commit it to git — it is project history, not cache. When you return, `/sweetclaude:go` reads state and re-orients. You do not need to remember where you left off.

**Enforcement.** TDD hooks physically block test file modification during implementation (hook-enforced, not advisory) and run tests automatically after every source edit. At higher TDD levels, test writer and implementer are separate AI agents in separate contexts — the implementer never sees the spec, only the failing tests.

**Behavioral stability.** Not all behavioral properties are guaranteed equally. Hook-enforced properties are deterministic and version-stable. Protocol Guardian (`/sweetclaude:guardian-on`) upgrades instruction-guided properties to deterministic enforcement for a session. The 15-contract behavioral regression suite validates properties after model upgrades.

**Deference levels.** Collaborative (stop after every sub-step), Guided (stop at major decisions), Autonomous (stop only at phase gates). Changeable mid-session.

For a full explanation of the architecture and design decisions behind SweetClaude → [How It Works](docs/user-guide/how-it-works.md)

## Upstream Dependencies

SweetClaude orchestrates these plugins — it does not fork or modify them:

| Dependency | License | Required | Role |
|---|---|---|---|
| [Superpowers](https://github.com/obra/superpowers) | MIT | Required for code/TDD features | Dev mechanics (plans, worktrees, debugging, code review). Not required for strategy-skills-only install. |
| [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag) | MIT | Optional | Local semantic search — per-project vector index, no external services |

For dependency risk, failure modes, and contingency plans → [Platform Dependencies](docs/user-guide/platform-dependencies.md)

## License

[GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0-or-later) — free to use, modify, and distribute. No restrictions for personal or commercial tools you build. AGPL obligations activate only if you deploy SweetClaude as a network service offered to others — in that case, you must make your modified source available under the same license. See [LICENSE](LICENSE) for full terms.

## Contribute

Contributions welcome. SweetClaude is built by solo developers, for solo developers.

**Looking for a technical co-maintainer.** SweetClaude is currently maintained by one person. The areas that need a second reviewer — the hook system, migration registry, and orchestration layer — require someone who understands how the phase pipeline works end to end. If you have read through the codebase and want meaningful ownership of a growing open-source project, open an issue introducing yourself. See [what requires full framework knowledge](CONTRIBUTING.md#what-requires-full-framework-knowledge) for the scope.

For skill improvements, documentation, walkthroughs, and examples — read [CONTRIBUTING.md](CONTRIBUTING.md) for where to start. Questions and ideas belong in [GitHub Discussions](https://github.com/carson-sweet/sweetclaude/discussions). Bugs and PRs go to Issues.

<p>
  <img src="sweetclaude-workshop.png" alt="SweetClaude Workshop" width="600" align="left">
</p>
<br clear="all"/>

## Support

If you're getting value from SweetClaude, consider [buying me a coffee](https://ko-fi.com/carsonsweet). Which in reality means you're moving dollars from my coffee budget to [my dog Smushford's](http://instagram.com/smushford) treat budget. 

Smushford thanks you.
<br clear="all"/>
<p>
  <img src="smushford.png" alt="Smushford Wellington DuBois III" width="400" align="left">
</p>
<br clear="all"/>





