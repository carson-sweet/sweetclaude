---
name: sweetclaude-design-change-impact-analysis
description: Ripple-effect analysis — before implementing a change, trace what's affected across code, tests, docs, APIs, and specs. Use at the start of IMPLEMENT phase for existing codebases, or on demand when any artifact changes.
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Ripple-Effect Analysis

Analyze the impact of changing: $ARGUMENTS

## Process

### For code changes:

1. **Identify the change target.** What file(s), function(s), or module(s) will change?

2. **Trace code dependencies:**
   - What imports/requires this module?
   - What calls this function?
   - What interfaces does this implement?
   - Use `Grep` to find all references across the codebase.

3. **Trace test coverage:**
   - What test files test this module/function?
   - Are there integration tests that exercise this path?
   - What test fixtures depend on this behavior?

4. **Trace API contracts:**
   - Does this change affect any public API endpoint?
   - Does it change request/response shapes?
   - Does it change error behaviors?
   - Are there consumers (other services, frontends) that depend on this?

5. **Trace documentation:**
   - Does the README reference this behavior?
   - Does the CLAUDE.md reference this?
   - Are there ADRs that depend on this decision?
   - Does the working repo PRD/tech spec reference this?

6. **Present impact summary:**
   ```
   RIPPLE ANALYSIS: [change description]

   Code affected:
   - [file:line] — [why]

   Tests affected:
   - [test file] — [what needs updating]

   APIs affected:
   - [endpoint] — [what changes]

   Docs affected:
   - [doc file] — [what's now stale]

   Risk: [Low/Medium/High]
   Recommendation: [proceed / investigate further / reconsider approach]
   ```

### For document/spec changes:

1. **Identify what changed** in the spec/brainstorm/PRD/architecture.

2. **Trace downstream artifacts:**
   - Does this change affect the PRD? (if brainstorm changed)
   - Does this change affect the architecture? (if PRD changed)
   - Does this change affect stories? (if architecture changed)
   - Does this change affect Gherkin specs? (if stories changed)
   - Does this change affect tests? (if Gherkin changed)
   - Does this change affect implementation? (if tests changed)

3. **Present document ripple summary** with the same format.

## Rules

- Run automatically at the start of IMPLEMENT phase for existing codebases.
- Available on demand at any phase for any artifact type.
- Be thorough but concise — list affected items, don't dump entire files.
- Flag items as "definitely affected" vs "possibly affected" when uncertain.
- If ripple analysis reveals the change is larger than expected, flag it and let the user decide how to proceed.
