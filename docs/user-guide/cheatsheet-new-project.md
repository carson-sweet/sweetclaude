# SweetClaude Cheatsheet: Starting a New Project

You have an idea. Maybe it is well-formed, maybe it is a napkin sketch. SweetClaude walks you through the entire journey — from articulating the concept through shipping tested code. This is not just a coding framework. The strategic and product work that happens before you write any code is often the most valuable part.

## Before You Start

1. Install SweetClaude (if you have not already) — inside Claude Code run:
   ```
   /plugin marketplace add carson-sweet/sweetclaude@main
   /plugin install sweetclaude@sweetclaude-stable
   ```
2. Create an empty folder for your project and open Claude Code in it
3. Run:
   ```
   /sweetclaude:go
   ```

That is it. SweetClaude takes over from here and walks you through each step.

## What Happens Next

### Step 1: Project Setup

SweetClaude creates:
- A git repository (if you want one)
- A `.sweetclaude/` folder that tracks your progress, decisions, and configuration
- A `strategy/` folder for strategic documents
- A `CLAUDE.md` file that teaches future AI sessions about your project

### Step 2: Concept Articulation

SweetClaude asks you to describe your idea in your own words. Then it helps you sharpen it into a clear statement: what is this, what problem does it solve, why does it matter, and what is it NOT. It will challenge your framing — not to be difficult, but because the best concepts survive scrutiny.

### Step 3: Product Discovery (Deep Dive)

SweetClaude runs `/sweetclaude:plan product-discovery` to establish what is being built, for whom, and why. You choose the depth:
- **Quick intent** — high-level framing in one pass
- **Standard** — pain and audience with structured prompts
- **Full pain thesis** — 11-section structured analysis, research-backed

At any depth, SweetClaude can analyze competitors via `/sweetclaude:plan product-competition` and define user personas via `/sweetclaude:plan user-personas`.

**Output:** Discovery artifacts in `strategy/` — depth depends on level chosen

### Step 4: Handoff

At this point you have a strategic foundation: concept, discovery artifacts, personas, and feature set. SweetClaude tells you what is available next and lets you decide when to continue.

## What Comes After (When You Are Ready)

SweetClaude does not push you forward. You move to the next phase when you are ready.

### Product Definition
- `/sweetclaude:plan product-brief` — strategic product brief, outline-first, scales to available input
- `/sweetclaude:plan product-prd` — full PRD with functional requirements and epics
- `/sweetclaude:plan product-manage-scope` — track what is in and out of scope

### Design
- `/sweetclaude:design design-user-flows` — convert user stories into UX/UI flows
- `/sweetclaude:design design-architecture` — system architecture
- `/sweetclaude:design design-tech-spec` — technical specification
- `/sweetclaude:design design-data-model` — schema and entity design
- `/sweetclaude:design design-api-design` — endpoint contracts
- `/sweetclaude:design design-ux` — user experience flows

### Planning
- `/sweetclaude:plan product-user-stories` — user stories with acceptance criteria
- `/sweetclaude:build product-user-tdd-tests` — convert stories to Gherkin test specs
- `/sweetclaude:build product-sprint-plan` — plan a sprint from the backlog

### Implementation
- `/sweetclaude:build code-feature` — build a new feature end-to-end (Gherkin → TDD Level 3 → PR)
- `/sweetclaude:build code-issue` — implement a GitHub issue end to end
- `/sweetclaude:maintain code-debt` — clean up tech debt (tests before touch)

### Review and Ship
- `/sweetclaude:build code-review` — code, security, and compliance review (menu at start)
- `/sweetclaude:build code-testing` — run tests, mutation, security review, and/or PR pre-check

### Milestones
- `/sweetclaude:plan product-milestones add` — create a roadmap target with success criteria
- `/sweetclaude:plan product-milestones review` — see all milestones grouped by Now / Next / Later
- `/sweetclaude:plan product-milestones link US-XXX MS-XXX` — attach a story to a milestone
- `/sweetclaude:plan product-milestones blockers MS-XXX` — what is stopping progress
- `/sweetclaude:plan product-milestones complete MS-XXX` — mark achieved, capture follow-ups

## What SweetClaude Can Do If You Ask

These are not part of the automatic flow. They are available anytime.

- **Competitive analysis** (`/sweetclaude:plan product-competition`) — competitive analysis at three depth levels — survey, matrix, or feature-deep
- **Market messaging** (`/sweetclaude:plan product-market-messaging`) — craft elevator pitches and value propositions per audience
- **Meeting prep** (`/sweetclaude:utils misc-meeting-prep`) — prepare agenda, talking points, and anticipated questions for a specific meeting
- **Research** (`/sweetclaude:plan product-research`) — market or technical research with evidence and sources
- **Academic paper** (`/sweetclaude:plan documents-academic-research`) — full six-phase pipeline from thesis through submission
- **Narrative arc** (`/sweetclaude:plan documents-narrative-arc`) — build a knowledge graph connecting your claims, evidence, and objectives
- **Decision tracking** (`/sweetclaude:design design-manage-decisions`) — record any decision with context and rationale, queryable later
- **Positioning statement** (`/sweetclaude:plan product-positioning-statement`) — for/who/that/unlike framework
- **Corpus pipeline and RAG search** (`/sweetclaude:utils document-corpus`) — organize messy files into canonical documents with full provenance (consolidate → triage → reconcile → promote), then index for semantic search. Presents a menu; pick the step you need or check status first.
- **Update SweetClaude** — update the Claude Code plugin package, restart Claude Code, then run `/sweetclaude:configure update` to sync framework files inside the installed channel
- **Version bumping** — run `scripts/bump-version.sh patch|minor|major` to bump version explicitly; no automatic bump on commit

## Tips

- **You can stop and resume anytime.** SweetClaude saves your progress in `.sweetclaude/`. Run `/sweetclaude:go` to pick up exactly where you left off — it reads your phase state and acts.
- **You can skip ahead.** The pipeline is a guide, not a cage. If you want to jump straight to architecture, do it.
- **You can go back.** Revisiting earlier phases is normal. New information during design might change your pain thesis. That is how good work happens.
- **You control the pace.** SweetClaude never pushes you to the next step. It waits until you say you are ready.
- **The strategic work is optional but valuable.** You can skip straight to code if you want. But the projects that go through strategy and product definition first tend to build the right thing, not just build a thing.
