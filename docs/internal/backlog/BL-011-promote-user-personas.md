---
id: BL-011
title: Promote personas to framework-level — rename and tighten discovery contract
priority: P2
status: backlog
created: 2026-05-01
---

## Summary

Rename `product-user-personas` → `user-personas` and promote the skill from the `product` bucket to framework-level (alongside `master`, `find-skill`, `status`, etc.). Tighten the contract so the skill requires validated discovery output as input — not as an optional starting point. Add diversity verification across attitudinal axes to the persona definition flow.

This is foundational work that BL-012 (`product-user-focus-group`) depends on.

## Why promote out of the `product` bucket

Personas are not exclusively a product artifact. They inform:

- Product work — discovery, brief, PRD, scope, sprint planning
- Design work — UX flows, information architecture, design critique
- Marketing work — positioning, messaging, market segmentation
- Code work — feature acceptance criteria, test scenarios
- Operations — onboarding playbooks, support content

The flat-prefix convention exists to communicate which bucket owns a skill. Personas are owned by no single bucket; they are foundational. The framework-level naming (no prefix) signals "this is consumed everywhere."

This is the same architectural reasoning that places `master`, `find-skill`, and `status` outside the bucket prefix — they are framework-level resources, not domain-level work.

## Why tighten the discovery contract

The current skill reads `state/discovery.yaml` opportunistically: *"Read `.sweetclaude/state/discovery.yaml` if it exists — use `target_user_summary` as a starting point."* This makes discovery a soft suggestion rather than a hard prerequisite.

The failure mode: a user runs `product-user-personas` without doing discovery first, the skill happily walks through persona definition with no grounding, and the resulting personas reflect the user's pre-discovery assumptions rather than examined ones. Discovery exists to challenge framing. Skipping it produces personas that survive no scrutiny.

Required change: the skill refuses entry without validated discovery output. Specifically, `state/discovery.yaml` must contain (proposed schema — actual fields settled in BL-013):

- At least one defined segment with rationale
- At least one attitudinal axis (e.g., "skeptic ↔ enthusiast," "price-sensitive ↔ premium-tolerant")
- At least one real-world scenario captured during the discovery interview
- A target user summary that survived at least one challenge round

If discovery output is missing or incomplete, the skill stops and routes to `/sweetclaude:product-discovery` with the gap explained.

## Why add diversity verification

A persona set with three personas all leaning the same direction on every attitudinal axis is not a persona set — it is one persona drafted three times. Diversity verification is an explicit step at the end of persona definition that cross-checks the personas against the attitudinal axes from discovery and flags coverage gaps.

Concrete flow:

1. User defines personas one at a time (existing flow)
2. After the last persona is marked done, the skill cross-tabs personas against attitudinal axes
3. If any axis is covered by zero personas or only one direction, the skill surfaces the gap:
   > "You have three personas, all of whom are price-sensitive. Discovery identified a price-sensitive ↔ premium-tolerant axis. Is the premium-tolerant end out of scope, or did we miss a persona?"
4. User decides: add a persona, mark the dimension out of scope (recorded as scope decision), or override with rationale

This step is non-skippable. It is fast — a minute or two — and prevents a class of errors that show up much later as "we built for the wrong segment."

## Decisions needed

1. **Backwards compatibility for the rename.** Hard cut, or alias `product-user-personas` to `user-personas` for some period?
2. **Always-loaded or domain-loaded?** Framework-level skills are sometimes always loaded (`master`, `find-skill`). Personas could be always loaded (cross-cutting) or loaded only when a relevant phase is active. Lean: always loaded — like `find-skill`, the cost is small and the skill is referenced from many other skills.
3. **State migration for existing projects.** Projects with `state/personas.yaml` already populated should not be invalidated. The diversity verification check should run lazily — flag gaps next time the skill is invoked, don't auto-fail existing state.

## Implementation outline

1. Move `skills/product-user-personas/` → `skills/user-personas/` (rename directory and SKILL.md frontmatter `name`)
2. Update `config/phase-skills.yaml` — remove from `product.skills`, add to `always_loaded.skills` (decision pending in Q2)
3. Update SKILL.md entry section: replace optional discovery read with mandatory contract check; refuse and route on missing/incomplete discovery
4. Add diversity verification step at end of persona loop
5. Update `find-skill` routing entries that reference the old name
6. Update CHEATSHEETs (CHEATSHEET-NEW-PROJECT.md, CHEATSHEET-EXISTING-PROJECT.md) and README references
7. Update `docs/user-guide/skills-reference.md`
8. Update `docs/architecture-sweetclaude-v1-2026-04-13.md` skill catalog
9. Add migration note to changelog

## Connection to other backlog items

- **BL-012** (`product-user-focus-group`) depends on this — focus group reads `state/personas.yaml` produced by the renamed skill
- **BL-013** (discovery handoff improvements) pairs with this — defines the actual schema of the discovery output that this skill requires
- **BL-014** (caucus pattern formalization) is independent but referenced from BL-012

## Branch

`feat/personas-promote`

## References

- Current skill: `/Users/carsonsweet/dev/sweetclaude/skills/product-user-personas/SKILL.md`
- Architecture doc: `/Users/carsonsweet/dev/sweetclaude/docs/architecture-sweetclaude-v1-2026-04-13.md` (flat-prefix naming convention)
- Phase-skill mapping: `/Users/carsonsweet/dev/sweetclaude/config/phase-skills.yaml`
