# SweetClaude v4 Migration Guide

**Version:** 4.0.0
**Date:** 2026-05-10

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
