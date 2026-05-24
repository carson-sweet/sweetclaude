---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Produce a concise 'where we are' summary: current phase, active work item, last 3 commits, checkpoint state, and any open flags."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:recap" 2>/dev/null || true`

# Recap

This skill has been absorbed into `/sweetclaude:status`.

The session view, checkpoint auto-trigger, and detour check-in behavior all live in the status skill now.

Invoke `/sweetclaude:status` (no argument) now:
