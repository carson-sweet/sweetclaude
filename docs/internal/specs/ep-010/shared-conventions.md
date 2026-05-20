---
epic: EP-010
title: Shared Conventions and Interfaces
version: 1.0
date: 2026-05-18
status: draft
---

# EP-010: Shared Conventions and Interfaces

All EP-010 designs reference these shared patterns. Changes here propagate to all stories.

## Installed path resolution

Canonical pattern for resolving the installed plugin path. Used by: STORY-300, 304, 305.

```bash
_resolve_install_path() {
  python3 -c "
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [e for versions in d.get('plugins', {}).values()
               for e in versions if e.get('scope') == 'user']
    entries.sort(key=lambda e: e.get('lastUpdated', ''), reverse=True)
    for e in entries:
        ip = e.get('installPath', '')
        if ip and os.path.isdir(os.path.join(ip, 'hooks')):
            print(ip)
            break
except Exception:
    pass
" 2>/dev/null
}
```

This is the same resolution pattern used in `scripts/preflight.sh` (lines 45-59), filtering by `scope=user` and sorting by `lastUpdated`. The only difference: we check for `hooks/` subdirectory instead of `scripts/`.

Fallback (for emergency script only):
```bash
find ~/.claude/plugins/cache -type d -path "*/sweetclaude/sweetclaude/*/hooks" \
  -exec dirname {} \; 2>/dev/null | head -1
```

## Phase detection

Canonical pattern for reading the active phase. Used by: STORY-300.

```bash
_read_phase() {
  local project_dir="$1"
  local phase=""

  # Schema v1: standalone phase.yaml
  if [ -f "$project_dir/.sweetclaude/state/phase.yaml" ]; then
    phase=$(grep "^phase:" "$project_dir/.sweetclaude/state/phase.yaml" 2>/dev/null | awk '{print $2}')
  fi

  # Schema v2: sweetclaude.yaml work.active.phase
  if [ -z "$phase" ] && [ -f "$project_dir/.sweetclaude/state/sweetclaude.yaml" ]; then
    phase=$(SC_YAML="$project_dir/.sweetclaude/state/sweetclaude.yaml" python3 - <<'PYEOF' 2>/dev/null
import os
try:
    import yaml
    d = yaml.safe_load(open(os.environ['SC_YAML']))
    w = (d or {}).get('work', {}).get('active', {})
    print(w.get('phase', '') if w else '')
except ImportError:
    pass
PYEOF
)
    # Fallback if PyYAML is not installed
    if [ -z "$phase" ]; then
      phase=$(grep "^ *phase:" "$project_dir/.sweetclaude/state/sweetclaude.yaml" 2>/dev/null \
        | head -1 | awk '{print $2}')
    fi
  fi

  printf '%s' "$phase"
}
```

Case-insensitive comparison: callers normalize with `tr '[:upper:]' '[:lower:]'` or match both cases.

**Python safety rule:** Never interpolate shell variables into `python3 -c "..."` strings. Always pass values as environment variables and use heredoc (`python3 - <<'PYEOF'`) so the Python source is static. This pattern is already used correctly in `test-guardian.sh` lines 42-53.

## Exit codes for sync-to-installed.sh

| Code | Meaning | Set by |
|---|---|---|
| 0 | Success (or dry-run passed) | 300 |
| 1 | Phase check blocked sync | 300 |
| 2 | Test gate blocked sync | 302 |
| 3 | Backup failed | 301 |
| 4 | Sync failed (rsync error) | 300 |
| 5 | Path resolution failed | 300 |
| 6 | Post-sync symlink detected | 305 |

## Sync targets

The sync script writes to multiple locations, matching `experimental-feature-setup`'s targets:

| Target | Content | Purpose |
|---|---|---|
| `$INSTALL_PATH/hooks/` | Repo `hooks/` | Plugin-native hooks dispatch from here |
| `$INSTALL_PATH/skills/` | Repo `skills/` | Plugin skill dispatch from here |
| `$INSTALL_PATH/scripts/` | Repo `scripts/` | Plugin scripts dispatch from here |
| `~/.claude/scripts/sweetclaude/` | Repo `scripts/` | Versionless scripts path (bootstrap, preflight) |
| `~/.claude/config/sweetclaude/` | Repo `config/` | Configuration files |
| `$VERSION_DIR/` | Repo skills/hooks/scripts | Version-named sibling directory |

Safety gates (phase check, test gate, backup, symlink check) apply to the hooks target only. All other targets sync unconditionally after hooks pass.

## hooks.bak/ convention

| Field | Value |
|---|---|
| Path | `$INSTALL_PATH/hooks.bak/` |
| Contents | Complete copy of `$INSTALL_PATH/hooks/` from immediately before the last sync |
| Generations | 1 (overwritten each sync) |
| Created by | STORY-301 (backup step in sync-to-installed.sh) |
| Read by | STORY-304 (hook-repair skill, emergency script) |

## Canonical sync pipeline sequence

The sync script layers all gates in strict order. This is the single source of truth — all stories adding steps to `sync-to-installed.sh` must place their code at the correct position.

```
1. Parse args (--force, --dry-run)           ← STORY-300
2. Resolve paths (repo root, installed path) ← STORY-300
3. Phase check (block if implement)          ← STORY-300
4. Test gate (run test-hooks.sh)             ← STORY-302
5. [dry-run exit]                            ← STORY-300
6. Backup (cp hooks/ to hooks.bak/)          ← STORY-301
7. Sync hooks (rsync)                        ← STORY-300
8. Post-sync checks (symlink verification)   ← STORY-305
9. Sync non-hook artifacts (unconditional)   ← STORY-300
```

Steps 1-4 run even in dry-run mode. Step 5 exits if `--dry-run`. Steps 6-9 only run in normal mode. The test gate (step 4) is non-bypassable — `--force` does not skip it.

## Test fixture conventions

All hook tests in `tests/test-hooks.sh` follow these patterns:

| Convention | Detail |
|---|---|
| Temp root | `$TMPROOT` (created once, cleaned up on EXIT trap) |
| Per-test HOME | `$TMPROOT/homeN` (prevents touching real ~/.claude) |
| Per-test project | `$TMPROOT/projN` with `_make_git_repo` |
| Phase fixture | `printf 'phase: implement\ntdd_phase: implementing\n' > "$PROJ/.sweetclaude/state/phase.yaml"` |
| Assertion | `pass "description"` / `fail "description"` with `$FAILED` counter |
| Test numbering | Sequential integers. Existing: 1-10. New tests start at 11. |
| JSON validation | Pipe hook output to `python3 -c "import sys, json; d = json.loads(sys.stdin.read()); ..."` |

## Implementation notes

### PyYAML fallback isolation

`_read_phase()` has two code paths for v2 YAML: PyYAML (primary) and grep (fallback). The grep fallback (`grep "^    phase:"` with 4-space indent) is exercised only when PyYAML is not installed. Implementers should verify both paths during testing. To test the grep fallback in isolation, temporarily rename the `import yaml` line to force the `ImportError` path, or run in a venv without PyYAML. Key edge cases for the grep fallback: quoted values (`phase: "implement"`), trailing whitespace, tab-indented YAML.

### installed_plugins.json edge cases

`_resolve_install_path()` reads `~/.claude/plugins/installed_plugins.json` and filters by `scope=user`. Implementers should be aware of these edge cases during testing:
- Multiple entries where the one with a `hooks/` subdirectory is not the first in the array
- An entry with `scope=global` appearing before the `scope=user` entry (should be filtered out)
- `lastUpdated` sort order selecting the most-recently-updated entry when multiple `scope=user` entries exist
- Valid JSON with zero matching entries (should produce exit code 5, same as missing file)
