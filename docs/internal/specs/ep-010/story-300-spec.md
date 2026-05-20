---
id: SPEC-300
story: STORY-300
epic: EP-010
version: 1.0
date: 2026-05-18
status: done
---

# Specification: STORY-300 Phase-aware sync gate

## User story

As a SweetClaude developer working on hook code during an IMPLEMENT phase, I want the sync-to-installed mechanism to refuse to copy my in-progress work to the installed path so that a broken repo hook can never take down my running session.

## Deliverables

1. New script: `scripts/sync-to-installed.sh`
2. Phase check integrated into `skills/experimental-feature-setup/SKILL.md`

## Technical design

### scripts/sync-to-installed.sh

Bash script. Executable (`chmod +x`). Invoked as `bash scripts/sync-to-installed.sh [--force] [--dry-run]`.

**Path resolution:**

```bash
# Repo root
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Installed path — uses canonical _resolve_install_path() from shared-conventions.md
# (filters by scope=user, sorts by lastUpdated, checks for hooks/ subdirectory)
INSTALL_PATH=$(_resolve_install_path)
```

If either path is unresolvable, exit non-zero with error message.

**Phase detection:**

Check both schema locations. Order: `phase.yaml` first (explicit phase file), then `sweetclaude.yaml` (unified state).

```bash
# Uses canonical _read_phase() from shared-conventions.md
# (checks phase.yaml first, falls back to sweetclaude.yaml with PyYAML + grep fallback)
# PROJECT_DIR is $(pwd) — the project being developed, not REPO_ROOT (the script's location).
# These are identical in normal use but differ in test fixtures.
PROJECT_DIR="$(pwd)"
PHASE=$(_read_phase "$PROJECT_DIR")
```

Case-insensitive check: block if `PHASE` matches `implement` or `IMPLEMENT`.

**`--force` behavior:**

Bypasses phase check only. Appends to decision log:

```bash
# Count existing entries
LAST_NUM=$(grep -oE '^\| [0-9]+' "$DECISION_LOG" | tr -d '| ' | sort -n | tail -1 || echo "0")
[ -z "$LAST_NUM" ] && LAST_NUM=0
NEXT_NUM=$((LAST_NUM + 1))
DATE=$(date +%Y-%m-%d)
echo "| $NEXT_NUM | $DATE | IMPLEMENT | Force-synced hooks during implement phase | Developer override via --force flag |" >> "$DECISION_LOG"
```

Decision log path: `$PROJECT_DIR/.sweetclaude/state/decision-log.md` (where `PROJECT_DIR=$(pwd)`). Format matches existing entries: `| # | Date | Phase | Decision | Rationale |`.

**`--dry-run` behavior:**

Runs all checks (phase, tests) but does not execute sync or backup. Prints what would happen. Exits 0 if all checks pass.

**Full sync after hooks pass gates:**

After hooks are synced and verified, the script syncs non-hook artifacts unconditionally:

```bash
# Skills
rsync -a "$REPO_ROOT/skills/" "$INSTALL_PATH/skills/"

# Scripts
rsync -a "$REPO_ROOT/scripts/" "$INSTALL_PATH/scripts/"
mkdir -p ~/.claude/scripts/sweetclaude
rsync -a "$REPO_ROOT/scripts/" ~/.claude/scripts/sweetclaude/

# Config
if [ -d "$REPO_ROOT/config" ]; then
  rsync -a "$REPO_ROOT/config/" ~/.claude/config/sweetclaude/
fi
```

No safety gates on these — they don't fire as hooks and can't deadlock a session.

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Sync completed (or dry-run passed) |
| 1 | Phase check blocked sync |
| 2 | Test gate blocked sync |
| 3 | Backup failed |
| 4 | Sync failed |
| 5 | Path resolution failed |
| 6 | Post-sync symlink detected |

### experimental-feature-setup integration

Add phase check to Step 4 of the skill, before the rsync commands. The check uses the same dual-schema logic. If phase is `implement` and no `--force` equivalent is provided, the skill refuses the sync step and reports why. Long-term, `experimental-feature-setup` can delegate to `sync-to-installed.sh` directly.

## Constraints

- `test-guardian.sh` reads phase from `phase.yaml` only (lines 24-29 of the hook). It does not read `sweetclaude.yaml`. The sync gate is more thorough than the hook it protects.
- Decision log uses markdown table format. New entries must be appended as table rows, not as free text.
- `experimental-feature-setup` is an untracked local-only skill. Changes to it are not committed to git.

## Success criteria

| # | Criterion | Verification |
|---|---|---|
| 300-1 | `scripts/sync-to-installed.sh` exists and is executable | `test -x scripts/sync-to-installed.sh` |
| 300-2 | Sync blocked when `phase.yaml` contains `phase: implement` | Exit code non-zero, output contains "IMPLEMENT" |
| 300-3 | Sync blocked when `phase.yaml` contains `phase: IMPLEMENT` | Same check with uppercase |
| 300-4 | Sync proceeds when `phase.yaml` is absent and `sweetclaude.yaml` has no active implement phase | Exit code 0 (or dry-run succeeds) |
| 300-5 | Sync proceeds when `phase.yaml` contains `phase: verify` | Exit code 0 |
| 300-6 | `--force` overrides phase check | Exit code 0 even with `phase: implement` |
| 300-7 | `--force` appends entry to decision log (actual sync only) | `grep` for today's date + "force" in decision-log.md after real sync. `--force --dry-run` must NOT append a log entry. |
| 300-8 | `experimental-feature-setup` applies the same phase check | Invoke skill with `phase: implement` active → sync step refused (manual verification — untracked skill) |
| 300-9 | Sync blocked when `sweetclaude.yaml` contains `work.active.phase: implement` and no `phase.yaml` exists | Exit code non-zero, output contains "IMPLEMENT" |
| 300-10 | `--dry-run` runs all checks without syncing | Exit code 0 if all checks pass, no files modified |
| 300-11 | `tests/test-sync.sh` exists and passes | `bash tests/test-sync.sh` exits 0. Scope: STORY-300's own test cases (phase gate, --force, --dry-run). Downstream stories (301, 302, 305) add their own test cases to this file. |
| 300-12 | Unknown argument produces non-zero exit and error message | `--bogus` → non-zero exit, stderr contains "Unknown argument" |
| 300-13 | Missing `installed_plugins.json` produces exit code 5 | No plugins JSON → exit 5 |
| 300-14 | `phase.yaml` takes precedence over `sweetclaude.yaml` | Both files present, `phase.yaml` says verify, `sweetclaude.yaml` says implement → exit 0 (verify wins) |
| 300-15 | `sweetclaude.yaml` with non-implement phase allows sync | `sweetclaude.yaml` has `work.active.phase: verify`, no `phase.yaml` → exit 0 |
| 300-16 | `--force` without `decision-log.md` does not error | `--force` during implement with no decision-log.md → exit 0 |
| 300-17 | `--dry-run` does not create new files at installed path | `--dry-run` with hooks in repo → file count at installed path unchanged |

## Dependencies

- None. This is the foundation script that STORY-301, 302, and 305 add to.

## Known gaps

None.
