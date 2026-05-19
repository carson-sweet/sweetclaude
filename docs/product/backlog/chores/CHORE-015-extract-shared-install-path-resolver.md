---
id: CHORE-015
type: chore
title: "Extract shared install-path resolver to eliminate triplicate drift"
status: new
priority: soon
effort: s
tags: [self-hosting, sync, scripts, drift, architecture]
created: 2026-05-19
updated: 2026-05-19
---

# Extract shared install-path resolver to eliminate triplicate drift

## Context

Three scripts contain independent copies of the same `installed_plugins.json` resolution logic (scope filter, lastUpdated sort, hooks/ subdir check, find fallback):

1. `scripts/sync-to-installed.sh` — `_resolve_install_path()` function (lines 20–36)
2. `scripts/preflight.sh` — inline resolver
3. `scripts/emergency-hook-restore.sh` — inline resolver (added by STORY-304)

The "zero SweetClaude dependencies" design principle for `emergency-hook-restore.sh` required the third copy. Each copy drifts independently. If `installed_plugins.json` adds a new `scope` value, renames `lastUpdated`, or restructures the plugin entry format, all three must be updated. No automated test currently detects divergence between them.

Surfaced by the STORY-304 architect caucus (concern C2).

## Work

1. Document a canonical version of the resolver as a comment block in `scripts/sync-to-installed.sh` — the reference copy.
2. Write a test (in `tests/` or `tests/hooks/`) that sources all three scripts and asserts the resolver logic produces identical output for the same synthetic `installed_plugins.json` input.
3. Update `scripts/emergency-hook-restore.sh`'s header comment to reference `sync-to-installed.sh` as the canonical version.

Do NOT attempt to extract to a shared function file — `emergency-hook-restore.sh`'s zero-dependency constraint forbids sourcing helpers. The goal is a drift-detection test, not DRY elimination.

## Acceptance criteria

- A test exists that fails if the three resolver copies produce different output for the same input
- `scripts/sync-to-installed.sh` is documented as the canonical reference for the resolver logic
- `scripts/emergency-hook-restore.sh` header references sync-to-installed.sh as the canonical copy
