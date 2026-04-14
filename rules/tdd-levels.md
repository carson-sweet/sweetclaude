# SweetClaude TDD Levels

## Level Selection Guide

| Work Type | Complexity | Recommended Level |
|---|---|---|
| Production hotfix | Any | Level 0 |
| Simple CRUD, config change | Low | Level 1 |
| Bug fix with clear scope | Low-Medium | Level 1-2 |
| Feature with defined behavior | Medium | Level 2 |
| Feature with Gherkin specs | Medium-High | Level 3 |
| Complex feature, many edge cases | High | Level 3 |
| Refactoring existing code | Any | Level 1 (lock behavior first) |

## Level Definitions

### Level 0: Hotfix
- Fix the immediate problem
- Write regression test in the same session
- No grace period — the test happens now, not "within 48 hours"
- Commit test + fix together

### Level 1: Light
- Single context — no subagent separation
- Write test → verify RED → implement → verify GREEN → refactor
- Tests still come first. Still confirmed RED before implementation.
- Appropriate for: simple additions, config, straightforward CRUD, small bug fixes

### Level 2: Standard
- Subagent separation: test writer context ≠ implementer context
- Tests committed to git before implementation begins
- Test-guardian hook active: test files are immutable during implementation
- Auto-test-runner hook active: tests run after every source edit
- Appropriate for: features, significant bug fixes, behavior changes

### Level 3: Full (from Gherkin)
- Full pipeline: Gherkin .feature → test writer agent → QA caucus → user approval → implementer agent
- Maximum context isolation — test writer sees Gherkin, implementer sees tests, neither sees the other's reasoning
- QA caucus reviews test plan from three angles before implementation starts
- Mutation testing available after GREEN
- Appropriate for: net-new features with user stories, complex behavior

## Enforcement Rules

- **Test-guardian hook** blocks edits to test files during implementation (Levels 1-3)
- **Auto-test-runner hook** runs tests after source edits during implementation (Levels 1-3)
- **Git checkpoint** commits failing tests before implementation starts (Levels 2-3)
- **Subagent isolation** ensures test writer and implementer have separate contexts (Levels 2-3)
- **No mocks by default** — real dependencies, real databases, real function calls (all levels)

## Override

User can always override the recommended level. User can also override test immutability with explicit approval. The system respects the user's judgment — these are guardrails, not cages.
