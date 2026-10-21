# SweetClaude Cheatsheet: Adopting an Existing Project

**Version:** 1.1
**Date:** 2026-10-21

You have a codebase. Maybe it is well-organized with tests and docs. Maybe it is a mess. Maybe it is somewhere in between. SweetClaude meets you where you are and adds structured process without disrupting what you have built.

SweetClaude is not just a coding tool. Even on an existing project, the strategic and product skills can add significant value — articulating your positioning, analyzing competitors, preparing for meetings, or organizing scattered documents from previous brainstorming sessions.

## Before You Start

1. Install SweetClaude (if you have not already) — inside Claude Code run:
   ```
   /plugin marketplace add carson-sweet/sweetclaude@main
   /plugin install sweetclaude@sweetclaude-stable
   ```
2. Open Claude Code in your project folder
3. Run:
   ```
   /sweetclaude:configure init
   ```

Init installs the SweetClaude files and runs setup. After that, `/sweetclaude:go` reads your state and proposes the next item.

## What Happens Next

### Step 1: Safety Snapshot

Before SweetClaude writes any file, it creates a `pre-sweetclaude` branch from your current state. If you ever want to undo everything SweetClaude did, check out that branch. If the branch cannot be created, for example because it already exists or the repository has no commits, SweetClaude stops and writes nothing until the cause is resolved.

### Step 2: Project Scan

SweetClaude looks at your project with a quick read-only pass: a file listing, the first lines of your README, and the last ten lines of `git log`. If the codebase looks inherited or disorganized, setup runs a fuller assessment instead and shows you its plan before changing anything.

### Step 3: Current State Interview

SweetClaude asks three questions about your project, one at a time:
1. What is the project name? (pre-filled from `package.json` or the README when found)
2. What stage is it at: early prototype, active development, approaching launch, or in production?
3. Which issue tracker should hold project issues: this repository (`local`) or GitHub Issues (`github`)?

It then asks which working mode fits: Flow, Kanban, Shape Up, or Agile.

Your stage answer sets `version_stage` in `.sweetclaude/state/sweetclaude.yaml`: early prototype is IDEA, active development is ALPHA, approaching launch is BETA, and in production is GA. SweetClaude does not place the project in a pipeline phase.

### Step 4: Setup

SweetClaude creates:
- A `.sweetclaude/` folder with `state/sweetclaude.yaml`, plans, and a `product/` tree (`backlog/`, `stories/`, `milestones/`)
- A SweetClaude section appended to your `CLAUDE.md` (the file is created if missing; existing content is never overwritten)

### Step 5: Optional Features

Setup ends by showing a status line and offering optional features. You pick the ones you want and SweetClaude onboards each. It does not choose a first action for you; run `/sweetclaude:go` to see the proposed next item.

## What You Can Do From Here

### Continue Building (Code Track)

If you are in the middle of implementation, these are your daily tools:

| Command | When to use it |
|---|---|
| `/sweetclaude:build code-feature` | Build a new feature end-to-end (Gherkin → TDD Level 3 → PR) |
| `/sweetclaude:build code-issue` | Implement a GitHub issue end to end |
| `/sweetclaude:maintain code-debt` | Clean up tech debt (tests before touch, always) |
| `/sweetclaude:build code-testing` | Run tests, mutation, security review, and/or PR pre-check |
| `/sweetclaude:build code-review` | Code, security, and compliance review |
| `/sweetclaude:plan product-milestones` | Track roadmap targets across strategy and product work |

### Fix Configuration Issues

If SweetClaude detected mismatches between its configuration and your actual project state:

```text
/sweetclaude:configure doctor
```

Doctor scans state, hooks, storage, migration, config, files, onboarding, and environment. It proposes fixes, routes unsafe legacy migration states to `/sweetclaude:configure recover`, and does not mutate files until the relevant safety flow confirms the action.

### Add Strategic Foundation (Even Mid-Project)

Your project may already have code, but you might not have documented the strategy behind it. SweetClaude can help with this at any time — it is not too late.

**Articulate what you are building:**
```
/sweetclaude:plan product-discovery
```
Establish what is being built, for whom, and why. Three depth levels from quick intent to full pain thesis. Even mid-project, making this explicit helps you prioritize features, write better marketing copy, and have sharper investor conversations.

**Define your users:**
```
/sweetclaude:plan user-personas
```
Who specifically has this pain? Define users — who they are, what they need to do, and what success looks like. Includes triggers and deal-breakers.

**Analyze the competitive landscape:**
```
/sweetclaude:plan product-competition
```
Who else operates in this space, how they are positioned, where the gaps are. Three depth levels — survey, matrix comparison, or feature-deep analysis.

**Craft market messaging:**
```
/sweetclaude:plan product-market-messaging
```
Elevator pitches, value propositions, and key messages per audience.

**Define positioning:**
```
/sweetclaude:plan product-positioning-statement
```
For/who/that/unlike framework.

### Organize Scattered Documents

If you have strategy documents, brainstorming exports, meeting notes, or research scattered across folders, Claude.ai sessions, or Google Drive downloads, run:

```
/sweetclaude:utils document-corpus
```

The skill presents a menu: consolidate raw files → triage (classify each file) → reconcile (draft canonical documents) → promote (finalize with provenance, archive, RAG index). Select **Status** at any point to see where the pipeline stands. The pipeline enforces ordering — skipping steps produces degraded or misleading results, and the skill explains why if you try. Every canonical document traces back to its source files.

This is especially useful for projects that started with lots of brainstorming in Claude.ai but never organized the output.

### Prepare for Meetings

```
/sweetclaude:utils misc-meeting-prep
```

Tell it who you are meeting, when, and what the purpose is. It pulls context from your strategy documents, drafts an agenda, talking points with confidence levels, anticipated questions with prepared responses, and leave-behinds. After the meeting, it captures your debrief.

### Write or Improve Documentation

```
/sweetclaude:utils documents-update-docs
```

After implementation changes behavior, this scans existing docs for stale references and proposes updates.

```
/sweetclaude:design design-manage-decisions
```

Record architecture or design decisions with context, options considered, and rationale. Query them later: "Why did we choose X?"

### Track Roadmap Milestones

```
/sweetclaude:plan product-milestones add
```

Create outcome-driven roadmap targets like "Exit Stealth" or "MVP Shipped" with measurable success criteria. Link user stories and backlog items to milestones. Track progress, identify blockers, and mark milestones achieved with follow-up capture. Sprint planning automatically reports which milestones a sprint advances.

### Set Up Semantic Search

```
/sweetclaude:utils document-corpus
```

Index your project documents for semantic search. Ask questions about your codebase and docs by meaning, not just keyword matching.

## Understanding Deference Levels

When SweetClaude starts, it asks how much control you want:

- **Collaborative** — stops after every sub-step. Best when you want to understand everything SweetClaude is doing.
- **Guided** — stops at major decisions. Best for daily work.
- **Autonomous** — stops only at phase gates. Best when you trust the process and want speed.

You can change this mid-session.

## Tips

- **The safety branch is your insurance.** `pre-sweetclaude` captures your project state before SweetClaude touched anything. If things go wrong, `git checkout pre-sweetclaude` gets you back.
- **`.sweetclaude/` is part of your project.** Commit it to git, except the guardian flag and recovery snapshots (`.sweetclaude/state/recovery-runs/`), which are derived. It contains your project state, plans, and backlog — valuable project context.
- **You do not have to use every skill.** If you only want TDD enforcement, just use the code skills. If you only want strategic help, just use the strategy skills. There is no required sequence.
- **Strategic work on existing projects is valuable.** Many projects have implicit strategy that was never documented. Making it explicit helps you prioritize, communicate with stakeholders, and make better decisions.
- **SweetClaude does not judge your code.** When adopting a project, it treats your codebase like an archaeologist treats a dig site — understanding before changing, respecting what is already there.
- **A short status line appears at session start.** It shows the project, the stage, and the active item, then asks whether to work on something or review the plan. Run `/sweetclaude:go` to pick up where you left off.
- **Keep SweetClaude updated.** Update the Claude Code plugin package, restart Claude Code, then run `/sweetclaude:configure update` to sync framework files inside the installed channel.
