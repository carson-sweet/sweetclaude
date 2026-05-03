# OSS Launch Readiness Plan

**Version:** 1.0
**Date:** 2026-05-01
**Source:** OSS Expert Caucus — `scratch/caucus_review_oss_sweetclaude.md`
**Status:** Planning

---

## Overview

Twenty recommendations from a six-turn expert caucus, organized into four execution phases. Each item references the caucus turn and panelist that raised it.

The organizing logic:
- **Phase 1 (hours):** README fixes that require zero new content — structural moves, text edits, label corrections. Unblock these before any attention spike.
- **Phase 2 (days):** New short documents and signals that complete the project's community surface. Nothing here requires major writing — the longest piece is walkthroughs.md.
- **Phase 3 (weeks):** Architecture-level work that changes the project's sustainability and differentiation. These run in parallel with everything else.
- **Phase 4 (months):** Structural reorganizations and formal governance. Done once the project has a second maintainer and real contributor activity.

---

## Phase 1 — README Edits (hours)

All eight are text edits to README.md. No new files. No new content required. Do these together in one sitting.

| # | Action | Source | Notes |
|---|---|---|---|
| 1.1 | Add Anthropic cost signal to opening section | T5 — Priscilla | Add one sentence after the "Built for:" line: "Requires [Claude Code](https://claude.ai/code) — Anthropic's CLI (paid subscription)." |
| 1.2 | Move "Things to Try First" above Prerequisites and Install | T5/T6 — Priscilla | Cut-and-paste move. The section is already written; just repositioned. |
| 1.3 | Cut "How It Works" section to ~200 words + link to full doc | T5/T6 — Marcus/Priscilla | Keep 3–4 architecture-philosophy paragraphs. Move the 1,100-word feature detail to `how-it-works.md`, which already exists and covers this better. |
| 1.4 | Fix AGPL description | T5/T6 — Dmitri | Current: "free to use, modify, and distribute for any purpose." Rewrite to: "Free to use, modify, and distribute. No restrictions for personal or commercial tools. AGPL obligations activate only if you deploy SweetClaude as a network service offered to others — full terms in [LICENSE](LICENSE)." |
| 1.5 | Fix Superpowers dependency label | T5 — Dmitri | Change "Required" → "Required for code/TDD features" in the upstream dependencies table. Add a note: strategy-skills-only install works without it. |
| 1.6 | Add "Verified on model X as of date" to behavioral regression entry | T5/T6 — Yuki | In the Advanced commands table, add: "15 behavioral contracts validated against claude-sonnet-4-6 as of 2026-05-01." Update each model release. |
| 1.7 | Add link to behavioral-regression/SKILL.md from Advanced commands | T5 — Yuki | One sentence after the behavioral regression entry: "Full contract list: [skills/behavioral-regression/SKILL.md](skills/behavioral-regression/SKILL.md)." |
| 1.8 | Remove or date-gate the "Note for existing clones" banner | T5 — Marcus | It was valid on 2026-05-01. Remove it now or add a removal date to the text. |

---

## Phase 2 — Community Surface (days)

New short-form content and project signals. Each item is bounded — none requires framework knowledge.

| # | Action | Source | Deliverable | Notes |
|---|---|---|---|---|
| 2.1 | Add "looking for technical co-maintainer" to README Contribute section | T5/T6 — Marcus | One paragraph in README | Name what "full framework knowledge" means; link to the What Requires Full Framework Knowledge table in CONTRIBUTING.md; describe the time commitment and decision-making scope. |
| 2.2 | Open a "Co-maintainer wanted" GitHub issue | T3/T6 — Marcus | GitHub issue | Same content as 2.1 but in an issue so it's findable. Pin it. |
| 2.3 | Enable GitHub Discussions; add link to README Contribute section | T5/T6 — Nadia | GitHub Discussions space | Zero setup. Gives contributors a question space that isn't the issue tracker. |
| 2.4 | Add project status signals to README header | T5 — Marcus/Nadia | 2–3 shields.io badges | At minimum: version badge, license badge. Optional: contributors badge. These make health legible at a glance. |
| 2.5 | Write `docs/user-guide/walkthroughs.md` | T3 — Nadia | New doc | Most-cited missing document. Three or four end-to-end scenario chains. Content already exists in skills-reference.md "Common Skill Combinations" section — expand each into a narrative walkthrough. |
| 2.6 | Write `docs/user-guide/faq.md` | T1 — Nadia | New doc | Address the predictable first questions: "Does this require an Anthropic subscription?", "What is the deference level?", "How is this different from Cursor/Copilot?", "Can I use this with [language]?", "What if Claude changes behavior?" |
| 2.7 | Create stubs for remaining broken doc links | T1 — Nadia | File stubs | `phases-and-workflows.md`, `tdd.md`, `corpus-system.md` — at minimum, stubs with "this page is under construction" so links don't 404. Full content can follow. |
| 2.8 | Move 80+ command tables to `COMMANDS.md`; replace in README with one link | T6 — Nadia | New COMMANDS.md | The All Commands section (Product, Design, Code, Docs, Misc, Autonomous) is ~200 lines of tables. Move to COMMANDS.md. Replace in README with: "→ [Full command reference](COMMANDS.md)." |
| 2.9 | Produce a demo terminal recording | T3/T6 — Priscilla | GIF or video link | 90 seconds: `/sweetclaude:on` on empty folder → 3 questions answered → product brief skeleton appears. Embed in README above Getting Started. |

---

## Phase 3 — Sustainability and Differentiation (weeks)

These run in parallel with everything else. None are blocked by Phase 1 or 2.

| # | Action | Source | Deliverable | Notes |
|---|---|---|---|---|
| 3.1 | Write platform dependency policy | T2/T3/T6 — Dmitri | New doc: `docs/governance/platform-dependency-policy.md` | One page. Answers: what does SweetClaude depend on, what is the failure mode per dependency, what triggers would cause reconsideration, is there a contingency plan (or explicit acknowledgment there isn't). Link from Upstream Dependencies section in README. |
| 3.2 | Publish behavioral contract status per model version | T2/T6 — Yuki | New file: `docs/behavioral-contracts/status.md` | Table: contract name × model version × PASS/FAIL × date tested. Start with claude-sonnet-4-6. Update each release. This turns the behavioral regression suite from a tool into published evidence. |
| 3.3 | Write `ROADMAP.md` | T6 — Marcus | New doc | Three sections: Now (active work), Next (committed next), Later (on deck). Even a minimal roadmap tells contributors what matters. Does not need to be detailed — three bullet points per section is enough. |
| 3.4 | Add `CODE_OF_CONDUCT.md` and `SUPPORT.md` | T6 — Nadia | Two new files | CODE_OF_CONDUCT: Contributor Covenant is standard, zero-effort. SUPPORT.md: one page pointing to GitHub Discussions for questions, GitHub Issues for bugs, the behavioral regression skill for model compatibility questions. |

---

## Phase 4 — Structural Work (months)

Do these after a second maintainer exists and the project has real contributor activity. Premature structural work is wasted if the project's shape changes.

| # | Action | Source | Notes |
|---|---|---|---|
| 4.1 | Full README reorganization: `README.md` (pitch) + `INSTALL.md` + `QUICKSTART.md` | T6 — Priscilla | Phase 1 and 2 work keeps the README useful in the interim. This restructuring is the permanent fix. |
| 4.2 | Automate behavioral regression CI | T2/T3/T6 — Yuki | Requires a test harness that can invoke Claude Code programmatically against the 15 contracts. Multi-week engineering. Highest long-term differentiation value. |
| 4.3 | Formal governance document | T6 — Dmitri | Meaningful only once there's a second maintainer. Covers: who has merge rights, how decisions are made, how maintainers are added/removed. |

---

## Dependency Map

```
1.1–1.8  (README edits)  ──┐
                            ├──► 2.9 (demo recording — needs clean README first)
                            └──► 2.4 (status badges — can go in same README pass)

2.1–2.2  (co-maintainer)  ──► 4.3 (governance — needs a second maintainer)

2.5–2.7  (doc stubs/walkthroughs) ──► 4.1 (README reorganization)

3.1      (platform policy) ──► 3.2 (behavioral contract status — both are governance docs)

3.2      (contract status) ──► 4.2 (CI automation — automates what 3.2 does manually)
```

---

## What to Ignore (for now)

The caucus raised three concerns that are real but are not action items yet:

- **Anthropic product absorption risk** — genuine threat, cannot be mitigated directly. The moat is community. Build the community.
- **Model version churn** — mitigated by 3.2 (published contract status) and eventually by 4.2 (CI). The manual process is acceptable short-term.
- **AGPL enforcement in network service context** — correctly handled. The license is right. No action needed beyond the README description fix in 1.4.

---

## Success Criteria

Phase 1 done: A developer landing on the README sees the cost signal immediately, finds a low-stakes try path in the first two screens, and hits no 404s in the docs links.

Phase 2 done: A developer who wants to contribute can find a question space (Discussions), see the project health signals (badges), read the walkthroughs, and know whether there's a co-maintainer opportunity.

Phase 3 done: The behavioral contract status is published and model-version-tagged. A platform dependency policy exists. There is a visible roadmap.

Phase 4 done: The README is restructured for its true job. Behavioral regression runs in CI. There is a second maintainer with formal governance.
