# Changelog

All notable changes to SweetClaude are documented here.

---

## [4.0.0] — 2026-05-10

### Breaking

Story storage moved from `.sweetclaude/product/backlog/BL-NNN.md` to `docs/product/backlog/<type>s/<TYPE>-NNN-<slug>.md`. ID scheme is now per-type (`STORY-NNN`, `BUG-NNN`, `DEBT-NNN`, `CHORE-NNN`). The legacy `BL-NNN` scheme is retired. v4 cannot run against v3 storage — the bootstrap hard stop blocks every v4 skill in a v3 project until migration completes.

### Migration

`/sweetclaude:migrate` runs once per project; a safety backup is created automatically. See [docs/user-guide/v4-migration.md](docs/user-guide/v4-migration.md) for the full migration walkthrough.

### New features

- Per-type subdirectories (`stories/`, `bugs/`, `debt/`, `chores/`) with `done/` archive subdirectory.
- `MIGRATION-MAP.md` for v3↔v4 ID lookups at `docs/product/backlog/MIGRATION-MAP.md`.
- `_health` lint rules for v4 storage invariants: counter drift detection, done/status placement invariant, v3 file detection.
- `fix-sweetclaude` auto-repair recipes for lint findings.

### Removed

The EP-999 backlog-holding-epic concept is replaced by the `docs/product/backlog/INDEX.md` source of truth for counters and the visible table of unscheduled work.
