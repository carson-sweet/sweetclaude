---
name: sweetclaude-code-qa-testing
description: "Run test suites and report results concisely. Just failures with file, line, and assertion — not full stdout dumps. Use when you need a clean pass/fail summary."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
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

4. **Do NOT dump full stdout/stderr.** Summarize failures only. The user can ask for verbose output if needed.

## Rules

- This skill reports. It does not fix. If the user wants fixes, direct them to `code/tdd` or `code/work-issue`.
- If the test command is not configured, say so and ask the user to add it to CLAUDE.md.
