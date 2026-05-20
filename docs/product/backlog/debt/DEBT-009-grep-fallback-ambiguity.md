---
id: DEBT-009
type: debt
title: "grep fallback for sweetclaude.yaml is ambiguous"
status: new
priority: later
effort: s
epic: EP-010
tags: [self-hosting, sync, correctness]
origin: STORY-300 adversarial-caucus
created: 2026-05-18
updated: 2026-05-18
---

# grep fallback for sweetclaude.yaml is ambiguous

The PyYAML-absent fallback in `_read_phase()` uses `grep "^ *phase:"` which matches any `phase:` key at any indentation depth, not just `work.active.phase`. If `sweetclaude.yaml` gains a second `phase:` key (e.g., under `work.historical`), the grep could return the wrong value. The `head -1` mitigates this only if `work.active.phase` appears first in the file.

Best-effort fallback by design — PyYAML handles the structured case correctly. But the grep path could be tightened to match the expected indent depth or use a more specific pattern.

## Origin

STORY-300 adversarial caucus finding.
