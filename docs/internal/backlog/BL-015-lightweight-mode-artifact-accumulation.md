# BL-015: Lightweight mode artifact accumulation

**Priority:** P2
**Depends on:** none
**Created:** 2026-05-06

## Summary

In lightweight mode, SweetClaude currently produces no structured artifacts — the `.sweetclaude/` tree stays sparse (typically just `sweetclaude.yaml`). This means that when a user wants to uplevel from lightweight to a more structured operating mode, they have to catch up on all the artifacts those phases would have produced (product brief, architecture doc, decision log, etc.) in a separate session.

The design gap: lightweight mode could quietly accumulate lightweight versions of key artifacts as conversations progress — a one-paragraph brief, a quick architecture note, a tentative data model — without requiring the user to run formal phase skills. These thin artifacts would give SweetClaude a foundation to build on if the user later decides to uplevel, making the transition cheaper and less disruptive.

## Problem

- User vibe-codes a prototype over several sessions
- Decides they want to take it to production and uplevel to Structured mode
- SweetClaude has no artifacts to work from — no brief, no architecture doc, no decision log
- User must run through Discover → Define → Design phases from scratch, even though much of that thinking already happened informally in conversation

## Proposed Approach

When in lightweight mode, SweetClaude should optionally (or automatically) maintain thin versions of key artifacts:

- **Mini brief** — 3–5 sentences: what it is, who it's for, what it's not
- **Architecture sketch** — stack, key components, any notable decisions made
- **Decision log entries** — any significant technical or product choices made in conversation
- **Open questions** — things that came up but weren't resolved

These would live in `.sweetclaude/` like normal artifacts but be clearly marked as lightweight / informal. When the user uplevels, the formal phase skills would flesh them out rather than starting from nothing.

## Open Questions

- Should this be automatic (always accumulate in background) or opt-in?
- How does SweetClaude know when a decision was made informally in conversation vs. just discussed?
- Should the mini artifacts be presented to the user for review, or silently maintained?

## Why P2

Not blocking for current users — lightweight mode works fine as-is. But this is a meaningful UX improvement for the common "prototype → production" trajectory and would make SweetClaude meaningfully more useful for projects that start exploratory and grow.
