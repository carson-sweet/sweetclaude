---
spdx-license: AGPL-3.0-or-later
description: "Tech debt cleanup. Locks current behavior with tests first, then refactors. Tests before touch, always. Use for refactoring, cleanup, performance work, or maintainability improvements."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Work Debt

Address tech debt for: $ARGUMENTS

## Process

1. **Define the debt.** What is the problem? Why now? What risk or cost does fixing it reduce?

2. **Scope the change.** Which files and modules are affected? What is explicitly NOT changing? Run `sweetclaude:design-change-impact-analysis` to map the blast radius.

3. **Lock current behavior.** Before touching any code, write tests that capture what exists:
   - What does this code do today? Test that.
   - What are the edge cases? Test those.
   - Use TDD Level 1 (Light): single-context, behavior-locking tests.
   - All tests must pass BEFORE any refactoring begins.

4. **Refactor.** Change the code. Run tests after each change. If any test fails, you changed behavior — revert and try again.

5. **Verify.** All behavior-locking tests still pass. No new failures anywhere. Run `sweetclaude:code-testing` on affected packages.

6. **PR.** Run `sweetclaude:code-testing`. The PR description must explain: what debt was addressed, why now, and confirm no behavior changes (or document intentional ones).

## Rules

- Tests before touch. Always. No exceptions.
- If you cannot write a test for current behavior, that is a finding. Report it. Do not skip it.
- Behavior changes during debt work require explicit user approval.
- Prefer small, committed steps over large rewrites.
