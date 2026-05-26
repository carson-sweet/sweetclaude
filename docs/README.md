# SweetClaude Documentation

Start with the guide that matches the SweetClaude plugin channel installed in
Claude Code. The main channel and beta channel are intentionally documented
separately because install, update, repair, migration, and state behavior differ.

## Main Version: Stable 3.x

Stable 3.x is the recommended channel for normal active project work.

| Item | Link |
|---|---|
| User guide index | [3.x Stable User Guide](user-guide/3.x/index.md) |
| Install and update | [3.x Install](user-guide/3.x/install.md) |
| How it works | [3.x How It Works](user-guide/3.x/how-it-works.md) |
| Changelog | [Stable 3.x changelog notes](../CHANGELOG.md#stable-3x-channel--current-3686) |

Stable 3.x uses:

```text
/plugin marketplace add carson-sweet/sweetclaude@stable-3.x
/plugin install sweetclaude@sweetclaude-stable
```

Stable project repair uses `/sweetclaude:fix-sweetclaude`. Stable update is
package update first, Claude Code restart second, then `/sweetclaude:update`
inside each project when framework files need syncing.

## Beta Version: 4.x Beta

4.x beta is explicit opt-in for users testing the newer project-maintenance and
taxonomy model.

| Item | Link |
|---|---|
| User guide index | [4.x Beta User Guide](user-guide/4.x-beta/index.md) |
| Install and update | [4.x Beta Install](user-guide/4.x-beta/install.md) |
| How it works | [4.x Beta How It Works](user-guide/4.x-beta/how-it-works.md) |
| Migration and recovery | [4.x Migration and Recovery](user-guide/4.x-beta/migration-and-recovery.md) |
| Rescue guide | [4.x Beta Rescue](user-guide/4.x-beta/beta-rescue.md) |
| Changelog | [4.x beta release history](../CHANGELOG.md#4112-beta--2026-05-25) |

4.x beta uses:

```text
/plugin marketplace add carson-sweet/sweetclaude@beta-4.x
/plugin install sweetclaude@sweetclaude-beta
```

4.x beta separates framework update from project maintenance. Update the plugin
package and restart Claude Code before running `/sweetclaude:update`. Project
repair, recovery, and supported migration route through `/sweetclaude:doctor`,
`/sweetclaude:recover`, and guarded `/sweetclaude:migrate`.

## Main Differences

| Area | Stable 3.x | 4.x beta |
|---|---|---|
| Recommended use | Normal active project work | Explicit beta testing |
| Installed key | `sweetclaude@sweetclaude-stable` | `sweetclaude@sweetclaude-beta` |
| Update boundary | Stable-only framework sync | Beta-only framework sync plus drift reporting |
| Repair entry point | `/sweetclaude:fix-sweetclaude` | `/sweetclaude:doctor` |
| Recovery | Manual or stable update repair paths | `/sweetclaude:recover` with snapshots and rollback report |
| Migration | Supported stable state migrations during update | Guarded taxonomy migration after doctor preflight |
| Product artifacts | Stable Markdown/YAML project state | Unified `ISSUE-NNN` taxonomy under `.sweetclaude/product/` plus rebuildable SQLite cache |

Do not use `/sweetclaude:update` to move between channels. Channel switching is
explicit: install the other plugin channel and follow that channel's guide.

## Other Entry Points

- [Back to main README](../README.md)
- [Choose a user-guide track](user-guide/index.md)
- [Full changelog](../CHANGELOG.md)
