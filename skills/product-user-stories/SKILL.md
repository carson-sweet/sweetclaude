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

## State Check

Read `.sweetclaude/state/skills.yaml`.

**If `skills.yaml` does not exist:**
- Check whether any `US-*.md` files exist under `{base_path}/stories/`
- If yes: write `skills.yaml` with `skills.product-user-stories.enabled: true`. Proceed normally.
- If no: write `skills.yaml` with `skills.product-user-stories.enabled: false`. Route to `onboard`.

**If `skills.yaml` exists:**
- If `skills.product-user-stories.enabled: true`: proceed normally.
- If `skills.product-user-stories.enabled: false` AND `$ARGUMENTS` is not `onboard` or `offboard`: say "User stories haven't been set up for this project yet. Starting onboarding..." and route to `onboard`.
- If `$ARGUMENTS` is `offboard` and `enabled: false`: say "User stories are not currently enabled. Nothing to offboard." Stop.

**State writes:**
- End of `onboard` (success): set `skills.product-user-stories.enabled: true`, `onboarded_at: {today ISO date}`
- End of `offboard`: set `skills.product-user-stories.enabled: false`, `offboarded_at: {today ISO date}`

---

## Offboard — Export data and stop using this skill

Invoked with argument `offboard`.

1. **Inventory what exists:**

```bash
find {base_path}/stories/ -name "US-*.md" 2>/dev/null | wc -l
ls {base_path}/stories/ 2>/dev/null | head -10
```

Present: "This project has {N} user story files in `{base_path}/stories/`."

If nothing exists, say: "No story data found. Nothing to export." Stop.

2. **Ask export format:**

> "Where do you want to export your user stories?
>   github     — create GitHub Issues via `gh issue create`
>   markdown   — copy files to a directory you specify
>   csv        — write a summary CSV to a path you specify
>   none       — skip export, go straight to cleanup options"

3. **Export:**

- **github:** For each US-*.md, run `gh issue create --title "{story title}" --body "{acceptance criteria}"`. Report what was created.
- **markdown:** Ask "Which directory?" Copy all `US-*.md` files there. Report files copied.
- **csv:** Ask "Which path?" Write one row per story: ID, title, persona, format, acceptance criteria (joined). Report path written.
- **none:** Skip.

4. **Confirm export complete** (if export ran):

> "Export complete. Confirm the files look correct before proceeding. Ready to continue? (yes/cancel)"

If cancel, stop. Do not touch SweetClaude files.

5. **⚠ IRREVERSIBLE DATA LOSS WARNING ⚠**

> "⚠ IRREVERSIBLE DATA LOSS WARNING ⚠
>
> The next step will permanently delete {N} story files from `{base_path}/stories/`.
> This cannot be undone.
>
> To confirm deletion, type exactly: DELETE MY STORIES
> To cancel, type anything else."

If the user types anything other than `DELETE MY STORIES` exactly, say "Cancelled. Your files are safe." and stop.

6. **Delete only after exact confirmation:**

```bash
rm -rf {base_path}/stories/
```

Report: "Story files deleted."

---

## Onboard — First-time setup

Invoked with argument `onboard` when this skill is newly installed.

1. **Scan for existing story artifacts:**

```bash
# GitHub Issues
gh issue list --state open --limit 30 2>/dev/null | head -20 || true

# Markdown files with story patterns
find . -maxdepth 4 -name "*.md" | xargs grep -li "As a\|user story\|acceptance criteria" 2>/dev/null | grep -v ".sweetclaude" | head -10

# Jira / Linear exports
find . -maxdepth 4 \( -name "*.csv" -o -name "*.json" \) | xargs grep -li "story\|issue\|ticket" 2>/dev/null | head -5
grep -ri "linear.app\|jira\|atlassian" README* docs/ .sweetclaude/ 2>/dev/null | head -5
```

2. **Present findings and ask:**

If existing stories found:
> "I found existing user story artifacts: {list}.
>
> Want me to import these into SweetClaude's story format?
>   import  — read them and create US-XXX files
>   fresh   — write new stories from scratch
>   cancel  — set up later with `/sweetclaude:product-user-stories`"

If nothing found:
> "No existing user stories found. Ready to write stories from scratch. This works best after personas are defined — have you run `/sweetclaude:product-user-personas`? (yes/no, we can proceed either way)"

3. **If import:** Read the source files/issues. For each story found, create a `US-XXX` file in `{base_path}/stories/`. Preserve the original acceptance criteria. Present a summary.

4. **If fresh / proceed without personas:** Route to **Step 1** below.

5. **If cancel:** "OK. Run `/sweetclaude:product-user-stories` when ready."

---

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
