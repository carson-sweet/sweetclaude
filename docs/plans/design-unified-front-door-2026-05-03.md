# Design: /sweetclaude Unified Front Door
**Version:** 1.0  
**Date:** 2026-05-03  
**Status:** Approved — ready for implementation planning  
**Reviewed by:** 5-user + 5-developer expert caucus (see scratch/caucus_review_unified_front_door.md)

---

## What This Is

Replace the 73-skill slash-command picker with a single natural-language entry point. Users type `/sweetclaude` and describe what they want in plain English. The skill reads one file, makes one decision, and routes internally. Power users retain explicit routing. New users never see a skill name.

---

## Visible Skills After This Change

| Skill | Purpose |
|-------|---------|
| `/sweetclaude [optional text]` | Everything — setup, routing, health, status, feature offers |
| `/sweetclaude:help` | Progressive onboarding chat — explains free-language usage, setup, features, modes |

All other skills become `user-invocable: false`. They remain callable by internal routing but never appear in the slash-command picker.

---

## `sweetclaude.yaml` — Single Source of Truth

**Location:** `.sweetclaude/state/sweetclaude.yaml`  
**Replaces:** `phase.yaml` + `skills.yaml`  
**Principle:** One read per invocation. Zero additional file reads for health check or routing decisions.

```yaml
schema_version: 1

project:
  name: ""
  type: existing-code          # new | existing-code
  version_stage: BETA          # IDEA | ALPHA | BETA | GA
  safety_snapshot: ""

framework:
  installed_version: '2.40.0'
  setup_complete: true
  migrated_at: null            # null = fresh install, timestamp = migrated from old schema
  migrated_from: null          # version that was running before migration
  migration_status: complete   # in_progress | complete | failed
  hook_last_ran: '2026-05-03T19:00:00Z'   # written by SessionStart hook each run
  consistency:
    last_checked: '2026-05-03T19:00:00Z'  # written by hook, not skill
    status: ok                            # ok | drift_detected
    drift: []                             # list of detected drift items
    check_error: null                     # null | "network_unavailable" | "parse_error" etc.
  update:
    available: null                       # null | '2.41.0'
    last_checked: '2026-05-03T19:00:00Z' # written by hook, not skill
    declined: false                       # resets to false when installed_version changes
    check_error: null                     # null | "network_unavailable" etc.

session:
  deference_level: collaborative         # collaborative | guided | autonomous
  default_action: null                   # null | "work" | "review" — set after 3 same answers

work:
  last_item_id: null
  active:
    id: null
    type: null
    workflow: []
    phase: null
    title: null
    started: null
    entry_category: null

# Feature registry — one entry per offerable feature
# status: not_offered | offered | active | declined | deferred
features:
  product_milestones:
    status: not_offered
    offered_at: null
    decided_at: null
    defer_until: null          # ISO timestamp — offer loop skips if now < defer_until
  product_backlog:
    status: not_offered
    offered_at: null
    decided_at: null
    defer_until: null
  product_personas:
    status: not_offered
    offered_at: null
    decided_at: null
    defer_until: null
  product_stories:
    status: not_offered
    offered_at: null
    decided_at: null
    defer_until: null
  document_corpus:
    status: not_offered
    offered_at: null
    decided_at: null
    defer_until: null
  usage_tracking:
    status: not_offered
    offered_at: null
    decided_at: null
    defer_until: null
  behavioral_regression:
    status: not_offered
    offered_at: null
    decided_at: null
    defer_until: null

health:
  last_checked: '2026-05-03T19:00:00Z'  # written by state-regenerator hook
  artifacts:
    milestones:  ok            # ok | missing | stale
    backlog:     ok
    personas:    missing
    stories:     missing
    corpus:      not_configured

# Rolling window — 10 items max, oldest dropped on overflow
work_history:
  - id: null
    title: ""
    type: null
    completed_at: null
    outcome: null              # shipped | abandoned | deferred

# Actionable learnings — max 15
# Full audit trail in improvement-register.jsonl
# Visible and editable via /sweetclaude:help → "review my preferences"
learnings: []
```

### Schema evolution

Unknown fields are tolerated without error — YAML parsers ignore them by default. Schema version bumps trigger migration via `sweetclaude:_migrate --schema-upgrade` before any other logic runs. Old schema versions are never deleted from the archive path.

---

## Sub-Skill Architecture

`/sweetclaude` is a thin orchestrator. It reads the file and delegates. All logic lives in focused internal sub-skills (all `user-invocable: false`):

| Sub-skill | Owns |
|-----------|------|
| `sweetclaude:_migrate` | One-time migration from `phase.yaml`/`skills.yaml` to `sweetclaude.yaml`; also handles schema version upgrades |
| `sweetclaude:_health` | Consistency scan and version check logic (invoked by hook, not skill) |
| `sweetclaude:_offer` | Feature offer loop — surfaces one offer per session, writes decision back to file |
| `sweetclaude:_route` | Natural language classifier — maps user text to internal skill |
| `sweetclaude:setup` | Consolidated `on` + `adopt` — 3 branches: new project / clean existing / messy inherited |

The orchestrator (`/sweetclaude`) reads `sweetclaude.yaml`, checks statuses, and delegates. It contains no time-comparison logic, no migration logic, no classification logic.

---

## Hook Responsibilities

### `session-preflight.sh` (SessionStart hook) — extended

The 24-hour checks run here, before the user types anything. Results are written to `sweetclaude.yaml`. The skill reads cached results only.

```
On SessionStart:
  Write hook_last_ran = now

  If sweetclaude.yaml doesn't exist:
    no-op (skill handles first-run detection)

  If now - consistency.last_checked > 24h:
    Run consistency scan (hooks wired? config intact? version matches installed_version?)
    Write consistency.status, consistency.drift, consistency.last_checked
    On failure: write consistency.check_error = "<error_type>", skip

  If now - update.last_checked > 24h:
    Check remote for new version
    Write update.available (or null), update.last_checked
    On failure: write update.check_error = "network_unavailable", skip
```

### `state-regenerator.sh` (PostToolUse hook) — unchanged

Continues writing `health.artifacts` cache after edits. No change needed.

---

## Decision Tree

```
/sweetclaude [optional args]

─── READ sweetclaude.yaml ────────────────────────────────── (one read, always)

PARSE FAILURE?
  → "Something in my config got scrambled. Let me fix it."
  → sweetclaude:fix-sweetclaude

schema_version != 1?
  → sweetclaude:_migrate --schema-upgrade

sweetclaude.yaml MISSING?
  phase.yaml or skills.yaml present?  →  sweetclaude:_migrate  (old → new schema)
  neither present?                    →  sweetclaude:setup (new project branch)

migration_status = in_progress or failed?
  → sweetclaude:_migrate  (resume/retry — migration is idempotent)

hook_last_ran is stale (> 2h ago)?
  → run sweetclaude:_health inline as fallback
    (covers edge case: skill invoked outside normal session)

setup_complete = false?
  → sweetclaude:setup  (detects: new project / clean existing / messy inherited)

consistency.status = drift_detected?
  → "I found some drift: [human-readable drift list]. Fix it now?"
     yes → sweetclaude:fix-sweetclaude
     no  → continue

update.available AND NOT update.declined?
  → "SweetClaude [version] is out. [One-line what's new]. Update now?"
     yes  → sweetclaude:update
     no   → update.declined = true, continue

─── ARGS PRESENT? ────────────────────────────────────────────────────────────

  "use [workflow-name]" pattern?       (explicit override — bypasses classifier)
    → route directly to named internal skill

  else → sweetclaude:_route classifies intent:
    incident signal ("broke", "error", "down", "crash")  → sweetclaude:something-broke
    status signal ("where are we", "what's done", "show me")
      → surface from sweetclaude.yaml (no extra reads):
        project · version_stage · active work · last 3 history items
    help signal ("how do I", "explain", "what is")       → sweetclaude:help
    work description (default)                           → sweetclaude:_route → matched workflow skill

─── NO ARGS ──────────────────────────────────────────────────────────────────

  Feature offer loop (one offer per session max):
    For each feature in order:
      product_milestones → product_backlog → product_personas →
      product_stories → document_corpus → usage_tracking → behavioral_regression

    Skip if: status = active, declined, or (deferred AND now < defer_until)
    First eligible not_offered feature:
      → sweetclaude:_offer  (human-language offer with why + benefit)
        "yes"      → invoke feature setup skill, set status = offered → active
        "not yet"  → set status = deferred, defer_until = now + 7 days
        "no"       → set status = declined
      → done (one offer per session)

  All features offered/active/declined/deferred AND all clear:
    If session.default_action is set:
      → skip question, execute default_action directly
    Else:
      → Surface status (from file, no reads):
          [Project name] · [version_stage] · [active work item or last completed]
          Next: [what sweetclaude thinks is next, from work.active phase or top backlog]
      → "Want to work on something, or review the current plan?"
           work   → free-text input → sweetclaude:_route → appropriate skill
           review → "Roadmap · Backlog · Open work · Bugs — which?"
        Track answer; after 3 same answers set session.default_action
```

---

## Feature Offer Copy (Human Language)

Offer copy never uses schema field names. Every offer leads with the benefit, ends with the ask.

| Feature | Offer copy |
|---------|-----------|
| `product_milestones` | "Want to set up some milestones? They give you a target to aim at and make it easy to see how far you've come." |
| `product_backlog` | "Want to start a backlog? It's the running list of everything you want to build — keeps ideas from falling through the cracks." |
| `product_personas` | "Want to define who your users are? Clear personas make every product decision easier — you'll refer back to them constantly." |
| `product_stories` | "Ready to write user stories? They turn your ideas into concrete, testable behavior — the input to writing code." |
| `document_corpus` | "Want to connect your docs to SweetClaude? I can search and reference them automatically so you don't have to re-explain context." |
| `usage_tracking` | "Want to turn on usage tracking? It helps surface what's working and what's slowing you down." |
| `behavioral_regression` | "Want to wire up behavioral regression testing? It checks that SweetClaude is still following the framework rules after model updates." |

Each offer has three responses:
- **Yes** — start the feature setup
- **Not yet** — defer for 7 days (never treated as rejection)
- **No** — decline permanently

---

## Migration Path (Old Schema → New)

Triggered when `sweetclaude.yaml` is missing and `phase.yaml` or `skills.yaml` are present. Runs once. Idempotent — safe to re-run if interrupted.

```
sweetclaude:_migrate

1. Set migration_status = in_progress  (write partial file immediately for recovery detection)
2. Read phase.yaml → extract: project.*, session.*, work.*
3. Read skills.yaml → extract: features.* (map status values)
4. Read improvement-register.md → extract top 15 learnings
5. Scan .sweetclaude/product/ → build work_history (last 10 completed items)
6. Scan artifact health → populate health.artifacts cache
7. Write complete sweetclaude.yaml
8. Set migration_status = complete
9. Archive:
     phase.yaml    → .sweetclaude/state/archive/phase.yaml.{date}
     skills.yaml   → .sweetclaude/state/archive/skills.yaml.{date}
10. Tell user: "Migrated to unified state format. Old files archived to .sweetclaude/state/archive/"
```

Schema upgrade migration (v1 → v2+): same pattern via `sweetclaude:_migrate --schema-upgrade`. The migration sub-skill knows all upgrade paths.

---

## First-Run Experience

When `sweetclaude.yaml` doesn't exist and no prior state files are found, `sweetclaude:setup` runs. What the user sees:

**Step 1 — Detection (silent)**
SweetClaude scans the current directory:
- Empty / no code → new project path
- Code present, no prior SweetClaude → standard onboarding path
- Messy / large inherited codebase → adopt workflow path

**Step 2 — Greeting**
"Hi — I'm SweetClaude. I'll help you build [new project / this project] with a structured workflow. Let me ask a few quick questions to get set up."

**Step 3 — Questions (one at a time)**
- What's the project name?
- What are you building? (one sentence)
- New idea or existing codebase? (auto-detected, confirmed)

**Step 4 — Setup (narrated)**
"Setting up your project... [creates directory structure, writes sweetclaude.yaml, generates CLAUDE.md]"
"All set. Here's where things stand: [status summary]. What do you want to work on first?"

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `sweetclaude.yaml` fails to parse | "Something in my config got scrambled. Let me fix it." → `sweetclaude:fix-sweetclaude` |
| Migration interrupted (`migration_status: in_progress`) | Auto-resume migration on next invocation |
| Migration failed (`migration_status: failed`) | Surface error + offer to re-run manually |
| Consistency check fails (no network / permission) | Write `check_error`, skip offer, retry next session |
| Version check fails (no network) | Write `check_error = "network_unavailable"`, skip offer, retry next session |
| `hook_last_ran` stale (> 2h) | Run `sweetclaude:_health` inline as fallback |

---

## What Gets Retired

| Current | Fate |
|---------|------|
| `phase.yaml` | Archived during migration, deleted after confirmed stable |
| `skills.yaml` | Archived during migration, deleted after confirmed stable |
| `sweetclaude:on` | Absorbed into `sweetclaude:setup` |
| `sweetclaude:adopt` | Absorbed into `sweetclaude:setup` |
| `sweetclaude:go` | Absorbed into `/sweetclaude` no-args routing |
| `sweetclaude:find-skill` | Absorbed into `sweetclaude:_route` |
| `sweetclaude:next-steps` | Absorbed into `/sweetclaude` no-args routing |
| `sweetclaude:status` | Absorbed into `/sweetclaude` status surface |
| `improvement-register.md` (as separate read) | Inline in `sweetclaude.yaml` as `learnings:` |

`on`, `adopt`, `go`, `find-skill`, `next-steps`, `status` become `user-invocable: false` immediately. Their skill files are refactored into the sub-skill architecture over the implementation cycle.

---

## Open Questions (Deferred to v2)

- `--advanced` mode: show top-N skill list for power users who want explicit routing (Marcus dissent — recommended for v1 consideration)
- Fine-grained deferral: user-set defer duration instead of fixed 5-session default
- Schema checksum field for corruption pre-detection
- `session.default_action` after 3 repeated same answers (in schema, implementation deferred)

---

## Implementation Sub-Tasks

1. Write `sweetclaude.yaml` schema and migration script (`sweetclaude:_migrate`)
2. Extend `session-preflight.sh` with 24h consistency and version checks
3. Build `sweetclaude:_health`, `sweetclaude:_offer`, `sweetclaude:_route`, `sweetclaude:setup`
4. Write thin `/sweetclaude` orchestrator skill referencing sub-skills
5. Rewrite `sweetclaude:help` as progressive onboarding chat
6. Set `user-invocable: false` on retired user-facing skills
7. Write migration test: verify phase.yaml + skills.yaml → sweetclaude.yaml round-trips correctly
8. Update `sweetclaude:fix-sweetclaude` to handle YAML parse failures
