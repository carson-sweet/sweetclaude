---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Migration orchestrator. Wraps the runner with snapshot, recovery menus, and end-of-session report."
---

# SweetClaude Migration

Internal skill. Called by `bootstrap` Step 5b when the registry-driven drift scan detects out-of-version state. Wraps the migration runner with the safety scaffolding from Gaps #5/#6:

- Pre-migration snapshot (tarball + git tag) before any handler runs.
- Recoverable-error menus surfacing handler-provided options.
- End-of-session report with Accept / Initiate rollback (+ Defer if BL-068 hook is installed).
- User-initiated rollback with explicit typed confirmation.

## Step 0: Detect state and route

```bash
RUNNER=$(find ~/.claude -name "runner.py" -path "*/migrations/*" 2>/dev/null | head -1)
if [ -z "$RUNNER" ]; then
  echo "ERROR: migration runner not found. Run /sweetclaude:update to install the latest framework."
  exit 1
fi

if [ -f .sweetclaude/state/sweetclaude.yaml ]; then
  echo "STATE=unified"
elif [ -f .sweetclaude/state/phase.yaml ] || [ -f .sweetclaude/state/skills.yaml ]; then
  echo "STATE=legacy"
else
  echo "STATE=none"
fi
```

- `STATE=unified` → Step 1 (runner path).
- `STATE=legacy` → Step 5 (one-shot consolidation, then re-enter via re-run).
- `STATE=none` → report `"Nothing to migrate. Run /sweetclaude:setup to initialize."` and stop.

---

## Step 1: Create pre-migration snapshot

```bash
python3 - "$RUNNER" << 'PY'
import sys, json
sys.path.insert(0, sys.argv[1].rsplit('/', 1)[0])
from runner import MigrationRunner
runner = MigrationRunner(project_dir=".")
try:
    snap = runner.create_snapshot()
except RuntimeError as e:
    print(f"SNAPSHOT_FAILED|{e}")
    sys.exit(1)
print(f"SNAPSHOT_OK|{json.dumps(snap.to_dict())}")
PY
```

- `SNAPSHOT_FAILED|<reason>` → abort. Report to user: `"Cannot create pre-migration safety snapshot: <reason>. Migration not started. Resolve the issue (commonly: free disk space, git repo state) and re-run."` Stop.
- `SNAPSHOT_OK|<json>` → save the SnapshotInfo JSON for use in Steps 3/4. Continue.

## Step 2: Run the migration

```bash
python3 - "$RUNNER" << 'PY'
import sys, json
sys.path.insert(0, sys.argv[1].rsplit('/', 1)[0])
from runner import MigrationRunner
runner = MigrationRunner(project_dir=".")
results = runner.run()
out = []
for r in results:
    out.append({
        "file_key": r.file_key,
        "success": r.success,
        "failure_mode": r.failure_mode,
        "failure_details": r.failure_details,
        "on_disk_version_before": r.on_disk_version_before,
        "on_disk_version_after": r.on_disk_version_after,
        "target_version": r.target_version,
        "recovery_menu": r.recovery_menu,
    })
print(json.dumps(out))
PY
```

Parse the JSON results. For each result:

- `success: true` → record in summary.
- `failure_mode: "recoverable"` → Step 3a (present `recovery_menu`).
- `failure_mode: "chain_broken"` or `"out_of_support_window"` → Step 3b (re-onboarding routing — bootstrap's Case B owns the decision; here we surface the failure and stop, letting bootstrap re-fire and route).
- Any other `failure_mode` → Step 3c (diagnostic + rollback offer).

## Step 3a: Recoverable failure — present handler menu

The handler-provided `recovery_menu` already includes the universal `Skip this file` and `Initiate rollback` entries (appended by the runner). Present via **AskUserQuestion**:

> `<recovery_menu.message>`
>
> (If `recovery_menu.current_id` is set: include `Current item: <current_id>`.)
>
> Options: `<recovery_menu.options[*].label>`

On user choice:
- `Initiate rollback` → Step 4b (typed confirmation, then rollback).
- `Skip this file` → re-invoke runner with the skip recorded; resume migration. (Resume semantics: out of scope for v3.66.0 if the runner doesn't support skip-and-continue yet. In that case, treat Skip as "abort this migration; don't roll back; user can manually edit and re-run." Document this limitation in the report.)
- Handler-specific action → the calling skill encodes the action (e.g., `set_type=story`) into params and re-invokes the runner.

## Step 3b: chain_broken / out_of_support_window — exit to bootstrap

```
echo "Migration cannot complete: <failure_mode> on <file_key>. Bootstrap will route to re-onboarding on next session entry."
```

Stop. User re-opens session; bootstrap Step 5b's Case B fires with the re-onboarding option.

## Step 3c: Other failures — diagnostic + rollback offer

Present:

> `Migration failed: <failure_mode> on <file_key>.`
> `Details: <failure_details>`

Then **AskUserQuestion**:

> Options:
> - `Initiate rollback` — restore to pre-migration state.
> - `Leave as-is and exit` — abort without rollback; manual recovery required.

## Step 4: End-of-session report (all results processed)

If every result is success, present the standardized report:

```
Migration complete.

  <per-category counts, e.g. "phase.yaml: v1→v2 (1 file)">

State file changes:
  <list of files migrated with from/to versions>

Pre-migration snapshot:
  tar:  <snap.tarball_path>
  git:  tag <snap.git_tag>

Review the changes. Then:
  [Accept]              Migration is good. Keep changes.
  [Initiate rollback]   Restore project to pre-migration state.
  [Defer decision]      Inspect manually; decide later. Snapshot stays available
                        for 24h. (Only shown if BL-068 hook is installed.)
```

Present via **AskUserQuestion**.

### Step 4a: Accept

Clear the pending-migration-decision marker if it exists. Done.

### Step 4b: Initiate rollback

Prompt:

> Rollback will discard all migration changes and restore the project to `<snap.git_tag>`. This cannot be undone. Type `rollback` to confirm.

Wait for the user to type exactly `rollback`. Then:

```bash
python3 - "$RUNNER" "$SNAPSHOT_JSON" << 'PY'
import sys, json
sys.path.insert(0, sys.argv[1].rsplit('/', 1)[0])
from runner import MigrationRunner, SnapshotInfo
snap_data = json.loads(sys.argv[2])
snap = SnapshotInfo(**snap_data)
runner = MigrationRunner(project_dir=".")
ok, reason = runner.rollback(snap)
print(f"ROLLBACK_{'OK' if ok else 'FAIL'}|{reason or ''}")
PY
```

Report success or failure. Clear the pending-decision marker.

### Step 4c: Defer decision

(Only available if `hooks/migration-decision-reminder.sh` from BL-068 is installed.) Write `.sweetclaude/state/pending-migration-decision.yaml` with snapshot data and `turn_count: 0`. The hook will inject reminders every prompt and hard-block at turn 10 until Accept or Initiate rollback.

---

## Step 5: Legacy consolidation (phase.yaml + skills.yaml → sweetclaude.yaml)

Only reached if `STATE=legacy` in Step 0.

This path uses the one-shot consolidation script that has shipped since v3.18 — it does NOT use the runner (the runner handles single-file or directory migrations; consolidation across files is a different shape).

```bash
INSTALLED=$(python3 -c "
import json
try:
    d = json.load(open('$HOME/.claude/plugins/installed_plugins.json'))
    e = [v for k,v in d.get('plugins',{}).items() if 'sweetclaude' in k.lower()]
    print(e[0][0].get('version','unknown') if e and e[0] else 'unknown')
except: print('unknown')
" 2>/dev/null)

SCRIPT=$(find ~/.claude -name "migrate-to-sweetclaude-yaml.py" 2>/dev/null | head -1)
if [ -z "$SCRIPT" ]; then
  echo "Consolidation script not found. Run /sweetclaude:update."
  exit 1
fi

python3 "$SCRIPT" --project-dir . --installed-version "$INSTALLED"
```

On success: report `"All set — consolidated to unified state format. Your old files are archived in .sweetclaude/state/archive/."`. Then tell the caller to re-invoke `bootstrap` so the orchestrator continues — the next entry will hit Step 0 with `STATE=unified` and apply any runner-driven schema migrations.

On error: `"Consolidation failed. Your original files are untouched. Run /sweetclaude:fix-sweetclaude to debug."` Stop.
