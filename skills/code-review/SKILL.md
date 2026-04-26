---
description: "Adversarial code review focused on logic errors, edge cases, regressions, performance, and missing error handling. Does not flag style issues."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Code Review

Review code changes adversarially.

## Scope

If $ARGUMENTS specifies files or a PR, review those. Otherwise, review staged changes or recent commits.

## Focus Areas

1. **Logic errors** — off-by-one, wrong operator, inverted condition, missing null check
2. **Edge cases** — empty input, boundary values, concurrent access, very large input
3. **Regressions** — does this change break existing behavior? Check callers and consumers.
4. **Missing error handling** — what happens when this fails? Network errors, invalid data, timeouts, disk full
5. **Performance** — N+1 queries, unbounded loops, missing pagination, unnecessary allocations, missing indexes
6. **Naming and contracts** — does the function do what its name says? Do types match reality?

## What NOT to Flag

- Style issues (formatting, naming conventions). The linter handles that.
- Opinions about code organization that do not affect correctness.
- Missing features that were not in scope.

## Output

```
Code Review: {scope}
═══════════════════

✗ Critical (must fix):
  - {finding} — {file}:{line}
    Problem: {what is wrong}
    Fix: {specific suggestion}

⚠ Warning (should fix):
  - {finding} — {file}:{line}
    Problem: {what could go wrong}
    Fix: {specific suggestion}

→ Nit (consider):
  - {finding} — {file}:{line}
    {suggestion}

✓ Looks good:
  - {area reviewed with no findings}
```

## Rules

- Be adversarial. Assume the code has bugs and find them.
- Every finding must have a specific fix suggestion.
- Read-only. Do not modify code.
- If the code is solid, say so. Do not manufacture findings.
