# Moving From 3.x Stable To 4.x Beta

This page is for stable 3.x users who are considering the 4.x beta channel.
Do not use `/sweetclaude:update` to move from stable to beta. `/sweetclaude:update`
syncs framework files inside the installed channel; it is not a channel switch.

## Stay On 3.x Stable For Normal Work

Stable 3.x is still the recommended channel for active project work. Keep it
updated with:

```text
/plugin update sweetclaude@sweetclaude-stable
```

Restart Claude Code, then run this inside each SweetClaude project when framework
files need syncing:

```text
/sweetclaude:update
```

## Opt Into 4.x Beta Explicitly

Install beta as its own channel:

```text
/plugin marketplace add carson-sweet/sweetclaude@beta-4.x
/plugin install sweetclaude@sweetclaude-beta
```

Restart Claude Code after installation. Then read the beta guide before running
maintenance commands:

- [4.x Beta User Guide](../4.x-beta/index.md)
- [4.x Migration and Recovery](../4.x-beta/migration-and-recovery.md)
- [4.x Beta Rescue](../4.x-beta/beta-rescue.md)

## Migration Rule

Do not start an old project by running `/sweetclaude:migrate`. In 4.x beta,
maintenance starts with plugin update, restart, `/sweetclaude:update`, then
`/sweetclaude:doctor`. Doctor decides whether recovery, supported migration,
compatibility mode, or normal work is appropriate.
