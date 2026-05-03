# Caucus Checkpoint — /sweetclaude unified front door (Final)
**Date:** 2026-05-03
**Status:** COMPLETE — 3 turns, 10 experts (5 users + 5 developers)

## 14 Mandatory Changes Before Implementation

1. Explicit routing override: `/sweetclaude use [workflow]` bypasses classifier
2. 5th feature state: `deferred` with `defer_until` timestamp
3. 24h checks → `session-preflight.sh` SessionStart hook (not inline skill logic)
4. `check_error` field for silent hook failures
5. `migration_status: in_progress|complete|failed` field
6. Migration archives old files (does not delete)
7. Parse failure → `fix-sweetclaude` with human-readable message
8. Schema version check at top of decision tree
9. Work history capped at 10 items (not 20)
10. Sub-skill architecture: 5 internal sub-skills, thin orchestrator
11. Offer copy is human-language — no schema field names in output
12. First-run experience described in design doc
13. `learnings` visible/editable via `/sweetclaude:help`
14. `hook_last_ran` timestamp so skill detects stale hook

## Future Work (v2)
- `--advanced` mode showing top-N skill list
- `session.default_action` remembering last answer
- Fine-grained deferral durations
- Schema checksum for corruption diagnosis

## Dissents
- Marcus: `--advanced` should be v1, not v2
- Priya: ship monolith first, extract sub-skills after real-use seams emerge

## Full review: scratch/caucus_review_unified_front_door.md
