# SweetClaude Cheatsheet: Adopting an Existing Project

You have a codebase. Maybe it is well-organized with tests and docs. Maybe it is a mess. Maybe it is somewhere in between. SweetClaude meets you where you are and adds structured process without disrupting what you have built.

SweetClaude is not just a coding tool. Even on an existing project, the strategic and product skills can add significant value — articulating your positioning, analyzing competitors, preparing for meetings, or organizing scattered documents from previous brainstorming sessions.

## Before You Start

1. Open your project folder
2. Start Claude Code with SweetClaude loaded:
   ```bash
   cd your-project
   claude --plugin-dir /path/to/sweetclaude
   ```
3. Run:
   ```
   /sweetclaude:sherpa-adopt
   ```

## What Happens Next

### Step 1: Safety Snapshot

Before SweetClaude changes anything, it creates a `pre-sweetclaude` branch from your current state. If you ever want to undo everything SweetClaude did, check out that branch. This is required — SweetClaude will not proceed without it.

If your project does not have git set up, SweetClaude offers to initialize it first.

### Step 2: Project Scan

SweetClaude scans your project and reports what it finds:
- **Code:** languages, frameworks, file count, test coverage
- **Tests:** do they exist, what framework, how many
- **Docs:** README, CLAUDE.md, architecture docs, ADRs, specs
- **Issues:** open GitHub issues and PRs
- **Strategy:** any positioning, competitive analysis, or research docs

This is read-only. Nothing changes.

### Step 3: Current State Interview

SweetClaude asks you four questions, one at a time:
1. Is this project early, mid-build, or mature?
2. What are you working on right now?
3. What is the biggest problem or frustration?
4. Is there anything messy, undocumented, or worrying?

### Step 4: Pipeline Positioning

Based on the scan and your answers, SweetClaude proposes where your project sits in the development lifecycle:
- Just an idea → DISCOVER
- Has specs but no code → PLAN or DESIGN
- Actively building → IMPLEMENT
- Code exists but untested → IMPLEMENT (lock behavior with tests)
- Feature-complete → VERIFY
- Shipping → use `/sweetclaude:new-task` for each piece of work

You confirm or adjust. SweetClaude does not assume it knows better than you.

### Step 5: Setup

SweetClaude creates:
- `.sweetclaude/` folder with state tracking, decision log, and traceability
- `strategy/` folder structure (empty, ready for strategic work if you want it)
- Updates to CLAUDE.md if needed

### Step 6: First Action

If you mentioned a problem or frustration in Step 3, SweetClaude suggests a specific first action using a specific command. Otherwise, it shows you the available commands and waits.

## What You Can Do From Here

### Continue Building (Code Track)

If you are in the middle of implementation, these are your daily tools:

| Command | When to use it |
|---|---|
| `/sweetclaude:code-work-issue` | Implement a GitHub issue end to end |
| `/sweetclaude:code-tdd` | Write a feature with test-driven development |
| `/sweetclaude:code-work-debt` | Clean up tech debt (tests before touch, always) |
| `/sweetclaude:code-pr-precheck` | Check everything before opening a PR |
| `/sweetclaude:code-code-review` | Get an adversarial code review |
| `/sweetclaude:code-qa-testing` | Run tests and get a clean pass/fail report |

### Fix Configuration Issues

If SweetClaude detected mismatches between its configuration and your actual project state:

```
/sweetclaude:fix-config
```

This audits CLAUDE.md accuracy, phase state, file locations, and empty registers. It proposes fixes for your approval — it does not change anything without asking.

### Add Strategic Foundation (Even Mid-Project)

Your project may already have code, but you might not have documented the strategy behind it. SweetClaude can help with this at any time — it is not too late.

**Articulate what you are building:**
```
/sweetclaude:strategy-concept
```
Produces a clear concept statement: what is this, what problem does it solve, why does it matter.

**Analyze the pain you are solving:**
```
/sweetclaude:strategy-pain-thesis
```
Walks through 11 sections of structured pain analysis. Even if you have been building for months, making the pain explicit helps you prioritize features, write better marketing copy, and have sharper investor conversations.

**Define your ideal customer:**
```
/sweetclaude:strategy-ideal-customer-profile
```
Who specifically has this pain? Demographics, behaviors, triggers, deal-breakers.

**Analyze the competitive landscape:**
```
/sweetclaude:strategy-competitive-analysis
```
Who else operates in this space, how they are positioned, where the gaps are.

**Compare features against competitors:**
```
/sweetclaude:product-feature-competitive
```
Build a feature matrix. Identify table-stakes features and differentiation opportunities.

**Craft market messaging:**
```
/sweetclaude:strategy-market-messaging
```
Elevator pitches, value propositions, and key messages per audience.

**Define positioning:**
```
/sweetclaude:product-positioning-statement
```
For/who/that/unlike framework.

### Organize Scattered Documents

If you have strategy documents, brainstorming exports, meeting notes, or research scattered across folders, Claude.ai sessions, or Google Drive downloads:

1. Run `/sweetclaude:init` and tell it you have files to onboard
2. Point it at the folder with your messy files
3. It copies them into `strategy/reconciliation/` (originals untouched)
4. Run the reconciliation process to inventory every file, categorize them, and optionally synthesize organized canonical documents

This is especially useful for projects that started with lots of brainstorming in Claude.ai but never organized the output.

### Prepare for Meetings

```
/sweetclaude:strategy-meeting-prep
```

Tell it who you are meeting, when, and what the purpose is. It pulls context from your strategy documents, drafts an agenda, talking points with confidence levels, anticipated questions with prepared responses, and leave-behinds. After the meeting, it captures your debrief.

### Write or Improve Documentation

```
/sweetclaude:design-update-docs
```

After implementation changes behavior, this scans existing docs for stale references and proposes updates.

```
/sweetclaude:design-manage-decisions
```

Record architecture or design decisions with context, options considered, and rationale. Query them later: "Why did we choose X?"

### Set Up Semantic Search

```
/sweetclaude:rag-index
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
- **`.sweetclaude/` is part of your project.** Commit it to git. It contains your decision history, assumptions, and progress — valuable project context.
- **You do not have to use every skill.** If you only want TDD enforcement, just use the code skills. If you only want strategic help, just use the strategy skills. There is no required sequence.
- **Strategic work on existing projects is valuable.** Many projects have implicit strategy that was never documented. Making it explicit helps you prioritize, communicate with stakeholders, and make better decisions.
- **SweetClaude does not judge your code.** When adopting a project, it treats your codebase like an archaeologist treats a dig site — understanding before changing, respecting what is already there.
- **Run `/sweetclaude:status` at the start of each session.** It tells you where you left off and what the next step is.
