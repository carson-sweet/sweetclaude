# Phase 3: Design

**Steps:**
- [DS1 — Architecture document](#ds1--architecture-document-autonomous)
- [DS2 — Tech spec](#ds2--tech-spec-autonomous)
- [DS3 — Service contract analysis](#ds3--service-contract-analysis-autonomous)
- [DS4 — Architecture and impact caucus](#ds4--architecture-and-impact-caucus-autonomous)
- [DS5 — Classify design findings](#ds5--classify-design-findings-autonomous)
- [DS6 — Design change approval](#ds6--design-change-approval-interactive)
- [DS7 — Cascade document update](#ds7--cascade-document-update-autonomous)
- [CK3 — Pre-lock check-in](#ck3--pre-lock-check-in-mandatory--always-runs-regardless-of-phase_checkins)

## DS1 — Architecture document (Autonomous)

Update `current_phase: DESIGN` in `john-wick.yaml`.

Invoke `sweetclaude:library-load design-architecture` with: PRD path, stories path, compliance context path. The compliance context informs data residency requirements, encryption at rest/in transit, and audit logging requirements — ensure the architecture document explicitly addresses each `derived_frameworks` entry from `compliance-context.yaml`.

The architecture document must preserve the frozen
`success_criteria_contract_hash` and map design decisions to relevant
`criterion_ids`. If a design requirement cannot trace to a frozen criterion,
route it to a `criteria-amendment-request.yaml`, backlog item, split-story
proposal, or human escalation.

Write architecture document to `docs/architecture-[feature-name]-v1-[YYYYMMDD].md`.
Record in `created_artifacts`: `{step: DS1, type: architecture, path: ..., version: 1}`.
Update `current_step: DS2`.

## DS2 — Tech spec (Autonomous)

Invoke `sweetclaude:library-load design-tech-spec` with: architecture document, PRD, stories. Write tech spec to `docs/tech-spec-[feature-name]-v1-[YYYYMMDD].md`.
Record in `created_artifacts`: `{step: DS2, type: tech_spec, path: ..., version: 1}`.
Update `current_step: DS3`.

## DS3 — Service contract analysis (Autonomous)

**Resume guard:** If `current_step` is `DS3-scope-gate` on resume, skip contract analysis entirely. Present the scope override prompt directly: 'The contract analysis found more than 6 external service dependencies. Type "override scope limit" to continue, or provide guidance on how to reduce external dependencies.' Clear `interactive_gate_pending` (set both fields to null). Set `status: active`. Write `current_step: DS4`, then continue.

Run the embedded service contract analysis. Read: architecture document, tech spec, compliance context. Scan `docs/` and any available READMEs for specs of services this service depends on.

Produce `docs/contract-analysis-[feature-name]-v1-[YYYYMMDD].md` with five sections:

**1. Outbound contracts** — What this service promises to consumers: API endpoints, event schemas, response shapes, implied SLAs.

**2. Inbound contracts** — What this service requires from providers: APIs it calls, data it expects, timing assumptions.

**3. Implicit contracts** — What this service assumes about the environment that isn't explicitly documented: ordering guarantees, idempotency assumptions, data consistency expectations.

**4. Compliance obligations** — What compliance requirements flow through to consumers. Derived from `compliance-context.yaml derived_frameworks`:
- `gdpr`: downstream consumers must handle PII under GDPR data processing agreements
- `hipaa`: PHI must not be stored by downstream consumers without BAAs
- `pci_dss`: cardholder data must not be cached downstream
- `coppa`/`gdpr_floor`: data minimization requirements apply to consumers

**5. Risk surface** — Where contracts are fragile: under-specified boundaries, assumed but unverified behavior, dependencies whose specs are absent or marked in-progress.

End with a risk table:
```markdown
| Contract | Type | Spec Available? | Risk |
|---|---|---|---|
| {name} | outbound/inbound | yes/no | low/medium/high |
```

If any dependency's spec is absent or marked in-progress, flag explicitly:
> "⚠ Dependency spec unavailable: [{service}]. Contract analysis for this dependency is based on assumptions. Verify before IP5."

Record in `created_artifacts`: `{step: DS3, type: contract_analysis, path: ..., version: 1}`.

**Scope check:** Count external service dependencies identified. If more than 4: surface a warning (same pattern as D1 epic warning). If more than 6: halt with override mechanism. Write `current_step: DS3-scope-gate` and `status: paused` before halting; resume guard at start of DS3 skips analysis and presents the override prompt directly.

Update `current_step: DS4`.

## DS4 — Architecture and impact caucus (Autonomous)

Before spawning the caucus, apply `../process-controls.md` using
`john-wick.yaml process_control.steps.DS4`. If no budget remains or a stop
disposition is active, set `status: waiting_for_user`,
`interactive_gate_pending.step: DS4`, and ask whether to approve a fresh
caucus budget, reopen the design contract, or pause. Do not spawn reviewers
while stopped.

Run a 3-turn architecture review caucus with these four personas (pass inline):

**Personas for architecture-impact:**
- **Senior architect**: Distributed systems, 15 years. Strong opinions on interface contracts; biased toward over-specifying rather than under-specifying boundaries. Challenges every "we'll figure it out" in the design.
- **Security engineer**: AppSec, threat modeling. Reads every design for attack surface; sees trust boundaries others miss. Flags auth gaps, injection surfaces, and data leakage paths.
- **SRE**: Reliability, observability. Asks "what does this look like at 3am when it's broken?" for every component. Flags missing metrics, missing circuit breakers, missing runbooks.
- **Upstream service owner**: Persona representing whoever owns the service this one depends on most. Questions every assumption about upstream behavior; knows all the undocumented behaviors and breaking changes.

Invoke caucus with: architecture doc, tech spec, contract analysis, compliance context, 3 turns, question: "Does this architecture correctly handle the service's compliance obligations, service contracts, and failure modes? What will break first in production?"

The caucus may judge whether the design satisfies the frozen
`criterion_ids`, but it may not add completion criteria. Findings outside the
frozen success criteria are routed as amendment requests, backlog, split-story
work, or human escalation.

Write output to `.sweetclaude/caucus/architecture-review-[YYYYMMDD].md`.
Record in `caucus_outputs`: `{step: DS4, path: ...}`.
Update `process_control.steps.DS4` with one caucus round and four reviewer
agents used. If the caucus returns blocking findings that require another
caucus or expand the architecture contract, increment blocking failures and
stop for user decision before any recaucus.
Update `current_step: DS5`.

## DS5 — Classify design findings (Autonomous)

Classify caucus findings as uncontested or contested (same uncontested/contested logic as D3/P3). Prepare a change summary:
```
Will apply automatically (uncontested):
- [finding] → [proposed change]

Requires your decision (contested):
- [finding] — [what the change would be and what it affects downstream]
```

Write change summary to `.sweetclaude/caucus/architecture-review-[YYYYMMDD]-changes.md`.
Record in `caucus_outputs`: `{step: DS5, path: ...}`.
Update `current_step: DS6`.

## DS6 — Design change approval (Interactive)

Update `john-wick.yaml`: set `status: waiting_for_user`, `interactive_gate_pending.step: DS6`, `interactive_gate_pending.description: Design change approval — review contested findings`.

Commit any new artifacts produced since DS4: `chore(john-wick): artifacts at DS6 — awaiting gate`.

Present the change summary from DS5. For each contested item:
1. Show the finding
2. Show the proposed change
3. Show which downstream artifacts would be affected (PRD, stories, Gherkin)
4. Wait for: approve, reject, or modify

Record all decisions. After all items are resolved, clear `interactive_gate_pending`, set `status: active`. Update `current_step: DS7`.

## DS7 — Cascade document update (Autonomous)

Apply all approved changes from DS6. For each downstream artifact in the chain — architecture → tech spec → contract analysis → PRD → stories → Gherkin — determine whether any approved change touches that artifact's content.

**Cascade protocol:**
1. For each artifact in the chain, determine if any approved change affects its content.
2. If yes: generate a targeted diff (specific section changes, not a full rewrite). Show what will change.
3. If a proposed diff would invalidate a previously approved artifact (e.g., an API shape change that invalidates a story's acceptance criteria): set `status: waiting_for_user`, `interactive_gate_pending.step: DS7`, `interactive_gate_pending.description: Cascade impact requires review`. Present:
   > "⚠ Cascade impact: this change affects [{artifact}]. The affected section was previously approved. Approve this cascade change to proceed, or reject it to drop this design change."
   Wait for user confirmation. On approval: clear `interactive_gate_pending`, set `status: active`, continue. On rejection: drop this specific design change and move to the next one.
4. Collect all approved diffs and apply in sequence. Increment `version` for each updated artifact in `created_artifacts`. Commit:
   ```
   docs: cascade approved design changes to {comma-separated list of affected artifacts}
   ```

**Hard stop:** The cascade never touches test files. If an approved change would require test changes, flag it:
> "⚠ Test impact: this change would require modifying tests. Test files are locked after IP5. Note this for post-IP5 review if needed."

Update `current_step: CK3`.

## CK3 — Pre-lock check-in (MANDATORY — always runs regardless of `phase_checkins`)

This check-in always runs. It is the last point at which design artifacts can be adjusted without unlocking tests. Do not advance to IP1 until CK3 passes with `none` or `minor`.

Invoke `sweetclaude:library-load john-wick-checkin` with:
- `phase=DESIGN`
- `question=Does the approved design (architecture, tech spec, contract analysis) still match the PRD, stories, frozen success_criteria_contract_hash, and criterion_ids? Has the cascade update introduced any inconsistencies? Are there open design questions that will surface as implementation surprises?`
- `discovery_artifacts={paths from discovery_artifacts in john-wick.yaml}`
- `phase_artifacts={architecture path, tech spec path, contract analysis path, PRD path, stories path, success criteria contract path}`
- `post_lock=false`

Record output in `checkin_outputs`: `{step: CK3, path: ..., findings: ..., escalated: false}`.

If result is `significant`: write `current_step: DS6` to `john-wick.yaml`. Present to user:
> "CK3 (mandatory pre-lock check) found a gap: [finding]. Returning to design review before tests are written."
Set `escalated: true` in the CK3 checkin_outputs entry. Do not advance to IP1.

If result is `none` or `minor`: log and continue. Update `current_step: IP1`.
