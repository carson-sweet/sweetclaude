<p>
  <img src="sweetclaude.png" alt="SweetClaude" width="180" align="left">
</p>
<br>
<br>
<br>
<br>
<br>

# SweetClaude

An end-to-end product development (meaning not just code) framework for Claude Code. From "I have an idea" to shipped, tested code — with strategy, product definition, architecture, and disciplined implementation. It includes an optional RAG-powered document consolidation and reconciliation system to turn those six different piles of documents and chat exports into canon.

SweetClaude is a Claude Code plugin with 55 skills that cover the full lifecycle of building software: articulating what you are building and why, defining who it is for, analyzing the competitive landscape, writing product specs, designing architecture, implementing with test-driven development, reviewing code, and shipping. It works with any language or framework.

Built by an enterprise CTO/CISO turned solo developer for solo developers who want AI as a creative partner with structure and discipline — not a passive autocomplete-on-steroids.

## What SweetClaude Does

Most AI coding tools start at implementation. SweetClaude starts at the idea.

**Strategy** — Academic research, stakeholder meeting preparation, narrative arc building, and market messaging. SweetClaude helps you craft external communications by audience and build a knowledge graph of strategic claims and evidence.

**Product** — A discovery-first pipeline: product-discovery (three depth levels from quick intent to full pain thesis), competitive analysis via product-competition, user persona definition with product-user-personas, positioning, product briefs, PRDs with testable acceptance criteria, user stories, and scope management.

**Design** — System architecture, technical specifications, UX flows, data models, API design, service boundaries, infrastructure planning. Every design decision is recorded with context and rationale so future sessions understand why things are the way they are.

**Code** — Test-driven development at four enforcement levels. At the highest level, a test-writer agent and an implementer agent work in separate contexts — the implementer never sees the spec, only the tests. Test files are physically blocked from modification during implementation. Tests run automatically after every edit.

**Milestones** — Roadmap targets that span strategy and product work. Milestones are outcome-driven goals like "Exit Stealth" or "Paid Pilot Live" — not releases or sprints. Create milestones with success criteria, link user stories and backlog items to them, track progress, identify blockers, and mark milestones achieved with follow-up capture. Sprint planning reports which milestones a sprint advances. Status views show active milestones with criterion counts.

**Corpus Management** — Projects accumulate documents across folders, Claude.ai sessions, and external tools. SweetClaude's corpus pipeline takes messy files through a four-step process — consolidate (scan, deduplicate, ingest), triage (classify), reconcile (draft and refine canonical documents with the user), and promote (finalize with provenance tracking, archival, and RAG indexing). A state machine enforces ordering so nothing gets corrupted. Every canonical document traces back to its source files.

**Semantic Search (RAG)** — Index your project documents for search by meaning, not just keywords. SweetClaude sets up a local RAG system using [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag) — a per-project vector database that runs on your machine with no external services. Supports PDF, Word, markdown, and text files. The embedding model downloads once (~90MB) then works offline. The corpus pipeline's promote step automatically indexes canonical documents into the RAG system so your best, most current documents are always searchable.

**Review and Ship** — Adversarial code review, security testing, mutation testing to verify your tests actually catch bugs, pre-PR quality gates, and documentation updates.

**Self-Updating** — Run `/sweetclaude:update-sweetclaude` from any project to fetch the latest version from GitHub and sync it across all installed locations. The update shows what changed, surfaces new capabilities, and checks whether your project's artifacts need migration for the new version. Private repos are handled transparently via `gh` authentication.

**Auto Version Bumping** — An opt-in hook that automatically bumps your project's version after every git commit. It reads conventional commit prefixes (`feat` → minor, `fix`/`chore` → patch, `BREAKING` → major), updates configured version files, and commits the bump. Enable it by creating `.sweetclaude/version-bump.yaml` in your project.

## Getting Started

### Prerequisites

| Dependency | Check | Install |
|---|---|---|
| [Claude Code](https://claude.ai/code) | `claude --version` | [Install guide](https://docs.anthropic.com/en/docs/claude-code/getting-started) |
| Git | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| [GitHub CLI](https://cli.github.com/) | `gh --version` | `brew install gh` or [cli.github.com](https://cli.github.com/) |
| Node.js (for RAG) | `node --version` | [nodejs.org](https://nodejs.org/) — optional, needed for `/sweetclaude:document-corpus` |

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

After install, all 55 skills are available as `/sweetclaude:skill-name` commands in every Claude Code session.

#### Strategy Skills Only

If you want the product thinking, strategy, and corpus management skills without the code and design phases:

```bash
./install.sh --strategy-skills-only
```

This installs strategy, product, corpus, and orchestration skills — no TDD hooks, no subagents, no Superpowers prerequisite required. Just Claude Code and Git. You can upgrade to the full install later by running `./install.sh`.

To update later, run `/sweetclaude:update-sweetclaude` from any project. It fetches the latest version from GitHub and syncs everywhere.

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

**Ask how SweetClaude is different.** Type: "How is SweetClaude different from other Claude Code coding frameworks and skills?" Claude explains what makes it unique: the strategic and product layers that happen before code, the structured pain thesis, the five domain buckets, the end-to-end lifecycle coverage.

**Browse all available commands.** Run `/sweetclaude:help` to see every command organized by category with a one-line description of each.

**Organize a pile of messy documents.** If you have brainstorming notes, Claude.ai session exports, research files, or strategy documents scattered across folders, run `/sweetclaude:document-corpus`. It presents a menu: consolidate raw files, triage (classify each one), reconcile (draft canonical documents), promote (finalize with provenance, archive, and RAG index). Select **Status** at any point to see where you are. Originals are never deleted.

**Check the status of a project SweetClaude already knows about.** If you have already run init on a project, open it and run `/sweetclaude:status`. It reads your progress and tells you where you are, what is done, and what the next step would be.

**Run a competitive landscape scan.** In any project, run `/sweetclaude:product-competition` and describe your space. SweetClaude researches competitors, maps the landscape, and produces a SWOT analysis. No project setup required beyond init.

**Get a code review.** On any project with code, run `/sweetclaude:code-review`. It reads your recent changes and gives an adversarial review focused on logic errors, edge cases, and missing error handling — not style nitpicks.

**Set up semantic search.** Run `/sweetclaude:document-corpus` in any project. It installs a local RAG server, indexes your documents (PDF, Word, markdown, text), and makes them searchable by meaning. Ask questions like "what did we decide about authentication?" and get relevant passages from your docs. Subsequent runs only index new or changed files.

### Your First Session

**Getting started (new or existing project):**

```
/sweetclaude:sherpa
```

Detects whether the folder is empty or already has a project. For new projects: walks through setup, product discovery, user personas, and hands off to the pipeline. For existing projects: creates a safety snapshot, scans the codebase, interviews you about current state, and positions you in the right phase.

**Checking project status:**

```
/sweetclaude:status
```

Shows where you are, what has been done, what is pending, and what the next step is.

**Walking through the pipeline step by step:**

```
/sweetclaude:next-steps
```

Figures out the next thing to do based on where you are, runs the right skill, then moves to the next step. You approve or redirect at each point.

## Key Use Cases

### "I have an idea for a product but have not started building anything"

Run `/sweetclaude:sherpa` in an empty folder. SweetClaude will:
1. Set up the project (git, directory structure, CLAUDE.md)
2. Ask what you want to build
3. Run product discovery — problem framing, personas, optional competitive landscape
4. Hand off to the product definition pipeline (brief, PRD, architecture, implementation)

### "I have a codebase and want to start using SweetClaude"

Run `/sweetclaude:sherpa` in your project folder. SweetClaude will:
1. Detect that there is an existing project
2. Create a safety snapshot (branch) before touching anything
3. Scan your code, tests, docs, and issues
4. Ask you about the current state and biggest concerns
5. Determine where your project sits in the development lifecycle
6. Set up tracking and offer to address your immediate concerns first

### "I need to build a specific feature"

Run `/sweetclaude:find-skill` and describe what you need. SweetClaude classifies the work (strategy, product, design, or code) and routes you to the right starting point with the right tools.

### "I have a GitHub issue to implement"

Run `/sweetclaude:code-work-issue` with the issue number. It reads the issue, analyzes impact, proposes a plan, implements with TDD, verifies, updates docs, and opens a PR.

### "I need to write a research paper"

Run `/sweetclaude:misc-academic-research`. Six-phase pipeline: establish your thesis and what is novel, review 35+ papers, pick a venue, draft section by section with quality scoring, simulate peer review, format and submit.

### "I have a pile of messy strategy files from various sessions"

Run `/sweetclaude:document-corpus`. It presents a menu — select **Consolidate** to ingest your files, then work through **Triage** → **Reconcile** → **Promote**. Select **Status** at any point to see where the pipeline stands. Each step explains why skipping it produces worse results.

## All Commands

### Getting Started
| Command | What it does |
|---|---|
| `/sweetclaude:sherpa` | New or existing project — detects context, walks you through setup |

### Orchestration
| Command | What it does |
|---|---|
| `/sweetclaude:master` | Session entry point, pre-flight check, phase routing |
| `/sweetclaude:help` | Show project status and all available commands |
| `/sweetclaude:status` | What is done, what is pending, what is next |
| `/sweetclaude:next-steps` | Walk through the pipeline step by step |
| `/sweetclaude:find-skill` | Classify work and enter the pipeline |
| `/sweetclaude:fix-sweetclaude` | Audit and repair SweetClaude configuration |
| `/sweetclaude:update-sweetclaude` | Fetch latest from GitHub and sync to all projects |
| `/sweetclaude:hibernate` | Freeze or thaw a project mid-phase |
| `/sweetclaude:metrics` | View, enable, or disable local performance metrics |

### Strategy
| Command | What it does |
|---|---|
| `/sweetclaude:misc-academic-research` | Research paper development (6 phases) |
| `/sweetclaude:misc-meeting-prep` | Stakeholder meeting deliverables |
| `/sweetclaude:misc-narrative-arc` | Knowledge graph of strategic claims and evidence |
| `/sweetclaude:product-market-messaging` | External communications by audience |

### Product
| Command | What it does |
|---|---|
| `/sweetclaude:product-discovery` | Establish what is being built, for whom, and why. Three depth levels from quick intent to full pain thesis. |
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

### Design
| Command | What it does |
|---|---|
| `/sweetclaude:design-user-flows` | Convert user stories into UX/UI flows — step-by-step paths through the interface. |
| `/sweetclaude:design-architecture` | System architecture |
| `/sweetclaude:design-tech-spec` | Technical specification |
| `/sweetclaude:design-ux` | UX design and wireframes |
| `/sweetclaude:design-solutioning-gate` | Validate design before implementation |
| `/sweetclaude:design-change-impact-analysis` | Trace blast radius before changes |
| `/sweetclaude:documents-update-docs` | Keep docs in sync after changes |
| `/sweetclaude:design-data-model` | Schema, entities, migrations |
| `/sweetclaude:design-api-design` | Endpoints, contracts, versioning |
| `/sweetclaude:design-manage-decisions` | Record decisions with rationale |

### Milestones
| Command | What it does |
|---|---|
| `/sweetclaude:misc-milestones add` | Create a new milestone with success criteria |
| `/sweetclaude:misc-milestones review` | List milestones grouped by Now / Next / Later |
| `/sweetclaude:misc-milestones link` | Attach a work item to a milestone (bidirectional) |
| `/sweetclaude:misc-milestones status` | Detail view of one milestone with progress |
| `/sweetclaude:misc-milestones blockers` | What is stopping a milestone from completing |
| `/sweetclaude:misc-milestones complete` | Mark achieved with follow-up capture |
| `/sweetclaude:misc-milestones unassigned` | Find work items with no milestone |

### Documents & Search
| Command | What it does |
|---|---|
| `/sweetclaude:document-corpus` | Full corpus pipeline + RAG — consolidate, triage, reconcile, promote, set up semantic search, reindex |

### Code
| Command | What it does |
|---|---|
| `/sweetclaude:code-tdd` | TDD at 4 levels (hotfix through full Gherkin) |
| `/sweetclaude:code-work-issue` | Implement a GitHub issue end-to-end |
| `/sweetclaude:code-work-debt` | Tech debt cleanup (lock behavior first) |
| `/sweetclaude:code-testing` | Pre-PR quality gate |
| `/sweetclaude:code-testing` | Run tests, report failures concisely |
| `/sweetclaude:code-testing` | Verify tests catch real faults |
| `/sweetclaude:code-testing` | Security review of code changes |
| `/sweetclaude:code-review` | Adversarial code review |

## How It Works

SweetClaude is a Claude Code plugin. After running the installer, all 55 skills are available as slash commands in every Claude Code session. You can also load it for a single session with `--plugin-dir` (see Quick Try above). Each skill is a set of instructions that Claude follows when you invoke it.

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

**Self-updating.** `/sweetclaude:update-sweetclaude` fetches the latest SweetClaude from GitHub (or a local repo), shows what changed, syncs to all installed locations, surfaces new capabilities that landed in the update, and checks whether project artifacts need migration for new schema fields.

**Language agnostic.** SweetClaude discovers your project's language, framework, test runner, and build tools automatically. It works with TypeScript, Python, Go, Rust, Java, or anything else.

## Upstream Dependencies

SweetClaude orchestrates these plugins — it does not fork or modify them:

| Dependency | License | Role |
|---|---|---|
| [Superpowers](https://github.com/obra/superpowers) | MIT | Dev mechanics (plans, worktrees, debugging, code review) |

## License

[PolyForm Shield 1.0.0](LICENSE) — use SweetClaude for any purpose, including building and selling commercial products. The only restriction: you cannot sell a product that competes with SweetClaude itself.

## Contributing

Contributions welcome. SweetClaude is built by solo developers, for solo developers. If you have ideas, skills, or improvements — open an issue or PR.

<p>
  <img src="sweetclaude-workshop.png" alt="SweetClaude Workshop" width="600" align="left">
</p>






















