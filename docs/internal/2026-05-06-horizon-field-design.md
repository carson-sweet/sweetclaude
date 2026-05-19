# Horizon Field for Backlog Items

**Version:** 1.0  
**Date:** 2026-05-06  
**Status:** Approved

---

## Summary

Add a `**Horizon:**` scheduling field to product backlog items (`BL-*.md`) with values `next | sooner | soon | later | someday`. Unify vocabulary with the project issues backlog (`I-*.md`) by renaming its existing priority values to match. All backlog views sort by horizon (earliest first), with P0/P1/P2/SPIKE shown as inline badges within each bucket. Bucket headings are displayed in ANSI bold blue in terminal output.

---

## Motivation

The current product backlog uses P0/P1/P2/SPIKE for sorting, which conflates urgency (severity) with scheduling intent (when to tackle). A horizon field separates these: P0/P1 still conveys urgency, while the horizon field answers "when do I want to work on this." Unifying vocabulary across both backlog systems (product and project issues) gives a single mental model across all views.

---

## Data Model

### Product backlog (`BL-*.md`)

Add an optional `**Horizon:**` markdown field alongside the existing `**Priority:**` field:

```markdown
**Priority:** P1
**Horizon:** sooner
```

Valid horizon values (in sort order): `next` (1) → `sooner` (2) → `soon` (3) → `later` (4) → `someday` (5)

Items with no `**Horizon:**` field are treated as `unscheduled` and sort last (6).

The existing `**Priority:** P0/P1/P2/SPIKE` field is unchanged. Both fields coexist.

### Project issues (`I-*.md`)

Rename values in the `priority` field of the sc-artifact schema:

| Old value | New value |
|-----------|-----------|
| `now`     | `next`    |
| `soonish` | `soon`    |
| `sooner`  | `sooner` (unchanged) |
| `later`   | `later` (unchanged) |
| `someday` | `someday` (unchanged) |

Field name (`priority`) is unchanged. Only the valid values change.

---

## Sort Order

`next (1) > sooner (2) > soon (3) > later (4) > someday (5) > unscheduled (6)`

Within each horizon bucket, items are not further reordered — filename order is used as a stable tiebreaker.

---

## Display Format

All backlog views use ANSI bold blue (`\033[1;34m...\033[0m`) for bucket headings. P0/P1/P2/SPIKE appear as inline `[Px]` badges on each item line.

```
\033[1;34mNEXT\033[0m (2)
  BL-009  [P2]  find-skill routes "concept articulation" wrong
  BL-003  [P0]  compare sweetclaude vs anthropic ultra

\033[1;34mSOONER\033[0m (1)
  BL-005  [P1]  reconcile syncog skills

\033[1;34mUNSCHEDULED\033[0m (3 — no horizon set)
  BL-001  [SPIKE]  agentic skills spike
  BL-016  [—]     gstack spike
```

This format applies in:
- `/sweetclaude:status` — backlog section
- `/sweetclaude:go` — Priority 4 proposal context
- `session-status.txt` — pre-flight status block
- `/sweetclaude:project-backlog` — project issues view (headings renamed: `NOW → NEXT`, `SOONISH → SOON`)

---

## `/sweetclaude:go` Behavior Change

**Priority 4** currently takes the first backlog filename found. With this change:

- Prefer the item with the earliest horizon (`next` before `sooner`, etc.)
- Multiple items tied at the same horizon: first filename as tiebreaker (existing behavior)
- Items with no horizon: eligible only after all horizoned items are evaluated

---

## Validation

When any skill writes `**Horizon:** later` or `**Horizon:** someday` to a BL-*.md item that has `**Priority:** P0` or `**Priority:** P1`, surface this prompt before saving:

> "P0/P1 item assigned to horizon '{later|someday}' — these usually signal urgent work. Reconcile: raise the horizon (next/sooner/soon), lower the priority (P2/SPIKE/none), or keep as-is with a note."

**Outcomes:**
- User raises horizon → write updated horizon value
- User lowers priority → write updated priority value  
- User keeps as-is → write both fields as specified, append user's note to item

**Fires in:**
- Any skill that sets `**Horizon:**` on an existing BL item
- `product-milestones complete` follow-up flow when creating new BL items

Note: project issues (`I-*.md`) have no severity/urgency field — their `priority` field is the horizon itself. The P0/P1 reconciliation validation is product backlog only.

---

## Files Changed

| File | Change |
|------|--------|
| `hooks/generate-session-state.sh` | Sort BL-*.md by Horizon in session-status.txt; P0/P1/P2 as inline badges |
| `skills/go/SKILL.md` | Priority 4: prefer earliest-horizon item; apply ANSI bold blue to bucket headings in output |
| `skills/status/SKILL.md` | Backlog section: sort by Horizon, ANSI bold blue headings, severity badges inline |
| `skills/product-milestones/SKILL.md` | Add `**Horizon:** ~` to BL template; add Horizon prompt in `add` flow; add validation in `complete` follow-up |
| `skills/project-backlog/SKILL.md` | Rename `NOW → NEXT`, `SOONISH → SOON`; apply ANSI bold blue to all bucket headings |
| `hooks/sc-artifact-impl.py` | Rename `now → next`, `soonish → soon` in issue schema priority enum |
| `skills/project-backlog-triage/SKILL.md` | Rename priority options; add validation for `later`/`someday` on P0/P1 issues |

---

## Non-Goals

- No migration script for existing BL-*.md items. Items without `**Horizon:**` fall into UNSCHEDULED naturally.
- No change to the P0/P1/P2/SPIKE field semantics — it remains an urgency/severity signal.
- No change to sprint planning logic — sprint promotion is unaffected.
- No cross-horizon bulk-set operation — items are updated individually when touched.
