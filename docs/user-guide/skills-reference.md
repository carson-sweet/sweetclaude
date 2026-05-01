# Skills Reference

**Version:** 1.0
**Date:** 2026-05-01

All 52 skills, organized by domain. This page is reference — for narrative explanations of how skills fit together, read [Walkthroughs](walkthroughs.md) and [How It Works](how-it-works.md).

You rarely need to memorize commands. `/sweetclaude:go` and `/sweetclaude:find-skill` route automatically based on project state and what you describe. The list below is for when you know what you want.

Many skills accept `$ARGUMENTS` to skip menus: `/sweetclaude:code-testing security`, `/sweetclaude:product-milestones add`, `/sweetclaude:document-corpus triage`.

---

## How to Use This Page

If you are looking up a specific skill, jump to its section. The bucket headings are: Orchestration, Product, Design, Code, Documents, plus the specialist subagent roster at the bottom.

If you are wondering "which skills go together for X?", the [Walkthroughs](walkthroughs.md) page chains skills end-to-end for six common scenarios. This page is the lookup; that page is the recipe.

---

## Orchestration (16 skills)

Session management, routing, framework health. Most of these are invoked automatically.

| Skill | Invocation | What it does |
|---|---|---|
| **Master** | _(auto)_ | Session entry point. Pre-flight check, phase state read, route to the right skill. Fires automatically at session start for configured projects. |
| **On** | `/sweetclaude:on` | Activate on any project — new idea or existing codebase. Detects context. Walks through setup. |
| **Off** | `/sweetclaude:off` | Suspend SweetClaude for this project. Preserves all artifacts. Reactivate with `:on`. |
| **Go** | `/sweetclaude:go` | Pick up where you left off. Reads state, checks phase exit criteria, routes to the right skill. No menu — it acts. |
| **Find Skill** | `/sweetclaude:find-skill` | Describe what you want to do. The framework classifies, confirms, updates state, and starts the right skill. |
| **Status** | `/sweetclaude:status` | Project status dashboard. Active work item, phase, recent commits, open issues, what's next. Fires automatically at session start for active projects. |
| **Next Steps** | `/sweetclaude:next-steps` | Walk through the pipeline step by step. Explains what the current phase requires and what comes after. |
| **Help** | `/sweetclaude:help` | Conversational help — describe what you want, learn how to work through prompting. Or browse all commands by category. |
| **Hibernate** | `/sweetclaude:hibernate` | Freeze a project. Saves full state, exports session context, disables auto-status. Resume later with `:on`. |
| **Purge** | `/sweetclaude:purge` | Delete all SweetClaude artifacts. Recommends a backup branch first. Requires typed confirmation. |
| **Update** | `/sweetclaude:update` | Fetch the latest version from GitHub and sync to all installed locations. Shows what changed. |
| **Fix SweetClaude** | `/sweetclaude:fix-sweetclaude` | Audit and repair configuration. Checks CLAUDE.md accuracy, phase state, file locations, empty registers. Proposes fixes — does not change anything without asking. |
| **Guardian On** | `/sweetclaude:guardian-on` | Enable Protocol Guardian. Enforces skill invocations, TDD discipline, and artifact saves for the rest of the session. |
| **Guardian Off** | `/sweetclaude:guardian-off` | Disable Protocol Guardian. |
| **Session Export** | `/sweetclaude:session-export` | Export a Claude.ai conversation as a structured document for corpus ingestion. |
| **Usage** | `/sweetclaude:usage` | View, enable, or disable local usage tracking. |

---

## Product (14 skills)

Strategy and product definition. Useful before any code is written and on existing projects to document implicit strategy.

### Discovery layer

| Skill | Invocation | What it does |
|---|---|---|
| **Product Discovery** | `/sweetclaude:product-discovery` | Establish what is being built, for whom, and why. Three depth levels: L1 quick intent, L2 problem and success, L3 full pain thesis. Collects compliance context (data categories, geography, user type) and derives applicable frameworks (GDPR, HIPAA, PCI DSS) — written to state for use throughout the pipeline. |
| **Product Research** | `/sweetclaude:product-research` | Market and solution research. Feeds the competitive seed list. |
| **Product Competition** | `/sweetclaude:product-competition` | Three depth levels: survey (who's in the space), matrix (structured comparison), feature-deep (capability analysis). |
| **Product User Personas** | `/sweetclaude:product-user-personas` | Define users — who they are, what tasks they need to do, what success looks like. Includes triggers and deal-breakers. |
| **Product Positioning Statement** | `/sweetclaude:product-positioning-statement` | For/who/that/unlike framework. |

### Definition layer

| Skill | Invocation | What it does |
|---|---|---|
| **Product Brief** | `/sweetclaude:product-brief` | Strategic product brief. Outline-first. Sections scale to available input depth. |
| **Product PRD** | `/sweetclaude:product-prd` | Full PRD — functional requirements, NFRs, epics. |
| **Product User Stories** | `/sweetclaude:product-user-stories` | Stories with acceptance criteria. Scoped to all personas, SLC, or MVP. |
| **Product User TDD Tests** | `/sweetclaude:product-user-tdd-tests` | Convert stories to Gherkin `.feature` files for TDD Level 3. |
| **Product Manage Scope** | `/sweetclaude:product-manage-scope` | Track scope changes with rationale. Prevents silent scope creep. |
| **Product Backlog** | `/sweetclaude:product-backlog` | Manage deferred work. |
| **Product Sprint Plan** | `/sweetclaude:product-sprint-plan` | Plan a sprint from the backlog. Reports which milestones a sprint advances. |
| **Product Market Messaging** | `/sweetclaude:product-market-messaging` | Elevator pitches, value propositions, key messages per audience. |
| **Product Milestones** | `/sweetclaude:product-milestones [sub]` | Outcome-driven roadmap targets like "Exit Stealth" or "Paid Pilot Live." Sub-commands: `add`, `review`, `link [US-XXX] [MS-XXX]`, `status`, `blockers`, `complete`, `unassigned`. |

---

## Design (9 skills)

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

## Documents and Strategy Specialists (7 skills)

Long-form document work, corpus management, and specialized strategy capabilities.

| Skill | Invocation | What it does |
|---|---|---|
| **Document Corpus** | `/sweetclaude:document-corpus [mode]` | Four-step pipeline for messy documents: consolidate → triage → reconcile → promote. Then index for RAG search. Full reference: [corpus-system.md](corpus-system.md). |
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

**Adopting an existing project, then fixing a flagged concern:**
```
/sweetclaude:on
→ (interview reveals concern)
→ code-debt (lock behavior with tests)
→ refactor in IMPLEMENT
→ code-review
→ code-testing pr-precheck
```

**Hotfix:**
```
/sweetclaude:find-skill "production is broken"
→ hotfix workflow (compressed)
→ DIAGNOSE → IMPLEMENT (test+fix) → SHIP → POST-MORTEM
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
