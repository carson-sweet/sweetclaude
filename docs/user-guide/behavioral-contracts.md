# Behavioral Contract Status

**Version:** 1.1
**Date:** 2026-08-09

SweetClaude's instruction-guided behavioral properties are probabilistic — they depend on how the underlying model interprets instructions, which can change with model upgrades. This page tracks which contracts have been validated against which model versions.

Run `/sweetclaude:behavioral-regression` to test the current model against all 15 contracts. Results from that run can be added here.

---

## What This Tracks

SweetClaude separates behavioral properties into two tiers:

- **Deterministic (hook-enforced):** Properties like "test files cannot be edited during IMPLEMENT" are enforced by shell hooks. They do not degrade with model upgrades.
- **Instruction-guided (tracked here):** Properties like "never push for phase advancement" or "always ask for concrete examples" are probabilistic. They can drift when the underlying model changes.

This page tracks the instruction-guided tier.

---

## Judge Validation — 2026-08-09

Before a contract result means anything, the thing producing it has to be shown
capable of being wrong. This section records that check. **It does not score any
contract.** It scores the judge.

**Judge:** `gpt-5.6-sol` via the Codex CLI (`provider: openai`)
**Harness:** `scripts/behavioral_judge.py discriminate --backend codex`
**Corpus:** 12 fixtures — one turn that plainly honours and one that plainly
breaks, for each of 6 contracts
**Run:** 2026-08-09, 72 seconds

| Contract | Evidence | Correct pass | Correct fail | Wrong | Discarded | Verdict |
|---|---|---|---|---|---|---|
| CONTRACT-01 | observable | 1 | 1 | 0 | 0 | DISCRIMINATES |
| CONTRACT-02 | inferred | 1 | 1 | 0 | 0 | DISCRIMINATES |
| CONTRACT-05 | observable | 1 | 1 | 0 | 0 | DISCRIMINATES |
| CONTRACT-12 | inferred | 1 | 1 | 0 | 0 | DISCRIMINATES |
| CONTRACT-13 | inferred | 1 | 1 | 0 | 0 | DISCRIMINATES |
| CONTRACT-14 | observable | 1 | 1 | 0 | 0 | DISCRIMINATES |

12 of 12 correct, 0 discarded for a missing or fabricated citation.

**Baseline.** An `always-pass` judge gets every honouring turn right and every
breaking turn wrong, so it scores 6/12 and discriminates on nothing. Both
degenerate backends are reported unscorable by the same harness, which is what
makes the result above worth reading.

### What this does not establish

- **No contract is scored.** These fixtures are written examples, not turns from
  real sessions. A judge that can separate a plain honouring turn from a plain
  breaking one has cleared the minimum bar, not proven it handles ambiguity.
- **Two fixtures per contract is thin.** 12/12 is consistent with a good judge
  and also with easy fixtures. The corpus was deliberately written unambiguous.
- **9 of 15 contracts have no fixtures at all** — 03, 04, 06, 07, 08, 09, 10,
  11, 15. They are unmeasured, and no claim about them appears here.
- The Codex backend is an agent wrapper with no temperature control, so it is
  weaker and less reproducible than a single-turn API completion. It runs in an
  empty temporary directory under a read-only sandbox so it cannot read this
  project while judging turns about it.

---

## Contract Status by Model Version

### claude-sonnet-4-6

**Tested:** 2026-05-01
**Tested by:** Carson Sweet
**Score:** 15/15
**Evidence quality: self-reported.** This run predates the independent judge and
records the model's own assessment of whether it followed its own instructions.
Read it as a claim, not a measurement — it is the weak evidence ISSUE-275 exists
to replace. It also predates the current model.

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
| CONTRACT-14 | Writes code without comments unless explicitly requested | No |
| CONTRACT-15 | Acknowledges improvement register entries at session start | No |

*Load-bearing contracts are those where failure most directly undermines SweetClaude's value proposition.*
