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
RUNNER=~/.claude/scripts/sweetclaude/migrations/runner.py
if [ ! -f "$RUNNER" ]; then
  echo "ERROR: migration runner not found at $RUNNER. Run /sweetclaude:update to install the latest framework."
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
SNAPSHOT_OUT=$(python3 ~/.claude/scripts/sweetclaude/migrations/run_snapshot.py "$RUNNER" .)
```

- `SNAPSHOT_FAILED|<reason>` → abort. Report to user: `"Cannot create pre-migration safety snapshot: <reason>. Migration not started. Resolve the issue (commonly: free disk space, git repo state) and re-run."` Stop.
- `SNAPSHOT_OK|<json>` → parse `SNAPSHOT_OUT` to extract the JSON portion (everything after the first `|`); save as `SNAPSHOT_JSON` for use in Steps 3/4. Continue.

## Step 2: Run the migration

```bash
MIGRATE_OUT=$(python3 ~/.claude/scripts/sweetclaude/migrations/run_migrate.py "$RUNNER" .)
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

Clear both pending markers — the migration-decision marker (BL-068) AND the drift-decision marker (so the next session's drift-gate scans fresh against the migrated state instead of re-surfacing the pre-migration prompt):

```bash
rm -f .sweetclaude/state/pending-migration-decision.yaml \
       .sweetclaude/state/pending-drift-decision.yaml 2>/dev/null || true
```

Done.

### Step 4b: Initiate rollback

Prompt:

> Rollback will discard all migration changes and restore the project to `<snap.git_tag>`. This cannot be undone. Type `rollback` to confirm.

Wait for the user to type exactly `rollback`. Then:

```bash
ROLLBACK_OUT=$(python3 ~/.claude/scripts/sweetclaude/migrations/run_rollback.py "$RUNNER" "$SNAPSHOT_JSON" .)
```

Report success or failure. Clear the pending-migration-decision marker, but PRESERVE `pending-drift-decision.yaml` — rollback restored the pre-migration state which still has drift, so drift-gate must re-surface it next session.

```bash
rm -f .sweetclaude/state/pending-migration-decision.yaml 2>/dev/null || true
```

### Step 4c: Defer decision

(Only available if `hooks/migration-decision-reminder.sh` from BL-068 is installed.) Write `.sweetclaude/state/pending-migration-decision.yaml` with snapshot data and `turn_count: 0`. The hook will inject reminders every prompt and hard-block at turn 10 until Accept or Initiate rollback.

---

## Step 5: Legacy consolidation (phase.yaml + skills.yaml → sweetclaude.yaml)

Only reached if `STATE=legacy` in Step 0.

This path uses the one-shot consolidation script that has shipped since v3.18 — it does NOT use the runner (the runner handles single-file or directory migrations; consolidation across files is a different shape).

```bash
INSTALLED=$(python3 -c "
import json, os
try:
    path = os.path.join(os.path.expanduser('~'), '.claude', 'plugins', 'installed_plugins.json')
    d = json.load(open(path))
    entries = []
    for k, v in d.get('plugins', {}).items():
        if k.lower() == 'sweetclaude':
            entries.extend(v if isinstance(v, list) else [v])
    user_entries = [e for e in entries if e.get('scope') == 'user']
    user_entries.sort(key=lambda e: e.get('lastUpdated', ''), reverse=True)
    print(user_entries[0].get('version', 'unknown') if user_entries else 'unknown')
except Exception:
    print('unknown')
" 2>/dev/null)

SCRIPT=~/.claude/scripts/sweetclaude/migrate-to-sweetclaude-yaml.py
if [ ! -f "$SCRIPT" ]; then
  echo "Consolidation script not found at $SCRIPT. Run /sweetclaude:update."
  exit 1
fi

python3 "$SCRIPT" --project-dir . --installed-version "$INSTALLED"
```

On success: report `"All set — consolidated to unified state format. Your old files are archived in .sweetclaude/state/archive/."`. Then tell the caller to re-invoke `bootstrap` so the orchestrator continues — the next entry will hit Step 0 with `STATE=unified` and apply any runner-driven schema migrations.

On error: `"Consolidation failed. Your original files are untouched. Run /sweetclaude:fix-sweetclaude to debug."` Stop.
