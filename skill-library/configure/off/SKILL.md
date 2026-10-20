---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Deactivate SweetClaude for the current project."
---


!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

# Deactivate SweetClaude

Suspend SweetClaude for this project without deleting anything. All state, decisions, and artifacts are preserved.

---

## Step 1: Check project state

If `.sweetclaude/` does not exist:
> "SweetClaude is not set up for this project. Run `/sweetclaude:configure init` to initialize it."
Stop.

If `.sweetclaude/disabled` already exists:
> "SweetClaude is already inactive for this project. Run `/sweetclaude:go` to reactivate."
Stop.

---

## Step 2: Deactivate

```bash
touch .sweetclaude/disabled
```

---

## Step 3: Confirm

> "SweetClaude is now inactive for this project. All artifacts are preserved.
>
> Run `/sweetclaude:go` to reactivate."
