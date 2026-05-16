# BL-021 Spike Findings: SweetClaude Bootstrap Efficiency
Date: 2026-05-02
Status: COMPLETE

## Current Bootstrap Token Cost

Files loaded at every session start (via `~/.claude/rules/sweetclaude/` global rules system):

| File | Chars | Est. Tokens |
|---|---|---|
| `interaction-model.md` | 10,150 | ~2,540 |
| `phase-gates.md` | 23,473 | ~5,870 |
| `tdd-levels.md` | 2,473 | ~620 |
| Project CLAUDE.md | 2,522 | ~630 |
| Global CLAUDE.md | 2,523 | ~630 |
| **Total** | **41,141** | **~10,290** |

Session-state.yaml (~1,019 chars, ~255 tokens) is already lazy-loaded per-skill via `!cat` — this is correct. Not a bootstrap cost.

---

## Which Rules Are Always Needed?

| File | Always needed? | Reasoning |
|---|---|---|
| `interaction-model.md` | **Yes** | Core behavioral rules — no-estimation, phase dwelling, deference, adaptive language. Must be present from token 1. |
| `phase-gates.md` | **No** | Detailed gate criteria. Only needed when evaluating phase advancement. The behavioral guard ("never push for advancement") is already in interaction-model.md. |
| `tdd-levels.md` | **Conditional** | Only needed for code work. ~620 tokens — small enough that removing it globally is probably not worth the migration cost. |

---

## The Optimization Opportunity

`phase-gates.md` is **57% of the rules bootstrap cost** (~5,870 of ~10,290 tokens) and is loaded on every session including strategy-only, document, and status sessions that never touch phase gate evaluation.

### Option A: Remove phase-gates.md from global rules, inject per-skill

Move `phase-gates.md` out of `~/.claude/rules/sweetclaude/`. Add `!cat ~/.claude/rules/sweetclaude/phase-gates.md` to the preprocessing blocks of skills that need gate evaluation:
- `sweetclaude:go` (always needs gates for phase assessment)
- `sweetclaude:status` (when active work item exists)
- Any skill with phase transition logic

**Savings:** ~5,870 tokens on sessions that don't invoke gate-evaluating skills (light sessions, strategy work, corpus management).
**Cost:** On sessions that DO invoke those skills, no savings — they load the full file.
**Risk:** LOW — the behavioral guardrail ("never push for phase advancement") lives in interaction-model.md, which stays global.

### Option B: Inject only relevant gates into session-state.yaml

`generate-session-state.sh` already runs at session start and outputs a ~255-token YAML snapshot. It could extract only the active work type's gate criteria from `phase-gates.md` (e.g., if `active_work_item.type: net-new-feature` and `phase: IMPLEMENT`, extract only the IMPLEMENT exit criteria for net-new-feature).

**Savings:** Global rules stay the same, but skills that read session-state.yaml get the relevant gates pre-distilled — no need to load the full 23K char file.
**Cost:** More complex `generate-session-state.sh` (YAML parsing of phase-gates.md).
**Value:** Skills get the precise gates they need, not all 30+ work-type × phase combinations.
**Risk:** LOW — the session-state.yaml already mediates what context skills see.

### Option C: Keep as-is

`phase-gates.md` is ~6K tokens out of a ~200K context window. The absolute savings from removing it are modest (3% of context). The migration cost (updating hooks, skills, and installation) is non-trivial.

---

## Recommendation: Option B, deferred to MS-005

**Don't do Option A now.** The absolute token savings are modest, and removing `phase-gates.md` from global rules creates a fragile dependency between the rules file location and every skill that evaluates gates. One missed skill and the framework silently loses phase gate enforcement.

**Do Option B in MS-005 when/if bootstrap cost becomes a real constraint.** The right implementation: extend `generate-session-state.sh` to include an `active_phase_gates` section with only the relevant work-type × phase gates. Skills read this from session-state.yaml instead of the full file. Net effect: ~5K token savings on phase-aware skills; sessions with no active work item pay zero gate-loading cost.

**Do now (zero migration cost):** Shell preprocessing is already the right pattern. `sweetclaude:master` pre-flight is already thin — no action needed there.

---

## Master Pre-flight Assessment

BL-021 asked: "Can shell preprocessing replace the `master` pre-flight?" Answer: **already replaced for the most part.** Each skill's `!cat session-state.yaml` block does the equivalent read. `sweetclaude:master`'s remaining value is routing (Situation A vs B). With the current design, `go` handles routing autonomously. `master` is ceremonial for users who don't know which skill to call. No migration needed.

---

## Go / No-Go

**Noop. No action items.**

The apparent savings from lazy-loading phase-gates.md (~6K tokens) disappear on examination: `sweetclaude:status` auto-runs at session start per CLAUDE.md, and it reads phase gate criteria as part of its phase assessment. So the gates are loaded on the first skill invocation of every SweetClaude session anyway. Lazy-loading would only save tokens on sessions where status fails or is explicitly skipped — too narrow to be worth the migration complexity.

Do not backlog Option B. Revisit only if users report hitting actual context pressure limits, which would be a different root cause than bootstrap token cost.
