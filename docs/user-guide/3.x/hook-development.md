# Hook Development

**Version:** 1.0 / **Date:** 2026-05-25

This page is for the stable 3.x channel. Stable 3.x does not have the 4.x beta
`/sweetclaude:hook-repair`, `/sweetclaude:doctor`, or `/sweetclaude:recover`
maintenance front doors. Use the manual recovery path below when a broken hook
blocks Claude Code Write or Edit operations.

## Recovery

**Symptom:** Claude Code returns `{"ok": false}` on Write or Edit operations.

Write and Edit hooks can block file changes when an installed hook has a syntax
error or logic bug. The Bash tool is unaffected by Write/Edit hooks, so recovery
uses shell commands instead of SweetClaude file edits.

The hooks most commonly involved in Write/Edit blockages are `test-guardian.sh`
and `auto-test-runner.sh`; both run during implementation phases. Other hooks
may warn or block narrow commands, but they should not prevent a direct Bash copy
of a known-good hook.

## Manual Repair

Find the installed plugin cache version:

```bash
ls ~/.claude/plugins/cache/sweetclaude/sweetclaude/
```

Check hook syntax:

```bash
bash -n ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh
```

If the installed cache has `hooks.bak/`, restore from it:

```bash
cp ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks.bak/<hook>.sh \
   ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh
```

Verify again:

```bash
bash -n ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh
```

## Reinstall If Manual Repair Fails

If there is no usable backup, update or reinstall the stable plugin package:

```text
/plugin update sweetclaude@sweetclaude-stable
```

Restart Claude Code after the plugin update. If the installed key is the legacy
unversioned key, update that exact key first:

```text
/plugin update sweetclaude@sweetclaude
```

Then standardize on the stable channel with the install commands in
[Install](install.md).

## What to Read Next

- [How It Works](how-it-works.md) — hook architecture and the Write/Edit matcher
- [Skills Reference](skills-reference.md) — stable 3.x system commands
- [TDD](tdd.md) — the testing discipline that keeps hooks correct
