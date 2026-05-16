# SweetClaude Strategy Split — Design Spec

**Date:** 2026-04-13
**Version:** 1.0
**Status:** Superseded by `docs/plans/skill-reorganization-plan-2026-04-13.md` (5-bucket architecture)
**Brief:** `docs/superpowers/specs/2026-04-13-sweetclaude-strategy-split-brief.md`

---

## 1. Directory Restructure

### Target Structure

```
~/.claude/skills/sweetclaude/
  SKILL.md                          # Master router (updated)
  discover-deep/SKILL.md            # Orchestration — both tracks
  work-router/SKILL.md              # Orchestration — updated for strategy routing
  hibernate/SKILL.md                # Orchestration — both tracks
  init/SKILL.md                     # Orchestration — updated for strategy/ creation
  code/
    tdd/SKILL.md
    fix-issue/SKILL.md
    pr-ready/SKILL.md
    ripple/SKILL.md
    auto-docs/SKILL.md
    scope-tracker/SKILL.md
    gherkin-bridge/SKILL.md
    mutation-testing/SKILL.md
  strategy/
    reconciliation/SKILL.md         # NEW — file onboarding and synthesis
    academic/SKILL.md               # NEW — paper development
    narrative-arc/SKILL.md          # NEW — knowledge graph
    meeting-prep/SKILL.md           # NEW — stakeholder deliverables
  shared/                           # Config and rules only — no skills
    (phase-gates.md, interaction-model.md, tdd-levels.md, phase-skills.yaml, etc.)
```

### Migration Rules

- Skill name prefix shifts: `sweetclaude-tdd` → `sweetclaude-code-tdd`
- Invocation notation shifts: `sweetclaude:tdd` → `sweetclaude:code/tdd`
- Every reference in `phase-skills.yaml`, `phase-gates.md`, and master `SKILL.md` updates
- Clean break — no aliases, no backward compatibility shims
- `notion-scaffold/` parked (WP-3, separate branch)
- Root-level skills (discover-deep, work-router, hibernate, init) stay at root — they're orchestration, not content

### Config Restructure (phase-skills.yaml)

Strategy work types get their own skill lists, not mixed into code lists:

```yaml
always_loaded:
  skills:
    - sweetclaude
    - sweetclaude:work-router
    - sweetclaude:hibernate
    - hibernate-project

code:
  phases:
    discover:
      skills: [sweetclaude:discover-deep, [removed], ...]
    implement:
      skills: [sweetclaude:code/tdd, sweetclaude:code/fix-issue, ...]
    # ... all 7 phases

strategy:
  phases:
    discover:
      skills: [sweetclaude:discover-deep, sweetclaude:strategy/narrative-arc, ...]
    define:
      skills: [sweetclaude:strategy/reconciliation, sweetclaude:strategy/academic, ...]
    # ... all 7 phases
```

### Artifact Placement Rules

**`docs/` (code-generative, stays with repo):**
- Implementation plans
- Technical specs / architecture docs
- Gherkin .feature files
- User stories with acceptance criteria
- API specs / schemas
- Test plans
- Design specs that map to implementation tasks
- Superpowers plans and specs that produce code tasks
- Technical backlog (`docs/backlog/`)

**`strategy/` (non-code, separable from repo):**
- Product briefs / PRDs
- Research papers and publication materials
- Market messaging and positioning
- Competitive analysis
- Stakeholder meeting prep and deliverables
- Business planning / commercialization strategy
- IP strategy
- Continuation prompts / session handoffs
- LanceDB embeddings / RAG index
- Expert caucus outputs
- SWOT analyses
- Decision logs and assumption registers
- Product feature ideas (NOT in docs/backlog/)

**Backlog guard:** SweetClaude work router prevents non-technical items from landing in `docs/backlog/`. Product ideas, feature concepts, and strategic initiatives route to `strategy/` instead.

### Project-Level Strategy Directory

```
{project-repo}/
  strategy/
    reconciliation/
      archive/               # Deprecated originals with lineage frontmatter
    positioning/
    competitive/
    market-messaging/
    biz-planning/
    academic/
    meeting-prep/
    narrative-arc/
    decisions/
    rag-index/
```

---

## 2. File Reconciliation v2

### Purpose

Onboard unstructured files into the `strategy/` system. First skill built because everything else works from an organized corpus.

### Workflow

```
1. User has files somewhere (e.g., ~/dev/my-project-archive/)
2. SweetClaude offers to copy them into strategy/reconciliation/
3. Skill creates INVENTORY — every file catalogued:
   | File | Type | Topic | Category | Date | Summary | Recommendation |
   (Category maps to strategy subdirectories)
   (Recommendation: categorize, merge-with {target}, archive-only, discard)
4. Skill creates PER-FILE PLAN
5. User approves inventory + plan
6. Skill reorganizes files under category subdirs with versioned filenames
7. Skill asks: run synthesis?
   → If yes: produce canonical-draft docs per topic area
   → Archive originals with deprecation frontmatter + lineage
   → Auto-ingest (RAG index + phase gate awareness)
```

### Versioning Scheme

```
{topic-slug}-v{major}.{minor}-canonical-draft.md    # Synthesized, awaiting user approval
{topic-slug}-v{major}.{minor}-canonical.md           # User-approved, current truth
{topic-slug}-v{major}.{minor}.md                     # Historical / working version
```

- All files have a version number
- `-canonical-draft` suffix: synthesized by AI, needs user review/edit/approval before promotion
- `-canonical` suffix: user-declared current truth. Only the user can promote a draft to canonical.
- When canonical gets revised: version bumps (`v1.0-canonical` → `v1.1-canonical`)
- Only one file per topic has the `-canonical` suffix at any time

**The skill explicitly communicates:** "These canonical-drafts are the best synthesis I can produce from the source material. They need your review, edits, and approval before they become canonical. Only you can promote a draft to canonical."

### Deprecation Frontmatter (archived originals)

```yaml
---
status: deprecated
incorporated_into: strategy/academic/cultivated-persona-paper-v1.0-canonical.md
original_source: /Users/me/dev/my-project-archive/parts and fodder/section-3.md
archived_date: 2026-04-13
category: academic
---
```

Lineage in both directions: canonical knows where content came from (synthesis process), archived originals know where they went.

### Synthesis Process

Per topic area, when user opts in:

1. Gather all files categorized to that topic
2. Use existing reconciling-documents extraction pattern (read each, extract to scratch file, note conflicts)
3. Ask user: do you have a template, example, or specific sections/topics? Present default outline if not.
4. Draft the canonical-draft document
5. Present for user review — explicitly a draft, not final
6. On approval: user promotes to canonical (skill renames suffix, updates archive frontmatter)

### RAG Ingestion

After canonical docs exist:
- Invoke `rag-index` to index `strategy/`
- Canonical docs get indexed; archived originals do not
- Phase gates check `strategy/` for existing canonical docs before starting related work

### What the Skill Does NOT Do

- Does not delete any files — only copies, moves within strategy/, adds frontmatter
- Does not make judgment calls about discarding without user approval
- Does not synthesize without explicit user opt-in
- Does not touch anything in `docs/`
- Does not produce canonical docs — only canonical-drafts. User promotes.

---

## 3. Academic Paper Development

### Foundation

Adapted from lishix520/academic-paper-skills (MIT). Keeps 5-phase pipeline architecture. Reorders starting point (first principles before venue selection). Generalizes beyond philosophy.

### Pipeline

**Phase 0: First Principles**
- What are the key concepts, arguments, and claims?
- What's the core thesis?
- What's novel — what doesn't exist in the literature yet?
- What are the strongest objections to this thesis?

**Phase 1: Literature & Positioning**
- Multi-round literature review (keyword + semantic search)
- Gap identification with evidence (3-5 citations per gap, from community skill)
- Positioning against prior work
- SWOT on the paper's thesis

**Phase 2: Structure & Venue**
- Target venue/platform selection (informed by thesis + positioning)
- Writing norms analysis (sample papers from target venue)
- Outline with section-level quality gates
- Reviewer-perspective assessment of outline

**Phase 3: Modular Drafting**
- Section-by-section writing (beats/modules)
- Per-section quality checkpoint (5-dimension rubric)
- Cross-reference consistency checks between sections
- Should use higher-performance model for argumentation quality

**Phase 4: Review & Revision**
- 7-dimension reviewer simulation (35-point scale, adapted)
- Expert caucus review (invoke existing caucus skill)
- Revision loop — address findings, re-review
- Final manuscript assembly

**Phase 5: Submission**
- Formatting for target venue
- Abstract and metadata finalization
- Submission checklist
- Post-submission: track status, plan responses to reviewer feedback

### Taken from Community Skill

- Phase structure concept (strategist + composer separation)
- Quality rubrics (5-dimension section assessment, 7-dimension reviewer simulation)
- Literature search methodology (3-round keyword + semantic)
- Python validation scripts as reference

### Added

- Phase 0 (first principles) — entirely new
- Generalization beyond philosophy — section guides for STEM, security research, AI safety
- Revision loop (community skill stops at assessment)
- Integration: caucus for expert review, rag-index for lit search, narrative-arc for strategic positioning
- Higher-performance model preference for Phase 0 and Phase 3

### Dropped

- Philosophy-specific platform recommendations
- Preprint-only assumption

### Narrative Arc Integration

Academic skill checks narrative-arc (read-only) for:
- Does this paper serve an objective in the arc?
- What claims does this paper need to support?
- What proof points should this paper strengthen?

Arc updates happen through the narrative-arc skill, not the academic skill.

### Reconciliation-v2 Integration

If academic source materials exist in `strategy/academic/` from reconciliation, the academic skill reads them as starting context for Phase 0.

---

## 4. Narrative Arc

### Design Scope

Full design deferred to its own DESIGN cycle. The knowledge graph concept is architecturally significant — node types, credibility scoring, graph traversal, and storage format need dedicated discovery and design grounded in a real project arc as the first instance.

### Interface Contract (locked in now)

**What narrative-arc exposes to other skills:**
- Given a document or claim → which objectives it serves, what it strengthens, what it weakens
- Given an objective → what supports it, what opposes it, what's missing (gaps)
- Given a topic area → credibility assessment (how well-supported are the claims?)

**What other skills do with it:**
- Academic: reads arc to understand what a paper needs to prove
- Meeting-prep: reads arc to understand what's strong enough to present vs. what's soft
- Reconciliation-v2: can populate initial arc nodes when synthesizing canonical-drafts (user approves)

**Storage:** `strategy/narrative-arc/` in the project repo. Format TBD — must be human-readable and AI-parseable.

**Not designing now:** node types, credibility scoring model, graph traversal logic, visualization.

---

## 5. Meeting Prep

### Workflow

```
Input: who, when, what's the purpose
    → Pull relevant context from strategy/ corpus (RAG search)
    → Pull relevant nodes from narrative-arc (what's strong, what's soft)
    → Draft deliverables:
        - Agenda with objectives
        - Talking points per topic (with confidence levels from arc)
        - Key asks / desired outcomes
        - Anticipated questions with prepared responses
        - Leave-behinds if applicable (one-pagers, summaries)
    → User reviews and edits
    → Post-meeting: capture debrief notes, update arc with outcomes
```

### Design Principle

Meeting prep is a **consumer** of the strategy corpus, not a producer. It reads from positioning, academic, biz-planning, competitive — whatever's relevant — and assembles deliverables. The only thing it writes back is the debrief, which may trigger arc updates.

### Stakeholder Profiles

Maintained in `strategy/meeting-prep/`:

```
strategy/meeting-prep/kevin-passarello.md
strategy/meeting-prep/don-brown.md
```

Each contains: role, relationship context, meeting history, what they care about, communication style notes. Updated after each debrief. Prevents the "who is Kevin again?" problem across sessions.

---

## 6. Project Initialization (Updated Init Skill)

### The Problem

The typical case isn't greenfield. It's "I have a code repo and/or a pile of strategic files somewhere else." Strategic materials live in Claude.ai exports, Google Drive, desktop folders, Slack, all over the place. The init skill must handle bringing these together.

### Three Scenarios

**Scenario A: Code repo exists, strategy files exist elsewhere.**
Most common case. The code repo gets `strategy/` added. Reconciliation-v2 onboards the external files.

```
1. Detect existing repo
2. Create strategy/ directory structure within it
3. Ask: "Do you have existing strategic materials to onboard?"
   → Yes: "Where are they?" → offer to copy into strategy/reconciliation/ → trigger reconciliation-v2
   → No: strategy/ created empty, ready for new work
4. Set up RAG index for strategy/
5. Initialize SweetClaude state if not present
```

**Scenario B: Code repo exists, no separate strategy files.**
Strategy work starts fresh in `strategy/` within the existing repo. Same flow as A minus the onboarding step.

**Scenario C: Strategy files exist, no code repo yet.**
The strategic materials are the starting point. Code may never come — some projects are purely strategic.

```
1. Ask: "Do you have an existing code repo for this project?"
   → No
2. Ask: "Create a new repo, or work without one?"
   → New repo: create with strategy/ as initial structure. No docs/, no src/.
   → No repo: create local project directory with strategy/, no git. Warn unversioned.
3. Ask: "Do you have existing strategic materials to onboard?"
   → trigger reconciliation-v2
4. Set up RAG index
5. Initialize SweetClaude state
```

### Key Principle

**A SweetClaude project can start from strategy and never touch code, or start from strategy and grow into code later.** The directory structure accommodates both:

```
# Strategy-only project (Scenario C)
my-project/
  strategy/
    reconciliation/
    positioning/
    academic/
    ...

# Later, if code work begins
my-project/
  strategy/        # Already populated
  docs/            # Added when code work begins
  src/             # Added when code work begins
  package.json     # etc.
```

Code-side directories (`docs/`, `src/`, config files) only appear when code work actually starts. They are not scaffolded preemptively.

---

## Build Order

1. **Directory restructure** — move existing skills, update all references
2. **Init skill update** — three-scenario project initialization
3. **Reconciliation-v2 skill** — onboard unstructured files, synthesize corpus
4. **Academic skill** — paper development pipeline
5. **Narrative arc skill** — knowledge graph (own design cycle first)
6. **Meeting prep skill** — stakeholder deliverables

Each goes through its own PLAN → IMPLEMENT → VERIFY cycle after this design is approved.
