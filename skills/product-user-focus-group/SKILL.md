---
spdx-license: AGPL-3.0-or-later
name: product-user-focus-group
user-invocable: true
description: "Synthetic panel research using persona archetypes as parallel subagent respondents. Three modes: ask (open qualitative), concept-test (comparison), message-test (variant testing). All outputs mandatorily labeled synthetic."
category: product
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Product User Focus Group

Synthetic panel research — N parallel isolated subagents, each instantiating one synthetic persona archetype, returning structured findings that are then synthesized by the orchestrator.

**All outputs are mandatorily labeled synthetic.** Synthetic findings are hypotheses to validate with real users, not validation themselves. This label cannot be suppressed.

---

## Mode Routing

Read `$ARGUMENTS`. Route by the first word:

| Argument | Mode |
|---|---|
| `ask [question]` | Open qualitative — what would users say? |
| `concept-test [comparison]` | Ranked choice — which concept do users prefer? |
| `message-test [variants]` | Variant testing — which message resonates? |
| *(none)* | Present menu (see below) |

If `$ARGUMENTS` is empty: present the mode menu via AskUserQuestion before proceeding.

---

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:setup` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.product.base_path` and `categories.strategy.base_path`.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`.

---

## Entry — Hard Gate ⚠️

**This gate cannot be soft-bypassed without explicit risk acceptance.**

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Read `.sweetclaude/state/personas.yaml`. If it does not exist or is empty:

> "⚠ Hard gate: no persona data found.
>
> `/sweetclaude:product-user-focus-group` requires validated personas before running synthetic research. Without grounded archetypes, the synthetic panel is projecting inventor assumptions, not modeling real users.
>
> Run `/sweetclaude:user-personas` to define your personas, then return here."

Stop. Do not proceed.

If `personas.yaml` exists, validate that at least one persona has **all four** required fields:
1. A real-world scenario (a specific triggering situation — not a category)
2. Observable success criteria (binary, measurable — includes a number, step count, time limit, or concrete outcome)
3. Deal-breakers populated (at least one)
4. Anti-profile defined (at least a brief statement of who is not a target user)

If no persona passes all four checks:

> "⚠ Hard gate: personas exist but are not validated.
>
> Synthetic research grounded in thin archetypes produces thin findings. The following required fields are missing from all personas: {list the specific missing fields}.
>
> Run `/sweetclaude:user-personas` to complete the persona definitions, then return here.
>
> If you want to proceed anyway, you must explicitly state: **'I understand synthetic findings are not validated user research'** — and this override will be logged to the decision log."

Wait for user response. If they provide the override phrase exactly, log it (see Override Logging below) and proceed with a note that outputs will be additionally flagged as lower-confidence. If they do not provide the override phrase, stop.

**Override Logging:**

Append to `.sweetclaude/state/decision-log.md`:

```markdown
## {ISO datetime} — product-user-focus-group hard gate override

**Decision:** Proceeded with synthetic research without fully validated personas.
**Risk acceptance:** User stated: "I understand synthetic findings are not validated user research"
**Missing validation:** {list the specific fields that were incomplete}
**Study ID:** {study-id generated below}
**Warning:** All outputs from this study carry lower-confidence synthetic labeling.
```

---

## Generate Study ID

```bash
study_id="study-$(date +%Y%m%d-%H%M%S)"
echo "Study ID: $study_id"
mkdir -p .sweetclaude/research/$study_id
```

---

## Mode Menu (if no $ARGUMENTS)

If the user invoked the skill without arguments, ask:

| Option label | Description |
|---|---|
| **ask** | Open question — what would personas say about a topic, problem, or concept? |
| **concept-test** | Show personas two or more concepts and ask which they prefer and why |
| **message-test** | Show personas message variants and ask which resonates and why |
| **Something else** | Different direction |

Then ask for the content (question / concepts / variants) before proceeding.

---

## Archetype Selection

Ask:
> "Which personas should participate in this study? Default is all archetypes from `personas.yaml`."

List the persona names/IDs from `personas.yaml`. Let the user select a subset or confirm "all."

Ask:
> "How many synthetic instances per archetype? Default is 3. Higher counts increase robustness but also cost."

Accept the user's answer. Default to 3 if they say "default" or provide no input.

Store: `archetypes_selected`, `instances_per_archetype`.

---

## Mode: ask

**Input:** A question the user wants answered by synthetic personas.

**Example questions:**
- "When you're evaluating a new tool like this, what makes you trust it?"
- "Walk me through the last time you had to solve [problem]."

**Subagent dispatch:**

For each archetype × instance (N = archetypes × instances_per_archetype):

Spawn a parallel subagent via the Agent tool with this briefing:

```
You are a synthetic research respondent instantiating this persona archetype:

---
{paste the full persona record from personas.yaml, including name, role, trigger, deal_breakers, tasks, success_criteria}
---

Instance parameters (seeded variation within archetype ranges):
- Instance ID: {archetype_id}-{instance_number}
- {Any age, tenure, geography, or context variation appropriate to this archetype — stay within the archetype's defined ranges}

You are participating in qualitative research. Answer the following question honestly as this person would, based on their role, context, trigger, and deal-breakers. Do not break character. Do not hedge with "as an AI."

Research question: {question}

Return ONLY valid JSON matching this schema:
{paste schema from schemas/ask.json}
```

**Retry budget:** If a subagent returns invalid JSON, re-prompt up to 2 times. After 2 failures, log the instance as `defective` and continue without it. If more than 30% of instances are defective, halt and warn the user.

---

## Mode: concept-test

**Input:** Two or more concepts to compare. Each concept is a name + brief description (1–3 sentences).

**Example:** "Concept A: automated onboarding in 3 steps. Concept B: self-guided onboarding with tutorial library."

**Ask the user:** How many concepts? (2–4 supported.) Collect name + description for each.

**Subagent dispatch:** Same parallel pattern as `ask` mode, with this task instead:

```
You are being shown {N} product concepts. As this persona, evaluate each:
1. Which concept do you prefer, and why?
2. How likely are you to pay for or adopt this? (1–5 scale: 1=very unlikely, 5=very likely)
3. What one thing would make your preferred concept better?
4. What one thing would make you walk away from this category entirely?

Concepts:
{list concepts with names and descriptions}

Return ONLY valid JSON matching this schema:
{paste schema from schemas/concept-test.json}
```

---

## Mode: message-test

**Input:** Two to four message variants. Each variant is a short message (headline, tagline, or value proposition — under 30 words).

**Ask the user:** Collect 2–4 message variants.

**Subagent dispatch:** Same parallel pattern, with this task:

```
You are being shown {N} message variants for a product. As this persona:
1. Which message resonates most with you, and why?
2. Which message would make you most likely to click or learn more?
3. Does any message feel off, misleading, or wrong for someone like you? If so, why?

Messages:
{list variants labeled A, B, C, D}

Return ONLY valid JSON matching this schema:
{paste schema from schemas/message-test.json}
```

---

## Per-Instance Validation

Before synthesis, validate each response:

- Parse JSON. If unparseable: retry up to 2 times, then mark `defective`.
- Check required fields are present and non-empty.
- Flag but do not discard responses where `purchase_intent` or `likelihood` are outside 1–5 range — record the raw value and note the anomaly.

Track: `total_instances`, `valid_instances`, `defective_instances`.

If defect rate > 30%: halt and present:
> "⚠ More than 30% of synthetic instances returned invalid responses ({defective_instances} of {total_instances}). This may indicate a problem with the archetype definitions or the research question. Proceed with partial results, or abort and revise the question?"

---

## Synthesis

After all valid responses are collected:

**For `ask` mode:**
1. Extract all `themes` arrays — flatten to a single theme list
2. Count theme frequency across instances — surface themes that appear in >30% of instances
3. Select 2–3 representative verbatim quotes per dominant theme
4. Note any themes that appear in one archetype but not others — these are archetype-specific signals worth calling out
5. Headline finding: the single most consistent signal across all archetypes

**For `concept-test` mode:**
1. Tally preferred concepts across all instances
2. Calculate mean purchase_intent per concept per archetype
3. Identify whether preference correlates with archetype (e.g., Archetype A prefers Concept 1, Archetype B prefers Concept 2) — this is a segmentation signal
4. Aggregate improvement suggestions by concept
5. Headline finding: which concept wins overall and whether preference is consistent or segmented

**For `message-test` mode:**
1. Tally resonance and likelihood-to-click by variant
2. Identify whether any archetype systematically misreads a message (rejection signals)
3. Aggregate verbatim rejection reasons for flagged messages
4. Headline finding: winning variant and any messages to avoid

---

## Output

**Write to corpus:**

Write `corpus/raw/inbox/research-{study-id}.md`:

```markdown
---
synthetic: true
study_id: {study-id}
mode: {ask | concept-test | message-test}
archetypes: [{list}]
instances_per_archetype: {N}
total_instances: {N}
valid_instances: {N}
defective_instances: {N}
date: {ISO date}
warning: "SYNTHETIC FINDINGS — these are hypotheses to validate with real users, not validated user research"
---

# Synthetic Focus Group — {mode} — {date}

**⚠ SYNTHETIC FINDINGS.** All responses were generated by AI instantiating persona archetypes. These are hypotheses, not validated user research. Validate with real fieldwork before treating as ground truth.

## Research Question / Concepts / Variants

{paste the question or concept/variant descriptions}

## Headline Finding

{headline finding from synthesis}

## Findings by Archetype

{findings section — one sub-section per archetype}

## Dominant Themes / Signals

{themes or preference signals from synthesis}

## Representative Verbatims

{2–3 quotes per dominant theme or concept — labeled with archetype and instance ID}

## Anomalies and Defective Instances

{list any defective instances and any anomalous responses}

## Methodology Notes

- Mode: {mode}
- Instances per archetype: {N}
- Retry budget: 2 retries per instance
- Override active: {yes/no — if yes, paste the override decision-log entry}
```

**Write study record:**

Write `.sweetclaude/research/{study-id}/instances.json` — the instance parameter objects used (not the responses).

Write `.sweetclaude/research/{study-id}/raw.json` — the per-instance JSON responses.

**Update assumption register:**

Append to `.sweetclaude/state/assumption-register.md` for each headline finding:

```markdown
## ASSUMPTION [{study-id}-{n}] — synthetic-pending-validation

**Finding:** {headline finding or dominant theme}
**Source:** Synthetic focus group study {study-id} — {mode} mode
**Archetypes:** {list}
**Status:** synthetic-pending-validation — requires real user research to confirm or invalidate
**Date:** {ISO date}
```

**Append to log:**

```markdown
## {ISO datetime} — product-user-focus-group ({mode})

**Status:** completed | partial (defective instances) | aborted
**Study ID:** {study-id}
**Mode:** {mode}
**Archetypes:** {list}
**Instances:** {valid}/{total} valid
**Headline:** {headline finding}
**Produced:** corpus/raw/inbox/research-{study-id}.md
**Open questions:** {bullets — what real fieldwork should validate}
```

---

## Rules

- **Never write synthetic instances to `state/personas.yaml`.** Synthetic instances are ephemeral. Personas are real user archetypes. These must never be conflated.
- **The `synthetic` label cannot be suppressed.** Every artifact — report, assumption, decision-log entry — carries it. No override removes the label.
- **Hard gate cannot be waived silently.** Override requires the exact phrase and is always logged.
- **Defective instances are logged, not silently dropped.** If a subagent returns garbage, record it.
- **Archetype-specific findings must be called out.** A signal that appears in one archetype but not others is information, not noise.
