# SweetClaude Capability Ledger

**Declared capabilities:** 131
**Works:** 83  ·  **Compromised:** 24  ·  **Broken:** 2  ·  **Not mechanically verifiable:** 22

A capability with no verification path is reported as broken, never
omitted — an omitted capability is indistinguishable from a working one.

| Capability | Tier | Status | Notes |
|---|---|---|---|
| `code.debt` | tier-1-structural | **works** |  |
| `code.deploy_ship` | tier-3-behavioral | **compromised** | rollback carries limitations: state written before the failure point is not unwound |
| `code.feature` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `code.hotfix` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `code.incident` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `code.issue` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `code.john_wick` | tier-1-structural | **compromised** | rollback carries limitations: an interrupted run resumes rather than unwinding |
| `code.john_wick_checkin` | tier-1-structural | **works** |  |
| `code.large_story` | tier-2-executable | **compromised** | rollback carries limitations: committed work on the story branch is discarded |
| `code.orchestrator` | tier-2-executable | **compromised** | rollback carries limitations: side effects of completed steps are not undone |
| `code.postmortem` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `code.review` | tier-1-structural | **works** |  |
| `code.rollback_revert` | tier-3-behavioral | **compromised** | rollback carries limitations: data written between deploy and revert is not restored |
| `code.security_patch` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `code.small_story` | tier-2-executable | **compromised** | rollback carries limitations: committed work on the story branch is discarded |
| `code.tdd` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `code.testing` | tier-1-structural | **works** |  |
| `code.ultraplan` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `code.verify` | tier-2-executable | **works** |  |
| `config.audit_redirect` | tier-1-structural | **works** |  |
| `corpus.consolidate` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `corpus.pipeline` | tier-2-executable | **works** |  |
| `corpus.promote` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `corpus.rag_reindex` | tier-1-structural | **works** |  |
| `corpus.rag_setup` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `corpus.reconcile` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `corpus.status` | tier-2-executable | **works** |  |
| `corpus.triage` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `design.api_design` | tier-1-structural | **works** |  |
| `design.architecture` | tier-1-structural | **works** |  |
| `design.change_impact` | tier-1-structural | **works** |  |
| `design.data_model` | tier-1-structural | **works** |  |
| `design.decisions` | tier-1-structural | **works** |  |
| `design.mockup_extract` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `design.mockup_graduate` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `design.mockup_sandbox` | tier-2-executable | **works** |  |
| `design.solutioning_gate` | tier-1-structural | **works** |  |
| `design.tech_spec` | tier-1-structural | **works** |  |
| `design.user_flows` | tier-1-structural | **works** |  |
| `design.ux` | tier-1-structural | **works** |  |
| `design.ux_review` | tier-1-structural | **works** |  |
| `design.wireframes` | tier-1-structural | **works** |  |
| `doctor.auto_fix` | tier-2-executable | **works** |  |
| `doctor.compatibility_mode` | tier-2-executable | **works** |  |
| `doctor.fix_graduation_blockers` | tier-2-executable | **works** |  |
| `doctor.manual_review` | tier-2-executable | **works** |  |
| `doctor.restore` | tier-2-executable | **compromised** | rollback carries limitations: restores only files a doctor run itself changed |
| `doctor.scan` | tier-2-executable | **works** |  |
| `documents.academic` | tier-1-structural | **works** |  |
| `documents.meeting_prep` | tier-1-structural | **works** |  |
| `documents.narrative_arc` | tier-1-structural | **works** |  |
| `documents.report_failure` | tier-2-executable | **works** |  |
| `documents.session_export` | tier-1-structural | **works** |  |
| `documents.update_docs` | tier-1-structural | **works** |  |
| `features.configure` | tier-2-executable | **compromised** | rollback carries limitations: onboarding side effects of a newly-enabled feature are not unwound by flipping its status back |
| `fix.sweetclaude_redirect` | tier-1-structural | **works** |  |
| `guardian.disable` | tier-2-executable | **compromised** | rollback carries limitations: state written before the failure point is not unwound |
| `guardian.enable` | tier-2-executable | **compromised** | rollback carries limitations: state written before the failure point is not unwound |
| `health.scan` | tier-2-executable | **compromised** | rollback carries limitations: state written before the failure point is not unwound |
| `hooks.repair_redirect` | tier-1-structural | **works** |  |
| `init.dispatch` | tier-2-executable | **works** |  |
| `install.feature_setup` | tier-1-structural | **compromised** | rollback carries limitations: state written before the failure point is not unwound |
| `metrics.usage` | tier-2-executable | **compromised** | rollback carries limitations: state written before the failure point is not unwound |
| `migrate.diagnose_redirect` | tier-1-structural | **works** |  |
| `migrate.flat_bl_to_issue` | tier-2-executable | **works** |  |
| `migrate.orchestrate` | tier-2-executable | **compromised** | rollback carries limitations: state written before the failure point is not unwound |
| `migrate.typed_legacy_backlog` | tier-2-executable | **works** |  |
| `product.brief` | tier-1-structural | **works** |  |
| `product.competition` | tier-1-structural | **works** |  |
| `product.discovery` | tier-1-structural | **works** |  |
| `product.focus_group` | tier-2-executable | **works** |  |
| `product.manage_scope` | tier-1-structural | **works** |  |
| `product.market_messaging` | tier-1-structural | **works** |  |
| `product.milestone_planning` | tier-2-executable | **works** |  |
| `product.milestones` | tier-1-structural | **works** |  |
| `product.parking_lot` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `product.personas` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `product.positioning` | tier-1-structural | **works** |  |
| `product.prd` | tier-1-structural | **works** |  |
| `product.research` | tier-1-structural | **works** |  |
| `product.roadmap` | tier-2-executable | **works** |  |
| `product.roadmap_analysis` | tier-2-executable | **works** |  |
| `product.sprint_plan` | tier-1-structural | **works** |  |
| `product.terminology` | tier-2-executable | **works** |  |
| `product.user_stories` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `product.user_tdd_tests` | tier-1-structural | **works** |  |
| `project.assess_shape` | tier-2-executable | **works** |  |
| `project.backlog` | tier-2-executable | **works** |  |
| `project.backlog_triage` | tier-2-executable | **compromised** | rollback carries limitations: audit log retains the intermediate transition |
| `project.course_correction` | tier-2-executable | **works** |  |
| `project.deactivate` | tier-2-executable | **compromised** | rollback carries limitations: state written before the failure point is not unwound |
| `project.epic_design` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `project.epics` | tier-2-executable | **compromised** | rollback carries limitations: audit log retains the intermediate transition |
| `project.epics_redirect` | tier-1-structural | **works** |  |
| `project.gh_import` | tier-2-executable | **works** |  |
| `project.gh_sync` | tier-2-executable | **compromised** | rollback carries limitations: audit log retains the intermediate transition |
| `project.goals` | tier-2-executable | **works** |  |
| `project.hibernate` | tier-1-structural | **compromised** | rollback carries limitations: state written before the failure point is not unwound |
| `project.issues` | tier-2-executable | **compromised** | rollback carries limitations: audit log retains the intermediate transition |
| `project.mode` | tier-2-executable | **works** |  |
| `project.retro` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `project.scope` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `project.sprints` | tier-2-executable | **compromised** | rollback carries limitations: audit log retains the intermediate transition |
| `project.themes` | tier-2-executable | **works** |  |
| `purge.remove_all` | tier-2-executable | **compromised** | rollback carries limitations: only if the recommended backup branch was created first; gitignored content is not recoverable from git alone |
| `quality.artifact_lint` | tier-2-executable | **broken** | entrypoint script scripts/artifact_lint.py not found |
| `quality.rubric_judge` | tier-3-behavioral | **broken** | entrypoint script scripts/artifact_judge.py not found |
| `recover.graduate_from_compatibility` | tier-2-executable | **works** |  |
| `recover.stabilize_without_migration` | tier-2-executable | **works** |  |
| `report.big_picture` | tier-2-executable | **works** |  |
| `report.dashboard` | tier-1-structural | **works** |  |
| `report.next_steps` | tier-2-executable | **works** |  |
| `report.recap` | tier-2-executable | **works** |  |
| `report.status` | tier-2-executable | **works** |  |
| `session.bootstrap` | tier-2-executable | **works** |  |
| `session.find_skill` | tier-2-executable | **works** |  |
| `session.go` | tier-2-executable | **works** |  |
| `session.help` | tier-2-executable | **compromised** | rollback carries limitations: a removed learning is not recoverable from the state file itself |
| `session.master` | tier-1-structural | **works** |  |
| `session.route` | tier-1-structural | **works** |  |
| `setup.onboard_project` | tier-2-executable | **compromised** | rollback carries limitations: purge removes all SweetClaude artifacts, not just this run's |
| `testing.accessibility` | tier-2-executable | **works** |  |
| `testing.behavioral_regression` | tier-3-behavioral | **not-mechanically-verifiable** | Tier 3 with no instrument: no rubric covers this postcondition, so nothing scores it today |
| `testing.compliance` | tier-2-executable | **works** |  |
| `testing.performance` | tier-2-executable | **works** |  |
| `testing.plan` | tier-2-executable | **works** |  |
| `testing.security` | tier-2-executable | **works** |  |
| `testing.session` | tier-2-executable | **works** |  |
| `update.check` | tier-2-executable | **works** |  |
| `update.framework_sync` | tier-2-executable | **works** |  |
| `work_item_artifacts.backfill` | tier-2-executable | **works** |  |

