---
spdx-license: AGPL-3.0-or-later
name: _health
user-invocable: false
description: Consistency scan and version check. Normally called by session-preflight.sh hook. Called inline by /sweetclaude when hook_last_ran is stale (> 2h).
---

# Health Check

Run the health check script inline. Called when `hook_last_ran` is stale — covers the case where the skill is invoked outside a normal session start.

## Step 1: Run the check

```bash
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
SCRIPT=$(find ~/.claude -name "sweetclaude-health-check.sh" 2>/dev/null | head -1)
if [ -z "$SCRIPT" ]; then
  echo "HEALTH_CHECK_SCRIPT_MISSING"
else
  PROJECT_DIR="$PROJECT_DIR" bash "$SCRIPT" 2>/dev/null \
    && echo "HEALTH_CHECK_COMPLETE" \
    || echo "HEALTH_CHECK_FAILED"
fi
```

If `HEALTH_CHECK_SCRIPT_MISSING`:
> "Health check script missing. Run `/sweetclaude:update` to reinstall."
Stop.

## Step 2: Report result to caller

After the script runs, read `.sweetclaude/state/sweetclaude.yaml` and return the updated values to the orchestrator:
- `framework.consistency.status`
- `framework.update.available`

The orchestrator will act on these values in Steps 6 and 7 of its decision tree.
