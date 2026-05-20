---
id: BL-005
title: Reconcile syncog skill specs against existing SweetClaude consolidations
priority: P1
status: backlog
created: 2026-05-01
---

## Summary

The inventory at `/Users/carsonsweet/dev/syncog-skills-corpus/specs/inventory.md` proposes 38 new SweetClaude skills derived from the syncog skills corpus. A verification audit found ~18 of them are duplicates or heavy overlaps of modes already embedded inside existing consolidated SweetClaude skills (`document-corpus`, `code-testing`, `product-competition`).

Acting on the inventory as-is would create duplicate skills that fork the unified state machines (e.g., `corpus-pipeline.yaml` shared by all six corpus modes) and shatter the menu-driven mode routing pattern that the existing skills depend on.

## Duplicates to mark "DO NOT BUILD"

Already exist as `$ARGUMENTS`-routed modes within `/sweetclaude:document-corpus` (828 lines):
- `corpus-status`
- `corpus-consolidate`
- `corpus-triage`
- `corpus-reconcile`
- `corpus-promote`
- `corpus-reindex`

Already exist as menu options within `/sweetclaude:code-testing`:
- `code-pr-precheck` (option 4: PR pre-check, steps 23–30)
- `code-mutation-testing` (option 2: Mutation, steps 68–99)
- `code-security-testing` (option 3: Security, plus `code-review` security mode)

Already covered by existing skill at depth:
- `product-feature-competitive` (already covered by `/sweetclaude:product-competition` L3 feature-deep analysis, lines 59–70)

## Decision needed

For each of the 10 duplicates above:
1. Mark inventory entry as "DUPLICATE — already a mode in {existing skill}"
2. Decide whether to delete or archive the spec files in `/Users/carsonsweet/dev/syncog-skills-corpus/{slug}/specs/`

## References

- Verification report: `/Users/carsonsweet/.claude/plans/delegated-forging-lerdorf.md`
- Inventory file: `/Users/carsonsweet/dev/syncog-skills-corpus/specs/inventory.md`
- Existing consolidated skill: `/Users/carsonsweet/dev/sweetclaude/skills/document-corpus/SKILL.md`
- Existing consolidated skill: `/Users/carsonsweet/dev/sweetclaude/skills/code-testing/SKILL.md`

## Connection to other backlog items

- BL-006 (stale corpus design doc) — same root issue
- BL-007 (partial-overlap taxonomy decisions) — sibling cleanup
- BL-010 (spec-writer briefing improvements) — root cause of why this happened
