---
name: sweetclaude:product/user-workflows
description: "Convert user stories into UX/UI flows showing the step-by-step path a user takes through the interface. Bridges product definition and UX design."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# User Workflows

Convert user stories into step-by-step UI flows for: $ARGUMENTS

## Context

Read relevant user stories from `stories/` and personas from product/discovery output.

## Process

### For each user story:

1. **Identify the trigger.** What event or action initiates this workflow? (button click, page load, notification, time-based)

2. **Map the happy path.** Step by step, what does the user see and do?
   ```
   Step 1: User sees {screen/component}
   Step 2: User {action — clicks, types, selects}
   Step 3: System {response — shows, navigates, saves}
   Step 4: User sees {confirmation/result}
   ```

3. **Map error paths.** For each step where something can go wrong:
   - What's the error condition?
   - What does the user see?
   - How do they recover?

4. **Map edge cases.** Empty states, first-time use, maximum data, permissions boundaries.

5. **Identify decision points.** Where does the user choose between paths? Document each fork.

### Produce the document

```
## User Workflow: {Story title}

**Trigger:** {what initiates this}
**Persona:** {who does this}

### Happy path
1. {step} → {what user sees}
2. {step} → {what user sees}
...

### Error paths
- At step {N}, if {condition}: {what happens}

### Edge cases
- Empty state: {what user sees}
- First use: {any onboarding needed}

### Decision points
- At step {N}: {choice A} or {choice B}
```

### Save

Save to `specs/workflows/` in `.sweetclaude/`. These feed into design/ux and product/user-tdd-tests.
