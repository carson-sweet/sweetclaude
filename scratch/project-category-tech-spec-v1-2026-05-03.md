# SweetClaude Project Category — Technical Specification
**Version:** 1.0  
**Date:** 2026-05-03  
**Status:** DRAFT  
**Authors:** Carson Sweet + Claude  
**Input:** `scratch/project-category-data-model-v1-2026-05-03.md` (v1.2)

---

## 1. Overview and Scope

This spec defines every technical decision needed before writing code for the Project category. It covers the storage adapter, Flow mode hook architecture, mode-shift mechanics, skill implementations, and migration tooling.

**In scope:** storage adapter, Flow mode inference hooks, mode-shift snapshots, all nine skills in the Project+Product skill inventory, entity ID assignment, cross-reference index, migration script.

**Out of scope:** UI/UX design, skill prose content, phase gate wording, TDD test design.

---

## 2. Storage Adapter

Skills call `sc_artifact_*` shell functions. The adapter resolves the active backend from `phase.yaml → storage_backend` and dispatches to Markdown or SQLite accordingly. Skills never read files or execute SQL directly.

### 2.1 Function signatures

```bash
# Read a single artifact by ID. Returns JSON object or empty string if not found.
sc_artifact_read <id>

# Overwrite all fields of an existing artifact. <json> must include all fields.
# Returns: 0 on success, 1 if ID not found.
sc_artifact_write <id> <json>

# Create a new artifact of the given type. Assigns next available ID.
# Returns: the assigned ID on stdout.
sc_artifact_create <type> <json>

# Query artifacts by type and optional key=value filters.
# Multiple filters are AND'd. Returns JSON array (empty array if no results).
sc_artifact_query <type> [key=value ...]

# Soft delete: sets status=cancelled and updated_at=now. Returns: 0 on success.
sc_artifact_delete <id>

# List all non-cancelled artifacts of a type. Returns JSON array.
sc_artifact_list <type>
```

**ID format:** `<PREFIX>-<NNN>` where NNN is zero-padded to three digits (e.g. `I-001`). If more than 999 artifacts exist for a type, padding expands naturally (`I-1000`). The adapter reads existing IDs in the index to find the next available number.

### 2.2 Markdown backend

**Implementation:** shell script dispatching file reads/writes against the `{product_base}/` directory tree.

Each `sc_artifact_*` call:

- **`read`:** Read the corresponding `.md` file. Parse the bold key-value metadata block (lines matching `**Key:** Value`) into JSON. Return JSON object.
- **`write`:** Read existing file. Update metadata block fields in-place. Preserve freeform body sections (Description, Acceptance criteria, etc.) unchanged. Set `**Updated:**` to today. Write file.
- **`create`:** Compute next ID by scanning `{type}-INDEX.md` for the highest existing NNN. Write new `.md` file from template. Append entry to the type's `INDEX.md`. Update `project-index.json`.
- **`query`:** Read `project-index.json`. Filter by type and key=value pairs. Return matching IDs. For each matching ID, call `sc_artifact_read`.
- **`delete`:** Call `sc_artifact_write` with `status=cancelled`. Update `project-index.json` entry.
- **`list`:** Read `project-index.json`. Return all entries of given type where `status != cancelled`.

**Metadata parsing rules:**
- Metadata block: contiguous lines at the top of the file (after the `# ID: Title` header) matching `**Key:** Value`
- First blank line after the header block ends the metadata region
- Multi-value fields (acceptance criteria, sprint history) are stored as inline comma-separated strings in metadata; the adapter parses/serializes them
- Body sections (H2 headings and below) are never parsed — treated as opaque text

**Template selection:** `sc_artifact_create` reads templates from `~/.claude/plugins/sweetclaude/skills/project-{type}/template.md`. If no template exists for the type, falls back to `~/.claude/plugins/sweetclaude/skills/project-base/template.md`.

### 2.3 SQLite backend

**Implementation:** shell script dispatching SQL via `sqlite3 {state_base}/project.db`.

Each `sc_artifact_*` call maps to straightforward SQL:

- **`read`:** `SELECT * FROM {table} WHERE id = ?` → JSON via `sqlite3 -json`
- **`write`:** `UPDATE {table} SET ... WHERE id = ?`
- **`create`:** `SELECT MAX(CAST(SUBSTR(id,INSTR(id,'-')+1) AS INT)) FROM {table}` to find next N, then `INSERT INTO {table} ...`
- **`query`:** `SELECT * FROM {table} WHERE {conditions}` with AND-joined conditions
- **`delete`:** `UPDATE {table} SET status='cancelled', updated_at=? WHERE id=?`
- **`list`:** `SELECT * FROM {table} WHERE status != 'cancelled'`

**Type → table mapping:**

| Type argument | Table |
|---|---|
| `issue` | `issues` |
| `epic` | `epics` |
| `sprint` | `sprints` |
| `roadmap_item` | `roadmap_items` |
| `release` | `releases` |
| `milestone` | `milestones` |
| `pitch` | `pitches` |

**`backlog` is not a type argument.** Skills call `sc_artifact_query issue sprint_id= status=backlog` (empty sprint_id = NULL). The SQLite `backlog` VIEW defined in the DDL is a convenience for direct SQL users only.

### 2.4 Backend dispatch

`sc_artifact_*` functions are thin wrappers that source the active backend:

```bash
# ~/.claude/hooks/sweetclaude/sc-artifact.sh

SC_BACKEND=$(python3 -c "
import yaml, sys
s = yaml.safe_load(open('.sweetclaude/state/phase.yaml'))
print(s.get('storage_backend','markdown'))
" 2>/dev/null || echo "markdown")

if [ "$SC_BACKEND" = "sqlite" ]; then
  source "$(dirname "$0")/sc-artifact-sqlite.sh"
else
  source "$(dirname "$0")/sc-artifact-markdown.sh"
fi
```

Each skill sources `sc-artifact.sh` at the top of its execution. No skill hardcodes a backend.

### 2.5 project-index.json schema

The cross-reference index is a lightweight lookup layer for the Markdown backend. Skills use it to answer "which issues are in sprint SP-003?" without reading every file.

**Location:** `{state_base}/project-index.json`

**Schema:**

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-03T12:00:00Z",
  "last_full_scan": "2026-05-03T12:00:00Z",
  "entities": [
    {
      "id": "I-001",
      "type": "issue",
      "title": "Login form validation",
      "status": "in_progress",
      "priority": "sooner",
      "effort": "s",
      "epic_id": "EP-001",
      "sprint_id": "SP-002",
      "roadmap_item_id": null,
      "source": "manual",
      "updated_at": "2026-05-03"
    },
    {
      "id": "EP-001",
      "type": "epic",
      "title": "Auth refactor",
      "status": "active",
      "roadmap_item_id": "RM-001",
      "updated_at": "2026-05-03"
    },
    {
      "id": "SP-002",
      "type": "sprint",
      "title": "Sprint 2",
      "status": "active",
      "start_date": "2026-05-06",
      "end_date": "2026-05-20",
      "updated_at": "2026-05-03"
    }
  ]
}
```

**Rules:**
- Only the fields needed for cross-reference queries are in the index — never full artifact content
- The index is append-only during a session; `state-regenerator` does full rebuilds
- If the index is missing or stale (older than last git commit touching the issues/ directory), `sc_artifact_query` falls back to full file scan and logs a warning
- SQLite backend does not use this file — queries go directly to the database

**`state-regenerator` hook:** runs on session start. Walks all `{product_base}/*/` directories, reads each `.md` metadata block, rebuilds `project-index.json`. Idempotent.

---

## 3. Flow Mode — Hook Architecture

### 3.1 Session start inference

`session-preflight.sh` reads `phase.yaml → mode`. If `flow`:

1. Read last scan timestamp from `{state_base}/flow-state.yaml`
2. Run git scan: `git log --oneline --since="{last_scan_ts}" --format="%H %s"` — classify each commit message by type (story/bug/chore/spike patterns below)
3. Run branch scan: `git branch -a` — classify branch names by prefix (`feature/`, `fix/`, `chore/`, `spike/`)
4. For each new inferred item, call `sc_artifact_create issue {..., source: inferred, evidence: "<commit_hash>"}` only if no existing inferred issue has the same evidence value (dedup)
5. Update `flow-state.yaml → last_scan_ts` to now
6. Print at most one line: `SweetClaude observing.` — nothing else

**Commit message classification patterns:**

| Pattern | Issue type assigned |
|---|---|
| Starts with `fix:`, `fix(`, `bugfix` | bug |
| Starts with `feat:`, `feat(`, `add:` | story |
| Starts with `chore:`, `chore(`, `refactor:`, `docs:` | chore |
| Starts with `spike:`, `research:`, `poc:` | spike |
| No match | story (default) |

**Branch name classification patterns:**

| Prefix | Action |
|---|---|
| `feature/*`, `feat/*` | Annotates the inferred issue derived from the branch's commits |
| `fix/*`, `bugfix/*` | Sets type=bug on the inferred issue |
| `chore/*`, `refactor/*` | Sets type=chore |
| `spike/*`, `poc/*` | Sets type=spike |

### 3.2 PostToolUse inference

Triggered on `Write` and `Edit` tool completions. Scoped to the file that was just modified.

```
PostToolUse: Write | Edit
→ scan modified file for TODO/FIXME/HACK/XXX comments
→ for each found comment:
    evidence = "{filepath}:{line}"
    if no existing inferred issue has evidence = this evidence:
      sc_artifact_create issue {
        title: <comment text, truncated to 80 chars>,
        type: chore,  # default; user can reclassify
        status: backlog,
        source: inferred,
        evidence: "{filepath}:{line}"
      }
→ no output to user — fully silent
```

**Dedup guard:** before creating any inferred artifact, query `sc_artifact_query issue source=inferred evidence={evidence}`. If a result exists, skip. This ensures re-editing the same file doesn't create duplicate inferred issues.

### 3.3 Inferred artifact lifecycle

Inferred artifacts start as draft candidates, not confirmed work items. When the user runs `project-issues` or `project-backlog` in Flow mode, they see:

```
18 inferred issues ready for review.
Run: project-backlog review-inferred
```

During review, the user can:
- **Promote:** set `source=manual`, edit title/type/priority as needed
- **Discard:** set `status=cancelled`
- **Defer:** leave as `source=inferred` for the next review session

**`flow-state.yaml` schema:**

```yaml
last_scan_ts: "2026-05-03T09:00:00Z"
last_commit_scanned: "abc1234"
inferred_count: 18
reviewed_count: 3
```

---

## 4. Mode-Shift Mechanics

### 4.1 Snapshot format

Before any mode transition, the current state is snapshotted to `{state_base}/snapshots/SNAPSHOT-NNN-{date}/`.

**Snapshot contents:**

```
SNAPSHOT-NNN-{date}/
  manifest.yaml        # snapshot metadata
  phase.yaml           # copy of current phase.yaml
  scope.yaml           # copy of scope.yaml if present
  project-index.json   # copy of current index
  issues-export.md     # all issues, one per section (Markdown backend: copy; SQLite: exported)
  epics-export.md      # all epics
  sprints-export.md    # all sprints
  roadmap-export.md    # all roadmap items
```

**`manifest.yaml`:**

```yaml
snapshot_id: SNAPSHOT-003
created_at: "2026-05-03T14:00:00Z"
trigger: mode_shift
from_mode: kanban
to_mode: agile
artifact_counts:
  issues: 24
  epics: 0
  sprints: 0
  roadmap_items: 6
```

Snapshots are never deleted automatically. They are the rollback point if a mode shift goes wrong.

### 4.2 Transition sequence

Executed by `project-mode shift <target_mode>`:

```
1. Validate: can we shift from current_mode → target_mode?
   - Any mode → any mode is permitted EXCEPT: agile_enterprise → flow (too much data loss)
   - agile_enterprise → flow requires explicit --force flag and double confirmation

2. Create snapshot (§4.1)

3. Determine artifact delta:
   - Upshift (more structure): which new entity types become available?
   - Downshift (less structure): which entity types are being retired?

4. For downshift — archive retired entities:
   - Pitches (Shape Up → other): set status=cancelled on all draft pitches
   - Sprints (Agile → Kanban): set status=cancelled on all planned sprints; 
     move in-progress sprint issues to backlog (sprint_id=null)
   - No data is deleted — archiving is always soft

5. Update phase.yaml:
   - Set mode = target_mode
   - Set mode_set_at = now
   - Append entry to mode_history with snapshot_id
   - Set storage_backend per mode defaults:
     - flow/kanban/shape_up → markdown
     - agile → markdown (opt-in sqlite: user prompted)
     - agile_enterprise → sqlite (unless user explicitly opts out)

6. Regenerate project-index.json

7. Print transition summary:
   "Mode shifted: {from} → {to}
    Snapshot: SNAPSHOT-NNN-{date}
    Artifacts archived: {list}
    Artifacts now available: {list}"
```

### 4.3 Storage backend migration (Markdown ↔ SQLite)

Triggered when `storage_backend` changes, independent of mode shift.

**Markdown → SQLite:**
1. Read all `.md` files via `sc_artifact_list` for each type
2. `INSERT` each into the SQLite database
3. Verify row counts match file counts
4. Set `storage_backend: sqlite` in `phase.yaml`
5. Keep `.md` files as read-only historical record (do not delete)

**SQLite → Markdown:**
1. `SELECT * FROM {table}` for each entity type
2. Write each row as a `.md` file using the standard template
3. Rebuild `project-index.json`
4. Set `storage_backend: markdown` in `phase.yaml`

Both directions are idempotent — can be re-run safely if interrupted.

---

## 5. Skill Architecture

### 5.1 Skill interaction map

```
project-scope
  ├── sc_artifact_read/write scope
  └── on change: surfaces cascade review prompt for roadmap + sprints

project-milestones
  ├── sc_artifact_create/read/write/list milestone
  └── on milestone achieved: checks if any release.milestone_id references it

project-roadmap
  ├── sc_artifact_create/read/write/list roadmap_item
  ├── sc_artifact_list release
  └── calls product-roadmap-analysis (optional, on demand)

project-epics
  ├── sc_artifact_create/read/write/list epic
  └── sc_artifact_query issue epic_id=<id>  (to show membership)

project-issues
  ├── sc_artifact_create/read/write/list issue
  ├── sc_artifact_list epic  (for epic selection on create)
  └── sc_artifact_list sprint  (for sprint assignment on create)

project-backlog
  ├── sc_artifact_query issue sprint_id= status=backlog  (backlog view)
  ├── sc_artifact_write issue sprint_id=<SP-NNN>  (promote to sprint)
  └── calls project-backlog-triage  (optional, on demand)

project-sprints
  ├── sc_artifact_create/read/write/list sprint
  ├── sc_artifact_query issue sprint_id=<id>  (sprint board view)
  ├── sc_artifact_write issue sprint_id=<next>  (carry-over on sprint close)
  └── sc_artifact_create issue_sprint_history entry  (on status change)

project-mode
  ├── reads phase.yaml
  ├── sc_artifact_list <all types>  (for assess mode)
  └── executes transition sequence (§4.2)  (for shift mode)

project-backlog-triage
  └── sc_artifact_query issue sprint_id= status=backlog  (backlog view)
  └── sc_artifact_write issue priority/effort/status  (triage output)

product-roadmap-analysis
  └── sc_artifact_list roadmap_item
  └── sc_artifact_list milestone  (for alignment check)
  └── sc_artifact_write roadmap_item priority  (stack-rank output)
```

### 5.2 project-backlog-triage — session design

A structured grooming session. Surfaces ungroomed issues one at a time and applies INVEST criteria + t-shirt sizing.

**Entry conditions:**
- Backlog must have at least one issue with `priority IS NULL OR effort IS NULL`
- Otherwise: "Backlog is already groomed. Nothing to triage."

**Session flow:**

```
1. Load backlog: sc_artifact_query issue sprint_id= status=backlog
2. Sort: ungroomed (missing priority or effort) first, then by created_at ASC
3. For each ungroomed issue:
   a. Display: title, type, description (first 3 lines), current priority/effort
   b. Apply INVEST check silently — flag any issues:
      - Independent? (does it depend on another unscheduled issue?)
      - Negotiable? (is the description prescriptive about implementation?)
      - Valuable? (does it have acceptance criteria or a clear outcome?)
      - Estimable? (is there enough information to size it?)
      - Small? (stories should be completable in one sprint)
      - Testable? (can acceptance criteria be verified?)
   c. Present recommendation:
      Priority: [recommended] — reasoning
      Effort:   [recommended] — reasoning
      INVEST flags: [list or "clean"]
   d. User responds: accept | override | skip | split
   e. On accept/override: sc_artifact_write issue {priority, effort, status: ready}
   f. On split: create two new issues from this one, cancel the original

4. Session summary:
   Groomed: N issues
   Flagged: N issues (INVEST concerns noted)
   Skipped: N issues
   Split: N issues → N new issues
```

**INVEST sizing heuristics (for effort recommendation):**

| Signals | Recommended effort |
|---|---|
| One acceptance criterion, trivial change | xs |
| 2–3 acceptance criteria, clear implementation path | s |
| 4–6 acceptance criteria, some unknowns | m |
| Multiple subsystems touched, integration work | l |
| Architectural change or significant unknowns | xl |
| Should probably be an epic, not an issue | xxl → prompt to convert |

### 5.3 product-roadmap-analysis — session design

A prioritization session using RICE scoring followed by human judgment stack-rank. Lives in Product because roadmap priority is a product decision — it balances business value, not just technical effort.

**Entry conditions:**
- Roadmap must have at least 2 items with `status IN (idea, planned)`
- Otherwise: "Roadmap has fewer than 2 active items to analyze."

**Session flow:**

```
1. Load roadmap: sc_artifact_query roadmap_item status=idea,planned
2. Load milestones: sc_artifact_list milestone  (for alignment check)
3. For each roadmap item, compute RICE score:

   RICE = (Reach × Impact × Confidence) / Effort

   Reach:      How many users/sessions affected per period?
               Estimated from: item type, description, linked milestones
               Scale: 1–10

   Impact:     How much does it move the needle per user?
               massive=3, high=2, medium=1, low=0.5, minimal=0.25
               Inferred from: rationale field, milestone alignment

   Confidence: How confident are we in these estimates?
               High=1.0, Medium=0.8, Low=0.5
               Based on: how well-defined the item is

   Effort:     Development months (proxy: roadmap item type)
               major_feature=3, minor_feature=1, enhancement=0.5, sunset=0.5

4. Present RICE-sorted list with scores and reasoning

5. Check milestone alignment:
   - Flag any milestone with no roadmap items contributing to it
   - Flag any roadmap item with high priority but no milestone connection

6. Present proposed stack-rank for user review:
   "Here's the RICE-ranked list. Review top-3 ordering — RICE is input to judgment,
    not a final answer. Adjust as needed."

7. On user confirmation: sc_artifact_write roadmap_item priority for each item
```

---

## 6. Entity ID Assignment

**Responsibility:** the storage adapter's `sc_artifact_create` function. Skills never assign IDs.

**Algorithm (Markdown backend):**

```bash
# For type "issue" → prefix "I", directory "issues/"
next_id() {
  local prefix=$1
  local dir=$2
  local max=0
  for f in "${dir}/${prefix}"-*.md; do
    n=$(echo "$f" | grep -oE '[0-9]+' | tail -1)
    [ "$n" -gt "$max" ] && max=$n
  done
  printf "%s-%03d" "$prefix" $((max + 1))
}
```

**Prefix → type mapping:**

| Prefix | Entity type |
|---|---|
| `I` | issue |
| `EP` | epic |
| `SP` | sprint |
| `RM` | roadmap_item |
| `REL` | release |
| `MS` | milestone |
| `PITCH` | pitch |
| `SNAPSHOT` | snapshot (not an artifact type, managed by project-mode) |

**Collision safety:** the algorithm reads the filesystem at assignment time. Concurrent writes in the same session are not expected (single-user, single-skill execution), but if two skills ran simultaneously and both computed `I-042`, the second write would overwrite the first. Acceptable for v1 — note as a known limitation.

---

## 7. Migration Script Design

The migration script converts the SweetClaude project's existing `MS-NNN` and `BL-NNN` files to the v1.2 data model format.

**Script:** `scripts/migrate-project-artifacts.sh`

**Inputs:** existing files at `.sweetclaude/product/milestones/` and `.sweetclaude/product/backlog/`

**Operations:**

```
Phase 1 — Milestone conversion
  For MS-001: reformat metadata to v1.2 template (add Criteria, mode_introduced)
  For MS-002, MS-003, MS-004:
    Rename to RM-NNN in roadmap/ directory
    Remap type: derive from content (MS-002/003 → major_feature, MS-004 → major_feature)
    Set status: planned
    Add rationale: section (stub — human fills in)
    Add mode_introduced: agile

Phase 2 — Backlog item conversion
  For each BL-NNN.md:
    Assign next I-NNN ID
    Move to issues/ directory as I-NNN-{slug}.md
    Add Status: backlog
    Add Sprint: (none)
    Map existing Priority field:
      high → sooner
      medium → soonish
      low → later
      (none) → soonish  # default
    Add Effort: m  # default stub — human corrects in triage
    Map existing Type field:
      feature → story
      enhancement → story
      bug → bug
      chore → chore
      spike → spike
      debt → chore
      sunset → chore
      (none) → story  # default
    Add mode_introduced: agile
    Keep body sections intact

Phase 3 — Index rebuild
  Rebuild MILESTONES-INDEX.md (remove converted MS-002/003/004)
  Create ROADMAP-INDEX.md (new)
  Create ISSUES-INDEX.md (all migrated I-NNN files)
  Rebuild project-index.json

Phase 4 — Cross-reference update
  Scan all .md files for references to BL-NNN and MS-002/003/004
  Replace with corresponding I-NNN and RM-NNN IDs
  Log all replacements to migration-report.md
```

**Dry-run mode:** `--dry-run` flag prints all intended operations without writing anything.

**Idempotency:** the script checks whether each target file already exists before writing. Re-running is safe.

**Output:** `scripts/migration-report.md` listing every file renamed, every ID reassigned, every cross-reference updated.

---

## 8. Open Technical Decisions

1. **`sc-artifact.sh` distribution:** These shell functions need to be sourced by skills at runtime. Current mechanism: skills source `~/.claude/hooks/sweetclaude/sc-artifact.sh`. This assumes the install path. When the skill runner is not in that path (e.g., different OS, non-standard install), sourcing fails silently. Resolution: add an existence check at the top of every Project skill and surface a clear error if the adapter is missing.

2. **SQLite binary availability:** The SQLite backend calls `sqlite3`. This is pre-installed on macOS but not always present on Linux. The adapter should check `command -v sqlite3` on first use and fall back to Markdown with a warning rather than crashing.

3. **project-index.json concurrency on create:** Documented in §6 as a known v1 limitation. If this becomes a real problem (unlikely for solo dev), a lock file (`project-index.json.lock`) pattern is the minimal fix.

4. **`project-mode assess` output format:** The assess sub-command reads all artifact counts and the current mode, then recommends whether to shift. The decision criteria ("recommend upshift when issue count > 50 and sprint usage is consistent") need to be defined before implementing the assess logic.

5. **Flow mode opt-out:** Currently, Flow mode inference runs silently. There is no per-session or per-directory opt-out short of disabling SweetClaude entirely. A `flow_inference: false` flag in `phase.yaml` would provide finer control without a full mode shift — worth adding before v1 ships.
