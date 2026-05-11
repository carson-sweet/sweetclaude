# SweetClaude v4 Migration Guide

**Version:** 4.0.0
**Date:** 2026-05-10

---

## Welcome to v4

SweetClaude v4 is a significant step forward in how your product backlog is organized and stored. The short version: your work items now live where they belong — alongside your code, in your project's `docs/` directory — instead of buried inside SweetClaude's internal state folder.

### What's new and why it matters

**Backlog lives in your repo, not inside the framework.** In v3, stories were stored under `.sweetclaude/product/backlog/` — a framework-internal location that most projects kept out of git. In v4, the backlog moves to `docs/product/backlog/`, which is a normal project directory that you control. If you want it tracked in git, track it. If you want it gitignored, gitignore it. SweetClaude no longer makes that decision for you.

**IDs tell you what something is.** The old `BL-NNN` prefix told you nothing. v4 uses per-type IDs: `STORY-NNN`, `BUG-NNN`, `DEBT-NNN`, `CHORE-NNN`. At a glance, you know what you're looking at — in file names, commit messages, and skill output.

**Closed work is archived, not deleted.** Done and abandoned items move to a `done/` subdirectory. They're out of the way but still there when you need them. No data is ever lost on close.

**A single INDEX.md is the source of truth.** `docs/product/backlog/INDEX.md` holds the counter state and a live table of all active work. Every skill reads from and writes to this file atomically — no more hunting across directories to figure out what's in the backlog.

**Health checks catch problems before they cause damage.** v4 includes built-in lint rules that detect counter drift, misplaced files, and stale v3 artifacts. `/sweetclaude:fix-sweetclaude` can repair most findings automatically.

### Migration is safe and reversible

Before touching a single file, `/sweetclaude:migrate` creates a full timestamped backup of your `.sweetclaude/` directory. If anything goes wrong, one command restores you to exactly where you started. The original `BL-NNN.md` files are never deleted during migration — they stay in place until you explicitly choose to remove them.

---

## What's changing in v4

- Stories move from `.sweetclaude/product/backlog/BL-NNN.md` to `docs/product/backlog/<type>s/<TYPE>-NNN-<slug>.md`.
- IDs are now per-type: `STORY-NNN`, `BUG-NNN`, `DEBT-NNN`, `CHORE-NNN`. The legacy `BL-NNN` prefix is retired.
- Active work lives under `<type>s/`; closed work moves to `<type>s/done/`.
- A new `INDEX.md` at `docs/product/backlog/INDEX.md` is the source of truth for counters and the visible table of unscheduled work.

---

## What you need to do

Run `/sweetclaude:migrate` from any v3 project the first time you open it after updating to v4. The bootstrap hard stop will block any v4 skill until migration runs.

---

## What migration does

- Creates a timestamped safety backup at `.sweetclaude/state/backups/pre-v4-<date>-<sha>.tar.gz`.
- Scans every `BL-NNN.md` file, validates it, and aborts before any write if validation fails. If validation fails, offers to run `/sweetclaude:migrate-diagnose`.
- Asks whether to migrate completed (done / cancelled / abandoned) stories.
- Shows a preview of every planned write before any file is created.
- Copies each story to its new location with its new ID; the original `BL-NNN.md` is left in place.
- Builds `INDEX.md` (counters + active tables) and `MIGRATION-MAP.md` (v3 ID → v4 ID lookup).
- Verifies every written file (frontmatter parses, fields match, body preserved) before declaring success.
- On any failure, restores `.sweetclaude/` from the backup and removes anything written under `docs/product/backlog/`.
- On success, offers to delete the original `.sweetclaude/product/backlog/` (the backup remains).

---

## If something goes wrong

- During migration, on any failure: the skill offers three options — `Work through it with me` (runs `/sweetclaude:migrate-diagnose`), `Reset framework state` (clears `.sweetclaude/` only; leaves `/docs/` untouched), `Wait` (exits with the hard stop still in effect).
- Manual rollback at any time: `rm -rf .sweetclaude && tar -xzf .sweetclaude/state/backups/pre-v4-<date>-<sha>.tar.gz` (substitute the actual archive filename from the listing).

---

## FAQ

**Do I have to migrate?**
Yes. v4 cannot run against v3 storage; the bootstrap hard stop blocks every v4 skill in a v3 project.

**What happens to my git history?**
Migration does not rewrite history. New files are created at new paths; the original `BL-NNN.md` files remain until you accept the post-migration delete offer. Whether the new `docs/product/` files are tracked depends on your project's `.gitignore`.

**Can I roll back?**
Yes, via the backup archive. The exact command is in the "If something goes wrong" section above.
