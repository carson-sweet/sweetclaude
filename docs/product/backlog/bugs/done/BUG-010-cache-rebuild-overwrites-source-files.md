---
id: BUG-010
type: bug
title: "Cache rebuild modifies source markdown files"
status: done
priority: now
epic: null
epic_sequence: null
created: 2026-05-19
updated: 2026-05-19
closed_date: 2026-05-19
---

## Summary

During the 4.0.9-beta release process, `python3 cache.py --project-dir . --rebuild` silently modified two source files:

- `docs/product/roadmap/epics/EP-009-workflow-orchestration-runbooks.md` — status changed from `proposed` to `done`, YAML arrays reformatted from inline to block, quotes added to dates
- `docs/product/roadmap/releases/REL-003-v4.1-workflow-orchestration.md` — status changed from `planned` to `released`, quote style changed, dates quoted

The cache is supposed to be read-only over source files. If it round-trips YAML (reads frontmatter, writes it back), any parse/serialize asymmetry corrupts the source of truth.

## Severity

Critical. Silent data corruption of roadmap state. Status fields changed without user intent. Caught only because the changes appeared in an unrelated `git diff`.

## Reproduction

1. Ensure EP-009 has `status: proposed` and REL-003 has `status: planned`
2. Run `python3 cache.py --project-dir . --rebuild`
3. Run `git diff` — observe status and formatting changes in the source files

## Expected behavior

`cache.py --rebuild` reads markdown files and populates the SQLite cache. It must never write to the source markdown files.

## Discovered

2026-05-19 during release/4.0.9-beta assembly. Changes were reverted with `git checkout --`.

## Fix

Fixed in commit `4fedad1` — `rollup()` and `update_frontmatter()` were removed from `scripts/cache.py`. The installed version diverged from the repo and had gained these write-back functions. The fix ported all legitimate additions (query_summary, query_epics, atomic .tmp write, completion_criteria_done support, UNIQUE tag constraint) while excluding the write-back functions entirely.

Verified: running `--rebuild` against the current codebase leaves EP-009 (status: proposed) and REL-003 (status: planned) unchanged.
