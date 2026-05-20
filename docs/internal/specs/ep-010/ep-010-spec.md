---
id: SPEC-EP-010
epic: EP-010
version: 1.0
date: 2026-05-18
status: draft
---

# Specification: EP-010 Self-Hosting Infrastructure

## Objective

Enable SweetClaude to manage its own development with zero manual safety rules. All three self-hosting carve-outs identified by the architect caucus are either eliminated (carve-outs 1 and 2) or reduced to a machine-checked invariant (carve-out 3).

## Architecture

### Two-copy model

| Copy | Path | Role |
|---|---|---|
| Repo | `/Users/carsonsweet/dev/sweetclaude/hooks/` | Development copy. Editable. |
| Installed | `~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/` | Live copy. Fires on every tool call. |

The installed path is resolved at runtime from `~/.claude/plugins/installed_plugins.json`. The resolution logic already exists in `skills/experimental-feature-setup/SKILL.md` Step 2.

### Threat model

A broken installed hook blocks all Write/Edit operations with no in-session escape via those tools. The Bash tool is NOT gated by Write|Edit hooks — it is the recovery escape hatch.

The three carve-outs and their mitigations:

| # | Carve-out | Mitigation | Stories |
|---|---|---|---|
| 1 | Level 1 TDD only on hooks | Pre-sync test gate blocks untested hooks from reaching installed path | 302, 303 |
| 2 | No sync during IMPLEMENT | Phase-aware sync gate blocks sync when phase is implement | 300 |
| 3 | No symlinks (unsolvable) | Machine detection at session start + automated repair | 305 |

Cross-cutting: backup-on-sync (301) provides the recovery source, Bash-based repair (304) is the recovery mechanism, documentation (306) makes the workflow explicit.

### Execution order in sync-to-installed.sh

The canonical sync script layers all gates in sequence. Safety gates apply to hooks only; non-hook artifacts sync unconditionally after hooks pass all gates.

```
1. Parse args (--force, --dry-run)
2. Resolve paths (repo root, installed path from installed_plugins.json)
3. Phase check → abort if phase: implement (unless --force; --force logs to decision-log.md)
4. Test gate → run bash tests/test-hooks.sh → abort on failure (--force does NOT bypass)
5. Dry-run exit → if --dry-run, report and exit 0 (steps 1-4 still run as validation)
6. Backup → cp installed hooks/ to hooks.bak/ → abort on failure
7. Sync hooks → rsync repo hooks/ to installed hooks/
8. Post-sync checks → chmod +x, verify no symlinks
9. Sync non-hook artifacts → rsync skills/, scripts/, config/ (no gates, unconditional)
```

### Phase detection

Phase state lives in one of two locations depending on schema version:

| Schema | Location | Field |
|---|---|---|
| v1 | `.sweetclaude/state/phase.yaml` | `phase: implement` |
| v2 | `.sweetclaude/state/sweetclaude.yaml` | `work.active.phase: implement` |

All phase checks in this epic must inspect both locations. A v2 project may not have `phase.yaml` at all.

### Story dependency graph

```
STORY-303 (test coverage)     — no dependencies, can start first
STORY-300 (sync gate)         — no dependencies, can start first
STORY-301 (backup)            — depends on 300 (adds to sync script)
STORY-302 (test gate)         — depends on 300, 303 (adds to sync script, needs tests to exist)
STORY-305 (symlink detection) — depends on 300 (adds post-sync check to sync script)
STORY-306 (documentation)     — depends on 300, 301, 302 (documents their outputs)
STORY-304 (recovery)          — depends on 301, 306 (needs hooks.bak/ and doc file)
```

Parallelizable: 300 and 303 can proceed concurrently. Everything else is sequential.

## Epic-level success criteria

From the epic file (10 criteria, E1–E10). All are covered by story-level criteria. No gap between epic criteria and story coverage.

## Scope

**In scope:** Full sync to installed path (hooks, skills, scripts, config) with hook-specific safety gates. Hook test coverage, hook backup/recovery, symlink detection, hook development documentation.

**Out of scope:** Safety gates for non-hook artifacts. Skills, scripts, and config sync unconditionally because they don't fire on tool calls and can't deadlock a session. The safety gates (phase check, test gate, backup, symlink check) apply to hooks only.

`sync-to-installed.sh` replaces `experimental-feature-setup` as the canonical sync mechanism.

## Known gaps

None. All gaps resolved:
- Sync scope: full sync with hook-specific gates (decided 2026-05-18).
- `--dry-run`: added as criterion 300-10 to STORY-300.
- Break-glass recovery: added as criteria 304-6/7/8 with standalone emergency script.
