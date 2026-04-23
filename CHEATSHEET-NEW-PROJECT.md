# SweetClaude Cheatsheet: Starting a New Project

You have an idea. Maybe it is well-formed, maybe it is a napkin sketch. SweetClaude walks you through the entire journey — from articulating the concept through shipping tested code. This is not just a coding framework. The strategic and product work that happens before you write any code is often the most valuable part.

## Before You Start

1. Install SweetClaude (if you have not already):
   ```bash
   git clone https://github.com/carson-sweet/sweetclaude.git
   cd sweetclaude
   ./install.sh                      # full install
   ./install.sh --strategy-skills-only  # or strategy/product skills only
   ```
2. Create an empty folder for your project and open Claude Code in it
3. Run:
   ```
   /sweetclaude:sherpa-start
   ```

That is it. SweetClaude takes over from here and walks you through each step.

> **Quick try without installing:** `claude --plugin-dir /path/to/sweetclaude` loads all skills for a single session.

## What Happens Next

### Step 1: Project Setup

SweetClaude creates:
- A git repository (if you want one)
- A `.sweetclaude/` folder that tracks your progress, decisions, and configuration
- A `strategy/` folder for strategic documents
- A `CLAUDE.md` file that teaches future AI sessions about your project

### Step 2: Concept Articulation

SweetClaude asks you to describe your idea in your own words. Then it helps you sharpen it into a clear statement: what is this, what problem does it solve, why does it matter, and what is it NOT. It will challenge your framing — not to be difficult, but because the best concepts survive scrutiny.

**Output:** `strategy/concept.md`

### Step 3: Pain Thesis

This is where SweetClaude goes deep. It walks you through 11 sections based on a structured pain analysis framework:

- What forces in the industry created this pain
- Who is personally accountable when this problem is not solved
- What the pain looks like from the inside and how it escalates
- What people do today and why those approaches fail
- What an effective solution must do (and what would cause rejection)
- Your strategic wedge — the narrowest slice buyers would pay for first
- How buyers will measure success
- Your ideal customer profile — who buys fastest, who to avoid
- Where your current capabilities match (and where the gaps are)
- How you will validate the thesis with real buyers

At each section, SweetClaude can research industry trends, analyze competitors, or brainstorm with you. You are not doing this alone.

**Output:** `strategy/pain-thesis.md` with a Red/Yellow/Green validation rubric

### Step 4: Ideal Customer Profile

SweetClaude sharpens the "who" from the pain thesis into a targetable profile: demographics, behaviors, purchase triggers, deal-breakers, and an explicit anti-profile (who you are NOT building for).

**Output:** `strategy/ideal-customer-profile.md`

### Step 5: Product Discovery

Now the product takes shape. SweetClaude interviews you about user personas one at a time. For each persona: role, tasks, success criteria. After personas are confirmed, it proposes features one at a time for you to include or exclude. Optionally, it researches competitors and extracts a "table stakes" feature set.

**Output:** Documented personas, feature set, and optional competitive analysis

### Step 6: Handoff

At this point you have a strategic foundation: concept, pain thesis, customer profile, personas, and feature set. SweetClaude tells you what is available next and lets you decide when to continue.

## What Comes After (When You Are Ready)

SweetClaude does not push you forward. You move to the next phase when you are ready.

### Product Definition
- `/sweetclaude:product-product-brief` — 11-section product brief, one section at a time
- `/sweetclaude:product-prd` — full PRD with functional requirements and epics
- `/sweetclaude:product-user-success-criteria` — measurable success per persona
- `/sweetclaude:product-manage-scope` — track what is in and out of scope

### Design
- `/sweetclaude:design-architecture` — system architecture
- `/sweetclaude:design-tech-spec` — technical specification
- `/sweetclaude:design-data-model` — schema and entity design
- `/sweetclaude:design-api-design` — endpoint contracts
- `/sweetclaude:design-ux` — user experience flows

### Planning
- `/sweetclaude:product-user-story` — user stories with acceptance criteria
- `/sweetclaude:product-user-tdd-tests` — convert stories to Gherkin test specs
- `/sweetclaude:product-sprint-plan` — plan a sprint from the backlog

### Implementation
- `/sweetclaude:code-tdd` — test-driven development at four enforcement levels
- `/sweetclaude:code-work-issue` — implement a GitHub issue end to end
- `/sweetclaude:code-work-debt` — clean up tech debt (tests before touch)

### Review and Ship
- `/sweetclaude:code-code-review` — adversarial code review
- `/sweetclaude:code-security-testing` — security review
- `/sweetclaude:code-pr-precheck` — pre-PR quality gate

### Milestones
- `/sweetclaude:milestones add` — create a roadmap target with success criteria
- `/sweetclaude:milestones review` — see all milestones grouped by Now / Next / Later
- `/sweetclaude:milestones link US-XXX MS-XXX` — attach a story to a milestone
- `/sweetclaude:milestones blockers MS-XXX` — what is stopping progress
- `/sweetclaude:milestones complete MS-XXX` — mark achieved, capture follow-ups

## What SweetClaude Can Do If You Ask

These are not part of the automatic flow. They are available anytime.

- **Competitive analysis** (`/sweetclaude:strategy-competitive-analysis`) — full landscape scan with SWOT analysis
- **Feature-level competitive comparison** (`/sweetclaude:product-feature-competitive`) — build a feature matrix against competitors
- **Market messaging** (`/sweetclaude:strategy-market-messaging`) — craft elevator pitches and value propositions per audience
- **Meeting prep** (`/sweetclaude:strategy-meeting-prep`) — prepare agenda, talking points, and anticipated questions for a specific meeting
- **Research** (`/sweetclaude:product-research`) — market or technical research with evidence and sources
- **Academic paper** (`/sweetclaude:strategy-academic-research`) — full six-phase pipeline from thesis through submission
- **Narrative arc** (`/sweetclaude:strategy-narrative-arc`) — build a knowledge graph connecting your claims, evidence, and objectives
- **Decision tracking** (`/sweetclaude:design-manage-decisions`) — record any decision with context and rationale, queryable later
- **Positioning statement** (`/sweetclaude:product-positioning-statement`) — for/who/that/unlike framework
- **Corpus pipeline** — organize messy files into canonical documents with full provenance:
  - `/sweetclaude:corpus-consolidate` — scan, deduplicate, ingest into corpus
  - `/sweetclaude:corpus-triage` — classify files (keep, reconcile, discard, defer)
  - `/sweetclaude:corpus-reconcile` — draft and refine canonical documents
  - `/sweetclaude:corpus-promote` — finalize with provenance, archive, RAG index
  - `/sweetclaude:corpus-status` — see where the pipeline stands
- **RAG search** (`/sweetclaude:rag-index`) — set up semantic search over your project documents so you can query by meaning, not just keywords
- **Update SweetClaude** (`/sweetclaude:update-skills`) — fetch the latest version from GitHub and sync to all projects
- **Auto version bumping** — create `.sweetclaude/version-bump.yaml` to auto-bump version files after every git commit based on conventional commit prefixes

## Tips

- **You can stop and resume anytime.** SweetClaude saves your progress in `.sweetclaude/`. Run `/sweetclaude:status` to see where you left off.
- **You can skip ahead.** The pipeline is a guide, not a cage. If you want to jump straight to architecture, do it.
- **You can go back.** Revisiting earlier phases is normal. New information during design might change your pain thesis. That is how good work happens.
- **You control the pace.** SweetClaude never pushes you to the next step. It waits until you say you are ready.
- **The strategic work is optional but valuable.** You can skip straight to code if you want. But the projects that go through strategy and product definition first tend to build the right thing, not just build a thing.
