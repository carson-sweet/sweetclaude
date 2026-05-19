# BL-016 Spike: GStack Competitive Analysis

**Date:** 2026-05-05  
**Source:** https://github.com/garrytan/gstack  
**Status:** DONE

---

## What GStack Is

GStack is Garry Tan's (YC CEO) open-sourced Claude Code setup, published March 2026. It packages 23 specialist slash commands that position Claude Code as a "virtual engineering team": `/office-hours` (YC-style product review), `/plan-eng-review` (engineering manager), `/review` (staff engineer code review), `/qa` (QA lead with browser), `/cso` (OWASP/STRIDE security officer), `/ship` (release engineer), and more.

It launched to 82K GitHub stars and 12K forks — the fastest-growing Claude Code toolkit by distribution reach.

The workflow follows a sprint pipeline: **Think → Plan → Build → Review → Test → Ship → Reflect**. Each skill produces artifacts that downstream skills consume. Parallelism is achieved via [Conductor](https://conductor.build), an external tool running 10–15 simultaneous Claude Code sessions.

Architecture: CLAUDE.md-driven workflow, plain markdown skill files, no Skills 2.0 agentic primitives, no frontmatter-based tool restrictions, contextual model selection (not per-skill override).

---

## Where It Overlaps with SweetClaude

| Concept | GStack | SweetClaude |
|---|---|---|
| Multi-role review | `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review` via `/autoplan` | QA caucus, code-reviewer, security-reviewer subagents |
| QA | `/qa`, `/qa-only` — diff-aware, auto-generates regression tests | QA caucus (service, component, integration specialists) |
| Security | `/cso` — OWASP + STRIDE audit | security-reviewer subagent |
| Sprint/workflow | Think → Plan → Build → Review → Test → Ship → Reflect | Phase pipeline (DISCOVER → DEFINE → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP) |
| Documentation | `/document-release` | `sweetclaude:documents-update-docs` |
| Retrospective | `/retro` | Improvement register + `sweetclaude:retro` (BL-030) |

---

## Where It Diverges

**No isolation enforcement.** GStack's `/autoplan` runs CEO → Design → Eng reviews *sequentially* — later reviewers see earlier reviewers' outputs. "Taste escalation" means accumulated decisions bias future ones. SweetClaude's QA caucus enforces strict isolation as a non-negotiable architectural rule: cross-contamination collapses the diversity. GStack's review pattern is aggregation with drift; SweetClaude's is diversity-preserving consensus.

**Role-based vs. phase-based.** GStack gives Claude specialist roles and trusts the sprint sequencing to produce quality. SweetClaude enforces phase gates — specific exit criteria that must be met before advancing. GStack is about velocity; SweetClaude is about discipline. Neither is wrong for its target user.

**No phase dwelling.** GStack optimizes for a solo founder moving fast ("810× productivity increase"). SweetClaude's deference system (collaborative/guided/autonomous) and explicit "never invite advancement" rule serve users who want quality gates, not just speed.

**External parallelism dependency.** GStack requires Conductor for parallel sessions. SweetClaude uses Claude Code native subagent spawning and worktrees — no external dependency.

**Not on Skills 2.0.** GStack uses the same CLAUDE.md-driven pattern as older SweetClaude skills. No tool-access frontmatter restrictions, no lifecycle hooks co-located with skills, no model override per skill. This is significant: the highest-profile Claude Code toolkit in the ecosystem is not adopting Skills 2.0 primitives, which reduces urgency for SweetClaude to migrate (see BL-001 findings).

**MIT vs. AGPL.** GStack is pure MIT — no commercial licensing signal. SweetClaude is AGPL-3.0 with a deferred private-use exception (BL-038). GStack's openness is a distribution advantage; SweetClaude's licensing is a future monetization signal. Different bets.

---

## Recommendation: Differentiate

GStack owns the "celebrity toolkit, maximum breadth, maximum speed" position. Competing there is a losing bet — 82K stars in two months is not a market gap to fill, it's a market Garry Tan already occupies.

SweetClaude's differentiation is structural, not cosmetic:

1. **Phase gates as quality enforcement.** GStack trusts roles; SweetClaude enforces exit criteria. For teams building regulated, audited, or high-stakes software, gate enforcement matters more than role breadth.

2. **Caucus isolation as a principle.** GStack's sequential aggregation with taste drift is a real tradeoff. SweetClaude's non-contamination rule produces more honest multi-perspective review. Name it explicitly in positioning.

3. **Deference system.** GStack has no equivalent — it's always "go fast." SweetClaude's collaborative/guided/autonomous modes let teams tune pace vs. autonomy. This matters for onboarding new team members or navigating unfamiliar domains.

4. **Skills 2.0 readiness.** GStack is not building toward agentic primitives. SweetClaude has the opportunity to be the first major toolkit to adopt tool-access restrictions and lifecycle hooks natively — reducing the class of human-error mistakes GStack's pattern cannot prevent.

**No new backlog items required.** This spike's findings feed into existing open items: BL-039 (marketplace positioning), BL-040 (async background execution — analogous to Conductor), BL-041 (caucus-style code review — direct overlap with GStack's `/autoplan`).
