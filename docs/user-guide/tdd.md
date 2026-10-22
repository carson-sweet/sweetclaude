# TDD Levels

**Version:** 1.3
**Date:** 2026-10-21

SweetClaude does not believe in advisory TDD. Advisory TDD fails. The implementer touches the test to make it pass, or writes the test after the code so the test rationalizes the implementation rather than specifying behavior.

This page explains the four enforcement levels, what each one feels like to use, and the failure modes each one prevents.

---

## Why Hooks, Not Prompts

Most TDD documentation says "write the test first." SweetClaude says it too, and at the higher levels it adds hooks that block the shortcuts.

The mechanism is four Claude Code hooks:

- **test-guardian** (PreToolUse) blocks edits to test files during the IMPLEMENT phase, once `code-tdd` has set `tdd_phase` to implementing with `scripts/tdd_phase.py`. Not warns. Blocks.
- **tdd-prewrite-guardian** (PreToolUse) blocks source file writes during the IMPLEMENT phase while no test files exist, when the Protocol Guardian is on (`/sweetclaude:configure guardian-on`).
- **auto-test-runner** (PostToolUse) runs tests automatically after every source edit while `tdd_phase` is implementing. Not reminds. Runs.
- **tdd-commit-gate** (PreToolUse) denies a `git commit` that adds implementation source files on a story branch while a TDD cycle is active and the branch has no earlier `test: RED` commit.

The failing tests are committed with `git-checkpoint.sh`, which `code-tdd` runs at the end of the RED step, before implementation begins.

This sounds extreme until you watch what happens without it: a test passes, you ship, and three weeks later production breaks because the test was passing for the wrong reason. The hooks remove that failure mode. The cost is that you cannot quickly "fix" a test by editing it — and that cost is the whole point.

You can override test immutability with explicit user approval. The override is per file and logged: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tdd_phase.py release --file <path> --approval "<the user's words>"` unfreezes that one file and appends a `tdd_override` event naming the file and the approval to `.sweetclaude/metrics/events.log`. This is for the case where a test has a genuine defect, not a coverage gap. The two are different and the framework wants you to be deliberate about which one you are claiming.

---

## Level Selection

The right level depends on the work, not your preference. The framework picks based on work type and complexity, but you can always override.

| Situation | Level |
|---|---|
| Production hotfix | 0 |
| Simple CRUD, config change | 1 |
| Bug fix with clear scope | 1 or 2 |
| Feature with defined behavior | 2 |
| Feature with Gherkin specs | 3 |
| Complex feature, many edge cases | 3 |
| Refactoring existing code | 1 (but lock behavior with tests first) |

---

## Level 0: Hotfix

**When**: production is degraded, you need to fix it now.

**The discipline**: fix the immediate problem, write a regression test in the same session, confirm the test fails without the fix, then commit the test and the fix together. Not within 48 hours. Now.

**What it feels like**: pressure. The hotfix workflow shape (DIAGNOSE → IMPLEMENT → SHIP → POST-MORTEM) compresses everything except the regression test. You are not writing exhaustive coverage. You are writing the one test that would have caught this bug, after the fix, then reverting the fix to confirm the test fails without the fix, re-applying it, and committing the test and the fix together. POST-MORTEM follows as a separate work item. It is not optional.

**What it prevents**: the same bug shipping twice. Without the regression test, the next change in the area could re-introduce the failure. With it, the test fails immediately if anyone tries.

---

## Level 1: Light

**When**: simple additions, config, straightforward CRUD, small bug fixes. Single-context work where subagent isolation is overhead.

**The discipline**: write test → verify it is RED → implement → verify it is GREEN → refactor. All in one context. Tests still come first. Tests still confirmed RED before implementation.

**What it feels like**: normal TDD. You write a test, it fails for the right reason, you write code, it passes. The hooks are running but the work is small enough that you do not bump into them often.

**What it prevents**: writing the implementation first and then writing a test that matches what you already wrote. The RED check is the protection — if the test passes immediately, something is wrong. Either the behavior already exists, or the test is not actually testing the new behavior.

---

## Level 2: Standard

**When**: features, significant bug fixes, behavior changes. Work that benefits from subagent separation but does not justify the full Gherkin pipeline.

**The discipline**:

0. A story branch is created (`{ID}/{slug}`, e.g. `ISSUE-046/git-branch-discipline`) to isolate the work from main.
1. Failing tests are written in the main context, against interfaces designed first.
2. Tests are verified RED and committed to git.
3. `code-tdd` sets `tdd_phase` to implementing. Test-guardian hook activates — test files become immutable.
4. Implementer agent (a subagent in a separate context) makes tests pass with code.
5. Auto-test-runner hook fires after every source edit.

**What it feels like**: choreographed. You write the failing tests with Claude in the main context and commit them. You watch the implementer subagent iterate against them. The implementer never sees your reasoning about what the tests should cover — only the tests themselves.

**What it prevents**: the implementer rationalizing a poor test. If the implementer can read the spec or your notes, it can argue that a test "really means" something other than what it says. The implementer subagent is dispatched with the tests, not your notes. It has to make the actual tests pass with actual code.

---

## Level 3: Full (from Gherkin)

**When**: net-new features with user stories, complex behavior, production-critical paths.

**The discipline**: maximum isolation, full pipeline.

0. A story branch is created (`{ID}/{slug}`) before any test or implementation work begins.
1. **Gherkin specs** — user stories converted to `.feature` files with Given/When/Then scenarios.
2. **Test writer agent** — a subagent that reads Gherkin in an isolated context, writes failing test code, has no knowledge of planned implementation.
3. **QA Caucus** — three specialist agents review the test plan in parallel:
   - **Service/API expert**: tenant isolation, state transitions, concurrency, inter-service interactions.
   - **Component/UI expert**: accessibility, loading states, user interaction edge cases.
   - **Integration expert**: gaps between layers, optimistic UI vs server state, multi-tab scenarios, security bypasses.
4. **User approval** — review QA findings, approve or request additions.
5. **Implementer agent** — reads tests in an isolated context, no knowledge of Gherkin or test writer reasoning, makes tests pass with minimal code.
6. **Mutation testing** (optional) — verifies tests actually catch faults, not just pass.

**What it feels like**: deliberate. The pipeline takes longer than feature development without it because four agents and three review angles are sequenced. The output is a feature where you can articulate why the tests cover what they cover, who reviewed each angle, and what the implementer did and did not have visibility into.

**What it prevents**: every failure mode the lower levels prevent, plus coverage blindness (the QA Caucus catches angles a single reviewer misses) and rationalization through spec-reading (the implementer never sees the spec).

---

## What "No Mocks by Default" Means

Real dependencies. Real databases. Real function calls. Mocking is not the default at any TDD level.

The reason is that mock/implementation divergence is how passing tests mask broken production behavior. A test that mocks the database and passes proves nothing about whether the real database accepts the query. A test that mocks the external API and passes proves nothing about whether the real API behaves as expected.

If a test requires a mock, the reason must be explicit. External services with rate limits, expensive operations, or non-deterministic behavior are reasonable cases. "Mocking is faster" is not.

---

## What the Hooks Catch

Concrete failure modes the hooks block:

| Without hooks | With hooks |
|---|---|
| Implementer edits a test to make it pass | test-guardian blocks the edit at the tool call level once `tdd_phase` is implementing |
| Tests fail silently and ship | auto-test-runner runs after every source edit; failure is immediate |
| Test writer's intent gets lost between sessions | the failing tests are committed with `git-checkpoint.sh` before implementation begins |
| Spec gets reverse-engineered from passing implementation | the implementer subagent is dispatched without the spec (instruction-guided, not a hook) |

If you disable the hooks, you also disable these protections. The framework still nominally tracks TDD level, but Level 2-3 without the hooks is approximately Level 1 in practice.

---

## Subagents Available

These run inside the TDD pipeline. You do not invoke them directly.

| Agent | Role |
|---|---|
| `sweetclaude:test-writer` | Writes failing tests from Gherkin or acceptance criteria. No knowledge of planned implementation. |
| `sweetclaude:implementer` | Makes failing tests pass with minimal code. No knowledge of specs or test writer reasoning. |
| `sweetclaude:qa-caucus-service` | Reviews test plan for service/API coverage gaps. |
| `sweetclaude:qa-caucus-component` | Reviews test plan for UI/component coverage gaps. |
| `sweetclaude:qa-caucus-integration` | Reviews test plan for cross-cutting and integration coverage gaps. |
| `sweetclaude:code-reviewer` | Adversarial code review post-implementation. |
| `sweetclaude:security-reviewer` | Security-focused code review. |
| `sweetclaude:workflow-guardian` | GitHub Actions workflow security review. |

---

## Anti-Patterns

Things SweetClaude will catch you doing if you try them:

**Editing a failing test to make it pass.** The test-guardian hook blocks the edit. If you genuinely need to fix a defective test, release that one file with `tdd_phase.py release` and explicit approval — and that override is logged.

**Writing tests after implementation.** The framework checkpoints failing tests before implementation begins. If you try to commit implementation without prior failing tests, the workflow refuses to advance: while a TDD cycle is active on a story branch, the `tdd-commit-gate` hook denies the `git commit` until the branch carries a `test: RED` commit. Level 0 hotfixes never set the cycle marker, so committing the test and the fix together stays allowed.

**Mocking the database to "make tests faster".** No mocks by default. If you mock, the reason is explicit and reviewed.

**"I'll write the regression test later"** for hotfixes. Level 0 is "in this session, not within 48 hours." Later does not happen.

**Skipping the QA Caucus** for Level 3. The Caucus is the part most likely to catch coverage angles you missed. Skipping it negates most of the value of running Level 3.

**Asking the implementer agent for guidance about the spec.** It cannot answer. It has not seen the spec. Ask the test writer or the user.

---

## What to Read Next

- The reasoning behind hook-based enforcement → [How It Works](how-it-works.md)
- A concrete walkthrough of Level 3 end-to-end → [Walkthroughs](walkthroughs.md#6-building-one-feature-with-full-tdd)
- Phase exit criteria for IMPLEMENT and VERIFY → [Phases and Workflows](phases-and-workflows.md)
