# Skill Reorganization Plan — 2026-04-13 v2

**Goal:** Restructure SweetClaude from the current code/strategy two-track model into a five-bucket architecture: strategy/, product/, design/, code/, deploy/ plus orchestration skills at root.

**Supersedes:** The code/strategy split from `docs/strategy-split-design-v1-2026-04-13.md`. That design introduced dual tracks. This plan replaces those two tracks with five domain buckets.

---

## Target Skill Map (47 skills)

### Orchestration (root) — 7 skills
| Skill | Status | Notes |
|---|---|---|
| sweetclaude | Exists | Master router — update for 5-bucket routing |
| help | Exists | Update command list for all 47 skills |
| status | **New** | Orient to project: what's done, what's pending, what's next |
| auto-flow | **New** | Walk through the pipeline step by step, invoke skills in sequence |
| init | Exists | Update directory scaffolding for 5-bucket structure |
| new-task | Exists | Update classification for 5 buckets |
| hibernate | Exists | No change needed |

### strategy/ — 8 skills
| Skill | Status | Notes |
|---|---|---|
| strategy/concept | **New** | Articulate what this is and why it exists |
| strategy/pain-thesis | **New** | Structured pain analysis (user has implementation guide) |
| strategy/ideal-customer-profile | **New** | Who specifically has this pain and will pay/use |
| strategy/competitive-analysis | **New** | Strategic-level landscape, alternatives, differentiation |
| strategy/academic-research | Exists | Was strategy/academic — rename |
| strategy/meeting-prep | Designed | Interface contract in strategy-split-design |
| strategy/narrative-arc | Designed | Interface contract in strategy-split-design |
| strategy/market-messaging | **New** | How you talk about it externally |

### product/ — 13 skills
| Skill | Status | Notes |
|---|---|---|
| product/discovery | Exists | Was discover (root) — move into product/ |
| product/positioning-statement | **New** | How the product is positioned |
| product/product-brief | **New wrapper** | Wraps [removed] + preflight guard |
| product/prd | **New wrapper** | Wraps [removed] |
| product/user-story | **New wrapper** | Wraps [removed] |
| product/user-tdd-tests | Exists | Was code/gherkin-bridge — move + rename |
| product/user-success-criteria | **New** | Measurable success definitions per persona/task |
| product/user-workflows | **New** | Convert user stories to UX/UI flows |
| product/manage-scope | Exists | Was code/scope-tracker — move + rename |
| product/backlog | Exists | Was standalone backlog-management — move |
| product/sprint-plan | **New wrapper** | Wraps [removed] |
| product/research | **New wrapper** | Wraps [removed] |
| product/feature-competitive | **New** | Product-level competitive feature/capability analysis |

### design/ — 11 skills
| Skill | Status | Notes |
|---|---|---|
| design/architecture | **New wrapper** | Wraps [removed] |
| design/tech-spec | **New wrapper** | Wraps [removed] |
| design/ux | **New wrapper** | Wraps [removed] |
| design/solutioning-gate | **New wrapper** | Wraps [removed] |
| design/change-impact-analysis | Exists | Was code/ripple — move + rename |
| design/update-docs | Exists | Was code/auto-docs — move + rename |
| design/data-model | **New** | Schema design, entity relationships, migration planning |
| design/api-design | **New** | Endpoint contracts, request/response shapes, versioning |
| design/services-design | **New** | Service boundaries, communication patterns, dependencies |
| design/infra-design | **New** | Infrastructure, deployment targets, environments |
| design/manage-decisions | **New** | Record and track decisions with rationale (replaces ADR) |

### code/ — 8 skills
| Skill | Status | Notes |
|---|---|---|
| code/tdd | Exists | No change |
| code/work-issue | Exists | Was code/fix-issue — rename |
| code/work-debt | **New** | Tech debt cleanup, lock behavior with tests first |
| code/pr-precheck | Exists | Was code/pr-ready — rename |
| code/qa-testing | **New** | Run test suites, report failures concisely |
| code/mutation-testing | Exists | No change |
| code/security-testing | **New** | Security review of code changes (promotes existing agent) |
| code/code-review | **New** | Adversarial code review (promotes existing agent) |

### deploy/ — deferred
Not scoped yet. Will cover PR finishing, CI/CD gates, verification, shipping.

---

## Migration Map

### Existing skills that move:
| Current Location | New Location | Change Type |
|---|---|---|
| discover/ | product/discovery/ | move |
| code/gherkin-bridge/ | product/user-tdd-tests/ | move + rename |
| code/scope-tracker/ | product/manage-scope/ | move + rename |
| code/ripple/ | design/change-impact-analysis/ | move + rename |
| code/auto-docs/ | design/update-docs/ | move + rename |
| code/fix-issue/ | code/work-issue/ | rename |
| code/pr-ready/ | code/pr-precheck/ | rename |
| strategy/academic/ | strategy/academic-research/ | rename |
| backlog-management (standalone) | product/backlog/ | move |

### Existing skills that stay:
| Skill | Change |
|---|---|
| sweetclaude | Update routing logic for 5 buckets |
| help | Update command list |
| init | Update scaffolding for 5-bucket dirs |
| new-task | Update classification for 5 buckets |
| hibernate | No change |
| code/tdd | No change |
| code/mutation-testing | No change |

### Removed:
| Skill | Reason |
|---|---|
| strategy/reconciliation | Becomes part of init onboarding workflow |

---

## Totals

| Category | Exists/Move | New | [removed] Wrapper | Designed | Total |
|---|---|---|---|---|---|
| Orchestration | 5 | 2 | 0 | 0 | 7 |
| strategy/ | 1 | 5 | 0 | 2 | 8 |
| product/ | 4 | 3 | 5 | 0 | 12 |
| design/ | 2 | 5 | 4 | 0 | 11 |
| code/ | 4 | 4 | 0 | 0 | 8 |
| **Total** | **16** | **19** | **9** | **2** | **46** |

Note: Product shows 12 in the breakdown but 13 in the skill map — product/feature-competitive brings it to 13. Corrected total: **47**.

---

## Execution Phases

### Phase 1: Restructure and move
Create the new directory structure and move all existing skills to their new homes. This is mechanical — no new skill content, just file moves, renames, and reference updates.

1. Create directories: strategy/, product/, design/, code/ under framework/skills/
2. Move 9 existing skills to new locations (see migration map)
3. Update frontmatter `name:` field in every moved/renamed skill
4. Update preflight-guard blocks in every moved skill
5. Delete emptied old directories
6. Update phase-skills.yaml — replace code:/strategy: with 5-bucket keys
7. Update phase-gates.md — all skill references
8. Update master SKILL.md — routing logic for 5 buckets
9. Update help SKILL.md — full command list
10. Update new-task SKILL.md — classification for 5 buckets
11. Update init SKILL.md — scaffold 5-bucket directory structure
12. Sync everything to ~/.claude/
13. Verify with diff
14. Commit

### Phase 2: New orchestration skills
Build the two new orchestration skills that drive the user experience.

1. **status** — read phase state, git log, working repo artifacts; present: where you are, what's done, what's pending, what's next
2. **auto-flow** — read current position in pipeline, determine next step, invoke the right skill, repeat; stop at phase gates for approval

### Phase 3: [removed] wrappers
Build 9 thin wrapper skills that add the preflight guard and SweetClaude context before delegating to [removed].

Each wrapper:
- Has preflight-guard block
- Sets up SweetClaude context (current phase, deference level, relevant state)
- Invokes the [removed] skill
- Captures outputs to working repo

Skills:
1. product/product-brief → [removed]
2. product/prd → [removed]
3. product/user-story → [removed]
4. product/sprint-plan → [removed]
5. product/research → [removed]
6. design/architecture → [removed]
7. design/tech-spec → [removed]
8. design/ux → [removed]
9. design/solutioning-gate → [removed]

### Phase 4: New skills (priority order)
Build new skills that don't exist yet. Ordered by dependency and immediate usefulness.

**Tier 1 — strategy foundation** (blocks everything else)
1. strategy/concept
2. strategy/pain-thesis (user has implementation guide)
3. strategy/ideal-customer-profile

**Tier 2 — code workflows** (common daily use)
4. code/work-debt
5. code/qa-testing
6. code/security-testing (promote from agent)
7. code/code-review (promote from agent)

**Tier 3 — product skills**
8. product/positioning-statement
9. product/user-success-criteria
10. product/user-workflows
11. product/feature-competitive

**Tier 4 — design skills**
12. design/data-model
13. design/api-design
14. design/services-design
15. design/infra-design
16. design/manage-decisions

**Tier 5 — remaining strategy**
17. strategy/market-messaging
18. strategy/meeting-prep (designed, needs implementation)
19. strategy/narrative-arc (designed, needs own design cycle for knowledge graph)

### Phase 5: Update all docs
- README.md — 5-bucket structure, updated "What's in the Box", user help for all commands
- Architecture doc — new skill map, components, phase-skill mapping
- PRD — new epics for each bucket
- Strategy-split design — mark as superseded
- Reconciliation plan — mark as superseded (reconciliation folded into init)
- This plan — mark phases as completed

---

## Config Changes

### phase-skills.yaml
Replace `code:` and `strategy:` top-level keys with five bucket keys: `strategy:`, `product:`, `design:`, `code:`, `deploy:`. The new-task and auto-flow skills classify into one of these buckets and surface appropriate skills.

### phase-gates.md
Update all "Available skills:" lines to reference new paths. Add bucket-specific exit criteria where the current phase-gate model maps to a bucket (e.g., product/ skills map to Discover+Define+Plan gates, design/ maps to Design gate, code/ maps to Implement gate).

### model-routing.yaml
Add routing for new skills. Strategy and design skills default to opus for reasoning quality. Code skills default to sonnet. QA/testing defaults to haiku.

### defaults.yaml
No change expected.

---

## User-Level Help (all 47 commands)

### Orchestration

**`/sweetclaude`** — Start a SweetClaude session. Checks if the project is configured, reads your phase state, asks your deference level, and tells you where you left off. If the project isn't set up, walks you through it.

**`/sweetclaude:help`** — Shows whether SweetClaude is configured for this project, what phase you're in, and lists every command you can run.

**`/sweetclaude:status`** — Orient to the project. Reads phase state, recent git history, and working repo artifacts. Tells you: where you are, what's been done, what's pending, and what the logical next step is.

**`/sweetclaude:auto-flow`** — Walks you through the pipeline step by step. Figures out where you are, picks the right skill for the next step, invokes it, then moves to the next. You approve or redirect at each step. Stops at phase gates for your sign-off.

**`/sweetclaude:init`** — Sets up SweetClaude for this project. Creates the working repo, state files, and CLAUDE.md. Asks if you have existing strategy files to onboard. Handles code repos, strategy-only projects, or both.

**`/sweetclaude:new-task`** — You describe what you need to do. SweetClaude classifies it (feature, bug, research paper, tech debt, etc.), picks the right bucket and pipeline entry point, and surfaces the tools for that work.

**`/sweetclaude:hibernate`** — Freezes the project. Captures your current phase, deference level, decisions, and improvement notes into HIBERNATION.md. When you come back, thaws it and picks up where you stopped.

### Strategy

**`/sweetclaude:strategy/concept`** — Articulate what this project is and why it exists. Produces a clear concept statement grounded in the problem being solved.

**`/sweetclaude:strategy/pain-thesis`** — Structured analysis of the pain your product addresses. Who feels it, how badly, what they do today, and why existing solutions fail. Uses a guided framework.

**`/sweetclaude:strategy/ideal-customer-profile`** — Define who specifically has this pain and will pay or use your solution. Demographics, behaviors, triggers, deal-breakers.

**`/sweetclaude:strategy/competitive-analysis`** — Strategic-level landscape analysis. Who else operates in this space, how they're positioned, where the gaps are, and what your differentiation is.

**`/sweetclaude:strategy/academic-research`** — Tell it what paper you're writing. Walks you through six phases: nail down your thesis and what's novel, review 35+ papers and find gaps, pick a venue and build a scored outline, draft section by section with quality checks, simulate peer review and revise, format and submit.

**`/sweetclaude:strategy/meeting-prep`** — Give it who, when, and purpose. It pulls relevant context from your strategy corpus, drafts an agenda, talking points with confidence levels, key asks, anticipated questions with responses, and leave-behinds. Post-meeting debrief updates the narrative arc.

**`/sweetclaude:strategy/narrative-arc`** — Build and query a knowledge graph connecting your strategic claims, proof points, objectives, and supporting/opposing evidence. Answers "what supports this claim" and "what would strengthen this objective."

**`/sweetclaude:strategy/market-messaging`** — Craft external messaging — how you describe the product, the problem, and the value to different audiences.

### Product

**`/sweetclaude:product/discovery`** — Walks you through structured discovery for a new product. Interviews you about user personas one at a time, then proposes features for you to include or exclude, then optionally researches competitors. Produces a documented feature set and persona map.

**`/sweetclaude:product/positioning-statement`** — Define how the product is positioned — for whom, what category, what differentiates it, and why that matters.

**`/sweetclaude:product/product-brief`** — Walks you through an 11-section product brief: executive summary, problem, audience, solution, goals, scope, stakeholders, constraints, success criteria, timeline, risks. One section at a time with probing follow-ups.

**`/sweetclaude:product/prd`** — Produces a full PRD with functional requirements, non-functional requirements, epics, user flows, dependencies, and assumptions. Builds on the product brief.

**`/sweetclaude:product/user-story`** — Write a user story with acceptance criteria from a feature or epic. Produces a story file with As-a/I-want/So-that plus testable acceptance criteria.

**`/sweetclaude:product/user-tdd-tests`** — Give it a user story. It produces a Gherkin `.feature` file with Given/When/Then scenarios covering happy path, errors, and edge cases. That `.feature` file is what TDD Level 3 uses to generate tests.

**`/sweetclaude:product/user-success-criteria`** — Define measurable success for each persona and task. Each criterion is evaluable as true/false after the product ships — no vague "users are happy."

**`/sweetclaude:product/user-workflows`** — Convert user stories into UX/UI flows showing the step-by-step path a user takes through the interface.

**`/sweetclaude:product/manage-scope`** — When you decide something is in scope that wasn't, or out that was, tell this command what changed and why. It logs the decision with rationale, updates the PRD's scope lists, and flags if any existing stories, architecture decisions, or tests are now invalidated.

**`/sweetclaude:product/backlog`** — Add, review, prioritize, or groom deferred work items. Tracks what's been parked and why, surfaces items when they become relevant.

**`/sweetclaude:product/sprint-plan`** — Plan a sprint by selecting stories from the backlog, estimating scope, and producing a sprint commitment with clear deliverables.

**`/sweetclaude:product/research`** — Conduct market or technical research on a specific question. Returns findings with evidence and sources, identifies gaps explicitly.

**`/sweetclaude:product/feature-competitive`** — Product-level competitive analysis focused on features and capabilities. Compare your feature set against competitors, identify table-stakes features, and find differentiation opportunities.

### Design

**`/sweetclaude:design/architecture`** — Define the system architecture: components, boundaries, communication patterns, data flow, and key technical decisions.

**`/sweetclaude:design/tech-spec`** — Produce a technical specification for a feature or system: detailed design, data structures, algorithms, error handling, and edge cases.

**`/sweetclaude:design/ux`** — Design the user experience: wireframes, interaction patterns, navigation, and user flow diagrams.

**`/sweetclaude:design/solutioning-gate`** — Run a quality check on the proposed solution before implementation. Validates architecture decisions, identifies risks, and confirms the design addresses the requirements.

**`/sweetclaude:design/change-impact-analysis`** — Tell it what you're about to change. It traces every file, test, API endpoint, and doc that depends on that code, then shows you the blast radius before you touch anything. Also works for spec/doc changes.

**`/sweetclaude:design/update-docs`** — Run after implementation. It diffs what changed, finds existing docs that reference the changed behavior, and proposes updates for your approval. Won't create new docs — only updates what's already there.

**`/sweetclaude:design/data-model`** — Design the data model: entities, relationships, constraints, indexes, and migration strategy. Produces schema definitions and migration plans.

**`/sweetclaude:design/api-design`** — Design API endpoints: routes, request/response shapes, authentication, pagination, error responses, and versioning strategy.

**`/sweetclaude:design/services-design`** — Design service boundaries: which services exist, how they communicate, what each owns, and where the boundaries are.

**`/sweetclaude:design/infra-design`** — Design infrastructure: deployment targets, environments, CI/CD pipeline, monitoring, and scaling strategy.

**`/sweetclaude:design/manage-decisions`** — Record a design or architecture decision with context, options considered, decision made, and rationale. Queryable later — "why did we choose X?"

### Code

**`/sweetclaude:code/tdd`** — You tell it what to build. It picks a TDD level based on complexity (you confirm), then runs the cycle: writes failing tests, confirms RED, implements to make them pass, confirms GREEN, refactors. At higher levels, it uses separate subagents for test writing and implementation so neither can cheat.

**`/sweetclaude:code/work-issue`** — Give it a GitHub issue number. It reads the issue, analyzes what's affected, proposes a plan for your approval, implements with TDD, verifies everything passes, updates docs, and opens a PR.

**`/sweetclaude:code/work-debt`** — Tell it what tech debt to address. It locks the current behavior with tests first (so nothing breaks), then refactors. Tests before touch, always.

**`/sweetclaude:code/pr-precheck`** — Run before opening a PR. It checks acceptance criteria, runs tests, greps for secrets and debug code, fills the PR template, verifies docs are current. Tells you what's missing and fixes it. Won't open the PR until everything passes.

**`/sweetclaude:code/qa-testing`** — Run the test suite for a package or service. Reports pass/fail concisely — just failures with file, line, and assertion, not full stdout dumps.

**`/sweetclaude:code/mutation-testing`** — Run after tests pass. It introduces small code mutations and checks if your tests catch them. Reports which mutations survived and whether the gaps matter. Optional.

**`/sweetclaude:code/security-testing`** — Review code changes for security issues: auth problems, injection vulnerabilities, secrets exposure, tenant boundary violations. Returns prioritized findings.

**`/sweetclaude:code/code-review`** — Adversarial code review focused on logic errors, edge cases, regressions, performance, and missing error handling. Does not flag style issues.
