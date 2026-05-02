# Full Command Reference

All SweetClaude slash commands organized by domain. The core and orchestration commands are in the [README](README.md). This page covers the domain-specific workflows.

> Most of these are invoked automatically by `/sweetclaude:go` based on your project state. You rarely need to invoke them directly — but you can if you know what you want.

---

## Product Workflows

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

---

## Design Workflows

| Command | What it does |
|---|---|
| `/sweetclaude:design-user-flows` | Convert user stories into UX/UI flows — step-by-step paths through the interface. |
| `/sweetclaude:design-architecture` | System architecture — reads compliance context from discovery and surfaces each derived framework as a hard requirement throughout the architecture document |
| `/sweetclaude:design-tech-spec` | Technical specification — enforces compliance requirements from architecture state (e.g. confirms chosen providers meet HIPAA BAA or SOC 2 requirements) |
| `/sweetclaude:design-ux` | UX design and wireframes |
| `/sweetclaude:design-solutioning-gate` | Validate design before implementation |
| `/sweetclaude:design-change-impact-analysis` | Trace blast radius before changes |
| `/sweetclaude:design-data-model` | Schema, entities, migrations |
| `/sweetclaude:design-api-design` | Endpoints, contracts, versioning |
| `/sweetclaude:design-manage-decisions` | Record decisions with rationale |

---

## Documentation Workflows

| Command | What it does |
|---|---|
| `/sweetclaude:document-corpus` | Full corpus pipeline + RAG — consolidate, triage, reconcile, promote, set up semantic search, reindex |
| `/sweetclaude:documents-update-docs` | Keep docs in sync after implementation changes |
| `/sweetclaude:documents-academic-research` | Research paper development — 6-phase pipeline from thesis through submission |
| `/sweetclaude:documents-narrative-arc` | Knowledge graph of strategic claims and evidence |

---

## Misc.

| Command | What it does |
|---|---|
| `/sweetclaude:misc-meeting-prep` | Stakeholder meeting deliverables — agenda, talking points, anticipated questions |

---

## Coding Workflows

| Command | What it does |
|---|---|
| `/sweetclaude:code-feature` | Build a new feature end-to-end (Gherkin → TDD Level 3 → PR) |
| `/sweetclaude:code-issue` | Implement a GitHub issue end-to-end |
| `/sweetclaude:code-debt` | Tech debt cleanup (lock behavior first) |
| `/sweetclaude:code-testing` | Run tests, mutation, security review, and/or PR pre-check |
| `/sweetclaude:code-review` | Code, security, and compliance review |

---

## Autonomous Pipeline

| Command | What it does |
|---|---|
| `/sweetclaude:john-wick` | Fully autonomous, resumable, multi-session SDLC pipeline — from product definition through PR, with pre-defined human gates |
| `/sweetclaude:john-wick-checkin` | Phase check-in subagent (invoked internally by John Wick — available standalone for drift detection) |
