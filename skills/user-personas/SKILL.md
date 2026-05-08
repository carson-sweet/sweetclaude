---
spdx-license: AGPL-3.0-or-later
name: user-personas
user-invocable: true
description: Define product users — who they are, what they need to do, and exactly what completing each task looks and feels like. Includes triggers, deal-breakers, and optional research-backed workflow expansion.
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# User Personas

Define the users of your product or tool — who they are, what they need to accomplish, and precisely what success and failure look like for each task.

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:setup` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.product.base_path`. This is the base directory for all product artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. if base is `.sweetclaude/product`, milestones go to `.sweetclaude/product/milestones/MS-001.md`).

4. Write artifacts to those paths.

## State Check

Read `.sweetclaude/state/skills.yaml`.

**Schema migration:** If `skills.yaml` exists with `schema_version: 1`, migrate this skill's entry before proceeding:
- `enabled: true` → `status: active`, `last_changed_at: {onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at` set → `status: paused`, `last_changed_at: {offboarded_at or onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at: ~` → `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
Drop `onboarded_at`/`offboarded_at`. Set `schema_version: 2`. Write atomically (see write protocol below).

**Dependency check:**
Read `~/.claude/config/sweetclaude/skills-registry.yaml`. Find `skills.user-personas.dependencies`. This skill has no dependencies — skip.

**If `skills.yaml` does not exist, OR exists but has no entry for `skills.user-personas`:**
- Check whether `.sweetclaude/state/personas.yaml` exists
- If yes: write entry with `status: active`, `last_changed_at: {today}`, `last_changed_by: migrated`
- If no: write entry with `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
- Use write protocol below.

**If `skills.yaml` exists and has an entry for `skills.user-personas`:**
- `status: active` → proceed normally
- `status: paused` AND `$ARGUMENTS` not in `[onboard, offboard, pause]`:
  > "Personas are currently paused. Resume? [yes/no]"
  If yes: write `status: active`, `last_changed_at: {today}`, `last_changed_by: resume` (using write protocol). Proceed normally.
  If no: stop.
- `status: uninitialized` AND `$ARGUMENTS` not in `[onboard, offboard, pause]`:
  → Run lightweight first-invocation flow (see below)
- `$ARGUMENTS` is `pause` → run pause operation
- `$ARGUMENTS` is `offboard` and `status: uninitialized`: "Personas aren't set up yet. Nothing to offboard." Stop.
- `$ARGUMENTS` is `pause` and `status: paused`: "Already paused." Stop.
- `$ARGUMENTS` is `pause` and `status: uninitialized`: "Not set up yet. Nothing to pause." Stop.

**Write protocol — all skills.yaml writes must follow this:**
1. Read and parse current `.sweetclaude/state/skills.yaml` (or start from default v2 structure if absent)
2. Merge your entry — do NOT remove or overwrite other skills' entries
3. Write merged content to `.sweetclaude/state/.skills.yaml.tmp`
4. Run: `mv .sweetclaude/state/.skills.yaml.tmp .sweetclaude/state/skills.yaml`

**State writes (use write protocol for all):**
- End of lightweight first-invocation (success): `status: active`, `last_changed_at: {today}`, `last_changed_by: first-invocation`
- End of onboard (success): `status: active`, `last_changed_at: {today}`, `last_changed_by: onboard`
- Pause operation: `status: paused`, `last_changed_at: {today}`, `last_changed_by: pause`
- Resume: `status: active`, `last_changed_at: {today}`, `last_changed_by: resume`
- End of offboard: `status: uninitialized`, `last_changed_at: {today}`, `last_changed_by: offboard`

---

## Pause — Temporarily stop using this skill

Invoked with argument `pause`.

Sets personas to `paused` status. Your persona data is untouched and you can resume at any time.

Write atomically (using write protocol):
- `skills.user-personas.status: paused`
- `skills.user-personas.last_changed_at: {today ISO date}`
- `skills.user-personas.last_changed_by: pause`

Say: "Paused. Your persona data is safe — nothing was deleted. Resume anytime by running `/sweetclaude:user-personas`."

---

## Offboard — Export data and stop using this skill

Invoked with argument `offboard`.

1. **Inventory what exists:**

```bash
ls {base_path}/personas/ 2>/dev/null
cat .sweetclaude/state/personas.yaml 2>/dev/null | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); print(len(d.get('personas',[]))) if d else print(0)" 2>/dev/null
```

Present: "This project has persona data in `.sweetclaude/state/personas.yaml` and `{base_path}/personas/`."

If nothing exists, say: "No persona data found. Nothing to export." Stop.

2. **Ask export format:**

> "Where do you want to export your personas?
>   markdown   — write each persona to a markdown file in a directory you specify
>   json       — write all personas to a single JSON file
>   none       — skip export, go straight to cleanup options"

3. **Export:**

- **markdown:** Ask "Which directory?" For each persona in `personas.yaml`, write a markdown file with all fields. Also copy any existing persona files from `{base_path}/personas/`. Report files written.
- **json:** Ask "Which path?" Write `personas.yaml` content as JSON. Report path written.
- **none:** Skip.

4. **Verify export (mandatory before deletion is unlocked):**

- **markdown verification:**
  ```bash
  source_count=$(cat .sweetclaude/state/personas.yaml 2>/dev/null | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); print(len(d.get('personas',[]))) if d else print(0)" 2>/dev/null)
  dest_count=$(ls {dest_dir}/*.md 2>/dev/null | wc -l)
  ```
  If dest_count ≥ source_count: "Export verified — {source_count} personas at `{dest_dir}`."
  If less: "⚠ File count mismatch — {source_count} personas, {dest_count} files at destination."
  On mismatch: ask "Continue anyway? [yes/cancel]". If cancel: stop.

- **json verification:**
  Read the JSON file written. Count entries in the personas array. If count ≥ source_count: "Export verified — {N} personas in JSON."
  If less: "⚠ Entry count mismatch." Ask "Continue anyway? [yes/cancel]". If cancel: stop.

- **none (no export chosen):**
  Require explicit acknowledgment:
  > "You've chosen to skip export. Your persona data will be permanently deleted with no backup.
  > Type exactly: NO BACKUP — to confirm, or anything else to cancel."
  If user types anything other than `NO BACKUP` exactly: "Cancelled. Your data is safe." Stop.

5. **⚠ IRREVERSIBLE DATA LOSS WARNING ⚠**

> "⚠ IRREVERSIBLE DATA LOSS WARNING ⚠
>
> The next step will permanently delete persona data from:
>   - `.sweetclaude/state/personas.yaml`
>   - `{base_path}/personas/` (if it exists)
>
> This cannot be undone.
>
> To confirm deletion, type exactly: DELETE MY PERSONAS
> To cancel, type anything else."

If the user types anything other than `DELETE MY PERSONAS` exactly, say "Cancelled. Your files are safe." and stop.

6. **Delete only after exact confirmation:**

```bash
rm -f .sweetclaude/state/personas.yaml
rm -rf {base_path}/personas/
```

Report: "Persona data deleted."

---

## Lightweight first-invocation — Quick setup on first use

Runs when the skill is invoked normally but `status` is `uninitialized`.

1. Ask inline:
   > "No personas defined yet. Briefly describe your first user type (role and primary goal), or type 'skip' to proceed without setup."

2. If the user describes a persona: create a minimal persona entry in `.sweetclaude/state/personas.yaml` with name/role/goal from the description. Report: "Created persona: {name}."

3. If **skip**: Proceed without creating any persona data.

4. Write state (using write protocol): `status: active`, `last_changed_at: {today}`, `last_changed_by: first-invocation`.

5. Proceed to the user's originally requested operation.

---

## Onboard — First-time setup

Invoked with argument `onboard` when this skill is newly installed.

1. **Scan for existing persona documents:**

```bash
find . -maxdepth 4 -name "*.md" | xargs grep -li "persona\|user type\|target user\|customer" 2>/dev/null | grep -v ".sweetclaude" | head -10
grep -ri "persona\|user type\|target user" README* docs/ .sweetclaude/state/ 2>/dev/null | head -5
```

2. **Present findings and ask:**

If existing docs found:
> "I found documents that may contain persona definitions: {list}.
>
> Want me to extract persona candidates from these now?
>   yes    — I'll read them and draft persona candidates for your review
>   fresh  — start from scratch instead
>   cancel — set up later with `/sweetclaude:user-personas`"

If nothing found:
> "No existing persona documents found. Ready to define personas from scratch. Proceed? (yes/cancel)"

3. **If yes (docs found):** Proceed to the **From Docs Path** below, using the found files as source documents.

4. **If fresh / yes (nothing found):** Proceed to the **Persona Loop** below.

5. **If cancel:** "OK. Run `/sweetclaude:user-personas` when ready."

---

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

**Discovery contract:** Read `.sweetclaude/state/discovery.yaml`.

- If it exists: use `target_user_summary` as a starting point for persona seeds. Also read `segments`, `scenarios`, `attitudinal_axes`, and `jtbd_candidates` if present — these are structured persona-precursor fields produced by BL-013 improvements to discovery. If these fields are absent (pre-BL-013 discovery files), do not block entry — proceed with what's available and note the gap: "Your discovery file predates structured segment and scenario capture. Consider re-running `/sweetclaude:product-discovery` to enrich it, or we'll build personas from what you have."
- If it does not exist: surface this gap before proceeding.

  Present:
  > "No discovery context found. Personas built without discovery context tend to be more speculative — you may need to revise them once you've done discovery work.
  >
  > Recommended: run `/sweetclaude:product-discovery` first to ground personas in real user research.
  >
  > Or continue here and we'll build the best personas we can from what you know now."

  Then call AskUserQuestion:

  | Option label | Description |
  |---|---|
  | **Run product-discovery first** | Recommended — ground personas in real research before defining them |
  | **Continue without discovery** | Build personas from what you know now; revise after discovery |
  | **Something else** | Different direction |

  If **Run product-discovery first**: invoke `sweetclaude:product-discovery`. Return here after it completes.
  If **Continue without discovery**: proceed with a note that these personas should be treated as provisional.

Read `.sweetclaude/state/research.yaml` if it exists — use for optional workflow expansion.

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

2. Call AskUserQuestion to choose how to build the workflow:

   | Option label | Description |
   |---|---|
   | **I'll draft it for you** | Recommended — Claude produces a draft workflow to review and adjust |
   | **Walk me through it** | You provide each element in turn |
   | **Something else** | Different approach |

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

## Diversity Verification

After all personas (and anti-profile, if defined) are complete, review the full persona set for coverage gaps:

Silently check:
- Are all personas the same seniority level (e.g., all managers, all beginners)?
- Are all personas from the same industry or company type?
- Are all personas the same technical skill level?
- Do any two personas have nearly identical triggers and deal-breakers?

If any gap is present, surface it:
> "Looking at the personas we've defined — {observation about the gap}. Is this intentional, or is there a user type we haven't covered?"

Do not manufacture personas. Only flag the gap and let the user decide whether to add more.

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
## {ISO datetime} — user-personas (n/a)

**Status:** completed | skipped | degraded
**Produced:** {filename}
**Personas defined:** {count}
**Tasks defined:** {total across all personas}
**Skipped/shortcuts:** {what, or none}
**Open questions:** {bullets}
```

Write deliverable to `{base_path}/{project-name}-user-personas-draft-v1.0-{yyyymmdd}.md` with standard front matter.
