---
name: sweetclaude-work-router
description: "Identify the type of work (code or strategy), classify the specific work type, and route to the correct pipeline entry point and skill track. Use at the start of any new work item. Prevents non-technical items from landing in docs/backlog/."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Work-Type Router

Determine what kind of work we're doing, which track it belongs to, and enter the pipeline at the right phase.

## Process

1. **Ask or detect.** If the user hasn't stated the work type, propose:
   > "This looks like [type] ([track] track) based on [reasoning]. That means we'd start at [phase]. Sound right?"

2. **Route based on type:**

### Code Track

| Work Type | Entry Phase | First Action |
|---|---|---|
| Net-new feature | DISCOVER | Brainstorm the concept, research the space |
| Bug fix | DEFINE | Reproduce the bug, characterize expected vs actual |
| Feature enhancement | DEFINE | Define what exists, what needs to change, why |
| Iteration / tech debt | DEFINE | Define what's being improved, why, what "better" means |

### Strategy Track

| Work Type | Entry Phase | First Action |
|---|---|---|
| Research paper | DISCOVER | First principles — thesis, key concepts, novelty, objections |
| Strategic positioning | DISCOVER | Landscape scan, framing options, terminology decisions |
| Competitive analysis | DISCOVER | Landscape mapping, SWOT, gap identification |
| Meeting prep | DEFINE | Who, when, purpose → gather context, draft deliverables |
| Market messaging | DEFINE | Audience definition, value prop, narrative drafting |
| Biz planning | DISCOVER | Opportunity mapping, path analysis, frameworks |
| File reconciliation | DEFINE | Inventory existing files, categorize, plan synthesis |

3. **Update state.** Write work type, track, and entry phase to `state/phase.yaml`:
   ```yaml
   phase: DISCOVER
   work_type: research-paper
   track: strategy
   ```

4. **Surface skills.** Read `phase-skills.yaml` and surface skills from the appropriate track (`code:` or `strategy:`) for the current phase.

5. **Escalation.** At any point, if the work reveals deeper issues:
   > "This [type] seems to point to a deeper [gap]. Want to escalate to DISCOVER and investigate before continuing?"

   If yes, re-route to DISCOVER scoped to the specific problem.

## Backlog Guard

When the user wants to add something to the backlog:

- **Technical items** (bugs, feature requests, tech debt, test gaps) → `docs/backlog/`. Proceed normally.
- **Non-technical items** (product ideas, strategic initiatives, market opportunities, positioning thoughts) → redirect to `strategy/`:
  > "That's a strategic item, not a technical backlog item. I'll capture it in `strategy/{appropriate-category}/` instead of `docs/backlog/`. OK?"

  On confirmation, write to the appropriate strategy subdirectory. If the category isn't clear, ask.

**Never silently put a non-technical item in docs/backlog/.** The backlog is for work that produces or modifies code.

## Mid-Stream Detection

If the nature of work shifts during a session (e.g., a bug fix reveals a feature gap, or research pivots to positioning):
- Detect the shift from conversation context
- Propose rerouting: "This is becoming [new type] ([track] track). Want to shift to [new phase]?"
- Preserve previous work state on reroute

## Cross-Track Detection

If the user starts code work but the conversation reveals strategic prerequisites (e.g., "we should figure out our positioning before building this feature"):
> "This needs strategic work before code work. Want to switch to the strategy track for [type], then come back to code when the strategic foundation is set?"

Similarly, if strategy work reveals something that needs building:
> "This positioning depends on a capability we haven't built. Want to create a code-track work item for it?"

## Tech Debt Note

Tech debt clearance is iteration work (code track). It follows:
DEFINE → DESIGN → IMPLEMENT (lock behavior with tests first, then refactor) → VERIFY → SHIP.
