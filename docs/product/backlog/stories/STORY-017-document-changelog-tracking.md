---
id: STORY-017
type: story
title: Document changelog — per-write metadata (datetime, skill, model, branch, summary)
status: new
priority: soon
effort: l
epic: null
milestone: null
sprint: null
tags: [changelog, metadata, traceability, model-evaluation, auditing]
origin: manual
created: 2026-05-14
updated: 2026-05-15
closed_date: null
---

## Description

As a developer using SweetClaude, I want every document write to append a changelog entry that records the datetime, a summary of the change, which skill made the change (or "Generic Claude Code" if no skill is active), the current git branch and commit SHA, and which Anthropic model executed the write, so that I can audit document history and later compare model performance across skills.

The model evaluation use case is first-class: the changelog will be the primary data source for assessing which model performs best at which skills.

## Acceptance Criteria

- [ ] Every skill that writes or mutates a document appends a changelog entry to that document
- [ ] Changelog entry format: `| {ISO datetime} | {summary} | {skill name or "Generic Claude Code"} | {branch}@{sha7} | {model id} |`
- [ ] Changelog section is placed at the bottom of every document under a `## Changelog` heading
- [ ] If no skill is active, the actor field is `Generic Claude Code`
- [ ] Model ID is the full Anthropic model identifier (e.g. `claude-sonnet-4-6`), not a display name
- [ ] Git branch and short SHA are resolved at write time; if not in a git repo, field is `no-vcs`
- [ ] Changelog entries are append-only — no skill ever rewrites or removes prior entries
- [ ] Documents without an existing `## Changelog` section get one created on first write
- [ ] Skills that read documents but do not mutate them do not append changelog entries

## Out of Scope

- Querying or aggregating changelog data across documents (separate story)
- Changelog entries for state files (`.sweetclaude/state/*.yaml`) — those have their own mutation tracking

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
