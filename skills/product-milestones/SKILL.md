---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Manage roadmap targets (milestones) that span strategy and product work."
category: product
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Milestones

Manage milestones: $ARGUMENTS

A milestone is a **roadmap target** — a named strategic outcome the project is driving toward. Not a release, not a sprint, not an epic. Examples: "Exit Stealth", "Paid Pilot Live", "Series A Readiness", "MVP Shipped".

## State Check

Read `.sweetclaude/state/skills.yaml`.

**Schema migration:** If `skills.yaml` exists with `schema_version: 1`, migrate this skill's entry before proceeding:
- `enabled: true` → `status: active`, `last_changed_at: {onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at` set → `status: paused`, `last_changed_at: {offboarded_at or onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at: ~` → `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
Drop `onboarded_at`/`offboarded_at`. Set `schema_version: 2`. Write atomically (see write protocol below).

**Dependency check:**
Read `~/.claude/config/sweetclaude/skills-registry.yaml`. Find `skills.product-milestones.dependencies`. This skill has no dependencies — skip.

**If `skills.yaml` does not exist, OR exists but has no entry for `skills.product-milestones`:**
- Check whether `{base_path}/milestones/MILESTONES-INDEX.md` exists
- If yes: write entry with `status: active`, `last_changed_at: {today}`, `last_changed_by: migrated`
- If no: write entry with `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
- Use write protocol below.

**If `skills.yaml` exists and has an entry for `skills.product-milestones`:**
- `status: active` → proceed normally
- `status: paused` AND `$ARGUMENTS` not in `[onboard, offboard, pause]`:
  > "Milestones are currently paused. Resume? [yes/no]"
  If yes: write `status: active`, `last_changed_at: {today}`, `last_changed_by: resume` (using write protocol). Proceed normally.
  If no: stop.
- `status: uninitialized` AND `$ARGUMENTS` not in `[onboard, offboard, pause]`:
  → Run lightweight first-invocation flow (see below)
- `$ARGUMENTS` is `pause` → run pause operation
- `$ARGUMENTS` is `offboard` and `status: uninitialized`: "Milestones aren't set up yet. Nothing to offboard." Stop.
- `$ARGUMENTS` is `pause` and `status: paused`: "Already paused." Stop.
- `$ARGUMENTS` is `pause` and `status: uninitialized`: "Not set up yet. Nothing to pause." Stop.

**Write protocol — all skills.yaml writes must follow this:**
1. Read and parse current `.sweetclaude/state/skills.yaml` (or start from default v2 structure if absent)
2. Merge your entry — do NOT remove or overwrite other skills' entries
3. Write merged content to `.sweetclaude/state/.skills.yaml.tmp`
4. Run: `mv .sweetclaude/state/.skills.yaml.tmp .sweetclaude/state/skills.yaml`

**State writes (use write protocol for all):**
- End of lightweight first-invocation (success): `status: active`, `last_changed_at: {today}`, `last_changed_by: first-invocation`
- End of onboard (success): `status: active`, `last_changed_at: {today}`, `last_changed_by: onboard`
- Pause operation: `status: paused`, `last_changed_at: {today}`, `last_changed_by: pause`
- Resume: `status: active`, `last_changed_at: {today}`, `last_changed_by: resume`
- End of offboard: `status: uninitialized`, `last_changed_at: {today}`, `last_changed_by: offboard`

---

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:setup` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.product.base_path`. This is the base directory for all product artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. if base is `.sweetclaude/product`, milestones go to `.sweetclaude/product/milestones/MS-001.md`).

4. Write artifacts to those paths.

## Routing

Classify the invocation by the first word of `$ARGUMENTS`:

| First word | Operation |
|------------|-----------|
| `onboard` | First-time setup — scan for existing data and migrate |
| `offboard` | Export data and optionally remove SweetClaude artifacts |
| `add` | Create a new milestone |
| `review` | List milestones grouped by Now / Next / Later |
| `link <item> <MS-XXX>` | Attach a product work item to a milestone |
| `status <MS-XXX>` | Detail view of one milestone |
| `blockers <MS-XXX>` | List what's unfinished on a milestone |
| `complete <MS-XXX>` | Mark a milestone achieved + chain follow-ups |
| `unassigned` | Find work items with no milestone |

If `$ARGUMENTS` is empty or doesn't match, default to `review`.

## Storage

```
{base_path}/milestones/
  MILESTONES-INDEX.md       Master index (one row per milestone)
  MS-001-short-name.md      One file per milestone
  MS-002-short-name.md
  ...
```

- IDs are `MS-XXX`. Read the index, find the highest number, increment by 1.
- IDs are permanent. Never renumber. Gaps are fine.

## Milestone file template

```markdown
# MS-XXX: Title

**Status:** proposed | active | achieved | dropped | superseded
**Sequence:** ~
**Owner:** [name/role]
**Depends on:** (other MS-XXX refs, if any)

## Outcome
One paragraph describing what this milestone represents and why it matters.

## Measuring success
- [ ] Criterion 1 (each evaluable as true/false)
- [ ] Criterion 2
- [ ] Criterion linked to artifact: `strategy/narrative-arc.md` finalized

## Non-goals
- What this milestone is explicitly NOT
- Second explicit exclusion

## Contributing work items
- US-012 — Landing page redesign
- BL-007 — Analytics tracking

## Notes
Free-form log of decisions, scope changes, blockers encountered.

---

## Changelog
| Version | Date       | Change summary       |
|---------|------------|----------------------|
| 1.0     | YYYY-MM-DD | Initial draft        |
```

## Status taxonomy

| Status       | Meaning                                                                  |
|--------------|--------------------------------------------------------------------------|
| `proposed`   | Drafted, not yet committed. Appears in "Later".                          |
| `active`     | Currently being driven. Appears in "Now". Can be multiple.               |
| `achieved`   | All criteria met; user confirmed. Terminal state.                        |
| `dropped`    | Abandoned with rationale in Notes. Terminal state.                       |
| `superseded` | Replaced by a newer milestone. Links to successor in Notes. Terminal.    |

## Operations
Routes by `$ARGUMENTS` first word (see [Routing](#routing) above) into one of 11 sub-operations defined in [operations.md](operations.md):

| Sub-op | Purpose |
|---|---|
| `pause` | Set status to paused — leave files intact |
| `offboard` | Export to GitHub / markdown / CSV, then optionally delete |
| Lightweight first-invocation | Auto-runs when status = uninitialized; creates index, optional GitHub import |
| `onboard` | Explicit first-time setup; scans for existing milestone/roadmap data |
| `add` | Create a new MS-XXX milestone |
| `review` | List milestones grouped Now / Later (and Achieved / Dropped if `--all`) |
| `link <item> <MS-XXX>` | Bidirectional attach a US/BL work item to a milestone |
| `status <MS-XXX>` | Detail view: criteria, contributing work items, recent notes |
| `blockers <MS-XXX>` | List unmet criteria, open work items, unmet dependencies |
| `complete <MS-XXX>` | Mark achieved, prompt for follow-ups (delegated to product-parking-lot) |
| `unassigned` | Hygiene scan — work items without a Milestone header |

Read [operations.md](operations.md) and execute the matching sub-section.

## Integration protocol

The milestones skill is the single source of truth for milestone data. Other skills should follow this protocol rather than writing their own milestone logic:

- **`sweetclaude:product/user-story`**: after creating a story, prompt "Assign this story to a milestone? [list of active + proposed milestones, or 'none / later']". On user selection, invoke `sweetclaude:product-milestones link <US-XXX> <MS-XXX>`.
- **`sweetclaude:product/sprint-plan`**: after stories are chosen for a sprint, read each story's `**Milestone:**` header. Report which milestones the sprint advances and count unassigned stories. If > 50% of sprint stories are unassigned, flag it as a scope concern.
- **`sweetclaude:status`**: in the orient view, include an "Active milestones" section showing each `active` milestone with its criterion-met count.

Strategy skills (`strategy/narrative-arc`, `product/market-messaging`, etc.) are **not modified**. Milestones reference their canonical artifacts by path as Measuring-success criteria; the milestones skill reads those files directly.

The `product/backlog` skill is not modified, but is invoked indirectly by the `complete` operation's follow-up chain.

## Rules / Invariants

- Every milestone has its own file under `{base_path}/milestones/`. The index is an index only.
- `MS-XXX` IDs are permanent. Never renumber. Gaps are fine.
- Bidirectional links must stay consistent. `link` updates both sides. Any skill that adds or removes a work item from a milestone must do the same.
- Terminal states (`achieved`, `dropped`, `superseded`) are never edited back to non-terminal. To re-activate a deprecated goal, create a new milestone that references the old one in its Notes.
- No derived state file. Progress is recomputed on every read by scanning files.
- Non-goals are not optional. Every milestone must have at least one explicit exclusion under `## Non-goals`.
- No time estimates. Status taxonomy and Now/Next/Later bucketing replace date-based roadmapping.

## Open items (tracked in design spec)

These are documented in `docs/milestones-skill-design-v1-2026-04-20.md` as open for a follow-up iteration:

- Canonical-artifact finalization convention (front-matter field vs path vs registry).
- Next-bucket promotion mechanism for `proposed` milestones.
- Bulk-link operation (defer until single-item link proves tedious).
- Whether to archive `achieved` milestones to `docs/milestones/archive/`.
