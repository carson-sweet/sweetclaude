---
id: DESIGN-304
story: STORY-304
spec: SPEC-304
epic: EP-010
version: 3.0
date: 2026-05-19
supersedes: design-304 v2.0 (2026-05-19)
status: draft
---

# Design: STORY-304 — Bash-based hook repair recovery procedure

Companion to SPEC-304 v2.1. This document captures the load-bearing design decisions only; the spec is the source of truth for script and test bodies and for acceptance criteria. v3.0 supersedes v2.0 in place to incorporate the `--dry-run` flag (spec v2.1 amendment), the four-test structure, the STORY-306 stub-file ordering decision (blast-radius Open Question 2, Option A), the README heading rename (blast-radius Open Question 3), and the 304-11 version-stamp resolution (blast-radius Open Question 6, Option A). Provenance preserved in `supersedes:`; the v2.0 content remains in git history for diff.

---

## Epic promotion assessment

**Verdict: NO. STORY-304 stays a story.**

Applying the three-part test independently of the blast-radius recommendation:

1. **More than 3 distinct subsystems?** No. The work touches `scripts/`, `tests/`, `skills/`, and `docs/`. Four directories, but `docs/` and `README.md` edits are reference-table bookkeeping (skill counts, table-row insertion, heading rename) — they do not constitute a subsystem in any architectural sense. The real engineering surfaces are three: the emergency script, its test, and the user-invocable skill. The user-guide page is a passive sink for content the spec already enumerates.

2. **More than 2 coordination roles?** No. Solo developer + AI assistance, single review surface, single release lane.

3. **Any single deliverable independently shippable?** No. The emergency script alone is unreachable from any documented entry point without the skill or the user-guide section. The skill alone has nothing to recover from without the script as fallback. The test exists only to lock the script's output contract. The deliverables are tightly cross-linked through the output-contract constants (`CONTRACT_LINE_*`, `EHR_*`) — none can be cut without breaking the others.

Counter-considerations weighed:

- *The blast radius touches twelve areas.* That breadth is in cross-reference bookkeeping (skill counts, completion-criteria arrays, CHANGELOG entries), not in engineering scope. Bookkeeping breadth does not justify an epic.
- *STORY-306 cross-dependency.* This was a real risk in design v2.0, now resolved by the Option A stub-file decision (see Decision 8 below). It does not warrant epic-level coordination — STORY-304 now self-creates the file with only the sections it owns.
- *Three copies of the install-path resolver* (`sync-to-installed.sh:20-36`, `preflight.sh`, this new script). Drift risk is real but it is a separate concern with no per-story remediation. Tracked in blast-radius Area 5; not a reason to split STORY-304.

Conclusion matches blast-radius: NO. Story stays at `effort: s`.

---

## Design decisions

### 1. Bash is the recovery channel — and `artifact-guardian.sh` does not block it

`hooks/hooks.json` registers `test-guardian.sh` and `auto-test-runner.sh` with `"matcher": "Write|Edit"`. The matcher is a tool-name regex evaluated by the Claude Code harness; the Bash tool name does not match these regexes, so Bash invocations are never routed through these hooks. When a Write/Edit hook is itself broken (syntax error or non-zero exit), the harness blocks Write and Edit — but Bash continues to work.

This is not a side effect being exploited. It is the intended escape hatch baked into the matcher architecture: Bash is needed for compile/test/restore workflows, and gating it would create unrecoverable deadlocks. STORY-304 codifies this property into a documented recovery channel, a script that uses it, and a skill that orchestrates it.

`artifact-guardian.sh` does match `Bash`, but it gates Bash invocations that touch artifact-protected paths (e.g. story state files under `.sweetclaude/state/`). `~/.claude/plugins/cache/.../hooks/` is not an artifact-protected path, so a recovery `cp` is not blocked. This is verified by reading the guard's path predicates; no change to artifact-guardian is required.

### 2. `set -e` (script) vs `set -euo pipefail` (test) asymmetry — deliberate

**Script: `set -e` only.** The recovery script's job is to make a best effort under degraded conditions. Three specific reasons strict mode is wrong here:

- `set -u` would force defensive `${VAR:-}` annotation on every env-var reference. `INSTALL_PATH`, `EMERGENCY_RESTORE_SOURCE_ONLY`, `DRY_RUN`, and the positional `$1` all may legitimately be unset, and the script already pattern-guards each (`if [ -n "${INSTALL_PATH:-}" ]`). Adding `-u` adds annotation noise without adding safety — the guards already exist.
- `set -o pipefail` would propagate failures from `find ... | head -1` patterns where short-circuiting at `head` is exactly the desired behavior. Treating this as failure would force unnecessary `|| true` clauses on every pipeline.
- The `python3` heredoc may produce empty output (no `installed_plugins.json`, or no matching entries). The script handles this by checking `[ -z "$INSTALL_PATH" ]` after the heredoc; under pipefail-equivalent semantics that empty output would be a non-zero exit propagating as a script failure.

**Test: `set -euo pipefail`.** Tests must fail loudly. An unset variable in the test harness is a bug, not a graceful degradation. A failing pipeline silently passing would let a regression through. The test is short, controlled, and authored to satisfy strict mode.

This asymmetry is intentional and the spec calls it out (v2.1 §"`set -e`, not `set -euo pipefail`") so future maintainers do not "normalize" the script to strict mode — that would silently break the recovery path the script exists to provide.

### 3. The `EMERGENCY_RESTORE_SOURCE_ONLY=1` sentinel

The test script needs the output-contract constants (`CONTRACT_LINE_*`, `CONTRACT_FATAL_*`, `EHR_*`) to assert against. The design rejects three alternatives in favor of source-with-sentinel:

- **Hard-coded literals in tests.** Drift risk — a script-side rename of `CONTRACT_LINE_RESTORED_PREFIX` would not break the test until the actual restore line is also changed; the test would happily match the wrong substring.
- **Constants in a separate `constants.sh` file sourced by both.** Two-file design for one logical unit; introduces a build-order ambiguity and a discoverability cost for a "zero SweetClaude dependencies" script.
- **Constants printed by a `--dump-contract` flag.** Requires the script's main body to be re-entered repeatedly during a test run. Conflicts with the "execute main logic once, write to disk" model.

The chosen mechanism: the test runs `EMERGENCY_RESTORE_SOURCE_ONLY=1 source "$SCRIPT"`. The script defines its `readonly` constants at the top, then encounters this guard:

```bash
if [ -n "${EMERGENCY_RESTORE_SOURCE_ONLY:-}" ]; then
  return 0 2>/dev/null || exit 0
fi
```

The `return 0 2>/dev/null || exit 0` pattern returns from the sourced context if the script was sourced (working `return`) and exits cleanly if it was executed directly (no `return` outside a function — that error is swallowed and `exit 0` runs). This makes the sentinel safe in both invocation modes.

Why this is safer than other test-isolation approaches:

- **Single source of truth.** The script file is the only place the constants exist. The test cannot accidentally diverge.
- **No build step.** Pure bash sourcing. No make target, no pre-compile, no install hook.
- **Test isolation is preserved.** The sentinel returns before `INSTALL_PATH` resolution, before the prefix check, before any side effects. The test gets the constants, nothing else.

### 4. The `INSTALL_PATH` back-door: two bypasses, both intentional

Setting `INSTALL_PATH` non-empty at script entry triggers two distinct bypasses:

1. **Skip `installed_plugins.json` resolution.** The script trusts the caller's value verbatim, never reads the JSON file, never calls `find`. The python3 heredoc and the `find` fallback are both gated behind `if [ -z "${INSTALL_PATH:-}" ]`.

2. **Skip the `$HOME/.claude/plugins/` prefix check.** The check exists to prevent a poisoned `installed_plugins.json` from causing the script to write outside the plugin tree. Tests need to write to a sandboxed tmpdir, which by construction is outside the plugin tree.

Both bypasses are required by the test design. If only (1) were bypassed, tests would still fail the prefix check on tmpdir paths. If only (2) were bypassed, the script would still try to read JSON in test runs and would either succeed with the wrong path or fail because the JSON file is absent in the sandbox. Both must be off together; both are gated by the single signal `INSTALL_PATH_OVERRIDE=1` (set when `INSTALL_PATH` was non-empty at entry).

**The code comment is load-bearing.** A future maintainer reading "skip prefix check" in isolation might "harden" it back into place, breaking every test. The comment must state explicitly:

```bash
# Prefix check applies only when INSTALL_PATH was resolved from installed_plugins.json.
# When the caller sets INSTALL_PATH explicitly (test back-door), trust it.
# DO NOT re-enable this check unconditionally — tests rely on the bypass to use
# tmpdir paths outside the plugin tree.
```

This is the only comment in the script that explains a non-obvious design constraint. Per project convention "no comments unless necessary" — necessity met here, comment stays.

Security note: a caller who can set environment variables in the Claude Code session can already set `PATH`, write to arbitrary files via Bash, etc. The back-door does not widen the attack surface. The prefix check defends against a corrupted `installed_plugins.json`, not against a hostile caller. The back-door is documented in the spec's "test-only" framing — it is not advertised to end users.

### 5. The `--dry-run` flag: parsing position, output contract, exit code

**Parsing position: BEFORE `BASH_SOURCE` resolution? AFTER?**

Decision: **AFTER the sentinel guard, BEFORE `BASH_SOURCE` resolution.** Rationale:

- The sentinel guard must run first so that `source` with `EMERGENCY_RESTORE_SOURCE_ONLY=1` returns before any argument parsing. Test sourcing should be inert.
- `--dry-run` is a positional argument, parsed by inspecting `${1:-}`. `BASH_SOURCE` resolution happens before any optional-arg handling because it computes `REPO_ROOT`, which both dry-run and real-run code paths need.

Concretely the order in the script body is:
1. Define `readonly` constants.
2. Sentinel guard (`EMERGENCY_RESTORE_SOURCE_ONLY`).
3. `--dry-run` detection (`if [ "${1:-}" = "--dry-run" ]; then DRY_RUN=1; shift; fi`).
4. `SCRIPT_PATH`/`REPO_ROOT` computation.
5. `INSTALL_PATH_OVERRIDE` detection.
6. Install-path resolution (skipped if override set).
7. Prefix check (skipped if override set).
8. Target-hook validation.
9. Dry-run branch (emit contract lines, exit 0) OR real-run branch (echo headers, perform `cp`, echo done line).

This order matters because `shift` must happen before any subsequent `${1:-}` reads (the optional `[hook-name.sh]` argument), so that `--dry-run foo.sh` correctly interprets `foo.sh` as the target after the shift.

**Output contract in dry-run mode** (pinned in `EHR_*` constants):
- `Resolved install path: <absolute-path>` — emitted always (one line).
- `Would restore: <hook-filename>` — one line per hook that would be touched. With a target arg, one line for that hook; without an arg, one line per `.sh` file in the discovery source (backup if available, else repo).

**Exit-0-always rationale.** Dry-run is a preview. The downstream consumer (a future skill, a tooling integration, or a human running it to inspect) should be able to capture stdout and parse it without branching on exit code. If the install path cannot be resolved, the script still emits the FATAL line on stderr and exits 1 — the "exit-0-always in dry-run" rule applies only when resolution succeeded. Stated more precisely: **exit code is determined by whether resolution succeeded; dry-run never adds a non-zero exit for the absence of files to restore.** A dry-run with `hooks.bak/` absent and `repo/hooks/` empty correctly emits the resolved-path line, zero `Would restore:` lines, and exits 0.

### 6. Install-path resolution: three-step cascade

1. **Back-door check.** If `INSTALL_PATH` is non-empty at entry, set `INSTALL_PATH_OVERRIDE=1` and skip steps 2–3.
2. **JSON resolution.** Python3 heredoc reads `~/.claude/plugins/installed_plugins.json`, filters for `scope == 'user'`, sorts by `lastUpdated` DESC, picks the first entry whose `installPath/hooks` directory exists.
3. **Find fallback.** If step 2 returned empty, run `find ~/.claude/plugins/cache -type d -path "*/sweetclaude/sweetclaude/*" -name hooks -exec dirname {} \; 2>/dev/null | head -1`.
4. **Fail.** If both 2 and 3 returned empty, or if the resolved path's `hooks/` subdir does not exist, print `$CONTRACT_FATAL_NO_INSTALL` to stderr and exit 1.

**Prefix check** runs after resolution succeeds and only when `INSTALL_PATH_OVERRIDE` is unset:

```bash
if [ -z "$INSTALL_PATH_OVERRIDE" ]; then
  case "$INSTALL_PATH" in
    "$HOME/.claude/plugins/"*) : ;;
    *) echo "FATAL: Resolved install path is outside plugin tree: $INSTALL_PATH" >&2; exit 1 ;;
  esac
fi
```

**Where the back-door overrides the prefix check** is encoded structurally: the `if [ -z "$INSTALL_PATH_OVERRIDE" ]` wraps the entire prefix check. There is no second path through this code; the back-door is the only way past it.

**Duplication note.** This cascade duplicates logic in `scripts/sync-to-installed.sh:20-36` (`_resolve_install_path`) and `scripts/preflight.sh`. Duplication is intentional — the "zero SweetClaude dependencies" design principle forbids sourcing helpers. Drift risk between the three copies is acknowledged in blast-radius Area 5 and tracked separately; not addressed in this story.

### 7. `hooks.bak/` absence handling: six scenarios

Per spec v2.1 §"`hooks.bak/` absence behavior" table — restated here for design completeness:

| Scenario | Behavior |
|---|---|
| `hooks.bak/` missing, repo has `hooks/`, no target arg | Falls back to copying from `$REPO_ROOT/hooks/`; prints `No backup found. Restoring ALL hooks from repo...` |
| `hooks.bak/` missing, repo has `hooks/`, target arg given | Per-file fallback: copies named hook from repo; prints `RESTORED <hook> from repo (no backup available)` |
| `hooks.bak/` missing, repo missing, no target arg | Loop body executes zero times (no `.sh` files matched); prints headers + `Done.` line but nothing restored |
| `hooks.bak/` missing, repo missing, target arg given | `FATAL: <hook> not found in backup or repo` → exit 1 |
| `hooks.bak/` present but empty | Same as missing — `find ... -name '*.sh' \| wc -l` returns 0, falls back to repo |
| `hooks.bak/` present with `.sh` files, no target arg | Copies all `.sh` from backup + `hooks.json` + `hooks-manifest.json` if present |

The empty-backup-empty-repo-no-target scenario (row 3) is intentionally a soft success: the script reports the paths it inspected and exits 0 with nothing copied. The user sees "no backup, no repo" and knows the next step is a marketplace reinstall. A hard FATAL would deny the diagnostic value of seeing the resolved paths.

### 8. `hook-development.md` stub: STORY-304 vs STORY-306 ownership

Blast-radius Open Question 2 (Option A) resolved this: **STORY-304 creates `docs/user-guide/hook-development.md` containing only the Recovery and Emergency Recovery (Break Glass) sections, plus a `## What to Read Next` section. STORY-306 expands the file later when it un-defers.**

What STORY-304 writes:

```markdown
# Hook Development

## Recovery
[content from spec v2.1 Deliverable 3, Recovery section]

## Emergency Recovery (Break Glass)
[content from spec v2.1 Deliverable 3, Break Glass section]

## What to Read Next

- [How It Works](how-it-works.md) — hook architecture and the Write|Edit matcher
- [Skills Reference](skills-reference.md) — full list of available skills including `/sweetclaude:hook-repair`
- [TDD](tdd.md) — the testing discipline that keeps hooks correct before they are synced
```

What STORY-306 will later add (not in scope for 304):
- Top-level overview of hook development.
- Logic testing workflow (`CLAUDE_FILE_PATH=... bash hooks/<hook>.sh`).
- Regression testing workflow (`bash tests/test-hooks.sh`).
- Sync timing guidance (SHIP phase only).
- Integration test wrapper pattern.

**State that leaves 306 free to extend cleanly:**
- The file opens with a single `# Hook Development` H1.
- The two sections STORY-304 owns are H2s, free-standing, with no upward references to (yet-nonexistent) earlier sections.
- The `## What to Read Next` section is placed at the bottom. STORY-306 inserts its new H2s **above** Recovery, preserving Recovery and Break Glass at the same depth.
- All three target files in the "What to Read Next" list (`how-it-works.md`, `skills-reference.md`, `tdd.md`) exist today — confirmed via the codebase index. No dangling links.

The 306-first ordering originally mandated by EP-010 architecture is superseded by this decision; the resolution is recorded in this design and in the story implementation notes.

### 9. Test isolation: sandboxed HOME + INSTALL_PATH back-door, not a fake plugin-tree path

The test creates `$TEST_TMPDIR/tN/install` with `hooks/` and (optionally) `hooks.bak/` subdirectories. It passes `INSTALL_PATH=$install` directly into the script as the back-door.

**Why the back-door rather than a fake `HOME/.claude/plugins/` path:**

- A fake `HOME` would require the test to also fake `installed_plugins.json` content, creating a second mock surface. The back-door avoids both — no fake HOME, no fake JSON.
- A fake plugin-tree path inside the real `HOME/.claude/plugins/` would risk colliding with real install state on the developer's machine. Sandboxing under `$TEST_TMPDIR` is unambiguously safe.
- A fake `HOME` would still leave the prefix check armed against the fake path — the path would have to start with the real `$HOME/.claude/plugins/` for the prefix check to pass, which forces it back into the real plugin tree. The back-door is the only clean way out.

`trap 'rm -rf "$TEST_TMPDIR"' EXIT` ensures cleanup on every exit path (success, failure, signal). This pattern matches the existing `tests/test-hooks.sh` cleanup style (line 16: `trap "rm -rf $TMPROOT" EXIT`).

The test does not need a git repo in the sandbox — the script's `BASH_SOURCE`-based `REPO_ROOT` resolution computes the real repo root from the script's own filesystem location, which works regardless of where the test was launched.

### 10. README rename: scope is heading + new row only

Blast-radius Open Question 3 resolved: rename the README "Housekeeping" table heading to "Maintenance & Troubleshooting" and add a `hook-repair` row to that table.

**Scope is bounded:**
- Line 145 heading: `### Housekeeping` → `### Maintenance & Troubleshooting`.
- One new row added to the table, format matching existing rows (`| /sweetclaude:hook-repair | Restore broken installed hooks from backup. Uses Bash only — works when Write/Edit are blocked. |`).
- **No other content in the Housekeeping section changes.** Existing rows (off, purge, update, fix-sweetclaude) keep their current text. No reordering, no description rewrites, no merging with other tables.

This bounded scope avoids unrelated edits piggybacking on a rename. If the user wants broader README work, it is a separate item.

### 11. Skills-reference entry: System table row format

The new entry goes into the System table at `docs/user-guide/skills-reference.md`. Per the existing entries (lines 46–60), the row format is:

```markdown
| **Hook Repair** | `/sweetclaude:hook-repair` | Restore broken installed hooks from `hooks.bak/`. Uses Bash only — works when Write/Edit hooks are blocking. Diagnoses broken hooks via `bash -n`, proposes restoration via AskUserQuestion, verifies after restore. Falls through to `bash scripts/emergency-hook-restore.sh` if backup is missing or itself broken. |
```

Required fields per existing convention:
- **Bold display name** in the first column.
- **Backticked invocation** (`/sweetclaude:hook-repair`) in the second column. Per `feedback_skill_discovery.md`, the slash command must match the directory name (`skills/hook-repair/`).
- **Description** in the third column, ending with a period. One sentence describing what it does, optionally followed by a sentence on constraints or fall-through behavior.

Counter updates:
- Line 6: `All 103 skills` → `All 104 skills`.
- Line 40: `## System (14 skills)` → `## System (15 skills)`.

**Pre-existing drift is out of scope.** The actual `skills/` directory contains ~109 entries; the doc claims 103. Reconciliation is CHORE-014, not STORY-304. STORY-304 bumps from the documented baseline only.

### 12. Implementation order

The deliverable sequence is constrained by TDD Level 2 (Standard) per the framework default and by the inter-deliverable dependencies. Recommended order:

1. **`tests/test-emergency-restore.sh` first** — TDD Level 2 requires tests committed before implementation. The test file references the script path and the `CONTRACT_LINE_*`/`EHR_*` constants via source. Initially the source will fail (script does not exist) — that is the RED state. The test is committed in RED.
2. **`scripts/emergency-hook-restore.sh` second** — implement until all four test functions pass (GREEN). The constants are declared here and become available to the test via source.
3. **`docs/user-guide/hook-development.md` third** — create the stub file with the Recovery, Break Glass, and What to Read Next sections. No code dependency; can be done any time after the script body and its output contract are stable, but doing it after the script makes the documented commands match the actual script behavior verbatim.
4. **`skills/hook-repair/SKILL.md` fourth** — the skill body references the emergency script in its fall-through branch ("if backup is missing or broken, direct user to `bash scripts/emergency-hook-restore.sh`"). Authored after the script so the referenced command works on first invocation.
5. **`README.md` rename + row addition, `docs/user-guide/skills-reference.md` row + count updates fifth** — pure bookkeeping. Done last so the counters and references match the actual final state of the other deliverables.
6. **Version stamp (criterion 304-11) at the end of VERIFY** — write `Validated against SweetClaude v3.68.6` into the story file only after running through the manual end-to-end recovery test (criterion 304-5) on a real installed copy.

This order is consistent with the constraint that test files are immutable during implementation (test-guardian hook), which means the test must be authored, committed, and then frozen before script implementation begins.

### 13. In-place rewrite rationale (this document)

Spec v2.1 superseded spec v2.0 in place using `supersedes:` frontmatter. v2.0 of this design doc predates the spec v2.1 amendment (the `--dry-run` flag, four test functions instead of three, STORY-306 stub-file ordering, README heading rename, version-stamp decision). The same rewrite-in-place rationale applies: single canonical artifact at the well-known path, provenance in `supersedes:`, git history retains v2.0 for diff.

Options considered:
- New parallel file (`design-304-v3.md`) — would force every downstream reader (skill, sync script, story file, blast-radius) to disambiguate. Rejected.
- In-place rewrite with `supersedes: design-304 v2.0 (2026-05-19)` — chosen.

---

## Implementation order

See Decision 12 above. Summary:

1. Write and commit `tests/test-emergency-restore.sh` (RED).
2. Implement `scripts/emergency-hook-restore.sh` (RED → GREEN).
3. Create `docs/user-guide/hook-development.md` stub.
4. Author `skills/hook-repair/SKILL.md`.
5. Update README and `skills-reference.md`.
6. Manual end-to-end test, then write version stamp.

---

## Open design questions

**None — all decisions are resolved.**

Spec v2.1 and the blast-radius Open Questions section (all six items marked RESOLVED on 2026-05-19) cover every implementation decision needed to begin coding. The only remaining uncertainties are operational, not design:

- Whether the manual end-to-end test (criterion 304-5) will surface a real-installed-path edge case not covered by the four sandboxed tests. If so, the test surface expands; the script's design does not need to change.
- Whether the install-path resolver duplication (blast-radius Area 5) becomes a real drift problem within the lifetime of REL-004. Out of scope; tracked separately.

If either of these manifests, the resolution belongs in a follow-up story, not in a STORY-304 design amendment.
