---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Session continuity — active work item, phase, checkpoint, recent commits, scratch files. For project health use /status; for the full delivery tree use /big-picture."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:recap" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Recap

Orient in one screen. Reads state files directly — no background agent.

## Entry

If pre-loaded state is `STATE_NOT_FOUND`, or neither `.sweetclaude/state/sweetclaude.yaml` nor `.sweetclaude/state/phase.yaml` exists: "This project is not configured for SweetClaude. Run `/sweetclaude:setup` to set it up." Stop.

## Step 1: Read current state

Session state is pre-loaded above. Use `active_work_item`, `deference`, `version_stage`, `checkpoint_next`, and `paths.product_base` from there directly.

Run inline — do NOT spawn a background agent:

```bash
# Recent commits
git log --oneline -3 2>/dev/null || echo "NO_GIT"

# Working tree
git status --short 2>/dev/null | head -10

# Checkpoint
tail -15 .sweetclaude/state/checkpoint.md 2>/dev/null || echo "NO_CHECKPOINT"

# Scratch directory (continuation files)
ls scratch/ 2>/dev/null | grep -iE "checkpoint|continue|resume|handoff" | head -5
```

## Step 2: Produce the recap

Output in this format. Use clean markdown — no box-drawing characters.

```
## SweetClaude Recap — {ISO date}

**Phase:** {active_work_item.phase or "none set"}
**Work item:** {active_work_item.id — active_work_item.title, or "none active"}
**Deference:** {deference}

### Recent commits
{last 3 git log lines, or "none"}

### Working tree
{uncommitted file count, or "clean"}

### Checkpoint
{checkpoint_next if set, or "No checkpoint — clean slate"}

### Scratch
{scratch continuation files if any, or omit section entirely}
```

Keep each section to 3–5 lines maximum. This is a quick orientation, not a full status report. For project health (roadmap, backlog, mode), run `/sweetclaude:status`. For the full delivery tree, run `/sweetclaude:big-picture`.

## Auto-trigger rule

This skill auto-fires (as a check-in, not a full recap) when:
- Session starts AND `checkpoint_next` is set in session state — surface the checkpoint before anything else
- A detour concludes after 5+ turns — see Context Continuity in the interaction model

In auto-trigger mode, produce only the Checkpoint section plus one sentence: "We were in the middle of {X}. Ready to pick up?"
