---
description: "Academic paper development — from first principles through submission. Six-phase pipeline: first principles, literature & positioning, structure & venue, modular drafting, review & revision, submission. Adapted from lishix520/academic-paper-skills (MIT). Use when writing research papers, position papers, or academic publications."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Academic Paper Development

Six-phase pipeline from first principles to submission. Each phase has quality gates that must pass before advancing. The user controls pacing.

**Model preference:** Phases 0 and 3 (argumentation) benefit from the highest-performance model available. Flag this at session start.

---

## Phase 0: First Principles

**Purpose:** Establish the intellectual foundation before any literature or venue considerations.

### Process

1. **Core thesis.** Ask: "What is the central claim of this paper?" Probe until it is a single, clear statement that could be true or false.

2. **Key concepts.** Identify the 3-5 concepts the paper depends on. For each: what does it mean in this context, and what does the reader need to understand before encountering it?

3. **Novelty.** Ask: "What does not exist in the literature yet that this paper provides?" Push for specificity. "A new approach to X" is not enough. What specifically is new?

4. **Strongest objections.** Propose 2-3 objections a skeptical reviewer would raise. Discuss with the user: which are addressable, which are acknowledged limitations?

5. **Scope boundary.** What is this paper NOT about? What related topics does it deliberately exclude?

### Integration

If canonical or canonical-draft documents exist in `strategy/academic/` for this topic (from reconciliation), read them as starting context. Do not start from zero if the corpus has material.

If `strategy/narrative-arc/` exists, check: does this paper serve an objective in the arc? What claims does it need to support?

### Quality Gate 0

- [ ] Core thesis is a single, falsifiable statement
- [ ] 3-5 key concepts identified and defined
- [ ] Novelty is specific (not "a new approach")
- [ ] At least 2 objections identified with response strategy
- [ ] Scope boundary explicit (at least 2 things this paper is NOT about)

---

## Phase 1: Literature & Positioning

**Purpose:** Understand what exists, identify gaps, and position this paper against prior work.

### Process

1. **Literature search — three rounds** (adapted from academic-paper-skills):
   - Round 1: Direct keyword search — 20-30 papers on the core topic
   - Round 2: Expanded search — 10-15 papers from adjacent fields, cited-by chains
   - Round 3: Foundational works — 5-10 seminal papers the field builds on
   - Use RAG index (`strategy/rag-index/`) and web search in combination

2. **Gap identification.** For each gap claimed:
   - State the gap clearly
   - Cite 3-5 papers that approach but don't fill the gap
   - Explain why existing work falls short
   - Connect back to the Phase 0 novelty claim

3. **Positioning against prior work.** For the 5-8 most relevant papers:
   - How does this paper differ?
   - What does this paper do that the prior work cannot?
   - Where does it build on vs. depart from prior work?

4. **SWOT analysis on the thesis.**
   - Strengths: what makes the argument compelling?
   - Weaknesses: what are the acknowledged limitations?
   - Opportunities: what does this open up for future work?
   - Threats: what could undermine the argument? (reproducibility, scope, competing work)

### Quality Gate 1

- [ ] 35+ papers reviewed across three rounds
- [ ] At least 3 gaps identified, each with 3+ citations as evidence
- [ ] 5-8 prior works positioned against with specific differentiators
- [ ] SWOT completed with actionable items (weaknesses addressed in paper or flagged as limitations)

---

## Phase 2: Structure & Venue

**Purpose:** Select target venue, learn its norms, and build a quality-gated outline.

### Process

1. **Venue selection.** Based on thesis, positioning, and intended audience, propose 2-3 target venues (journals, conferences, workshops, preprint platforms). For each:
   - Scope fit (does this paper's topic match?)
   - Audience fit (who reads this venue?)
   - Impact and prestige
   - Timeline (submission deadlines, review cycles)
   - Recommend one with rationale. User decides.

2. **Writing norms analysis.** Read 3-5 recent papers from the target venue:
   - Typical length and section structure
   - Citation style and density
   - Tone and formality level
   - What makes papers in this venue successful?

3. **Outline construction.** Build a 3-level hierarchical outline:
   - Level 1: Major sections (Introduction, Related Work, [Core sections], Discussion, Conclusion)
   - Level 2: Subsections with purpose statements
   - Level 3: Key points, arguments, and evidence per subsection
   - Word count targets per section (informed by venue norms)

4. **Reviewer-perspective assessment.** Score the outline on 7 dimensions (adapted from academic-paper-skills):

   | Dimension | What It Measures | Score |
   |---|---|---|
   | Clarity | Is the argument structure clear from the outline? | /5 |
   | Completeness | Are all necessary sections and sub-arguments present? | /5 |
   | Literature support | Does the outline reference sufficient evidence? | /5 |
   | Methodological clarity | Is the approach/methodology evident? | /5 |
   | Originality | Does the outline convey what's new? | /5 |
   | Organization | Does the flow make logical sense? | /5 |
   | Venue fit | Does the structure match the target venue's norms? | /5 |

   **Threshold: ≥28/35.** If below, revise outline before proceeding.

### Quality Gate 2

- [ ] Target venue selected with rationale
- [ ] 3-5 sample papers analyzed for norms
- [ ] 3-level outline complete with word count targets
- [ ] Reviewer assessment ≥28/35

---

## Phase 3: Modular Drafting

**Purpose:** Write the paper section by section, with quality checkpoints after each.

**Model preference:** Use the highest-performance model available. Argumentation quality is the bottleneck.

### Writing Sequence

Write sections in this order (not the order they appear in the paper):

1. **Core argument sections** — the novel contribution (write these first while the argument is freshest)
2. **Related work** — position against literature from Phase 1
3. **Methodology/approach** — if applicable
4. **Introduction** — frame the paper now that you know what it says
5. **Discussion** — implications, limitations, future work
6. **Conclusion** — summarize contributions and significance
7. **Abstract** — write last (250-300 words, captures the whole paper)

### Per-Section Quality Checkpoint

After each section, assess on 5 dimensions (adapted from academic-paper-skills):

| Dimension | What It Measures | Score |
|---|---|---|
| Argument | Is the reasoning sound and well-supported? | /4 |
| Citations | Are claims backed by appropriate references? | /4 |
| Clarity | Is the writing clear and precise? | /4 |
| Structure | Does the section flow logically? | /4 |
| Consistency | Does it align with other sections already written? | /4 |

**Threshold: ≥16/20.** If below, revise before moving to next section.

### Cross-Reference Check

After all sections are drafted:
- Verify terminology is consistent throughout
- Verify forward/backward references are accurate
- Verify no section contradicts another
- Verify the abstract accurately reflects the final paper

### Quality Gate 3

- [ ] All sections drafted
- [ ] Each section scored ≥16/20
- [ ] Cross-reference check passed
- [ ] Abstract written and matches paper content

---

## Phase 4: Review & Revision

**Purpose:** Simulate peer review, incorporate feedback, iterate.

### Process

1. **7-dimension reviewer simulation.** Score the complete manuscript:

   | Dimension | What It Measures | Score |
   |---|---|---|
   | Originality | Does it make a genuine contribution? | /10 |
   | Significance | Does the contribution matter to the field? | /10 |
   | Soundness | Is the reasoning valid and methodology appropriate? | /10 |
   | Clarity | Is the paper well-written and understandable? | /10 |
   | Literature | Is prior work adequately covered and positioned against? | /10 |
   | Completeness | Are there missing arguments, sections, or evidence? | /10 |
   | Venue fit | Is this paper appropriate for the target venue? | /10 |

   **Threshold: ≥56/70.** If below, identify the weakest dimensions and revise.

2. **Expert caucus review.** Invoke the `caucus` skill for multi-perspective review. Request perspectives relevant to the paper's domain (e.g., for an AI safety paper: security researcher, ML researcher, formal methods expert).

3. **Revision loop.**
   - Compile findings from reviewer simulation + caucus
   - Prioritize: critical issues → important → minor
   - Revise the manuscript
   - Re-run reviewer simulation on revised sections
   - Repeat until ≥56/70 with no critical findings

4. **Final assembly.** Ensure all sections are coherent as a whole. Read the paper end-to-end one final time.

### Quality Gate 4

- [ ] Reviewer simulation ≥56/70
- [ ] Expert caucus completed, findings addressed
- [ ] No critical findings remaining
- [ ] End-to-end read completed

---

## Phase 5: Submission

**Purpose:** Format, finalize, and submit.

### Process

1. **Formatting.** Apply target venue's formatting requirements:
   - Template (LaTeX, Word, markdown)
   - Citation style (APA, IEEE, ACM, etc.)
   - Page/word limits
   - Figure/table formatting

2. **Abstract and metadata.** Finalize:
   - Abstract (250-300 words, last revision)
   - Keywords (5-8, informed by venue's taxonomy)
   - Author information and affiliations
   - Acknowledgments

3. **Submission checklist.**
   - [ ] Paper meets venue's formatting requirements
   - [ ] Page/word count within limits
   - [ ] All references are complete and properly formatted
   - [ ] Supplementary materials prepared (if applicable)
   - [ ] Cover letter drafted (if required)
   - [ ] All co-authors have reviewed and approved

4. **Submit.** Follow the venue's submission process.

5. **Post-submission.** Create a tracking document in `strategy/academic/`:
   ```
   strategy/academic/{paper-slug}-submission-tracker.md
   ```
   Contents: submission date, venue, expected review timeline, reviewer feedback (when received), revision plan.

### Quality Gate 5

- [ ] Formatted per venue requirements
- [ ] Abstract finalized
- [ ] Submission checklist complete
- [ ] Tracking document created

---

## Narrative Arc Integration

This skill reads the narrative arc but does not write to it.

**Before Phase 0:** Check `strategy/narrative-arc/` for:
- Does this paper serve an objective in the arc?
- What claims does the arc need this paper to support?
- What proof points should this paper strengthen?

**After Phase 4:** Report what the paper contributes to the arc. The user decides whether and how to update the arc via the narrative-arc skill.

## Reconciliation Integration

If `strategy/academic/` contains files from reconciliation (versioned source materials, canonical-drafts, or canonical docs), read them as starting context for Phase 0. Don't start from zero if the corpus has material on this topic.

## Attribution

Quality gate architecture and rubric framework adapted from [lishix520/academic-paper-skills](https://github.com/lishix520/academic-paper-skills) (MIT License).
