# Operation and routing-path inventory

Version: 1.0.0

Date: 2026-10-19

Status: required coverage, not execution evidence

Read [the test design](README.md) for entry variants, fixture definitions, profiles and acceptance rules. Every row below requires direct and indirect coverage of both the happy outcome and the stated failure modes. The same prompt is reused with a changed failure fixture; the user must not be told which route to pick.

`ISSUE-001`, `EP-001`, `MS-001`, `#42` and other IDs are deliberately seeded fixture identities. Context resolves stores (business goal, roadmap target, milestone) that share an ID family. Where wording remains ambiguous, assert clarification first. Internal/redirect rows are continuation paths reached through their owning public workflow, not public commands.

For each workflow, the branch list expands its operation rows. Each semicolon-separated choice/value and each source decision is a separate branch obligation. Profile relevance and a concrete scenario-to-source map are required before execution completeness can be claimed.

## top/go

Source: [skills/go/SKILL.md](../../../skills/go/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Distinguish argument routing from state proposal; wait for actual selection; follow first unmet phase criterion and authoritative closeout.

Failure obligations: Wrong priority, lost intent, action before proposal approval or invalid evidence must fail rather than appear complete.

Branch inventory: All five priorities and 26 phase-table rows; review/proceed/other; stale plan; mode gate; PR recording; closeout substeps.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.go.propose` | Propose what we should work on next. | I am back in the project and unsure what deserves attention first. |
| `top.go.request` | Help me fix the known lending authentication bug. | Staff still hit the known authentication failure when lending books. |
| `top.go.review-other` | Show other candidates instead of the proposed item. | The first proposal is not what I want to take on right now. |
| `top.go.closeout` | Close out the verified current story. | The current story's verification is complete and its approved delivery now needs the recorded closeout. |

## top/plan

Source: [skills/plan/SKILL.md](../../../skills/plan/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Preserve request verbatim and hand off category→index/loader→exact workflow; empty/unclear requests receive focused clarification.

Failure obligations: Wrong category authority, whole-library loading, fabricated workflow or lost args fails.

Branch inventory: Empty args; underspecified request; concrete request; conflicting category; no workflow matches; one vs ambiguous match.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.plan.entry` | Help with this plan task using the supplied project context. | I need help in the plan area but have not yet described a concrete operation. |

## top/design

Source: [skills/design/SKILL.md](../../../skills/design/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Preserve request verbatim and hand off category→index/loader→exact workflow; empty/unclear requests receive focused clarification.

Failure obligations: Wrong category authority, whole-library loading, fabricated workflow or lost args fails.

Branch inventory: Empty args; underspecified request; concrete request; conflicting category; no workflow matches; one vs ambiguous match.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.design.entry` | Help with this design task using the supplied project context. | I need help in the design area but have not yet described a concrete operation. |

## top/build

Source: [skills/build/SKILL.md](../../../skills/build/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Preserve request verbatim and hand off category→index/loader→exact workflow; empty/unclear requests receive focused clarification.

Failure obligations: Wrong category authority, whole-library loading, fabricated workflow or lost args fails.

Branch inventory: Empty args; underspecified request; concrete request; conflicting category; no workflow matches; one vs ambiguous match.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.build.entry` | Help with this build task using the supplied project context. | I need help in the build area but have not yet described a concrete operation. |

## top/maintain

Source: [skills/maintain/SKILL.md](../../../skills/maintain/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Preserve request verbatim and hand off category→index/loader→exact workflow; empty/unclear requests receive focused clarification.

Failure obligations: Wrong category authority, whole-library loading, fabricated workflow or lost args fails.

Branch inventory: Empty args; underspecified request; concrete request; conflicting category; no workflow matches; one vs ambiguous match.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.maintain.entry` | Help with this maintain task using the supplied project context. | I need help in the maintain area but have not yet described a concrete operation. |

## top/configure

Source: [skills/configure/SKILL.md](../../../skills/configure/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Preserve request verbatim and hand off category→index/loader→exact workflow; empty/unclear requests receive focused clarification.

Failure obligations: Wrong category authority, whole-library loading, fabricated workflow or lost args fails.

Branch inventory: Empty args; underspecified request; concrete request; conflicting category; no workflow matches; one vs ambiguous match.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.configure.entry` | Help with this configure task using the supplied project context. | I need help in the configure area but have not yet described a concrete operation. |

## top/utils

Source: [skills/utils/SKILL.md](../../../skills/utils/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Preserve request verbatim and hand off category→index/loader→exact workflow; empty/unclear requests receive focused clarification.

Failure obligations: Wrong category authority, whole-library loading, fabricated workflow or lost args fails.

Branch inventory: Empty args; underspecified request; concrete request; conflicting category; no workflow matches; one vs ambiguous match.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.utils.entry` | Help with this utils task using the supplied project context. | I need help in the utils area but have not yet described a concrete operation. |

## top/status

Source: [skills/status/SKILL.md](../../../skills/status/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Render exact requested live view without advancing or repairing work; one declared cache rebuild per invocation.

Failure obligations: Guard stop, unknown argument, unavailable data or warnings are truthful; no hidden product-state repairs.

Branch inventory: No arg; conditional menu; issue/epic/release/roadmap/backlog/dependencies/sprint; filters; all warnings and schema guards.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.status.session` | Show the current project status. | I have lost track of where we left off in this project. |
| `top.status.issue` | Show status for ISSUE-001. | I need to understand what is happening with ISSUE-001 right now. |
| `top.status.epic` | Show status for EP-001. | I need the current progress and remaining work in EP-001. |
| `top.status.release` | Show status for MS-001. | I need the current progress and included work for MS-001. |
| `top.status.roadmap` | Show the roadmap status. | I need a current picture of milestones, epics and their issues together. |
| `top.status.backlog` | Show the backlog status. | I need to see the current uncommitted work grouped by priority. |
| `top.status.backlog-priority` | Show only P0 backlog items. | I need the highest urgency backlog items without the lower-priority queue. |
| `top.status.backlog-epic` | Show backlog items belonging to EP-001. | I need only the waiting work that contributes to EP-001. |
| `top.status.dependencies` | Show work dependencies. | I cannot tell what is blocking what across the project. |
| `top.status.sprint` | Show the current sprint status. | I need a current iteration summary without changing its work. |
| `top.status.unknown` | Show status for the unsupported view wibble. | The status view name I remember is wibble; if that is wrong I need help choosing a valid one. |

## top/help

Source: [skills/help/SKILL.md](../../../skills/help/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Answer via correct help branch/reference with useful menus and no unintended workflow execution.

Failure obligations: Invalid/old command guidance, hidden setup/mode mutations or unavailable platform claim fails.

Branch inventory: Every main/submenu; mode recommendation follow-ups; new/existing project; survey consent; skip; preferences; freeform.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.help.menu` | Explain how to use SweetClaude. | I am new here and do not know what SweetClaude can help me do. |
| `top.help.phases` | Explain the project phases. | I do not understand how an idea becomes a shipped product in this workflow. |
| `top.help.phase-workflows` | Explain which workflows fit each phase. | I know the phase names but not what kind of work belongs in each. |
| `top.help.structure` | Explain project structure and deliverables. | I cannot tell where SweetClaude's outputs live or what each stage produces. |
| `top.help.hello-world` | Walk through a hello-world project. | I need a small concrete example of using the framework from the beginning. |
| `top.help.existing` | Explain how SweetClaude approaches an existing project. | Our app already exists and I do not understand how adopting the framework differs from starting fresh. |
| `top.help.modes` | Explain the operating modes. | I keep hearing Flow, Kanban, Shape Up and Agile and do not know how they differ. |
| `top.help.mode-advice` | Help me choose an operating mode without changing it. | I want advice on how much structure fits this project before making a decision. |
| `top.help.mode-differences` | Explain what changes in practice between modes. | The mode names alone do not tell me what a working day would look like. |
| `top.help.mode-switch` | Explain how to switch modes later. | I worry we will be stuck with the initial operating style if the team changes. |
| `top.help.workflows` | Explain the available workflows and skills. | I know the main commands but not the kinds of work they can guide. |
| `top.help.examples` | Show concrete workflow examples. | I learn better from an actual feature, incident or product-startup walkthrough. |
| `top.help.testing` | Explain how SweetClaude handles testing. | I do not understand what evidence the framework expects before calling work complete. |
| `top.help.project` | Discuss how SweetClaude would approach my project. | I have a specific project situation and need a tailored explanation before adopting anything. |
| `top.help.freeform` | Explain the difference between disabling the guardian and deactivating SweetClaude. | These two ways of turning things off sound similar and I need to understand them before acting. |
| `top.help.skip-welcome` | Skip the help welcome in future sessions. | I know the introduction already and want future help sessions to begin with the conversation. |
| `top.help.preferences` | Show what SweetClaude has learned about my preferences. | I want to inspect the user preferences that influence how the framework works with me. |
| `top.help.forget` | Remove the selected learned preference. | One of the recorded preferences no longer represents how I want the framework to behave. |

## top/master

Source: [skills/master/SKILL.md](../../../skills/master/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Honor activation/install/project gates, apply learnings/deference/context and only user-led evidence-backed phase transitions.

Failure obligations: Declined setup, missing installation, failed gate or missing manifest blocks framework work; no partial-mode workaround.

Branch inventory: Configured/legacy/absent/disabled; unset deference; work/checkpoint; SOP; phase exit/reflection/summary/confirmation; commit/state.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.master.start` | Begin the framework session using its master preflight. | The active project's framework session needs its installation, state and collaboration rules established. |
| `top.master.transition` | Advance the current phase after reviewing its exit criteria. | I have explicitly decided this phase is ready to end and need the prescribed exit check and decision process. |

## top/bootstrap

Source: [skills/bootstrap/SKILL.md](../../../skills/bootstrap/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Apply all startup guards and offers in order before arguments or all-clear status routing.

Failure obligations: Retired/stale channel, unsupported drift or declined setup prevents unsafe project operations; no generic Configure recursion.

Branch inventory: Every bootstrap source branch; hard/advisory guard; update declines; doctor marker; args vs no args.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.bootstrap.startup` | Initialize the framework's session routing. | A new framework session needs startup guards resolved before handling project work. |

## top/_route

Source: [skills/_route/SKILL.md](../../../skills/_route/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Forward unchanged natural-language intent to find-skill and the correct public category.

Failure obligations: Quoted/negated/unrelated task must not acquire mutation authority; lost context or wrong destination fails.

Branch inventory: Six categories; conflicting signals; missing context; no match; source bounds.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top._route.route` | Handle the supplied natural-language project request. | The session intent router has received the user's actual request and must preserve its meaning. |

## top/find-skill

Source: [skills/find-skill/SKILL.md](../../../skills/find-skill/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Choose one category from dominant intent, or one focused clarification where authority/gates differ; preserve request.

Failure obligations: No mutation while ambiguous, no full library enumeration and no silently changed request.

Branch inventory: Each signal category; overlapping signals; multi-intent; category-owned mutation boundary.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.find-skill.classify` | Classify the current project request and route it. | The internal router has a concrete user goal and must choose its owning public category. |

## top/library-load

Source: [skills/library-load/SKILL.md](../../../skills/library-load/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Read selected category index, choose one matching workflow, read exact unique body and execute its gates.

Failure obligations: Absent/ambiguous identifier, conflicting authority or missing body routes safely through find-skill/clarification; never fake load.

Branch inventory: Category+request; known identifier; unique/zero/multiple match; one index; one workflow; required references only.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `top.library-load.category` | Load the correct workflow for this category and request. | A public category has accepted the user's goal and now needs one specific library workflow. |
| `top.library-load.identifier` | Resolve the caller's known library identifier with its context. | A legitimate internal caller already names a workflow and needs the unique installed body located safely. |

## build/code-feature

Source: [skill-library/build/code-feature/SKILL.md](../../../skill-library/build/code-feature/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Create/reuse dedicated story branch, locate specs or write story/Gherkin, run immutable-test TDD, verify with fresh evidence and record completion.

Failure obligations: Missing process ledger/spec, trunk/dirty conflict, absent failing test or failed verification prevents implementation/completion.

Branch inventory: Story found/absent; existing/new branch; Gherkin found/generated; test red→green; contract and receipt gates.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.code-feature.implement` | Build the approved lending checkout feature. | The checkout design and stories are approved, but staff still cannot lend a book in the application. |

## build/code-issue

Source: [skill-library/build/code-issue/SKILL.md](../../../skill-library/build/code-issue/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Read specified existing GitHub issue and acceptance criteria, branch, implement test-first, review and verify against that issue.

Failure obligations: Missing/invalid issue, inaccessible remote or absent evidence blocks; tracker-management intent must never select this workflow.

Branch inventory: Issue number/URL; current remote; context gaps; branch; regression/feature; completion/PR handoff.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.code-issue.implement` | Implement GitHub issue #42 in the fixture repository. | GitHub #42 describes the accepted overdue-warning bug and the application still has that defect. |

## build/code-review

Source: [skill-library/build/code-review/SKILL.md](../../../skill-library/build/code-review/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Review chosen scope/type with relevant specialists and evidence-qualified findings; preserve source on review-only requests.

Failure obligations: Unknown scope, unavailable reviewer or unsupported claim is disclosed; no unsolicited fixes.

Branch inventory: Code/security/compliance/caucus; diff/PR/path/repo; inline/background as permitted; specialty results; confidence/dedup; failure/empty.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.code-review.code` | Review the current code changes for correctness. | This diff may introduce lending regressions and needs an independent correctness assessment. |
| `build.code-review.security` | Run the code-review security option on this diff. | The code-review menu is open and the authentication changes need its security review path. |
| `build.code-review.compliance` | Run the code-review compliance option on this diff. | The code-review menu is open and we need its compliance-focused assessment of this change. |
| `build.code-review.caucus` | Run a specialty caucus review of the lending changes. | The change crosses architecture, security and performance boundaries and needs the combined specialty review workflow. |

## build/code-tdd

Source: [skill-library/build/code-tdd/SKILL.md](../../../skill-library/build/code-tdd/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Execute selected TDD level through legitimate caller, proving required red/green/refactor sequence with immutable behavioral tests.

Failure obligations: Implementation without red evidence, changing tests to pass or unauthorized mocks is blocked/corrected.

Branch inventory: L0 hotfix; L1 light; L2 standard; L3 Gherkin; mode defaults/override; branch; all languages; test edit attempts.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.code-tdd.level-0` | Use the emergency test discipline offered for this approved hotfix. | The hotfix workflow is at its test-discipline choice and this is the documented emergency path. |
| `build.code-tdd.level-1` | Use the light test-first option for this small change. | The TDD selection is open and this bounded CRUD change needs the light option. |
| `build.code-tdd.level-2` | Use the standard test-first option for this bug fix. | The TDD selection is open and we need the normal regression-first discipline. |
| `build.code-tdd.level-3` | Use the full Gherkin-driven test-first option. | The feature has agreed Gherkin scenarios and the TDD workflow should derive tests from them. |

## build/code-testing

Source: [skill-library/build/code-testing/SKILL.md](../../../skill-library/build/code-testing/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Execute selected tests/mutation/security/PR checks and retain exact commands/results without conflating skipped checks and passes.

Failure obligations: Missing runner/tool, nonzero exit, mutation survivor or failed precheck remains failed/partial.

Branch inventory: Each check singly and combinations; runner detection; mutation tool availability; CI/PR precheck; test failures.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.code-testing.test-suite` | Run the project test suite. | We need current evidence that the lending changes have not broken existing behavior. |
| `build.code-testing.mutation` | Run mutation testing on the lending changes. | The tests pass, but I want to know whether they would catch meaningful mistakes in this code. |
| `build.code-testing.security` | Run the security option from the code-testing checklist. | The code-testing menu is open and its security check still has not been run. |
| `build.code-testing.pr-precheck` | Run the pull-request pre-check. | The code is ready for review, but required pre-submission checks may still be missing. |
| `build.code-testing.combined` | Run the suite, mutation check and PR pre-check together. | All three code-testing selections are needed for this delivery and we need separate results for each. |

## build/code-verify

Source: [skill-library/build/code-verify/SKILL.md](../../../skill-library/build/code-verify/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Run fresh checks appropriate to each claim, create validated subject-specific evidence receipt and record actual outcome.

Failure obligations: Old output, wrong subject, failed command, incomplete check or unverifiable claim prevents passing receipt/completion.

Branch inventory: Tests/build/lint/typecheck/bug fixed/requirements/deploy claims; explicit no change; evidence unavailable; record pass/fail/blocked.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.code-verify.verify` | Verify ISSUE-001 before we call it complete. | The implementation looks finished, but we lack fresh evidence that its promised behavior actually works. |

## build/deploy-ship

Source: [skill-library/build/deploy-ship/SKILL.md](../../../skill-library/build/deploy-ship/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Validate VERIFY, detect deployment config, confirm target/commands, execute approved local fixture deploy, smoke and evidence-backed closeout.

Failure obligations: Missing receipt/config, denied target, deploy failure or failing smoke prevents ship/completion claim and triggers truthful recovery.

Branch inventory: Detected/unknown runtime; execute/guide; checklist; security not run/skipped; smoke success/failure; active plan archive; milestone/sprint/misc path; work history.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.deploy-ship.ship` | Ship the verified lending release to the fixture service. | Verification is complete and approved; the isolated test service still runs the previous release. |
| `build.deploy-ship.guide` | Guide me through deploying the verified lending release without executing deployment commands. | Verification is complete, but I need deployment instructions while I retain control of execution. |

## build/john-wick

Source: [skill-library/build/john-wick/SKILL.md](../../../skill-library/build/john-wick/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Run resumable autonomous SDLC through its six phase documents, maintaining process ledger, contracts, budgets and explicit gates.

Failure obligations: Missing prerequisite, denied gate, failed review/test, interruption or budget exhaustion yields honest checkpoint rather than false completion.

Branch inventory: Fresh/resume; phases 0–6; each substage; gate approve/revise/stop; errors; checkpoint; no background work during stop.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.john-wick.start` | Run the full autonomous John Wick workflow for the approved lending feature. | I want the documented autonomous delivery pipeline to own this feature from its initial definition through verified closeout. |
| `build.john-wick.resume` | Resume the interrupted John Wick workflow. | The autonomous delivery session stopped after its saved checkpoint and the work is still unfinished. |

## build/john-wick-checkin

Source: [skill-library/build/john-wick-checkin/SKILL.md](../../../skill-library/build/john-wick-checkin/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Validate phase exit from caller context, report criterion-level evidence and collect mandatory reflection without taking over implementation.

Failure obligations: Missing context, failed criteria or malformed reviewer output cannot authorize phase exit.

Branch inventory: Each phase input; pass/fail; contradictory artifacts; reflection no changes/specific changes; return to caller.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.john-wick-checkin.checkin` | Assess this phase exit against the frozen criteria. | The autonomous workflow reached a phase boundary and needs its independent check-in before proceeding. |

## build/large-story

Source: [skill-library/build/large-story/SKILL.md](../../../skill-library/build/large-story/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Use its own controller through supported route surfaces, preserve frozen criteria, enforce phases and evidence, and finalize only on controller authority.

Failure obligations: Missing/changed contract, invalid transition, enforcement failure, stale ledger or failed closeout blocks downstream work and completion language.

Branch inventory: Independent controller for large story; route/init/design/plan/probe/implement/verify/ship/finalize/status; contract amendments; canonical/mirror sync; protected writes; branch; restart.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.large-story.start` | Start a large story for the approved lending change. | This lending change needs the documented large-story workflow with enforced phases and evidence before it is called finished. |
| `build.large-story.resume` | Resume the interrupted large story. | Our large-story controller has saved unfinished work and we need to continue from that state. |
| `build.large-story.status` | Show where the current large story is blocked. | The large-story workflow is still in flight and I need its actual controller status. |

## build/orchestrator

Source: [skill-library/build/orchestrator/SKILL.md](../../../skill-library/build/orchestrator/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Validate stored workflow, recover crashes and handle each controller yield with allowed worker dispatch and persisted results.

Failure obligations: Invalid workflow, failed worker, rejected gate, limit or halt never becomes complete; no dispatch while stopped.

Branch inventory: execute_step/gate/failure/escalation/max_iterations/budget_exhausted/complete/halted; stale in-flight result; resume exactly once.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.orchestrator.run` | Execute the accepted tracked workflow. | The orchestrator caller has an approved workflow whose steps now need controlled execution. |
| `build.orchestrator.resume` | Resume the interrupted tracked workflow. | The tracked workflow stopped with an in-flight step and needs crash reconciliation before continuing. |

## build/product-sprint-plan

Source: [skill-library/build/product-sprint-plan/SKILL.md](../../../skill-library/build/product-sprint-plan/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Select stories against capacity/criteria, produce approved sprint commitment and preserve feature state.

Failure obligations: Unavailable dependencies, disallowed mode, unready stories or declined commitment blocks unauthorized sprint activation.

Branch inventory: Active/paused/uninitialized; lightweight/full onboarding; existing imports; pause/offboard; commitment revisions.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.product-sprint-plan.plan` | Plan a sprint from our ready lending stories. | We know the ready stories but have not agreed a realistic sprint commitment. |
| `build.product-sprint-plan.onboard` | Set up the sprint-planning feature. | We need the sprint-planning workflow initialized before selecting work. |
| `build.product-sprint-plan.pause` | Pause the sprint-planning feature. | Keep our planning data, but stop using this feature for now. |
| `build.product-sprint-plan.offboard` | Offboard the sprint-planning feature and preserve its data. | We will plan sprints elsewhere and need the existing information retained. |

## build/product-user-tdd-tests

Source: [skill-library/build/product-user-tdd-tests/SKILL.md](../../../skill-library/build/product-user-tdd-tests/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Convert agreed stories to executable-shaped Gherkin feature files and traceability without implementation.

Failure obligations: Missing/ambiguous acceptance criteria, unsupported story format or failing spec validation is surfaced before test implementation.

Branch inventory: Single/multiple stories; existing feature files; generic vs Gherkin story input; acceptance gaps.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.product-user-tdd-tests.generate` | Generate Gherkin test specifications from the agreed lending stories. | The stories are approved, but we have no scenario files defining observable acceptance behavior yet. |

## build/project-backlog

Source: [skill-library/build/project-backlog/SKILL.md](../../../skill-library/build/project-backlog/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: View/promote/defer/review imported backlog through guarded mode-aware local operations with audit/cache consistency.

Failure obligations: Legacy unsafe state, Shape Up block, invalid sprint/item or rejected inferred detail prevents mutation.

Branch inventory: Full view; promote valid/absent sprint; deferred status; inferred confirm/correct/reject; kanban warning.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.project-backlog.view` | Show the unscheduled issue backlog. | I need to see work that has not been committed to a sprint. |
| `build.project-backlog.promote` | Promote ISSUE-001 into sprint SP-001. | The sprint has room and ISSUE-001 is still sitting outside it. |
| `build.project-backlog.defer` | Defer backlog issue ISSUE-001. | ISSUE-001 should wait rather than remain in the current ready queue. |
| `build.project-backlog.review-inferred` | Review imported issues marked inferred. | Some imported backlog details were guessed and need our confirmation. |

## build/project-backlog-triage

Source: [skill-library/build/project-backlog-triage/SKILL.md](../../../skill-library/build/project-backlog-triage/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Lint current store, walk ungroomed issues oldest-first, apply explicit accept/edit/split/defer/decline decisions and report summary.

Failure obligations: Malformed item, migration risk, rejected recommendation or stop preserves undecided work.

Branch inventory: INVEST recommendations; severity/priority; split children and parent handling; zero/one/multiple; mode;

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.project-backlog-triage.triage` | Groom the issue backlog with me. | The backlog contains old, unclear items that are not ready for delivery decisions. |

## build/project-epics

Source: [skill-library/build/project-epics/SKILL.md](../../../skill-library/build/project-epics/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Redirect to Plan epic management preserving original arguments and announce deprecated internal entry when applicable.

Failure obligations: Do not expose deprecated slash discovery or loop through generic Plan without retained epic intent.

Branch inventory: Every epic operation; args present/empty; historical caller.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.project-epics.redirect` | Continue the existing epic-management request. | A retained workflow has called the deprecated epic helper and its original epic operation must survive the redirect. |

## build/project-gh-import-issues

Source: [skill-library/build/project-gh-import-issues/SKILL.md](../../../skill-library/build/project-gh-import-issues/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Import explicitly requested open GitHub issues into local v4 store with stable mapping and inferred flags, then rebuild cache.

Failure obligations: Missing auth/origin, unsafe legacy store, partial fetch or duplicate mapping prevents blind duplicate import.

Branch inventory: GitHub/local tracker distinction; empty/first/repeat import; mapped/unmapped issues; types/labels; bounded limit and pagination observations.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.project-gh-import-issues.import` | Import open GitHub issues into our local issue store. | We explicitly want local copies of the open remote issues; merely choosing GitHub as the tracker will not do that. |

## build/project-gh-sync-issues

Source: [skill-library/build/project-gh-sync-issues/SKILL.md](../../../skill-library/build/project-gh-sync-issues/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Perform both documented closure passes with receipt/status rules, remote reconciliation and accurate per-item summary.

Failure obligations: Missing auth, unresolved mapping, absent local completion evidence or remote error remains failed/skipped with no guessed success.

Branch inventory: Remote closed→local; local done→remote; already synchronized; conflicts; repeated run; partial pass failure.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.project-gh-sync-issues.sync` | Synchronize issue status between the local store and GitHub. | Some linked issues were closed remotely and others locally; both records now disagree. |

## build/project-issues

Source: [skill-library/build/project-issues/SKILL.md](../../../skill-library/build/project-issues/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Execute requested tracker-specific operation; read back remote mutations or validate local status/files/cache/audit; preserve other system of record.

Failure obligations: Invalid tracker, missing auth/origin, invalid ID, missing label, receipt failure or rejected decision stops without fallback or unauthorized issue changes.

Branch inventory: Tracker unset→local/local/github/invalid; tracker change only key; local and GitHub operations; shape_up pitch source; local closure/reopen origin; local triage; remote existing-label triage.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.project-issues.tracker-github` | Use GitHub for this project's issues. | Our team works entirely in GitHub; keeping a separate local issue system no longer fits. |
| `build.project-issues.tracker-local` | Use local issue tracking again. | We want this project's issue records kept in the repository instead of GitHub. |
| `build.project-issues.list-local` | List our open local issues. | In this locally tracked project I cannot tell which issues remain unresolved. |
| `build.project-issues.backlog-local` | Show local issues not assigned to a sprint. | In this locally tracked project some issues have no sprint and need to be visible together. |
| `build.project-issues.view-local` | Show local issue ISSUE-001. | In this locally tracked project I need the complete details of ISSUE-001. |
| `build.project-issues.new-local` | Create a local issue for duplicate lending records. | In this locally tracked project duplicate lending records need to be captured as a new issue before any fix. |
| `build.project-issues.update-local` | Update the title and priority of local issue ISSUE-001. | In this locally tracked project ISSUE-001 understates the duplicate-record problem and ranks it too low. |
| `build.project-issues.close-local` | Close local ISSUE-001 with its verified completion receipt. | In this locally tracked project the recorded completion evidence for ISSUE-001 is ready and the issue should be finished. |
| `build.project-issues.decline-local` | Decline local issue ISSUE-001 with a reason. | In this locally tracked project we decided not to pursue ISSUE-001 and need that decision recorded. |
| `build.project-issues.triage-local` | Move local ISSUE-001 from backlog into ready roadmap work. | In this locally tracked project ISSUE-001 has been reviewed and is ready for delivery rather than untriaged backlog. |
| `build.project-issues.reopen-local` | Reopen local issue ISSUE-001. | In this locally tracked project the defect in the completed ISSUE-001 has returned. |
| `build.project-issues.list-github` | List our open GitHub issues. | This project uses GitHub and I cannot see which remote issues remain unresolved. |
| `build.project-issues.backlog-github` | Show the GitHub issue backlog. | This project uses GitHub and I need the remote open-issue queue. |
| `build.project-issues.view-github` | Show GitHub issue #42. | This project uses GitHub and I need the complete remote details for #42. |
| `build.project-issues.new-github` | Create a GitHub issue for duplicate lending records. | This GitHub-tracked project needs the duplicate-record problem captured as a new issue before a fix. |
| `build.project-issues.update-github` | Update GitHub issue #42's title and labels. | This GitHub-tracked project has inaccurate wording and classification on #42. |
| `build.project-issues.close-github` | Close GitHub issue #42. | The work on #42 in this GitHub-tracked project is resolved and its remote issue should reflect that. |
| `build.project-issues.decline-github` | Decline GitHub issue #42. | We decided not to pursue #42 in this GitHub-tracked project and need it closed accordingly. |
| `build.project-issues.reopen-github` | Reopen GitHub issue #42. | The defect tracked remotely in #42 has returned after it was closed. |
| `build.project-issues.triage-github` | Apply our existing triage label to GitHub issue #42. | Issue #42 needs to enter the repository's established remote triage queue. |
| `build.project-issues.triage-remove-github` | Remove our triage label from GitHub issue #42. | Issue #42 has completed remote triage and should leave that label's queue. |

## build/project-sprints

Source: [skill-library/build/project-sprints/SKILL.md](../../../skill-library/build/project-sprints/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Manage agile sprint plan/status/activation/board/update/close/retro with proper membership, carryover and cache/audit.

Failure obligations: Disallowed mode, missing/competing active sprint or incomplete closure decisions requires explicit resolution.

Branch inventory: No active/one/multiple; capacity; issue priority; 50% milestone-unassigned boundary; planned→active; unfinished carryover; retro.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.project-sprints.status` | Show the active sprint status. | I need to know where our current iteration stands. |
| `build.project-sprints.list` | List all sprints. | I need the history and future iteration list, not only the active one. |
| `build.project-sprints.new` | Create a new sprint from selected ready issues. | Our next iteration has no plan or selected work yet. |
| `build.project-sprints.start` | Start planned sprint SP-001. | SP-001 is planned and the team is beginning that iteration now. |
| `build.project-sprints.board` | Show the active sprint board. | I need to see each issue's position in the current iteration. |
| `build.project-sprints.update` | Update ISSUE-001 on the active sprint. | The active iteration board has an outdated status for ISSUE-001. |
| `build.project-sprints.close` | Close the active sprint. | The iteration has ended and unfinished work needs an explicit carryover decision. |
| `build.project-sprints.retro` | Run the retrospective for the most recently closed sprint. | The last iteration ended and we have not captured what should change next time. |

## build/project-themes

Source: [skill-library/build/project-themes/SKILL.md](../../../skill-library/build/project-themes/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Manage optional theme grouping, tags and closure without changing issue delivery status.

Failure obligations: Missing theme/issues or rejected tagging/close does not silently modify membership.

Branch inventory: Category grouping; empty/list; view; create; tag batch; close with linked issues.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.project-themes.list` | List our issue themes. | The issue list is hard to understand without its domain groupings. |
| `build.project-themes.view` | Show theme TH-001 and its issues. | I need to see what work belongs to the lending domain grouping. |
| `build.project-themes.new` | Create a Returns theme. | Returns work needs a shared domain label. |
| `build.project-themes.tag` | Tag selected issues with theme TH-001. | These related issues are not connected to their agreed domain grouping. |
| `build.project-themes.close` | Close theme TH-001. | We are retiring this grouping and need its theme record closed without pretending its issues are done. |

## build/small-story

Source: [skill-library/build/small-story/SKILL.md](../../../skill-library/build/small-story/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Use its own controller through supported route surfaces, preserve frozen criteria, enforce phases and evidence, and finalize only on controller authority.

Failure obligations: Missing/changed contract, invalid transition, enforcement failure, stale ledger or failed closeout blocks downstream work and completion language.

Branch inventory: Independent controller for small story; route/init/design/plan/probe/implement/verify/ship/finalize/status; contract amendments; canonical/mirror sync; protected writes; branch; restart.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.small-story.start` | Start a small story for the approved lending change. | This lending change needs the documented small-story workflow with enforced phases and evidence before it is called finished. |
| `build.small-story.resume` | Resume the interrupted small story. | Our small-story controller has saved unfinished work and we need to continue from that state. |
| `build.small-story.status` | Show where the current small story is blocked. | The small-story workflow is still in flight and I need its actual controller status. |

## build/testing-accessibility

Source: [skill-library/build/testing-accessibility/SKILL.md](../../../skill-library/build/testing-accessibility/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Run scoped WCAG audit with actual automated/manual evidence, save report and create only authorized findings.

Failure obligations: Unavailable browser/scanner/screen reader, unknown target or failed check remains unverified/failed rather than accessible.

Branch inventory: Automated/keyboard/screen-reader/visual/cognitive; tool absent; findings and filing consent; report list/view.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.testing-accessibility.audit` | Audit the lending interface for accessibility. | Staff using keyboards or assistive technology may be unable to complete lending tasks. |
| `build.testing-accessibility.list` | List prior accessibility audits. | I need to know which accessibility assessments have already been performed. |
| `build.testing-accessibility.view` | Show accessibility audit A11Y-001. | I need the detailed evidence from our first accessibility assessment. |
| `build.testing-accessibility.findings` | Show open accessibility findings. | I cannot tell which known accessibility problems are still unresolved. |

## build/testing-compliance

Source: [skill-library/build/testing-compliance/SKILL.md](../../../skill-library/build/testing-compliance/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Track selected standard/control assessments and evidence with honest gap report; no certification claim.

Failure obligations: Unsupported standard/control, missing or stale evidence, unavailable source or rejected assessment is explicit.

Branch inventory: SOC2/HIPAA/GDPR catalogs; discovery security context; coverage none/partial/full; control across standards; evidence paths.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.testing-compliance.status` | Show our compliance tracking status. | We need to understand which tracked controls have evidence and which remain gaps. |
| `build.testing-compliance.init` | Initialize GDPR control tracking. | We need a dedicated tracked set of GDPR controls before assessing evidence. |
| `build.testing-compliance.assess` | Assess our tracked HIPAA controls for gaps. | HIPAA controls are initialized, but we do not know which requirements lack evidence. |
| `build.testing-compliance.log` | Record the supplied evidence for control CC6.1. | The access-control check has evidence that is not linked to its tracked control yet. |
| `build.testing-compliance.report` | Generate the compliance gap report. | We need a current consolidated account of missing or inadequate control evidence. |

## build/testing-performance

Source: [skill-library/build/testing-performance/SKILL.md](../../../skill-library/build/testing-performance/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Define scenarios, record independently measured baselines/results, compare thresholds and preserve benchmark history.

Failure obligations: Missing/invalid metric, incomparable environment, unknown scenario or absent baseline cannot be fabricated into pass.

Branch inventory: Status/scenarios; baseline first/replace; result; above/equal/below each threshold; comparison regression/improvement; units.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.testing-performance.status` | Show performance baselines and recent results. | I cannot tell what performance we currently expect or what was measured most recently. |
| `build.testing-performance.scenario-new` | Define a load scenario for 100 simultaneous lending checkouts. | We need a repeatable workload representing the busy-store rush. |
| `build.testing-performance.scenario-list` | List our load scenarios. | I need to see which repeatable performance workloads already exist. |
| `build.testing-performance.baseline` | Record this measured checkout result as the baseline. | The first controlled benchmark has run and needs to become the reference for later comparisons. |
| `build.testing-performance.benchmark` | Record this new checkout benchmark result. | We reran the workload after the change and need the actual result stored for comparison. |
| `build.testing-performance.compare` | Compare the latest benchmark against the baseline. | We changed the lending code and need to know whether its measured performance regressed. |
| `build.testing-performance.threshold` | Set the agreed latency threshold for the checkout scenario. | We have measurements but no explicit pass/fail performance boundary for checkout. |

## build/testing-plan

Source: [skill-library/build/testing-plan/SKILL.md](../../../skill-library/build/testing-plan/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: List/view/create/update scoped strategy with ownership, environments and binary entry/exit criteria.

Failure obligations: Unknown plan, ambiguous scope or unsupported test claim requires correction; no automatic test execution.

Branch inventory: New/update; types and out-of-scope; missing context; revision.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.testing-plan.list` | List our test plans. | I cannot see which verification strategies are already defined. |
| `build.testing-plan.view` | Show test plan TP-001. | I need the agreed scope and exit criteria for this verification effort. |
| `build.testing-plan.new` | Create a test strategy for the lending release. | The release has requirements but no agreed plan for proving they work. |
| `build.testing-plan.update` | Update test plan TP-001 to include returns. | The test strategy still omits a workflow now included in the release. |

## build/testing-security

Source: [skill-library/build/testing-security/SKILL.md](../../../skill-library/build/testing-security/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Run scoped threat model/OWASP/dependency review, preserve evidence, save report and offer finding work.

Failure obligations: Missing target/audit tool or incomplete evidence stays unverified; no unsupported security assurance.

Branch inventory: STRIDE categories; OWASP; language-specific audits; findings filing; list/view/open findings.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.testing-security.review` | Perform a structured security review and threat model for the lending service. | We need a standalone threat assessment of the service, not just a code-diff review. |
| `build.testing-security.list` | List prior security review reports. | I need to know what security assessments have already been recorded. |
| `build.testing-security.view` | Show security review SR-001. | I need the threat and evidence details from the first security assessment. |
| `build.testing-security.findings` | Show open security findings. | Known security concerns may still be unresolved and I need the current list. |

## build/testing-session

Source: [skill-library/build/testing-session/SKILL.md](../../../skill-library/build/testing-session/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Run scripted/exploratory manual QA, persist case outcomes/bugs/notes, resume and close truthfully.

Failure obligations: Missing plan, invalid session, unsupported target or interrupted case remains untested/blocked; no manufactured test result.

Branch inventory: Scripted/exploratory; charter; pass/fail/blocked/skip; bug filing yes/no; resume open/closed/missing; session close.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `build.testing-session.new` | Start a manual QA session for lending returns. | We need to try the returns workflow systematically and record what happens. |
| `build.testing-session.resume` | Resume QA session QA-001. | The manual testing session stopped midway and several cases still lack outcomes. |
| `build.testing-session.list` | List past QA sessions. | I need to see which manual verification sessions have already happened. |
| `build.testing-session.view` | Show QA session QA-001. | I need the case results and bugs from the first manual testing session. |

## configure/_features

Source: [skill-library/configure/_features/SKILL.md](../../../skill-library/configure/_features/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Display actual optional feature state, collect enable/disable/defer choices, merge decisions and onboard only newly enabled features.

Failure obligations: Malformed state/config or declined choice preserves existing settings; metrics ground truth is not inferred from stale YAML.

Branch inventory: Every feature; active/declined/deferred/unoffered; metrics config; onboarding dependencies; defer expiry.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure._features.manage` | Choose which optional SweetClaude features are enabled. | SweetClaude has optional features and I do not know which ones are currently active or worth enabling. |

## configure/_health

Source: [skill-library/configure/_health/SKILL.md](../../../skill-library/configure/_health/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Run consistency/version/storage checks and return caller disposition without claiming repair or migration.

Failure obligations: Check failure, missing script or inconsistent product base is reported; no fabricated healthy result.

Branch inventory: No drift/drift/error; product-base divergence; v4 storage lint; version check failure.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure._health.check` | Run the framework health check requested by session startup. | Startup has stale health data and needs its internal consistency check before continuing. |

## configure/_migrate

Source: [skill-library/configure/_migrate/SKILL.md](../../../skill-library/configure/_migrate/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Create verified snapshot, run registered schema chain, handle failures/menu and accept/rollback/defer report; consolidate legacy state when specified.

Failure obligations: Missing/broken handler, out-of-support chain or failed snapshot blocks migration; refusal/defer must preserve correct pending state.

Branch inventory: Detect state; no-op; recoverable retry/skip; chain broken; other failure; accept/rollback/defer; phase+skills consolidation.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure._migrate.migrate` | Upgrade the SweetClaude state schema through the registered migration chain. | Startup found supported state-file drift and the project's files need the registry-driven schema upgrade. |

## configure/behavioral-regression

Source: [skill-library/configure/behavioral-regression/SKILL.md](../../../skill-library/configure/behavioral-regression/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Run all 16 interaction contracts against an actual model, score with evidence and record actual failures.

Failure obligations: Unavailable model, invalid judge output, missing evidence or skipped contract cannot be reported as passing.

Branch inventory: CONTRACT-01 through CONTRACT-16 individually; PASS/FAIL/NA; model versions; failure recording policy; transcript rubric.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.behavioral-regression.run` | Run SweetClaude's interaction behavioral regression checks. | I am concerned that SweetClaude has stopped respecting its conversation and approval promises. |

## configure/claude-config-audit

Source: [skill-library/configure/claude-config-audit/SKILL.md](../../../skill-library/configure/claude-config-audit/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Redirect original diagnostic intent to Configure→Doctor without recursion or lost scope.

Failure obligations: Retired slash surface must stay undiscoverable; ambiguous generic Configure cannot perform a different operation.

Branch inventory: Original args empty/present; retained caller; doctor destination readable; redirect termination.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.claude-config-audit.redirect` | Continue the retained claude-config-audit diagnostic request. | An older internal caller has requested claude-config-audit and needs the current Doctor workflow with its original diagnostic intent preserved. |

## configure/doctor

Source: [skill-library/configure/doctor/SKILL.md](../../../skill-library/configure/doctor/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Scan read-only, choose maintenance route/menu, offer safety branch, archive, execute approved recipes, rescan, persist and report reversible actual outcomes.

Failure obligations: Retired/stale plugin, unsupported recipe, missing snapshot, failed mutation/restore or skipped fix cannot become healthy/repaired.

Branch inventory: All 15 current scan categories; maintenance statuses; terminal fallback; explain/dry/proceed/no fixes; stored choice/interactive; safety branch; auto/prompted/batch; suppress; restore.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.doctor.scan` | Diagnose this SweetClaude installation without repairing it yet. | SweetClaude behaves inconsistently and I need to understand its configuration problems before changing anything. |
| `configure.doctor.verbose` | Show a detailed Doctor diagnosis. | The summary does not contain enough detail to evaluate the reported framework problems. |
| `configure.doctor.explain` | Explain the Doctor fixes before applying them. | Doctor found several problems, but I do not yet understand the consequences of its proposed changes. |
| `configure.doctor.dry-run` | Preview the Doctor fixes without applying them. | I need to see exactly what Doctor would change before deciding. |
| `configure.doctor.repair` | Apply the approved Doctor fixes. | The diagnosis and proposed repairs have been reviewed and the selected framework fixes are approved. |
| `configure.doctor.restore-all` | Undo all changes from the specified prior Doctor run. | The last Doctor repair made things worse and we need its archived before-images restored. |
| `configure.doctor.restore-file` | Restore only the selected file from the prior Doctor archive. | One file changed by Doctor needs to go back, while its other repairs should remain. |
| `configure.doctor.suppress` | Suppress the selected accepted Doctor finding. | We understand this particular framework warning and deliberately accept it for this project. |
| `configure.doctor.unsuppress` | Remove the suppression for the selected Doctor finding. | We want Doctor to report the previously accepted condition again. |
| `configure.doctor.graduate` | Graduate this eligible project from compatibility mode through Doctor. | The guard says the project meets current layout requirements and only the compatibility lock remains. |
| `configure.doctor.fix-graduation` | Resolve the listed graduation blockers through Doctor. | The project is nearly eligible to leave compatibility mode, but specific fixable blockers remain. |
| `configure.doctor.re-onboard` | Re-onboard SweetClaude from the broken state using the safe archive flow. | Normal repairs cannot resolve this project's framework state and we need a fresh setup with the old data preserved. |

## configure/feature-setup

Source: [skill-library/configure/feature-setup/SKILL.md](../../../skill-library/configure/feature-setup/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Locate development repo, sync approved disposable installations, verify structure and rebuild project cache.

Failure obligations: Missing repo, rejected sync gate, test failure or wrong destination prevents deployment success claim.

Branch inventory: Repo lookup choices; dry run; multiple installs; safety backup; tests; structure/cache failure; selected hash.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.feature-setup.sync` | Deploy this local SweetClaude checkout to the disposable installed locations. | The fixture installations still use the older plugin files and need the development sync workflow. |

## configure/fix-sweetclaude

Source: [skill-library/configure/fix-sweetclaude/SKILL.md](../../../skill-library/configure/fix-sweetclaude/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Redirect original diagnostic intent to Configure→Doctor without recursion or lost scope.

Failure obligations: Retired slash surface must stay undiscoverable; ambiguous generic Configure cannot perform a different operation.

Branch inventory: Original args empty/present; retained caller; doctor destination readable; redirect termination.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.fix-sweetclaude.redirect` | Continue the retained fix-sweetclaude diagnostic request. | An older internal caller has requested fix-sweetclaude and needs the current Doctor workflow with its original diagnostic intent preserved. |

## configure/guardian-off

Source: [skill-library/configure/guardian-off/SKILL.md](../../../skill-library/configure/guardian-off/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Disable session Protocol Guardian only, retaining framework/project data and respecting deterministic gates that remain active.

Failure obligations: Missing session/config or failed flag update is reported; no claim that all hooks/framework are disabled.

Branch inventory: Already off/on; session scope; new session; large/small controller gates remain independently checked.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.guardian-off.disable` | Turn off the Protocol Guardian for this session. | I want the session guardian paused while keeping SweetClaude and the project data active. |

## configure/guardian-on

Source: [skill-library/configure/guardian-on/SKILL.md](../../../skill-library/configure/guardian-on/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Enable guardian for current session and establish its specified checks/context without resetting project work.

Failure obligations: Missing setup/helper or rejected activation does not fabricate active enforcement.

Branch inventory: Already on/off; missing features; retrospective violation check; actual blocked tool attempt.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.guardian-on.enable` | Enable the Protocol Guardian for this session. | SweetClaude keeps skipping required process steps and I want its session enforcement active. |

## configure/hibernate

Source: [skill-library/configure/hibernate/SKILL.md](../../../skill-library/configure/hibernate/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Preserve and restore framework context alongside hibernate/unhibernate behavior with no loss of active work.

Failure obligations: Unavailable base hibernation capability or partial state save/restore is disclosed without false completion.

Branch inventory: Hibernate/unhibernate; context summary; saved SweetClaude state; missing checkpoint; external integration absent.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.hibernate.hibernate` | Hibernate this SweetClaude-managed project. | We are setting the project aside and need its current working context safely preserved. |
| `configure.hibernate.unhibernate` | Unhibernate this SweetClaude-managed project. | We are returning to the project after putting it aside and need its saved context restored. |

## configure/hook-repair

Source: [skill-library/configure/hook-repair/SKILL.md](../../../skill-library/configure/hook-repair/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Redirect original diagnostic intent to Configure→Doctor without recursion or lost scope.

Failure obligations: Retired slash surface must stay undiscoverable; ambiguous generic Configure cannot perform a different operation.

Branch inventory: Original args empty/present; retained caller; doctor destination readable; redirect termination.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.hook-repair.redirect` | Continue the retained hook-repair diagnostic request. | An older internal caller has requested hook-repair and needs the current Doctor workflow with its original diagnostic intent preserved. |

## configure/init

Source: [skill-library/configure/init/SKILL.md](../../../skill-library/configure/init/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Detect none/legacy/partial/damaged/configured after functional-install guard and dispatch exactly to owning workflow.

Failure obligations: Broken install, declined activation or unparseable state prevents blind new-state replacement.

Branch inventory: Disabled activate/decline; plugin functional/nonfunctional; none→setup; legacy→migration; partial→setup; damaged→doctor/recovery; configured health/features.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.init.initialize` | Initialize SweetClaude for this project. | This project needs SweetClaude brought into a usable state, but I do not know whether it needs setup, migration or repair. |

## configure/migrate

Source: [skill-library/configure/migrate/SKILL.md](../../../skill-library/configure/migrate/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Select correct flat-BL or typed taxonomy migrator, preview approved plan, snapshot, execute, verify references/counts and finalize safely.

Failure obligations: Unsafe guard, lock/collision/orphan, failed backup/validation/verification or rejected preview prevents destructive finalization.

Branch inventory: Flat vs typed; source parse tiers; duplicate resolution; completed include/archive; orphan decisions; reference rewriting; dry-run; rollback; external bases; retention.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.migrate.flat` | Migrate our flat BL backlog to current ISSUE format. | This project still has a flat set of BL-numbered work items and current views do not recognize them. |
| `configure.migrate.typed` | Migrate our typed legacy stories, bugs and debt to ISSUE format. | The backlog still uses separate stories, bugs and debt folders with older ID families. |
| `configure.migrate.rollback` | Roll back the failed taxonomy migration using its verified snapshot. | The migration stopped after partial conversion and the preserved snapshot is needed to restore the original layout. |

## configure/migrate-diagnose

Source: [skill-library/configure/migrate-diagnose/SKILL.md](../../../skill-library/configure/migrate-diagnose/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Redirect original diagnostic intent to Configure→Doctor without recursion or lost scope.

Failure obligations: Retired slash surface must stay undiscoverable; ambiguous generic Configure cannot perform a different operation.

Branch inventory: Original args empty/present; retained caller; doctor destination readable; redirect termination.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.migrate-diagnose.redirect` | Continue the retained migrate-diagnose diagnostic request. | An older internal caller has requested migrate-diagnose and needs the current Doctor workflow with its original diagnostic intent preserved. |

## configure/off

Source: [skill-library/configure/off/SKILL.md](../../../skill-library/configure/off/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Create project-disabled marker, preserve data, confirm inactive behavior in subsequent session.

Failure obligations: Unconfigured/already-disabled state or write failure cannot falsely report active deactivation effects.

Branch inventory: State absent/active/disabled; repeated operation; reactivation handoff; no deletion; global rule leakage.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.off.deactivate` | Deactivate SweetClaude for this project. | Keep our framework data, but I want SweetClaude to stay out of this project from now on. |

## configure/project-assess-shape

Source: [skill-library/configure/project-assess-shape/SKILL.md](../../../skill-library/configure/project-assess-shape/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Interview one question at a time and recommend Flow/Kanban/Shape Up/Agile; accepted recommendation writes project.mode and compiles gates; skip explicitly sets Flow.

Failure obligations: Incomplete/conflicting answers do not silently select or shift a mode.

Branch inventory: All four recommendations; ordered five-question logic; yes writes/compiles, no alternatives, tell-me-more; skip→Flow; advice-only request grants no shift authority.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.project-assess-shape.recommend` | Help me choose a SweetClaude project mode. | I do not know how much process this team needs or which operating style fits our work. |
| `configure.project-assess-shape.skip` | Skip the project-mode assessment for now. | I do not want to answer the mode interview yet; use its documented skip behavior. |

## configure/project-mode

Source: [skill-library/configure/project-mode/SKILL.md](../../../skill-library/configure/project-mode/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Assess, shift with snapshot and confirmed cascade, compile gates, preserve history and explicit user intent.

Failure obligations: Invalid mode, unmet upshift prerequisites, declined cleanup or partial write must not claim completed shift.

Branch inventory: All 12 directed transitions; same/unset mode; upshift generation; downshift archive cleanup; shape_up solo bet/cycle duration; effective-gates regenerate.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.project-mode.assess` | Assess whether our current SweetClaude mode still fits. | Our team has changed and the current process may no longer suit how we work. |
| `configure.project-mode.shift-flow` | Shift SweetClaude to Flow mode. | We want minimal conversational structure and have chosen Flow as the project's new mode. |
| `configure.project-mode.shift-kanban` | Shift SweetClaude to Kanban mode. | We want continuous delivery with explicit work-in-progress limits. |
| `configure.project-mode.shift-shape-up` | Shift SweetClaude to Shape Up mode. | We have chosen pitch-driven bounded cycles rather than maintaining a normal backlog. |
| `configure.project-mode.shift-agile` | Shift SweetClaude to Agile mode. | We have chosen sprint-based iterations with structured planning and verification. |
| `configure.project-mode.history` | Show SweetClaude mode history and snapshots. | I need to know when our operating process changed and what can be restored. |
| `configure.project-mode.betting` | Run the solo betting-table decision for the current pitch. | The Shape Up pitch is ready but implementation is waiting for the explicit bet decision. |
| `configure.project-mode.cycle` | Set the Shape Up cycle duration. | Our Shape Up cycle length needs an explicit project-level choice. |

## configure/purge

Source: [skill-library/configure/purge/SKILL.md](../../../skill-library/configure/purge/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Show exact artifact inventory, recommend safety branch and delete only owned paths after required typed confirmation.

Failure obligations: No artifacts, wrong/cancelled confirmation, unowned path or failed deletion preserves/report exact residual state; no false purge.

Branch inventory: No state; default/relocated artifact roots; branch accept/decline; exact phrase; path safety; partial deletion; README/CLAUDE integration cleanup.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.purge.purge` | Remove all SweetClaude artifacts from this fixture project. | We are leaving SweetClaude entirely and want its project artifacts removed through the documented confirmation flow. |

## configure/recover

Source: [skill-library/configure/recover/SKILL.md](../../../skill-library/configure/recover/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Locate helper, diagnose, plan, verify snapshot, get approval, execute owned recovery and report resumable/rollback state.

Failure obligations: Missing helper, invalid diagnosis/JSON, no recovery needed, blockers, snapshot failure or refusal stops before execution.

Branch inventory: No recovery/plan possible/blocked; stabilize without migration; plan execute/stop; resume/rollback provided run directory; failure checkpoint.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.recover.diagnose` | Diagnose and plan safe recovery for the broken SweetClaude state. | A previous update or repair left the framework inconsistent and we need a recovery plan before touching it again. |
| `configure.recover.execute` | Execute the reviewed snapshot-backed SweetClaude recovery plan. | The recovery plan and verified snapshot are ready and the specific recovery execution is approved. |
| `configure.recover.resume` | Resume recovery from the specified interrupted run directory. | The recovery process stopped after recording progress and needs to continue from its durable run state. |
| `configure.recover.rollback` | Roll back the specified SweetClaude recovery run. | We need to restore the recovery run's preserved pre-change state instead of continuing it. |

## configure/retro

Source: [skill-library/configure/retro/SKILL.md](../../../skill-library/configure/retro/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Read/group improvement register, confirm keep/edit/remove learnings, write checkpoint summary and retain auditability.

Failure obligations: Empty/malformed register or rejected edit prevents invented lessons or unwanted deletion.

Branch inventory: No entries; duplicates/themes; keep/edit/remove; confirmation; checkpoint.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.retro.review` | Review and clean up SweetClaude's improvement register. | The recorded process lessons may contain duplicates or outdated guidance and need a deliberate review. |

## configure/setup

Source: [skill-library/configure/setup/SKILL.md](../../../skill-library/configure/setup/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Detect new/organized/inherited, interview sequentially, preserve settings and code, set canonical state/privacy/trees/traceability/plans/cache/session and route to mode.

Failure obligations: Declined setup, unavailable tracker or failed write leaves truthful partial state; no overwrite of unrelated settings/data.

Branch inventory: A new/B existing/C messy; code/history heuristics; stage mapping; local/GitHub choice; default private product base; settings both files; repeated partial setup.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.setup.new` | Set up SweetClaude for this new empty project. | This directory has no code or project history yet and needs its first SweetClaude setup. |
| `configure.setup.existing` | Set up SweetClaude for this organized existing codebase. | The application already works and has tests; we want SweetClaude added without disturbing it. |
| `configure.setup.inherited` | Set up SweetClaude for this messy inherited codebase. | We inherited a mixed codebase with many TODOs and no reliable tests, and need a safe starting workflow. |

## configure/sweetclaude-behavioral-regression

Source: [skill-library/configure/sweetclaude-behavioral-regression/SKILL.md](../../../skill-library/configure/sweetclaude-behavioral-regression/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Validate four-mode config, compiled gates, artifact schemas, WIP and manual enforcement paths with explicit per-layer report.

Failure obligations: Failed/omitted/manual-unexecuted check remains failed/not-run; no all-green summary from config parsing alone.

Branch inventory: Automated layers; each MODE_CHECK; each mode implementation gate; WIP boundary; report.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.sweetclaude-behavioral-regression.run` | Run the four-mode enforcement regression workflow. | I want to know whether Flow, Kanban, Shape Up and Agile actually enforce their documented differences. |

## configure/update

Source: [skill-library/configure/update/SKILL.md](../../../skill-library/configure/update/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Run channel/preflight/check/safety/major gate/sync/metadata/project-check/cleanup and surface supported capabilities; preserve project-state separation.

Failure obligations: Retired/stale install, fetch failure, unsafe removed skill, denied major update or failed sync/metadata prevents false success; recover if partial.

Branch inventory: Already current; branch/tag source; removed skills; major accept/decline; stable/prerelease; install copy lookup; sync backup; no inline taxonomy migration; capability offer choices.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.update.update` | Update SweetClaude to its latest supported version. | The installed framework may be behind and needs its documented safe update process. |
| `configure.update.check` | Check whether SweetClaude has an update without installing it. | I only want to know whether a supported newer framework version exists right now. |

## configure/usage

Source: [skill-library/configure/usage/SKILL.md](../../../skill-library/configure/usage/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Toggle local metrics, show outcome-qualified dashboard/insights, or archive/reset only approved metric data.

Failure obligations: Malformed/missing metrics, denied reset or write failure cannot claim tracking/reset succeeded; no duplicate or invented success events.

Branch inventory: on/off/already state; show/dashboard alias; outcomes; empty/partial events; reset/archive; eight declared event types and failure outcomes.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.usage.on` | Enable SweetClaude usage tracking. | We want local records of which framework workflows are used and how they turn out. |
| `configure.usage.off` | Disable SweetClaude usage tracking. | Stop collecting local usage events while keeping the framework itself active. |
| `configure.usage.show` | Show SweetClaude usage and outcomes. | I need to see actual workflow activity and outcomes, including blocked or failed work. |
| `configure.usage.reset` | Archive and reset SweetClaude usage events. | The current metrics should be preserved as an archive while a fresh collection period begins. |

## configure/work-item-artifacts

Source: [skill-library/configure/work-item-artifacts/SKILL.md](../../../skill-library/configure/work-item-artifacts/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Onboard and backfill per-item work directories with confirmed moves/manifests; create or inspect individual paths without loss.

Failure obligations: Collision, invalid ID, failed backfill or declined migration preserves source data and correct feature state.

Branch inventory: First explanation/backfill none/some; full/manual/single; existing dirs; co-located contract/report resolution; status.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `configure.work-item-artifacts.onboard` | Enable per-work-item artifact directories. | Artifacts are scattered across the project and we want each story, epic and milestone to have a predictable home. |
| `configure.work-item-artifacts.backfill` | Backfill existing work-item artifacts into their per-item directories. | The feature is enabled, but older work still has artifacts in the legacy locations. |
| `configure.work-item-artifacts.single` | Backfill artifacts for ISSUE-001 only. | Only ISSUE-001 needs its older artifacts moved into its own work directory now. |
| `configure.work-item-artifacts.status` | Show the status of per-work-item artifact storage. | I need to know which work items have complete artifact directories and which still need backfill. |

## design/design-api-design

Source: [skill-library/design/design-api-design/SKILL.md](../../../skill-library/design/design-api-design/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Produce endpoint contracts, auth/errors/versioning and saved API artifact at resolved technical path.

Failure obligations: Missing requirements or privacy manifest requires clarification/stop; no implementation or invented auth contract.

Branch inventory: Existing/new API; per-endpoint request/response/errors; pagination/auth/versioning; partial context.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.design-api-design.design` | Design the lending inventory API contracts. | The client and service teams disagree on requests, responses and errors for lending operations. |

## design/design-architecture

Source: [skill-library/design/design-architecture/SKILL.md](../../../skill-library/design/design-architecture/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Interview, analyze boundaries/risks, review decisions and ADRs, save architecture and state after approval.

Failure obligations: Unknown constraints or rejected decisions remain unresolved; no premature code or missing artifact path fallback.

Branch inventory: Context present/degraded; alternatives/tradeoffs; decision list approve/revise; component boundaries; existing ADR reuse.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.design-architecture.design` | Design the architecture for lending inventory. | We know what the product must do, but not how to divide responsibilities and data flow safely. |

## design/design-change-impact-analysis

Source: [skill-library/design/design-change-impact-analysis/SKILL.md](../../../skill-library/design/design-change-impact-analysis/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Trace affected code/tests/docs/API/specs and save a ripple map without implementing the change.

Failure obligations: Unknown target or incomplete dependencies are marked uncertain; no unjustified complete impact claim.

Branch inventory: Code vs document/spec; known/unknown consumers; narrow/broad change; missing target.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.design-change-impact-analysis.code` | Analyze the impact of changing the lending record schema. | A lending schema change may break callers and tests that are not obvious from the model file. |
| `design.design-change-impact-analysis.document` | Analyze the impact of changing our return-policy specification. | We changed a documented behavior and do not know which requirements and implementation assumptions depend on it. |

## design/design-data-model

Source: [skill-library/design/design-data-model/SKILL.md](../../../skill-library/design/design-data-model/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Define entities, relationships, constraints/indexes and migration strategy in approved data artifact.

Failure obligations: Missing privacy or inconsistent requirement prevents blind schema choice; no live schema changes.

Branch inventory: New/existing schema; cardinality; constraints; migration/backfill/rollback design.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.design-data-model.design` | Design the data model for lending inventory. | We cannot yet represent who borrowed which copy, its due date and a completed return consistently. |

## design/design-manage-decisions

Source: [skill-library/design/design-manage-decisions/SKILL.md](../../../skill-library/design/design-manage-decisions/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Record options/context/rationale/consequences with stable DEC ID; query relevant existing decisions.

Failure obligations: Duplicate/conflicting decision or absent query target is surfaced; preserve earlier decision history.

Branch inventory: Record/query; next-ID allocation; alternatives; superseding rationale.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.design-manage-decisions.record` | Record our decision to keep lending records in PostgreSQL. | We agreed on PostgreSQL but the reasons and rejected alternatives are still only in chat. |
| `design.design-manage-decisions.query` | Show the design decisions about lending record storage. | I cannot remember why we chose the current storage approach. |

## design/design-solutioning-gate

Source: [skill-library/design/design-solutioning-gate/SKILL.md](../../../skill-library/design/design-solutioning-gate/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Run prescribed solution validation using project context; return explicit gaps and gate result.

Failure obligations: Missing artifacts, unavailable delegated capability or failed validation cannot be called approved.

Branch inventory: Complete/incomplete solution; delegated execution available/unavailable; gate pass/fail.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.design-solutioning-gate.validate` | Validate the proposed lending solution before implementation. | We have a design, but I am concerned it misses a requirement or creates a serious integration risk. |

## design/design-tech-spec

Source: [skill-library/design/design-tech-spec/SKILL.md](../../../skill-library/design/design-tech-spec/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Resolve and document repository, development, environment, CI, hosting, auth, monitoring and scaling decisions.

Failure obligations: Unknown deployment/security constraints stay open; no infrastructure creation or code implementation.

Branch inventory: Every interview topic; existing decisions reused; outline review; audience/NDA; revision; saved state.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.design-tech-spec.write` | Write the technical specification for our approved lending design. | The architecture exists, but an implementer still has to guess about environments, CI, authentication and operations. |

## design/design-user-flows

Source: [skill-library/design/design-user-flows/SKILL.md](../../../skill-library/design/design-user-flows/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Choose persona/story scope, produce normal/alternate/error interface flows and save flow state.

Failure obligations: Missing stories/personas is disclosed and resolved; no unsupported assumed workflow.

Branch inventory: All/SLC/MVP/custom scope; existing vs absent personas/stories; scope revision.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.design-user-flows.design` | Turn the lending user stories into user flows. | The stories say what staff need to do, but the sequence of screens and decisions is unclear. |

## design/design-ux

Source: [skill-library/design/design-ux/SKILL.md](../../../skill-library/design/design-ux/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Gather inspiration and interview requirements, write visual/interaction spec and handoff guidance.

Failure obligations: Missing constraints or rejected direction needs iteration; no unapproved implementation.

Branch inventory: First-message inspiration; inspiration declined; design interview topics; existing flows; handoff choice.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.design-ux.design` | Design the visual and interaction experience for lending inventory. | We have workflows but no consistent visual direction or interaction rules for staff using the product all day. |

## design/design-ux-review

Source: [skill-library/design/design-ux-review/SKILL.md](../../../skill-library/design/design-ux-review/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Review selected wireframes/mockup/description with selected personas; validate respondents and label synthetic findings.

Failure obligations: Missing target/personas, invalid response or exhausted retry is explicit; no invented user validation.

Branch inventory: Target selection; all/custom personas; respondent JSON valid/invalid; retry; consensus/divergence; quantitative task completion; findings follow-up consent.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.design-ux-review.review` | Run a synthetic persona UX review of the lending mockup. | The mockup looks plausible, but I want to understand where our defined user types might fail to complete their tasks. |

## design/design-wireframes

Source: [skill-library/design/design-wireframes/SKILL.md](../../../skill-library/design/design-wireframes/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Generate self-contained scoped HTML/CSS wireframes consistent with flow and UX; review/iterate and save state.

Failure obligations: Missing flows/privacy or broken assets is surfaced; no premature production implementation.

Branch inventory: All/SLC/MVP/custom; UX style present/absent; annotation optional; file collisions; review/iteration.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.design-wireframes.generate` | Create wireframes for the agreed lending user flows. | We know the steps staff need to take but cannot yet see the screen layouts. |

## design/mockup-extract

Source: [skill-library/design/mockup-extract/SKILL.md](../../../skill-library/design/mockup-extract/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Trace real component imports/aliases/tokens into Current baseline; typecheck and register accurate source provenance.

Failure obligations: Missing sandbox/component, unresolved import or type error prevents baseline success claim.

Branch inventory: Sandbox absent/present; component ambiguous; alias variants; token/font sync; external imports; registry new/existing.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.mockup-extract.extract` | Extract the existing LendingTable component into the mockup sandbox. | We want to redesign LendingTable, but the sandbox needs an accurate copy of what production currently does first. |

## design/mockup-graduate

Source: [skill-library/design/mockup-graduate/SKILL.md](../../../skill-library/design/mockup-graduate/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Transform approved mockup into main-app conventions, update routing and acceptance criteria, record state and offer cleanup.

Failure obligations: Unapproved target, missing dependency, rejected transformation or failed build blocks graduation claim.

Branch inventory: Approved target selection; package managers; deps present/missing; routing needed/none; normal/loading/error/empty/interaction criteria; cleanup keep/delete.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.mockup-graduate.graduate` | Move the approved lending mockup into the application. | The lending screen design is approved in the sandbox and the real app still has the old experience. |

## design/mockup-sandbox

Source: [skill-library/design/mockup-sandbox/SKILL.md](../../../skill-library/design/mockup-sandbox/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Create/reuse isolated sandbox, gather context, iterate preview and register explicit approval without altering main app.

Failure obligations: Missing tool/dependency, failed preview or rejected mockup remains partial/unapproved.

Branch inventory: First setup/reuse; new screen/existing redesign; context present/absent; before-after; iteration; approve/revise/stop.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.mockup-sandbox.create` | Create an interactive mockup for the lending checkout screen. | Staff cannot react meaningfully to a written checkout design; we need something they can try separately from the application. |
| `design.mockup-sandbox.iterate` | Revise the checkout mockup to show overdue warnings. | The current sandbox version hides an overdue warning until staff have already checked the book out. |

## design/ultraplan

Source: [skill-library/design/ultraplan/SKILL.md](../../../skill-library/design/ultraplan/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Compose bounded prompt from artifacts, launch actual tool, ingest its result and save architecture/state for review.

Failure obligations: Tool unavailable, launch failure, missing output or rejected plan remains blocked/partial; no invented execution.

Branch inventory: Native vs unavailable tool; sufficient/missing phase context; resulting plan path; extraction; review.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `design.ultraplan.plan` | Use ultraplan to develop an architecture plan from our current artifacts. | Our requirements and constraints are ready, and I want the ultraplan workflow to turn them into a reviewed architecture proposal. |

## maintain/code-debt

Source: [skill-library/maintain/code-debt/SKILL.md](../../../skill-library/maintain/code-debt/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Lock existing behavior with tests, scope bounded refactor, implement via TDD and verify behavior preservation.

Failure obligations: Unknown intended behavior, insufficient baseline or test edits used to hide regression blocks success.

Branch inventory: Existing tests/none; debt scope; behavior-preserving vs requested behavior change; all supported TDD defaults.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `maintain.code-debt.refactor` | Refactor the duplicated lending validation code without changing behavior. | The same validation logic appears in three places and routine maintenance is becoming risky. |

## maintain/hotfix

Source: [skill-library/maintain/hotfix/SKILL.md](../../../skill-library/maintain/hotfix/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Confirm production impact/repro/root cause, bound fix, test/review, ship approved fixture and create mandatory postmortem.

Failure obligations: Nonproduction request, unproven cause, widening scope or failed smoke/review cannot become expedited success.

Branch inventory: Production yes/no; rollback alternative; test level selection; expedited review; postmortem follow-up.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `maintain.hotfix.fix` | Hotfix the reproduced production checkout regression. | Production checkout fails on the known duplicate-copy input after yesterday's release and customers cannot lend books. |

## maintain/postmortem

Source: [skill-library/maintain/postmortem/SKILL.md](../../../skill-library/maintain/postmortem/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Build evidence-based timeline/5-whys/contributors/actions, save document and create approved action items linked to incident.

Failure obligations: Missing incident/time evidence or disputed cause stays uncertain; no blame or fabricated events.

Branch inventory: Incident identified/missing; hotfix/rollback caller; action items new/existing; follow-up consent; closure.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `maintain.postmortem.write` | Write a postmortem for the lending outage. | The outage is resolved, but we have not captured its timeline, contributing causes or prevention work. |

## maintain/rollback-revert

Source: [skill-library/maintain/rollback-revert/SKILL.md](../../../skill-library/maintain/rollback-revert/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Identify artifact, confirm blast radius and rollback method, execute owned fixture rollback, verify recovery and spawn postmortem.

Failure obligations: Unknown/unsafe target, declined action, rollback failure or unhealthy service remains unresolved.

Branch inventory: Git revert/deploy prior artifact/config rollback; data implications; dry guide vs execute; smoke; required postmortem.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `maintain.rollback-revert.rollback` | Roll back the failed fixture release to its last healthy artifact. | The new release is broken and restoring the previous known-good version is the agreed recovery choice. |

## maintain/security-patch

Source: [skill-library/maintain/security-patch/SKILL.md](../../../skill-library/maintain/security-patch/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Reproduce vulnerability, classify blast radius, patch/test, enforce mandatory post-fix security review, ship and record disclosure/follow-up.

Failure obligations: Absent reproduction, failed review, unapproved disclosure/deploy or unresolved vulnerability blocks shipping.

Branch inventory: Code/dependency issue; severity; patch scope; review pass/fail; disclosure known/unknown; post-ship obligations.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `maintain.security-patch.patch` | Patch the reproduced lending-record authorization vulnerability. | A staff account can read another store's lending records and we have a concrete reproduction requiring a security fix. |

## maintain/something-broke

Source: [skill-library/maintain/something-broke/SKILL.md](../../../skill-library/maintain/something-broke/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Use runbook, at most three triage questions, classify incident, choose fix/rollback, verify resolution and record postmortem/state.

Failure obligations: Missing diagnosis/runbook, ineffective fix or failed recovery probe remains unresolved; no speculative production mutation.

Branch inventory: Runbook present/absent; severity; fix vs rollback; recovery failure; checkpoint/context; postmortem required.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `maintain.something-broke.triage` | Help diagnose the production lending outage. | The live store service suddenly returns errors and we do not yet know why. |

## plan/course-correction

Source: [skill-library/plan/course-correction/SKILL.md](../../../skill-library/plan/course-correction/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Document signal, revised direction, scope/personas and per-item decisions; confirm before committing changes.

Failure obligations: Single weak signal, disputed pivot, missing artifacts or rejected triage decision must not silently rewrite direction.

Branch inventory: Single vs accumulated signals; live vs prelaunch; target persona changes; brief/PRD present/absent; each in-flight item keep/repurpose/drop/defer.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.course-correction.pivot` | Help us change from event inventory to lending inventory. | Our bookstore interviews keep asking for loans instead of event stock; the current plan no longer fits. |
| `plan.course-correction.triage` | Review existing work against our agreed lending-inventory direction. | We changed direction and I cannot tell which unfinished items are still useful. |

## plan/documents-academic-research

Source: [skill-library/plan/documents-academic-research/SKILL.md](../../../skill-library/plan/documents-academic-research/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Produce grounded paper artifacts through six explicit quality gates; preserve citations and venue constraints.

Failure obligations: Missing evidence, unverifiable citations, below-threshold score or denied gate prevents advancement/submission claims.

Branch inventory: Phases 0–5 individually; existing corpus/narrative vs absent; outline 28/35, section 16/20, review 56/70 boundaries; drafting/revision loops; venue changes.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.documents-academic-research.first-principles` | Develop the first-principles argument for our research paper. | We have a research idea but cannot yet say precisely what claim the paper defends. |
| `plan.documents-academic-research.literature` | Develop the literature and positioning section for our paper. | Our paper draft makes a claim, but I cannot tell how it differs from prior research. |
| `plan.documents-academic-research.structure` | Choose the venue and structure our research paper. | We have the argument and literature but no coherent outline or target venue. |
| `plan.documents-academic-research.draft` | Draft the next agreed section of our research paper. | The approved paper outline is ready and the methods section is still blank. |
| `plan.documents-academic-research.revise` | Review and revise our complete research paper. | The full paper draft exists but its weakest arguments need another pass before submission. |
| `plan.documents-academic-research.submission` | Prepare our approved paper for submission to the selected venue. | The revised paper passed review, but we still lack the venue-ready package. |

## plan/documents-narrative-arc

Source: [skill-library/plan/documents-narrative-arc/SKILL.md](../../../skill-library/plan/documents-narrative-arc/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Persist/query/update a claims-proof-objectives graph with supporting and opposing evidence.

Failure obligations: Missing graph, unknown claim or contradictory/unavailable evidence is surfaced rather than fabricated.

Branch inventory: Build from corpus; query support/weakness/credibility/path; update new and weakened evidence; privacy resolution.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.documents-narrative-arc.build` | Build the narrative arc connecting our claims, evidence and objectives. | We have scattered proof points but no way to see which strategic claims they support. |
| `plan.documents-narrative-arc.query` | Show what supports claim C1 in our narrative arc. | I am not convinced the evidence behind C1 reaches our stated objective. |
| `plan.documents-narrative-arc.update` | Update our narrative arc with the new interview evidence. | The new interviews contradict one of our old claims and the argument map may be stale. |

## plan/epic-design

Source: [skill-library/plan/epic-design/SKILL.md](../../../skill-library/plan/epic-design/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Present and confirm an ordered epic story list with promise, integration, prerequisite, implementation and test/review coverage.

Failure obligations: Unknown epic, unavailable artifact system, rejected story list or >14 stories must be handled explicitly before writes.

Branch inventory: Existing/new/no epic; artifact fallback; missing design assumptions; applicable/nonapplicable implementation sections; 14-story boundary; split.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.epic-design.existing` | Design the stories for epic EP-001. | EP-001 promises inventory reconciliation, but nobody can tell the complete sequence of work needed to deliver it. |
| `plan.epic-design.new` | Design a new epic for lending inventory and its ordered stories. | Lending inventory needs a complete delivery package and we have not created an epic yet. |

## plan/epics

Source: [skill-library/plan/epics/SKILL.md](../../../skill-library/plan/epics/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Use epic files/cache for requested operation; preserve links, sequence and evidence-gated completion.

Failure obligations: Missing IDs, conflicting links, second active epic or incomplete criteria/receipt require error/confirmation/stop.

Branch inventory: Default/unknown→review; review active/all; one active epic conflict; relink yes/no; complete gaps/override/receipt; status intent/cascade.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.epics.add` | Add an epic called Inventory reconciliation. | Inventory reconciliation needs a named work area with its own objective and completion criteria. |
| `plan.epics.review` | Review our current epics. | I have lost track of which major work areas are active and which are waiting. |
| `plan.epics.review-all` | Show every epic, including completed and paused ones. | The current epic view hides work areas I remember from earlier releases. |
| `plan.epics.link` | Link ISSUE-001 to EP-001. | ISSUE-001 belongs in the reconciliation work area, but it is still unassigned. |
| `plan.epics.status` | Show the status of EP-001. | I cannot tell how close the reconciliation epic is to its stated outcome. |
| `plan.epics.complete` | Complete EP-001 using its verified completion evidence. | All agreed EP-001 criteria have current evidence and this work area should now be recorded as finished. |

## plan/product-brief

Source: [skill-library/plan/product-brief/SKILL.md](../../../skill-library/plan/product-brief/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Review outline/audience/NDA/style, write approved substantive brief, state and effort log at manifest-routed path.

Failure obligations: Missing privacy manifest stops writing; unsupported claims, rejected outline or missing audience/NDA decisions require resolution.

Branch inventory: Context rich/degraded; bullets/narrative/other; one-section interviews; revisions; Additional Development; versioned document.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-brief.write` | Write a product brief for bookstore lending inventory. | The bookstore team cannot agree who this lending product serves, why it matters or what success would mean. |
| `plan.product-brief.revise` | Revise the lending inventory product brief with the agreed narrower audience. | Our brief still targets chains even though we agreed to serve independent stores first. |

## plan/product-competition

Source: [skill-library/plan/product-competition/SKILL.md](../../../skill-library/plan/product-competition/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Produce evidence-backed survey/matrix/feature comparison at chosen depth with sources and effort state.

Failure obligations: No competitors, provider failure, unsupported pricing/claims or user skip are disclosed; no invented research.

Branch inventory: L1/L2/L3; research seed/manual seed; Firecrawl available/unavailable; frustration and partial exit.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-competition.survey` | Give us a quick competitive survey for lending inventory. | I know only one rival and need a broad sense of the alternatives before narrowing the idea. |
| `plan.product-competition.matrix` | Compare lending-inventory competitors in a structured matrix. | We have a shortlist but cannot compare audience, pricing, strengths and weaknesses consistently. |
| `plan.product-competition.feature-deep` | Compare competitors deeply on overdue-item handling. | The broad comparison is done, but overdue handling could determine our differentiation. |

## plan/product-discovery

Source: [skill-library/plan/product-discovery/SKILL.md](../../../skill-library/plan/product-discovery/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Capture intent, concrete problem/success and evidence at the selected depth; save discovery/compliance state and log.

Failure obligations: Abstract or insufficient L3 inputs are probed; user skip records gaps; no synthetic assumption is presented as proof.

Branch inventory: L1/L2/L3; recommendation commercial/internal/hobby; challenge/scenario; required segments/JTBD/scenarios; geography/data/minors compliance combinations; frustration/skip.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-discovery.l1` | Help me clarify the basic intent and boundaries of a small lending tool. | I want a small tool for lending books but cannot yet describe its basic purpose clearly. |
| `plan.product-discovery.l2` | Explore the user problem and success criteria for our internal lending tool. | Our team says lending is painful, but I do not know what a successful fix looks like in a real shift. |
| `plan.product-discovery.l3` | Develop a full customer pain thesis for our commercial lending product. | We might sell this product, but who owns the pain, how costly it is and whether anyone would pay are still uncertain. |

## plan/product-manage-scope

Source: [skill-library/plan/product-manage-scope/SKILL.md](../../../skill-library/plan/product-manage-scope/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Record dated in/out scope movement with rationale and affected artifacts; do not add implementation.

Failure obligations: Unclear direction, contradictory boundary or missing state prompts clarification instead of silently expanding scope.

Branch inventory: In→out; out→in; discovery of affected specs; explicit status/cascade decision.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-manage-scope.add` | Record barcode scanning moving into the agreed scope. | We previously excluded barcode scanning, but the agreed product promise now depends on it. |
| `plan.product-manage-scope.remove` | Record supplier integrations moving out of scope. | Supplier integration is still listed as included even though we agreed to defer it. |

## plan/product-market-messaging

Source: [skill-library/plan/product-market-messaging/SKILL.md](../../../skill-library/plan/product-market-messaging/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Produce audience-specific value, voice and messaging artifacts grounded in existing positioning.

Failure obligations: Missing evidence or contested claim is flagged; publication is not implied by drafting.

Branch inventory: Multiple audiences; existing/absent positioning; requested voice; revision.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-market-messaging.write` | Draft launch messaging for independent bookstore owners. | Owners keep misunderstanding what our lending product does and why it would help their store. |
| `plan.product-market-messaging.revise` | Adjust the launch messaging for store staff rather than owners. | The current message talks about margins, but the people doing the lending care about finishing a shift without missing items. |

## plan/product-milestone-planning

Source: [skill-library/plan/product-milestone-planning/SKILL.md](../../../skill-library/plan/product-milestone-planning/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Run guided outcome/criteria/risks/prerequisites/confidence workshop; review sequence and hand off confirmed milestones.

Failure obligations: Vague success, conflicting prerequisites, premature date estimate or rejected sequence is corrected before tracking writes.

Branch inventory: One/multiple milestones; early preview; gate/checkpoint; confidence; dependency sequence; explicit handoff accept/decline.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-milestone-planning.workshop` | Help us plan outcome-based milestones for lending inventory. | We have a long feature list but no sensible checkpoints showing that the product is becoming useful. |

## plan/product-milestones

Source: [skill-library/plan/product-milestones/SKILL.md](../../../skill-library/plan/product-milestones/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Perform milestone operation from operations.md; permanent IDs, bidirectional links, criteria and non-goals stay consistent.

Failure obligations: Unknown/terminal target, incomplete criteria, failed export or rejected destructive confirmation prevents invalid mutation.

Branch inventory: All operations.md subflows; current/paused/uninitialized; legacy schema; export GitHub/Markdown/CSV/none; exact deletion phrases; terminal follow-up chain.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-milestones.add` | Add a milestone for the first store completing a lending cycle. | We need a measurable checkpoint proving one store can finish the entire lending process. |
| `plan.product-milestones.review` | Review our current milestones. | I cannot see which product outcomes matter now and which are later. |
| `plan.product-milestones.review-all` | Show all milestones including achieved and dropped ones. | Some older outcome checkpoints disappeared from the current milestone view. |
| `plan.product-milestones.link` | Link ISSUE-001 to milestone MS-001. | The first lending checkpoint is missing the issue that makes returns work. |
| `plan.product-milestones.status` | Show milestone MS-001 in detail. | I need to understand the evidence and contributing work behind our first lending checkpoint. |
| `plan.product-milestones.blockers` | Show what blocks milestone MS-001. | The first lending checkpoint has stalled and I cannot see which criteria or dependencies remain open. |
| `plan.product-milestones.complete` | Mark milestone MS-001 achieved using its verified criteria. | The first store finished the agreed lending cycle and the evidence for MS-001 is recorded. |
| `plan.product-milestones.unassigned` | Show work without a milestone. | Some work may not contribute to any of our agreed checkpoints. |
| `plan.product-milestones.onboard` | Set up milestone tracking from our existing roadmap documents. | Our milestones live in old planning notes and are not available in SweetClaude yet. |
| `plan.product-milestones.pause` | Pause milestone tracking. | Keep our milestone data, but I do not want milestone tracking active for now. |
| `plan.product-milestones.offboard` | Export and offboard milestone tracking. | We are moving milestone management elsewhere and need to take the data with us safely. |

## plan/product-parking-lot

Source: [skill-library/plan/product-parking-lot/SKILL.md](../../../skill-library/plan/product-parking-lot/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Manage deferred ideas with explicit priority and permanent detail records, preserving its currently declared legacy format for observation.

Failure obligations: Missing manifest, import/export failure or destructive confirmation refusal stops unsafe writes; legacy-format conflicts are reported.

Branch inventory: Add/review/update/promote; inferred/imported data; GitHub/Linear/Jira/Notion/Markdown; pause/resume/onboard/offboard; BL→ISSUE downstream compatibility.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-parking-lot.add` | Save gift-card support as a deferred idea. | Gift cards could be useful eventually, but they should not interrupt our current lending work. |
| `plan.product-parking-lot.review` | Review our deferred ideas. | We captured future ideas earlier and I want to see what is parked. |
| `plan.product-parking-lot.update` | Update the priority of the parked gift-card idea. | Gift cards can wait longer than we originally thought. |
| `plan.product-parking-lot.promote` | Promote the parked gift-card idea to active work. | We are ready to act on the gift-card idea that we previously set aside. |
| `plan.product-parking-lot.onboard` | Set up deferred-idea tracking from our existing notes. | Future ideas are scattered across old notes and are easy to lose. |
| `plan.product-parking-lot.pause` | Pause deferred-idea tracking. | Keep the ideas, but stop using the parking lot for now. |
| `plan.product-parking-lot.offboard` | Export and offboard deferred-idea tracking. | We will manage future ideas elsewhere and need the existing list preserved. |

## plan/product-positioning-statement

Source: [skill-library/plan/product-positioning-statement/SKILL.md](../../../skill-library/plan/product-positioning-statement/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Define category and differentiated positioning; challenge, refine and save approved statement and state.

Failure obligations: Missing user/value evidence or indistinguishable positioning triggers probing instead of invented differentiation.

Branch inventory: Known/missing discovery/brief/personas/competition; category challenge; iteration.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-positioning-statement.write` | Write the positioning statement for our bookstore lending product. | People understand the features but cannot explain who this is for or why it differs from a spreadsheet. |

## plan/product-prd

Source: [skill-library/plan/product-prd/SKILL.md](../../../skill-library/plan/product-prd/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Create reviewed outline and substantive requirements document, state, versioned output and effort log; preserve context links.

Failure obligations: Missing privacy, vague success, unsupported requirements or rejected draft requires stop/revision; no automatic implementation.

Branch inventory: Collaborative/autonomous interview; existing brief/personas vs missing; bullet/narrative style; scope changes/revisions.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-prd.write` | Write a PRD for the agreed lending-inventory scope. | The brief explains the product, but developers still lack clear functional and nonfunctional requirements. |
| `plan.product-prd.revise` | Revise the PRD to exclude supplier integration. | The requirements still include an integration we agreed to leave out of the first release. |

## plan/product-research

Source: [skill-library/plan/product-research/SKILL.md](../../../skill-library/plan/product-research/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Offer and run chosen-depth solution survey using available providers; preserve commercial/open-source lenses and sources.

Failure obligations: Declined research or unavailable provider records a partial/skipped outcome; no fabricated market evidence.

Branch inventory: Offer yes/no; depth; Firecrawl/standard; commercial and open source; skip/frustration.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-research.survey` | Survey existing solutions before we build our lending product. | I worry we are about to rebuild something that already exists, either as a service or open source. |

## plan/product-roadmap

Source: [skill-library/plan/product-roadmap/SKILL.md](../../../skill-library/plan/product-roadmap/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Perform roadmap/release operation with proper downstream work type, status intent, dependency and evidence rules.

Failure obligations: Unknown MS, missing prerequisites, unmet gate or rejected status change cannot silently start work or close a target.

Branch inventory: Full/single; activation by work type; defer/complete/cancel; release aggregation; linked child status cascade; no auto completion.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-roadmap.list` | Show the product roadmap. | I cannot see the order in which our agreed delivery targets are meant to land. |
| `plan.product-roadmap.view` | Show roadmap item MS-001. | I need the details behind the first roadmap target. |
| `plan.product-roadmap.new` | Create a roadmap target for lending returns. | Returns need a delivery target in our roadmap. |
| `plan.product-roadmap.activate` | Activate roadmap target MS-001. | We have selected the first roadmap target and want to begin its correct delivery workflow. |
| `plan.product-roadmap.defer` | Defer roadmap target MS-001. | The first roadmap target should wait rather than remain scheduled now. |
| `plan.product-roadmap.complete` | Complete roadmap target MS-001 with its evidence. | The delivery target represented by MS-001 has met its verified outcome. |
| `plan.product-roadmap.cancel` | Cancel roadmap target MS-001. | We have decided the first roadmap target should no longer be delivered. |
| `plan.product-roadmap.release-new` | Create a release containing the selected lending targets. | We need one named release grouping the targets we plan to deliver together. |
| `plan.product-roadmap.release-view` | Show release MS-002 and its included targets. | I cannot tell which roadmap work belongs to the upcoming release. |

## plan/product-roadmap-analysis

Source: [skill-library/plan/product-roadmap-analysis/SKILL.md](../../../skill-library/plan/product-roadmap-analysis/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Calculate evidence-qualified RICE and alignment, propose stack rank and apply only confirmed order.

Failure obligations: Missing reach/impact/confidence/effort, unsupported estimates or rejected rank leaves ordering unmodified.

Branch inventory: Full/alignment/single item; tied/incomplete scores; scope/milestone mismatch; confirm/adjust/decline.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-roadmap-analysis.analyze` | Analyze and prioritize our roadmap with RICE. | We have several delivery targets competing for attention and no consistent basis for their order. |
| `plan.product-roadmap-analysis.alignment` | Check roadmap alignment with our scope and milestones. | Our roadmap may have drifted away from the outcomes we agreed to pursue. |
| `plan.product-roadmap-analysis.item` | Analyze the priority of roadmap item MS-001. | I understand the broad order but not the evidence supporting MS-001 in particular. |

## plan/product-terminology

Source: [skill-library/plan/product-terminology/SKILL.md](../../../skill-library/plan/product-terminology/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: List/add/view/update/search shared glossary; preserve aliases, definitions and dated changes.

Failure obligations: Unknown term, duplicate/alias collision or conflicting meaning requires explicit resolution.

Branch inventory: Empty/list; add term/no term; view; update; search exact/alias/definition/no match.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-terminology.list` | Show our shared product glossary. | People use different words for the same lending concepts and I need the agreed vocabulary. |
| `plan.product-terminology.add` | Define the term lending cycle in our glossary. | The team keeps using lending cycle with different meanings. |
| `plan.product-terminology.view` | Show the glossary definition of lending cycle. | I need to know exactly what we mean by lending cycle. |
| `plan.product-terminology.update` | Update lending cycle to include the return step. | Our current definition stops at checkout and omits the return. |
| `plan.product-terminology.search` | Search the glossary for terms related to overdue items. | I remember we agreed a word for late returns but cannot recall it. |

## plan/product-user-focus-group

Source: [skill-library/plan/product-user-focus-group/SKILL.md](../../../skill-library/plan/product-user-focus-group/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Run selected synthetic study with gated evidence, validated respondent schema, labeled synthesis and pending-validation assumptions.

Failure obligations: Missing prerequisites without exact override stops; invalid respondents retry within budget; >30% defects halts; no real-user claims.

Branch inventory: ask/concept/message; no-arg menu; discovery/persona hard gate; override exact/wrong; default/custom archetypes/instances; retry 0/1/2/exhausted; defect threshold boundaries; schemas.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-user-focus-group.ask` | Ask a synthetic persona panel what would frustrate them about lending inventory. | Before field interviews, I want a clearly simulated view of the concerns our defined user types might raise. |
| `plan.product-user-focus-group.concept-test` | Run a synthetic comparison of the two lending concepts. | We have two concepts and want a simulated preference comparison across our defined personas. |
| `plan.product-user-focus-group.message-test` | Run a synthetic test of the two launch message variants. | Our two message drafts emphasize different benefits and we want simulated reactions before real research. |

## plan/product-user-stories

Source: [skill-library/plan/product-user-stories/SKILL.md](../../../skill-library/plan/product-user-stories/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Create persona-task-grounded stories in selected format and scope; preserve acceptance criteria and state.

Failure obligations: Missing persona context requires permission to degrade; export/confirmation failures preserve stories; no hidden scope expansion.

Branch inventory: Gherkin/generic; all personas/SLC/MVP/custom; existing imports GitHub/Markdown/Jira/Linear; dependency gate; onboarding/pause/offboard; export GitHub/Markdown/CSV/none.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.product-user-stories.write` | Write user stories for the agreed lending workflow. | The requirements exist, but the team still cannot describe what each user must accomplish step by step. |
| `plan.product-user-stories.onboard` | Set up user-story management using our existing story documents. | Our old user stories have not been brought into the current project workflow. |
| `plan.product-user-stories.pause` | Pause user-story management. | Leave the story files intact, but stop using this feature for now. |
| `plan.product-user-stories.offboard` | Export and offboard user-story management. | We are moving story management elsewhere and need the data preserved before cleanup. |

## plan/project-goals

Source: [skill-library/plan/project-goals/SKILL.md](../../../skill-library/plan/project-goals/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Manage binary business outcomes in the goals store with measurable success, achieved/missed evidence and history.

Failure obligations: Feature delivery disguised as business goal, vague criteria or missing goal is challenged; status is not fabricated.

Branch inventory: List/view/new/achieved/missed; pending next-goal signal; binary criteria; roadmap distinction.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.project-goals.list` | List our business goals. | I can see features, but not the business outcomes we are trying to achieve. |
| `plan.project-goals.view` | Show business goal MS-001. | I need the full success definition for our first business outcome. |
| `plan.project-goals.new` | Create a business goal for five stores completing a lending cycle. | Shipping features alone will not tell us whether stores are actually adopting the product. |
| `plan.project-goals.achieved` | Mark business goal MS-001 achieved with the recorded evidence. | The five stores in our goal have now completed their lending cycles. |
| `plan.project-goals.missed` | Mark business goal MS-001 missed and record why. | The adoption goal did not happen and we need to preserve that outcome honestly. |

## plan/project-scope

Source: [skill-library/plan/project-scope/SKILL.md](../../../skill-library/plan/project-scope/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: View/set/update/history scope; confirm changes and assess conflicting open work before cascade.

Failure obligations: Duplicate initial set, too-broad boundary or rejected cascade does not overwrite scope or alter work silently.

Branch inventory: No scope; first definition; 3 out-of-scope boundary; update with/without conflicts; per-item response; history empty/populated.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.project-scope.view` | Show our agreed project scope. | I cannot tell which capabilities this project has committed to and which are excluded. |
| `plan.project-scope.set` | Define the initial scope of our lending product. | We have a product idea but no explicit boundary around what belongs in it. |
| `plan.project-scope.update` | Update scope to exclude supplier integrations and assess affected work. | Our agreed boundary changed, but related open work may still assume supplier integration. |
| `plan.project-scope.history` | Show the history of project scope changes. | I need to understand how our current scope differs from earlier decisions. |

## plan/user-personas

Source: [skill-library/plan/user-personas/SKILL.md](../../../skill-library/plan/user-personas/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Build grounded persona/task definitions with failures, success criteria, anti-profile and diversity checks; preserve state.

Failure obligations: Missing discovery offers explicit paths; inferred fields labeled; skipped tasks recorded; export failure/deletion refusal preserves data.

Branch inventory: Docs vs interview; draft/user-supplied tasks; task reuse; research expansion consent; anti-profile yes/no; diversity gaps; onboarding/pause/offboard; Markdown/JSON/none export.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `plan.user-personas.interview` | Define user personas for bookstore lending staff. | We keep saying users, but a part-time clerk and a store owner have different tasks and failure concerns. |
| `plan.user-personas.from-docs` | Derive draft personas from the supplied interview documents. | Our interviews describe distinct user types, but nobody has assembled the evidence into usable profiles. |
| `plan.user-personas.onboard` | Set up persona management from existing user research. | We already have user research files and want them incorporated rather than starting from zero. |
| `plan.user-personas.pause` | Pause persona management. | Keep the research and profiles, but stop the persona feature for now. |
| `plan.user-personas.offboard` | Export and offboard persona management. | We need our persona information in another system before removing the current feature. |

## utils/big-picture

Source: [skill-library/utils/big-picture/SKILL.md](../../../skill-library/utils/big-picture/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Redirect to Status roadmap using same project context; render real hierarchy without mutation.

Failure obligations: Missing data or unavailable status route does not fabricate a roadmap or expose old slash discovery.

Branch inventory: Retained helper caller; empty/full tree; Status warnings.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.big-picture.redirect` | Continue the whole-project overview request. | A retained caller requested the big-picture helper and needs the current Status roadmap view. |

## utils/corpus-consolidate

Source: [skill-library/utils/corpus-consolidate/SKILL.md](../../../skill-library/utils/corpus-consolidate/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Scan/hash sources, estimate tokens/dedup, approve manifest, copy unique files in batches and verify state without deleting originals.

Failure obligations: Missing sources, unreadable file, rejected plan or partial copy is reported; no inaccurate all-files-copied claim.

Branch inventory: Multiple sources; exact/near duplicate; exclusions; scan/dedup workers; plan approve/revise/cancel; collision; batch failure.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.corpus-consolidate.consolidate` | Consolidate the supplied document directories into the corpus inbox. | Our project documents are scattered across several folders and contain repeated copies we need organized without losing originals. |

## utils/corpus-promote

Source: [skill-library/utils/corpus-promote/SKILL.md](../../../skill-library/utils/corpus-promote/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Promote only approved working docs atomically; archive sources and update state/index one document at a time.

Failure obligations: Unapproved/missing doc, collision, archive/index failure or interrupted move leaves honest per-doc state and no false promotion.

Branch inventory: Ready/unready documents; approval; partial batch; source archival; RAG configured/unconfigured; repeated run.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.corpus-promote.promote` | Promote the approved working documents to the canonical corpus. | The reconciled documents are approved, but search and readers still need them finalized as the authoritative versions. |

## utils/corpus-rag-reindex

Source: [skill-library/utils/corpus-rag-reindex/SKILL.md](../../../skill-library/utils/corpus-rag-reindex/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Rebuild selected RAG scope from actual eligible sources and verify query/index counts without changing source docs.

Failure obligations: Missing MCP/index, invalid scope or failed ingestion remains partial; no stale-index success claim.

Branch inventory: All/collection scope; missing manifest; changed/removed docs; failed/successful rebuild.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.corpus-rag-reindex.reindex` | Rebuild the corpus RAG index from the canonical source files. | The existing semantic index may be stale or damaged and needs a clean rebuild. |

## utils/corpus-rag-setup

Source: [skill-library/utils/corpus-rag-setup/SKILL.md](../../../skill-library/utils/corpus-rag-setup/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Verify reconciliation, configure scoped local MCP/index/gitignore, discover/ingest eligible docs, write manifest and validate retrieval.

Failure obligations: Missing provider, unreconciled sources without required handling, invalid config or partial ingest blocks ready claim.

Branch inventory: Install present/absent; new/existing .mcp config merge; root; canonical-only gate; index absent/current/stale; update/delete; query known fact.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.corpus-rag-setup.setup` | Set up semantic search for the approved canonical corpus. | Our documents are finalized, but there is no working semantic search over the authoritative set. |
| `utils.corpus-rag-setup.update` | Update the existing corpus semantic-search index. | The canonical corpus changed since its last successful indexing run. |

## utils/corpus-reconcile

Source: [skill-library/utils/corpus-reconcile/SKILL.md](../../../skill-library/utils/corpus-reconcile/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Inventory staged docs, select cluster, analyze conflicts, propose/draft/revise and checkpoint each approved canonical draft.

Failure obligations: No staged material, unreliable analysis, rejected proposal or save failure leaves unapproved drafts explicitly unresolved.

Branch inventory: Single/multiple clusters; supporting/conflicting docs; per-file workers; approve/revise/defer; continue/finish; no automatic promotion.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.corpus-reconcile.reconcile` | Reconcile the staged lending documents into one canonical draft. | The staged notes disagree about current lending behavior and we need an approved authoritative account. |

## utils/corpus-status

Source: [skill-library/utils/corpus-status/SKILL.md](../../../skill-library/utils/corpus-status/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Report live counts/stages/timestamps and next-action recommendation using actual pipeline data.

Failure obligations: Missing/malformed state or directories is shown accurately; no pipeline execution from status request.

Branch inventory: Zero/nonzero each stage; declared counts diverge; missing index; stale last run.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.corpus-status.status` | Show the document corpus pipeline status. | I cannot tell how many documents are waiting, reconciled or already authoritative. |

## utils/corpus-triage

Source: [skill-library/utils/corpus-triage/SKILL.md](../../../skill-library/utils/corpus-triage/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Classify inbox per approved fast/guided batches into keep/reconcile/discard/defer and persist verified moves/state.

Failure obligations: Missing inbox, rejected classification or partial worker/move failure preserves undecided files and reports exact residuals.

Branch inventory: Fast/guided; all four classifications; cancel; batch scope; zero/one/many; source preservation and discard authority.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.corpus-triage.triage` | Triage the corpus inbox documents. | The inbox mixes useful material, conflicting drafts and things we do not want in the authoritative corpus. |

## utils/dashboard

Source: [skill-library/utils/dashboard/SKILL.md](../../../skill-library/utils/dashboard/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Rebuild cache, launch owned local server and verify actual reachable dashboard; preserve data.

Failure obligations: Missing dependency, occupied port, failed process or HTTP error prevents ready claim; do not kill unrelated process.

Branch inventory: Start/already running; port bind; cache health; browser data; server stop/ownership.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.dashboard.launch` | Open the local SweetClaude dashboard. | I need a browser view of the roadmap, backlog and workflow activity rather than a terminal summary. |

## utils/document-corpus

Source: [skill-library/utils/document-corpus/SKILL.md](../../../skill-library/utils/document-corpus/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Present live pipeline menu and delegate exact selected step with retained context, preserving feature lifecycle and canonicalization order.

Failure obligations: Missing state, paused refusal, provider unavailable or ambiguous generic Utils recursion cannot masquerade as execution.

Branch inventory: Seven step menu choices; direct step names; setup/update RAG label; lightweight/full onboarding; pause/resume/offboard; typed destructive confirmations.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.document-corpus.menu` | Help manage our document corpus. | We have project documents to organize and I need to choose the right stage of the corpus workflow. |
| `utils.document-corpus.onboard` | Onboard our project documents into the corpus feature. | We already have documents and want the full corpus workflow initialized from the existing material. |
| `utils.document-corpus.pause` | Pause the document corpus feature. | Leave the document data intact but stop the corpus workflow for now. |
| `utils.document-corpus.offboard` | Export and offboard the document corpus feature. | We are moving away from corpus management and need explicit choices about preserving documents, index and state. |

## utils/documents-update-docs

Source: [skill-library/utils/documents-update-docs/SKILL.md](../../../skill-library/utils/documents-update-docs/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Derive actual behavior changes from implementation, update affected docs/traceability and report exact scope.

Failure obligations: Unknown changed behavior, missing source or unsupported documentation claim is surfaced rather than invented.

Branch inventory: Implementation changed/no behavior changed; affected API/user/dev docs; traceability; contextual review.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.documents-update-docs.update` | Update documentation for the implemented lending behavior change. | The code now rejects duplicate loans, but our usage and API documentation still describe the old behavior. |

## utils/misc-meeting-prep

Source: [skill-library/utils/misc-meeting-prep/SKILL.md](../../../skill-library/utils/misc-meeting-prep/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Prepare meeting-specific agenda/objectives/brief/talking points and optional debrief/stakeholder record; do not send invitations/messages.

Failure obligations: Unknown purpose/audience, missing evidence or rejected deliverable requires clarification; no invented stakeholder facts.

Branch inventory: Meeting type; existing profiles; draft/review; debrief/none; profile updates permission.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.misc-meeting-prep.prepare` | Prepare the agenda and brief for our lending-launch meeting. | Tomorrow's launch discussion has no clear decisions, supporting context or agenda yet. |
| `utils.misc-meeting-prep.debrief` | Capture the debrief from our lending-launch meeting. | The launch meeting ended and its decisions, follow-ups and stakeholder signals are still only in my notes. |

## utils/next-steps

Source: [skill-library/utils/next-steps/SKILL.md](../../../skill-library/utils/next-steps/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Explain current pipeline step and its next skill with current context, respecting user-led phase decisions.

Failure obligations: Missing/conflicting phase data is disclosed; orientation must not automatically advance work.

Branch inventory: Each phase mapping; current artifact completeness; execute only on explicit follow-up authority; stop.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.next-steps.orient` | Walk me through where this project sits in the workflow. | I am lost in the process and need to understand what our current work involves. |

## utils/recap

Source: [skill-library/utils/recap/SKILL.md](../../../skill-library/utils/recap/SKILL.md). Entry: legitimate caller only (or redirect). Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Redirect to no-argument Status session orientation, preserving checkpoint/context.

Failure obligations: No fake history or additional execution; no public deprecated command.

Branch inventory: Active/no active work; checkpoint set/absent; detour return; new session.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.recap.redirect` | Continue the current-session recap request. | A retained caller requested the recap helper and needs the current Status session view. |

## utils/report-failure

Source: [skill-library/utils/report-failure/SKILL.md](../../../skill-library/utils/report-failure/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Only after explicit request, assign FR ID and write evidence-qualified failure report at ignored local path with uncertainty.

Failure obligations: No explicit record request means no invocation; missing evidence or report-write failure cannot be invented into a completed report.

Branch inventory: First/subsequent ID; existing ignore entry; exact evidence; 5 whys; confidence; no automatic filing from frustration alone.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.report-failure.record` | Write a structured failure report for this observed workflow mistake. | Please preserve a formal record of the mistake we just observed, its evidence, impact and likely mechanism. |

## utils/session-export

Source: [skill-library/utils/session-export/SKILL.md](../../../skill-library/utils/session-export/SKILL.md). Entry: public command/conversation matrix. Profiles: P01–P16, with explicit applicability accounting.

Expected happy outcome: Detect actual platform first, choose scope and create verified portable session package within actual platform limitations.

Failure obligations: Unsupported API/platform, inaccessible attachments or incomplete export is explicit; no invented filesystem/download actions.

Branch inventory: Claude Code vs Claude.ai web/desktop; full/scoped; transcript/assets/context; attachment limitations; quality checks.

| Path ID | Direct plain language | Indirect plain language |
|---|---|---|
| `utils.session-export.export` | Export this session as a complete portable package. | We need to continue this conversation elsewhere with its context and available artifacts preserved. |
