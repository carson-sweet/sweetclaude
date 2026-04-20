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
