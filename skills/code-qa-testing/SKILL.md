---
description: "Run test suites and report results concisely. Failures with file, line, and assertion only. Use when you need a clean pass/fail summary."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# QA Testing

Run tests for: $ARGUMENTS (package name, service name, or "all")

## Process

1. **Read the project's test command** from CLAUDE.md or `state/project.yaml`.

2. **Run the tests.** If $ARGUMENTS specifies a package or service, scope the run. If "all", run the full suite.

3. **Report concisely:**

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

4. **Do not dump full stdout/stderr.** Summarize failures only. The user can ask for verbose output.

## Rules

- This skill reports. It does not fix. For fixes, use `code/tdd` or `code/work-issue`.
- If the test command is not configured, say so and ask the user to add it to CLAUDE.md.
