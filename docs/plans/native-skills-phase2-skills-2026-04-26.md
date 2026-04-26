# Native Skills Redesign — Phase 2: Native Skill Implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write 12 native SweetClaude skill files — replacing all BMAD wrappers with fully self-contained skills that own their own workflow.

**Architecture:** Each task writes one `SKILL.md` file. Tasks 1–12 are independent and safe to execute in parallel. Task 13 (sync) and Task 14 (validation) must run after all skill tasks complete. The authoritative specification for each skill is in `docs/native-skills-redesign-draft-v1.0-20260426.md` — read the relevant section before writing each skill.

**Prerequisite:** Phase 1 plan (`native-skills-phase1-cleanup-2026-04-26.md`) must be complete.

**Tech Stack:** Markdown (SKILL.md authoring), YAML (frontmatter validation), bash (file ops, rsync), Python 3 (YAML parse check), git.

**Repo:** `/Users/carsonsweet/dev/sweetclaude`
**Installed:** `/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0`
**Design spec:** `/Users/carsonsweet/dev/sweetclaude/docs/native-skills-redesign-draft-v1.0-20260426.md`

---

## Pre-flight

```bash
# Phase 1 complete — these old skills must not exist
ls /Users/carsonsweet/dev/sweetclaude/skills/ | grep -E "^(strategy-concept|strategy-pain-thesis|product-product-brief|product-user-story)$"
# Expected: no output

# Design spec exists
ls /Users/carsonsweet/dev/sweetclaude/docs/native-skills-redesign-draft-v1.0-20260426.md
# Expected: the file

# Python3 available
python3 --version
```

---

## Shared conventions for all skill files

Every SKILL.md in this plan follows this structure:

```markdown
---
name: sweetclaude:{skill-name}
description: {one-line description, under 120 chars}
---

# {Skill Title}

## Entry

{How the skill starts — what state it reads, what it creates if missing}

## {Main workflow sections...}

## Exit

{What state file it writes, what log entry it appends}
```

**Entry behavior (standard, adapt per skill):**
```markdown
## Entry

Check for `.sweetclaude/` directory. If not found:
> "This project isn't configured for SweetClaude yet. Run `/sweetclaude:init` to set it up, then try again."
Stop.

Check for `.sweetclaude/log.md`. If not found, create it:
```markdown
# SweetClaude Effort Log
```

Read the following state files if they exist (used to avoid re-collecting known information):
- {list relevant state files for this skill}
```

**Exit behavior (standard, adapt per skill):**
```markdown
## Exit

Write `{state-file}.yaml` to `.sweetclaude/state/`. Schema:
```yaml
{complete schema}
```

Append to `.sweetclaude/log.md`:
```markdown
## {ISO datetime} — {skill-name} ({depth: L1|L2|L3|n/a})

**Status:** completed | skipped | degraded
**Degraded because:** {if degraded — omit otherwise}
**Produced:** {filename or none}
**Skipped/shortcuts:** {what, or none}
**Key decisions:** {bullets or none}
**Open questions:** {bullets or none}
**Open loops/todos:** {bullets or none}
```
```

**Cross-cutting behaviors to include in every skill:**

- Frustration detection: "If the user seems frustrated at any point, offer to proceed with what's already gathered or circle back to this section later. Accept immediately if they want to skip."
- Graceful degradation: "If [prior state file] is missing, note this to the user, recommend completing [prior skill] first, accept if they decline, and proceed with what's available. Write `degraded` status to the effort log."
- Progressive analysis: "Do not re-ask information already captured in prior depth levels or state files."
- Depth offer: "After completing [L1/current level], offer to continue to [L2/next level]. Briefly explain what the next level adds. Accept the user's choice without pressure."

---

## Task 1: product-discovery

**Files:**
- Modify: `skills/product-discovery/SKILL.md` (overwrite with new content)

Read design spec **Section 5, Skill 1** before writing.

- [ ] **Step 1: Write SKILL.md**

Write `/Users/carsonsweet/dev/sweetclaude/skills/product-discovery/SKILL.md`:

```markdown
---
name: sweetclaude:product-discovery
description: Establish what is being built, for whom, and why — at the depth appropriate for the project type. Three depth levels from quick intent to full pain thesis.
---

# Product Discovery

Establish what is being built, for whom, and why. This skill conducts a structured interview at the depth you choose — from a quick orientation to a full pain thesis.

## Entry

Check for `.sweetclaude/` directory. If not found:
> "This project isn't configured for SweetClaude yet. Run `/sweetclaude:init` to set it up, then try again."
Stop.

Check for `.sweetclaude/log.md`. If not found, create it with the header `# SweetClaude Effort Log`.

## Depth Levels

Before starting, ask:
> "How deep do you want to go with discovery?
> - **L1 — Intent and boundaries:** Quick orientation — what you're building, for whom, and what's explicitly out of scope. Takes 2–3 questions.
> - **L2 — Problem and success:** Adds a concrete problem definition, audience refinement, success criteria, and a challenge of your framing. Good for significant internal tools.
> - **L3 — Full pain thesis:** Adds pain measurement, market context, accountability analysis, escalation chains, and a validation rubric. Appropriate for commercial products.
> Which level, or should I suggest based on what you tell me about the project?"

If the user asks for a suggestion: ask what they're building and their intent (L1 question), then recommend a level based on their answer. Commercial → recommend L3. Internal tool → recommend L2. Utility or hobby → recommend L1.

## L1 — Intent and Boundaries

Ask one question at a time. Do not combine questions.

1. "Describe what you're building in your own words."

2. If the target user is not apparent from their answer: "Who is this for?"

3. "What is this — commercial product, internal tool, simple utility, hobby project, or something else?"

4. "What is this explicitly NOT? Give me at least one thing that's out of scope."

After these questions, produce:

```
**What:** {one-sentence description}
**For:** {target user}
**Intent:** {commercial | internal | utility | hobby | other}
**Not in scope:** {at least one item}
```

Present this and ask if it's accurate. Adjust until confirmed.

If the user chose L1, go to [Exit]. Otherwise continue to L2.

## L2 — Problem and Success

Do not re-ask anything captured in L1.

5. "What specific problem does this solve? Give me a concrete scenario — a specific person in a specific situation, not an abstract pain."

6. "For the person in that scenario: what does success look like? What are they able to do or stop doing?"

7. **Challenge the framing.** Propose at least one of:
   - An alternative framing of the problem ("Another way to see this: [reframe]. Is the real problem upstream/downstream of what you described?")
   - A gap ("You said X, but what about Y — have you thought through that?")
   - A questionable assumption ("This assumes Z is true — is it?")
   Do not accept the first framing without scrutiny.

After discussion, produce an updated concept statement incorporating L2 additions. Present and confirm.

If the user chose L2, go to [Exit]. Otherwise continue to L3.

## L3 — Full Pain Thesis

Do not re-ask anything captured in L1 or L2. Ask one question at a time.

8. "What do people use today to deal with this problem?" (existing approaches/alternatives)

9. "Why does that fail — what specifically breaks or falls short?"

10. "Is this problem a must-have to solve (like medicine — budget already exists for this category) or a nice-to-have (like vitamins — discretionary spending)?"

11. "Who gets fired, fined, or blamed when this problem isn't solved?" (accountability owner)

12. "Why can't they fix it themselves?" (control gap)

13. "Walk me through what happens when this problem hits — from the first sign to the worst case." (escalation chain)

14. "Can this problem be measured in time lost or money spent? If so, roughly how much per instance?"

15. "Is there any market research, analyst coverage, or industry data on this problem — market size, problem descriptions, or published statistics you're aware of?"

16. Produce a **Validation Rubric** assessing the current state of evidence:

| Pain element | Status | Evidence |
|---|---|---|
| Pain exists | 🔴 Assumption / 🟡 Qualitative / 🟢 Quantified | {what you have} |
| Pain is owned | 🔴 / 🟡 / 🟢 | {what you have} |
| Budget exists | 🔴 / 🟡 / 🟢 | {what you have} |
| Existing solutions fail | 🔴 / 🟡 / 🟢 | {what you have} |

🔴 = intuition or assumption only. 🟡 = qualitative evidence (conversations, observed behavior). 🟢 = quantified (specific costs, specific buyer quotes, data).

Present the rubric and explain: "The goal before committing to a wedge is to move every critical element from Red to Yellow, and the top three from Yellow to Green."

17. "What is the narrowest, most painful slice of this problem that a buyer or user would want solved on its own — before seeing anything else?" (wedge)

Apply the **checkbook test**: "If you described only this capability in a meeting, would they write a check or sign up?" Discuss until the wedge is clear.

Produce the complete pain thesis. Present and confirm.

## Frustration and Skip Handling

If the user seems frustrated at any point, offer:
> "We can proceed with what we have so far, or come back to this section. Which would you prefer?"

Accept immediately. Log what was skipped.

## Exit

Write `.sweetclaude/state/discovery.yaml`:

```yaml
project_type: commercial | internal | utility | hobby | other
intent: {one-line}
problem_summary: {one-line, or "" if L1 only}
target_user_summary: {one-line}
depth_run: L1 | L2 | L3
not_scope:
  - {item}
pain_thesis_present: true | false
validation_rubric_run: true | false
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-discovery ({depth})

**Status:** completed
**Depth:** {L1 | L2 | L3}
**Produced:** none (state only)
**Skipped/shortcuts:** {what was skipped, or none}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```
```

- [ ] **Step 2: Validate frontmatter**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/product-discovery/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
assert data['name'] == 'sweetclaude:product-discovery', f'Wrong name: {data[\"name\"]}'
print('OK:', data['name'])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/product-discovery/SKILL.md
git commit -m "feat: implement native product-discovery skill (L1/L2/L3 depth levels, pain thesis)"
```

---

## Task 2: product-research

**Files:**
- Modify: `skills/product-research/SKILL.md` (overwrite with new content)

Read design spec **Section 5, Skill 2** before writing.

- [ ] **Step 1: Write SKILL.md**

Write `/Users/carsonsweet/dev/sweetclaude/skills/product-research/SKILL.md`:

```markdown
---
name: sweetclaude:product-research
description: Survey the solution field — what exists commercially and open source — so the user understands what they're entering before building. Feeds the competitive seed list.
---

# Product Research

Survey the solution landscape for the problem you're solving. This skill produces a state-of-the-art assessment and an initial list of competing solutions — commercial and open source.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/discovery.yaml` if it exists. Use `project_type` and `problem_summary` to inform the research and depth suggestion. If missing, note this and proceed without it.

## Offer to Run

Before starting, explain what this skill does and ask if the user wants it:

> "Product research surveys what already exists in your problem space — commercial products, open-source projects, and the general state of the art. It answers two questions: 'Should I just use something that exists?' and 'Is what I'm building novel, entering a crowded space, or going somewhere with no market?'
>
> Based on your project type ({project_type from discovery, or 'the information you've shared'}), I'd suggest {L1 for utilities/hobby | L2 for internal tools | L2 or L3 for commercial}. Want to run it?"

If the user declines, write a skipped entry to the log and stop.

## Depth Levels

**L1 — Landscape survey:**
- What product categories exist that address this problem?
- Who are the main commercial players? (name, one-line description, general positioning)
- Who are the notable open-source projects? (name, one-line description)
- What is the general community and user sentiment about existing solutions?

**L2 — Comparative assessment** (includes L1):
- Which solutions are most relevant to what the user is building?
- What do they do well and where do they fall short?
- Pricing and distribution model for the main commercial options
- Initial competitive seed list (name, type: commercial/open_source, one-line description) — this feeds `product-competition`

**L3 — SOTA depth** (includes L1 and L2):
- Deep research on the most relevant 3–5 solutions
- Industry analyst or journalist coverage
- Developer community discussions (Reddit, Hacker News, Stack Overflow)
- Emerging or experimental approaches
- Assessment of whether the space is crowded, novel, or lacks a market

## Research Process

Use web search to conduct research. Search for:
- "{problem domain} software" / "{problem domain} tools"
- "{problem domain} open source alternatives"
- "best {problem domain} solutions {current year}"
- "{top competitor names} reviews" / "{top competitor names} alternatives"
- Community discussions: site:reddit.com, news.ycombinator.com

For each solution found, record: name, type (commercial/open_source), URL, one-line description, notable strengths, notable weaknesses (from user reviews and community discussion).

## Two-Lens Output

Present findings through two lenses:

**"Should I just use something that exists?"**
Honest assessment for the self-solver case. If a good existing solution covers the need, say so clearly.

**"Is what I'm building novel, crowded, or in a space with no market?"**
Commercial viability framing. Characterize the space: emerging (few solutions, growing need), crowded (many solutions, differentiation hard), established (mature solutions, requires clear differentiation), or nascent (problem identified but no real solutions yet).

## Frustration and Skip Handling

If the user seems frustrated or wants to skip, offer to proceed with what's gathered. Log the shortcut.

## Exit

Write `.sweetclaude/state/research.yaml`:

```yaml
sota_summary: {paragraph summary}
solution_field_assessment: crowded | novel | no_market | emerging | established | unclear
depth_run: L1 | L2 | L3
competitor_seeds:
  - name: {}
    type: commercial | open_source
    url: {}
    description: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-research ({depth})

**Status:** completed | skipped | degraded
**Degraded because:** {if applicable}
**Depth:** {L1 | L2 | L3}
**Produced:** {deliverable filename or none}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```

Write deliverable document to `docs/{project-name}-research-draft-v1.0-{yyyymmdd}.md` with standard front matter.
```

- [ ] **Step 2: Validate frontmatter**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/product-research/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
assert data['name'] == 'sweetclaude:product-research'
print('OK:', data['name'])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/product-research/SKILL.md
git commit -m "feat: implement native product-research skill (SOTA survey, two-lens output, competitive seeding)"
```

---

## Task 3: product-competition

**Files:**
- Create: `skills/product-competition/` (new directory)
- Create: `skills/product-competition/SKILL.md`

Read design spec **Section 5, Skill 3** before writing.

- [ ] **Step 1: Create directory and write SKILL.md**

```bash
mkdir -p /Users/carsonsweet/dev/sweetclaude/skills/product-competition
```

Write `/Users/carsonsweet/dev/sweetclaude/skills/product-competition/SKILL.md`:

```markdown
---
name: sweetclaude:product-competition
description: Competitive analysis at three depth levels — from a quick company survey to feature-by-feature deep analysis. Consolidates strategic and feature-level competitive work.
---

# Product Competition

Competitive analysis at the depth appropriate to your needs. This skill consolidates strategic positioning analysis and feature-level comparison into one progressive workflow.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/research.yaml` if it exists — `competitor_seeds` provides the starting list. If missing, ask the user to name competitors to analyze.

## Depth Levels

Ask:
> "How deep do you want the competitive analysis?
> - **L1 — Survey:** Who competes, what they claim, and what users say. Quick orientation.
> - **L2 — Matrix:** Side-by-side comparison of selected competitors vs. your product on key dimensions, plus pricing and distribution.
> - **L3 — Feature-deep:** You pick specific features. I do deep analysis via product docs, user reviews, and journalist coverage — feature by feature.
> Which level?"

## L1 — Survey

For each competitor in the seed list (or user-provided list):
- Company name and product name
- Their stated positioning (how they describe themselves)
- Their claimed differentiators (what they say makes them different)
- General community and user sentiment (from review sites, forums, social media)

Present as a structured list. Ask: "Are there competitors missing from this list?"

## L2 — Matrix

Select the most relevant 3–6 competitors with the user. Build a comparison matrix:

| Dimension | Your product | Competitor A | Competitor B | ... |
|---|---|---|---|---|
| Target user | | | | |
| Core use case | | | | |
| Key strengths | | | | |
| Key weaknesses | | | | |
| Pricing model | | | | |
| Distribution | | | | |
| {additional dimensions} | | | | |

Ask the user what dimensions matter most to them before building the matrix.

Also capture for each competitor:
- Target market / target user segment
- Pricing model (freemium, subscription tiers, per-seat, usage-based, open core, etc.)
- Distribution strategy (self-serve, sales-led, open source, app stores, etc.)

## L3 — Feature-Deep

Ask the user which specific features they want to analyze. For each selected feature:

1. Research how each relevant competitor implements this feature:
   - Read their official product documentation
   - Find deep user reviews on G2, Capterra, Reddit, Hacker News, or equivalent
   - Look for journalist or analyst coverage
2. Produce a feature-by-feature comparison table for that feature across competitors
3. Summarize: who does it best and why, what's missing across all of them, what your product's opportunity is

Repeat for each selected feature.

## Frustration and Skip Handling

If the user wants to stop or skip remaining features, accept immediately and log what was covered.

## Exit

Write `.sweetclaude/state/competition.yaml`:

```yaml
depth_run: L1 | L2 | L3
competitors:
  - name: {}
    depth_analyzed: L1 | L2 | L3
    positioning: {}
    key_differentiators: []
    target_market: {}
    pricing_model: {}
    distribution: {}
features_analyzed:
  - feature: {}
    findings_summary: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-competition ({depth})

**Status:** completed | skipped | degraded
**Depth:** {L1 | L2 | L3}
**Produced:** {filename}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```

Write deliverable to `docs/{project-name}-competition-draft-v1.0-{yyyymmdd}.md` with standard front matter.
```

- [ ] **Step 2: Validate**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/product-competition/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
assert data['name'] == 'sweetclaude:product-competition'
print('OK:', data['name'])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/product-competition/
git commit -m "feat: add native product-competition skill (L1 survey / L2 matrix / L3 feature-deep)"
```

---

## Task 4: product-user-personas

**Files:**
- Create: `skills/product-user-personas/` (new directory)
- Create: `skills/product-user-personas/SKILL.md`

Read design spec **Section 5, Skill 4** before writing.

- [ ] **Step 1: Create directory and write SKILL.md**

```bash
mkdir -p /Users/carsonsweet/dev/sweetclaude/skills/product-user-personas
```

Write `/Users/carsonsweet/dev/sweetclaude/skills/product-user-personas/SKILL.md`:

```markdown
---
name: sweetclaude:product-user-personas
description: Define product users — who they are, what they need to do, and exactly what completing each task looks and feels like. Includes triggers, deal-breakers, and optional research-backed workflow expansion.
---

# Product User Personas

Define the users of your product or tool — who they are, what they need to accomplish, and precisely what success and failure look like for each task.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/discovery.yaml` if it exists — use `target_user_summary` as a starting point. Read `.sweetclaude/state/research.yaml` if it exists — use for optional workflow expansion.

## Persona Loop

Repeat for each persona until the user says there are no more.

### Persona Definition

Ask one question at a time:

1. "Describe this person — their role, context, and what they're responsible for."

2. "What triggers them to go looking for a solution like yours? What specific event or situation makes them search?" (Not a category — a specific moment.)

3. "What would make them walk away from your product even if it technically works? Think about: price threshold, missing integrations, required expertise or setup, trust or credibility requirements."

Record: name (or role label), role, context, trigger, deal-breakers.

### Task Loop

For each persona, repeat until the user says the persona is done:

**Task definition:**

1. "What's a task this person needs to accomplish with your product?"

2. Offer to build the workflow: "I can draft the workflow details for you to review, or you can walk me through it. Which would you prefer?"

   If Claude drafts: produce draft workflow with steps, inputs, success criteria, and failure modes. Ask for review and adjustment.
   If user provides: ask for each element in turn.

**Workflow elements:**
- Steps (numbered sequence of actions from start to completion)
- Information needed to begin (what must the user have or know before starting?)
- Success criteria: **must be observable, binary, and specific.** Include a number, step count, time limit, or concrete outcome.
  - Bad: "User manages contacts easily"
  - Good: "User creates a new contact in under 3 steps without leaving the current view"
- Common failure modes (what goes wrong and how?)

**Challenge:** After the success criteria are defined, ask: "If every criterion passed but the user was still unhappy, what would be missing?" That gap is another criterion. Add it.

**Optional research expansion:** After the task has initial shape:
> "I can research how other products handle this workflow — looking at the competitive landscape we covered, best practices, and key features that support it. I'd propose improvements with my reasoning for why they'd help users. Want me to do that?"

If yes: use research state + web search if needed. Propose only improvements with clear, stated user value. Apply YAGNI and KISS — do not add workflow steps to fill space. Present proposals with inferred user value explicitly stated.

### New Persona Task Reuse

When starting each new persona, always ask:
> "Before we define tasks for [new persona name], do any of the tasks we've already defined apply to them? We can reuse those rather than redefine them."

List the already-defined tasks by name for easy reference.

## Anti-Profile

After all personas are complete, offer:
> "Do you want to define an anti-profile — a description of who is explicitly NOT a target user? This can clarify product boundaries and prevent building for the wrong person."

If yes: "Who would misuse this, churn immediately, or demand features that would dilute the core value for your real users?"

## Frustration and Skip Handling

If the user seems frustrated at any point:
> "We can move on with what we have. Do you want to continue with the next task, the next persona, or skip to writing up what we have?"

Accept immediately. Log what was skipped.

## Exit

Write `.sweetclaude/state/personas.yaml`:

```yaml
personas:
  - id: persona-1
    name: {}
    role: {}
    trigger: {}
    deal_breakers: []
    tasks:
      - id: task-1
        description: {}
        workflow_steps: []
        inputs_needed: {}
        success_criteria: []
        failure_modes: []
        research_expanded: true | false
anti_profile: {} | null
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-user-personas (n/a)

**Status:** completed | skipped | degraded
**Produced:** {filename}
**Personas defined:** {count}
**Tasks defined:** {total across all personas}
**Skipped/shortcuts:** {what, or none}
**Open questions:** {bullets}
```

Write deliverable to `docs/{project-name}-user-personas-draft-v1.0-{yyyymmdd}.md` with standard front matter.
```

- [ ] **Step 2: Validate**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/product-user-personas/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
assert data['name'] == 'sweetclaude:product-user-personas'
print('OK:', data['name'])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/product-user-personas/
git commit -m "feat: add native product-user-personas skill (triggers, deal-breakers, task workflows, research expansion)"
```

---

## Task 5: product-brief

**Files:**
- Modify: `skills/product-brief/SKILL.md` (overwrite — dir was renamed from product-product-brief in Phase 1)

Read design spec **Section 5, Skill 6** before writing.

- [ ] **Step 1: Write SKILL.md**

Write `/Users/carsonsweet/dev/sweetclaude/skills/product-brief/SKILL.md`:

```markdown
---
name: sweetclaude:product-brief
description: Write a product brief — a strategic document describing what is being built, for whom, why it matters, and what success looks like. Scales to available input depth.
---

# Product Brief

Write a product brief from the discovery, research, competition, and persona work completed so far. Sections and depth scale to what's available.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read all available state files:
- `.sweetclaude/state/discovery.yaml`
- `.sweetclaude/state/research.yaml`
- `.sweetclaude/state/competition.yaml`
- `.sweetclaude/state/personas.yaml`
- `.sweetclaude/state/positioning.yaml`

If none exist, note graceful degradation and proceed with what the user provides directly.

## Pre-Write Flow

Work through these four steps before writing anything:

**Step 1 — Outline:** Present a bullet-point outline of sections based on available input. For example:
```
Proposed outline:
- Executive Summary
- Problem Statement
- Target Audience
- Solution Overview
- Business Objectives
- Scope (in-scope and out-of-scope)
- Success Criteria
- Risks and Assumptions
- Additional Development (sections not yet covered)
```
"Does this outline look right? Add, remove, or reorder before I write."

Wait for confirmation or adjustments.

**Step 2 — Style:** "Would you prefer a bullets-style brief (faster to read, easier to update) or a narrative-style brief (better for external audiences and investors)?"

**Step 3 — Audience:** "Who is the primary audience? Internal team, investors, potential customers, or a hybrid?"

**Step 4 — Sensitive content:** "Are there any details you'd like to omit — competitive strategy, financial projections, partner names, or anything under NDA?"

## Writing

Write the brief per the confirmed outline and style. Every paragraph is numbered `[N]` at the start (draft only).

The brief always ends with an **Additional Development** section — a bulleted list of content and sections that would typically appear in a product brief at this stage but were not covered in this pass. This tells the user what remains to be developed.

## Collaborative Revision

After presenting the draft:
> "Review it and let me know what you'd like to change. Minor changes (wording, additions, clarifications) get a minor version bump. Major changes (structure, direction, voice) get a major version bump."

On revision: write a new file per the naming convention. Update the previous file's front matter `status` to `deprecated` and rename it accordingly.

When the user approves as final: offer to remove paragraph numbers before writing the final version.

## Document Production System

File naming: `{project-name}-product-brief-{status}-v{major}.{minor}-{yyyymmdd}.md`

Front matter:
```yaml
---
title: {Project Name} Product Brief
version: {major}.{minor}
status: draft | final | deprecated
author: {user's name — ask if not known}
assisted_by: Claude Code + SweetClaude
date: {YYYY-MM-DD}
audience: {internal | investors | customers | hybrid}
nda: false | "NDA: {statement}"
changes: {what changed, or "initial draft"}
previous_file: {prior filename, or "none"}
---
```

## Exit

Write `.sweetclaude/state/brief.yaml`:

```yaml
audience: {}
nda: true | false
sections_present: []
key_decisions: []
current_version: {}
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-brief (n/a)

**Status:** completed | degraded
**Degraded because:** {if applicable}
**Produced:** {filename}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```
```

- [ ] **Step 2: Validate**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/product-brief/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
assert data['name'] == 'sweetclaude:product-brief'
print('OK:', data['name'])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/product-brief/SKILL.md
git commit -m "feat: implement native product-brief skill (pre-write flow, outline-first, revision workflow)"
```

---

## Task 6: product-prd

**Files:**
- Modify: `skills/product-prd/SKILL.md` (overwrite)

Read design spec **Section 5, Skill 7** before writing.

- [ ] **Step 1: Write SKILL.md**

Write `/Users/carsonsweet/dev/sweetclaude/skills/product-prd/SKILL.md`:

```markdown
---
name: sweetclaude:product-prd
description: Write a Product Requirements Document — functional requirements, non-functional requirements, epics, and success metrics. Scales to available input depth.
---

# Product PRD

Write a Product Requirements Document (PRD) from the discovery, research, brief, and persona work completed so far.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read available state files:
- `.sweetclaude/state/discovery.yaml`
- `.sweetclaude/state/brief.yaml`
- `.sweetclaude/state/personas.yaml`
- `.sweetclaude/state/research.yaml`

If brief state is missing, recommend running `product-brief` first. Accept if user declines. Log degraded status.

## Pre-Write Flow

Same four steps as product-brief:

**Step 1 — Outline:** Present proposed PRD structure. Typical modern PRD sections:
```
- Executive Summary
- Problem Statement (with concrete scenario)
- Goals and Success Metrics (measurable, binary criteria)
- Functional Requirements (numbered, testable)
- Non-Functional Requirements (performance, security, compliance, scalability)
- Epics and User Story Summary
- Out of Scope
- Assumptions and Constraints
- Open Questions
- Additional Development
```
"Adjust the outline before I write."

**Step 2 — Style:** Bullets or narrative?

**Step 3 — Audience:** Internal, investors, customers, or hybrid?

**Step 4 — Sensitive content:** Anything to omit?

## Writing

Write the PRD per the confirmed outline. Every paragraph numbered `[N]` (draft only).

**Functional requirements** must be numbered and testable. Format:
```
FR-001: {The system shall...}
FR-002: {The system shall...}
```

**Success metrics** must be observable and binary (true/false after ship). Bad: "Users are happy." Good: "User completes primary workflow in under 3 steps."

Always end with **Additional Development** — sections and requirements typically present in a PRD at this stage that were not covered.

## Collaborative Revision

Same revision workflow as product-brief — minor changes get minor bump, major changes get major bump. Previous file deprecated on revision.

## Document Production System

File naming: `{project-name}-prd-{status}-v{major}.{minor}-{yyyymmdd}.md`

Front matter: same schema as product-brief.

## Exit

Write `.sweetclaude/state/prd.yaml`:

```yaml
epics: []
functional_requirements_count: 0
nfrs: []
current_version: {}
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-prd (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```
```

- [ ] **Step 2: Validate**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/product-prd/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
assert data['name'] == 'sweetclaude:product-prd'
print('OK:', data['name'])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/product-prd/SKILL.md
git commit -m "feat: implement native product-prd skill (numbered FRs, binary success metrics, revision workflow)"
```

---

## Task 7: product-user-stories

**Files:**
- Modify: `skills/product-user-stories/SKILL.md` (overwrite — dir renamed from product-user-story in Phase 1)

Read design spec **Section 5, Skill 8** before writing.

- [ ] **Step 1: Write SKILL.md**

Write `/Users/carsonsweet/dev/sweetclaude/skills/product-user-stories/SKILL.md`:

```markdown
---
name: sweetclaude:product-user-stories
description: Write user stories for a defined scope — Gherkin or generic format, scoped to all personas, SLC, or MVP. Uses best-practice naming and numbering.
---

# Product User Stories

Write user stories for your product, in the format and scope that best fits your needs.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/personas.yaml` — required for task definitions. If missing:
> "User stories require persona and task definitions. I recommend running `product-user-personas` first. Want to do that now, or continue without it?"
Accept if user declines. Log degraded status.

Read `.sweetclaude/state/prd.yaml` and `.sweetclaude/state/brief.yaml` if available.

## Step 1 — Format

"What format do you want for the user stories?

- **Gherkin** (Given/When/Then) — structured, precise, better for design and development handoff, and for test-driven development
- **Generic** (As a / I want / So that) — readable, flexible, better for product management, user-guide writing, and marketing handoff
- **Both** — Gherkin for dev handoff, generic for stakeholders
- **Something else** — tell me what you need"

## Step 2 — Scope

"What scope do you want to cover?

- **Everything** — all tasks for all personas
- **SLC** (Simple-Lovable-Complete) — stories for the narrowest complete promise to one key user. I can explain this if helpful.
- **MVP** (Minimum Viable Product) — you tell me which persona-tasks are in MVP vs. later roadmap"

If the user asks what SLC means:
> "SLC is an alternative to MVP that focuses on making a promise to one specific user and completely delivering on it — rather than delivering a partial version of many things. Simple: the smallest scope. Lovable: it has to be good at what it does. Complete: it fully delivers the promised value. The result tends to ship faster and earn more trust than a classic MVP."

**SLC path:**
1. "Who is the most important user — the one person whose problem you absolutely must solve in this release?"
2. "What is the promise to them — the one thing they'll be able to do when this ships that they can't do today?" Coach toward specificity: "The promise should be concrete enough that you could announce it and someone would know exactly what they're getting."
3. Based on personas.yaml tasks, suggest which tasks need to be implemented to fulfill the promise.
4. Get confirmation or adjustment.

**MVP path:**
1. Present all persona-tasks from personas.yaml.
2. "Which of these must be in MVP? Mark the ones that are later roadmap."
3. Get confirmation.

**All path:** Include every task from every persona.

## Step 3 — Write

Write stories for the confirmed scope.

**Naming and numbering:** Use best-practice conventions:
- Stories grouped by persona, then by functional area within persona
- Story IDs: `US-{persona-abbr}-{NNN}` (e.g., `US-ADM-001`)
- Epic IDs if using epics: `EP-{NNN}`
- Each story title: short verb phrase ("Create contact", "Export report")

**Gherkin format:**
```gherkin
Story US-ADM-001: Create a new contact

As an Admin
I want to create a new contact record
So that I can track interactions with that person

Scenario: Successful contact creation
  Given I am on the Contacts page
  When I click "New Contact" and fill in the required fields
  Then a new contact record is saved and visible in my contact list

Scenario: Missing required field
  Given I am on the New Contact form
  When I submit without filling in the Name field
  Then I see an error message "Name is required" and the form is not submitted
```

**Generic format:**
```
Story US-ADM-001: Create a new contact
As an Admin, I want to create a new contact record so that I can track interactions with that person.
Acceptance criteria:
- Contact is created when all required fields are filled and submitted
- Error is shown when required fields are missing
- New contact appears in the contact list immediately after creation
```

Present all stories when complete. Offer to adjust scope, format, or individual stories.

## Document Production System

File naming: `{project-name}-user-stories-{status}-v{major}.{minor}-{yyyymmdd}.md`

Front matter: standard schema. Note in `audience` field who these are for.

## Collaborative Revision

Same revision workflow — minor bump for edits, major bump for scope or format changes. Previous file deprecated.

## Exit

Write `.sweetclaude/state/stories.yaml`:

```yaml
format: gherkin | generic | both
scope: all | slc | mvp
slc_promise: {} | null
stories:
  - id: {}
    title: {}
    persona_id: {}
    epic_id: {} | null
    format: gherkin | generic
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-user-stories (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Format:** {gherkin | generic | both}
**Scope:** {all | slc | mvp}
**Story count:** {N}
**Open questions:** {bullets}
```
```

- [ ] **Step 2: Validate**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/product-user-stories/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
assert data['name'] == 'sweetclaude:product-user-stories'
print('OK:', data['name'])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/product-user-stories/SKILL.md
git commit -m "feat: implement native product-user-stories skill (Gherkin/generic, SLC/MVP/all scope)"
```

---

## Task 8: design-user-flows

**Files:**
- Modify: `skills/design-user-flows/SKILL.md` (overwrite — dir renamed from product-user-workflows in Phase 1)

Read design spec **Section 5, Skill 9** before writing.

- [ ] **Step 1: Write SKILL.md**

Write `/Users/carsonsweet/dev/sweetclaude/skills/design-user-flows/SKILL.md`:

```markdown
---
name: sweetclaude:design-user-flows
description: Convert user stories into UX/UI flows — step-by-step paths through the interface. Bridges product definition and UX design.
---

# Design User Flows

Convert user stories into interface flows — the step-by-step paths a user takes through the UI to complete each story. This bridges product definition and UX design.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/stories.yaml` — required for story list. If missing:
> "User flows require user stories. I recommend running `product-user-stories` first. Want to do that now, or continue without it?"

Read `.sweetclaude/state/personas.yaml` if available (for user context).

## Process

For each user story (or selected subset if the user wants to focus):

1. Identify the entry point — where in the interface does the user begin this flow?

2. Map the steps — each step is one user action and the system response:
   - Step N: [User action] → [System response / state change]

3. Identify decision points — where does the flow branch? (e.g., validation errors, optional steps, conditional paths)

4. Define the success state — what does the interface show when the story is successfully completed?

5. Define key error states — what does the interface show when something goes wrong?

Present each flow as a numbered step sequence. Offer to add a simple ASCII flow diagram if helpful.

**Example flow:**

```
Story US-ADM-001: Create a new contact

Entry point: Contacts list page

Flow:
  1. User clicks "New Contact" button → Modal or page opens with empty contact form
  2. User fills in Name (required), Email (optional), Phone (optional) → Fields validate inline
  3. User clicks "Save" → System validates all required fields
     → If Name missing: inline error "Name is required", form stays open
     → If valid: contact saved, modal closes, new contact appears at top of list
  4. User sees success toast: "Contact created"

Success state: Contact list visible with new entry at top, toast notification displayed
Error state: Form stays open, required field highlighted with error message
```

Ask after each flow: "Does this capture it correctly? Anything to adjust?"

## Scope Selection

If there are many stories, offer to scope: "Do you want flows for all stories, just the SLC/MVP scope, or specific ones?"

## Exit

Write `.sweetclaude/state/ux-flows.yaml`:

```yaml
flows:
  - story_id: {}
    entry_point: {}
    steps: []
    success_state: {}
    error_states: []
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — design-user-flows (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Flows defined:** {count}
**Open questions:** {bullets}
```

Write deliverable to `docs/{project-name}-user-flows-draft-v1.0-{yyyymmdd}.md` with standard front matter.
```

- [ ] **Step 2: Validate**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/design-user-flows/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
assert data['name'] == 'sweetclaude:design-user-flows'
print('OK:', data['name'])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/design-user-flows/SKILL.md
git commit -m "feat: implement native design-user-flows skill (story-to-interface flow mapping)"
```

---

## Task 9: design-architecture

**Files:**
- Modify: `skills/design-architecture/SKILL.md` (overwrite)

Read design spec **Section 5, Skill 10** before writing.

- [ ] **Step 1: Write SKILL.md**

Write `/Users/carsonsweet/dev/sweetclaude/skills/design-architecture/SKILL.md`:

```markdown
---
name: sweetclaude:design-architecture
description: Define system architecture — components, boundaries, communication patterns, data flow, and compliance requirements. Produces ADRs and an architecture document.
---

# Design Architecture

Define the architecture for your system. This skill conducts a structured interview, produces Architectural Decision Records (ADRs) for each significant decision, and generates an architecture document ready for development.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read available state:
- `.sweetclaude/state/brief.yaml`
- `.sweetclaude/state/prd.yaml`
- `.sweetclaude/state/personas.yaml`
- `.sweetclaude/state/stories.yaml`

Note any missing state files — the interview is the primary input, but prior artifacts inform decisions.

## Step 1 — Architecture Interview

Ask one question at a time. Always offer a recommendation before asking the user to decide.

**Platform decisions:**
1. "What programming language(s) will this be built in? I can recommend based on your team, use case, and ecosystem if helpful."
2. "What type of application is this primarily — web app, CLI tool, CLI utility, desktop app, mobile app, or something else?"
3. "How will this be deployed — SaaS (cloud-hosted, you manage), on-premises (customer hosts), locally run (runs on user's machine), or a hybrid?"

**Architecture style:**
4. "What's your instinct on architecture style — monolith (simpler, one deployable), services (microservices or macro-services, more complex), or are you unsure?" Offer a recommendation based on team size and scale indicators from prior state. A solo founder with an early-stage product should start with a monolith unless there's a strong reason not to.

**Data:**
5. "What kind of database do you need — relational (structured data, SQL), document (flexible schema, JSON), time-series, graph, or a mix?" Recommend based on the use case.

**Compliance and security interview (mandatory, do not skip):**
6. "Does your product handle any of the following regulated data types? Answer yes or no for each:
   - PII (personally identifiable information — names, emails, addresses, IDs)
   - PHI (protected health information — anything health/medical related)
   - PCI data (payment card numbers, CVVs, cardholder data)
   - Financial data subject to regulatory oversight (SOX, SEC, etc.)
   - Any other regulated data or compliance frameworks your industry requires (GDPR, CCPA, HIPAA, SOC 2, etc.)"

**If any regulated data:** "These are legal requirements, not design preferences. I'll flag specific compliance constraints throughout the architecture and tech spec." Surface and label these as HARD REQUIREMENTS.

**Additional questions as needed** based on what the prior answers imply (auth requirements, third-party integrations, offline capability, etc.)

## Step 2 — Analyze

Review all interview answers alongside available prior artifacts. Surface any conflicts: does the architecture interview imply something inconsistent with what the PRD or stories require?

## Step 3 — Decision List

Produce a list of architectural decisions to be made. Walk through each with the user. For each decision:
- State the decision to be made
- Give a recommendation with reasoning
- Note any compliance requirements that constrain the options
- Record the decision once made

## Step 4 — ADRs

Create an ADR for each significant decision. Use the following format (standard ADR format):

```markdown
# ADR-{NNN}: {Title}

**Date:** {YYYY-MM-DD}
**Status:** Accepted | Proposed | Deprecated | Superseded

## Context

{What situation or requirement prompted this decision?}

## Decision

{What was decided?}

## Rationale

{Why this option over alternatives?}

## Consequences

{What becomes easier or harder as a result of this decision?}

## Alternatives Considered

{What other options were evaluated and why were they rejected?}
```

Save each ADR to `docs/adr/ADR-{NNN}-{kebab-title}.md`.

## Step 5 — Boundary Design

**If service-oriented architecture:**
Define service boundaries:
- Which services exist?
- What does each service own (data, business logic)?
- How do services communicate (REST, gRPC, message queue, events)?
- Where are the seams — what can change in one service without affecting others?

**If monolith:**
Define module/domain boundaries:
- What are the bounded contexts within the monolith?
- What are the internal module boundaries?
- What are the domain seams — where would you split if you needed to?
- What must not bleed across module boundaries?

## Step 6 — Architecture Document

Write the architecture document. Standard sections:
- Overview and guiding principles
- Technology decisions (language, framework, database, deployment)
- Architecture style and rationale
- Component diagram (ASCII or description)
- Data flow
- Compliance and security requirements (labeled as HARD REQUIREMENTS if applicable)
- Boundary design (services or modules)
- ADR index (links to each ADR)
- Open questions

## Document Production System

ADRs: `docs/adr/ADR-{NNN}-{title}-{yyyymmdd}.md`
Architecture doc: `{project-name}-architecture-draft-v1.0-{yyyymmdd}.md`

Both follow the standard front matter schema.

## Exit

Write `.sweetclaude/state/architecture.yaml`:

```yaml
style: monolith | services | hybrid
tech_stack:
  language: {}
  framework: {}
  database: {}
  deployment: {}
compliance_requirements: []
adr_ids: []
boundary_design_type: services | modules
current_architecture_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — design-architecture (n/a)

**Status:** completed | degraded
**Produced:** {architecture doc filename}, {ADR count} ADRs
**Compliance flags:** {list or none}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```
```

- [ ] **Step 2: Validate**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/design-architecture/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
assert data['name'] == 'sweetclaude:design-architecture'
print('OK:', data['name'])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/design-architecture/SKILL.md
git commit -m "feat: implement native design-architecture skill (ADRs, compliance interview, boundary design)"
```

---

## Task 10: design-tech-spec

**Files:**
- Modify: `skills/design-tech-spec/SKILL.md` (overwrite)

Read design spec **Section 5, Skill 11** before writing.

- [ ] **Step 1: Write SKILL.md**

Write `/Users/carsonsweet/dev/sweetclaude/skills/design-tech-spec/SKILL.md`:

```markdown
---
name: sweetclaude:design-tech-spec
description: Technical specification — every decision a developer needs before writing the first line of code. Repo, environments, CI/CD, hosting, auth, monitoring, scaling.
---

# Design Tech Spec

Define every technical decision a developer needs before committing code against user stories. This is the bridge between architecture decisions and day-one development.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/architecture.yaml` — required for architecture style and compliance requirements. If missing:
> "The tech spec builds on architectural decisions. I recommend running `design-architecture` first. Want to do that now, or continue without it?"
Accept if user declines. Log degraded. Note any compliance requirements from architecture state — treat them as hard requirements throughout.

Read `.sweetclaude/state/discovery.yaml` for project type and intent (informs cost/complexity recommendations).

## Interview and Decision Process

For each topic below: describe the decision to be made, ask what the user knows or prefers, offer a recommendation, record the decision. Always factor in:
- User's situation (solo founder, small team, larger team — ask if not known from prior state)
- Cost constraints (ask: "Are you bootstrapping or do you have runway for infrastructure costs?")
- Compliance requirements from architecture state (treat as non-negotiable)

### Repo Structure

"Will this be a monorepo (all code in one repository) or separate repos per service/component?"

Recommendation guidance:
- Monolith or small team → monorepo (simpler tooling, easier cross-cutting changes)
- Many services with separate teams → polyrepo (clear ownership, independent deploys)
- Bootstrapping → monorepo (lower tooling cost)

Also decide: branching strategy (trunk-based, gitflow, or other) and PR workflow.

### Source Control Platform

"GitHub, GitLab, Bitbucket, or self-hosted?"

Recommendation guidance: GitHub for most projects (ecosystem, Actions, Copilot integration). GitLab if self-hosting or compliance requires it.

### Local Development Environment

"How will developers run the app locally?"
- Native (install dependencies directly)
- Docker Compose (containerized local stack)
- Dev containers (VS Code devcontainer or similar)
- Nix or similar reproducible environment

Recommendation: Docker Compose for most projects with external dependencies (database, cache). Native for simple apps or CLIs.

Also: what toolchain is needed (package manager, build tools, linters)?

### Environments

"What environments do you need?"

Minimum viable: local dev + production.
Recommended: local dev + staging + production.
Full: local dev + CI + staging + production (+ feature environments if needed).

For each environment: how does it differ from production (data, scale, access), and how do you promote between them?

### CI/CD

"What CI/CD platform?" (GitHub Actions, GitLab CI, CircleCI, other)

For each environment, define the pipeline:
- **On every PR:** {lint, typecheck, unit tests, security scan, build check}
- **On merge to main:** {build, deploy to staging, integration tests}
- **Production gate:** {manual approval | automated smoke tests | canary | all three}
- **Rollback plan:** {how to roll back a bad deploy in under 5 minutes}

### Hosting Provider

"Where will this run in production?"

Ask about:
- Compute: serverless (Lambda, Cloud Run, Vercel), containers (ECS, Cloud Run, Fly.io), VMs (EC2, GCE), PaaS (Railway, Render, Heroku)
- Database hosting: managed (RDS, PlanetScale, Neon, Supabase) vs. self-managed
- Storage: S3-compatible, Cloudflare R2, or provider-native
- CDN/edge: Cloudflare, Fastly, provider CDN

Factor in cost constraints. Bootstrapping → Fly.io, Railway, or Render for compute; Neon or Supabase for database. Funded → AWS/GCP/Azure with managed services.

If compliance requirements exist: confirm that chosen provider meets those requirements (e.g., HIPAA BAA, SOC 2 certification, data residency).

### Auth

"How will you handle authentication and authorization?"

Options:
- Managed auth service (Auth0, Clerk, Supabase Auth, Cognito) — faster, more expensive at scale
- Self-hosted auth library (NextAuth, Lucia, Passport) — more control, more to maintain
- OAuth only (for developer tools) — simpler if users already have GitHub/Google accounts

Authorization: role-based (RBAC), attribute-based (ABAC), or simple permissions?

If PII/PHI is involved: auth must support audit logging and session management — flag these as requirements.

### Monitoring and Observability

"What will you monitor?"

Define:
- **Uptime monitoring:** Which endpoints? What SLA? (e.g., Uptime Robot, Better Uptime)
- **Application monitoring / APM:** Error tracking and performance (Sentry, Datadog, New Relic, or provider-native)
- **Logging:** Structured JSON logging. Log levels (error, warn, info, debug). Retention period. Destination (CloudWatch, Datadog, Logtail, self-hosted).
- **Alerts:** Who gets paged? At what threshold? (e.g., error rate > 1% for 5 minutes, p99 latency > 2s)
- **Dashboards:** What does on-call watch? (key metrics: request rate, error rate, latency, queue depth)

Bootstrapping: Sentry (free tier) + Uptime Robot + provider logs is sufficient to start.

### Scaling

"What's your expected load profile at launch and at meaningful scale?"

Define:
- Expected concurrent users at launch
- What triggers horizontal scaling (more instances) vs. vertical scaling (bigger instance)
- Known bottlenecks (database, external API rate limits, file processing, etc.)
- Any stateful components that complicate horizontal scaling (sessions, file uploads)

For bootstrapped projects: don't over-engineer. Define the scaling story so you know where the ceiling is, not to build for it now.

## Tech Spec Document

Write the tech spec with all decisions documented. Standard sections:
- Repo and source control
- Local development setup (step-by-step for a new developer)
- Environments
- CI/CD pipeline (include the pipeline config skeleton if using GitHub Actions or similar)
- Hosting architecture diagram (ASCII)
- Auth design
- Monitoring and observability setup
- Scaling strategy
- Compliance requirements (labeled HARD REQUIREMENTS if applicable)

When the tech spec is reviewed and approved to final:
> "The architecture document, ADRs, tech spec, and user stories are now complete. This set is ready for development handoff."

## Document Production System

File naming: `{project-name}-tech-spec-{status}-v{major}.{minor}-{yyyymmdd}.md`

Front matter: standard schema.

## Exit

Write `.sweetclaude/state/tech-spec.yaml`:

```yaml
repo_structure: monorepo | polyrepo
source_control: github | gitlab | bitbucket | other
environments: []
cicd_platform: {}
hosting_provider: {}
auth_approach: {}
monitoring_tools: []
scaling_notes: {}
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — design-tech-spec (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Key decisions:** {bullets}
**Compliance requirements applied:** {list or none}
**Open questions:** {bullets}
```
```

- [ ] **Step 2: Validate**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/design-tech-spec/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
assert data['name'] == 'sweetclaude:design-tech-spec'
print('OK:', data['name'])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/design-tech-spec/SKILL.md
git commit -m "feat: implement native design-tech-spec skill (repo, CI/CD, hosting, auth, monitoring, scaling)"
```

---

## Task 11: design-ux

**Files:**
- Modify: `skills/design-ux/SKILL.md` (overwrite)

Read design spec **Section 5, Skill 12** before writing.

- [ ] **Step 1: Write SKILL.md**

Write `/Users/carsonsweet/dev/sweetclaude/skills/design-ux/SKILL.md`:

```markdown
---
name: sweetclaude:design-ux
description: Define the visual and interaction design of the product — look, feel, layout, and style. Produces a UX/UI design spec for handoff to AI mockup tools or a design team.
---

# Design UX

Define the look, feel, and interaction design of your product. This skill conducts a design interview and produces a UX/UI specification suitable for handoff to mockup tools or a design team.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read available state:
- `.sweetclaude/state/brief.yaml` (audience and tone context)
- `.sweetclaude/state/personas.yaml` (user context for design empathy)
- `.sweetclaude/state/architecture.yaml` (platform constraints — web vs. native, etc.)
- `.sweetclaude/state/ux-flows.yaml` (existing user flows to design for)

## Step 1 — Inspiration (First Message Only)

The very first message to the user must be:

> "Before we start the design interview, do you have screenshots or URLs of apps or websites that inspire you — products that have a look, feel, or vibe you want to capture?
>
> Sharing existing references is by far the fastest way to establish design direction. If you have them, drop them here. If not, no problem — we'll build it up through the interview."

Accept images and URLs. If the user shares references, analyze them:
- What visual style do they share (minimal, bold, dense, playful, professional, etc.)?
- What layout patterns appear?
- What color approach (monochrome, accent color, colorful)?
- What interaction feel (static, subtle animation, rich animation)?

Summarize what you observe from the references. Confirm with the user before proceeding.

## Step 2 — Design Interview

Ask one question at a time.

1. **Vibe and feeling:** "Are there existing products or websites — beyond what you've already shared — that have the aesthetic or feeling you want?"

2. **Words:** "What words do you want people to use when describing your product? Pick 3–5." Offer examples: clean, powerful, friendly, professional, playful, minimal, dense, calm, energetic, trustworthy, innovative.

3. **Priority:** "If you had to rank these three in order of importance for your design, how would you rank them: usability (easy to learn and use), aesthetic (beautiful and distinctive), simplicity (as little as possible)?"

4. **Information density:** "When you think about screens full of information, which feels right for your product?
   - Dense: lots of data visible at once, efficient for power users
   - Balanced: clear hierarchy, moderate information per screen
   - Open: roomy, minimal, lots of whitespace, calm"

5. **Color and theme:**
   "Light mode, dark mode, or user-switchable?
   Do you have brand colors, a logo, or visual assets already? If yes, share them."

6. **Interactions:** "How should the product feel when you interact with it?
   - Simple and immediate: things happen instantly, no animation
   - Subtle: small transitions that feel polished but not distracting
   - Expressive: animations and motion that communicate state and delight"

7. **AI/Copilot features in the UI:** "Will there be any AI-assist or copilot features embedded in the interface — things like inline suggestions, a chat panel, command palette, or similar?"

8. **Layout structure:** "What general layout pattern feels right? Here are common approaches:
   - Sidebar navigation (persistent left nav, content on right — common for dashboards and SaaS apps)
   - Top navigation (horizontal nav bar, full-width content — common for marketing sites and simple apps)
   - Command/search-first (no persistent nav, everything via search or command palette — common for developer tools)
   - Single-column (content stacked vertically — common for editorial, documentation, mobile-first)
   Which feels closest, or describe what you're imagining?"

## Step 3 — Write the UX/UI Design Spec

Based on all interview responses and any shared references, write the UX/UI design specification. Sections:

- **Design principles** (3–5 principles derived from the interview — e.g., "Clarity over density", "Motion earns its place")
- **Visual style** (color palette, typography direction, iconography style, imagery style)
- **Layout system** (grid, spacing scale, breakpoints if responsive)
- **Component style** (buttons, forms, cards, navigation — describe the visual treatment)
- **Interaction design** (animation philosophy, transition types, feedback patterns)
- **Dark/light mode** (if applicable)
- **AI/copilot UI patterns** (if applicable — how AI features are presented and accessed)
- **Accessibility baseline** (contrast requirements, keyboard navigation, screen reader considerations)

## Step 4 — Handoff Guidance

After presenting the spec:
> "This spec can be handed off to AI mockup and design tools. Current tools worth trying:
> - **v0 by Vercel** (v0.dev) — excellent for React/Tailwind UI generation from descriptions
> - **Galileo AI** — UI design generation from natural language
> - **Figma with AI plugins** — traditional design tool with growing AI assist features
> - **Uizard** — wireframes and mockups from sketches or descriptions
>
> When handing off, share this spec plus any reference screenshots you provided. The more specific the spec, the better the output."

## Document Production System

File naming: `{project-name}-ux-design-{status}-v{major}.{minor}-{yyyymmdd}.md`

Front matter: standard schema.

## Exit

Write `.sweetclaude/state/ux.yaml`:

```yaml
style_keywords: []
color_palette:
  primary: {}
  secondary: {}
  background: {}
  text: {}
layout_pattern: sidebar | top-nav | command-first | single-column | other
interaction_style: simple | subtle | expressive
density: dense | balanced | open
dark_mode: true | false | user-switchable
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — design-ux (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Key decisions:** {bullets — style direction, layout, color approach}
**Open questions:** {bullets}
```
```

- [ ] **Step 2: Validate**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/design-ux/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
assert data['name'] == 'sweetclaude:design-ux'
print('OK:', data['name'])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/design-ux/SKILL.md
git commit -m "feat: implement native design-ux skill (inspiration-first, design interview, AI mockup handoff)"
```

---

## Task 12: product-positioning-statement (review and update)

**Files:**
- Review: `skills/product-positioning-statement/SKILL.md`

This skill is not a BMAD wrapper — it has native content. Review it to ensure:
1. The description references that it builds on competition, personas, and discovery (not just concept and ICP as it currently says)
2. Its entry behavior reads the new state files (`competition.yaml`, `personas.yaml`, `discovery.yaml`)
3. Its exit behavior writes `positioning.yaml` and appends to `log.md`

- [ ] **Step 1: Read the current skill**

```bash
cat /Users/carsonsweet/dev/sweetclaude/skills/product-positioning-statement/SKILL.md
```

- [ ] **Step 2: Update frontmatter description**

Change:
```
description: "Define how the product is positioned — for whom, what category, what differentiates it, and why that matters. Builds on strategy/concept and strategy/ideal-customer-profile."
```

To:
```
description: "Define how the product is positioned — for whom, what category, what differentiates it, and why that matters. Runs after discovery, research, competition, and personas are complete."
```

- [ ] **Step 3: Add entry state file reads**

Add at the top of the skill body (before the existing process steps), an Entry section that reads:
- `.sweetclaude/state/competition.yaml` (for differentiators)
- `.sweetclaude/state/personas.yaml` (for ICP)
- `.sweetclaude/state/discovery.yaml` (for pain thesis)

If any are missing, recommend completing those skills first. Accept if user declines.

- [ ] **Step 4: Add exit behavior**

Add at the end of the skill:

```markdown
## Exit

Write `.sweetclaude/state/positioning.yaml`:

```yaml
target_segment: {}
positioning_statement: {}
differentiators: []
category: {}
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-positioning-statement (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Key decisions:** {bullets}
```
```

- [ ] **Step 5: Validate**

```bash
python3 -c "
import yaml
content = open('/Users/carsonsweet/dev/sweetclaude/skills/product-positioning-statement/SKILL.md').read()
data = yaml.safe_load(content.split('---')[1])
print('name:', data.get('name', '(from directory)'))
print('description:', data['description'][:60])
print('OK')
"
```

- [ ] **Step 6: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/product-positioning-statement/SKILL.md
git commit -m "feat: update product-positioning-statement to read new state files and write positioning.yaml"
```

---

## Task 13: Sync all to installed location

Run after all 12 skill tasks are complete.

- [ ] **Step 1: Sync skills**

```bash
rsync -a --delete \
  /Users/carsonsweet/dev/sweetclaude/skills/ \
  /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/
```

- [ ] **Step 2: Verify new skills present in installed**

```bash
ls /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/ | grep -E "^(product-competition|product-user-personas|design-user-flows)$"
```

Expected: 3 lines.

- [ ] **Step 3: Verify old skills absent from installed**

```bash
ls /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/ | grep -E "^(strategy-concept|strategy-pain-thesis|product-product-brief|product-user-story|product-user-workflows|code-code-review)$"
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add -A
git commit -m "chore: sync phase 2 skills to installed plugin location" 2>/dev/null || echo "Nothing uncommitted"
```

---

## Task 14: Final validation

- [ ] **Step 1: Validate all SKILL.md frontmatter**

```bash
python3 << 'EOF'
import os, yaml, sys
errors = []
skills_dir = "/Users/carsonsweet/dev/sweetclaude/skills"
for skill in sorted(os.listdir(skills_dir)):
    path = os.path.join(skills_dir, skill, "SKILL.md")
    if not os.path.exists(path):
        continue
    content = open(path).read()
    parts = content.split("---")
    if len(parts) < 3:
        errors.append(f"{skill}: no valid frontmatter delimiters")
        continue
    try:
        data = yaml.safe_load(parts[1])
        if not data.get("description"):
            errors.append(f"{skill}: missing description field")
    except yaml.YAMLError as e:
        errors.append(f"{skill}: YAML error — {e}")
if errors:
    print("ERRORS:")
    for e in errors:
        print(" ", e)
    sys.exit(1)
else:
    print(f"OK — {len(os.listdir(skills_dir))} skills validated")
EOF
```

Expected: `OK — 55 skills validated` (53 from Phase 1 + 2 new = 55)

- [ ] **Step 2: Confirm all 12 new skills have correct name fields**

```bash
python3 << 'EOF'
import os, yaml
expected = {
    "product-discovery": "sweetclaude:product-discovery",
    "product-research": "sweetclaude:product-research",
    "product-competition": "sweetclaude:product-competition",
    "product-user-personas": "sweetclaude:product-user-personas",
    "product-brief": "sweetclaude:product-brief",
    "product-prd": "sweetclaude:product-prd",
    "product-user-stories": "sweetclaude:product-user-stories",
    "design-user-flows": "sweetclaude:design-user-flows",
    "design-architecture": "sweetclaude:design-architecture",
    "design-tech-spec": "sweetclaude:design-tech-spec",
    "design-ux": "sweetclaude:design-ux",
}
skills_dir = "/Users/carsonsweet/dev/sweetclaude/skills"
errors = []
for skill_dir, expected_name in expected.items():
    path = os.path.join(skills_dir, skill_dir, "SKILL.md")
    content = open(path).read()
    data = yaml.safe_load(content.split("---")[1])
    actual = data.get("name", f"(no name field — from directory: sweetclaude:{skill_dir})")
    if data.get("name") and data["name"] != expected_name:
        errors.append(f"{skill_dir}: expected {expected_name}, got {actual}")
    else:
        print(f"OK: {skill_dir} → {actual}")
if errors:
    print("\nERRORS:")
    for e in errors:
        print(" ", e)
EOF
```

- [ ] **Step 3: Confirm no BMAD references remain anywhere in framework**

```bash
grep -ri "bmad" \
  /Users/carsonsweet/dev/sweetclaude/skills/ \
  /Users/carsonsweet/dev/sweetclaude/rules/ \
  /Users/carsonsweet/dev/sweetclaude/config/ \
  --include="*.md" --include="*.yaml" -l
```

Expected: no output.

- [ ] **Step 4: Final commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git status --short
# If clean: all done.
# If anything uncommitted: git add -A && git commit -m "chore: final cleanup after phase 2 skill implementation"
```

Phase 2 complete. Both plans are done. SweetClaude now has 55 fully native skills with no BMAD dependencies.
