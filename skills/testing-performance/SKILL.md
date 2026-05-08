---
spdx-license: AGPL-3.0-or-later
name: testing-performance
user-invocable: true
description: "Define load scenarios, establish performance baselines, set thresholds. Compare benchmark results. Ties into performance optimization phase gates."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
PERF_FILE="$PWD/.sweetclaude/state/performance.yaml"
cat "$PERF_FILE" 2>/dev/null || echo "PERF_NOT_FOUND"

ls .sweetclaude/testing/performance/benchmark-*.json 2>/dev/null | wc -l | xargs -I{} echo "BENCHMARK_COUNT={}"
ls .sweetclaude/testing/performance/benchmark-*.json 2>/dev/null | tail -3
```

# Testing Performance

Define load scenarios, set thresholds, and track benchmark results over time. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `status` | → **Status** — baselines and recent results |
| `scenario new` | → **Define** a new load scenario |
| `scenario list` | → **List** all scenarios |
| `baseline record` | → **Record** a benchmark result as the baseline |
| `benchmark record` | → **Record** a benchmark result for comparison |
| `compare` | → **Compare** latest results against baseline |
| `threshold set <scenario>` | → **Set** performance thresholds for a scenario |

---

## Status

Use performance state from shell block.

If `PERF_NOT_FOUND`: "No performance tracking initialized. Run `testing-performance scenario new` to define a scenario."

Otherwise present:

```
Performance Status
══════════════════════════════════════════════════

Scenarios
  API — homepage load         baseline: 2024-03-01   last run: 2024-04-15
  API — POST /api/search      baseline: 2024-03-01   last run: 2024-04-15
  Background — bulk export    baseline: —             last run: —

Latest vs Baseline
  homepage load     p50: 120ms → 130ms (+8%)    p99: 450ms → 520ms (+16%)  ⚠ p99 > threshold
  POST /api/search  p50: 80ms  → 75ms  (-6%)    p99: 310ms → 280ms (-10%)  ✓
```

---

## Scenario New

Ask one question at a time:

**1. Operation name** — "What operation or endpoint is this scenario testing? One line."

Examples: `GET /api/projects`, `POST /api/search`, `background job: nightly export`, `page load: dashboard`

**2. Operation type** — HTTP endpoint, background job, CLI command, page load, database query

**3. Load profile** — "Describe the load this should simulate."

For HTTP:
- Concurrent users at steady state
- Ramp-up period (e.g., 0 → 50 users over 30 seconds)
- Test duration (e.g., 5 minutes at steady state)
- Request rate (if fixed) or think time (if user-simulated)

For background jobs / CLI:
- Input size or count (e.g., 10,000 records, 500MB file)
- Whether parallelism is in scope

**4. Thresholds** — "What performance is acceptable?" Ask for:
- p50 latency target (median — what most users experience)
- p95 latency target (95th percentile — near-worst case)
- p99 latency target (99th percentile — tail latency)
- Error rate limit (e.g., < 0.1%)
- Throughput floor (if applicable — minimum requests/sec)

Defaults if not specified:
- p50: 200ms for HTTP, no limit for batch
- p95: 500ms for HTTP
- p99: 1000ms for HTTP
- Error rate: < 0.1%

**5. Tool** — "What tool will you run this with?" (k6, Locust, wrk, ab, custom script, manual)

If none: "You can record results manually — just record the measured values when you run the test."

---

Write to performance.yaml:

```bash
python3 - <<'PYEOF'
import yaml
from datetime import datetime

try:
    with open('.sweetclaude/state/performance.yaml') as f:
        state = yaml.safe_load(f) or {}
except FileNotFoundError:
    state = {'schema_version': 1, 'scenarios': {}}

state['scenarios']['<scenario_id>'] = {
    'name': '<name>',
    'type': '<type>',
    'load_profile': {
        'concurrent_users': '<N>',
        'ramp_up_seconds': '<N>',
        'duration_seconds': '<N>'
    },
    'thresholds': {
        'p50_ms': <N>,
        'p95_ms': <N>,
        'p99_ms': <N>,
        'error_rate_pct': <N>
    },
    'tool': '<tool>',
    'baseline': None,
    'results': []
}

with open('.sweetclaude/state/performance.yaml', 'w') as f:
    yaml.dump(state, f, default_flow_style=False, allow_unicode=True)
print('ok')
PYEOF
```

Confirm: `Scenario defined — {name}`

---

## Baseline Record

Arguments: `baseline record`

Ask: "Which scenario?" (list defined scenarios)

Ask for measured values:
- p50 latency (ms)
- p95 latency (ms)
- p99 latency (ms)
- error rate (%)
- throughput (req/s or jobs/min — if applicable)
- environment and conditions (e.g., "staging, 2-core instance, warm cache")
- tool and command used

```bash
mkdir -p .sweetclaude/testing/performance/
python3 - <<'PYEOF'
import yaml, json
from datetime import datetime

with open('.sweetclaude/state/performance.yaml') as f:
    state = yaml.safe_load(f)

result = {
    'recorded_at': datetime.now().isoformat(),
    'type': 'baseline',
    'p50_ms': <p50>,
    'p95_ms': <p95>,
    'p99_ms': <p99>,
    'error_rate_pct': <error_rate>,
    'throughput': <throughput_or_null>,
    'environment': '<environment>',
    'tool': '<tool>',
    'command': '<command_or_null>'
}

scenario = state['scenarios']['<scenario_id>']
scenario['baseline'] = result
if 'results' not in scenario:
    scenario['results'] = []
scenario['results'].append(result)

with open('.sweetclaude/state/performance.yaml', 'w') as f:
    yaml.dump(state, f, default_flow_style=False, allow_unicode=True)

# Also save as timestamped benchmark file
filename = f".sweetclaude/testing/performance/benchmark-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump({'scenario': '<scenario_id>', **result}, f, indent=2)
print(f'saved: {filename}')
PYEOF
```

Compare against thresholds immediately:

```
Baseline recorded — {scenario name}
  p50:   {value}ms   threshold: {threshold}ms  {✓ or ⚠}
  p95:   {value}ms   threshold: {threshold}ms  {✓ or ⚠}
  p99:   {value}ms   threshold: {threshold}ms  {✓ or ⚠}
  errors: {value}%   threshold: {threshold}%   {✓ or ⚠}
```

If any threshold exceeded at baseline: "Baseline is already above threshold for {metric}. Consider updating the threshold to reflect reality, or filing a performance issue."

---

## Benchmark Record

Arguments: `benchmark record`

Same as baseline record but `type: benchmark`. Saved to results array and timestamped file. Does not replace the baseline.

---

## Compare

Load all scenarios with at least one benchmark result after the baseline.

For each scenario:

```
{scenario name} — {date of latest run}
─────────────────────────────────────────
         Baseline    Latest    Delta    Threshold
p50      120ms       130ms     +8%      200ms  ✓
p95      310ms       340ms     +10%     500ms  ✓
p99      450ms       520ms     +16%     1000ms ✓
errors   0.0%        0.1%      +0.1pp   0.1%   ✓
```

Flag regressions: any metric that increased >10% from baseline, or any metric above threshold.

If a regression is detected: "Regression detected in {scenario}: {metric} increased {delta}. File a performance issue?"

On yes:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_create issue '{
  "title": "Performance regression: <scenario> — <metric> +<delta>",
  "type": "bug",
  "status": "backlog",
  "priority": "sooner",
  "description": "Baseline: <baseline>\nLatest: <latest>\nDelta: <delta>\nThreshold: <threshold>",
  "tags": ["performance"]
}'
```

---

## Threshold Set

Arguments: `threshold set <scenario>`

Load current thresholds. Ask for updates. Write back to performance.yaml. Confirm.

---

## Rules

- A baseline is required before regressions can be detected. Surface this clearly: "No baseline for {scenario} — record one before this comparison is meaningful."
- p99 matters more than p50 for user experience. If p50 is fast but p99 is slow, the system has a tail problem — name it.
- Environment and conditions must be recorded with every benchmark. A 2x improvement that reflects a larger instance is not a code improvement.
- Threshold violations at baseline don't invalidate the baseline — they are a signal. The baseline is what the system does, not what you want it to do.
- This skill tracks results. It does not run load tests. Pair it with k6, Locust, wrk, or equivalent.
