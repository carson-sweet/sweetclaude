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


## Evidence Receipt

Before making any completion, close, ship, or release claim on a concrete work
item, write a completion evidence receipt. `--run` executes the command and
records what it actually did — exit code and output — rather than recording an
assertion about a run that happened earlier in the conversation:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/evidence.py write \
  --project-dir . \
  --subject-id {WORK_ITEM_ID} \
  --receipt-type completion \
  --check verification \
  --status pass \
  --command "{exact verification command}" \
  --summary "{short result summary}" \
  --run
```

If the command fails, the write is refused. That is the gate working: there is
nothing to decide and nothing to be honest about, because the receipt reports
the run rather than your account of it.

Keep the returned `receipt` path and pass it to closeout commands with
`--evidence-receipt {receipt}`. Closing an issue requires a verified receipt —
one written without `--run` is refused there.

Give `--command` a single command that verifies the whole item. If verification
genuinely cannot be reduced to one command, run each one with its own `--run`
receipt rather than picking the one that passes.

## Record the outcome

Verification either passed or it did not, and that is the whole point of the
skill — so it is the clearest signal the metrics log can carry. Record it
before finishing (ISSUE-276):

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/record-event.sh skill_completed \
  skill=sweetclaude:code-verify outcome=completed "detail=all checks passed"
```

If any check failed, record the failure and name the check — a failure with no
detail cannot be acted on later:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/record-event.sh skill_completed \
  skill=sweetclaude:code-verify outcome=failed "detail={which check failed}"
```

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
