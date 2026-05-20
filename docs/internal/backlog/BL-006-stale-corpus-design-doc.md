---
id: BL-006
title: Update stale corpus management design doc
priority: P2
status: done
completed: 2026-05-05
created: 2026-05-01
---

## Summary

`docs/corpus-management-design-v2-2026-04-15.md` claims separate corpus skills exist that were never built. The actual implementation consolidated all six corpus management modes into a single skill (`document-corpus`, 828 lines) with `$ARGUMENTS`-based mode routing.

The doc misled an inventory audit: a spec-writer agent reading the design doc believed `corpus-consolidate` and `corpus-triage` existed as standalone skills, when in fact those file paths point to non-existent files.

## Specific staleness

Doc claims (lines 174, 186):
- "Status: Implemented (skills/corpus-consolidate/SKILL.md)" — file does not exist
- "Status: Implemented (skills/corpus-triage/SKILL.md)" — file does not exist
- Consolidate, Triage, Reconcile, Promote, Reindex, Status all listed as separate skills with implementation order

Actual state (verified 2026-05-01):
- All 6 modes live inside `skills/document-corpus/SKILL.md`
- Mode routing at line 37: *"If `$ARGUMENTS` was passed (e.g. `/sweetclaude:document-corpus triage`), skip the menu and route directly."*
- `corpus-pipeline.yaml` is shared state across all 6 modes — splitting them would fork this state machine

## Decision needed

Pick one:
1. **Update the doc** to reflect that corpus management was consolidated into one skill with mode routing (not six separate skills). Document the rationale for the consolidation choice.
2. **Revisit the consolidation decision.** If the original design intent (separate skills) was correct, plan an extraction migration that preserves shared state.

## References

- Doc to update: `/Users/carsonsweet/dev/sweetclaude/docs/corpus-management-design-v2-2026-04-15.md`
- Actual implementation: `/Users/carsonsweet/dev/sweetclaude/skills/document-corpus/SKILL.md`
- Discovered during: BL-005 verification audit
