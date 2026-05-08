---
spdx-license: AGPL-3.0-or-later
name: product-terminology
user-invocable: true
description: "Define and maintain a shared domain glossary. Each entry records a term's name, definition, rationale, aliases, and words to avoid — preventing naming drift across docs, code, and conversation."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
PRODUCT_BASE=$(python3 -c "
import yaml, sys
try:
    d = yaml.safe_load(open('.sweetclaude/state/session-state.yaml'))
    print(d.get('paths', {}).get('product_base', '.sweetclaude/product'))
except:
    print('.sweetclaude/product')
" 2>/dev/null || echo ".sweetclaude/product")

GLOSSARY="$PRODUCT_BASE/vocabulary/glossary.md"
echo "GLOSSARY_PATH=$GLOSSARY"
[ -f "$GLOSSARY" ] && echo "GLOSSARY_EXISTS=true" || echo "GLOSSARY_EXISTS=false"
[ -f "$GLOSSARY" ] && cat "$GLOSSARY" || echo "GLOSSARY_EMPTY"
```

# Product Terminology

Shared domain glossary. One term per entry — name, definition, rationale, aliases, and words to avoid. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `list` | → **List** all terms |
| `add [term]` | → **Add** a new term (opens interview) |
| `view <term>` | → **View** a single entry |
| `update <term>` | → **Update** an existing entry |
| `search <query>` | → **Search** definitions and aliases |

---

## List

If `GLOSSARY_EXISTS=false` or `GLOSSARY_EMPTY`: "No glossary yet. Run `product-terminology add <term>` to define the first entry."

Otherwise parse the glossary and display a summary table:

```
Domain Glossary  ({N} terms)
══════════════════════════════

  Term               Definition (excerpt)
  ─────────────────  ──────────────────────────────────────────
  {term}             {first 60 chars of definition}…
  {term}             {first 60 chars of definition}…
```

Sort alphabetically. If the glossary has more than 20 terms, group by first letter.

---

## Add

Interview for the new term. One question at a time. The term name may come from `$ARGUMENTS` (e.g. `add onboarding`) — if so, skip the first question.

**1. Name**
"What is the term? Give the canonical form — singular noun, lowercase, exactly as it should appear in docs."

Check against existing glossary. If the new term is within edit-distance 2 of an existing term, or shares a root with one, surface the conflict:
> "This looks similar to an existing entry: **{existing term}** — {definition excerpt}. Is this a synonym (add as alias to that entry), a more specific concept (add as a new entry with a note), or something different?"

**2. Definition**
"Define it in one sentence. Focus on what it *is*, not what it *does* or what it's *used for*. Avoid circular definitions (don't use the term in its own definition)."

Push back if:
- The definition uses the term itself
- The definition is longer than two sentences (suggest trimming)
- The definition could apply to a different term in the glossary

**3. Rationale**
"Why this word and not an alternative? What confusion does this naming prevent?"

This is the most valuable field — it records the decision, not just the outcome. Probe if the answer is thin: "What other words were considered and rejected?"

**4. Aliases**
"Any synonyms or alternate spellings this term should match when searched? (Enter as comma-separated list, or press enter to skip.)"

**5. Avoid**
"Any words that should NOT be used for this concept — terms that are tempting but wrong, legacy names, or names used differently in adjacent contexts? (Comma-separated, or skip.)"

Once all five fields are collected, write the entry:

```bash
python3 - <<'PYEOF'
import os, re
from datetime import datetime

product_base_raw = "$PRODUCT_BASE"
glossary_path = "$GLOSSARY"
os.makedirs(os.path.dirname(glossary_path), exist_ok=True)

term = "<term>"
definition = "<definition>"
rationale = "<rationale>"
aliases = [a.strip() for a in "<aliases>".split(",") if a.strip()] if "<aliases>" else []
avoid = [a.strip() for a in "<avoid>".split(",") if a.strip()] if "<avoid>" else []
today = datetime.now().strftime("%Y-%m-%d")

entry = f"""
## {term}

**Definition:** {definition}

**Rationale:** {rationale}
"""

if aliases:
    entry += f"\n**Aliases:** {', '.join(aliases)}\n"
if avoid:
    entry += f"\n**Avoid:** {', '.join(avoid)}\n"

entry += f"\n_Added: {today}_\n"

if not os.path.exists(glossary_path):
    header = f"# Domain Glossary\n\n_Last updated: {today}_\n\n---\n"
    with open(glossary_path, "w") as f:
        f.write(header + entry)
    print(f"Created glossary with first entry: {term}")
else:
    with open(glossary_path, "a") as f:
        f.write("\n---\n" + entry)
    print(f"Added: {term}")
PYEOF
```

Confirm: `Added **{term}** to the glossary.`

If the "Avoid" list is non-empty, add a note: "These terms are now marked as out-of-vocabulary: {avoid list}. When they appear in future docs or code, the glossary is the reference for why."

---

## View

Parse `$ARGUMENTS` for the term name (everything after `view `).

If not found in glossary:
> "**{term}** not found. Run `product-terminology list` to see all terms, or `product-terminology add {term}` to define it."

If found, display the full entry:

```
{term}
══════════════════════════════════════════════════

Definition
  {definition}

Rationale
  {rationale}

Aliases
  {aliases or "(none)"}

Avoid
  {avoid list or "(none)"}

Added: {date}
```

---

## Update

Parse `$ARGUMENTS` for the term name (everything after `update `).

If not found: route to Add with a note: "**{term}** isn't in the glossary yet. Want to add it?"

If found, display the current entry and ask:
> "What needs to change? (Definition / Rationale / Aliases / Avoid / Rename the term itself)"

Apply the change. If renaming the term:
- Update the `## {term}` heading
- Add the old name to the Aliases list with a note "(formerly {old name})"
- Note: "The old name is now an alias. Existing docs that used it still resolve to this entry when searched."

Rewrite the entry in place (find-and-replace the section between `## {term}` and the next `---` or end of file).

Confirm: `Updated **{term}**.`

---

## Search

Parse `$ARGUMENTS` for the query (everything after `search `).

Search the glossary for the query string across:
- Term names (exact and partial match)
- Definitions
- Aliases
- Avoid lists

Display results grouped by match type:

```
Search: "{query}"  —  {N} results

Exact term match:
  {term}  —  {definition excerpt}

Definition contains:
  {term}  —  …{surrounding context}…

Alias match:
  {term}  (alias: {matching alias})  —  {definition excerpt}

Avoid list match:
  {term}  (avoid: {matching word})  —  This term should NOT be called "{query}". Use "{term}" instead.
```

If no results: "No glossary entries match **{query}**. Run `product-terminology add {query}` to define it."

---

## Rules

- Never modify an existing entry without showing the current version first.
- The Rationale field is not optional — a glossary entry without rationale is just a dictionary; the rationale is what makes it a decision record.
- When surfacing a naming conflict during Add, never silently pick the resolution — always surface it and let the user decide.
- The Avoid list is load-bearing: terms on it represent active naming confusion risks, not just preferences.
