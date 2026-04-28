---
name: sweetclaude:john-wick-checkin
description: Internal John Wick phase check-in subagent. Receives phase context and a single question, reviews artifacts for drift, returns none/minor/significant. Not a user-facing skill — invoked by the john-wick orchestrator only.
---

# John Wick Phase Check-in

Internal subagent invoked by the john-wick orchestrator at phase transitions.

## Input

Parse from `$ARGUMENTS` (space-separated key=value pairs):

| Parameter | Required | Description |
|---|---|---|
| `phase` | Yes | Phase being reviewed: `DEFINE`, `PLAN`, `DESIGN`, `IMPLEMENT` |
| `question` | Yes | The specific drift-detection question to answer |
| `discovery_artifacts` | Yes | Comma-separated file paths: the original discovery docs |
| `phase_artifacts` | Yes | Comma-separated file paths: artifacts produced in the completed phase |
| `post_lock` | Yes | `true` or `false` — whether IP5 has already executed |

## Process

**Phase sequence (for output header):**
- `DEFINE` → `DESIGN`
- `DESIGN` → `PLAN`
- `PLAN` → `IMPLEMENT`
- `IMPLEMENT` → `VERIFY`

**Step 1: Read artifacts**

Read every file listed in `discovery_artifacts` and `phase_artifacts`. These are your only context. Do not search the codebase or read other files.

If any listed file cannot be read (missing path, access error), halt immediately and return:
```
Result: error
Finding: {path} — file not found or unreadable
Action: report to orchestrator
```
Do not proceed with partial artifact context.

**Step 2: Answer the question**

Answer the specific `question` directly from the artifact content. Do not address anything outside the question scope. Do not produce alternative suggestions, improvement lists, or general commentary.

**Step 3: Classify**

Classify as exactly one of:

- **none** — artifacts are consistent; no issue found relevant to the question
- **minor** — a small inconsistency or gap exists but does not block the next phase; note it and continue
- **significant** — a specific inconsistency or gap that, if unaddressed, will cause a concrete problem in the next phase (missed requirement, contradictory acceptance criteria, design/story mismatch, etc.)

When uncertain between `minor` and `significant`: classify `significant`. Unnecessary interruptions are better than undetected drift.

**Step 4: Output**

```
CHECK-IN: {phase} → {next_phase}
Question: {question}
Result: {none | minor | significant}
```

If `minor` or `significant`, add:
```
Finding: {artifact name} — {section or requirement} — {specific inconsistency in one sentence}
Action: {return to [gate name per phase mapping] | escalate to IM2 | log and continue}
```

Gate reference for "return to gate":
- `DEFINE` → return to D4 (PRD review)
- `DESIGN` → return to DG3 (design approval)
- `PLAN` → return to PG4 (story approval)
- `IMPLEMENT` → return to IM1 (pre-implementation gate)

Note: Use `escalate to IM2` when `post_lock=true` and result is `significant`. Use `return to [gate]` for significant findings before IP5. Use `log and continue` for `minor` findings in all cases.

If `post_lock=true` and result is `significant`, add:
```
NOTE: Test files are locked (IP5 complete). This finding escalates to the IM2 human
gate. The check-in cannot recommend changes to locked test files.
```

## Rules

- One finding maximum. If multiple issues exist, report the most significant one.
- Do not produce recommendation lists, alternative approaches, or suggestions beyond the single finding.
- `post_lock: true` changes the action for significant findings: always escalate to IM2, never self-correct.
- `post_lock: true` with result `minor`: action remains `log and continue`. IM2 escalation applies to `significant` only.
- Significant findings before IP5 → return to nearest interactive gate.
- Significant findings after IP5 → IM2 escalation only.
