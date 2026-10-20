# Phase 1: Define

## D1 — Generate PRD (Autonomous)

**Resume guard:** If `current_step` is `D1-scope-gate` on resume, skip PRD generation entirely. The PRD already exists. Present the scope override prompt directly: 'The PRD has more than 8 epics. Type "override scope limit" to continue, or provide guidance on how to decompose the PRD.' Clear `interactive_gate_pending` (set both fields to null). Set `status: active`. Write `current_step: D2`, then continue.

Invoke `sweetclaude:library-load product-prd` with `--autonomous` flag. The skill reads discovery artifacts and compliance context, generates a complete PRD draft without user interaction, and flags thin sections inline.

The PRD is written to `docs/[feature-name]-prd-draft-v1.0-[YYYYMMDD].md`.

Record in `created_artifacts`: `{step: D1, type: prd, path: ..., version: 1}`.

If the PRD contains any ⚠ flagged sections, write their section names to `john-wick.yaml` as a top-level `d1_flags` list (e.g., `d1_flags: [Problem Statement, Goals and Success Metrics]`). D3 and D4 will read this list to present flags to the user.

**Scope check:** After the PRD is generated, count the epics. If more than 6 epics: surface a warning:
> "⚠ Scope warning: This PRD has {N} epics. John Wick recommends decomposing into smaller services before continuing. Large scope compounds errors in an autonomous pipeline."

After surfacing the warning, continue. Write `current_step: D2`.

If more than 8 epics: halt and require explicit user override:
> "⚠ Hard limit: {N} epics exceeds the maximum for autonomous execution (8). Decompose the PRD into smaller services, or type 'override scope limit' to proceed at your own risk."

Write `current_step: D1-scope-gate` to `john-wick.yaml`. Update `john-wick.yaml`: set `status: paused`. Leave `interactive_gate_pending` null (do not set it). Do not advance `current_step` until the override is accepted.

If the scope check passes (≤ 8 epics): Update `current_step: D2`. (Override-accepted transition is handled exclusively by the D1 resume guard above — it writes `current_step: D2` there and does not return here.)

## D2 — PRD caucus (Autonomous)

Before spawning the caucus, apply `../process-controls.md` using
`john-wick.yaml process_control.steps.D2`. If no budget remains or a stop
disposition is active, set `status: waiting_for_user`,
`interactive_gate_pending.step: D2`, and ask whether to approve a fresh caucus
budget, reopen the PRD contract, or pause. Do not spawn reviewers while
stopped.

Run a 3-turn product design review caucus on the PRD. Pass these four personas inline to the caucus skill — do not rely on a preset file:

**Personas for product-design-review:**
- **PM — "the pragmatist"**: 10 years B2B SaaS, former engineer. Scope creep detector; believes features die from complexity, not ambition. Challenges every "nice to have."
- **UX researcher**: Mixed methods, 8 years. Advocates for the user who isn't in the room; skeptical of assumption-based personas. Probes for real user evidence.
- **Domain expert**: Deep subject matter knowledge in the service's domain. Flags technical accuracy issues; biased toward correctness over shipping speed.
- **Devil's advocate — "the skeptic"**: Strategy/venture background. Questions whether the problem is real; argues for doing less. Challenges scope, not execution.

Invoke the caucus skill with: PRD path, personas above, 3 turns, question: "Does this PRD define a product that solves the stated problem for the stated user, with scope that is achievable and justified?"

Write caucus output to `.sweetclaude/caucus/prd-review-[YYYYMMDD].md`.
Record in `caucus_outputs`: `{step: D2, path: ...}`.
Update `process_control.steps.D2` with one caucus round and four reviewer
agents used. If the caucus returns blocking findings that require another
caucus or substantial contract expansion, increment blocking failures and stop
for user decision before any recaucus.
Update `current_step: D3`.

## D3 — Apply uncontested findings (Autonomous)

Read the D2 caucus output. Classify each finding:

- **Uncontested**: all four personas agree, or three agree and one is silent
- **Contested**: personas disagree, or the finding requires a product decision the orchestrator cannot make

Apply uncontested findings directly to the PRD — targeted edits, not a rewrite. Prepare a structured change summary:
```
Applied (uncontested):
- [finding] → [change made]

Pending user decision (contested):
- [finding] — [what the personas disagreed on]
- [flagged section from D1] — [what information was missing]
```

Write this change summary to `.sweetclaude/caucus/prd-review-[YYYYMMDD]-changes.md`. Record in `caucus_outputs`: `{step: D3, path: .sweetclaude/caucus/prd-review-[YYYYMMDD]-changes.md}`. This persists the summary across context loss so D4 does not need to regenerate it.

Update `current_step: D4`.

## D4 — PRD approval (Interactive)

Present the PRD section by section. For each section:
1. Show the section content
2. Show any contested caucus findings for that section
3. Show any D1 flags (⚠ markers) for that section
4. Wait for: approval ("ok", "looks good", or similar), or edits

Do not advance to the next section until the current section is confirmed. After all sections are approved, apply any user edits and commit:
```
docs: approved PRD for {feature_name} at D4
```

Update `created_artifacts` version to final. Clear `d1_flags` in
`john-wick.yaml` (set to empty list).

Create
`.sweetclaude/contracts/success-criteria-contract.yaml` from the approved PRD.
The contract must contain only binary, measurable success criteria with stable
`criterion_ids`, explicit pass/fail conditions, evidence artifact paths,
evidence owners, and evidence freshness rules. Reject subjective or
multi-outcome criteria before continuing.

Write `.sweetclaude/contracts/success-criteria-lint-report.json` and fail the
gate unless every criterion is binary and measurable. Compute and record
`success_criteria_contract_hash` after the contract is frozen. Store the
contract path, hash, and `criterion_ids` in `john-wick.yaml`.

Before updating `current_step: CK1`, run:

```bash
python3 scripts/success_criteria_contracts.py validate-contract --contract .sweetclaude/contracts/success-criteria-contract.yaml
```

If the runtime validator fails, stay in D4 and correct the contract or route to
human decision. Do not continue to Plan with an invalid or stale contract.

No later phase, review, caucus, verification, release, or completion step may
add completion criteria. Later concerns require `criteria-amendment-request.yaml`,
backlog routing, split-story routing, or human escalation.

Update `current_step: CK1`.

## CK1 — Define phase check-in (Conditional)

If `phase_checkins: false`: skip. Update `current_step: P1`.

If `phase_checkins: true`: invoke `sweetclaude:library-load john-wick-checkin` with:
- `phase=DEFINE`
- `question=Does the approved PRD have sufficient coverage to generate user stories? Are any epics or acceptance criteria underspecified to the point where story writing would require guessing?`
- `discovery_artifacts={paths from discovery_artifacts in john-wick.yaml}`
- `phase_artifacts={PRD path}`
- `post_lock=false`

Record output in `checkin_outputs`.

If result is `significant`: write `current_step: D4` in `john-wick.yaml` before presenting to user:
> "CK1 found a gap: [finding]. Returning to PRD review."
Do not write `current_step: P1` until after the D4 re-review is confirmed and complete.

If result is `none` or `minor`: log and continue. Update `current_step: P1`.
