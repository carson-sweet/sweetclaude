---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Diagnostic scan and repair. Checks 8 categories: state integrity, hooks, storage, migration, config, files, onboarding, environment."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:doctor" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: if pre-loaded state above shows STATE_NOT_FOUND, or neither .sweetclaude/state/sweetclaude.yaml nor .sweetclaude/state/phase.yaml exists, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Doctor

Diagnostic scan and repair for your SweetClaude project. Checks 8 categories, offers fixes, and keeps a backup of everything it touches.

Thin orchestrator — all scanning and file mutation happens in `scripts/doctor.py`. This skill owns rendering, menus, prompted fixes, and user interaction. All file writes go through the script's `execute_recipe` pipeline to guarantee backup and diff recording.

---

## Step 1: Scan

```bash
python3 scripts/doctor.py scan --project-dir . 2>/dev/null
```

Parse the JSON output. Handle these cases:

**Not configured:** If the output contains `"error": "not-configured"`, print:
> SweetClaude is not configured for this project.

Stop. Do not continue to Step 2.

**Parse failure:** If the output is not valid JSON or the command exits non-zero, print:
> Doctor scan failed. Run `python3 scripts/doctor.py scan --project-dir .` manually to see the error.

Stop.

**Success:** Store the parsed result. Extract `findings`, `skipped_categories`, `suppressions_resolved`, and `project_state_summary`. Count findings by severity (error/warning/info) for the summary line in Step 9.

---

## Step 2: Render report

**Zero findings:** If `findings` is empty:

Check if `.sweetclaude/state/last-doctor-run.json` exists.
- First run (file missing): print "This is your first checkup — doctor scans your project for common issues and offers to fix them." then "All clear."
- Subsequent run: print "All clear."

Skip to Step 9 (persist the clean run).

**Findings present:** Render the report.

### Summary tier (default)

Group findings by severity. For each group, print a header with icon and the findings:

```
### ❌ Errors (N)
- {summary}
- {summary}

### ⚠️ Warnings (N)
- {summary}

### ℹ️ Info (N)
- {summary}
```

Use the `summary` field from each finding (plain English, no paths or codes).

### Detail tier (--verbose)

If the user invoked doctor with `--verbose` or asked for details, render the detail tier instead:

```
### ❌ Errors (N)
- {detail}
  Files: {file_paths joined by ", "}
  Fix: {fix_type}

### ⚠️ Warnings (N)
- {detail}
  Files: {file_paths joined by ", "}
  Fix: {fix_type}
```

### Skipped categories

If `skipped_categories` is non-empty:
> Skipped {N} check categories due to missing dependencies:
> - {category}: {reason}

### Resolved suppressions

If `suppressions_resolved` is non-empty, list each one:
> Previously suppressed findings resolved:
> - {finding_id_1}
> - {finding_id_2}

---

## Step 3: Pre-fix menu

If no findings have `fix_type` of `auto` or `prompted`, skip to Step 8.

Check for a stored menu default. Read `.sweetclaude/state/last-doctor-run.json` and check `menu_preference`. If the user passed `--interactive`, ignore stored preference.

If a stored default of `proceed` exists and `--interactive` was not passed, skip the menu — print "Using stored preference: proceed" and go to Step 4.

Otherwise, present the menu via AskUserQuestion:

Options:
1. **Explain what I'll do** — "Show a numbered list describing each planned change"
2. **Show me a dry run** — "Simulate the fixes and show before/after diffs without changing anything"
3. **Proceed** — "Apply fixes (you'll be asked about each prompted fix)"
4. **No fixes needed** — "Skip all fixes and just record the scan results"

### Explain

If the user picks Explain:

Number each finding that has a fix (auto or prompted). For each:
> {N}. {summary} → {fix_type} fix

After the list, the user can ask about a specific number for detail (show `detail` field and `file_paths`). Then re-present the Step 3 menu.

### Dry run

If the user picks dry run:

```bash
echo '{scan_findings_json}' | python3 scripts/doctor.py dry-run --project-dir .
```

Parse the `simulations` array. For each:
- If it has `before` and `after`: show a before/after comparison
- If it has `note`: show the note
- If it has `description`: show the description

After rendering, re-present the Step 3 menu.

### Proceed

Continue to Step 4.

### No fixes needed

Skip to Step 8 (suppression offer). No safety branch, no archive, no fixes.

### Remember-last-choice

Track consecutive identical menu choices. After this run completes, the choice is saved via the `--menu-preference` arg to `persist`.

If the user has now picked the same option 3 consecutive runs (check previous `last-doctor-run.json` files), offer via AskUserQuestion:
> "You've chosen {choice} the last 3 times — want me to skip this menu from now on? (You can always override with `--interactive`.)"

Options: Yes, skip the menu / No, keep asking

If yes, the persist step will store `menu_default` in addition to `menu_preference`.

---

## Step 4: Safety branch offer

**Always present this step.** Never skip it due to stored preferences.

First check prerequisites:

```bash
git rev-parse --is-inside-work-tree 2>/dev/null
```

If not a git repo: print "Not a git repository — skipping safety branch." Continue to Step 5.

```bash
git status --porcelain 2>/dev/null
```

If dirty working tree: warn "You have uncommitted changes — the safety branch will include them."

Present via AskUserQuestion:
- **Yes, create a safety branch (Recommended)** — "Create doctor/run-{timestamp} from current HEAD as a restore point"
- **No, proceed on current branch** — "Make changes directly on the current branch"

If yes:

```bash
git branch doctor/run-{timestamp}
```

This creates the branch as a restore point WITHOUT switching to it. If the branch name already exists, append `-2`, `-3`, etc. Record the branch name — pass it to `persist` via `--safety-branch`.

If no: record that the user declined (pass `--safety-branch ""` to persist, or omit the arg).

---

## Step 5: Create archive and run auto-fixes

```bash
python3 scripts/doctor.py create-archive --project-dir .
```

Store the `archive_dir` from the response.

Then pipe the scan findings to auto-fix:

```bash
echo '{scan_findings_json}' | python3 scripts/doctor.py auto-fix --project-dir . --archive-dir {archive_dir}
```

Parse the result. Report:

**Successes:**
> Fixed {N} items automatically:
> - {description}

**Failures:**
> Failed to fix {N} items:
> - {description}: {error}

If no auto-fixable findings existed, skip this output.

### Post-fix rescan

If `post_fix_categories` is non-empty:

```bash
echo '{scan_findings_json}' | python3 scripts/doctor.py post-fix-rescan --project-dir . --categories {comma_separated_categories}
```

If the rescan returns new findings:
> ### Post-fix findings
> A fix revealed a previously hidden issue:
> - {summary}

### Refresh prompted findings

After auto-fix and post-fix rescan, filter the prompted-fix findings list: drop any finding whose ID no longer appears in a fresh scan of its category (it was resolved by an auto-fix). Use the post-fix rescan results for this — if a prompted finding's ID is absent from the rescan of its category, remove it from the prompted list.

---

## Step 6: Prompted fixes

Group prompted-fix findings by category. Process each category:

### Batch presentation

If a category has multiple findings of the same `fix_recipe.type`, batch them. Present via AskUserQuestion:

> {N} {description of batch} — for example: "3 files need moving to done/"

Options:
- **Fix all** — "Apply the fix to all {N} items"
- **Review each** — "Show me each item and let me decide individually"
- **Skip all** — "Skip all {N} items"

### Individual review

For each finding (or if user chose "Review each"):

Present the finding details and offer via AskUserQuestion:
- **Fix it** — description of what the fix does
- **Skip** — "Leave it as-is for now"
- **Suppress** — "Don't report this finding again"

**On Fix:**

Execute the fix through the script's backup pipeline. For fix types that have a concrete recipe action (not just `"prompt"`):

```bash
echo '[{single_finding_json}]' | python3 scripts/doctor.py auto-fix --project-dir . --archive-dir {archive_dir} --include-prompted
```

For fix types that require further user input or skill delegation:

- `config_conflict`: Present the options from `fix_recipe.options` (adopt / keep / keep both) via AskUserQuestion. Apply the chosen resolution, then record:
  ```bash
  echo '{"finding_id": "...", "action": "prompted-fix", "choice": "...", "description": "...", "timestamp": "..."}' | python3 scripts/doctor.py record-action --archive-dir {archive_dir}
  ```

- `hook_restore`: Present source options (backup vs repo) via AskUserQuestion. Restore the file, record the action.

- `migration`: Delegate to the appropriate skill or script per Step 7. Record the result.

- `yaml_repair`: Present options (auto-fix syntax, show file for manual edit, restore from archive) via AskUserQuestion. Apply, record.

- `bootstrap`: Run the bootstrap script via the auto-fix pipeline with `--include-prompted`, record.

**On Skip:**
```bash
echo '{"finding_id": "...", "action": "skip", "timestamp": "..."}' | python3 scripts/doctor.py record-action --archive-dir {archive_dir}
```

**On Suppress:**

Ask for a reason string. Write the suppression:

```python
# Add to doctor-suppressions.json
{"finding_id": "...", "suppressed_at": "{ISO timestamp}", "reason": "{user's reason}"}
```

Record the action:
```bash
echo '{"finding_id": "...", "action": "suppress", "reason": "...", "timestamp": "..."}' | python3 scripts/doctor.py record-action --archive-dir {archive_dir}
```

---

## Step 7: Migration and restore delegation

When a prompted fix involves migration or restoration:

- **Schema migration** (`fix_recipe.script` = "runner.py"): Invoke `sweetclaude:_migrate` skill. Record result via `record-action`.

- **Taxonomy migration** (`fix_recipe.script` = "migrate_taxonomy.py"): Run the script directly. Record result.

- **v3-to-v4 migration** (`fix_recipe.script` = "migrate-v3-to-v4.py"): Run the script. Record result.

- **Purge/re-onboard**: Invoke `sweetclaude:purge`. Record result.

---

## Step 8: Suppression offer

After all fixes are processed (or if there were no fixes, or the user chose "No fixes needed"), if there are remaining unfixed findings:

> Want to suppress any of the remaining findings so they don't show up next time?

Present via AskUserQuestion:
- **Yes, let me choose** — "Review remaining findings and choose which to suppress"
- **No** — "Keep reporting everything"

If yes: present each remaining finding with suppress/keep options (same as Step 6 suppress flow).

For findings where `previously_suppressed` is true, note: "This finding was previously suppressed, resolved, and has now re-emerged."

---

## Step 9: Persist and summary

If no archive was created (zero-findings or "No fixes needed" path), create one for the persist record:

```bash
python3 scripts/doctor.py create-archive --project-dir .
```

Pipe the original scan findings to persist:

```bash
echo '{scan_findings_json}' | python3 scripts/doctor.py persist --project-dir . --archive-dir {archive_dir} --menu-preference {choice_from_step_3} --safety-branch {branch_name_or_empty}
```

Count severities from the findings array: errors = findings where severity="error", warnings = severity="warning", info = severity="info". Get fix counts from the archive actions (auto_fixed, user_fixed, skipped).

Render the summary line:

> **{errors} errors, {warnings} warnings, {info} info. {auto_fixed} auto-fixed, {user_fixed} user-fixed, {skipped} skipped.**

Report the archive location (unconditional — always show if an archive exists):
> Run details saved to `.sweetclaude/state/doctor-runs/{timestamp}/`

Prune old archives:

```bash
python3 scripts/doctor.py prune-archives --project-dir .
```

Silent — do not report pruning results to the user.

---

## Rules

- **Read-only scan.** The scan phase (Step 1) never writes. All writes happen in Steps 5-7.
- **All mutations go through the script.** Even prompted fixes use `auto-fix --include-prompted` or `record-action`. The skill never writes files directly via Bash — this guarantees backup and diff recording per FR-2.4.
- **Archive is unconditional.** Every run creates an archive, regardless of whether changes were made.
- **Safety branch is always offered.** Never skip it due to stored preferences or menu defaults. Never subject it to remember-last-choice. Uses `git branch` (not `checkout -b`) to avoid switching context.
- **Skip is always available.** Doctor never blocks on a single finding. The user can skip any prompted fix, skip all fixes, or exit the menu entirely.
- **No deletions without backup.** Enforced by `scripts/doctor.py`'s `execute_recipe`, not by this skill.
- **Prompted fixes are batched where possible.** Multiple findings of the same type in the same category are presented as a group.
- **Summary tier is default.** Use plain English summaries with severity icons unless the user asks for `--verbose` detail.
- **Use AskUserQuestion for all bounded decisions.** Pre-fix menu, safety branch, prompted fixes, suppression — all via AskUserQuestion, never text-imitation menus.
