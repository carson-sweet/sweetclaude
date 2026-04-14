---
name: sweetclaude:code/work-debt
description: "Tech debt cleanup. Locks current behavior with tests first, then refactors. Tests before touch, always. Use for refactoring, cleanup, performance work, or maintainability improvements."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Work Debt

Address tech debt for: $ARGUMENTS

## Process

1. **Define the debt.** What specifically is the problem? Why now? What risk or cost does it reduce?

2. **Scope the change.** What files/modules are affected? What's explicitly NOT changing? Run `design/change-impact-analysis` to understand the blast radius.

3. **Lock current behavior.** Before touching any code, write tests that capture the current behavior:
   - What does this code do today? Test that.
   - What are the edge cases? Test those.
   - Use TDD Level 1 (Light) — single-context, behavior-locking tests.
   - All tests must pass BEFORE any refactoring begins.

4. **Refactor.** Now change the code. After each change, run tests. If any test fails, you changed behavior — revert and try again.

5. **Verify.** All original behavior-locking tests still pass. No new failures anywhere. Run `code/qa-testing` on affected packages.

6. **PR.** Run `code/pr-precheck`. The PR description must explain: what debt was addressed, why now, and confirm no behavior changes (or document intentional ones).

## Rules

- Tests before touch. Always. No exceptions.
- If you can't write a test for current behavior, that's a finding — report it, don't skip it.
- Behavior changes during debt work require explicit user approval.
- Prefer small, committed steps over large rewrites.
