---
description: "Define measurable success for each persona and task. Each criterion is evaluable as true/false after the product ships. No vague 'users are happy.'"
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# User Success Criteria

Define measurable success for: $ARGUMENTS

## Context

Read personas from `product/discovery` output or `strategy/ideal-customer-profile.md`. Each success criterion maps to a specific persona and task.

## Process

### For each persona:

1. **List their tasks** (from discovery or ICP).

2. **For each task, define success.** Each criterion is:
   - **Observable** — you can watch someone do it or measure it
   - **Binary** — after ship, it is either true or false
   - **Specific** — includes a number, a step count, a time, or a concrete outcome

   Bad: "User can manage contacts easily"
   Good: "User creates a new contact in under 3 steps without leaving the current view"

   Bad: "Search is fast"
   Good: "Search returns results in under 500ms for datasets up to 10,000 records"

3. **Challenge each criterion.** Ask: "If this passed but users were still unhappy, what is missing?" That missing thing is another criterion.

### Produce the document

```
## User Success Criteria: {Project Name}

### {Persona 1}

**Task: {task description}**
- [ ] {criterion — binary, observable, specific}
- [ ] {criterion}

**Task: {task description}**
- [ ] {criterion}
```

### Save

Save to `docs/user-success-criteria.md`. These criteria are referenced by product/product-brief (success criteria section) and product/user-tdd-tests (drive Gherkin scenarios).
