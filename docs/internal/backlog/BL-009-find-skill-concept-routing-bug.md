---
id: BL-009
title: find-skill routes "concept articulation" to wrong skill
priority: P2
status: backlog
created: 2026-05-01
---

## Summary

`/sweetclaude:find-skill` currently routes user phrases like "concept articulation" or "frame this concept" to `documents-narrative-arc`. That skill is for knowledge-graph queries on strategic claims and proof points — it does not handle concept framing.

The correct destination is `sweetclaude:concept-framing`, which is in the Plan 3 list (named planned but not yet built). Likely a leftover routing entry from when concept-framing was unbuilt and a fallback was needed.

## Impact

Low blast radius today — most users probably do not phrase requests this way. But the moment `concept-framing` lands (BL-008 candidate), the routing must move with it, or the skill will be unreachable from natural language.

## Decision needed

Pick one:
1. **Wait until `concept-framing` is built** and fix routing in the same change (preferred — bundle with BL-008 work)
2. **Remove the bad routing now** and let `find-skill` show "no match — clarify" until concept-framing exists
3. **Repoint to a better fallback** like `product-discovery` L1 (closer to concept work than narrative-arc)

## References

- File to fix: `/Users/carsonsweet/dev/sweetclaude/skills/find-skill/SKILL.md`
- Discovered during: BL-005 verification audit, specifically the strategy-concept spec analysis
- Target skill (when built): `/sweetclaude:concept-framing` (BL-008 candidate)
