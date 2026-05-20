---
closed_date: '2026-05-15'
created: 2026-05-15
effort: m
epic: null
id: STORY-023
milestone: null
origin: manual
priority: soon
sprint: null
status: done
tags:
- workflow
- closeout
- prs
- branches
- schema
- go
- deploy-ship
- automation
title: Story closeout — automatic PR closure, branch deletion, and done/ promotion
type: story
updated: 2026-05-15
---

## Description

As a developer using SweetClaude, I want the framework to automatically close the story's tracked PRs, delete the branch, and move the story file to `done/` when a story ships — so that closing a story is a single action with no loose ends, and no skill stops to ask me "what's next?" when the answer is obvious.

**Two problems this solves:**

1. **No PR/branch tracking per story.** The story schema has no `prs` field. When a story closes, there is no authoritative record of which PRs or branches belong to it. Cleanup is manual and routinely skipped, producing stale open PRs and dead branches.

2. **Skills drop the user at closeout.** After SHIP, `go` and `deploy-ship` surface a "run `/sweetclaude:go` to pick up the next item" prompt and stop. The closeout actions — close PR, delete branch, move story file to `done/`, update status — are left entirely to the user. The framework has enough information to do all of them without asking.

## Acceptance Criteria

### Schema

- [ ] Story frontmatter gains a `prs` field: a list of objects `{number: int, branch: str, title: str, opened_at: date}`, defaulting to `[]`
- [ ] When a PR is opened for a story (detected by `gh pr create` output in context, or via explicit `sweetclaude:go` tracking), the PR number and branch are written to the story's `prs` field
- [ ] The v4 story schema doc (`docs/internal/v4-story-schema.md`) is updated to include `prs`

### Closeout automation (fires at end of SHIP phase)

- [ ] After smoke test passes (or after PR merge for non-deployment stories), the skill runs closeout automatically — no prompt, no "what's next?"
- [ ] Closeout steps, in order:
  1. For each PR in `prs`: if open, close it with `gh pr close {N} --comment "Closed as part of {STORY-ID} closeout."` — skip if already merged or closed
  2. For each branch in `prs`: if the branch exists locally and is fully merged, delete it with `git branch -d`; if remote exists, delete with `git push origin --delete` — skip if branch has unmerged commits
  3. Move the story file from its current directory to the `done/` subdirectory
  4. Update story frontmatter: `status: done`, `closed_date: {today}`
  5. Update `INDEX.md`: remove the story row from the active table, bump nothing (counters don't change on close)
  6. Update `phase.yaml`: clear `active_work_item`
- [ ] Each step is reported inline as it completes (`✓ PR #57 closed`, `✓ branch feat/foo deleted`, etc.)
- [ ] If any step fails (e.g. branch has unmerged commits), report the failure and continue with remaining steps — do not abort the whole closeout
- [ ] After closeout: say "Done. {STORY-ID} — {title} — closed." and stop. No "what would you like to do next?" No menu. No prompt.

### Sub-PR detection

- [ ] Before closeout runs, scan for open PRs whose branches are contained in the story's merged branch (same check as the pre-ship checklist item added to `deploy-ship`): `git merge-base --is-ancestor`
- [ ] Any detected sub-PRs not already in `prs` are closed with the same superseded comment and reported

## Out of Scope

- Reopening a closed story (separate workflow)
- Bulk closeout of multiple stories
- Automatically detecting PR open events outside of a `sweetclaude:go` session (passive tracking)

## Open Questions

- Should `prs` be frontmatter (machine-queryable) or a `## PRs` body section (richer, but harder to parse)? Frontmatter list is simpler and consistent with the existing schema approach.
- For non-deployment stories (library/framework projects where "ship" = merge to main), should closeout fire immediately after the PR merge is confirmed, or wait for an explicit signal?

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
