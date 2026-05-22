---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Redirects to sweetclaude:doctor. Hook diagnostics are now part of the doctor system."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:hook-repair" 2>/dev/null || true`

# Hook Repair

> **This skill has been replaced by `/sweetclaude:doctor`.** Doctor includes hook health checks (category: `hook_health`) with the same diagnostics plus a full safety model.

Invoke `sweetclaude:doctor` now.
