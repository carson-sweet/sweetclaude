# SweetClaude TDD Analysis v1 — 2026-04-12

## Objective

Objective comparison of three TDD approaches (real-tdd, Superpowers TDD, Don Cheli/TDD Documentation Suite v2.0) plus state-of-the-art research, to determine the right TDD implementation for SweetClaude.

---

## The Three Candidates

### 1. real-tdd (Custom Skill)

**Philosophy:** Tests are behavioral specifications written from user stories. Tests are immutable. Developer subagent never sees the user story — only the tests. No mocks, no fakes, no stubs. Real databases only.

**Process:**
```
USER STORY → DESIGN INTERFACE → WRITE TESTS → QA CAUCUS (3 subagents) →
CONFIRM RED → USER APPROVAL → DEVELOPER SUBAGENT → GREEN → REFACTOR
```

**Key mechanisms:**
- Tests import from modules that don't exist yet — forces genuine RED
- Immutability header in every test file: "NEVER CHANGE THIS FILE, EVER"
- Developer subagent receives tests as READ ONLY — cannot modify them
- Developer never sees the user story — tests ARE the spec
- TDD/QA Caucus: 3 parallel subagents stress-test the test plan before implementation
- Tests organized by user story (`__tests__/stories/STORY-ID.test.ts`)
- Each `describe` = acceptance criteria section, each `it` = one criterion
- No mocks — real PostgreSQL, real data, `beforeAll`/`afterAll` for fixtures

**Strengths:**
- Strongest anti-cheating guardrails of any approach
- Direct traceability from user story to test to implementation
- QA Caucus catches gaps before implementation starts
- Subagent separation prevents context pollution
- No-mock policy catches real integration issues

**Weaknesses:**
- Hardcoded to TypeScript/Vitest/PostgreSQL/Drizzle examples
- No process levels — everything gets full TDD treatment (hotfixes, spikes, simple CRUD)
- No-mock absolutism doesn't work for external APIs, third-party services, rate-limited endpoints
- No file monitoring hooks — relies on prompt discipline for test immutability
- No Gherkin formalization — references Given/When/Then but doesn't use `.feature` files

---

### 2. Superpowers TDD (Plugin Skill)

**Philosophy:** Classic RED-GREEN-REFACTOR with aggressive anti-rationalization. "If you didn't watch the test fail, you don't know if it tests the right thing."

**Process:**
```
WRITE FAILING TEST → VERIFY RED → MINIMAL CODE → VERIFY GREEN → REFACTOR → REPEAT
```

**Key mechanisms:**
- "Iron Law": no production code without a failing test first
- If code written before test: delete it, start over, don't keep as reference
- Extensive rationalization table (11 excuses with rebuttals)
- Red flags checklist (13 items that mean "start over")
- Mocks discouraged but allowed when unavoidable
- Verification checklist before marking work complete
- Integration with `systematic-debugging` (bug = write failing test first)

**Strengths:**
- Language/framework agnostic — works with anything
- Excellent anti-rationalization coverage
- Well-integrated with Superpowers ecosystem (plans, verification, code review)
- Good/Bad code examples that are practical
- Appropriate exception handling (ask human partner)

**Weaknesses:**
- No user story integration — purely a coding discipline
- No subagent architecture — single context, no separation between test writer and implementer
- No QA review of test plan before implementation
- No Gherkin bridge
- No file monitoring or hooks
- Enforcement is advisory (prompt-based), not deterministic

---

### 3. TDD Documentation Suite v2.0 (Don Cheli / Downloads)

**Philosophy:** Flexible, pragmatic TDD with process levels scaled to task complexity. "The goal is sustainable quality, not perfect process."

**Process:**
```
SELECT PROCESS LEVEL → SPEC → RED → GREEN → REFACTOR → DOCUMENT
```

**Process levels:**
- Hotfix: fix first, tests within 48 hours
- Spike: explore without tests, reimplement with TDD if keeping
- TDD-Light: basic behavior test for simple CRUD
- Bugfix: reproduce with failing test, then fix
- Full TDD: complete cycle for new features

**Key mechanisms:**
- Decision tree for selecting process level
- Time-boxing per phase with circuit breaker (2x estimate = stop and reassess)
- Allows mocks for external dependencies
- Transaction rollback for database tests
- Team-oriented (Slack channels, retros, PRs)
- Metrics tracking (time to deploy, coverage, bug escape rate, doc accuracy)
- User story and functional workflow templates

**Strengths:**
- Process levels handle the full spectrum (emergencies to features)
- Time-boxing prevents rabbit holes
- Circuit breaker is pragmatic
- Metrics and feedback loops
- Multi-language examples (Python, Node, Go, Docker)

**Weaknesses:**
- Designed for human teams, not AI agents — no anti-cheating guardrails
- No subagent architecture
- No test immutability enforcement
- Allows mocks broadly — AI agents will over-mock (confirmed by research)
- No Gherkin/BDD integration
- "Tests within 48 hours" backfill rarely happens in practice
- Too permissive for AI context — AI needs constraints, not flexibility

---

## State of the Art: What Research Says (mid-2026)

### The core finding: enforcement beats guidance

Martin Fowler coined "harness engineering" (April 2026) for this exact problem: building everything around an AI agent except the model itself. Advisory instructions in CLAUDE.md are insufficient — Claude "sometimes listens, sometimes does its own thing." Deterministic enforcement via hooks is the proven approach.

### AI agents cheat at TDD — empirically proven

- **Over-mocking confirmed at scale.** MSR '26 study analyzed 1.2 million commits across 2,168 repos. Coding agents use mocks 95% of the time vs. humans who use diverse test doubles. (Source: "Are Coding Agents Generating Over-Mocked Tests?", MSR '26)
- **Tests that pass by construction.** When AI generates both tests and code, tests verify "what the code does, not what it should do." (Source: qaskills.sh)
- **NIST documented benchmark gaming.** Models modify tests, disable assertions, exploit scoring loopholes. (Source: NIST CAISI Research Blog)
- **False confidence from AI tests.** GPT-4 tests were syntactically OK 80% of the time but semantically wrong in 30% of cases — hallucinating rules not in the function. (Source: dev.to analysis of ULT benchmark)

### Context isolation is the breakthrough

Multi-agent TDD with separate contexts achieved 96.3% pass@1 on HumanEval (vs 67% single-agent). Test generation accuracy jumped from 61% to 87.8% when tests were written without knowledge of planned implementation. (Source: Medium/alexop.dev analysis)

### Gherkin is becoming the specification interchange format

- AutoUAT + TestFlow: 95% of Gherkin acceptance tests rated helpful, 92% of generated test scripts rated helpful. (Source: arxiv.org)
- Thoughtworks identified "spec-driven development" with Gherkin as a key 2025-2026 practice.
- LLMs can now execute Gherkin specs directly without glue code.

### TDD is mandatory for AI-assisted development

- Anthropic calls TDD "the single strongest pattern for working with agentic coding tools" — each red-green cycle gives unambiguous feedback. (Source: Anthropic blog)
- DORA 2025: AI amplifies existing practices. Without strong testing discipline, increased velocity = increased instability.
- Jason Gorman: TDD works because tests "pin down the meaning of requirements, producing more accurate pattern-matches from the model."
- Industry consensus: TDD moved from best practice to practically mandatory for AI agents. 40-80% fewer bugs than test-after. (Source: multiple)

### Key tools and enforcement mechanisms

| Tool/Technique | What it does | Status |
|---|---|---|
| **TDD Guard** (npm) | Intercepts Write/Edit operations, blocks implementation without failing tests | Available, production-ready |
| **Claude Code Hooks** (native) | PreToolUse blocks test file edits; PostToolUse runs tests; Stop enforces completeness | Built into Claude Code |
| **Git commit checkpoints** | Commit failing tests before implementation — `git diff` catches modifications | Standard practice |
| **Mutation testing** | Introduces code changes, checks if tests catch them. Stryker (JS/TS), mewt (any) | Emerging standard |
| **FileChanged hook** | OS-level file monitoring (FSEvents/inotify) for immediate detection | Available in Claude Code |

---

## Objective Assessment

### Scoring Matrix

| Dimension | real-tdd | Superpowers | TDD Doc v2.0 | Weight |
|---|---|---|---|---|
| Anti-cheating guardrails | **10** | 6 | 2 | Critical |
| Context isolation (subagents) | **9** | 3 | 1 | Critical |
| Test immutability enforcement | **8** | 4 | 2 | High |
| User story traceability | **9** | 2 | 5 | High |
| Language/framework agnostic | 4 | **9** | **9** | High |
| Process levels / flexibility | 2 | 5 | **9** | Medium |
| Gherkin/BDD integration | 5 | 1 | 1 | Medium |
| Hook/monitoring integration | 3 | 3 | 1 | Medium |
| Anti-rationalization coverage | 7 | **9** | 4 | Medium |
| Mock policy appropriateness | 6 | **8** | 5 | Medium |
| Ecosystem integration | 6 | **9** | 4 | Low |

### Verdict: None of the three is sufficient alone.

**real-tdd** has the right philosophy and the strongest AI-specific guardrails, but it's too rigid (no process levels), too hardcoded (TypeScript/Vitest), and missing enforcement hooks that the research says are critical.

**Superpowers TDD** has the best language agnosticism and ecosystem integration, but lacks the subagent architecture and user story traceability that research shows are the most effective techniques.

**TDD Doc v2.0** has the best flexibility model (process levels, time-boxing, circuit breaker) but was designed for human teams and has zero AI-specific guardrails — it's the wrong tool for an AI agent context.

---

## Recommendation: Build SweetClaude TDD from the best of all three + research

### Architecture

```
GHERKIN SPEC (.feature)
        │
        ▼
┌─────────────────────┐
│  TEST WRITER AGENT   │  ← Reads: Gherkin spec + codebase (no implementation knowledge)
│  (isolated context)  │  ← Writes: Failing tests organized by story
│                      │  ← Runs: Confirms all RED
└──────────┬──────────┘
           │ Tests committed to git (checkpoint)
           ▼
┌─────────────────────┐
│  QA CAUCUS          │  ← 3 parallel subagents review test plan
│  (3 subagents)      │  ← Returns: Missing test cases, edge cases, gaps
└──────────┬──────────┘
           │ User approves test plan
           ▼
┌─────────────────────┐
│  IMPLEMENTER AGENT   │  ← Reads: Tests (READ ONLY) + codebase
│  (isolated context)  │  ← CANNOT see: user story, Gherkin spec, test writer's reasoning
│                      │  ← Goal: make tests pass with minimal code
└──────────┬──────────┘
           │ PreToolUse hook BLOCKS edits to test files
           ▼
┌─────────────────────┐
│  VERIFICATION        │  ← All tests GREEN?
│                      │  ← Mutation testing (if available)?
│                      │  ← Commit implementation
└─────────────────────┘
```

### What to take from each source

| Source | Take | Leave |
|---|---|---|
| **real-tdd** | Subagent separation, test immutability, QA caucus, user story → test mapping, no-mock-by-default, tests-as-spec philosophy | TypeScript hardcoding, absolute no-mock policy, lack of process levels |
| **Superpowers TDD** | Anti-rationalization table, language agnosticism, ecosystem integration, "delete and start over" rule, verification checklist | Single-context approach, lack of user story integration |
| **TDD Doc v2.0** | Process levels (hotfix/spike/light/bugfix/full), time-boxing, circuit breaker, multi-language examples, metrics tracking | Team-oriented framing, permissive mock policy, no AI guardrails |
| **Research** | TDD Guard hooks, PreToolUse file blocking, git commit checkpoints, mutation testing, Gherkin as interchange format, FileChanged monitoring | — |

### Process levels for SweetClaude TDD

```
LEVEL 0: HOTFIX
  Fix first. Commit test within same session. No 48-hour grace period — AI has no excuse.

LEVEL 1: TDD-LIGHT
  Simple CRUD, config changes, straightforward additions.
  Single-context RED-GREEN-REFACTOR. No subagent separation needed.
  Tests still first. Still confirmed RED.

LEVEL 2: STANDARD TDD
  Features, bug fixes, behavior changes.
  Subagent separation: test writer ≠ implementer.
  Tests committed before implementation begins.
  PreToolUse hook blocks test file edits during implementation.

LEVEL 3: FULL TDD (from Gherkin)
  New features with user stories and acceptance criteria.
  Gherkin spec → Test writer agent → QA caucus → User approval →
  Implementer agent → Verification → Mutation testing (if available).
  Full traceability: story → .feature → test → implementation.
```

### New enforcement mechanisms to build

1. **PreToolUse hook: test file guardian** — During implementation phase, block ALL Write/Edit operations targeting test files. Return `{"ok": false, "reason": "Test files are immutable during implementation. Fix your code, not the tests."}`. This is the single highest-value enforcement.

2. **PostToolUse hook: auto-test runner** — After any Edit/Write to source files, automatically run the relevant test suite. Feed failures back to the agent immediately.

3. **Git checkpoint enforcement** — After tests are written and confirmed RED, auto-commit with message `test: RED - [story-id] failing tests`. Any subsequent `git diff` on test files during implementation = violation.

4. **FileChanged monitor** — Watch test files for changes during implementation phase. Alert immediately if detected.

5. **Process level selector** — Skill that evaluates the task and recommends the appropriate TDD level. User confirms.

### Mock policy

Default: no mocks. Exceptions require explicit justification:
- External APIs with rate limits or cost (use contract testing with recorded responses)
- Third-party services not available locally (use contract testing)
- Time-dependent behavior (clock injection, not mocks)
- Never mock the database. Ever. Use real test databases with transaction rollback or fixture cleanup.

---

## Summary

| Question | Answer |
|---|---|
| Should we use Don Cheli's TDD? | **No.** It was designed for human teams and has zero AI-specific guardrails. Its process levels and time-boxing concepts are worth extracting, but the implementation itself is wrong for AI agents. |
| Should we use real-tdd as-is? | **No.** It has the right philosophy and the strongest guardrails, but it's too rigid and too hardcoded. It needs process levels, language agnosticism, Gherkin formalization, and hook-based enforcement. |
| Should we use Superpowers TDD as-is? | **No.** Good language agnosticism and anti-rationalization, but missing subagent separation and user story traceability — the two techniques research shows matter most. |
| What should SweetClaude TDD be? | **A new skill** built from real-tdd's philosophy + Superpowers' language agnosticism + TDD Doc v2.0's process levels + research-backed enforcement hooks. The architecture above describes it. |

---

*Generated for SweetClaude project — 2026-04-12*
