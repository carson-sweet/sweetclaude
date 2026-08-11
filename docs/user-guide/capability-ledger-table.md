# SweetClaude Capability Ledger

**Declared capabilities:** 110
**Works:** 87  ·  **Compromised:** 18  ·  **Broken:** 5  ·  **Not mechanically verifiable:** 0

A capability with no verification path is reported as broken, never
omitted — an omitted capability is indistinguishable from a working one.

| Capability | Tier | Status | Notes |
|---|---|---|---|
| `code.debt` | tier-1-structural | **works** |  |
| `code.feature` | tier-1-structural | **works** |  |
| `code.hotfix` | tier-1-structural | **works** |  |
| `code.incident` | tier-1-structural | **works** |  |
| `code.issue` | tier-1-structural | **works** |  |
| `code.john_wick` | tier-1-structural | **compromised** | rollback carries limitations: an interrupted run resumes rather than unwinding |
| `code.large_story` | tier-2-executable | **compromised** | rollback carries limitations: committed work on the story branch is discarded |
| `code.orchestrator` | tier-2-executable | **compromised** | rollback carries limitations: side effects of completed steps are not undone |
| `code.postmortem` | tier-1-structural | **works** |  |
| `code.review` | tier-1-structural | **works** |  |
| `code.rollback_revert` | tier-1-structural | **compromised** | rollback carries limitations: data written between deploy and revert is not restored |
| `code.security_patch` | tier-1-structural | **works** |  |
| `code.small_story` | tier-2-executable | **compromised** | rollback carries limitations: committed work on the story branch is discarded; entrypoint coverage 70% is below 80% |
| `code.tdd` | tier-1-structural | **works** |  |
| `code.testing` | tier-1-structural | **works** |  |
| `code.ultraplan` | tier-1-structural | **works** |  |
| `code.verify` | tier-2-executable | **works** |  |
| `config.audit_redirect` | tier-1-structural | **works** |  |
| `corpus.consolidate` | tier-1-structural | **works** |  |
| `corpus.pipeline` | tier-1-structural | **works** |  |
| `corpus.promote` | tier-1-structural | **works** |  |
| `corpus.rag_reindex` | tier-1-structural | **works** |  |
| `corpus.rag_setup` | tier-1-structural | **works** |  |
| `corpus.reconcile` | tier-1-structural | **works** |  |
| `corpus.status` | tier-1-structural | **works** |  |
| `corpus.triage` | tier-1-structural | **works** |  |
| `design.api_design` | tier-1-structural | **works** |  |
| `design.architecture` | tier-1-structural | **works** |  |
| `design.change_impact` | tier-1-structural | **works** |  |
| `design.data_model` | tier-1-structural | **works** |  |
| `design.decisions` | tier-1-structural | **works** |  |
| `design.mockup_extract` | tier-1-structural | **works** |  |
| `design.mockup_graduate` | tier-1-structural | **works** |  |
| `design.mockup_sandbox` | tier-1-structural | **works** |  |
| `design.solutioning_gate` | tier-1-structural | **works** |  |
| `design.tech_spec` | tier-1-structural | **works** |  |
| `design.user_flows` | tier-1-structural | **works** |  |
| `design.ux` | tier-1-structural | **works** |  |
| `design.ux_review` | tier-1-structural | **works** |  |
| `design.wireframes` | tier-1-structural | **works** |  |
| `doctor.auto_fix` | tier-2-executable | **works** |  |
| `doctor.compatibility_mode` | tier-1-structural | **broken** | no verification_commands declared |
| `doctor.fix_graduation_blockers` | tier-2-executable | **works** |  |
| `doctor.manual_review` | tier-1-structural | **broken** | no verification_commands declared |
| `doctor.restore` | tier-2-executable | **compromised** | rollback carries limitations: restores only files a doctor run itself changed |
| `doctor.scan` | tier-2-executable | **works** |  |
| `documents.academic` | tier-1-structural | **works** |  |
| `documents.meeting_prep` | tier-1-structural | **works** |  |
| `documents.narrative_arc` | tier-1-structural | **works** |  |
| `documents.report_failure` | tier-1-structural | **works** |  |
| `documents.session_export` | tier-1-structural | **works** |  |
| `documents.update_docs` | tier-1-structural | **works** |  |
| `fix.sweetclaude_redirect` | tier-1-structural | **works** |  |
| `hooks.repair_redirect` | tier-1-structural | **works** |  |
| `init.dispatch` | tier-1-structural | **works** |  |
| `migrate.diagnose_redirect` | tier-1-structural | **works** |  |
| `migrate.flat_bl_to_issue` | tier-2-executable | **compromised** | entrypoint coverage 79% is below 80% |
| `migrate.typed_legacy_backlog` | tier-2-executable | **works** |  |
| `product.brief` | tier-1-structural | **works** |  |
| `product.competition` | tier-1-structural | **works** |  |
| `product.discovery` | tier-1-structural | **works** |  |
| `product.focus_group` | tier-1-structural | **works** |  |
| `product.manage_scope` | tier-1-structural | **works** |  |
| `product.market_messaging` | tier-1-structural | **works** |  |
| `product.milestone_planning` | tier-1-structural | **works** |  |
| `product.milestones` | tier-1-structural | **works** |  |
| `product.parking_lot` | tier-1-structural | **works** |  |
| `product.personas` | tier-1-structural | **works** |  |
| `product.positioning` | tier-1-structural | **works** |  |
| `product.prd` | tier-1-structural | **works** |  |
| `product.research` | tier-1-structural | **works** |  |
| `product.roadmap` | tier-1-structural | **works** |  |
| `product.roadmap_analysis` | tier-1-structural | **works** |  |
| `product.sprint_plan` | tier-1-structural | **works** |  |
| `product.terminology` | tier-1-structural | **works** |  |
| `product.user_stories` | tier-1-structural | **works** |  |
| `product.user_tdd_tests` | tier-1-structural | **works** |  |
| `project.assess_shape` | tier-1-structural | **works** |  |
| `project.backlog` | tier-2-executable | **compromised** | entrypoint coverage 72% is below 80% |
| `project.backlog_triage` | tier-2-executable | **compromised** | rollback carries limitations: audit log retains the intermediate transition |
| `project.course_correction` | tier-2-executable | **compromised** | entrypoint coverage 72% is below 80% |
| `project.epic_design` | tier-1-structural | **works** |  |
| `project.epics` | tier-2-executable | **compromised** | rollback carries limitations: audit log retains the intermediate transition |
| `project.epics_redirect` | tier-1-structural | **works** |  |
| `project.gh_import` | tier-2-executable | **compromised** | entrypoint coverage 72% is below 80% |
| `project.gh_sync` | tier-2-executable | **compromised** | rollback carries limitations: audit log retains the intermediate transition |
| `project.goals` | tier-1-structural | **works** |  |
| `project.issues` | tier-2-executable | **compromised** | rollback carries limitations: audit log retains the intermediate transition |
| `project.mode` | tier-1-structural | **works** |  |
| `project.retro` | tier-1-structural | **works** |  |
| `project.scope` | tier-1-structural | **works** |  |
| `project.sprints` | tier-2-executable | **compromised** | rollback carries limitations: audit log retains the intermediate transition |
| `project.themes` | tier-1-structural | **works** |  |
| `purge.remove_all` | tier-1-structural | **compromised** | rollback carries limitations: only if the recommended backup branch was created first; gitignored content is not recoverable from git alone |
| `quality.artifact_lint` | tier-2-executable | **broken** | entrypoint script scripts/artifact_lint.py not found |
| `quality.rubric_judge` | tier-3-behavioral | **broken** | entrypoint script scripts/artifact_judge.py not found |
| `recover.graduate_from_compatibility` | tier-2-executable | **works** |  |
| `recover.stabilize_without_migration` | tier-2-executable | **works** |  |
| `setup.onboard_project` | tier-2-executable | **compromised** | rollback carries limitations: purge removes all SweetClaude artifacts, not just this run's |
| `testing.accessibility` | tier-1-structural | **works** |  |
| `testing.behavioral_regression` | tier-1-structural | **works** |  |
| `testing.compliance` | tier-1-structural | **works** |  |
| `testing.mode_regression` | tier-1-structural | **works** |  |
| `testing.performance` | tier-1-structural | **works** |  |
| `testing.plan` | tier-1-structural | **works** |  |
| `testing.security` | tier-1-structural | **works** |  |
| `testing.session` | tier-1-structural | **works** |  |
| `update.check` | tier-2-executable | **compromised** | entrypoint coverage 79% is below 80% |
| `update.framework_sync` | tier-1-structural | **broken** | no verification_commands declared |
| `work_item_artifacts.backfill` | tier-2-executable | **works** |  |

