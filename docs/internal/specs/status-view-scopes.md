# Status View Scopes

Version: 3.1
Date: 2026-05-23
Issue: ISSUE-186 (EP-002b)

## Principle

One command (`/sweetclaude:status`), dynamic views. The skill detects what exists in the project and presents only relevant views. No dead commands — if there are no sprints, sprint never appears.

Every view runs a scoped consistency check before rendering. Checks are informational, not blocking — the view always renders, with warnings prepended if issues are found.

## Entry flow

1. If an argument is provided (`/sweetclaude:status EP-002`, `/sweetclaude:status backlog P0`), skip to the matching view directly. No session view, no menu.
2. If no argument: rebuild cache (with freshness check), show session view, then present the drill-down menu.
3. If the argument doesn't resolve (ID not found, invalid view name), show a one-line error and fall back to the menu.

### Freshness check

Cache rebuild runs at most once per skill invocation. The rebuild result (including the skipped list) is held in memory for the duration of the invocation so that downstream views can reference it without re-running the rebuild.

### Argument syntax

```
/sweetclaude:status                     → session view + menu
/sweetclaude:status EP-002              → epic view for EP-002
/sweetclaude:status ISSUE-034           → issue view for ISSUE-034
/sweetclaude:status MS-008              → release view for MS-008
/sweetclaude:status roadmap             → roadmap view
/sweetclaude:status backlog             → backlog view (all)
/sweetclaude:status backlog P0          → backlog view filtered to P0
/sweetclaude:status backlog --epic EP-002  → backlog view filtered to epic
/sweetclaude:status dependencies        → dependencies view
/sweetclaude:status sprint              → sprint view (active sprint)
```

## Consistency checks

Every view runs a scoped check before rendering. The check is **informational, not blocking** — the view always renders. If the check finds issues, prepend a warnings section:

```
Warnings:
  - EP-002 stored status 'new' but children suggest 'active'
  - ISSUE-099 references epic EP-999 which does not exist

---
(view content follows)
```

If no issues are found, no warnings section appears.

### Check definitions

| Check | Definition | Used by |
|-------|-----------|---------|
| active-item-exists | active_work_item in session-state.yaml resolves to a file on disk with matching status | session |
| schema-valid | frontmatter passes `validate_frontmatter()` from schema.py against the **source file** (not cached data — the cache skips invalid items, so this check must read the file directly) | issue |
| status-canonical | status field value is in `CANONICAL_STATUSES` (from status.py) after `normalize_status()` | issue |
| epic-ref-resolves | epic field value matches an existing item ID on disk | issue, backlog |
| derived-mismatch | stored status differs from derived status. For epics: `derived_status(child_statuses)`. For milestones: two-pass — first compute each epic's derived status from its children, then compute milestone derived from those epic derived values. Must match the algorithm in doctor.py's `check_derived_status` and cache.py's `query_milestones_compact`. | epic, release |
| criteria-agreement | if all children are done/terminal AND completion_criteria is a non-empty list, at least one criterion should be marked done. Epics with no completion_criteria defined are exempt from this check. | epic |
| child-ids-resolve | all IDs in the children set resolve to existing items | epic |
| done-location | items with terminal status are in done/ directory, and vice versa. Requires a **filesystem walk** — the cache does not store directory location as a queryable field. Reuses the same logic as `check_storage_lint` in doctor.py. | release, backlog |
| counter-drift | max ID number seen in files on disk exceeds the max ID stored in the cache. Computed by comparing `query_next_id()` result against a filesystem scan of `ISSUE-*.md` filenames. Same logic as `check_storage_lint` in doctor.py. | backlog |
| cache-health | rebuild skipped-count is zero. Read from the in-memory rebuild result (held from the freshness check step), not from the database. | roadmap |
| cross-location-dup | no item ID appears in both backlog/ and roadmap/. Requires a **filesystem walk** — the cache deduplicates at ingest and cannot show both copies. Same logic as `check_storage_lint` in doctor.py. | roadmap |
| dep-targets-resolve | all depends_on targets resolve to existing item IDs | dependencies |
| no-cycles | dependency graph has no circular chains. Requires topological sort — **new code**, build as `query_dependency_graph` in cache.py. If not yet implemented, omit the "Circular dependencies" section from output and note "cycle detection not available." | dependencies |
| sprint-dates-valid | sprint start date < sprint end date (single-day sprints where start == end are valid) | sprint |
| sprint-items-resolve | all item IDs in the sprint artifact resolve to existing items in the cache or on disk | sprint |
| theme-goal-items-resolve | all linked item IDs resolve to existing items | theme/goal |
| theme-goal-status | theme/goal stored status is consistent with linked children (same derived-status logic) | theme/goal |

## Views

### session

Question: "What am I working on right now?"

Shown when: no argument provided (default view).

Output — compact, 5-7 lines max:

```
ISSUE-034  Add Stripe webhook handler  [active / IMPLEMENT]
  branch: feat/issue-034-stripe  (2 uncommitted)
  last: a1b2c3f  feat(stripe): parse event types
        d4e5f6g  test(stripe): webhook signature validation
  checkpoint: "webhook retry logic next"
  deference: collaborative
```

If no active work item:

```
No active work item.

Your project has {N} epics and {M} issues. Run /sweetclaude:go to pick one up.
```

Fields:
- Active work item (id, title, phase) — from session-state.yaml
- Current branch + uncommitted file count — from git
- Last 2-3 commits — from git log
- Checkpoint (if set) — from checkpoint.md
- Deference level — from session-state.yaml

Not in this view: doctor checkup, improvement register, mode/WIP, known conflicts. These are housekeeping — surface them only when they need attention (doctor has findings, improvement register is non-empty), as a single line at the bottom:

```
  notes: 3 learnings from prior sessions · last checkup 2 days ago (all clear)
```

Omit the notes line entirely if improvement register is empty AND last doctor checkup was clean or doesn't exist.

#### Auto-trigger behavior

These behaviors transfer from the current recap skill:
- **Session start with checkpoint_next set**: show only the checkpoint line: `Last session ended mid-task: {checkpoint_next}. Pick up here?` — not the full session view.
- **Detour conclusion (5+ turns)**: one-line check-in: `We were on {X} — {summary}. Ready to pick back up?` — not the full session view.

`/sweetclaude:recap` redirects to `/sweetclaude:status` (no argument form).

### issue

Question: "What's the state of this issue?"

Shown when: user passes an issue ID (`/sweetclaude:status ISSUE-034`), or selects from menu, or active work item is an issue and user picks "Current issue" from the menu.

```
ISSUE-034  Add Stripe webhook handler
  type: enhancement  status: active  priority: P1
  epic: EP-005 — Payment Integration [active]
  branch: feat/issue-034-stripe  phase: IMPLEMENT
  blocked_reason: —
  depends_on: ISSUE-031 (done), ISSUE-032 (in-review)
```

If the issue ID doesn't exist: `ISSUE-034 not found. It may have been moved to done/ or archived.`

Consistency check: schema-valid, status-canonical, epic-ref-resolves (all run against the source file, not cached data).

### epic

Question: "How is this effort going?"

Shown when: epics exist. Menu label: `Epic ({N} epics)`.

Default (no ID specified): show active work item's parent epic if set. Otherwise present an AskUserQuestion menu of epics.

```
EP-005  Payment Integration  [active]  (derived: active — matches)
  Objective: Integrate Stripe for subscription billing and one-time payments

  Criteria:  3/5 complete
    [x] Webhook endpoint receives and validates events
    [x] Subscription lifecycle (create, upgrade, cancel)
    [ ] One-time payment flow
    [x] Idempotency on retries
    [ ] Invoice PDF generation

  Issues:  8/12 done
    ISSUE-031  Stripe SDK setup                     done
    ISSUE-032  Webhook signature validation          in-review
    ISSUE-033  Subscription create flow              active
    ISSUE-034  Add Stripe webhook handler            active  **
    ISSUE-035  Payment failure handling               blocked  ⚠ "awaiting Stripe sandbox fix"
    ... (+3 done, not shown)

  Blockers:
    ISSUE-035 — awaiting Stripe sandbox fix
```

Output caps:
- Show all non-done issues. Done issues summarized as `(+N done, not shown)`.
- If more than 20 non-done issues, show top 20 by priority and note `(+M more, run /sweetclaude:status backlog --epic {epic_id})`.

Discrepancy display: if stored != derived, show `(derived: {X} — MISMATCH)` in red-toned language. If they match, show `(derived: {X} — matches)`.

Consistency check: derived-mismatch, criteria-agreement, child-ids-resolve.

### release

Question: "What's shipping in this milestone?"

Shown when: milestones exist. Menu label: `Release ({N} milestones)`.

```
MS-008  Release and Roadmap System  [active]  target: v4.1.0

  EP-001  Doctor System               done  (14/14)
  EP-002  Status System               active (4/7 criteria)  ** 2 blocked
  EP-003  Agentic Workflows           new (0/5)

  Blockers:
    ISSUE-089  RBAC migration fails on empty orgs  (EP-002, P0)
    ISSUE-091  Audit schema review pending legal    (EP-002, blocked)

  Progress: 1/3 epics done · 18/26 issues done
```

Output caps:
- Show all epics (milestones rarely have more than 10).
- Blockers: show all blocked/on-hold items across all epics, max 10. If more, note `(+N more blockers)`.

Consistency check: derived-mismatch, done-location.

### roadmap

Question: "Where is the whole project?"

Shown when: milestones or epics exist. Menu label: `Roadmap`.

```
MS-007  Core Platform  [done]
├── EP-001  Doctor System          ✓ done
└── EP-003  Hook Infrastructure    ✓ done
↓
MS-008  Release and Roadmap System  [active]
├── EP-002  Status System          [active]  4/7 criteria
│   ├── ISSUE-182  Schema validation       ✓
│   ├── ISSUE-184  Derived status          ✓
│   ├── ISSUE-186  View scope definition   [active]
│   └── (+3 more)
└── EP-004  Release Automation     [new]  0/3 criteria
↓
MS-009  Agent Framework  [new]

3 milestones · 4 epics · 26 issues
Unlinked: 5 items not assigned to an epic
```

Output caps:
- Per epic: show up to 5 non-done issues. Done issues collapsed to `✓`. Remaining as `(+N more)`.
- Per milestone: show all epics (no cap).
- Unlinked backlog: count + top 5 items, not the full list.

Discrepancy markers: if a milestone or epic's stored status differs from derived, append `⚠ children suggest [{derived}]`.

Cache health: if rebuild skipped any items, append one line: `{scanned} scanned, {ingested} indexed, {len(skipped)} skipped — run /sweetclaude:doctor for details`.

Consistency check: cache-health, counter-drift, cross-location-dup.

### backlog

Question: "What's in the queue?"

Shown when: backlog items exist. Menu label: `Backlog ({N} items)`.

Supports filtering: `/sweetclaude:status backlog P0` shows only P0 items. `/sweetclaude:status backlog --epic EP-002` shows only items linked to EP-002.

Note: the `--epic` filter requires a new `epic` parameter on `query_backlog()` in cache.py. This is new code.

Note: `query_backlog()` excludes items with status `done`, `abandoned`, and `deferred`. Deferred items are intentionally excluded from the backlog view — they are not in the queue. To see deferred items, use `/sweetclaude:project-backlog` which shows the full unfiltered list.

```
Now (P0) — 3 items
  ISSUE-089  [P0]  RBAC migration fails on empty orgs     (EP-002, blocked)
  ISSUE-090  [P0]  Status audit trail gaps                 (EP-002, active)
  ISSUE-091  [P0]  Audit schema review pending legal       (EP-002, blocked)

Sooner (P1) — 5 items
  ISSUE-092  [P1]  Dashboard official integration          (EP-002, new)
  ISSUE-093  [P1]  Dashboard write-back API                (EP-002, new)
  ... (+3 more)

Soon (P2) — 8 items
  ... (showing top 5)

Unscheduled — 4 items (no priority set)
  ...

Total: 20 items · 3 unlinked (no epic)
```

Output caps:
- Per horizon bucket: show up to 5 items. If more, note `(+N more)`.
- When filtered (e.g., `backlog P0`): show up to 50 matching items. If more, note `(+N more — narrow the filter)`.
- Total line always shows full count.
- If a filtered view returns zero matches: `No items match filter '{filter}'. Total backlog: {N} items.`

Consistency check: counter-drift, done-location, epic-ref-resolves.

### dependencies

Question: "What blocks what?"

Shown when: any item has a non-empty depends_on field. Menu label: `Dependencies ({N} items have dependencies)`.

```
Blocked chains:
  ISSUE-178 → ISSUE-182 → ISSUE-186  (EP-002, all active)
  ISSUE-201 → ISSUE-203              (EP-005, 201 blocked)

Unresolved references:
  ISSUE-199 depends_on ISSUE-999  (ISSUE-999 does not exist)

Circular dependencies:
  (none detected)

{N} items have dependencies · {M} blocked chains · {K} unresolved refs
```

Output format is an adjacency-chain rendering: show only items that participate in dependency relationships. Items with zero dependencies are not shown.

Blocked chains: first detect and remove any cycles from the traversal set (to prevent infinite loops). Then traverse the acyclic remainder from leaf nodes back to root items. Show the longest chains first, max 15 chains. If more, note `(+N more chains)`.

If cycle detection is not yet implemented (`query_dependency_graph` does not exist), omit the "Circular dependencies" section entirely and note: `Cycle detection not yet available.`

Consistency check: dep-targets-resolve, no-cycles.

Implementation note: cycle detection requires a topological sort over the dependencies table. This is new code — not currently implemented in cache.py or doctor.py. Build as a `query_dependency_graph` function in cache.py.

### sprint

Question: "How is this sprint going?"

Shown when: sprint artifacts exist in `.sweetclaude/artifacts/sprints/` with an active sprint.

Implementation note: sprint data lives in `.sweetclaude/artifacts/sprints/*.yaml`, not in the cache's scan paths (backlog/, roadmap/). This view reads sprint artifacts directly from disk, not from the cache. Item ID resolution (for the sprint-items-resolve check) queries the cache to verify each referenced item exists.

```
Sprint 4: "Status System"  [active]  May 19 – May 30

  done:        6/10 items (60%)
  in-progress: 2
  to-do:       2

  ISSUE-186  View scope definition      active
  ISSUE-187  Output format specs         new
  ISSUE-188  Dashboard integration       new  (blocked by ISSUE-186)
  ... (+6 done, not shown)
```

Velocity: done items / total items assigned at sprint start. Denominator is total items in the sprint artifact, not items ever associated.

Consistency check: sprint-dates-valid, sprint-items-resolve.

### theme / goal

Question: "How are we tracking against this theme/goal?"

Shown when: items with type=theme or type=goal exist in the cache.

Data source: the theme/goal item itself is read from frontmatter on disk. Linked items are found by querying the cache's items table for items whose frontmatter contains a matching `theme` or `goal` field.

Implementation note: the cache schema does not currently have `theme` or `goal` columns. This view requires either adding those columns to the items table schema or performing a frontmatter scan of source files. Flag as new schema work.

```
THEME-01  Developer Experience  [active]

  Linked items: 12 total · 7 done · 3 active · 2 new
  Progress: 58%

  Active:
    ISSUE-045  Improve error messages     active (EP-003)
    ISSUE-067  CLI help text overhaul     active (EP-004)
    ISSUE-089  Status view redesign       active (EP-002)
```

Only show non-done linked items. Done items appear as the count in the summary line.

Consistency check: theme-goal-items-resolve, theme-goal-status.

## Menu behavior

After the session view (when no argument is given), present available drill-down views. Only views with data appear. Use AskUserQuestion with the question-form descriptions as labels:

```
Which view?
  "How is this effort going?" — Epic (3 epics)
  "What's shipping?" — Release (2 milestones)
  "Where is the whole project?" — Roadmap
  "What's in the queue?" — Backlog (14 items)
  "What blocks what?" — Dependencies (5 items)
  "How is this sprint going?" — Sprint: "Status System"
  "Current issue" — ISSUE-034: Add Stripe webhook handler
  Something else
```

Rules:
- "Current issue" only appears if there is an active work item that is an issue type.
- Sprint, theme/goal only appear if data exists, with identifying info in the label.
- Counts in parentheses give scale.
- The menu is one-shot. After a view renders, the user can ask for another view conversationally or run `/sweetclaude:status` again. No automatic re-presentation.

## Output format

All views render as plain Markdown text. No ANSI codes, no box-drawing characters except `├──`, `└──`, `│`, `↓` in the roadmap tree. Output must be pasteable into Slack, a PR description, or a plain text file without garbling.

## Overlap rules

1. Entity IDs may appear in any view for navigation
2. Each view owns its consistency checks — checks do not repeat across views
3. Derived status appears in epic (per-item discrepancy detail) and roadmap (tree markers) — different granularity, not duplication
4. Session context (git, checkpoint, deference) appears only in the session view
5. depends_on appears in issue (inline list) and dependencies (graph rendering) — the issue view shows direct dependencies for one item, the dependencies view shows the full graph across the project

## Eliminated from current status skill

- Roadmap summary line → roadmap view
- Backlog breakdown by horizon → backlog view
- RAG state → `/sweetclaude:corpus-status`
- Version numbers → `/sweetclaude:help`
- Known config conflicts → doctor checkup, surfaced in session notes line only when findings exist
