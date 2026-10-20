+# Skill Audit Ledger

**Status:** Analysis complete; implementation not authorized by this ledger.  
**Date:** 2026-10-19  
**Authority:** [Tiered Skill Architecture](tiered-skill-architecture.md)

## Scope and method

This ledger inventories all 122 current `skills/*/SKILL.md` entries. It uses each skill’s declared description and top-level process shape, the current routing/reference surface, and the architecture boundaries approved for `Plan`, `Design`, `Build`, `Maintain`, `Configure`, and `Utils`. `Consolidate`, `Retire`, and `Reclassify` are proposed dispositions, not completed changes.

A disposition can only be executed after the migration gates in the architecture document are met: reference inventory, installed-path fixture, public-catalog verification, and preservation of the current workflow’s evidence and mutation contracts.

### Disposition meanings

| Disposition | Meaning |
|---|---|
| Retain | Keep as a focused Tier 2 workflow. |
| Consolidate | Fold into the named canonical workflow, index, or view after contract comparison. |
| Reclassify | Keep its capability but change its category, visibility, or role. |
| Retire | Remove after a time-bounded compatibility route; the named target is canonical. |
| Keep internal | Preserve as support/controller logic with no user-selectable workflow. |

## Ledger

| Current skill | Proposed home | Tier | Disposition | Canonical role / evidence |
|---|---|---|---|---|
| `_features` | Configure | 2 internal | Reclassify | Configure feature settings — Distinct stateful feature configuration, not public. |
| `_health` | Configure | 2 internal | Consolidate | doctor health checks — Its stated consistency scan is a doctor sub-operation. |
| `_migrate` | Configure | 2 internal | Keep internal | migrate controller — Owns snapshot and runner choreography behind migrate. |
| `_route` | Build | 1 internal | Retain | Tier 1 request router — Owns fast coarse classification before category indexes. |
| `behavioral-regression` | Configure | 2 library | Retire | Retired 2026-10-20. Contracts moved to `config/behavioral-contracts.md`; scoring is `scripts/behavioral_judge.py`. |
| `big-picture` | Utils | 2 library | Consolidate | status view: full — Overlaps status/recap; preserve as a full-status view. |
| `bootstrap` | Configure | 1 internal | Consolidate | Tier 1 startup controller — Overlaps master pre-flight and initial routing. |
| `claude-config-audit` | Configure | retire | Retire | doctor — Declared redirect to doctor. |
| `code-debt` | Maintain | 2 library | Retain | Maintain / code debt — Distinct health-improvement workflow. |
| `code-feature` | Build | 2 library | Retain | Build / feature — Distinct net-new implementation workflow. |
| `code-issue` | Build | 2 library | Retain | Build / issue — Distinct tracked-issue implementation workflow. |
| `code-review` | Build | 2 library | Retain | Build / review — Distinct adversarial review outcome. |
| `code-tdd` | Build | 2 internal | Reclassify | Build / TDD subworkflow — Declared internal process; remove direct command exposure. |
| `code-testing` | Build | 2 library | Consolidate | Build / verification index — Menu overlaps specialized testing workflows; retain modes only where unique. |
| `code-verify` | Build | 2 library | Retain | Build / completion verification — Owns evidence-before-completion gate. |
| `corpus-consolidate` | Utils | 2 library | Retain | Utils / corpus consolidate — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `corpus-promote` | Utils | 2 library | Retain | Utils / corpus promote — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `corpus-rag-reindex` | Utils | 2 library | Retain | Utils / corpus rag reindex — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `corpus-rag-setup` | Utils | 2 library | Retain | Utils / corpus rag setup — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `corpus-reconcile` | Utils | 2 library | Retain | Utils / corpus reconcile — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `corpus-status` | Utils | 2 library | Retain | Utils / corpus status — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `corpus-triage` | Utils | 2 library | Retain | Utils / corpus triage — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `course-correction` | Plan | 2 library | Retain | Plan / course correction — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `dashboard` | Utils | 2 library | Retain | Utils / dashboard — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `deploy-ship` | Build | 2 library | Retain | Build / deploy ship — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `design-api-design` | Design | 2 library | Retain | Design / design api design — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `design-architecture` | Design | 2 library | Retain | Design / design architecture — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `design-change-impact-analysis` | Design | 2 library | Retain | Design / design change impact analysis — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `design-data-model` | Design | 2 library | Retain | Design / design data model — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `design-manage-decisions` | Design | 2 library | Retain | Design / design manage decisions — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `design-solutioning-gate` | Design | 2 library | Retain | Design / design solutioning gate — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `design-tech-spec` | Design | 2 library | Retain | Design / design tech spec — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `design-user-flows` | Design | 2 library | Retain | Design / design user flows — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `design-ux` | Design | 2 library | Retain | Design / design ux — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `design-ux-review` | Design | 2 library | Retain | Design / design ux review — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `design-wireframes` | Design | 2 library | Retain | Design / design wireframes — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `doctor` | Configure | 2 library | Retain | Configure / doctor — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `document-corpus` | Utils | 2 index | Consolidate | Utils / corpus index — Declared pipeline menu; become category index, not a peer workflow. |
| `documents-academic-research` | Plan | 2 library | Retain | Plan / documents academic research — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `documents-narrative-arc` | Plan | 2 library | Retain | Plan / documents narrative arc — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `documents-update-docs` | Utils | 2 library | Retain | Build / documentation update — Distinct implementation-follow-on outcome. |
| `epic-design` | Plan | 2 library | Retain | Plan / epic decomposition — Distinct ordered-story design output. |
| `epics` | Plan | 2 library | Retain | Plan / epic management — Distinct ongoing epic state management. |
| `feature-setup` | Configure | 2 internal | Reclassify | Configure / developer install — Developer-only plugin sync, not product setup. |
| `find-skill` | Build | 1 internal | Consolidate | Tier 1 category/index router — Fine-grained routing becomes category-index selection. |
| `fix-sweetclaude` | Configure | retire | Retire | doctor — Declared redirect to doctor. |
| `go` | Build | 1 public | Retain | Default entry router — Primary natural-language entry point. |
| `guardian-off` | Configure | 2 library | Consolidate | Configure / guardian toggle — Pair with guardian-on as one stateful operation. |
| `guardian-on` | Configure | 2 library | Consolidate | Configure / guardian toggle — Pair with guardian-off as one stateful operation. |
| `help` | Utils | 1 public | Retain | Public help — Owns command explanation without full-library loading. |
| `hibernate` | Configure | 2 library | Retain | Configure / hibernate — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `hook-repair` | Configure | retire | Retire | doctor — Declared redirect to doctor. |
| `hotfix` | Maintain | 2 library | Retain | Maintain / hotfix — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `init` | Configure | 2 library | Consolidate | Configure / setup router — State detection belongs under Configure; setup remains distinct. |
| `john-wick` | Build | 2 library | Retain | Build / john wick — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `john-wick-checkin` | Build | 2 internal | Keep internal | Build / John Wick check-in — Declared internal subagent support. |
| `large-story` | Build | 2 internal | Keep internal | Build / large-story controller — Distinct controller-backed execution path. |
| `master` | Configure | 1 internal | Consolidate | Tier 1 startup controller — Overlaps bootstrap session pre-flight and routing. |
| `migrate` | Configure | 2 library | Retain | Configure / migrate — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `migrate-diagnose` | Configure | retire | Retire | doctor — Declared redirect to doctor. |
| `misc-meeting-prep` | Utils | 2 library | Retain | Utils / misc meeting prep — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `mockup-extract` | Design | 2 library | Retain | Design / mockup extract — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `mockup-graduate` | Design | 2 library | Retain | Design / mockup graduate — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `mockup-sandbox` | Design | 2 library | Retain | Design / mockup sandbox — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `next-steps` | Utils | 2 library | Consolidate | help / workflow orientation — Informational flow belongs as a Help view. |
| `off` | Configure | 2 library | Retain | Configure / off — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `orchestrator` | Build | 2 internal | Keep internal | Build / orchestrator — Owns controller main loop, not a user workflow. |
| `postmortem` | Maintain | 2 library | Retain | Maintain / postmortem — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-brief` | Plan | 2 library | Retain | Plan / product brief — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-competition` | Plan | 2 library | Retain | Plan / product competition — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-discovery` | Plan | 2 library | Retain | Plan / product discovery — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-manage-scope` | Plan | 2 library | Retain | Plan / product manage scope — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-market-messaging` | Plan | 2 library | Retain | Plan / product market messaging — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-milestone-planning` | Plan | 2 library | Retain | Plan / product milestone planning — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-milestones` | Plan | 2 library | Retain | Plan / product milestones — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-parking-lot` | Plan | 2 library | Retain | Plan / product parking lot — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-positioning-statement` | Plan | 2 library | Retain | Plan / product positioning statement — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-prd` | Plan | 2 library | Retain | Plan / product prd — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-research` | Plan | 2 library | Retain | Plan / product research — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-roadmap` | Plan | 2 library | Retain | Plan / product roadmap — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-roadmap-analysis` | Plan | 2 library | Retain | Plan / product roadmap analysis — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-sprint-plan` | Build | 2 library | Retain | Build / product sprint plan — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-terminology` | Plan | 2 library | Retain | Plan / product terminology — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-user-focus-group` | Plan | 2 library | Retain | Plan / product user focus group — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-user-stories` | Plan | 2 library | Retain | Plan / product user stories — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `product-user-tdd-tests` | Build | 2 library | Retain | Build / product user tdd tests — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `project-assess-shape` | Configure | 2 library | Retain | Configure / project assess shape — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `project-backlog` | Build | 2 library | Retain | Build / project backlog — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `project-backlog-triage` | Build | 2 library | Retain | Build / project backlog triage — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `project-epics` | Build | retire | Retire | epics — Declared deprecated redirect. |
| `project-gh-import-issues` | Build | 2 library | Consolidate | Build / issue integrations — Local-store import is an issue-management operation. |
| `project-gh-sync-issues` | Build | 2 library | Consolidate | Build / issue integrations — Local-store synchronization is an issue-management operation. |
| `project-goals` | Plan | 2 library | Retain | Plan / project goals — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `project-issues` | Build | 2 library | Retain | Build / project issues — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `project-mode` | Configure | 2 library | Retain | Configure / project mode — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `project-scope` | Plan | 2 library | Retain | Plan / project scope — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `project-sprints` | Build | 2 library | Retain | Build / project sprints — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `project-themes` | Build | 2 library | Retain | Build / project themes — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `purge` | Configure | 2 library | Retain | Configure / purge — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `recap` | Utils | 2 library | Consolidate | status view: recap — Overlaps status; preserve concise view. |
| `recover` | Configure | 2 library | Retain | Configure / recover — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `report-failure` | Utils | 2 library | Retain | Utils / failure report — Explicit, bounded cross-cutting reporting outcome. |
| `retro` | Configure | 2 library | Retain | Configure / retro — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `rollback-revert` | Maintain | 2 library | Retain | Maintain / rollback revert — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `security-patch` | Maintain | 2 library | Retain | Maintain / security patch — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `session-export` | Utils | 2 library | Retain | Utils / session export — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `setup` | Configure | 2 internal | Retain | Configure / setup — Owns onboarding branches after routing. |
| `small-story` | Build | 2 internal | Keep internal | Build / small-story controller — Distinct controller-backed execution path. |
| `something-broke` | Maintain | 2 library | Retain | Maintain / something broke — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `status` | Build | 1 public | Retain | Public status — Owns non-mutating project orientation. |
| `sweetclaude-behavioral-regression` | Configure | 2 library | Retire | Retired 2026-10-20 with its `testing.mode_regression` capability. |
| `testing-accessibility` | Build | 2 library | Retain | Build / testing accessibility — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `testing-compliance` | Build | 2 library | Retain | Build / testing compliance — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `testing-performance` | Build | 2 library | Retain | Build / testing performance — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `testing-plan` | Build | 2 library | Retain | Build / testing plan — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `testing-security` | Build | 2 library | Retain | Build / testing security — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `testing-session` | Build | 2 library | Retain | Build / testing session — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `ultraplan` | Design | 2 library | Retain | Design / ultraplan — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `update` | Configure | 2 library | Retain | Configure / update — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `usage` | Configure | 2 library | Retain | Configure / usage — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `user-personas` | Plan | 2 library | Retain | Plan / user personas — Distinct stated workflow outcome; validate against nearest neighbor during implementation planning. |
| `work-item-artifacts` | Configure | 2 library | Retain | Configure / artifacts — Distinct artifact-layout configuration and backfill. |

## Findings requiring design decisions

1. **Startup/router overlap:** `master`, `bootstrap`, `find-skill`, and `_route` all participate in entry or routing. Consolidation must preserve the pre-flight and disabled-project boundaries before reducing files.

2. **Status overlap:** `status`, `recap`, and `big-picture` differ primarily by view depth. A single Status workflow with explicit `recap`, `default`, and `full` views is the proposed canonical shape.

3. **Doctor aliases:** `claude-config-audit`, `fix-sweetclaude`, `hook-repair`, and `migrate-diagnose` declare Doctor as their successor. They are retirement candidates, but release migration must retain clear compatibility guidance until direct references are removed.

4. **Corpus shape:** `document-corpus` is an umbrella router over focused pipeline actions. It should become the Utils corpus index while the individual pipeline workflows remain focused library entries.

5. **Issue integrations:** GitHub import and local-mirror synchronization should be capability modes beneath issue management, not top-level public commands. Their existing migration/evidence guards must remain intact.

6. **Guardians:** enable and disable are opposite state transitions of one Configure operation, not two independently discoverable workflows.

7. **Testing surface:** `code-testing` is a menu across verification activities while `testing-*` skills are focused operations. Audit their exact overlap before deciding which `code-testing` modes remain.

## Next audit pass

Before any migration, compare the candidates above at procedure level: state read/write paths, mutation authority, required receipts, hooks, callers, and test coverage. Record the result in a migration story for each bounded batch; do not use this ledger alone as authority to delete or merge a skill.

## Verification

- Enumerated skill files: **122**.
- Ledger rows: **122**.
- Direct retirement candidates were identified from their own declared redirect/deprecation text.


