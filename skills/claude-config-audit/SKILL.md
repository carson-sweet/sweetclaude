---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Redirects to sweetclaude:doctor. Config compatibility checks are now part of the doctor system."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:claude-config-audit" 2>/dev/null || true`

# Claude Config Audit

> **This skill has been replaced by `/sweetclaude:doctor`.** Doctor includes config compatibility checks (category: `config_compat`) with the same 10 detection patterns plus a full safety model.

Invoke `sweetclaude:doctor` now.
