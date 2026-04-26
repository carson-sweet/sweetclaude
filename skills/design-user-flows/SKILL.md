---
name: sweetclaude:design-user-flows
description: Convert user stories into UX/UI flows — step-by-step paths through the interface. Bridges product definition and UX design.
---

# Design User Flows

Convert user stories into interface flows — the step-by-step paths a user takes through the UI to complete each story. This bridges product definition and UX design.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/stories.yaml` — required for story list. If missing:
> "User flows require user stories. I recommend running `product-user-stories` first. Want to do that now, or continue without it?"

Read `.sweetclaude/state/personas.yaml` if available (for user context).

## Process

For each user story (or selected subset if the user wants to focus):

1. Identify the entry point — where in the interface does the user begin this flow?

2. Map the steps — each step is one user action and the system response:
   - Step N: [User action] → [System response / state change]

3. Identify decision points — where does the flow branch? (e.g., validation errors, optional steps, conditional paths)

4. Define the success state — what does the interface show when the story is successfully completed?

5. Define key error states — what does the interface show when something goes wrong?

Present each flow as a numbered step sequence. Offer to add a simple ASCII flow diagram if helpful.

**Example flow:**

```
Story US-ADM-001: Create a new contact

Entry point: Contacts list page

Flow:
  1. User clicks "New Contact" button → Modal or page opens with empty contact form
  2. User fills in Name (required), Email (optional), Phone (optional) → Fields validate inline
  3. User clicks "Save" → System validates all required fields
     → If Name missing: inline error "Name is required", form stays open
     → If valid: contact saved, modal closes, new contact appears at top of list
  4. User sees success toast: "Contact created"

Success state: Contact list visible with new entry at top, toast notification displayed
Error state: Form stays open, required field highlighted with error message
```

Ask after each flow: "Does this capture it correctly? Anything to adjust?"

## Scope Selection

If there are many stories, offer to scope: "Do you want flows for all stories, just the SLC/MVP scope, or specific ones?"

## Exit

Write `.sweetclaude/state/ux-flows.yaml`:

```yaml
flows:
  - story_id: {}
    entry_point: {}
    steps: []
    success_state: {}
    error_states: []
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — design-user-flows (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Flows defined:** {count}
**Open questions:** {bullets}
```

Write deliverable to `docs/{project-name}-user-flows-draft-v1.0-{yyyymmdd}.md` with standard front matter.
