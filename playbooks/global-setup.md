# Claude Code Environment Optimization — Implementation Prompt

Paste everything below into a fresh Claude Code session. Each phase ends with a checkpoint where you approve before proceeding.

---

## START OF PROMPT

You are going to optimize my global Claude Code environment in a structured, phased way. This is infrastructure work on the Claude Code configuration itself — not application code.

### Context

My environment currently has:
- A 280-line `~/CLAUDE.md` that exceeds best-practice limits and degrades instruction-following
- The **Superpowers** plugin (v5.0.7, from `claude-plugins-official`) — this is good, we are keeping it
- The **Don Cheli SDD framework** (v1.26.0) installed at `~/.claude/don-cheli/` — this is redundant with Superpowers and must be removed entirely
- A **`real-tdd`** user skill at `~/.claude/skills/real-tdd/` — redundant with Superpowers' TDD skill, must be removed
- **Plaintext AWS credentials** embedded in `~/.claude/settings.json` allow-list entries (lines containing `export AWS_ACCESS_KEY_ID` and `export AWS_SECRET_ACCESS_KEY`) — these must be removed from the file
- 148 allow rules in `settings.json`, many stale
- `"skipDangerousModePermissionPrompt": true` in settings
- User skills we ARE keeping: `backlog-management`, `caucus`, `reconciling-documents`
- MCP servers that need cleanup (some "needs auth" and unused)

### Operating rules for this entire task

1. **Work phase by phase.** Complete one phase fully, report what you did, then STOP and ask me to approve before starting the next phase.
2. **Before modifying any file, show me exactly what you plan to change** — the file path, what you'll add/remove/modify, and why. Wait for my "go" before writing.
3. **After each modification, verify it** — re-read the file or run a validation command to confirm the change landed correctly.
4. **If anything requires information you don't have** (my stack, commands, preferences), ask me. Do not guess or use placeholders silently.
5. **Keep a running log.** After each phase, output a summary: what changed, what was verified, what's next.
6. **If a session ends mid-work**, the phase summaries serve as the recovery log. The next session can resume from the last completed phase.

---

## PHASE 1: Audit current state

**Goal:** Build a verified inventory of what exists before changing anything.

Do all of the following, then report findings:

1. Read `~/CLAUDE.md` and report: line count, major sections, what it mandates
2. List contents of `~/.claude/don-cheli/` (top-level dirs and file count)
3. List contents of `~/.claude/skills/` (each skill directory)
4. Read `~/.claude/settings.json` and report:
   - Whether plaintext AWS credentials appear in the allow-list
   - The total number of allow rules
   - The value of `skipDangerousModePermissionPrompt`
   - Any hooks currently configured
5. Check if `~/.claude/settings.local.json` exists and report its contents
6. List installed plugins: `~/.claude/plugins/` structure
7. List any files in `~/.claude/agents/`
8. Check for `~/cli_history/` directory (old progress tracking system)

**Output:** A numbered inventory of everything found. Then STOP and wait for my approval.

---

## PHASE 2: Security — Remove credentials from settings

**Goal:** Remove plaintext AWS credentials from `settings.json`. This is the highest-priority fix.

1. Read `~/.claude/settings.json`
2. Identify every line in the allow-list that contains `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY`
3. Show me the exact lines you will remove
4. Wait for my approval
5. Remove those lines
6. Re-read the file and confirm the credentials are gone
7. Confirm the JSON is still valid after removal

**IMPORTANT:** Do NOT rotate the keys or touch AWS configuration. I will handle key rotation separately outside of Claude Code. You are only removing the credential strings from `settings.json`.

**Output:** Confirmation that credentials are removed and the file is valid JSON. Then STOP.

---

## PHASE 3: Remove Don Cheli framework

**Goal:** Completely remove the Don Cheli SDD framework.

1. Verify `~/.claude/don-cheli/` exists and show its size (`du -sh`)
2. Check if `~/CLAUDE.md` references Don Cheli (search for "don-cheli", "don cheli", "especdev", "dc:", "sdd")
3. Check if `~/.claude/settings.json` has any Don Cheli hooks or references
4. Show me everything that will be removed/modified
5. Wait for my approval
6. Remove the directory: `rm -rf ~/.claude/don-cheli/`
7. Remove any Don Cheli references from other config files (but do NOT rewrite `~/CLAUDE.md` yet — that's Phase 5)
8. Verify the directory is gone

**Output:** Confirmation of removal and any remaining references that need cleanup in later phases. Then STOP.

---

## PHASE 4: Remove redundant user skill

**Goal:** Remove the `real-tdd` skill (redundant with Superpowers' TDD enforcement).

1. Read `~/.claude/skills/real-tdd/SKILL.md` and show me its contents
2. Confirm that Superpowers has a `test-driven-development` skill that covers this (check `~/.claude/plugins/cache/claude-plugins-official/superpowers/` for the TDD skill)
3. Show me the removal plan
4. Wait for my approval
5. Remove: `rm -rf ~/.claude/skills/real-tdd/`
6. Verify the remaining skills are intact: `ls ~/.claude/skills/`

**Output:** Confirmation. List remaining user skills. Then STOP.

---

## PHASE 5: Rewrite `~/CLAUDE.md`

**Goal:** Replace the 280-line global CLAUDE.md with a lean ~60-80 line version focused on universal rules that apply across all projects.

This is the **user-level** global CLAUDE.md, not a project-specific one. It should contain only rules that apply to every Claude Code session regardless of project.

**Before writing, ask me:**
- What programming languages/frameworks do I primarily use?
- Any global code style rules I want enforced everywhere?
- Any global "never do this" rules beyond what's standard?

Then draft the new `~/CLAUDE.md` with these sections (and nothing else):

```
# Global development rules

## Session discipline
- [Rules about how Claude should work across all projects]
- [Compaction preservation rules]
- [Verification requirements]

## Global invariants
- [Things that must never happen in any project: commit secrets, skip tests, etc.]

## Git workflow
- [Universal git conventions]

## Code quality
- [2-3 universal style/quality rules]
```

**Design principles for this file:**
- Target 60-80 lines maximum
- No project-specific build commands (those go in project-level CLAUDE.md)
- No documentation of Claude Code's own behavior (it already knows)
- No Superpowers mandate (the plugin is installed; mandating it in CLAUDE.md wastes instruction budget)
- No progress tracking templates (Superpowers handles session recovery via plans)
- No session-start requirements (reading git trees, progress files, etc. — this added latency and token cost)
- Every line must pass the test: "Would removing this cause Claude to make mistakes?"

1. Show me the complete draft
2. Wait for my approval (I may request edits)
3. Back up the old file: `cp ~/CLAUDE.md ~/CLAUDE.md.backup`
4. Write the new file
5. Re-read it and confirm line count and content

**Output:** The new file contents and line count. Then STOP.

---

## PHASE 6: Create new user-level skills

**Goal:** Create skills that replace the useful parts of what was removed (Don Cheli reasoning frameworks) and add new capabilities for structured development.

### Skill 1: `reasoning-frameworks`

Create `~/.claude/skills/reasoning-frameworks/SKILL.md`:

```markdown
---
name: reasoning-frameworks
description: Apply structured reasoning frameworks (first-principles, pre-mortem, Pareto, inversion, second-order effects) to strategic or architectural decisions.
---
Apply reasoning framework to: $ARGUMENTS

Available frameworks (pick the most relevant, or the one specified):

**First Principles**: Decompose to fundamental truths. What do we know for certain? What are we assuming? Rebuild from ground truth.

**Pre-Mortem**: Imagine the decision has failed catastrophically. What went wrong? Work backward to identify failure modes and mitigations.

**Pareto Analysis**: Identify the 20% of factors driving 80% of the outcome. Focus on highest-leverage actions.

**Inversion**: Instead of "how do we succeed?", ask "how do we definitely fail?" Avoid those paths.

**Second-Order Effects**: For each proposed action, trace: what happens next? And then what? Identify unintended consequences.

Process:
1. State the decision or question clearly
2. Apply the framework systematically
3. Present findings with concrete recommendations
4. Flag key uncertainties and what would change the recommendation
```

### Skill 2: `fix-issue`

Create `~/.claude/skills/fix-issue/SKILL.md`:

```markdown
---
name: fix-issue
description: Implement a single GitHub issue end-to-end with exploration, planning, TDD, verification, and a PR.
---
Fix GitHub issue $ARGUMENTS.

Process:
1. Explore: read the Issue, any linked Notion docs, and relevant code paths. Summarize current behavior and risks. Do not change code yet.
2. Plan: propose a stepwise plan with file list, test strategy, and verification commands. Wait for approval.
3. Implement: write tests first where possible. Change minimal code to satisfy acceptance criteria.
4. Verify: run lint + unit tests for affected packages. Capture and report results.
5. PR: open a PR with the project's PR template filled. Include how-to-verify steps.

Rules:
- If acceptance criteria are unclear or missing, stop and ask.
- Keep changes minimal and aligned to existing patterns.
- Every behavior change needs a test.
- If you hit a blocker, report it rather than working around it silently.
```

### Skill 3: `pr-ready`

Create `~/.claude/skills/pr-ready/SKILL.md`:

```markdown
---
name: pr-ready
description: Final pre-PR checklist — verify tests pass, fill PR template, check for secrets and debug code, ensure acceptance criteria are met.
---
Prepare PR for the current branch.

Checklist:
1. All acceptance criteria from the linked Issue are met
2. Tests pass (run lint + unit + integration as applicable)
3. PR template is filled completely (What, Why, How to verify, Rollout plan)
4. No secrets, credentials, or debug code in the diff
5. Commit messages are descriptive
6. Branch is rebased on latest main if needed

If any item fails, report what's missing and fix it before proceeding.
```

**Steps:**
1. Show me all three skill files
2. Wait for my approval (I may edit)
3. Create the directories and files
4. Verify: `ls -la ~/.claude/skills/` and read back each SKILL.md

**Output:** List of all user skills (old + new). Then STOP.

---

## PHASE 7: Prune settings.json allow rules

**Goal:** Reduce the 148 allow rules to a clean, well-scoped set.

1. Read `~/.claude/settings.json` and extract the full allow-list
2. Categorize every rule into:
   - **KEEP** — standard dev tools used regularly (git, python, pip, npm, node, gh, make, etc.)
   - **KEEP** — broad tool access that's genuinely needed (aws CLI if I use it, docker, etc.)
   - **REMOVE** — one-off commands from past sessions (specific CloudFormation stack names, specific deploy scripts, one-time admin commands)
   - **REMOVE** — overly broad permissions that should be tightened
   - **ASK** — rules you're unsure about
3. Present the categorized list in a table
4. Wait for my approval
5. Update the settings file
6. Verify: re-read the file, confirm valid JSON, report new rule count

**Target:** ~40-60 well-scoped rules.

**Output:** Before/after rule count. Then STOP.

---

## PHASE 8: Settings hardening

**Goal:** Tighten remaining settings for safety.

1. **`skipDangerousModePermissionPrompt`**: Show me the current value. Recommend whether to change it to `false` and explain the tradeoff. Wait for my decision.

2. **`settings.local.json`**: Read the 22 WebFetch domain allows. Categorize as KEEP (regularly used) vs REMOVE (one-off research). Present the list. Wait for my decision.

3. **Plugin blocklist**: Read `~/.claude/plugins/blocklist.json`. No changes needed — just confirm it's sane.

4. **Plugin marketplaces**: Read marketplace registrations. Confirm `claude-plugins-official` is present. Evaluate whether `superpowers-marketplace` is still needed (Superpowers is now in the official marketplace). Wait for my decision.

5. Apply approved changes.
6. Verify all modified files.

**Output:** Summary of all settings changes. Then STOP.

---

## PHASE 9: Clean up old artifacts

**Goal:** Remove leftover artifacts from the old configuration.

1. Check for `~/cli_history/` — if it exists, show its contents and size. This was the old progress tracking system replaced by Superpowers. Recommend removal.
2. Check for any stale files in `~/.claude/` that don't belong (temp files, old backups, orphaned configs)
3. Check for `~/CLAUDE.md.backup` (created in Phase 5) — confirm we're done with it
4. Present removal plan
5. Wait for my approval
6. Execute removals
7. Verify

**Output:** Final state of `~/.claude/` directory listing. Then STOP.

---

## PHASE 10: Final verification and summary

**Goal:** Confirm the environment is clean, consistent, and optimized.

Run these checks:
1. `cat ~/CLAUDE.md | wc -l` — confirm line count is in target range
2. `ls ~/.claude/skills/` — confirm expected skills remain
3. `ls ~/.claude/plugins/cache/` — confirm Superpowers and Frontend Design are present
4. Confirm `~/.claude/don-cheli/` is gone
5. Confirm `~/.claude/skills/real-tdd/` is gone
6. Read `~/.claude/settings.json` — confirm:
   - No AWS credentials
   - No Don Cheli hooks
   - Allow-list is pruned
   - Valid JSON
7. Estimate the context budget improvement (before vs after baseline token load)

**Output:** A final summary report:
- What was removed
- What was created
- What was modified
- Before/after metrics (CLAUDE.md line count, allow rule count, skill count, estimated context savings)
- Any follow-up items for me to handle manually (AWS key rotation, MCP server auth decisions, project-level CLAUDE.md creation)

---

## NOTES FOR SESSION RECOVERY

If this task spans multiple sessions, the phase summaries serve as the recovery log. At the start of a new session, say:

> "I'm continuing the environment optimization. The last completed phase was Phase [N]. Let me verify the current state before starting Phase [N+1]."

Then re-check the relevant state before proceeding.

## END OF PROMPT
