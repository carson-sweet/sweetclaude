---
id: BUG-001
type: bug
title: Corpus setup must run end-to-end before next skill setup begins
status: done
priority: sooner
effort: m
epic: EP-039
milestone: null
sprint: null
tags: [onboarding, corpus, orchestration]
origin: manual
created: 2026-05-12
updated: 2026-05-15
closed_date: 2026-05-15
---

## Description

When the corpus skill is being set up during bootstrap/onboarding, the entire corpus pipeline (raw → triage → reconcile → promote) must complete before the orchestrator moves on to set up another skill. Currently the orchestrator stops at the first step (raw inbox population) and immediately moves to the next skill, leaving the corpus in a half-onboarded state.

This may apply generically to any multi-step skill setup — corpus is just the observed trigger. The fix should either (a) serialize multi-step skill setups in the orchestrator, or (b) flag mid-pipeline skills as "not done onboarding" so the orchestrator returns to them before claiming setup is complete.

## Steps to Reproduce

1. Run bootstrap with multiple newly-enabled features that require onboarding, including corpus and behavioral-regression.
2. Watch the orchestrator process the corpus skill first.

## Expected / Actual

**Expected:** Corpus setup runs to completion — raw files copied, triage classifies them, reconciliation produces canonical drafts, promote finalizes the canonical set. Only then does the orchestrator move to the next skill (behavioral-regression).

**Actual:** Corpus setup completes only step 1 (copy 123 files to `corpus/raw/inbox/`, commit), prints "Next: run `/sweetclaude:corpus-triage`...", then immediately moves to behavioral-regression setup. Triage is never invoked. The corpus skill is left in a partially-onboarded state and the user has no clear signal that they need to come back to it.

Verbatim transcript fragment from the observed incident:

```
⏺ Done. 123 files copied to corpus/raw/inbox/, committed. Next: run /sweetclaude:corpus-triage
  to classify these inbox files before they can be promoted to canonical.

  Now continuing with the second newly-enabled feature — behavioral regression:
```

## Acceptance Criteria

- [x] Bootstrap orchestrator either completes the entire multi-step setup for a skill before moving to the next, OR explicitly defers the remaining steps and surfaces a clear "X skill onboarding paused at step N — resume with /sweetclaude:X" message before moving on.
- [x] Corpus setup specifically: raw → triage → reconcile → promote runs to completion within a single onboarding session (or the user is explicitly asked whether to continue or pause between major stages).
- [x] The orchestrator's "moving to next skill" message acknowledges if a previous skill setup is incomplete and why.
- [ ] Regression test: a fixture with corpus + behavioral-regression both newly enabled exercises the orchestrator and asserts that corpus is either fully onboarded or explicitly paused with a user-visible message.

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
