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
| `/sweetclaude:product-parking-lot` | Manage deferred work |
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
| `/sweetclaude:product-roadmap-analysis` | RICE scoring and stack-rank analysis. Scope and milestone alignment check. Proposed priority order for user confirmation. |

---

## Project Management Workflows

| Command | What it does |
|---|---|
| `/sweetclaude:project-issues` | Create, view, update, and close issues. Tracks sprint history per issue. Warns on adrift issues (carried over 2+ sprints). |
| `/sweetclaude:project-epics` | Group issues into epics. View progress (done/total). Cancel epics and return issues to backlog. Warns if an epic exceeds 12 issues. |
| `/sweetclaude:project-sprints` | Plan, start, and close sprints. Sprint board grouped by status. Carry/descope/close on sprint closure. Velocity and retrospective on close. Enforces single active sprint. |
| `/sweetclaude:project-backlog` | Backlog view grouped by priority bucket (NOW/SOONER/SOONISH/LATER/SOMEDAY). Promote issues to sprint. Surface inferred issues from Flow mode. |
| `/sweetclaude:project-backlog-triage` | INVEST-based grooming session. Works through ungroomed issues one at a time — recommend priority + effort, accept/override/skip/split. Sets status to `ready` when groomed. |
| `/sweetclaude:project-roadmap` | Priority-stacked roadmap. Create items, activate with workflow routing by type, defer, complete, cancel. Create and view releases. |
| `/sweetclaude:project-scope` | Define and maintain the project scope document. One statement, in-scope list, out-of-scope list (minimum 3). Cascade review on updates flags conflicting open items. |
| `/sweetclaude:project-goals` | Binary business goals — achieved or not. Challenge vague criteria at creation. `achieved`, `missed` sub-commands. |
| `/sweetclaude:project-mode` | Assess and shift project modes: flow → kanban → shape_up → agile → agile_enterprise. Snapshots state before every shift. Upshift/downshift signal detection. |
| `/sweetclaude:product-roadmap-analysis` | RICE scoring and stack-rank analysis for roadmap items. Scope and milestone alignment check. Proposed priority order for confirmation. |

---

## Testing Workflows

| Command | What it does |
|---|---|
| `/sweetclaude:testing-plan` | Define a test strategy for a feature or release. Scope, test types, environments, entry and exit criteria. Challenges vague exit criteria before accepting. |
| `/sweetclaude:testing-security` | Structured security review. STRIDE threat model → OWASP Top 10 checklist → dependency audit. P0/P1 findings filed as `now`-priority issues. |
| `/sweetclaude:testing-compliance` | Compliance control testing. SOC 2 / HIPAA / GDPR / PCI-DSS control catalog. Track status (pass/partial/gap/N/A), log evidence, generate gap report. Gaps filed as issues. |
| `/sweetclaude:testing-session` | Manual QA session — scripted or exploratory charter. Pass/fail per test case. File bugs mid-session with severity → priority mapping. |
| `/sweetclaude:testing-performance` | Define load scenarios, record baselines, compare benchmarks. Regression detection with threshold alerts. Integrates with k6, Locust, wrk, or manual runs. |
| `/sweetclaude:testing-accessibility` | WCAG 2.1 Level AA audit. Automated scan guidance + manual keyboard, screen reader, and visual checklist. Critical findings block release. |

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

## System

SweetClaude framework management. These commands configure, repair, and control the framework itself — not project work.

| Command | What it does |
|---|---|
| `/sweetclaude:on` | Activate SweetClaude on a project — new idea or existing codebase. Detects context automatically. |
| `/sweetclaude:init` | Bootstrap infrastructure only (no product discovery). Use when you want the scaffolding without the onboarding ceremony. |
| `/sweetclaude:adopt` | Onboard an existing or messy codebase. Full ASSESS → DIAGNOSE → PLAN → SCAFFOLD → ITERATE pipeline. |
| `/sweetclaude:off` | Deactivate SweetClaude. Preserves all artifacts. Reactivate with `:on`. |
| `/sweetclaude:update` | Fetch and install the latest SweetClaude version. Migrates state files and prompts to onboard new skills. |
| `/sweetclaude:fix-sweetclaude` | Audit and repair SweetClaude configuration — phase state, CLAUDE.md accuracy, file locations, skills.yaml, registers, hooks, git tracking. |
| `/sweetclaude:purge` | Delete all SweetClaude artifacts from the project. Requires typed confirmation. |
| `/sweetclaude:behavioral-regression` | Validate that the current Claude model version honors the framework's 15 behavioral contracts. Run after model upgrades. |
| `/sweetclaude:guardian-on` | Enable Protocol Guardian for the session — enforces skill invocations, TDD discipline, artifact saves. |
| `/sweetclaude:guardian-off` | Disable Protocol Guardian. |
| `/sweetclaude:usage` | Toggle or view local usage tracking. |
| `/sweetclaude:help` | Conversational help. Describe what you want to accomplish; the assistant shows you how. |

---

## Autonomous Pipeline

| Command | What it does |
|---|---|
| `/sweetclaude:john-wick` | Fully autonomous, resumable, multi-session SDLC pipeline — from product definition through PR, with pre-defined human gates |
| `/sweetclaude:john-wick-checkin` | Phase check-in subagent (invoked internally by John Wick — available standalone for drift detection) |
