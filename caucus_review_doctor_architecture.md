# Caucus Review: sweetclaude:doctor Architecture (ISSUE-177)

**Date:** 2026-05-22
**Proctor:** Automated caucus — architecture review against PRD requirements
**Scope:** FR/NFR gap analysis, failure modes, implementation risks, missing details
**Documents reviewed:** `issue-177-doctor-architecture.md`, `issue-177-doctor-prd.md`

---

## Committee

| # | Name | Role | Stance |
|---|---|---|---|
| 1 | Dr. Priya Ramaswamy | Principal Platform Architect, Lattice Infrastructure | Collaborative |
| 2 | Gunnar Eklund | Staff Architect, Breakpoint Security | Adversarial |
| 3 | Luciana Torres | Senior Developer, Meridian DevTools | Collaborative |
| 4 | Dmitri Volkov | Senior Developer, CrashOverride (solo consultancy) | Adversarial |

---

## Verdict: 4/4 Approve with Changes (5 blocking, 7 advisory)

| Panelist | Verdict | Key condition |
|---|---|---|
| Dr. Priya Ramaswamy | Approve with changes | Subcommand table, content-based backup, ProjectState purity |
| Gunnar Eklund | Approve with changes | Content-based backup pipeline, subcommand table |
| Luciana Torres | Approve with changes | Subcommand table, remember-last-choice storage |
| Dmitri Volkov | Approve with changes | Subcommand table, RecipeResult dataclass |

---

## Position Trajectory

| Panelist | Turn 1 | Turn 2 | Turn 3 |
|---|---|---|---|
| Priya | Approve with minor gaps | Core sound, 3 gaps flagged | Approve w/ changes (3 blocking) |
| Gunnar | Wants significant revision | Approve w/ specific changes | Approve w/ changes (2 blocking) |
| Luciana | Approve with practical gaps | Conceded on stdin, full gap list | Approve w/ changes (2 blocking) |
| Dmitri | Wants significant revision | Dropped suppression to advisory | Approve w/ changes (2 blocking) |

---

## Consensus Findings (all 4/4 unless noted)

1. **Architecture is structurally sound.** Boundary between skill and script, check registry, archive system, and data model are well-designed.

2. **Happy path is solid, failure paths were underspecified.** Resolved by Turn 2 convergence on content-based backup + sole mutation path enforcement.

3. **Subcommand surface area grew from 5 to 8** during review. The architecture must document all 8 with stdin/stdout contracts.

4. **Content-based backup is the correct pattern.** Read file into memory once, backup from buffer, modify from buffer, atomic write. Eliminates TOCTOU between backup and modification.

5. **`execute_recipe` is the sole file-mutation entry point.** Required `archive_path` parameter makes it structurally impossible to bypass backup.

6. **Stdin-based data flow between subcommands.** Eliminates temp file orchestration, stale data, and cleanup burden.

7. **Manifest assembly happens once at `persist` time.** Auto-fix results + prompted-fix results (via `record-action` append) assembled into final manifest.

8. **`_original_findings` removed from ProjectState.** Pass as separate parameter to post-fix rescan. ProjectState stays pure (filesystem snapshot only).

9. **FR-8 deprecation wrappers don't need architecture treatment.** (4/4)

10. **`previously_suppressed` field on Finding simplifies skill UX.** (4/4 advisory)

11. **Remember-last-choice stored as `menu_preference` in `last-doctor-run.json`.** (3/4)

---

## Prioritized Recommendations

| # | Recommendation | Support | Blocking? | Architecture section affected |
|---|---|---|---|---|
| 1 | Update subcommand table to 8 subcommands with stdin/stdout contracts | 4/4 | **Yes** | CLI interface |
| 2 | Specify content-based backup pipeline (read once, backup from buffer, modify from buffer, atomic write) | 4/4 | **Yes** | Archive system, Auto-fix pipeline |
| 3 | `RecipeResult` dataclass for `execute_recipe` return type | 4/4 | **Yes** | Auto-fix pipeline |
| 4 | Fix `_original_findings` — pass as separate param to post-fix rescan | 4/4 | **Yes** | Post-fix rescan |
| 5 | FR-2.1 remember-last-choice: `menu_preference` field in `last-doctor-run.json` | 3/4 | **Yes** | New section or Persistence |
| 6 | `skipped_categories` in scan output for graceful degradation visibility | 3/4 | Advisory (strong) | CLI interface, scan output |
| 7 | `previously_suppressed: bool` on Finding dataclass | 4/4 | Advisory | Data model |
| 8 | `run_script` allowlist (cache.py, generate-session-state.sh only) | 3/4 | Advisory | Auto-fix pipeline |
| 9 | FR-2.2 safety branch prerequisites (dirty tree, branch collision, no git) | 3/4 | Advisory | Skill orchestration flow |
| 10 | FR-1.4 early exit JSON contract (`{"error": "not-configured"}`) | 3/4 | Advisory | CLI interface |
| 11 | FR-2.6 idempotency as per-recipe precondition checks | 2/4 | Advisory | Auto-fix pipeline |
| 12 | Test fixture strategy note (ProjectState from fixture directories) | 2/4 | Advisory | New section |

---

## Key Technical Resolutions

### Content-based backup pipeline (Blocking #2)

Replace the current `backup_file(archive_path, file_path)` with:

```python
def execute_recipe(project_dir, recipe, archive_path) -> RecipeResult:
    file_path = resolve_target(project_dir, recipe)
    content = file_path.read_bytes() if file_path.exists() else b""
    before_hash = backup_content(archive_path, file_path, content)
    new_content = apply_transform(content, recipe)
    atomic_write(file_path, new_content)
    after_hash = hash_bytes(new_content)
    write_diff(archive_path, file_path, content, new_content)
    return RecipeResult(before_hash=before_hash, after_hash=after_hash,
                       backup_path=..., success=True)
```

One read, one write, no window for races. If `apply_transform` throws, backup exists and original file is untouched. If `atomic_write` throws, backup exists and file is either original or new (atomic). No partial state possible.

### Updated subcommand table (Blocking #1)

| Subcommand | Input | Output | Side effects |
|---|---|---|---|
| `scan` | `--project-dir` | `{findings, skipped_categories, suppressions_resolved, project_state_summary}` | none (read-only) |
| `create-archive` | `--project-dir` | `{"archive_dir": "..."}` | creates directory |
| `auto-fix` | `--project-dir --archive-dir`, stdin: findings | `{actions, post_fix_categories}` | modifies files, writes backups |
| `post-fix-rescan` | `--project-dir --categories c1,c2`, stdin: original findings | `{findings}` (new only) | none |
| `record-action` | `--archive-dir`, stdin: action JSON | `{"recorded": true}` | appends to pending-actions.jsonl |
| `dry-run` | `--project-dir`, stdin: findings | `{simulations}` | none |
| `persist` | `--project-dir --archive-dir` | `{"path": "..."}` | writes last-doctor-run.json, assembles manifest |
| `prune-archives` | `--project-dir` | `{"pruned": [...]}` | deletes old archive dirs |

### Stdin-based data flow

Findings flow from `scan` stdout → skill captures → pipes to `auto-fix`/`dry-run`/`post-fix-rescan` stdin. No temp files. Skill holds the findings in a bash variable between calls.

---

## Unresolved Disagreements

None. All disputes resolved by Turn 3.

---

## Minority Reports

None. All panelists converged.
