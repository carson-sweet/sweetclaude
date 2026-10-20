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
| Feature, issue, implementation, test, review, QA, sprint, deploy, ship | `build` |
| Bug in production, hotfix, refactor, technical debt, dependency upgrade, performance, rollback, postmortem | `maintain` |
| SweetClaude setup, mode, hooks, health, update, migration, recovery, disablement, usage | `configure` |
| Meeting preparation, session export, corpus, dashboard, bounded cross-cutting utility | `utils` |

If signals compete and the category changes mutation authority or workflow
gates, ask one focused clarification. Otherwise route directly. The category
command invokes the Tier 2 library loader and the selected workflow remains
responsible for its own safety and completion requirements.
