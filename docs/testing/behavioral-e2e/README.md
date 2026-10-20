# SweetClaude end-to-end behavioral test design and path inventory

Version: 1.1.0

Date: 2026-10-19

Status: inventory, selectable clusters and executable Tier 1 routing harness; no behavioral cases executed from this harness

This package defines what must be tested against the current working implementation before a behavioral test suite is written. Start with this document, then read [the operation inventory](paths.md) and [the source decision and routing register](source-map.md). [The machine-readable inventory](inventory.json) contains the same operation records, source fingerprints, and coverage obligations for a later runner. These are one deliverable.

Use [selectable test clusters](CLUSTERS.md) to enable or disable tiers, families, individual skills, routing, behavior, hooks, capabilities or journeys. The cluster catalog overlays the full inventory; it never removes its baseline obligations. The selection command previews exactly the chosen scope without running tests or calling a model. Selection-tool regression tests validate this tooling separately from SweetClaude's behavioral acceptance.

The target is the working tree on `codex/tiered-skill-library`, based on commit `e95225c566a9ad53226cfd001eeab1dc488ac2fd`, including its staged, unstaged, and untracked implementation files. The plugin manifest reports `4.5.2`. Neither that version nor the commit alone identifies this implementation. The inventory's SHA-256 source fingerprints identify the files inspected. Freeze a copy of those exact files for execution; if a relevant hash changes, reconcile this inventory before accepting results.

## 1. Acceptance target

A passing case demonstrates this complete chain:

`user request → startup/preflight → public command or implicit router → selected category → selected library workflow → required collaborators/controllers/hooks → authorized mutation or stop → independently verified outcome → truthful response`

Naming the expected workflow is insufficient. Producing the right file or GitHub issue through an improvised shortcut is also insufficient. The existing [live E2E report](../../design/live-e2e-behavioral-test-2026-10-19.md) records exactly that distinction: issue creation succeeded while the library workflow was bypassed. That is a routing/process failure even if the output is useful.

The current discovered surface is nine public commands, five internal top-level skills, and 115 library workflows across six categories. Internal workflows, redirects, state-based branches, and implementation-declared but unavailable destinations remain in scope. Their expected result may be an explicit blocked or unsupported outcome rather than success.

| Inventory layer | Count |
|---|---:|
| Public commands / internal top-level skills | 9 / 5 |
| Plan / Design / Build / Maintain / Configure / Utils workflows | 24 / 15 / 28 / 6 / 26 / 16 |
| Named operation paths with direct and indirect prompts | 347 |
| Source decision and section anchors requiring coverage disposition | 4,967 |
| Distinct skill-reference / helper-reference call sites | 645 / 394 |
| Registered hook commands / capability contracts | 19 / 132 |
| Fingerprinted implementation/reference files | 288 |

The 4,967 source anchors include supporting sections and repeated declarations; they are not 4,967 independent behavioral paths. Likewise, the 347 operations are base paths, before the required entry, branch, fault and continuation variants. An exact executable-case count requires resolving the source anchors against those variants. No total test count or passing coverage is claimed here.

## 2. Meaning of a path

A path is a distinguishable externally observable execution route: entry surface, intent, selected workflow/operation, relevant preconditions, decision or fault, and terminal behavior. It is not every possible sentence or every permutation of a loop. Enumerating every natural-language string or unbounded conversation is impossible; the finite coverage target is every declared routing edge, operation, branch outcome, menu choice, gate outcome, and bounded recovery outcome in the inspected sources.

Every operation in `paths.md` has a stable ID, two concrete prompts, an outcome, and a failure obligation. Every source decision has an ID in `source-map.md`. A later case ID must identify both, for example:

`build.project-issues.close-local / go-indirect / local-terminal-without-receipt / reject / autonomous / run-02`

The operation rows are not a smoke-test sample. All rows are required for full-suite acceptance; a named cluster selection may intentionally test only a subset and must report the remaining rows as not selected. Shared profiles below expand selected rows into additional cases; they do not permit silently omitting a difficult leaf within that selected scope. Source-register entries are coverage obligations, not evidence that those cases pass. When a register entry is a template heading, reference, code branch, or repeated instruction rather than an independent behavioral branch, the implementation-stage coverage map must explicitly attach it to its owning case or mark it structurally nonbehavioral with a reason. An unmapped entry prevents a completeness claim.

## 3. Entry and wording matrix

For each user-reachable library operation, run both prompts in the operation table through all three surfaces. Do not add expected skill names, workflow IDs, routing hints, or instructions to announce the route to the ordinary prompts.

| Variant | Submitted request | Required evidence |
|---|---|---|
| category-direct | `/sweetclaude:<category> <direct prompt>` | Category → library loader/index → correct workflow → operation |
| category-indirect | `/sweetclaude:<category> <indirect prompt>` | Same operation inferred from a concrete need rather than an explicit operation verb |
| go-direct | `/sweetclaude:go <direct prompt>` | `find-skill` → category → loader → workflow |
| go-indirect | `/sweetclaude:go <indirect prompt>` | Same chain without an explicit operation name |
| bare-direct | `<direct prompt>` in an active project session | Native intent matching or `_route` → correct public category → library workflow |
| bare-indirect | `<indirect prompt>` in an active project session | Same observable behavior from the need described |

For `help`, `status`, and no-argument `go`, use their dedicated public command, direct conversational request, and indirect conversational request. Exercise literal no-argument syntax as a separate discovery case. For all six category commands, exercise an empty argument and an underspecified argument: show a bounded choice or ask one useful clarification; do not invent mutation authority. Exact routing for an empty category is currently under-specified and is tracked as an oracle gap.

Internal-only workflows (`master`, `bootstrap`, `_route`, `find-skill`, `library-load`, TDD, controller/orchestrator support, maintenance helpers, check-in agents, redirects) are exercised through their legitimate callers. Do not manufacture a public slash command for them. Apply direct/indirect wording to the parent user request, then assert the internal edge. Redirects need both an actual caller/reference case and a negative public-discovery case.

Repeat happy and failure cases with the direct and indirect prompts. For a fault case, keep the same user goal and change only the fixture/fault. If an indirect prompt reasonably supports multiple operations with materially different authority, the expected first outcome is one focused clarification. Supply the disambiguating answer and assert the exact downstream operation. Accepting any vaguely related workflow is not a pass.

## 4. Fixture catalog

Each fixture is an isolated project with a separate temporary home, Claude configuration, plugin install registry/cache, Git configuration, MCP configuration, and tool environment. Isolation must be verified by observing resolved paths and outbound requests; `--setting-sources project,local` alone is not proof that user hooks, credentials, or plugins are isolated. Use synthetic credential values in faults and never capture real credential payloads.

| Fixture | Required contents |
|---|---|
| F00 absent | Empty directory, no Git, no `.sweetclaude`, no README |
| F01 new | Empty Git repository; variants with/without initial commit and README |
| F02 organized | Small executable service, real tests, committed baseline, initialized SweetClaude, local tracker |
| F03 inherited | Mixed code, no tests, >20 TODO/FIXME/HACK/XXX markers; independently vary each heuristic |
| F04 inactive | Healthy project plus `.sweetclaude/disabled`; a separate unconfigured project |
| F05 damaged | Empty/truncated/nonmapping/malformed state; missing manifest; stale/malformed session cache; partial setup |
| F06 legacy | Flat BL layout; typed stories/bugs/debt/chores; duplicate IDs; mixed modern/legacy; external product base |
| F07 current | Complete ISSUE/EP/MS tree, linked/unlinked work, dependencies, terminal folders, alternate public/private artifact bases |
| F08 modes | Clones of F07 for unset, flow, kanban, shape_up, agile; boundary WIP counts; approved/unapproved pitches and sprints |
| F09 controlled story | Frozen criteria, phase artifacts, evidence ledger and receipts; large and small controller instances |
| F10 incident | Local service with reproducible failed release, previous healthy release, runbook and smoke endpoint |
| F11 corpus | Source duplicates, near-duplicates, conflicting versions, staged/working/canonical docs, binary/unsupported files, local RAG fixture |
| F12 research | Known discovery, personas, stories, literature, claims and citations; seeded malformed synthetic respondents |
| F13 installation | Disposable install roots with stable/legacy/retired/stale channel records, versionless directories, missing helpers and mismatched versions |
| F14 GitHub | Dedicated disposable repository and scoped test identity; local issue sentinels; known issue/PR/label/branch states |
| F15 tool failures | Deterministic tool/MCP/service fault injection; permissions, timeout, nonzero exit, malformed/partial output, connection loss |
| F16 workspace safety | Dirty staged/unstaged/untracked sentinels; alternate trunk; unusual paths; symlink escape; competing state edits |
| F17 native platforms | Actual supported Claude Code session; separate Claude.ai web/desktop export contexts where required |

Never run purge, migration, recovery, installation sync, doctor repair, mode shift, deployment, rollback, issue mutation, or branch cleanup against the shared development checkout or normal installation. This document authorizes designing those cases; it does not execute them. A future runner must restrict all writes and external resources to fixture ownership. Teardown failure is reported and the exact owned resources are retained for recovery.

## 5. Mandatory expansion profiles

For full acceptance, apply every relevant profile to every operation. A cluster run may intentionally select particular profiles; report other profiles as not selected, while preserving all runtime safety and approval requirements. Relevance must be recorded with a source-backed reason; an unrecorded omission is uncovered. Profiles are independent case dimensions, not an instruction to run a meaningless full Cartesian product.

| Profile | Enumerated paths and expected results |
|---|---|
| P01 readiness | absent project; disabled project with activate/decline; missing global component; legacy-only state; configured state; incomplete setup; schema absent/1/2/unknown; malformed state. Only explicit setup/activation authority opens the setup route. Decline stops framework work. |
| P02 input | valid input; empty; unknown verb; missing ID; wrong family ID; nonexistent ID; ambiguous natural language; multiple intents; correction; quoted operation name; negated request; request for explanation only. Invalid input must not become an unrelated write. |
| P03 decision | Each visible menu choice; free-text alternative where allowed; approval; refusal; cancel; user stop; wrong typed phrase; exact typed phrase; no answer. No answer never means approval. Persisted choices apply only to the choices the source permits. |
| P04 storage | Default and relocated bases; public/private paths; missing manifest; unreadable/malformed manifest; missing parent; path with spaces/Unicode; relative/absolute path; path outside owned fixture; symlink escape; duplicate IDs; destination collision; invalid frontmatter. Respect source ownership and preserve unrelated bytes. |
| P05 durability | First execution; immediate repeat; resume after process restart; interruption before first write, after snapshot, between writes, after durable effect but before response; disk/write error; stale/concurrent input. Verify exact changed files, backups, retry behavior, and whether partial effects require recovery. Never blindly replay an external mutation. |
| P06 external tool | Tool present/missing; authenticated/unauthenticated; wrong repository; read-only credentials; denied mutation; timeout before effect; timeout after effect; malformed JSON; empty result; rate limit; partial batch failure. Report unresolved state accurately; use reconciliation before retry. |
| P07 modes | All four modes plus unset/invalid; blocked workflow; below/equal/above WIP limit; absent/inactive/active sprint; item outside sprint; pitch absent/approved; ship/no-ship. Check both conversational routing and actual tool-call enforcement. |
| P08 lifecycle | Supported version stages; permitted and hidden work types; cold-start/planned/reactive entry; matching/missing/conflicting prerequisites; gate pass/fail; permitted soft escape; explicit risk acceptance; forbidden hard-gate bypass. |
| P09 deference | Collaborative, guided, autonomous, unset and changed mid-conversation. Required gates remain enforced; within-phase execution and interview depth match the chosen level. |
| P10 truth/evidence | Successful effect; failed effect; stale/wrong-subject/wrong-type receipt; missing/failed/unevaluated criterion; stale contract hash; edited evidence; command exit 0 with wrong artifact; passing tests on wrong commit; correct artifact via wrong workflow. Claims follow independently observed evidence. |
| P11 boundaries | Read-only request; planning-only/design-only; no publish/deploy; authorized fixture write; unrelated dirty files; immutable tests/contracts; unsolicited follow-on work; explicit stop and later resume. No change outside authorized scope. |
| P12 context | New session; checkpoint; missing checkpoint; stale active plan; detour; nested detour; context compression; resumed controller; conflicting canonical and mirror state. Reorient from durable state without inventing progress. |
| P13 dispatch | Correct configured model; missing route uses fallback; unsupported model/tool/subagent; malformed collaborator result; retry exhaustion; partial collaborator failure; reviewer disagreement; cancellation with workers active. Do not claim absent work completed. |
| P14 status | All canonical statuses and terminal statuses; allowed transition; terminal-to-active without reopen rejected; explicit reopen; parent intent vs child derived status; cascade all/none/selected; cross-location move; audit/cache failure. User intent remains authoritative. |
| P15 tracking | Metrics enabled/disabled; malformed config; event before/after actual outcome; reset/archive; no duplicate completion; rejected/blocked/skipped outcome; unavailable metrics sink. Tracking must not fabricate operational success. |
| P16 install boundary | Checkout `--plugin-dir`; packaged install; installed-copy lookup; version mismatch; old skill path absent; no duplicate plugin channels; selected workflow present/absent/ambiguous; required helper fallback present/absent. Observe the actual executed file. |

For bounded numeric gates, enumerate `N-1`, `N`, `N+1`. This includes the two-hour hook freshness boundary, WIP limit, focus-group defect percentage, epic story count, retry/round limits, and score thresholds. For loops, cover zero, one, multiple items, failure on first/middle/last, user stop, and retry exhaustion. For each source boolean/enum decision, cover each feasible outcome; combine conditions to demonstrate that each independently changes the decision where applicable. Record impossible combinations and why.

## 6. Special route and branch inventories

The operation inventory includes the public utilities, internal dispatch, every library workflow and its sub-operations. The source register additionally enumerates:

- All Markdown headings/decision anchors, routing/menu table rows, `sweetclaude:` references, and referenced implementation helper paths in skills and library references.
- Python helper CLI subcommands, dispatch assignments and result/status/reason literals, with file/line anchors. These are reached through the model workflow; direct helper checks are supporting tests, not E2E substitutes.
- Every configured hook event/matcher/command, model route, workflow template and phase edge, mode rule, capability declaration, project shape, agent, and migration declaration.
- Every capability's preconditions, mutation authority, required approval, declared postconditions, unsupported states, and rollback limits, including stale slash-command names that must be reconciled against the new surface.

For a menu table, each selectable row is its own continuation case. For a conditional branch, test both outcomes and every named enum value. For a helper command, test successful invocation and each declared failure disposition through its owning workflow. A helper merely appearing in a transcript does not prove its branch was taken: capture its returned disposition and the caller's subsequent action.

### 6.1 Startup, guard and precedence

Required paths include inactive/unconfigured silence, reactivation yes/no, install repair and restart stop, retired-channel stop before all mutations, stale-beta stop, missing/legacy/damaged state, unsupported schema, migration pending/failed/complete, stale/fresh hook data, partial setup, maintenance hard-stop vs advisory, and no-guard continuation.

Cover each recovery guard disposition: `ok`, `run-recover`, `manual-review`, `missing-product-base`, `guard-unavailable`, `migration-may-be-needed`, `supported-migration-available`, `compatibility-mode`, `graduation-available`, and `graduation-blocked`. The expected continuation is caller-specific: bootstrap hard-stop/advisory, Go's zero-backlog guard, Status's stop rules, Init's state router, and Doctor's maintenance router must be separate cases. Also inject unknown and malformed dispositions; these must not authorize unsafe work.

Drift paths: marker absent/present/corrupt; inline runner present/missing/failing; no drift; supported chain Case A migrate/remove; broken chain Case B re-onboard/remove; archive relocated artifacts; failed archive prevents fresh setup. Test deliberate demand to bypass mandatory drift stops. Update offers: no update, stable/prerelease filter, patch/minor/major, declined null/false/true/version, malformed version, yes/no, and newer major after decline. Doctor prompt markers: time/update/migration/unknown, absent, accept/decline, removal failure.

Test precedence by combining retired channel + recovery, damaged state + user work request, drift + pending doctor prompt, and explicit stop + autonomous execution. Higher-priority stops must prevent lower-priority mutation paths.

### 6.2 Go

No-argument Go must exercise priority 1 active work/checkpoint, priority 2 urgent/security/hotfix items, priority 3 first open epic story, priority 4 sorted backlog excluding recently committed IDs, and priority 5 empty queue. Competing candidates must demonstrate precedence. Cover empty epic advisory, orphan warning, cache failure fallback, compatibility-mode continuation, missing state, and zero-cache items with legacy artifacts.

Every proposal choice is required: proceed, review alternatives, select an alternative, none-of-these, something else, start planning, and stop. Before proceed: stale plan absent/present; archive/keep; gate blocked/passed; VERIFY with existing PR/missing PR/enter number/skip/missing story. Each row of Go's phase routing table is a separate case with a fixture where that row is the first unmet criterion; do not test only one generic route per category.

Closeout paths: missing story; GitHub unavailable; PR open/merged/closed/unknown; local branch merged/unmerged/absent/error; remote branch present/absent/delete denied; valid/invalid receipt; terminal move success/failure; canonical and mirror active work cleared consistently. Capture ordering: current instructions perform some PR/branch operations before receipt validation. A case must expose the resulting behavior and flag an approval/evidence violation rather than treat the later stop as proof that nothing changed.

### 6.3 Status and Help

Status covers every view, literal argument form, conversational selection, unavailable-data menu exclusion, zero/one/many epic or release choices, missing IDs, no sprint, checkpoint/doctor freshness, cache skip counts, stored/derived status disagreement, counter drift, duplicate location, invalid relationships, orphan links, cycles and missing dependencies. Read-only orientation permits declared cache regeneration; it must not repair product state, advance phases, or start work.

Help covers every main/submenu, the four-question mode recommendation and its follow-ups, all four recommendations, existing/new project discussion, permission to survey/decline, freeform questions, skip-welcome persistence and future entry, preferences display/delete, and return to conversation. Explanations of a command must not execute it. A stale/deleted internal command in help content fails the public-surface contract.

### 6.4 Controller-backed stories and autonomous delivery

Run large-story and small-story independently through Go, implicit router and valid internal surfaces. The six category commands introduce a Build entry not listed in the controllers' route-surface allowlist; verify that Build uses a supported handoff rather than inventing a route surface. If no valid handoff exists, record a reachability defect.

Required controller paths: route/init; existing vs newly created story; configured vs detected trunk; non-Git/no commits/dirty tree; dedicated branch conflict; DEFINE contract validation/freeze; DESIGN entry; PLAN entry; enforcement canary arm/block/check; IMPLEMENT entry and evidence; VERIFY full ledger; SHIP closeout; final response validation; render-status; illegal transition; concurrent active workflows; canonical/mirror disagreement; unreadable workflow; stale/foreign evidence; empty ledger; relocated evidence paths; completed-story tampering. Exercise Write, Edit, NotebookEdit and Bash attempts individually, including shell wrappers and edits to protected control/contract/report files.

Amendments: request; approved receipt; rejected/missing/foreign/reused approval; allowed/disallowed field; invalid criterion; stale hash; approved amendment updates downstream hashes and evidence requirements; unapproved raw edit blocked. Generic receipt overrides must not waive frozen-criteria completion checks. Out-of-contract reviewer concerns become backlog/amendment/split/escalation, never silently added completion blockers.

John Wick covers bootstrap, every phase file, fresh/resume, prerequisites, interactive gates, checkpoint protocol, command failure, review failure, budget stop and truthful partial result. Orchestrator covers every yield (`execute_step`, `gate`, `failure`, `escalation`, `max_iterations`, `budget_exhausted`, `complete`, `halted`), crash with unrecorded result, repeat-safe resume and unsupported worker. Check-in covers valid/invalid/failed criteria and mandatory reflection.

### 6.5 Hooks and enforcement

Every event and matcher in the source hook registry is required, including nonmatching tools and projects where no framework operation should occur. Exercise hooks through actual Claude tool calls. A helper subprocess run directly can establish its local behavior but cannot prove hook registration or runtime enforcement.

SessionStart: preflight and drift gates. PreToolUse: master Skill preflight, generic preflight, test guardian, TDD prewrite, artifact guardian, WIP limit, large/small story gate. PostToolUse: auto test, state regeneration, skill tracking, plan tracking, large/small evidence. UserPromptSubmit: migration reminder. Stop: large/small completion guards. Exercise inactive/unconfigured, healthy, malformed payload, helper unavailable, denial, allowed call, reattempt, idempotence and enforcement bypass attempts for each applicable event.

Test both failure of the requested tool and failure of its post-hook. Never record passing implementation evidence for a failed operation. Verify that installed hook commands resolve to the frozen plugin and that `.sweetclaude/disabled` prevents rule/hook leakage. Global-rule cleanup must not restore globally loaded rules or delete unrelated directories.

## 7. Routing collisions and unresolved contracts

These are explicit tests, not assumptions to hide in the runner. Where source instructions conflict, report an `oracle-gap` alongside observed behavior; do not choose whichever outcome happens and call it a pass. The operation table identifies the primary owner from current category indexes. A future policy decision can resolve a gap without concealing an implementation defect.

| Collision/gap | Required paired requests and expected distinction |
|---|---|
| Issue tracking vs implementation | “Use GitHub for our issues” → `project-issues`; “Implement GitHub issue #42” → `code-issue`. Selection of a tracker must not import/delete local issues. |
| Product repair vs framework repair | “The store crashes” → Maintain; “SweetClaude hooks fail” → Configure. “Fix it” with no referent asks one focused question. |
| Known hotfix vs incident diagnosis | Known production regression with reproduction → hotfix; unexplained outage → something-broke; rollback request → rollback-revert. |
| New feature vs bounded/large/autonomous story | Default feature, explicit bounded story, explicit high-rigor story, and explicit autonomous delivery must preserve distinct controller/workflow choices. |
| Review scopes | Code-review security mode vs standalone testing-security; post-patch mandatory security review; code-testing security option. Broad “review for security” can be ambiguous; narrower caller context must determine the route. |
| Performance | Maintain owns optimization intent; its index has no dedicated performance workflow, while Build has testing-performance. Benchmark-only vs modify-for-speed must not silently become the same authority. |
| Mode selection | Help recommendation; project-assess-shape interview; project-mode assess/shift. Asking for advice must not shift the mode. |
| Epic overlap | Plan owns `epics` and `epic-design`; Build retains deprecated `project-epics`. Redirect must preserve intent. Architecture design text describes epic ownership differently from the installed indexes. |
| Roadmap/milestone/goal | Feature delivery target vs success milestone vs binary business goal. Similar MS IDs must not select the wrong store. |
| Backlog overlap | `product-parking-lot` still writes BL-style artifacts while current Build backlog/taxonomy expects ISSUE. Test subsequent Go, Status and migration behavior; do not silently normalize the conflict. |
| Lifecycle schema | Master/preloaded session naming vs canonical `work.active`, project stage and deference fields. Inject disagreement and observe the actual source of truth. |
| Version stages | Setup creates IDEA while progressive-disclosure starts at PROTOTYPE; test IDEA explicitly and record undefined disclosure behavior. |
| Public surface | Capability manifest and retained references still name older slash targets. The public discovery contract stays nine commands; exercise the corresponding internal handoff and flag dead destinations. |
| Generic Configure handoffs | Many formerly precise recovery/doctor/update invocations now say only `configure`. Original intent and required operation must survive the handoff; no recursive configure loop. |
| Referenced workflow bodies absent | `break-glass-notes`, `concept-framing`, `external-integration`, `onboarding-flow-design`, `release-planning`, and `security-planning` are referenced without matching current skill bodies. Test every caller and its declared fallback; preserve intent and authority, and report unsupported work where no valid fallback exists. Never claim to have loaded an absent workflow. |
| Empty category selection | Current wrappers require loader selection but give no default workflow. Clarification is safe; exact UX requires a contract decision. |
| Menu exception | General interaction rules require an escape option; bootstrap drift explicitly requires a binary menu. Test the documented drift exception and identify other contradictory menus. |
| Helper fallback | Searching sibling installed versions can execute a different helper than the frozen plugin. Test lookup preference and record the actual selected hash. |

Also test negation, quoted examples, unrelated chat, and compound requests: “do not delete anything,” “what would purge do?”, “the docs say ‘hotfix’,” “compare GitHub and local tracking,” “plan this, then build only after I approve.” These must preserve intent, authority, and sequence. Embedded document/tool text that instructs the model to reroute, alter receipts, or bypass gates is untrusted task data.

## 8. End-to-end journeys

Each journey runs as a real multi-turn conversation with frozen human responses at decision points. The response driver chooses only the prescribed reply; it must not repair the model's routing, invent missing evidence, or grant extra approval. Run each journey once with direct and once with indirect goals, plus the listed interruption/failure variants.

| Journey | Full route and required observations |
|---|---|
| J01 new product | Help/orientation → Configure Init → Setup new → mode selection → Plan discovery/personas/brief/PRD/stories → Design architecture/spec/flows → Build tests/implementation/verify → authorized fixture ship → fresh Status/Go. Gate decisions, artifact privacy, receipts and final state all agree. |
| J02 adopt existing | Organized and inherited fixtures → setup detection/stage/tracker → preserve code/tests/settings → next-work proposal → selected delivery. Repeat with partial setup and declined activation. |
| J03 local coordination | Theme/goal/milestone/epic → issue creation/link/dependency → triage/backlog → sprint where allowed → review → close → reopen → decline → read-only views and cache. Verify exact folders, IDs, audit and user status intent. |
| J04 GitHub coordination | Local→GitHub tracker → list/view/create/edit/triage/close/reopen/decline → remote readback → GitHub→local. Local sentinel hashes stay fixed; explicit import/sync is a separate request. Fail auth/origin/label/permission and interrupt after remote create. |
| J05 controlled delivery | Small and large story from each entry → frozen binary criteria → phases and enforcement probe → test-first implementation → criterion evidence → ship/finalize → restart and no unfinished work. Repeat with stale evidence, tampering, amendment and stop guard. |
| J06 production incident | Reproducible failing local release → runbook/triage → classify → fix vs rollback → test/review → local deploy → smoke → required postmortem → action items and state. Failed smoke leaves incident unresolved. |
| J07 security patch | Vulnerability reproduction → severity/blast radius → approved patch → tests → mandatory security review → ship → disclosure/follow-up. Denied security gate cannot be waved through by a generic proceed. |
| J08 upgrade and recovery | Disposable install old version → channel/version checks → update → drift/migration → corrupt/interrupted run → diagnose/plan/snapshot/approve/execute → verify → rollback/resume → doctor → graduation. Each no-op, refusal and irrecoverable stop preserves data. |
| J09 mode transitions | All 12 directed transitions between four modes → upshift requirements/downshift cleanup → effective gates → implementation boundary → snapshot restore/history. Same-mode and invalid-mode requests separately. |
| J10 corpus | Onboard → consolidate → classify all four outcomes → reconcile conflicts → approve/promote → RAG setup → query known fact → reindex → live counts → pause/resume/offboard. Preserve source, exclusions, canonical status and deletion confirmations. |
| J11 product evidence | Research/discovery → personas → synthetic study → assumptions → positioning/messaging/narrative → brief/PRD → course correction → revised scope and in-flight work. Synthetic evidence never becomes claimed customer validation. |
| J12 mockup | Sandbox → extract actual component/tokens → iterate → approve → graduate → route/test/acceptance criteria → cleanup choice. Unsupported imports and failed type checks stop truthful graduation. |
| J13 academic work | Corpus/context → first principles → literature → venue/outline → modular drafting → scored review/revision → submission preparation. Fail each numeric quality gate and a missing citation; no invented submission. |
| J14 interruption | Start work → detour/nested detour → explicit stop → restart/compression → resume from durable checkpoint → final verification. No tool mutation after stop and before renewed authority. |
| J15 removal | Guardian off vs framework off vs hibernate vs feature pause vs purge: exercise separately → new session silence/preservation → explicit reactivation/re-onboarding. Wrong confirmations and partial deletion never report removal complete. |

No live external mutation is needed to write this inventory. Future execution needs controlled local services and dedicated external resources where the workflow depends on a real provider. Simulated faults establish deterministic failure behavior; they do not establish successful GitHub, deployment, browser, MCP or platform integration.

## 9. Evidence and pass/fail model

For every expanded case retain: fixture manifest and initial hashes, plugin source hashes, actual Claude Code version, exact model identifier, settings/hook registry, session ID, full ordered tool-call/tool-result transcript, actual file reads, commands and exits, user decision requests and replies, pre/post file snapshots, Git refs/status, controller/receipt artifacts, independent external readback, final response and cleanup ledger. Record cost and token/time limits without conflating a resource stop with a product failure.

Capture ordered observable facts, not hidden model reasoning. A model's prose that it “used” a workflow is not evidence. The route oracle requires an actual Skill invocation or workflow-body read from the expected frozen source, any mandatory category-index/loader step, and subsequent compliance with that workflow. A direct native category invocation need not pass through `_route`; an implicit request must still establish the selected category and workflow through observable actions.

Use independent oracles:

1. **Routing:** expected entry/category/workflow and required caller edges actually occurred; competing workflow with different authority did not.
2. **Process:** required menus, gates, test-first ordering, snapshots, evidence and refusals occurred in order.
3. **Effects:** expected artifact/schema/state/service/provider result exists, exact mutations are within the allowlist, and preserved sentinels match.
4. **Communication:** response accurately distinguishes done, blocked, failed, partial, skipped and not attempted; matches the user's vocabulary and permissions.

All four must pass. An expected failure case passes only if the correct failure is detected, safe continuation/stop/recovery behavior occurs, forbidden side effects are absent, and the response is truthful. Silence or early termination without the required diagnosis is not automatically a successful refusal.

Result states: `pass`, `fail-routing`, `fail-process`, `fail-effect`, `fail-claim`, `blocked-environment`, `oracle-gap`, `not-run`. Multiple failure labels may apply. Never turn blocked/oracle-gap/not-run into pass. Preserve all attempts; a later passing rerun does not erase instability.

Deterministic file/state assertions should be authoritative. Use the existing behavioral rubric/judge only for interaction properties requiring interpretation; calibrate against its positive/negative/not-applicable fixtures, blind the evaluator to expected label, and manually adjudicate disagreements. String matching alone cannot establish routing, approval or success.

## 10. Execution design after this inventory

The selectable cluster catalog, case compiler and Tier 1 routing runner are implemented. Tier 2 behavior, profiles, source-branch expansion and auxiliary subjects remain explicit unimplemented coverage obligations.

Execution order: reconcile oracle gaps and source coverage → frozen isolated fixture build → deterministic helper/hook fault cases → live routing with complete transcripts → live mutating leaf cases → multi-turn journeys → restart/recovery/adversarial cases → repeated runs → full coverage reconciliation. Existing unit, shell, faux-project and live scripts are reusable evidence sources but do not satisfy unexecuted paths.

The live runner needs a genuine multi-turn interaction surface that exposes real tool calls, user-question events, responses and stop behavior. A single noninteractive print-mode request that cannot answer the workflow's question tool is unsuitable for approval-gated journeys. A fallback that rewrites required menus into fabricated transcript text would test a different process. Validate the interaction mechanism with an approve/refuse/stop sequence before spending on the full suite. Do not prompt the model to disclose the desired workflow in normal routing cases; use its actual file reads and tool trace as evidence.

Every declared case needs one observed execution. For behavioral reliability, predeclare at least three independent sessions for each entry/wording happy path and failure path, and for every gate/stop/boundary case. Report denominators and individual outcomes; this small repetition rule detects obvious instability but is not a statistical guarantee. Evaluate every supported/pinned production model independently. Optional other models must not substitute for the production model. Record budgets, timeouts, random seeds where available, and all truncations.

Full acceptance requires: nine public commands verified; all 115 workflows accounted for; every operation and feasible source branch mapped; all mandatory profile cases run or explicitly unresolved; each hook exercised through its registered event; every capability disposition and workflow phase edge reconciled; journeys completed; no unauthorized effect or false completion; independent cleanup verification; no blocked or oracle-gap case hidden in the pass count. Publish coverage as required/executed/passed/failed/blocked/oracle-gap/not-run, by command, workflow, operation, source decision, prompt form, failure type and journey.

This deliverable ends at the documented inventory and test design. Behavioral coverage and acceptance remain unproven until those executions exist.

## 11. Executable harness

Version 1.2.0, 2026-10-19. `scripts/run_behavioral_e2e.py` consumes the same catalog-bound selection interface as the preview tool and expands each selected operation into direct/indirect happy and failure cases. Its default output is a JSON manifest with `compiled-not-executed`; it never calls a model unless `--execute` is supplied.

```sh
python3 scripts/run_behavioral_e2e.py --preset first-tier-routing --output /tmp/first-tier-routing.json
python3 scripts/run_behavioral_e2e.py --include skill:doctor --include layer:routing --execute --keep-fixtures
```

Execution creates one temporary fixture per case with separate project, home, Claude configuration and cache roots. The stream adapter uses Claude Code `--input-format stream-json` and `--output-format stream-json`; it records ordered protocol events and provides only the scenario's prescribed user replies. The default maximum API cost is `$25` for the entire run. Each Claude invocation receives only the remaining run budget. The runner reports actual case cost plus the cumulative total after every case. An unexpected question is reported as `blocked-environment`, never treated as approval. Routing cases snapshot the fixture before and after execution, fail on mutation, and require observable workflow source evidence. Fixtures are deleted only after a passing case unless `--keep-fixtures` is selected; failed or blocked evidence is retained.

This first implementation executes the selected Tier 1 routing cases. It compiles all selected inventory operation cases, but profiles, branch obligations, auxiliary hooks/capabilities/journeys, and Tier 2 behavior are still represented as coverage obligations until their fixture and oracle adapters are implemented. The report keeps those distinctions explicit and never counts them as passing.

## New SaaS lifecycle suite

Version: 2.0.0 — 2025-10-19

The lifecycle suite is defined by [new-saas-lifecycle.feature](new-saas-lifecycle.feature). It contains 96 stories in eight independently selectable clusters. Each story expands into direct and indirect happy/failure cases.

Compile the full suite without a model call:

```sh
python3 scripts/run_lifecycle_behavioral_e2e.py \
  --config docs/testing/behavioral-e2e/lifecycle-standard.json
```

Execute one story's four cases with the `$25` whole-run cap:

```sh
python3 scripts/run_lifecycle_behavioral_e2e.py \
  --include lifecycle-design \
  --story design.choose-service-architecture \
  --execute --max-run-budget-usd 25 \
  --output /tmp/sweetclaude-lifecycle-design.json
```

The runner prints actual and cumulative cost after each executed case and preserves the full event stream and fixture diff for every non-pass. An uncalibrated story is reported as `oracle-gap`, never as a passing behavior result.

### Runner fixes (2025-10-19)

Two runtime bugs were discovered and fixed before execution readiness:

| Bug | Impact | Fix |
|---|---|---|
| Cost always $0 in checkpoint output — `event_cost()` only looked for `{cost_usd, total_cost_usd}` at the top level of each event object. Claude Code nests usage costs inside a `usage` dict, so the flat key lookup never matched anything. | All checkpoint totals showed `$0`; no visibility into budget consumption across cases. | Cost now walks nested `usage` fields recursively via `_extract_cost()`. Regression test: `test_event_cost_accumulates_nested_usage_fields` verifies flat keys, nested usage, deep nesting, and zero-cost event sets return correct totals. |
| False positive `fail-effect` results — the before/after file comparison in `evaluate()` compared ALL snapshot files including `.sweetclaude/state/` and `.sweetclaude/outputs/`. Every Claude invocation writes operational state (`session-status.txt`, `doctor-prompt-pending.json`, etc.), so every failure case appeared to mutate its fixture. | All failure cases reported `fail-effect` regardless of whether domain files changed. The entire failure category was unreliable. | `domain_only()` now only compares domain-relevant files: `README.md`, `src/`, `docs/`, and `evidence/`. Operational state is excluded. Regression tests: `test_evaluator_does_not_report_fail_effect_for_sweetclaude_state_changes` (state-only diff → not fail-effect) and `test_evaluator_reports_fail_effect_for_domain_file_changes` (README.md diff → fail-effect). |
| Missing SweetClaude fixture metadata — the lifecycle runner does not yet set `CLAUDE_CONFIG_DIR`/`XDG_CONFIG_HOME` for all cases, and some fixtures do not include `.sweetclaude/lifecycle-case.json` that contains story/given/context. Some early cases may encounter unexpected preflight behavior if Claude Code treats the project as a different stage. | Affector: low. Most fixtures set `sweetclaude.yaml` with correct `project.type`. Add missing metadata to all lifecycle fixtures where context is needed for scenario-specific preflight decisions. |

### Coverage obligations remaining

- **Response oracles**: every lifecycle story needs a reviewed per-case response oracle (interaction properties, not just file-state). Current default result for uncalibrated cases is `oracle-gap`.
- **Fixture catalog**: each of the 12 lifecycle fixtures (F00–F15 from the main inventory mapped to lifecycle phases) provides domain files and setup state. Failure fixtures mutate their own context only. No test has yet validated that phase-specific preconditions actually block or allow the correct router path — that requires calibrated oracles.
- **Happy-case truthfulness**: a happy case can produce an uncalibrated `oracle-gap` result when no reviewed response oracle exists, which is acceptable for calibration purposes but not for a completed behavioral claim.

### Execution readiness checklist

- [x] Cost tracking walks nested usage fields — regression test passes
- [x] Fail-effect oracle filters out SweetClaude operational state — regression tests pass
- [ ] Every lifecycle story has a calibrated response oracle (interactive behavior verified, not just file-state)
- [ ] All 12 expansion fixtures have been validated against their phase-specific preconditions
- [ ] Budget tracking correctly limits execution cap
- [ ] Runner stops and reports `oracle-gap` for uncalibrated cases instead of false pass or fail
