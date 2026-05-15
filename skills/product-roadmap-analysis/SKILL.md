---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "RICE scoring and stack-rank analysis for roadmap items."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:product-roadmap-analysis" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"

sc_artifact_list roadmap_item
sc_artifact_list milestone
sc_artifact_query roadmap_item status=in_progress,planned

SCOPE_FILE="$PWD/.sweetclaude/state/scope.yaml"
cat "$SCOPE_FILE" 2>/dev/null || echo "SCOPE_NOT_FOUND"
```

# Product Roadmap Analysis

RICE scoring and stack-rank analysis for roadmap items — surface misalignment, challenge priorities, and propose a revised order. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `analyze` | → **Full analysis** — RICE scoring + stack-rank proposal |
| `alignment` | → **Alignment check** — scope and milestone alignment only |
| `item <RM-NNN>` | → **Single item** — deep RICE and rationale for one item |

---

## Full Analysis

### Step 1: Load context

Use roadmap items and scope from shell block above.

If no roadmap items exist: "No roadmap items to analyze. Run `product-roadmap new` to add items."

If `SCOPE_NOT_FOUND`: note that scope alignment checks will be skipped. Proceed with RICE only.

---

### Step 2: RICE scoring

RICE = **(Reach × Impact × Confidence) / Effort**

For each `planned` or `in_progress` roadmap item, estimate the four inputs. Base estimates on:
- The item's `description` and `rationale`
- Type (`major_feature`, `minor_feature`, `enhancement`, `sunset`)
- Current priority and any contributing epics or issues

**Reach** — how many users benefit in a meaningful way, relative to other items?

| Score | Signal |
|---|---|
| 5 | All users, core workflow |
| 4 | Most users, or high-value segment |
| 3 | Many users, secondary workflow |
| 2 | Some users, edge case |
| 1 | Few users, niche use case |

**Impact** — how much does this move the needle per user who benefits?

| Score | Signal |
|---|---|
| 3 | Massive impact — removes a blocker or dramatically improves core task |
| 2 | High impact — significant improvement to an existing capability |
| 1 | Medium impact — noticeable improvement |
| 0.5 | Low impact — minor convenience |
| 0.25 | Minimal — polish, cosmetic |

**Confidence** — how sure are we about Reach and Impact estimates?

| Score | Signal |
|---|---|
| 1.0 | High — data, user research, or validated assumptions |
| 0.8 | Medium — informed guess, some signals |
| 0.5 | Low — mostly assumptions |

**Effort** — relative implementation cost (not time)

| Score | Signal |
|---|---|
| 1 | Trivial — < 1 sprint |
| 2 | Small — 1 sprint |
| 4 | Medium — 2–3 sprints |
| 8 | Large — 4+ sprints or high uncertainty |
| 16 | Extra-large — multi-sprint with unknowns; consider splitting |

Effort defaults by type if unknown:
- `major_feature` → 8
- `minor_feature` → 4
- `enhancement` → 2
- `sunset` → 4

---

### Step 3: Present scores

```
Roadmap RICE Analysis
══════════════════════════════════════════════════════════════

 ID       Title                        R   I    C    E    RICE   Current
 ──────────────────────────────────────────────────────────────────────
 RM-001   Auth SSO support             4 × 3 × 1.0 ÷ 8 = 1.50   #1
 RM-003   Dark mode                    3 × 0.5 × 0.8 ÷ 2 = 0.60  #4
 RM-002   Webhook integrations         5 × 2 × 0.8 ÷ 4 = 2.00   #2
 RM-005   Bulk export                  3 × 1 × 0.5 ÷ 2 = 0.75   #3
 RM-004   Legacy API v1 sunset         2 × 1 × 1.0 ÷ 4 = 0.50   #5
```

Show scores sorted by RICE descending. Include current priority for comparison.

After the table, note any significant mismatches: items where RICE rank and current rank diverge by 2+.

---

### Step 4: Alignment check

**Scope alignment** (if scope loaded):

For each roadmap item, check whether it fits the scope statement and in-scope list:
- Flag any item that seems to stretch or contradict the scope statement
- Flag any item that matches something in the out-of-scope list

```
Scope alignment
  RM-003  Dark mode — MAY CONFLICT: scope out-of-scope includes "cosmetic customization"
  RM-001  Auth SSO support — IN SCOPE
```

If no conflicts: "All items appear aligned with current scope."

**Milestone alignment** (if milestones loaded):

For each pending milestone, check whether the roadmap provides a path to achieving it:

```
Milestone alignment
  MS-002  First paying customer — no roadmap items directly support this milestone
  MS-003  100 active projects — RM-001 (Auth SSO) may be a dependency
```

If a milestone has no supporting roadmap item, flag it as a planning gap.

---

### Step 5: Proposed stack-rank

Based on RICE scores, present a proposed priority order:

```
Proposed stack-rank (by RICE)
  #1  RM-002  Webhook integrations     RICE: 2.00  (currently #2 — no change)
  #2  RM-001  Auth SSO support         RICE: 1.50  (currently #1 — move down 1)
  #3  RM-005  Bulk export              RICE: 0.75  (currently #3 — no change)
  #4  RM-003  Dark mode                RICE: 0.60  (currently #4 — no change)
  #5  RM-004  Legacy API v1 sunset     RICE: 0.50  (currently #5 — no change)
```

Include a one-line rationale for each item that moves.

Offer: "Apply this stack-rank? Say `yes` to update priorities, `adjust` to change specific inputs, or `no` to leave as-is."

---

### Step 6: Apply confirmed stack-rank

On user confirmation (`yes`):

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_write <RM-NNN> '{"priority": <N>}'
```

Apply for each item that changed. Confirm:

```
Stack-rank updated
  RM-002  #1  (was #2)
  RM-001  #2  (was #1)
  (no change: RM-005, RM-003, RM-004)
```

On `adjust`:

Ask: "Which item do you want to change, and what's the updated input?" Accept: `RM-NNN reach=5`, `RM-NNN confidence=1.0`, etc. Recalculate and re-present the table.

On `no`: "Stack-rank unchanged."

---

## Alignment Check (only)

Arguments: `alignment`

Skip RICE scoring. Run Step 4 only (scope + milestone alignment) and present results.

End with: "Run `product-roadmap-analysis` for full RICE scoring."

---

## Single Item

Arguments: `item <RM-NNN>`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_read <RM-NNN>
sc_artifact_query epic roadmap_item_id=<RM-NNN>
sc_artifact_query issue roadmap_item_id=<RM-NNN> epic_id=
```

Run full RICE scoring for this one item. Present:

```
RM-NNN — {title}
─────────────────────────────────────────
Type:     {type}         Priority:  #{N}
Status:   {status}

RICE Scoring
  Reach:       {score}  — {reasoning}
  Impact:      {score}  — {reasoning}
  Confidence:  {score}  — {reasoning}
  Effort:      {score}  — {reasoning}
  ─────────────────────────────────────
  RICE score:  {score}

Contributing work
  {N} epics, {M} direct issues
  {list epics by ID and status}

Scope fit
  {in scope / possible conflict / explain}
```

Offer: "Update RICE inputs? Say `reach=N`, `impact=N`, `confidence=N`, or `effort=N`."

---

## Rules

- RICE scores are estimates — the model cannot know exact reach or impact. Present reasoning so the user can challenge inputs.
- RICE is an input to prioritization, not a mandate. The user decides the final order.
- If a `deferred` or `idea` item scores higher than active items, surface it: "RM-NNN is deferred but scores {X} — higher than {N} active items. Worth reconsidering?"
- Sunset items carry hidden cost: not sunsetting has a reach/impact cost too. Factor in tech debt and support burden.
- Never apply a stack-rank without explicit user confirmation. Roadmap priority is a business decision.
