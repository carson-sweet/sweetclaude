# Plan: Naming Disambiguation
**Status:** planned
**Date:** 2026-05-03
**Priority:** high — UX friction, gets worse as skill count grows

---

## Problem

Four skills with overlapping names create a lookup problem for new users:

| Pair | Confusion |
|---|---|
| `product-milestones` / `project-milestones` | Both sound like "milestone tracking." The product variant is outcome-driven roadmap targets ("Exit Stealth", "Paid Pilot Live") linked to work items. The project variant is binary business goals (MS-NNN, achieved or not). |
| `product-backlog` / `project-backlog` | Both sound like "backlog management." The product variant is a deep parking lot — each item gets substantive thinking, tracks what's deferred and why. The project variant is the sprint-ready execution queue grouped by priority. |

---

## Proposed Renames

### `project-milestones` → `project-goals`

**Why:** The `project-milestones` skill tracks binary business goals — "this happened or it didn't." The word "milestone" in project management already means a delivery checkpoint, which is what `product-milestones` does. Calling business goals "goals" is both more accurate and more distinct.

**Changes:**
- `skills/project-milestones/SKILL.md` → `skills/project-goals/SKILL.md`
- Frontmatter: `name: sweetclaude:project-goals`
- `find-skill/SKILL.md`: update routing table row
- `master/SKILL.md`: update skill surfacing bullet
- `COMMANDS.md`: update section heading and command
- `docs/user-guide/skills-reference.md`: update skill name and description
- `skills/project-roadmap/SKILL.md`: anywhere it references `project-milestones` for release completion checks
- Install: copy to `~/.claude/plugins/cache/.../skills/project-goals/`
- Remove old: `~/.claude/plugins/cache/.../skills/project-milestones/`

### `product-backlog` → `product-parking-lot`

**Why:** The product-backlog skill is explicitly a parking lot — "tracks what's been parked and why." It surfaces items when they become relevant. The project-backlog is the sprint-ready execution queue. "Parking lot" is unambiguous — you'd never confuse it with an execution backlog.

**Changes:**
- `skills/product-backlog/SKILL.md` → `skills/product-parking-lot/SKILL.md`
- Frontmatter: `name: sweetclaude:product-parking-lot`
- `find-skill/SKILL.md`: update routing table row (`Backlog management` → `Parking lot / deferred ideas`)
- `master/SKILL.md`: update skill surfacing
- `COMMANDS.md`: update section
- `docs/user-guide/skills-reference.md`: update
- Anywhere `product-backlog` is cross-referenced (check: `product-sprint-plan`, `product-prd`)
- Install: copy to `~/.claude/plugins/cache/.../skills/product-parking-lot/`
- Remove old: `~/.claude/plugins/cache/.../skills/product-backlog/`

---

## What Does NOT Change

- `project-backlog` — stays. The name is accurate and distinct from `product-parking-lot`.
- `product-milestones` — stays. "Product milestone" is standard language for delivery targets.
- `product-roadmap-analysis` — stays. "Analysis" suffix makes it distinct from `project-roadmap`.

---

## Sequencing

1. Rename `project-milestones` first (lower cross-reference surface)
2. Search for all cross-references in skills/ before renaming (grep for `project-milestones` and `product-backlog`)
3. Rename `product-backlog`
4. Update routing files (find-skill, master)
5. Update docs
6. Sync to plugin cache
7. Commit

## Risk

- Any user project that invokes `/sweetclaude:project-milestones` by name in a CLAUDE.md or script will get "skill not found." Mitigation: add a one-line compatibility note to INSTALL.md and the next release changelog.
- grep search before rename to catch all cross-references.
