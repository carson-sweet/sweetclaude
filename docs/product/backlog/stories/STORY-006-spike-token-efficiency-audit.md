---
id: STORY-006
type: story
title: "Spike: token efficiency audit — measure and reduce framework overhead per session"
status: new
priority: soon
effort: m
epic: null
milestone: null
sprint: null
tags: [spike, cost, tokens, prompt-cache, performance, framework]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
---

## Description

As a SweetClaude user running nontrivial projects on Opus, I want the framework's per-session token overhead to be audited and reduced, so that I'm paying for reasoning and implementation work — not for framework boilerplate re-read on every turn.

**Origin:** Filed 2026-05-13 by Carson Sweet. Derived from a multi-hour MS-003 replanning session with a five-figure token burn. Context: Opus at 1M context is expensive; many observed overhead sources are avoidable framework choices, not unavoidable reasoning costs.

**Observed overhead sources from a real session:**

| Source | Estimated overhead | Notes |
|---|---|---|
| SessionStart hook context dump | ~500 tokens/session | Full ethos block, improvement-register summary, paths block, schema version — most of which the model has memorized |
| Skill instruction bodies | ~6000 tokens for `bootstrap` alone | Meta-instructions and bash-script bodies the model re-reads step-by-step |
| State files reloaded per skill | Compounds across all skills in a chain | Every skill independently reads `sweetclaude.yaml`, `phase.yaml`, `session-state.yaml` |
| `big-picture` / `status` / `recap` output | Full ASCII tree on every call | Recomputes from scratch; no delta mode |
| No prompt-cache discipline | Framework-wide | Skill bodies are large enough to benefit from explicit cache breakpoints; none declared |
| MEMORY.md auto-loaded every turn | Compounds as memory grows | 15+ entries loaded whether relevant or not |
| Skills re-read what prior skills already read | Compounds in chains | `bootstrap` → `master` → `status` → `big-picture` each ingest the same state files |

### Six proposed tracks

**A. Prompt-cache breakpoints** — Identify which skill-instruction bodies are stable enough across invocations to benefit from Anthropic's 5-minute prompt cache TTL. Most skill bodies are stable. Mark them with explicit cache breakpoints. Estimated impact: large — `bootstrap` alone is ~6000 tokens read every session.

**B. Skill-instruction compaction** — Many skills contain step-by-step bash scripts and Python blocks inline. Move these into sidecar runner scripts the skill invokes by name, reducing skill bodies to thin "invoke runner, interpret output" instructions. Estimated impact: medium-large.

**C. State-load consolidation** — Replace per-skill state-file reads with a single shared "session state" preloaded once per session and referenced by name. Extend the existing `pre-loaded session state` pattern (already used by some skills) to all skills. Estimated impact: medium.

**D. Output minimization** — Skills that render state (`status`, `recap`, `big-picture`) support a `--minimal` mode that emits only changes since last render, or a structured artifact other skills can consume without re-parsing. Estimated impact: medium per call, large in chained sessions.

**E. MEMORY.md scoping** — Load only relevant memories at session start (filter by tags, project, or by an LLM-classified relevance pass at session boot). Estimated impact: small per turn, compounds as memory grows.

**F. Skill-chain routing overhead** — When a chain of skills is invoked (`_route` → target skill), the routing skill body should be one-shot — not re-read into context as the chain unfolds. Estimated impact: small per chain, compounds.

### Interaction with other enhancements

- **STORY-005** (model-aware execution) routes each skill to the right model tier — (A)+(B)+(C) reduce the token count at each tier regardless of which model is used.
- **STORY-003** (wave planning) reduces total Opus turns by landing design once and running impl at a cheaper model.
- This spike is independently shippable — does not depend on STORY-004 or STORY-005.

## Acceptance Criteria

- [ ] Run a real session through token accounting: measure how many input tokens were framework overhead vs project content vs user content — establish a baseline
- [ ] Identify top-3 cost contributors and the lowest-effort intervention per contributor
- [ ] Prototype the highest-ROI intervention (likely track A — prompt-cache breakpoints on the largest stable skills) and measure the token reduction on a representative session
- [ ] Ship at least one of tracks A, B, C, D as a concrete enhancement in a near-term release; defer the rest based on measured impact
- [ ] Decision artifact: which tracks shipped, which deferred, measured reduction vs baseline

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
