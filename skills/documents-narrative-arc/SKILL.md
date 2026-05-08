---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Build and query a knowledge graph connecting strategic claims, proof points, objectives, and supporting/opposing evidence. Answers 'what supports this claim' and 'what would strengthen this objective.'"
category: strategy
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Narrative Arc

Build and query the strategic narrative graph.

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:setup` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.strategy.base_path`. This is the base directory for all strategy artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. if base is `.sweetclaude/strategy`, competitive analysis goes to `.sweetclaude/strategy/competitive-analysis/`).

4. Write artifacts to those paths.

## What This Is

A typed knowledge graph that connects everything in your strategy:
- **Objectives** — what you're trying to achieve
- **Claims** — assertions you make about the world, the problem, or your solution
- **Proof points** — evidence that supports claims (data, research, testimonials, demonstrations)
- **Supporting literature** — published work that backs your position
- **Opposing literature** — published work that challenges your position
- **Conclusions** — what follows from the claims + evidence
- **Open questions** — things you don't know yet that matter

Documents (papers, briefs, specs) grow as leaves on this framework. Each one strengthens the arc's ability to achieve its objectives.

## Commands

### Build: `narrative-arc build`

Walk the user through constructing or extending the arc:

1. **Objectives.** What are you trying to achieve strategically? (not product features — strategic outcomes)
2. **Claims.** What do you assert is true that supports those objectives?
3. **Evidence.** For each claim — what supports it? What opposes it? Rate confidence: high/medium/low.
4. **Gaps.** Where is evidence missing? What would strengthen a weak claim?
5. **Connections.** How do claims support objectives? How do documents feed claims?

Save to `{base_path}/narrative-arc/arc.md` as structured markdown.

### Query: `narrative-arc query {question}`

Answer questions by traversing the graph:
- "What supports the claim that X?" → list proof points and literature
- "What would strengthen objective Y?" → identify weak claims and evidence gaps
- "How credible is claim Z?" → assess based on supporting vs opposing evidence
- "What's the strongest path from evidence to objective?" → trace the chain

### Update: `narrative-arc update`

When new evidence, documents, or claims are added, update the graph:
- Add the new node
- Connect to existing nodes
- Re-assess confidence levels where affected
- Flag if any objective's support chain weakened

## Storage

`{base_path}/narrative-arc/arc.md` — human-readable, AI-parseable structured markdown. Not a database — the graph is small enough to fit in a file.

## Rules

- Other skills read the arc (meeting-prep checks confidence, academic checks what to prove). Only this skill writes to it.
- Confidence ratings are honest. "Low" means "we believe this but cannot prove it yet." That is useful — it tells you where to focus.
- The arc is never done. It evolves as evidence accumulates.
