# Workflows and Skills — content for sweetclaude:help Option 3

## Option 3 — Workflows and Skills (top-level)

SweetClaude has deep coverage across the full project lifecycle — from discovery and product definition through design, implementation, testing, and ship. Built natively on Claude Code's Skills framework and Anthropic's multi-agent architecture. You don't need to learn any of it. The single entry point is `/sweetclaude:go` — it reads your project state, figures out what to work on next, and drives the right workflow. Skills and workflows run automatically based on what you're doing.

For those who want to go deeper, skills compose into dynamic, situation-driven workflows — a feature build, for example, chains spec generation, isolated test writing, a multi-angle QA review, and implementation into a single pipeline. Workflows adapt to the project rather than following a fixed script.

The full inventory is in the skills reference: https://github.com/carson-sweet/sweetclaude/blob/main/docs/user-guide/index.md

## Option 3a — View all skills by phase

Here's the full skill set organized by the phase where they're most commonly used:

**Discover** — `product-discovery`, `user-personas`, `product-user-focus-group`, `product-competition`, `product-parking-lot`

**Define** — `product-brief`, `product-prd`, `product-terminology`, `product-user-stories`, `product-manage-scope`

**Design** — `design-architecture`, `design-data-model`, `design-api-design`, `design-ux`, `design-user-flows`, `design-wireframes`, `design-tech-spec`, `design-solutioning-gate`, `design-manage-decisions`, `design-change-impact-analysis`, `design-ux-review`

**Plan** — `project-backlog`, `project-sprints`, `project-themes`, `project-goals`, `project-scope`, `project-epics`, `epic-design`, `product-milestone-planning`, `product-milestones`, `product-roadmap`, `product-sprint-plan`

**Implement** — `code-feature`, `code-issue`, `code-debt`, `code-tdd`

**Verify** — `code-review`, `code-verify`, `testing-plan`, `testing-security`, `testing-accessibility`, `testing-performance`, `testing-compliance`, `testing-session`

**Ship** — `deploy-ship`

**Ongoing** — `status`, `go`, `recap`, `session-export`, `misc-meeting-prep`, `retro`, `next-steps`

I can explain any of these, or give you some examples of how these are dynamically combined into workflows, or anything else — tell me where you want to go next.

## Option 3b — Explore workflow examples

Here are three examples of how SweetClaude composes skills into workflows:

**Building a new feature (Structured mode)**
`code-feature` kicks off the pipeline: it generates Gherkin acceptance specs from the story, dispatches a test writer agent that produces failing tests, convenes a QA caucus that reviews the test plan from three angles, then dispatches an implementer agent to make them green. `code-review` and `code-verify` run before ship. The test writer and implementer never share context — each works in isolation.

**Responding to a production bug**
`something-broke` triages the incident, establishes a reproduction case, and identifies the root cause. `code-issue` runs the fix through a lightweight TDD cycle. `deploy-ship` handles the release. A post-mortem work item gets created automatically.

**Kicking off a new product**
`product-discovery` establishes personas and scenarios. `product-brief` produces the one-pager. `design-architecture` and `design-data-model` define the technical shape. `project-backlog` turns it into prioritized work. `sweetclaude:go` takes it from there.

In all cases, `/sweetclaude:go` is the entry point — it reads your project state and decides which workflow to run next.

## Option 3c — How does testing work?

SweetClaude doesn't ask you to do TDD — it enforces it. There's a difference.

Most AI coding tools will write tests if you ask. SweetClaude uses Claude Code hooks to make test discipline physically unavoidable:

- **Test-guardian hook** — blocks any edit to test files during the implementation phase. The implementer cannot modify tests to make them pass. Tests are written once, then locked.
- **Auto-test-runner hook** — runs the test suite automatically after every source file edit. You see RED or GREEN after every change, not at the end.

There are four TDD levels — you don't choose them manually, SweetClaude selects based on the operating mode and work type:

**Level 0 (Hotfix)** — Fix the immediate problem, write a regression test in the same session. No ceremony.

**Level 1 (Light)** — Tests written before implementation, all in one context. Right for simple additions and config changes.

**Level 2 (Standard)** — Test writer and implementer are separate subagents. The implementer never sees the spec — only failing tests. Test files are committed to git before implementation begins. Active in Kanban, Shape Up, and Agile modes.

**Level 3 (Full)** — Maximum isolation. Gherkin acceptance specs → test writer agent → QA caucus reviews the test plan from three independent angles → implementer agent makes tests go green. Active in John Wick mode and available on demand.

The rule underneath all of this: **never modify test files to make them pass. Fix the implementation.**
