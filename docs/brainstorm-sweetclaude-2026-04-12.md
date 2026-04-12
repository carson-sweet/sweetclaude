# Brainstorming Session: SweetClaude

**Date:** 2026-04-12
**Objective:** Define a unified Claude Code framework (SweetClaude) that combines the best of Superpowers, BMAD, Don Cheli, and custom skills into a single end-to-end platform for RAG-powered knowledge work and disciplined TDD development — from initial concept through fully tested, deployed code.

**Context:**
- Solo developer, fast-paced, broad project spectrum (web apps, microservices, CLIs, APIs, utilities)
- No single language/framework — must be generic
- Follows a deliberate progression: concept → competitive landscape → functional definition → architecture → code
- Three existing systems (Superpowers, BMAD, Don Cheli) with significant overlap and friction
- Custom skills that fill real gaps and should be preserved
- Two core problems: (1) large-corpus knowledge work beyond Claude.ai limits, (2) end-to-end TDD lifecycle

## Techniques Used
1. Mind Mapping — full capability inventory across all sources
2. SCAMPER — creative recombination of existing tools
3. Reverse Brainstorming — failure mode analysis

---

## Key Insights

### Insight 1: The Pipeline Is the Product
**Description:** SweetClaude isn't a collection of skills — it's a pipeline with explicit phases and gates. The user's natural workflow (concept → landscape → functional def → architecture → code) maps directly onto BMAD's agent progression (Creative Intelligence → Business Analyst → Product Manager → System Architect → Developer). Each phase has entry criteria, exit criteria, and defined outputs that feed the next phase.
**Source:** Mind mapping (Branch 2 + Branch 3), SCAMPER (Combine), Reverse Brainstorming (#2 phase confusion)
**Impact:** High
**Effort:** Medium
**Why it matters:** Without explicit phases, Claude mixes concerns — starts coding during brainstorming, starts architecting during implementation. The pipeline prevents this.

### Insight 2: Gherkin Is the Bridge Between Worlds
**Description:** The transition from product definition to development is the hardest handoff. Gherkin acceptance criteria (Given/When/Then) serve as the contract between BMAD's product phase and the TDD implementation phase. BMAD stories → Gherkin AC → `real-tdd` red tests → implementation. This is the core innovation of SweetClaude.
**Source:** Mind mapping (Branch 2 → Branch 3 gap), SCAMPER (Combine)
**Impact:** High
**Effort:** Medium
**Why it matters:** Without this bridge, product specs and code diverge. With it, every behavior is traceable from user need to passing test.

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
- **BMAD** owns the product lifecycle (brainstorm → brief → PRD → spec → architecture → stories → sprints)
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

---

## Capability Inventory: What Stays, What Goes, What's New

### KEEP — From BMAD
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
- brainstorming (for quick technical brainstorming; BMAD for structured product brainstorming)

### KEEP — Custom Skills
- real-tdd (overrides Superpowers TDD)
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
- **`sweetclaude-init`** — Single-command project bootstrap (two repos, GitHub, Notion, RAG, CLAUDE.md generation)
- **Phase-aware skill router** — Tracks current phase, surfaces relevant capabilities
- **Gherkin bridge** — Formal transition from BMAD stories to real-tdd test cases
- **Security reviewer subagent** — Replaces Don Cheli's security-audit
- **Workflow guardian subagent** — GitHub Actions security review
- **Test runner subagent** — Isolated test execution with minimal output
- **Auto-reindex hook** — RAG index stays fresh on file changes
- **Lean global CLAUDE.md** — 60-80 lines, universal rules only
- **Project CLAUDE.md generator** — Created during init from codebase discovery

---

## SweetClaude Phase Model

```
Phase 1: DISCOVER     → Brainstorm, Research, Caucus, Reasoning Frameworks
Phase 2: DEFINE       → Product Brief, PRD, Competitive Analysis
Phase 3: DESIGN       → Tech Spec, UX Design, Architecture, Solutioning Gate
Phase 4: PLAN         → Stories (with Gherkin AC), Sprint Planning, Backlog
Phase 5: IMPLEMENT    → real-tdd, fix-issue, Worktrees, Parallel Agents, Debugging
Phase 6: VERIFY       → Code Review, Security Review, PR-Ready, Verification
Phase 7: SHIP         → Branch Finishing, CI/CD Gates, Deploy
Phase 8: MAINTAIN     → Backlog Management, Document Reconciliation, RAG Updates
```

Each phase has:
- Entry criteria (previous phase outputs exist)
- Available skills/workflows for that phase
- Exit criteria (required outputs produced)
- Checkpoint (commit to SweetClaude working repo)

---

## Statistics
- Total capabilities mapped: 65+
- Categories: 5 major branches
- Key insights: 7
- Techniques applied: 3
- Sources analyzed: 4 (Superpowers, BMAD, Don Cheli, Custom Skills)

## Recommended Next Steps

This brainstorm output feeds directly into BMAD's **Product Brief** workflow, where the Business Analyst agent will:
1. Formalize the problem statement and target user (solo developer workflow)
2. Define success criteria for SweetClaude
3. Identify MVP vs. future phases
4. Produce the brief that feeds into PRD and Tech Spec

Run: `/bmad:product-brief`

---

*Generated by BMAD Method v6 - Creative Intelligence*
