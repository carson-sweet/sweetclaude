# SweetClaude Cheatsheet: Starting a New Project

**Version:** 1.0
**Date:** 2026-10-21

You have an idea. Maybe it is well-formed, maybe it is a napkin sketch. SweetClaude supports the entire journey — from articulating the concept through shipping tested code. This is not just a coding framework. The strategic and product work that happens before you write any code is often the most valuable part.

## Before You Start

1. Install SweetClaude (if you have not already) — inside Claude Code run:
   ```
   /plugin marketplace add carson-sweet/sweetclaude@main
   /plugin install sweetclaude@sweetclaude-stable
   ```
2. Create an empty folder for your project and open Claude Code in it
3. Run:
   ```
   /sweetclaude:configure init
   ```

Init installs the SweetClaude files and runs setup. After that, `/sweetclaude:go` reads your state and proposes the next item.

## What Happens Next

### Step 1: Project Setup

Setup asks for the project name, a one-sentence description, where issues should live (this repository or GitHub Issues), and a working mode. It creates:
- A `.sweetclaude/` folder that tracks your progress, decisions, and configuration
- A `.sweetclaude/product/` tree with `backlog/`, `stories/`, and `milestones/` folders
- A `.sweetclaude/state/sweetclaude.yaml` file with the project at the IDEA stage

### Project Instructions File

Setup also appends a short SweetClaude section to your project's `CLAUDE.md`, creating the file if it does not exist, so future AI sessions know the project is managed with SweetClaude. Existing content is never overwritten.

### Step 2: Feature Selection

Setup hands off to optional feature selection. You choose which optional features to turn on, such as milestones and the backlog, and SweetClaude onboards each one you pick. Nothing else runs automatically after this.

### Step 3: Product Discovery

After feature selection, start discovery yourself with `/sweetclaude:plan product-discovery`. It establishes what is being built, for whom, and why. You choose the depth:
- **L1 — Intent and boundaries** — high-level framing in one pass
- **L2 — Problem and success** — pain and audience with structured prompts
- **L3 — Full pain thesis** — the deepest level, with up to 17 research-backed questions

At any depth, you can analyze competitors via `/sweetclaude:plan product-competition` and define user personas via `/sweetclaude:plan user-personas`.

**Output:** `.sweetclaude/state/discovery.yaml` and `.sweetclaude/state/compliance-context.yaml`

### Step 4: Handoff

At this point you have a strategic foundation: discovery output, personas, and feature set. Run `/sweetclaude:go` to see what is available next and decide when to continue.

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
- `/sweetclaude:plan product-milestones link ISSUE-NNN MS-NNN` — attach an issue to a milestone
- `/sweetclaude:plan product-milestones blockers MS-NNN` — what is stopping progress
- `/sweetclaude:plan product-milestones complete MS-NNN` — mark achieved, capture follow-ups

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

## Tips

- **You can stop and resume anytime.** SweetClaude saves your progress in `.sweetclaude/`. Run `/sweetclaude:go` to pick up exactly where you left off — it reads state and proposes the next item, then waits for you.
- **You can skip ahead.** The pipeline is a guide, not a cage. If you want to jump straight to architecture, do it.
- **You can go back.** Revisiting earlier phases is normal. New information during design might change your pain thesis. That is how good work happens.
- **You control the pace.** SweetClaude never pushes you to the next step. It waits until you say you are ready.
- **The strategic work is optional but valuable.** You can skip straight to code if you want. But the projects that go through strategy and product definition first tend to build the right thing, not just build a thing.
