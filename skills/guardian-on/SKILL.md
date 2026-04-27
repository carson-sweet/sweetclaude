---
name: guardian-on
description: Enable the Protocol Guardian — enforces skill invocations, TDD discipline, and artifact saves for the current session
---

# Protocol Guardian — Enable

Activates enforcement for the three most common SweetClaude protocol violations:
- **Skill skipping** (A) — obligation task chain enforces required skill invocations
- **Artifact skipping** (C) — hook warns when committing without required phase artifacts
- **TDD bypass** (D) — hook blocks source file writes until test files exist

Guardian is session-scoped. It does not persist across sessions or commits.

## Steps

**0. Ensure state directory exists:**
Run:
```bash
mkdir -p .sweetclaude/state
```

**1. Create the guardian flag:**
Run:
```bash
touch .sweetclaude/state/guardian-enabled
```

**2. Prevent the flag from being committed:**
Add `.sweetclaude/state/guardian-enabled` to the project root `.gitignore`:
```bash
grep -qxF ".sweetclaude/state/guardian-enabled" .gitignore 2>/dev/null || echo ".sweetclaude/state/guardian-enabled" >> .gitignore
```


**3. Initialize session state:**
Run this command to write the session state file:
```bash
cat > .sweetclaude/state/session-guardian.json << EOF
{
  "enabled": true,
  "session_start": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "skills_invoked": [],
  "test_files_written": [],
  "artifacts_created": [],
  "tdd_status": "pending"
}
EOF
```

`tdd_status` starts as `"pending"` (TDD not yet started). It transitions to `"writing_tests"` → `"red"` → `"implementing"` → `"green"` as work progresses in the IMPLEMENT phase.

**4. Create obligation task chain** based on current phase from `.sweetclaude/state/phase.yaml`:

If `.sweetclaude/state/phase.yaml` does not exist or is unreadable, use the Unknown branch below.

*IMPLEMENT phase:*
- Task 1: Invoke `sweetclaude:code-feature` or `sweetclaude:code-issue`
- Task 2: Write failing tests — blocked by Task 1
- Task 3: Verify RED (run tests, confirm failure) — blocked by Task 2
- Task 4: Implement to GREEN — blocked by Task 3
- Task 5: Commit with tests — blocked by Task 4

*DESIGN phase:*
- Task 1: Invoke `sweetclaude:design-architecture` or `sweetclaude:design-tech-spec`
- Task 2: Get design approved — blocked by Task 1
- Task 3: Save artifact to `docs/` — blocked by Task 2

*DEFINE phase:*
- Task 1: Invoke `sweetclaude:product-brief` or `sweetclaude:product-prd`
- Task 2: Complete all required sections — blocked by Task 1
- Task 3: Save artifact to `docs/` — blocked by Task 2

*DISCOVER phase:*
- Task 1: Invoke `sweetclaude:product-discovery`
- Task 2: Define at least one persona — blocked by Task 1
- Task 3: Define scope boundary — blocked by Task 2

*PLAN phase:*
- Task 1: Invoke `sweetclaude:product-user-stories`
- Task 2: Write acceptance criteria for all stories — blocked by Task 1
- Task 3: Generate Gherkin `.feature` files (TDD Level 3) or confirm Level 1/2 — blocked by Task 2

*VERIFY phase:*
- Task 1: Invoke `sweetclaude:code-review`
- Task 2: Resolve all Critical findings — blocked by Task 1
- Task 3: PR template filled and docs updated — blocked by Task 2

*Unknown or no phase:* Create a single task: "Determine current phase and invoke the appropriate skill."

**5. For subagent dispatch:**
When guardian is active and you use `superpowers:subagent-driven-development`, prepend this block to every implementer subagent prompt before dispatching:

```
PROTOCOL REQUIREMENTS (guardian active):
- Write failing tests BEFORE writing source code
- Verify RED before implementing
- Do not commit without all tests GREEN
- Do not modify test files
```

**6. Session responsibilities while guardian is active:**
You must keep `session-guardian.json` updated during the session. Fields `enabled` and `session_start` are set at initialization and do not change. The fields you must actively maintain are:
- Add to `skills_invoked` each time you invoke a skill (the `skill-tracker.sh` hook does this automatically, but you should also update it if the hook misses any)
- Add to `artifacts_created` when you save a design doc, product brief, architecture doc, etc.
- Update `tdd_status` as TDD progresses: `writing_tests` → `red` → `implementing` → `green`
- Mark obligation tasks complete as you finish them

**7. Confirm:**
> "Protocol Guardian active. Enforcing skill invocations, test-first, and artifact saves."
