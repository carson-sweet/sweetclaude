---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Run verification before claiming work is complete."
---

# Code Verify

**Core principle:** A claim without fresh verification evidence is a guess, not a result.

This skill runs before any statement that work is done, passing, or fixed. Arguments: `$ARGUMENTS`

---

## The Gate

Before making any completion claim, run this sequence:

1. **Identify** — what command proves the claim? (test suite, linter, build, smoke test)
2. **Run it now** — full command, fresh execution, complete output
3. **Read the output** — exit code, failure count, any warnings
4. **Then make the claim** — with the evidence, not before it

If the command hasn't run in this response, the claim cannot be made.

---

## Verification by Claim Type

| Claim | Required evidence |
|---|---|
| "Tests pass" | Test runner output showing 0 failures, current run |
| "Linter clean" | Linter output showing 0 errors, current run |
| "Build succeeds" | Build command exit 0, current run |
| "Bug fixed" | Original reproduction case now passes |
| "Regression test works" | RED confirmed (test fails on broken code), GREEN confirmed (test passes on fix) |
| "Requirements met" | Line-by-line check against acceptance criteria |
| "Phase complete" | Phase gate exit criteria checked item by item |

---

## SweetClaude Hook Integration

The auto-test-runner hook fires after every source edit — so tests have already run. This skill is not a reminder to run tests. It is a gate on *claiming* that those test results constitute completion.

The distinction: "tests ran" is a mechanical fact. "the feature is done" is a claim that requires reading the output, checking coverage, and verifying exit criteria — not just confirming the hook fired.

---

## Stop Signs

Do not proceed to commit, PR, or phase advancement if any of the following are true:

- The last test run was in a previous response
- The output was not read in full (scrolled past, assumed)
- Any test is failing, even one you think is unrelated
- The linter has warnings you haven't evaluated
- Acceptance criteria haven't been checked line by line
- You're about to say "should be fine" or "looks good"

---

## Phase Gate Use

When called as part of VERIFY phase exit:

1. Run the full test suite
2. Run the linter
3. Run the build (if applicable)
4. Check acceptance criteria against the implementation line by line
5. Confirm all phase gate exit criteria are met

Present results as a checklist. Mark each item explicitly pass/fail. Do not summarize — show the evidence.
