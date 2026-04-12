# Product Brief: SweetClaude v1 — 2026-04-12

**Author:** Carson Sweet
**Status:** Approved
**Project type:** Open-source framework (non-commercial license)

---

## 1. Executive Summary

SweetClaude is an open-source (non-commercial license) Claude Code framework that combines RAG-powered knowledge work with a disciplined, end-to-end TDD development lifecycle — from initial concept through fully tested, deployed code. It merges the best capabilities of Superpowers, BMAD, and purpose-built skills into a single phase-gated platform that can bootstrap any project type with one command. SweetClaude is a creative partner, not a passive executor — it soundboards ideas, challenges assumptions, introduces alternatives, and actively contributes to the thinking, not just the typing. Built by a solo developer for solo developers, shared with the community — not for corporate extraction.

---

## 2. Problem Statement

**Problem:** Claude Code is powerful but fragmented. Developers cobble together plugins (Superpowers, Don Cheli, BMAD), custom skills, and ad-hoc CLAUDE.md rules that overlap, conflict, and bloat the context window. There's no unified framework that takes a project from concept through tested code using a coherent, disciplined pipeline. TDD enforcement is especially broken — existing tools either lack AI-specific guardrails or are too rigid and hardcoded to one stack.

**Why now:** AI-assisted development has hit an inflection point where, per DORA 2025, AI amplifies existing practices — teams without discipline ship instability faster. The tooling ecosystem is mature enough (hooks, subagents, MCP, Gherkin bridges) to build a real framework, not just a skill collection.

**Impact if unsolved:** Developers continue assembling fragile tool stacks that overlap, conflict, and degrade Claude's performance. TDD discipline remains advisory — Claude cheats, modifies tests, over-mocks, and ships code that passes tests but misses bugs. Projects lack traceability from requirement to implementation. Every new project starts from scratch.

---

## 3. Target Audience

**Primary users:** Solo developers using Claude Code who build across a broad spectrum — web apps, microservices, CLIs, APIs, utilities — with no single language or framework. They work fast but want discipline. They follow a deliberate progression from concept through architecture before touching code.

**Secondary users:** Small teams (2-3 devs) who want a shared development framework with built-in quality gates. Also, developers new to TDD who want enforced discipline rather than advisory guidance.

**Top user needs:**
1. A single, coherent framework that eliminates plugin overlap and conflict
2. TDD enforcement that actually prevents AI cheating — not advisory, deterministic
3. Zero-friction project bootstrap that sets up everything with one command

---

## 4. Solution Overview

**Proposed solution:** A single installable Claude Code framework with:

**Core features:**
- Phase-gated pipeline (Discover → Define → Design → Plan → Implement → Verify → Ship) with entry/exit criteria and enforcement
- Work-type routing — SweetClaude identifies the type of work (net-new feature, bug fix, feature enhancement, iteration) and enters the pipeline at the appropriate phase:
  - Net-new features: full pipeline from Discover
  - Bug fixes, enhancements, iterations: enter at Define, escalate to Discover if deeper issues surface
- Gherkin bridge that formally transitions product stories into TDD test specs via isolated subagents
- Four-level TDD with hook-based enforcement (test file guardian, auto-test runner, git checkpoints)
- RAG-powered knowledge layer (semantic search + Notion + git history, loaded on demand)
- One-command project bootstrap (`sweetclaude init`) creating dual repos, GitHub, Notion scaffold (optional), RAG index, and auto-generated CLAUDE.md
- Phase-aware skill surfacing — only relevant capabilities shown for the current phase
- Configurable model routing — rules for which model handles which tasks, with user-defined config and default fallback (e.g., Haiku for test runs, Sonnet for code review, Opus for architecture)
- Ripple-effect analysis — before implementing a change, automatically trace dependencies, tests, APIs, and consumers, and present impact assessment
- Automatic documentation updates — when implementation changes behavior, auto-update relevant docs as part of verification
- Lightweight traceability (requirements → Gherkin → tests → code) via structured markdown, no infrastructure overhead
- Mutation testing as verification layer
- Creative partnership — actively soundboards, challenges, and introduces ideas, not just executes
- Decision log — captures what was decided and why at each phase transition, not just what was produced
- Assumption register — SweetClaude explicitly surfaces its assumptions for user challenge
- "Propose and invite challenge" interaction — SweetClaude proposes, user pushes back, faster than Q&A
- Adaptive flow — detects when user is driving or redirecting, follows without resistance
- Phase re-entry — revisiting earlier phases is normal and expected, not exceptional
- Scope change tracking — logs when items move between in/out of scope with rationale
- Mid-stream work-type detection — recognizes when the nature of work shifts and adapts
- Dual context window management — manages Claude's token limits AND the human's cognitive load simultaneously; machine context via lazy loading, human context via deference levels, re-orientation, and persistent logs
- Deference levels — user-declared autonomy setting (Collaborative/Guided/Autonomous) governing checkpoint frequency, changeable mid-stream
- Phase dwelling — system stays present in current phase, never pushes advancement; user decides when to move on
- Continuous improvement register — per-project log of what's working and what's not in the collaboration itself; read by future sessions

**Value proposition:** Stop assembling a Frankenstein of plugins. Start a project, tell SweetClaude what you're building, and it walks with you through every phase — doing the grind work for you with the right tools, enforced discipline, and full traceability — concept to deployed, tested code. It thinks with you, not for you, but remains creative and will challenge your ideas — in a healthy, productive way.

---

## 5. Project Goals

**Goals:**
- Release a usable v1.0 internal build today (2026-04-12)
- Establish SweetClaude as the reference framework for disciplined AI-assisted TDD development
- Build a contributor community around the non-commercial open-source model
- Achieve adoption by solo developers and small teams after public release

**Success metrics:**
- GitHub stars and forks
- Number of projects bootstrapped with `sweetclaude init`
- Community contributions (PRs, skills, issues)
- Developer feedback on TDD enforcement effectiveness (does it actually prevent AI cheating?)

**Value:** Gives every solo developer access to the same structured, disciplined, creative development pipeline that previously required assembling 3+ tools and extensive customization.

---

## 6. Scope

### In scope (v1.0)
- Lean global CLAUDE.md (~60-80 lines)
- SweetClaude TDD skill with all four process levels and hook-based enforcement
- Gherkin bridge skill (BMAD stories → .feature files → isolated test writer → QA caucus)
- Phase-aware skill router with entry/exit criteria
- `sweetclaude init` project bootstrap (dual repos, GitHub, CLAUDE.md generation)
- Test file guardian hook (PreToolUse blocks test edits during implementation)
- Auto-test runner hook (PostToolUse runs tests after source edits)
- RAG index setup per project
- Notion integration (optional — enabled during init if user wants it)
- Mutation testing as verification layer
- Configurable model routing (user-defined rules with default fallback model)
- Integration with existing Superpowers and BMAD plugins (upstream dependencies, not forks)
- Security reviewer and workflow guardian subagents
- Traceability tracker (structured markdown)
- Ripple-effect analysis skill
- Automatic documentation updates
- Creative partner behavior embedded across all phases

### Out of scope (v1.0) — Future
- **`sweetclaude adopt`** — Drop SweetClaude into an existing (likely vibe-coded) codebase. Unlike `init`, this requires a full assessment/recovery process: (1) ASSESS — full codebase scan for structure, test coverage, dependency map, pattern consistency, dead code, security surface; (2) DIAGNOSE — report on health, debt, danger zones, uncovered code; (3) PLAN — prioritized remediation plan: stabilize first, add tests to lock behavior before changing anything, document before knowledge is lost; (4) SCAFFOLD — set up working repo, CLAUDE.md, RAG index, traceability baseline from what exists; (5) ITERATE — user works through remediation using the iteration lifecycle. Key principle: treat an adopted codebase like an archaeologist treats a dig site, not a demolition crew.
- Automatic boilerplate implementation (e.g., Google OAuth for web apps, JWT for microservices) — needs a template library mapping project types to expected components, plus skills to implement each
- Multi-developer / team workflows
- IDE integrations beyond Claude Code CLI
- Auto-update mechanism
- Marketplace distribution as a Claude Code plugin
- Community skill library

---

## 7. Stakeholders

- **Carson Sweet (Creator)** — High influence. Primary user, architect, and maintainer.
- **Solo developer community** — Medium influence. Target users whose adoption and feedback drive the project's direction.
- **Small team early adopters (2-3 devs)** — Low influence. Secondary users who validate multi-user applicability in future phases.
- **BMAD / Superpowers maintainers** — Low influence. Upstream dependencies — SweetClaude integrates with their plugins as a good citizen, not a fork or derivative.

---

## 8. Constraints and Assumptions

**Constraints:**

- Must work within Claude Code's native extension model (skills, hooks, subagents, MCP) — no custom runtime or binary
- Must be language/framework agnostic — no hardcoding to a specific stack
- Non-commercial license — limits certain distribution channels but aligns with community values
- Context window is a hard physical limit — everything must be lazy-loaded and lean
- Solo maintainer at launch — scope must be achievable by one person

**Assumptions:**
- Users have Claude Code installed and a working Claude API subscription
- Users have GitHub accounts and `gh` CLI authenticated
- Users are comfortable with terminal-based workflows
- Superpowers and BMAD plugins remain available and maintained upstream
- Claude Code's hook, skill, and subagent APIs remain stable

---

## 9. Success Criteria

- A developer installs SweetClaude and runs `sweetclaude init` on a new project in under 5 minutes with zero manual configuration
- The developer is talked through a guided process — concept discovery, refinement, definition, design, planning, implementation, verification, shipping, bug fixes, enhancement, and iteration
- The TDD enforcement actually prevents AI cheating — tests are never silently modified during implementation
- The phase pipeline feels natural, not bureaucratic — it guides without slowing you down
- SweetClaude acts as a creative partner, not a passive executor — it soundboards ideas, challenges assumptions, introduces alternatives, and actively contributes to the thinking, not just the typing
- Projects bootstrapped with SweetClaude produce measurably higher-quality code (fewer bugs, better test coverage) than ad-hoc Claude Code usage
- The community adopts it, contributes skills, and it becomes the reference framework for disciplined AI-assisted development

---

## 10. Timeline

- **v1.0 internal release:** 2026-04-12 (today)
- **Future milestones:** TBD based on v1.0 usage and feedback

---

## 11. Risks

- **Risk:** ~~Scope is ambitious for a single-day v1.0~~ **RETIRED.** All three tiers (34 files) were built in ~30 minutes. Traditional scope estimates do not apply to AI-assisted solo development. SweetClaude should never discourage ambition with time-based anxiety.

- **Risk:** Upstream dependencies (Superpowers, BMAD) change or break compatibility
  - **Likelihood:** Low
  - **Mitigation:** Pin to known versions. SweetClaude orchestrates, doesn't fork — upstream changes are isolated.

- **Risk:** TDD enforcement hooks add friction that slows development instead of helping
  - **Likelihood:** Medium
  - **Mitigation:** Process levels (0-3) let you dial enforcement up or down. Dogfood immediately.

- **Risk:** Context window bloat from too many skills/hooks loaded at once
  - **Likelihood:** Medium
  - **Mitigation:** Phase-aware routing and lazy loading are core design requirements, not nice-to-haves.

- **Risk:** Community doesn't adopt because non-commercial license is too restrictive
  - **Likelihood:** Low
  - **Mitigation:** Non-commercial is the right call for the values. The audience that matters will respect it.

---

## 12. Licensing

**SweetClaude:** Non-commercial open-source license (exact license TBD — candidates: CC BY-NC-SA 4.0, Polyform NonCommercial)

**Upstream dependencies (integrated, not forked):**
| Dependency | License | Obligations |
|---|---|---|
| Superpowers | MIT | Include copyright notice |
| BMAD | MIT | Include copyright notice. Don't use "BMAD" trademark. |
| Gherkin/Cucumber | MIT | Include copyright notice. Don't use "Cucumber" name/logo. |
| Don Cheli | Apache 2.0 | Keep attribution if any code used. Mark modifications. (Concepts only — no code taken.) |

---

## Supporting Documents

- Brainstorm: `/Users/carsonsweet/dev/sweetclaude/docs/brainstorm-sweetclaude-2026-04-12.md`
- TDD Analysis: `/Users/carsonsweet/dev/sweetclaude/docs/tdd-analysis-v1-2026-04-12.md`
- Environment Audit: `/Users/carsonsweet/dev/sweetclaude/audit/2026-04-08-environment-audit.md`

---

*Generated by BMAD Method v6 — Business Analyst*

