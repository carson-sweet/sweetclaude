---
name: sweetclaude-strategy-narrative-arc
description: "Build and query a knowledge graph connecting strategic claims, proof points, objectives, and supporting/opposing evidence. Answers 'what supports this claim' and 'what would strengthen this objective.'"
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Narrative Arc

Build and query the strategic narrative graph.

## What This Is

The narrative arc is a typed knowledge graph that connects everything in your strategy:
- **Objectives** — what you're trying to achieve
- **Claims** — assertions you make about the world, the problem, or your solution
- **Proof points** — evidence that supports claims (data, research, testimonials, demonstrations)
- **Supporting literature** — published work that backs your position
- **Opposing literature** — published work that challenges your position
- **Conclusions** — what follows from the claims + evidence
- **Open questions** — things you don't know yet that matter

Documents (papers, briefs, specs) grow as leaves on this framework — each one exists to strengthen the arc's ability to achieve its objectives.

## Commands

### Build: `narrative-arc build`

Walk the user through constructing or extending the arc:

1. **Objectives.** What are you trying to achieve strategically? (not product features — strategic outcomes)
2. **Claims.** What do you assert is true that supports those objectives?
3. **Evidence.** For each claim — what supports it? What opposes it? Rate confidence: high/medium/low.
4. **Gaps.** Where is evidence missing? What would strengthen a weak claim?
5. **Connections.** How do claims support objectives? How do documents feed claims?

Save to `strategy/narrative-arc/arc.md` as structured markdown.

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

`strategy/narrative-arc/arc.md` — human-readable, AI-parseable structured markdown. Not a database — the graph is small enough to fit in a file.

## Rules

- Other skills READ the arc (meeting-prep checks confidence, academic checks what to prove). Only this skill WRITES to it.
- Confidence ratings are honest. "Low" means "we believe this but can't prove it yet." That's fine — it tells you where to focus.
- The arc is never "done." It evolves as evidence accumulates.
