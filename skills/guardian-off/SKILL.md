---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Disable the Protocol Guardian for the current session"
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Protocol Guardian — Disable

**1. Check if guardian is active:**
Run:
```bash
if [ ! -f .sweetclaude/state/guardian-enabled ]; then
  echo "Protocol Guardian was not active."
  exit 0
fi
```
If the flag file does not exist, report: "Protocol Guardian was not active." and stop.

**2. Remove the guardian flag:**
Run:
```bash
rm -f .sweetclaude/state/guardian-enabled
```

**3. Mark session state as disabled:**
If `.sweetclaude/state/session-guardian.json` exists, update the `enabled` field to `false`:
```bash
if [ -f .sweetclaude/state/session-guardian.json ]; then
  tmp=$(mktemp)
  jq '.enabled = false' .sweetclaude/state/session-guardian.json > "$tmp" && mv "$tmp" .sweetclaude/state/session-guardian.json
fi
```

**4. Confirm:**
> "Protocol Guardian disabled."

`session-guardian.json` is left in place for reference. Obligation tasks remain visible but are no longer enforced.
