---
id: CHORE-014
type: chore
title: "Reconcile skills-reference.md skill count with actual skills/ directory"
status: new
priority: sooner
effort: s
tags: [skills, documentation, skills-reference, count-drift]
created: 2026-05-19
updated: 2026-05-19
---

# Reconcile skills-reference.md skill count with actual skills/ directory

## Context

As of 2026-05-19, `ls skills/` returns 109 directories but `docs/user-guide/skills-reference.md` reports "All 103 skills." Six skills are unaccounted for. STORY-304 bumped the documented count from 103→104 without reconciling the gap, per backlog decision (blast-radius-304.md OQ4).

## Work

1. Diff `ls skills/` against all skill entries in `docs/user-guide/skills-reference.md`
2. For skills in `skills/` but not in the reference: add entries or confirm they are intentionally unlisted (internal-only, deprecated, etc.)
3. For skills in the reference but not in `skills/`: remove stale entries or restore missing directories
4. Update the global count heading at line 6 and each domain section heading to match reality
5. Verify `ls skills/ | wc -l` matches the heading after changes

## Acceptance criteria

- `docs/user-guide/skills-reference.md` global count matches `ls skills/ | wc -l`
- Every domain section heading count matches the number of skills listed under it
- No skill directory exists without a corresponding reference entry (or a documented reason for omission)
