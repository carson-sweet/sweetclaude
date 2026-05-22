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

Run `doctor.py scan` and filter findings to the `storage_lint` category. This avoids duplicating lint rules — they exist only in `scripts/doctor.py`.

```bash
python3 scripts/doctor.py scan --project-dir . 2>/dev/null
```

Parse the JSON output. If it contains `"error": "not-configured"`, skip lint (not a SweetClaude project). Otherwise, filter `findings` to entries where `category == "storage_lint"`.

If any storage_lint findings exist, render them in the existing _health format:

```
## v4 Lint Findings
- {finding.id}: {finding.detail}
```

If no storage_lint findings: `## v4 Lint: OK`

Surface any findings to the caller. If invoked from `big-picture` or `project-backlog-triage`, print findings before the skill's normal output.

## Step 3a: product_base source-of-truth drift check

`paths.product_base` is recorded in two places: `.sweetclaude/artifact-privacy.yaml` (authoritative) and `.sweetclaude/state/session-state.yaml` (derived snapshot). They MUST match. If they diverge, a skill made a decision based on stale session-state — surface it.

```python
import pathlib, yaml

privacy_path = pathlib.Path('.sweetclaude/artifact-privacy.yaml')
session_path = pathlib.Path('.sweetclaude/state/session-state.yaml')
mismatch = None

if privacy_path.exists() and session_path.exists():
    try:
        privacy = yaml.safe_load(privacy_path.read_text()) or {}
        session = yaml.safe_load(session_path.read_text()) or {}
        authoritative = (privacy.get('categories') or {}).get('product', {}).get('base_path')
        snapshot = (session.get('paths') or {}).get('product_base')
        if authoritative and snapshot and authoritative.rstrip('/') != snapshot.rstrip('/'):
            mismatch = (authoritative, snapshot)
    except yaml.YAMLError:
        pass

if mismatch:
    print(f"## product_base divergence")
    print(f"- artifact-privacy.yaml (authoritative): {mismatch[0]}")
    print(f"- session-state.yaml (snapshot):        {mismatch[1]}")
    print(f"- Fix: re-run the session-state regen hook (or open a new session).")
```

Surface the divergence inline if present. Non-blocking — informational.
