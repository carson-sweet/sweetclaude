---
name: product-discovery
description: Structured Discover phase for net-new products and apps. Persona-driven discovery, iterative feature brainstorming, optional competitive analysis. Scales to work type.
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Discover Deep — Structured Discovery for Net-New Work

You are conducting the Discover phase for a new product or application. This is not a freeform brainstorm — it is a structured interview that produces concrete personas, vetted features, and optional competitive intelligence.

**Work-type scaling:** The master skill routes here based on detected work type.
- **Products/apps:** Run the full workflow (all three stages below).
- **CLIs/libraries:** Run Stage 1 with primary user only, Stage 2 only if user requests, skip Stage 3 unless user requests.
- **Utilities/scripts:** Skip this skill — the master skill handles minimal Discover directly.

The user can always request the full workflow regardless of detected work type.

---

## Stage 1: Persona Discovery

Conduct an iterative interview to define all user personas.

**For each persona, capture:**
1. **Name/label** — a short identifier (e.g., "Field Sales Rep", "DevOps Engineer", "Casual Browser")
2. **Job title or role** — what they do professionally or contextually
3. **Tasks** — what specific tasks do they need to complete using this product?
4. **Success criteria per task** — what does success look like for each task? How does the user know they accomplished it?

**Interview protocol:**
- Start with the primary user: "Let's start with the primary user of this product. What's their role or job title?"
- Ask about their tasks one at a time. For each task, ask what success looks like.
- After each persona is fully defined, ask: **"Are there additional user personas we should define?"**
- If yes, repeat the full persona interview for the next persona.
- Continue until the user says all personas are captured.
- One persona at a time. One task at a time. Do not batch.

**After all personas are defined, present a consolidated view:**

```
## User Personas & Tasks

### Persona 1: [Name] — [Job Title]
- Task: [task description]
  Success: [what success looks like]
- Task: [task description]
  Success: [what success looks like]

### Persona 2: [Name] — [Job Title]
- Task: [task description]
  Success: [what success looks like]
...
```

Ask: **"Does this look right? Any corrections or additions?"**

Do not proceed to Stage 2 until the user confirms the consolidated view.

---

## Stage 2: Feature Brainstorming

After personas and tasks are confirmed, ask: **"Would you like me to brainstorm additional features and capabilities based on these personas?"**

If the user declines, skip to Stage 3.

If the user accepts:

**Brainstorming protocol:**
- Propose features **one at a time**, each with:
  - Feature name
  - Which persona(s) it serves
  - Brief rationale (1-2 sentences)
- After each feature, ask: **"Include or exclude?"**
- Track included and excluded features separately.
- **Maximum 10 features per batch.** After 10, say: "That's 10 features in this batch. Here's the included list so far: [list]. Would you like another batch of 10, or is this enough?"
- Continue batches until the user signals satisfaction.

**Brainstorming quality:**
- Features should be grounded in the personas and tasks defined in Stage 1, not generic.
- Propose at least 2 features that challenge or extend the user's original concept — not just obvious derivations.
- If a feature overlaps with something already in scope, note the overlap and ask if the user wants to keep both or merge.

After brainstorming is complete, present the final included feature list.

---

## Stage 3: Competitive Analysis

After feature brainstorming (or after persona confirmation if brainstorming was skipped), ask: **"Would you like me to do a quick competitive analysis — searching for similar products, projects, or open-source alternatives?"**

If the user declines, skip to Wrap-Up.

If the user accepts:

**Research protocol:**
- Search the web, GitHub, Product Hunt, and relevant directories for:
  - Competing products or services in the same category
  - Open-source projects solving a similar problem
  - Related tools or technologies
- Present each result with:
  - Name and URL
  - ~25-word synopsis
- Handle "nothing found" gracefully: "I searched [sources] and didn't find direct competitors. This is either a novel space or a niche without established players. We can proceed without competitive benchmarking."

**After presenting the list, offer two paths:**
1. **Drill down:** "Want me to go deeper on any of these? Pick one or more and I'll do a detailed analysis."
2. **Table stakes:** "Or I can analyze all of them together and extract a 'table stakes' feature set — the common features that users in this category expect as baseline."

If the user picks drill-down:
- For each selected competitor, research and present: what it does well, what it does poorly, pricing model, target audience, key differentiators.
- After each analysis, ask if the user wants to continue with more competitors or move on.

If the user picks table stakes:
- Analyze the competitive landscape and present a list of features that appear across multiple competitors.
- For each table-stakes feature, note which competitors have it and recommend include/exclude for the user's product.
- The user approves or rejects each table-stakes feature.

---

## Wrap-Up

After all stages are complete:

1. **Summarize what was produced:**
   - Number of personas defined
   - Number of tasks across all personas
   - Number of features included (original + brainstormed + table stakes)
   - Whether competitive analysis was performed
   - Key decisions made during discovery

2. **Save artifacts** to `.sweetclaude/`:
   - `brainstorm/personas.md` — consolidated persona/task view
   - `brainstorm/feature-list.md` — included features with rationale
   - `brainstorm/competitive-analysis.md` — competitor list and analysis (if performed)

3. **Log decisions** in `.sweetclaude/state/decision-log.md`.

4. **Do not push for phase advancement.** Present the summary and wait. The user decides when Discover is done.
