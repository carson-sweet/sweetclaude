# v4 Caucus Findings — 2026-05-12

**Status:** Revision pass complete + lightweight follow-up caucus pass complete. All Critical and Warning findings resolved. 4 follow-up bugs in v2.0 revisions identified and fixed:
- Backup integrity check double-prefix path bug (Step 1c)
- Stale-lock removal instruction had bogus `rmdir`+`rm -rf` ordering (Step 1a)
- Step 8b atomic finalize rename order was backwards (corrected: `sweetclaude.yaml` LAST)
- Auto-restore read pre-existence flag AFTER restoring `.sweetclaude/`, losing it (corrected: snapshot first)

Plus 8 smaller gaps closed:
- `docs/product/` pre-existence now captures a snapshot tarball, not just a flag
- `active → active` added to v3→v4 status mapping table
- EP-MISC-general (non-numeric) counter recovery handling specified
- Sprint artifacts removed from Phase 1 bootstrap detection; deferred to Phase 2 with MIGRATION-MAP `Skipped` entries
- `docs/product/backlog/SCHEMA.md` marked non-normative with pointer to canonical
- Stale "TODO: create" for sprint template removed from schema cross-references
- Schema §6 opening sentence now mentions milestone counter
- Step 7b in-memory snapshot replaced with explicit "extract from backup" spec

**Status:** Action required — v4 docs are not ready for implementation
**Caucus rounds reviewed:** Five parallel reviewers (architecture, code/logic, security, tests, ecosystem)
**Source docs:**
- `/Users/carsonsweet/dev/sweetclaude/docs/internal/v4-story-system-design-2026-05-10.md` (v1.2)
- `/Users/carsonsweet/dev/sweetclaude/docs/internal/v4-migration-spec-2026-05-10.md` (v1.3)
- `/Users/carsonsweet/dev/sweetclaude/docs/internal/v4-story-schema.md`
- `/Users/carsonsweet/dev/sweetclaude/docs/internal/v4-story-template.md`
- `/Users/carsonsweet/dev/sweetclaude/docs/internal/v4-smoke-test-2026-05-10.md`

---

## Why this caucus happened

The v4 docs were marked "Approved — ready for implementation" after two prior caucus rounds (C1–C38). Those rounds focused on migration safety. The user requested a third round before implementation began. This round looked at the broader system: structural integrity, schema consistency, skill ecosystem impact, test coverage, and user communication. It found ~25 distinct issues across all severities.

The prior caucuses are not invalidated — their safety mechanisms (backup, validation manifest, auto-restore, atomic finalize) are largely sound. But the system around those mechanisms has gaps.

---

## Critical findings (12)

These must be resolved before implementation starts. Each represents either silent data loss risk, breaking-change-not-acknowledged-as-breaking, or "the day-one v4 experience is broken."

### C1. Schema is defined in four places with irreconcilable conflicts

The story schema appears in four documents with different allowed values:

| Field | story-system-design v1.2 | v4-story-schema.md | SCHEMA.md | template |
|---|---|---|---|---|
| `priority` | `next · sooner · soon · later · someday` (5) | `now · soon · later` (3) | `next / sooner / soon / later / someday` | `soon` example |
| `effort` | `xs · s · m · l · xl · xxl` (6) | `s · m · l · xl` (4) | — | — |
| `origin` | `manual · inferred · imported` | `manual · imported · generated` | — | `manual` |

The schema reference doc (`v4-story-schema.md`) is most likely to be loaded by an implementer because its title says "Reference." Building skill validation against it produces incompatible data with skills built from the design doc.

**Recommended fix:** Designate exactly one normative schema document. Mark the others "non-normative; see {canonical}.md" or delete them. The canonical doc should be embedded by reference in the design and migration specs rather than restating allowed values.

### C2. Sprint files referenced but never defined

Story schema has `sprint: SPRINT-003`. Agile mode hard-blocks without sprints. The design doc says "sprint files live in the roadmap under the epic or milestone directory" — but:
- No filename pattern (the design says `SPRINT-003`; every existing skill uses `SP-NNN`)
- No frontmatter spec
- No body sections spec
- No directory location shown in the directory tree
- No counter mechanics (counter recovery covers story/bug/debt/chore only)
- No migration path for v3 sprint artifacts (Step 5 of migration spec migrates only `BL-NNN-*.md`)

**Recommended fix:** Add a "Sprint File Schema" section to the design doc covering filename, location, frontmatter, body, counter. Reconcile SPRINT-NNN vs SP-NNN before any user sees v4. Add sprint-artifact migration to the migration spec Step 5.

### C3. Backup lives inside the migration blast radius

Backup writes to `.sweetclaude/state/backups/`. This is:
- Inside the directory being migrated
- Destroyable by Option 2 "Reset framework state" (which says "only `.sweetclaude/` state files are reset")
- The user's stated "only recovery option" per the delete-offer warning at Step 8.4

If the user takes Option 2 from the failure menu, they may destroy their only backup along with the framework state.

**Recommended fix:** Require a second backup at a path outside the project (e.g., `~/.sweetclaude/backups/{project-slug}/`). Explicitly exclude `.sweetclaude/state/backups/` from Option 2's scope. Surface both backup locations in the delete-offer warning.

### C4. Option 2 can destroy irreplaceable, non-recreatable state

The failure menu Option 2 ("Reset framework state") says it touches only "`.sweetclaude/` state files." But `.sweetclaude/state/` contains:
- `decision-log.md` — irreplaceable, not derivable from `docs/`
- `improvement-register.md` — irreplaceable, not derivable from `docs/`
- `assumption-register.md` — irreplaceable
- `scope-changes.md` — irreplaceable

The design doc says these are "not recreatable from project docs" but the failure-menu spec offers Option 2 without enumerating what it deletes.

**Recommended fix:** Option 2 must display a full file manifest of what it will delete (not a category description) and require explicit confirmation. Files that are user-authored content (decision log, improvement register, assumption register, scope changes) must be excluded by default.

### C5. `tar -tzf` is not sufficient backup integrity validation

`tar -tzf` lists the archive table of contents — it verifies the header is readable. It does not decompress data blocks. A backup that passes `tar -tzf` can still be corrupt. The migration spec uses this as the only gate before offering the irreversible delete in Step 8.4.

**Recommended fix:** Add test extraction of at least 3 randomly sampled files (`tar -xzf --to-stdout`) before allowing the delete offer. Confirm extracted sizes are nonzero. Optionally verify a content hash for at least one known file (e.g., a recently-modified `BL-NNN-*.md`).

### C6. Auto-restore doesn't clean up `docs/product/` orphans

The backup captures `.sweetclaude/` only. The migration writes to `docs/product/`. If migration fails mid-Step-5 or Step-7, auto-restore restores `.sweetclaude/` correctly but leaves orphan files in `docs/product/`. The failure menu's claim "project has been restored to its previous state" is false.

**Recommended fix:** Record whether `docs/product/` existed before migration. Auto-restore must either (a) delete `docs/product/` if it did not pre-exist, or (b) restore its pre-migration contents from a separate captured snapshot. Spec language must match what the implementation actually does.

### C7. Step 8 finalize is not atomic

Step 8.1 writes `artifact-privacy.yaml`. Step 8.2 writes `sweetclaude.yaml`. The spec says 8.1 triggers auto-restore on failure but does not address 8.1-succeeds-8.2-fails. That state has the new path active in artifact-privacy but the old version in framework state.

**Recommended fix:** Either write both files in a single transaction (temp + atomic rename pair), or write `sweetclaude.yaml` first so the version bump is the commit point and `artifact-privacy.yaml` is rolled back on failure. Make the atomicity claim true.

### C8. Verification doesn't confirm all source files were processed

Step 7 verifies "every file just written" — output-side only. If a source file was scanned in Step 2, passed validation, was counted in the preview, but was silently dropped during Step 5 (write error not propagated, duplicate-ID collision, mis-routed type), Step 7 passes because every written file is correct. The dropped file simply doesn't appear.

**Recommended fix:** Step 2 produces a manifest of source files with expected output paths. Step 7 reconciles: `source_count == written_count` per type and per active/done scope. Shortfall is a migration failure that triggers auto-restore.

### C9. `.gitignore` conflict on SweetClaude itself (and similar repos)

SweetClaude's own `.gitignore` excludes `/docs/*` except `/docs/README.md` and `/docs/user-guide/`. v4 puts product data under `docs/product/`. On this repo (and any repo using a similar denylist pattern), migration would silently gitignore all product data including `MIGRATION-MAP.md` — the only record mapping `BL-NNN` to new IDs.

This affects the SweetClaude maintainer first (dogfooding) and any open-source project with a similar pattern.

**Recommended fix:** Migration spec must run `git check-ignore docs/product/INDEX.md` (or equivalent) before proceeding. If ignored, hard-stop with a tailored message showing a suggested allowlist patch (`!/docs/product/`). Add to release gates: "Migration tested against a repo with `/docs/*` denylist gitignore pattern."

### C10. Phase 1 scope phrase hides ~12 skills that must change

The migration spec says Phase 1 is "Backlog system — file structure, migration skill, updated backlog/issue skills." This phrase encompasses 3 skills literally (project-issues, project-backlog, project-backlog-triage). It excludes:

**Day-one breakage if not updated:**
- `status/SKILL.md` — globs `backlog/BL-*.md`; renders empty post-migration
- `go/SKILL.md` — same glob; greps git log for `BL-[0-9]+`
- `big-picture/SKILL.md` — `ls ${product_base}/backlog/BL-*.md`; parses `BL-\d+` regex throughout
- `recap/SKILL.md` — reads `paths.product_base`; misses roadmap stories

**Also affected:**
- `project-sprints/SKILL.md` — 22 `sc-artifact.sh` source calls; needs full rewrite
- `project-epics/SKILL.md` — 10 sourcing calls; references `I-NNN`
- `project-gh-import-issues/SKILL.md` — description still says "I-NNN artifacts"
- `project-gh-sync-issues/SKILL.md` — description says "I-NNN issues"
- `epic-design/SKILL.md` — writes to `{product_base}/stories/` which doesn't exist in v4
- `fix-sweetclaude/SKILL.md` — owns an entire path-ownership table that's structurally wrong post-v4
- `code-feature`, `code-issue`, `code-tdd` — branch naming, commit prefixes use BL-NNN convention
- `product-sprint-plan/SKILL.md`

**Recommended fix:** Replace the "updated backlog/issue skills" phrase with an explicit skill inventory split by phase. Phase 1 must include the orientation read-side skills (status, go, big-picture, recap) so day-one experience works. Phase 2 owns the roadmap-side rewrites.

### C11. No v3-style ID lookup affordance

After migration, typing `BL-046` resolves to nothing. MIGRATION-MAP.md is a read-only table users must manually consult. Git history, PR descriptions, commit messages, and branch names referring to `BL-NNN` become orphaned identifiers.

**Recommended fix:** `project-issues view BL-NNN` (and similar lookups) must detect the v3-style prefix and auto-resolve via MIGRATION-MAP.md. The finalize report and bootstrap completion message should point users to the lookup behavior.

### C12. EP-999 simultaneously removed and reused

Design doc line 27: "EP-999 concept — Removed entirely."
Design doc line 142+: `EP-999-general-misc` exists as a per-milestone roadmap fallback epic.

Same ID, two different meanings. A user who reads the v4 announcement seeing "EP-999 removed" and then finds `EP-999-general-misc/` in their roadmap will be confused — did the migration leave it?

Additionally: if a project legitimately reaches 999 epics (unlikely but not impossible), there's an ID collision with no detection.

**Recommended fix:** Rename the fallback. `EP-DEFAULT-general` or `EP-MISC-general` or just `epic-misc/` (no number) — anything that doesn't reuse the literal `EP-999` string.

---

## Warning findings (10)

These should be fixed before public ship but don't block implementation start.

### W1. Counter-recovery silently resolves duplicate-ID violations via `max()`

If the same `TYPE-NNN` filename appears in both backlog and roadmap, counter recovery picks `max(N)` and moves on. The data integrity violation (same ID in two places) is undetected.

**Fix:** During recovery, if a `TYPE-NNN` stem appears in both backlog and roadmap, halt with a fatal inconsistency report.

### W2. Concurrent skill invocations can produce duplicate IDs

INDEX.md counter is read-increment-written without locking. Two simultaneous story-creation operations can both read counter=7 and both write `STORY-008`.

**Fix:** Story creation requires file-level lock on INDEX.md, or uses atomic counter increment (write to temp + rename). Document the contract.

### W3. Slug uniqueness not enforced

The slug algorithm doesn't check for collisions. Two stories with similar titles can produce identical slugs after truncation.

**Fix:** Slug generation checks for existing `TYPE-NNN-<slug>.md` files (all types, both backlog and roadmap). On collision, append `-2`, `-3`, etc.

### W4. v3 status mapping is incomplete

Migration spec remaps `backlog` → `new` and `cancelled` → `abandoned`. The v3 schema uses `in_progress` and `in_review` (visible in `project-issues/SKILL.md`). Neither is in the remap table. A story with `status: in_progress` would carry an invalid status into v4.

**Fix:** Add `in_progress` → `active` and `in_review` → `active` (or define explicitly). Pre-migration validation must check status against the full v3 enum.

### W5. Lock file check-then-write has a race

`[ -f $LOCK_FILE ]` followed by `echo ... > $LOCK_FILE` is not atomic. Two sessions starting within a sub-second window can both pass the check.

**Fix:** Use `set -o noclobber` with `>|`, or `mkdir` (atomic on POSIX). The lock acquisition must be atomic at the filesystem level.

### W6. Skipped done items become unreadable orphans

If the user skips done items in Step 3, those v3 files remain in `.sweetclaude/product/backlog/`. The health check rule explicitly excludes them ("active and future stories have been migrated"). No v4 skill can read them. MIGRATION-MAP.md doesn't list them.

**Fix:** The skip decision must log skipped items in MIGRATION-MAP.md (with `migrated: no` rows). Alternatively, offer "Migrate done items to a read-only archive" — full v4 format with `status: done` in `done/`, no counter increment.

### W7. Bootstrap hard-stop fires forever if user declines cleanup

Step 8.4 offers to delete `.sweetclaude/product/backlog/`. If declined, v3 files remain. The bootstrap hard-stop detects v3 by file presence — so the hard-stop fires on every subsequent session.

**Fix:** Bootstrap detection must use a state flag (e.g., `framework.v4.migration_completed: true` in `sweetclaude.yaml`), not file presence. The cleanup decline is a user choice and shouldn't trigger perpetual blocking.

### W8. `.gitignore` offer framing is misleading

The design doc says the `.gitignore` offer is "especially relevant for open-source repos." Closed-source repos with cloud SCM hosting also have data exposure concerns. Product roadmaps, backlog items describing unshipped security work, and competitive strategy are all committable by default.

**Fix:** Offer at all projects regardless of public/private status. Reframe the prompt to describe what data would be committed if not ignored.

### W9. Release gates are weak

- "Migration tested on at least one real v3 project" — one project, no required checklist, no evidence artifact
- All three listed candidate projects are the author's own
- No multi-project rollout testing
- No `.gitignore` testing
- No CHANGELOG.md exists yet (release gate item, not just an entry to write)

**Fix:** Specify minimum 2-3 projects from distinct user contexts, a required verification checklist, and the evidence artifact (e.g., a migration log file committed under `docs/internal/v4-release-evidence/`).

### W10. `sweetclaude:migrate` vs `sweetclaude:_migrate` naming mismatch

The bootstrap hard-stop message tells users to run `/sweetclaude:migrate`. The bootstrap skill itself invokes `sweetclaude:_migrate` (with underscore). Either there's a new public migrate skill, or the message is wrong.

**Fix:** Reconcile. Either create a public `sweetclaude:migrate` skill that wraps `_migrate`, or update the hard-stop message.

---

## Other warnings (briefly)

- **`migrate-diagnose` marked "not user-invocable" without enforcement.** No `internal: true` flag exists in the skill registry. (architecture #10)
- **MIGRATION-MAP.md in `docs/product/backlog/` is a non-story file in a story directory.** Skills globbing `docs/product/backlog/*.md` will encounter it. Move to `docs/product/MIGRATION-MAP.md`. (architecture #11)
- **Auto-restore atomicity unspecified.** No recovery path for interrupted restore. (security #4)
- **"Backlog and roadmap completely separate" is convention only.** No write-time enforcement. (code-reviewer #12)
- **Roadmap `done/` is flat per-epic; backlog `done/` is per-type.** Inconsistency not called out; counter-recovery glob doesn't cover roadmap done/. (architecture #8, code-reviewer #13–14)
- **Backup retention deletes oldest before new is verified.** Race window where neither backup is valid. (security info-2)
- **Status/directory consistency only checked by health check.** No write-time enforcement contract. (code-reviewer #11)
- **`tar -czf` includes the destination archive in its own input.** Self-referential archive risk. (code-reviewer #9)
- **Validation manifest doesn't check filename↔frontmatter ID consistency.** (code-reviewer #10)
- **`planning-concepts.md` referenced but doesn't exist.** Design doc says it must be updated; file isn't in the repo. (ecosystem #3)
- **No documentation rollout plan.** Per-skill docs mandate exists but where/when/format is unspecified. (ecosystem #10)
- **BOM/CRLF normalization specified but no test fixture exists.** (tests #6)
- **"Show me each story" pagination unimplemented and untested.** (tests #12)

## Nits

- **Counter recovery scans roadmap which doesn't exist until Phase 2.** Phase-aware annotation needed. (architecture #3)
- **Story template only shows the story type body sections.** Incomplete reference. (architecture #12)
- **`v3-final` branch push assumes `origin` remote exists.** (code-reviewer #18)
- **Lock file PID is shell PID.** Insufficient session identity for stale-lock diagnosis. (security info-1)
- **No v4 forward-compat policy.** What guarantees v4.0 stories remain readable after v4.x changes? (tests #15)

---

## Revision plan

This section lists the changes the v4 source docs need. The revision pass produces a new version (v1.3 / v2.0) of each doc.

### `v4-story-system-design-2026-05-10.md`

1. Add **Sprint File Schema** section (addresses C2). Specify filename, location, frontmatter, body, counter. Reconcile SPRINT-NNN vs SP-NNN.
2. Rename `EP-999-general-misc` to a non-numeric or different-prefix slug (addresses C12).
3. Replace `EP-999` reference in line 41 (`planning-concepts.md must be updated`) with the actual file to update, OR add a release-gate item to create it (addresses ecosystem #3).
4. Add a **Concurrency** section covering INDEX.md write protocol, atomic counter increment, slug uniqueness check (addresses W2, W3).
5. Strengthen the "backlog and roadmap completely separate" rule with a write-time enforcement contract (addresses code-reviewer #12).
6. Reconcile roadmap `done/` structure with backlog `done/` (per-type vs flat-per-epic) — pick one and apply consistently (addresses architecture #8, code-reviewer #13–14).
7. Update counter recovery glob to handle the chosen roadmap done/ structure.
8. Reframe the `.gitignore` offer (addresses W8).
9. Add a **Documentation Plan** section (addresses ecosystem #10).
10. Mark this doc as canonical schema source; remove duplicate schema text from other docs (addresses C1).

### `v4-migration-spec-2026-05-10.md`

1. Move backup to `~/.sweetclaude/backups/{project-slug}/` plus retain in-tree copy (addresses C3, C6).
2. Add `.gitignore` detection to Step 1 (addresses C9).
3. Strengthen `tar -tzf` validation with test extraction (addresses C5).
4. Add input/output reconciliation to Step 7 (addresses C8).
5. Make Step 8 truly atomic (single transaction or write-order swap) (addresses C7).
6. Document Option 2 file manifest, exclude user-authored state files (addresses C4).
7. Add `in_progress` and `in_review` to status remap table; check against full v3 enum in Step 2 (addresses W4).
8. Replace check-then-write lock with `mkdir`-based atomic lock (addresses W5).
9. Add filename↔frontmatter ID consistency check to Step 2 (addresses code-reviewer #10).
10. Add MIGRATION-MAP.md "skipped items" section (addresses W6).
11. Switch bootstrap hard-stop detection to state flag, not file presence (addresses W7).
12. Reconcile `sweetclaude:migrate` vs `sweetclaude:_migrate` naming (addresses W10).
13. Move MIGRATION-MAP.md out of `docs/product/backlog/` (addresses architecture #11).
14. Strengthen release gates: multi-project, required checklist, evidence artifact (addresses W9).
15. Replace single-project "Migration tested on at least one real v3 project" gate with multi-project, with explicit per-project checklist.
16. Add release-gate items: CHANGELOG.md created, `.gitignore` denylist case tested, gitignore-detection case tested.

### `v4-story-schema.md` and `SCHEMA.md`

1. Pick one as canonical, delete or mark the other non-normative (addresses C1).
2. Update to match `v4-story-system-design-2026-05-10.md` exactly.
3. Add `origin: inferred` (currently has `generated`) — reconcile with design doc.

### `v4-story-template.md`

1. Add body sections for all four story types (story, bug, debt, chore) (addresses architecture #12).

### `v4-smoke-test-2026-05-10.md`

1. Convert PENDING manual verifications 4–7 into automated test specifications.
2. Add BOM/CRLF fixture tests.
3. Add counter recovery test scenarios (both backlog-only and post-promotion).
4. Add `.gitignore`-denylist fixture test.
5. Add input/output reconciliation test (deliberately corrupt one written file post-Step-5).

### New documents needed

- `docs/user-guide/v4-migration-guide.md` — user-facing migration guide (referenced in release gates but not specified).
- `docs/user-guide/planning-concepts.md` — referenced in design doc; doesn't exist.
- `docs/internal/v4-sprint-schema.md` — if sprint schema is added as a standalone doc rather than inline in story-system-design.
- `CHANGELOG.md` — net-new file, release gate.

---

## Recommended revision sequencing

1. **Resolve C1 first (schema reconciliation).** Pick canonical source. Update all four docs to match. This unblocks downstream revisions because the data shape is settled.
2. **Resolve C2 second (sprint schema).** This is the largest schema gap and affects multiple skills' Phase 1 scope.
3. **Resolve C10 third (Phase 1 skill inventory).** Without this, the migration spec's phasing is undefined.
4. **Then resolve all data-safety criticals (C3–C9, C11).** These are tractable individual fixes once the schema is locked.
5. **Then resolve structural criticals (C12).**
6. **Warnings as a batch.** Many are independent and can be addressed in parallel during the revision pass.

The full revision pass produces:
- Updated `v4-story-system-design-2026-05-10.md` → likely renamed `v4-story-system-design-v2-{revision-date}.md` or similar
- Updated `v4-migration-spec-2026-05-10.md` → same
- Reconciled schema docs (one canonical, others removed)
- New `v4-sprint-schema.md` (if separate)
- New `v4-migration-guide.md` (user-facing)
- New `planning-concepts.md` (user-facing) or removal of the reference

After revisions, a final caucus pass on the revised docs would be lower-cost than this one because the structural issues are settled.
