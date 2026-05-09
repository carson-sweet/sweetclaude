---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Define and maintain project scope."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
SCOPE_FILE="$PWD/.sweetclaude/state/scope.yaml"
cat "$SCOPE_FILE" 2>/dev/null || echo "SCOPE_NOT_FOUND"
```

# Project Scope

Scope is a single document — one statement of what the project does and for whom, with explicit in-scope and out-of-scope lists. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `view` | → **View** current scope |
| `set` | → **Define** scope (first time) |
| `update` | → **Update** scope and trigger cascade |
| `history` | → **View** change history |

---

## View

Use the scope output from the shell block above.

If `SCOPE_NOT_FOUND`: "No scope defined yet. Run `project-scope set` to define it."

Otherwise present:

```
Project Scope  (v{version}, updated {last_changed})
══════════════════════════════════════════════════

Statement
  {statement}

In scope
  • {item}
  • {item}

Out of scope
  • {item}
  • {item}
```

---

## Set (first time)

Only if scope.yaml does not exist. Ask one question at a time:

1. **Statement** — "Complete this sentence: 'This project is a [what] for [whom] that [does what].'"

   Challenge if too broad or too narrow. A good statement fits in one sentence and clearly excludes things by implication.

2. **In scope** — "List the things this project explicitly does — one per line. These are the things you'd defend if someone asked 'why does this do X?'"

3. **Out of scope** — "List the things this project explicitly does NOT do — one per line. Minimum three. These prevent scope creep by naming the temptations."

   If fewer than 3 out-of-scope items: "Three or more out-of-scope items helps prevent scope creep. What else is this project specifically not trying to do?"

Write the scope file:

```bash
python3 -c "
import yaml
from datetime import datetime
scope = {
    'schema_version': 1,
    'version': 1,
    'last_changed': datetime.now().strftime('%Y-%m-%d'),
    'statement': '''<statement>''',
    'in_scope': <in_scope_list>,
    'out_of_scope': <out_of_scope_list>,
    'change_log': []
}
with open('$PWD/.sweetclaude/state/scope.yaml', 'w') as f:
    yaml.dump(scope, f, default_flow_style=False, allow_unicode=True)
print('ok')
"
```

Confirm: `Scope defined (v1)`

---

## Update

Read current scope first:

```bash
cat "$PWD/.sweetclaude/state/scope.yaml"
```

Show current scope (same as View). Ask: "What's changing?"

Accept the user's description of the change. Classify it:
- **Expansion** — adding something to in-scope, or removing from out-of-scope
- **Contraction** — removing from in-scope, or adding to out-of-scope
- **Restatement** — rewording without changing meaning

For expansions: challenge before accepting. "Adding [X] to scope means this project now covers [X]. What's the concrete reason — feature request, strategic pivot, or new use case?"

Once confirmed, apply the change:

```bash
python3 - <<'PYEOF'
import yaml
from datetime import datetime

with open('$PWD/.sweetclaude/state/scope.yaml') as f:
    scope = yaml.safe_load(f)

scope['version'] += 1
scope['last_changed'] = datetime.now().strftime('%Y-%m-%d')

# Apply changes: <update in_scope / out_of_scope / statement as needed>

scope['change_log'].append({
    'date': datetime.now().strftime('%Y-%m-%d'),
    'change': '<one line description of change>',
    'cascade_triggered': True
})

with open('$PWD/.sweetclaude/state/scope.yaml', 'w') as f:
    yaml.dump(scope, f, default_flow_style=False, allow_unicode=True)
print('ok')
PYEOF
```

**Cascade review:** After any scope change, load open roadmap items and backlog issues and surface those that may conflict with the new scope:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query roadmap_item status=planned,in_progress
sc_artifact_query issue status=backlog,ready,in_progress
```

Present a cascade summary:

```
Scope changed. Review these open items for alignment:

Roadmap items possibly affected:
  RM-NNN  {title}  — {reason it might conflict}

Issues possibly affected:
  I-NNN   {title}  — {reason it might conflict}

No action required now — this is a heads-up. Update or cancel items that no longer fit.
```

If nothing appears to conflict: "No open items appear to conflict with the scope change."

Confirm: `Scope updated to v{N}  (+cascade review surfaced)`

---

## History

```bash
cat "$PWD/.sweetclaude/state/scope.yaml"
```

Extract and display the `change_log` array:

```
Scope change history
Version  Date        Change
───────────────────────────────────────────────────────
v3       2026-05-15  Added mobile support to in-scope
v2       2026-05-01  Removed enterprise SSO from in-scope
v1       2026-04-01  Initial scope definition
```

---

## Rules

- Scope is a singleton — one file, one source of truth. Never create a second scope document.
- Out-of-scope list must always have 3+ items. Enforce at creation and after contraction updates.
- Cascade review is informational, not blocking. The user decides what to do with flagged items.
- A restatement (wording change, no meaning change) still increments the version but does NOT trigger cascade review. Ask "does this change what the project does, or just how it's described?" before deciding.
- Scope.yaml lives in `.sweetclaude/state/` — it is always private and never committed to public repos.
