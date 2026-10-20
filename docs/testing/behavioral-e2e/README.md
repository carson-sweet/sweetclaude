# Behavioral Routing Suite

**Version:** 2.0.0

**Date:** 2026-10-20

This suite checks that a plain-language request reaches the right Tier 1 category and the right Tier 2 workflow. It does not check what the workflow does after it loads.

## Files

- `tests/behavioral/routing_cases.yaml`: 33 cases. 24 come from the stories in `new-saas-lifecycle.feature` (Monitor stories are excluded) and 9 are supplemental cases for configure and utils. Each case gives an expected category, the workflows that are acceptable, and whether a clarifying question counts as a pass.
- `scripts/routing_behavior.py`: the fixture, the driver and the oracle.
- `tests/test_routing_behavior.py`: tests that need no LLM and run in CI. They validate the case file against the library indexes, calibrate the oracle on the recorded transcripts in `tests/fixtures/routing_transcripts/`, and run the driver against a fake `claude`.

## Running it live

```
python3 scripts/routing_behavior.py --tier smoke          # 6 cases, one per category, about $0.90
python3 scripts/routing_behavior.py --tier full           # 33 cases, about $4.50
python3 scripts/routing_behavior.py --only design-api --entry both
python3 scripts/routing_behavior.py --tier full --dry-run
```

Both tiers send every case through `/sweetclaude:go`. A case that fails through `go` is run again through its category command (`/sweetclaude:<category>`), which shows whether Tier 1 or Tier 2 is at fault. `--no-diagnose` turns that re-run off. Results are written to `.sweetclaude/routing-results/`, which is gitignored.

Every run uses your normal Claude login and loads this checkout with `--plugin-dir`, with project and local settings only. Each run also gets:

- a new throwaway Git project;
- a $0.25 spend cap, a 90-second timeout and a $5 cap on the whole run;
- Write and Edit disabled, and Bash denied apart from the startup commands the Tier 1 skills declare.

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
