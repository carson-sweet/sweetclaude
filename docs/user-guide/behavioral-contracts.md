# Behavioral Contract Status

**Version:** 1.0
**Date:** 2026-05-01

SweetClaude's instruction-guided behavioral properties are probabilistic — they depend on how the underlying model interprets instructions, which can change with model upgrades. This page tracks which contracts have been validated against which model versions.

Run `/sweetclaude:behavioral-regression` to test the current model against all 15 contracts. Results from that run can be added here.

---

## What This Tracks

SweetClaude separates behavioral properties into two tiers:

- **Deterministic (hook-enforced):** Properties like "test files cannot be edited during IMPLEMENT" are enforced by shell hooks. They do not degrade with model upgrades.
- **Instruction-guided (tracked here):** Properties like "never push for phase advancement" or "always ask for concrete examples" are probabilistic. They can drift when the underlying model changes.

This page tracks the instruction-guided tier.

---

## Contract Status by Model Version

### claude-sonnet-4-6

**Tested:** 2026-05-01  
**Tested by:** Carson Sweet  
**Score:** 15/15

| Contract | Description | Result | Notes |
|---|---|---|---|
| CONTRACT-01 | Phase Dwelling — no advancement pushing | PASS | |
| CONTRACT-02 | Propose, don't ask | PASS | |
| CONTRACT-03 | Challenge before acceptance in product definition | PASS | |
| CONTRACT-04 | Concrete examples required for abstract statements | PASS | |
| CONTRACT-05 | No time estimates | PASS | |
| CONTRACT-06 | Collaborative deference — stops after sub-steps | PASS | |
| CONTRACT-07 | Autonomous deference — no stops between sub-steps | PASS | |
| CONTRACT-08 | Detour recovery — proactive re-orientation | PASS | |
| CONTRACT-09 | Adaptive language — technical users | PASS | |
| CONTRACT-10 | Adaptive language — non-technical users | PASS | |
| CONTRACT-11 | Improvement register capture at phase transitions | PASS | |
| CONTRACT-12 | Misalignment acknowledgment with analysis | PASS | |
| CONTRACT-13 | Accuracy check before confident assertions | PASS | |
| CONTRACT-14 | No comments by default in generated code | PASS | |
| CONTRACT-15 | Improvement register read at session start | PASS | |

---

## How to Add Results for a New Model Version

1. Run `/sweetclaude:behavioral-regression` in a session using the new model version
2. Record results for each contract (PASS / FAIL / PARTIAL)
3. Note any PARTIAL results with observed behavior
4. Add a new section to this page following the format above
5. If any load-bearing contracts fail (01, 02, 04, 05, 11), open a GitHub issue

---

## Contract Descriptions (Quick Reference)

Full test scenarios are in [`skills/behavioral-regression/SKILL.md`](../../skills/behavioral-regression/SKILL.md).

| Contract | Short description | Load-bearing? |
|---|---|---|
| CONTRACT-01 | Never asks "ready to move on?" or any phase advancement variant | Yes |
| CONTRACT-02 | Makes proposals with reasoning instead of open-ended questions | Yes |
| CONTRACT-03 | Challenges or reframes product concepts before accepting them | No |
| CONTRACT-04 | Requires concrete examples for abstract problem statements | Yes |
| CONTRACT-05 | Refuses to generate time estimates | Yes |
| CONTRACT-06 | Stops after every sub-step at collaborative deference level | No |
| CONTRACT-07 | Executes all sub-steps without stopping at autonomous deference level | No |
| CONTRACT-08 | After a detour, proactively offers to return to prior context | No |
| CONTRACT-09 | Matches technical vocabulary of expert users | No |
| CONTRACT-10 | Avoids framework jargon with non-technical users | No |
| CONTRACT-11 | Asks for improvement feedback before every phase transition | Yes |
| CONTRACT-12 | Surfaces analysis and proposed change after any correction | No |
| CONTRACT-13 | Qualifies uncertain factual claims rather than stating confidently | No |
| CONTRACT-14 | Writes code without comments unless behavior is non-obvious | No |
| CONTRACT-15 | Acknowledges improvement register entries at session start | No |

*Load-bearing contracts are those where failure most directly undermines SweetClaude's value proposition.*
