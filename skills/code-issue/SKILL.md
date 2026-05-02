---
spdx-license: AGPL-3.0-or-later
description: "Implement a GitHub issue end-to-end. Explore the issue, plan, implement with TDD, verify, and open a PR."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Implement Issue

Implement GitHub issue $ARGUMENTS using the SweetClaude pipeline.

## Process

1. **Explore.** Read the issue (`gh issue view $ARGUMENTS`). Follow linked docs (Notion, specs, ADRs). Read relevant source files. Summarize current behavior and risks. Do not change code yet.

2. **Ripple analysis.** Run `sweetclaude:design-change-impact-analysis` on the affected area. Present the impact assessment.

3. **Plan.** Propose a step-by-step plan with:
   - Files to modify
   - TDD level (bug fix → Level 1-2, feature → Level 2-3)
   - Test strategy: what test files, what assertions
   - Verification commands
   Wait for approval (respecting deference level).

4. **Implement with TDD.** Invoke `sweetclaude:code-tdd` at the planned level:
   - Bug fixes: Level 1-2 — regression test first, then fix
   - Features: Level 2-3 — depends on whether Gherkin specs exist

5. **Verify.** Run lint and tests for affected packages. Invoke `superpowers:verification-before-completion`.

6. **Update docs.** Run `sweetclaude:documents-update-docs` to check if documentation needs updating.

7. **PR.** Run `sweetclaude:code-testing` for the pre-PR checklist. Create branch, commit, and open PR with `gh pr create`. Fill the PR template completely — reference the issue number.

## Rules

- If acceptance criteria are unclear or missing, stop and ask before writing tests.
- Keep changes minimal. Follow existing patterns.
- Every behavior change needs a test.
- If you hit a blocker, report it. Do not work around it silently.
- Update traceability in `.sweetclaude/` after completion.
