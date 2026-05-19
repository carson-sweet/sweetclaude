---
id: STORY-005
type: story
title: "Spike: model-aware skill execution — automatic or assisted model switching per skill"
status: new
priority: later
effort: m
epic: null
milestone: null
sprint: null
tags: [spike, model-routing, cost, skills, opus, sonnet, haiku]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
---

## Description

As a SweetClaude user, I want the framework to route each skill invocation to the appropriate model tier — or at minimum offer me a model switch with reasoning — so that I'm not paying Opus rates for mechanical file rendering or losing quality by running architecture work at Sonnet.

**Origin:** Filed 2026-05-13 by Carson Sweet. Derived from a multi-hour MS-003 replanning session where every step ran on Opus because there was no framework signal to drop to Sonnet. **Depends on STORY-004** (per-skill model declarations) — this spike cannot be meaningfully prototyped until every skill has a `requires.reasoning` value.

**Today:** Calling Claude Code at Opus runs every skill at Opus. Calling at Sonnet runs every skill at Sonnet. No mechanism exists for the framework to say "this skill needs Opus, switch up" or "this is `corpus-status`, drop to Haiku."

**Constraint:** Model switching should always offer, never force. The user's judgment is final.

### Four options to investigate

**Option A — Skill manifests as hints to the harness**
The harness reads each skill's declared `requires.reasoning` (STORY-004) and, when invoking the skill, suggests a model switch to the user: "This skill (`design-tech-spec`) needs high-reasoning capability. Switch to Opus for this skill, then return to current model? (Y / N / N for session)". Non-blocking; user can decline.

**Option B — Skill-internal sub-agent dispatch**
SweetClaude skills already invoke subagents for some work (Explore, test-writer, implementer). Extend this pattern so that mechanical sub-steps within an otherwise high-reasoning skill are dispatched to a cheaper model. Example: `design-architecture` runs at Opus, but its "list current files in `src/systems/`" sub-step dispatches to Haiku.

**Option C — Session-level skill chains with declared model per chain**
When the user invokes a sequence like `product-prd` → `epic-design` → `code-feature`, the framework could checkpoint between skills and prompt: "Moving from `epic-design` (high-reasoning) to `code-feature` (medium-reasoning). Drop to Sonnet to save tokens? (Y / N)".

**Option D — Background-agent escape hatch**
For skills where the highest-reasoning step is bounded (e.g. "write 1 ADR"), allow the user to dispatch that step to a one-shot Opus subagent and bring the result back into a Sonnet main session.

### Interaction with other enhancements

- **STORY-003** (wave planning) + this spike = biggest cost savings: design lands once at Opus, impl follows at Sonnet.
- **STORY-004** (per-skill declarations) is the prerequisite data layer.
- **STORY-006** (token efficiency) tightens per-turn footprint independently of model tier.

## Acceptance Criteria

- [ ] Document the friction points: where exactly in the framework the model switch would happen, what plumbing exists today in Claude Code's skill invocation path, what would need to be built
- [ ] Prototype at least Option A end-to-end in one skill (suggested: `design-architecture`) — user sees a model-switch prompt when invoking the skill from a non-Opus session
- [ ] Cost model: estimate token savings on a real session (the MS-003 replanning session from 2026-05-13 is the reference candidate)
- [ ] Decision artifact: ship one option, ship multiple, or none — with rationale

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
