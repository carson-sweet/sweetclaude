---
id: BL-014
title: Document caucus as a formal subagent architectural pattern
priority: P3
status: backlog
created: 2026-05-01
---

## Summary

Add a "Subagent patterns" subsection to `architecture-sweetclaude-v1.md` formalizing **caucus** as a documented architectural primitive. Lightweight — one paragraph plus a list of current and possible instances. The goal is to prevent pattern drift as more caucus-shaped skills are added.

The word "caucus" stays internal — it is an architectural term, not a user-facing skill name. User-facing skills use domain language (`product-user-focus-group`, not `user-interview-caucus`). The QA caucus is the only place "caucus" appears in user-visible names today, and that subagent set is invoked from inside `code-feature` rather than as a standalone command.

## The pattern

```
Caucus

A pattern in which N parallel isolated subagents — each instantiated with
a defined role or perspective — return structured findings independently,
which are then synthesized by the orchestrating skill.

The isolation is non-negotiable: subagents in a caucus cannot see one
another's reasoning, drafts, or outputs. Cross-contamination collapses
the diversity that makes the pattern work.

Each caucus instance specifies:
  - The subagent role definitions (specialist roles, persona archetypes,
    stakeholder perspectives, etc.)
  - The structured response schema each subagent must produce
  - The synthesis stage that aggregates findings into a single output
  - Mandatory diversity across roles — a caucus of three identical roles
    is not a caucus
```

## Current and proposed instances

| Caucus | Subagent roles | Invoked from | Status |
|---|---|---|---|
| **QA caucus** | 3 specialist QA roles: service/API, component/UI, integration | `code-feature` (TDD Level 3 pipeline) | Implemented |
| **User focus group caucus** | N synthetic instances of canonical persona archetypes from `state/personas.yaml` | `product-user-focus-group` | Proposed (BL-012) |
| **Stakeholder review caucus** | N C-level personas (CEO, CFO, CTO, CISO, etc.) pressure-testing a strategic decision | (future, not scoped) | Hypothetical |
| **Adversarial review caucus** | N domain-adversary roles (security, legal, compliance, accessibility) reviewing a design or change | (future, not scoped) | Hypothetical |

The hypothetical instances are listed not because they need to be built — they may never be — but to make clear the pattern generalizes beyond the two current cases.

## Why formalize

Without formalization:
- Each caucus-shaped skill is implemented based on whatever the prior author did, with drift in subagent isolation rigor, response schemas, and synthesis approaches
- New maintainers have to reverse-engineer conventions from prior skills
- The non-negotiable rule (isolation) can erode through "minor" exceptions

With formalization:
- New caucus-shaped skills follow a documented pattern
- Subagent isolation requirements are stated once, applied everywhere
- The pattern is greppable in code review ("this skill claims to be a caucus but the subagents see each other's responses — fail")

The cost is one paragraph plus a table. The benefit is consistency over time as more caucus-shaped skills are added.

## Where it goes

`docs/architecture-sweetclaude-v1-2026-04-13.md` — add a new subsection under the architecture pattern section, between the existing "Architecture Pattern" and "File Architecture" sections. Title: **Subagent Patterns**. Content: the pattern definition above, plus the table of current and proposed instances.

Cross-references to add:
- `code-feature` SKILL.md — note that QA caucus implements the caucus pattern (see architecture)
- `agents/sweetclaude/qa-caucus-*.md` — same note in agent definitions
- `product-user-focus-group/SKILL.md` (when BL-012 lands) — note that the focus group implements the caucus pattern
- `docs/user-guide/how-it-works.md` — "Why Subagents Are Isolated" section already touches on this; add a one-line link to the caucus-pattern definition

## Decisions needed

1. **Should we also document the *non-caucus* subagent patterns?** Currently SweetClaude has at least two non-caucus subagent uses: the test-writer/implementer pair (sequential isolation, not parallel), and the John Wick check-in pattern. If we are documenting caucus, we should consider whether to document these too, for completeness.
   Lean: yes, brief paragraph each. Total addition stays under one page.
2. **Where does the subagent-isolation principle itself live?** Today it is implicit in TDD-level documentation and skill-by-skill discussion. It could be promoted to a top-level architectural driver in the drivers table (currently 10 drivers). Lean: add as driver #11, or add a brief mention to driver #6 (TDD enforcement hooks).

## Implementation outline

1. Draft the "Subagent Patterns" subsection content
2. Edit `docs/architecture-sweetclaude-v1-2026-04-13.md`
3. Add cross-references in the four locations listed above (skipping `product-user-focus-group` until BL-012 lands)
4. Optionally: address decision Q1 by adding non-caucus pattern paragraphs in the same subsection
5. Update `docs/user-guide/how-it-works.md` to reference the architecture-doc subsection

## Connection to other backlog items

- **BL-012** (focus group) — when this lands, `product-user-focus-group` SKILL.md should reference the caucus-pattern subsection. If BL-014 ships first, BL-012 references it. If BL-012 ships first, BL-014 cross-references back.
- **BL-011** and **BL-013** are independent

## Branch

`docs/caucus-pattern`

## References

- QA caucus subagents: `/Users/carsonsweet/dev/sweetclaude/agents/sweetclaude/qa-caucus-service.md`, `qa-caucus-component.md`, `qa-caucus-integration.md`
- Architecture doc: `/Users/carsonsweet/dev/sweetclaude/docs/architecture-sweetclaude-v1-2026-04-13.md`
- TDD discussion of subagent isolation: `/Users/carsonsweet/dev/sweetclaude/docs/user-guide/tdd.md` (Level 2 and Level 3 sections)
- How-it-works subagent isolation: `/Users/carsonsweet/dev/sweetclaude/docs/user-guide/how-it-works.md` ("Why Subagents Are Isolated")
