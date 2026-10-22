# Hook Development

**Version:** 1.3 / **Date:** 2026-10-21

## Recovery

**Symptom:** a tool call fails with a hook error. When an installed hook has a bash syntax error it exits with status 2, and Claude Code reports a blocking hook error with the syntax error on stderr. Run `/sweetclaude:configure doctor` to diagnose and restore.

A hook can stop a tool call only when it is a PreToolUse hook. PostToolUse and Stop hooks run after the tool or response and give feedback; they cannot block the write itself. `auto-test-runner.sh` is a PostToolUse hook, so it reports test results after a Write or Edit and never blocks one.

The hooks that can block a tool call are `test-guardian.sh` (denies test file writes once `tdd_phase` is implementing), `tdd-prewrite-guardian.sh` (denies source writes until test files exist, when the guardian is on), `wip-limit.sh` (blocks only a call that activates an issue in Kanban mode when the WIP limit is already reached), and `preflight-guard.sh` (blocks until first valid invocation of the command that configures the project).

Every PreToolUse hook whose matcher covers Write or Edit can be the source of a blockage: `preflight-guard.sh`, `test-guardian.sh`, `tdd-prewrite-guardian.sh`, `wip-limit.sh`, `large-story-gate.sh` and `small-story-gate.sh`. Bash calls are also checked, so a recovery command is not exempt from hooks. Seven PreToolUse hooks match Bash in `hooks/hooks.json`:

- `preflight-guard.sh` blocks every tool call while the `/tmp/.sweetclaude-needs-preflight-<hash>` flag exists. The flag is cleared when `.sweetclaude/state/sweetclaude.yaml`, `.sweetclaude/state/phase.yaml` or `.sweetclaude-skip` exists. The command that configures the project stays reachable.
- `test-guardian.sh` blocks writes to test files during implementation, including Bash writes. Release a single test file with `python3 scripts/tdd_phase.py release --file <test file> --approval "<user's words>"`.
- `artifact-guardian.sh` warns without blocking, and only on `git commit`.
- `tdd-commit-gate.sh` denies a `git commit` that adds implementation source files on a story branch while a TDD cycle is active and no earlier commit on the branch has subject `test: RED`. Any other commit is allowed.
- `wip-limit.sh` blocks only the call that activates an issue in Kanban mode when the WIP limit is reached. Any other call is allowed.
- `large-story-gate.sh` and `small-story-gate.sh` deny tool calls outside the permitted phase of an active large-story or small-story workflow. With no active workflow they allow everything.

`tdd-prewrite-guardian.sh` matches Write and Edit only. It blocks source writes until test files exist; `/sweetclaude:configure guardian-off` bypasses it.

### Automated repair

Run:

    /sweetclaude:configure doctor

The `hook_health` category checks each hook and offers to restore a broken one by copying it from the plugin's hooks directory, then verifies the restored copy. `/sweetclaude:configure doctor` is a redirect to doctor.

### Manual repair

If the skill is unavailable, use Bash directly. `hooks.bak/` exists only after `scripts/sync-to-installed.sh` has been run (the developer sync described in CONTRIBUTING.md); a marketplace install has no backup directory, so restore from the repo copy instead:

    # Identify the broken hook
    bash -n ~/.claude/plugins/cache/sweetclaude-stable/sweetclaude/<ver>/hooks/<hook>.sh

    # Restore from the backup left by sync-to-installed.sh
    cp ~/.claude/plugins/cache/sweetclaude-stable/sweetclaude/<ver>/hooks.bak/<hook>.sh \
       ~/.claude/plugins/cache/sweetclaude-stable/sweetclaude/<ver>/hooks/<hook>.sh

    # Verify
    bash -n ~/.claude/plugins/cache/sweetclaude-stable/sweetclaude/<ver>/hooks/<hook>.sh

Replace `<ver>` with the installed version. Find it with:

    ls ~/.claude/plugins/cache/sweetclaude-stable/sweetclaude/

## Emergency Recovery (Break Glass)

If `/sweetclaude:configure doctor` is itself broken or unavailable, use the emergency restore script. This script has zero dependencies on SweetClaude infrastructure.

### From inside a deadlocked Claude Code session

Run the script from the installed plugin, because it finds the install from its own location and a relative `scripts/` path exists only inside the SweetClaude repo:

    bash ~/.claude/plugins/cache/sweetclaude-stable/sweetclaude/<ver>/scripts/emergency-hook-restore.sh

### From a terminal outside Claude Code

    bash /path/to/sweetclaude-repo/scripts/emergency-hook-restore.sh

### To restore a single hook

    bash ~/.claude/plugins/cache/sweetclaude-stable/sweetclaude/<ver>/scripts/emergency-hook-restore.sh test-guardian.sh

The script tries `hooks.bak/` first (present only after `scripts/sync-to-installed.sh`). If no backup exists, it copies directly from the repo.

### If nothing works

If the repo is also broken and no backup exists:

1. Re-install SweetClaude from the plugin marketplace
2. Or: check out a known-good git tag and copy hooks manually:
   `git checkout v3.68.6 -- hooks/ && cp hooks/*.sh ~/.claude/plugins/cache/.../hooks/`

## Testing Unreleased Hooks (`--plugin-dir`)

When you add or change a hook and want to test it before it ships, you will run the repo copy with `--plugin-dir`. **Do not run it alongside the installed plugin** — both are named `sweetclaude`, and Claude Code deduplicates hooks by command string across plugin sources. With two same-named `sweetclaude` plugins active, hook registration is unreliable: some events register and others are silently dropped, so your new hook may never fire even though the script is correct. `/hooks` will show fewer hooks than `hooks.json` defines.

Run the repo copy as the **only** `sweetclaude` plugin, one of two ways:

**A — clean config dir (least disruptive, recommended):**

    CLAUDE_CONFIG_DIR=/tmp/sc-clean claude --plugin-dir /path/to/sweetclaude

No installed plugins load, so there is no name collision. Verify with `/hooks` that the counts match `hooks.json` (e.g. PreToolUse, PostToolUse, Stop groups all present).

**B — uninstall the marketplace copy for the duration:**

    # in a normal session
    /plugin            # uninstall sweetclaude@sweetclaude-stable
    # quit, then:
    claude --plugin-dir /path/to/sweetclaude
    # ...test... then reinstall afterward via /plugin

**Confirm hooks loaded before trusting a test:** run `/hooks` and check that every event group your change touches is present and the counts match `hooks.json`. A hook that does not appear is not loaded — fix loading before concluding anything about behavior. (`claude --debug hooks` logs hook evaluation live if you need detail.)

The large-story workflow has a built-in guard for exactly this failure: it runs an enforcement self-check before IMPLEMENT and refuses to proceed if its gate hook is not actually loaded — so a dropped hook fails loud rather than letting the workflow run unprotected.

## What to Read Next

- [How It Works](how-it-works.md) — hook architecture and the Write|Edit matcher
- [Skills Reference](skills-reference.md) — full list of available skills including `/sweetclaude:configure doctor`
- [TDD](tdd.md) — the testing discipline that keeps hooks correct before they are synced
