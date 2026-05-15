---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Produce a concise 'where we are' summary: current phase, active work item, last 3 commits, checkpoint state, and any open flags."
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

# Open flags (improvement register)
tail -10 .sweetclaude/state/improvement-register.md 2>/dev/null || echo "NO_REGISTER"
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

### Checkpoint
{checkpoint_next if set, or "No checkpoint — clean slate"}

### Open flags
{improvement register entries if any, or "None"}
```

Keep each section to 3–5 lines maximum. This is a quick orientation, not a full status report. For full status, run `/sweetclaude:status`.

## Auto-trigger rule

This skill auto-fires (as a check-in, not a full recap) when:
- Session starts AND `checkpoint_next` is set in session state — surface the checkpoint before anything else
- A detour concludes after 5+ turns — see Context Continuity in the interaction model

In auto-trigger mode, produce only the Checkpoint section plus one sentence: "We were in the middle of {X}. Ready to pick up?"
