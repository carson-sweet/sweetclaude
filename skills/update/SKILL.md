---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Update SweetClaude to the latest version from GitHub."
---

# Update SweetClaude

Fetch the latest SweetClaude and sync it to all installed locations.

**This skill can be run from any project directory.**

All logic lives in `scripts/update.py`. This skill calls its subcommands in
sequence, reads their JSON output, and presents results to the user.

---

## Recovery fallback

If `${CLAUDE_PLUGIN_ROOT}/scripts/update.py` does not exist when any step
below is attempted, stop immediately and tell the user:

```
Update script not found. This can happen after a partial update.

To recover, run this Claude Code command:
/plugin update sweetclaude@sweetclaude-beta

Then restart Claude Code and run /sweetclaude:update again.
```

Do not attempt to continue the update without the script.

---

## Contract

<!-- The four sentences below are grep-anchored by recover_project.py's _update_skill_contract_check and tests/test_recovery_skill.py. If you reword them, update the check's required list and the tests in the same change. -->

Update never mutates project work-item state.
Update does not run project-state migrations inline; route project repair to `/sweetclaude:doctor`.
Do not present a migration prompt from update.
Do not write `doctor-prompt-pending.json` from update.

---

## Step 1: Preflight

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update.py" preflight \
  --project-dir . \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --from-update
```

Read the JSON output. Required fields for subsequent steps:

- `plugin_key` → `PLUGIN_KEY`
- `install_path` → `INSTALL_PATH`
- `version` → `INSTALLED_VERSION`
- `git_commit_sha` → `INSTALLED_SHA`
- `channel` → `CHANNEL`
- `expected_ref` → `EXPECTED_REF`
- `runner` → `RUNNER`
- `legacy_marketplace` → `LEGACY_MARKETPLACE`

If `ok` is not `true`, stop: "SweetClaude cannot find a repairable plugin entry."

If `stale_beta_install` is `true`, print:

```
SweetClaude beta plugin update required.
──────────────────────────────────────
Installed plugin: {plugin_key}
Installed version: {version}
Minimum safe beta: {minimum_safe_beta_version}

Run this Claude Code command:
{plugin_update_command}

Then restart Claude Code and run:
/sweetclaude:update

Stopping here because this installed beta is old enough to have unsafe
update/recovery behavior. No project files were changed.
```

Stop. Do not invoke any other skill.

Present current state:

```
SweetClaude v{INSTALLED_VERSION}
════════════════════════════════

Installed: {INSTALL_PATH}
Commit:    {INSTALLED_SHA (first 7 chars)}
Channel:   {CHANNEL} ({EXPECTED_REF})
Source:    https://github.com/carson-sweet/sweetclaude
```

If `LEGACY_MARKETPLACE` is true, add:
`Legacy install metadata detected; this update will repair the recorded version, commit, and install path.`

---

## Step 2: Check for updates

Read the `install_path` from the preflight output. Extract `repository` from
`{INSTALL_PATH}/.claude-plugin/plugin.json` (fallback: `https://github.com/carson-sweet/sweetclaude`).

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update.py" check \
  --ref "{EXPECTED_REF}" \
  --installed-sha "{INSTALLED_SHA}" \
  --repo "{repository}" \
  --install-path "{INSTALL_PATH}" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}"
```

Read the JSON output. Save `source_dir`, `tmpdir`, `effective_sha`, `new_version`,
`new_skills` for later steps.

If `ok` is false:
- If `auth_error` is true: "The SweetClaude repo requires authentication. Run `! gh auth login` to authenticate with GitHub, then try again."
- Otherwise: report the error from `detail`.
- Stop.

**Beta → stable migration check (ISSUE-244).** If `CHANNEL` is `beta`, before
reporting up-to-date, run the advisory nudge:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update.py" channel-migration \
  --channel "$CHANNEL" --installed-version "$INSTALLED_VERSION"
```

If the JSON `migrate` is `true`, print the `notice` verbatim before anything
else — the beta channel is being retired and the user needs the one-time
switch to the stable channel. This is advisory: never block or fail the update
on it. (The helper is `beta_stable_migration_notice` in `scripts/update.py`.)

If `up_to_date` is true: "Already up to date." **Jump to Step 5** — even when
framework is current, the project may have pending migrations.

Otherwise, present what changed:

```
Update available: {INSTALLED_SHA short} → {effective_sha short}
═══════════════════════════════════════════════════════════════

Commits:
  {changelog}

Changes:
  {diff_summary entries, e.g. "Skills: 3, Hooks: 1, Scripts: 2"}
```

Wait for user confirmation before proceeding.

---

## Step 2b: Safety check for removed skills

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update.py" safety-check \
  --source "{source_dir}" \
  --install-path "{INSTALL_PATH}" \
  --project-dir .
```

If `has_live_artifacts` is true, present the affected list and use AskUserQuestion:

- **Proceed anyway** — I understand the content will be orphaned
- **Cancel** — I'll migrate the content before updating
- **Skip removing these skills** — sync everything else (not implemented — cancel instead)

If user cancels, run cleanup and stop.

If no live artifacts: continue silently.

---

## Step 2c: Major version gate

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update.py" major-gate \
  --installed-version "{INSTALLED_VERSION}" \
  --incoming-version "{new_version}"
```

If `gate_applies` is true, present via AskUserQuestion:

> **SweetClaude v4 is available — this is a major release.**
>
> All work items use the ISSUE-NNN prefix and are stored in `.sweetclaude/product/backlog/`. Each project migrates independently the first time you open it after updating.
>
> Migration creates a safety backup and can be rolled back.

- **Yes, update**
- **Not now**

On "Not now": write `framework.update.declined: true` to `.sweetclaude/state/sweetclaude.yaml` (if it exists). Run cleanup. Stop.

If gate does not apply: continue.

---

## Step 3: Sync

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update.py" sync \
  --source "{source_dir}" \
  --install-path "{INSTALL_PATH}" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}"
```

Read the JSON output. Save `version_dir`, `sync_target`, `hook_cleaned`.

If `ok` is false, report errors. Run cleanup. Stop.

If `verify_errors` is non-empty, report them as warnings but continue.

If `registry_ok` is false, warn: "skills-registry.yaml not found after sync."

---

## Step 4: Update metadata

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update.py" metadata \
  --plugin-key "{PLUGIN_KEY}" \
  --install-path "{sync_target}" \
  --version "{new_version}" \
  --sha "{effective_sha}" \
  --project-dir .
```

---

## Step 5: Project checks

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update.py" project-check \
  --project-dir . \
  --runner "{RUNNER}"
```

Read the JSON output.

**If `drift_count` > 0:** print partial-update report and stop:

```
SweetClaude update PARTIAL.
═══════════════════════════

✓ Version:    {INSTALLED_VERSION} → {new_version}  (framework synced)
✗ Project:    {drift_count} state file(s) need migration review

No project files were changed by update.
Run /sweetclaude:doctor — it auto-fixes state schema drift through the
migration runner (backed up, reversible).

Drift details:
  {drift_lines}
```

Run cleanup. Stop.

**If `orphan_count` > 0:** report non-blocking:

```
Found {orphan_count} orphaned work item file(s).
No files were changed. Run /sweetclaude:doctor to review and resolve them
(resolution is archived and reversible).
```

**If `old_taxonomy_count` > 0:** report non-blocking:

```
Found {old_taxonomy_count} work item(s) using legacy taxonomy prefixes.
No files were changed. Run sweetclaude:doctor for read-only diagnostics.
```

**If `bold_format_count` > 0:** report non-blocking:

```
Found {bold_format_count} artifact file(s) using Bold Key-Value format.
Run sweetclaude:doctor --check format_consistency --auto-fix to convert.
```

---

## Step 6: Cleanup and report

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update.py" cleanup --tmpdir "{tmpdir}"
```

Print the success report:

```
SweetClaude updated.
═══════════════════

✓ Version:    {INSTALLED_VERSION} → {new_version}
✓ Commit:     {INSTALLED_SHA short} → {effective_sha short}
✓ Files:      synced across skills, rules, hooks, config, scripts
{if hook_cleaned > 0: ✓ Hooks:      reconciled {hook_cleaned} stale entries}
✓ Project:    clean

→ Restart Claude Code to use this update — skills are loaded at session start.
```

If `hook_cleaned > 0`, also append:
`→ Restart Claude Code to stop the in-session ${CLAUDE_PLUGIN_ROOT} error from old settings.json entries.`

If `new_skills` is non-empty:

```
New skills added (not available until restart):
  {/sweetclaude:{name} for each}
```

Do not offer to run any skill. The current session does not have the updated set.

---

## Step 7: Surface capabilities

Read [capability-surface.md](capability-surface.md) for the "What's new in this
update" section only. Do not execute its project skill-state migration,
bootstrap, or onboarding sections from update.

---

## Rules

- **Always show the diff preview and wait for confirmation before syncing.**
- **Prefer `gh` over `git` for cloning.** The script handles this automatically.
- **Never ask for tokens or credentials.** If auth fails, tell the user to run `gh auth login`.
- **Always clean up temp directories**, even on failure. Call `cleanup` on any error exit.
- **Do not touch ~/.claude/settings.json.** Hook reconciliation is handled by the sync subcommand.
- **Do not modify ~/CLAUDE.md.**
- **Do not mutate per-project `.sweetclaude/` directories from update except for
  `framework.installed_version` (Step 4) and explicit user decline state in
  the major-version gate.** Framework sync is global; project
  migration/recovery is separate.
- **Argument compatibility contract.** The subcommand argument interface in
  `scripts/update.py` must remain backward-compatible across releases. After
  sync replaces the script mid-update, subsequent steps call the new script
  with arguments dictated by this skill file (which may be from the prior
  version). Adding new optional arguments is safe; removing or renaming
  required arguments is not.
