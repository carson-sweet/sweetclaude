# Caucus Review: sweetclaude:doctor PRD v2 (ISSUE-177)

**Date:** 2026-05-22
**Proctor:** Automated caucus (round 2 — updated PRD with safety model)
**Scope:** Pros, cons, concerns, opportunities, lived experiences, recommendations
**Documents reviewed:** `issue-177-doctor-product-brief.md` (updated), `issue-177-doctor-prd.md` (updated)

---

## Committee

| # | Name | Role | Perspective |
|---|---|---|---|
| 1 | Dr. Amara Okonkwo | Principal Platform Architect, Lattice Systems | Consolidation advocate, UX-first |
| 2 | Ravi Subramanian | Senior Staff Engineer, Meridian Cloud | Unix philosophy, lived monolith-split experience |
| 3 | Mei-Lin Zhao | Solo Founder, VertexLegal | SweetClaude power user since v2.x |
| 4 | Tomás Herrera | Junior Developer, Finch Health | SweetClaude user 2 months, discoverability-first |
| 5 | Ingrid Vestergaard | Staff Engineer, NovaCraft | OpenClaw `oc health` builder, 3 years |
| 6 | Kwame Asante | Senior Developer, Strata Analytics | Custom scripts, no SweetClaude, Unix philosophy |

---

## Verdict: 6/6 Approve (4 with minor additions, 2 unconditional)

| Panelist | Verdict | Key condition |
|---|---|---|
| Dr. Amara Okonkwo | Approve with minor additions | Check registry, remember-last-choice, numbered explainer |
| Ravi Subramanian | Approve with minor additions | Post-fix rescan, partial-failure handling, pure-function NFR |
| Mei-Lin Zhao | Approve | Archive retention, hybrid bootstrap, happy path |
| Tomás Herrera | Approve with minor additions | Finding suppression, first-run preamble, branch always offered |
| Ingrid Vestergaard | Approve with minor additions | Manifest schema, performance target, dry-run cap |
| Kwame Asante | Approve | Update epics, suppression auto-cleanup, archive as framework pattern |

---

## Position Trajectory (Across Both Caucus Rounds)

| Panelist | Round 1 T1 | Round 1 T3 | Round 2 T1 | Round 2 T3 |
|---|---|---|---|---|
| Amara | Strong approve, clean-break deprecation | Approve w/ changes, conceded wrappers | Safety model improved trust, menu friction concern | Approve, remember-last-choice solves friction |
| Ravi | Cautious, monolith + ordering concerns | Approve w/ changes, conceded single-file | Archive solves ordering concern, dry-run impl question | Approve, simulated dry-run acceptable for v1 |
| Mei-Lin | Enthusiastic | Approve | Safety model perfect for power users | Approve, unchanged |
| Tomás | Nervous about auto-fix | Approve w/ changes, dry-run compromise | Trust fully established by safety model | Approve, suppression + preamble |
| Ingrid | Supportive, extensibility push | Approve w/ changes | Registry/rescan still unaddressed, archive strong | Approve, all items converged |
| Kwame | Skeptical, scan-only-first | Approve w/ changes, reversed to scan+fix | "Single best feature" (archive), approve | Approve unconditional, archive as framework pattern |

---

## Consensus Findings (5/6+ support)

1. **Safety model is correct and complete.** The three-option menu (explain/dry-run/proceed), safety branch offer, per-run archive, and no-deletion-without-backup guarantee together create a tool that is fast for confident users and safe for cautious ones. (6/6)

2. **Archive directory is the single most valuable feature.** It makes every other design decision lower-stakes because changes are always reversible and auditable. (6/6)

3. **Safety branch offer always persists.** Even if the user has opted into fast mode (remember-last-choice), the branch offer is always shown. The branch is the undo mechanism; the menu is the preview mechanism. Different purposes, different persistence rules. (6/6)

4. **Two-tier report with summary default.** Summary tier uses plain English, no component names or file paths. Detail tier via `--verbose`. (6/6, carried from round 1)

5. **Check function registry dict at module level.** `CHECKS = {"category": fn, ...}`. Scan iterates the dict. Self-documenting, extensible. (5/6)

6. **Remember-last-choice with escalating trust.** After 3 consecutive identical menu choices, offer to persist as default. Not an explicit "fast mode" setting — earned through repetition. (5/6)

7. **Finding suppression with auto-cleanup.** `doctor-suppressions.json`. Users mark findings as acknowledged. Auto-remove entries when the underlying finding resolves. Report resolution as info. (5/6)

8. **Post-fix category-scoped rescan.** After auto-fixes, rescan only affected categories. New findings go into a "Post-fix" section. (5/6)

9. **Hybrid bootstrap: event-triggered + 7-day time fallback.** Post-update and post-migration event triggers, plus 7-day time-based fallback for slow drift. (5/6)

10. **Archive retention: 30 days or last 5 runs, whichever retains more.** Prune at start of each run. (5/6)

11. **Simulated dry run for v1.** Single-file writes only. Multi-file or conditional fixes require real execution. (6/6)

12. **Numbered explainer format.** One sentence per planned change, numbered for reference. (4/6, no objections)

13. **Happy-path output mandatory.** "All clear." when zero findings. (5/6, carried from round 1)

14. **Pure-function NFR.** No check function calls another. Each receives project state, returns findings. (4/6)

15. **Epics need updating for safety model scope.** Significant new stories for archive, suppression, retention, menu, manifest. (6/6)

---

## Unresolved Disagreements

None. All disagreements from both rounds converged by Turn 3 of round 2.

---

## Prioritized Recommendations for PRD Update

| # | Recommendation | Support | PRD Section |
|---|---|---|---|
| 1 | Remember-last-choice with escalating trust | 5/6 | Add to FR-2.1 |
| 2 | Finding suppression (`doctor-suppressions.json`) with auto-cleanup | 5/6 | New FR-9 |
| 3 | Archive retention: 30 days or last 5 | 5/6 | Add to FR-2.3 |
| 4 | Check function registry dict | 5/6 | New NFR-6 |
| 5 | Post-fix category-scoped rescan | 5/6 | New FR-2.7 |
| 6 | Hybrid bootstrap: event + 7-day time | 5/6 | Revise FR-6.1 |
| 7 | Pure-function NFR | 4/6 | New NFR-7 |
| 8 | Numbered explainer list format | 4/6 | Clarify FR-2.1 option 1 |
| 9 | Manifest schema specification | 4/6 | Clarify FR-2.3 |
| 10 | Performance target: 2s scan, 5s total | 4/6 | Revise NFR-1 |
| 11 | Dry-run simulation cap (single-file only) | 6/6 | Clarify FR-2.1 option 2 |
| 12 | First-run preamble (2-line, self-suppressing) | 4/6 | Add to FR-4 |
| 13 | Partial-failure handling for auto-fix | 3/6 | Clarify FR-2.5 |
| 14 | Update epics for safety model scope | 6/6 | Revise Epics 1, 2, 5 |
| 15 | Archive pattern as framework standard utility | 3/6 | Future: shared `scripts/archive.py` |

---

## Minority Reports

No minority positions remain. Kwame Asante, the strongest initial skeptic, gave an unconditional approve in the final round, noting: "The archive pattern should become a framework standard — not just for doctor, but for any SweetClaude tool that modifies files." This represents a shift from "this tool shouldn't exist" (round 1, Turn 1) to "this tool's safety pattern should be the default for all tools."

---

## Key Insight Across Both Rounds

The product owner's intervention between rounds — adding the safety model with explain/dry-run/proceed menu, mandatory archive, and no-deletion-without-backup — resolved the deepest disagreements from round 1 (auto-fix trust, transparency, reversibility) and created new consensus that didn't exist before. The committee's highest-rated feature (archive directory) and most important architectural decision (safety branch always persists) both came from this intervention. The PRD is stronger for having been challenged and revised.
