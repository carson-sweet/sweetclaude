---
id: BUG-009
type: bug
title: Epic completion criteria only in body text — cache renders Criteria 0/0
status: new
priority: now
effort: s
epic: null
epic_sequence: null
milestone: null
sprint: null
tags: [cache, big-picture, roadmap, epic]
origin: manual
created: 2026-05-19
updated: 2026-05-19
closed_date: null
---

## Description

The roadmap cache (`cache.py`) reads epic completion criteria from frontmatter fields `completion_criteria` (list of strings) and `completion_criteria_done` (list of 0-indexed positions). When an epic defines success criteria only in the markdown body (as a numbered list under "Epic-Level Success Criteria"), the cache sees no criteria and reports `criteria_done: 0, criteria_total: 0`.

`/sweetclaude:big-picture` renders this as `Criteria: 0/0` on the epic line, making it look like zero progress has been made regardless of how many stories are complete.

## Reproduction

1. Create an epic with success criteria in the markdown body but no `completion_criteria` in frontmatter
2. Complete stories that satisfy some criteria
3. Run `/sweetclaude:big-picture`
4. Epic line shows `Criteria: 0/0`

## User-visible consequence

After completing 3 of 7 stories on EP-010 (several hours of work), the big-picture dashboard showed `Criteria: 0/0` — making it appear that nothing had been accomplished. This was not caught until the user noticed and escalated.

## Root cause

The epic creation workflow (caucus output for EP-010) placed success criteria in the markdown body as a numbered list. The cache parser only reads structured frontmatter. There is no validation or warning when an epic has body criteria but no frontmatter criteria.

## Fix applied (EP-010)

Added `completion_criteria` and `completion_criteria_done` fields to EP-010 frontmatter. Cache now correctly reports `Criteria: 4/10`.

## Proposed systemic fix

Two options (not mutually exclusive):

1. **Validation at epic creation.** When an epic is created or imported, warn if the body contains a numbered list under a "criteria" heading but the frontmatter has no `completion_criteria` field.

2. **Cache fallback parser.** Have `cache.py` attempt to extract criteria from the markdown body if frontmatter `completion_criteria` is empty. Parse numbered list items under headings matching `*criteria*` or `*success*`.

Option 1 is simpler and prevents the problem at the source. Option 2 is more resilient but adds parsing complexity.

## Acceptance criteria

- [ ] All existing epics have `completion_criteria` in frontmatter if they have body-text criteria
- [ ] Epic creation workflow produces `completion_criteria` in frontmatter
- [ ] A warning is surfaced (lint, health check, or creation-time) when body criteria exist without frontmatter criteria
