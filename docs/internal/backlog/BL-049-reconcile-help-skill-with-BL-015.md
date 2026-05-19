# BL-049: Reconcile sweetclaude:help with BL-015 deliverable

**Priority:** P2
**Depends on:** BL-015 (lightweight mode artifact accumulation)
**Created:** 2026-05-06

## Summary

The `sweetclaude:help` skill's "What actually changes at each level" section (Operating Modes → Option 2b) currently describes lightweight mode as it will behave once BL-015 ships — quietly accumulating thin artifacts in the background. When BL-015 is complete, this help content should be reviewed and updated to match the actual implementation details (artifact names, opt-in vs. automatic behavior, where they live, how they're presented to the user).

## What to check on completion of BL-015

- Does the thin artifact behavior match what's described in the help text?
- Are the artifact names (`sweetclaude.yaml`, mini brief, architecture sketch, decision log entries) accurate?
- Is the behavior automatic or opt-in? Update help text to match.
- Does the "uplevel" transition work the way the help text describes?
- Update any related help sub-options (Project Phases → Project structure and deliverables) if the `.sweetclaude/` directory structure changes.

## File to update

`/skills/help/SKILL.md` — Option 2b section ("What actually changes at each level"), and potentially Option 1b ("Project structure and deliverables").
