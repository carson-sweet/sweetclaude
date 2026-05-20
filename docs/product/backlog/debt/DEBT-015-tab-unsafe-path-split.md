---
id: DEBT-015
type: debt
title: "Tab-unsafe path split in find fallback of emergency-hook-restore.sh"
status: new
priority: later
effort: xs
tags: [self-hosting, hooks, emergency-restore, correctness, shell]
created: 2026-05-19
updated: 2026-05-19
---

# Tab-unsafe path split in find fallback of emergency-hook-restore.sh

## Context

Identified during STORY-304 adversarial completion caucus.

`scripts/emergency-hook-restore.sh` lines 100–107 resolve the most-recently-modified install path using a find fallback. It builds candidate lines as `<mtime>\t<path>` (tab-separated), sorts numerically, and splits on tab with `cut -f2-`:

```bash
INSTALL_PATH=$(find "$HOME/.claude/plugins/cache" -type d \
  -path "*/sweetclaude/sweetclaude/*" -name hooks 2>/dev/null \
  | while IFS= read -r d; do
      printf '%s\t%s\n' "$(stat -f '%m' "$d" 2>/dev/null || stat -c '%Y' "$d" 2>/dev/null)" "$d"
    done \
  | sort -rn | head -1 | cut -f2- || true)
```

A filesystem path containing a literal tab character would corrupt the `cut -f2-` split and resolve the wrong install path. In practice, plugin cache paths under `~/.claude/plugins/cache/` never contain tabs, so this is a theoretical edge case — but a correctness failure in a recovery-path script is worth eliminating.

## Work

Replace the tab-delimited sort pattern with a null-delimited or space-safe alternative. One approach:

```bash
INSTALL_PATH=$(find "$HOME/.claude/plugins/cache" -type d \
  -path "*/sweetclaude/sweetclaude/*" -name hooks 2>/dev/null \
  | while IFS= read -r d; do
      printf '%s %s\n' "$(stat -f '%m' "$d" 2>/dev/null || stat -c '%Y' "$d" 2>/dev/null)" "$d"
    done \
  | sort -rn | head -1 | cut -d' ' -f2- || true)
```

Space is also unsafe in paths but no safer than tab. The robust fix is `find -printf '%T@ %p\0'` (GNU) with NUL-delimited sort — but that sacrifices macOS portability. An alternative: sort by mtime using `stat` output piped through `sort -t$'\t' -k1,1rn` with explicit IFS, then extract the second field without relying on `cut`.

The fix must preserve the cross-platform (macOS + Linux) compatibility already established by the `stat -f '%m' || stat -c '%Y'` pattern.

## Acceptance criteria

- Install-path resolution produces the correct result when a plugin cache path contains a tab character
- Existing `test_cascade_resolution` tests continue to pass
- No new `source` calls introduced (zero-dependency invariant preserved)
