# Build Library Index

This index is read only after Tier 1 selected this category. Choose one workflow; do not load every workflow body.

**Selection boundary:** requests to choose, switch, configure, list, create, or
otherwise manage the project's issue tracker belong to `project-issues`.
Choose `code-issue` only when the user supplies an existing GitHub issue to
implement. In particular, “use GitHub for this project's issues” must load
`project-issues`, never `code-issue`.

| Workflow | Trigger / outcome |
|---|---|
| `code-feature` | Build a new feature end-to-end. |
| `code-issue` | Implement a specified, existing GitHub issue end-to-end; not for tracker configuration or issue management. |
| `code-review` | Code, security, and compliance review. |
| `code-tdd` | Internal TDD process skill — invoked by code-feature, code-issue, and code-debt. |
| `code-testing` | Run any combination of test suite, mutation testing, security review, and PR pre-check. |
| `code-verify` | Run verification before claiming work is complete. |
| `deploy-ship` | SHIP phase skill. |
| `john-wick` | Fully autonomous, resumable, multi-session SDLC pipeline. |
| `john-wick-checkin` | Internal John Wick phase check-in subagent. |
| `large-story` | Internal bounded, evidence-gated large-story workflow. |
| `orchestrator` | Orchestrator main loop — executes tracked workflow steps via subagents. |
| `product-sprint-plan` | Plan a sprint by selecting stories from the backlog, estimating scope, and producing a sprint commitment. |
| `product-user-tdd-tests` | Transition user stories into Gherkin .feature files. |
| `project-backlog` | View and manage the unscheduled issue backlog. |
| `project-backlog-triage` | Structured backlog grooming session. |
| `project-epics` | DEPRECATED — use /sweetclaude:plan epics instead. Redirects automatically. |
| `project-gh-import-issues` | Import open GitHub Issues into the local issue store as v4 story files. |
| `project-gh-sync-issues` | Bidirectional status sync between local issue files and GitHub Issues. |
| `project-issues` | Manage project issues and select the local or GitHub issue tracker — list, view, create, update, close, or change tracker. |
| `project-sprints` | Sprint planning, activation, board view, and close. |
| `project-themes` | Manage themes — optional domain-grouping labels on stories. |
| `small-story` | Internal bounded, evidence-gated small-story workflow. |
| `testing-accessibility` | WCAG 2.1 Level AA audit. |
| `testing-compliance` | Compliance control testing and evidence collection. |
| `testing-performance` | Define load scenarios, establish performance baselines, set thresholds. |
| `testing-plan` | Define and maintain a test strategy for a feature or release. |
| `testing-security` | Structured security review. |
| `testing-session` | Run a manual QA session. |
