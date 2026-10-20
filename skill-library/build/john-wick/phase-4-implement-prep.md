# Phase 4: Implement Prep

## IP1 — Spawn test writer (Autonomous)

Update `current_phase: IMPLEMENT_PREP` in `john-wick.yaml`.

Before spawning the test writer, verify that `john-wick.yaml` contains
`success_criteria_contract.path`, `success_criteria_contract_hash`, and
`criterion_ids`, and that the hash still matches the frozen contract file.
Stop for user decision if the contract is missing, stale, or contradictory.

Apply `../process-controls.md` using
`john-wick.yaml process_control.steps.IP1`. If subagent budget is missing,
exhausted, or stopped, set `status: waiting_for_user`,
`interactive_gate_pending.step: IP1`, and ask whether to approve a fresh test
writer budget or pause. Do not spawn the test writer while stopped.

Spawn a test writer subagent (TDD Level 3). The subagent receives: all `.feature` files from `.sweetclaude/features/`, and existing test file patterns from the project for structural context. Do NOT pass the architecture document, tech spec, contract analysis, or source implementation files — the subagent has no implementation knowledge and writes tests from Gherkin only.

The generated tests must trace to frozen `criterion_ids`. Missing coverage is a
pre-lock test gap or `criteria-amendment-request.yaml`; it is not permission to
add completion criteria.

The subagent writes test files and commits them. Record all test file paths in `created_artifacts` with `type: tests`. Update `process_control.steps.IP1` with the subagent dispatch. Update `current_step: IP2`.

## IP2 — QA caucus on test coverage (Autonomous)

Before spawning the QA caucus, apply `../process-controls.md` using
`john-wick.yaml process_control.steps.IP2`. If no budget remains or a stop
disposition is active, set `status: waiting_for_user`,
`interactive_gate_pending.step: IP2`, and ask whether to approve a fresh
caucus budget, reopen/split test coverage scope, or pause. Do not spawn
reviewers while stopped.

Spawn three QA caucus subagents in parallel:
- `qa-caucus-service`
- `qa-caucus-component`
- `qa-caucus-integration`

Input for each: test files, Gherkin specs, stories, PRD.

Input also includes the frozen success criteria contract path and
`success_criteria_contract_hash`. QA reviewers may identify criterion coverage
gaps but may not add completion criteria.

Consolidate gaps using the same uncontested/contested rule as D3: a gap is uncontested if all three caucus outputs flag it, or two flag it and one is silent. Write the consolidated gap list to `.sweetclaude/caucus/qa-coverage-[YYYYMMDD].md`. Record in `caucus_outputs`: `{step: IP2, path: ...}`. Update `process_control.steps.IP2` with one caucus round and three reviewer agents used. Test files are pre-lock at this point — apply uncontested gap coverage additions to test files. If the caucus exposes blocking coverage drift that would require another caucus, increment blocking failures and stop for user decision or test-contract reopen before any recaucus. Update `current_step: IP3`.

## IP3 — RED validation (Autonomous)

Run the full test suite. All tests must fail (RED). If any tests pass unexpectedly:
1. Investigate: is the test trivially true? Is there existing code satisfying it?
2. Correct the test or the test setup until all tests fail for the right reasons.
3. Do not advance until every test is RED.

After 3 correction attempts, if any tests still pass unexpectedly: halt and present:
> "IP3: {N} tests cannot be made to fail after 3 correction attempts. Options: (1) Unlock tests and rewrite — return to IP1, (2) Skip these tests and proceed to IP4, (3) Abort."
Wait for user decision. On return to IP1: set `current_step: IP1`. On skip: record skipped tests in `context_checkpoint.notes`, proceed to IP4. On abort: `status: paused`. Stop.

Also increment `process_control.steps.IP3.process_failure_count` for each RED
correction attempt. If the failure count exceeds the process-control limit or
the failures show repeated pass-state bypasses, stop for user decision before
more test edits.

Update `current_step: IP4`.

## IP4 — Post-RED QA pass (Autonomous)

Before the focused QA review, apply `../process-controls.md` using
`john-wick.yaml process_control.steps.IP4`. If no review budget remains or a
stop disposition is active, stop for user decision before running review.

Run a single-turn focused QA review: "Did anything slip through the RED validation? Are there any test cases that are trivially satisfiable or that don't actually test the stated behavior?"

Apply any final adjustments to test files. Commit:
```
test: RED — {feature_name} failing tests committed
```

Update `current_step: IP5`.

## IP5 — Test lock (Autonomous)

Collect all test file paths from `created_artifacts` where `type: tests`. Write them to `locked_test_files` in `john-wick.yaml`.

The `test-guardian` hook now enforces these locks across all subsequent file writes — any attempt to modify a locked test file will be blocked.

Emit: "Test files locked. From this point, test modifications require explicit user unlock and return to IP1."

Update `current_step: IP6`.

Commit: `chore(john-wick): IP5 test lock — {N} files locked`

## IP6 — Create issues (Conditional)

**If `github_mode: true`:**

For each story in the stories document, create a GitHub issue:
```bash
gh issue create \
  --title "{story title}" \
  --body "{acceptance criteria in markdown}" \
  --label "john-wick" \
  --label "{feature_name}"
```

On failure (rate limit, auth error): wait 5 seconds and retry once. If retry fails, log the error and continue — do not halt the pipeline for issue creation failures.

Record each issue number in `john-wick.yaml issue_list`. Update `current_step: IM1`.

**If `github_mode: false`:**

Write `.sweetclaude/state/issue-list.md`:
```markdown
# Issue List — {feature_name}

| # | Title | Status |
|---|---|---|
| 1 | {story title} | pending |
| 2 | {story title} | pending |
```

Record in `john-wick.yaml issue_list` with sequential numbers. Update `current_step: IM1`.
