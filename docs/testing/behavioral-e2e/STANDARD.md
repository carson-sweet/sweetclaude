# Standard Behavioral Run

Version: 1.0.0

Date: 2026-10-19

The standard recurring scope is a three-session public-routing regression run. It uses [standard.json](standard.json) and selects one representative operation for each public command: Go request, Plan, Design, Build, Maintain, Configure, Utils, Status session, and Help menu.

Every operation runs through `/sweetclaude:<command>` with direct and indirect plain-language wording, against both its happy fixture and the changed-fault fixture. This yields 36 cases per session and 108 independent attempts per run. It deliberately excludes bare entry, literal discovery, Tier 2 execution, profiles, branch matrices, hooks, capabilities, provider-dependent changes, and multi-turn journeys. Those remain in the full acceptance inventory and cannot be claimed by this recurring run.

Run the selection preview:

```sh
python3 scripts/select_behavioral_clusters.py --config docs/testing/behavioral-e2e/standard.json
```

Estimate cost without model calls:

```sh
python3 scripts/estimate_behavioral_e2e_cost.py
```

Run it with the `$25` whole-run ceiling:

```sh
python3 scripts/run_behavioral_e2e.py \
  --config docs/testing/behavioral-e2e/standard.json \
  --repeat 3 --execute --max-run-budget-usd 25 \
  --output /tmp/sweetclaude-standard-run.json
```

The runner displays actual cost and cumulative total after every attempt. If the remaining cap is exhausted, it stops before starting another test and reports the unrun denominator. A stopped run is not a passing standard run.

[standard-cost-estimate.json](standard-cost-estimate.json) uses 22 recorded live cases: the mean estimate is `$11.40`; the maximum-observed-rate estimate is `$19.69`. These are estimates, not a price guarantee. The `$25` cap remains authoritative.
