---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Natural language classifier — maps user text to the right internal skill."
---

# Route

Classify `$ARGUMENTS` and invoke the matched skill. Do not ask the user for clarification first — make a call, then confirm if the match is non-obvious.

## Explicit override (check first)

If `$ARGUMENTS` begins with `use ` followed by a known workflow name, bypass classification and route directly:

Known workflow names (case-insensitive):
`code-feature`, `code-issue`, `code-debt`, `code-review`, `code-testing`,
`something-broke`, `deploy-ship`, `design-architecture`, `design-tech-spec`,
`design-api-design`, `design-data-model`, `design-ux`, `design-wireframes`,
`design-user-flows`, `product-discovery`, `product-brief`, `product-prd`,
`user-personas`, `product-user-stories`, `product-milestones`,
`product-backlog`, `project-issues`, `project-sprints`, `testing-plan`,
`testing-security`, `testing-accessibility`, `john-wick`, `adopt`

Example: `use code-feature` → invoke `sweetclaude:code-feature`

## Classification table

If no explicit override, classify by dominant signal in `$ARGUMENTS`:

| Signal | Examples | Route to |
|--------|----------|---------|
| Incident / broken | "broke", "error", "crash", "down", "not working", "exception", "failing in prod" | `sweetclaude:something-broke` |
| Status / review | "where are we", "what's done", "show me status", "what's next", "what have we done" | Surface status from `sweetclaude.yaml` inline — show project · version_stage · active work · last 3 history items |
| Help / explain | "how do I", "explain", "what is", "help me understand", "show me how" | `sweetclaude:help` |
| Build / feature | "build", "add", "implement", "create", "new feature", "I want to" | `sweetclaude:code-feature` |
| Bug / fix | "bug", "fix", "broken", "wrong", "regression", "not working as expected" | `sweetclaude:code-issue` |
| Refactor / debt | "refactor", "clean up", "restructure", "tech debt", "messy", "untangle" | `sweetclaude:code-debt` |
| Review | "review", "check my code", "look at this PR", "feedback on" | `sweetclaude:code-review` |
| Deploy / ship | "deploy", "ship", "release", "go live", "push to prod" | `sweetclaude:deploy-ship` |
| Design | "design", "architecture", "spec", "API", "schema", "data model", "wireframe" | `sweetclaude:design-architecture` (default) — refine to specific design skill based on context |
| Product | "product brief", "PRD", "personas", "user stories", "roadmap", "milestones" | `sweetclaude:find-skill` with `$ARGUMENTS` |
| Testing | "test", "QA", "accessibility", "security audit", "performance" | `sweetclaude:testing-plan` (default) |
| Default | anything else | `sweetclaude:find-skill` with `$ARGUMENTS` |

## Confirmation

For non-obvious matches (anything without a strong single signal), confirm before invoking:
> "That sounds like [work type]. Starting [skill name description]? (Yes / tell me more)"

For strong single-signal matches (`build X`, `fix Y`, `deploy`, `something broke`), invoke directly without confirmation.

## After routing

Invoke the matched skill. Pass `$ARGUMENTS` as context. The matched skill handles its own flow from there.
