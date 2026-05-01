---
spdx-license: AGPL-3.0-or-later
description: "Manage deferred work. Add, review, prioritize, or groom backlog items. Each item gets its own file with substantive initial thinking, not just a title. Tracks what's been parked and why, surfaces items when they become relevant."
category: product
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Backlog Management

Manage backlog: $ARGUMENTS

## Environment Assessment

**Run this before anything else — including Artifact Path Resolution.**

### Step 1: Check for existing SweetClaude backlog

Read `.sweetclaude/artifact-privacy.yaml` to get `categories.product.base_path`. Check whether `{base_path}/backlog/` already contains `BL-*.md` files.

- If backlog files exist: returning user. Skip to **Routing** — normal operations apply. Do not re-run assessment.
- If empty or doesn't exist: first use. Continue to Step 2.

### Step 2: Look for existing backlog systems

```bash
# GitHub Issues
gh issue list --state open --limit 20 2>/dev/null | head -10 || true

# Linear, Jira, Notion references
grep -ri "linear.app\|jira\|atlassian\|notion.so" README* docs/ .sweetclaude/ 2>/dev/null | head -5

# Existing markdown todo/backlog files
find . -maxdepth 4 -name "*.md" | xargs grep -li "backlog\|todo\|to-do\|tasks" 2>/dev/null | grep -v ".sweetclaude" | head -10
```

### Step 3: Present findings and ask

If an existing system was detected:
> "I found what looks like an existing backlog or task tracking system: {what you found}. How do you want to proceed?
> 1. **Import** — migrate existing items into SweetClaude backlog files
> 2. **Start fresh** — ignore the old system, start clean
> 3. **Side by side** — keep both, just start adding new items here"

If nothing detected:
> "No existing backlog found. Ready to set up SweetClaude backlog tracking under {base_path}/backlog/. Go ahead?"

Wait for the user's answer before proceeding. If they choose **Import**, read the detected files/issues and create SweetClaude `BL-*.md` files from them. Then route normally.

---

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:on` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.product.base_path`. This is the base directory for all product artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. if base is `.sweetclaude/product`, milestones go to `.sweetclaude/product/milestones/MS-001.md`).

4. Write artifacts to those paths.

## Routing

Classify before adding:
- **Technical items** (bugs, feature requests, tech debt, test gaps) go to `{base_path}/backlog/`.
- **Strategic items** (product ideas, feature concepts, strategic initiatives, market opportunities) go to `strategy/`. Tell the user: "That is a strategic item. Capturing it in strategy/ instead of {base_path}/backlog/."

Never silently put a non-technical item in docs/backlog/.

## Structure

```
{base_path}/backlog/
  BACKLOG-INDEX.md          # Master index with priority, summary, links
  BL-001-short-name.md      # Detail file per item
  BL-002-short-name.md
  ...
```

## Adding a Backlog Item

### Step 1: Assign the next BL number
Read `{base_path}/backlog/BACKLOG-INDEX.md`, find the highest BL-XXX number, increment by 1.

### Step 2: Determine priority
If not obvious from context, use AskUserQuestion with these options:
- "P1" — next after current milestone ships
- "P2" — important but not urgent
- "P3" — nice to have / exploratory
- "SPIKE" — research needed before sizing

### Step 3: Write the detail file
Create `{base_path}/backlog/BL-XXX-short-descriptive-name.md`:

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

Always include substantive initial thinking, not just a title. Capture context while it is fresh. Initial thinking written during the conversation is far more valuable than reconstructing it later.

### Step 4: Update the index
Add a row to `{base_path}/backlog/BACKLOG-INDEX.md`, grouped by category:
```
| BL-XXX | Short description | Priority | [BL-XXX](BL-XXX-short-name.md) |
```

### Step 5: Confirm
Tell the user: "Added BL-XXX to the backlog: [title]. [one-sentence summary]."

## Reviewing the Backlog

When the user asks to review:
1. Read `{base_path}/backlog/BACKLOG-INDEX.md`.
2. Summarize: total items, count by priority, stale items.
3. Identify items now unblocked (dependencies completed).
4. Suggest re-prioritization if project context changed.
5. Flag items that overlap or could be combined.

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
- BL numbers are permanent. Never renumber. Gaps are fine.
- Group by category in the index, not by date or priority alone.
- Link dependencies. If BL-013 depends on BL-010, say so in both files.
- Spikes produce a recommendation, not deliverables.
