# Caucus Checkpoint — user-invokable skills decision (Final)
**Date:** 2026-05-03
**Topic:** Which SweetClaude skills should be user-invokable?
**Status:** COMPLETE — 3 turns, 5 experts

## 7 CLEAR NOs (apply `user-invokable: false`)
- `code-tdd` — internal, stated explicitly in own description
- `john-wick-checkin` — internal subagent
- `master` — phase router, not a user command
- `documents-update-docs` — always downstream of a change; no cold entry use case
- `design-solutioning-gate` — workflow-routed gate; context-dependent
- `guardian-on` — primarily offered via conversation (4-1; Marcus dissents)
- `guardian-off` — same (4-1; Marcus dissents)

## All others: keep user-invokable

## Key Decisions
- `go` and `next-steps` BOTH stay — different behaviors (autonomous vs. step-through)
- `design-change-impact-analysis` stays YES — "what breaks if I change X" is a real standalone verb
- `john-wick` stays visible — powerful but intentional
- `guardian-on/off` are NO per majority — conversational offer is the primary path

## Follow-on Work
- Monitor `next-steps` vs `go` usage — may be redundant in practice
- Taxonomy debt: solutioning-gate, change-impact-analysis, update-docs should eventually be absorbed into parent skills as modes/flags

## Minority Report
Marcus Wellstone dissents on guardian-on/off: hiding creates fragile dependency on conversational offer UX.
