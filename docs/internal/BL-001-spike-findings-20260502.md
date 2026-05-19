# BL-001 Spike Findings: Claude Code Skills System
Date: 2026-05-02
Status: COMPLETE

## What is the official name?

"Skills" — nothing more. "Agentic skills" and "Skills 2.0" are third-party marketing terms. Anthropic's docs use "Skills" throughout. Source: code.claude.com/docs/en/skills.md

---

## Current Skill Frontmatter Fields (official)

| Field | Purpose |
|---|---|
| `name` | Invocation name (slash command) |
| `description` | Used for routing and display |
| `when_to_use` | Instructs Claude when to invoke |
| `allowed-tools` | Restricts which tools this skill can use |
| `model` | Model override for this skill |
| `effort` | Effort level: low/medium/high/xhigh/max |
| `context: fork` | Isolated subagent context |
| `agent` | Subagent type (when `context: fork`) |
| `hooks` | Skill-scoped lifecycle hooks |
| `user-invocable` | Whether user can invoke directly |
| `paths` | Path restrictions |
| `shell` | Shell preprocessing behavior |

---

## Key Findings

### 1. Shell preprocessing is official
`!`command`` and ` ```! ``` ` fenced blocks are documented. Claude Code executes the command before Claude sees anything — it's not Claude running the command, it's pre-invocation injection. `disableSkillShellExecution: true` in settings disables it globally. SweetClaude's current use of `!cat .sweetclaude/state/session-state.yaml` is canonical.

### 2. `isolation: "worktree"` does not exist
There is no worktree isolation frontmatter field. `context: fork` creates an isolated conversation context (no shared history with parent), not a git worktree. BL-023's fix of using explicit `EnterWorktree`/`ExitWorktree` tool calls was the correct approach — there was never a declarative worktree field to rely on.

### 3. Tool restrictions are real (`allowed-tools`)
Declarative tool restriction is documented. A skill can declare `allowed-tools: [Read, Grep, Glob]` to prevent Claude from using other tools within that skill's context. This is more robust than the current hook-based enforcement (test-guardian) which relies on instruction-following.

### 4. Model override is real
`model: haiku` in frontmatter routes the skill to a lighter model. Relevant for low-complexity SweetClaude skills (status, init, retro) that don't need Opus/Sonnet reasoning.

### 5. Skill-scoped hooks
`hooks: [config]` is documented but the format reference points to a separate hooks page. The key question (whether hooks fire only during this skill's execution or globally for the session) is not resolved in the skills doc alone.

### 6. Global install model works fine
`~/.claude/skills/<skill-name>/SKILL.md` is the documented path for personal (global) skills. The SweetClaude plugin distribution model (`~/.claude/plugins/sweetclaude@sweetclaude/skills/`) is a plugin path variant — compatible with the documented hierarchy.

---

## Recommended Adoption Strategy: SELECTIVE

**Adopt now (low risk, high value):**
- `allowed-tools` for TDD subagents — declare exact tool lists for test-writer and implementer. Replaces hook-based enforcement with declarative restriction. Spawn as follow-up item.

**Evaluate (medium risk, medium value):**
- `model: haiku` for lightweight skills (status, init, retro). Reduces token cost on skills that mostly read YAML and format output. Worth profiling — savings may be modest if most sessions invoke heavier skills anyway.

**Skip (complexity without clear benefit):**
- `context: fork` — current subagent pattern (Agent tool with explicit prompts) is more controllable and debuggable. `context: fork` is opaque about what context the subagent inherits.
- Skill-scoped hooks — current global hooks work and are easier to debug. Only migrate if a specific skill needs isolation from global hook behavior.

**Nothing to do:**
- `isolation: "worktree"` — never existed; BL-023 already handled the correct implementation.
- Shell preprocessing — already using it correctly.

---

## Follow-up Backlog Items

| Item | Priority |
|---|---|
| Add `allowed-tools` to TDD test-writer and implementer agents (replaces hook enforcement) | P2 |
| Evaluate `model: haiku` for status/init/retro/find-skill (cost profiling) | P3 |
