---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Consistency scan and version check."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:_health" 2>/dev/null || true`

# Health Check

Run the health check script inline. Called when `hook_last_ran` is stale — covers the case where the skill is invoked outside a normal session start.

## Step 1: Run the check

```bash
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
SCRIPT=~/.claude/hooks/sweetclaude/sweetclaude-health-check.sh
if [ ! -f "$SCRIPT" ]; then
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

## Step 3: v4 storage lint rules (delegated to doctor.py)

Run `doctor.py scan` with the `--category` flag to run only `storage_lint` checks:

```bash
python3 ~/.claude/scripts/sweetclaude/doctor.py scan --project-dir . --category storage_lint 2>/dev/null
```

Parse the JSON output. If it contains `"error": "not-configured"`, skip lint (not a SweetClaude project). Otherwise, read `findings` from the result.

If any findings exist, render them in the existing _health format:

```
## v4 Lint Findings
- {finding.id}: {finding.detail}
```

If no findings: `## v4 Lint: OK`

Surface any findings to the caller. If invoked from `big-picture` or `project-backlog-triage`, print findings before the skill's normal output.

## Step 3a: product_base source-of-truth drift check (delegated to doctor.py)

Run `doctor.py scan` with the `--category` flag to run only `state_integrity` checks:

```bash
python3 ~/.claude/scripts/sweetclaude/doctor.py scan --project-dir . --category state_integrity 2>/dev/null
```

Parse the JSON output. If the command fails (crash, timeout, or `"error"` in JSON), report informational and continue — non-blocking.

Filter findings to those with id prefix `state-integrity:product-base-drift`. If any exist, render:

```
## product_base divergence
- {finding.detail}
- Fix: re-run the session-state regen hook (or open a new session).
```

If no drift findings: no output (silent pass).
