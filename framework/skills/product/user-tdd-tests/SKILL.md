---
name: sweetclaude:product/user-tdd-tests
description: Transition BMAD user stories into Gherkin .feature files. The .feature files become the contract for TDD test generation. Use during PLAN phase after stories are written.
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Gherkin Bridge

Convert user story $ARGUMENTS into a Gherkin .feature file.

## Process

1. **Read the user story.** Find the story file in `.sweetclaude/` under `stories/EPIC-XXX/`. Extract all acceptance criteria.

2. **Generate .feature file.** For each acceptance criterion, write one or more Gherkin scenarios:

```gherkin
Feature: [Story title]
  As a [user type from story]
  I want [goal from story]
  So that [benefit from story]

  Scenario: [Acceptance criterion - happy path]
    Given [precondition]
    When [action]
    Then [expected result]
    And [additional assertions]

  Scenario: [Acceptance criterion - error case]
    Given [precondition]
    When [invalid action]
    Then [expected error behavior]
```

3. **Cover all paths.** For each acceptance criterion:
   - Happy path scenario
   - Error/validation scenarios
   - Edge cases explicitly mentioned in the story
   - Boundary conditions

4. **Save .feature file** alongside the story: `stories/EPIC-XXX/story-XXX.feature`

5. **Update traceability.** Append to `traceability/requirements-map.md`:
   ```
   | Story-XXX | story-XXX.feature | [scenarios listed] | [tests: pending] | [impl: pending] |
   ```

6. **Present to user.** Show the .feature file. This is the contract that drives test generation.

## Rules

- .feature files use standard Gherkin syntax (Given/When/Then/And/But)
- One .feature file per user story
- Scenarios should be concrete and testable — no vague language
- Include data examples where behavior varies by input (Scenario Outline + Examples)
- The .feature file is the source of truth for TDD Level 3 — the test writer agent reads only this
