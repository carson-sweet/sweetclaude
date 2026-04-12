---
name: sweetclaude-pr-ready
description: Final pre-PR quality gate. Verify tests pass, fill PR template, check for secrets and debug code, ensure acceptance criteria are met, update traceability. Use before opening any PR.
---

# PR Ready

Prepare PR for the current branch.

## Checklist

1. **Acceptance criteria met.** Read the linked issue. Every AC checkbox satisfied.
2. **Tests pass.** Run lint + unit + integration as applicable. All green. No skipped tests.
3. **No secrets in diff.** Grep for API keys, tokens, passwords, .env values in staged changes.
4. **No debug code.** Grep for console.log, debugger, print(), TODO/FIXME/HACK in new code.
5. **PR template filled.** What, Why, Scope, How to verify, Rollout plan, Security checklist.
6. **Commit messages descriptive.** Conventional commit format, no "fix stuff" or "wip".
7. **Branch rebased on latest main** if needed.
8. **Docs updated.** Run `sweetclaude:auto-docs` — any stale docs flagged and updated.
9. **Traceability updated.** Working repo `traceability/requirements-map.md` reflects the implementation.

If any item fails, report what's missing and fix it before proceeding.

Do not open the PR until all items pass.
