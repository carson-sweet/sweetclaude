---
name: product/backlog
description: "Manage deferred work. Add, review, prioritize, or groom backlog items. Each item gets its own file with substantive initial thinking, not just a title. Tracks what's been parked and why, surfaces items when they become relevant."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Backlog Management

Manage backlog: $ARGUMENTS

## Routing

When adding items, classify first:
- **Technical items** (bugs, feature requests, tech debt, test gaps) → `docs/backlog/`
- **Strategic items** (product ideas, feature concepts, strategic initiatives, market opportunities) → `strategy/`. Tell the user: "That's a strategic item — I'll capture it in strategy/ instead of docs/backlog/."

Never silently put a non-technical item in docs/backlog/.

## Structure

```
docs/backlog/
  BACKLOG-INDEX.md          # Master index with priority, summary, links
  BL-001-short-name.md      # Detail file per item
  BL-002-short-name.md
  ...
```

## Adding a Backlog Item

### Step 1: Assign the next BL number
Read `BACKLOG-INDEX.md`, find the highest BL-XXX number, increment by 1.

### Step 2: Determine priority
Ask the user if not obvious from context:
- **P1** — Should be next after current milestone ships
- **P2** — Important but not urgent
- **P3** — Nice to have / exploratory
- **SPIKE** — Research needed before sizing

### Step 3: Write the detail file
Create `BL-XXX-short-descriptive-name.md`:

```markdown
# BL-XXX: Title

**Priority:** P1/P2/P3/SPIKE
**Depends on:** (other backlog items or user stories, if any)

## Summary
One paragraph describing what this is and why it matters.

## Initial Thinking
- What the implementation might look like
- Key technical decisions
- Dependencies and prerequisites
- Risks or open questions
- Architecture implications — does this affect the data model, API, or infrastructure?
- Connection to other backlog items

## Open Questions
- Unresolved questions that need answers before this can be sized
```

Always include substantive initial thinking — not just a title. Capture context while it's fresh. Initial thinking written during the conversation is 10x more valuable than reconstructing it later.

### Step 4: Update the index
Add a row to `BACKLOG-INDEX.md`, grouped by category:
```
| BL-XXX | Short description | Priority | [BL-XXX](BL-XXX-short-name.md) |
```

### Step 5: Confirm
Tell the user: "Added BL-XXX to the backlog: [title]. [one-sentence summary]."

## Reviewing the Backlog

When the user asks to review:
1. Read `BACKLOG-INDEX.md`
2. Summarize: total items, count by priority, any stale items
3. Identify items now unblocked (dependencies completed)
4. Suggest re-prioritization if project context has changed
5. Flag items that overlap or could be combined

## Updating a Backlog Item

1. Read the existing detail file
2. Update the relevant sections
3. Update the index if priority or title changed
4. Note what changed and why at the bottom of the detail file

## Promoting to Active Work

When a backlog item is ready to be built:
1. Move it to the project plan as an active task
2. Mark it in the index (strikethrough or status column)
3. The detail file becomes the starting brief for design/planning

## Rules

- Every item gets a file. The index is just an index.
- BL numbers are permanent. Never renumber. Leave gaps.
- Group by category in the index, not by date or priority alone.
- Link dependencies — if BL-013 depends on BL-010, say so in both files.
- Spikes are research tasks that produce a recommendation, not work items.
