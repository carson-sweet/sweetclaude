---
epic: EP-010
title: Blast Radius and Downstream Impact Analysis
version: 1.0
date: 2026-05-18
status: draft
---

# EP-010: Blast Radius and Downstream Impact Analysis

## Per-Story Impact

---

### STORY-300: Phase-aware sync gate

**Components directly modified:**

| Component | Nature of change |
|---|---|
| `scripts/sync-to-installed.sh` | **Created.** New script. No existing file displaced. |
| `skills/experimental-feature-setup/SKILL.md` | **Modified.** Phase check added to Step 4 before rsync commands. |

**Components indirectly affected:**

| Component | Why affected | Risk |
|---|---|---|
| `.sweetclaude/state/decision-log.md` | `--force` appends a new row. 15+ skills read this file. | Low. Append-only. New entries don't change existing rows. Table format is stable (29 entries, pattern well-established). |
| `.sweetclaude/state/phase.yaml` | New reader. Script greps for `phase:` field. | Low. Read-only. Same grep pattern as `test-guardian.sh`. |
| `.sweetclaude/state/sweetclaude.yaml` | New reader. Script parses `work.active.phase` via Python+YAML. | Low. Read-only. Same field structure used by `generate-session-state.sh`. |
| `~/.claude/plugins/installed_plugins.json` | New reader. Script resolves `installPath`. | Low. Read-only. Same resolution logic already in `scripts/preflight.sh` and `experimental-feature-setup`. |

**Test suites affected:**

| Test file | Impact |
|---|---|
| `tests/test-hooks.sh` | None directly. STORY-302 adds the test-gate call to this script, but 300 itself doesn't touch tests. |
| New: sync script tests | STORY-300 needs its own test coverage. Not in an existing test file — either a new `tests/test-sync.sh` or inline in `test-hooks.sh`. |

**Documentation affected:**

| Document | Impact |
|---|---|
| `docs/user-guide/hook-development.md` | Referenced by STORY-306. The sync script is documented there. |
| `CONTRIBUTING.md` | Line 83 references `hooks/*.sh` as "deterministic enforcement; bugs here affect every session." The new sync script at `scripts/` is adjacent but not in `hooks/`. No update needed unless CONTRIBUTING.md lists `scripts/` too. |

**Integration points:**

| Integration | Detail |
|---|---|
| `experimental-feature-setup` ↔ sync gate | The skill must check phase before syncing. The spec says to add the check inline, not delegate to `sync-to-installed.sh`. Long-term, the skill can delegate. |
| `scripts/preflight.sh` | Contains an existing `installed_plugins.json` resolution pattern (lines 43-61). STORY-300's script should reuse this pattern, not reinvent it. |

---

### STORY-301: Backup-on-sync

**Components directly modified:**

| Component | Nature of change |
|---|---|
| `scripts/sync-to-installed.sh` | **Modified.** Backup step added between test gate and sync. |
| `~/.claude/plugins/cache/.../hooks.bak/` | **Created.** New directory at installed path. Does not exist today. |

**Components indirectly affected:**

| Component | Why affected | Risk |
|---|---|---|
| STORY-304 (hook-repair skill) | Depends on `hooks.bak/` existing. If 301's backup format changes, 304's restore breaks. | Medium. Tight coupling by design — the backup IS the restore source. |
| STORY-304 (`scripts/emergency-hook-restore.sh`) | Same dependency on `hooks.bak/` location and contents. | Medium. Same coupling. |
| `sweetclaude-health-check.sh` | Currently checks `hooks.json` existence at the installed path (line 97). Does not check `hooks.bak/`. No impact. | None. |

**Test suites affected:**

| Test file | Impact |
|---|---|
| Sync script tests (from 300) | Backup behavior is part of the sync script. Tests for 301 criteria belong in the same test file as 300. |

**Documentation affected:**

| Document | Impact |
|---|---|
| `docs/user-guide/hook-development.md` | Recovery section references `hooks.bak/`. |

---

### STORY-302: Pre-sync test gate

**Components directly modified:**

| Component | Nature of change |
|---|---|
| `scripts/sync-to-installed.sh` | **Modified.** Test gate step added between phase check and backup. |

**Components indirectly affected:**

| Component | Why affected | Risk |
|---|---|---|
| `tests/test-hooks.sh` | The sync script invokes this file. A change to `test-hooks.sh` exit code behavior could affect the gate. | Low. The exit code contract (0 = pass, non-zero = fail) is standard and unlikely to change. |
| All hooks tested by `test-hooks.sh` | Indirectly gated — a regression in ANY tested hook blocks ALL syncs. | Low. This is the intended behavior. |

**Test suites affected:**

| Test file | Impact |
|---|---|
| Sync script tests | Gate behavior (block on failure, pass on success, --force doesn't bypass) must be tested. |
| `tests/test-hooks.sh` | Not modified, but its behavior becomes load-bearing for the sync pipeline. A flaky test would block syncs. |

**Documentation affected:**

None beyond what STORY-306 covers.

---

### STORY-303: Extend test-hooks.sh coverage

**Components directly modified:**

| Component | Nature of change |
|---|---|
| `tests/test-hooks.sh` | **Modified.** ~11 new test cases appended (tests 11-21). File grows from 277 to ~450 lines. |

**Components indirectly affected:**

| Component | Why affected | Risk |
|---|---|---|
| `hooks/test-guardian.sh` | Test subject. Tests exercise all code paths. If hook behavior changes, tests catch it. | None (that's the point). |
| `hooks/auto-test-runner.sh` | Test subject. Same as above. | None. |
| `hooks/hooks.json` | Indirectly — tests validate behavior that depends on the hook registration (Write\|Edit matcher). Tests don't read hooks.json directly. | None. |
| STORY-302 (test gate) | The test gate runs `test-hooks.sh`. More tests = longer gate execution time. | Low. Bash tests with fixture `touch` commands add <2 seconds total. |
| `tests/test-skill-bash-blocks.sh` | Not affected. This tests SKILL.md bash blocks, not hook scripts. | None. |
| `.sweetclaude/state/phase.yaml` | Test fixtures create fake `phase.yaml` files in temp dirs. Real `phase.yaml` is never touched. | None. |

**Test suites affected:**

| Test file | Impact |
|---|---|
| `tests/test-hooks.sh` | Directly modified. New tests must not break existing tests 1-10. |
| `tests/hooks/test-tdd-prewrite-guardian.sh` | Related hook test. Not modified, but if `tdd-prewrite-guardian.sh` shares code paths with `test-guardian.sh`, behavioral assumptions should be consistent. |

**Documentation affected:**

None directly. STORY-306 documents the test suite.

---

### STORY-304: Bash-based hook repair recovery

**Components directly modified:**

| Component | Nature of change |
|---|---|
| `skills/hook-repair/SKILL.md` | **Created.** New skill. |
| `scripts/emergency-hook-restore.sh` | **Created.** New standalone script. |
| `docs/user-guide/hook-development.md` | **Modified.** Recovery and break-glass sections added. |

**Components indirectly affected:**

| Component | Why affected | Risk |
|---|---|---|
| `hooks/hooks.json` | The hook-repair skill is NOT a hook — it's a skill. No registration change needed. | None. |
| `hooks/hooks-manifest.json` | Same — not a hook. No manifest change. | None. |
| `~/.claude/plugins/cache/.../hooks.bak/` | Read by both the skill and emergency script. If STORY-301 changes backup location or format, both break. | Medium. Document the coupling explicitly. |
| `~/.claude/plugins/installed_plugins.json` | Read by emergency script for path resolution. Same pattern as STORY-300. | Low. Read-only. |
| `README.md` | Contains a skill reference table. New skill `hook-repair` should be listed. | Low. Additive change. |
| `hooks/hooks-manifest.json` | If the project tracks skills in the manifest, `hook-repair` might need an entry. Currently the manifest only tracks hooks, not skills. | None. |
| `tests/test-skill-bash-blocks.sh` | Automatically discovers SKILL.md files under `skills/`. The new `hook-repair/SKILL.md` will be included in its bash-block validation sweep. Bash blocks in the skill must pass `bash -n`. | Low but important. Write valid bash in the SKILL.md. |

**Test suites affected:**

| Test file | Impact |
|---|---|
| `tests/test-skill-bash-blocks.sh` | Automatically picks up `skills/hook-repair/SKILL.md`. No code change needed, but the new skill's bash blocks must be syntactically valid. |

**Documentation affected:**

| Document | Impact |
|---|---|
| `docs/user-guide/hook-development.md` | Recovery + break-glass sections added by this story. |
| `README.md` | Skill reference table — add `hook-repair` entry. |
| `docs/user-guide/skills-reference.md` | If this file catalogs all skills, add `hook-repair`. |

---

### STORY-305: Session-start symlink detection

**Components directly modified:**

| Component | Nature of change |
|---|---|
| `hooks/session-preflight.sh` | **Modified.** New Step 10 (symlink check) inserted. ~15 lines added. |
| `skills/fix-sweetclaude/SKILL.md` | **Modified.** New sub-step 7e (symlink repair) added. ~25 lines. |
| `scripts/sync-to-installed.sh` | **Modified.** Post-sync symlink verification added. ~8 lines. |

**Components indirectly affected:**

| Component | Why affected | Risk |
|---|---|---|
| Every SweetClaude session | `session-preflight.sh` fires on EVERY session start. A bug here affects every user. | **High.** This is the highest-risk change in EP-010. The new check must be defensive — a failure in the symlink check must not block session startup. |
| `hooks/generate-session-state.sh` | Called by session-preflight Step 12. If the symlink check `exit 0`s early (on detection), state generation is skipped. This is intentional but changes session-start behavior. | Medium. Users with symlinked hooks will see different session-start behavior (heal message instead of normal status). |
| `hooks/sweetclaude-health-check.sh` | Called by session-preflight Step 12. Same early-exit impact as above. | Medium. Same reasoning. |
| `tests/test-hooks.sh` | Tests 8-10 test session-preflight. The new symlink check runs BEFORE Step 12, so existing tests (which don't create symlinks) should pass unchanged. But if the step numbering or flow changes, assertions may need updating. | Medium. Verify existing tests still pass after the change. |
| `tests/test-upgrade-path-e2e.sh` | References session-preflight in e2e fixtures. May create fixture hooks that could trigger the symlink check if they happen to be symlinks. | Low. Fixtures use `cp`, not `ln -s`. |
| `tests/test-v3.66.0-followups.sh` | References session-preflight. Same low-risk as above. | Low. |
| `.sweetclaude/plans/session-preflight-rewrite-plan.md` | Existing plan for session-preflight changes. This plan should be reviewed — may conflict with or supersede the EP-010 changes. | Low. Plans are aspirational, not authoritative. |

**Test suites affected:**

| Test file | Impact |
|---|---|
| `tests/test-hooks.sh` | Existing session-preflight tests (8-10) must still pass. New test(s) needed for symlink detection behavior. |
| `tests/test-skill-bash-blocks.sh` | `fix-sweetclaude/SKILL.md` is modified. Its bash blocks are already in the validation sweep. New bash blocks must pass `bash -n`. |

**Documentation affected:**

| Document | Impact |
|---|---|
| `docs/user-guide/hook-development.md` | STORY-306 documents the two-copy architecture. Symlink detection is part of that story. |
| `scratch/v3-upgrade-assessment-2026-05-11/02-preflight.md` | Historical assessment. No update needed but useful reference. |

---

### STORY-306: Hook development workflow documentation

**Components directly modified:**

| Component | Nature of change |
|---|---|
| `docs/user-guide/hook-development.md` | **Created.** New documentation file. |

**Components indirectly affected:**

| Component | Why affected | Risk |
|---|---|---|
| `docs/user-guide/index.md` | The user guide index should list the new page. | Low. Additive. |
| `docs/user-guide/tdd.md` | Cross-referenced by the new doc. If `tdd.md` content changes, cross-references may go stale. | Low. Link-level coupling only. |
| `docs/user-guide/how-it-works.md` | Same cross-reference coupling. | Low. |
| `docs/user-guide/phases-and-workflows.md` | Same. | Low. |

**Test suites affected:**

None. This is a documentation-only story.

**Documentation affected:**

| Document | Impact |
|---|---|
| `docs/user-guide/index.md` | Add entry for `hook-development.md`. |
| `docs/user-guide/tdd.md` | Consider adding a "What to Read Next" link to `hook-development.md`. |

---

## Cumulative Impact Analysis

### Shared components touched by multiple stories

| Component | Stories that modify it | Coordination needed |
|---|---|---|
| `scripts/sync-to-installed.sh` | 300 (creates), 301 (adds backup), 302 (adds test gate), 305 (adds post-sync check) | **High.** Four stories modify the same file. Implementation order is strict: 300 → 301 → 302 → 305. Each story adds a step to the pipeline. If implemented concurrently, merge conflicts are guaranteed. |
| `docs/user-guide/hook-development.md` | 306 (creates), 304 (adds recovery + break-glass sections) | **Medium.** Two stories modify the same file. Order: 306 first (creates structure), 304 second (adds sections). |
| `tests/test-hooks.sh` | 303 (adds ~11 tests) | **Low.** Only one story modifies this file. But STORY-302 makes this file load-bearing for the sync pipeline — any flakiness in existing or new tests blocks all syncs. |
| `hooks/session-preflight.sh` | 305 (adds symlink check) | **Low.** Only one story modifies this file. But it fires on every session start, so the blast radius of a bug is the entire user base. |
| `skills/fix-sweetclaude/SKILL.md` | 305 (adds symlink repair sub-step) | **Low.** Only one story modifies this file. But fix-sweetclaude is 757 lines and heavily integrated (called by session-preflight heal, references from 4+ backlog items). |

### Ordering dependencies (strict)

```
STORY-303 ─────────────────────────────────────────────┐
                                                        │
STORY-300 ──→ STORY-301 ──→ STORY-302 ──→ STORY-305   │
                  │                                     │
                  │         ┌───────────────────────────┘
                  │         │
                  ▼         │
              STORY-306 ────┘
                  │
                  ▼
              STORY-304
```

- **300 before 301**: 301 adds to the script 300 creates.
- **301 before 302**: 302 adds to the script; also, 302's test gate is more valuable after 303 extends coverage. But 302 doesn't strictly depend on 303 — the gate works with existing tests.
- **302 before 305**: 305 adds the post-sync check. Logically this is after the sync pipeline is complete.
- **300 + 303 in parallel**: No dependency between them. Both can start immediately.
- **306 before 304**: 304 adds sections to the file 306 creates.
- **301 before 304**: 304's recovery depends on `hooks.bak/` existing.

### Interaction risks

| Interaction | Risk | Mitigation |
|---|---|---|
| **302 + 303: test gate depends on test quality** | If STORY-303 introduces a flaky test, STORY-302's gate blocks all syncs intermittently. | Run `test-hooks.sh` 10x in a loop before shipping 303. The marker-file retry loop (303 spec) must be robust. |
| **300 + 305: phase check + symlink check both modify sync script** | Both add steps to `sync-to-installed.sh`. If implemented concurrently, merge conflict. | Sequential implementation. 300 first (creates file), 305 last (adds post-sync check). |
| **304 + 301: recovery depends on backup existence** | If `hooks.bak/` doesn't exist (first use, or 301 hasn't shipped), the hook-repair skill fails. The emergency script falls back to repo copy. | Emergency script has the repo fallback. The skill reports a clear error. Document the dependency. |
| **305 + session-preflight: early exit changes session-start flow** | If symlinks are detected, session-preflight exits after `emit_heal` and skips state generation (Steps 12-14). This changes the session experience. | Intentional. The heal message directs users to fix-sweetclaude. State generation is skipped because the session is in a degraded state. |
| **300 + experimental-feature-setup: dual sync paths** | Until experimental-feature-setup delegates to sync-to-installed.sh, both tools exist with overlapping scope. A developer might use the wrong one. | Document: `sync-to-installed.sh` is canonical. `experimental-feature-setup` is legacy/local-only. Long-term, the skill delegates to the script. |
| **304 skill + test-skill-bash-blocks.sh: auto-validation** | The new `hook-repair/SKILL.md` is automatically picked up by `test-skill-bash-blocks.sh`. Any bash block in the skill that fails `bash -n` will be caught by this existing test. | Write valid bash. Run `test-skill-bash-blocks.sh` after creating the skill. |

### Components NOT affected (explicit exclusions)

These components were investigated and confirmed unaffected:

| Component | Why unaffected |
|---|---|
| `hooks/hooks.json` | No hook registrations are added, removed, or modified. |
| `hooks/hooks-manifest.json` | No manifest entries change. The new skill (`hook-repair`) is not a hook. |
| `hooks/drift-gate.sh` | Not touched. Different concern (schema drift, not self-hosting). |
| `hooks/master-preflight.sh` | Not touched. Guards skill invocation order, not sync. |
| `hooks/artifact-guardian.sh` | Not touched. Guards Bash artifact edits, not relevant to sync or recovery. |
| `hooks/preflight-guard.sh` | Not touched. Guards all tools pre-bootstrap. |
| `hooks/state-regenerator.sh` | Not touched. PostToolUse state regeneration. |
| `hooks/tdd-prewrite-guardian.sh` | Not touched. TDD level 3 specific. |
| `hooks/wip-limit.sh` | Not touched. Work-in-progress limits. |
| `config/` | No configuration changes. |
| `scripts/migrations/` | No migration handlers added. |
| `.sweetclaude/state/sweetclaude.yaml` | Read-only by STORY-300. Never written. |
| `.sweetclaude/state/skills.yaml` | Not referenced by any EP-010 story. |
| All existing skills except `fix-sweetclaude` and `experimental-feature-setup` | Not modified. |

### Test suite impact summary

| Test file | Modified by | Run-as-gate by | Risk level |
|---|---|---|---|
| `tests/test-hooks.sh` | STORY-303 | STORY-302 (sync gate) | **High** — flaky tests block all syncs |
| `tests/test-skill-bash-blocks.sh` | None (but auto-discovers new skill) | None | **Low** — validates bash syntax only |
| `tests/test-upgrade-path-e2e.sh` | None | None | **Low** — may need review if session-preflight flow changes |
| `tests/test-v3.66.0-followups.sh` | None | None | **Low** — references session-preflight but unlikely to break |
| `tests/test-health-check.sh` | None | None | **None** — health check is not modified |
| New: sync script tests | STORY-300 creates | N/A | **Medium** — new test file needed |

### Documentation impact summary

| Document | Stories | Nature |
|---|---|---|
| `docs/user-guide/hook-development.md` | 306 (create), 304 (add sections) | **New file.** Net-new documentation. |
| `docs/user-guide/index.md` | 306 | **Additive.** New entry in index. |
| `docs/user-guide/tdd.md` | 306 | **Optional.** Cross-reference link. |
| `README.md` | 304 | **Additive.** New skill in reference table. |
| `docs/user-guide/skills-reference.md` | 304 | **Additive.** New skill entry. |
| `CONTRIBUTING.md` | None | **None.** Existing hook guidance still accurate. |

### Risk ranking

| Story | Blast radius | Failure impact | Overall risk |
|---|---|---|---|
| **STORY-305** | Small (3 files modified) | **High** — session-preflight fires every session. Bug = broken session start for all users. | **HIGH** |
| **STORY-303** | Small (1 file modified) | **High** — flaky test + STORY-302 gate = blocked syncs. | **MEDIUM-HIGH** |
| **STORY-300** | Medium (2 files modified, new script) | **Medium** — sync script is developer-facing, not session-start. Bug = failed sync, not deadlock. | **MEDIUM** |
| **STORY-302** | Small (1 file modified) | **Medium** — gate depends on test quality. Blocks sync on test failure. | **MEDIUM** |
| **STORY-301** | Small (1 file + new dir) | **Low** — backup is additive. Failure = no backup, not broken sync. Criterion 301-5 (abort on failure) raises this slightly. | **LOW-MEDIUM** |
| **STORY-304** | Medium (3 new files) | **Low** — all net-new, no existing behavior changed. | **LOW** |
| **STORY-306** | Small (1 new file) | **None** — documentation only. | **NONE** |
