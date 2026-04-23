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

SweetClaude is a Claude Code plugin with 60 skills that cover the full lifecycle of building software: articulating what you are building and why, defining who it is for, analyzing the competitive landscape, writing product specs, designing architecture, implementing with test-driven development, reviewing code, and shipping. It works with any language or framework.

Built by an enterprise CTO/CISO turned solo developer for solo developers who want AI as a creative partner with structure and discipline — not a passive autocomplete-on-steroids.

## What SweetClaude Does

Most AI coding tools start at implementation. SweetClaude starts at the idea.

**Strategy** — Before you write a line of code, SweetClaude helps you articulate what you are building, who has the pain you are solving, what the competitive landscape looks like, and whether the pain is real enough to sustain a business. It walks you through building a pain thesis, defining your ideal customer profile, and crafting market messaging.

**Product** — SweetClaude guides you through structured product discovery: persona interviews one at a time, feature brainstorming with include/exclude decisions, product briefs, PRDs with testable acceptance criteria, user stories, success metrics, and scope management.

**Design** — System architecture, technical specifications, UX flows, data models, API design, service boundaries, infrastructure planning. Every design decision is recorded with context and rationale so future sessions understand why things are the way they are.

**Code** — Test-driven development at four enforcement levels. At the highest level, a test-writer agent and an implementer agent work in separate contexts — the implementer never sees the spec, only the tests. Test files are physically blocked from modification during implementation. Tests run automatically after every edit.

**Milestones** — Roadmap targets that span strategy and product work. Milestones are outcome-driven goals like "Exit Stealth" or "Paid Pilot Live" — not releases or sprints. Create milestones with success criteria, link user stories and backlog items to them, track progress, identify blockers, and mark milestones achieved with follow-up capture. Sprint planning reports which milestones a sprint advances. Status views show active milestones with criterion counts.

**Corpus Management** — Projects accumulate documents across folders, Claude.ai sessions, and external tools. SweetClaude's corpus pipeline takes messy files through a four-step process — consolidate (scan, deduplicate, ingest), triage (classify), reconcile (draft and refine canonical documents with the user), and promote (finalize with provenance tracking, archival, and RAG indexing). A state machine enforces ordering so nothing gets corrupted. Every canonical document traces back to its source files.

**Semantic Search (RAG)** — Index your project documents for search by meaning, not just keywords. SweetClaude sets up a local RAG system using [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag) — a per-project vector database that runs on your machine with no external services. Supports PDF, Word, markdown, and text files. The embedding model downloads once (~90MB) then works offline. The corpus pipeline's promote step automatically indexes canonical documents into the RAG system so your best, most current documents are always searchable.

**Review and Ship** — Adversarial code review, security testing, mutation testing to verify your tests actually catch bugs, pre-PR quality gates, and documentation updates.

**Self-Updating** — Run `/sweetclaude:update-skills` from any project to fetch the latest version from GitHub and sync it across all installed locations. The update shows what changed, surfaces new capabilities, and checks whether your project's artifacts need migration for the new version. Private repos are handled transparently via `gh` authentication.

**Auto Version Bumping** — An opt-in hook that automatically bumps your project's version after every git commit. It reads conventional commit prefixes (`feat` → minor, `fix`/`chore` → patch, `BREAKING` → major), updates configured version files, and commits the bump. Enable it by creating `.sweetclaude/version-bump.yaml` in your project.

## Getting Started

### Prerequisites

| Dependency | Check | Install |
|---|---|---|
| [Claude Code](https://claude.ai/code) | `claude --version` | [Install guide](https://docs.anthropic.com/en/docs/claude-code/getting-started) |
| Git | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| [GitHub CLI](https://cli.github.com/) | `gh --version` | `brew install gh` or [cli.github.com](https://cli.github.com/) |
| Node.js (for RAG) | `node --version` | [nodejs.org](https://nodejs.org/) — optional, needed for `/sweetclaude:rag-index` |

### Install

```bash
git clone https://github.com/carson-sweet/sweetclaude.git
cd sweetclaude
./install.sh
```

The installer:
- Checks prerequisites (Claude Code, Git, Superpowers, BMAD)
- Backs up your existing `~/.claude/` configuration
- Scans for conflicting plugins and offers to clean them up
- Copies skills, hooks, agents, rules, and config to `~/.claude/`
- Wires TDD enforcement hooks into `settings.json`
- Generates `uninstall.sh` and `restore-config.sh` for clean removal

After install, all 60 skills are available as `/sweetclaude:skill-name` commands in every Claude Code session.

To update later, run `/sweetclaude:update-skills` from any project. It fetches the latest version from GitHub and syncs everywhere.

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

**Organize a pile of messy documents.** If you have brainstorming notes, Claude.ai session exports, research files, or strategy documents scattered across folders, run `/sweetclaude:init` in the project and tell it you have files to onboard. It copies them into `corpus/raw/inbox/` (originals untouched). Then work through the corpus pipeline: `/sweetclaude:corpus-consolidate` to deduplicate, `/sweetclaude:corpus-triage` to classify, `/sweetclaude:corpus-reconcile` to draft canonical documents, and `/sweetclaude:corpus-promote` to finalize with provenance tracking. Run `/sweetclaude:corpus-status` anytime to see where you are.

**Check the status of a project SweetClaude already knows about.** If you have already run init on a project, open it and run `/sweetclaude:status`. It reads your progress and tells you where you are, what is done, and what the next step would be.

**Run a competitive landscape scan.** In any project, run `/sweetclaude:strategy-competitive-analysis` and describe your space. SweetClaude researches competitors, maps the landscape, and produces a SWOT analysis. No project setup required beyond init.

**Get a code review.** On any project with code, run `/sweetclaude:code-code-review`. It reads your recent changes and gives an adversarial review focused on logic errors, edge cases, and missing error handling — not style nitpicks.

**Set up semantic search.** Run `/sweetclaude:rag-index` in any project. It installs a local RAG server, indexes your documents (PDF, Word, markdown, text), and makes them searchable by meaning. Ask questions like "what did we decide about authentication?" and get relevant passages from your docs. Subsequent runs only index new or changed files.

### Your First Session

**Starting a brand new project:**

```
/sweetclaude:sherpa-start
```

This walks you through everything from "I have an idea" to a configured project. It chains together: project setup, concept articulation, pain thesis, ideal customer profile, and product discovery. At the end, it hands off to the pipeline for product definition, design, and implementation.

**Adopting an existing project:**

```
/sweetclaude:sherpa-adopt
```

This scans your codebase, understands what exists (code, tests, docs, issues), asks you about the current state, and figures out where you are in the development lifecycle. It sets up SweetClaude without disrupting what you have. Before making any changes, it creates a `pre-sweetclaude` branch so you can always revert.

**Checking project status:**

```
/sweetclaude:status
```

Shows where you are, what has been done, what is pending, and what the next step is.

**Walking through the pipeline step by step:**

```
/sweetclaude:auto-flow
```

Figures out the next thing to do based on where you are, runs the right skill, then moves to the next step. You approve or redirect at each point.

## Key Use Cases

### "I have an idea for a product but have not started building anything"

Run `/sweetclaude:sherpa-start` in an empty folder. SweetClaude will:
1. Set up the project (git, directory structure, CLAUDE.md)
2. Help you articulate the concept
3. Walk you through a structured pain analysis — who has this problem, how badly, what they do today, why existing solutions fail
4. Define your ideal customer profile
5. Run product discovery — personas, features, competitive landscape
6. Hand off to the product definition pipeline (brief, PRD, architecture, implementation)

### "I have a codebase and want to start using SweetClaude"

Run `/sweetclaude:sherpa-adopt` in your project folder. SweetClaude will:
1. Create a safety snapshot (branch) before touching anything
2. Scan your code, tests, docs, and issues
3. Ask you about the current state and biggest concerns
4. Determine where your project sits in the development lifecycle
5. Set up tracking and offer to address your immediate concerns first

### "I need to build a specific feature"

Run `/sweetclaude:new-task` and describe what you need. SweetClaude classifies the work (strategy, product, design, or code) and routes you to the right starting point with the right tools.

### "I have a GitHub issue to implement"

Run `/sweetclaude:code-work-issue` with the issue number. It reads the issue, analyzes impact, proposes a plan, implements with TDD, verifies, updates docs, and opens a PR.

### "I need to write a research paper"

Run `/sweetclaude:strategy-academic-research`. Six-phase pipeline: establish your thesis and what is novel, review 35+ papers, pick a venue, draft section by section with quality scoring, simulate peer review, format and submit.

### "I have a pile of messy strategy files from various sessions"

Run `/sweetclaude:init` and point it at the files. It copies them into `corpus/raw/inbox/`. Then work through the corpus pipeline:
1. `/sweetclaude:corpus-consolidate` — scan, deduplicate, generate a plan, copy unique files in batches
2. `/sweetclaude:corpus-triage` — classify each file as keep, reconcile, discard, or defer
3. `/sweetclaude:corpus-reconcile` — draft and refine canonical documents from the classified files
4. `/sweetclaude:corpus-promote` — finalize with provenance sidecars, archive sources, index into RAG

Run `/sweetclaude:corpus-status` at any point to see where the pipeline stands.

## All Commands

### Getting Started
| Command | What it does |
|---|---|
| `/sweetclaude:sherpa-start` | Brand new project — walk through everything from idea to code |
| `/sweetclaude:sherpa-adopt` | Existing project — scan, assess, set up SweetClaude |

### Orchestration
| Command | What it does |
|---|---|
| `/sweetclaude:master` | Session entry point, pre-flight check, phase routing |
| `/sweetclaude:help` | Show project status and all available commands |
| `/sweetclaude:status` | What is done, what is pending, what is next |
| `/sweetclaude:auto-flow` | Walk through the pipeline step by step |
| `/sweetclaude:init` | Set up SweetClaude for a project |
| `/sweetclaude:new-task` | Classify work and enter the pipeline |
| `/sweetclaude:fix-config` | Audit and repair SweetClaude configuration |
| `/sweetclaude:update-skills` | Fetch latest from GitHub and sync to all projects |
| `/sweetclaude:hibernate` | Freeze or thaw a project mid-phase |

### Strategy
| Command | What it does |
|---|---|
| `/sweetclaude:strategy-concept` | Articulate what this product / project is and why it exists |
| `/sweetclaude:strategy-pain-thesis` | Structured user / customer pain analysis using 11-section framework |
| `/sweetclaude:strategy-ideal-customer-profile` | Who has this pain and will invest in relieving it |
| `/sweetclaude:strategy-competitive-analysis` | Strategic landscape and differentiation |
| `/sweetclaude:strategy-academic-research` | Research paper development (6 phases) |
| `/sweetclaude:strategy-meeting-prep` | Stakeholder meeting deliverables |
| `/sweetclaude:strategy-narrative-arc` | Knowledge graph of strategic claims and evidence |
| `/sweetclaude:strategy-market-messaging` | External communications by audience |

### Product
| Command | What it does |
|---|---|
| `/sweetclaude:product-discovery` | Persona interviews, feature brainstorming, competitive scan |
| `/sweetclaude:product-positioning-statement` | For/who/that/unlike positioning |
| `/sweetclaude:product-product-brief` | 11-section product brief, one section at a time |
| `/sweetclaude:product-prd` | Full PRD with FRs, NFRs, epics |
| `/sweetclaude:product-user-story` | User stories with acceptance criteria |
| `/sweetclaude:product-user-tdd-tests` | Stories to Gherkin .feature files |
| `/sweetclaude:product-user-success-criteria` | Measurable success per persona |
| `/sweetclaude:product-user-workflows` | User stories to UX/UI flows |
| `/sweetclaude:product-manage-scope` | Track scope changes with rationale |
| `/sweetclaude:product-backlog` | Manage deferred work |
| `/sweetclaude:product-sprint-plan` | Plan sprints from backlog |
| `/sweetclaude:product-research` | Market or technical research |
| `/sweetclaude:product-feature-competitive` | Product-level feature comparison |

### Design
| Command | What it does |
|---|---|
| `/sweetclaude:design-architecture` | System architecture |
| `/sweetclaude:design-tech-spec` | Technical specification |
| `/sweetclaude:design-ux` | UX design and wireframes |
| `/sweetclaude:design-solutioning-gate` | Validate design before implementation |
| `/sweetclaude:design-change-impact-analysis` | Trace blast radius before changes |
| `/sweetclaude:design-update-docs` | Keep docs in sync after changes |
| `/sweetclaude:design-data-model` | Schema, entities, migrations |
| `/sweetclaude:design-api-design` | Endpoints, contracts, versioning |
| `/sweetclaude:design-services-design` | Service boundaries and communication |
| `/sweetclaude:design-infra-design` | Infrastructure and deployment |
| `/sweetclaude:design-manage-decisions` | Record decisions with rationale |

### Milestones
| Command | What it does |
|---|---|
| `/sweetclaude:milestones add` | Create a new milestone with success criteria |
| `/sweetclaude:milestones review` | List milestones grouped by Now / Next / Later |
| `/sweetclaude:milestones link` | Attach a work item to a milestone (bidirectional) |
| `/sweetclaude:milestones status` | Detail view of one milestone with progress |
| `/sweetclaude:milestones blockers` | What is stopping a milestone from completing |
| `/sweetclaude:milestones complete` | Mark achieved with follow-up capture |
| `/sweetclaude:milestones unassigned` | Find work items with no milestone |

### Corpus Management
| Command | What it does |
|---|---|
| `/sweetclaude:corpus-consolidate` | Scan directories, deduplicate, copy into corpus/raw/inbox/ |
| `/sweetclaude:corpus-triage` | Classify inbox files for reconciliation, archival, or deferral |
| `/sweetclaude:corpus-reconcile` | Draft and refine canonical documents from staged files |
| `/sweetclaude:corpus-promote` | Finalize approved documents — provenance, archive, RAG index |
| `/sweetclaude:corpus-reindex` | Rebuild RAG collections from source files |
| `/sweetclaude:corpus-status` | Show pipeline state, file counts, and next step |

### Semantic Search
| Command | What it does |
|---|---|
| `/sweetclaude:rag-index` | Set up local RAG and index project documents (PDF, Word, markdown, text) |

### Code
| Command | What it does |
|---|---|
| `/sweetclaude:code-tdd` | TDD at 4 levels (hotfix through full Gherkin) |
| `/sweetclaude:code-work-issue` | Implement a GitHub issue end-to-end |
| `/sweetclaude:code-work-debt` | Tech debt cleanup (lock behavior first) |
| `/sweetclaude:code-pr-precheck` | Pre-PR quality gate |
| `/sweetclaude:code-qa-testing` | Run tests, report failures concisely |
| `/sweetclaude:code-mutation-testing` | Verify tests catch real faults |
| `/sweetclaude:code-security-testing` | Security review of code changes |
| `/sweetclaude:code-code-review` | Adversarial code review |

## How It Works

SweetClaude is a Claude Code plugin. After running the installer, all 60 skills are available as slash commands in every Claude Code session. You can also load it for a single session with `--plugin-dir` (see Quick Try above). Each skill is a set of instructions that Claude follows when you invoke it.

**State tracking.** SweetClaude creates a `.sweetclaude/` directory in your project to track progress, decisions, assumptions, and scope changes. This survives between sessions — when you come back, `/sweetclaude:status` tells you where you left off.

**Safety.** Before modifying an existing project, SweetClaude creates a `pre-sweetclaude` branch. You can always revert. The `.sweetclaude/` directory is committed to your project repo — it is part of your project history, not a separate system.

**Deference levels.** You control how much SweetClaude stops for approval:
- **Collaborative** — stops after every sub-step
- **Guided** — stops at major decisions
- **Autonomous** — stops only at phase gates

**TDD enforcement.** During implementation, hooks physically block test file modifications. Tests run automatically after every source edit. At higher TDD levels, the test writer and implementer are separate AI agents that cannot see each other's reasoning.

**Corpus management.** The corpus pipeline organizes scattered documents into searchable canonical truth. A state machine enforces the four-step ordering (consolidate → triage → reconcile → promote) so files cannot be processed out of order. Every canonical document has provenance sidecars tracing it back to source files. Originals are never deleted.

**Semantic search.** The RAG system uses [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag) to run a per-project vector database locally. No external services, no API keys, no data leaving your machine. The embedding model downloads once and works offline. The corpus pipeline's promote step indexes canonical documents automatically, and `/sweetclaude:rag-index` handles standalone indexing for any project. Supports PDF, Word (.docx), markdown, and text files.

**Milestones.** Roadmap targets live in `docs/milestones/` as individual files with success criteria, contributing work items, and notes. Links between milestones and stories are bidirectional — editing one updates the other. Sprint planning aggregates milestone advancement automatically. Progress is computed from files on every read, not cached in a derived state file.

**Auto version bumping.** An opt-in PostToolUse hook on Bash detects successful `git commit` commands, reads the conventional commit prefix, and bumps version files automatically. Enable it by creating `.sweetclaude/version-bump.yaml` listing which files to update. The hook commits the bump with a `chore(version):` prefix to prevent loops.

**Self-updating.** `/sweetclaude:update-skills` fetches the latest SweetClaude from GitHub (or a local repo), shows what changed, syncs to all installed locations, surfaces new capabilities that landed in the update, and checks whether project artifacts need migration for new schema fields.

**Language agnostic.** SweetClaude discovers your project's language, framework, test runner, and build tools automatically. It works with TypeScript, Python, Go, Rust, Java, or anything else.

## Upstream Dependencies

SweetClaude orchestrates these plugins — it does not fork or modify them:

| Dependency | License | Role |
|---|---|---|
| [Superpowers](https://github.com/obra/superpowers) | MIT | Dev mechanics (plans, worktrees, debugging, code review) |
| [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) | MIT | Product lifecycle (brainstorm, PRD, architecture, stories) |

## License

[PolyForm Shield 1.0.0](LICENSE) — use SweetClaude for any purpose, including building and selling commercial products. The only restriction: you cannot sell a product that competes with SweetClaude itself.

## Contributing

Contributions welcome. SweetClaude is built by solo developers, for solo developers. If you have ideas, skills, or improvements — open an issue or PR.

<p>
  <img src="sweetclaude-workshop.png" alt="SweetClaude Workshop" width="600" align="left">
</p>






















