# Architecture: SweetClaude v1 — 2026-04-12

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
| 3 | Session recovery | Sessions die; state must survive | Working repo persistence, git checkpoints, phase state files |
| 4 | Language/framework agnosticism | No hardcoded stack assumptions | Codebase discovery drives all config; templates, not constants |
| 5 | Upstream compatibility | Must not break Superpowers or BMAD | Orchestrate via delegation, never override or monkey-patch |
| 6 | TDD enforcement hooks | Advisory TDD fails; deterministic enforcement required | Native Claude Code hooks (PreToolUse, PostToolUse, Stop) |
| 7 | RAG + semantic knowledge | Large document corpus, per-project index | mcp-local-rag, index in working repo, query on demand |
| 8 | Persistent project memory | Decisions, assumptions, traceability must outlive sessions | Structured markdown in working repo, committed at checkpoints |
| 9 | Phase dwelling over rushing | User controls pace; system never pushes advancement | No unprompted "move on?" — all skills written to dwell |
| 10 | Ripple-effect management | Changes propagate across artifacts; nothing falls out of sync | Dependency awareness across docs, code, tests, specs |

---

## Architecture Pattern

**Pattern:** Orchestration layer over existing plugins, implemented as Claude Code native extensions (skills, hooks, subagents, rules, config files).

**Rationale:** SweetClaude is not an application with a server, database, or API. It's a framework of files that Claude Code loads and executes. The architecture is about file organization, loading strategy, and interaction patterns — not services and infrastructure.

**Key principle:** SweetClaude orchestrates Superpowers and BMAD; it doesn't replace or fork them. It adds a phase pipeline, enforcement hooks, interaction model, and project scaffolding that those plugins don't provide.

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
│  │  │ Phase      │  │ Test guard │  │ QA caucus   │  │   │
│  │  │ Router     │  │ Auto-test  │  │ Security    │  │   │
│  │  │ TDD        │  │ Git ckpt   │  │ Workflow    │  │   │
│  │  │ Gherkin    │  │ Auto-fmt   │  │ Test runner │  │   │
│  │  │ Init       │  │ Protected  │  │ Code review │  │   │
│  │  │ Ripple     │  │ paths      │  │             │  │   │
│  │  │ ...        │  │            │  │             │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  │   │
│  │                                                    │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  │   │
│  │  │   RULES    │  │   CONFIG   │  │  WORKING   │  │   │
│  │  │            │  │            │  │   REPO     │  │   │
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
│       ├── init/SKILL.md              # Project bootstrap
│       ├── tdd/SKILL.md              # SweetClaude TDD (all 4 levels)
│       ├── gherkin-bridge/SKILL.md   # Story → .feature → tests
│       ├── ripple/SKILL.md           # Ripple-effect analysis
│       ├── fix-issue/SKILL.md        # End-to-end issue implementation
│       ├── pr-ready/SKILL.md         # Pre-PR quality gate
│       └── work-router/SKILL.md      # Work-type detection and routing
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
│       └── git-checkpoint.sh         # Auto-commits at phase transitions
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

### Per-project SweetClaude working repo

```
<project>-sweetclaude/
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

### Component 2: Work Router
**Purpose:** Identifies the type of work and routes to the correct pipeline entry point.
**Responsibilities:**
- Ask or detect work type (net-new, bug fix, enhancement, iteration)
- Route to appropriate phase entry
- Detect mid-stream work-type shifts
- Handle escalation to Discover when deeper issues surface
**FRs addressed:** FR-005, FR-025
**Loads:** At session start, before any work begins

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
**Purpose:** Auto-commits working repo state at phase transitions and TDD milestones.
**Responsibilities:**
- Commit failing tests with `test: RED - [story-id]` message before implementation
- Commit phase state, decision log, assumption register at phase transitions
- Detectable via `git diff` if test files modified post-commit
**FRs addressed:** FR-010, FR-004 (checkpoint aspect)
**Implementation:** Shell script at `~/.claude/hooks/sweetclaude/git-checkpoint.sh`

### Component 7: Project Init Skill
**Purpose:** One-command project bootstrap.
**Responsibilities:**
- Create code repo and working repo directories
- Initialize git in both, push to GitHub
- Run codebase discovery (FR-002)
- Generate project CLAUDE.md from discovery results
- Initialize RAG index
- Scaffold working repo directory structure
- Optionally scaffold Notion workspace
- Set initial phase state to Discover
**FRs addressed:** FR-001, FR-002, FR-003, FR-014
**Loads:** On demand (`sweetclaude init`)

### Component 8: Gherkin Bridge Skill
**Purpose:** Transitions BMAD user stories to Gherkin .feature files.
**Responsibilities:**
- Read user story with acceptance criteria
- Generate `.feature` file with Given/When/Then scenarios
- Store in working repo under `stories/EPIC-XXX/`
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

### Component 12: Working Repo State Manager
**Purpose:** Manages all persistent state in the working repo.
**Responsibilities:**
- Read/write `state/phase.yaml`
- Append to `state/decision-log.md`
- Manage `state/assumption-register.md`
- Manage `state/scope-changes.md`
- Manage `state/improvement-register.md`
- Update `traceability/requirements-map.md`
- Git commit state at checkpoints
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

---

## Phase-Skill Mapping

**`config/sweetclaude/phase-skills.yaml`:**

```yaml
phases:
  discover:
    skills:
      - bmad:brainstorm
      - bmad:research
      - sweetclaude:work-router
      - caucus
      - reasoning-frameworks
    agents: []
    hooks: []

  define:
    skills:
      - bmad:product-brief
      - bmad:prd
      - sweetclaude:work-router
      - sweetclaude:ripple
      - reconciling-documents
      - backlog-management
    agents: []
    hooks: []

  design:
    skills:
      - bmad:tech-spec
      - bmad:architecture
      - bmad:create-ux-design
      - bmad:solutioning-gate-check
      - sweetclaude:ripple
      - caucus
      - reasoning-frameworks
    agents: []
    hooks: []

  plan:
    skills:
      - bmad:create-story
      - bmad:sprint-planning
      - sweetclaude:gherkin-bridge
      - backlog-management
    agents: []
    hooks: []

  implement:
    skills:
      - sweetclaude:tdd
      - sweetclaude:fix-issue
      - sweetclaude:ripple
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

  verify:
    skills:
      - sweetclaude:pr-ready
      - sweetclaude:ripple
      - superpowers:requesting-code-review
      - superpowers:receiving-code-review
      - superpowers:verification-before-completion
      - superpowers:simplify
    agents:
      - sweetclaude:code-reviewer
      - sweetclaude:security-reviewer
      - sweetclaude:workflow-guardian
    hooks: []

  ship:
    skills:
      - superpowers:finishing-a-development-branch
      - sweetclaude:pr-ready
    agents: []
    hooks: []
```

**Always loaded (regardless of phase):**
- Master skill (phase router + interaction model)
- Rules: `interaction-model.md`, `phase-gates.md`, `tdd-levels.md`
- Working repo state manager

---

## NFR Coverage

### NFR-001: Context Window Efficiency
**Solution:** Phase-skill mapping (above) ensures only relevant skills load per phase. Master skill is lean — reads phase state, surfaces skill list, manages interaction. RAG queries on demand. Working repo state read as small YAML/MD files, not bulk-loaded.
**Validation:** Measure baseline context at session start. Target: under 15KB.

### NFR-002: Language/Framework Agnosticism
**Solution:** Codebase discovery (FR-002) populates a `project.yaml` with detected language, test runner, formatter, build commands. All hooks and skills read from this file — no hardcoded commands anywhere. Hook scripts use `$PROJECT_TEST_CMD`, `$PROJECT_FMT_CMD` variables set from `project.yaml`.
**Validation:** Test init + TDD cycle on Python, TypeScript, Go projects.

### NFR-003: Session Recovery
**Solution:** Working repo contains `state/phase.yaml` with current phase, work type, deference level. Decision log, assumption register committed at every phase transition. Master skill reads state on session start and resumes.
**Validation:** Kill session mid-phase, restart, verify resume from last checkpoint.

### NFR-004: Installation Simplicity
**Solution:** Single install mechanism — copy/clone SweetClaude files into `~/.claude/`. No compilation. Prerequisites: Claude Code CLI, git, GitHub CLI (`gh`), Superpowers plugin (5.0.7+), BMAD Method (6.0.0+). The installer validates all prerequisites and versions before proceeding.
**Validation:** Fresh machine install in under 5 minutes following docs.

### NFR-005: Upstream Compatibility
**Solution:** SweetClaude never modifies Superpowers or BMAD files. Phase-skill mapping delegates to upstream skills by name. If upstream skill not found, warn and continue. Hooks are additive (SweetClaude hooks in separate namespace, no conflicts).
**Validation:** Disable SweetClaude, verify Superpowers and BMAD still work independently.

### NFR-006: Security — No Credential Exposure
**Solution:** Init generates `.gitignore` for both repos excluding `.env`, `*.pem`, `*.key`, credentials. Hooks never log environment variables. Working repo stores no secrets.
**Validation:** Grep both repos for credential patterns after full lifecycle test.

### NFR-007: Performance — Hook Overhead
**Solution:** PreToolUse hooks (test guardian) are simple file path checks — under 100ms. PostToolUse hooks (auto-test runner) launch tests asynchronously — don't block next edit.
**Validation:** Time hook execution during normal development session.

### NFR-008: Extensibility
**Solution:** Custom skills declare phase membership by adding entries to `phase-skills.yaml`. Custom subagents follow same markdown frontmatter format. Custom hooks added to `settings.json` without modifying core files.
**Validation:** Add a custom skill, verify it appears in correct phase.

---

## Development Tiers

### Tier 1 — Ship today as actual files
Core pipeline, enforcement hooks, and project scaffolding.

| Component | Type | Files to Create |
|---|---|---|
| Master Skill | Skill | `skills/sweetclaude/SKILL.md` |
| Work Router | Skill | `skills/sweetclaude/work-router/SKILL.md` |
| TDD Skill | Skill | `skills/sweetclaude/tdd/SKILL.md` |
| Gherkin Bridge | Skill | `skills/sweetclaude/gherkin-bridge/SKILL.md` |
| Project Init | Skill | `skills/sweetclaude/init/SKILL.md` |
| Ripple-Effect | Skill | `skills/sweetclaude/ripple/SKILL.md` |
| Fix-Issue | Skill | `skills/sweetclaude/fix-issue/SKILL.md` |
| PR-Ready | Skill | `skills/sweetclaude/pr-ready/SKILL.md` |
| Discover Deep | Skill | `skills/sweetclaude/discover-deep/SKILL.md` |
| Test Guardian | Hook | `hooks/sweetclaude/test-guardian.sh` |
| Auto-Test Runner | Hook | `hooks/sweetclaude/auto-test-runner.sh` |
| Git Checkpoint | Hook | `hooks/sweetclaude/git-checkpoint.sh` |
| Test Writer Agent | Subagent | `agents/sweetclaude/test-writer.md` |
| Implementer Agent | Subagent | `agents/sweetclaude/implementer.md` |
| Phase Gates | Rules | `rules/sweetclaude/phase-gates.md` |
| TDD Levels | Rules | `rules/sweetclaude/tdd-levels.md` |
| Global CLAUDE.md | Config | `~/CLAUDE.md` |
| Phase-Skills Map | Config | `config/sweetclaude/phase-skills.yaml` |
| Defaults | Config | `config/sweetclaude/defaults.yaml` |

**Estimated files:** 18
**FRs covered:** FR-001, FR-002, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-014, FR-016, FR-017, FR-023, FR-024

### Tier 2 — Behavioral guidance encoded in rules and preambles
Interaction model — can't be hook-enforced, relies on prompt discipline. Written as rules files and skill preambles that shape Claude's behavior.

| Component | Type | Files to Create |
|---|---|---|
| Interaction Model | Rules | `rules/sweetclaude/interaction-model.md` |
| Decision Log Template | Template | `templates/decision-log-entry.md` |
| Assumption Register Template | Template | `templates/assumption-register.md` |
| Improvement Register Template | Template | `templates/improvement-register.md` |
| Auto-Doc Updates | Skill | `skills/sweetclaude/auto-docs/SKILL.md` |

**Estimated files:** 5
**FRs covered:** FR-018, FR-022, FR-025, FR-026, FR-027, FR-028, FR-029, FR-030, FR-031, FR-033, FR-034, FR-035, FR-036, FR-037

### Tier 3 — Post v1.0
Features that require more infrastructure, testing, or dependency management.

| Component | Type | Notes |
|---|---|---|
| Notion Scaffold | Skill | Requires Notion MCP auth + workspace setup |
| QA Caucus (3 agents) | Subagents | Needs real-world calibration |
| Mutation Testing | Skill | Per-language tool selection |
| Auto-Reindex | Hook | Needs file watcher integration |
| Security Reviewer | Subagent | Needs calibration against real codebases |
| Workflow Guardian | Subagent | Needs calibration |
| Model Routing | Config | Requires config schema + validation |
| Scope Change Tracking | State | Lower priority persistence |

**FRs covered:** FR-003, FR-012, FR-013, FR-015, FR-019, FR-020, FR-021, FR-032

---

## Key Trade-offs

### Trade-off 1: Behavioral guidance vs. deterministic enforcement
**Decision:** Tier 2 interaction model FRs are implemented as rules/preambles, not hooks.
**Gain:** Can ship today; covers the full interaction vision.
**Lose:** Claude may not always follow behavioral guidance (our own research confirmed this).
**Rationale:** No hook mechanism exists for conversational behavior. Rules + preambles are the best available tool. The continuous improvement register (FR-036) creates a feedback loop to refine these over time.

### Trade-off 2: Two repos vs. one repo
**Decision:** Every project gets a code repo and a SweetClaude working repo.
**Gain:** Clean separation — embeddings, specs, state don't pollute the product codebase. Working repo can be private even if code repo is public.
**Lose:** More git management. Two repos to keep in sync.
**Rationale:** Mixing RAG indexes, brainstorm outputs, and phase state into a product codebase is wrong. The separation is worth the overhead.

### Trade-off 3: Phase-scoped skill loading vs. flat availability
**Decision:** Skills only surface for their mapped phase.
**Gain:** Smaller context window, prevents wrong-tool selection, clearer UX.
**Lose:** User must override to use an out-of-phase skill.
**Rationale:** Context window efficiency (Driver #1) is the hardest constraint. Phase scoping is the highest-leverage optimization. Override is always available.

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
| FR-003 | Init Skill (Notion scaffold) | 3 |
| FR-004 | Master Skill (phase pipeline) | 1 |
| FR-005 | Work Router | 1 |
| FR-006 | Master Skill (phase-skill mapping) | 1 |
| FR-007 | TDD Skill + Test Writer + Implementer agents | 1 |
| FR-008 | Test Guardian Hook | 1 |
| FR-009 | Auto-Test Runner Hook | 1 |
| FR-010 | Git Checkpoint Script | 1 |
| FR-011 | Gherkin Bridge Skill | 1 |
| FR-012 | QA Caucus Agents (3) | 3 |
| FR-013 | Mutation Testing Skill | 3 |
| FR-014 | Init Skill (RAG setup) | 1 |
| FR-015 | Auto-Reindex Hook | 3 |
| FR-016 | Working Repo State Manager (traceability) | 1 |
| FR-017 | Ripple-Effect Skill | 1 |
| FR-018 | Auto-Docs Skill | 2 |
| FR-019 | Security Reviewer Agent | 3 |
| FR-020 | Workflow Guardian Agent | 3 |
| FR-021 | Model Routing Config | 3 |
| FR-022 | Interaction Model Rules | 2 |
| FR-023 | Global CLAUDE.md | 1 |
| FR-024 | Master Skill + Phase-Skill Map | 1 |
| FR-025 | Work Router (mid-stream detection) | 2 |
| FR-026 | Master Skill (phase re-entry) | 2 |
| FR-027 | Interaction Model Rules | 2 |
| FR-028 | Interaction Model Rules | 2 |
| FR-029 | Working Repo State Manager (decision summary) | 2 |
| FR-030 | Working Repo State Manager (decision log) | 2 |
| FR-031 | Working Repo State Manager (assumption register) | 2 |
| FR-032 | Working Repo State Manager (scope changes) | 3 |
| FR-033 | Master Skill + Defaults Config (deference level) | 2 |
| FR-034 | Interaction Model Rules (detour management) | 2 |
| FR-035 | Interaction Model Rules (dual context) | 2 |
| FR-036 | Working Repo State Manager (improvement register) + Interaction Model Rules (triggers) | 2 |
| FR-037 | Interaction Model Rules (phase dwelling) | 2 |
| FR-038 | Discover Deep Skill (persona discovery) | 1 |
| FR-039 | Discover Deep Skill (feature brainstorming) | 1 |
| FR-040 | Discover Deep Skill (competitive analysis) | 1 |
| FR-041 | Discover Deep Skill + Master Skill (work-type scaling) | 1 |

---

## Supporting Documents

- PRD: `docs/prd-sweetclaude-v1-2026-04-12.md`
- Product Brief: `docs/product-brief-sweetclaude-v1-2026-04-12.md`
- Brainstorm: `docs/brainstorm-sweetclaude-2026-04-12.md`
- TDD Analysis: `docs/tdd-analysis-v1-2026-04-12.md`

---

*Generated by BMAD Method v6 — System Architect*
