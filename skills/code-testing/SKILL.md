---
spdx-license: AGPL-3.0-or-later
description: "Run any combination of test suite, mutation testing, security review, and PR pre-check. Opens a menu at start — pick one or several."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Code Testing

## Step 1: Choose what to run

Present this menu and ask the user to pick one or more:

```
What do you want to run? (pick one or several)

  1. Test suite      — run tests, report pass/fail
  2. Mutation        — verify tests actually catch faults
  3. Security        — review code for auth, injection, and secrets issues
  4. PR pre-check    — final quality gate before opening a PR
```

Accept any combination: "1", "1 3", "all", "1 2 3 4", "security", "test suite and pr", etc. Parse the intent.

If `$ARGUMENTS` was passed (e.g. `/sweetclaude:code-testing security`), skip the menu and use that as the selection.

Run selected checks in this order: test suite → mutation → security → PR pre-check. Complete each before starting the next.

---

## Test Suite

Run tests for: $ARGUMENTS (package name, service name, or "all")

**Process:**

1. Read the project's test command from CLAUDE.md or `state/project.yaml`.

2. Run the tests. If a package or service was specified, scope the run. Otherwise run the full suite.

3. Report concisely:

   If all pass:
   ```
   ✓ {N} tests passed, 0 failed
   ```

   If any fail:
   ```
   ✗ {N} passed, {M} failed

   Failures:
   - {test name} — {file}:{line}
     Expected: {expected}
     Received: {actual}
   ```

4. Do not dump full stdout/stderr. Summarize failures only. The user can ask for verbose output.

**Rules:**
- This check reports. It does not fix. For fixes, use `code-tdd` or `code-issue`.
- If the test command is not configured, say so and ask the user to add it to CLAUDE.md.

---

## Mutation Testing

Verify that tests detect faults, not just achieve coverage.

**Process:**

1. Detect language and select tool:
   - JavaScript/TypeScript: Stryker Mutator (`npx stryker run`)
   - Python: mutmut (`mutmut run`)
   - Go: gremlins (`gremlins unleash`)
   - Rust: cargo-mutants (`cargo mutants`)
   - Other: mewt (language-agnostic, Trail of Bits)
   - If no tool is available for the detected language, report and skip.

2. Scope to changed files only. Use `git diff` to identify changed source files.

3. Run the mutation testing tool scoped to those files.

4. Report results:
   - Mutation score (killed / total mutants)
   - List of surviving mutants: file, line, mutation type, what changed
   - For each survivor: is the gap meaningful or trivial?

5. Recommend action:
   - Score > 80%: "✓ Tests are solid. Surviving mutants are [trivial/edge cases]."
   - Score 60–80%: "⚠ Meaningful gaps. Add tests for: [list]"
   - Score < 60%: "✗ Tests are not catching real faults. Add tests before merging."

**Rules:**
- Never modify source code to improve mutation score. Only add tests.
- Scope to changed files only — full-codebase mutation is too slow.

---

## Security Review

Review code changes for security issues.

**Scope:** If $ARGUMENTS specifies files or a PR, review those. Otherwise review staged changes or recent commits.

**Checklist:**

For each file in scope:

*Authentication & Authorization*
- [ ] Auth checks present on all endpoints/handlers that need them
- [ ] Authorization scoped correctly (tenant boundaries, role checks)
- [ ] No auth bypass paths (direct object reference, parameter manipulation)
- [ ] Session handling follows project patterns

*Injection*
- [ ] SQL: parameterized queries, no string concatenation
- [ ] XSS: output encoding, no raw HTML insertion
- [ ] Command injection: no user input in shell commands
- [ ] Path traversal: no user input in file paths without validation

*Secrets & Data*
- [ ] No hardcoded credentials, API keys, or secrets
- [ ] No secrets in logs or error messages
- [ ] Sensitive data not exposed in API responses
- [ ] PII handling follows project patterns

*Dependencies*
- [ ] No known-vulnerable dependencies introduced
- [ ] New dependencies from reputable sources

**Output:**

```
Security Review: {scope}
════════════════════════

✗ Critical:
  - {finding} — {file}:{line} — {what to fix}

⚠ Warning:
  - {finding} — {file}:{line} — {what to fix}

→ Info:
  - {finding} — {file}:{line} — {recommendation}

✓ Clean:
  - {area checked with no findings}
```

**Rules:**
- Read-only. Do not modify code.
- If no issues found, say so clearly. Do not manufacture findings.
- Flag ambiguous cases as Info with context for the user to decide.

---

## PR Pre-Check

Final quality gate before opening a PR.

**Checklist:**

1. **Acceptance criteria met.** Read the linked issue. Every AC checkbox satisfied.
2. **Tests pass.** Run lint, unit, and integration tests. All green. No skipped tests.
3. **No secrets in diff.** Grep for API keys, tokens, passwords, .env values in staged changes.
4. **No debug code.** Grep for console.log, debugger, print(), TODO/FIXME/HACK in new code.
5. **PR template filled.** What, Why, Scope, How to verify, Rollout plan, Security checklist.
6. **Commit messages descriptive.** Conventional commit format. No "fix stuff" or "wip".
7. **Branch rebased on latest main** if needed.
8. **Docs updated.** Run `sweetclaude:documents-update-docs`. Flag and update any stale docs.
9. **Traceability updated.** `traceability/requirements-map.md` reflects the implementation.

If any item fails, report what is missing. Do not open the PR until all items pass.
