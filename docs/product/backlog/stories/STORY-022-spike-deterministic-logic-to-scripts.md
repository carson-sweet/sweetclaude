---
id: STORY-022
type: story
title: Spike — move deterministic logic out of LLM skills and into scripts
status: new
priority: soon
effort: l
epic: null
milestone: null
sprint: null
tags: [spike, architecture, scripts, skills, determinism, reliability, llm-surface]
origin: manual
created: 2026-05-14
updated: 2026-05-15
closed_date: null
---

## Description

As a developer using SweetClaude, I want to identify and move all deterministic logic out of LLM-driven skills and into Python/shell scripts, so that non-deterministic LLM behavior is only involved where judgment is genuinely required and every operation that can be deterministic is.

The current system mixes deterministic operations (file parsing, status normalization, index updates, counter management, path resolution) with LLM orchestration inside the same skill. This invites subtle bugs: the LLM may interpret instructions inconsistently, improvise steps that weren't intended, or produce outputs that vary across sessions. The migration script (`migrate-v3-to-v4.py`) and migration runner (`runner.py`) are the right model — pure Python, testable, reproducible. More of the system should look like them.

## Spike Questions

1. **Audit**: Which skill operations are purely mechanical (no judgment required)? Candidates include: index rebuilds, counter increments, status transitions, file moves, frontmatter patching, drift detection, hook reconciliation, version comparisons.
2. **LLM boundary**: What is the minimum surface that genuinely requires LLM judgment? Likely: natural-language interpretation, synthesis, writing prose, making trade-off decisions.
3. **Interface pattern**: What is the right interface between scripts and skills? (Skills call scripts via Bash, parse JSON output, act on results — as migrate already does.)
4. **Test coverage**: Deterministic scripts can be unit-tested. Which of the currently untestable skill behaviors would become testable after extraction?
5. **Migration complexity**: How much existing skill logic can be extracted without breaking the user-facing interface?

## Acceptance Criteria

- [ ] Audit complete: every skill annotated with a breakdown of deterministic vs. judgment-required operations
- [ ] At least three deterministic operations extracted from skills into scripts with unit tests
- [ ] No user-facing behavior changes — skills still own the interface, scripts own the computation
- [ ] Decision recorded: scope and priority of full extraction effort
- [ ] If proceeding: follow-on stories created per skill or per operation class

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
