# Phase 2: Plan

## P1 — Generate user stories (Autonomous)

Update `current_phase: PLAN` in `john-wick.yaml`.

Invoke `sweetclaude:library-load product-user-stories` with the approved PRD as input. Generate human-readable stories with acceptance criteria. Write to `.sweetclaude/stories/[feature-name]-stories-v1.md`.

Each story must reference the relevant frozen `criterion_ids` from the
`success_criteria_contract_hash`. If a PRD/story requirement cannot map to a
frozen criterion, record it as a `criteria-amendment-request.yaml` candidate
and stop for user decision before treating it as required completion scope.

Record in `created_artifacts`: `{step: P1, type: stories, path: ..., version: 1}`.
Update `current_step: P2`.

## P2 — Story review caucus (Autonomous)

Before spawning the caucus, apply `../process-controls.md` using
`john-wick.yaml process_control.steps.P2`. If no budget remains or a stop
disposition is active, set `status: waiting_for_user`,
`interactive_gate_pending.step: P2`, and ask whether to approve a fresh caucus
budget, reopen/split stories, or pause. Do not spawn reviewers while stopped.

Run a 2-turn story review caucus with these four personas (pass inline — do not rely on a preset file):

**Personas for story-review:**
- **Product owner**: Acceptance criteria writer for 200+ stories. Flags unmeasurable criteria immediately; biased toward specificity. Rewrites vague criteria as concrete pass/fail tests.
- **Senior engineer**: Full-stack, 12 years. Translates story intent into implementation risk; flags stories that assume impossible interfaces or underspecified data shapes.
- **QA lead**: Test design and exploratory testing. Reads acceptance criteria as test cases; finds the ambiguous cases that will cause test failures.
- **Accessibility reviewer**: WCAG, inclusive design. Ensures stories include accessibility requirements as first-class criteria, not afterthoughts.

Invoke caucus with: stories path, personas above, 2 turns, question: "Are these stories specific enough to write deterministic acceptance tests? Are any acceptance criteria ambiguous, unmeasurable, or missing?"

The caucus may audit traceability to the frozen `criterion_ids`, but it may not
add completion criteria. Any missing or ambiguous criterion becomes a
`criteria-amendment-request.yaml`, backlog item, split-story proposal, or human
escalation.

Write caucus output to `.sweetclaude/caucus/story-review-[YYYYMMDD].md`.
Record in `caucus_outputs`: `{step: P2, path: ...}`.
Update `process_control.steps.P2` with one caucus round and four reviewer
agents used. If the caucus returns blocking findings that imply the story
contract is unstable, increment blocking failures and stop for user decision or
story split before any recaucus.
Update `current_step: P3`.

## P3 — Apply uncontested story adjustments (Autonomous)

Classify caucus findings as uncontested (three or more personas agree, or three agree and one is silent) or contested. Apply uncontested adjustments to the stories document — targeted edits, not a rewrite. Write the change summary to `.sweetclaude/caucus/story-review-[YYYYMMDD]-changes.md`. Record in `caucus_outputs`: `{step: P3, path: ...}`.

Update `current_step: P4`.

## P4 — Generate Gherkin (Autonomous)

For each story in the stories document, invoke `sweetclaude:library-load product-user-tdd-tests` to generate Gherkin `.feature` files. Write to `.sweetclaude/features/[story-slug].feature`. Commit:
```
test: Gherkin specs for {feature_name} stories
```

Every generated feature file must preserve the relevant `criterion_ids` so test
coverage can be traced back to the frozen `success_criteria_contract_hash`.

Record in `created_artifacts`: `{step: P4, type: gherkin, path: .sweetclaude/features/, version: 1}`.
Update `current_step: CK2`.

## CK2 — Plan phase check-in (Conditional)

If `phase_checkins: false`: skip. Update `current_step: DS1`.

If `phase_checkins: true`: invoke `sweetclaude:library-load john-wick-checkin` with:
- `phase=PLAN`
- `question=Is the Gherkin internally consistent and does it cover all PRD success criteria? Are there stories with no Gherkin coverage?`
- `discovery_artifacts={paths from discovery_artifacts in john-wick.yaml}`
- `phase_artifacts={stories path, all .feature file paths}`
- `post_lock=false`

Record output in `checkin_outputs`: `{step: CK2, path: ..., findings: ..., escalated: false}`.

If result is `significant`:
  Set `status: waiting_for_user`, `interactive_gate_pending.step: CK2`, `interactive_gate_pending.description: Gherkin coverage gap — direction needed`.
  Commit: `chore(john-wick): CK2 significant — awaiting gate`.
  Present:
  ```
  JOHN WICK — Plan Phase Check-in Gate
  ══════════════════════════════════════
  CK2 found a gap: [finding]

  Options:
  1. Regenerate Gherkin — re-run P4 with the gap in mind
  2. Proceed anyway — accept the gap and continue to Design
  3. Abort — stop here and review stories manually
  ```
  On user decision:
  - Regenerate: clear `interactive_gate_pending`, set `status: active`, write `current_step: P4`. Increment `created_artifacts` version for the gherkin entry when P4 re-runs.
  - Proceed: clear `interactive_gate_pending`, set `status: active`, write `current_step: DS1`.
  - Abort: set `status: paused`. Stop.

If result is `none` or `minor`: log finding and continue. Update `current_step: DS1`.
