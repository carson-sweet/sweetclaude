# SweetClaude User Guides

SweetClaude has two separate user-guide tracks. Choose the guide that matches the
plugin channel installed in Claude Code.

| Track | Installed key | Use it when | Guide |
|---|---|---|---|
| Stable 3.x | `sweetclaude@sweetclaude-stable` | You want the recommended stable channel for active project work. | [3.x Stable User Guide](3.x/index.md) |
| 4.x beta | `sweetclaude@sweetclaude-beta` | You intentionally opted into beta project maintenance and taxonomy changes. | [4.x Beta User Guide](4.x-beta/index.md) |

The tracks are intentionally separate. Install, update, recovery, migration,
state layout, and skill-surface details differ enough that shared guide pages are
more confusing than useful.

## Install Shortcuts

Stable 3.x:

```text
/plugin marketplace add carson-sweet/sweetclaude@stable-3.x
/plugin install sweetclaude@sweetclaude-stable
```

4.x beta:

```text
/plugin marketplace add carson-sweet/sweetclaude@beta-4.x
/plugin install sweetclaude@sweetclaude-beta
```

Do not use `/sweetclaude:update` to move between channels. Update the installed
plugin package first, restart Claude Code, then run `/sweetclaude:update` inside
that same channel.
