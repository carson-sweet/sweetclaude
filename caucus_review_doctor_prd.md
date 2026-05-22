# Caucus Review: sweetclaude:doctor PRD (ISSUE-177)

**Date:** 2026-05-22
**Proctor:** Automated caucus
**Scope:** Pros, cons, concerns, opportunities, lived experiences, recommendations
**Documents reviewed:** `issue-177-doctor-product-brief.md`, `issue-177-doctor-prd.md`

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

## Turn 1: Initial Reactions

### Strengths identified
- Problem statement is precise and grounded in a concrete scenario (unanimous)
- Severity-grouped report maps to developer mental model (Amara)
- Auto-fix list (FR-2.1) is genuinely safe — all reconstructable (Ravi, Kwame concurred)
- JSON output contract is architecturally sound (Ingrid)
- Consolidation solves a real, lived pain point (Mei-Lin, Tomás)

### Concerns raised
- Report format too technical for stated user persona (Mei-Lin, Tomás)
- Auto-fix trust varies dramatically by user experience level (Tomás, Ravi)
- Single-file `doctor.py` will be 800+ lines day one (Ravi)
- Check categories hardcoded, not extensible (Ingrid)
- No "all clear" happy path output specified (Mei-Lin)
- No false-positive suppression mechanism (Kwame)
- Auto-fix ordering problem: fixes can reveal new findings (Ravi)
- Deprecation wrappers are lies vs. clean break debate (Amara vs Kwame)
- 5-epic / 30-story scope may be over-engineered (Kwame)
- Bootstrap prompt at 7 days may trigger reflexive dismissal (Ingrid)

---

## Turn 2: Deep Dive

### Auto-fix trust model
Three positions emerged: auto-fix default (Mei-Lin), dry-run-first-run (Tomás), scan-only-first-release (Kwame). By end of Turn 2:
- Mei-Lin's argument that FR-2.1 items are inherently idempotent and non-reversible (cache rebuild, version string write) won against Ravi's undo proposal
- Tomás shifted to "first-run explainer" instead of dry-run default
- Kwame held scan-only position until Turn 3

### Single-file viability
Ravi conceded single file works if functions are pure. Proposed 1200-line split threshold. Amara proposed NFR: no check function may call another check function. Tomás noted single file harder to navigate for newcomers.

### Bootstrap trigger
Ingrid proposed event-triggered (post-update). Mei-Lin defended time-based for slow drift. Consensus: hybrid — event after updates/migrations, 7-day time fallback.

### Post-fix rescan
Ingrid introduced "scan twice" pattern from OpenClaw experience. Ravi refined: rescan only affected categories. 4/6 supported.

---

## Turn 3: Final Verdicts

| Panelist | Verdict | Condition |
|---|---|---|
| Dr. Amara Okonkwo | Approve with changes | Check registry, auto-fix closed-list NFR |
| Ravi Subramanian | Approve with changes | Post-fix rescan, partial-failure spec, pure-function NFR |
| Mei-Lin Zhao | Approve | Summary-tier default, happy path |
| Tomás Herrera | Approve with changes | Two-tier report, first-run explainer, suppression |
| Ingrid Vestergaard | Approve with changes | Check registry, 2s perf target, suppression JSON |
| Kwame Asante | Approve with changes | Suppression JSON, happy path, first-run explainer |

**Result: 6/6 approve (5 with changes, 1 unconditional)**

---

## Position Trajectory

| Panelist | Turn 1 | Turn 2 | Turn 3 |
|---|---|---|---|
| Amara | Strong approve, clean-break deprecation | Conceded wrappers have UX value | Approve with changes |
| Ravi | Cautious, monolith concern | Conceded single-file viable; raised ordering bug | Approve with changes |
| Mei-Lin | Enthusiastic approve | Won idempotency argument against undo | Approve |
| Tomás | Nervous about auto-fix | Shifted dry-run → first-run explainer | Approve with changes |
| Ingrid | Supportive, extensibility push | Won hybrid bootstrap argument | Approve with changes |
| Kwame | Skeptical, scan-only-first | Held position | Reversed to scan+fix-together |

---

## Consensus Findings

These findings had 5/6 or 6/6 support:

1. **The consolidation is correct.** 10 fragmented components into one entry point solves a real discoverability and trust problem. (6/6)

2. **Two-tier report: summary default, detail opt-in.** Summary tier uses user-facing language ("3 work items may have been lost"). Detail tier shows paths and component names. Default to summary. `--verbose` for detail. (5/6, Ravi neutral)

3. **Hybrid bootstrap trigger.** Event-triggered after updates and migrations. Time-based fallback at 7 days for slow-drift detection. (5/6)

4. **Check function registry.** Internal dict at module level mapping category names to check functions. Low cost, self-documenting, extensible. (5/6)

5. **Auto-fix is a closed, append-only list.** New checks default to prompted. Moving to auto-fix requires explicit justification. Write as an NFR. (5/6)

6. **Happy path output is mandatory.** "All clear. ✓" when zero findings. Builds trust. Add as FR-4.4. (5/6)

7. **Finding suppression mechanism.** `.sweetclaude/state/doctor-suppressions.json` — users mark findings as acknowledged. `--include-suppressed` to see all. Prevents false-positive fatigue. (4/6)

8. **Post-fix rescan (category-scoped).** After auto-fixes, rescan only affected categories. Surface new findings in a "Post-fix" section. Prevents fix-reveals-more-problems surprise. (4/6)

9. **First-run explainer.** On first doctor run per project, 2-line preamble explaining what doctor does. Suppressed on subsequent runs. (4/6)

10. **Pure-function NFR.** No check function may call or import from another check function. Each receives project state, returns findings. (4/6)

---

## Unresolved Disagreements

### Performance target: 2 seconds vs 5 seconds
- **For 2s (Ingrid):** If prompted at session start, 5 seconds feels like a hang. Scan should parallelize.
- **For 5s (Ravi, implicit):** The scan calls subprocesses (`cache.py`, `runner.py`). 2 seconds may not be achievable without architectural changes.
- **Resolution path:** Measure actual performance after implementation. Set 5s as the hard ceiling, 2s as the stretch goal.

### Single file split threshold
- **For 1200-line threshold (Ravi):** Written-down thresholds prevent "we'll split later" drift.
- **Against explicit threshold (Amara):** Pure-function discipline is the structural guarantee; line count is a proxy for the real problem (coupling).
- **Resolution path:** Start single file with pure-function NFR. Revisit at first review.

---

## Prioritized Recommendations

Ordered by committee support level and impact:

| # | Recommendation | Support | PRD change |
|---|---|---|---|
| 1 | Two-tier report (summary default) | 5/6 | Revise FR-4.1, FR-4.2, add `--verbose` to FR-7.3 |
| 2 | Check function registry dict | 5/6 | Add to FR-7.1 or new NFR |
| 3 | Auto-fix closed-list NFR | 5/6 | New NFR-6 |
| 4 | Hybrid bootstrap (event + 7-day) | 5/6 | Revise FR-6.1 |
| 5 | Happy-path output (FR-4.4) | 5/6 | Add FR-4.4 |
| 6 | Finding suppression mechanism | 4/6 | New FR-9 |
| 7 | Post-fix category rescan | 4/6 | Revise FR-7.4 |
| 8 | First-run explainer | 4/6 | Add to FR-4 or UX section |
| 9 | Pure-function NFR | 4/6 | New NFR-7 |
| 10 | Partial-failure spec for auto-fix | 3/6 | Revise FR-2 |

---

## Minority Reports

**Kwame Asante** held a minority position through Turn 2 that doctor should ship scan-only first and add fix in a subsequent release, to learn from user behavior before designing the fix surface. He reversed this position in Turn 3 after Mei-Lin and Tomás (the actual user personas) argued that "the user who runs doctor is the user who wants things fixed." Kwame's underlying concern — that the fix list was designed by framework authors, not derived from user behavior — remains valid as a monitoring point post-ship. **Recommendation:** track which prompted fixes users actually accept vs skip in the first release to validate the fix list empirically.

**Ravi Subramanian** noted that the single-file decision will likely be revisited within 2 releases as the check count grows. He does not oppose the current decision but wants it on record that the split boundary (pure functions with no cross-dependencies) should be maintained from day one so the eventual split is clean.
