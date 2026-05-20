# Brainstorming Session: SweetClaude

**Date:** 2026-04-12
**Objective:** Define a unified Claude Code framework (SweetClaude) that combines the best of Superpowers, [removed], Don Cheli, and custom skills into a single end-to-end platform for RAG-powered knowledge work and disciplined TDD development — from initial concept through fully tested, deployed code.

**Context:**
- Solo developer, fast-paced, broad project spectrum (web apps, microservices, CLIs, APIs, utilities)
- No single language/framework — must be generic
- Follows a deliberate progression: concept → competitive landscape → functional definition → architecture → code
- Three existing systems (Superpowers, [removed], Don Cheli) with significant overlap and friction
- Custom skills that fill real gaps and should be preserved
- Two core problems: (1) large-corpus knowledge work beyond Claude.ai limits, (2) end-to-end TDD lifecycle

## Techniques Used
1. Mind Mapping — full capability inventory across all sources
2. SCAMPER — creative recombination of existing tools
3. Reverse Brainstorming — failure mode analysis

---

## Key Insights

### Insight 1: The Pipeline Is the Product
**Description:** SweetClaude isn't a collection of skills — it's a pipeline with explicit phases and gates. The user's natural workflow (concept → landscape → functional def → architecture → code) maps directly onto [removed]'s agent progression (Creative Intelligence → Business Analyst → Product Manager → System Architect → Developer). Each phase has entry criteria, exit criteria, and defined outputs that feed the next phase.
**Source:** Mind mapping (Branch 2 + Branch 3), SCAMPER (Combine), Reverse Brainstorming (#2 phase confusion)
**Impact:** High
**Effort:** Medium
**Why it matters:** Without explicit phases, Claude mixes concerns — starts coding during brainstorming, starts architecting during implementation. The pipeline prevents this.

### Insight 2: Gherkin Is the Bridge Between Worlds
**Description:** The transition from product definition to development is the hardest handoff. Gherkin acceptance criteria (Given/When/Then) serve as the contract between [removed]'s product phase and the TDD implementation phase. [removed] stories → Gherkin `.feature` files → isolated test writer agent → QA caucus → user approval → isolated implementer agent → verification. Research confirms this: AutoUAT + TestFlow studies show 95% of Gherkin acceptance tests rated helpful, 92% of generated test scripts rated helpful. Thoughtworks identified spec-driven development with Gherkin as a key 2025-2026 practice. LLMs can now execute Gherkin specs directly without glue code.
**Source:** Mind mapping (Branch 2 → Branch 3 gap), SCAMPER (Combine), TDD Analysis research (arxiv.org AutoUAT, Thoughtworks)
**Impact:** High
**Effort:** Medium
**Why it matters:** Without this bridge, product specs and code diverge. With it, every behavior is traceable from user need to passing test. Research validates Gherkin as the emerging standard interchange format between product requirements and AI-generated tests.

### Insight 3: Two Repos, One Command
**Description:** Every project needs two GitHub repos: the code repo (the product) and the SweetClaude working repo (embeddings, specs, brainstorm outputs, working documents). A single `sweetclaude init <project-name>` command creates both, sets up GitHub remotes, initializes RAG, scaffolds Notion, generates project CLAUDE.md from codebase discovery, and verifies the setup.
**Source:** User requirement, SCAMPER (Modify), Reverse Brainstorming (#6 bootstrap friction)
**Impact:** High
**Effort:** High
**Why it matters:** If setup is painful, it won't be used consistently. Zero-friction bootstrap means every project gets the full framework.

### Insight 4: Phase-Aware Skill Surfacing
**Description:** SweetClaude should know what phase the project is in and surface only relevant capabilities. During brainstorming, don't show TDD skills. During implementation, don't show PRD tools. This replaces the current flat list of 50+ skills that forces Claude to evaluate relevance every message.
**Source:** Reverse Brainstorming (#5 skill explosion), SCAMPER (Reverse)
**Impact:** High
**Effort:** Medium
**Why it matters:** Reduces context window load, eliminates wrong-skill selection, and creates a clearer UX — you always know what SweetClaude can do right now.

### Insight 5: Knowledge Layer = RAG + Notion + Git History
**Description:** SweetClaude's knowledge layer is three sources unified: (1) RAG index over project docs and reference material, (2) Notion for living product artifacts (PRD, specs, ADRs), (3) Git history for implementation decisions and code evolution. All three should be queryable, but loaded on demand to preserve context window.
**Source:** Mind mapping (Branch 1), SCAMPER (Combine), Reverse Brainstorming (#1 context bloat, #3 index rot)
**Impact:** High
**Effort:** High
**Why it matters:** This is the "far more complex work with a much larger document corpus" requirement. Without it, SweetClaude is just a fancy skill collection.

### Insight 6: Best-of-Breed Selection Is Clear
**Description:** The overlap analysis reveals clean ownership lines:
- **[removed]** owns the product lifecycle (brainstorm → brief → PRD → spec → architecture → stories → sprints)
- **Superpowers** owns the development mechanics (plans, parallel agents, worktrees, debugging, code review, branch management)
- **Custom skills** own the quality contracts and specialized capabilities (real-tdd, fix-issue, pr-ready, caucus, reasoning-frameworks, rag-index, session-export, backlog-management, reconciling-documents)
- **Don Cheli** is fully replaced — every capability it provides is covered better by one of the above three
**Source:** Mind mapping (all branches), SCAMPER (Eliminate)
**Impact:** High
**Effort:** Low (removal is straightforward)
**Why it matters:** Eliminates ~700KB of redundant commands, resolves all overlap conflicts, and halves the skill registry.

### Insight 7: Checkpoints Prevent Loss
**Description:** Every phase transition must be a checkpoint: git commit in the SweetClaude working repo, plan file updated, workflow status tracked. Combined with Superpowers' plan recovery and git history, this means any session can resume from the last completed phase.
**Source:** Reverse Brainstorming (#8 no way to resume), Mind mapping (Branch 5)
**Impact:** Medium
**Effort:** Low
**Why it matters:** Solo developer + long-running projects + Claude context limits = sessions will die. Recovery must be automatic, not manual.

### Insight 8: Enforcement Beats Guidance — TDD Must Be Hook-Enforced
**Description:** Research conclusively shows that advisory TDD instructions (CLAUDE.md, prompt text) are insufficient. Claude "sometimes listens, sometimes does its own thing." Martin Fowler coined "harness engineering" (April 2026) for this: deterministic enforcement via hooks is the proven approach. The MSR '26 study (1.2M commits, 2,168 repos) empirically confirmed that AI coding agents over-mock 95% of the time. NIST documented agents modifying tests, disabling assertions, and exploiting scoring loopholes. The countermeasure is a layered enforcement stack: PreToolUse hooks that physically block test file edits during implementation, git commit checkpoints on failing tests, PostToolUse hooks that auto-run tests after code changes, and optionally mutation testing to verify test quality.
**Source:** TDD Analysis research (Fowler "harness engineering", MSR '26 over-mocking study, NIST benchmark gaming, TDD Guard, CircleCI test hooks)
**Impact:** Critical
**Effort:** Medium
**Why it matters:** Without deterministic enforcement, TDD discipline degrades. This is the single highest-leverage improvement SweetClaude can make over all three existing approaches.

### Insight 9: Context Isolation Is the AI TDD Breakthrough
**Description:** Separating test-writing and implementation into different subagent contexts — where the test writer never sees implementation and the implementer never sees the user story — is the most effective AI TDD technique discovered. Research shows multi-agent TDD with separate contexts achieved 96.3% pass@1 on HumanEval (vs 67% single-agent), and test generation accuracy jumped from 61% to 87.8% when tests were written without knowledge of planned implementation. Anthropic itself calls TDD "the single strongest pattern for working with agentic coding tools."
**Source:** TDD Analysis research (HumanEval multi-agent study, Anthropic blog, alexop.dev analysis)
**Impact:** Critical
**Effort:** Medium
**Why it matters:** Single-context TDD allows the test writer's analysis to bleed into the implementer's thinking, undermining genuine test-first development. Context isolation is what makes AI TDD actually work.

### Insight 10: No Existing TDD Tool Is Sufficient — SweetClaude Needs Its Own
**Description:** Deep analysis of real-tdd, Superpowers TDD, and Don Cheli's TDD Documentation Suite reveals that none is sufficient alone. real-tdd has the right philosophy (subagent separation, test immutability, QA caucus) but is too rigid and hardcoded to TypeScript. Superpowers has the best language agnosticism but lacks subagent separation. Don Cheli has useful process levels (hotfix/spike/light/full) but zero AI-specific guardrails. SweetClaude TDD must be a new skill combining: real-tdd's philosophy + Superpowers' language agnosticism + Don Cheli's process levels + research-backed enforcement hooks.
**Source:** TDD Analysis (full comparison document)
**Impact:** Critical
**Effort:** High
**Why it matters:** TDD is the foundation of SweetClaude's development lifecycle. Getting it wrong undermines everything downstream.

### Insight 11: Lightweight Traceability Over Knowledge Graphs
**Description:** For a solo developer, a full knowledge graph (Neo4j) for artifact traceability is overkill. A structured markdown traceability file in the SweetClaude working repo — mapping requirements → Gherkin stories → tests → implementation — provides 80% of the value with zero infrastructure. The Gherkin bridge (Insight 2) combined with story-organized test files (Insight 10) creates a natural traceability chain without a separate database.
**Source:** Brainstorm discussion, architecture evaluation
**Impact:** Medium
**Effort:** Low
**Why it matters:** Avoids infrastructure complexity while maintaining the traceability chain from requirement to passing test.

### Insight 12: Dual Context Window Management
**Description:** SweetClaude manages two context windows simultaneously: Claude's (token limits, lazy loading, phase-scoped skills) and the human's (cognitive load, working memory, ability to hold details). The human context window is managed through deference levels, detour tracking, re-orientation summaries, decision logs, and assumption registers. Both constraints shape every design decision.
**Source:** Architecture session — observed that the human repeatedly needed re-orientation after detours, while Claude needed aggressive context pruning for different reasons.
**Impact:** Critical
**Effort:** Medium
**Why it matters:** Optimizing only for Claude's context window ignores half the problem. A system that's efficient for the machine but overwhelming for the human fails at partnership.

### Insight 13: Deference Levels — A Dial, Not a Switch
**Description:** User-declared autonomy setting governing how frequently SweetClaude stops for approval. Collaborative stops after every sub-step. Guided stops at phase gates and major decisions. Autonomous stops only at phase gates. Changeable mid-stream — early phases may need Collaborative, later phases Autonomous.
**Source:** Architecture session — Claude kept jumping ahead without approval, user corrected.
**Impact:** High
**Effort:** Low
**Why it matters:** Different work demands different pacing. Forcing one mode creates either approval hell or runaway execution.

### Insight 14: Phase Dwelling Over Phase Rushing
**Description:** The system should stay present in the current phase and never push advancement. Constant "is this complete?" and "ready to move on?" signals that iteration is delay rather than work. The user decides when a phase is done. The system's default posture is to deepen, not advance.
**Source:** Architecture session — Claude's constant approval-seeking pressured the user toward premature advancement.
**Impact:** Critical
**Effort:** Low
**Why it matters:** Rushing through phases to check boxes produces shallow work. Dwelling in phases produces insight. The best ideas in this session came from iterating on things Claude initially presented as "done."

### Insight 15: Context Continuity — Detour Management
**Description:** When conversation detours, the system must track where it branched, follow the detour, and proactively re-orient the user when the detour completes. Handles nested detours. The human brain cannot hold the full conversation tree — the system must.
**Source:** Architecture session — user had to ask "replay where we are" after multiple detours.
**Impact:** High
**Effort:** Medium
**Why it matters:** Without this, the human carries the cognitive burden of tracking conversation branches. That's the system's job.

### Insight 16: Continuous Improvement Register
**Description:** Per-project log of what's working and what's not in the collaboration itself. Populated after friction, after smooth stretches, and periodically. Not project decisions — interaction quality. Read by future sessions to improve behavior over time.
**Source:** Architecture session — discussion about whether positive feedback helps AI assistants.
**Impact:** High
**Effort:** Low
**Why it matters:** Without capturing what works (not just what fails), the system corrects past mistakes but drifts away from validated approaches. Both directions matter.

---

## Capability Inventory: What Stays, What Goes, What's New

### KEEP — From [removed]
- Brainstorm workflow (Creative Intelligence)
- Product Brief workflow (Business Analyst)
- PRD workflow (Product Manager)
- Tech Spec workflow (Product Manager)
- UX Design workflow (UX Designer)
- Architecture workflow (System Architect)
- Solutioning Gate Check (Architect)
- Create Story / Dev Story (Scrum Master / Developer)
- Sprint Planning (Scrum Master)
- Research workflow (Creative Intelligence)
- Workflow Status tracking
- Workflow Init

### KEEP — From Superpowers
- writing-plans / executing-plans
- dispatching-parallel-agents / subagent-driven-development
- using-git-worktrees
- systematic-debugging
- test-driven-development (as fallback; real-tdd overrides)
- requesting-code-review / receiving-code-review / code-reviewer agent
- verification-before-completion
- finishing-a-development-branch
- simplify
- writing-skills
- brainstorming (for quick technical brainstorming; [removed] for structured product brainstorming)

### KEEP (as input/inspiration) — Custom Skills
- real-tdd — philosophy, subagent separation, QA caucus, test immutability (to be rebuilt as SweetClaude TDD)
- fix-issue (end-to-end issue implementation)
- pr-ready (pre-PR quality gate)
- caucus (multi-expert deliberation)
- reasoning-frameworks (structured decision-making)
- backlog-management (deferred work tracking)
- reconciling-documents (spec conflict resolution)
- rag-index (semantic search setup)
- session-export (session portability)

### REMOVE — Don Cheli
- All 76 `/dc:*` commands
- All 76 `/especdev:*` duplicate commands
- All 15 `/razonar:*` commands (replaced by reasoning-frameworks)
- All 48 internal skills
- All 9 rules files
- All hooks
- Auto-update mechanism
- Templates, scripts, locales

### NEW — To Build
- **SweetClaude TDD skill** — New unified TDD skill combining real-tdd philosophy + Superpowers language agnosticism + process levels (hotfix/light/standard/full-from-Gherkin) + hook-based enforcement. See `docs/tdd-analysis-v1-2026-04-12.md` for full architecture.
- **`sweetclaude-init`** — Single-command project bootstrap (two repos, GitHub, Notion, RAG, CLAUDE.md generation)
- **Phase-aware skill router** — Tracks current phase, surfaces relevant capabilities
- **Gherkin bridge** — Formal transition from [removed] stories to `.feature` files to isolated test writer agent
- **Test file guardian hook** — PreToolUse hook that blocks ALL Write/Edit to test files during implementation phase. Highest-value single enforcement mechanism.
- **Auto-test runner hook** — PostToolUse hook that runs relevant tests after any source file edit. Feeds failures back to agent immediately.
- **Git checkpoint enforcement** — Auto-commit failing tests before implementation begins. `git diff` on test files during implementation = violation.
- **TDD process level selector** — Skill that evaluates task complexity and recommends appropriate TDD level (0-3). User confirms.
- **Security reviewer subagent** — Replaces Don Cheli's security-audit
- **Workflow guardian subagent** — GitHub Actions security review
- **Test runner subagent** — Isolated test execution with minimal output
- **QA caucus subagent trio** — 3 parallel subagents that stress-test test plans (service/API expert, component expert, integration/cross-cutting expert)
- **Auto-reindex hook** — RAG index stays fresh on file changes
- **Lean global CLAUDE.md** — 60-80 lines, universal rules only
- **Project CLAUDE.md generator** — Created during init from codebase discovery
- **Traceability tracker** — Structured markdown in working repo mapping requirements → Gherkin → tests → implementation

---

## SweetClaude Phase Model

```
Phase 1: DISCOVER     → Brainstorm, Research, Caucus, Reasoning Frameworks
Phase 2: DEFINE       → Product Brief, PRD, Competitive Analysis
Phase 3: DESIGN       → Tech Spec, UX Design, Architecture, Solutioning Gate
Phase 4: PLAN         → Stories → Gherkin .feature files, Sprint Planning, Backlog
Phase 5: IMPLEMENT    → SweetClaude TDD (level 0-3), fix-issue, Worktrees, Parallel Agents, Debugging
                         TDD enforcement: test file guardian hook, auto-test runner hook, git checkpoints
                         Context isolation: test writer agent ≠ implementer agent
Phase 6: VERIFY       → Code Review, Security Review, PR-Ready, Verification, Mutation Testing (optional)
Phase 7: SHIP         → Branch Finishing, CI/CD Gates, Deploy
Phase 8: MAINTAIN     → Backlog Management, Document Reconciliation, RAG Updates, Traceability Updates
```

**Phase 4→5 transition (the Gherkin bridge):**
```
[removed] Stories → Gherkin .feature files → Test Writer Agent (isolated) →
QA Caucus (3 subagents) → User Approval → Tests committed to git →
Implementer Agent (isolated, tests READ ONLY) → GREEN → Refactor
```

**TDD process levels (Phase 5):**
```
Level 0: HOTFIX    — Fix first, test in same session. No grace period.
Level 1: LIGHT     — Simple CRUD. Single-context RED-GREEN-REFACTOR.
Level 2: STANDARD  — Features/bugs. Subagent separation. Tests committed before impl.
Level 3: FULL      — From Gherkin. Full pipeline with QA caucus + mutation testing.
```

Each phase has:
- Entry criteria (previous phase outputs exist)
- Available skills/workflows for that phase
- Exit criteria (required outputs produced)
- Checkpoint (commit to SweetClaude working repo)
- Enforcement hooks active for that phase

---

## Statistics
- Total capabilities mapped: 65+
- Categories: 5 major branches
- Key insights: 16 (7 from initial brainstorm + 4 from TDD analysis + 5 from architecture session)
- Techniques applied: 3 (Mind Mapping, SCAMPER, Reverse Brainstorming) + deep research
- Sources analyzed: 4 systems (Superpowers, [removed], Don Cheli, Custom Skills) + web research (MSR '26, Anthropic, Fowler, NIST, DORA, multiple practitioner reports)

## Recommended Next Steps

This brainstorm output feeds directly into [removed]'s **Product Brief** workflow, where the Business Analyst agent will:
1. Formalize the problem statement and target user (solo developer workflow)
2. Define success criteria for SweetClaude
3. Identify MVP vs. future phases
4. Produce the brief that feeds into PRD and Tech Spec

Run: `/[removed]`

---

*Generated by [removed] Method v6 - Creative Intelligence*
