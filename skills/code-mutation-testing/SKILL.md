---
description: Run mutation testing to verify test quality after implementation. Introduces small code changes and checks if tests catch them. Use after TDD GREEN phase to validate test effectiveness.
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Mutation Testing

Verify that tests detect faults, not just achieve coverage.

## Process

1. **Detect language and select tool:**
   - JavaScript/TypeScript: Stryker Mutator (`npx stryker run`)
   - Python: mutmut (`mutmut run`)
   - Go: gremlins (`gremlins unleash`)
   - Rust: cargo-mutants (`cargo mutants`)
   - Other: mewt (language-agnostic, Trail of Bits)
   - If no tool is available for the detected language, report and skip.

2. **Scope the mutation run.** Only mutate files changed in the current work. Use git diff to identify changed source files.

3. **Run mutations.** Execute the mutation testing tool scoped to changed files.

4. **Report results:**
   - Mutation score (killed / total mutants)
   - List of surviving mutants with: file, line, mutation type, what it changed
   - For each survivor: is the test gap meaningful or trivial?

5. **Recommend action:**
   - Score > 80%: "✓ Tests are solid. Surviving mutants are [trivial/edge cases]."
   - Score 60-80%: "⚠ Meaningful gaps. Add tests for: [list]"
   - Score < 60%: "✗ Tests are not catching real faults. Add tests before merging."

## Rules

- Optional. The user can skip per run.
- Never modify source code to improve mutation score. Only add tests.
- Run after GREEN, before PR.
- Scope to changed files only. Full-codebase mutation is too slow for interactive use.
