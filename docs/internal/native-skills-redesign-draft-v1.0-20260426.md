---
title: Native Skills Redesign — Replace [removed] Wrappers
version: 1.0
status: draft
author: Carson Sweet
assisted_by: Claude Code + SweetClaude
date: 2026-04-26
audience: internal
nda: false
changes: initial draft
previous_file: none
---

# Native Skills Redesign

**Purpose:** Replace 10 [removed]-wrapper skills with fully native SweetClaude skills, add one new skill, consolidate two competitive analysis skills into one, reorganize the product pipeline, and eliminate all [removed] dependencies from the framework.

---

## 1. Background

[1] Seven SweetClaude skills currently delegate their entire workflow to [removed] by calling `[removed]` and following that workflow. [removed] is not installed in the current environment and was never deeply exercised. These skills are effectively dead code that silently fails at invocation. Three additional files (`skills/master/SKILL.md`, `rules/phase-gates.md`, `rules/interaction-model.md`) contain direct [removed] references that need removal.

[2] The replacement design is native — no external framework delegation. Each skill behaves like a skilled collaborator running a structured conversation, starting from the user's context, using research to fill gaps and surface best practices. The model for how these skills should behave is the brainstorming conversation itself: one question at a time, starting from user intent, proposing rather than asking, challenging assumptions.

---

## 2. Scope

### 2a. Skills Being Replaced ([removed] wrappers → native)

| Old skill | Wraps | Replacement |
|---|---|---|
| product-product-brief | [removed] | product-brief (also renamed) |
| product-prd | [removed] | product-prd (native) |
| product-user-story | [removed] | product-user-stories (renamed + native) |
| product-research | [removed] | product-research (native) |
| design-tech-spec | [removed] | design-tech-spec (native) |
| design-ux | [removed] | design-ux (native) |
| design-architecture | [removed] | design-architecture (native) |

### 2b. Skills Being Consolidated

| Skills removed | Replaced by |
|---|---|
| product-feature-competitive + strategy-competitive-analysis | product-competition (new) |

### 2c. Skills Being Absorbed (content folded into new skills, standalone deleted)

| Skill absorbed | Absorbed into |
|---|---|
| strategy-concept | product-discovery (L1/L2) |
| strategy-pain-thesis | product-discovery (L3) |
| strategy-ideal-customer-profile | product-user-personas |
| product-user-success-criteria | product-user-personas |
| design-infra-design | design-tech-spec |
| design-services-design | design-architecture |

### 2d. Skills Being Added

- `product-user-personas` — new skill, placed before product-brief
- `product-competition` — new consolidated skill

### 2e. Skills Being Renamed/Moved

| Old name | New name | Reason |
|---|---|---|
| product-product-brief | product-brief | bucket collision (product-product) |
| product-user-story | product-user-stories | plural; more accurate |
| product-user-workflows | design-user-flows | produces design artifacts; moved to design phase |
| code-code-review | code-review | bucket collision (code-code) |

### 2f. Files Needing [removed] Reference Removal

- `skills/master/SKILL.md` — references [removed], [removed], [removed] by name
- `rules/phase-gates.md` — references "[removed] 9-item checklist"
- `rules/interaction-model.md` — references stripping [removed] time estimates

---

## 3. Implementation Approach

[3] Two phases, in order:

**Phase 1 — Shared Infrastructure.** Build the four cross-cutting systems once. All skills depend on these. Starting implementation without them risks inconsistency across 12 skills.

**Phase 2 — Skills.** All 12 pipeline skills built in parallel by agents, each consuming the Phase 1 infrastructure. Each skill is a standalone `SKILL.md`.

---

## 4. Shared Infrastructure

### 4a. Effort Log

[4] Every project maintains a single running log at `.sweetclaude/log.md`. The log is append-only — skills never overwrite entries, only add new ones. The user may also write to it directly. The log is the authoritative record of what ran, what was skipped, what was decided, and what remains open.

**Entry format:**

```markdown
## {ISO datetime} — {skill-name} ({depth: L1|L2|L3|n/a})

**Status:** completed | skipped | degraded
**Degraded because:** {what was missing, if degraded — omit if not degraded}
**Produced:** {deliverable filename, or "none"}
**Skipped/shortcuts:** {what was skipped and why, or "none"}
**Key decisions:** {bullet list, or "none"}
**Open questions:** {bullet list, or "none"}
**Open loops/todos:** {bullet list, or "none"}
```

[5] If `.sweetclaude/log.md` does not exist when a skill runs, the skill creates it fresh with a header comment. Skills do not run migration — they only create a fresh log if one is absent.

### 4b. State Files

[6] Each skill writes a YAML state file to `.sweetclaude/state/` on completion. Downstream skills read these files to avoid re-collecting information already gathered. State files contain machine-readable summaries, not full document content.

**State file schemas:**

```yaml
# discovery.yaml
project_type: commercial | internal | utility | hobby
intent: {one-line}
problem_summary: {one-line}
target_user_summary: {one-line}
depth_run: L1 | L2 | L3
not_scope: [list of explicit out-of-scope items]

# research.yaml
sota_summary: {paragraph}
solution_field_assessment: crowded | novel | no_market | unclear
competitor_seeds:
  - name: {}
    type: commercial | open_source
    description: {}

# competition.yaml
depth_run: L1 | L2 | L3
competitors:
  - name: {}
    depth_analyzed: L1 | L2 | L3
    positioning: {}
    key_differentiators: []
    target_market: {}
    pricing_model: {}

# personas.yaml
personas:
  - name: {}
    role: {}
    trigger: {}
    deal_breakers: []
    tasks:
      - description: {}
        workflow_steps: []
        inputs_needed: {}
        success_criteria: []
        failure_modes: []

# positioning.yaml
target_segment: {}
positioning_statement: {}
differentiators: []
category: {}

# brief.yaml
audience: internal | investors | customers | hybrid
nda: true | false
sections_present: []
key_decisions: []

# prd.yaml
epics: []
functional_requirements_count: 0
nfrs: []

# stories.yaml
format: gherkin | generic | both
scope: all | slc | mvp
stories:
  - id: {}
    title: {}
    persona: {}
    format: {}

# ux-flows.yaml
flows:
  - story_id: {}
    entry_point: {}
    steps: []
    success_state: {}

# architecture.yaml
style: monolith | services | hybrid
tech_stack: {}
compliance_requirements: []
adr_ids: []

# tech-spec.yaml
repo_structure: monorepo | polyrepo
environments: []
cicd_tool: {}
hosting_provider: {}
auth_approach: {}
source_control: github | gitlab | other
monitoring_approach: {}

# ux.yaml
style_keywords: []
color_palette: {}
layout_pattern: {}
interaction_style: simple | animated | mixed
density: dense | open | balanced
```

### 4c. Document Production System

[7] All deliverable documents produced for the user follow this system.

**Front matter (YAML block at top of every deliverable):**

```yaml
---
title: {document title}
version: {major}.{minor}
status: draft | final | deprecated
author: {user's name}
assisted_by: Claude Code + SweetClaude
date: {YYYY-MM-DD}
audience: internal | investors | customers | hybrid
nda: false | "NDA: {brief statement}"
changes: {what changed from prior version, or "initial draft"}
previous_file: {prior filename, or "none"}
---
```

**File naming:** `{title}-{status}-v{major}.{minor}-{yyyymmdd}.md`
Example: `whizbang-product-brief-draft-v2.3-20260426.md`

**Paragraph numbering:** All paragraphs in draft documents are prefixed `[N]` where N is a sequential integer. Example: `[3] Lorem ipsum...`. Numbers appear in drafts only. When the user approves a draft as final, offer to remove paragraph numbers before writing the final version.

**Revision workflow:**
- User provides feedback → skill cuts a new revision
- Minor changes (wording, clarifications, additions within existing structure) → increment minor version
- Major changes (structural reorganization, change in direction, voice, or style) → increment major version
- On revision: update the previous file's `status` field to `deprecated` and rename it to match (e.g., `...-draft-v1.0-...` → `...-deprecated-v1.0-...`)

### 4d. Cross-Cutting Skill Behaviors

[8] These behaviors apply to all skills in the pipeline.

**Depth levels:** Every skill defines what L1/L2/L3 means for its domain. Skills auto-suggest a depth level based on context (e.g., project type from discovery state) but always let the user choose. The chosen depth is recorded in the effort log.

**Graceful degradation:** When a skill runs with missing prior-stage input: (1) recommend completing the missing stage — one sentence, no pressure; (2) accept immediately if the user declines; (3) proceed with what's available; (4) write a degraded status entry to the effort log noting what was missing and what the skill proceeded without. Skills never hard-fail on missing input.

**Frustration detection and graceful exit (strategy/planning skills):** If the user seems frustrated mid-interview, offer to proceed with what's already gathered or to circle back to the current section later. If the user skips or shortcuts a section, accept without resistance and log what was skipped.

**Progressive analysis:** When a skill has depth levels, never re-ask or re-collect information already established at a prior level. Each level builds on the previous without duplication.

---

## 5. Pipeline Skill Specifications

### Skill 1: product-discovery

[9] **Purpose:** Establish what is being built, for whom, and why — at the depth appropriate for the project type.

**Depth levels:**

*L1 — Intent and boundaries:*
- Ask the user to describe the project in their own words
- If target user is not apparent from the description, ask
- Ask intent: commercial product, internal tool, simple utility, hobby project, or other
- Produce an explicit "what this is NOT" boundary — at least one out-of-scope item
- Output: short concept statement with intent, user, and explicit boundary

*L2 — Problem and success (offered for commercial products and significant internal tools):*
- Specific problem being solved — ask for a concrete scenario, not abstract pain
- For whom specifically — refine the user description
- What success looks like for that user
- Challenge the framing: propose at least one of — an alternative framing of the problem, a gap in the solution, or a questionable assumption. Do not accept the first framing without scrutiny.

*L3 — Full pain thesis (offered for commercial products):*
- What approaches/solutions this replaces
- Impact of the problem: to the individual, and to their organization
- Can the problem be measured in time or money?
- Market/industry research available as background (market size, problem descriptions, analyst reports)
- Medicine vs. vitamins — is solving this a budget-already-exists necessity or discretionary spending?
- Accountability-control asymmetry — who gets fired, fined, or blamed when this goes wrong, and why can't they fix it themselves?
- Escalation chain — trace the problem from first symptom to worst-case outcome
- Validation rubric — assess each pain element as Red (assumption), Yellow (qualitative evidence), or Green (quantified with specific buyer quotes or data)
- Checkbook test — for the proposed wedge: "if you described only this capability in a meeting, would they write a check?"

**Output:** No deliverable document. Writes `discovery.yaml` to state.

---

### Skill 2: product-research

[10] **Purpose:** Survey the solution field — what exists commercially and in open source — so the user understands what they're entering before building.

**Behavior:** Explain what this skill does and ask if the user wants it before running. Many users will want to skip straight to building. Record in the effort log if skipped.

**Depth levels:** Auto-suggested based on project type. Commercial → suggest L2 or L3. Internal tool → suggest L1. Utility/hobby → suggest skipping. User decides.

*L1 — Solution landscape:* What product categories exist that address this problem? Who are the main players (commercial and open source)? What is the general community and user sentiment?

*L2 — Comparative assessment:* Which solutions are most relevant? What do they do well and where do they fall short? What is the pricing and distribution model for the commercial options? Initial competitive seed list (name, type, one-line description).

*L3 — SOTA depth:* Deep research on the most relevant solutions. Industry analyst coverage. Developer community discussions. Emerging approaches. Assessment of whether the problem space is crowded, novel, or lacks a market entirely.

**Two lenses presented in output:**
1. "Should I just use something that exists?" — honest assessment for self-solvers
2. "Is what I'm building novel, crowded, or in a space with no market?" — commercial viability framing

**Output:** Research deliverable document + `research.yaml`. Initial competitor seed list feeds `product-competition`.

---

### Skill 3: product-competition

[11] **Purpose:** Competitive analysis at the depth appropriate to the user's needs — from a quick survey to feature-by-feature deep analysis.

**Depth levels:**

*L1 — Survey:* Who competes in this space? What do they claim as their positioning and differentiators? What does community and user sentiment say about them?

*L2 — Matrix:* Select the most relevant competitors. Build a comparison matrix: user's product vs. each competitor on key dimensions. Assess each competitor's target market and target users. Capture pricing model and distribution strategy for each.

*L3 — Feature-deep:* User selects specific features for deep analysis. For each selected feature: analyze competitor product documentation, deep user reviews, journalist reviews, analyst coverage. Produce a feature-by-feature comparison.

**Output:** Competition deliverable document + `competition.yaml`.

---

### Skill 4: product-user-personas

[12] **Purpose:** Define the users of the product — who they are, what they need to do, and exactly what completing each task looks and feels like.

**Persona definition:** For each persona — name, role, context. Then: trigger (what specific moment or event makes them go looking for a solution — not a category, a specific situation), and deal-breakers (what would make them walk away even if the product technically works: price threshold, missing integration, required expertise, trust/credibility bar).

**Task definition:** For each task the persona needs to complete:
- Workflow steps — the sequence of actions from start to completion
- Information needed to begin — what must the user have or know before starting?
- Success criteria — must be observable, binary, and specific. Includes a number, step count, time limit, or concrete outcome. Bad: "user manages contacts easily." Good: "user creates a new contact in under 3 steps without leaving the current view."
- Common failure modes — what goes wrong and how?
- Challenge: "if this success criterion passed but the user was still unhappy, what's missing?" — that missing thing is another criterion.

**Task-building flow:**
1. User provides initial task description
2. Offer to build the remaining workflow details for review, or let the user provide them directly
3. When the task has initial shape, offer to research and expand — using prior competitive and market research to surface how other products handle this workflow, best practices, key features that support it, and significant improvement proposals
4. Any expansion must state its inferred user value. YAGNI and KISS apply. Do not add workflow steps to fill space.

**Persona-building flow:**
- Keep offering new tasks per persona until the user says the persona is complete
- Keep offering new personas until the user says there are no more
- When starting each new persona: always ask whether any already-defined tasks also apply to this persona — reuse saves significant time
- After all personas are complete: offer an anti-profile section — who is explicitly NOT a target user, and why?

**Output:** User personas deliverable document + `personas.yaml`.

---

### Skill 5: product-positioning-statement

[13] **Purpose:** Define how the product is positioned — for whom, in what category, what differentiates it, and why that matters.

**Prerequisite context:** This skill requires differentiators (from `product-competition`), pain and ICP (from `product-discovery` L3), and user definitions (from `product-user-personas`). It cannot produce a credible positioning statement without these. If they are missing, recommend completing them first — accept quickly if the user declines and proceed with what's available.

**Output:** Positioning statement deliverable document + `positioning.yaml`. Feeds `product-brief` value proposition section.

---

### Skill 6: product-brief

[14] **Purpose:** Write a product brief — a strategic document that describes what is being built, for whom, why it matters, and what success looks like.

**Pre-write flow:**
1. Present a bullet-point outline of sections, based on available input depth. Ask the user to adjust the outline before writing.
2. Ask: bullets or narrative style?
3. Ask: intended audience — internal, investors, customers, or hybrid?
4. Ask: are there sensitive details or NDA material to omit?

**Content:** Sections and depth scale to available input. The brief always ends with an "Additional Development" section — a bulleted list of content and sections that would typically appear in a product brief at this stage but were not covered, so the user knows what remains.

**Output:** Product brief deliverable document + `brief.yaml`. Follows document production system.

---

### Skill 7: product-prd

[15] **Purpose:** Write a Product Requirements Document — the formal requirements artifact that captures functional requirements, non-functional requirements, epics, and success metrics.

**Behavior:** Same pre-write flow as `product-brief` (outline → style → audience → NDA check). Sections and depth scale to available input.

**Typical sections:** Executive summary, problem statement, goals and success metrics, functional requirements (numbered, testable), non-functional requirements, epics and user story summary, out-of-scope, assumptions and constraints, open questions.

**Output:** PRD deliverable document + `prd.yaml`. Follows document production system.

---

### Skill 8: product-user-stories

[16] **Purpose:** Write user stories for the defined scope, in the format most useful for the intended audience.

**Step 1 — Format:** Ask whether the user wants:
- Gherkin-style stories (Given/When/Then — better for design and development handoff, TDD)
- Generic user stories (As a / I want / So that — better for product management, user-guide writing, marketing handoff)
- Both
- Something else

**Step 2 — Scope:** Ask whether to write stories for:
- All tasks for all personas
- SLC (Simple-Lovable-Complete) — offer to explain; many users are unfamiliar with this framing
- MVP (Minimum Viable Product)

*SLC path:* Ask who the most important user is and what promise is being made to them. Coach the user through articulating the promise — it should be specific and deliverable. Suggest which task(s) need to be implemented to fulfill that promise. Get confirmation or adjustment before proceeding.

*MVP path:* Ask which persona-tasks must be in MVP and which are later roadmap items.

*All path:* Include everything.

**Step 3 — Write:** Write all stories for the confirmed scope. Present when complete.

**Conventions:** Use best-practice naming and numbering for user stories — research current conventions at implementation time. Apply hierarchy by persona and functional area where appropriate. Apply front matter and file naming system unless it explicitly collides with user story best practices.

**Output:** User stories deliverable document + `stories.yaml`. Follows document production system.

---

### Skill 9: design-user-flows

[17] **Purpose:** Convert user stories into UX/UI flows — step-by-step paths a user takes through the interface. Bridges product definition and UX design.

**Input:** Reads `stories.yaml` and `personas.yaml`. For each story, traces the interface path: entry point, steps, decision points, error states, success state.

**Output:** User flows deliverable document + `ux-flows.yaml`. Feeds `design-ux` as input for interaction design.

---

### Skill 10: design-architecture

[18] **Purpose:** Define the system architecture — components, boundaries, communication patterns, data flow, and key decisions. Produce ADRs for each significant decision and an architecture document suitable for development handoff.

**Step 1 — Architecture interview:**

Decision points to cover:
- Primary language(s) and runtime
- Database — type (relational, document, graph, etc.) and specific technology
- Architecture style — monolith, services (microservices or macro-services), or hybrid
- Deployment model — web app, CLI app, CLI utility, desktop app, or combination
- Hosting model — on-premises, SaaS, locally run, or hybrid
- Any other significant architectural decisions specific to this project

Compliance and security interview (in the same step):
- Is any PII (personally identifiable information) being handled?
- Is any PHI (protected health information) being handled?
- Is any PCI data (payment card data) being handled?
- Is any financial data subject to regulatory oversight being handled?
- Any other regulated data or compliance requirements?

[19] Answers to compliance questions drive hard legal requirements throughout the architecture and tech spec — they are not options to weigh against convenience. Surface them explicitly and label them as requirements.

**Step 2 — Analyze:** Review responses alongside all available prior artifacts (brief, PRD, personas, user stories). Surface conflicts between what was stated in the interview and what the prior artifacts imply.

**Step 3 — Decision list:** Produce a list of architectural decisions to be made. Walk through each one with the user. Always offer a recommendation with reasoning. Record the decision and rationale.

**Step 4 — ADRs:** Create an ADR for each significant decision. Use best-practice ADR format — research current conventions at implementation time. Apply front matter and file naming unless it explicitly collides with ADR conventions.

**Step 5 — Boundary design (conditional on architecture style):**
- Service-oriented: define service boundaries — which services exist, how they communicate, what each service owns, where the seams are
- Monolith: define module/domain boundaries — bounded contexts, internal module structure, domain seams within the monolith
Both answer the same core question: where are the seams in this system?

**Step 6 — Architecture document:** Produce the architecture document. No handoff recommendation here — that belongs to `design-tech-spec`.

**Output:** Architecture deliverable document + ADR files + `architecture.yaml`.

---

### Skill 11: design-tech-spec

[20] **Purpose:** Drill down from architectural design into every technical decision a developer needs before writing the first line of code against a story.

**Coverage:**
- Repo structure — monorepo vs. separate repos for services; rationale
- Local development environment — setup requirements, toolchain, dev containers or native
- Environment strategy — test, staging, and production environments; how they differ; how to promote between them
- CI/CD implementation — what runs on every PR (lint, typecheck, test, security scan); what runs on merge to main; what gates production (approval, staging validation, canary); rollback plan
- Hosting provider — specific platform, tier, region
- Auth implementation — authentication and authorization design; specific library or service
- Source control platform — GitHub, GitLab, or other; branching strategy
- Monitoring and observability — what to monitor; alert thresholds and who gets paged; structured logging strategy and retention policy
- Scaling strategy — expected load profile; what scales horizontally vs. vertically; known bottleneck areas

[21] **Behavior throughout:** Ask questions as needed. Always offer a recommendation before asking the user to decide. Every recommendation must account for the user's situation (solo founder, small team, enterprise), cost constraints (bootstrapping vs. funded), and compliance requirements surfaced in `design-architecture` (treat these as hard requirements, not options to weigh).

**When complete:** When the tech spec is reviewed and approved to "final," recommend that the architecture document, ADRs, tech spec, and user stories are collectively ready for development handoff.

**Output:** Tech spec deliverable document + `tech-spec.yaml`. Follows document production system.

---

### Skill 12: design-ux

[22] **Purpose:** Define the visual and interaction design of the product — look, feel, vibe, structure, and style — and produce a UX/UI design spec suitable for handoff to AI mockup tools or a design team.

**Step 1 (first message only):** Ask whether the user has screenshots or URLs of apps or websites that inspire them. Explain that existing visual references are by far the fastest way to establish design direction. Accept images and URLs as input throughout the conversation.

**Step 2 — Design interview:**
- Look, feel, vibe — are there existing products or sites that have the aesthetic they want?
- Words — what words do they want people to use when describing the product? (e.g., "clean," "powerful," "friendly," "professional")
- Priority — rank: usability vs. aesthetic vs. simplicity
- Information density — dense and information-rich, or open and roomy and clean?
- Light, dark, or theme support
- Key colors, logos, brandmarks — existing brand assets or starting from scratch?
- Interactions — simple and immediate, or animated and expressive?
- UI copilot or AI-assist features embedded in the interface?
- Layout structure — present links to a few common layout patterns (e.g., sidebar navigation, top navigation, dashboard grid, single-column editorial) for the user to react to

**Step 3 — Write the spec:** Produce the UX/UI design spec following the document production system.

**Step 4 — Handoff:** Explain that the spec can be handed off to AI mockup tools. Recommend several current options to try (research and update this list at implementation time — the landscape changes frequently).

**Output:** UX/UI design spec deliverable document + `ux.yaml`. Follows document production system.

---

## 6. Migration (update-sweetclaude Step 8 Extension)

[23] When `update-sweetclaude` runs on an existing SweetClaude project, Step 8 is extended to handle migration to the new infrastructure:

1. **Seed the effort log:** If `.sweetclaude/log.md` does not exist, read `phase.yaml` and any other existing state and create a log entry summarizing what appears to have been completed prior to migration.
2. **Register pre-existing docs:** Scan `docs/` for existing artifact files and add an entry to the effort log listing them as pre-existing artifacts. Do not modify them.
3. **Create state directory:** Create `.sweetclaude/state/` if it does not exist.
4. **Offer document migration:** Identify existing deliverable documents that do not follow the new front matter and file naming conventions. Present a preview showing each file and what it would change to (old front matter → new front matter, old filename → new filename). Ask whether the user wants to approve all changes at once or file by file. Never rename or reformat without explicit approval.

[24] Individual skills never run migration. If a skill runs in a project without state files, it treats missing state as optional missing input and degrades gracefully per the cross-cutting behavior.

---

## 7. Files Modified Outside of Skills

| File | Change |
|---|---|
| `skills/master/SKILL.md` | Remove all `[removed]:` references; update skill names for renamed skills |
| `rules/phase-gates.md` | Remove [removed] 9-item checklist reference; update phase skill lists |
| `rules/interaction-model.md` | Remove "strip [removed] time estimates" reference |
| `skills/update-sweetclaude/SKILL.md` | Add Step 8 migration behavior described in Section 6 |

---

## 8. Post-Redesign Skill Count

Starting count: 61 skills
Deletions (absorbed or consolidated): -10
Additions: +2 (product-user-personas, product-competition)
Net renames (no count change): product-brief, product-user-stories, design-user-flows, code-review

**Post-redesign total: ~49 skills**
