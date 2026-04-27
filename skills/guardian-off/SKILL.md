---
name: guardian-off
description: Disable the Protocol Guardian for the current session
---

# Protocol Guardian — Disable

**1. Remove the guardian flag:**
Run:
```bash
rm -f .sweetclaude/state/guardian-enabled
```

**2. Confirm:**
> "Protocol Guardian disabled."

`session-guardian.json` is left in place for reference. Obligation tasks remain visible but are no longer enforced.
