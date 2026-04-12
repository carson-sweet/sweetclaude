# SweetClaude Phase Gates

Entry and exit criteria for each phase. A phase cannot advance until exit criteria are met (user can override).

## Phase 1: DISCOVER
**Entry:** New project or escalation from later phase
**Exit criteria:**
- Problem/concept clearly articulated
- Research complete (competitive landscape, prior art if applicable)
- Key decisions documented in decision log
- Ready to define scope and requirements
**Available skills:** bmad:brainstorm, bmad:research, caucus, reasoning-frameworks

## Phase 2: DEFINE
**Entry:** DISCOVER complete, OR bug fix/enhancement/iteration entering pipeline
**Exit criteria:**
- Product brief approved (for net-new features)
- PRD with FRs, NFRs, and epics (for larger work)
- Bug reproduction documented (for bug fixes)
- Enhancement scope defined (for enhancements)
- Improvement criteria defined (for iteration)
**Available skills:** bmad:product-brief, bmad:prd, sweetclaude:work-router, sweetclaude:ripple, reconciling-documents, backlog-management

## Phase 3: DESIGN
**Entry:** DEFINE complete
**Exit criteria:**
- Architecture document approved (for features requiring architecture)
- Tech spec approved (for features requiring technical design)
- Design change identified (for bug fixes — may be trivial)
- Solutioning gate passed (for complex work)
**Available skills:** bmad:tech-spec, bmad:architecture, bmad:create-ux-design, bmad:solutioning-gate-check, sweetclaude:ripple, caucus, reasoning-frameworks

## Phase 4: PLAN
**Entry:** DESIGN complete
**Exit criteria:**
- User stories written with acceptance criteria
- Gherkin .feature files generated (for TDD Level 3)
- Sprint plan (if applicable)
- Traceability map started
**Available skills:** bmad:create-story, bmad:sprint-planning, sweetclaude:gherkin-bridge, backlog-management

## Phase 5: IMPLEMENT
**Entry:** PLAN complete (or DEFINE/DESIGN complete for simpler work types)
**Exit criteria:**
- All tests pass (RED → GREEN completed)
- Implementation satisfies acceptance criteria
- Ripple-effect analysis completed (for changes to existing code)
- Code committed
**Available skills:** sweetclaude:tdd, sweetclaude:fix-issue, sweetclaude:ripple, superpowers:writing-plans, superpowers:executing-plans, superpowers:using-git-worktrees, superpowers:systematic-debugging, superpowers:dispatching-parallel-agents
**Hooks active:** test-guardian, auto-test-runner, git-checkpoint

## Phase 6: VERIFY
**Entry:** IMPLEMENT complete (all tests green)
**Exit criteria:**
- Code review completed (no critical findings)
- Security review completed (if applicable)
- PR template filled
- Documentation updated
- Traceability map complete
**Available skills:** sweetclaude:pr-ready, sweetclaude:ripple, sweetclaude:auto-docs, superpowers:requesting-code-review, superpowers:verification-before-completion, superpowers:simplify

## Phase 7: SHIP
**Entry:** VERIFY complete
**Exit criteria:**
- PR merged
- Deployment successful (if applicable)
- Post-deploy verification (if applicable)
**Available skills:** superpowers:finishing-a-development-branch, sweetclaude:pr-ready
