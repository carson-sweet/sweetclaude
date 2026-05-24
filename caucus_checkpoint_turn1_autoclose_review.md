# Caucus Checkpoint — Auto-Close Implementation Review

**Topic:** Review of milestone auto-close/auto-reopen implementation in status.py  
**Date:** 2026-05-24  
**Scope:** Correctness, edge cases, race conditions  
**Status:** Complete (1 turn)

## Position Tally
- 3/3 confirm transition logic and propagation chain correct
- 2/3 flag missing unlink rollback in _reopen_file (actionable fix)
- 1/3 flags mixed-terminal rollup semantics (document, not fix)
- 1/3 flags concurrent modification race (self-healing, document)

## Actionable Findings
1. **_reopen_file missing rollback** — if path.unlink() fails after dest write, two copies exist. Add rollback matching set_terminal lines 472-479.
2. **Mixed-terminal rollup** — derived_status returns "done" when all children terminal, even if some are "declined". Design choice, not bug. Document.
3. **Concurrency assumption** — concurrent child changes can leave milestone temporarily inconsistent. Self-healing on next operation. Document if system ever becomes multi-user.
