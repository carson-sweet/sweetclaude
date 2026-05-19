---
id: STORY-020
type: story
title: Upfront story assessment and workflow template selection — risk, complexity,
  breaking status, effort, blast radius
status: new
priority: soon
effort: xl
epic: EP-001
sprint: null
tags:
- workflow
- assessment
- tdd
- risk
- breaking-changes
- caucus
- template-selection
- design-first
origin: manual
created: 2026-05-14
updated: 2026-05-15
closed_date: null
epic_sequence: 1
---

## Description

As a developer using SweetClaude, I want SweetClaude to assess each story upfront across multiple dimensions before any work begins, then select a pre-defined workflow template that implements the correct discipline end-to-end — from design through deployment — so that the level of rigor applied to a story matches its actual risk and complexity rather than being uniform across all work.

Assessment dimensions include: level of definition/design completeness, technical complexity, risk, breaking status, blast radius, effort level. The selected template determines: branch strategy, TDD level, QA requirements, which caucus agents run (and in what composition), code review requirements, and deployment gates.

**Balanced caucus requirement:** Caucus composition must prevent perpetual optimization — a caucus where every agent agrees with the author is useless. Templates must specify caucus agents by *role* (adversarial, supportive, domain-expert) not just by count, and must ensure at least one agent is explicitly tasked with finding what the author didn't think of.

## Acceptance Criteria

- [ ] When a story transitions to `active`, SweetClaude runs a structured upfront assessment and saves the result to the story file as a `## Assessment` section
- [ ] Assessment covers: definition completeness, technical complexity (xs/s/m/l/xl), risk level (low/medium/high/critical), breaking status (true/false), blast radius (isolated/module/cross-cutting/system-wide), effort estimate, and any special flags (external-input parsing, auth changes, data migration, public API change)
- [ ] Assessment result maps to a named workflow template from `config/workflow-templates.yaml`
- [ ] Selected template is shown to the user with the reasoning before work begins; user can override
- [ ] User override is logged to the story's `## Assessment` section with rationale
- [ ] Templates specify caucus composition by role: at minimum one adversarial agent, one supportive/continuity agent, one domain-specific agent; for breaking:true stories the adversarial slot is mandatory
- [ ] Assessment persists in the story file and is referenced by all subsequent phases — no phase re-derives it from scratch
- [ ] If story scope changes mid-work (detected by significant description edit or user statement), assessment re-runs and template re-selection is offered
- [ ] `config/workflow-templates.yaml` is extended to cover all needed risk/complexity combinations; gaps are surfaced as CHORE items
- [ ] Assessment storage format is decided and documented: frontmatter fields (machine-readable, queryable by skills) vs. `## Assessment` body section (richer narrative) vs. both; decision recorded in the story before implementation begins
- [ ] Reassessment triggers are defined and enforced: if story description changes substantially or user explicitly states scope has changed, assessment re-runs and template re-selection is offered before the next phase begins
- [ ] Caucus composition is specified by role, not agent name: each template slot is labeled adversarial / continuity / domain-expert; the same agent cannot fill the adversarial and continuity slots simultaneously; for breaking:true the adversarial slot is non-negotiable
- [ ] Override audit trail: when a user overrides the selected template, the override is written to the story file with the user's stated rationale and the template that was rejected; this data is available for retrospectives

## Open Questions

- What is the minimum viable set of templates for v1 of this feature?
- Should assessment run automatically when a story goes `active`, or should it be a deliberate user step? (Impacts Guided vs. Autonomous deference behavior)

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
