# SweetClaude Documentation

**Version:** 2.0
**Date:** 2026-08-03

Start with the guide that matches the SweetClaude plugin channel installed in
Claude Code.

## Stable: 5.x on `main`

Stable 5.x is the recommended channel for normal active project work.

| Item | Link |
|---|---|
| User guide index | [User Guide](user-guide/index.md) |
| Install and update | [Install](user-guide/install.md) |
| How it works | [How It Works](user-guide/how-it-works.md) |
| Migration and recovery | [Migration and Recovery](user-guide/migration-and-recovery.md) |
| Rescue guide | [4.x Beta Rescue](user-guide/beta-rescue.md) (for installs from the retired beta channel) |
| Changelog | [Full changelog](../CHANGELOG.md) |

Stable 5.x uses:

```text
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
```

Stable 5.x separates framework update from project maintenance. Update the
plugin package and restart Claude Code, then use `/sweetclaude:configure` and
state the outcome you want (for example, “update SweetClaude” or “diagnose and
repair this project”). Project repair, recovery, and supported migration are
routed internally by that configuration entry point.

## Legacy: 3.x on `stable-3.x`

Legacy 3.x receives maintenance only. New installs should use stable 5.x.

| Item | Link |
|---|---|
| User guide index | [3.x User Guide (stable-3.x branch)](https://github.com/carson-sweet/sweetclaude/blob/stable-3.x/docs/user-guide/index.md) |
| Install and update | [3.x Install (stable-3.x branch)](https://github.com/carson-sweet/sweetclaude/blob/stable-3.x/docs/user-guide/install.md) |

Legacy 3.x uses:

```text
/plugin marketplace add carson-sweet/sweetclaude@stable-3.x
/plugin install sweetclaude@sweetclaude-legacy
```

To move a 3.x project to the stable line, run these in order. Old 3.x installs registered their marketplace as `sweetclaude-stable`, so remove it first:

```text
/plugin marketplace remove sweetclaude-stable
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
```

Then restart Claude Code and run `/sweetclaude:configure doctor` in each project. Doctor routes legacy project state to recovery or migration; update does not migrate project data.

## Retired: 4.x Beta

The 4.x beta channel is retired. It no longer receives updates and cannot be
installed. If `/plugin list` shows `sweetclaude@sweetclaude-beta`, make the
one-time switch to stable — run these in order so SweetClaude stays installed throughout (both channels are installed briefly, and all three steps finish before you restart Claude Code):

```text
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
/plugin marketplace remove sweetclaude-beta
```

Then restart Claude Code and use `/sweetclaude:configure update SweetClaude`. If a former beta
install is stuck, see [4.x Beta Rescue](user-guide/beta-rescue.md).

## Design & Analysis

| Item | Link |
|---|---|
| Native Claude Code capabilities vs. SweetClaude | [Native capabilities analysis](design/native-capabilities-analysis.md) |
| Tiered command and library design | [Tiered skill architecture](design/tiered-skill-architecture.md) |
| Skill audit and disposition | [Skill audit ledger](design/skill-audit-ledger.md) |

## Historical records

`internal/`, `plans/`, and `codex-evaluation/` preserve dated design, release,
and evaluation evidence. They may name the command surface that existed at the
time of the record; use the current user guide, not those records, for current
commands.

## Other Entry Points

- [Back to main README](../README.md)
- [User guide](user-guide/index.md)
- [Full changelog](../CHANGELOG.md)
