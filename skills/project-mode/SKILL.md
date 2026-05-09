---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Assess and shift project modes."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"

CURRENT_MODE=$(python3 -c "
import yaml
try:
    p = yaml.safe_load(open('$PWD/.sweetclaude/state/phase.yaml'))
    print(p.get('mode','flow'))
except:
    print('flow')
" 2>/dev/null || echo "flow")

# Artifact counts for assess output
python3 "${_sc_hooks}/sc-artifact-impl.py" \
  query "$SC_PROJECT_ROOT" "$SC_PRODUCT_BASE" "$SC_STATE_BASE" \
  issue sprint_id= status=backlog 2>/dev/null | \
  python3 -c "import json,sys; items=json.load(sys.stdin); print(f'BACKLOG_COUNT={len(items)}')" 2>/dev/null

python3 "${_sc_hooks}/sc-artifact-impl.py" \
  list "$SC_PROJECT_ROOT" "$SC_PRODUCT_BASE" "$SC_STATE_BASE" \
  issue 2>/dev/null | \
  python3 -c "import json,sys; items=json.load(sys.stdin); print(f'TOTAL_ISSUES={len(items)}')" 2>/dev/null

python3 "${_sc_hooks}/sc-artifact-impl.py" \
  query "$SC_PROJECT_ROOT" "$SC_PRODUCT_BASE" "$SC_STATE_BASE" \
  sprint status=active 2>/dev/null | \
  python3 -c "import json,sys; items=json.load(sys.stdin); print(f'ACTIVE_SPRINTS={len(items)}')" 2>/dev/null

echo "CURRENT_MODE=$CURRENT_MODE"
```

# Project Mode

Assess whether the current project mode fits, or shift to a new one. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `assess` | → **Assess** current mode fitness |
| `shift <mode>` | → **Shift** to a new mode |
| `history` | → **View** mode history and snapshots |

Valid mode names: `flow`, `kanban`, `shape_up`, `agile`, `agile_enterprise`

---

## Assess

Use `CURRENT_MODE`, `BACKLOG_COUNT`, `TOTAL_ISSUES`, `ACTIVE_SPRINTS` from the shell block.

Present the current mode and a fitness assessment:

```
Current mode: {CURRENT_MODE}
─────────────────────────────────────────
Issues:   {TOTAL_ISSUES} total  ({BACKLOG_COUNT} in backlog)
Sprints:  {ACTIVE_SPRINTS} active
```

**Mode descriptions:**

| Mode | Best for |
|---|---|
| `flow` | Solo dev in early exploration. No ceremony. SweetClaude observes quietly. |
| `kanban` | Continuous delivery, no fixed sprints. Issues flow through a status board. |
| `shape_up` | 6-week cycles with pitches. Fixed appetite, variable scope. |
| `agile` | Sprint-based. Velocity tracking, backlog grooming, retrospectives. |
| `agile_enterprise` | Agile + compliance gates, mandatory traceability, security reviews. |

**Upshift signals** — suggest considering a higher-structure mode if:
- `flow` → `kanban`: TOTAL_ISSUES > 20 and they're not getting reviewed
- `kanban` → `agile`: BACKLOG_COUNT > 30 or user mentions "sprints" or "planning"
- `agile` → `agile_enterprise`: user mentions compliance, regulated data, external audit

**Downshift signals** — suggest considering a lower-structure mode if:
- `agile` → `kanban`: ACTIVE_SPRINTS = 0 for 3+ sprints running (sprint rhythm has broken down)
- Any → `flow`: user explicitly wants to stop tracking work for a period

Present a recommendation based on the signals, or "Current mode fits well" if no signals.

End with: "Run `project-mode shift <mode>` to change, or continue as-is."

---

## Shift

Arguments: `shift <target_mode>`

```bash
CURRENT_MODE=$(python3 -c "
import yaml
p = yaml.safe_load(open('$PWD/.sweetclaude/state/phase.yaml'))
print(p.get('mode','flow'))
" 2>/dev/null)
```

**Step 1: Validate the transition.**

Hard block: `agile_enterprise` → `flow` without `--force`. Say:
"Shifting from agile_enterprise to flow would hide all compliance artifacts and sprint history. This is a significant downgrade. Pass `--force` if you're certain."

All other transitions are permitted.

**Step 2: Show what changes.**

For upshifts — what becomes available:
```
Shifting {current} → {target}

New capabilities:
  • {list artifacts/skills that become available}

No artifacts are deleted — existing data is preserved.
```

For downshifts — what gets archived:
```
Shifting {current} → {target}

Artifacts being archived (soft — not deleted):
  • {list artifacts/skills that become unavailable}
  • Active sprints will have planned issues returned to backlog.
```

Confirm: "Proceed with shift?"

**Step 2a: Cascade check (upshift to more structured mode).**

### Cascade check (upshift to more structured mode)

**Shifting to Agile:**
Check for `{product_base}/backlog/BACKLOG-INDEX.md` and at least one file in `{product_base}/epics/`. If missing:
> "Agile works best with an organized backlog and epics. Missing: {list}. Set these up now, or skip and set them up later? (setup now / skip)"

**Shifting to Shape Up:**
Check for any files in `{product_base}/pitches/`. If none:
> "Shape Up uses pitches as the entry point for all work. You don't have any yet. Write your first pitch now, or skip? (write pitch / skip)"

**Shifting to Kanban:**
If `wip_limit` is not set in sweetclaude.yaml, ask:
> "Kanban enforces WIP limits to control flow. What's your WIP limit for in_progress items? (default: 3)"
Write `wip_limit: {N}` to sweetclaude.yaml.

**Step 2b: Cascade clean (downshift to less structured mode).**

### Cascade clean (downshift to less structured mode)

**Shifting from Agile:**
Check for any sprint artifact with `status: active`. If found:
> "You have an active sprint. Close or cancel it before shifting modes."
> Run `/sweetclaude:project-sprints close` or `/sweetclaude:project-sprints cancel`.
Block until resolved.

**Shifting from Shape Up:**
Check for any cycle artifact with `status: planning` or `status: active`. If found:
> "You have an open cycle ({CYC-XXX}). Close it before shifting? (yes / skip)"

**Step 3: Create snapshot.**

```bash
TODAY=$(date +%Y-%m-%d)
SNAPSHOT_NUM=$(ls "$PWD/.sweetclaude/state/snapshots/" 2>/dev/null | grep -c "^SNAPSHOT-" || echo 0)
SNAPSHOT_NUM=$((SNAPSHOT_NUM + 1))
SNAPSHOT_ID="SNAPSHOT-$(printf '%03d' $SNAPSHOT_NUM)-$TODAY"
SNAPSHOT_DIR="$PWD/.sweetclaude/state/snapshots/$SNAPSHOT_ID"
mkdir -p "$SNAPSHOT_DIR"

# Snapshot current state
cp "$PWD/.sweetclaude/state/phase.yaml" "$SNAPSHOT_DIR/phase.yaml" 2>/dev/null
cp "$PWD/.sweetclaude/state/scope.yaml" "$SNAPSHOT_DIR/scope.yaml" 2>/dev/null
cp "$PWD/.sweetclaude/state/project-index.json" "$SNAPSHOT_DIR/project-index.json" 2>/dev/null

# Manifest
cat > "$SNAPSHOT_DIR/manifest.yaml" << MANIFEST
snapshot_id: $SNAPSHOT_ID
created_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
trigger: mode_shift
from_mode: $CURRENT_MODE
to_mode: <target_mode>
MANIFEST

echo "Snapshot: $SNAPSHOT_ID"
```

**Step 4: Handle downshift artifact archiving.**

If shifting away from `agile` or `agile_enterprise`:
- Cancel all `planned` sprints (set status=cancelled)
- Move their issues back to backlog (sprint_id=null, status=backlog)

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query sprint status=planned
```

For each planned sprint:
```bash
sc_artifact_write <SP-NNN> '{"status": "cancelled"}'
```

Do not touch `active` sprints — ask the user to close them first.

**Step 5: Update phase.yaml.**

```bash
python3 - <<'PYEOF'
import yaml
from datetime import datetime

with open('$PWD/.sweetclaude/state/phase.yaml') as f:
    phase = yaml.safe_load(f)

phase['mode'] = '<target_mode>'
phase['mode_set_at'] = datetime.now().strftime('%Y-%m-%d')

if 'mode_history' not in phase:
    phase['mode_history'] = []
phase['mode_history'].append({
    'mode': '$CURRENT_MODE',
    'set_at': phase.get('mode_set_at', datetime.now().strftime('%Y-%m-%d')),
    'snapshot_id': '$SNAPSHOT_ID'
})

# Storage backend defaults
backend_defaults = {
    'flow': 'markdown', 'kanban': 'markdown', 'shape_up': 'markdown',
    'agile': 'markdown', 'agile_enterprise': 'sqlite'
}
phase['storage_backend'] = backend_defaults.get('<target_mode>', 'markdown')

with open('$PWD/.sweetclaude/state/phase.yaml', 'w') as f:
    yaml.dump(phase, f, default_flow_style=False, allow_unicode=True)
print('ok')
PYEOF
```

**Step 6: Regenerate effective gates.**

```bash
bash $HOME/dev/sweetclaude/scripts/generate-effective-gates.sh
```

Output: "Mode set to **{mode}**. Effective gates compiled."

**Step 7: Confirm.**

```
Mode shifted: {from} → {to}
Snapshot:     {SNAPSHOT_ID}
Storage:      {new backend}

{any archived artifacts listed}
```

---

## History

```bash
python3 -c "
import yaml
p = yaml.safe_load(open('$PWD/.sweetclaude/state/phase.yaml'))
history = p.get('mode_history', [])
current = p.get('mode', 'unknown')
print(f'Current: {current}')
for h in reversed(history):
    print(f\"  {h.get('set_at','?')}  {h.get('mode','?')}  snapshot={h.get('snapshot_id','—')}\")
"
ls "$PWD/.sweetclaude/state/snapshots/" 2>/dev/null | head -10
```

Present:

```
Mode history
Current: {mode}

Date        Mode         Snapshot
────────────────────────────────────────────────
2026-05-01  agile        SNAPSHOT-002-2026-05-01
2026-04-01  flow         SNAPSHOT-001-2026-04-01
```

"Snapshots are stored at `.sweetclaude/state/snapshots/`. Each contains a full export of project state at the time of the shift."

---

## Rules

- Always snapshot before shifting. No exceptions, no --skip-snapshot flag.
- Never delete artifacts on downshift — archive only (soft state changes).
- If an active sprint exists when shifting away from agile, block: "Close the active sprint before shifting modes."
- Storage backend changes take effect after the next session start — skills reload the backend on invocation.
- `agile_enterprise` → `flow` requires explicit `--force` because it hides compliance artifacts.

---

## Shape Up — Solo Betting Table (DEFINE phase)

When `mode` is `shape_up` and the current phase is `DEFINE`, after the pitch document is written, present three required questions:

1. "What is the core outcome if this ships? (one sentence)"
2. "What are the rabbit holes — the parts most likely to blow up the appetite?"
3. "What is explicitly NOT in scope for this cycle?"

All three must be answered. Write to the pitch artifact:

```yaml
betting_table:
  core_outcome: "{answer 1}"
  rabbit_holes: "{answer 2}"
  non_goals: "{answer 3}"
  approved: true
  approved_at: "{ISO timestamp}"
```

Set `betting_table_approved: true` on linked issues. This is the gate the IMPLEMENT phase checks.

---

## Shape Up — Cycle Duration

Ask at setup:
> "What is your cycle duration? Shape Up default is 6 weeks. (Enter number of weeks, or press Enter for 6)"

Write `cycle_duration_weeks: {N}` to sweetclaude.yaml before running generate-effective-gates.

Available as a standalone configuration update: `/sweetclaude:project-mode configure cycle_duration_weeks <N>`
