---
spdx-license: AGPL-3.0-or-later
description: "Build a new feature end-to-end. Generates Gherkin specs if needed, runs full TDD Level 3 pipeline (test writer → QA caucus → implementer), then verifies and opens a PR."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Build Feature

Build feature: $ARGUMENTS

## Process

### Step 1: Locate specs

Check for existing artifacts in this order:
1. Gherkin `.feature` files in `.sweetclaude/` or `features/` matching the feature name
2. User stories in `.sweetclaude/stories/`
3. PRD or product brief in `docs/`

If Gherkin specs already exist → skip to Step 3.
If user stories exist but no Gherkin → go to Step 2b.
If nothing exists → go to Step 2a.

### Step 2a: Write the user story

Ask:
> "Describe the feature in one sentence: who does what, and what outcome do they get?"

Then draft a user story:
```
As a {persona}, I want to {action} so that {outcome}.

Acceptance criteria:
- Given {context}, when {action}, then {result}
- ...
```

Present and confirm before continuing.

### Step 2b: Generate Gherkin

Invoke `sweetclaude:product-user-tdd-tests` with the user story as input to generate `.feature` files. Wait for completion and user approval of the Gherkin before continuing.

### Step 3: TDD Level 3

Run the full Level 3 pipeline from `sweetclaude:code-tdd`:

1. **Spawn test writer subagent.** Receives: the `.feature` file, existing codebase for patterns. No knowledge of planned implementation. Writes failing tests that fully specify the Gherkin behavior.

2. **QA Caucus.** Spawn three parallel review subagents:
   - `sweetclaude:qa-caucus-service` — service/API coverage
   - `sweetclaude:qa-caucus-component` — UI/component coverage (if applicable)
   - `sweetclaude:qa-caucus-integration` — cross-cutting concerns
   Consolidate findings. Present gaps to user for approval. Add approved gaps to test files.

3. **Verify RED.** Run tests. All must fail. If any pass unexpectedly, investigate before continuing.

4. **User approval.** Present the test files. Wait for explicit approval before implementation begins.

5. **Commit tests.** Git checkpoint: `test: RED - {feature-name} failing tests`

6. **Spawn implementer subagent.** Receives: test files (read-only), existing codebase. Never sees user stories, Gherkin, or test-writing reasoning. Instruction: make the tests pass with minimum code.

7. **Verify GREEN.** All tests pass. No other tests regressed.

8. **Refactor.** Clean up implementation. Tests stay green after each change.

### Step 4: Verify

Run `sweetclaude:code-testing` — at minimum the test suite and PR pre-check. Offer mutation testing for critical paths.

Run `sweetclaude:documents-update-docs` to check if documentation needs updating.

### Step 5: PR

Create branch, commit, and open PR with `gh pr create`. PR description must reference the user story or Gherkin spec, list acceptance criteria met, and include test evidence.

## Rules

- No implementation without failing tests.
- Test files are immutable once committed — if a test looks wrong, report it, do not change it.
- Keep changes minimal. Only build what the acceptance criteria require.
- If acceptance criteria are ambiguous, stop and clarify before writing tests.
