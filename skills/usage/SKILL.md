---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Toggle and view local usage tracking."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Usage

Opt-in local telemetry for understanding how SweetClaude is being used in a project. No external services, no network calls — just append-only event logs in `.sweetclaude/metrics/`.

## Subcommands

Parse the user's input to determine the subcommand:

| Input | Action |
|-------|--------|
| `usage on` | Enable metrics collection |
| `usage off` | Disable metrics collection |
| `usage`, `usage show`, `usage dashboard` | Show the dashboard |
| `usage reset` | Archive current events and start fresh |

## Subcommand: on

1. Create `.sweetclaude/metrics/` directory if it doesn't exist.
2. Write `.sweetclaude/metrics/config.yaml`:
   ```yaml
   schema_version: 1
   enabled: true
   enabled_at: {ISO 8601 timestamp}
   ```
3. Create `.sweetclaude/metrics/events.log` if it doesn't exist (empty file).
4. Confirm:
   ```
   Metrics enabled. SweetClaude will record:
     - Skill invocations
     - Phase gate outcomes
     - TDD enforcement events (guardian blocks, level selection)
     - Deference level and phase transitions

   All data stays in .sweetclaude/metrics/ — local, committed with your project.
   View anytime: /sweetclaude:usage
   ```

## Subcommand: off

1. Update `.sweetclaude/metrics/config.yaml`:
   ```yaml
   schema_version: 1
   enabled: false
   disabled_at: {ISO 8601 timestamp}
   ```
2. Do NOT delete existing data.
3. Confirm:
   ```
   Metrics disabled. Existing data preserved in .sweetclaude/metrics/.
   Re-enable anytime: /sweetclaude:usage on
   ```

## Subcommand: reset

1. Rename `events.log` to `events-{date}.log` as an archive.
2. Create a fresh empty `events.log`.
3. Confirm how many events were archived.

## Subcommand: show (default)

Read `.sweetclaude/metrics/events.log` and compute the dashboard.

If metrics are not enabled or no events exist, say so and offer to enable.

### Dashboard format

```
SweetClaude Usage — {project name}
═════════════════════════════════════

Collection: {enabled|disabled}   Events: {count}   Since: {earliest event date}

Skill Usage (top 10)
  {skill name}                    {count}
  {skill name}                    {count}
  ...

Phase Gate Outcomes
  {phase}    {pass count} passed   {fail count} failed   {waive count} waived
  ...

TDD Enforcement
  Guardian blocks:     {count}
  Level distribution:  L0: {n}  L1: {n}  L2: {n}  L3: {n}

Phase Distribution
  {phase}              {session count} sessions
  ...

Deference Levels Used
  Collaborative: {n}   Guided: {n}   Autonomous: {n}
```

If any section has zero data, omit it rather than showing empty tables.

### Insights

After the dashboard, add 1-3 short observations based on the data. Examples:
- "Pain thesis is your most-used skill — it's invoked 3x more than any other strategy skill."
- "Phase gate for Define has failed 4 times on 'measurable success criteria' — this criterion may need refinement or the phase needs more attention."
- "TDD guardian has blocked 12 edits across 3 sessions — enforcement is active and firing."
- "You've never used Autonomous deference — consider it for implementation phases where architecture is locked."

Only surface insights that are actionable or surprising. Don't state the obvious.

---

## Recording Protocol

Other SweetClaude skills record metrics by appending to `.sweetclaude/metrics/events.log`. This section defines the contract.

### Check before recording

Before recording an event, a skill MUST check:
1. Does `.sweetclaude/metrics/config.yaml` exist?
2. Does it contain `enabled: true`?

If either is false, skip recording silently. Never prompt the user about metrics from other skills.

### Event format

Each event is a YAML document separated by `---`:

```yaml
---
timestamp: {ISO 8601}
event: {event_type}
{event-specific fields}
```

### Event types

#### skill_invoked
Recorded when any SweetClaude skill is invoked.
```yaml
---
timestamp: 2026-04-23T14:30:00Z
event: skill_invoked
skill: sweetclaude:product-discovery
phase: discover
```

#### phase_gate_check
Recorded when phase gate exit criteria are evaluated.
```yaml
---
timestamp: 2026-04-23T14:45:00Z
event: phase_gate_check
phase: discover
result: pass|fail|waived
criteria_met: 5
criteria_total: 7
criteria_failed:
  - competitive_analysis_offered
  - improvement_checkin
```

#### phase_transition
Recorded when the project moves between phases.
```yaml
---
timestamp: 2026-04-23T15:00:00Z
event: phase_transition
from_phase: discover
to_phase: define
```

#### tdd_level_selected
Recorded when a TDD level is chosen for a task.
```yaml
---
timestamp: 2026-04-23T15:10:00Z
event: tdd_level_selected
level: 2
work_type: feature
```

#### tdd_guardian_block
Recorded when test-guardian blocks a file edit.
```yaml
---
timestamp: 2026-04-23T15:15:00Z
event: tdd_guardian_block
file: tests/auth.test.ts
phase: implement
tdd_level: 2
```

#### deference_set
Recorded when the deference level is set or changed.
```yaml
---
timestamp: 2026-04-23T14:00:00Z
event: deference_set
level: guided
```

#### session_start
Recorded when a SweetClaude session begins (master skill pre-flight).
```yaml
---
timestamp: 2026-04-23T14:00:00Z
event: session_start
phase: implement
deference: guided
```
