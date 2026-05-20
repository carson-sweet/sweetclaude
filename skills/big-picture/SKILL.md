---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Show the full project at a glance — roadmap pipeline with releases, epics, and stories. Trigger on: 'big picture', 'whole project status', 'full status', 'what's the full state', 'project overview', 'where is everything', 'show me everything'."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:big-picture" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: if pre-loaded state above shows STATE_NOT_FOUND, or neither .sweetclaude/state/sweetclaude.yaml nor .sweetclaude/state/phase.yaml exists, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Big Picture

Render the full project at a glance. No background agents — reads state directly.

## Step 0: v4 lint check

Before rendering, run the v4 lint rules from `sweetclaude:_health` Step 3 inline. If any findings are present, surface them before the normal output:

```
## v4 Storage Warnings
- counter-drift:story (stored=3, max_id_seen=5)
- done-status-mismatch:STORY-002-foo.md has status=done but is not in done/
```

Proceed to Step 1 regardless of findings — this is informational, not blocking.

## Step 1: Schema check

Use `phase_schema_version` from pre-loaded session state above:
- If absent or `1`: warn — "Your config is on schema v1. Run `/sweetclaude:update` to upgrade." Stop.
- If `2`: proceed.

## Step 2: Detect roadmap mode

Check whether the roadmap system exists:

```bash
ls docs/product/roadmap/epics/EP-*.md 2>/dev/null | head -1
```

- If output is non-empty → **Roadmap mode** (Step 3a)
- If empty → **Legacy milestone mode** (Step 3b)

## Step 3a: Roadmap pipeline (cache-backed)

Rebuild the cache, then run all three queries:

```bash
python3 scripts/cache.py --project-dir . --rebuild 2>/dev/null
python3 scripts/cache.py --project-dir . --query releases-compact 2>/dev/null
python3 scripts/cache.py --project-dir . --query summary 2>/dev/null
python3 scripts/cache.py --project-dir . --query backlog --unlinked-only 2>/dev/null
```

- `releases-compact` — compact hierarchy (id, title, status, criteria_done/total, story list) for the tree display; use this instead of `releases` to avoid output truncation on large projects
- `summary` — pre-computed totals for the bottom summary line (**use these numbers, do not count from the releases JSON**)
- `backlog --unlinked-only` — open items with no epic, for the unlinked section (top 5 only)

Skip to Step 4a.

## Step 3b: Legacy milestone pipeline

Read artifact path:

```bash
product_base=$(python3 -c "
import yaml, sys
d = yaml.safe_load(open('.sweetclaude/state/session-state.yaml')) or {}
print(d.get('paths', {}).get('product_base', '.sweetclaude/product'))
" 2>/dev/null || echo ".sweetclaude/product")

echo "PRODUCT_BASE=$product_base"
ls ${product_base}/milestones/MS-*.md 2>/dev/null || echo "NO_MILESTONES"
```

If output contains `NO_MILESTONES`, output:
> No milestones or roadmap configured. Run `/sweetclaude:product-milestones` to create milestones, or `/sweetclaude:epics add` to create your first epic.

Stop.

Build the pipeline with the inline Python block from the legacy v4.0.x big-picture skill (milestone toposort, work item nesting, summary counts). Skip to Step 4b.

## Step 4a: Render roadmap

Output in this format. Use clean markdown — no ANSI codes, no horizontal dividers.

---

**{project name}** · {version_stage}

### Roadmap

For each release (ordered by ID):

```
REL-{NNN}  {title}  [{status}]
```

For each epic within that release (ordered by ID):

```
├── EP-{NNN}  {title}  [{status}]
│   Objective: {objective (truncate to 80 chars)}
│   Criteria: {done}/{total} complete
│   ├── {STORY-NNN}  {title (truncate to 50 chars)}  [{status}]
│   ├── {STORY-NNN}  {title}  [{status}]
│   └── {STORY-NNN}  {title}  [{status}]
```

Use `✓` for done stories and done epics. Use `├──` / `└──` connectors.

After all releases, if there are backlog items not linked to any epic, show:

```
### Unlinked Backlog

{N} items not assigned to an epic. Run `/sweetclaude:epics link {ITEM-ID} EP-NNN` to assign.
```

Only show the count and the top 5 items by priority. Do not list the full backlog.

### Summary line

After the roadmap:

`{total releases} releases · {active epics} active · {total stories across all epics} stories`

---

Then output:

### Active Work

- If there is an `active_work_item` set in pre-loaded session state with a non-null `id`, output:
  > Currently in progress: **{id}** — {title} [{phase}]
- Otherwise:
  > No work item currently active. Run `/sweetclaude:go` to pick up where you left off.

---

Output nothing else. No closing question. No framework health. No trailing prompts.

## Step 4b: Render milestones (legacy)

**{project name}** · {version_stage}

### Milestone Pipeline

`{total} milestones · {done} done · {active} active · {remaining} remaining`

Then output the pipeline lines verbatim, preserving `↓`, `├──`, `└──`, and status annotations.

If no milestones were produced (empty pipeline), output:
> No milestones found. Run `/sweetclaude:product-milestones` to create your first milestone.

---

Then output:

### Active Work

- If there is an `active_work_item` set in pre-loaded session state with a non-null `id`, output:
  > Currently in progress: **{id}** — {title} [{phase}]
- Otherwise:
  > No work item currently active. Run `/sweetclaude:go` to pick up where you left off.

---

Output nothing else. No closing question. No framework health. No trailing prompts.
