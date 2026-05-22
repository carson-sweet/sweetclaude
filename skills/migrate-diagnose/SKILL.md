---
name: sweetclaude:migrate-diagnose
description: "Redirects to sweetclaude:doctor. File diagnostics are now part of the doctor system."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:migrate-diagnose" 2>/dev/null || true`

# Migrate Diagnose

> **This skill has been replaced by `/sweetclaude:doctor`.** Doctor includes file diagnostics checks (category: `file_diagnostics`) with the same frontmatter validation plus a full safety model.

Invoke `sweetclaude:doctor` now.
