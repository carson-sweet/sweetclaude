# Tiered Skill Architecture

**Status:** Implemented on `codex/tiered-skill-library`. User-facing references use `/sweetclaude:<category> <workflow>`; internal handoffs use `sweetclaude:library-load <workflow>`.  
**Version:** 1.1  
**Date:** 2026-10-20  
**Decision owner:** Product owner

## Decision

SweetClaude will expose a small, stable Tier 1 command surface and keep
specialized workflows as Tier 2 library skills. Tier 2 skills are **not**
directly slash-addressable. A Tier 1 category command or the default router
selects, reads, and executes the one Tier 2 workflow that matches the user's
goal.

The public categories are:

1. Plan
2. Design
3. Build
4. Maintain
5. Configure
6. Utils

`status`, `help`, and the default router remain public utilities rather than
categories.

## Why

The current installation exposes every packaged skill as a slash command.
That makes the command surface hard to scan, gives specialized procedures
equal prominence with the normal entry points, and loads discovery metadata
for the whole catalog at session start. The existing catalog has 122 skills;
the full bodies should remain on-demand resources rather than a public command
menu.

This design makes the normal interaction simple:

```text
Tell SweetClaude what you need
        |
        v
/sweetclaude:go or a category command
        |
        v
Tier 1 classifies the request and reads one category index
        |
        v
The category index selects and loads one Tier 2 workflow
        |
        v
That workflow owns its normal checks, execution, and handoff
```

The categorization is a routing aid. It does not weaken project-state gates,
hooks, evidence requirements, or user approval requirements in the selected
workflow.

## Public Tier 1 commands

| Command | Role | Must not do |
|---|---|---|
| `/sweetclaude:go` | Default natural-language entry point. Reads project state and routes to a category or a Tier 2 workflow. | Reimplement every category's procedure. |
| `/sweetclaude:plan` | Enter planning: problem framing, research, scope, priorities, roadmap, and work selection. | Make architecture or code changes. |
| `/sweetclaude:design` | Enter solution design: architecture, specifications, models, APIs, UX, and decisions. | Implement the solution. |
| `/sweetclaude:build` | Enter delivery execution: work-item coordination, implementation, verification, review, and shipping. | Treat an unverified result as complete. |
| `/sweetclaude:maintain` | Improve or repair the product/codebase: refactoring, debt, upgrades, performance, and incident remediation. | Change SweetClaude's own operating configuration. |
| `/sweetclaude:configure` | Configure or repair SweetClaude itself: onboarding, modes, state, hooks, updates, migration, recovery, and deactivation. | Perform product-code maintenance as a side effect. |
| `/sweetclaude:utils` | Route cross-cutting, task-shaped utilities that do not own a lifecycle category. | Become an uncategorized dumping ground. |
| `/sweetclaude:status` | Report current project, active work, and blockers. | Advance work or mutate state merely to produce a report. |
| `/sweetclaude:help` | Explain the public surface and provide examples. | Load the complete library merely to enumerate it. |

The Tier 1 commands may be implemented by a small set of dispatcher skills;
they do not need nine unrelated orchestration implementations. Their command
names are a public compatibility contract once released.

## Category ownership

| Category | Owns | Representative Tier 2 workflows | Excludes |
|---|---|---|---|
| Plan | What to do and why: discovery, research, users, requirements, priorities, roadmap, scope, goals, work selection. | product discovery, research, personas, brief, PRD, roadmap, backlog/issue planning | Architecture, code, and framework setup. |
| Design | How the selected work should be shaped: technical design, APIs, data, UX, wireframes, and decisions. | architecture, tech spec, data model, API design, UX, design decisions | Building and shipping. |
| Build | Deliver planned work: issue coordination, implementation, TDD, verification, review, QA, security review, and shipping. | feature/issue implementation, code review, code verify, testing, sprint execution | Refactors or repairs whose primary purpose is codebase health. |
| Maintain | Improve or repair the product/codebase: debt, refactors, dependencies, performance, security patches, hotfixes, rollback, incident response, and postmortems. | code debt, dependency upgrade, performance work, hotfix, rollback, postmortem | Plugin setup, state repair, or framework upgrades. |
| Configure | Operate SweetClaude: first-run setup, modes, guardian, health/doctor, recovery, migration, update, usage, hibernation, disablement. | init, setup, doctor, recover, migrate, update, mode, guardian, off | Product backlog, code cleanup, or release delivery. |
| Utils | Cross-cutting utilities with a bounded output that do not own a lifecycle phase. | meeting prep, session export, document/corpus operations, sandbox/extraction utilities | Any recurring Plan, Design, Build, Maintain, or Configure workflow. |

### Boundary rules

- **Maintain changes the product/codebase; Configure changes SweetClaude's
  operation for that project.** This distinction is mandatory.
- Issues, epics, backlogs, and sprints are Build delivery coordination, even
  when they contain no source-code edit in a particular invocation.
- A utility that develops a recurring lifecycle, state machine, or ownership
  boundary must move out of Utils into its owning category.
- A workflow may link to a downstream category, but it must not silently
  execute it. The downstream workflow remains the authority for its own gates.

## Tier 2 library contract

Tier 2 is a library, not a second slash-command surface.

Each Tier 2 workflow must have:

1. exactly one primary user outcome;
2. an unambiguous trigger and non-goals;
3. one owning category and one entry in that category's index;
4. explicit inputs, mutations, outputs, and completion/hand-off behavior;
5. links to optional references, templates, and scripts instead of embedding
   unrelated background material in its root instructions; and
6. no assertion that it is publicly invocable as a slash command.

The dispatcher reads only the selected category index first. It then reads one
chosen workflow and only the references required by that workflow. A category
index must not inline its constituent workflow bodies.

### Tier 2 selection contract

1. The user may enter through `go`, a category command, or natural language.
2. Tier 1 selects one category from the request and current state.
3. The category index selects one workflow based on its declared trigger.
4. If two workflows are plausible and their choice would materially change
   scope or mutation authority, Tier 1 asks one focused clarification.
5. Tier 1 passes the original request and relevant state to the selected
   workflow; it does not summarize away safety-relevant constraints.
6. The selected workflow owns execution. A dispatcher does not claim its
   gates passed without the workflow's prescribed evidence.

## Installation shape

The installed plugin must separate discovery from the library:

```text
skills/                       # Tier 1 only: public commands and internal router
  go/
  plan/
  design/
  build/
  maintain/
  configure/
  utils/
  status/
  help/
  _route/
skill-library/                # Not discovered as slash commands
  plan/
    INDEX.md
    product-discovery/
    ...
  design/
    INDEX.md
    ...
  build/
    INDEX.md
    ...
  maintain/
    INDEX.md
    ...
  configure/
    INDEX.md
    ...
  utils/
    INDEX.md
    ...
```

The exact filesystem mechanism must be verified against the target Claude Code
plugin discovery behavior before migration. The invariant is behavioral: only
Tier 1 appears in the default slash-command catalog; Tier 2 remains readable
by the dispatcher at a stable installed path.

`scripts/sync-to-installed.sh`, package validation, release checks, direct
path references, and documentation must be updated together. A move is not
complete merely because an individual workflow can still be read in a source
checkout.

## Skill audit to follow this design

The next activity is an evidence-backed library audit, not an immediate bulk
move. Every current skill receives one disposition:

| Disposition | Meaning |
|---|---|
| Retain | A focused workflow with a distinct outcome and owner. |
| Consolidate | Shares one outcome, authority, and lifecycle with another workflow. |
| Split | Contains multiple independently selectable outcomes, authorities, or mutation boundaries. |
| Reclassify | Is focused but belongs in a different category. |
| Retire | Is obsolete, a compatibility redirect with no enduring user value, or duplicates a canonical path. |
| Keep internal | Remains a Tier 1 or library support component but is not user-selectable. |

### Audit questions

For each skill, answer from its source and current callers:

1. What single recognizable user goal does it own?
2. What trigger distinguishes it from its nearest neighbor?
3. Does it decide or mutate something that another skill already owns?
4. Are its input, output, mutation scope, and completion condition explicit?
5. Is it a workflow, a reusable reference, a template, a script, a redirect,
   or a router mislabeled as a workflow?
6. Does it need a public command, a Tier 2 library entry, or only an internal
   helper role?
7. Does its full instruction body contain unrelated branches that should be
   separate workflows or linked references?
8. Does its declared description make the intended trigger clear enough for
   reliable routing?

The audit must preserve deterministic controls. A consolidation cannot merge
workflows merely because their prose sounds similar if they have different
state transitions, evidence gates, approval authority, or mutation scope.

## Migration gates

No Tier 2 move is complete until all of these are true:

1. The workflow has a category, disposition, and canonical owner recorded in
   the audit ledger.
2. Every known route, manifest entry, script path, documentation link, test,
   and cross-skill reference resolves to its new canonical location or an
   explicit compatibility redirect.
3. The public Tier 1 catalog exposes only the nine commands above.
4. A fixture can route a representative request through `go` and through its
   category command to the same intended library workflow.
5. The workflow's current deterministic checks still run from the installed
   library path.
6. Legacy direct slash commands either fail with a clear migration message or
   are retained as intentional, time-bounded compatibility aliases.
7. Installation, update, and release validation prove that Tier 2 is present
   but not slash-discovered in a clean installation.

## Risks and safeguards

| Risk | Safeguard |
|---|---|
| A dispatcher guesses the wrong workflow. | Category indexes use explicit trigger and non-goal rules; ask when the choice changes authority or scope. |
| A library move breaks a hard-coded path. | Exhaustive repository reference inventory and installed-path fixture before each migration batch. |
| Tiering hides an emergency repair path. | `configure` routes doctor/recovery directly; its minimal repair path remains Tier 1. |
| Utils becomes a junk drawer. | Every Utils entry needs a bounded output and an explicit non-lifecycle rationale; recurring workflows are reclassified. |
| Consolidation removes a safety distinction. | Compare state transitions, mutation authority, and gate/evidence contracts before merging. |
| Documentation drifts from the installed catalog. | Generate or verify the public-command list and audit ledger in release validation. |

## Non-goals

- This design does not consolidate, split, move, or retire any existing skill.
- This design does not change phase gates, state schemas, hooks, or workflow
  evidence requirements.
- This design does not promise a particular Claude Code plugin discovery
  mechanism before it is verified in a clean installation.
- This design does not require every Tier 2 workflow to be implemented as a
  new skill; a reference, script, or template should remain that simpler form
  when it does not own a user workflow.

## Implementation sequence

1. Build the audit ledger from the current catalog and record dispositions.
2. Define the Tier 1 dispatcher contract and category-index schema.
3. Prototype the installed directory split in an isolated fixture; verify
   slash discovery and on-demand library loading.
4. Migrate one low-risk category end-to-end, including references, tests,
   installation, and compatibility behavior.
5. Review the measured context surface and routing accuracy.
6. Migrate remaining categories in bounded batches, stopping on any routing or
   gate regression.

The audit ledger is the next artifact. It must be completed before the first
bulk library relocation.
