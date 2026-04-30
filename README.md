<p>
  <img src="sweetclaude.png" alt="SweetClaude" width="180" align="left">
</p>
<br>
<br>
<br>
<br>
<br>

# SweetClaude

A plugin for Claude Code that provides workflow automation and co-piloting for end-to-end product development - from "I have an idea" to shipped, tested code — with structured workflows for strategy, product definition, architecture, technical design, test-driven development, QA testing, code reviews, and documentation. It includes RAG-powered document consolidation and reconciliation (optional) to turn those piles of scattered documents and chat exports into canonical documentation.

SweetClaude's skills cover the full lifecycle of building software: articulating what you are building and why, defining who it is for, analyzing the competitive landscape, writing product specs, designing architecture, implementing with test-driven development, reviewing code, and shipping. Because it sits on top of Claude Code, it works with any language or framework.

Built by an enterprise CTO/CISO and serial entrepreneur- originally for himself, and later for early-stage companies and solopreneurs who need a thoughtful, organized AI partner — not passive autocomplete-on-steroids.

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

**Self-Updating** — Run `/sweetclaude:update` from any project to fetch the latest version from GitHub and sync it across all installed locations. The update shows what changed, surfaces new capabilities, and migrates project artifacts from schema v1 to v2 if needed. Private repos are handled transparently via `gh` authentication.

**Auto Version Bumping** — An opt-in hook that automatically bumps your project's version after every git commit. It reads conventional commit prefixes (`feat` → minor, `fix`/`chore` → patch, `BREAKING` → major), updates configured version files, and commits the bump. Enable it by creating `.sweetclaude/version-bump.yaml` in your project.

## Getting Started

### Prerequisites

| Dependency | Check | Install |
|---|---|---|
| [Claude Code](https://claude.ai/code) | `claude --version` | [Install guide](https://docs.anthropic.com/en/docs/claude-code/getting-started) |
| Git | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| [GitHub CLI](https://cli.github.com/) | `gh --version` | `brew install gh` or [cli.github.com](https://cli.github.com/) |
| Node.js (for RAG) | `node --version` | [nodejs.org](https://nodejs.org/) — optional, needed for corpus management and semantic search |

### Install

```bash
git clone https://github.com/carson-sweet/sweetclaude.git
cd sweetclaude
./install.sh
```

The installer:
- Checks prerequisites (Claude Code, Git; Superpowers for full install)
- Backs up your existing `~/.claude/` configuration
- Scans for conflicting plugins and offers to clean them up
- Copies skills, hooks, agents, rules, and config to `~/.claude/`
- Wires TDD enforcement hooks into `settings.json`
- Generates `uninstall.sh` and `restore-config.sh` for clean removal

After install, all skills are available as `/sweetclaude:skill-name` commands in every Claude Code session.

#### Strategy Skills Only

If you want the product thinking, strategy, and corpus management skills — without the code and design phases:

```bash
./install.sh --strategy-skills-only
```

This installs strategy, product, corpus, and orchestration skills — no TDD hooks, no subagents, no Superpowers prerequisite required. Just Claude Code and Git. You can upgrade to the full install later by running `./install.sh`.

To update later, run `/sweetclaude:update` from any project. It fetches the latest version from GitHub and syncs everywhere.

### Quick Try (No Install)

Want to try SweetClaude without installing? Load it as a plugin for a single session:

```bash
git clone https://github.com/carson-sweet/sweetclaude.git
claude --plugin-dir /path/to/sweetclaude
```

All skills are available for that session. TDD enforcement hooks and global configuration are not active — those require the full install.

### Things to Try First

These are low-risk ways to see what SweetClaude can do before committing to a workflow.

**Ask Claude to explain the process.** Just type: "Explain the full SweetClaude process end-to-end — what are all the phases, what happens in each one, and what skills are involved?" Claude reads the master skill and gives you the full picture.

**Ask to see everything SweetClaude can do.** Type: "Show me all the things SweetClaude can do." Claude walks through every domain — strategy, product, design, code, review — and explains each capability.

**Ask what problems you can hand to SweetClaude.** Type: "What kinds of problems or use cases can I hand to SweetClaude?" This surfaces capabilities you might not expect — meeting prep, competitive analysis, academic paper writing, document organization, pain thesis development.

**Ask how SweetClaude is different.** Type: "How is SweetClaude different from other Claude Code coding frameworks and skills?" Claude explains what makes it unique: the strategic and product layers that happen before code, the structured pain thesis, the six domain buckets, the end-to-end lifecycle coverage.

**Browse all available commands.** Run `/sweetclaude:help` to see every command organized by category with a one-line description of each.

**Organize a pile of messy documents.** If you have brainstorming notes, Claude.ai session exports, research files, or strategy documents scattered across folders, tell SweetClaude "I have a pile of documents I need to organize." It runs a four-step pipeline: consolidate (scan, deduplicate, ingest), triage (classify), reconcile (draft canonical documents), promote (finalize with provenance, archive, and RAG index). Originals are never deleted.

**Check the status of a project SweetClaude already knows about.** If you have already activated SweetClaude for a project, open it and run `/sweetclaude:status`. It reads your progress and tells you where you are, what is done, and what the next step would be.

**Run a competitive landscape scan.** In any project, tell SweetClaude "run a competitive landscape scan for my space." It researches competitors, maps the landscape, and produces a SWOT analysis. No project setup required beyond activation.

**Get a code review.** On any project with code, tell SweetClaude "review my recent changes." It gives an adversarial review focused on logic errors, edge cases, and missing error handling — not style nitpicks.

**Run an autonomous end-to-end pipeline.** Tell SweetClaude "run the autonomous pipeline" or ask about John Wick mode. It executes the full product-definition → design → TDD → implementation → review → PR cycle with minimal human involvement. Human pause points are pre-defined and rare — the pipeline pauses at interactive gates, shows its work, waits for explicit approval, and resumes where it left off across sessions. If the prerequisites aren't met, it tells you exactly what to complete first.

**Set up semantic search.** Tell SweetClaude "set up semantic search for my documents." It installs a local RAG server, indexes your documents (PDF, Word, markdown, text), and makes them searchable by meaning. Ask questions like "what did we decide about authentication?" and get relevant passages from your docs. Subsequent runs only index new or changed files.

### Your First Session

**Activate SweetClaude for a project (new or existing):**

```
/sweetclaude:on
```

Detects whether the folder is empty or already has a project. For new projects: walks through setup, product discovery, user personas, and hands off to the pipeline. For existing projects: creates a safety snapshot, scans the codebase, interviews you about current state, and positions you in the right phase.

**Pick up where you left off:**

```
/sweetclaude:go
```

Reads your project state, checks phase gate exit criteria, and routes to the right skill. No menu — it tells you what needs to happen and does it.

**Check project status:**

```
/sweetclaude:status
```

Shows version stage, active work item, phase progress, SweetClaude version, and RAG corpus state. Prompts at the start of each session for active projects.

**Suspend or remove SweetClaude:**

```
/sweetclaude:off    # suspend — preserves all artifacts, reactivate with /sweetclaude:on
/sweetclaude:purge  # delete all artifacts — warns and requires typed confirmation first
```

**Get help:**

```
/sweetclaude:help
```

Conversational assistant that explains how to work with SweetClaude through prompting, not commands. Describe what you want to do and it shows you how.

## Key Use Cases

### "I have an idea for a product but have not started building anything"

Run `/sweetclaude:on` in an empty folder. SweetClaude will:
1. Set up the project (git, directory structure, CLAUDE.md)
2. Ask what you want to build
3. Run product discovery — problem framing, personas, optional competitive landscape
4. Hand off to the product definition pipeline (brief, PRD, architecture, implementation)

### "I have a codebase and want to start using SweetClaude"

Run `/sweetclaude:on` in your project folder. SweetClaude will:
1. Detect that there is an existing project
2. Create a safety snapshot (branch) before touching anything
3. Scan your code, tests, docs, and issues
4. Ask you about the current state and biggest concerns
5. Determine where your project sits in the development lifecycle
6. Set up tracking and offer to address your immediate concerns first

### "I need to build a specific feature"

Run `/sweetclaude:go` and describe what you need. SweetClaude classifies the work (strategy, product, design, or code) and routes to the right starting point with the right tools.

### "I have a GitHub issue to implement"

Run `/sweetclaude:go` and mention the issue number or paste the title. SweetClaude reads the issue, analyzes impact, proposes a plan, implements with TDD, verifies, updates docs, and opens a PR.

### "I need to write a research paper"

Tell SweetClaude "I need to write a research paper on [topic]." Six-phase pipeline: establish your thesis and what is novel, review 35+ papers, pick a venue, draft section by section with quality scoring, simulate peer review, format and submit.

### "I have a pile of messy strategy files from various sessions"

Tell SweetClaude "I have a pile of documents I need to organize." It presents a menu — select **Consolidate** to ingest your files, then work through **Triage** → **Reconcile** → **Promote**. Select **Status** at any point to see where the pipeline stands. Each step explains why skipping it produces worse results.

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
| `/sweetclaude:guardian-on` | Enable Protocol Guardian — enforces skill invocations and protocol steps for the session |
| `/sweetclaude:guardian-off` | Disable Protocol Guardian |
| `/sweetclaude:session-export` | Export a Claude.ai session as a structured document |
| `/sweetclaude:usage` | View, enable, or disable local usage tracking |

> **Note:** The product, design, code, and corpus skills below are invoked automatically by `/sweetclaude:go` based on your project state. You do not need to invoke them directly — but you can if you know what you want. The tables below explain the workflows that are available, but don't worry. The /sweetclaude-go command keeps track of where you are and will keep you on track (and if you want to jump to a different track, just say so). 

### Product Workflows
| Command | What it does |
|---|---|
| `/sweetclaude:product-discovery` | Establish what is being built, for whom, and why. Three depth levels from quick intent to full pain thesis. Collects compliance context (data categories, geography, user type) and derives applicable frameworks — written to `.sweetclaude/state/compliance-context.yaml` for use throughout the pipeline. |
| `/sweetclaude:product-competition` | Competitive analysis at three depth levels — survey, matrix comparison, or feature-deep analysis. |
| `/sweetclaude:product-user-personas` | Define users — who they are, what they need to do, and what success looks like. Includes triggers and deal-breakers. |
| `/sweetclaude:product-positioning-statement` | For/who/that/unlike positioning |
| `/sweetclaude:product-brief` | Strategic product brief. Outline-first, scales to available input. |
| `/sweetclaude:product-prd` | Full PRD with FRs, NFRs, epics |
| `/sweetclaude:product-user-stories` | User stories in Gherkin or generic format, scoped to all personas, SLC, or MVP. |
| `/sweetclaude:product-user-tdd-tests` | Stories to Gherkin .feature files |
| `/sweetclaude:product-manage-scope` | Track scope changes with rationale |
| `/sweetclaude:product-backlog` | Manage deferred work |
| `/sweetclaude:product-sprint-plan` | Plan sprints from backlog |
| `/sweetclaude:product-research` | Market and solution landscape research. Feeds the competitive seed list. |
| `/sweetclaude:product-market-messaging` | External communications by audience |
| `/sweetclaude:product-milestones add` | Create a new milestone with success criteria |
| `/sweetclaude:product-milestones review` | List milestones grouped by Now / Next / Later |
| `/sweetclaude:product-milestones link` | Attach a work item to a milestone (bidirectional) |
| `/sweetclaude:product-milestones status` | Detail view of one milestone with progress |
| `/sweetclaude:product-milestones blockers` | What is stopping a milestone from completing |
| `/sweetclaude:product-milestones complete` | Mark achieved with follow-up capture |
| `/sweetclaude:product-milestones unassigned` | Find work items with no milestone |

### Design Workflows
| Command | What it does |
|---|---|
| `/sweetclaude:design-user-flows` | Convert user stories into UX/UI flows — step-by-step paths through the interface. |
| `/sweetclaude:design-architecture` | System architecture — reads compliance context from discovery and surfaces each derived framework as a hard requirement throughout the architecture document |
| `/sweetclaude:design-tech-spec` | Technical specification — enforces compliance requirements from architecture state (e.g. confirms chosen providers meet HIPAA BAA or SOC 2 requirements) |
| `/sweetclaude:design-ux` | UX design and wireframes |
| `/sweetclaude:design-solutioning-gate` | Validate design before implementation |
| `/sweetclaude:design-change-impact-analysis` | Trace blast radius before changes |
| `/sweetclaude:documents-update-docs` | Keep docs in sync after changes |
| `/sweetclaude:design-data-model` | Schema, entities, migrations |
| `/sweetclaude:design-api-design` | Endpoints, contracts, versioning |
| `/sweetclaude:design-manage-decisions` | Record decisions with rationale |

### Documentation Workflows
| Command | What it does |
|---|---|
| `/sweetclaude:document-corpus` | Full corpus pipeline + RAG — consolidate, triage, reconcile, promote, set up semantic search, reindex |
| `/sweetclaude:documents-update-docs` | Keep docs in sync after implementation changes |
| `/sweetclaude:documents-academic-research` | Research paper development — 6-phase pipeline from thesis through submission |
| `/sweetclaude:documents-narrative-arc` | Knowledge graph of strategic claims and evidence |

### Misc.
| Command | What it does |
|---|---|
| `/sweetclaude:misc-meeting-prep` | Stakeholder meeting deliverables — agenda, talking points, anticipated questions |

### Coding Workflows
| Command | What it does |
|---|---|
| `/sweetclaude:code-feature` | Build a new feature end-to-end (Gherkin → TDD Level 3 → PR) |
| `/sweetclaude:code-issue` | Implement a GitHub issue end-to-end |
| `/sweetclaude:code-debt` | Tech debt cleanup (lock behavior first) |
| `/sweetclaude:code-testing` | Run tests, mutation, security review, and/or PR pre-check |
| `/sweetclaude:code-review` | Code, security, and compliance review |

### Autonomous Pipeline
| Command | What it does |
|---|---|
| `/sweetclaude:john-wick` | Fully autonomous, resumable, multi-session SDLC pipeline — from product definition through PR, with pre-defined human gates |
| `/sweetclaude:john-wick-checkin` | Phase check-in subagent (invoked internally by John Wick — available standalone for drift detection) |

## How It Works

SweetClaude is a Claude Code plugin. After running the installer, all skills are available as slash commands in every Claude Code session. You can also load it for a single session with `--plugin-dir` (see Quick Try above). Each skill is a set of instructions that Claude follows when you invoke it.

**State tracking.** SweetClaude creates a `.sweetclaude/` directory in your project to track progress, decisions, assumptions, and scope changes. This survives between sessions — when you come back, `/sweetclaude:status` tells you where you left off.

**Safety.** Before modifying an existing project, SweetClaude creates a `pre-sweetclaude` branch. You can always revert. The `.sweetclaude/` directory is committed to your project repo — it is part of your project history, not a separate system.

**Deference levels.** You control how much SweetClaude stops for approval:
- **Collaborative** — stops after every sub-step
- **Guided** — stops at major decisions
- **Autonomous** — stops only at phase gates

**TDD enforcement.** During implementation, hooks physically block test file modifications. Tests run automatically after every source edit. At higher TDD levels, the test writer and implementer are separate AI agents that cannot see each other's reasoning.

**Corpus management.** The corpus pipeline organizes scattered documents into searchable canonical truth. A state machine enforces the four-step ordering (consolidate → triage → reconcile → promote) so files cannot be processed out of order. Every canonical document has provenance sidecars tracing it back to source files. Originals are never deleted.

**Semantic search.** The RAG system uses [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag) to run a per-project vector database locally. No external services, no API keys, no data leaving your machine. The embedding model downloads once and works offline. The corpus pipeline's promote step indexes canonical documents automatically, and `/sweetclaude:document-corpus` handles standalone indexing for any project. Supports PDF, Word (.docx), markdown, and text files.

**Milestones.** Roadmap targets live in `docs/milestones/` as individual files with success criteria, contributing work items, and notes. Links between milestones and stories are bidirectional — editing one updates the other. Sprint planning aggregates milestone advancement automatically. Progress is computed from files on every read, not cached in a derived state file.

**Auto version bumping.** An opt-in PostToolUse hook on Bash detects successful `git commit` commands, reads the conventional commit prefix, and bumps version files automatically. Enable it by creating `.sweetclaude/version-bump.yaml` listing which files to update. The hook commits the bump with a `chore(version):` prefix to prevent loops.

**Self-updating.** `/sweetclaude:update` fetches the latest SweetClaude from GitHub (or a local repo), shows what changed, syncs to all installed locations, surfaces new capabilities that landed in the update, and checks whether project artifacts need migration for new schema fields.

**Protocol Guardian.** An optional enforcement layer that catches protocol drift mid-session. When enabled via `/sweetclaude:guardian-on`, it monitors skill invocations, TDD discipline, and artifact saves — and blocks on violations rather than issuing warnings. Disable at any time with `/sweetclaude:guardian-off`. SweetClaude will also proactively offer to enable it if it detects repeated protocol skipping.

**John Wick mode.** A fully autonomous, resumable pipeline that runs the complete product-definition → design → TDD → implementation → review → PR cycle with minimal human involvement. State is persisted in `.sweetclaude/state/john-wick.yaml` so the pipeline survives session boundaries and can resume exactly where it paused. Human gate points are pre-defined and rare: PRD approval, design change approval, and significant test failure triage. Past those gates, John Wick runs without stopping. A hard scope guardrail prevents autonomous pipelines from growing beyond what can be reasoned about clearly: more than 8 epics or 6 external dependencies triggers a warning and decomposition recommendation.

**Language agnostic.** SweetClaude discovers your project's language, framework, test runner, and build tools automatically. It works with TypeScript, Python, Go, Rust, Java, or anything else.

## Upstream Dependencies

SweetClaude orchestrates these plugins — it does not fork or modify them:

| Dependency | License | Required | Role |
|---|---|---|---|
| [Superpowers](https://github.com/obra/superpowers) | MIT | Full install | Dev mechanics (plans, worktrees, debugging, code review) |
| [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag) | MIT | Optional | Local semantic search — per-project vector index, no external services |

## License

[GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0-or-later) — free to use, modify, and distribute for any purpose. If you run SweetClaude as a network service or incorporate it into a distributed product, you must disclose the use of SweetClaude and make the complete source available, including modifications, under the same license. See [LICENSE](LICENSE) for full terms.

## Contributing

Contributions welcome. SweetClaude is built by solo developers, for solo developers. If you have ideas, skills, or improvements — open an issue or PR.

If you're getting value, consider buying me a coffee. Which in reality means you're shifting dollars from my coffee budget to my dog Smushford's treat budget. Smushford thanks you.

<p>
  <img src="sweetclaude-workshop.png" alt="SweetClaude Workshop" width="600" align="left">
</p>






















