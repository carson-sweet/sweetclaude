---
name: work-router
description: Identify the type of work (net-new feature, bug fix, enhancement, iteration) and route to the correct pipeline entry point. Use at the start of any new work item.
---

# Work-Type Router

Determine what kind of work we're doing and enter the pipeline at the right phase.

## Process

1. **Ask or detect.** If the user hasn't stated the work type, propose:
   > "This looks like a [type] based on [reasoning]. That means we'd start at [phase]. Sound right?"

2. **Route based on type:**

| Work Type | Entry Phase | First Action |
|---|---|---|
| Net-new feature | DISCOVER | Brainstorm the concept, research the space |
| Bug fix | DEFINE | Reproduce the bug, characterize expected vs actual |
| Feature enhancement | DEFINE | Define what exists, what needs to change, why |
| Iteration / tech debt | DEFINE | Define what's being improved, why, what "better" means |

3. **Update state.** Write work type and entry phase to `state/phase.yaml`.

4. **Escalation.** At any point, if the work reveals deeper issues:
   > "This [bug/enhancement/iteration] seems to point to a deeper [design flaw / architectural gap / missing capability]. Want to escalate to DISCOVER and investigate before continuing?"

   If yes, re-route to DISCOVER scoped to the specific problem and its ripple effects.

## Mid-Stream Detection

If the nature of work shifts during a session (e.g., a bug fix reveals a feature gap, or brainstorming pivots to implementation):
- Detect the shift from conversation context
- Propose rerouting: "This is becoming a [new type]. Want to shift to [new phase]?"
- Preserve previous work state on reroute

## Tech Debt Note

Tech debt clearance is iteration work. It follows the iteration lifecycle:
DEFINE → DESIGN → IMPLEMENT (lock behavior with tests first, then refactor) → VERIFY → SHIP.
