# Commands and Skill Library

SweetClaude has a deliberately small public command surface. You never invoke an individual library workflow with a slash command. State the outcome you want after a category command; SweetClaude selects and loads the one focused workflow it needs.

## Public commands

| Command | Use it for |
|---|---|
| `/sweetclaude:go [request]` | Resume work or describe an outcome when you are unsure of the category. |
| `/sweetclaude:plan [request]` | Product strategy, discovery, requirements, scope, roadmaps, and planning. |
| `/sweetclaude:design [request]` | UX, architecture, data, API, and implementation design. |
| `/sweetclaude:build [request]` | Features, issues, tests, review, delivery, and execution tracking. |
| `/sweetclaude:maintain [request]` | Defects, incidents, debt, security patches, rollback, and postmortems. |
| `/sweetclaude:configure [request]` | Onboarding, project settings, diagnostics, migration, recovery, and SweetClaude lifecycle actions. |
| `/sweetclaude:utils [request]` | Corpus work, dashboards, recaps, meeting preparation, and exports. |
| `/sweetclaude:status` | Show the project’s current state. |
| `/sweetclaude:help` | Explain the system or help choose a command. |

`/sweetclaude:go` is the safe default. For example, `/sweetclaude:go we need to pivot` routes to planning; `/sweetclaude:go production is broken` routes to maintenance.

## How category routing works

1. Pick the category whose outcome best matches your request, or use `go`.
2. Describe the desired result in ordinary language. Include an existing issue number only when you want that issue implemented.
3. SweetClaude reads that category’s index, selects one library workflow, and loads only that workflow’s instructions.

The library workflow names below are documentation and routing vocabulary, not commands. They are intentionally not slash-addressable.

## Plan library

Use `/sweetclaude:plan` for: course correction; academic research; narrative arcs; epics; product briefs, discovery, competition, messaging, milestones, positioning, PRDs, research, roadmaps, terminology, personas, and user stories; scope; goals; and deferred-work management.

```text
/sweetclaude:plan write a product brief for the inventory app
/sweetclaude:plan prioritize our roadmap with RICE
/sweetclaude:plan define the first two user personas
```

## Design library

Use `/sweetclaude:design` for: architecture, technology specifications, data models, API contracts, UX, user flows, wireframes, mockup sandbox work, decision records, change-impact analysis, solution validation, UX reviews, and ultraplan preparation.

```text
/sweetclaude:design define the data model for inventory and stock movements
/sweetclaude:design review the checkout flow for accessibility
/sweetclaude:design create a mockup sandbox for the account settings flow
```

## Build library

Use `/sweetclaude:build` for: feature delivery; implementation of an existing GitHub issue; TDD, testing, verification, review, and shipping; backlog, sprint, theme, and epic execution; and project issue management.

```text
/sweetclaude:build implement GitHub issue #42
/sweetclaude:build add CSV import with tests
/sweetclaude:build run a security review before release
/sweetclaude:build plan the next sprint
```

### Issue tracking: local or GitHub

Every project has one issue tracker setting: `local` (the default) or `github`. During onboarding, SweetClaude can ask which to use. Change it later in ordinary language:

```text
/sweetclaude:build use GitHub for this project's issues
/sweetclaude:build use local issue tracking for this project
```

Selecting GitHub verifies `gh` authentication and the repository remote before changing project state. It does not silently import, sync, close, or delete issues. Requests to manage the tracker or create/view/update/close project issues route to the issue-management workflow. Requests to implement an already specified GitHub issue route to the implementation workflow.

## Maintain library

Use `/sweetclaude:maintain` for: debt reduction, production incidents, hotfixes, security fixes, deployment rollback or revert, and postmortems.

```text
/sweetclaude:maintain investigate the checkout outage
/sweetclaude:maintain patch CVE-2026-1234
/sweetclaude:maintain lock current behavior with tests before refactoring auth
```

## Configure library

Use `/sweetclaude:configure` for: first-time setup; project mode and feature settings; updates; diagnostics and repair; recovery; supported migration; hibernation; suspension or purge; usage settings; hook repair; and SweetClaude’s own regression checks.

```text
/sweetclaude:configure set this project up
/sweetclaude:configure diagnose and repair this project
/sweetclaude:configure migrate the legacy backlog if it is safe
/sweetclaude:configure update SweetClaude
```

Destructive actions such as purge remain confirmation-gated. Diagnostics begin read-only.

## Utilities library

Use `/sweetclaude:utils` for: document corpus consolidation, triage, reconciliation, promotion, and local RAG; dashboard and big-picture views; recaps and next steps; meeting preparation; documentation updates; session export; and explicitly requested failure reports.

```text
/sweetclaude:utils organize these research documents into a corpus
/sweetclaude:utils prepare for tomorrow's roadmap meeting
/sweetclaude:utils export this session
```

## What does not work

Old leaf-style names such as `code-feature`, `doctor`, and `product-brief` are no longer public commands. Use their category command plus an outcome instead. The internal loader and individual library workflows are implementation details and are never user-facing commands.

See [How It Works](how-it-works.md) for the architecture and [Migration and Recovery](migration-and-recovery.md) for project maintenance.
