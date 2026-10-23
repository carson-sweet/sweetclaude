---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Internal router from a request to a Tier 1 category."
---

# Tier 1 Router

Classify `$ARGUMENTS` into one category, then invoke the matching Tier 1
command with the unchanged request. Do not enumerate or load the whole Tier 2
library.

| Dominant signal | Category |
|---|---|
| Product problem, customer, research, scope, priority, roadmap, persona, requirement | `plan` |
| Architecture, specification, API, data model, UX, wireframe, design decision | `design` |
| Feature, issue, issue tracker choice (local or GitHub), implementation, defect found while building or before release, test (including load, performance, accessibility, and security testing), review, QA, sprint, deploy, ship | `build` |
| Bug in production, hotfix, refactor, technical debt, dependency upgrade, fixing slow existing code, rollback, postmortem | `maintain` |
| SweetClaude setup, mode, hooks, health, update, migration, recovery, disablement, usage | `configure` |
| Meeting preparation, session export, corpus, dashboard, whole-project overview of milestones, epics, and issues, writing or updating documentation, bounded cross-cutting utility | `utils` |

Boundary cases:

- Choosing or switching the project's issue tracker is `build` (`project-issues`), even though the choice is stored in SweetClaude state.
- Measuring or load-testing against a performance target is `build`; changing existing code to make it faster is `maintain`.
- A defect found while building, in unreleased code or failing unit tests, is `build`; a bug in shipped production code is `maintain`.
- A whole-project overview is `utils`; `/sweetclaude:status` is only for current active work and blockers.
- Writing or updating a document — including API documentation — is `utils` (`documents-update-docs`); designing an API is `design`.

If signals compete and the category changes mutation authority or workflow
gates, ask one focused clarification. Otherwise route directly. The category
command invokes the Tier 2 library loader and the selected workflow remains
responsible for its own safety and completion requirements.
