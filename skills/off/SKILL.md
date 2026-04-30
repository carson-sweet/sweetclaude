---
name: sweetclaude:off
description: Deactivate SweetClaude for the current project. Preserves all artifacts. Run sweetclaude:on to reactivate.
---

# Deactivate SweetClaude

Suspend SweetClaude for this project without deleting anything. All state, decisions, and artifacts are preserved.

---

## Step 1: Check project state

If `.sweetclaude/` does not exist:
> "SweetClaude is not set up for this project. Run `/sweetclaude:on` to initialize it."
Stop.

If `.sweetclaude/disabled` already exists:
> "SweetClaude is already inactive for this project. Run `/sweetclaude:on` to reactivate."
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
> Run `/sweetclaude:on` to reactivate."
