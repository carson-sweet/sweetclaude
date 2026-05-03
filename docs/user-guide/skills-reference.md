# Skills Reference

**Version:** 1.4
**Date:** 2026-05-03

All 81 skills, organized by domain. This page is reference — for narrative explanations of how skills fit together, read [Walkthroughs](walkthroughs.md) and [How It Works](how-it-works.md).

You rarely need to memorize commands. `/sweetclaude:go` and `/sweetclaude:find-skill` route automatically based on project state and what you describe. The list below is for when you know what you want.

Many skills accept `$ARGUMENTS` to skip menus: `/sweetclaude:code-testing security`, `/sweetclaude:product-milestones add`, `/sweetclaude:document-corpus triage`.

---

## How to Use This Page

If you are looking up a specific skill, jump to its section. The bucket headings are: Orchestration, System, Product, Design, Code, Project Management, Testing, Documents, plus the specialist subagent roster at the bottom.

If you are wondering "which skills go together for X?", the [Walkthroughs](walkthroughs.md) page chains skills end-to-end for six common scenarios. This page is the lookup; that page is the recipe.

---

## Orchestration (8 skills)

Session navigation and automatic routing. Most of these fire without being invoked directly.

| Skill | Invocation | What it does |
|---|---|---|
| **Master** | _(auto)_ | Session entry point. Pre-flight check, phase state read, route to the right skill. Fires automatically at session start for configured projects. |
| **Go** | `/sweetclaude:go` | Pick up where you left off. Reads state, checks phase exit criteria, routes to the right skill. No menu — it acts. |
| **Find Skill** | `/sweetclaude:find-skill` | Describe what you want to do. The framework classifies, confirms, updates state, and starts the right skill. |
| **Status** | `/sweetclaude:status` | Project status dashboard. Active work item, phase, recent commits, open issues, what's next. Shows warnings when a data-owning skill is marked `active` but its artifacts are missing on disk — directs to `/sweetclaude:fix-sweetclaude`. Fires automatically at session start for active projects. |
| **Next Steps** | `/sweetclaude:next-steps` | Walk through the pipeline step by step. Explains what the current phase requires and what comes after. |
| **Retro** | `/sweetclaude:retro` | End-of-phase or end-of-project retrospective. Surfaces what went well, what didn't, and what to adjust. Writes learnings to the improvement register so future sessions start with them applied. |
| **Session Export** | `/sweetclaude:session-export` | Export a Claude.ai conversation as a structured document for corpus ingestion. |
| **Hibernate** | `/sweetclaude:hibernate` | Freeze a project. Saves full state, exports session context, disables auto-status. Resume later with `:on`. |

---

## System (12 skills)

Framework management — setup, teardown, updates, audits, and guards. Always available regardless of version stage.

| Skill | Invocation | What it does |
|---|---|---|
| **On** | `/sweetclaude:on` | Activate on any project — new idea or existing codebase. Detects context. Walks through setup. |
| **Init** | `/sweetclaude:init` | Bootstrap SweetClaude infrastructure only (no product discovery). Detects project type, creates `.sweetclaude/`, generates CLAUDE.md stub. For existing codebases with real history, use `:adopt` instead. |
| **Adopt** | `/sweetclaude:adopt` | Onboard an existing codebase with real history. ASSESS → DIAGNOSE → PLAN → SCAFFOLD → ITERATE. Never touches src/ or tests/ without consent. |
| **Off** | `/sweetclaude:off` | Suspend SweetClaude for this project. Preserves all artifacts. Reactivate with `:on`. |
| **Update** | `/sweetclaude:update` | Fetch the latest version from GitHub and sync to all installed locations. Shows what changed. Migrates `skills.yaml` from schema v1 to v2 and prompts to onboard skills that are still `uninitialized`. |
| **Fix SweetClaude** | `/sweetclaude:fix-sweetclaude` | Audit and repair configuration. Checks CLAUDE.md accuracy, phase state, file locations, `skills.yaml` consistency, empty registers, hook registrations. Proposes fixes — does not change anything without asking. |
| **Purge** | `/sweetclaude:purge` | Delete all SweetClaude artifacts. Recommends a backup branch first. Requires typed confirmation. |
| **Behavioral Regression** | `/sweetclaude:behavioral-regression` | Run the 15-contract behavioral test suite against the current model version. Tests phase dwelling, propose-not-ask, TDD enforcement claims, deference levels, detour recovery, improvement register triggers, and more. Run after any Claude model upgrade to detect silent behavioral drift. |
| **Guardian On** | `/sweetclaude:guardian-on` | Enable Protocol Guardian. Enforces skill invocations, TDD discipline, and artifact saves for the rest of the session. |
| **Guardian Off** | `/sweetclaude:guardian-off` | Disable Protocol Guardian. |
| **Usage** | `/sweetclaude:usage` | View, enable, or disable local usage tracking. |
| **Help** | `/sweetclaude:help` | Conversational help — describe what you want, learn how to work through prompting. Or browse all commands by category. |

---

## Product (14 skills)

Strategy and product definition. Useful before any code is written and on existing projects to document implicit strategy.

### Discovery layer

| Skill | Invocation | What it does |
|---|---|---|
| **Product Discovery** | `/sweetclaude:product-discovery` | Establish what is being built, for whom, and why. Three depth levels: L1 quick intent, L2 problem and success, L3 full pain thesis. Collects compliance context (data categories, geography, user type) and derives applicable frameworks (GDPR, HIPAA, PCI DSS) — written to state for use throughout the pipeline. |
| **Product Research** | `/sweetclaude:product-research` | Market and solution research. Feeds the competitive seed list. |
| **Product Competition** | `/sweetclaude:product-competition` | Three depth levels: survey (who's in the space), matrix (structured comparison), feature-deep (capability analysis). |
| **Product User Personas** | `/sweetclaude:product-user-personas` | Define users — who they are, what tasks they need to do, what success looks like. Includes triggers and deal-breakers. State-tracked: first invocation prompts for a first user type; subsequent invocations proceed immediately. Use `pause` to suspend without deleting data, `onboard` for the full setup ceremony. |
| **Product Positioning Statement** | `/sweetclaude:product-positioning-statement` | For/who/that/unlike framework. |

### Definition layer

| Skill | Invocation | What it does |
|---|---|---|
| **Product Brief** | `/sweetclaude:product-brief` | Strategic product brief. Outline-first. Sections scale to available input depth. |
| **Product PRD** | `/sweetclaude:product-prd` | Full PRD — functional requirements, NFRs, epics. |
| **Product User Stories** | `/sweetclaude:product-user-stories` | Stories with acceptance criteria. Scoped to all personas, SLC, or MVP. State-tracked: first invocation offers GitHub Issues import; warns (does not block) if `product-user-personas` is not active. Use `pause` to suspend without deleting data. |
| **Product User TDD Tests** | `/sweetclaude:product-user-tdd-tests` | Convert stories to Gherkin `.feature` files for TDD Level 3. |
| **Product Manage Scope** | `/sweetclaude:product-manage-scope` | Track scope changes with rationale. Prevents silent scope creep. |
| **Product Parking Lot** | `/sweetclaude:product-parking-lot` | Manage deferred work. State-tracked: first invocation runs a lightweight setup (optional GitHub Issues import); subsequent invocations proceed immediately. Use `/sweetclaude:product-parking-lot pause` to suspend without deleting data. |
| **Product Sprint Plan** | `/sweetclaude:product-sprint-plan` | Plan a sprint from the backlog. Reports which milestones a sprint advances. Requires `product-parking-lot` to be `active`. |
| **Product Market Messaging** | `/sweetclaude:product-market-messaging` | Elevator pitches, value propositions, key messages per audience. |
| **Product Milestones** | `/sweetclaude:product-milestones [sub]` | Outcome-driven roadmap targets like "Exit Stealth" or "Paid Pilot Live." Sub-commands: `add`, `review`, `link [US-XXX] [MS-XXX]`, `status`, `blockers`, `complete`, `unassigned`. State-tracked: first invocation runs a lightweight setup; use `pause` to suspend, `onboard` for full ceremony. |
| **Product Roadmap Analysis** | `/sweetclaude:product-roadmap-analysis [analyze\|alignment\|item RM-NNN]` | RICE scoring (Reach × Impact × Confidence ÷ Effort) for all planned and active roadmap items. Scope and milestone alignment check. Proposes a revised stack-rank — applies only on confirmation. |

---

## Design (12 skills)

Technical design. Every significant decision is recorded with context and rationale to `.sweetclaude/state/decision-log.md`.

| Skill | Invocation | What it does |
|---|---|---|
| **Design Architecture** | `/sweetclaude:design-architecture` | System architecture. Reads compliance context from discovery and surfaces each derived framework (GDPR, HIPAA, etc.) as a hard requirement throughout the architecture document. Produces ADRs. |
| **Design Tech Spec** | `/sweetclaude:design-tech-spec` | Technical specification. Enforces compliance requirements from architecture state (e.g., confirms chosen providers meet HIPAA BAA or SOC 2 requirements). |
| **Design Data Model** | `/sweetclaude:design-data-model` | Schema and entity design. Tables, relationships, indexes, migration path. |
| **Design API Design** | `/sweetclaude:design-api-design` | Endpoint contracts. Routes, request/response shapes, error codes, versioning. |
| **Design User Flows** | `/sweetclaude:design-user-flows` | Convert user stories into UX/UI flows — step-by-step paths through the interface. |
| **Design UX** | `/sweetclaude:design-ux` | UX design and wireframes. |
| **Design Solutioning Gate** | `/sweetclaude:design-solutioning-gate` | Required before implementation for high-risk work. Confirms the right solution is being built, an alternative was considered, and a rollback plan exists. |
| **Design Change Impact Analysis** | `/sweetclaude:design-change-impact-analysis` | Trace blast radius before changes. Surfaces ripple effects across artifacts before they become bugs. |
| **Design Manage Decisions** | `/sweetclaude:design-manage-decisions` | Record any decision with context, options considered, and rationale. Query later: "Why did we choose X?" |
| **Mockup Sandbox** | `/sweetclaude:mockup-sandbox` | Create an isolated Vite + React + Tailwind + shadcn/ui mockup environment at `artifacts/mockup-sandbox/`. Scaffold components with parallel variants, preview at `localhost:5174`, track approved mockups in `.sweetclaude/state/mockup-registry.yaml`. Start here for any UI work before touching production code. |
| **Mockup Extract** | `/sweetclaude:mockup-extract [ComponentName]` | Extract a component from the main app into the mockup sandbox. Rewrites `@/` imports, stubs API calls/routing/auth, creates a group CSS file from the main app's globals, and type-checks before sharing a preview URL. |
| **Mockup Graduate** | `/sweetclaude:mockup-graduate` | Graduate registry-approved mockups into production code. Analyzes production patterns (routing lib, state management, data fetching), presents a transformation plan before writing any code, adds loading/error/empty states and accessibility, and extracts Gherkin acceptance criteria to `acceptance-criteria-{group}.md`. |

---

## Code (6 skills)

Implementation. These skills enforce TDD via hooks, run tests and reviews, and manage the implementation lifecycle.

| Skill | Invocation | What it does |
|---|---|---|
| **Code Feature** | `/sweetclaude:code-feature [description]` | Build a new feature end-to-end. Generates Gherkin specs if needed. Runs full TDD Level 3 pipeline: test writer → QA caucus → implementer. Verifies. Opens a PR. |
| **Code Issue** | `/sweetclaude:code-issue [issue#]` | Implement a GitHub issue end to end. Reads acceptance criteria from the issue, runs the TDD pipeline, closes the issue. |
| **Code Debt** | `/sweetclaude:code-debt` | Tech debt cleanup. Locks existing behavior with tests (SCOPE phase) before touching code. |
| **Code Testing** | `/sweetclaude:code-testing [mode]` | Menu of four checks: test suite, mutation testing, security review, PR pre-check. Pick one or several. Skips menu if `$ARGUMENTS` passed. |
| **Code Review** | `/sweetclaude:code-review [type]` | Adversarial code, security, and compliance review. Opens a menu. Pick one or several. Assumes problems exist and finds them. |
| **Code TDD** | `/sweetclaude:code-tdd` | TDD enforcement and guidance. Explains the levels, runs the appropriate pipeline for the current work, enforces RED → GREEN → refactor. |

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

## Project Management (10 skills)

Execution-layer tracking. These skills manage the work that delivers the product — not what to build (that's product/), but how the building is organized and tracked.

| Skill | Invocation | What it does |
|---|---|---|
| **Project Issues** | `/sweetclaude:project-issues` | Create, view, update, and close issues. Maintains sprint history per issue. Warns on adrift issues (carried over 2+ sprints). Supports `list`, `backlog`, `view`, `new`, `update`, `close`, `reopen`. |
| **Project Epics** | `/sweetclaude:project-epics` | Group issues into epics with progress tracking. Cancel an epic and its issues return to backlog. Warns if an epic exceeds 12 issues. |
| **Project Sprints** | `/sweetclaude:project-sprints` | Full sprint lifecycle: plan, start, board, update, close, retrospective. Velocity calculated on close. Sprint history maintained per issue. Enforces single active sprint. |
| **Project Backlog** | `/sweetclaude:project-backlog` | Backlog view grouped by priority bucket (NOW/SOONER/SOONISH/LATER/SOMEDAY/UNESTIMATED). Promote issues to a sprint. Surface inferred issues from Flow mode inference. |
| **Project Backlog Triage** | `/sweetclaude:project-backlog-triage` | Structured grooming session. Works through ungroomed issues one at a time using INVEST criteria. Recommend priority + effort, accept/override/skip/split/cancel. Sets status to `ready` when groomed. |
| **Project Roadmap** | `/sweetclaude:project-roadmap` | Priority-stacked roadmap with force-ranked items. Create, activate (routes to correct downstream workflow by type), defer, complete, cancel. Create and view releases. |
| **Project Scope** | `/sweetclaude:project-scope` | Singleton scope document — one statement, in-scope list, minimum three out-of-scope items. Cascade review on update flags conflicting open roadmap items and issues. |
| **Project Goals** | `/sweetclaude:project-goals` | Binary business goals — achieved or not. Criteria must be evaluable as true/false. `list`, `view`, `new`, `achieved`, `missed`. |
| **Project Mode** | `/sweetclaude:project-mode` | Assess and shift project modes: flow → kanban → shape_up → agile → agile_enterprise. Snapshots state before every shift. Detects upshift/downshift signals from artifact counts. Hard block: agile_enterprise → flow requires `--force`. |

---

## Testing (6 skills)

Independent QA, security, compliance, and performance validation — not tied to a single feature's TDD cycle. All actionable findings file directly to project-issues.

| Skill | Invocation | What it does |
|---|---|---|
| **Testing Plan** | `/sweetclaude:testing-plan` | Define a test strategy for a feature, release, or area. Scope, test types, environments, entry criteria, exit criteria. Challenges vague exit criteria before accepting. |
| **Testing Security** | `/sweetclaude:testing-security` | Structured security review. STRIDE threat model → OWASP Top 10 checklist → dependency audit. P0 findings block release. P0/P1 filed as `now`-priority issues. |
| **Testing Compliance** | `/sweetclaude:testing-compliance` | Control testing and evidence collection for SOC 2, HIPAA, GDPR, and PCI-DSS. Track per-control status (pass/partial/gap/N/A), log evidence locations, generate gap reports. Gaps filed as issues. |
| **Testing Session** | `/sweetclaude:testing-session` | Manual QA session — scripted test cases or exploratory charter. Pass/fail per case. File bugs mid-session; severity maps to issue priority. Resume open sessions. |
| **Testing Performance** | `/sweetclaude:testing-performance` | Load scenario definitions, baseline recording, and benchmark comparison. Regression detection with configurable p50/p95/p99 and error rate thresholds. Tool-agnostic: works with k6, Locust, wrk, or manual runs. |
| **Testing Accessibility** | `/sweetclaude:testing-accessibility` | WCAG 2.1 Level AA audit. Automated scan guidance + manual keyboard navigation, screen reader, and visual checklist. Critical findings block release. Findings filed as issues. |

---

## Deploy (2 skills)

Deployment and incident response.

| Skill | Invocation | What it does |
|---|---|---|
| **Deploy Ship** | `/sweetclaude:deploy-ship` | Guided deployment for work items that have completed VERIFY. Confirms deployment config, runs a 7-item pre-ship checklist (AC met, tests passing, no secrets in diff, changelog present, rollback plan documented, break-glass notes updated at GA+, monitoring active), guides the deploy command, and smoke-tests post-deploy. Does not run the deploy itself — guides you through it. Logs checklist result and smoke test to `decision-log.md`. |
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

### Document Corpus modes

```
status       Pipeline state, file counts, what to do next
consolidate  Scan, deduplicate, ingest into raw/inbox/
triage       Classify each file (keep/reconcile/discard/defer)
reconcile    Draft canonical documents from related files
promote      Finalize with provenance, archive sources, RAG index
rag          Set up local RAG search (installs mcp-local-rag)
reindex      Rebuild RAG embeddings
```

---

## Common Skill Combinations

You rarely use one skill in isolation. The patterns below are the chains that show up most often.

**New project from idea to first feature:**
```
/sweetclaude:on
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

**Adopting an existing codebase:**
```
/sweetclaude:adopt
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

**Hotfix:**
```
/sweetclaude:find-skill "production is broken"
→ hotfix workflow (compressed)
→ DIAGNOSE → IMPLEMENT (test+fix) → SHIP → POST-MORTEM
```

**Production incident:**
```
/sweetclaude:something-broke
→ severity classification (P0/P1/P2)
→ fix-vs-rollback decision
→ :hotfix or :rollback-revert
→ confirm resolution → mandatory post-mortem
```

**Document organization:**
```
/sweetclaude:document-corpus
→ consolidate → triage → reconcile → promote → rag
```

**Course correction mid-project:**
```
/sweetclaude:find-skill "we need to pivot"
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

## What to Read Next

- How these skills chain in real scenarios → [Walkthroughs](walkthroughs.md)
- Why the skills are organized this way → [How It Works](how-it-works.md)
- Phase exit criteria the skills are written against → [Phases and Workflows](phases-and-workflows.md)
