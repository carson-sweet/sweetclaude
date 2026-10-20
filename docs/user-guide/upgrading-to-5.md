# Upgrading to SweetClaude 5.0

**Version:** 1.0

**Date:** 2026-10-20

SweetClaude 5.0 replaces the one-command-per-workflow menu with nine commands. Your project data, state files and issues do not change; only the command names do.

## The nine commands

| Command | Use it for |
|---|---|
| `/sweetclaude:go` | Describe what you want in plain words; SweetClaude picks the category and workflow. |
| `/sweetclaude:plan` | Problem framing, research, scope, priorities, roadmap. |
| `/sweetclaude:design` | Architecture, specifications, data models, APIs, UX. |
| `/sweetclaude:build` | Implementation, issues, testing, review, shipping. |
| `/sweetclaude:maintain` | Production fixes, refactoring, debt, rollback, postmortems. |
| `/sweetclaude:configure` | SweetClaude itself: setup, modes, doctor, recovery, update. |
| `/sweetclaude:utils` | Meeting prep, session export, corpus, dashboard, overviews. |
| `/sweetclaude:status` | Current project, active work and blockers. |
| `/sweetclaude:help` | The command list and examples. |

You can name a workflow after its category, for example `/sweetclaude:configure doctor`, or describe the task and let the category choose. If you type a removed command, SweetClaude tells you its new form and runs it.

## Old commands and their replacements

| Old command | 5.0 command | What it does |
|---|---|---|
| `/sweetclaude:course-correction` | `/sweetclaude:plan course-correction` | Course correction — document the pivot, triage in-flight work, and update project direction. |
| `/sweetclaude:documents-academic-research` | `/sweetclaude:plan documents-academic-research` | Academic paper development — from first principles through submission. |
| `/sweetclaude:documents-narrative-arc` | `/sweetclaude:plan documents-narrative-arc` | Build and query a knowledge graph connecting strategic claims, proof points, objectives, and supporting/opposing evidence. |
| `/sweetclaude:epic-design` | `/sweetclaude:plan epic-design` | Produce a complete, ordered story list for an epic. |
| `/sweetclaude:epics` | `/sweetclaude:plan epics` | Manage epics and objectives — add, review, link, status, complete. Always loaded. |
| `/sweetclaude:product-brief` | `/sweetclaude:plan product-brief` | Write a product brief — a strategic document describing what is being built, for whom, why it matters, and what success looks like. |
| `/sweetclaude:product-competition` | `/sweetclaude:plan product-competition` | Competitive analysis at three depth levels — from a quick company survey to feature-by-feature deep analysis. |
| `/sweetclaude:product-discovery` | `/sweetclaude:plan product-discovery` | Establish what is being built, for whom, and why — at the depth appropriate for the project type. |
| `/sweetclaude:product-manage-scope` | `/sweetclaude:plan product-manage-scope` | Track scope changes when items move between in-scope and out-of-scope. |
| `/sweetclaude:product-market-messaging` | `/sweetclaude:plan product-market-messaging` | Craft external messaging — how you describe the product, the problem, and the value to different audiences. |
| `/sweetclaude:product-milestone-planning` | `/sweetclaude:plan product-milestone-planning` | Guided milestone planning workshop. |
| `/sweetclaude:product-milestones` | `/sweetclaude:plan product-milestones` | Manage roadmap targets (milestones) that span strategy and product work. |
| `/sweetclaude:product-parking-lot` | `/sweetclaude:plan product-parking-lot` | Manage deferred work. |
| `/sweetclaude:product-positioning-statement` | `/sweetclaude:plan product-positioning-statement` | Define how the product is positioned — for whom, what category, what differentiates it, and why that matters. |
| `/sweetclaude:product-prd` | `/sweetclaude:plan product-prd` | Write a Product Requirements Document — functional requirements, non-functional requirements, epics, and success metrics. |
| `/sweetclaude:product-research` | `/sweetclaude:plan product-research` | Survey the solution field — what exists commercially and open source — so the user understands what they're entering before building. |
| `/sweetclaude:product-roadmap` | `/sweetclaude:plan product-roadmap` | Manage the product roadmap — feature delivery targets, releases, and priority stack. |
| `/sweetclaude:product-roadmap-analysis` | `/sweetclaude:plan product-roadmap-analysis` | RICE scoring and stack-rank analysis for roadmap items. |
| `/sweetclaude:product-terminology` | `/sweetclaude:plan product-terminology` | Define and maintain a shared domain glossary. |
| `/sweetclaude:product-user-focus-group` | `/sweetclaude:plan product-user-focus-group` | Synthetic panel research using persona archetypes as parallel subagent respondents. |
| `/sweetclaude:product-user-stories` | `/sweetclaude:plan product-user-stories` | Write user stories for a defined scope — Gherkin or generic format, scoped to all personas, SLC, or MVP. |
| `/sweetclaude:project-goals` | `/sweetclaude:plan project-goals` | Manage project goals — binary business goals. |
| `/sweetclaude:project-scope` | `/sweetclaude:plan project-scope` | Define and maintain project scope. |
| `/sweetclaude:user-personas` | `/sweetclaude:plan user-personas` | Define product users — who they are, what they need to do, and exactly what completing each task looks and feels like. |
| `/sweetclaude:design-api-design` | `/sweetclaude:design design-api-design` | Design API endpoints: routes, request/response shapes, authentication, pagination, error responses, and versioning strategy. |
| `/sweetclaude:design-architecture` | `/sweetclaude:design design-architecture` | Define system architecture — components, boundaries, communication patterns, data flow, and compliance requirements. |
| `/sweetclaude:design-change-impact-analysis` | `/sweetclaude:design design-change-impact-analysis` | Ripple-effect analysis for changes to EXISTING code or specs — trace what is affected across code, tests, docs, APIs, and specs. |
| `/sweetclaude:design-data-model` | `/sweetclaude:design design-data-model` | Design the data model: entities, relationships, constraints, indexes, and migration strategy. |
| `/sweetclaude:design-manage-decisions` | `/sweetclaude:design design-manage-decisions` | Record and track design and architecture decisions with context, options considered, decision made, and rationale. |
| `/sweetclaude:design-solutioning-gate` | `/sweetclaude:design design-solutioning-gate` | Validate the proposed solution before implementation. |
| `/sweetclaude:design-tech-spec` | `/sweetclaude:design design-tech-spec` | Technical specification — every decision a developer needs before writing the first line of code. |
| `/sweetclaude:design-user-flows` | `/sweetclaude:design design-user-flows` | Convert user stories into UX/UI flows — step-by-step paths through the interface. |
| `/sweetclaude:design-ux` | `/sweetclaude:design design-ux` | Define the visual and interaction design of the product — look, feel, layout, and style. |
| `/sweetclaude:design-ux-review` | `/sweetclaude:design design-ux-review` | Virtual UX review session. |
| `/sweetclaude:design-wireframes` | `/sweetclaude:design design-wireframes` | Generate HTML/CSS wireframes from user flows. |
| `/sweetclaude:mockup-extract` | `/sweetclaude:design mockup-extract` | Pull an existing production component into the mockup sandbox as an accurate 'Current' baseline for design iteration. |
| `/sweetclaude:mockup-graduate` | `/sweetclaude:design mockup-graduate` | Move an approved mockup from the sandbox into the main application. |
| `/sweetclaude:mockup-sandbox` | `/sweetclaude:design mockup-sandbox` | Create and iterate on interactive UI mockups in an isolated Vite + React + Tailwind + shadcn/ui sandbox. |
| `/sweetclaude:ultraplan` | `/sweetclaude:design ultraplan` | Prepare a structured ultraplan prompt from current phase artifacts, launch ultraplan, and ingest the resulting plan as the DESIGN phase architecture artifact. |
| `/sweetclaude:code-feature` | `/sweetclaude:build code-feature` | Build a new feature end-to-end. |
| `/sweetclaude:code-issue` | `/sweetclaude:build code-issue` | Implement a specified, existing GitHub issue end-to-end; not for tracker configuration or issue management. |
| `/sweetclaude:code-review` | `/sweetclaude:build code-review` | Code, security, and compliance review. |
| `/sweetclaude:code-tdd` | `/sweetclaude:build code-tdd` | Internal TDD process skill — invoked by code-feature, code-issue, and code-debt. |
| `/sweetclaude:code-testing` | `/sweetclaude:build code-testing` | Run any combination of test suite, mutation testing, security review, and PR pre-check. |
| `/sweetclaude:code-verify` | `/sweetclaude:build code-verify` | Run verification before claiming work is complete. |
| `/sweetclaude:deploy-ship` | `/sweetclaude:build deploy-ship` | SHIP phase skill. |
| `/sweetclaude:john-wick` | `/sweetclaude:build john-wick` | Fully autonomous, resumable, multi-session SDLC pipeline. |
| `/sweetclaude:john-wick-checkin` | `/sweetclaude:build john-wick-checkin` | Internal John Wick phase check-in subagent. |
| `/sweetclaude:large-story` | `/sweetclaude:build large-story` | Internal bounded, evidence-gated large-story workflow. |
| `/sweetclaude:orchestrator` | `/sweetclaude:build orchestrator` | Orchestrator main loop — executes tracked workflow steps via subagents. |
| `/sweetclaude:product-sprint-plan` | `/sweetclaude:build product-sprint-plan` | Plan a sprint by selecting stories from the backlog, estimating scope, and producing a sprint commitment. |
| `/sweetclaude:product-user-tdd-tests` | `/sweetclaude:build product-user-tdd-tests` | Transition user stories into Gherkin .feature files. |
| `/sweetclaude:project-backlog` | `/sweetclaude:build project-backlog` | View and manage the unscheduled issue backlog. |
| `/sweetclaude:project-backlog-triage` | `/sweetclaude:build project-backlog-triage` | Structured backlog grooming session. |
| `/sweetclaude:project-epics` | `/sweetclaude:build project-epics` | DEPRECATED — use /sweetclaude:plan instead. Redirects automatically. |
| `/sweetclaude:project-gh-import-issues` | `/sweetclaude:build project-gh-import-issues` | Import open GitHub Issues into the local issue store as v4 story files. |
| `/sweetclaude:project-gh-sync-issues` | `/sweetclaude:build project-gh-sync-issues` | Bidirectional status sync between local issue files and GitHub Issues. |
| `/sweetclaude:project-issues` | `/sweetclaude:build project-issues` | Manage project issues and select the local or GitHub issue tracker — list, view, create, update, close, or change tracker. |
| `/sweetclaude:project-sprints` | `/sweetclaude:build project-sprints` | Sprint planning, activation, board view, and close. |
| `/sweetclaude:project-themes` | `/sweetclaude:build project-themes` | Manage themes — optional domain-grouping labels on stories. |
| `/sweetclaude:small-story` | `/sweetclaude:build small-story` | Internal bounded, evidence-gated small-story workflow. |
| `/sweetclaude:testing-accessibility` | `/sweetclaude:build testing-accessibility` | WCAG 2.1 Level AA audit. |
| `/sweetclaude:testing-compliance` | `/sweetclaude:build testing-compliance` | Compliance control testing and evidence collection. |
| `/sweetclaude:testing-performance` | `/sweetclaude:build testing-performance` | Define load scenarios, establish performance baselines, set thresholds. |
| `/sweetclaude:testing-plan` | `/sweetclaude:build testing-plan` | Define and maintain a test strategy for a feature or release. |
| `/sweetclaude:testing-security` | `/sweetclaude:build testing-security` | Structured security review. |
| `/sweetclaude:testing-session` | `/sweetclaude:build testing-session` | Run a manual QA session. |
| `/sweetclaude:code-debt` | `/sweetclaude:maintain code-debt` | Tech debt cleanup. |
| `/sweetclaude:hotfix` | `/sweetclaude:maintain hotfix` | Hotfix — minimal patch for a production issue with expedited review and mandatory post-mortem. |
| `/sweetclaude:postmortem` | `/sweetclaude:maintain postmortem` | Post-mortem authoring — timeline, root cause analysis, contributing factors, and action items. |
| `/sweetclaude:rollback-revert` | `/sweetclaude:maintain rollback-revert` | Roll back or revert a deployment — identify the cause, execute the rollback, confirm recovery. |
| `/sweetclaude:security-patch` | `/sweetclaude:maintain security-patch` | Security patch — vulnerability fix with mandatory security review and disclosure tracking. |
| `/sweetclaude:something-broke` | `/sweetclaude:maintain something-broke` | Reactive production incident skill. |
| `/sweetclaude:_features` | `/sweetclaude:configure _features` | Feature configuration — shows all optional SweetClaude features with descriptions and current status, lets the user enable or disable them. |
| `/sweetclaude:_health` | `/sweetclaude:configure _health` | Consistency scan and version check. |
| `/sweetclaude:_migrate` | `/sweetclaude:configure _migrate` | Migration orchestrator. Wraps the runner with snapshot, recovery menus, and end-of-session report. |
| `/sweetclaude:claude-config-audit` | `/sweetclaude:configure claude-config-audit` | Redirects to sweetclaude:library-load doctor. Config compatibility checks are now part of the doctor system. |
| `/sweetclaude:doctor` | `/sweetclaude:configure doctor` | Diagnostic scan, repair, and rollback. Checks 8 categories (state integrity, hooks, storage, migration, config, files, onboarding, environment), fixes what it safely can, and can restore (roll back / undo / revert) the files a previous doctor run changed. |
| `/sweetclaude:feature-setup` | `/sweetclaude:configure feature-setup` | Deploy local repo to installed locations and rebuild the project cache. |
| `/sweetclaude:fix-sweetclaude` | `/sweetclaude:configure fix-sweetclaude` | Redirects to sweetclaude:library-load doctor. This skill has been absorbed into the doctor diagnostic system. |
| `/sweetclaude:guardian-off` | `/sweetclaude:configure guardian-off` | Disable the Protocol Guardian for the current session |
| `/sweetclaude:guardian-on` | `/sweetclaude:configure guardian-on` | Enable the Protocol Guardian — enforces skill invocations, TDD discipline, and artifact saves for the current session |
| `/sweetclaude:hibernate` | `/sweetclaude:configure hibernate` | Use when hibernating or unhibernating a project managed by SweetClaude. |
| `/sweetclaude:hook-repair` | `/sweetclaude:configure hook-repair` | Redirects to sweetclaude:library-load doctor. Hook diagnostics are now part of the doctor system. |
| `/sweetclaude:init` | `/sweetclaude:configure init` | Entry point for onboarding a project to SweetClaude — reads current state and hands off to the skill that owns the work. |
| `/sweetclaude:migrate` | `/sweetclaude:configure migrate` | Migrate legacy work items to unified ISSUE-NNN format. Supports flat BL-NNN layouts and typed legacy backlog layouts (stories/, bugs/, debt/). |
| `/sweetclaude:migrate-diagnose` | `/sweetclaude:configure migrate-diagnose` | Redirects to sweetclaude:library-load doctor. File diagnostics are now part of the doctor system. |
| `/sweetclaude:off` | `/sweetclaude:configure off` | Deactivate SweetClaude for the current project. |
| `/sweetclaude:project-assess-shape` | `/sweetclaude:configure project-assess-shape` | Interview user and recommend a SweetClaude project mode (Flow, Kanban, Shape Up, or Agile) |
| `/sweetclaude:project-mode` | `/sweetclaude:configure project-mode` | Assess and shift project modes. |
| `/sweetclaude:purge` | `/sweetclaude:configure purge` | Delete all SweetClaude artifacts from the current project. |
| `/sweetclaude:recover` | `/sweetclaude:configure recover` | Recover or unblock SweetClaude projects left in bad update, migration, doctor, or repair states. |
| `/sweetclaude:retro` | `/sweetclaude:configure retro` | Review and maintain the improvement register. |
| `/sweetclaude:setup` | `/sweetclaude:configure setup` | Consolidated onboarding skill. |
| `/sweetclaude:update` | `/sweetclaude:configure update` | Update SweetClaude to the latest version from GitHub. |
| `/sweetclaude:usage` | `/sweetclaude:configure usage` | Toggle and view local usage tracking. |
| `/sweetclaude:work-item-artifacts` | `/sweetclaude:configure work-item-artifacts` | Co-locate all artifacts per story, epic, and milestone into .sweetclaude/work/<ID>/. Manages onboarding, backfill, and per-item directory creation. |
| `/sweetclaude:big-picture` | `/sweetclaude:utils big-picture` | Show the full project at a glance — the roadmap pipeline with its milestones, epics and issues. Covers whole-project status, overview, and where any piece of work currently sits. |
| `/sweetclaude:corpus-consolidate` | `/sweetclaude:utils corpus-consolidate` | Scan source directories, deduplicate files, copy unique files into corpus/raw/inbox/. |
| `/sweetclaude:corpus-promote` | `/sweetclaude:utils corpus-promote` | Finalize approved documents from corpus/working/. |
| `/sweetclaude:corpus-rag-reindex` | `/sweetclaude:utils corpus-rag-reindex` | Rebuild RAG collections from source files. |
| `/sweetclaude:corpus-rag-setup` | `/sweetclaude:utils corpus-rag-setup` | Configure and run local semantic search on project documents using mcp-local-rag. |
| `/sweetclaude:corpus-reconcile` | `/sweetclaude:utils corpus-reconcile` | Take staged files and work with the user to produce approved canonical documents in corpus/working/. |
| `/sweetclaude:corpus-status` | `/sweetclaude:utils corpus-status` | Show the current state of the document corpus pipeline — file counts in each stage, last-run timestamps per step, and recommended next action. |
| `/sweetclaude:corpus-triage` | `/sweetclaude:utils corpus-triage` | Classify files in corpus/raw/inbox/ as keep-as-is, needs-reconciliation, discard, or defer. |
| `/sweetclaude:dashboard` | `/sweetclaude:utils dashboard` | Launch a local web dashboard showing roadmap, releases, epics, backlog, dependencies, git history, and skill activity. |
| `/sweetclaude:document-corpus` | `/sweetclaude:utils document-corpus` | Manage the full document corpus pipeline — consolidate raw files, triage, reconcile into canonical documents, promote, set up semantic search (RAG), and reindex. |
| `/sweetclaude:documents-update-docs` | `/sweetclaude:utils documents-update-docs` | Update documentation when implementation changes behavior. |
| `/sweetclaude:misc-meeting-prep` | `/sweetclaude:utils misc-meeting-prep` | Prepare for a specific meeting. |
| `/sweetclaude:next-steps` | `/sweetclaude:utils next-steps` | Walk through the pipeline step by step. |
| `/sweetclaude:recap` | `/sweetclaude:utils recap` | Produce a concise 'where we are' summary: current phase, active work item, last 3 commits, checkpoint state, and any open flags. |
| `/sweetclaude:report-failure` | `/sweetclaude:utils report-failure` | Write one structured failure report and root cause analysis to .sweetclaude/failure/. Invoke ONLY when the user explicitly asks to record/report a failure, mistake, or incident. Never auto-invoke. |
| `/sweetclaude:session-export` | `/sweetclaude:utils session-export` | Export a Claude.ai session as a complete, portable package. |
