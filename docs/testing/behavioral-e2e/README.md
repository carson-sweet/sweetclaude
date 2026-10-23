# Behavioral Routing Suite

**Version:** 2.1.0

**Date:** 2026-10-23

This suite checks that a plain-language request reaches the right Tier 1 category and the right Tier 2 workflow. It does not check what the workflow does after it loads.

## Files

- `tests/behavioral/routing_cases.yaml`: 33 cases. 24 come from the stories in `new-saas-lifecycle.feature` (Monitor stories are excluded) and 9 are supplemental cases for configure and utils. Each case gives an expected category, the workflows that are acceptable, and whether a clarifying question counts as a pass.
- `scripts/routing_behavior.py`: the fixture, the driver and the oracle.
- `tests/test_routing_behavior.py`: tests that need no LLM and run in CI. They validate the case file against the library indexes, calibrate the oracle on the recorded transcripts in `tests/fixtures/routing_transcripts/`, and run the driver against a fake `claude`.

## Running it live

```
python3 scripts/routing_behavior.py --tier smoke          # 6 cases, one per category
python3 scripts/routing_behavior.py --tier full           # 33 cases
python3 scripts/routing_behavior.py --only design-api --entry both
python3 scripts/routing_behavior.py --tier full --dry-run
```

Both tiers send every case through `/sweetclaude:go`. A case that fails through `go` is run again through its category command (`/sweetclaude:<category>`), which shows whether Tier 1 or Tier 2 is at fault. The re-run happens at most once per case, however many repeats fail. `--no-diagnose` turns it off. Results are written to `.sweetclaude/routing-results/`, which is gitignored.

Every run uses your normal Claude login and loads this checkout with `--plugin-dir`, with project and local settings only. Each run also gets:

- a new throwaway Git project;
- a $0.50 spend cap, a 90-second timeout and an $8 cap on the whole run;
- Bash allowed in the throwaway fixture, with Write, Edit and NotebookEdit disabled.

Each case runs once. A case whose first graded run fails is rerun, up to 3 runs (`--repeat 3`), while a 2-of-3 majority is still reachable. A case passes when its first graded run passes, or when at least 2 graded runs pass and passes are a majority. A case whose graded runs disagree is reported as unstable. `harness-error` runs are left out of the count, and a case with no graded runs gets the verdict `harness-error`. The summary carries `cases`, `verdicts` and `unstable` alongside the per-run fields.

The run is interrupted as soon as a workflow's `SKILL.md` is read.

## Oracle

The oracle reads tool calls only. Nothing the model says in prose counts as evidence.

- **Workflow:** the first `Read` of `skill-library/<category>/<workflow>/SKILL.md`.
- **Category:** the first `Read` of `skill-library/<category>/INDEX.md`. If there is none, a `Skill` call to `sweetclaude:<category>` or `sweetclaude:status`/`help`, or the arguments passed to `library-load`.
- **Statuses:**
  - `pass` and `pass-clarified` count as passes. `pass-clarified` applies only when the case allows a clarifying question.
  - `wrong-category`, `wrong-workflow`, `clarified` and `no-route` count as failures.
  - `harness-error` is neither a pass nor a failure. It covers a fixture rejected by the startup check, a plugin missing or loaded from the wrong place, missing Tier 1 commands, timeouts and CLI failures.

Before any paid run, the driver runs `hooks/session-preflight.sh` against the fixture and refuses to start if it is rejected. That rejection is the failure that invalidated every case on 2026-10-19 (see `FAILURE-REGISTER.md`, BEH-001).

## Baselines (Sonnet)

**2026-10-20, first run:** 30 of 33 passed, $4.43. All three failures were Tier 1 category choices: `build-issue-tracker` went to configure, `test-performance` went to maintain, and `utils-big-picture` went to `sweetclaude:status`. Each passed through its category command, and find-skill boundary rules fixed them.

**2026-10-20, 5.0.0 release candidate:** 32 of 33 passed, $4.20. The one miss, `plan-milestone`, was a fixture artifact: the weekly doctor checkup prompt fired in the fresh project. The fixture now records a recent doctor run, and the case passed on rerun. Every run's catalog listed exactly the nine Tier 1 commands.

## Harness change policy (2026-10-23)

The harness is changed only through cases, fixtures and flags. A structural change to the driver or the oracle requires a recorded transcript that the oracle misgrades, added to `tests/fixtures/routing_transcripts/` with the change.

The defaults are: Bash allowed in the throwaway fixture with Write, Edit and NotebookEdit disallowed; a $0.50 per-case cap; an $8 run cap as the spend control; and one run per case, with failed cases rerun up to 3 times and graded by a 2-of-3 majority, with unstable cases reported (changed 2026-10-23 to cut a full run from about $15 to about $5).

Run the full tier before and after any change to skill descriptions, `find-skill`, or an INDEX file, and compare which cases flip. A run with no decision it could change should not happen.

The suite is not a release gate. The release gate was removed in `b4611e60`.
