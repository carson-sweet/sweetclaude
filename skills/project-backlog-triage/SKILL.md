---
spdx-license: AGPL-3.0-or-later
name: project-backlog-triage
user-invocable: true
description: "Structured backlog grooming session. Applies INVEST criteria and sets priority and effort estimates on ungroomed issues one at a time."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"

# Load ungroomed issues: missing priority or effort
ALL_BACKLOG=$(python3 "${_sc_hooks}/sc-artifact-impl.py" \
  query "$SC_PROJECT_ROOT" "$SC_PRODUCT_BASE" "$SC_STATE_BASE" \
  issue sprint_id= status=backlog 2>/dev/null)

UNGROOMED=$(echo "$ALL_BACKLOG" | python3 -c "
import json, sys
items = json.load(sys.stdin)
ungroomed = [i for i in items if not i.get('priority') or not i.get('effort')]
print(json.dumps(ungroomed))
print(f'UNGROOMED_COUNT={len(ungroomed)}', file=__import__('sys').stderr)
" 2>/dev/null)

echo "$ALL_BACKLOG" | python3 -c "
import json, sys
items = json.load(sys.stdin)
ungroomed = [i for i in items if not i.get('priority') or not i.get('effort')]
print(f'UNGROOMED_COUNT={len(ungroomed)}')
print(f'TOTAL_BACKLOG={len(items)}')
"
```

# Project Backlog Triage

A focused grooming session. Works through ungroomed issues one at a time using INVEST criteria and t-shirt sizing. Arguments: `$ARGUMENTS`

---

## Entry check

Read `UNGROOMED_COUNT` from the shell output above.

If `UNGROOMED_COUNT` is 0: "Backlog is fully groomed — all {TOTAL_BACKLOG} issues have priority and effort estimates. Nothing to triage."

Otherwise: "Starting triage — {UNGROOMED_COUNT} issues need grooming."

---

## Triage loop

Load ungroomed issues sorted by: `done` last, then by created_at ascending (oldest first).

For each issue:

### 1. Present the issue

```
─────────────────────────────────────────
Issue {n} of {UNGROOMED_COUNT}: {ID}

  {title}
  Type: {type}

  {description — first 4 lines}

  Current priority: {priority or '—'}
  Current effort:   {effort or '—'}
```

### 2. Run INVEST check silently

Evaluate these criteria against the issue's description and acceptance criteria. Flag only genuine concerns — don't flag every issue.

| Criterion | What to check |
|---|---|
| **Independent** | Does it reference another unscheduled issue as a prerequisite? |
| **Negotiable** | Does the description dictate implementation rather than outcome? |
| **Valuable** | Is there a clear user/business outcome, or just a task? |
| **Estimable** | Is there enough information to size it, or are there unknown unknowns? |
| **Small** | Can this realistically be done in one sprint? |
| **Testable** | Can acceptance criteria be written (or are they already present)? |

### 3. Present recommendation

```
INVEST: {clean | list any flags}

Recommended:
  Priority: {next|sooner|soon|later|someday}  — {one-line reason}
  Effort:   {xs|s|m|l|xl|xxl}                   — {one-line reason}
```

**Effort sizing heuristics:**

| Signals | Effort |
|---|---|
| One AC, trivial code change | xs |
| 2–3 ACs, clear path | s |
| 4–6 ACs, some unknowns | m |
| Multiple subsystems, integration work | l |
| Architectural change, significant unknowns | xl |
| Should probably be split into an epic | xxl → prompt to split |

### 4. Wait for user response

Accept:
- **`y`** or just Enter → accept recommendation as-is
- **`p=sooner e=m`** → override specific fields
- **`skip`** → skip this issue, come back later
- **`split`** → split into two issues (see below)
- **`cancel`** → mark as cancelled, remove from backlog
- **`done`** → mark as already done
- **`q`** → quit triage session, save progress

### 5. Apply decision

On `y` or field overrides:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <ID> '{"priority": "<priority>", "effort": "<effort>", "status": "ready"}'
```

On `cancel`:
```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_delete <ID>
```

On `done`:
```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <ID> '{"status": "done"}'
```

### 6. Split flow

If the user says `split`:

Ask: "What are the two parts? Give me two titles."

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_create issue '{"title": "<part 1>", "type": "<type>", "status": "backlog", "epic_id": "<epic or null>"}'
sc_artifact_create issue '{"title": "<part 2>", "type": "<type>", "status": "backlog", "epic_id": "<epic or null>"}'
sc_artifact_delete <original_id>
```

Confirm: "Split into {new_id_1} and {new_id_2}. Original {ID} cancelled."

Both new issues re-enter the triage queue immediately.

---

## Session summary

After the user exits (all done, `q`, or all issues processed):

```
Triage session complete
────────────────────────
Groomed:   {N} issues
Skipped:   {N} issues
Split:     {N} issues → {M} new
Cancelled: {N} issues
Done:      {N} issues

Remaining ungroomed: {N}
```

If `remaining > 0`: "Run `project-backlog-triage` again to continue."

---

## Rules

- Triage one issue at a time. Never batch-present multiple issues.
- INVEST flags are informational. The user decides what to do with them — don't block on INVEST failures.
- If an issue has `xxl` effort, always prompt to split. Never silently accept xxl as the final estimate.
- Skipped issues stay ungroomed and will reappear next session.
- Status is set to `ready` (not `backlog`) when groomed — this signals the issue is sprint-eligible.
- Session progress is not persisted mid-session. If the user closes Claude, skipped issues remain ungroomed.
