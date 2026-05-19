---
id: BLAST-304
story: STORY-304
title: "Blast Radius and Impact Analysis — STORY-304"
date: 2026-05-19
status: resolved
---

# Blast Radius: STORY-304 — Bash-based hook repair recovery procedure

## Summary

STORY-304 is a narrow but high-coordination story. It creates one standalone script, one test script, one user-invocable skill, and one new user-guide page (or, per SPEC-304, two new sections in a doc that another deferred story creates). The total surface in the repo is small (5 files affected — 3 created, 2 modified), but six cross-references must stay coherent: skill-count headings in two locations (README + skills-reference.md), backlog dependencies on STORY-301 (`hooks.bak/`) and STORY-306 (`hook-development.md`), the EP-010 epic completion-criteria array, and an unresolved spec/story divergence over the test script's location, name, structure, and number of test functions. The biggest standalone risk is the spec/story divergence — implementing one side will fail the verification grep of the other.

## Affected Areas

### 1. `scripts/emergency-hook-restore.sh`

- **What it is**: New standalone bash recovery script with zero SweetClaude dependencies. Resolves installed path via the same `installed_plugins.json` reader used by `scripts/sync-to-installed.sh` (lines 20-36), with a `find` fallback. Restores hooks from `hooks.bak/`, falling back to repo `hooks/` if no backup exists. Accepts optional bare hook filename argument.
- **Nature of impact**: NEW.
- **Specific change required**: Create file, make executable. Output contract constants pinned as `readonly` at top of file. `INSTALL_PATH` env var doubles as test back door (skips both `installed_plugins.json` resolution and the `$HOME/.claude/plugins/` prefix check). Uses `set -e` only — explicitly NOT `set -euo pipefail` (recovery script tolerates degraded conditions; see DESIGN-304 §4).
- **Risk level**: MEDIUM. The script writes to the live installed hooks path. The `INSTALL_PATH` back door deliberately disables the prefix-guard safety check — acceptable per design rationale (DESIGN-304 §5) since a caller who can set env vars already has equivalent powers, but the back door must be code-commented clearly so a future maintainer does not "harden" it and break tests.
- **Dependencies**: Depends on `~/.claude/plugins/installed_plugins.json` (read-only). Depends on STORY-301's `hooks.bak/` for full functionality (falls back to repo if absent). Path-resolution logic duplicates `scripts/sync-to-installed.sh`'s `_resolve_install_path()` — see Area 5.

---

### 2. `tests/test-emergency-restore.sh` — **RESOLVED (Option B, 2026-05-19)**

- **What it is**: Test script for the emergency restore script.
- **Nature of impact**: NEW.
- **Specific change required**: Create `tests/test-emergency-restore.sh` with four test functions: `test_restore_from_backup`, `test_fallback_to_repo`, `test_back_door_skips_prefix_check`, `test_dry_run_preview`. Uses `EMERGENCY_RESTORE_SOURCE_ONLY=1` sentinel sourcing to capture `CONTRACT_LINE_*` and `EHR_*` constants. The emergency script has `--dry-run` flag added (Option B). See SPEC-304 v2.1 for full script body.
- **Risk level**: LOW (resolved). Story implementation notes and acceptance criteria updated to match spec v2.1. CHORE-013 is not applicable — test is at `tests/` not `tests/hooks/`, so the glob in the gate won't pick it up; this is correct and intentional.
- **Dependencies**: Depends on Area 1. CHORE-013 does NOT apply to this file's location.

---

### 3. Test gate integration via `tests/test-hooks.sh` and `scripts/sync-to-installed.sh`

- **What it is**: The canonical pre-sync test gate. `scripts/sync-to-installed.sh:103-122` runs `bash tests/test-hooks.sh` and aborts on non-zero exit. Today, `tests/test-hooks.sh` has 22 inline tests but does NOT invoke any scripts under `tests/hooks/` — all 6 existing files in that directory run orphaned, manually only.
- **Nature of impact**: REFERENCED. STORY-304 does not modify these files. CHORE-013 ("Wire `tests/hooks/*.sh` into the pre-sync test gate") is the item that wires them in.
- **Specific change required**: None in STORY-304 directly. The test file resolved to `tests/test-emergency-restore.sh` (not `tests/hooks/`), so CHORE-013's glob (`tests/hooks/*.sh`) does not capture it. This is correct — the emergency restore test is not a hook test and should not be in the hooks test directory. CHORE-013 has no bearing on STORY-304.
- **Risk level**: LOW (resolved). The test at `tests/` is run directly by acceptance criteria verification (`bash tests/test-emergency-restore.sh`). No gate wiring needed.
- **Dependencies**: CHORE-013 is NOT applicable. Open Question 5 (CHORE-013 timing) is closed — the test location makes it moot.

---

### 4. `skills/hook-repair/SKILL.md`

- **What it is**: New user-invocable skill at `skills/hook-repair/SKILL.md`. Bash-only (never uses Write/Edit, since those may be blocked).
- **Nature of impact**: NEW.
- **Specific change required**: Create with `user-invocable: true` frontmatter, AGPL-3.0-or-later SPDX header, `!`-prefixed `record-event.sh` invocation, and a 5-step procedure (resolve → check backup → diagnose → propose via AskUserQuestion → restore + verify). Spec instructs to avoid description verbs like "automatically" or "whenever" — auto-invocation pattern-matching risk from MEMORY.md's `feedback_hibernate_explicit_only.md` lesson.
- **Risk level**: LOW. Additive. The skill is opt-in (user-invocable) and uses only Bash. The auto-invocation risk is mitigated by description wording per the spec's known-gaps section.
- **Dependencies**: Picked up automatically by `tests/test-skill-bash-blocks.sh` (line 20: `find "$REPO_ROOT/skills" -name "SKILL.md"`). All fenced bash blocks in the skill must pass `bash -n`. No registration required in `hooks/hooks.json` or `hooks-manifest.json` (skill, not hook). Skill count headings (Area 7) must be updated.

---

### 5. `installed_plugins.json` reader duplication

- **What it is**: The python3 one-liner that reads `~/.claude/plugins/installed_plugins.json`, filters for `scope == 'user'`, sorts by `lastUpdated` DESC, and picks the first entry with a `hooks/` subdir.
- **Nature of impact**: REFERENCED (and duplicated). This logic already lives in `scripts/sync-to-installed.sh:20-36` (`_resolve_install_path`) and `scripts/preflight.sh`. STORY-304's emergency script copies it inline (DESIGN-304 §5 implicit; SPEC-304 lines 132-146).
- **Specific change required**: None — duplication is intentional. The emergency script's "zero SweetClaude dependencies" design principle forbids sourcing helper functions.
- **Risk level**: MEDIUM. Three copies of the resolver drift independently. If the `installed_plugins.json` schema changes (new `scope` value, renamed `lastUpdated` field, etc.), all three must be updated. No automated test will catch the drift — the sync script and the emergency script both succeed against the current schema.
- **Dependencies**: All consumers depend on the schema. Not blocking, but worth noting in the decision log so the duplication is visible.

---

### 6. `hooks.bak/` dependency on STORY-301

- **What it is**: STORY-301 created `hooks.bak/` at the installed path during sync. STORY-301 has shipped in 4.0.9-beta (per REL-002 release notes line 13 and EP-010 epic `completion_criteria_done: [0, 1, 2, 3, 4]`). The `tests/test-sync.sh` lines 549-794 cover backup creation.
- **Nature of impact**: REFERENCED. STORY-304 reads `hooks.bak/` but does not modify it.
- **Specific change required**: None — depends on already-shipped behavior.
- **Risk level**: LOW. The dependency is on a shipped, well-tested feature. The emergency script gracefully degrades to repo-copy fallback when `hooks.bak/` is absent (SPEC-304 lines 240-249 enumerate all six absence scenarios). The skill (Deliverable 4) reports a clear error and falls through to the emergency script. Fresh installs (no sync yet performed) will not have `hooks.bak/` — the emergency script handles this case.
- **Dependencies**: None outbound. Depends on STORY-301's backup format remaining stable (single-generation, full copy, includes `.sh` and `hooks.json`/`hooks-manifest.json`).

---

### 7. Skill count headings — README.md and skills-reference.md

- **What it is**: Two locations carry skill counts that must stay in sync with `ls skills/` count.
  - `docs/user-guide/skills-reference.md:6` — `All 103 skills, organized by domain.`
  - `docs/user-guide/skills-reference.md:40` — `## System (14 skills)`
  - `README.md:130-170` (Housekeeping table) — does NOT contain a numeric skill count; the story's Implementation Note line 49 says it does, but actual inspection shows the table has no count.
- **Nature of impact**: MODIFIED. Story-required updates per criteria 304-12, 304-13 and Implementation Notes line 49.
- **Specific change required**:
  - skills-reference.md line 6: `103` → `104`.
  - skills-reference.md line 40: `## System (14 skills)` → `## System (15 skills)`.
  - skills-reference.md System table: add `**Hook Repair** | /sweetclaude:hook-repair | …` row.
  - README.md: add `hook-repair` to a skills-reference section. The exact insertion point is unclear — neither Common Commands subsection (Primary, Housekeeping, Advanced) is obviously the right home for an emergency-recovery skill. **Implementation Notes line 49 references "Housekeeping table at line 145" but that table does not currently contain a skill count.** See Open Questions.
- **Risk level**: MEDIUM. Skill-count drift was the specific learning recorded in `feedback_apply_edits_to_all_surfaces.md`. The current repo has 109 directories in `skills/` but skills-reference.md claims 103 — there is pre-existing drift not caused by this story. STORY-304 should not be responsible for reconciling that drift, but the new entry could land on top of an incorrect baseline.
- **Dependencies**: None. Numeric updates are local edits. But the README insertion point needs a directional choice from the user.

---

### 8. `docs/user-guide/hook-development.md` — file does not exist yet

- **What it is**: STORY-304 Deliverable 3 (Recovery + Emergency Recovery sections). The file is created by STORY-306, which is currently `status: deferred`.
- **Nature of impact**: BLOCKED — story acceptance criteria 304-1, 304-2, 304-3, 304-9, 304-10 all grep against `docs/user-guide/hook-development.md`. The file does not exist in the repo today.
- **Specific change required**: Either (a) implement STORY-306 first (per SPEC-304 line 560 and DESIGN-304's implicit ordering and EP-010 architecture spec line 75), or (b) have STORY-304 create a stub `hook-development.md` containing only the Recovery / Emergency Recovery sections, and have STORY-306 fill in the rest. The EP-010 epic spec explicitly mandates 306-first ordering ("Implementation order: 306 first, then 304"). But STORY-306 is `status: deferred`.
- **Risk level**: HIGH. STORY-304 is `status: active`, STORY-306 is `status: deferred`. Shipping 304 alone leaves it blocked on its own acceptance grep until 306 is undeferred. This is a real ordering inconsistency, not just a doc bug.
- **Dependencies**: Hard dependency on STORY-306, or on a reduced-scope variant where 304 creates the file with placeholder sections that 306 expands.

---

### 9. EP-010 completion criteria — array bookkeeping

- **What it is**: `docs/product/roadmap/epics/EP-010-self-hosting-infrastructure.md:21` — `completion_criteria_done: [0, 1, 2, 3, 4]` (0-indexed indices into the criteria list, which has 10 entries).
- **Nature of impact**: MODIFIED. Shipping STORY-304 completes criterion #5 "Broken hook recoverable via Bash (304)" — index 5 in the array.
- **Specific change required**: After ship, update array to `[0, 1, 2, 3, 4, 5]`. Story acceptance criteria do not mandate this update — it is bookkeeping owned by EP-010 management, not by STORY-304's implementation.
- **Risk level**: LOW. Pure bookkeeping. The array drift is recoverable.
- **Dependencies**: None upstream. Downstream: EP-009 (Workflow Orchestration Runbooks) has an inferred dependency on EP-010 completion (epic spec line 165), and #5 is one of the 10 criteria gating that completion. Stories 305, 306, and the "Zero manual rules" meta-criterion still block EP-010 completion after 304 ships.

---

### 10. STORY-305 / STORY-306 deferred coordination

- **What it is**: Both STORY-305 (symlink detection) and STORY-306 (hook dev docs) are `status: deferred` but `priority: now`, both in REL-004. REL-004 is `status: active`.
- **Nature of impact**: REFERENCED. STORY-304 does not modify these stories, but its viability is entangled with both.
  - STORY-305: no direct content overlap. STORY-305 modifies `session-preflight.sh`, `fix-sweetclaude/SKILL.md`, and `sync-to-installed.sh`. STORY-304 touches none of those. Indirectly: symlink-induced session deadlock is one of the failure modes the hook-repair skill is designed to recover from. The skill's "Step 2: Check for backup" detection would not work if hooks are symlinks (the backup would be a symlink to the broken target). Worth a sentence in the skill or doc, but not blocking.
  - STORY-306: direct overlap. STORY-306's `## Recovery` section (spec lines 86-93) is a cross-reference stub to STORY-304's content. STORY-304's Deliverable 3 IS the content of STORY-306's Recovery section. The two stories' content does not conflict — they are designed to interlock — but the file must exist before 304 can write to it.
- **Specific change required**: None on the 305 side. On the 306 side, undefer or accept that 304 cannot pass acceptance criteria until 306 ships.
- **Risk level**: MEDIUM. The deferred-but-priority-now status of 306 is the blocker. STORY-304 cannot complete in isolation.
- **Dependencies**: STORY-304 → STORY-306 (file existence). STORY-305 is independent.

---

### 11. CHANGELOG.md and CONTRIBUTING.md

- **What it is**: `CHANGELOG.md:19` already mentions `hooks.bak/` (from STORY-301). `CONTRIBUTING.md:72` documents the manual `cp hooks.bak/<hook>.sh hooks/<hook>.sh` recovery pattern.
- **Nature of impact**: MODIFIED (probable). Story acceptance criteria do not mandate CHANGELOG or CONTRIBUTING updates, but `feedback_apply_edits_to_all_surfaces.md` argues that copy edits apply to every surface in one turn.
- **Specific change required**: Add a CHANGELOG.md row for 4.0.10 (REL-004) covering the emergency script + skill. Update CONTRIBUTING.md line 72 to mention the new `scripts/emergency-hook-restore.sh` and `/sweetclaude:hook-repair` skill alongside the existing manual `cp` instructions.
- **Risk level**: LOW. Additive doc edits.
- **Dependencies**: None.

---

### 12. Pre-existing `blast-radius-analysis.md`

- **What it is**: `docs/internal/specs/ep-010/blast-radius-analysis.md` already exists (v1.0, 2026-05-18) and already contains a "STORY-304" section (lines 147-181). This new file (BLAST-304) is a story-scoped follow-up, not a replacement.
- **Nature of impact**: REFERENCED (no change needed). This file augments, not replaces, the epic-level blast-radius-analysis.
- **Risk level**: LOW.

---

## Epic Boundary Assessment

**Recommendation: NO — STORY-304 should remain a story, not be promoted to an epic.**

Applying the criteria:

1. **More than 3 distinct subsystems?** No. Five files in three subsystems — scripts/, skills/, tests/. README and skills-reference.md are reference-table updates, not subsystem work. Hook-development.md is one doc page (or two sections of one). Three subsystems is at the boundary, not above it.

2. **Coordination across more than 2 teams/roles?** No. Solo developer with AI assistance.

3. **Is any single deliverable itself story-sized?** No. The largest deliverable — the emergency script — is ~130 lines including comments and is fully specified in SPEC-304 §Deliverable 1 with the complete code body. The test script is ~140 lines and equally complete. The skill is ~50 lines. None of these are independently shippable in a meaningful sense — they are tightly coupled by the output-contract design.

The two real risks (spec/story test-script divergence; STORY-306 file dependency) are coordination issues, not scope issues. Neither becomes easier by splitting STORY-304 into multiple stories — both are best resolved by reconciling the existing artifacts before implementation begins.

The story is correctly sized at `effort: s`. The blast radius is broader than the deliverable count suggests, but the breadth is in cross-reference bookkeeping (skill counts, completion criteria, CHANGELOG), not in independently shippable work.

---

## Open Questions

These require user input before implementation begins. They cannot be resolved by reading documents.

1. ~~**Spec/story divergence on the test script (Area 2).**~~ **RESOLVED — Option B (2026-05-19).** `--dry-run` flag added to the emergency script; test file at `tests/test-emergency-restore.sh`; four test functions: `test_restore_from_backup`, `test_fallback_to_repo`, `test_back_door_skips_prefix_check`, `test_dry_run_preview`. SPEC-304 v2.1 is the canonical reference. Story implementation notes and criteria updated to match.

   These are not reconcilable — they imply different scripts. If we go story-first, SPEC-304 v2.0 needs a v3.0 supersede. If we go spec-first, the story's criteria 304-6/7/8 need editing.

2. ~~**STORY-306 ordering (Area 8).**~~ **RESOLVED — Option A (2026-05-19).** STORY-304 creates `docs/user-guide/hook-development.md` with only the Recovery and Emergency Recovery sections. STORY-306 adds the rest (workflow content) when undeferred. 304 acceptance criteria can pass on ship.

3. ~~**README.md insertion point (Area 7).**~~ **RESOLVED (2026-05-19).** Add `hook-repair` to the Housekeeping table. Rename that table heading from "Housekeeping" to "Maintenance & Troubleshooting". Update the story implementation notes accordingly.

4. ~~**Pre-existing skill-count drift (Area 7).**~~ **RESOLVED — Option A (2026-05-19).** Bump from documented baseline (103→104). Full reconciliation of the 6-skill gap (109 actual vs 103 documented) deferred to CHORE-014.

5. ~~**CHORE-013 timing (Area 3).**~~ **MOOT — RESOLVED (2026-05-19).** The test file lives at `tests/test-emergency-restore.sh`, outside the `tests/hooks/` glob. CHORE-013 does not affect STORY-304 at all. CHORE-013 remains `priority: later` independently.

6. ~~**Story 304-11 version stamp.**~~ **RESOLVED — Option A (2026-05-19).** Stamp the version the recovery was validated against, not the ship version. Current branch is `release/3.68.x` at v3.68.6. The implementer writes `Validated against SweetClaude v3.68.6` in the story file during IMPLEMENT/VERIFY after confirming the recovery procedure works on that version.
