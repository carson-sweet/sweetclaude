# Roadmap Schema — v1

**Date:** 2026-05-15

Defines the YAML frontmatter fields for release and epic files under `docs/product/roadmap/`.

---

## Release (`releases/REL-NNN-slug.md`)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | `REL-NNN` format |
| `type` | string | yes | Always `release` |
| `title` | string | yes | Human-readable release name |
| `status` | string | yes | One of: `planning`, `active`, `released`, `abandoned` |
| `version` | string | yes | Semantic version string (e.g., `4.1`) |
| `created` | date | yes | ISO date |
| `updated` | date | yes | ISO date |

Releases do not maintain an `epics` list. A release's epics are derived by querying all epics where `release: REL-NNN`.

### Status values

- **planning** — epics are being defined and sequenced
- **active** — at least one epic is being worked
- **released** — shipped
- **abandoned** — cancelled

---

## Epic (`epics/EP-NNN-slug.md`)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | `EP-NNN` format |
| `type` | string | yes | Always `epic` |
| `title` | string | yes | Capability area name |
| `status` | string | yes | One of: `new`, `active`, `done`, `paused` |
| `release` | string | no | Parent release ID (`REL-NNN`) |
| `objective` | string | yes | One-sentence success statement |
| `completion_criteria` | list | yes | Ordered list of criteria strings |
| `completion_criteria_done` | list | no | List of integer indexes (0-based) marking done criteria |
| `depends_on` | list | no | List of epic IDs this epic depends on |
| `created` | date | yes | ISO date |
| `updated` | date | yes | ISO date |

Epics do not maintain a `stories` list. An epic's stories are derived by querying all stories where `epic: EP-NNN`, ordered by `epic_sequence`.

### Status values

- **new** — defined but not started
- **active** — currently being worked (only one epic may be active at a time)
- **done** — all completion criteria met
- **paused** — temporarily suspended

### Constraints

- Only one epic may have `status: active` at a time across the entire project.
- Stories within the active epic are worked in `epic_sequence` order.

---

## Story-to-epic linkage

Stories declare their epic membership via two fields in story frontmatter:

| Field | Type | Description |
|---|---|---|
| `epic` | string | Parent epic ID (`EP-NNN`), or null if unassigned |
| `epic_sequence` | integer | Position within the epic's execution order (1-based), or null |

These fields live on the story file — the epic file does not maintain a reverse list. The SQLite cache materializes the relationship for fast queries.
