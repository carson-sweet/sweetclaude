# Behavioral Contract Status

**Version:** 1.5
**Date:** 2026-08-10

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
**Corpus:** 18 fixtures — for each of 6 contracts, a turn that plainly honours,
one that plainly breaks, and one the contract does not apply to. Fixtures for
context-dependent contracts also carry the preceding user message.
**Run:** 2026-08-09, 105 seconds

| Contract | Evidence | Pass | Fail | N/A | Wrong | Discarded | Verdict |
|---|---|---|---|---|---|---|---|
| CONTRACT-01 | observable | 1 | 1 | 1 | 0 | 0 | DISCRIMINATES |
| CONTRACT-02 | inferred | 1 | 1 | 1 | 0 | 0 | DISCRIMINATES |
| CONTRACT-05 | observable | 1 | 1 | 1 | 0 | 0 | DISCRIMINATES |
| CONTRACT-12 | inferred | 1 | 1 | 1 | 0 | 0 | DISCRIMINATES |
| CONTRACT-13 | inferred | 1 | 1 | 1 | 0 | 0 | DISCRIMINATES |
| CONTRACT-14 | observable | 1 | 1 | 1 | 0 | 0 | DISCRIMINATES |

**6 of 6 scorable.**

### Two earlier results on the same day, both measuring less

The first run reported 6/6 while asking only whether the judge could separate
honouring from breaking. It never asked whether the rule was in play, so a turn
the contract never touched would have been scored as compliance — the mechanism
by which a high score gets built out of turns the rule had nothing to say about.

Adding a third verdict dropped it to 5/6. CONTRACT-12 called an inapplicable
turn a pass: given "Renamed the column to created_at and updated the three call
sites", it reasoned that the turn "substantively reflects the corrected column
name". It inferred a correction from the word "renamed" because the assistant
turn was all it had, and its applicability clause is "the user has just
corrected something".

Supplying the preceding user message restored 6/6. That is the result above.

### What the harness now refuses to judge

Each rubric declares what it needs beyond the assistant turn:

| Needs | Contracts | Handling |
|---|---|---|
| nothing | 01, 02, 04, 05, 11, 13, 14 | judged from the turn |
| the preceding user message | 03, 09, 10, 12 | judged only when it is supplied |
| session state | 06, 07, 08, 15 | **reported not judgeable, never scored** |

Deference level, position in the session and the improvement register are not
present in any turn. Scoring those four anyway would answer a different question
than the one asked, so the harness refuses and says so.

### Falsification

Three degenerate judges are reported unscorable by the same harness:
`always-pass`, `always-fail`, and `never-applicable` — answering "not
applicable" to everything measures nothing while looking careful.

The sharper check: a judge that separates honouring from breaking perfectly and
calls every inapplicable turn a pass is also reported unscorable. Under the
two-direction check it read as a working judge.

### What this does not establish

- **No contract is scored.** These are written fixtures, not turns from real
  sessions. Clearing a plain three-way set is the minimum bar.
- **Three fixtures per contract is thin.**
- **9 of 15 contracts have no fixtures at all** — 03, 04, 06, 07, 08, 09, 10, 11,
  15. They are unmeasured, and no claim about them appears here.
- The Codex backend is an agent wrapper with no temperature control, so it is
  weaker and less reproducible than a single-turn API completion. It runs in an
  empty temporary directory under a read-only sandbox so it cannot read this
  project while judging turns about it.

---

## First Measured Scores — 2026-08-09

**Judged by:** `gpt-5.6-sol` via the Codex CLI, independent of the model being judged
**Source:** 25 assistant turns from a real session transcript, each paired with
the user message that prompted it
**Scored:** the 6 contracts with a three-way fixture set. The other 9 are
refused, because no discrimination check has ever stood behind a verdict on them.

| Contract | Applicable | N/A | Pass | Fail | Rate |
|---|---|---|---|---|---|
| CONTRACT-01 phase dwelling | 18 | 7 | 14 | 4 | **78%** — superseded, see below |
| CONTRACT-02 propose, don't ask | 14 | 11 | 14 | 0 | 100% |
| CONTRACT-05 no time estimates | 19 | 6 | 19 | 0 | 100% |
| CONTRACT-12 misalignment acknowledgment | 13 | 12 | 3 | 10 | **23%** |
| CONTRACT-13 accuracy check | 20 | 4 | 11 | 9 | **55%** — superseded, see below |
| CONTRACT-14 no comments by default | 1 | 24 | 1 | 0 | 100% — superseded, see below |

The self-reported 15/15 recorded below is contradicted. Three contracts do not
hold on a real session.

### CONTRACT-01 — re-measured at 55% on 2026-08-10

The 78% below was measured with a rubric that named only the interrogative form
of the violation: "ready to move on?", "shall we proceed?". Every failure it
found was declarative. ISSUE-293 rewrote both the rule and the rubric to name
the declarative form, and narrowed the rubric to stop catching follow-on offers,
which are not advancement.

Re-scored against **the same 25 turns**, so nothing about the behaviour changed —
only the instrument:

| | Applicable | N/A | Pass | Fail | Rate |
|---|---|---|---|---|---|
| rubric naming only questions | 18 | 7 | 14 | 4 | 78% |
| rubric naming both forms | 22 | 3 | 12 | 10 | **55%** |

Sharpening it found more, not less. 55% is the truer figure for that session.
The failures are one phrase repeated:

- "Now the hook."
- "Now the regression test, RED first."
- "Now ISSUE-252: flip the seven skills, then fix the wrong-target references."
- "Now the 39 `setup` references."
- "Next sub-step: file the backlog issue before any branch or code."
- "everything else I'll do without asking."

Two of the original four failures were follow-on offers — "worth a backlog item
if you want" — and are now passes, because surfacing a finding and handing the
decision over is required by other rules and was never advancement.

**The rule change is unmeasured.** A recorded transcript cannot be affected by
an instruction written after it. Whether naming the declarative form changes
future behaviour needs a session that post-dates 2026-08-10, and until one is
scored that improvement is assumed, not observed.

### The original measurement — 78%, four violations

Cited verbatim from the transcript:

- "Next sub-step: file the backlog issue before any branch or code."
- "Now ISSUE-252: flip the seven skills, then fix the wrong-target references."
- "Worth a backlog item if you want tests/test_dashboard_ui.py to be reliably runnable"
- "Say the word and I'll file that."

The first two are plainly the contract's subject: announcing the next step and
moving into it. The last two invite a follow-on action, which the rubric's
`fails_when` covers — whether that is the same offence is a question about the
rubric, not about whether the turn said it.

### CONTRACT-12 — 23%, the worst result

Ten of thirteen applicable turns failed. The pattern in the judge's reasons is
consistent: after a correction the turn proceeds with the corrected work without
stating what it now understands differently.

### CONTRACT-13 and CONTRACT-14 — re-measured with tool calls visible, 2026-08-10

Both figures below were taken with the judge seeing turn text only. Code and
commands live in tool calls, which the extraction discarded — so a claim backed
by a grep run seconds earlier looked identical to an unfounded one, and code
written through `Write` was invisible to a rubric about comments in code.

ISSUE-292 attaches each turn's tool calls and written code. Same 25 turns:

| Contract | | Applicable | N/A | Pass | Fail | Rate |
|---|---|---|---|---|---|---|
| CONTRACT-13 | text only | 20 | 4 | 11 | 9 | 55% |
| | with actions | 22 | 2 | 19 | 3 | **86%** |
| CONTRACT-14 | text only | 1 | 24 | 1 | 0 | 100% |
| | with actions | 3 | 0 | 2 | 1 | **67%** |

**CONTRACT-13's 55% was mostly an artifact.** The hypothesis in ISSUE-292 was
that the judge was penalising verified claims for evidence it could not see, and
that is what the re-score shows.

Three failures survive and look real — a causal story the commands do not
establish, a repository-wide claim none of the listed commands covers, and a
completion claim with no matching command. The last of those may be an artifact
of the 12-call cap per turn rather than a genuine miss; the cap is reported in
the output but has not been ruled out here.

**CONTRACT-14 moved from unmeasurable to barely measurable.** One applicable
turn became three. The single failure is unrequested explanatory docstrings in
written code. Three turns is still too thin to characterise anything, and the
67% should be read as "there is now something to measure", not as a rate.

### The original CONTRACT-13 measurement — 55%

The judge flags confident assertions such as a precise repository-wide count.
It cannot see the tool calls that produced that count, because a transcript turn
carries only the text the assistant emitted. A claim backed by a command run
seconds earlier is indistinguishable from an unfounded one.

This result is reported and should not be acted on as though it were sound. See
ISSUE-292.

### CONTRACT-14 — one applicable turn in twenty-five

Code is written through tool calls, not in turn text, so this contract is barely
measurable from a transcript at all. 100% of one turn is not evidence.

### Scope

25 turns of one session by one user on one project. Directional, not a
characterisation of the framework. The failures are citable and specific; the
percentages are small-sample.

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
