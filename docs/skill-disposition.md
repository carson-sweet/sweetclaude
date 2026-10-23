+# SweetClaude Skill Disposition

This inventory covers every skill packaged with SweetClaude. The disposition is a default-installation recommendation: user-facing workflows stay available on demand, while framework support and routing skills remain internal. This is not a statement that a skill body is loaded by default; only discovery metadata needs to be available before a skill is selected.

| Name | Brief description | Disposition |
|---|---|---|
| `_features` | Feature configuration — shows all optional SweetClaude features with descriptions and current status, lets the user enable or disable them. | Keep — internal |
| `_health` | Consistency scan and version check. | Keep — internal |
| `_migrate` | Migration orchestrator. Wraps the runner with snapshot, recovery menus, and end-of-session report. | Keep — internal |
| `_route` | Natural language classifier — maps user text to the right internal skill. | Keep — internal |
| `behavioral-regression` | Run SweetClaude's behavioral regression test suite. | Retired 2026-10-20 — contracts moved to `config/behavioral-contracts.md`, scored by `scripts/behavioral_judge.py` |
| `big-picture` | Show the full project at a glance — the roadmap pipeline with its milestones, epics and issues. Covers whole-project status, overview, and where any piece of work currently sits. | Keep — on-demand |
| `bootstrap` | Session startup skill — pre-flight checks, drift/update offers, and initial routing. | Keep — internal |
| `claude-config-audit` | Redirects to sweetclaude:doctor. Config compatibility checks are now part of the doctor system. | Keep — internal |
| `code-debt` | Tech debt cleanup. | Keep — on-demand |
| `code-feature` | Build a new feature end-to-end. | Keep — on-demand |
| `code-issue` | Implement a GitHub issue end-to-end. | Keep — on-demand |
| `code-review` | Code, security, and compliance review. | Keep — on-demand |
| `code-tdd` | Internal TDD process skill — invoked by code-feature, code-issue, and code-debt. | Keep — on-demand |
| `code-testing` | Run any combination of test suite, mutation testing, security review, and PR pre-check. | Keep — on-demand |
| `code-verify` | Run verification before claiming work is complete. | Keep — on-demand |
| `corpus-consolidate` | Scan source directories, deduplicate files, copy unique files into corpus/raw/inbox/. | Keep — on-demand |
| `corpus-promote` | Finalize approved documents from corpus/working/. | Keep — on-demand |
| `corpus-rag-reindex` | Rebuild RAG collections from source files. | Keep — on-demand |
| `corpus-rag-setup` | Configure and run local semantic search on project documents using mcp-local-rag. | Keep — on-demand |
| `corpus-reconcile` | Take staged files and work with the user to produce approved canonical documents in corpus/working/. | Keep — on-demand |
| `corpus-status` | Show the current state of the document corpus pipeline — file counts in each stage, last-run timestamps per step, and recommended next action. | Keep — on-demand |
| `corpus-triage` | Classify files in corpus/raw/inbox/ as keep-as-is, needs-reconciliation, discard, or defer. | Keep — on-demand |
| `course-correction` | Course correction — document the pivot, triage in-flight work, and update project direction. | Keep — on-demand |
| `dashboard` | Launch a local web dashboard showing roadmap, releases, epics, backlog, dependencies, git history, and skill activity. | Keep — on-demand |
| `deploy-ship` | SHIP phase skill. | Keep — on-demand |
| `design-api-design` | Design API endpoints: routes, request/response shapes, authentication, pagination, error responses, and versioning strategy. | Keep — on-demand |
| `design-architecture` | Define system architecture — components, boundaries, communication patterns, data flow, and compliance requirements. | Keep — on-demand |
| `design-change-impact-analysis` | Ripple-effect analysis for changes to EXISTING code or specs — trace what is affected across code, tests, docs, APIs, and specs. | Keep — on-demand |
| `design-data-model` | Design the data model: entities, relationships, constraints, indexes, and migration strategy. | Keep — on-demand |
| `design-manage-decisions` | Record and track design and architecture decisions with context, options considered, decision made, and rationale. | Keep — on-demand |
| `design-solutioning-gate` | Validate the proposed solution before implementation. | Keep — on-demand |
| `design-tech-spec` | Technical specification — every decision a developer needs before writing the first line of code. | Keep — on-demand |
| `design-user-flows` | Convert user stories into UX/UI flows — step-by-step paths through the interface. | Keep — on-demand |
| `design-ux` | Define the visual and interaction design of the product — look, feel, layout, and style. | Keep — on-demand |
| `design-ux-review` | Virtual UX review session. | Keep — on-demand |
| `design-wireframes` | Generate HTML/CSS wireframes from user flows. | Keep — on-demand |
| `doctor` | Diagnostic scan, repair, and rollback. Checks 8 categories (state integrity, hooks, storage, migration, config, files, onboarding, environment), fixes what it safely can, and can restore (roll back / undo / revert) the files a previous doctor run changed. | Keep — on-demand |
| `document-corpus` | Manage the full document corpus pipeline — consolidate raw files, triage, reconcile into canonical documents, promote, set up semantic search (RAG), and reindex. | Keep — on-demand |
| `documents-academic-research` | Academic paper development — from first principles through submission. | Keep — on-demand |
| `documents-narrative-arc` | Build and query a knowledge graph connecting strategic claims, proof points, objectives, and supporting/opposing evidence. | Keep — on-demand |
| `documents-update-docs` | Update documentation when implementation changes behavior. | Keep — on-demand |
| `epic-design` | Produce a complete, ordered story list for an epic. | Keep — on-demand |
| `epics` | Manage epics and objectives — add, review, link, status, complete. Always loaded. | Keep — on-demand |
| `feature-setup` | Deploy local repo to installed locations and rebuild the project cache. | Keep — on-demand |
| `find-skill` | Find and start the right skill for any work. | Keep — internal |
| `fix-sweetclaude` | Redirects to sweetclaude:doctor. This skill has been absorbed into the doctor diagnostic system. | Keep — on-demand |
| `go` | Assess what to work on next and propose it. | Keep — on-demand |
| `guardian-off` | Disable the Protocol Guardian for the current session | Keep — on-demand |
| `guardian-on` | Enable the Protocol Guardian — enforces skill invocations, TDD discipline, and artifact saves for the current session | Keep — on-demand |
| `help` | SweetClaude help and skill discovery. | Keep — on-demand |
| `hibernate` | Use when hibernating or unhibernating a project managed by SweetClaude. | Keep — on-demand |
| `hook-repair` | Redirects to sweetclaude:doctor. Hook diagnostics are now part of the doctor system. | Keep — on-demand |
| `hotfix` | Hotfix — minimal patch for a production issue with expedited review and mandatory post-mortem. | Keep — on-demand |
| `init` | Entry point for onboarding a project to SweetClaude — reads current state and hands off to the skill that owns the work. | Keep — on-demand |
| `john-wick` | Fully autonomous, resumable, multi-session SDLC pipeline. | Keep — on-demand |
| `john-wick-checkin` | Internal John Wick phase check-in subagent. | Keep — internal |
| `large-story` | Internal bounded, evidence-gated large-story workflow. | Keep — internal |
| `master` | SweetClaude master skill — phase router, interaction model, and session entry point. | Keep — internal |
| `migrate` | Migrate legacy work items to unified ISSUE-NNN format. Supports flat BL-NNN layouts and typed legacy backlog layouts (stories/, bugs/, debt/). | Keep — on-demand |
| `migrate-diagnose` | Redirects to sweetclaude:doctor. File diagnostics are now part of the doctor system. | Keep — on-demand |
| `misc-meeting-prep` | Prepare for a specific meeting. | Keep — on-demand |
| `mockup-extract` | Pull an existing production component into the mockup sandbox as an accurate 'Current' baseline for design iteration. | Keep — on-demand |
| `mockup-graduate` | Move an approved mockup from the sandbox into the main application. | Keep — on-demand |
| `mockup-sandbox` | Create and iterate on interactive UI mockups in an isolated Vite + React + Tailwind + shadcn/ui sandbox. | Keep — on-demand |
| `next-steps` | Walk through the pipeline step by step. | Keep — internal |
| `off` | Deactivate SweetClaude for the current project. | Keep — on-demand |
| `orchestrator` | Orchestrator main loop — executes tracked workflow steps via subagents. | Keep — internal |
| `postmortem` | Post-mortem authoring — timeline, root cause analysis, contributing factors, and action items. | Keep — on-demand |
| `product-brief` | Write a product brief — a strategic document describing what is being built, for whom, why it matters, and what success looks like. | Keep — on-demand |
| `product-competition` | Competitive analysis at three depth levels — from a quick company survey to feature-by-feature deep analysis. | Keep — on-demand |
| `product-discovery` | Establish what is being built, for whom, and why — at the depth appropriate for the project type. | Keep — on-demand |
| `product-manage-scope` | Track scope changes when items move between in-scope and out-of-scope. | Keep — on-demand |
| `product-market-messaging` | Craft external messaging — how you describe the product, the problem, and the value to different audiences. | Keep — on-demand |
| `product-milestone-planning` | Guided milestone planning workshop. | Keep — on-demand |
| `product-milestones` | Manage roadmap targets (milestones) that span strategy and product work. | Keep — on-demand |
| `product-parking-lot` | Manage deferred work. | Keep — on-demand |
| `product-positioning-statement` | Define how the product is positioned — for whom, what category, what differentiates it, and why that matters. | Keep — on-demand |
| `product-prd` | Write a Product Requirements Document — functional requirements, non-functional requirements, epics, and success metrics. | Keep — on-demand |
| `product-research` | Survey the solution field — what exists commercially and open source — so the user understands what they're entering before building. | Keep — on-demand |
| `product-roadmap` | Manage the product roadmap — feature delivery targets, releases, and priority stack. | Keep — on-demand |
| `product-roadmap-analysis` | RICE scoring and stack-rank analysis for roadmap items. | Keep — on-demand |
| `product-sprint-plan` | Plan a sprint by selecting stories from the backlog, estimating scope, and producing a sprint commitment. | Keep — on-demand |
| `product-terminology` | Define and maintain a shared domain glossary. | Keep — on-demand |
| `product-user-focus-group` | Synthetic panel research using persona archetypes as parallel subagent respondents. | Keep — on-demand |
| `product-user-stories` | Write user stories for a defined scope — Gherkin or generic format, scoped to all personas, SLC, or MVP. | Keep — on-demand |
| `product-user-tdd-tests` | Transition user stories into Gherkin .feature files. | Keep — on-demand |
| `project-assess-shape` | Interview user and recommend a SweetClaude project mode (Flow, Kanban, Shape Up, or Agile) | Keep — on-demand |
| `project-backlog` | View and manage the unscheduled issue backlog. | Keep — on-demand |
| `project-backlog-triage` | Structured backlog grooming session. | Keep — on-demand |
| `project-epics` | DEPRECATED — use /sweetclaude:epics instead. Redirects automatically. | Keep — on-demand |
| `project-gh-import-issues` | Import open GitHub Issues into the local issue store as v4 story files. | Keep — on-demand |
| `project-gh-sync-issues` | Bidirectional status sync between local issue files and GitHub Issues. | Keep — on-demand |
| `project-goals` | Manage project goals — binary business goals. | Keep — on-demand |
| `project-issues` | Manage project issues — list, view, create, update, and close. | Keep — on-demand |
| `project-mode` | Assess and shift project modes. | Keep — on-demand |
| `project-scope` | Define and maintain project scope. | Keep — on-demand |
| `project-sprints` | Sprint planning, activation, board view, and close. | Keep — on-demand |
| `project-themes` | Manage themes — optional domain-grouping labels on stories. | Keep — on-demand |
| `purge` | Delete all SweetClaude artifacts from the current project. | Keep — on-demand |
| `recap` | Produce a concise 'where we are' summary: current phase, active work item, last 3 commits, checkpoint state, and any open flags. | Keep — on-demand |
| `recover` | Recover or unblock SweetClaude projects left in bad update, migration, doctor, or repair states. | Keep — on-demand |
| `report-failure` | Write one structured failure report and root cause analysis to .sweetclaude/failure/. Invoke ONLY when the user explicitly asks to record/report a failure, mistake, or incident. Never auto-invoke. | Keep — on-demand |
| `retro` | Review and maintain the improvement register. | Keep — on-demand |
| `rollback-revert` | Roll back or revert a deployment — identify the cause, execute the rollback, confirm recovery. | Keep — on-demand |
| `security-patch` | Security patch — vulnerability fix with mandatory security review and disclosure tracking. | Keep — on-demand |
| `session-export` | Export a Claude.ai session as a complete, portable package. | Keep — on-demand |
| `setup` | Consolidated onboarding skill. | Keep — internal |
| `small-story` | Internal bounded, evidence-gated small-story workflow. | Keep — internal |
| `something-broke` | Reactive production incident skill. | Keep — on-demand |
| `status` | Orient to active work and blockers. | Keep — on-demand |
| `sweetclaude-behavioral-regression` | Validates that mode enforcement is working correctly across all four modes. | Retired 2026-10-20 |
| `testing-accessibility` | WCAG 2.1 Level AA audit. | Keep — on-demand |
| `testing-compliance` | Compliance control testing and evidence collection. | Keep — on-demand |
| `testing-performance` | Define load scenarios, establish performance baselines, set thresholds. | Keep — on-demand |
| `testing-plan` | Define and maintain a test strategy for a feature or release. | Keep — on-demand |
| `testing-security` | Structured security review. | Keep — on-demand |
| `testing-session` | Run a manual QA session. | Keep — on-demand |
| `ultraplan` | Prepare a structured ultraplan prompt from current phase artifacts, launch ultraplan, and ingest the resulting plan as the DESIGN phase architecture artifact. | Keep — on-demand |
| `update` | Update SweetClaude to the latest version from GitHub. | Keep — on-demand |
| `usage` | Toggle and view local usage tracking. | Keep — on-demand |
| `user-personas` | Define product users — who they are, what they need to do, and exactly what completing each task looks and feels like. | Keep — on-demand |
| `work-item-artifacts` | Co-locate all artifacts per story, epic, and milestone into .sweetclaude/work/<ID>/. Manages onboarding, backfill, and per-item directory creation. | Keep — on-demand |

