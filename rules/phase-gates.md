# SweetClaude Phase Gates
# Schema version: 2
# Generated from: docs/superpowers/specs/2026-04-29-phase-workflow-separation-design.md

Entry and exit criteria for each work type × phase combination.
A phase cannot advance until exit criteria are met.
User can override with "I've addressed this informally — proceed" (soft gate).
Hard gates are marked ⚠️ and cannot be soft-bypassed at GA+.

> See config/workflow-templates.yaml for the phase sequence per work type.
> See config/workflow-templates.yaml hard_gate_policy for the full gate policy.

## Phase Definitions

### Standard phases (all work types)
- **DISCOVER** — understand the problem space before committing to a solution
- **DEFINE** — specify what will be built and how success is measured
- **DESIGN** — decide the technical approach before writing code
- **PLAN** — break work into stories, tests, and tasks
- **IMPLEMENT** — write the code, making tests go from RED to GREEN
- **VERIFY** — review, test, and validate the implementation
- **SHIP** — merge, deploy, and confirm in production

### New phases (specific work types)
- **DIAGNOSE** — understand root cause before fixing. Reproduction case, baseline benchmark, or incident triage.
- **ASSESS** — map scope and risk before committing. What's affected? What's the rollback plan?
- **SCOPE** — lock existing behavior with tests before refactoring. Defines what changes and what must not.
- **TRIAGE** — review all in-flight work after a course correction: keep / drop / repurpose.
- **CUTOVER** — switch traffic or data from old system to new. Both have been running in parallel.
- **CLEANUP** — remove old system artifacts after cutover or deprecation sunset.
- **POST-MORTEM** — required follow-on after hotfix or rollback. What happened, why, what changes.

---

## Net-new feature

**DISCOVER**
- At least one persona defined: role, primary tasks, success criteria per task
- At least one concrete real-world scenario per persona
- Core feature set established
- At least one thing explicitly out of scope
- At least one assumption challenged or alternative framing raised
- Competitive landscape assessed or explicitly declined
- Key decisions in decision log

**DEFINE**
- Product brief: all 11 sections substantively populated (no TBD, no single-sentence sections)
- Problem statement includes a specific scenario or real-world example
- Scope section has 3+ explicit out-of-scope items
- Every success criterion is measurable (true/false evaluable post-ship)
- PRD written: functional requirements, non-functional requirements, epics

**DESIGN**
- Architecture document written and reviewed
- Tech spec written and reviewed
- Data model designed
- API contracts defined (if applicable)
- UX flows documented
- Solutioning gate passed
- Key design decisions recorded

**PLAN**
- User stories written with acceptance criteria for all epics
- Gherkin .feature files or test specs generated
- Traceability map started (stories → requirements)

**IMPLEMENT**
- All tests passing (RED → GREEN complete)
- All acceptance criteria satisfied
- Change impact analysis complete (if modifying existing code)
- Code committed

**VERIFY**
- Code review complete — no critical findings open
- Security review complete (if security-sensitive)
- All tests passing in CI
- Documentation updated
- Traceability map complete

**SHIP**
- Security review complete, OR security surface explicitly confirmed absent (skip reason logged in checkpoint)
- PR merged or code deployed
- Smoke test passing in production
- Changelog / release notes updated

---

## External integration

**DISCOVER**
- External service purpose confirmed and justified
- API documentation reviewed: auth model, rate limits, data contracts, error handling, quotas
- Integration approach decided: webhook vs. polling, SDK vs. raw HTTP
- Sandbox/test environment confirmed available (or unavailability documented)
- External service cost/pricing confirmed
- Failure modes and fallback strategy identified

**DEFINE**
- Integration scope defined: what data flows in/out, under what conditions
- Error handling strategy defined: degraded behavior when external service is unavailable
- SLA of external service noted (becomes a ceiling on your own SLA)
- Blocking dependencies identified

**DESIGN**
- External service abstracted behind a clean interface (not called directly throughout codebase)
- Contract tests designed: what behavior must the external service exhibit
- Data mapping documented: external schema → internal schema
- Auth flow designed and reviewed
- Retry, timeout, and circuit-breaker strategy designed

**PLAN**
- Task breakdown complete
- Contract tests written (test external service behavior, not your code)
- Integration tests designed

**IMPLEMENT**
- Adapter implemented behind interface
- Contract tests passing against sandbox
- Integration tests passing
- Error/fallback paths implemented and tested
- Auth flow implemented and tested

**VERIFY**
- Code review complete
- Security review complete: credentials stored correctly, no secrets in code
- Contract tests passing
- Integration tested against real external service (not just sandbox)
- Failure/fallback scenarios tested end-to-end

**SHIP**
- Security review complete, OR security surface explicitly confirmed absent (skip reason logged in checkpoint)
- Deployed and verified against production external service
- Monitoring configured for integration health
- Documentation updated
- Break-glass notes updated with integration failure procedure

---

## Course correction

**DISCOVER**
- Signal that triggered the correction documented
- Signal aggregation confirmed: this is a pattern, not a single data point
- New direction clearly articulated
- Old direction clearly stated (for comparison and traceability)
- Assumptions being invalidated identified

**DEFINE**
- Revised direction document or updated product brief written
- Updated personas (if the target user is changing)
- New scope established
- Old scope formally retired and documented

**TRIAGE**
- All in-flight work items reviewed and each tagged: keep / drop / repurpose / defer
- Impact on existing users assessed: what breaks, what changes
- Data migration needs identified (if user-facing changes require it)
- New backlog items created from repurposed work
- Dropped items closed with documented rationale

**SHIP**
- Revised direction committed to project state
- Backlog updated and clean — no zombie items from old direction
- Decision log updated with the course correction and rationale
- Follow-on work items created

---

## Security planning

**DISCOVER**
- User interviewed on: business model, customer types, data handled (PII, health, financial), current and target markets
- Regulatory environment assessed: which standards apply now, which will apply at scale
- Current security posture assessed: existing controls documented

**DEFINE**
- Applicable standards mapped with rationale and business trigger:
  - GDPR: required if EU users handle personal data
  - SOC 2 Type 1: 6–12 months before SOC 2 Type 2 is needed
  - SOC 2 Type 2: required when approaching larger B2B customers
  - HIPAA: required if handling protected health information
  - PCI-DSS: required if processing payment card data
- Phased roadmap written: what to achieve by when, tied to version_stage milestones
- Quick wins identified: controls to implement now regardless of stage

**SHIP**
- Security roadmap document committed to project
- Quick-win controls added to backlog with priority
- Any currently overdue items flagged against current version_stage

---

## Enhancement / iteration

**DEFINE**
- Change scoped: what is being improved and how
- Existing behavior documented: what changes, what stays the same
- Success criteria defined: how will we know the enhancement worked
- Change impact analysis complete: what else might be affected

**DESIGN**
- Approach decided and documented
- If UX change: updated flows reviewed
- If API change: contracts reviewed, backward compatibility assessed
- Edge cases identified

**IMPLEMENT**
- Tests written for new/changed behavior (RED → GREEN)
- Existing tests still passing (no regressions)
- Code committed

**VERIFY**
- Code review complete
- All tests passing
- Enhancement behaves as specified in success criteria

**SHIP**
- Security review complete, OR security surface explicitly confirmed absent (skip reason logged in checkpoint)
- Deployed and smoke tested
- Documentation updated if behavior changed
- Changelog entry added

---

## Tech debt / refactor

**DEFINE**
- Scope defined: what code is changing, what patterns are being introduced or removed
- Motivation documented: why is this debt, what problem does it cause
- Risk assessed: what could break

**SCOPE**
- Existing behavior locked with tests — suite covers all behavior that must be preserved
- Tests confirmed to fail if any locked behavior changes (verified against a deliberate break)
- Refactor boundaries defined: what's in scope for this session, what's deferred
- Rollback plan documented

**IMPLEMENT**
- Refactored code passes all existing tests
- No new test failures
- No behavior changes — only structural changes
- Code is measurably cleaner than before

**VERIFY**
- Code review confirms: behavior unchanged, structure improved, no new complexity introduced
- All tests passing
- No performance regression

**SHIP**
- Deployed and smoke tested
- No incidents in first deployment window
- Decision log updated with what changed and why

---

## Compliance requirement

**ASSESS**
- Requirement identified precisely: which standard, which control, which clause
- Gap analysis complete: what exists, what is missing
- Evidence requirements understood: what must be produced to prove compliance
- Timeline established: is there an audit date or certification deadline
- External dependencies identified: auditor, legal review, third-party tools

**DEFINE**
- Controls to implement documented
- Acceptance criteria for each control defined (what does "compliant" look like)

**DESIGN**
- Technical approach for each control designed
- Impact on existing architecture assessed
- Data handling changes reviewed (retention, encryption, access controls)

**IMPLEMENT**
- All controls implemented
- Evidence artifacts generated (logs, policies, access records)
- Documentation written

**VERIFY**
- Security review complete
- Each control tested against its acceptance criteria
- Evidence package assembled and reviewed
- Legal/compliance review complete (if required by the standard)

**SHIP**
- Controls deployed to production
- Evidence archived in the designated location
- Audit trail established
- Next review date scheduled and added to backlog

---

## Infrastructure change

**DEFINE**
- Change scoped: what infrastructure is changing and why
- Risk level assessed: downtime possible? data risk? performance impact?
- Rollback plan exists before any design begins

**DESIGN** ⚠️ HARD GATE at GA+: solutioning gate required, no soft bypass
- Solutioning gate passed
- Architecture reviewed for the change
- Rollback procedure documented in detail — not just "revert the commit," step-by-step
- Monitoring plan defined: what signals confirm healthy state after change
- Change window planned if downtime is required

**IMPLEMENT**
- Change implemented and verified in staging first
- Runbook written: step-by-step execution with rollback steps at each stage

**VERIFY**
- Staging smoke test passing
- Performance verified: no regression
- Security posture verified: no new exposure introduced
- Rollback tested in staging if possible

**SHIP**
- Security review complete, OR security surface explicitly confirmed absent (skip reason logged in checkpoint)
- Change deployed to production
- Monitoring confirming healthy signals
- Rollback procedure on standby for first 24 hours
- Break-glass notes updated

---

## Onboarding flow design

**DEFINE**
- Target persona confirmed: who is being onboarded
- Success metric defined: what does a successfully onboarded user do or know
- Current drop-off points identified (if product is live)
- Explicit out-of-scope: what this onboarding flow will not try to do

**DESIGN**
- Flow mapped step-by-step
- UX for each step designed: screens, copy, interactions
- Edge cases handled: incomplete onboarding, re-entry, skipping steps
- At least one real user has reviewed the flow (even informally)

**IMPLEMENT**
- Flow implemented and testable end-to-end
- Analytics events instrumented at each step
- Edge cases implemented

**VERIFY**
- End-to-end test passing
- Analytics events confirmed firing correctly
- Code review complete

**SHIP**
- Deployed and walked through by at least one real user
- Completion rate baseline established
- Onboarding playbook updated to reflect new flow

---

## Release planning

**DEFINE**
- Release scope locked: exactly what's in, what's deferred
- Version number assigned
- Breaking changes identified
- Migration requirements identified
- Communication plan decided: who needs to know, when, how

**PLAN**
- Changelog / release notes drafted
- Pre-release checklist assembled and confirmed
- Migration guides written (if applicable)
- Deployment order planned (if multi-step)
- Rollback plan confirmed viable

**SHIP**
- All pre-release checklist items confirmed
- Release artifact built and tagged
- Changelog published
- Communication sent
- Post-release monitoring confirmed active

---

## Bug fix

**DIAGNOSE**
- Reproduction case established and documented: exact steps to reproduce
- Root cause identified: not just the symptom, the underlying reason
- Scope of impact assessed: how many users affected, how severe
- Affected code identified: files, functions, lines
- Missing test identified: what test should have caught this (absence noted if none)

**IMPLEMENT**
- Fix targets root cause (not just symptom)
- Regression test written that fails on the bug and passes after the fix
- No unrelated changes in the same commit

**VERIFY**
- Regression test passing
- No new test failures introduced
- Bug confirmed fixed against original reproduction case

**SHIP**
- Deployed
- Fix confirmed working in production
- Changelog entry added if user-visible

---

## Security patch

**DIAGNOSE**
- Vulnerability identified and described: CVE or internal report, affected versions, affected systems
- Blast radius assessed: what data or systems are exposed, who is affected
- Severity classified: P0 (immediate), P1 (urgent), P2 (important)
- Disclosure timeline established: is there a coordinated disclosure deadline
- Temporary mitigation identified: can exposure be reduced while patch is built

**IMPLEMENT**
- Patch is minimal: fixes only the vulnerability, no refactoring
- Patch does not introduce new attack surface
- Regression test written proving the vulnerability is closed

**VERIFY** ⚠️ HARD GATE: security review is mandatory before SHIP, no soft bypass
- Security review complete: independent review of the patch
- Patch confirmed not introducing new vulnerabilities
- Regression test passing
- Affected dependency updated if root cause was a dependency

**SHIP**
- Deployed, in an expedited window if P0/P1
- Coordinated disclosure published if deadline applies
- Changelog entry published
- Affected users notified if data was exposed
- Follow-on task created for any deferred work (broader audit, related systems)

---

## Performance optimization

**DIAGNOSE**
- Baseline benchmark established: current performance measured under realistic conditions
- Bottleneck identified: specific function, query, or operation that is the constraint
- Target defined: what does "good enough" performance look like
- Root cause understood: why is this slow

**DESIGN**
- Optimization approach decided and documented
- Expected improvement estimated
- Risk assessed: could this change behavior or introduce instability
- Alternative approaches considered

**IMPLEMENT**
- Optimization implemented
- No behavior changes — only performance changes
- All existing tests still passing

**VERIFY**
- Benchmark re-run: improvement confirmed against baseline
- No correctness regressions (all tests passing)
- No new bottleneck introduced elsewhere (profiled after, not just the target area)

**SHIP**
- Deployed
- Production monitoring confirming improvement
- Baseline updated with new benchmark numbers

---

## Rollback / revert

**DIAGNOSE**
- Specific deploy or change identified as the cause
- Impact confirmed: this is the right thing to roll back
- Rollback method decided: git revert, deploy previous artifact, feature flag off
- Data impact assessed: will rolling back leave data in an inconsistent state
- Stakeholders informed

**SHIP**
- Rollback executed
- Production confirmed healthy after rollback
- Monitoring showing recovery
- Incident declared resolved
- POST-MORTEM work item spawned (required — not optional)

---

## Technology migration

**ASSESS**
- Current state documented: what is being replaced and why
- Migration scope defined: what systems, services, and code paths are affected
- Risk assessed: what could go wrong, what is the blast radius
- Migration strategy decided: big bang vs. incremental vs. parallel-run
- Rollback plan documented: how to return to the old system if migration fails

**DESIGN** ⚠️ HARD GATE at GA+: solutioning gate required, no soft bypass
- Target architecture designed
- Migration path designed: how to move from current to target
- Parallel-run strategy designed (if incremental): how old and new coexist during transition
- Data compatibility assessed: does old data work in the new system
- Solutioning gate passed

**PLAN**
- Migration broken into phases, each with its own rollback point
- Test strategy defined for each phase
- Cutover criteria defined: what signals confirm it is safe to cut over

**IMPLEMENT**
- New system built alongside old (parallel-run)
- Data compatibility verified
- Each phase implemented and verified before proceeding to the next

**VERIFY**
- New system verified under realistic load
- Parity verified: new system produces equivalent results to old system for the same inputs
- Rollback confirmed viable: tested return to old system

**CUTOVER** ⚠️ HARD GATE: human decision required, explicit confirmation logged, no soft bypass
- Cutover criteria met (as defined in PLAN)
- Monitoring active on new system
- Rollback procedure on standby
- Cutover executed
- New system confirmed healthy under production load
- Old system traffic at zero

**CLEANUP**
- Old system code removed
- Old system infrastructure decommissioned
- Old data migrated or archived per retention policy
- Documentation updated: no references to old system in active docs
- Break-glass notes updated

---

## Data migration

**ASSESS** ⚠️ HARD GATE at GA+: solutioning gate + change impact analysis required, no soft bypass
- Data to migrate identified: tables, collections, files, volume
- Schema mapping defined: old → new
- Data quality issues identified: nulls, invalid values, encoding problems
- Rollback plan: how to restore from backup if migration fails
- Downtime requirement assessed: live migration or maintenance window

**DESIGN**
- Migration script designed and peer reviewed
- Dry-run strategy defined: how to test without touching production
- Integrity checks defined: row counts, checksums, sample record verification
- Rollback script designed and tested

**PLAN**
- Migration steps sequenced
- Maintenance window planned (if required)
- Backup confirmed before any migration begins

**IMPLEMENT**
- Migration script implemented
- Dry run executed against a copy of production data
- Dry run results verified: correct output, acceptable duration

**VERIFY** ⚠️ HARD GATE: integrity checks mandatory before SHIP, no soft bypass
- Migration executed against production data
- Integrity checks pass: row counts match, checksums match, sample records verified manually
- Application behavior verified against migrated data
- Rollback plan confirmed still viable post-migration

**SHIP**
- Migration confirmed complete and healthy
- Old schema marked deprecated or removed
- Application fully running on new schema
- Documentation updated

---

## API deprecation

**ASSESS**
- API being deprecated identified precisely: endpoint, version, specific fields
- Consumer impact assessed: who calls this, how often, what do they depend on
- Migration path for consumers defined: what to use instead
- Sunset date established

**DEFINE**
- Deprecation notice written: what is being removed, when, what to use instead
- Migration guide written for consumers
- Changelog entry written

**IMPLEMENT**
- Compatibility layer implemented to keep deprecated API working during migration window
- Migration helpers built if assisting consumers
- Deprecation warnings added to API responses (headers or response body)

**VERIFY**
- Migration guide reviewed (by at least one consumer if possible)
- Compatibility layer tested
- Deprecation warnings confirmed firing in all relevant paths

**SHIP**
- Deprecation notice published
- Migration guide published and linked from API documentation
- Sunset date communicated to all known consumers

**CLEANUP** (fires at sunset date)
- Consumer traffic confirmed at zero or negligible
- Deprecated API removed from codebase
- Compatibility layer removed
- All documentation updated to remove references

---

## Dependency upgrade

**ASSESS**
- Changelog reviewed for breaking changes between current and target version
- Breaking changes identified and impact on the codebase assessed
- Test coverage of affected areas confirmed
- Transitive dependency changes noted

**IMPLEMENT**
- Dependency updated in package manifest
- Breaking changes addressed in application code
- Tests updated where API changed (to reflect new API, not to make them pass artificially)

**VERIFY**
- All tests passing
- No unexpected behavior changes
- No performance regression

**SHIP**
- Deployed and smoke tested
- Security advisory resolved (if upgrade was security-driven)
- Changelog entry added

---

## Hotfix

**DIAGNOSE**
- Production impact confirmed: what is broken, who is affected, severity
- Root cause identified to the degree possible under time pressure
- Fix approach decided: simplest possible fix that resolves the production issue
- Scope minimized: fix only what is breaking, nothing else
- Rollback assessed: is rollback faster than patching

**IMPLEMENT**
- Minimal fix only — no refactoring, no cleanup, no related improvements
- Smoke test written confirming the fix works against the production issue
- Existing tests still passing (no regressions introduced by the fix)

**SHIP** (expedited — normal code review gate is relaxed, but not eliminated)
- At minimum: async notification sent to a stakeholder OR self-review checklist completed and logged (solo devs: document your own review)
- Deployed to production
- Fix confirmed resolving the production issue
- Incident declared resolved
- POST-MORTEM work item created (required, not optional)

**POST-MORTEM** (follow-on work item, spawned from SHIP)
- Timeline of events documented
- Root cause analysis complete (5 whys or equivalent)
- Contributing factors identified
- Action items defined: what changes to prevent recurrence
- Action items added to backlog with priority
- Follow-on tech debt item created if the hotfix was a workaround rather than a real fix
