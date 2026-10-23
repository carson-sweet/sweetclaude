<img src="sweetclaude.png" alt="SweetClaude" width="180" style="display:block;margin-left:0;">

# SweetClaude

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE) [![Version](https://img.shields.io/badge/version-5.1.2-blue)](https://github.com/carson-sweet/sweetclaude/releases/tag/v5.1.2)

## TL;DR

Start Claude Code and run:
```
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
(restart Claude Code)
/sweetclaude:help

/sweetclaude:go give me an overview of what you can do
```

## What It Is

A software development partner for the full project lifecycle — from the first idea through design, implementation, testing, and ship. SweetClaude teaches itself about your project and preferences through conversation, then applies those learnings to deal with the less-fun parts of the project.

SweetClaude works well when structure, traceability, and product thinking is valued over raw coding speed. It's the wrong tool if you **just** want to go faster — we suggest [GStack](https://github.com/garry-tan/gstack) if speed is your primary goal. It was built for software development, but has also been used successfully for academic research, product marketing strategy, and other knowledge-intensive work.

*EXPERIMENTAL: If you want fast and disciplined, there is the experimental (and therefore potentially unpredictable) [John Wick mode](#operating-modes).*

Requires [Claude Code](https://claude.ai/code) and an Anthropic subscription. We recommend using a model designed for day-to-day work (e.g. Sonnet 4.6 at the time of writing) although you can take it up to top-tier frontier models — just be mindful that models like Opus burn through your Anthropic usage way faster. Our honest experience is that Opus is overkill for most anything except perhaps initial product discovery and brainstorming, or if Sonnet gets stuck on a tough problem. You can always switch models mid-stream with the Claude Code command  `/model` .

Install SweetClaude (below) then run `/sweetclaude:help` to get a guided walk-through of what it is, how it works, and whether it's right for your project before touching a single file.



## Key Design Principles

There's a massive number of Claude Code plugins out there. To help you decide if SweetClaude might be one that's helpful, here are the top principles used when designing SweetClaude:

* **Successful projects take more than code.** If you're here you probably already know this, but really thinking through what you're building, for who, why, and how they'll use it results in a good product that delivers value to users. Unfortunately, that part is a lot less fun than vibe-coding — it's real work. SweetClaude is primarily about taking care of that work — and a bunch of other lessfun work — in a structured, reliable way.
* **Hide the complexity**. SweetClaude has over 100 skills built natively on Claude Code's Skills framework and Anthropic's multi-agent architecture. These skills compose into dynamic, situation-driven workflows across four operating modes. *<u>Few people want to learn all that</u>.*  To hide the complexity, SweetClaude uses a conversational interface with just a few commands as entry points, and an orchestrator skill does the rest (you can also name a specific workflow after its category, such as `/sweetclaude:configure doctor`).
* **Adapt to user preferences as they evolve.** AI assisted vibe-coding is fantastic for rapid experimentation and iteration to see if an idea is viable. An assistant framework should be able to capture things passively without killing the vibe and then be able to use what it captured to dial up the structure and discipline as needed, based on what it learned in the vibe phase. The framework adjusts to the user's preferences — not the other way around — and is designed to dial up or dial back the level of structure mid-project as needed.



## Quick Start

Start Claude Code in your project folder as you normally would, then inside Claude Code run these commands:

```
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
(restart Claude Code)
/sweetclaude:help
```


## Basic Usage

Inside Claude Code, the primary command is `/sweetclaude:go` which keeps things simple. Use natural language after the command to drive things. The  `/sweetclaude:go`  command acts as a primary interface (sometimes the only command needed) to SweetClaude's work state, skills, and workflow orchestration, so you don't have to know every skill command — which would be madness.

Use `/sweetclaude:go` followed by what you want to do, in plain English — "show me milestones and sprints", "let's see the backlog", I want to start building X", "what should I work on next". Or use `/sweetclaude:go` with no arguments to just pick up where you left off. SweetClaude will ask questions if needed and route work into its workflow library — it handles the red tape, you do the creating.

You can use SweetClaude to start a new effort from scratch, or have it adopt an existing project. Just point to any documents you might have — backlog, roadmaps, design, etc. — it will assess and migrate what you have and then help you fill in the gaps.

A few other key commands to know about are:

* `/sweetclaude:help` — the guided tour. Walks you through what SweetClaude is, how it works, and whether it's right for your project before touching a single file.
* `/sweetclaude:status` — project dashboard. Active work item, phase, roadmap, backlog, recent commits at a glance.
* `/sweetclaude:configure` — configure SweetClaude or diagnose an unexpected installation, hook, state, migration, or onboarding problem.


We've tried to design SweetClaude to be intuitive, but additional documentation is available if needed or desired:

→ [User guide, update, and migration](docs/user-guide/index.md)

→ [Full skills reference](docs/user-guide/skills-reference.md)



## First Steps

Once SweetClaude is installed, here are some things to try. You'll quickly get oriented.

* `/sweetclaude:go give me a quick overview of what you can do`
* `/sweetclaude:go tell me about the product development lifecycle phases you use`
* `/sweetclaude:go tell me about the differences in flow mode, kanban mode, shape up mode, and agile mode`
* `/sweetclaude:go help me choose the best mode for my project`
* `/sweetclaude:go give me a breakdown of all skills by product lifecycle phase`
* `/sweetclaude:go tell me about your RAG enabled design and doc management`
* `/sweetclaude:go explain how you would onboard my existing project`



## Operating Modes

SweetClaude has four operating modes that support everything from vibe-coding hobby projects through enterprise-class B2B product development. It also has one experimental mode that isn't recommended for anything that matters (maybe initial prototyping). Those modes are:

* **Flow** — the default mode, usually the right mode to start any new project. Can be the right mode for quick experiments or non-critical projects. No phases, no gates, no ceremony. SweetClaude observes quietly, builds what you ask, and collects thin artifacts in the background — personas, decisions, scope notes — without interrupting your momentum. If you decide to dial up the structure, everything it captured is already there. Best for: early-stage exploration, side projects, and any time you need to move fast and figure out what you're building.
* **Kanban** — continuous delivery with one hard rule: no more than three things in progress at once. No sprints, no planning ceremonies, no velocity calculations. Work flows from backlog to done at whatever pace makes sense. SweetClaude enforces the WIP limit and surfaces blocked items before they quietly pile up. The wip-limit hook denies activating a fourth issue while three are in progress. Best for: maintenance work, steady feature delivery, and solo developers who want lightweight structure without sprint overhead.
* **Shape Up** — six-week cycles where appetite is fixed and scope is variable. Work starts with a pitch: what problem are we solving, what's the rough shape of the solution, and what won't we build? A betting table decides what gets the next cycle. No backlog grooming, no story points, no carry-over. If it doesn't ship in the cycle, it goes back to the pile. Best for: product-focused work where you want strong scope discipline and a natural forcing function against gold-plating. SweetClaude enforces the mode's rules: implementation is blocked until the betting table approves the pitch, and advancing past VERIFY requires a recorded ship/no-ship decision on the cycle.
* **Agile** — sprint-based delivery with a full planning, execution, and retrospective cycle. Each sprint anchors to a milestone and has an explicit active/closed state. SweetClaude enforces the mode's rules: implementation is blocked when no sprint is active, and work is warned when the issue is outside the active sprint — the warning surfaces as context, never a denial. Velocity is tracked on close and feeds into future planning. Best for: projects with defined delivery commitments, multiple contributors, or any situation where stakeholders expect predictable, time-boxed output.
* **John Wick mode** — an experiment at the intersection of vibe-coding and disciplined product development. John Wick mode goes fully autonomous after a short project discovery cycle. Intensely disciplined — TDD Level 3, subagent isolation, QA caucus, hard gates at key decisions. Not for everyday use — but no other mode comes close for maximum automation. Fast, independent, admittedly dangerous - but disciplined. No loose ends. Ask `/sweetclaude:build` to start it. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.)

Switch modes at any time through `/sweetclaude:configure`. SweetClaude snapshots your current state before any transition. It's also best to take a Git snapshot for belt-and-suspenders safety - SweetClaude can do that for you too, as well as roll things back if needed. Just tell SweetClaude what you need to do.



## Major Features

- **Discovery-first pipeline** — Compliance requirements (GDPR, HIPAA, PCI DSS) flow from user and data discovery into architecture and code review automatically — not a checkbox at the end.
- **Compliance-ready from day one** — SOC 2, GDPR, HIPAA, and PCI DSS requirements surface automatically during discovery, not as an afterthought. For regulated industries, SweetClaude produces the artifacts your auditor needs: decision logs, gate records, and traceability maps.
- **Enforced TDD at four levels** — At the highest level, test writer and implementer are separate AI agents. Test files are physically blocked from modification during implementation by hooks. Tests run after every source edit.
- **Persistent phase state** — `.sweetclaude/` tracks phase, decisions, and scope changes in git. Return after weeks and `/sweetclaude:go` re-orients without re-explaining.
- **Mockup pipeline** — Design UI components in an isolated Vite + React sandbox before touching production code. Graduate approved mockups with acceptance criteria extracted automatically.
- **Local semantic search over your design documents** — LanceDB-powered RAG, fully offline, no API keys, no external services. Index your architecture docs, data model, and product decisions so both you and SweetClaude can ask questions and get canonical answers instantly. Setup takes one command.
- **Corpus management** — Four-step pipeline (consolidate → triage → reconcile → promote) for messy document collections. Pairs with local RAG for full document lifecycle management.
- **Behavioral contracts** — 16 instruction-guided behavioral contracts. A transcript judge scores 6 of them, 4 cannot be judged from transcripts, and a routing suite checks that requests reach the right workflow. Hook-enforced properties are tracked separately from the 16.



## How It Works

SweetClaude is implemented as a Claude Code plugin. After install, nine public commands are available in every session: `go`, `plan`, `design`, `build`, `maintain`, `configure`, `utils`, `status`, and `help`. Each workflow command loads only the relevant part of the Tier 2 library; individual library workflows are intentionally not slash-addressable. Load for a single session with `--plugin-dir` without a global install.

TDD hooks physically block test file modification during implementation and run tests automatically after every source edit. At higher TDD levels, test writer and implementer are separate AI agents — the implementer never sees the spec, only failing tests.

→ [Full architecture and design decisions](docs/user-guide/how-it-works.md)



## Common Commands

These nine commands are the whole command surface. Add a workflow name or a plain-English request after any of them. You can also refer to the [complete skills reference](docs/user-guide/skills-reference.md).

### Primary
| Command | What it does |
|---|---|
| `/sweetclaude:go` | Pick up where you left off. Reads state, checks phase exit criteria, routes to the right skill. Pass plain-English arguments to describe what you want. |
| `/sweetclaude:status` | Project status dashboard — active work item, phase, roadmap, backlog. |
| `/sweetclaude:help` | Conversational help — describe what you want to do, browse features, or ask questions |

### Workflow entry points
| Command | What it does |
|---|---|
| `/sweetclaude:plan` | Product strategy, research, scope, roadmaps, and planning. |
| `/sweetclaude:design` | Product, UX, and technical design. |
| `/sweetclaude:build` | Delivery, testing, deployment, and project work. |
| `/sweetclaude:maintain` | Defects, debt, security patches, recovery, and postmortems. |
| `/sweetclaude:configure` | Setup, settings, lifecycle administration, migration, and diagnostics. |
| `/sweetclaude:utils` | Cross-workflow utilities such as corpus work, dashboards, recap, and exports. |

`/sweetclaude:go` can route to every workflow automatically. The library workflows that do the focused work remain internal, which keeps the slash-command surface small and coherent.

→ [All skills by category](docs/user-guide/skills-reference.md)



## Dependencies

| Dependency | License | Required | Role |
|---|---|---|---|
| [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag) | MIT | Optional | Local semantic search — per-project vector index, no external services |

For dependency risk, failure modes, and contingency plans → [Platform Dependencies](docs/user-guide/platform-dependencies.md)



## License

[GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0-or-later) — free to use, modify, and distribute. No restrictions for personal or commercial tools you build — you just can't monetize SweetClaude directly, via distribution or SaaS. Full terms in [LICENSE](LICENSE).

**Enterprises**: use the [contact form on the project owner's website](https://www.carsonsweet.com) to inquire about licensing or customizations for your organization's needs.



## Migrating from Older Channels

<!-- docs-claims: ignore slash:/sweetclaude:doctor -->
**From 4.x:** Run `/plugin marketplace update sweetclaude-stable`, then `/plugin update sweetclaude@sweetclaude-stable`, then restart Claude Code. After the restart, run `/sweetclaude:configure update` in each project. Your project data does not change. SweetClaude 5.0 replaces the one-command-per-workflow menu with nine commands; for example `/sweetclaude:doctor` is now `/sweetclaude:configure doctor`. Claude Code reports old commands as unknown; `/sweetclaude:help` lists the new ones. See [Upgrading to 5.0](docs/user-guide/upgrading-to-5.md) for the full mapping. 4.x receives no further releases.

**From the 4.x beta channel:** The beta channel is retired. Switch in this order so SweetClaude stays installed throughout (both channels are installed briefly, and all three steps finish before you restart Claude Code):

```
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
/plugin marketplace remove sweetclaude-beta
```

Removing the beta marketplace uninstalls its plugin, so add and install stable first. Then restart Claude Code and run `/sweetclaude:configure update` on the stable channel.

Beta releases before `v4.1.9-beta` had known update/recovery risks. See [4.x Beta Rescue](docs/user-guide/beta-rescue.md) if an existing beta install reports `4.1.8-beta` or older.

**From 3.x:** The 3.x channel has been renamed to `sweetclaude-legacy`. To move a 3.x install onto the stable line:

```
/plugin marketplace remove sweetclaude-stable
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
```

Old 3.x installs registered their marketplace as `sweetclaude-stable`, so remove it first. Then restart Claude Code and run `/sweetclaude:configure doctor` in each project; doctor routes legacy project state to recovery or migration, and update does not migrate project data.

To stay on 3.x, re-add the renamed legacy marketplace (a one-time step — the marketplace name changed):

```
/plugin marketplace remove sweetclaude-stable
/plugin marketplace add carson-sweet/sweetclaude@stable-3.x
/plugin install sweetclaude@sweetclaude-legacy
```

→ [Legacy 3.x documentation](https://github.com/carson-sweet/sweetclaude/blob/stable-3.x/docs/user-guide/install.md)



## Known Issues

**SweetClaude startup message appears twice.** When Claude Code starts or restarts after context compression, you may see the SweetClaude activation message printed twice:

```
SessionStart:startup says: SweetClaude is active. Type /sweetclaude:go to begin.
SessionStart:startup says: SweetClaude is active. Type /sweetclaude:go to begin.
```

This is a [known Claude Code bug](https://github.com/anthropics/claude-code/issues/24115) where plugin hooks are loaded from both the marketplace source directory and the installed cache simultaneously, causing each SessionStart event to fire twice. There is no stable workaround. It is annoying but harmless — SweetClaude is only activated once.

## Contribute

Contributions welcome. SweetClaude is built by solo developers, for solo developers.

**Looking for a technical co-maintainer.** SweetClaude is currently maintained by one person. The areas that need a second reviewer — the hook system, migration registry, and orchestration layer — require someone who understands how the phase pipeline works end to end. If you have read through the codebase and want meaningful ownership of a growing open-source project, open an issue introducing yourself. See [what requires full framework knowledge](CONTRIBUTING.md#what-requires-full-framework-knowledge) for the scope.

For skill improvements, documentation, walkthroughs, and examples — read [CONTRIBUTING.md](CONTRIBUTING.md) for where to start. Questions and ideas belong in [GitHub Discussions](https://github.com/carson-sweet/sweetclaude/discussions). Bugs and PRs go to Issues.


<img src="sweetclaude-workshop.png" alt="SweetClaude Workshop" width="600" style="display:block;margin-left:0;">



## Support

If you're getting value from SweetClaude, consider [buying me a coffee](https://ko-fi.com/carsonsweet).

Which in reality means you're moving dollars from my coffee budget to [my dog Smushford's](http://instagram.com/smushford) treat budget.

Smushford thanks you.

<img src="smushford.png" alt="Smushford Wellington DuBois III" width="400" style="display:block;margin-left:0;">
