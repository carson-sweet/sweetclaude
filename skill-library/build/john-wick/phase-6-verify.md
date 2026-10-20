# Phase 6: Verify

## V1 — Full test run + report (Autonomous)

Update `current_phase: VERIFY` in `john-wick.yaml`.

Run the complete test suite on the feature branch. Generate a final MD test report (see report-format.md) and append to the aggregate report. If any tests fail: run the severity classifier (see severity-classifier.md). If significant failures: invoke IM2. **V1-specific IM2 behavior:** Fix-and-continue from V1 re-enters at V1 (re-run the full test suite) — do NOT re-enter the IM1 loop. After 2 consecutive Fix-and-continue cycles from V1, IM2 presents only Skip (proceed to V2 with known test failures documented) and Abort options. If not significant: log and continue.

Validate `.sweetclaude/reports/success-criteria-ledger.json` against the frozen
`success_criteria_contract_hash`. Every frozen `criterion_ids` entry must be
present, evaluated, fresh, and passed. Do not advance if
`all_success_criteria_passed == true` is absent or false.

Run:

```bash
python3 scripts/success_criteria_contracts.py validate-ledger --contract .sweetclaude/contracts/success-criteria-contract.yaml --ledger .sweetclaude/reports/success-criteria-ledger.json
```

Before any V1 Fix-and-continue cycle, apply `../process-controls.md` using
`john-wick.yaml process_control.steps.V1`. Each failed cycle increments
`process_failure_count`. If the process-control limit is reached before the
V1-specific two-cycle cap, stop at IM2 with no autonomous fix attempt.

Update `current_step: V2`.

## V2 — Code, security, and compliance review (Autonomous)

Invoke `sweetclaude:library-load code-review` with all three review types: code, security, and compliance.

The compliance review reads `.sweetclaude/state/compliance-context.yaml` automatically (Plan 1 updated this skill). No manual framework specification needed.

Review may verify the frozen criteria ledger, but no review, caucus,
verification, release, or completion step may add completion criteria. Findings
outside the frozen criteria must route to backlog, amendment request, split
story, or human escalation.

Write review output to `.sweetclaude/reports/code-review-[YYYYMMDD].md`.
Record in `created_artifacts`: `{step: V2, type: report, path: ..., version: 1}`.

If any Critical findings in code or security review: set `status: waiting_for_user`, `interactive_gate_pending.step: V2`, `interactive_gate_pending.description: Critical review findings require decision`. Commit: `chore(john-wick): artifacts at V2 — awaiting gate`. Present findings. Wait for user decision before continuing. On response: clear `interactive_gate_pending`, set `status: active`.

Update `current_step: V3`.

## V3 — Update user-facing documentation (Autonomous)

Invoke `sweetclaude:library-load documents-update-docs` for all user-facing documentation affected by the feature. If the skill does not exist: log "sweetclaude:library-load documents-update-docs not found — skipping V3" and continue.

Update `current_step: V4`.

## V4 — Update design documents (Autonomous)

Update all design documents (architecture, tech spec, contract analysis) to reflect the final implementation. These are now post-implementation records, not pre-implementation plans. Increment versions in `created_artifacts` only for entries whose content was actually modified. Commit:
```
docs: update design documents to reflect final {feature_name} implementation
```

Update `current_step: V5`.

## V5 — Cut PR (Interactive)

Update `john-wick.yaml`: set `status: waiting_for_user`, `interactive_gate_pending.step: V5`, `interactive_gate_pending.description: Final PR review`.

Commit any remaining artifacts: `chore(john-wick): artifacts at V5 — awaiting gate`.

Before creating the PR:
1. Verify the current git branch matches `feature_branch` in `john-wick.yaml`: run `git rev-parse --abbrev-ref HEAD`. If they do not match: halt with "Branch mismatch: current branch is {current}, expected {feature_branch}. Checkout the correct branch before continuing."
2. Check if a PR already exists for this branch: `gh pr view --head {feature_branch} 2>/dev/null`. If one exists, use its URL instead of creating a new one — skip the `gh pr create` step.

Create the final pull request:

```bash
gh pr create \
  --title "{feature_name}: {one-line description from PRD executive summary}" \
  --base main \
  --head {feature_branch} \
  --body "..."
```

If `gh pr create` fails: set `status: error`, record in `context_checkpoint.notes`, and follow the Error Handling protocol. Do not proceed.

PR description must reference (in order):
1. Approved PRD: `{prd_path}` (version {N})
2. User stories: `{stories_path}`
3. Gherkin specs: `.sweetclaude/features/`
4. Test report (aggregate): `.sweetclaude/reports/test-report-{feature_name}.md`
5. Success criteria ledger: `.sweetclaude/reports/success-criteria-ledger.json` with `all_success_criteria_passed == true`
6. Code review findings: `.sweetclaude/reports/code-review-[YYYYMMDD].md`
7. Compliance frameworks applied: {list from compliance-context.yaml derived_frameworks}
8. Any IM2 escalations that occurred and how they were resolved (list from checkin_outputs where escalated=true)

Present the PR URL to the user:
```
JOHN WICK — Pipeline Complete
══════════════════════════════
PR: {url}

Pipeline summary:
- Phases completed: Bootstrap → Define → Plan → Design → Implement Prep → Implement → Verify
- Issues resolved: {N complete} / {N total}
- Issues skipped: {N skipped}
- Tests: {pass}/{total}
- Check-ins run: {N} (significant findings: {N})
- IM2 escalations: {N}
- Review findings: {N critical} critical, {N warning} warning

Compliance frameworks applied: {list from compliance-context.yaml}
```

On user acknowledgment: clear `interactive_gate_pending` (set both `step` and `description` to null). Close the current session: set `sessions[-1].ended` to the current ISO timestamp. Update `john-wick.yaml status: complete`. Record PR URL in `created_artifacts`: `{step: V5, type: pr, path: {url}, version: 1}`.
