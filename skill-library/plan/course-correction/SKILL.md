---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Course correction — document the pivot, triage in-flight work, and update project direction."
---


!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

<preflight-guard>
STOP. Before executing this skill, check: if pre-loaded state above shows STATE_NOT_FOUND, or neither .sweetclaude/state/sweetclaude.yaml nor .sweetclaude/state/phase.yaml exists, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Course Correction

A structured pivot when the project direction changes. Document why, triage what's in flight, and establish the new direction.

**Phases:** DISCOVER → DEFINE → TRIAGE → SHIP.

---

## Step 1: Document the signal (DISCOVER)

> "What's driving the course correction? I need to understand:
>
> 1. **The signal** — what happened that triggered this change? (user feedback, market shift, technical constraint, strategic decision, failed assumption)
> 2. **Is this a pattern or a single data point?** A course correction should be driven by aggregated signal, not a single event.
> 3. **What assumption is being invalidated?** Every pivot means something we believed turned out to be wrong."

Record: `SIGNAL`, `SIGNAL_TYPE` (single/aggregated), `INVALIDATED_ASSUMPTION`.

If `SIGNAL_TYPE` is single:

> "This appears to be a single signal. Course corrections based on a single data point are risky — the pivot itself can be wrong. Are there other signals that corroborate this, or is this conviction-based?"

Not a blocker — just surface the risk. The user decides.

---

## Step 2: Articulate old and new direction (DISCOVER → DEFINE)

> "Let me capture both directions clearly so we can triage what's in flight:
>
> **Old direction:** {ask user to state it in one sentence}
> **New direction:** {ask user to state it in one sentence}
>
> What specifically is changing? Common categories:
> - **Target user** — building for a different persona or segment
> - **Problem focus** — solving a different problem for the same user
> - **Solution approach** — same problem, fundamentally different technical or product approach
> - **Scope** — same direction but significantly larger or smaller
> - **Priority** — same features but different ordering"

Record: `OLD_DIRECTION`, `NEW_DIRECTION`, `CHANGE_TYPE`.

---

## Step 3: Update scope and personas (DEFINE)

Check for existing product artifacts:

```bash
ls .sweetclaude/product/product-brief.md .sweetclaude/product/prd.md 2>/dev/null
```

```bash
ls .sweetclaude/product/personas/ 2>/dev/null
```

For each artifact that exists:

> "The {artifact} needs to be updated to reflect the new direction. I'll draft the revisions — review them before I write."

If the target user is changing: update or create new personas. Retire old personas with a note: "Retired {date} — course correction from {OLD_DIRECTION} to {NEW_DIRECTION}."

If the product brief exists: draft a revised version. Mark changes clearly so the user can see what shifted.

If a PRD exists: identify which requirements are invalidated, which survive, and which are new.

Do not rewrite everything — mark what changed and why. The history of the pivot is valuable.

---

## Step 4: Triage in-flight work (TRIAGE)

This is the core of the skill. Every in-flight work item must be reviewed.

```bash
find .sweetclaude/product/backlog -name 'ISSUE-*.md' -exec grep -l 'status: \(in-progress\|new\|blocked\)' {} \; 2>/dev/null
```

```bash
find .sweetclaude/product -name 'EPIC-*.md' -exec grep -l 'status: \(active\|in-progress\|new\)' {} \; 2>/dev/null
```

For each item, present it and ask for a disposition via AskUserQuestion:

> "**{ITEM_ID}: {title}**
> Status: {status} | Priority: {priority}
>
> In light of the new direction ({NEW_DIRECTION}), what happens to this?"

| Option | Description |
|---|---|
| **Keep** | Still relevant to the new direction — no changes needed |
| **Repurpose** | Relevant but needs to be reframed for the new direction |
| **Drop** | No longer relevant — close with rationale |
| **Defer** | Might be relevant later but not now — move to backlog with low priority |

**On Keep:** no changes.

**On Repurpose:** ask what changes. Update the item's title, description, or acceptance criteria. Add a note: "Repurposed {date} — course correction."

**On Drop:** close the item. Add rationale: "Dropped {date} — course correction from {OLD_DIRECTION} to {NEW_DIRECTION}. Reason: {user's reason}."

**On Defer:** set priority to low, add label `deferred-course-correction`.

After all items are triaged, summarize:

```
Triage complete:
- Keep: {N} items
- Repurpose: {N} items
- Drop: {N} items
- Defer: {N} items
```

---

## Step 5: Assess impact on existing users (TRIAGE)

If the product is live:

> "Does this course correction affect existing users?
>
> 1. **What breaks?** — features being removed or changed
> 2. **What changes?** — behavior that shifts
> 3. **Data migration** — does existing user data need to move, transform, or be deprecated?"

If the product is not live: skip this step.

Record any migration needs as new backlog items.

---

## Step 6: Create new work items (TRIAGE → SHIP)

For the new direction, identify work that needs to happen:

> "What new work does the new direction require? I'll create backlog items for each."

For each new item:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --query next-id --prefix ISSUE
```

Write to `.sweetclaude/product/backlog/ISSUE-{NNN}-{slug}.md` with standard frontmatter.

Rebuild cache after all items are created:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --rebuild
```

---

## Step 7: Commit the new direction (SHIP)

Write the course correction to the decision log:

```markdown
| {next #} | {today} | Course correction: {OLD_DIRECTION} → {NEW_DIRECTION} | Signal: {SIGNAL}. Invalidated assumption: {INVALIDATED_ASSUMPTION}. Triage: {N} kept, {N} repurposed, {N} dropped, {N} deferred. {N} new items created. | Old direction documented in decision log entry {original entry #} |
```

Update `.sweetclaude/state/sweetclaude.yaml` if the project name or version_stage changed.

Present the summary:

> "Course correction committed.
>
> **Old direction:** {OLD_DIRECTION}
> **New direction:** {NEW_DIRECTION}
>
> **Triage results:**
> - Kept: {list}
> - Repurposed: {list}
> - Dropped: {list}
> - Deferred: {list}
> - New items: {list}
>
> **Updated artifacts:** {list of changed files}
>
> The backlog now reflects the new direction."

---

## Rules

- **Every in-flight item must be triaged.** No items survive a course correction without explicit review. Zombie items from the old direction are a guaranteed source of confusion.
- **The old direction must be documented.** Do not erase history. The record of what changed and why is valuable for future decisions.
- **Signal aggregation matters.** Surface the risk of pivoting on a single signal, but do not block. The user decides.
- **Do not close items without rationale.** Every dropped item gets a reason. "Course correction" alone is not sufficient — state why this specific item is no longer relevant.
- **Repurposed items keep their history.** Add notes, don't rewrite. The evolution of an item tells a story.
- **User impact assessment is mandatory for live products.** If the product has users, the course correction's impact on them must be addressed.
