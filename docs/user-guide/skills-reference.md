# SweetClaude Skills Reference

**Version:** 1.6
**Date:** 2026-05-07

All 103 skills, organized by domain. Internal framework skills (_features, _health, _migrate, _route, bootstrap, master) are listed in their sections but not user-invocable. This page is reference — for narrative explanations of how skills fit together, read [Walkthroughs](walkthroughs.md) and [How It Works](how-it-works.md).

You rarely need to memorize commands. `/sweetclaude:go` is the single entry point — it routes automatically based on project state and what you describe in plain English. The list below is for when you know exactly what you want.

Many skills accept `$ARGUMENTS` to skip menus: `/sweetclaude:code-testing security`, `/sweetclaude:product-milestones add`, `/sweetclaude:document-corpus triage`.

---

## How to Use This Page

If you are looking up a specific skill, jump to its section. The bucket headings are: Orchestration, System, Product, Design, Code, Project Management, Testing, Documents, plus the specialist subagent roster at the bottom.

If you are wondering "which skills go together for X?", the [Walkthroughs](walkthroughs.md) page chains skills end-to-end for six common scenarios. This page is the lookup; that page is the recipe.

---

## Orchestration

Session navigation and automatic routing. Most of these fire without being invoked directly — `/sweetclaude:go` is the primary entry point.

| Skill | Invocation | What it does |
|---|---|---|
| **Go** | `/sweetclaude:go` | Pick up where you left off. Reads state, checks phase exit criteria, routes to the right skill. Pass plain-English arguments to describe what you want. |
| **Recap** | `/sweetclaude:recap` | One-screen orientation: current phase, active work item, last 3 commits, checkpoint state. Run after a break or context switch. Auto-triggers a checkpoint check-in at session start when unfinished work exists. |
| **Status** | `/sweetclaude:status` | Project status dashboard. Active work item, phase, roadmap, backlog, recent commits. |
| **Find Skill** | _(internal)_ | Classifies plain-English input, confirms routing, updates state, and starts the right skill. Invoked automatically by `/sweetclaude:go` when arguments are present. |
| **Next Steps** | _(internal)_ | Walk through the pipeline step by step. Explains what the current phase requires and what comes after. |
| **Retro** | `/sweetclaude:retro` | End-of-phase or end-of-project retrospective. Surfaces what went well, what didn't, and what to adjust. Writes learnings to the improvement register so future sessions start with them applied. |
| **Session Export** | `/sweetclaude:session-export` | Export a Claude.ai conversation as a structured document for corpus ingestion. |
| **Hibernate** | `/sweetclaude:hibernate` | Freeze a project. Saves full state, exports session context, disables auto-status. Resume later with `/sweetclaude:go`. |
| **Ultraplan** | `/sweetclaude:ultraplan` | Prepare a structured ultraplan prompt from current phase artifacts, launch ultraplan, and ingest the resulting plan as the DESIGN phase architecture artifact. |

---

## System (14 skills)

Framework management — setup, teardown, updates, audits, and guards. Always available regardless of version stage.

| Skill | Invocation | What it does |
|---|---|---|
| **Setup** | _(internal)_ | Activate on any project — new idea or existing codebase. Detects context, walks through setup, writes `sweetclaude.yaml`. Invoked automatically by `/sweetclaude` when no state file exists. |
| **Init** | `/sweetclaude:init` | Bootstrap SweetClaude infrastructure only (no product discovery). Detects project type, creates `.sweetclaude/`, generates CLAUDE.md stub. For existing codebases with real history, use `/sweetclaude` (which routes to setup) instead. |
| **Off** | `/sweetclaude:off` | Suspend SweetClaude for this project. Preserves all artifacts. Reactivate with `/sweetclaude:go`. |
| **Update** | `/sweetclaude:update` | Fetch the latest version from GitHub and sync to all installed locations. Shows what changed. Migrates `phase.yaml`/`skills.yaml` from v2.x to `sweetclaude.yaml` format. |
| **Fix SweetClaude** | `/sweetclaude:fix-sweetclaude` | Audit and repair configuration. Checks CLAUDE.md accuracy, phase state, file locations, `sweetclaude.yaml` consistency, empty registers, hook registrations. If `sweetclaude.yaml` is unparseable, offers repair options. Proposes fixes — does not change anything without asking. |
| **Purge** | `/sweetclaude:purge` | Delete all SweetClaude artifacts. Recommends a backup branch first. Requires typed confirmation. |
| **Assess Mode** | `/sweetclaude:project-assess-shape` | Five-question interview to recommend and configure a project mode (Flow, Kanban, Shape Up, or Agile). Writes mode to `sweetclaude.yaml` and compiles `effective-gates.yaml`. Runs automatically at init; available on demand to re-assess. |
| **Behavioral Regression** | `/sweetclaude:behavioral-regression` | Run the 15-contract behavioral test suite against the current model version. Tests phase dwelling, propose-not-ask, TDD enforcement claims, deference levels, detour recovery, improvement register triggers, and more. Run after any Claude model upgrade to detect silent behavioral drift. |
| **Mode Regression** | `/sweetclaude:sweetclaude-behavioral-regression` | Validate that mode enforcement is working correctly across all four modes. Tests all three enforcement layers: `effective-gates.yaml`, `wip-limit.sh` hook, and MODE_CHECK blocks. Run after any change to the modes system. |
| **Guardian On** | `/sweetclaude:guardian-on` | Enable Protocol Guardian. Enforces skill invocations, TDD discipline, and artifact saves for the rest of the session. |
| **Guardian Off** | `/sweetclaude:guardian-off` | Disable Protocol Guardian. |
| **Usage** | `/sweetclaude:usage` | View, enable, or disable local usage tracking. |
| **Help** | `/sweetclaude:help` | Conversational help — describe what you want, learn how to work through prompting. Or browse all commands by category. |

---

## Product (18 skills)

Strategy and product definition. Useful before any code is written and on existing projects to document implicit strategy.

### Discovery layer

| Skill | Invocation | What it does |
|---|---|---|
| **Product Discovery** | `/sweetclaude:product-discovery` | Establish what is being built, for whom, and why. Three depth levels: L1 quick intent, L2 problem and success, L3 full pain thesis. Each depth produces structured persona-precursor output: named segments, real-world scenarios (L1+); attitudinal axes, optional JTBD candidates (L2+); minimum 2 segments, 1 axis, 2 JTBD, 2 scenarios as L3 exit criteria. Collects compliance context (data categories, geography, user type) and derives applicable frameworks (GDPR, HIPAA, PCI DSS). |
| **Product Research** | `/sweetclaude:product-research` | Market and solution research. Feeds the competitive seed list. |
| **Product Competition** | `/sweetclaude:product-competition` | Three depth levels: survey (who's in the space), matrix (structured comparison), feature-deep (capability analysis). |
| **User Personas** | `/sweetclaude:user-personas` | Define users — who they are, what tasks they need to do, what success looks like. Includes triggers and deal-breakers. Always loaded (cross-cuts all domains). State-tracked: first invocation prompts for a first user type; subsequent invocations proceed immediately. Use `pause` to suspend without deleting data, `onboard` for the full setup ceremony. |
| **Product User Focus Group** | `/sweetclaude:product-user-focus-group [mode]` | Synthetic panel research using persona archetypes as parallel subagent respondents. Three modes: `ask` (open qualitative), `concept-test` (ranked preference), `message-test` (variant resonance). **Hard gate:** requires validated personas in `state/personas.yaml` before entry. All outputs mandatorily labeled synthetic — findings are hypotheses, not validated user research. |
| **Product Positioning Statement** | `/sweetclaude:product-positioning-statement` | For/who/that/unlike framework. |

### Definition layer

| Skill | Invocation | What it does |
|---|---|---|
| **Product Brief** | `/sweetclaude:product-brief` | Strategic product brief. Outline-first. Sections scale to available input depth. |
| **Product PRD** | `/sweetclaude:product-prd` | Full PRD — functional requirements, NFRs, epics. |
| **Product User Stories** | `/sweetclaude:product-user-stories` | Stories with acceptance criteria. Scoped to all personas, SLC, or MVP. State-tracked: first invocation offers GitHub Issues import; warns (does not block) if `user-personas` is not active. Use `pause` to suspend without deleting data. |
| **Product User TDD Tests** | `/sweetclaude:product-user-tdd-tests` | Convert stories to Gherkin `.feature` files for TDD Level 3. |
| **Product Manage Scope** | `/sweetclaude:product-manage-scope` | Track scope changes with rationale. Prevents silent scope creep. |
| **Product Parking Lot** | `/sweetclaude:product-parking-lot` | Manage deferred work. State-tracked: first invocation runs a lightweight setup (optional GitHub Issues import); subsequent invocations proceed immediately. Use `/sweetclaude:product-parking-lot pause` to suspend without deleting data. |
| **Product Sprint Plan** | `/sweetclaude:product-sprint-plan` | Plan a sprint from the backlog. Reports which milestones a sprint advances. Requires `product-parking-lot` to be `active`. |
| **Product Market Messaging** | `/sweetclaude:product-market-messaging` | Elevator pitches, value propositions, key messages per audience. |
| **Product Milestones** | `/sweetclaude:product-milestones [sub]` | Outcome-driven roadmap targets like "Exit Stealth" or "Paid Pilot Live." Sub-commands: `add`, `review`, `link [US-XXX] [MS-XXX]`, `status`, `blockers`, `complete`, `unassigned`. State-tracked: first invocation runs a lightweight setup; use `pause` to suspend, `onboard` for full ceremony. |
| **Product Roadmap Analysis** | `/sweetclaude:product-roadmap-analysis [analyze\|alignment\|item RM-NNN]` | RICE scoring (Reach × Impact × Confidence ÷ Effort) for all planned and active roadmap items. Scope and milestone alignment check. Proposes a revised stack-rank — applies only on confirmation. |
| **Product Milestone Planning** | `/sweetclaude:product-milestone-planning` | Guided workshop for defining milestone success criteria, dependency mapping, and risk bets. Challenges weak definitions. Hands off to `product-milestones` for tracking. |
| **Product Terminology** | `/sweetclaude:product-terminology` | Define and maintain a shared domain glossary. Each entry records term name, definition, rationale, aliases, and words to avoid. Prevents naming drift across docs, code, and conversation. |

---

## Design (14 skills)

Technical design. Every significant decision is recorded with context and rationale to `.sweetclaude/state/decision-log.md`.

| Skill | Invocation | What it does |
|---|---|---|
| **Design Architecture** | `/sweetclaude:design-architecture` | System architecture. Reads compliance context from discovery and surfaces each derived framework (GDPR, HIPAA, etc.) as a hard requirement throughout the architecture document. Produces ADRs. |
| **Design Tech Spec** | `/sweetclaude:design-tech-spec` | Technical specification. Enforces compliance requirements from architecture state (e.g., confirms chosen providers meet HIPAA BAA or SOC 2 requirements). |
| **Design Data Model** | `/sweetclaude:design-data-model` | Schema and entity design. Tables, relationships, indexes, migration path. |
| **Design API Design** | `/sweetclaude:design-api-design` | Endpoint contracts. Routes, request/response shapes, error codes, versioning. |
| **Design User Flows** | `/sweetclaude:design-user-flows` | Convert user stories into UX/UI flows — step-by-step paths through the interface. |
| **Design UX** | `/sweetclaude:design-ux` | Define the visual and interaction design of the product — look, feel, layout, and style. Produces a UX/UI design spec for handoff to AI mockup tools or a design team. For wireframe generation, use `design-wireframes`; for virtual UX review sessions, use `design-ux-review`. |
| **Design Wireframes** | `/sweetclaude:design-wireframes` | Generate self-contained HTML/CSS wireframes from user flows. One file per flow, covering all key screen states. Reads visual style from `ux.yaml` if available; uses neutral defaults otherwise. |
| **Design UX Review** | `/sweetclaude:design-ux-review` | Virtual UX review session. Spawns parallel subagents — one per persona — each walking through a flow or wireframe independently and returning structured feedback. Synthesizes findings into prioritized recommendations. All output labeled synthetic. |
| **Design Solutioning Gate** | `/sweetclaude:design-solutioning-gate` | Required before implementation for high-risk work. Confirms the right solution is being built, an alternative was considered, and a rollback plan exists. |
| **Design Change Impact Analysis** | `/sweetclaude:design-change-impact-analysis` | Trace blast radius before changes. Surfaces ripple effects across artifacts before they become bugs. |
| **Design Manage Decisions** | `/sweetclaude:design-manage-decisions` | Record any decision with context, options considered, and rationale. Query later: "Why did we choose X?" |
| **Mockup Sandbox** | `/sweetclaude:mockup-sandbox` | Create an isolated Vite + React + Tailwind + shadcn/ui mockup environment at `artifacts/mockup-sandbox/`. Scaffold components with parallel variants, preview at `localhost:5174`, track approved mockups in `.sweetclaude/state/mockup-registry.yaml`. Start here for any UI work before touching production code. |
| **Mockup Extract** | `/sweetclaude:mockup-extract [ComponentName]` | Extract a component from the main app into the mockup sandbox. Rewrites `@/` imports, stubs API calls/routing/auth, creates a group CSS file from the main app's globals, and type-checks before sharing a preview URL. |
| **Mockup Graduate** | `/sweetclaude:mockup-graduate` | Graduate registry-approved mockups into production code. Analyzes production patterns (routing lib, state management, data fetching), presents a transformation plan before writing any code, adds loading/error/empty states and accessibility, and extracts Gherkin acceptance criteria to `acceptance-criteria-{group}.md`. |

---

## Code (7 skills)

Implementation. These skills enforce TDD via hooks, run tests and reviews, and manage the implementation lifecycle.

| Skill | Invocation | What it does |
|---|---|---|
| **Code Feature** | `/sweetclaude:code-feature [description]` | Build a new feature end-to-end. Generates Gherkin specs if needed. Runs full TDD Level 3 pipeline: test writer → QA caucus → implementer. Verifies. Opens a PR. |
| **Code Issue** | `/sweetclaude:code-issue [issue#]` | Implement a GitHub issue end to end. Reads acceptance criteria from the issue, runs the TDD pipeline, closes the issue. |
| **Code Debt** | `/sweetclaude:code-debt` | Tech debt cleanup. Locks existing behavior with tests (SCOPE phase) before touching code. |
| **Code Testing** | `/sweetclaude:code-testing [mode]` | Menu of four checks: test suite, mutation testing, security review, PR pre-check. Pick one or several. Skips menu if `$ARGUMENTS` passed. |
| **Code Review** | `/sweetclaude:code-review [type]` | Adversarial code, security, and compliance review. Opens a menu. Pick one or several. Assumes problems exist and finds them. |
| **Code TDD** | `/sweetclaude:code-tdd` | TDD enforcement and guidance. Explains the levels, runs the appropriate pipeline for the current work, enforces RED → GREEN → refactor. |
| **Code Verify** | `/sweetclaude:code-verify` | Run verification before claiming work is complete. Evidence before claims — always. Required before any success assertion, commit, or phase advancement. |

### Code Testing modes

```
1 / test-suite     Run tests, report pass/fail
2 / mutation       Mutation testing — verify tests catch faults
3 / security       Auth, injection, secrets review
4 / pr-precheck    Coverage, review, changelog, docs — final quality gate
```

### Code Review modes

```
1 / code           Logic errors, edge cases, regressions, performance
2 / security       Auth, injection, secrets, OWASP Top 10
3 / compliance     Licenses, data handling, privacy, regulatory
```

---

## Project Management (11 skills)

Execution-layer tracking. These skills manage the work that delivers the product — not what to build (that's product/), but how the building is organized and tracked.

| Skill | Invocation | What it does |
|---|---|---|
| **Project Issues** | `/sweetclaude:project-issues` | Create, view, update, and close issues. Reads and writes v4 story files under `docs/product/backlog/`. Closing a story moves the file to `done/` and sets `closed_date`. Supports `list`, `backlog`, `view`, `new`, `update`, `close`, `reopen`. |
| **Project Epics** | `/sweetclaude:project-epics` | Optional goal lens that groups stories by functional area. A classification attribute — tracks progress toward a named goal across multiple sprints, not a delivery container. Cancel an epic and its stories return to the backlog. Warns if an epic exceeds 20 stories. |
| **Epic Design** | `/sweetclaude:epic-design [EP-NNN\|new <title>]` | Produce a complete, ordered story list for an epic. Design-first sequence: no implementation stories are written until design stories are complete and their outputs are on disk. Accepts an existing epic or creates a new one. |
| **Project Sprints** | `/sweetclaude:project-sprints` | Full sprint lifecycle: plan, start, board, update, close, retrospective. Each sprint anchors to a milestone (`milestone_id`). Velocity calculated on close. Sprint history maintained per issue. Enforces single active sprint. |
| **Project Themes** | `/sweetclaude:project-themes` | Optional domain-grouping labels on stories — classification attributes, not delivery containers. For large multi-service projects (50+ stories) where epics alone leave the inventory unnavigable. Tag stories with a theme; themes carry no delivery commitment and have no definition of done. |
| **Project Backlog** | `/sweetclaude:project-backlog` | Backlog view grouped by priority bucket (NOW/SOON/LATER/SOMEDAY/UNESTIMATED). Reads from `docs/product/backlog/INDEX.md`. Promote issues to a sprint. Review imported issues. |
| **Project Backlog Triage** | `/sweetclaude:project-backlog-triage` | Structured grooming session. Sources rows from `docs/product/backlog/INDEX.md`. Works through ungroomed issues one at a time using INVEST criteria. Writes back to individual story files and INDEX. Sets status to `ready` when groomed. |
| **Product Roadmap** | `/sweetclaude:product-roadmap` | Priority-stacked roadmap with force-ranked items. Create, activate (routes to correct downstream workflow by type), defer, complete, cancel. Create and view releases. |
| **Project Scope** | `/sweetclaude:project-scope` | Singleton scope document — one statement, in-scope list, minimum three out-of-scope items. Cascade review on update flags conflicting open roadmap items and issues. |
| **Project Goals** | `/sweetclaude:project-goals` | Binary business goals — achieved or not. Criteria must be evaluable as true/false. `list`, `view`, `new`, `achieved`, `missed`. |
| **Project Mode** | `/sweetclaude:project-mode` | Assess and shift project modes: flow → kanban → shape_up → agile. Snapshots state before every shift. Detects upshift/downshift signals from artifact counts. Each mode compiles `effective-gates.yaml` with its enforcement rules. |
| **GitHub Import Issues** | `/sweetclaude:project-gh-import-issues` | Pull open GitHub Issues into `docs/product/backlog/stories/` as v4 story files with `origin: imported`. Idempotent — issues already imported by GitHub number are skipped. Maps size/effort labels to effort field. |
| **GitHub Sync Issues** | `/sweetclaude:project-gh-sync-issues` | Bidirectional status sync against `docs/product/backlog/` story files only (roadmap sync is Phase 2). Pass 1: GH closed → local done (moves file to `done/`). Pass 2: local done → `gh issue close`. Reports counts for each direction. |

---

## Testing (6 skills)

Independent QA, security, compliance, and performance validation — not tied to a single feature's TDD cycle. All actionable findings file directly to project-issues.

| Skill | Invocation | What it does |
|---|---|---|
| **Testing Plan** | `/sweetclaude:testing-plan` | Define a test strategy for a feature, release, or area. Scope, test types, environments, entry criteria, exit criteria. Challenges vague exit criteria before accepting. |
| **Testing Security** | `/sweetclaude:testing-security` | Structured security review. STRIDE threat model → OWASP Top 10 checklist → dependency audit. P0 findings block release. P0/P1 filed as `next`-priority issues. |
| **Testing Compliance** | `/sweetclaude:testing-compliance` | Control testing and evidence collection for SOC 2, HIPAA, GDPR, and PCI-DSS. Track per-control status (pass/partial/gap/N/A), log evidence locations, generate gap reports. Gaps filed as issues. |
| **Testing Session** | `/sweetclaude:testing-session` | Manual QA session — scripted test cases or exploratory charter. Pass/fail per case. File bugs mid-session; severity maps to issue priority. Resume open sessions. |
| **Testing Performance** | `/sweetclaude:testing-performance` | Load scenario definitions, baseline recording, and benchmark comparison. Regression detection with configurable p50/p95/p99 and error rate thresholds. Tool-agnostic: works with k6, Locust, wrk, or manual runs. |
| **Testing Accessibility** | `/sweetclaude:testing-accessibility` | WCAG 2.1 Level AA audit. Automated scan guidance + manual keyboard navigation, screen reader, and visual checklist. Critical findings block release. Findings filed as issues. |

---

## Deploy (2 skills)

Deployment and incident response.

| Skill | Invocation | What it does |
|---|---|---|
| **Deploy Ship** | `/sweetclaude:deploy-ship` | Guided deployment for work items that have completed VERIFY. Confirms deployment config, runs a 7-item pre-ship checklist (AC met, tests passing, no secrets in diff, changelog present, rollback plan documented, break-glass notes updated at GA+, monitoring active), guides the deploy command, and smoke-tests post-deploy. Does not run the deploy itself — guides you through it. Logs checklist result and smoke test to `decision-log.md`. Archives the active plan file to `.sweetclaude/plans/archive/` organized by milestone and sprint. |
| **Something Broke** | `/sweetclaude:something-broke` | Production incident response. Classifies severity (P0/P1/P2) in ≤3 questions, decides fix-vs-rollback, routes to `:hotfix` or `:rollback-revert`, confirms resolution, and spawns a mandatory post-mortem work item. The post-mortem is required — a resolved incident without one is incomplete. |

---

## Documents and Strategy Specialists (7 skills)

Long-form document work, corpus management, and specialized strategy capabilities.

| Skill | Invocation | What it does |
|---|---|---|
| **Document Corpus** | `/sweetclaude:document-corpus [mode]` | Four-step pipeline for messy documents: consolidate → triage → reconcile → promote. Then index for RAG search. Full reference: [corpus-system.md](corpus-system.md). State-tracked: first invocation asks whether you have documents to add; use `pause` to suspend, `onboard` for full ceremony. |
| **Documents Update Docs** | `/sweetclaude:documents-update-docs` | After implementation changes behavior, scan existing docs for stale references and propose updates. |
| **Documents Academic Research** | `/sweetclaude:documents-academic-research` | Six-phase pipeline for academic papers: thesis through submission. Includes peer review simulation. |
| **Documents Narrative Arc** | `/sweetclaude:documents-narrative-arc` | Knowledge graph connecting your claims, evidence, and strategic objectives. Query later: "What evidence supports claim X?" |
| **Misc Meeting Prep** | `/sweetclaude:misc-meeting-prep` | Prepare for a specific meeting. Drafts agenda, talking points with confidence levels, anticipated questions with prepared responses, and leave-behinds. Captures debrief afterward. |
| **John Wick** | `/sweetclaude:john-wick` | Autonomous multi-session SDLC pipeline. Runs the full pipeline without stopping at every sub-step, using phase check-ins to validate exit criteria. For when you want maximum autonomy. |
| **John Wick Check-In** | `/sweetclaude:john-wick-checkin` | Phase check-in subagent used internally by John Wick. Available standalone for drift detection. |

### Document Corpus sub-skills

Each pipeline step is also a standalone skill you can invoke directly:

| Skill | Invocation | What it does |
|---|---|---|
| **Corpus Status** | `/sweetclaude:corpus-status` | Pipeline state, file counts, what to do next. |
| **Corpus Consolidate** | `/sweetclaude:corpus-consolidate` | Scan, deduplicate, ingest documents into `raw/inbox/`. |
| **Corpus Triage** | `/sweetclaude:corpus-triage` | Classify each file: keep / reconcile / discard / defer. |
| **Corpus Reconcile** | `/sweetclaude:corpus-reconcile` | Draft canonical documents from related or conflicting files. |
| **Corpus Promote** | `/sweetclaude:corpus-promote` | Finalize with provenance, archive sources, rebuild RAG index. |
| **Corpus RAG Setup** | `/sweetclaude:corpus-rag-setup` | Set up local RAG search (installs mcp-local-rag). |
| **Corpus RAG Reindex** | `/sweetclaude:corpus-rag-reindex` | Rebuild RAG embeddings after document changes. |

---

## Common Skill Combinations

You rarely use one skill in isolation. The patterns below are the chains that show up most often.

**New project from idea to first feature:**
```
/sweetclaude:go   (routes to setup → product-discovery automatically)
→ product-discovery (L2 or L3)
→ product-brief
→ product-prd
→ design-architecture
→ design-data-model
→ design-api-design
→ product-user-stories
→ product-user-tdd-tests
→ code-feature
```

**Onboarding an existing codebase:**
```
/sweetclaude:go  (routes to sweetclaude:setup, which detects existing codebase)
→ ASSESS (language/toolchain/CI/security scan)
→ DIAGNOSE (Critical/High/Medium/Low findings)
→ PLAN (remediation sequence)
→ SCAFFOLD (SweetClaude infrastructure on safety branch)
→ ITERATE (remediation backlog items created)
→ code-debt (work through Critical/High findings)
```

**UI feature with mockup-first design:**
```
/sweetclaude:mockup-sandbox (scaffold environment)
→ mockup-extract [ExistingComponent] (pull in prod components)
→ iterate on design in sandbox
→ mockup-graduate (graduate approved mockups to prod code)
→ code-feature (TDD pipeline from extracted acceptance criteria)
→ deploy-ship
```

**Shipping a completed feature:**
```
/sweetclaude:deploy-ship
→ pre-ship checklist (AC, tests, secrets scan, changelog, rollback plan)
→ deploy command
→ smoke test
→ work item closed
```

**Hotfix / production incident:**
```
/sweetclaude:something-broke
→ severity classification (P0/P1/P2)
→ fix-vs-rollback decision
→ DIAGNOSE → IMPLEMENT (test+fix) → SHIP → POST-MORTEM
```

**Document organization:**
```
/sweetclaude:document-corpus
→ consolidate → triage → reconcile → promote → rag
```

**Course correction mid-project:**
```
/sweetclaude "we need to pivot"
→ DISCOVER (signal aggregation) → DEFINE (new direction) → TRIAGE (in-flight work) → SHIP (commit revised direction)
```

---

## Subagents

These run inside skills. You do not invoke them directly. They appear in tool execution but the skill is the entry point.

| Agent | Role |
|---|---|
| `sweetclaude:test-writer` | Writes failing tests from Gherkin or acceptance criteria. No knowledge of planned implementation. |
| `sweetclaude:implementer` | Makes failing tests pass with minimal code. No knowledge of specs or test writer reasoning. |
| `sweetclaude:qa-caucus-service` | Reviews test plan for service/API coverage gaps: tenant isolation, state transitions, concurrency. |
| `sweetclaude:qa-caucus-component` | Reviews test plan for UI/component coverage gaps: accessibility, loading states, interaction edge cases. |
| `sweetclaude:qa-caucus-integration` | Reviews test plan for cross-cutting gaps: optimistic UI vs server state, multi-tab, security bypasses. |
| `sweetclaude:code-reviewer` | Adversarial code review post-implementation. Logic errors, edge cases, regressions, performance. |
| `sweetclaude:security-reviewer` | Security review. Auth issues, injection, secrets, OWASP Top 10. |
| `sweetclaude:workflow-guardian` | GitHub Actions security review. SHA pinning, least-privilege tokens, safe triggers. |

---

## Bringing Your Own Context Skills

SweetClaude's skills are **behavioral contracts** — they enforce how you build software (phase gates, TDD discipline, caucus review) regardless of what framework or library you're using. They do not document framework APIs or codebase conventions.

If your project uses a specialized framework, internal API, or proprietary tooling that Claude doesn't know well, you'll want **context skills** alongside SweetClaude's process skills. Tools like [Skill Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) can generate reference skills from your documentation sites, GitHub repos, PDFs, or OpenAPI specs in 15–45 minutes. These pair cleanly with SweetClaude: Skill Seekers provides the context ("here is how our internal auth API works"), SweetClaude provides the process ("here is how to build the feature that uses it correctly").

You do not need to choose between them. Install both in `~/.claude/skills/` and they coexist without conflict.

---

## What to Read Next

- How these skills chain in real scenarios → [Walkthroughs](walkthroughs.md)
- Why the skills are organized this way → [How It Works](how-it-works.md)
- Phase exit criteria the skills are written against → [Phases and Workflows](phases-and-workflows.md)
