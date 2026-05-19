---
id: BL-003
title: Compare SweetClaude planning and review vs. Anthropic ultra plan / ultra review
priority: P2
created: 2026-04-28
---

## Description

SweetClaude has its own planning pipeline (john-wick mode) and code review skill. Anthropic ships `ultraplan` and `ultrareview` in Claude Code. Compare the two approaches across quality, coverage, and workflow fit.

## What to compare

**Planning:**
- SweetClaude john-wick mode: full SDLC pipeline from discovery artifacts → PRD → design → TDD → implementation → PR
- Anthropic ultraplan: generates implementation plans from a task description

Dimensions: artifact quality, missed requirements, over-engineering, user effort required, multi-session continuity.

**Review:**
- SweetClaude `/sweetclaude:code-review`: code + security + compliance, reads compliance-context.yaml, structured output
- Anthropic `/ultrareview`: multi-agent cloud review, separate billing, async

Dimensions: finding overlap, unique findings per tool, false positive rate, latency, cost, actionability of findings.

## Motivation

The first head-to-head comparison opportunity was the john-wick-mode branch — ultrareview was invoked but returned `/code/disabled` (feature not enabled). Once access is available, run both on the same branch and document differences.

## Acceptance criteria

- [ ] Both tools run on the same branch/PR
- [ ] Findings catalogued in a comparison table (unique to SweetClaude, unique to ultrareview, overlap)
- [ ] Qualitative notes: what does each tool catch that the other misses?
- [ ] Recommendation: where does SweetClaude add value beyond what Anthropic ships natively?
