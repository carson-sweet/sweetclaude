# PRD: SweetClaude v1.1 — 2026-04-13

**Author:** Carson Sweet
**Status:** Draft
**Product Brief:** `docs/product-brief-sweetclaude-v1-2026-04-12.md`
**Brainstorm:** `docs/brainstorm-sweetclaude-2026-04-12.md`
**TDD Analysis:** `docs/tdd-analysis-v1-2026-04-12.md`

---

## Business Objectives

1. Release v1.0 internal build today (2026-04-12)
2. Establish SweetClaude as the reference framework for disciplined AI-assisted TDD development
3. Build a contributor community around non-commercial open-source
4. Give every solo developer access to a structured, disciplined, creative development pipeline

**Success Metrics:**
- GitHub stars and forks
- Projects bootstrapped with `sweetclaude init`
- Community contributions
- TDD enforcement effectiveness (does it prevent AI cheating?)

---

## User Personas

**Primary: Solo Developer**
- Builds across broad spectrum (web apps, microservices, CLIs, APIs, utilities)
- No single language or framework
- Works fast but wants discipline
- Follows deliberate progression: concept → landscape → functional definition → architecture → code
- Wants a creative partner, not a passive tool

**Secondary: Small Team (2-3 devs)**
- Wants shared development framework with quality gates
- Future consideration — v1.0 targets solo developers

**Secondary: TDD Newcomer**
- Wants enforced discipline, not advisory guidance
- Benefits from SweetClaude making TDD non-optional

---

## Key User Flows

**Flow 1: New Project**
```
sweetclaude init <name> → Discover → Define → Design → Plan → Implement → Verify → Ship
```

**Flow 2: Bug Fix**
```
"I found a bug" → Define (reproduce/characterize) → Design (determine fix) →
Implement (regression test first, then fix) → Verify → Ship
May escalate to Discover if bug reveals design flaw.
```

**Flow 3: Feature Enhancement**
```
"This feature needs to be better" → Define → Design → Implement → Verify → Ship
May escalate to Discover if enhancement has architectural implications.
```

**Flow 4: Iteration / Tech Debt**
```
"This needs cleanup" → Define → Design → Implement (lock behavior with tests first) →
Verify → Ship
Tech debt clearance is iteration work.
May escalate to Discover if iteration reveals structural issues.
```

**Flow 5: Net-New Feature on Existing Project**
```
"I want to add X" → Discover → Define → Design → Plan → Implement → Verify → Ship
Full pipeline.
```

---

## Functional Requirements

### EPIC-001: Project Bootstrap

#### FR-001: One-Command Project Init
**Priority:** Must Have
**Description:** `sweetclaude init <project-name>` creates a complete project environment: code repo, SweetClaude working repo, GitHub remotes for both, project-level CLAUDE.md auto-generated from codebase discovery, RAG index initialized, directory structure scaffolded.
**Acceptance Criteria:**
- [ ] Single command creates both repos with correct directory structure
- [ ] Both repos pushed to GitHub as private repos under user's account
- [ ] Project CLAUDE.md generated with detected language, framework, build/test commands
- [ ] RAG index initialized
- [ ] Total setup time under 5 minutes
**Dependencies:** FR-002

#### FR-002: Codebase Discovery
**Priority:** Must Have
**Description:** Automatically detect language(s), framework(s), package manager, test runner, formatter, build commands, and directory structure. Use findings to generate project CLAUDE.md and configure SweetClaude for the project.
**Acceptance Criteria:**
- [ ] Identifies at least: Python, TypeScript/JavaScript, Go, Rust, Java
- [ ] Detects test runner and generates correct test commands
- [ ] Detects formatter and generates correct format commands
- [ ] Works on empty projects (scaffolds defaults) and existing codebases

#### FR-003: Optional Notion Scaffold
**Priority:** Should Have
**Description:** During init, user is asked if they want Notion integration. If yes, creates project workspace with pages for PRD, tech spec, ADRs, and stories.
**Acceptance Criteria:**
- [ ] Opt-in prompt during init
- [ ] Creates structured Notion pages linked to project
- [ ] Skipping does not break any other functionality

---

### EPIC-002: Phase Pipeline & Work-Type Routing

#### FR-004: Phase Pipeline Engine
**Priority:** Must Have
**Description:** Seven-phase pipeline (Discover → Define → Design → Plan → Implement → Verify → Ship) with defined entry criteria, exit criteria, and available skills per phase. Tracks current phase in the SweetClaude working repo.
**Acceptance Criteria:**
- [ ] Each phase has documented entry/exit criteria
- [ ] Phase state persisted to working repo (survives session restart)
- [ ] Cannot advance to next phase without exit criteria met (with user override)
- [ ] Phase transitions create git checkpoints in working repo

#### FR-005: Work-Type Router
**Priority:** Must Have
**Description:** At the start of any work, SweetClaude identifies the type of work and routes to the correct pipeline entry point.
**Acceptance Criteria:**
- [ ] Net-new features → enter at Discover (Phase 1)
- [ ] Bug fixes → enter at Define (Phase 2)
- [ ] Feature enhancements → enter at Define (Phase 2)
- [ ] Iteration/tech debt → enter at Define (Phase 2)
- [ ] Any work type can escalate to Discover if deeper issues surface

#### FR-006: Phase-Aware Skill Surfacing
**Priority:** Must Have
**Description:** Only skills and workflows relevant to the current phase are surfaced. Reduces context window load and prevents wrong-tool selection.
**Acceptance Criteria:**
- [ ] Each phase has a defined skill set
- [ ] Skills outside current phase are not loaded into context
- [ ] User can explicitly request an out-of-phase skill (override)

#### FR-025: Mid-Stream Work-Type Detection
**Priority:** Should Have
**Description:** SweetClaude recognizes when the nature of work shifts during a session (e.g., from brainstorming to implementation, or from feature work to bug fix) and adapts routing without requiring user to formally declare a new work type.
**Acceptance Criteria:**
- [ ] Detects work-type shift from conversation context
- [ ] Proposes rerouting: "This looks like it's becoming a [type]. Want to shift?"
- [ ] User confirms before rerouting
- [ ] Previous work state preserved (not lost on reroute)

#### FR-026: Phase Re-Entry Support
**Priority:** Must Have
**Description:** Revisiting earlier phases is normal and expected. When new information surfaces during later phases (e.g., TDD analysis during planning reveals architectural gaps), SweetClaude supports going back to update earlier-phase artifacts without treating it as a failure.
**Acceptance Criteria:**
- [ ] User can explicitly return to any earlier phase
- [ ] SweetClaude can recommend re-entry when it detects earlier-phase assumptions are invalidated
- [ ] Earlier-phase artifacts are updated, not replaced (preserves history)
- [ ] Re-entry logged in decision log with rationale

---

### EPIC-003: TDD Enforcement

#### FR-007: SweetClaude TDD Skill
**Priority:** Must Have
**Description:** Unified TDD skill with four process levels, language/framework agnostic, combining real-tdd philosophy with hook-based enforcement.
**Acceptance Criteria:**
- [ ] Level 0 (Hotfix): fix first, test in same session
- [ ] Level 1 (Light): single-context RED-GREEN-REFACTOR for simple work
- [ ] Level 2 (Standard): subagent separation, tests committed before implementation
- [ ] Level 3 (Full): Gherkin → test writer agent → QA caucus → implementer agent
- [ ] Works with any language and test framework detected during init

#### FR-008: Test File Guardian Hook
**Priority:** Must Have
**Description:** PreToolUse hook that blocks ALL Write/Edit operations targeting test files during implementation phase.
**Acceptance Criteria:**
- [ ] Blocks edits to test files during implementation
- [ ] Returns clear error: "Test files are immutable during implementation. Fix your code, not the tests."
- [ ] Can be overridden only with explicit user approval
- [ ] Active during TDD levels 1-3

#### FR-009: Auto-Test Runner Hook
**Priority:** Must Have
**Description:** PostToolUse hook that automatically runs relevant tests after any source file edit. Feeds failures back to the agent immediately.
**Acceptance Criteria:**
- [ ] Detects which test files are relevant to the changed source file
- [ ] Runs tests after each Edit/Write to source files
- [ ] Failure output fed back to agent for immediate correction
- [ ] Does not run during test-writing phase (only during implementation)

#### FR-010: Git Checkpoint Enforcement
**Priority:** Must Have
**Description:** After tests are written and confirmed RED, auto-commit with descriptive message before implementation begins. Any modification to test files during implementation is detectable via git diff.
**Acceptance Criteria:**
- [ ] Failing tests auto-committed with message `test: RED - [story-id] failing tests`
- [ ] Commit happens before implementer agent starts
- [ ] `git diff` on test files during implementation = detectable violation

#### FR-011: Gherkin Bridge
**Priority:** Must Have
**Description:** Formal transition from BMAD user stories to Gherkin `.feature` files that serve as the contract for TDD test generation.
**Acceptance Criteria:**
- [ ] BMAD stories with acceptance criteria → `.feature` files with Given/When/Then
- [ ] `.feature` files stored in working repo with traceability to source story
- [ ] Test writer agent reads `.feature` files to generate test cases
- [ ] Works at TDD Level 3

#### FR-012: QA Caucus
**Priority:** Should Have
**Description:** Three parallel subagents review the test plan before implementation: service/API expert, component expert, integration/cross-cutting expert. Returns missing test cases and gaps.
**Acceptance Criteria:**
- [ ] Three subagents run in parallel
- [ ] Each reviews from a different angle
- [ ] Consolidated gap list presented to user for approval
- [ ] Approved gaps added to test files before implementation begins

#### FR-013: Mutation Testing
**Priority:** Should Have
**Description:** After tests pass, optionally run mutation testing to verify tests actually detect faults.
**Acceptance Criteria:**
- [ ] Integrates with available mutation testing tools (Stryker for JS/TS, mutmut for Python, etc.)
- [ ] Reports mutation score and surviving mutants
- [ ] Optional — user can skip per run

---

### EPIC-004: Knowledge Layer

#### FR-014: RAG Index Per Project
**Priority:** Must Have
**Description:** Each project gets a local semantic search index over project docs, reference material, and codebase. Auto-initialized during project init.
**Acceptance Criteria:**
- [ ] Index created during `sweetclaude init`
- [ ] Supports PDF, MD, TXT, DOCX
- [ ] Queryable via MCP tools
- [ ] Index stored in SweetClaude working repo (not code repo)

#### FR-015: Auto-Reindex Hook
**Priority:** Should Have
**Description:** RAG index stays current. When indexed files change, automatically re-index modified files.
**Acceptance Criteria:**
- [ ] Detects new/modified files in indexed directories
- [ ] Incremental reindex (not full rebuild)
- [ ] Runs without manual intervention

#### FR-016: Traceability Tracker
**Priority:** Must Have
**Description:** Structured markdown in the working repo mapping requirements → Gherkin stories → tests → implementation files. Updated as work progresses through phases.
**Acceptance Criteria:**
- [ ] Traceability file created per epic/feature
- [ ] Updated when Gherkin stories are created
- [ ] Updated when tests are generated
- [ ] Updated when implementation files are created
- [ ] Human-readable markdown, not a database

---

### EPIC-005: Quality & Verification

#### FR-017: Ripple-Effect Analysis
**Priority:** Must Have
**Description:** Before implementing a change to an existing codebase, automatically trace what's affected: dependencies, tests, APIs, consumers. Present impact assessment before proceeding.
**Acceptance Criteria:**
- [ ] Identifies files/modules that depend on the change target
- [ ] Identifies tests that cover the change target
- [ ] Identifies API contracts that may be affected
- [ ] Presents impact summary to user before implementation begins
- [ ] Runs automatically at start of Implement phase for existing codebases

#### FR-018: Automatic Documentation Updates
**Priority:** Must Have
**Description:** When implementation changes behavior, auto-update relevant docs (README, API docs, ADRs, CLAUDE.md) as part of the verification phase.
**Acceptance Criteria:**
- [ ] Detects which docs reference changed behavior
- [ ] Proposes updates (user approves before writing)
- [ ] Runs during Verify phase before PR
- [ ] Does not create docs that don't exist — only updates existing

#### FR-019: Security Reviewer Subagent
**Priority:** Should Have
**Description:** Subagent that reviews code changes for security issues: auth, injection, secrets, tenant boundaries.
**Acceptance Criteria:**
- [ ] Runs on-demand or as part of Verify phase
- [ ] Read-only tools only
- [ ] Returns prioritized findings (Critical/Warning/Info)

#### FR-020: Workflow Guardian Subagent
**Priority:** Should Have
**Description:** Subagent that reviews GitHub Actions workflow changes for security best practices.
**Acceptance Criteria:**
- [ ] Checks SHA pinning, token permissions, dangerous triggers
- [ ] Runs automatically when `.github/workflows/` files are modified
- [ ] Returns findings with specific fix suggestions

---

### EPIC-006: Model Routing

#### FR-021: Configurable Model Routing
**Priority:** Should Have
**Description:** User-defined rules for which Claude model handles which tasks. Config file with rules and a default fallback model.
**Acceptance Criteria:**
- [ ] Config file (YAML or JSON) defines routing rules
- [ ] Rules map task types to model IDs (e.g., `test-runner: haiku`, `code-review: sonnet`, `architecture: opus`)
- [ ] Default fallback model for anything not explicitly routed
- [ ] 100% user-configurable — SweetClaude provides sensible defaults but user owns the config
- [ ] Config validated during init

---

### EPIC-007: Creative Partnership & Interaction Model

#### FR-022: Active Creative Partner Behavior
**Priority:** Must Have
**Description:** Across all phases, SweetClaude actively soundboards ideas, challenges assumptions, introduces alternatives, and contributes to thinking — not just executes instructions.
**Acceptance Criteria:**
- [ ] During Discover: proposes alternative approaches, asks "have you considered..."
- [ ] During Define: challenges scope, identifies gaps, suggests features user hasn't mentioned
- [ ] During Design: proposes architectural alternatives, flags tradeoffs
- [ ] During Implement: suggests better patterns, warns about complexity
- [ ] Behavior is helpful, not obstructive — user can say "just do it" to skip

#### FR-027: Propose-and-Challenge Interaction Mode
**Priority:** Must Have
**Description:** Instead of asking questions and waiting, SweetClaude proposes answers/approaches and invites the user to push back. Faster than Q&A, surfaces assumptions, enables creative collaboration.
**Acceptance Criteria:**
- [ ] Default interaction mode is "here's what I think, push back" not "what do you think?"
- [ ] Proposals include reasoning so user can evaluate
- [ ] User corrections are incorporated immediately
- [ ] Works across all phases

#### FR-028: Adaptive Flow — Follow the User
**Priority:** Must Have
**Description:** When the user redirects, stops, edits files directly, or changes direction, SweetClaude drops its current plan and follows. No resistance, no "but we were on step 7."
**Acceptance Criteria:**
- [ ] Detects user redirection (stop, topic change, direct file edits)
- [ ] Acknowledges the shift and adapts immediately
- [ ] Previous work state preserved (can resume if user wants)
- [ ] Never argues against a direction change

#### FR-033: Deference Level Setting
**Priority:** Must Have
**Description:** At session start, SweetClaude asks the user how autonomous vs. collaborative it should be. This governs checkpoint frequency across all skills, phases, and sub-steps. User can change the level mid-stream.
**Acceptance Criteria:**
- [ ] Three levels: Collaborative (stop after every sub-step), Guided (stop at phase gates and major decisions), Autonomous (stop only at phase gates)
- [ ] Asked at session start
- [ ] User can change level mid-stream with immediate effect
- [ ] Level persisted to working repo for session recovery
- [ ] All skills and workflows respect the current deference level

#### FR-034: Context Continuity — Detour Management
**Priority:** Must Have
**Description:** When conversation detours from the current topic (user raises a side issue, asks a question, changes subject), SweetClaude follows the detour (per FR-028) but tracks where the conversation branched. When the detour is satisfied, SweetClaude proactively suggests circling back and re-orients the user to where they were without being asked.
**Acceptance Criteria:**
- [ ] Detects when conversation branches away from current work
- [ ] Tracks the branch point (what was being discussed, what step, what was pending)
- [ ] When detour completes, suggests: "We were on [X]. Ready to circle back?"
- [ ] On circle-back, re-orients the user with a concise summary of where things stand
- [ ] Handles nested detours (detour within a detour)

#### FR-035: Dual Context Window Management
**Priority:** Must Have
**Description:** SweetClaude manages two context windows simultaneously: Claude's (the machine context window with token limits) and the human's (cognitive load, working memory, ability to hold details). Design decisions must account for both constraints. The human context window is managed through deference levels (FR-033), context continuity (FR-034), decision logs (FR-030), assumption registers (FR-031), re-orientation summaries, and proactive state recaps.
**Acceptance Criteria:**
- [ ] Machine context managed via: lazy loading, phase-scoped skills, lean CLAUDE.md, on-demand RAG
- [ ] Human context managed via: deference levels, detour tracking, re-orientation, decision/assumption persistence, sub-step checkpoints
- [ ] When presenting complex information, SweetClaude structures it for human comprehension (summaries first, details on request)
- [ ] After any interruption or detour, SweetClaude recaps current state before continuing
- [ ] Long sessions include periodic "here's where we are" summaries without being asked

#### FR-029: Pre-Checkpoint Decision Summary
**Priority:** Must Have
**Description:** Before any phase transition commit, SweetClaude presents a bullet list of decisions made during the phase. User confirms. The confirmed list becomes the decision log entry.
**Acceptance Criteria:**
- [ ] Decision summary generated from conversation context
- [ ] Presented to user before phase transition commit
- [ ] User confirms or edits
- [ ] Stored in working repo as part of the decision log

#### FR-030: Decision Log
**Priority:** Must Have
**Description:** Persistent log in the working repo capturing what was decided and why at each phase, not just what was produced. Survives session restarts.
**Acceptance Criteria:**
- [ ] One entry per phase transition
- [ ] Each entry includes: phase, date, decisions made, rationale, alternatives considered
- [ ] Stored as structured markdown in working repo
- [ ] Committed with phase transition checkpoint

#### FR-031: Assumption Register
**Priority:** Must Have
**Description:** SweetClaude explicitly surfaces its assumptions in a visible register so the user can challenge them. Not buried in reasoning — presented as a reviewable list.
**Acceptance Criteria:**
- [ ] Assumptions captured per phase
- [ ] Presented to user for review at phase transitions
- [ ] User can confirm, reject, or modify each assumption
- [ ] Rejected assumptions trigger rework of dependent decisions
- [ ] Stored in working repo

#### FR-032: Scope Change Tracking
**Priority:** Should Have
**Description:** When items move between in-scope and out-of-scope (or vice versa), log the change with rationale. History is valuable when revisiting priorities.
**Acceptance Criteria:**
- [ ] Scope changes logged with: item, direction (in→out or out→in), rationale, date
- [ ] Log stored in working repo
- [ ] Queryable: "what scope changes have we made?"

#### FR-036: Continuous Improvement Register
**Priority:** Must Have
**Description:** Per-project register that captures what's working and what's not in the human-AI collaboration itself — not project decisions, but interaction quality. Populated at concrete milestones, not left to chance. Lives in working repo, read by future sessions.
**Acceptance Criteria:**
- [ ] Stored in working repo (per-project, not global)
- [ ] Captures both corrections AND confirmations (what works, not just what failed)
- [ ] **Mandatory trigger: every phase transition.** Before advancing, ask: "Before we move on — anything about how this phase went that I should do differently going forward?"
- [ ] **Mandatory trigger: after code review.** The Verify phase includes the largest feedback surface — always check in after review findings are addressed
- [ ] **Friction trigger:** After user corrections, misalignment, or frustration, SweetClaude proposes what happened and what to change, saves on user confirmation
- [ ] **Success trigger:** After smooth stretches or user compliments, ask what specifically worked
- [ ] **Session-start trigger:** If improvement register has entries, acknowledge them and confirm they still apply
- [ ] Future sessions read the register and adjust behavior
- [ ] Register must never be empty after a project completes Implement phase — if it is, the triggers weren't firing

#### FR-037: Phase Dwelling
**Priority:** Must Have
**Description:** SweetClaude stays present in the current phase. It does not push for advancement, ask "ready to move on?", or treat iteration as delay. The user decides when a phase is complete. The system's default posture is to remain in the current phase and deepen the work, not advance to the next step.
**Acceptance Criteria:**
- [ ] No unprompted "shall we move on?" or "is this complete?" prompts
- [ ] After presenting work, SweetClaude remains available for iteration without signaling impatience
- [ ] Phase advancement happens only when user explicitly signals readiness
- [ ] Works at all deference levels — even Autonomous does not auto-advance phases

---

### EPIC-008: Global Configuration

#### FR-023: Lean Global CLAUDE.md
**Priority:** Must Have
**Description:** Global `~/CLAUDE.md` rewritten to 60-80 lines covering only universal rules that apply to every project.
**Acceptance Criteria:**
- [ ] Under 80 lines
- [ ] Covers: session discipline, global invariants, git workflow, code quality
- [ ] No project-specific content
- [ ] No plugin mandates

#### FR-024: Superpowers & BMAD Integration
**Priority:** Must Have
**Description:** SweetClaude works alongside Superpowers and BMAD as upstream dependencies. Phase router delegates to appropriate BMAD workflows and Superpowers skills.
**Acceptance Criteria:**
- [ ] BMAD workflows invocable during Discover/Define/Design/Plan phases
- [ ] Superpowers skills invocable during Implement/Verify/Ship phases
- [ ] No conflicts between SweetClaude hooks and upstream plugin hooks
- [ ] Graceful behavior if either plugin is not installed (warn, don't crash)

---

### EPIC-009: Structured Discover Phase

#### FR-038: Persona-Driven Discovery
**Priority:** Must Have
**Description:** During Discover for net-new products/apps, SweetClaude conducts an iterative persona interview. For each persona: job title, tasks they need to complete, and success criteria for each task. After each persona is defined, asks "Are there additional user personas?" and repeats until all personas are captured. Then presents all personas and tasks in a single consolidated view for user verification.
**Acceptance Criteria:**
- [ ] Each persona has: name/label, job title or role, list of tasks, success criteria per task
- [ ] Iterative loop continues until user signals all personas are defined
- [ ] Consolidated view presents all personas with their tasks in one list, separated by persona
- [ ] User confirms or edits the consolidated view before proceeding
- [ ] Scales down for non-product work types (CLIs, libraries) — lighter persona treatment
**Dependencies:** FR-004

#### FR-039: Iterative Feature Brainstorming
**Priority:** Must Have
**Description:** After personas and tasks are confirmed, SweetClaude asks if the user wants to brainstorm additional features and capabilities. If yes, proposes features one at a time for the user to include or exclude. Capped at 10 features per batch. User can request additional batches. Iterates until user is satisfied.
**Acceptance Criteria:**
- [ ] Triggered only after persona/task consolidation is confirmed
- [ ] Features presented one at a time with rationale (not batched)
- [ ] User includes or excludes each feature explicitly
- [ ] Maximum 10 features per batch; user informed of the cap
- [ ] User can request additional batches of 10
- [ ] Iteration ends when user signals satisfaction
- [ ] Included features are added to the working feature set for the product brief
**Dependencies:** FR-038

#### FR-040: Competitive Analysis
**Priority:** Should Have
**Description:** After feature brainstorming, SweetClaude offers to perform competitive research. Searches for competing projects, technologies, open-source alternatives on GitHub, product launch sites, and the web. Presents a list with ~25-word synopsis per competitor. User can drill into specific competitors for detailed analysis, or request a "table stakes" feature set derived from the competitive landscape.
**Acceptance Criteria:**
- [ ] Offered as optional step after feature brainstorming
- [ ] Searches web, GitHub, product launch sites for similar applications/categories
- [ ] Each competitor presented with name, URL, and ~25-word synopsis
- [ ] "Nothing found" path handled gracefully — does not force user through empty exercise
- [ ] User can select individual competitors for deeper analysis
- [ ] User can request "table stakes" analysis across all competitors (common feature set)
- [ ] Table stakes features presented for user to include/exclude from product scope
**Dependencies:** FR-039

#### FR-041: Discover Phase Scales to Work Type
**Priority:** Must Have
**Description:** The structured Discover workflow (personas, brainstorming, competitive analysis) is designed for net-new products and apps. For CLIs, libraries, utilities, and smaller work, the workflow scales down — lighter persona treatment, optional brainstorming, competitive analysis only if relevant. The master skill detects work type and adjusts Discover depth accordingly.
**Acceptance Criteria:**
- [ ] Products/apps: full persona + brainstorming + competitive workflow
- [ ] CLIs/libraries: simplified persona (primary user only), skip brainstorming unless user requests
- [ ] Utilities/scripts: minimal Discover — concept articulation and scope boundary only
- [ ] User can always request the full workflow regardless of detected work type

---

### EPIC-010: Strategy Track

#### FR-042: Strategy File Reconciliation
**Priority:** Must Have
**Description:** Onboard unstructured files into the `strategy/` system. Inventories files in a target directory, categorizes each by domain and document type, applies versioning conventions, and optionally synthesizes content into canonical-draft documents that follow the strategy corpus structure.
**Acceptance Criteria:**
- [ ] Scans target directory and produces a typed inventory (file, domain, doc-type, status)
- [ ] Categorizes files by domain (e.g., market, product, technical, organizational) and document type (e.g., memo, analysis, presentation, raw notes)
- [ ] Applies versioning to onboarded files consistent with strategy corpus conventions
- [ ] Optional synthesis: generates canonical-draft documents from clusters of related files
- [ ] Non-destructive — originals preserved, copies/symlinks placed into `strategy/`

#### FR-043: Academic Paper Development
**Priority:** Must Have
**Description:** Six-phase pipeline for developing academic papers: first principles exploration, literature review, structure and venue selection, drafting, review and revision, and submission preparation. Adapted from lishix520/academic-paper-skills (MIT license).
**Acceptance Criteria:**
- [ ] Phase 1 (First Principles): guided exploration of research question, contribution, and novelty
- [ ] Phase 2 (Literature Review): structured search, synthesis, and gap identification
- [ ] Phase 3 (Structure & Venue): paper outline generation and venue matching
- [ ] Phase 4 (Drafting): section-by-section drafting with citation integration
- [ ] Phase 5 (Review & Revision): structured self-review, peer-review simulation, revision tracking
- [ ] Phase 6 (Submission): formatting, compliance checks, cover letter generation
- [ ] Each phase has defined entry/exit criteria
- [ ] Attribution: adapted from lishix520/academic-paper-skills (MIT)

#### FR-044: Narrative Arc Knowledge Graph
**Priority:** Must Have
**Description:** Typed knowledge graph connecting strategy domains — objectives, claims, proof points, and literature references. Enables traversal queries such as "what evidence supports claim X?" or "which objectives lack proof points?" Design deferred to its own cycle; interface contract locked now.
**Acceptance Criteria:**
- [ ] Node types defined: Objective, Claim, ProofPoint, LiteratureRef (minimum)
- [ ] Edge types defined: supports, contradicts, cites, derives-from (minimum)
- [ ] Interface contract published: query API, ingestion API, export format
- [ ] Interface contract is stable — implementation may change, contract does not
- [ ] Design and implementation deferred to dedicated cycle

#### FR-045: Meeting Prep
**Priority:** Should Have
**Description:** Generate stakeholder-specific meeting deliverables from the strategy corpus and narrative arc knowledge graph. Given a meeting context (attendees, agenda, objectives), produces tailored briefing documents, talking points, and anticipated questions with sourced answers.
**Acceptance Criteria:**
- [ ] Accepts meeting context: attendees (with roles), agenda items, meeting objectives
- [ ] Generates stakeholder-specific briefing documents (different emphasis per audience)
- [ ] Produces talking points aligned to agenda items
- [ ] Generates anticipated questions with sourced answers from strategy corpus
- [ ] Sources all claims back to strategy corpus documents or knowledge graph nodes
- [ ] Degrades gracefully when knowledge graph is not yet populated (falls back to corpus search)

#### FR-046: Dual-Track Work Router
**Priority:** Must Have
**Description:** Extends the existing work router (FR-005) to classify incoming work as code-track or strategy-track, then surfaces the appropriate skill set for the identified track. Code-track routes through the existing phase pipeline. Strategy-track routes to strategy-specific skills.
**Acceptance Criteria:**
- [ ] Classifies work as code-track or strategy-track based on user intent
- [ ] Code-track work routes through existing phase pipeline (FR-004, FR-005)
- [ ] Strategy-track work surfaces strategy skills (FR-042 through FR-045)
- [ ] Ambiguous work prompts user for clarification
- [ ] User can override classification at any time

#### FR-047: Pre-Flight Guard Hook
**Priority:** Must Have
**Description:** Deterministic `PreToolUse` hook that blocks the first tool use in a session if SweetClaude is not configured for the current project. Ensures the framework is initialized before any work begins. Per-project opt-out via `.sweetclaude-skip` marker file in the project root.
**Acceptance Criteria:**
- [ ] Fires on first `PreToolUse` event of a session
- [ ] Blocks tool use if SweetClaude working repo not found or not configured
- [ ] Returns clear error message with instructions to run `sweetclaude init` or create `.sweetclaude-skip`
- [ ] `.sweetclaude-skip` in project root bypasses the guard for that project
- [ ] Does not fire on subsequent tool uses after first pass/fail
- [ ] Deterministic — no LLM reasoning, pure file-existence checks

---

## Non-Functional Requirements

### NFR-001: Context Window Efficiency
**Priority:** Must Have
**Description:** SweetClaude must minimize baseline context window consumption. All skills, rules, and context loaded on demand, never eagerly.
**Acceptance Criteria:**
- [ ] Baseline context load under 15KB (global CLAUDE.md + phase router + active phase skills only)
- [ ] Skills loaded only when invoked
- [ ] RAG queries on demand, not preloaded
- [ ] Phase transition unloads previous phase's skills

### NFR-002: Language/Framework Agnosticism
**Priority:** Must Have
**Description:** All skills, hooks, and processes must work with any programming language and framework. No hardcoded assumptions about TypeScript, Python, or any other stack.
**Acceptance Criteria:**
- [ ] TDD skill works with any test runner detected by codebase discovery
- [ ] Hook scripts use project-detected commands, not hardcoded ones
- [ ] Examples in documentation cover at least 3 languages
- [ ] No skill file contains hardcoded language-specific commands

### NFR-003: Session Recovery
**Priority:** Must Have
**Description:** Any session can be resumed from the last completed phase. Phase state, decision log, assumption register, and working artifacts survive session death.
**Acceptance Criteria:**
- [ ] Phase state persisted to working repo after every transition
- [ ] Decision log committed at every checkpoint
- [ ] New session can read working repo state and resume
- [ ] No work lost on unexpected session termination (within last checkpoint)

### NFR-004: Installation Simplicity
**Priority:** Must Have
**Description:** SweetClaude installs with minimal steps. No complex dependency chains or manual configuration.
**Acceptance Criteria:**
- [ ] Install in 3 steps or fewer
- [ ] Prerequisites clearly documented with minimum versions (Claude Code CLI, git, GitHub CLI, Superpowers 5.0.7+, BMAD 6.0.0+)
- [ ] Installer validates all prerequisites and versions before proceeding
- [ ] No compilation or build step required
- [ ] Verify installation with a single command

### NFR-005: Upstream Compatibility
**Priority:** Must Have
**Description:** SweetClaude must not break Superpowers or BMAD functionality. It orchestrates, not overrides.
**Acceptance Criteria:**
- [ ] All Superpowers skills remain independently invocable
- [ ] All BMAD workflows remain independently invocable
- [ ] No hook conflicts
- [ ] SweetClaude can be disabled without affecting upstream plugins

### NFR-006: Security — No Credential Exposure
**Priority:** Must Have
**Description:** SweetClaude must never store, log, or expose credentials, API keys, or secrets.
**Acceptance Criteria:**
- [ ] No credentials in any config file
- [ ] Hooks do not log sensitive environment variables
- [ ] Init does not write secrets to working repo
- [ ] `.gitignore` configured to exclude `.env` and credential files

### NFR-007: Performance — Hook Overhead
**Priority:** Should Have
**Description:** Enforcement hooks (test guardian, auto-test runner) must not add unacceptable latency to the development flow.
**Acceptance Criteria:**
- [ ] PreToolUse hooks complete in under 500ms
- [ ] PostToolUse auto-test runner launches asynchronously (does not block next edit)
- [ ] User can disable individual hooks if needed

### NFR-008: Extensibility
**Priority:** Should Have
**Description:** Users and community can add custom skills, subagents, and hooks that integrate with SweetClaude's phase pipeline.
**Acceptance Criteria:**
- [ ] Custom skills can declare which phase(s) they belong to
- [ ] Custom subagents follow the same invocation pattern as built-in ones
- [ ] Custom hooks can be added without modifying SweetClaude core files
- [ ] Documentation explains how to extend

---

## Epics & Traceability Matrix

| Epic ID | Epic Name | FRs | Priority |
|---|---|---|---|
| EPIC-001 | Project Bootstrap | FR-001, FR-002, FR-003 | Must Have |
| EPIC-002 | Phase Pipeline & Work-Type Routing | FR-004, FR-005, FR-006, FR-025, FR-026 | Must Have |
| EPIC-003 | TDD Enforcement | FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013 | Must Have |
| EPIC-004 | Knowledge Layer | FR-014, FR-015, FR-016 | Must Have |
| EPIC-005 | Quality & Verification | FR-017, FR-018, FR-019, FR-020 | Must Have |
| EPIC-006 | Model Routing | FR-021 | Should Have |
| EPIC-007 | Creative Partnership & Interaction Model | FR-022, FR-027, FR-028, FR-029, FR-030, FR-031, FR-032, FR-033, FR-034, FR-035, FR-036, FR-037 | Must Have |
| EPIC-008 | Global Configuration | FR-023, FR-024 | Must Have |
| EPIC-009 | Structured Discover Phase | FR-038, FR-039, FR-040, FR-041 | Must Have |
| EPIC-010 | Strategy Track | FR-042, FR-043, FR-044, FR-045, FR-046, FR-047 | Must Have |

**Totals:**
- Functional Requirements: 47 (34 Must, 11 Should, 2 Could)
- Non-Functional Requirements: 8 (6 Must, 2 Should)
- Epics: 10

---

## Prioritization Summary

| Priority | FRs | NFRs | Total |
|---|---|---|---|
| Must Have | 34 | 6 | 40 |
| Should Have | 11 | 2 | 13 |
| Could Have | 2 | 0 | 2 |

---

## Dependencies

**Internal:**
- FR-002 (Codebase Discovery) must complete before FR-001 (Project Init) can generate CLAUDE.md
- FR-011 (Gherkin Bridge) required for FR-007 TDD Level 3
- FR-004 (Phase Pipeline) required for FR-006 (Skill Surfacing) and FR-029 (Decision Summary)

**External:**
- Claude Code CLI (runtime environment)
- Superpowers plugin 5.0.7+ (upstream dependency — dev mechanics)
- BMAD Method 6.0.0+ (upstream dependency — product lifecycle)
- GitHub CLI (`gh`) (project hosting)
- Git
- mcp-local-rag (RAG functionality)
- Notion MCP (optional — Notion integration)

---

## Assumptions

- Users have Claude Code installed and a working Claude API subscription
- Users have GitHub accounts and `gh` CLI authenticated
- Users are comfortable with terminal-based workflows
- Superpowers plugin (5.0.7+) and BMAD Method (6.0.0+) installed as upstream dependencies
- Claude Code's hook, skill, and subagent APIs remain stable
- mcp-local-rag remains available for RAG functionality

---

## Out of Scope (v1.0)

- **`sweetclaude adopt`** — onboarding existing/vibe-coded codebases (future epic, documented in product brief)
- Automatic boilerplate implementation (Google OAuth, JWT, etc.)
- Multi-developer / team workflows
- IDE integrations beyond Claude Code CLI
- Auto-update mechanism
- Marketplace distribution
- Community skill library

---

## Open Questions

1. **License selection:** CC BY-NC-SA 4.0 vs. Polyform NonCommercial — to be decided during Design phase
2. **Hook testing:** How do we test hooks in isolation before integrating? Need a test harness strategy.
3. **Mutation testing tool selection:** Stryker vs. mewt vs. language-specific tools — defer to per-project discovery
4. **RAG scaling:** What happens when the index grows very large? Pruning strategy needed.

---

## Supporting Documents

- Product Brief: `docs/product-brief-sweetclaude-v1-2026-04-12.md`
- Brainstorm: `docs/brainstorm-sweetclaude-2026-04-12.md`
- TDD Analysis: `docs/tdd-analysis-v1-2026-04-12.md`
- Environment Audit: `audit/2026-04-08-environment-audit.md`

---

*Generated by BMAD Method v6 — Product Manager*
