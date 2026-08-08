---
artifact_type: product-brief
violates: BRIEF-MEASURABLE-CRITERIA
note: "Every success criterion is subjective; none is evaluable post-ship."
---

# Product Brief: sweetclaude:doctor
**ISSUE-177** | v1 | 2026-05-22

---

## 1. Problem Statement

SweetClaude's health and repair surface is scattered across 10 components — 4 skills, 3 hooks, and 3 scripts — each with its own invocation path, its own subset of checks, and its own interaction model. A developer whose hooks are broken has to know that `hook-repair` exists. A developer with counter drift has to know that `_health` runs lint rules. A developer with orphaned files from a version upgrade has to know about `scan-orphans`. Nobody knows all of these exist.

Concrete scenario: a developer updates SweetClaude from 4.0.x to 4.1.0. The update renamed `STORY-NNN` to `ISSUE-NNN` and flattened typed subdirectories. They have 3 orphaned files in `stories/`, counter drift from a manual rename last week, and `sweetclaude.yaml` still says `installed_version: 4.0.0`. No single command surfaces all three problems. `fix-sweetclaude` catches the version field but not the orphans. `_health` catches the counter drift but not the version field. The orphan scan doesn't exist in the update flow yet (added in ISSUE-176 but only for the migrate skill). The developer experiences this as "things are slightly broken in ways I can't diagnose."

## 2. Target Audience

SweetClaude project maintainers: developers who have set up SweetClaude on one or more projects and need the framework environment to stay healthy as the framework evolves. Technical enough to use Claude Code daily, but should not need to know SweetClaude internals to keep things working.

## 3. Core Value Proposition

One command — `/sweetclaude:doctor` — scans everything, reports everything, fixes what's safe, and asks about the rest. The developer never needs to know which of the 10 underlying components to reach for.

## 4. Feature Set

### 4a. Single-pass diagnostic scan

Doctor runs all checks in one pass and collects findings into a unified report. No 14-step sequential walkthrough. The scan covers:

| Category | What it checks |
|---|---|
| State file integrity | YAML parse errors, missing state files, schema version currency |
| Hook health | Syntax validation (`bash -n`), manifest presence, required hooks exist, stale/reclassified entries in settings.json, rules files present |
| Storage lint | Counter drift, done/status mismatch, cross-location duplicate IDs, v3 files present, epic missing criteria, product_base divergence |
| Migration currency | Schema drift (state file versions vs registry), taxonomy drift (old prefixes), orphaned files (typed subdirs, scratch, stray) |
| Config compatibility | CLAUDE.md/settings.json/rules conflicts with SweetClaude (FATAL/WARNING/INFO severity) |
| File diagnostics | Missing frontmatter, parse errors, invalid fields, duplicate IDs in work items |
| Onboarding state | skills.yaml completeness, feature configuration gaps |
| Environment wiring | CLAUDE.md accuracy, session-state validity, plan directory |

### 4b. Severity-grouped report

Findings are grouped by severity, not by source component:

- **Errors** — must fix before SweetClaude functions correctly (broken hooks, FATAL config conflicts, YAML parse failures, broken migration chains)
- **Warnings** — should fix, degrading behavior (counter drift, done/status mismatch, stale version field, taxonomy drift, orphaned files, WARNING config conflicts)
- **Info** — FYI, no action needed (redundant config rules, feature setup gaps, register population)

### 4c. Auto-fix safe findings

Doctor auto-fixes findings that are safe and deterministic without prompting:
- Counter drift → rebuild cache
- Stale `installed_version` field → reconcile with `installed_plugins.json`
- Stale drift markers → remove
- Missing plan directory → create
- Session-state regeneration → run hook

### 4d. Prompt for destructive/ambiguous findings

Doctor prompts for findings that change files, move data, or have multiple valid resolutions:
- Hook restoration (from backup or repo)
- File moves (done/ ↔ active directory)
- Orphan recovery (include in migration, show each, skip)
- Schema/taxonomy migration (migrate now, skip, purge)
- Config conflict resolution (adopt SweetClaude's rule, keep existing, keep both)
- YAML repair (fix, show file, restore from archive)

### 4e. Bootstrap prompt (weekly)

- Track `last_doctor_run` timestamp in `sweetclaude.yaml`
- At session start, if >7 days since last run: "It's been a while since your last checkup. Want me to run a quick one?"
- Skip silently if recent
- Always skippable, never blocking
- Integrated into the existing health-check hook cadence

## 5. User Experience

### Invocation

```
/sweetclaude:doctor
```

User-invocable. Also callable by other skills (update, bootstrap) when they detect problems.

### Interaction model

1. **Scan phase:** all checks run silently. Progress indicator: "Scanning... (state files, hooks, storage, migrations, config)"
2. **Report phase:** two-tier grouped findings displayed. Summary tier by default (user-facing language), detail tier with `--verbose`.
3. **Pre-fix menu:** if any fixes are available, present three options: Explain what I'll do / Show me a dry run / Proceed. User can loop between explain and dry-run before committing.
4. **Safety branch offer:** always offered before any writes. Strong recommendation to create one.
5. **Fix phase:** archive directory created unconditionally. Auto-fixes applied, then prompted fixes presented (batched where possible). Every change backed up and diffed in the archive.
6. **Summary:** "Doctor complete. N errors, N warnings, N info. N auto-fixed, N user-fixed, N skipped. Run details: .sweetclaude/state/doctor-runs/{timestamp}/"

### Report format (summary tier)

```
SweetClaude Doctor
══════════════════

Errors (2):
  ✗ One of your startup hooks has a syntax error and won't run
  ✗ Your Claude settings block a tool SweetClaude needs (Agent)

Warnings (3):
  ⚠ 3 work items may have been lost during a previous update
  ⚠ ISSUE-042 is marked done but isn't in the done folder
  ⚠ 12 files still use the old naming format

Info (1):
  ℹ Your improvement register is empty

6 findings · 5 fixable · 1 info only
```

### Safety model

Every doctor run that modifies files:
- Offers a safety branch (recommended)
- Creates `.sweetclaude/state/doctor-runs/{timestamp}/` with full backup of every modified/deleted file and diffs for every change
- Records all actions in `manifest.json` — what changed, before/after, user's choice for each prompted fix
- Never deletes a file without a backup copy in the archive

## 6. Success Criteria

1. Users will be happy with the result.
2. The experience should feel much better than before.
3. Quality will be high.

## 7. Scope

### In scope
- All checks from the 10 absorbed components
- Unified report with severity grouping
- Auto-fix for safe/deterministic findings
- Prompted action for destructive/ambiguous findings
- Weekly bootstrap prompt
- Backing script with test coverage
- Deprecation path for absorbed skills

### Out of scope
- Project content quality (backlog triage, story quality, strategy)
- RAG corpus integrity (`corpus-reconcile` stays separate)
- Workflow prerequisites (`orchestrator_checks.py`)
- Git history or commit hygiene
- Code quality or test coverage
- Performance optimization or benchmarking
- Multi-project scanning (doctor runs in one project at a time)

## 8. Dependencies

- `scripts/cache.py` — for counter drift check and rebuild
- `scripts/migrations/runner.py` — for schema drift detection
- `scripts/migrate/migrate-v3-to-v4.py scan-orphans` — for orphan scanning
- `scripts/migrate/migrate_taxonomy.py --dry-run` — for taxonomy drift detection
- `hooks/sweetclaude-health-check.sh` — for the bootstrap prompt timing (or doctor replaces the timing logic)

## 9. Risks

| Risk | Mitigation |
|---|---|
| Doctor becomes a monolith that's hard to maintain | Backing script with modular check functions, each independently testable |
| Auto-fix causes data loss | Auto-fix is limited to cache rebuilds, version field writes, marker deletion, directory creation — all reconstructable. Everything that touches user data prompts. |
| Absorbing 10 components creates a long deprecation tail | Deprecate in one release (4.2.0), remove in the next (4.3.0). `fix-sweetclaude` and `hook-repair` become thin wrappers that call doctor. |
| Bootstrap prompt is annoying | Always skippable. 7-day cadence is conservative. User can configure or disable. |

## 10. Assumptions

- The backing script pattern (Python script + thin skill orchestrator) proven by `migrate-v3-to-v4.py` scales to doctor's broader scope.
- Users would rather see one grouped report than walk through 14 sequential steps.
- Auto-fixing counter drift and version fields is universally safe (no user scenario where the stale value is intentional).

## 11. Decisions (closed)

1. **Single file.** `scripts/doctor.py` — split into modules only if it outgrows maintainability.
2. **Update skill delegates later.** Doctor proves out independently first; update's inline checks stay.
3. **Persist findings.** Write `.sweetclaude/state/last-doctor-run.json` (timestamp + findings). Status and big-picture read it.
