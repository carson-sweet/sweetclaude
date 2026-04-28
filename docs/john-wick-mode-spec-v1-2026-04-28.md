# John Wick Mode — Design Spec v1 — 2026-04-28

**Author:** Carson Sweet
**Status:** Draft
**Branch:** `john-wick-mode`
**Context:** Brainstormed 2026-04-28. Superpowers is the only external dependency allowed. All other capabilities are native SweetClaude.
**Last revised:** 2026-04-28 — scope guardrails, compliance context, phase check-ins added

---

## 1. Purpose

John Wick mode is a fully autonomous, resumable, multi-session SDLC pipeline. Given completed discovery artifacts, it runs the full product-definition → design → TDD → implementation → review → PR cycle with minimal human involvement. Human pause points are explicit, pre-defined, and rare.

The name is intentional: the mode does not ask permission, does not stop to think out loud, and does not leave loose ends. It runs until it hits a gate, pauses cleanly, and picks back up the moment it gets approval.

---

## 2. What It Is Not

- It is not a single-session workflow. The pipeline is too long. It is designed as a multi-session state machine from the start.
- It is not a replacement for human judgment. The interactive gates exist because certain decisions (PRD approval, design change approval, significant test failure triage) require a human call.
- It is not a tool for half-configured projects. The prerequisite gate is hard. If the prerequisites aren't met, it does not start.
- It does not depend on any external framework other than Superpowers, which is already present.
- It is not designed for large, poorly-bounded services. If the PRD produces more than 6 epics or the contract analysis identifies more than 4 external service dependencies, John Wick surfaces a scope warning and recommends decomposing before continuing. Past a hard limit (8 epics or 6 external dependencies), it refuses to proceed without explicit user override. Autonomous pipelines compound scope problems — a service that is too large to reason about clearly is too large to build autonomously.
- It does not coordinate across concurrent runs. Each service gets its own isolated John Wick run. See §14.

---

## 3. Prerequisites Gate

Before any pipeline step runs, John Wick validates all of the following. Failure on any item halts with a specific, actionable error message.

| # | Prerequisite | Check | Error if missing |
|---|---|---|---|
| 1 | SweetClaude initialized | `.sweetclaude/state/phase.yaml` exists | "Run `/sweetclaude:init` first." |
| 2 | Personas artifact | `.sweetclaude/` or `docs/` contains a personas document | "Complete product discovery first: `/sweetclaude:product-discovery`" |
| 3 | Task analysis with success + failure criteria | Task analysis artifact exists with success criteria and known failure modes per task | "Task analysis incomplete. Rerun `/sweetclaude:product-discovery`." |
| 4 | Constraints analysis | Constraints artifact exists | "Constraints analysis missing." |
| 5 | Dangerously-skip-permissions acknowledged | User must explicitly confirm they understand the mode — shown as a warning with a typed confirmation, not a y/n | "John Wick mode requires explicit acknowledgment." |
| 6 | GitHub mode check | If user selects GitHub mode: `gh auth status` exits 0 | "GitHub CLI not authenticated. John Wick can help you fix this now." |
| 7 | No active john-wick.yaml in error state | If a previous run exists, it must be in `complete` or `paused` state | "Previous run is in error state. Inspect `.sweetclaude/state/john-wick.yaml` before restarting." |
| 8 | Compliance context | `.sweetclaude/state/compliance-context.yaml` exists | "Compliance context missing. John Wick will collect it at B4." |

On first run, prerequisites 1-5 are checked. Prerequisite 8 is checked and collected at B4 if absent. Prerequisites 6-7 are checked after the user answers the GitHub question in B1.

---

## 4. Pipeline

Every step has a type:

- **A** — Autonomous. John Wick runs without stopping.
- **I** — Interactive. John Wick pauses, presents output, waits for explicit user approval before continuing.
- **CK** — Check-in. Autonomous phase review. Surfaces drift findings; may return to a prior interactive gate if issues are significant. Check-ins **before IP5** can trigger cascade updates to design artifacts. Check-ins **after IP5** can only escalate to a human gate — they cannot modify locked test files.
- **C(github)** — Conditional on GitHub mode. Skipped in local tracking mode.

### Phase 0: Bootstrap

| Step | Type | Description |
|---|---|---|
| B1 | I | Ask: GitHub Issues or local tracking? If GitHub: verify `gh auth status`. If not working, help the user fix it before continuing. |
| B2 | I | Ask: what is the name for this feature branch? |
| B3 | A | Create the feature branch. Copy all discovery artifacts into `docs/` on the branch. Commit: `chore: initialize john-wick pipeline for [feature-name]`. |
| B4 | I | If `.sweetclaude/state/compliance-context.yaml` does not exist: collect compliance context now (see §7.9). Three questions: (1) what data categories does this service handle, (2) where are your users, (3) what is the user type. Write result to `.sweetclaude/state/compliance-context.yaml`. Skipped if file already exists from a prior discovery session. |

### Phase 1: Define

| Step | Type | Description |
|---|---|---|
| D1 | A | Generate PRD from discovery artifacts. No conversation — synthesize directly from personas, task analysis, constraints, and compliance context. Write to `docs/prd-[feature]-v1-[date].md`. |
| D2 | A | Product design caucus on the PRD. Preset: `product-design-review`. 3 turns. Write caucus output to `.sweetclaude/caucus/prd-review-[date].md`. |
| D3 | A | Classify caucus findings: uncontested vs. contested. Apply uncontested findings to PRD. Prepare a changes summary for the interactive gate. |
| D4 | I | Present PRD in sections. For each section: show the section, show any contested caucus findings, wait for approval or edits. Continue section by section until PRD is fully approved. Update PRD with any edits. Commit approved PRD. |
| CK1 | CK | Phase 1 check-in. Runs if `phase_checkins: true`. Reviews: does the approved PRD have sufficient coverage to generate stories? Are any epics or acceptance criteria underspecified? If significant gaps found: return to D4 gate. If minor: note in check-in log and continue. |

### Phase 2: Plan

| Step | Type | Description |
|---|---|---|
| P1 | A | Generate human-readable user stories from approved PRD. Write to `.sweetclaude/stories/[feature]-stories-v1.md`. |
| P2 | A | Story review caucus. Preset: `story-review`. 2 turns. Write output to `.sweetclaude/caucus/story-review-[date].md`. |
| P3 | A | Apply uncontested story adjustments. Update stories doc. |
| P4 | A | Generate Gherkin `.feature` files from approved stories using `sweetclaude:product-user-tdd-tests`. Write to `.sweetclaude/features/`. Commit. |
| CK2 | CK | Phase 2 check-in. Runs if `phase_checkins: true`. Reviews: is the Gherkin internally consistent? Does it cover the PRD's success criteria? Are there stories with no Gherkin coverage? If significant gaps found: revise Gherkin before continuing. |

### Phase 3: Design

| Step | Type | Description |
|---|---|---|
| DS1 | A | Generate initial architecture document using `sweetclaude:design-architecture`. Compliance context informs data residency, encryption at rest/in transit, and audit logging requirements. Write to `docs/architecture-[feature]-v1-[date].md`. |
| DS2 | A | Generate tech spec using `sweetclaude:design-tech-spec`. Write to `docs/tech-spec-[feature]-v1-[date].md`. |
| DS3 | A | Run service contract analysis (see §7.3). Compliance context informs contract obligations — e.g., EU users require GDPR-compliant data handling contracts with downstream consumers. Write to `docs/contract-analysis-[feature]-v1-[date].md`. |
| DS4 | A | Architecture and impact caucus. Preset: `architecture-impact`. 3 turns. Input documents: architecture doc, tech spec, contract analysis, compliance context. Write output to `.sweetclaude/caucus/architecture-review-[date].md`. |
| DS5 | A | Classify findings: uncontested vs. contested. Prepare change summary: what John Wick will apply, what needs human decision. |
| DS6 | I | Present change summary. User approves, rejects, or modifies each contested item. Record decisions. |
| DS7 | A | Apply all approved changes. Run cascade update across the artifact chain: architecture → tech spec → contract analysis → PRD (if impacted) → stories (if impacted) → Gherkin (if impacted). For each artifact, generate a proposed diff rather than a silent rewrite. Commit approved changes. |
| CK3 | CK | **Mandatory pre-lock check-in. Always runs regardless of `phase_checkins` setting.** Reviews: does the approved design still match the PRD and stories? Has the cascade update introduced any inconsistencies? Are there open design questions that will surface as implementation surprises? If issues found: return to DS6 gate. This is the last point at which design artifacts can be adjusted without unlocking tests. Do not proceed to IP1 until this check-in passes cleanly. |

### Phase 4: Implement Prep

| Step | Type | Description |
|---|---|---|
| IP1 | A | Spawn test writer subagent from Gherkin specs (TDD Level 3). Subagent receives: `.feature` files, existing codebase for patterns. No implementation knowledge. |
| IP2 | A | QA caucus on test coverage. Spawn `sweetclaude:qa-caucus-service`, `sweetclaude:qa-caucus-component`, `sweetclaude:qa-caucus-integration` in parallel. Input: test plan, Gherkin specs, user stories, PRD. Consolidate gaps. Apply uncontested gaps to test files. |
| IP3 | A | RED validation. Run full test suite. All tests must fail. If any pass unexpectedly, investigate and correct before continuing. |
| IP4 | A | Post-RED lightweight QA caucus. 1-turn pass with a focused "did anything slip through?" review. Apply any final adjustments to test files. Commit: `test: RED — [feature-name] failing tests`. |
| IP5 | A | **Test lock.** Set test-guardian scope to cover all subagents for this pipeline run. Record locked file paths in `john-wick.yaml`. After this point, no check-in or subagent may modify test files. Modifications to tests after IP5 require explicit user unlock + return to IP1. |
| IP6 | C(github) | Create GitHub issues from user stories. Each story becomes one issue: title from story, acceptance criteria in body, label `john-wick`. Record issue numbers in `john-wick.yaml`. |
| IP6-local | C(!github) | Create local issue list in `.sweetclaude/state/issue-list.md`. Same content, no GitHub. |

### Phase 5: Implement

| Step | Type | Description |
|---|---|---|
| IM1 | A | Issue iteration loop (see §5). If `phase_checkins: true`, a lightweight check-in runs after each issue branch merges. Run until all issues complete or an escalation fires. |
| IM2 | I(conditional) | Escalation gate: if severity classifier (§7.6) or a post-IP5 check-in detects significant problems, pause and present to user. Help user decide: fix and continue, skip issue, abort. Resume from decision. |

### Phase 6: Verify

| Step | Type | Description |
|---|---|---|
| V1 | A | Run full test suite on feature branch. Generate MD test report (see §7.5). |
| V2 | A | Run `sweetclaude:code-review`. Security review subagent included. Compliance review subagent runs against compliance-context.yaml (see §7.7). |
| V3 | A | Run `sweetclaude:documents-update-docs` for all user-facing documentation. |
| V4 | A | Update all design documents (architecture, tech spec, contract analysis) to reflect final implementation. |
| V5 | I | Cut final PR using `gh pr create`. PR description references: approved PRD, user stories, Gherkin specs, test report, review findings, compliance context. Present PR URL to user for final approval. |

---

## 5. Issue Iteration Loop

The core of Phase 5. Runs until the issue list is exhausted or an escalation fires.

```
for each issue in issue-list where status = pending:
  1. Create branch: {issue-number}-{slugified-title}
  2. Run sweetclaude:code-issue with issue context
  3. Run unit + integration tests
  4. Generate MD test report (appended to aggregate report)
  5. Evaluate failure severity (§7.6)
     - If significant: pause, escalate to user (IM2 gate), resume from decision
     - If not significant: attempt bug fixes, rerun tests
  6. If phase_checkins=true: run per-issue check-in
     - Review: is this implementation drifting from the design?
     - If drift detected: escalate to IM2 gate (cannot modify locked tests)
     - Note: check-ins after IP5 surface findings only — they do not autonomously
       adjust locked artifacts
  7. If tests green: merge branch back to feature branch, mark issue complete
  8. Advance to next issue
```

Each issue's branch is created from the feature branch and merged back to the feature branch — not to main. The feature branch is the integration point. Main is only touched by the final PR in V5.

---

## 6. State Machine

### File: `.sweetclaude/state/john-wick.yaml`

```yaml
schema_version: 1
status: active | paused | waiting_for_user | complete | error
feature_name: string
feature_branch: string
github_mode: boolean
phase_checkins: boolean           # default: false; see §7.10 for when to recommend true

current_phase: BOOTSTRAP | DEFINE | PLAN | DESIGN | IMPLEMENT_PREP | IMPLEMENT | VERIFY
current_step: string  # e.g. "D2", "IP3", "IM1:issue-7"

discovery_artifacts:
  personas: string | null         # file path
  task_analysis: string | null
  constraints: string | null
compliance_context: string | null # path to compliance-context.yaml

created_artifacts:
  - step: string
    type: prd | stories | gherkin | architecture | tech_spec | contract_analysis | tests | report | pr
    path: string
    version: integer

issue_list:
  - number: integer               # GitHub issue number or local sequence number
    title: string
    branch: string
    status: pending | in_progress | complete | escalated | skipped

caucus_outputs:
  - step: string
    path: string

checkin_outputs:
  - step: string
    path: string
    findings: none | minor | significant
    escalated: boolean

interactive_gate_pending:
  step: string | null
  description: string | null

locked_test_files:
  - string                        # file paths locked after IP5

context_checkpoint:
  step: string
  timestamp: string
  notes: string

sessions:
  - started: string
    ended: string | null
    steps_completed: [string]
```

### Resume protocol

When John Wick starts:

1. If no `john-wick.yaml` exists: run prerequisites gate, then start at B1.
2. If `john-wick.yaml` exists with `status: waiting_for_user`: present the pending gate, collect input, continue from `current_step`.
3. If `status: paused` or `active`: present a one-line recap ("Last completed: DS4. Resuming from DS5.") and continue from `current_step`.
4. If `status: complete`: tell the user the pipeline is done and point to the PR.
5. If `status: error`: show the error, do not auto-resume. Require user to inspect and clear.

On every step completion: update `john-wick.yaml` before starting the next step. State is always one step ahead of where work has been done.

### Context window management

Before each autonomous step, estimate remaining context budget. If within ~20% of limit:

1. Commit current state to git: `chore(john-wick): checkpoint at [step]`
2. Update `context_checkpoint` in `john-wick.yaml`
3. Emit to user: "Context limit approaching. State saved at [step]. Run `/sweetclaude:john-wick` to resume."
4. Stop cleanly.

Do not attempt to squeeze in another step. A clean stop is better than a corrupted one.

---

## 7. New Capabilities Required

### 7.1 Autonomous PRD generation mode

`product-prd` is currently a conversational skill. It needs an execution path that:
- Accepts paths to discovery artifacts (including compliance context) as input
- Generates a complete PRD draft without prompting the user
- Uses the PRD's section structure but populates from artifact content
- Flags sections where discovery artifacts didn't provide enough signal (presents these at the D4 interactive gate instead of halting)

Implementation: add an `--autonomous` flag or an internal parameter. When set, skip all `AskUserQuestion` calls and synthesize from input documents.

### 7.2 Cascade document update

When design changes are approved in DS6, downstream artifacts need updating. This must not be a blind rewrite.

Protocol:
1. For each downstream artifact in the chain (architecture → tech spec → PRD → stories → Gherkin), determine whether the approved change touches that artifact's content.
2. If yes: generate a proposed diff — specific section changes, not a full rewrite.
3. Collect all proposed diffs and commit as a single update: `docs: cascade approved design changes to [list of artifacts]`
4. If a proposed diff would invalidate a previously approved artifact (e.g., a changed API shape invalidates a story's acceptance criteria), flag it explicitly rather than silently rewriting.

The cascade stops at test files. Tests are immutable once locked at IP5.

### 7.3 Service contract analysis

A new analysis capability (not a standalone skill — embedded in the John Wick orchestrator):

Given the architecture document, tech spec, compliance context, and any available specs or READMEs for other services in the project:

1. **Outbound contracts:** What does this service promise to its consumers? (API endpoints, event schemas, response shapes, SLAs implied by design)
2. **Inbound contracts:** What does this service require from its providers? (APIs it calls, data it expects, timing assumptions)
3. **Implicit contracts:** What does this service assume about the environment that isn't explicitly documented? (ordering guarantees, idempotency assumptions, data consistency expectations)
4. **Compliance obligations:** What compliance requirements flow through to consumers? (e.g., GDPR data handling requirements this service must impose on downstream consumers; see compliance context)
5. **Risk surface:** Where are the contracts fragile — under-specified, assumed but not verified, or dependent on a service whose spec isn't available?

Output: `docs/contract-analysis-[feature]-v1-[date].md` with the five sections above plus a risk table.

### 7.4 GitHub Issues creation

Given the user stories document, create one GitHub issue per story:

```
gh issue create \
  --title "[story title]" \
  --body "[acceptance criteria in markdown]" \
  --label "john-wick" \
  --label "[feature-name]"
```

Record each issue number in `john-wick.yaml`. Handle failures gracefully (rate limits, auth errors) with retry logic.

For local mode: write `.sweetclaude/state/issue-list.md` with the same content.

### 7.5 MD test report generation

After each test run, generate a markdown report:

```markdown
# Test Report — [feature] — [timestamp]

## Summary
- Total: N | Pass: N | Fail: N | Skip: N
- Coverage: N% (if available)
- Run time: N seconds

## Failures
### [test name]
- File: [path:line]
- Expected: [value]
- Actual: [value]
- Stack: [first relevant frame]

## Passed
[collapsed list]
```

Write to `.sweetclaude/reports/test-report-[issue-or-phase]-[timestamp].md`. Append to an aggregate report for the full pipeline.

### 7.6 Test failure severity classifier

After each test run, classify the results:

**Significant (escalate to user):**
- More than 30% of tests failing after bug fix attempt
- Any test in the "happy path" or "core flow" category failing (determined by test name patterns and Gherkin story mapping)
- Compile/import errors that prevent the suite from running at all
- Security review findings with severity High or Critical

**Not significant (continue):**
- Isolated edge case failures with clear cause
- Failures in optional or enhancement features
- Test infrastructure issues with known workarounds

The classifier is heuristic. When uncertain, it escalates — false positives (unnecessary interruptions) are better than false negatives (silent bad states).

### 7.7 Compliance review subagent

A new review subagent parallel to the existing security review subagent.

The compliance framework is driven by `.sweetclaude/state/compliance-context.yaml`, collected at step B4. The subagent reads this file first, then reviews code against the identified requirements:

- EU users specified → GDPR review is mandatory (PII handling, right to erasure, data minimization, consent)
- US healthcare users → HIPAA checklist (PHI handling, access controls, audit logging, BAAs)
- Financial data → PCI-DSS patterns (cardholder data, encryption, access logging)
- Minors in userbase → COPPA requirements (parental consent flows, data collection limits)
- No specific framework identifiable → GDPR as floor

Regardless of framework, always examines:
- PII handling (collection, storage, transmission, retention)
- Authentication and authorization patterns
- Audit logging and traceability
- Data residency implications
- Third-party data sharing

Output: section appended to the code review output doc.

### 7.8 Caucus persona presets

Three new presets for the `caucus` skill. These are added to the caucus `persona-presets.md` file.

**`product-design-review`**

| Persona | Expertise | Key bias |
|---|---|---|
| PM — "the pragmatist" | 10 years B2B SaaS, former engineer | Scope creep detector; believes features die from complexity, not ambition |
| UX researcher | Mixed methods, 8 years | Advocates relentlessly for the user who isn't in the room; skeptical of assumption-based personas |
| Domain expert | Deep subject matter knowledge in the service's domain | Flags technical accuracy issues; biased toward correctness over shipping speed |
| Devil's advocate — "the skeptic" | Strategy/venture background | Questions whether the problem is real; argues for doing less |

**`story-review`**

| Persona | Expertise | Key bias |
|---|---|---|
| Product owner | Acceptance criteria writer for 200+ stories | Flags unmeasurable criteria immediately; biased toward specificity |
| Senior engineer | Full-stack, 12 years | Translates story intent into implementation risk; flags stories that assume impossible interfaces |
| QA lead | Test design, exploratory testing | Reads acceptance criteria as test cases; finds the ambiguous cases every time |
| Accessibility reviewer | WCAG, inclusive design | Ensures stories include accessibility requirements, not as an afterthought |

**`architecture-impact`**

| Persona | Expertise | Key bias |
|---|---|---|
| Senior architect | Distributed systems, 15 years | Strong opinions about interface contracts; biased toward over-specifying rather than under-specifying boundaries |
| Security engineer | AppSec, threat modeling | Reads every design for attack surface; sees trust boundaries others miss |
| SRE | Reliability, observability | Asks "what does this look like at 3am when it's broken?" for every component |
| Upstream service owner | Persona representing whoever owns the service this one depends on most | Questions every assumption about upstream behavior; knows all the undocumented behaviors |

### 7.9 Compliance context collection

A structured three-question interview collected at B4 (or earlier via `product-discovery` if that skill is updated to include this section).

**Questions:**

1. **Data categories** — Which of these does this service handle? (select all that apply)
   - Personal identifiable information (names, emails, addresses, IDs)
   - Financial data (payment methods, transaction records, account balances)
   - Health or medical data
   - Behavioral or tracking data (usage logs, location, clickstreams)
   - None of the above

2. **User geography** — Where are your users? (select all that apply)
   - United States
   - European Union / UK
   - Global / unknown
   - Other (specify)

3. **User type** — Which applies? (select all that apply)
   - Consumers (B2C)
   - Enterprise users (B2B)
   - Minors or potentially mixed-age audience
   - Healthcare providers or patients
   - Financial services users

**Output schema** (`.sweetclaude/state/compliance-context.yaml`):

```yaml
schema_version: 1
collected_at: timestamp
data_categories:
  - pii | financial | health | behavioral | none
user_geography:
  - us | eu_uk | global | other
user_type:
  - b2c | b2b | minors | healthcare | financial
derived_frameworks:
  - gdpr | hipaa | pci_dss | coppa | gdpr_floor
notes: string | null
```

The `derived_frameworks` field is computed from the answers: EU geography + PII → GDPR; US + health data → HIPAA; financial data → PCI-DSS; minors in audience → COPPA; all others → GDPR as floor.

This file is also the right place to add compliance notes discovered during design (DS1, DS3) that refine the initial assessment.

### 7.10 Phase check-in subagent

A lightweight review subagent that runs at phase transitions to detect drift before it compounds.

**When to enable:** John Wick recommends enabling `phase_checkins: true` at the prerequisites gate if the scope check at B3/D1 suggests the PRD will have more than 4 epics, or if the contract analysis is likely to identify more than 2 external service dependencies. For simpler services, the mandatory CK3 (pre-lock check) is sufficient.

**What each check-in does:**

The check-in subagent receives:
- The original discovery artifacts (personas, tasks, constraints)
- All artifacts produced in the completed phase
- A specific review question scoped to the transition

It produces a findings report: `none` (all clear), `minor` (notes but no action needed), or `significant` (return to prior gate).

**The IP5 boundary is absolute:**

Before IP5: check-in findings can trigger cascade updates via DS6 or P4 revision.
After IP5: check-in findings escalate to the IM2 human gate only. The check-in subagent is explicitly instructed that it cannot recommend test file changes — only implementation or design document changes that do not affect locked tests.

**Preventing check-in inflation:**

Check-ins are 1-turn reviews, not full caucuses. They have a narrow scope question and a binary output: proceed or escalate. They do not produce recommendations lists, alternative approaches, or general commentary. If a check-in produces anything other than "clear" or "here is the specific issue preventing progress," it is misconfigured.

---

## 8. Hooks

### Test file lock (IP5)

The existing `test-guardian` hook applies within a session. John Wick mode needs it to apply across all subagents spawned during the pipeline.

Required: verify that the test-guardian hook's scope covers subagent file edits. If it does not, extend it so that when `john-wick.yaml` contains `locked_test_files`, any file edit touching those paths is blocked regardless of which agent (main or subagent) initiates it.

Locked file paths are written to `john-wick.yaml` at IP5 and checked on every file write thereafter.

### Issue branch naming (Phase 5)

No new hook needed. The issue iteration loop enforces branch naming by construction: branch names are generated as `{issue-number}-{slug}` before `git checkout -b` is called.

---

## 9. Orchestrator Architecture

John Wick mode is a single skill (`sweetclaude:john-wick`) that acts as a dispatcher. It does not contain implementation logic for individual steps — it calls the appropriate existing skill or embedded capability, then updates state.

```
john-wick skill
  ├── reads john-wick.yaml (or initializes it)
  ├── determines current_step
  ├── dispatches to step handler:
  │     ├── existing skills (product-prd, design-architecture, etc.) for skill-backed steps
  │     ├── embedded logic for new capabilities (contract analysis, cascade update, etc.)
  │     ├── check-in subagent for CK steps
  │     └── interactive gate handler for I-type steps
  ├── on step completion: updates john-wick.yaml
  ├── checks context budget
  └── advances to next step or pauses cleanly
```

Skill invocations use the `Skill` tool exactly as a user would. This keeps skill behavior consistent — John Wick does not bypass any skill's preflight guards or internal logic.

For steps that require subagents (test writer, implementer, QA caucus), John Wick spawns them via the `Agent` tool exactly as the called skill would. The subagent isolation rules from `code-tdd` Level 3 apply unchanged.

---

## 10. Interactive Gate Pattern

When John Wick reaches an I-type step:

1. Complete any autonomous work that precedes the gate (e.g., generate the draft, run the caucus, prepare the change summary).
2. Update `john-wick.yaml`: set `status: waiting_for_user`, `interactive_gate_pending.step`, `interactive_gate_pending.description`.
3. Commit any new artifacts.
4. Present the gate to the user in a structured format:

```
JOHN WICK — [Phase Name] Gate
══════════════════════════════
[What was done since the last gate]

[The content requiring review — presented in sections]

[Specific question(s) requiring user decision]

When you're ready: approve, edit, or type your changes. John Wick will
continue once you confirm.
```

5. Wait. Do not continue until the user responds.
6. On user response: record the decision, update artifacts as approved, update `john-wick.yaml` (`status: active`), continue.

For the PRD section review (D4): present one section at a time. Do not present the next section until the current one is confirmed. This prevents the user from being overwhelmed and ensures each section gets real attention.

---

## 11. Dependency Constraints

- **Superpowers**: used for `caucus` skill and `superpowers:*` skills already in the pipeline. No new Superpowers dependencies.
- **No new external frameworks**: all new capabilities are native SweetClaude — embedded in the orchestrator skill or as new SweetClaude subagents.
- **`gh` CLI**: required for GitHub mode. Not a new dependency — it's already used by `code-feature` and `code-issue`. John Wick adds a verification step and a setup-assist flow at B1.
- **Git**: already required.
- **Test runner**: detected from project `CLAUDE.md` or `project.yaml`, same as existing TDD skills.

---

## 12. Out of Scope

These items were considered and explicitly excluded:

| Item | Reason |
|---|---|
| Parallel issue implementation (multiple issues at once) | Increases complexity and merge conflict risk; sequential is safer for v1 |
| Automated compliance remediation | Compliance review surfaces findings; fixing them is implementation work that must go through the normal issue loop, not an autonomous patch step |
| Mutation testing in the pipeline | Valuable but slows the loop; can be added post-v1 |
| John Wick coordinating across concurrent service runs | Each service run is isolated; see §14 for the coordination model |
| Automatic rollback on test failure | Too aggressive; the escalation gate handles failures with human judgment |
| Cross-service Gherkin coordination | Service contracts are analyzed (DS3), but Gherkin is written per-service |
| Compliance framework auto-detection from code | Compliance context is explicitly collected (B4), not inferred from code patterns — explicit is more reliable and auditable |

---

## 13. Success Criteria

John Wick mode is working correctly when:

- A user can invoke it with completed discovery artifacts and receive an approved PR without manually navigating any pipeline steps except the designated interactive gates (B1, B2, B4, D4, DS6, V5, and conditional IM2)
- Context compression during a run results in a clean resume without lost state or duplicate work
- The final PR's description is fully traceable: PRD → stories → Gherkin → tests → implementation → review
- Test files are provably immutable from the moment of IP5 through V5
- A run on a project with no GitHub mode produces identical artifacts to a run with GitHub mode, with the only difference being where issues are tracked
- Compliance context collected at B4 flows through architecture (DS1), contract analysis (DS3), and the final compliance review (V2) without the user needing to re-specify requirements at any step
- When `phase_checkins: true`, the CK3 mandatory pre-lock check catches at least one design/PRD inconsistency in a run where inconsistencies were introduced — the check-in does not silently pass on a dirty state
- The scope check at D1/D4 prevents a John Wick run from starting on a service with more than 8 epics without explicit user override

---

## 14. Multi-Service Use and Concurrency

John Wick is designed for one service at a time. Each service gets its own isolated run with its own `john-wick.yaml`, its own feature branch, and its own pipeline state. John Wick A knows nothing about John Wick B.

**This is intentional.** Autonomous pipelines that try to coordinate across concurrent runs introduce coupling that compounds failures — if Service A's pipeline pauses waiting for Service B's design to stabilize, you have two blocked pipelines instead of one. The coordination problem is kept with the human, where it belongs.

**The real risk is at DS3 (service contract analysis).** When John Wick analyzes contracts for Service A, it looks at what Service B promises as a provider. If Service B is also in flight under its own John Wick run and its API design is still changing, Service A's contract analysis is working from a moving target. John Wick will flag this explicitly when it detects that a dependency's spec is absent or marked as in-progress. It will not silently assume a stable contract.

**Coordination checkpoints.** If you are running John Wick on multiple services concurrently, the natural coordination checkpoints are the interactive gates — specifically D4 (PRD approval) and DS6 (design change approval). These are the moments where you, as the human coordinator, can compare states across all running pipelines and catch cross-service conflicts before they propagate into tests or implementation.

**Recommended sequencing.** Where services have hard dependencies (Service A calls Service B's API), run the upstream service's John Wick pipeline through at least DS7 (design approved and committed) before starting the downstream service's pipeline. This gives DS3 a stable contract to analyze. Where services are peers with only loose coupling, concurrent runs are lower risk — the contract analysis will be approximate, but the DS6 gate gives you a chance to correct it.

**Documentation.** The feature branch for each service should include a `docs/cross-service-dependencies.md` noting which other services are depended on and the status of their John Wick runs at the time the contract analysis was written. This creates an audit trail for cross-service coordination decisions.

---

*Next: implementation plan*
