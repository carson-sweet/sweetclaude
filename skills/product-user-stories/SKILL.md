---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:product-user-stories
description: Write user stories for a defined scope — Gherkin or generic format, scoped to all personas, SLC, or MVP. Uses best-practice naming and numbering.
category: product
---

# Product User Stories

Write user stories for your product, in the format and scope that best fits your needs.

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:on` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.product.base_path`. This is the base directory for all product artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. if base is `.sweetclaude/product`, milestones go to `.sweetclaude/product/milestones/MS-001.md`).

4. Write artifacts to those paths.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/personas.yaml` — required for task definitions. If missing:
> "User stories require persona and task definitions. I recommend running `product-user-personas` first. Want to do that now, or continue without it?"
Accept if user declines. Log degraded status.

Read `.sweetclaude/state/prd.yaml` and `.sweetclaude/state/brief.yaml` if available.

## Step 1 — Format

"What format do you want for the user stories?

- **Gherkin** (Given/When/Then) — structured, precise, better for design and development handoff, and for test-driven development
- **Generic** (As a / I want / So that) — readable, flexible, better for product management, user-guide writing, and marketing handoff
- **Both** — Gherkin for dev handoff, generic for stakeholders
- **Something else** — tell me what you need"

## Step 2 — Scope

"What scope do you want to cover?

- **Everything** — all tasks for all personas
- **SLC** (Simple-Lovable-Complete) — stories for the narrowest complete promise to one key user. I can explain this if helpful.
- **MVP** (Minimum Viable Product) — you tell me which persona-tasks are in MVP vs. later roadmap"

If the user asks what SLC means:
> "SLC is an alternative to MVP that focuses on making a promise to one specific user and completely delivering on it — rather than delivering a partial version of many things. Simple: the smallest scope. Lovable: it has to be good at what it does. Complete: it fully delivers the promised value. The result tends to ship faster and earn more trust than a classic MVP."

**SLC path:**
1. "Who is the most important user — the one person whose problem you absolutely must solve in this release?"
2. "What is the promise to them — the one thing they'll be able to do when this ships that they can't do today?" Coach toward specificity: "The promise should be concrete enough that you could announce it and someone would know exactly what they're getting."
3. Based on personas.yaml tasks, suggest which tasks need to be implemented to fulfill the promise.
4. Get confirmation or adjustment.

**MVP path:**
1. Present all persona-tasks from personas.yaml.
2. "Which of these must be in MVP? Mark the ones that are later roadmap."
3. Get confirmation.

**All path:** Include every task from every persona.

## Step 3 — Write

Write stories for the confirmed scope.

**Naming and numbering:** Use best-practice conventions:
- Stories grouped by persona, then by functional area within persona
- Story IDs: `US-{persona-abbr}-{NNN}` (e.g., `US-ADM-001`)
- Epic IDs if using epics: `EP-{NNN}`
- Each story title: short verb phrase ("Create contact", "Export report")

**Gherkin format:**
```gherkin
Story US-ADM-001: Create a new contact

As an Admin
I want to create a new contact record
So that I can track interactions with that person

Scenario: Successful contact creation
  Given I am on the Contacts page
  When I click "New Contact" and fill in the required fields
  Then a new contact record is saved and visible in my contact list

Scenario: Missing required field
  Given I am on the New Contact form
  When I submit without filling in the Name field
  Then I see an error message "Name is required" and the form is not submitted
```

**Generic format:**
```
Story US-ADM-001: Create a new contact
As an Admin, I want to create a new contact record so that I can track interactions with that person.
Acceptance criteria:
- Contact is created when all required fields are filled and submitted
- Error is shown when required fields are missing
- New contact appears in the contact list immediately after creation
```

Present all stories when complete. Offer to adjust scope, format, or individual stories.

## Document Production System

File naming: `{project-name}-user-stories-{status}-v{major}.{minor}-{yyyymmdd}.md`

Front matter: standard schema. Note in `audience` field who these are for.

## Collaborative Revision

Same revision workflow — minor bump for edits, major bump for scope or format changes. Previous file deprecated.

## Exit

Write `.sweetclaude/state/stories.yaml`:

```yaml
format: gherkin | generic | both
scope: all | slc | mvp
slc_promise: {} | null
stories:
  - id: {}
    title: {}
    persona_id: {}
    epic_id: {} | null
    format: gherkin | generic
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-user-stories (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Format:** {gherkin | generic | both}
**Scope:** {all | slc | mvp}
**Story count:** {N}
**Open questions:** {bullets}
```
