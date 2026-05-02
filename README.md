<img src="sweetclaude.png" alt="SweetClaude" width="180" align="left">
<br clear="all"/>

# SweetClaude

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![GitHub contributors](https://img.shields.io/github/contributors/carson-sweet/sweetclaude)](https://github.com/carson-sweet/sweetclaude/graphs/contributors)
[![GitHub last commit](https://img.shields.io/github/last-commit/carson-sweet/sweetclaude)](https://github.com/carson-sweet/sweetclaude/commits/main)

**Not the right tool for everyone.** If you want fast, frictionless code completion while you're writing, [Cursor](https://cursor.sh) is a better fit. SweetClaude is built for a different job: taking you from "I have an idea" through product definition, architecture, test-driven implementation, and shipped code — as a single coherent workflow. If you keep starting projects and not finishing them, or if you're building a product and want discipline from strategy to code, keep reading.

**Built for:** Early-stage founders, technical solopreneurs, and senior ICs who want a structured partner — not autocomplete-on-steroids. Projects where the 70% of work that happens before a function is written matters as much as the implementation.

**Requires:** [Claude Code](https://claude.ai/code) — Anthropic's CLI (paid subscription).

A plugin for Claude Code that covers the full lifecycle: articulating what you are building and why, defining who it is for, analyzing the competitive landscape, writing product specs, designing architecture, implementing with test-driven development, reviewing code, and shipping. Works with any language or framework. Workflow structure is tiered — weekend projects and commercial SaaS have different needs — and automatically adjusts as the project matures.

Built by an enterprise CTO/CISO and serial entrepreneur, originally as his toolchain.

## What SweetClaude Does

Most AI coding tools start at implementation. SweetClaude starts at the idea.

**Strategy** — Academic research, stakeholder meeting preparation, narrative arc building, and market messaging. SweetClaude helps you craft external communications by audience and build a knowledge graph of strategic claims and evidence.

**Product** — A discovery-first pipeline: product-discovery (three depth levels from quick intent to full pain thesis) asks what data the product handles, where users are, and who they are — deriving applicable compliance frameworks (GDPR, HIPAA, PCI DSS, COPPA) and writing a compliance context file that flows through architecture, tech spec, and final code review. Also covers competitive analysis, user persona definition, positioning, product briefs, PRDs with testable acceptance criteria, user stories, and scope management.

**Design** — System architecture, technical specifications, UX flows, data models, API design, service boundaries, infrastructure planning. Every design decision is recorded with context and rationale so future sessions understand why things are the way they are.

**Code** — Test-driven development at four enforcement levels. At the highest level, a test-writer agent and an implementer agent work in separate contexts — the implementer never sees the spec, only the tests. Test files are physically blocked from modification during implementation. Tests run automatically after every edit.

**Milestones** — Roadmap targets that span strategy and product work. Milestones are outcome-driven goals like "Exit Stealth" or "Paid Pilot Live" — not releases or sprints. Create milestones with success criteria, link user stories and backlog items to them, track progress, identify blockers, and mark milestones achieved with follow-up capture. Sprint planning reports which milestones a sprint advances. Status views show active milestones with criterion counts.

**Corpus Management** — Projects accumulate documents across folders, Claude.ai sessions, and external tools. SweetClaude's corpus pipeline takes messy files through a four-step process — consolidate (scan, deduplicate, ingest), triage (classify), reconcile (draft and refine canonical documents with the user), and promote (finalize with provenance tracking, archival, and RAG indexing). A state machine enforces ordering so nothing gets corrupted. Every canonical document traces back to its source files.

**Semantic Search (RAG)** — Index your project documents for search by meaning, not just keywords. SweetClaude sets up a local RAG system using [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag) — a per-project vector database that runs on your machine with no external services. Supports PDF, Word, markdown, and text files. The embedding model downloads once (~90MB) then works offline. The corpus pipeline's promote step automatically indexes canonical documents into the RAG system so your best, most current documents are always searchable.

**Review and Ship** — Adversarial code review, security testing, mutation testing to verify your tests actually catch bugs, pre-PR quality gates, and documentation updates.

**Skills state tracking** — Six data-owning skills (`product-backlog`, `product-milestones`, `product-sprint-plan`, `product-user-personas`, `product-user-stories`, `document-corpus`) maintain explicit onboarding state in `.sweetclaude/state/skills.yaml`. Each skill can be `active` (in use), `paused` (data intact, skill off), or `uninitialized` (never set up). First invocation runs a lightweight setup flow automatically. Pausing a skill suspends it without deleting any data — different from offboarding, which exports and removes data. `/sweetclaude:status` surfaces skill inconsistencies (e.g., a skill marked active but missing its artifacts). `/sweetclaude:fix-sweetclaude` can bootstrap or repair the file.

**Self-Updating** — Run `/sweetclaude:update` from any project to fetch the latest version from GitHub and sync it across all installed locations. The update shows what changed, surfaces new capabilities, migrates `skills.yaml` from schema v1 to v2, and prompts to onboard any skills still `uninitialized`. Private repos are handled transparently via `gh` authentication.

**Auto Version Bumping** — An opt-in hook that automatically bumps your project's version after every git commit. It reads conventional commit prefixes (`feat` → minor, `fix`/`chore` → patch, `BREAKING` → major), updates configured version files, and commits the bump. Enable it by creating `.sweetclaude/version-bump.yaml` in your project.

## Getting Started

→ [Install SweetClaude](INSTALL.md) — prerequisites, install options, updating, uninstalling
→ [Your first session](QUICKSTART.md) — first commands, common starting points

### Things to Try First

These work before installing — just describe them to Claude in any session that has SweetClaude loaded.

**Ask Claude to explain the process.** "Explain the full SweetClaude process end-to-end — what are all the phases, what happens in each one, and what skills are involved?"

**Browse all available commands.** Run `/sweetclaude:help` to see every command organized by category.

**Organize a pile of messy documents.** Tell SweetClaude "I have a pile of documents I need to organize." Four-step corpus pipeline: consolidate → triage → reconcile → promote. Originals are never deleted.

**Get a code review.** Tell SweetClaude "review my recent changes." Adversarial review focused on logic errors, edge cases, and missing error handling — not style.

**Run an autonomous end-to-end pipeline.** Tell SweetClaude "run the autonomous pipeline" or ask about John Wick mode.

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

→ [Full command reference — all product, design, code, corpus, and autonomous pipeline skills](COMMANDS.md)

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





