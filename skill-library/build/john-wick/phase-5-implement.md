# Phase 5: Implement

## IM1 — Issue iteration loop (Autonomous)

Update `current_phase: IMPLEMENT` in `john-wick.yaml`.

Execute the following loop until all issues are complete or an IM2 escalation fires:

```
For each issue in issue_list where status = pending:

  1. Update issue status to in_progress in john-wick.yaml.

  2. Create or checkout branch:
     If the branch {issue-number}-{slugified-title} does not exist:
       git checkout -b {issue-number}-{slugified-title}
     If it already exists (re-entering after IM2 Fix-and-continue or Abort+Resume):
       git checkout {issue-number}-{slugified-title}

  3. Invoke sweetclaude:library-load code-issue with issue context:
     - Issue title and acceptance criteria
     - Architecture doc and tech spec
     - Locked test files (read-only — test-guardian enforces this)
     - Compliance context
     - Frozen `success_criteria_contract_hash` and relevant `criterion_ids`

     Before invoking, apply `../process-controls.md` using
     `john-wick.yaml process_control.steps.IM1-issue-{number}`. If implementer
     budget is missing, exhausted, or stopped, set
     `status: waiting_for_user`, `interactive_gate_pending.step: IM2`, and
     present the escalation gate before invoking more agents or patching.

  4. Run the full test suite. Generate a test report (see report-format.md).
     Append to aggregate report at .sweetclaude/reports/test-report-{feature_name}.md.

  5. Evaluate failure severity (see severity-classifier.md).
     - If significant: pause loop, update issue status to escalated,
       set john-wick.yaml status=waiting_for_user, advance to IM2 gate.
     - If not significant: attempt bug fixes (up to 3 iterations).
       Re-run tests after each fix. Re-evaluate severity.
       If still failing after 3 iterations: escalate to IM2.
       Each fix attempt increments
       `process_control.steps.IM1-issue-{number}.process_failure_count`.
       If the process-control limit is reached before the third fix, escalate
       to IM2 immediately. Do not continue a patch-test loop after the process
       ledger reports a stop.

  6. Once tests are green (after step 5 completes — not after each individual fix attempt):
     Update `.sweetclaude/reports/success-criteria-ledger.json` for the current
     issue. The ledger must map each relevant frozen criterion id to accepted
     evidence, pass/fail status, evidence freshness, and the evaluated
     `success_criteria_contract_hash`. The issue may be marked complete only
     when its relevant ledger entries support `all_success_criteria_passed == true`.

     If phase_checkins=true: invoke sweetclaude:library-load john-wick-checkin with:
     - phase=IMPLEMENT
     - question=Is this implementation drifting from the approved design? Does the code match the architecture, tech spec, frozen success_criteria_contract_hash, and criterion_ids?
     - discovery_artifacts={paths from john-wick.yaml}
     - phase_artifacts={architecture path, tech spec path, current issue branch diff, success-criteria-ledger.json}
     - post_lock=true
     If significant: escalate to IM2 (cannot modify locked tests).
     Record significant drift as a blocking failure in the process-control
     ledger. A second significant drift for the same issue requires IM2 and a
     human decision before further implementation.

  7. If all tests green: merge branch to feature branch.
     git checkout {feature_branch} && git merge {issue-branch} --no-ff
     Commit message: "feat({feature_name}): close issue #{number} — {title}"
     If github_mode=true: run `gh issue close {number}` to close the GitHub issue.
     Update issue status to complete in john-wick.yaml.

  8. Advance to next issue.
```

When all issues are complete: update `current_phase: VERIFY`, `current_step: V1`.

## IM2 — Escalation gate (Interactive, conditional)

Fires when the severity classifier returns significant, or when a post-IP5 check-in finds significant drift.

Present:
```
JOHN WICK — Implementation Escalation
══════════════════════════════════════
Issue: #{number} — {title}

Problem:
{finding or severity classifier output}

Options:
1. Fix and continue — describe what you want changed; John Wick will apply it and resume
2. Skip this issue — mark as skipped, continue to next issue
3. Abort — stop the pipeline here; state is saved

Your decision:
```

On user decision:
- **Fix and continue**: record `status: waiting_for_user` in `john-wick.yaml`. On response: clear `interactive_gate_pending` (set both fields to null). Set `status: active`. Apply the user's described fix. Re-enter the issue loop at step 4 (test run) — the branch already exists and code changes have been applied.
- **Skip**: update issue status to `skipped` in `john-wick.yaml`. Set `status: active`. Continue loop.
- **Abort**: set `john-wick.yaml status: paused`. Stop.
