---
id: BL-013
title: Improve product-discovery output to support tightened personas contract
priority: P2
status: backlog
created: 2026-05-01
---

## Summary

Improve `product-discovery` to produce richer persona-precursor output: named segments, attitudinal axes, jobs-to-be-done candidates, and structured real-world scenarios. The current discovery skill produces `target_user_summary` (a free-form blob); downstream skills (especially `user-personas`, see BL-011) need structured fields they can validate against.

This is a schema change to `state/discovery.yaml` plus interview-flow additions to capture the new fields. Independent of BL-011 in branching but logically pairs with it — BL-011 hard-gates on these fields existing.

## The gap

Today's `product-discovery` SKILL.md (L2 and L3 paths) does good work on:

- Problem articulation
- Target audience description
- Pain measurement (L3)
- Market context (L3)
- Validation rubric (L3)

What it does *not* produce in structured form:

1. **Named segments** — the discovery interview surfaces "who has this pain" but doesn't formally separate them into named groups with rationale. Personas downstream end up inferring segments from prose.
2. **Attitudinal axes** — discovery often reveals "some users are skeptics, some are enthusiasts" but the axis itself is not captured as a structured artifact. Personas need this to verify diversity.
3. **JTBD candidates** — discovery touches on what users are trying to accomplish but doesn't distill jobs-to-be-done as testable hypotheses for personas to anchor tasks.
4. **Real-world scenarios** — phase gates require "at least one concrete real-world scenario per persona," but the scenario originates in discovery. The current skill gathers them but doesn't format them as reusable artifacts.

The gap shows up clearly in BL-011: tightening the personas contract requires fields that discovery currently doesn't produce in machine-readable form.

## Proposed schema additions to state/discovery.yaml

```yaml
# Existing fields preserved:
target_user_summary: ...
problem_statement: ...
# (and L2/L3 fields)

# New structured fields:
segments:
  - id: seg-1
    name: "Solo founders pre-revenue"
    description: "Founders with an MVP and no paying customers yet"
    rationale: "Identified during interview — pain peaks here because runway pressure overlaps with no validation"

attitudinal_axes:
  - id: axis-1
    name: "Risk tolerance"
    poles:
      low: "Validation-first — won't ship without external signal"
      high: "Conviction-driven — ships on intuition"
    rationale: "Surfaced in interview when user described two distinct customer archetypes"

jtbd_candidates:
  - id: jtbd-1
    when: "I am two weeks from a fundraise"
    i_want_to: "show traction signal that doesn't depend on revenue"
    so_that: "investors don't discount the round on pre-revenue grounds"
    confidence: "medium — based on user's own past experience, not validated externally"

scenarios:
  - id: scn-1
    persona_seed: "Solo founder, ~6 months in, technical background"
    moment: "Friday night before a pitch on Monday"
    context: "Has a deck, has a demo, has zero customer quotes"
    pain_point: "Cannot show signal that the product solves a real pain"
    current_workaround: "Uses friends as 'customers' which investors see through"
```

The schema is additive — existing discovery output remains valid; new fields are populated for new runs.

## Interview-flow additions

The discovery skill already conducts a structured interview at three depths. The additions sit at well-defined points in the existing flow rather than forcing new interview rounds:

**L1 (intent and boundaries):**
- Current: produces target user summary, core feature set, out-of-scope items
- Addition: at minimum, capture one named segment with rationale and one real-world scenario. L1 is intentionally light — segments and scenarios are mandatory; axes and JTBD are optional but offered.

**L2 (problem and success):**
- Current: adds problem definition, audience refinement, success criteria, framing challenge
- Addition: explicitly ask for at least one attitudinal axis ("Who in this audience would push back on the framing? What's the spectrum?") and capture as structured field. JTBD candidates encouraged.

**L3 (full pain thesis):**
- Current: adds pain measurement, market context, accountability, escalation, validation rubric
- Addition: minimum 2 segments, minimum 1 attitudinal axis, minimum 2 JTBD candidates, minimum 2 scenarios. These are enforced as exit criteria.

## Decisions needed

1. **Backwards compatibility for state/discovery.yaml.** Existing projects have the old schema. Approach: lazy migration — when `user-personas` runs and discovery is missing new fields, prompt the user to add them rather than re-run discovery. Old projects keep working.
2. **Should JTBD be mandatory at any depth?** Lean: optional at L1, encouraged at L2, mandatory at L3. JTBD framing is specific and not every team uses it; forcing it at L1 is overhead.
3. **How far to push attitudinal axes?** Lean: one axis minimum at L2, two minimum at L3. Beyond two, diminishing returns and the framework starts feeling academic.
4. **Should scenarios be cross-linked to personas later?** Lean: yes — when `user-personas` instantiates an archetype, it links to the originating scenario(s). Provides traceability "this persona came from this real moment."

## Implementation outline

1. Update `skills/product-discovery/SKILL.md` to capture the new structured fields at the appropriate depth
2. Define schema additions in a comment block in the SKILL.md (since there is no formal schema file convention yet)
3. Update phase gate exit criteria in `rules/phase-gates.md` for DISCOVER (net-new-feature, external-integration) — add the new minimum-field requirements at L2 and L3
4. Update `state/discovery.yaml` template if one exists
5. Update `docs/user-guide/skills-reference.md` discovery entry
6. Update `docs/user-guide/state-and-memory.md` with the new schema
7. Add lazy-migration note to BL-011 implementation (BL-011 needs to handle pre-existing discovery files gracefully)

## Connection to other backlog items

- **BL-011** (personas promote) — pairs directly. BL-011 hard-gates on these fields; this item produces them.
- **BL-012** (focus group) — indirect dependency. Better discovery → better personas → better synthetic instances.
- **Existing phase gates** (DISCOVER exit criteria) — adding the new minimums updates the exit criteria.

## Branch

`feat/discovery-handoff`

## References

- Current skill: `/Users/carsonsweet/dev/sweetclaude/skills/product-discovery/SKILL.md`
- Phase gates: `/Users/carsonsweet/.claude/rules/sweetclaude/phase-gates.md` (DISCOVER exit criteria)
- State schema: `/Users/carsonsweet/dev/sweetclaude/.sweetclaude/state/` (in any active project)
