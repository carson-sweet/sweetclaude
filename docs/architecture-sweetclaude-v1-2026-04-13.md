# Architecture: SweetClaude v1 — 2026-04-13

**Author:** Carson Sweet
**Status:** Draft
**PRD:** `docs/prd-sweetclaude-v1-2026-04-12.md`
**Product Brief:** `docs/product-brief-sweetclaude-v1-2026-04-12.md`

---

## Architectural Drivers

These ten constraints shape every design decision:

| # | Driver | Constraint | Design Impact |
|---|---|---|---|
| 1 | Context window efficiency | Claude's token limit is finite; bloat degrades instruction-following | Lazy loading, phase-scoped skills, lean CLAUDE.md, on-demand RAG |
| 2 | Conversation branch management | Human can't hold full context; detours lose state | Detour tracking, re-orientation, decision/assumption persistence |
| 3 | Session recovery | Sessions die; state must survive | `.sweetclaude/` state persistence, git checkpoints, phase state files |
| 4 | Language/framework agnosticism | No hardcoded stack assumptions | Codebase discovery drives all config; templates, not constants |
| 5 | Upstream compatibility | Must not break Superpowers or BMAD | Orchestrate via delegation, never override or monkey-patch |
| 6 | TDD enforcement hooks | Advisory TDD fails; deterministic enforcement required | Native Claude Code hooks (PreToolUse, PostToolUse, Stop) |
| 7 | RAG + semantic knowledge | Large document corpus, per-project index | mcp-local-rag, index in `.sweetclaude/`, query on demand |
| 8 | Persistent project memory | Decisions, assumptions, traceability must outlive sessions | Structured markdown in `.sweetclaude/`, committed at checkpoints |
| 9 | Phase dwelling over rushing | User controls pace; system never pushes advancement | No unprompted "move on?" — all skills written to dwell |
| 10 | Ripple-effect management | Changes propagate across artifacts; nothing falls out of sync | Dependency awareness across docs, code, tests, specs |

---

## Architecture Pattern

**Pattern:** Orchestration layer over existing plugins, implemented as Claude Code native extensions (skills, hooks, subagents, rules, config files).

**Rationale:** SweetClaude is not an application with a server, database, or API. It's a framework of files that Claude Code loads and executes. The architecture is about file organization, loading strategy, and interaction patterns — not services and infrastructure.

**Key principle:** SweetClaude orchestrates Superpowers and BMAD; it doesn't replace or fork them. It adds a phase pipeline, enforcement hooks, interaction model, and project scaffolding that those plugins don't provide.

**Five-bucket architecture:** Skills are organized into five domain buckets — `strategy/`, `product/`, `design/`, `code/`, `deploy/` — with orchestration skills at root level. The `new-task` and `auto-flow` skills classify work into a bucket and surface appropriate skills.

```
┌─────────────────────────────────────────────────────────┐
│                    CLAUDE CODE RUNTIME                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              SWEETCLAUDE LAYER                     │   │
│  │                                                    │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  │   │
│  │  │   SKILLS   │  │   HOOKS    │  │  SUBAGENTS  │  │   │
│  │  │            │  │            │  │             │  │   │
│  │  │ Orchestr(7)│  │ Test guard │  │ QA caucus   │  │   │
│  │  │ Strategy(8)│  │ Auto-test  │  │ Security    │  │   │
│  │  │ Product(12)│  │ Git ckpt   │  │ Workflow    │  │   │
│  │  │ Design (11)│  │ Auto-reidx │  │ Test runner │  │   │
│  │  │ Code   (8) │  │ Preflight  │  │ Code review │  │   │
│  │  │            │  │ guard      │  │             │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  │   │
│  │                                                    │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  │   │
│  │  │   RULES    │  │   CONFIG   │  │.SWEETCLAUDE│  │   │
│  │  │            │  │            │  │  STATE DIR │  │   │
│  │  │ Phase      │  │ CLAUDE.md  │  │ Phase state │  │   │
│  │  │ gates      │  │ Model      │  │ Decision    │  │   │
│  │  │ TDD        │  │ routing    │  │ log         │  │   │
│  │  │ levels     │  │ Deference  │  │ Assumptions │  │   │
│  │  │            │  │ level      │  │ Traceability│  │   │
│  │  │            │  │            │  │ RAG index   │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │  SUPERPOWERS     │  │     BMAD         │               │
│  │  (upstream)      │  │  (upstream)      │               │
│  │                  │  │                  │               │
│  │  Plans, worktrees│  │  Brainstorm, PRD │               │
│  │  Debugging       │  │  Architecture    │               │
│  │  Code review     │  │  Stories, Sprint │               │
│  │  Parallel agents │  │  Research        │               │
│  └─────────────────┘  └─────────────────┘               │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              MCP SERVERS                          │    │
│  │  mcp-local-rag │ Notion │ Neon │ Tavily │ ...    │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## File Architecture

### Global installation (`~/.claude/`)

```
~/.claude/
├── CLAUDE.md                          # Lean global rules (60-80 lines)
├── settings.json                      # Global hooks, permissions
├── skills/
│   └── sweetclaude/
│       ├── SKILL.md                   # Master skill — phase router + interaction model
│       ├── help/SKILL.md              # Help and onboarding
│       ├── status/SKILL.md            # Project status dashboard
│       ├── auto-flow/SKILL.md         # Automatic bucket/skill routing
│       ├── init/SKILL.md              # Project bootstrap
│       ├── new-task/SKILL.md          # Work-type detection and routing
│       ├── hibernate/SKILL.md         # Project freeze/thaw with SweetClaude state
│       ├── strategy/                  # Strategic development skills (8)
│       │   ├── concept/SKILL.md
│       │   ├── pain-thesis/SKILL.md
│       │   ├── ideal-customer-profile/SKILL.md
│       │   ├── competitive-analysis/SKILL.md
│       │   ├── academic-research/SKILL.md
│       │   ├── meeting-prep/SKILL.md
│       │   ├── narrative-arc/SKILL.md
│       │   └── market-messaging/SKILL.md
│       ├── product/                   # Product development skills (12)
│       │   ├── discovery/SKILL.md
│       │   ├── positioning-statement/SKILL.md
│       │   ├── product-brief/SKILL.md
│       │   ├── prd/SKILL.md
│       │   ├── user-story/SKILL.md
│       │   ├── user-tdd-tests/SKILL.md
│       │   ├── user-success-criteria/SKILL.md
│       │   ├── user-workflows/SKILL.md
│       │   ├── manage-scope/SKILL.md
│       │   ├── sprint-plan/SKILL.md
│       │   ├── research/SKILL.md
│       │   └── feature-competitive/SKILL.md
│       ├── design/                    # Design skills (11)
│       │   ├── architecture/SKILL.md
│       │   ├── tech-spec/SKILL.md
│       │   ├── ux/SKILL.md
│       │   ├── solutioning-gate/SKILL.md
│       │   ├── change-impact-analysis/SKILL.md
│       │   ├── update-docs/SKILL.md
│       │   ├── data-model/SKILL.md
│       │   ├── api-design/SKILL.md
│       │   ├── services-design/SKILL.md
│       │   ├── infra-design/SKILL.md
│       │   └── manage-decisions/SKILL.md
│       ├── code/                      # Code skills (8)
│       │   ├── tdd/SKILL.md
│       │   ├── work-issue/SKILL.md
│       │   ├── work-debt/SKILL.md
│       │   ├── pr-precheck/SKILL.md
│       │   ├── qa-testing/SKILL.md
│       │   ├── mutation-testing/SKILL.md
│       │   ├── security-testing/SKILL.md
│       │   └── code-review/SKILL.md
│       └── deploy/                    # Deploy skills (placeholder)
│
├── agents/
│   └── sweetclaude/
│       ├── test-writer.md            # Isolated test writer (TDD Level 2-3)
│       ├── implementer.md            # Isolated implementer (TDD Level 2-3)
│       ├── qa-caucus-service.md      # QA caucus — service/API expert
│       ├── qa-caucus-component.md    # QA caucus — component expert
│       ├── qa-caucus-integration.md  # QA caucus — cross-cutting expert
│       ├── security-reviewer.md      # Security review
│       ├── workflow-guardian.md       # GitHub Actions review
│       └── code-reviewer.md          # Adversarial code review
│
├── rules/
│   └── sweetclaude/
│       ├── phase-gates.md            # Entry/exit criteria per phase
│       ├── tdd-levels.md             # TDD level definitions and enforcement rules
│       └── interaction-model.md      # Deference levels, dwelling, continuity, improvement
│
├── hooks/
│   └── sweetclaude/
│       ├── test-guardian.sh          # PreToolUse — blocks test file edits during impl
│       ├── auto-test-runner.sh       # PostToolUse — runs tests after source edits
│       ├── git-checkpoint.sh         # Auto-commits at phase transitions
│       ├── auto-reindex.sh           # Triggers RAG re-indexing on file changes
│       └── preflight-guard.sh        # PreToolUse — blocks if SweetClaude not configured
│
└── config/
    └── sweetclaude/
        ├── defaults.yaml             # Default model routing, deference level, etc.
        └── phase-skills.yaml         # Which skills/agents are available per phase
```

### Per-project code repo (the product being built)

```
<project>/
├── CLAUDE.md                          # Project-specific rules (auto-generated by init)
├── .claude/
│   └── settings.json                 # Project-level hook config (merges with global)
├── src/                              # Application source code
├── tests/                            # Test files
│   └── stories/                      # Story-organized tests (TDD Level 3)
├── features/                         # Gherkin .feature files
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── pull_request_template.md
│   └── CODEOWNERS
└── docs/
    └── adr/                          # Architecture decision records
```

### Per-project `.sweetclaude/` state directory

```
<project>/.sweetclaude/
├── state/
│   ├── phase.yaml                    # Current phase, work type, deference level
│   ├── decision-log.md               # What was decided and why, per phase
│   ├── assumption-register.md        # Active assumptions, confirmed/rejected
│   ├── scope-changes.md              # Scope change history with rationale
│   └── improvement-register.md       # Collaboration quality feedback
│
├── traceability/
│   ├── requirements-map.md           # Requirements → stories → tests → code
│   └── ripple-map.md                 # Dependency graph across artifacts
│
├── specs/
│   ├── product-brief.md
│   ├── prd.md
│   ├── architecture.md
│   └── tech-spec.md
│
├── stories/
│   ├── EPIC-001/
│   │   ├── story-001.md
│   │   └── story-001.feature         # Gherkin acceptance criteria
│   └── EPIC-002/
│       └── ...
│
├── brainstorm/
│   └── *.md                          # Brainstorm session outputs
│
├── rag-index/                        # Vector embeddings (gitignored if large)
│   └── .gitkeep
│
└── .gitignore
```

---

## Component Architecture

### Component 1: Master Skill — Phase Router + Interaction Model
**Purpose:** The entry point for every SweetClaude session. Reads phase state, determines deference level, surfaces appropriate skills, manages conversation branches.
**Responsibilities:**
- Read `state/phase.yaml` to determine current phase and work type
- Ask deference level at session start (or read from state)
- Surface only skills relevant to current phase (from `phase-skills.yaml`)
- Track conversation branches for detour management
- Enforce phase dwelling — never prompt for advancement
- Trigger pre-checkpoint decision summaries at phase transitions
- Periodic re-orientation summaries during long sessions
**FRs addressed:** FR-004, FR-006, FR-025, FR-026, FR-028, FR-033, FR-034, FR-035, FR-037
**Loads:** Always (this is the session entry point)

### Component 2: New Task / Auto-Flow
**Purpose:** Classifies work into one of the five domain buckets and surfaces appropriate skills.
**Responsibilities:**
- Ask or detect work type and classify into strategy, product, design, code, or deploy bucket
- Route to appropriate skills from the matched bucket
- Auto-flow mode: automatically determine bucket from context without user prompting
- Detect mid-stream work-type shifts
- Handle escalation when deeper issues surface
**FRs addressed:** FR-005, FR-025
**Loads:** New-task always loaded; auto-flow on demand

### Component 3: SweetClaude TDD Skill
**Purpose:** Unified TDD enforcement across four process levels.
**Responsibilities:**
- Select TDD level based on work type and complexity
- Level 0: fix first, test same session
- Level 1: single-context RED-GREEN-REFACTOR
- Level 2: spawn test-writer and implementer subagents in isolated contexts
- Level 3: read Gherkin .feature → spawn test-writer → QA caucus → implementer
- Coordinate with test-guardian hook for enforcement
- Coordinate with git-checkpoint for test commits
**FRs addressed:** FR-007, FR-010, FR-011
**Loads:** During Implement phase only

### Component 4: Test Guardian Hook
**Purpose:** Deterministic enforcement — blocks test file modifications during implementation.
**Responsibilities:**
- PreToolUse: intercept Write/Edit operations
- Check if target file is in test directories
- Check if current phase is implementation (not test-writing)
- Block with clear error message if violation detected
- Allow override only on explicit user approval
**FRs addressed:** FR-008
**Implementation:** Shell script at `~/.claude/hooks/sweetclaude/test-guardian.sh`
**Loads:** Always active during Implement phase

### Component 5: Auto-Test Runner Hook
**Purpose:** Runs relevant tests after every source file edit during implementation.
**Responsibilities:**
- PostToolUse: detect when source files are edited
- Determine which test files cover the changed source
- Execute tests asynchronously (don't block next edit)
- Feed failures back to agent
- Skip during test-writing phase
**FRs addressed:** FR-009
**Implementation:** Shell script at `~/.claude/hooks/sweetclaude/auto-test-runner.sh`
**Loads:** Always active during Implement phase

### Component 6: Git Checkpoint Script
**Purpose:** Auto-commits `.sweetclaude/` state at phase transitions and TDD milestones.
**Responsibilities:**
- Commit failing tests with `test: RED - [story-id]` message before implementation
- Commit phase state, decision log, assumption register at phase transitions
- Detectable via `git diff` if test files modified post-commit
**FRs addressed:** FR-010, FR-004 (checkpoint aspect)
**Implementation:** Shell script at `~/.claude/hooks/sweetclaude/git-checkpoint.sh`

### Component 7: Project Init Skill
**Purpose:** One-command project bootstrap.
**Responsibilities:**
- Create code repo with `.sweetclaude/` state directory inside
- Initialize git, push to GitHub
- Run codebase discovery (FR-002)
- Generate project CLAUDE.md from discovery results
- Initialize RAG index
- Scaffold `.sweetclaude/` directory structure
- Optionally scaffold Notion workspace
- Set initial phase state to Discover
**FRs addressed:** FR-001, FR-002, FR-003, FR-014
**Loads:** On demand (`sweetclaude init`)

### Component 8: Gherkin Bridge Skill
**Purpose:** Transitions BMAD user stories to Gherkin .feature files.
**Responsibilities:**
- Read user story with acceptance criteria
- Generate `.feature` file with Given/When/Then scenarios
- Store in `.sweetclaude/stories/EPIC-XXX/`
- Update traceability map
- Feed `.feature` to TDD Level 3 test-writer agent
**FRs addressed:** FR-011
**Loads:** During Plan phase

### Component 9: Ripple-Effect Analysis Skill
**Purpose:** Before implementing changes, trace what's affected across the entire project.
**Responsibilities:**
- Analyze dependencies of change target (imports, consumers, tests)
- Check docs that reference changed behavior
- Check API contracts that may be affected
- Present impact summary before implementation proceeds
- For document ripple: scan brainstorm, PRD, architecture, stories for references to changed concepts
**FRs addressed:** FR-017, FR-018 (doc update aspect)
**Loads:** At start of Implement phase for existing codebases; on demand for document changes

### Component 10: Structured Discover Skill
**Purpose:** Structured discovery workflow for net-new products and apps. Replaces freeform brainstorming with a persona-driven interview that produces concrete user definitions, vetted feature sets, and optional competitive analysis.
**Responsibilities:**
- Conduct iterative persona interviews: for each persona, capture job title, tasks, success criteria per task
- Loop until user signals all personas are defined
- Present consolidated persona/task view for user verification
- Offer feature brainstorming: propose features one at a time (batches of 10), user includes/excludes each
- Support multiple brainstorming batches until user is satisfied
- Offer optional competitive analysis: search for competing projects, technologies, open-source alternatives
- Present competitors with ~25-word synopsis; offer drill-down or "table stakes" feature extraction
- Handle "nothing found" gracefully for novel/niche projects
- Scale to work type: full workflow for products/apps, lighter for CLIs/libraries, minimal for utilities/scripts
**FRs addressed:** FR-038, FR-039, FR-040, FR-041
**Loads:** During Discover phase for net-new work types

### Component 11: Subagent Suite
**Purpose:** Isolated agents for specific tasks requiring context separation.
**Agents:**

| Agent | Purpose | Context | Tools | Tier |
|---|---|---|---|---|
| test-writer | Write failing tests from Gherkin/.feature | Gherkin + codebase, NO implementation knowledge | Read, Grep, Glob, Write, Bash | 1 |
| implementer | Make tests pass | Tests (READ ONLY) + codebase, NO user story/Gherkin | Read, Grep, Glob, Write, Edit, Bash | 1 |
| qa-caucus-service | Review test plan — service/API angle | Test files + codebase | Read, Grep, Glob | 2 |
| qa-caucus-component | Review test plan — component angle | Test files + codebase | Read, Grep, Glob | 2 |
| qa-caucus-integration | Review test plan — cross-cutting angle | Test files + codebase | Read, Grep, Glob | 2 |
| security-reviewer | Security review | Code diff + codebase | Read, Grep, Glob | 3 |
| workflow-guardian | GitHub Actions review | Workflow files | Read, Grep, Glob | 3 |
| code-reviewer | Adversarial code review | PR diff + codebase | Read, Grep, Glob | 3 |

**FRs addressed:** FR-007 (Level 2-3), FR-012, FR-019, FR-020
**Loads:** On demand per TDD level and phase

### Component 12: State Directory Manager
**Purpose:** Manages all persistent state in the `.sweetclaude/` directory.
**Responsibilities:**
- Read/write `state/phase.yaml`
- Append to `state/decision-log.md`
- Manage `state/assumption-register.md`
- Manage `state/scope-changes.md`
- Manage `state/improvement-register.md`
- Update `traceability/requirements-map.md`
- Git commit `.sweetclaude/` state at checkpoints
**FRs addressed:** FR-016, FR-029, FR-030, FR-031, FR-032, FR-036
**Loads:** Always (lightweight — reads YAML/MD, no heavy processing)

### Component 13: Interaction Model Rules
**Purpose:** Behavioral guidance for creative partnership, encoded as rules and skill preambles.
**Responsibilities:**
- Propose-and-challenge mode (default interaction pattern)
- Adaptive flow (follow user redirects)
- Phase dwelling (never push advancement)
- Context continuity (track detours, re-orient)
- Dual context window awareness
- Periodic improvement check-ins
**FRs addressed:** FR-022, FR-027, FR-028, FR-034, FR-035, FR-037
**Implementation:** `~/.claude/rules/sweetclaude/interaction-model.md` + preambles in every skill
**Loads:** Rules file loaded per session; preambles loaded with each skill

### Component 14: Pre-Flight Guard Hook
**Purpose:** Global PreToolUse hook that blocks on first tool use if SweetClaude is not configured for the current project. Prevents sessions from proceeding without proper SweetClaude setup.
**Responsibilities:**
- PreToolUse: intercept first tool use per session per project
- Check for `.sweetclaude/state/phase.yaml`
- Block with setup instructions if SweetClaude is not configured
- Per-project opt-out via `.sweetclaude-skip` file in project root
- Session dedup via `/tmp` flags keyed to project path hash — only checks once per project per session
**Implementation:** Shell script at `~/.claude/hooks/sweetclaude/preflight-guard.sh`
**Loads:** Always active (global PreToolUse hook)

### Component 15: Hibernate Skill
**Purpose:** Freeze and thaw projects with full SweetClaude state preservation. Extends the `hibernate-project` skill with phase state, deference level, decision log, and improvement register handling.
**Responsibilities:**
- Read and capture SweetClaude state from `.sweetclaude/` (phase, deference, pending detours)
- Summarize improvement register and decision log entries
- Add SweetClaude State section to HIBERNATION.md
- On thaw: restore phase state, re-read improvement register, re-orient user
**FRs addressed:** FR-004 (state persistence)
**Loads:** Always loaded (via `always_loaded` in phase-skills.yaml)

### Component 16: Status Skill
**Purpose:** Project status dashboard. Reads `.sweetclaude/` state and presents a summary of current phase, pending decisions, open assumptions, and recent activity.
**Responsibilities:**
- Read `state/phase.yaml`, decision log, assumption register, improvement register
- Present consolidated status view
- Surface blockers and pending items
**Loads:** On demand (orchestration skill)

### Component 17: Help Skill
**Purpose:** Onboarding and reference for SweetClaude commands and workflows.
**Responsibilities:**
- List available skills and their descriptions
- Explain phase pipeline and bucket routing
- Provide quick-start guidance for new users
**Loads:** On demand (orchestration skill)

### Components 18-46: Domain Bucket Skills

The strategy, product, design, and code buckets are now fully built with all skills shipped. Each skill follows the standard SKILL.md format and loads via the bucket mapping in `phase-skills.yaml`.

**Strategy bucket (8 skills):** concept, pain-thesis, ideal-customer-profile, competitive-analysis, academic-research, meeting-prep, narrative-arc, market-messaging.

**Product bucket (12 skills):** discovery, positioning-statement, product-brief, prd, user-story, user-tdd-tests, user-success-criteria, user-workflows, manage-scope, sprint-plan, research, feature-competitive.

**Design bucket (11 skills):** architecture, tech-spec, ux, solutioning-gate, change-impact-analysis, update-docs, data-model, api-design, services-design, infra-design, manage-decisions.

**Code bucket (8 skills):** tdd, work-issue, work-debt, pr-precheck, qa-testing, mutation-testing, security-testing, code-review.

**Deploy bucket:** Placeholder — no skills yet.

---

## Phase-Skill Mapping

**`config/sweetclaude/phase-skills.yaml`:**

The phase-skills map uses a five-bucket structure — `strategy:`, `product:`, `design:`, `code:`, `deploy:` — instead of the earlier dual-track `code:`/`strategy:` split. The `new-task` and `auto-flow` skills classify work into a bucket and surface appropriate skills.

```yaml
always_loaded:
  skills:
    - sweetclaude
    - sweetclaude:new-task
    - sweetclaude:hibernate
    - hibernate-project
  rules:
    - sweetclaude/interaction-model.md
    - sweetclaude/phase-gates.md
    - sweetclaude/tdd-levels.md

strategy:
  skills:
    - sweetclaude:strategy/concept
    - sweetclaude:strategy/pain-thesis
    - sweetclaude:strategy/ideal-customer-profile
    - sweetclaude:strategy/competitive-analysis
    - sweetclaude:strategy/academic-research
    - sweetclaude:strategy/meeting-prep
    - sweetclaude:strategy/narrative-arc
    - sweetclaude:strategy/market-messaging
    - caucus
    - reasoning-frameworks
  agents: []
  hooks: []

product:
  skills:
    - sweetclaude:product/discovery
    - sweetclaude:product/positioning-statement
    - sweetclaude:product/product-brief
    - sweetclaude:product/prd
    - sweetclaude:product/user-story
    - sweetclaude:product/user-tdd-tests
    - sweetclaude:product/user-success-criteria
    - sweetclaude:product/user-workflows
    - sweetclaude:product/manage-scope
    - sweetclaude:product/backlog
    - sweetclaude:product/sprint-plan
    - sweetclaude:product/research
    - sweetclaude:product/feature-competitive
    - reconciling-documents
  agents: []
  hooks: []

design:
  skills:
    - sweetclaude:design/architecture
    - sweetclaude:design/tech-spec
    - sweetclaude:design/ux
    - sweetclaude:design/solutioning-gate
    - sweetclaude:design/change-impact-analysis
    - sweetclaude:design/update-docs
    - sweetclaude:design/data-model
    - sweetclaude:design/api-design
    - sweetclaude:design/services-design
    - sweetclaude:design/infra-design
    - sweetclaude:design/manage-decisions
    - caucus
    - reasoning-frameworks
  agents: []
  hooks: []

code:
  skills:
    - sweetclaude:code/tdd
    - sweetclaude:code/work-issue
    - sweetclaude:code/work-debt
    - sweetclaude:code/pr-precheck
    - sweetclaude:code/qa-testing
    - sweetclaude:code/mutation-testing
    - sweetclaude:code/security-testing
    - sweetclaude:code/code-review
    - superpowers:writing-plans
    - superpowers:executing-plans
    - superpowers:using-git-worktrees
    - superpowers:systematic-debugging
    - superpowers:dispatching-parallel-agents
    - superpowers:subagent-driven-development
  agents:
    - sweetclaude:test-writer
    - sweetclaude:implementer
    - sweetclaude:qa-caucus-service
    - sweetclaude:qa-caucus-component
    - sweetclaude:qa-caucus-integration
  hooks:
    - test-guardian
    - auto-test-runner
    - git-checkpoint

deploy:
  skills: []
  agents: []
  hooks: []
```

**Always loaded (regardless of phase or bucket):**
- Master skill (phase router + interaction model)
- New-task skill, hibernate skill, hibernate-project skill
- Rules: `interaction-model.md`, `phase-gates.md`, `tdd-levels.md`
- State directory manager

---

## NFR Coverage

### NFR-001: Context Window Efficiency
**Solution:** Phase-skill mapping (above) ensures only relevant skills load per phase. Master skill is lean — reads phase state, surfaces skill list, manages interaction. RAG queries on demand. `.sweetclaude/` state read as small YAML/MD files, not bulk-loaded.
**Validation:** Measure baseline context at session start. Target: under 15KB.

### NFR-002: Language/Framework Agnosticism
**Solution:** Codebase discovery (FR-002) populates a `project.yaml` with detected language, test runner, formatter, build commands. All hooks and skills read from this file — no hardcoded commands anywhere. Hook scripts use `$PROJECT_TEST_CMD`, `$PROJECT_FMT_CMD` variables set from `project.yaml`.
**Validation:** Test init + TDD cycle on Python, TypeScript, Go projects.

### NFR-003: Session Recovery
**Solution:** `.sweetclaude/state/phase.yaml` contains current phase, work type, deference level. Decision log, assumption register committed at every phase transition. Master skill reads state on session start and resumes.
**Validation:** Kill session mid-phase, restart, verify resume from last checkpoint.

### NFR-004: Installation Simplicity
**Solution:** Single install mechanism — copy/clone SweetClaude files into `~/.claude/`. No compilation. Prerequisites: Claude Code CLI, git, GitHub CLI (`gh`), Superpowers plugin (5.0.7+), BMAD Method (6.0.0+). The installer validates all prerequisites and versions before proceeding.
**Validation:** Fresh machine install in under 5 minutes following docs.

### NFR-005: Upstream Compatibility
**Solution:** SweetClaude never modifies Superpowers or BMAD files. Phase-skill mapping delegates to upstream skills by name. If upstream skill not found, warn and continue. Hooks are additive (SweetClaude hooks in separate namespace, no conflicts).
**Validation:** Disable SweetClaude, verify Superpowers and BMAD still work independently.

### NFR-006: Security — No Credential Exposure
**Solution:** Init generates `.gitignore` excluding `.env`, `*.pem`, `*.key`, credentials. Hooks never log environment variables. `.sweetclaude/` stores no secrets.
**Validation:** Grep repo for credential patterns after full lifecycle test.

### NFR-007: Performance — Hook Overhead
**Solution:** PreToolUse hooks (test guardian) are simple file path checks — under 100ms. PostToolUse hooks (auto-test runner) launch tests asynchronously — don't block next edit.
**Validation:** Time hook execution during normal development session.

### NFR-008: Extensibility
**Solution:** Custom skills declare phase membership by adding entries to `phase-skills.yaml`. Custom subagents follow same markdown frontmatter format. Custom hooks added to `settings.json` without modifying core files.
**Validation:** Add a custom skill, verify it appears in correct phase.

---

## Development Tiers

All 46 skills across the five domain buckets are now Tier 1 — built and shipped.

| Bucket | Count | Skills |
|---|---|---|
| Orchestration | 7 | master (SKILL.md), help, status, auto-flow, init, new-task, hibernate |
| Strategy | 8 | concept, pain-thesis, ideal-customer-profile, competitive-analysis, academic-research, meeting-prep, narrative-arc, market-messaging |
| Product | 12 | discovery, positioning-statement, product-brief, prd, user-story, user-tdd-tests, user-success-criteria, user-workflows, manage-scope, sprint-plan, research, feature-competitive |
| Design | 11 | architecture, tech-spec, ux, solutioning-gate, change-impact-analysis, update-docs, data-model, api-design, services-design, infra-design, manage-decisions |
| Code | 8 | tdd, work-issue, work-debt, pr-precheck, qa-testing, mutation-testing, security-testing, code-review |
| Deploy | 0 | (placeholder — no skills yet) |

Supporting infrastructure also shipped:

| Component | Type |
|---|---|
| Test Guardian | Hook |
| Auto-Test Runner | Hook |
| Git Checkpoint | Hook |
| Auto-Reindex | Hook |
| Pre-Flight Guard | Hook |
| Test Writer Agent | Subagent |
| Implementer Agent | Subagent |
| QA Caucus (3 agents) | Subagents |
| Security Reviewer | Subagent |
| Workflow Guardian | Subagent |
| Code Reviewer | Subagent |
| Phase Gates | Rules |
| TDD Levels | Rules |
| Interaction Model | Rules |
| Phase-Skills Map | Config |
| Defaults | Config |

---

## Key Trade-offs

### Trade-off 1: Behavioral guidance vs. deterministic enforcement
**Decision:** Interaction model FRs are implemented as rules/preambles, not hooks.
**Gain:** Covers the full interaction vision with the tools available today.
**Lose:** Claude may not always follow behavioral guidance (our own research confirmed this).
**Rationale:** No hook mechanism exists for conversational behavior. Rules + preambles are the best available tool. The continuous improvement register (FR-036) creates a feedback loop to refine these over time.

### Trade-off 2: Separate repo vs. in-repo `.sweetclaude/` directory
**Decision:** SweetClaude state lives inside the project repo as `.sweetclaude/`.
**Gain:** Single repo to manage. No sync overhead. State travels with the codebase. Simpler init, simpler git workflow.
**Lose:** SweetClaude artifacts (specs, brainstorms, RAG index) are visible in the project repo. Cannot have a private working directory if code repo is public (use `.gitignore` for sensitive items).
**Rationale:** The two-repo model added real friction for minimal benefit. A dotfile directory inside the project achieves clean separation without the operational overhead of maintaining two repos.

### Trade-off 3: Bucket-scoped skill loading vs. flat availability
**Decision:** Skills only surface for their matched domain bucket.
**Gain:** Smaller context window, prevents wrong-tool selection, clearer UX.
**Lose:** User must override to use an out-of-bucket skill.
**Rationale:** Context window efficiency (Driver #1) is the hardest constraint. Bucket scoping is the highest-leverage optimization. Override is always available.

### Trade-off 4: Language agnosticism vs. deep framework integration
**Decision:** SweetClaude discovers and adapts to any stack rather than deeply integrating with specific frameworks.
**Gain:** Works with anything. Single framework to maintain.
**Lose:** Can't leverage framework-specific optimizations (e.g., Rails generators, Next.js conventions).
**Rationale:** The user builds across a broad spectrum with no single stack. Generic + discoverable beats deep + narrow.

---

## FR Traceability

| FR | Component(s) | Tier |
|---|---|---|
| FR-001 | Init Skill | 1 |
| FR-002 | Init Skill (codebase discovery) | 1 |
| FR-003 | Init Skill (Notion scaffold) | 1 |
| FR-004 | Master Skill (phase pipeline) | 1 |
| FR-005 | New Task / Auto-Flow | 1 |
| FR-006 | Master Skill (phase-skill mapping) | 1 |
| FR-007 | TDD Skill + Test Writer + Implementer agents | 1 |
| FR-008 | Test Guardian Hook | 1 |
| FR-009 | Auto-Test Runner Hook | 1 |
| FR-010 | Git Checkpoint Script | 1 |
| FR-011 | Gherkin Bridge Skill | 1 |
| FR-012 | QA Caucus Agents (3) | 1 |
| FR-013 | Mutation Testing Skill | 1 |
| FR-014 | Init Skill (RAG setup) | 1 |
| FR-015 | Auto-Reindex Hook | 1 |
| FR-016 | State Directory Manager (traceability) | 1 |
| FR-017 | Ripple-Effect Skill | 1 |
| FR-018 | Auto-Docs Skill | 1 |
| FR-019 | Security Reviewer Agent | 1 |
| FR-020 | Workflow Guardian Agent | 1 |
| FR-021 | Model Routing Config | 1 |
| FR-022 | Interaction Model Rules | 1 |
| FR-023 | Global CLAUDE.md | 1 |
| FR-024 | Master Skill + Phase-Skill Map | 1 |
| FR-025 | New Task / Auto-Flow (mid-stream detection) | 1 |
| FR-026 | Master Skill (phase re-entry) | 1 |
| FR-027 | Interaction Model Rules | 1 |
| FR-028 | Interaction Model Rules | 1 |
| FR-029 | State Directory Manager (decision summary) | 1 |
| FR-030 | State Directory Manager (decision log) | 1 |
| FR-031 | State Directory Manager (assumption register) | 1 |
| FR-032 | State Directory Manager (scope changes) | 1 |
| FR-033 | Master Skill + Defaults Config (deference level) | 1 |
| FR-034 | Interaction Model Rules (detour management) | 1 |
| FR-035 | Interaction Model Rules (dual context) | 1 |
| FR-036 | State Directory Manager (improvement register) + Interaction Model Rules (triggers) | 1 |
| FR-037 | Interaction Model Rules (phase dwelling) | 1 |
| FR-038 | Product Discovery Skill (persona discovery) | 1 |
| FR-039 | Product Discovery Skill (feature brainstorming) | 1 |
| FR-040 | Strategy Competitive Analysis Skill | 1 |
| FR-041 | Product Discovery Skill + Master Skill (work-type scaling) | 1 |
| FR-042 | Pre-Flight Guard Hook (project configuration enforcement) | 1 |
| FR-043 | Hibernate Skill (project freeze/thaw with SweetClaude state) | 1 |
| FR-044 | Strategy Reconciliation Skill (file onboarding and organization) | 1 |
| FR-045 | Strategy Academic Research Skill (academic paper development pipeline) | 1 |

---

## Supporting Documents

- PRD: `docs/prd-sweetclaude-v1-2026-04-12.md`
- Product Brief: `docs/product-brief-sweetclaude-v1-2026-04-12.md`
- Brainstorm: `docs/brainstorm-sweetclaude-2026-04-12.md`
- TDD Analysis: `docs/tdd-analysis-v1-2026-04-12.md`

---

*Generated by BMAD Method v6 — System Architect*
