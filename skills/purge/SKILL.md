---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:purge
user-invocable: true
description: Delete all SweetClaude artifacts from the current project. Shows all files, warns, requires the user to type "I understand", then deletes .sweetclaude/.
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Purge SweetClaude

Remove all SweetClaude artifacts from this project. This cannot be undone.

---

## Step 1: Check for artifacts

```bash
ls .sweetclaude/ 2>/dev/null
```

If `.sweetclaude/` does not exist:
> "No SweetClaude artifacts found in this project."

Stop.

---

## Step 2: Recommend a branch

```bash
git branch --show-current
```

Tell the user:

> "Before deleting, create a backup branch so your SweetClaude artifacts are preserved in git history:
>
> ```
> git checkout -b sweetclaude-backup-$(date +%Y-%m-%d)
> ```
>
> Have you created a branch? (or say 'skip' to proceed without one)"

Wait for the user's response. If they want help creating the branch, run the command for them. Accept any affirmative or "skip" before continuing.

---

## Step 3: Show all files to be deleted

```bash
find .sweetclaude -type f | sort
find .sweetclaude -type d | sort
```

Present:

> "The following will be permanently deleted:
>
> ```
> {full file and directory list}
> ```
>
> **{N} files** across **{M} directories** inside `.sweetclaude/`."

---

## Step 4: Require typed confirmation

> "Type **I understand** to confirm deletion, or anything else to cancel."

Read the user's next message exactly.

- If it is `I understand` (case-insensitive) → proceed to Step 5.
- Anything else →
  > "Purge cancelled. No files were deleted."
  Stop.

---

## Step 5: Delete

```bash
rm -rf .sweetclaude/
```

Verify:

```bash
[ -d .sweetclaude ] && echo "ERROR: directory still exists" || echo "Deleted."
```

Report:

> "Done. {N} files deleted.
>
> Run `/sweetclaude:setup` to reinitialize this project."
