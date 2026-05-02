---
spdx-license: AGPL-3.0-or-later
description: "Manage roadmap targets (milestones) that span strategy and product work. Create, review, link work items to, and track completion of outcome-driven milestones like 'Exit Stealth' or 'Paid Pilot Live'."
category: product
---

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
   > "No artifact privacy manifest found. Run `/sweetclaude:on` to configure artifact privacy, then return here."
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

### `pause` — Temporarily stop using this skill

Invoked with argument `pause`.

Sets milestones to `paused` status. Your milestone files are untouched and you can resume at any time by invoking this skill normally.

Write atomically (using write protocol):
- `skills.product-milestones.status: paused`
- `skills.product-milestones.last_changed_at: {today ISO date}`
- `skills.product-milestones.last_changed_by: pause`

Say: "Paused. Your milestone files are safe — nothing was deleted. Resume anytime by running `/sweetclaude:product-milestones`."

---

### `offboard` — Export data and stop using this skill

1. **Inventory what exists:**

```bash
ls {base_path}/milestones/MS-*.md 2>/dev/null | wc -l
ls {base_path}/milestones/ 2>/dev/null
```

Present: "This project has {N} milestone files in `{base_path}/milestones/`."

If nothing exists, say: "No milestone data found. Nothing to export." Stop.

2. **Ask export format** (one question):

> "Where do you want to export your milestones?
>   github     — create GitHub milestones via `gh milestone create`
>   markdown   — copy files to a directory you specify
>   csv        — write a summary CSV to a path you specify
>   none       — skip export, go straight to cleanup options"

3. **Export:**

- **github:** For each MS-*.md file with status `active` or `proposed`, run `gh milestone create --title "{title}" --description "{outcome}"`. Report what was created.
- **markdown:** Ask "Which directory?" Validate it exists. Copy all `MS-*.md` files and `MILESTONES-INDEX.md` there. Report files copied.
- **csv:** Ask "Which path?" Write one row per milestone: ID, title, status, owner, criterion count, met count. Report path written.
- **none:** Skip.

4. **Verify export (mandatory before deletion is unlocked):**

- **github verification:**
  ```bash
  gh milestone list 2>/dev/null | wc -l
  ```
  If result ≥ exported_count: "Export verified — {N} milestones confirmed in GitHub."
  If result < exported_count: "⚠ Export may be incomplete — only {actual} milestones found but expected at least {exported_count}."
  If `gh` unavailable: "Could not verify GitHub export automatically. Confirm you see all {N} milestones in GitHub."
  On any failure or mismatch: ask "Continue anyway despite unverified export? [yes/cancel]". If cancel: stop, do not proceed to deletion.

- **markdown verification:**
  ```bash
  source_count=$(ls {base_path}/milestones/MS-*.md 2>/dev/null | wc -l)
  dest_count=$(ls {dest_dir}/MS-*.md 2>/dev/null | wc -l)
  ```
  If dest_count ≥ source_count: "Export verified — {source_count} files at `{dest_dir}`."
  If less: "⚠ File count mismatch." Ask "Continue anyway? [yes/cancel]". If cancel: stop.

- **csv verification:**
  Read the CSV written. Count data rows (excluding header). If row_count ≥ source_count: "Export verified."
  If less: "⚠ Row count mismatch." Ask "Continue anyway? [yes/cancel]". If cancel: stop.

- **none (no export chosen):**
  Require explicit acknowledgment:
  > "You've chosen to skip export. Your data will be permanently deleted with no backup.
  > Type exactly: NO BACKUP — to confirm you understand, or anything else to cancel."
  If user types anything other than `NO BACKUP` exactly: "Cancelled. Your data is safe." Stop.

5. **⚠ IRREVERSIBLE DATA LOSS WARNING ⚠**

> "⚠ IRREVERSIBLE DATA LOSS WARNING ⚠
>
> The next step will permanently delete {N} files from `{base_path}/milestones/`.
> This cannot be undone. There is no undo, no recycle bin, no recovery.
>
> Only proceed if you have confirmed your export is complete and correct.
>
> To confirm deletion, type exactly: DELETE MY MILESTONES
> To cancel, type anything else."

Wait for input. If the user types anything other than `DELETE MY MILESTONES` exactly, say "Cancelled. Your files are safe." and stop.

6. **Delete only after exact confirmation:**

```bash
rm -rf {base_path}/milestones/
```

Report: "Milestone files deleted. SweetClaude will no longer track milestones for this project."

---

### Lightweight first-invocation — Quick setup on first use

Runs when the skill is invoked normally but `status` is `uninitialized`. Does NOT run when `$ARGUMENTS` is `onboard`.

1. Read `artifact-privacy.yaml` → `{base_path}`. If absent: "No artifact privacy manifest found. Run `/sweetclaude:on` to configure artifact privacy, then return here." Stop.

2. Present inline:
   > "No milestones set up yet. I'll create the milestones directory at `{base_path}/milestones/`.
   > Import from GitHub Milestones? [yes/no/skip]"

3. If **yes**:
   ```bash
   gh milestone list 2>/dev/null
   ```
   Create `MILESTONES-INDEX.md` with the standard header. For each GitHub milestone found, create an `MS-XXX` file with title and description. Report how many were imported.

4. If **no** or **skip**: Create `{base_path}/milestones/MILESTONES-INDEX.md` with the standard header only.

5. Write state (using write protocol): `status: active`, `last_changed_at: {today}`, `last_changed_by: first-invocation`.

6. Proceed to the user's originally requested operation (do not re-route to the full onboard flow).

---

### `onboard` — First-time setup

1. **Scan for existing milestone and roadmap data:**

```bash
# GitHub milestones
gh milestone list 2>/dev/null | head -20 || true
gh issue list --label milestone --limit 20 2>/dev/null | head -20 || true

# Linear, Jira, Notion references
grep -ri "linear.app\|jira\|atlassian\|notion.so" README* docs/ .sweetclaude/ 2>/dev/null | head -5

# Existing markdown milestone/roadmap files
find . -maxdepth 4 -name "*.md" | xargs grep -li "milestone\|roadmap" 2>/dev/null | grep -v ".sweetclaude" | head -10
```

2. **Present findings and ask:**

If existing data found:
> "I found existing milestone/roadmap data:
>   {list what was found — file names, GitHub milestone names, etc.}
>
> What do you want to do?
>   import    — create SweetClaude milestone files from this data
>   fresh     — start clean, ignore existing data
>   cancel    — set up later with `/sweetclaude:product-milestones onboard`"

If nothing found:
> "No existing milestone tracking found. I'll create the milestones directory at `{base_path}/milestones/`. Proceed? (yes/cancel)"

3. **If import:** For each milestone or roadmap item found, read the source and create a SweetClaude `MS-XXX` file using the milestone template. Populate all fields from the source data where available; leave others as defaults. Present a summary of what was created. Then tell the user: "Use `/sweetclaude:product-milestones review` to see your milestones."

4. **If fresh / yes:** Create `{base_path}/milestones/MILESTONES-INDEX.md` with the standard header. Tell the user: "Ready. Use `/sweetclaude:product-milestones add` to create your first milestone."

5. **If cancel:** "OK. Run `/sweetclaude:product-milestones onboard` when ready."

---

### `add` — Create a new milestone

1. Read `{base_path}/milestones/MILESTONES-INDEX.md`. If it does not exist, create it with this header:

```markdown
# Milestones Index

| ID | Title | Status | Owner | Short summary |
|----|-------|--------|-------|---------------|
```

2. Find the highest existing `MS-XXX` in the index. Increment by 1. If the index is empty, start at `MS-001`.
3. Ask the user (one question at a time, per SweetClaude interaction model):
   - Title (short, descriptive, 2-5 words)
   - Outcome (one paragraph — what "achieved" looks like)
   - Measuring success criteria: ask for a list. For each criterion, offer: "Link this to a canonical artifact path? (optional, e.g. `strategy/narrative-arc.md`)"
   - Non-goals: require at least one. If the user offers none, prompt: "What is this milestone explicitly NOT? A non-goals list with zero items is a scope red flag."
   - Depends on: list of other MS-XXX refs (optional)
   - Owner: default to the value of `owner` in `.sweetclaude/state/phase.yaml` if present; otherwise prompt.
4. Default `Status:` to `proposed`. Ask the user only if they indicate otherwise.
5. Write the file at `{base_path}/milestones/MS-XXX-<slug>.md` using the milestone template from the previous section, filling in all fields. `<slug>` is a dash-lowercased version of the title (e.g., "Exit Stealth" → `exit-stealth`).
6. Append a row to `{base_path}/milestones/MILESTONES-INDEX.md`:

```
| MS-XXX | [Title](MS-XXX-slug.md) | proposed | Owner | One-sentence outcome summary |
```

7. Tell the user: "Added MS-XXX: {title}. Status: proposed. File: {base_path}/milestones/MS-XXX-{slug}.md"

### `review` — List milestones by commitment level

1. Scan `{base_path}/milestones/` for all files matching `MS-*.md` (exclude `MILESTONES-INDEX.md`).
2. Read each file's `**Status:**` field.
3. Group:
   - **Now**: `active`
   - **Next**: (see Open Items — default empty; promotion mechanism is an open design question in the spec)
   - **Later**: `proposed`
   - Terminal states (`achieved`, `dropped`, `superseded`): hidden unless `review --all` was invoked.
4. For each displayed milestone, compute a progress snapshot:
   - Count `- [x]` and `- [ ]` lines under the `## Measuring success` heading.
   - For criteria that reference an artifact path, note whether the path is populated vs. a bare text criterion. (Artifact finalization check — see Open Items for the canonical convention.)
5. Present in this format:

```
Milestones
══════════

Now (active):
  → MS-001 Exit Stealth         3/5 criteria met
  ✓ MS-003 MVP Shipped          4/4 criteria met — ready to complete

Later (proposed):
  MS-004 Paid Pilot Live
  MS-005 Series A Readiness
```

6. If `--all` was passed, append terminal-state milestones after Later:

```
Achieved:
  MS-002 Private Alpha        (2026-03-15)

Dropped:
  MS-006 Desktop App          (2026-02-01 — rationale: see Notes)
```

7. If no milestones exist, say: "No milestones yet. Run `/sweetclaude:product-milestones add` to create one."

### `link <work-item> <MS-XXX>` — Bidirectional attach

1. Validate the work-item ref: must match `^(US|BL)-\d+$`. If not, tell the user the expected format and stop.
2. Locate the work-item file:
   - `US-XXX` → search `stories/**/US-XXX-*.md` then `.sweetclaude/stories/**/US-XXX-*.md`.
   - `BL-XXX` → search `{base_path}/backlog/BL-XXX-*.md`.
   - If not found, tell the user and stop.
3. Validate `{base_path}/milestones/MS-XXX-*.md` exists. If not, tell the user and stop.
4. Read the work item. Check for an existing `**Milestone:**` header (exact match: line starting with `**Milestone:**`).
   - If present and equals the requested MS: no-op. Say "Already linked."
   - If present but different: ask "This work item is currently linked to {old MS}. Replace with {new MS}? (yes/no)" — require explicit yes. If no, stop.
5. Write/update the work item's `**Milestone:**` header:
   - If no header exists, insert `**Milestone:** MS-XXX` immediately after the H1 title line.
   - If a header exists, replace its value.
6. Read `{base_path}/milestones/MS-XXX-*.md`. In the `## Contributing work items` section:
   - If the item is not already listed, add `- {work-item-ref} — {title from work item's H1}`.
   - If the section does not exist, create it before `## Notes`.
7. If the work item was previously linked to a different milestone:
   - Read that old milestone file.
   - Remove the work item from its Contributing work items section.
   - Append a Changelog row: "{date} — Removed {work-item-ref} (relinked to {new MS})."
8. Append a Changelog row to the new milestone file: "{date} — Linked {work-item-ref}."
9. Tell the user: "Linked {work-item-ref} to MS-XXX. {if relinked: 'Removed from {old MS}.'}"

### `status <MS-XXX>` — Detail view

1. Read `{base_path}/milestones/MS-XXX-*.md`. If missing, tell user and stop.
2. For each item in `## Measuring success`:
   - If the item references an artifact path (pattern: backtick-wrapped path like `` `strategy/narrative-arc.md` ``), read that file. Determine "met" using the finalization convention (see Open Items — default: file exists and its first heading is not `# DRAFT`).
   - Otherwise, use the checkbox state directly (`- [x]` met, `- [ ]` not met).
3. For each item in `## Contributing work items`, read the work-item file and classify:
   - **done**: work item's own status marker says completed/done/merged.
   - **in-progress**: marker says active/in-progress.
   - **pending**: no active marker.
   - **unknown**: file missing or no marker — flag with `?`.
4. Render:

```
MS-001: Exit Stealth
Status: active  |  Owner: Carson
Depends on: (none)

Outcome:
One paragraph...

Measuring success:
  [x] Criterion 1
  [ ] Criterion 2
  [x] strategy/narrative-arc.md finalized
  [ ] product/market-messaging.md finalized

Non-goals:
  - Not a self-serve launch
  - Not a pricing change

Contributing work items:
  US-012  (done)        Landing page redesign
  US-015  (in-progress) Press kit generator
  BL-007  (pending)     Analytics tracking

Recent notes:
  2026-04-18 — Narrative arc finalized.
  2026-04-10 — Decided to split press kit from landing page.
```

5. "Recent notes" shows the last 3 Notes entries (by date if dated, otherwise by file order).

### `blockers <MS-XXX>` — What is stopping us

1. Read the milestone file. If missing, tell user and stop.
2. Compute:
   - **Unmet criteria:** each `- [ ]` line under Measuring success, and each artifact-reference criterion where the artifact is not finalized.
   - **Open work items:** each item under Contributing work items that is not in `done` state (same classification as `status`).
   - **Unmet dependencies:** each MS-XXX in Depends on whose Status is not `achieved`.
3. Render:

```
Blockers for MS-001 Exit Stealth
═════════════════════════════════

✗ Unmet criteria (2):
  - Criterion 2
  - product/market-messaging.md finalized

⚠ Open work items (2):
  US-015  (in-progress) Press kit generator
  BL-007  (pending)     Analytics tracking

⚠ Dependencies not met (1):
  MS-000  Company name finalized  (status: proposed)
```

4. If nothing is blocking, say: "Nothing is blocking MS-XXX. All criteria met, all contributing work items done, all dependencies achieved. Run `/sweetclaude:product-milestones complete MS-XXX` to mark it achieved."

### `complete <MS-XXX>` — Mark achieved and chain follow-ups

1. Read the milestone file. If missing, tell user and stop.
2. If current Status is already terminal (`achieved`, `dropped`, `superseded`), tell the user and stop. Do not transition from a terminal state.
3. Evaluate criteria (same logic as `status`):
   - If any criterion is unmet, list them.
   - Ask: "These criteria are not met: {list}. Proceed with explicit waiver?"
   - If the user declines, stop without changes.
   - If the user accepts, prompt: "Waiver rationale?" Append to `## Notes`: `{date} — Completion waiver: {rationale}. Unmet at completion: {list}.`
4. Evaluate contributing work items:
   - If any are not in `done` state, list them.
   - Ask: "These contributing work items are not done: {list}. Continue?"
   - If no, stop. If yes, proceed.
5. Set `**Status:**` to `achieved`.
6. Append Changelog row: `{date} — Marked achieved. {if waived: 'Waived N criteria — see Notes.'}`
7. Update `{base_path}/milestones/MILESTONES-INDEX.md`: change the status column for this milestone to `achieved`.
8. **Follow-up chain.** Ask the user:

```
Milestone achieved. Any follow-ups to capture?

Categories:
  - incomplete_scope — parts deferred from this milestone
  - next_steps      — what users will want next
  - tech_debt       — shortcuts taken that should be paid back
  - test_gaps       — missing test coverage uncovered during the work

List each follow-up as: "<category>: <short title>". Enter blank line when done.
```

9. For each follow-up entered, invoke `sweetclaude:product/backlog` with arguments that route to its `add` flow. Pass the category as context. Do not inline the backlog-add logic — delegate. If the user indicated a strategic item, the backlog skill's existing router will redirect to `strategy/`.
10. Tell the user: "MS-XXX marked achieved. {N} follow-ups filed."

### `unassigned` — Hygiene check

1. Scan work-item files:
   - Stories: `stories/**/US-*.md` and `.sweetclaude/stories/**/US-*.md`.
   - Backlog: `{base_path}/backlog/BL-*.md`.
2. For each file, check for a `**Milestone:**` header line.
3. Group items with no header by type:

```
Unassigned work items (5)
═════════════════════════

⚠ Stories (2):
  US-008  Onboarding email flow
  US-011  Usage dashboard

⚠ Backlog (3):
  BL-003  Migrate to Postgres
  BL-005  Add rate limiting
  BL-009  Vendor management page
```

4. Tell the user: "These have no milestone. Either link them to a milestone (`/sweetclaude:product-milestones link <item> <MS-XXX>`) or confirm they are distractions / out of roadmap. Not doing anything is also fine — this check is advisory."
5. Do not force action. Do not modify files. Surface only.

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
