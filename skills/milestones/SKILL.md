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
