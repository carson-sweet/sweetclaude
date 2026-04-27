# Protocol Guardian — Design Spec
**Version:** 1.0  
**Date:** 2026-04-27  
**Status:** Approved

---

## Problem

Claude (main orchestrating session and dispatched subagents) frequently ignores SweetClaude protocols. The three most common violations:

- **A — Skill skipping:** Jumping to implementation without invoking required skills (e.g., brainstorming, code-feature)
- **C — Artifact skipping:** Not saving required artifacts (design docs, decision logs, improvement register entries)
- **D — TDD bypass:** Writing source code before tests, skipping RED→GREEN discipline

The goal is **prevention**, not retrospective correction. The guardian is **off by default** and must be explicitly enabled.

---

## Architecture

Two coordinated layers:

```
Hooks layer (shell, external)         Guardian skill (reasoning layer)
──────────────────────────────────    ──────────────────────────────────
tdd-prewrite-guardian.sh              sweetclaude:guardian-on
  PreToolUse Write|Edit                 creates flag + obligation chain
  blocks source writes w/o tests
                                      sweetclaude:guardian-off
artifact-guardian.sh                    removes flag
  PreToolUse Bash (git commit)
  warns on missing artifacts/tests    Updated subagent prompts
                                        implementer-prompt.md
skill-tracker.sh                        protocol block injected when
  PostToolUse Skill                       guardian is active
  records skill invocations
```

Bridge: `.sweetclaude/state/session-guardian.json` — written by the guardian skill and `skill-tracker.sh`, read by hooks.

---

## On/Off Mechanism

- **Default:** off
- **Enable:** `/sweetclaude:guardian-on` → creates `.sweetclaude/state/guardian-enabled` flag file
- **Disable:** `/sweetclaude:guardian-off` → removes flag file
- All hooks check for the flag file at the top and exit cleanly if absent — zero overhead when off
- Flag file is gitignored (per-developer preference, not committed)

---

## Frustration Detection

Added to `master` skill and `interaction-model.md` as a standing trigger.

Signals to watch for:
- User says "you skipped X", "you ignored Y", "you're not following the protocol"
- Same correction repeated twice in a session
- Visible exasperation about Claude missing steps

When triggered, offer (do not auto-enable):
> "Looks like I've been skipping protocol steps. Want me to enable the Protocol Guardian? It enforces skill invocations, TDD discipline, and artifact saves."

---

## Hooks

### `tdd-prewrite-guardian.sh` (PreToolUse, Write|Edit) — NEW

Fires when Claude writes or edits any file.

Logic:
1. Check guardian flag — exit cleanly if absent
2. Check if current phase is IMPLEMENT (read `phase.yaml`)
3. Check if target file is a source file (not test, not config, not docs) — detect by path patterns
4. If source file: check `session-guardian.json` for any `test_files_written` entries OR check `git status` for new/modified test files
5. If no test evidence found → **block** with:  
   `"No test files found this session. Write tests first. Update tdd_status to 'writing_tests' in session-guardian.json to begin."`

Complements the existing `test-guardian.sh` (which blocks test file *modifications* during implementation). This hook blocks source file *creation* before tests exist.

### `artifact-guardian.sh` (PreToolUse, Bash — git commit) — NEW

Fires before every Bash tool call.

Logic:
1. Check guardian flag — exit cleanly if absent
2. Check if command matches `git commit` — exit cleanly otherwise
3. Read current phase from `phase.yaml`
4. Check `session-guardian.json` for phase-required artifacts:
   - DESIGN: architecture or tech spec file present?
   - IMPLEMENT: `tdd_status` was `implementing` (not skipped), test files exist?
5. If requirements unmet → **warn** (print, do not block):  
   `"Warning: committing without [missing artifact]. Proceed with caution."`
6. Also warn if staged source files have no corresponding staged test files.

Warn rather than block — commits should never be hard-blocked, just flagged.

### `skill-tracker.sh` (PostToolUse, Skill) — NEW

Fires after every Skill tool invocation.

Logic:
1. Check guardian flag — exit cleanly if absent
2. Read `CLAUDE_TOOL_INPUT` for the skill name
3. Append skill name and timestamp to `session-guardian.json`.`skills_invoked`
4. No blocking, no output — pure bookkeeping

### hooks.json additions

```json
"PreToolUse": [
  { "matcher": "Write|Edit", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/tdd-prewrite-guardian.sh" },
  { "matcher": "Bash",       "command": "${CLAUDE_PLUGIN_ROOT}/hooks/artifact-guardian.sh" }
],
"PostToolUse": [
  { "matcher": "Skill",      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/skill-tracker.sh" }
]
```

---

## Session State File

**Path:** `.sweetclaude/state/session-guardian.json`  
**Written by:** `sweetclaude:guardian-on` (init), `skill-tracker.sh` (skill invocations), Claude (artifacts, tdd_status)  
**Read by:** `tdd-prewrite-guardian.sh`, `artifact-guardian.sh`

```json
{
  "enabled": true,
  "session_start": "2026-04-27T14:32:00Z",
  "skills_invoked": [
    "superpowers:brainstorming",
    "sweetclaude:code-feature"
  ],
  "test_files_written": ["src/auth/auth.test.ts"],
  "artifacts_created": ["docs/superpowers/specs/2026-04-27-auth-design.md"],
  "tdd_status": "implementing"
}
```

Field responsibilities:
- `enabled` — mirrors flag file; Claude reads this to check guardian state
- `skills_invoked` — written by `skill-tracker.sh` automatically
- `test_files_written` — written by `tdd-prewrite-guardian.sh` when it detects a test file being written (Claude does not write this field)
- `artifacts_created` — Claude writes when saving design docs, product briefs, etc.
- `tdd_status` — Claude writes as TDD progresses: `writing_tests` → `red` → `implementing` → `green`

---

## Protocol Guardian Skill

### `sweetclaude:guardian-on`

1. Create `.sweetclaude/state/guardian-enabled` flag file
2. Read `phase.yaml` to determine current phase and work type
3. Create `TaskCreate` obligation chain for the current phase with `addBlockedBy` dependencies

Example chain for IMPLEMENT phase:
```
Task 1: Invoke sweetclaude:code-feature or sweetclaude:code-issue
Task 2: Write failing tests  [blocked by 1]
Task 3: Verify RED           [blocked by 2]
Task 4: Implement to GREEN   [blocked by 3]
Task 5: Commit with tests    [blocked by 4]
```

4. Initialize `session-guardian.json`
5. Print: `"Protocol Guardian active. Enforcing skill invocations, test-first, and artifact saves."`

### `sweetclaude:guardian-off`

1. Remove `.sweetclaude/state/guardian-enabled`
2. Print: `"Protocol Guardian disabled."`
3. Leave `session-guardian.json` in place for reference

---

## Subagent Enforcement

Hooks fire globally (Claude Code level, not per-context), so `tdd-prewrite-guardian.sh` and `artifact-guardian.sh` cover subagents automatically for mechanical violations.

For the reasoning layer, update `subagent-driven-development/implementer-prompt.md` with a conditional protocol block:

```
PROTOCOL REQUIREMENTS (guardian active):
- Write failing tests BEFORE writing source code
- Verify RED before implementing
- Do not commit without all tests GREEN
- Do not modify test files
```

Update `subagent-driven-development` SKILL.md: before dispatching any implementer, check for the guardian flag and if set, prepend the protocol block to the implementer prompt template.

---

## Files Added/Modified

**New files:**
- `hooks/tdd-prewrite-guardian.sh`
- `hooks/artifact-guardian.sh`
- `hooks/skill-tracker.sh`
- `skills/guardian-on/SKILL.md`
- `skills/guardian-off/SKILL.md`

**Modified files:**
- `hooks/hooks.json` — add three new hook entries
- `skills/subagent-driven-development/implementer-prompt.md` — add conditional protocol block
- `skills/subagent-driven-development/SKILL.md` — add guardian flag check before dispatch
- `skills/master/SKILL.md` — add frustration detection trigger
- `rules/sweetclaude/interaction-model.md` — add frustration detection trigger
- `.gitignore` or `.sweetclaude/.gitignore` — add `state/guardian-enabled`

---

## Out of Scope

- Real-time live monitoring of subagent conversation history (not possible — context isolation)
- Auto-enabling the guardian without user consent
- Retrospective audit of past sessions
- Enforcement when SweetClaude is not configured for the project
