---
name: sweetclaude-product-backlog
description: "Manage deferred work. Add, review, prioritize, or groom backlog items. Tracks what's been parked and why, surfaces items when they become relevant. Wraps backlog-management with SweetClaude context."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Backlog Management

Manage backlog: $ARGUMENTS

## SweetClaude Context

- Backlog items live in `docs/backlog/` (technical items) or `strategy/` (strategic items)
- Non-technical items (product ideas, feature concepts, strategic initiatives) route to `strategy/`, not `docs/backlog/`
- Read existing backlog index if present: `docs/backlog/BACKLOG-INDEX.md`
- When adding items, classify: is this technical debt, a feature request, a spike, or a strategic initiative?

## Execute

Invoke the `backlog-management` skill and follow its workflow. Apply the classification rules above to ensure items land in the right place.
