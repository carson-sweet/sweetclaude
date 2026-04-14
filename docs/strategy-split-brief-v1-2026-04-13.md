# SweetClaude Strategy Split — Product Brief

**Date:** 2026-04-13
**Version:** 1.0
**Status:** Superseded by `docs/plans/skill-reorganization-plan-2026-04-13.md` (5-bucket architecture)
**Owner:** Carson Sweet

---

## 1. Executive Summary

SweetClaude is being restructured from a code-only development framework into a dual-capability system supporting both technical development (`code/`) and strategic product development (`strategy/`). The strategy side supports the full non-technical product lifecycle: business planning, competitive analysis, market positioning, messaging, and academic research that feeds commercial credibility. Shared infrastructure (phase gates, interaction model, deference levels, improvement register) applies to both sides. Individual skills within the strategy side handle specific work types — paper development, narrative arc tracking, file reconciliation, meeting prep — but they serve the higher-level strategic goals, not the other way around.

The first implementation priority is driven by active SynCog needs: academic publication feeding a positioning arc that supports commercialization conversations with university partners.

## 2. Problem Statement

SweetClaude currently only supports technical development workflows — code, TDD, debugging, deployment. But product development doesn't start or end with code. Before a line gets written, there's strategic positioning, competitive analysis, business planning, and messaging work that determines *what* gets built and *why it matters*. After code ships, there's market positioning, academic publication, and stakeholder engagement that determines whether anyone cares.

Today this work happens in unstructured folders with ad-hoc Claude sessions, manual context handoffs via continuation prompts, and no version control. Strategic artifacts get lost, decisions aren't tracked, and every new session starts from scratch. The same AI-assisted discipline that SweetClaude brings to code — structured phases, quality gates, improvement tracking, session continuity — is completely absent from the strategic side.

**Concrete example:** The SynCog Cultivated Persona paper exists as 27 markdown files across two directories with session exports mixed in, no git history, and continuation prompts as the only handoff mechanism. The paper feeds a positioning arc that connects to university partnerships and commercialization strategy, but that arc lives entirely in Carson's head. If he steps away for a month, an AI assistant would need hours of orientation just to understand what connects to what.

## 3. Target Audience

Solo product owner / founder running AI-assisted development from concept through commercialization. Technical enough to build software but also responsible for the strategic work that surrounds it — positioning, academic credibility, business development, stakeholder management. Not a team of specialists; one person wearing every hat, using AI as a force multiplier across all of them.

## 4. Solution Overview

Restructure SweetClaude into three directories:

- **`code/`** — existing technical skills, moved as-is
- **`strategy/`** — new skills for non-technical product development
- **`shared/`** — phase gates, interaction model, deference levels, improvement register, config

The work router learns to classify strategy work types and surface the right skills per phase. Strategy work flows through the same 7-phase pipeline but with different skills and different phase gate expectations at each step.

Strategy artifacts live in a `strategy/` directory within each project repo, parallel to `docs/`. This keeps them separable — move `strategy/` out and the repo looks like a standard code project.

Nine strategy subdirectories organize artifacts by domain:

```
strategy/
  reconciliation/          # Intake zone for unstructured files
    archive/               # Deprecated originals with lineage frontmatter
  positioning/             # Who we are, how we describe ourselves, terminology
  competitive/             # Competitive analysis, SWOT, landscape maps
  market-messaging/        # External messaging, pitch materials, stakeholder narratives
  biz-planning/            # Commercialization, monetization, IP strategy, licensing
  academic/                # Papers, lit reviews, publication strategy, venue planning
  meeting-prep/            # Deliverables per person/org, talking points, agendas
  narrative-arc/           # Cross-cutting knowledge graph connecting strategy domains
  decisions/               # Decision logs, assumption registers
  rag-index/               # LanceDB embeddings, vector store
```

Four skills built first (driven by active SynCog needs, in priority order):

1. **File reconciliation v2** — onboard unstructured files into strategy/, categorize, synthesize canonical docs (everything else works from a clean corpus)
2. **Academic paper development** — adapted from community skill (MIT), extended with first-principles starting point
3. **Narrative arc** — cross-cutting knowledge graph tracking how pieces connect and sequence across strategy domains (see Design Constraint below)
4. **Meeting prep** — stakeholder-specific deliverable generation

Remaining skills (positioning, competitive, market-messaging, biz-planning) built as needs arise.

### Design Constraint: Narrative Arc as Knowledge Graph

The narrative arc is NOT a timeline or sequence. It is a typed knowledge graph:

- **Node types:** objectives, audiences, first-principles, claims, proof points, supporting literature/research, opposing literature/research, conclusions, open concerns/issues/questions
- **Properties:** each node has credibility scores (scoring model TBD during DESIGN)
- **Documents as leaves:** on the framework of the arc, documents grow that serve specific purposes — each one strengthens the arc's ability to achieve its objectives
- **Queries:** the skill should answer "what supports this claim" and "what would strengthen this objective" by traversing the graph

This is a DESIGN phase concern, not a DEFINE concern — noted here to prevent the narrative-arc skill from being designed as a flat tracker.

## 5. Business Objectives

- Bring the same structured discipline to strategic work that SweetClaude already brings to code
- Eliminate context loss between AI sessions on strategic work
- Make the narrative arc — the connective tissue between academic, positioning, and commercial work — explicit and trackable
- Enable any AI assistant to pick up strategic work mid-stream without hours of orientation
- Keep strategic and technical artifacts cleanly separable

## 6. Scope

**In scope:**
- Directory restructure (`code/`, `strategy/`, `shared/`)
- Work router updates for strategy work types
- Phase-skills.yaml restructure for dual-track skill surfacing
- Four priority skills (reconciliation-v2, academic, narrative-arc, meeting-prep)
- Artifact placement rules enforced by SweetClaude (backlog guard against non-technical items routing to docs/)
- Adaptation of lishix520/academic-paper-skills (MIT) as foundation for academic skill
- Patterns from anthropics/skills doc-coauthoring integrated where applicable
- Conceptual brainstorming skill should use higher-performance model when available

**Out of scope:**
- Positioning skill (build when active positioning work begins)
- Competitive analysis skill (build when next competitive scan needed)
- Market messaging skill (build when there's an audience to message to)
- Biz planning skill (build when active deals require planning)
- coreyhaines31/marketingskills evaluation (parked, revisit when messaging work activates)
- Any changes to existing code/ skill behavior
- Multi-user or team workflows

## 7. Constraints & Assumptions

**Constraints:**
- Skills live in `~/.claude/skills/` (not git-tracked) — unwindable by deleting files
- Community skill adaptation limited to MIT/Apache 2.0 licensed work only (deanpeters/Product-Manager-Skills is CC BY-NC-SA, cannot use)
- Strategy artifacts must be separable from code repos (`strategy/` directory can be moved out)
- SweetClaude shared infrastructure (phase pipeline, interaction model) cannot break for existing code workflows
- Conceptual brainstorming should use a higher-performance model when available

**Assumptions:**
- Solo user — no multi-user collaboration workflows needed
- SynCog is the first project to exercise strategy skills, but the skills should be project-agnostic
- The existing reconciling-documents skill is superseded by reconciliation-v2 for strategy work (original remains useful for code-side doc comparison)
- RAG indexing of strategy/ corpus uses existing rag-index skill infrastructure

## 8. Success Criteria

1. `syncog-general` files are organized under `strategy/` with category subdirectories, versioned filenames, and canonical synthesized documents
2. Deprecated originals have frontmatter indicating lineage to canonical docs
3. The RAG index covers all canonical strategy documents
4. An AI assistant starting a fresh session on the SynCog project can identify the narrative arc, current paper status, and next strategic priorities within 5 minutes of orientation
5. Existing code/ skills work identically to before the restructure — zero behavioral regression
6. The work router correctly classifies "write a research paper" as strategy work and surfaces academic skills, not code skills
7. Backlog guard prevents non-technical items from landing in docs/backlog/

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Directory restructure breaks existing skill references | Medium | High | Move code/ skills one at a time, verify each before proceeding |
| Phase gates become unwieldy with two tracks of skills | Low | Medium | Strategy work types get their own skill lists in phase-skills.yaml, not mixed into code lists |
| Reconciliation-v2 produces low-quality canonical docs from messy inputs | Medium | Medium | User approves per-file plan before synthesis; canonical docs are drafts for user review, not final |
| Academic skill adaptation drifts from original's strengths | Low | Medium | Keep the 5-phase pipeline architecture; extend, don't rewrite |
| Narrative arc skill is too abstract to be useful | Medium | Medium | Ground it in the SynCog arc as the first concrete instance; generalize from there |

## 10. Timeline

No time estimates. Quality gates, not calendar gates. Build priority order is: reconciliation-v2 → academic → narrative-arc → meeting-prep. Each skill goes through its own DESIGN → PLAN → IMPLEMENT → VERIFY cycle.

## 11. Stakeholders

Carson Sweet — sole user, product owner, reviewer, and beneficiary.

---

## Community Skills Evaluation (conducted during DISCOVER)

| Repo | License | Quality | Verdict |
|---|---|---|---|
| lishix520/academic-paper-skills | MIT | High (2,500+ lines, 5-phase pipeline) | **ADAPT** — use as foundation for academic skill |
| anthropics/skills | Apache 2.0 | High (doc-coauthoring, internal-comms) | **STEAL PATTERNS** — 3-stage framework, reader testing |
| coreyhaines31/marketingskills | MIT | Unverified | **PARK** — evaluate when messaging work activates |
| deanpeters/Product-Manager-Skills | CC BY-NC-SA | High but unusable | **SKIP** — non-commercial license |

## Key Decisions from DISCOVER

| Decision | Rationale |
|---|---|
| Single repo, subdirectory split (code/, strategy/, shared/) | Shared infrastructure is natural; avoids duplication |
| One shared pipeline, strategy-aware | Phases are abstract enough; work router sub-classifies per work type |
| strategy/ in project repo parallel to docs/ | Separable — move strategy/ out and the repo looks normal |
| docs/ = code-generative artifacts only (Gherkin and beyond) | Clean boundary: does this artifact feed code generation? |
| Backlog stays in docs/ with guard | Product ideas route to strategy/, technical backlog stays in docs/ |
| Adapt academic-paper-skills (MIT) | Strong 5-phase pipeline, extend with first-principles start |
| narrative-arc is cross-cutting, own skill | Not inside positioning/ — coordinates across all strategy domains |
| Reconciliation first in build order | Everything else works from an organized, normalized corpus |
| Academic papers start from key concepts/arguments/first-principles | Before lit review, before platform analysis |
| Conceptual brainstorming uses higher-performance model | Strategic/creative work benefits from stronger reasoning |
