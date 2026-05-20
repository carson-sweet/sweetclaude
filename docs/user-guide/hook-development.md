# Hook Development

**Version:** 1.0 / **Date:** 2026-05-19

## Recovery

**Symptom:** Claude Code returns `{"ok": false}` on Write or Edit operations.
Run `/sweetclaude:hook-repair` to diagnose and restore.

When an installed hook has a syntax error or logic bug, Write and Edit
operations are blocked — the broken hook returns `{"ok": false}` for
every call. The Bash tool is unaffected because Write|Edit hooks only
match those two tools. The two hooks most commonly involved in Write|Edit
blockages are `test-guardian.sh` and `auto-test-runner.sh` — both fire on
every Write or Edit call during an active implementation phase.

Three other hooks also match Bash, but none block a recovery `cp`:
`artifact-guardian.sh` (warn-only, gates only `git commit`),
`wip-limit.sh` (blocks only in Kanban mode at WIP limit, not during
recovery), and `preflight-guard.sh` (blocks until first valid invocation;
clears automatically once `phase.yaml` exists). In a normal recovery
scenario all three are either inactive or transparent.

### Automated repair

If the hook-repair skill is available:

    /sweetclaude:hook-repair

The skill diagnoses broken hooks, offers to restore from `hooks.bak/`,
and verifies the restoration.

### Manual repair

If the skill is unavailable, use Bash directly:

    # Identify the broken hook
    bash -n ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh

    # Restore from backup
    cp ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks.bak/<hook>.sh \
       ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh

    # Verify
    bash -n ~/.claude/plugins/cache/sweetclaude/sweetclaude/<ver>/hooks/<hook>.sh

Replace `<ver>` with the installed version. Find it with:

    ls ~/.claude/plugins/cache/sweetclaude/sweetclaude/

## Emergency Recovery (Break Glass)

If the hook-repair skill is itself broken or unavailable, use the
emergency restore script. This script has zero dependencies on
SweetClaude infrastructure.

### From inside a deadlocked Claude Code session

The Bash tool is never gated by Write/Edit hooks. Run:

    bash scripts/emergency-hook-restore.sh

### From a terminal outside Claude Code

    cd /path/to/sweetclaude-repo
    bash scripts/emergency-hook-restore.sh

### To restore a single hook

    bash scripts/emergency-hook-restore.sh test-guardian.sh

The script tries `hooks.bak/` first (last known-good state). If no
backup exists, it copies directly from the repo.

### If nothing works

If the repo is also broken and no backup exists:

1. Re-install SweetClaude from the plugin marketplace
2. Or: check out a known-good git tag and copy hooks manually:
   `git checkout v3.68.6 -- hooks/ && cp hooks/*.sh ~/.claude/plugins/cache/.../hooks/`

## What to Read Next

- [How It Works](how-it-works.md) — hook architecture and the Write|Edit matcher
- [Skills Reference](skills-reference.md) — full list of available skills including `/sweetclaude:hook-repair`
- [TDD](tdd.md) — the testing discipline that keeps hooks correct before they are synced
