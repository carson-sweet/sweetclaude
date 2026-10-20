# Upgrading to SweetClaude 5.0

**Version:** 1.0

**Date:** 2026-10-20

SweetClaude 5.0 replaces the one-command-per-workflow menu with nine commands. Your project data, state files and issues do not change; only the command names do.

## Upgrading from 4.x

The 5.0 commands do not exist until 5.0 is installed. Run `/plugin marketplace update sweetclaude-stable`, then `/plugin update sweetclaude@sweetclaude-stable`, then restart Claude Code. Do not run the update step that 4.x ships: its sync does not install the 5.0 workflow library. After the restart, run `/sweetclaude:configure update` in each project.

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

You can name a workflow after its category, for example `/sweetclaude:configure doctor`, or describe the task and let the category choose. In an interactive session, Claude Code reports a removed command as unknown; use the table below or `/sweetclaude:help`. In non-interactive sessions (`claude -p` and the SDK), SweetClaude names the new form and runs it.

## Old commands and their replacements

| Old command name (was typed after `/sweetclaude:`) | 5.0 command | What it does |
|---|---|---|
| `course-correction` | `/sweetclaude:plan course-correction` | Course correction — document the pivot, triage in-flight work, and update project direction. |
| `documents-academic-research` | `/sweetclaude:plan documents-academic-research` | Academic paper development — from first principles through submission. |
| `documents-narrative-arc` | `/sweetclaude:plan documents-narrative-arc` | Build and query a knowledge graph connecting strategic claims, proof points, objectives, and supporting/opposing evidence. |
| `epic-design` | `/sweetclaude:plan epic-design` | Produce a complete, ordered story list for an epic. |
| `epics` | `/sweetclaude:plan epics` | Manage epics and objectives — add, review, link, status, complete. Always loaded. |
| `product-brief` | `/sweetclaude:plan product-brief` | Write a product brief — a strategic document describing what is being built, for whom, why it matters, and what success looks like. |
| `product-competition` | `/sweetclaude:plan product-competition` | Competitive analysis at three depth levels — from a quick company survey to feature-by-feature deep analysis. |
| `product-discovery` | `/sweetclaude:plan product-discovery` | Establish what is being built, for whom, and why — at the depth appropriate for the project type. |
| `product-manage-scope` | `/sweetclaude:plan product-manage-scope` | Track scope changes when items move between in-scope and out-of-scope. |
| `product-market-messaging` | `/sweetclaude:plan product-market-messaging` | Craft external messaging — how you describe the product, the problem, and the value to different audiences. |
| `product-milestone-planning` | `/sweetclaude:plan product-milestone-planning` | Guided milestone planning workshop. |
| `product-milestones` | `/sweetclaude:plan product-milestones` | Manage roadmap targets (milestones) that span strategy and product work. |
| `product-parking-lot` | `/sweetclaude:plan product-parking-lot` | Manage deferred work. |
| `product-positioning-statement` | `/sweetclaude:plan product-positioning-statement` | Define how the product is positioned — for whom, what category, what differentiates it, and why that matters. |
| `product-prd` | `/sweetclaude:plan product-prd` | Write a Product Requirements Document — functional requirements, non-functional requirements, epics, and success metrics. |
| `product-research` | `/sweetclaude:plan product-research` | Survey the solution field — what exists commercially and open source — so the user understands what they're entering before building. |
| `product-roadmap` | `/sweetclaude:plan product-roadmap` | Manage the product roadmap — feature delivery targets, releases, and priority stack. |
| `product-roadmap-analysis` | `/sweetclaude:plan product-roadmap-analysis` | RICE scoring and stack-rank analysis for roadmap items. |
| `product-terminology` | `/sweetclaude:plan product-terminology` | Define and maintain a shared domain glossary. |
| `product-user-focus-group` | `/sweetclaude:plan product-user-focus-group` | Synthetic panel research using persona archetypes as parallel subagent respondents. |
| `product-user-stories` | `/sweetclaude:plan product-user-stories` | Write user stories for a defined scope — Gherkin or generic format, scoped to all personas, SLC, or MVP. |
| `project-goals` | `/sweetclaude:plan project-goals` | Manage project goals — binary business goals. |
| `project-scope` | `/sweetclaude:plan project-scope` | Define and maintain project scope. |
| `user-personas` | `/sweetclaude:plan user-personas` | Define product users — who they are, what they need to do, and exactly what completing each task looks and feels like. |
| `design-api-design` | `/sweetclaude:design design-api-design` | Design API endpoints: routes, request/response shapes, authentication, pagination, error responses, and versioning strategy. |
| `design-architecture` | `/sweetclaude:design design-architecture` | Define system architecture — components, boundaries, communication patterns, data flow, and compliance requirements. |
| `design-change-impact-analysis` | `/sweetclaude:design design-change-impact-analysis` | Ripple-effect analysis for changes to EXISTING code or specs — trace what is affected across code, tests, docs, APIs, and specs. |
| `design-data-model` | `/sweetclaude:design design-data-model` | Design the data model: entities, relationships, constraints, indexes, and migration strategy. |
| `design-manage-decisions` | `/sweetclaude:design design-manage-decisions` | Record and track design and architecture decisions with context, options considered, decision made, and rationale. |
| `design-solutioning-gate` | `/sweetclaude:design design-solutioning-gate` | Validate the proposed solution before implementation. |
| `design-tech-spec` | `/sweetclaude:design design-tech-spec` | Technical specification — every decision a developer needs before writing the first line of code. |
| `design-user-flows` | `/sweetclaude:design design-user-flows` | Convert user stories into UX/UI flows — step-by-step paths through the interface. |
| `design-ux` | `/sweetclaude:design design-ux` | Define the visual and interaction design of the product — look, feel, layout, and style. |
| `design-ux-review` | `/sweetclaude:design design-ux-review` | Virtual UX review session. |
| `design-wireframes` | `/sweetclaude:design design-wireframes` | Generate HTML/CSS wireframes from user flows. |
| `mockup-extract` | `/sweetclaude:design mockup-extract` | Pull an existing production component into the mockup sandbox as an accurate 'Current' baseline for design iteration. |
| `mockup-graduate` | `/sweetclaude:design mockup-graduate` | Move an approved mockup from the sandbox into the main application. |
| `mockup-sandbox` | `/sweetclaude:design mockup-sandbox` | Create and iterate on interactive UI mockups in an isolated Vite + React + Tailwind + shadcn/ui sandbox. |
| `ultraplan` | `/sweetclaude:design ultraplan` | Prepare a structured ultraplan prompt from current phase artifacts, launch ultraplan, and ingest the resulting plan as the DESIGN phase architecture artifact. |
| `code-feature` | `/sweetclaude:build code-feature` | Build a new feature end-to-end. |
| `code-issue` | `/sweetclaude:build code-issue` | Implement a specified, existing GitHub issue end-to-end; not for tracker configuration or issue management. |
| `code-review` | `/sweetclaude:build code-review` | Code, security, and compliance review. |
| `code-tdd` | `/sweetclaude:build code-tdd` | Internal TDD process skill — invoked by code-feature, code-issue, and code-debt. |
| `code-testing` | `/sweetclaude:build code-testing` | Run any combination of test suite, mutation testing, security review, and PR pre-check. |
| `code-verify` | `/sweetclaude:build code-verify` | Run verification before claiming work is complete. |
| `deploy-ship` | `/sweetclaude:build deploy-ship` | SHIP phase skill. |
| `john-wick` | `/sweetclaude:build john-wick` | Fully autonomous, resumable, multi-session SDLC pipeline. |
| `john-wick-checkin` | `/sweetclaude:build john-wick-checkin` | Internal John Wick phase check-in subagent. |
| `large-story` | `/sweetclaude:build large-story` | Internal bounded, evidence-gated large-story workflow. |
| `orchestrator` | `/sweetclaude:build orchestrator` | Orchestrator main loop — executes tracked workflow steps via subagents. |
| `product-sprint-plan` | `/sweetclaude:build product-sprint-plan` | Plan a sprint by selecting stories from the backlog, estimating scope, and producing a sprint commitment. |
| `product-user-tdd-tests` | `/sweetclaude:build product-user-tdd-tests` | Transition user stories into Gherkin .feature files. |
| `project-backlog` | `/sweetclaude:build project-backlog` | View and manage the unscheduled issue backlog. |
| `project-backlog-triage` | `/sweetclaude:build project-backlog-triage` | Structured backlog grooming session. |
| `project-epics` | `/sweetclaude:build project-epics` | DEPRECATED — use /sweetclaude:plan instead. Redirects automatically. |
| `project-gh-import-issues` | `/sweetclaude:build project-gh-import-issues` | Import open GitHub Issues into the local issue store as v4 story files. |
| `project-gh-sync-issues` | `/sweetclaude:build project-gh-sync-issues` | Bidirectional status sync between local issue files and GitHub Issues. |
| `project-issues` | `/sweetclaude:build project-issues` | Manage project issues and select the local or GitHub issue tracker — list, view, create, update, close, or change tracker. |
| `project-sprints` | `/sweetclaude:build project-sprints` | Sprint planning, activation, board view, and close. |
| `project-themes` | `/sweetclaude:build project-themes` | Manage themes — optional domain-grouping labels on stories. |
| `small-story` | `/sweetclaude:build small-story` | Internal bounded, evidence-gated small-story workflow. |
| `testing-accessibility` | `/sweetclaude:build testing-accessibility` | WCAG 2.1 Level AA audit. |
| `testing-compliance` | `/sweetclaude:build testing-compliance` | Compliance control testing and evidence collection. |
| `testing-performance` | `/sweetclaude:build testing-performance` | Define load scenarios, establish performance baselines, set thresholds. |
| `testing-plan` | `/sweetclaude:build testing-plan` | Define and maintain a test strategy for a feature or release. |
| `testing-security` | `/sweetclaude:build testing-security` | Structured security review. |
| `testing-session` | `/sweetclaude:build testing-session` | Run a manual QA session. |
| `code-debt` | `/sweetclaude:maintain code-debt` | Tech debt cleanup. |
| `hotfix` | `/sweetclaude:maintain hotfix` | Hotfix — minimal patch for a production issue with expedited review and mandatory post-mortem. |
| `postmortem` | `/sweetclaude:maintain postmortem` | Post-mortem authoring — timeline, root cause analysis, contributing factors, and action items. |
| `rollback-revert` | `/sweetclaude:maintain rollback-revert` | Roll back or revert a deployment — identify the cause, execute the rollback, confirm recovery. |
| `security-patch` | `/sweetclaude:maintain security-patch` | Security patch — vulnerability fix with mandatory security review and disclosure tracking. |
| `something-broke` | `/sweetclaude:maintain something-broke` | Reactive production incident skill. |
| `_features` | `/sweetclaude:configure _features` | Feature configuration — shows all optional SweetClaude features with descriptions and current status, lets the user enable or disable them. |
| `_health` | `/sweetclaude:configure _health` | Consistency scan and version check. |
| `_migrate` | `/sweetclaude:configure _migrate` | Migration orchestrator. Wraps the runner with snapshot, recovery menus, and end-of-session report. |
| `claude-config-audit` | `/sweetclaude:configure claude-config-audit` | Redirects to sweetclaude:library-load doctor. Config compatibility checks are now part of the doctor system. |
| `doctor` | `/sweetclaude:configure doctor` | Diagnostic scan, repair, and rollback. Checks 8 categories (state integrity, hooks, storage, migration, config, files, onboarding, environment), fixes what it safely can, and can restore (roll back / undo / revert) the files a previous doctor run changed. |
| `feature-setup` | `/sweetclaude:configure feature-setup` | Deploy local repo to installed locations and rebuild the project cache. |
| `fix-sweetclaude` | `/sweetclaude:configure fix-sweetclaude` | Redirects to sweetclaude:library-load doctor. This skill has been absorbed into the doctor diagnostic system. |
| `guardian-off` | `/sweetclaude:configure guardian-off` | Disable the Protocol Guardian for the current session |
| `guardian-on` | `/sweetclaude:configure guardian-on` | Enable the Protocol Guardian — enforces skill invocations, TDD discipline, and artifact saves for the current session |
| `hibernate` | `/sweetclaude:configure hibernate` | Use when hibernating or unhibernating a project managed by SweetClaude. |
| `hook-repair` | `/sweetclaude:configure hook-repair` | Redirects to sweetclaude:library-load doctor. Hook diagnostics are now part of the doctor system. |
| `init` | `/sweetclaude:configure init` | Entry point for onboarding a project to SweetClaude — reads current state and hands off to the skill that owns the work. |
| `migrate` | `/sweetclaude:configure migrate` | Migrate legacy work items to unified ISSUE-NNN format. Supports flat BL-NNN layouts and typed legacy backlog layouts (stories/, bugs/, debt/). |
| `migrate-diagnose` | `/sweetclaude:configure migrate-diagnose` | Redirects to sweetclaude:library-load doctor. File diagnostics are now part of the doctor system. |
| `off` | `/sweetclaude:configure off` | Deactivate SweetClaude for the current project. |
| `project-assess-shape` | `/sweetclaude:configure project-assess-shape` | Interview user and recommend a SweetClaude project mode (Flow, Kanban, Shape Up, or Agile) |
| `project-mode` | `/sweetclaude:configure project-mode` | Assess and shift project modes. |
| `purge` | `/sweetclaude:configure purge` | Delete all SweetClaude artifacts from the current project. |
| `recover` | `/sweetclaude:configure recover` | Recover or unblock SweetClaude projects left in bad update, migration, doctor, or repair states. |
| `retro` | `/sweetclaude:configure retro` | Review and maintain the improvement register. |
| `setup` | `/sweetclaude:configure setup` | Consolidated onboarding skill. |
| `update` | `/sweetclaude:configure update` | Update SweetClaude to the latest version from GitHub. |
| `usage` | `/sweetclaude:configure usage` | Toggle and view local usage tracking. |
| `work-item-artifacts` | `/sweetclaude:configure work-item-artifacts` | Co-locate all artifacts per story, epic, and milestone into .sweetclaude/work/<ID>/. Manages onboarding, backfill, and per-item directory creation. |
| `big-picture` | `/sweetclaude:utils big-picture` | Show the full project at a glance — the roadmap pipeline with its milestones, epics and issues. Covers whole-project status, overview, and where any piece of work currently sits. |
| `corpus-consolidate` | `/sweetclaude:utils corpus-consolidate` | Scan source directories, deduplicate files, copy unique files into corpus/raw/inbox/. |
| `corpus-promote` | `/sweetclaude:utils corpus-promote` | Finalize approved documents from corpus/working/. |
| `corpus-rag-reindex` | `/sweetclaude:utils corpus-rag-reindex` | Rebuild RAG collections from source files. |
| `corpus-rag-setup` | `/sweetclaude:utils corpus-rag-setup` | Configure and run local semantic search on project documents using mcp-local-rag. |
| `corpus-reconcile` | `/sweetclaude:utils corpus-reconcile` | Take staged files and work with the user to produce approved canonical documents in corpus/working/. |
| `corpus-status` | `/sweetclaude:utils corpus-status` | Show the current state of the document corpus pipeline — file counts in each stage, last-run timestamps per step, and recommended next action. |
| `corpus-triage` | `/sweetclaude:utils corpus-triage` | Classify files in corpus/raw/inbox/ as keep-as-is, needs-reconciliation, discard, or defer. |
| `dashboard` | `/sweetclaude:utils dashboard` | Launch a local web dashboard showing roadmap, releases, epics, backlog, dependencies, git history, and skill activity. |
| `document-corpus` | `/sweetclaude:utils document-corpus` | Manage the full document corpus pipeline — consolidate raw files, triage, reconcile into canonical documents, promote, set up semantic search (RAG), and reindex. |
| `documents-update-docs` | `/sweetclaude:utils documents-update-docs` | Update documentation when implementation changes behavior. |
| `misc-meeting-prep` | `/sweetclaude:utils misc-meeting-prep` | Prepare for a specific meeting. |
| `next-steps` | `/sweetclaude:utils next-steps` | Walk through the pipeline step by step. |
| `recap` | `/sweetclaude:utils recap` | Produce a concise 'where we are' summary: current phase, active work item, last 3 commits, checkpoint state, and any open flags. |
| `report-failure` | `/sweetclaude:utils report-failure` | Write one structured failure report and root cause analysis to .sweetclaude/failure/. Invoke ONLY when the user explicitly asks to record/report a failure, mistake, or incident. Never auto-invoke. |
| `session-export` | `/sweetclaude:utils session-export` | Export a Claude.ai session as a complete, portable package. |
