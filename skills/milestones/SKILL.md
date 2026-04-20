---
description: "Manage roadmap targets (milestones) that span strategy and product work. Create, review, link work items to, and track completion of outcome-driven milestones like 'Exit Stealth' or 'Paid Pilot Live'."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Milestones

Manage milestones: $ARGUMENTS

A milestone is a **roadmap target** — a named strategic outcome the project is driving toward. Not a release, not a sprint, not an epic. Examples: "Exit Stealth", "Paid Pilot Live", "Series A Readiness", "MVP Shipped".

## Routing

Classify the invocation by the first word of `$ARGUMENTS`:

| First word | Operation |
|------------|-----------|
| `add` | Create a new milestone |
| `review` | List milestones grouped by Now / Next / Later |
| `link <item> <MS-XXX>` | Attach a product work item to a milestone |
| `status <MS-XXX>` | Detail view of one milestone |
| `blockers <MS-XXX>` | List what's unfinished on a milestone |
| `complete <MS-XXX>` | Mark a milestone achieved + chain follow-ups |
| `unassigned` | Find work items with no milestone |

If `$ARGUMENTS` is empty or doesn't match, default to `review`.

## Storage

```
docs/milestones/
  MILESTONES-INDEX.md       Master index (one row per milestone)
  MS-001-short-name.md      One file per milestone
  MS-002-short-name.md
  ...
```

- IDs are `MS-XXX`. Read the index, find the highest number, increment by 1.
- IDs are permanent. Never renumber. Gaps are fine.

## Milestone file template

```markdown
# MS-XXX: Title

**Status:** proposed | active | achieved | dropped | superseded
**Owner:** [name/role]
**Depends on:** (other MS-XXX refs, if any)

## Outcome
One paragraph describing what this milestone represents and why it matters.

## Measuring success
- [ ] Criterion 1 (each evaluable as true/false)
- [ ] Criterion 2
- [ ] Criterion linked to artifact: `strategy/narrative-arc.md` finalized

## Non-goals
- What this milestone is explicitly NOT
- Second explicit exclusion

## Contributing work items
- US-012 — Landing page redesign
- BL-007 — Analytics tracking

## Notes
Free-form log of decisions, scope changes, blockers encountered.

---

## Changelog
| Version | Date       | Change summary       |
|---------|------------|----------------------|
| 1.0     | YYYY-MM-DD | Initial draft        |
```

## Status taxonomy

| Status       | Meaning                                                                  |
|--------------|--------------------------------------------------------------------------|
| `proposed`   | Drafted, not yet committed. Appears in "Later".                          |
| `active`     | Currently being driven. Appears in "Now". Can be multiple.               |
| `achieved`   | All criteria met; user confirmed. Terminal state.                        |
| `dropped`    | Abandoned with rationale in Notes. Terminal state.                       |
| `superseded` | Replaced by a newer milestone. Links to successor in Notes. Terminal.    |

## Operations

### `add` — Create a new milestone

1. Read `docs/milestones/MILESTONES-INDEX.md`. If it does not exist, create it with this header:

```markdown
# Milestones Index

| ID | Title | Status | Owner | Short summary |
|----|-------|--------|-------|---------------|
```

2. Find the highest existing `MS-XXX` in the index. Increment by 1. If the index is empty, start at `MS-001`.
3. Ask the user (one question at a time, per SweetClaude interaction model):
   - Title (short, descriptive, 2-5 words)
   - Outcome (one paragraph — what "achieved" looks like)
   - Measuring success criteria: ask for a list. For each criterion, offer: "Link this to a canonical artifact path? (optional, e.g. `strategy/narrative-arc.md`)"
   - Non-goals: require at least one. If the user offers none, prompt: "What is this milestone explicitly NOT? A non-goals list with zero items is a scope red flag."
   - Depends on: list of other MS-XXX refs (optional)
   - Owner: default to the value of `owner` in `.sweetclaude/state/phase.yaml` if present; otherwise prompt.
4. Default `Status:` to `proposed`. Ask the user only if they indicate otherwise.
5. Write the file at `docs/milestones/MS-XXX-<slug>.md` using the milestone template from the previous section, filling in all fields. `<slug>` is a dash-lowercased version of the title (e.g., "Exit Stealth" → `exit-stealth`).
6. Append a row to `MILESTONES-INDEX.md`:

```
| MS-XXX | [Title](MS-XXX-slug.md) | proposed | Owner | One-sentence outcome summary |
```

7. Tell the user: "Added MS-XXX: {title}. Status: proposed. File: docs/milestones/MS-XXX-{slug}.md"
