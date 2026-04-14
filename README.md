<p align="left">
  <img src="sweetclaude.png" alt="SweetClaude" width="300" align="left">
</p>






# SweetClaude

An end-to-end development framework for Claude Code. From "I have an idea" to shipped, tested code — with strategy, product definition, architecture, and disciplined implementation in between.

SweetClaude is a Claude Code plugin with 52 skills that cover the full lifecycle of building software: articulating what you are building and why, defining who it is for, analyzing the competitive landscape, writing product specs, designing architecture, implementing with test-driven development, reviewing code, and shipping. It works with any language or framework.

Built by a solo developer for solo developers who want AI as a creative partner with structure and discipline — not a passive autocomplete.

## What SweetClaude Does

Most AI coding tools start at implementation. SweetClaude starts at the idea.

**Strategy** — Before you write a line of code, SweetClaude helps you articulate what you are building, who has the pain you are solving, what the competitive landscape looks like, and whether the pain is real enough to sustain a business. It walks you through building a pain thesis, defining your ideal customer profile, and crafting market messaging.

**Product** — SweetClaude guides you through structured product discovery: persona interviews one at a time, feature brainstorming with include/exclude decisions, product briefs, PRDs with testable acceptance criteria, user stories, success metrics, and scope management.

**Design** — System architecture, technical specifications, UX flows, data models, API design, service boundaries, infrastructure planning. Every design decision is recorded with context and rationale so future sessions understand why things are the way they are.

**Code** — Test-driven development at four enforcement levels. At the highest level, a test-writer agent and an implementer agent work in separate contexts — the implementer never sees the spec, only the tests. Test files are physically blocked from modification during implementation. Tests run automatically after every edit.

**Review and Ship** — Adversarial code review, security testing, mutation testing to verify your tests actually catch bugs, pre-PR quality gates, and documentation updates.

## Getting Started

### Prerequisites

| Dependency | Check | Install |
|---|---|---|
| [Claude Code](https://claude.ai/code) | `claude --version` | [Install guide](https://docs.anthropic.com/en/docs/claude-code/getting-started) |
| Git | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| [GitHub CLI](https://cli.github.com/) | `gh --version` | `brew install gh` or [cli.github.com](https://cli.github.com/) |

### Install

```bash
git clone https://github.com/carson-sweet/sweetclaude.git
```

Then start Claude Code with the plugin loaded:

```bash
claude --plugin-dir /path/to/sweetclaude
```

All 52 skills are immediately available as `/sweetclaude:skill-name` commands.

### Things to Try First

These are low-risk ways to see what SweetClaude can do before committing to a workflow.

**Ask Claude to explain the process.** Just type in natural language: "Explain the full SweetClaude process end-to-end — what are all the phases, what happens in each one, and what skills are involved?" Claude reads the master skill and gives you the full picture.

**Browse all available commands.** Run `/sweetclaude:help` to see every command organized by category with a one-line description of each.

**Organize a pile of messy documents.** If you have brainstorming notes, Claude.ai session exports, research files, or strategy documents scattered across folders, run `/sweetclaude:init` in the project and tell it you have files to onboard. It copies them (originals untouched), then you can run the reconciliation skill to inventory, categorize, and synthesize them into an organized corpus.

**Check the status of a project SweetClaude already knows about.** If you have already run init on a project, open it and run `/sweetclaude:status`. It reads your progress and tells you where you are, what is done, and what the next step would be.

**Run a competitive landscape scan.** In any project, run `/sweetclaude:strategy-competitive-analysis` and describe your space. SweetClaude researches competitors, maps the landscape, and produces a SWOT analysis. No project setup required beyond init.

**Get a code review.** On any project with code, run `/sweetclaude:code-code-review`. It reads your recent changes and gives an adversarial review focused on logic errors, edge cases, and missing error handling — not style nitpicks.

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

Run `/sweetclaude:init` and point it at the files. It copies them into a reconciliation directory. Then run the reconciliation skill to inventory every file, categorize them, and optionally synthesize organized canonical documents.

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
| `/sweetclaude:hibernate` | Freeze or thaw a project mid-phase |

### Strategy
| Command | What it does |
|---|---|
| `/sweetclaude:strategy-concept` | Articulate what this is and why it exists |
| `/sweetclaude:strategy-pain-thesis` | Structured pain analysis using 11-section framework |
| `/sweetclaude:strategy-ideal-customer-profile` | Who has this pain and will pay |
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

SweetClaude is a Claude Code plugin. When you load it with `--plugin-dir`, all 52 skills become available as slash commands. Each skill is a set of instructions that Claude follows when you invoke it.

**State tracking.** SweetClaude creates a `.sweetclaude/` directory in your project to track progress, decisions, assumptions, and scope changes. This survives between sessions — when you come back, `/sweetclaude:status` tells you where you left off.

**Safety.** Before modifying an existing project, SweetClaude creates a `pre-sweetclaude` branch. You can always revert. The `.sweetclaude/` directory is committed to your project repo — it is part of your project history, not a separate system.

**Deference levels.** You control how much SweetClaude stops for approval:
- **Collaborative** — stops after every sub-step
- **Guided** — stops at major decisions
- **Autonomous** — stops only at phase gates

**TDD enforcement.** During implementation, hooks physically block test file modifications. Tests run automatically after every source edit. At higher TDD levels, the test writer and implementer are separate AI agents that cannot see each other's reasoning.

**Language agnostic.** SweetClaude discovers your project's language, framework, test runner, and build tools automatically. It works with TypeScript, Python, Go, Rust, Java, or anything else.

## Upstream Dependencies

SweetClaude orchestrates these plugins — it does not fork or modify them:

| Dependency | License | Role |
|---|---|---|
| [Superpowers](https://github.com/obra/superpowers) | MIT | Dev mechanics (plans, worktrees, debugging, code review) |
| [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) | MIT | Product lifecycle (brainstorm, PRD, architecture, stories) |

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — free for personal use, research, education, nonprofits, and government. Not for commercial use.

## Contributing

<p align="center">
  <img src="sweetclaude-workshop.png" alt="SweetClaude Workshop" width="600">
</p>

Contributions welcome. SweetClaude is built by solo developers, for solo developers. If you have ideas, skills, or improvements — open an issue or PR.
