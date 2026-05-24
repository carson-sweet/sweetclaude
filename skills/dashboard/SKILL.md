---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Launch a local web dashboard showing roadmap, releases, epics, backlog, dependencies, git history, and skill activity."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:dashboard" 2>/dev/null || true`

# Dashboard

Launch a local read-only web dashboard for the current project.

Tabs align with the status view scopes spec (v3.1):
- **Roadmap** — milestone/epic/issue tree with derived status
- **Releases** — per-milestone detail with blockers and progress
- **Epics** — table with stored vs derived status, criteria, issue counts
- **Backlog** — priority horizon grouping (P0/P1/P2/P3/Unscheduled)
- **Dependencies** — blocked chains and unresolved references
- **Git** — commit log with item ID cross-references
- **Activity** — skill event timeline

## Step 1: Ensure cache is current

```bash
python3 scripts/cache.py --project-dir . --rebuild 2>/dev/null
```

## Step 2: Launch server

```bash
PORT=${1:-8411}
python3 scripts/dashboard.py --project-dir . --port "$PORT" &
DASH_PID=$!
sleep 1
if kill -0 "$DASH_PID" 2>/dev/null; then
  echo "DASHBOARD_RUNNING"
  echo "PID=$DASH_PID"
  echo "URL=http://127.0.0.1:$PORT"
else
  echo "DASHBOARD_FAILED"
fi
```

If `DASHBOARD_RUNNING`: open the browser and present:

```bash
open "http://127.0.0.1:$PORT" 2>/dev/null || xdg-open "http://127.0.0.1:$PORT" 2>/dev/null || true
```

> Dashboard running at **http://127.0.0.1:{PORT}** (PID {PID}). Press Ctrl+C in the terminal or close this session to stop it.

If `DASHBOARD_FAILED`:
> "Dashboard failed to start. Check that port {PORT} is available."

## Rules

- Read-write. Status changes via the dashboard use `write_status()` / `set_terminal()` with `source: manual`. Parent items with `source: auto` auto-sync from children; `source: manual` parents are immune to auto-sync.
- Runs on 127.0.0.1 only — not exposed to the network.
- Auto-rebuilds the cache on launch to ensure fresh data.
- Default port 8411. Pass a different port as an argument: `/sweetclaude:dashboard 8080`
