# SweetClaude Phase Gates

Entry and exit criteria for each phase. A phase cannot advance until exit criteria are met (user can override).

> Skills are organized into five domain buckets (strategy, product, design, code, deploy). Phase gates reference skills by their bucket path. See `phase-skills.yaml` for the full mapping.

## Phase 1: DISCOVER
**Entry:** New project or escalation from later phase
**Exit criteria (net-new products/apps):**
- User personas defined: at least one persona with job title, tasks, and success criteria per task — iterative loop completed until user confirmed all personas captured
- Personas and tasks consolidated: single view presented to user, verified correct
- Feature set established: core features defined, with optional brainstorming round(s) completed if user requested
- Concrete scenario: at least one specific user scenario or real-world example per persona
- Challenged at least once: at least one alternative framing, potential gap, or questionable assumption was raised and addressed
- Scope boundary: at least one thing has been explicitly identified as out of scope
- Key decisions documented in decision log
- Competitive analysis offered: user accepted or declined; if accepted, research artifacts saved
- Improvement check-in: "Before we move on — anything about how this phase went that I should do differently?"
**Exit criteria (CLIs, libraries, utilities):**
- Primary user identified with tasks and success criteria
- Core features defined
- Scope boundary established
- Key decisions documented in decision log
**Available skills:** product/discovery, strategy/concept, strategy/pain-thesis, strategy/competitive-analysis, product/research, caucus, reasoning-frameworks

## Phase 2: DEFINE
**Entry:** DISCOVER complete, OR bug fix/enhancement/iteration entering pipeline
**Exit criteria (net-new features):**
- All 11 sections populated: product brief has substantive content in Executive Summary, Problem Statement, Target Audience, Solution Overview, Business Objectives, Scope, Stakeholders, Constraints/Assumptions, Success Criteria, Timeline, and Risks — a section with only a single sentence or generic filler ("TBD", "N/A" without justification) counts as missing
- Concrete problem example: problem statement includes at least one specific scenario, user story, or real-world example
- Explicit out-of-scope: scope section has 3+ items in the out-of-scope list — if fewer, either the scope is too narrow to need a brief or the boundaries haven't been thought through
- Measurable success: each success criterion can be evaluated as true or false after the project ships — "users are happy" fails; "user completes primary workflow in under 3 steps" passes
- BMAD validation checklist: the 9-item checklist has been run with all items passing or explicitly waived by the user with documented rationale
- PRD with FRs, NFRs, and epics (for larger work requiring a PRD)
- Improvement check-in: "Before we move on — anything about how this phase went that I should do differently?"
**Exit criteria (other work types):**
- Bug reproduction documented (for bug fixes)
- Enhancement scope defined (for enhancements)
- Improvement criteria defined (for iteration)
**Available skills:** product/product-brief, product/prd, product/manage-scope, product/backlog, product/user-success-criteria, design/change-impact-analysis, reconciling-documents

## Phase 3: DESIGN
**Entry:** DEFINE complete
**Exit criteria:**
- Architecture document approved (for features requiring architecture)
- Tech spec approved (for features requiring technical design)
- Design change identified (for bug fixes — may be trivial)
- Solutioning gate passed (for complex work)
- Improvement check-in
**Available skills:** design/architecture, design/tech-spec, design/ux, design/solutioning-gate, design/data-model, design/api-design, design/services-design, design/infra-design, design/change-impact-analysis, design/manage-decisions, caucus, reasoning-frameworks

## Phase 4: PLAN
**Entry:** DESIGN complete
**Exit criteria:**
- User stories written with acceptance criteria
- Gherkin .feature files generated (for TDD Level 3)
- Sprint plan (if applicable)
- Traceability map started
- Improvement check-in
**Available skills:** product/user-story, product/user-tdd-tests, product/user-workflows, product/sprint-plan, product/backlog

## Phase 5: IMPLEMENT
**Entry:** PLAN complete (or DEFINE/DESIGN complete for simpler work types)
**Exit criteria:**
- All tests pass (RED → GREEN completed)
- Implementation satisfies acceptance criteria
- Change-impact analysis completed (for changes to existing code)
- Code committed
- Improvement check-in
**Available skills:** code/tdd, code/work-issue, code/work-debt, design/change-impact-analysis, superpowers:writing-plans, superpowers:executing-plans, superpowers:using-git-worktrees, superpowers:systematic-debugging, superpowers:dispatching-parallel-agents
**Hooks active:** test-guardian, auto-test-runner, git-checkpoint

## Phase 6: VERIFY
**Entry:** IMPLEMENT complete (all tests green)
**Exit criteria:**
- Code review completed (no critical findings)
- Security review completed (if applicable)
- PR template filled
- Documentation updated
- Traceability map complete
**Available skills:** code/pr-precheck, code/qa-testing, code/mutation-testing, code/security-testing, code/code-review, design/update-docs, superpowers:verification-before-completion

## Phase 7: SHIP
**Entry:** VERIFY complete
**Exit criteria:**
- PR merged
- Deployment successful (if applicable)
- Post-deploy verification (if applicable)
**Available skills:** superpowers:finishing-a-development-branch, sweetclaude:hibernate

## Cross-Phase Skills

These skills are available in ALL phases via `always_loaded` in phase-skills.yaml:

- **sweetclaude** — Master router, session entry point
- **sweetclaude:new-task** — Classify work and enter pipeline
- **sweetclaude:hibernate** — Freeze or thaw a project at any point
