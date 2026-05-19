---
id: DEBT-001
type: debt
title: "Sync script exit code hygiene"
status: new
priority: later
effort: s
epic: EP-010
tags: [self-hosting, sync, code-quality]
origin: STORY-300 code-review
created: 2026-05-18
updated: 2026-05-18
---

# Sync script exit code hygiene

Remove dead `|| echo "0"` in decision-log entry numbering (grep already handles empty output via the `[ -z "$LAST_NUM" ]` guard). Assign a distinct exit code for unknown arguments — currently exits 1, which collides with exit 1 (phase check blocked).

## Origin

STORY-300 code review nit N-1 and adversarial caucus finding.
