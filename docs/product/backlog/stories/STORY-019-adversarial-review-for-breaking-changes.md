---
id: STORY-019
type: story
title: Adversarial review gate for breaking changes — breaking flag, mandatory code-reviewer
  pass
status: new
priority: sooner
effort: l
epic: EP-001
sprint: null
tags:
- quality
- tdd
- code-review
- caucus
- breaking-changes
- adversarial
- safety
origin: manual
created: 2026-05-14
updated: 2026-05-15
closed_date: null
epic_sequence: 4
---

## Description

As a developer using SweetClaude, I want every story to carry a `breaking: true | false` attribute and for that flag to trigger mandatory adversarial review discipline — across TDD level selection, QA caucus composition, code review, and pre-merge gates — so that breaking changes cannot slip through with only author-perspective review.

**Problem this solves:** BUG-007 (`AttributeError: 'str' object has no attribute 'get'`) shipped because both the LLM that wrote the code and the LLM that wrote the tests had the same blind spot. The test suite looked comprehensive by count but was not adversarial by design — it optimized for happy-path migration, not failure-branch coverage. Any function that parses external input needs at least one test per failure branch. The root fix is a standing adversarial reviewer pass that is structurally separated from the author context and explicitly tasked with finding what the author wasn't thinking about.

## Acceptance Criteria

- [ ] Story frontmatter schema includes a `breaking: true | false | null` field; `null` means unassessed (treated as `false` unless the story assessment sets it — see STORY-020)
- [ ] When `breaking: true`, TDD level is forced to Level 2 minimum (Level 3 recommended); Level 0/1 requires explicit override with logged rationale
- [ ] When `breaking: true`, a `code-reviewer` subagent pass is mandatory before IMPLEMENT closes — it runs in a separate context from the implementer with an adversarial prompt ("find what the author wasn't thinking about")
- [ ] When `breaking: true`, QA caucus includes the `code-reviewer` agent in addition to the standard three-angle caucus
- [ ] For any function or method that parses external input (user data, file content, API responses), at least one test per failure branch is required — enforced at VERIFY phase
- [ ] The mandatory adversarial pass produces a named finding report; IMPLEMENT cannot close if findings are unresolved or unacknowledged
- [ ] `breaking: true` stories are surfaced distinctly in backlog views and sprint planning

## Out of Scope

- Automatic detection of whether a change is breaking (that is part of STORY-020 assessment)
- Changes to existing non-breaking story workflows

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
