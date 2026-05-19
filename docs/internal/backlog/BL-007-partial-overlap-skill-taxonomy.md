---
id: BL-007
title: Resolve 4 partial-overlap skill taxonomy decisions
priority: P2
status: backlog
created: 2026-05-01
---

## Summary

Four proposed skills from the syncog inventory have a real distinction from existing SweetClaude skills, but the boundary is blurry. Building them without explicit scope decisions would create taxonomy confusion — users would not know when to invoke which skill.

These need decisions before any build, not specs and tests.

## The four

### 1. `design-thinker` vs `product-discovery` L2

`product-discovery` L2 step 57 is "challenge the framing." `design-thinker` proposes problem reframing as a separate entry point. Risk: redundant questioning, user confusion about when to use each.

**Options:** separate skill / mode within `product-discovery` / drop entirely / merge as L4 depth.

### 2. `strategy-concept` → `concept-framing` vs `product-discovery` L1

`product-discovery` L1 step 34 already handles "describe what you're building" — raw idea intake. `concept-framing` proposes a step *before* discovery for raw-idea-to-concept-statement work.

**Options:** quick shortcut skill / genuine earlier phase / drop and use discovery L1 / merge into `product-brief` intake.

### 3. `product-user-workflows` vs `product-user-personas` + `design-user-flows`

Personas already capture per-task definitions (steps 49–56). Design-user-flows already captures interface step sequences. The proposed skill claims a "task-layer journey" between them.

**Options:** intermediate layer / merge into personas / merge into flows / drop.

### 4. `design-services-design` — already absorbed?

`docs/native-skills-redesign-draft-v1.0-20260426.md` section 2c explicitly marks `design-services-design` for absorption into `design-architecture`. Inventory tagged it as a new Plan 2 skill — contradicting the prior decision.

**Options:** honor the absorption decision (drop the spec) / reopen the decision / split into two skills (architecture-level vs service-boundary-level).

## Decision-making approach

Each of these is a small design decision — probably 15-30 minutes of thought per skill, not a build effort. Could be batched in a single design session. Until decisions land, leave specs in `/syncog-skills-corpus/{slug}/specs/` but do not act on them.

## References

- Verification report: `/Users/carsonsweet/.claude/plans/delegated-forging-lerdorf.md`
- Native skills redesign: `/Users/carsonsweet/dev/sweetclaude/docs/native-skills-redesign-draft-v1.0-20260426.md` section 2c

## Connection to other backlog items

- BL-005 (10 outright duplicates) — sibling cleanup
- BL-008 (clean keepers) — these 4 should not be built until decided
