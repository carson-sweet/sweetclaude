---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:design-ux-review
user-invocable: true
description: Virtual UX review session. Spawns parallel subagents — one per persona — each walking through a flow or wireframe independently and returning structured feedback. Synthesizes findings into prioritized recommendations. All output labeled synthetic.
category: design
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Design UX Review

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:setup` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.design.base_path`. This is the base directory for all design artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. wireframes go to `{base_path}/wireframes/wireframe-*.html`).

4. Write artifacts to those paths.

Run a virtual UX review session. Each defined persona is instantiated as an independent subagent that walks through a user flow or wireframe and returns structured feedback. The orchestrator synthesizes findings across personas into consensus themes, divergent opinions, and prioritized recommendations.

All output is labeled **synthetic**. Synthetic findings are hypotheses to validate with real users, not a substitute for real research.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:setup` first. Stop.

Read `.sweetclaude/state/personas.yaml` — required. If missing or empty:
> "A UX review requires defined personas. Run `/sweetclaude:user-personas` first to define who you're designing for."

Stop if personas are absent.

Read `.sweetclaude/state/ux-flows.yaml` — optional but expected. If missing, the user can still provide a flow description manually.

Read `.sweetclaude/state/wireframes.yaml` — optional. If present, list available wireframe files so the user can choose what to review.

## Review Target Selection

Ask the user what to review:
> "What should the panel review?
> 1. A user flow (step-by-step interaction path)
> 2. A wireframe file
> 3. Both — walk the flow, then react to the wireframe
>
> Which, and for which story or flow?"

For **flow review:** extract the chosen flow's steps, entry point, success state, and error states from `ux-flows.yaml`. If `ux-flows.yaml` is missing, ask the user to describe the flow in plain language.

For **wireframe review:** read the specified HTML file. Extract the structural content — screen sections, labeled elements, annotation panel text — and describe it as a prose layout description for the subagents. (Subagents cannot render HTML visually; they work from the structural description.)

For **both:** provide the flow steps first, then the wireframe layout description as additional context.

## Persona Scope

Default: all personas in `personas.yaml`.

If more than five personas are defined, ask:
> "You have {N} personas. Review all of them or a subset? (More panels = richer coverage but slower.)"

## Session Execution

Spawn one subagent per persona using the Agent tool. All subagents run in parallel. Each subagent is isolated — it receives no output from the others.

### Subagent prompt template

Pass this to each subagent, filling in the persona and review target:

---
You are {persona.name}. Here is who you are:

**Role:** {persona.role}
**Primary goal:** {persona.primary_goal}
**Key tasks:** {persona.key_tasks joined as bullets}
**Success looks like:** {persona.success_criteria}
**Deal-breakers:** {persona.deal_breakers}
**Background / context:** {persona.background}

You are being asked to walk through a product experience and give honest feedback as this person — not as an AI assistant. Stay in character throughout. Do not be diplomatic. If something would frustrate you, say so directly.

---

**What you are reviewing:**

{flow steps and/or wireframe layout description}

---

Respond with ONLY this JSON structure — no prose outside the JSON:

```json
{
  "persona_id": "{persona.id}",
  "first_impression": "One sentence, in your voice, as {persona.name}",
  "would_complete_task": true | false,
  "completion_confidence": "confident | uncertain | no",
  "confusion_points": [
    {
      "element": "Which step or screen element",
      "issue": "What confused or frustrated you",
      "severity": "high | medium | low"
    }
  ],
  "what_worked": ["string", "..."],
  "what_didnt_work": ["string", "..."],
  "deal_breaker_triggered": true | false,
  "deal_breaker_reason": "Explain if true, null if false",
  "verbatim": "One sentence in your voice summarizing the overall experience"
}
```
---

### Handling invalid responses

If a subagent returns malformed JSON or breaks character, re-prompt it once with the same prompt plus:
> "Your previous response was not valid JSON. Return only the JSON structure, nothing else."

If it fails again, mark that persona's result as `incomplete` and continue synthesis with the remaining results.

## Synthesis

After all subagents complete, synthesize findings:

### 1. Task completion rate
Count how many personas `would_complete_task: true` with confidence `confident` or `uncertain`. Present as: `{N} of {total} personas would complete the task ({percent}%).`

### 2. Deal-breakers
List any `deal_breaker_triggered: true` results with the persona name and reason. These are the highest-priority findings.

### 3. Consensus findings
Issues flagged by 2 or more personas as `high` or `medium` severity. These are confirmed friction points regardless of persona differences.

### 4. Divergent findings
Issues flagged by only one persona, or where personas disagreed. These are persona-specific needs — worth noting but lower priority than consensus findings.

### 5. What worked
Items appearing in `what_worked` across 2+ personas.

### 6. Priority recommendations
Derive the top 3–5 actionable changes from the synthesis:
- Deal-breakers come first regardless of consensus count
- Then consensus high-severity issues
- Then consensus medium-severity issues
- Phrase each as a specific change: "Move the [X] action to [location]" not "Improve discoverability"

### 7. Verbatim quotes
Include one verbatim per persona. These give the flavor of the session.

## Synthetic Label

Every section of the output — the report header, every finding, every recommendation — carries the label `[SYNTHETIC]`. Include this notice at the top of the report:

> **Synthetic research notice:** This review was conducted by AI agents instantiated as persona archetypes. Findings are hypotheses, not validated user research. Use them to prioritize what to test with real users, not as a substitute for testing.

## Output

Write the synthesis report to `{base_path}/{project-name}-ux-review-{story-id}-{yyyymmdd}.md` with standard front matter.

Append to `.sweetclaude/state/assumption-register.md`: each priority recommendation as an assumption tagged `synthetic-pending-validation`.

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — design-ux-review (n/a)

**Status:** completed | partial
**Review target:** {flow or wireframe, story ID}
**Personas:** {N} reviewed, {N} complete
**Task completion rate:** {N}/{total}
**Deal-breakers:** {count}
**Recommendations:** {count}
**Report:** {filename}
```

Append to `.sweetclaude/state/checkpoint.md` (create if absent):

```markdown
## {ISO datetime} — design-ux-review

Done: UX review for {story ID} — {N}/{total} personas, {count} recommendations
Next: {if deal-breakers: "Address deal-breakers in wireframes, then re-run review" | else: "Incorporate findings and advance to PLAN"}
Open: {deal-breaker summary if any, or "none"}
```

## After the Session

Present the synthesis, then ask:
> "Want to adjust the wireframe or flow based on any of these findings, then run the panel again?"

If yes, the user updates the flow or wireframe using the appropriate skill, then re-invokes `/sweetclaude:design-ux-review`. Re-runs are tracked as separate sessions in the log.
