---
description: Final pre-PR quality gate. Verify tests pass, fill PR template, check for secrets and debug code, ensure acceptance criteria are met, update traceability. Use before opening any PR.
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# PR Ready

Prepare PR for the current branch.

## Checklist

1. **Acceptance criteria met.** Read the linked issue. Every AC checkbox satisfied.
2. **Tests pass.** Run lint, unit, and integration tests as applicable. All green. No skipped tests.
3. **No secrets in diff.** Grep for API keys, tokens, passwords, .env values in staged changes.
4. **No debug code.** Grep for console.log, debugger, print(), TODO/FIXME/HACK in new code.
5. **PR template filled.** What, Why, Scope, How to verify, Rollout plan, Security checklist.
6. **Commit messages descriptive.** Conventional commit format. No "fix stuff" or "wip".
7. **Branch rebased on latest main** if needed.
8. **Docs updated.** Run `sweetclaude:design/update-docs`. Flag and update any stale docs.
9. **Traceability updated.** Working repo `traceability/requirements-map.md` reflects the implementation.

If any item fails, report what is missing and fix it before proceeding.

Do not open the PR until all items pass.
