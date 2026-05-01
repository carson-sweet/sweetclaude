---
spdx-license: AGPL-3.0-or-later
description: Ripple-effect analysis for changes to EXISTING code or specs — trace what is affected across code, tests, docs, APIs, and specs. ONLY invoke when the user explicitly asks for impact analysis, or when a change targets existing artifacts. NEVER invoke when designing new features from scratch.
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Ripple-Effect Analysis

Analyze the impact of changing: $ARGUMENTS

## Process

### For code changes:

1. **Identify the change target.** Which file(s), function(s), or module(s) change?

2. **Trace code dependencies:**
   - What imports or requires this module?
   - What calls this function?
   - What interfaces does this implement?
   - Use `Grep` to find all references across the codebase.

3. **Trace test coverage:**
   - Which test files cover this module or function?
   - Do integration tests exercise this path?
   - Do test fixtures depend on this behavior?

4. **Trace API contracts:**
   - Does this affect a public API endpoint?
   - Does it change request or response shapes?
   - Does it change error behavior?
   - Do other services or frontends depend on this?

5. **Trace documentation:**
   - Does the README reference this behavior?
   - Does CLAUDE.md reference this?
   - Do any ADRs depend on this decision?
   - Does the `docs/` PRD or tech spec reference this?

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
   - [doc file] — [what is now stale]

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

- Only invoke on explicit user request or when the user has confirmed scope of a change to existing artifacts.
- Available on demand at any phase for any artifact type.
- Be thorough but concise. List affected items. Do not dump entire files.
- Flag items as "definitely affected" vs "possibly affected" when uncertain.
- If ripple analysis reveals the change is larger than expected, flag it and let the user decide how to proceed.
