---
id: CHORE-008
type: chore
title: v4 plan documentation cleanup — STORY-040 vs STORY-018 + /sweetclaude:update v4 behavior
status: new
priority: later
effort: s
epic: null
milestone: null
sprint: null
tags: [docs, v4-plan, hygiene]
origin: manual
created: 2026-05-13
updated: 2026-05-13
closed_date: null
---

## Description

Two documentation gaps in the v4 plan documents that confused the May 11 assessment but don't affect user-visible behavior.

**Origin:** May 11 v4 assessment items E1 + E2.

## E1: STORY-040 vs STORY-018 conflation

The v4 plan document describes two different `installed_version: 4.0.0` writes as if they're the same operation:

- **STORY-040 ("version bump"):** writes 4.0.0 to THIS repo's `package.json` and `.claude-plugin/plugin.json` — dev-side release engineering.
- **STORY-018 (migrate skill Step 8):** writes 4.0.0 to the USER's `.sweetclaude/state/sweetclaude.yaml` — runtime project state mutation.

These are conceptually distinct (release engineering vs migration of a user's project) but the plan text reads as if they're the same. Reader-confusing.

**Fix:** Update the plan document to label each story with its scope (dev-side / runtime) and clarify they are not duplicates.

## E2: /sweetclaude:update's v4 behavior underspecified

The plan never says what writes `installed_plugins.json` when a v4 plugin update happens, where the v4 plugin files come from, or how the update mechanism integrates with Claude Code's plugin system. This gap is what allowed the May 11 A2 finding to go undetected (and ultimately turned out to be a non-issue, but only after the v3.68.x patches surfaced enough evidence on the dev machine to disprove the claim).

**Fix:** Update the plan document (and possibly `skills/update/SKILL.md` Step 3c) to clearly specify:
- Where v4 plugin files come from (marketplace vs source repo for `/sweetclaude:update`)
- What writes `installed_plugins.json` (Claude Code's installer vs SweetClaude's update skill)
- The expected end-state of installed_plugins.json after a v3→v4 update

## Severity

`later` priority. These are documentation hygiene fixes, not bugs. No code change needed; just plan/spec text edits.

## Acceptance Criteria

- [ ] v4 plan document (likely `docs/plans/v4-epics-stories-2026-05-10.md` or successor) labels STORY-040 as "dev-side release engineering" and STORY-018 as "runtime project state"
- [ ] Update skill documentation describes the v3→v4 plugin file movement explicitly

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
