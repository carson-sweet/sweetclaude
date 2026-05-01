---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:product-user-personas
description: Define product users — who they are, what they need to do, and exactly what completing each task looks and feels like. Includes triggers, deal-breakers, and optional research-backed workflow expansion.
---

# Product User Personas

Define the users of your product or tool — who they are, what they need to accomplish, and precisely what success and failure look like for each task.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/discovery.yaml` if it exists — use `target_user_summary` as a starting point. Read `.sweetclaude/state/research.yaml` if it exists — use for optional workflow expansion.

## Path Selection

Ask:
> "Are you starting from scratch, or do you have existing documents to extract personas from — things like a PRD, brief, research notes, or prior persona definitions?"

- **From scratch:** proceed to Persona Loop below.
- **From docs:** proceed to From Docs path below, then continue into the Persona Loop for refinement.

## From Docs Path

Ask the user to share or specify the source documents. Accept any of:
- File paths (read directly)
- Pasted text
- A mix of both

Read all provided content. Extract persona candidates:

For each distinct user type you identify, draft:
- A name or role label
- Role, context, responsibilities
- Inferred trigger (what situation drives them to this product)
- Inferred deal-breakers (what would make them leave)
- Tasks they appear to need (from requirements, job descriptions, use cases, or any narrative in the docs)

Present all candidates as a structured draft:

> "From your documents I found {N} persona candidates. Here they are — correct anything that's wrong, add what's missing, and tell me if I missed a user type entirely."

Show each candidate concisely. Wait for the user to review and confirm or adjust.

After confirmation, note which fields are thin or inferred so the user knows where to fill gaps:
> "Fields marked [inferred] came from indirect evidence. We'll sharpen them as we go through the task loop."

Then continue into the Persona Loop below — start at the Task Loop for each confirmed persona, skipping the initial definition questions for fields already populated. Ask definition questions only for fields still blank or marked [inferred].

---

## Persona Loop

Repeat for each persona until the user says there are no more.

### Persona Definition

Ask one question at a time:

1. "Describe this person — their role, context, and what they're responsible for."

2. "What triggers them to go looking for a solution like yours? What specific event or situation makes them search?" (Not a category — a specific moment.)

3. "What would make them walk away from your product even if it technically works? Think about: price threshold, missing integrations, required expertise or setup, trust or credibility requirements."

Record: name (or role label), role, context, trigger, deal-breakers.

### Task Loop

For each persona, repeat until the user says the persona is done:

**Task definition:**

1. "What's a task this person needs to accomplish with your product?"

2. Offer to build the workflow: "I can draft the workflow details for you to review, or you can walk me through it. Which would you prefer?"

   If Claude drafts: produce draft workflow with steps, inputs, success criteria, and failure modes. Ask for review and adjustment.
   If user provides: ask for each element in turn.

**Workflow elements:**
- Steps (numbered sequence of actions from start to completion)
- Information needed to begin (what must the user have or know before starting?)
- Success criteria: **must be observable, binary, and specific.** Include a number, step count, time limit, or concrete outcome.
  - Bad: "User manages contacts easily"
  - Good: "User creates a new contact in under 3 steps without leaving the current view"
- Common failure modes (what goes wrong and how?)

**Challenge:** After the success criteria are defined, ask: "If every criterion passed but the user was still unhappy, what would be missing?" That gap is another criterion. Add it.

**Optional research expansion:** After the task has initial shape:
> "I can research how other products handle this workflow — looking at the competitive landscape we covered, best practices, and key features that support it. I'd propose improvements with my reasoning for why they'd help users. Want me to do that?"

If yes: use research state + web search if needed. Propose only improvements with clear, stated user value. Apply YAGNI and KISS — do not add workflow steps to fill space. Present proposals with inferred user value explicitly stated.

### New Persona Task Reuse

When starting each new persona, always ask:
> "Before we define tasks for [new persona name], do any of the tasks we've already defined apply to them? We can reuse those rather than redefine them."

List the already-defined tasks by name for easy reference.

## Anti-Profile

After all personas are complete, offer:
> "Do you want to define an anti-profile — a description of who is explicitly NOT a target user? This can clarify product boundaries and prevent building for the wrong person."

If yes: "Who would misuse this, churn immediately, or demand features that would dilute the core value for your real users?"

## Frustration and Skip Handling

If the user seems frustrated at any point:
> "We can move on with what we have. Do you want to continue with the next task, the next persona, or skip to writing up what we have?"

Accept immediately. Log what was skipped.

## Exit

Write `.sweetclaude/state/personas.yaml`:

```yaml
personas:
  - id: persona-1
    name: {}
    role: {}
    trigger: {}
    deal_breakers: []
    tasks:
      - id: task-1
        description: {}
        workflow_steps: []
        inputs_needed: {}
        success_criteria: []
        failure_modes: []
        research_expanded: true | false
anti_profile: {} | null
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-user-personas (n/a)

**Status:** completed | skipped | degraded
**Produced:** {filename}
**Personas defined:** {count}
**Tasks defined:** {total across all personas}
**Skipped/shortcuts:** {what, or none}
**Open questions:** {bullets}
```

Write deliverable to `docs/{project-name}-user-personas-draft-v1.0-{yyyymmdd}.md` with standard front matter.
