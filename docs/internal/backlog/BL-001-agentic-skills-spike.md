# BL-001: Spike — Agentic Skills (Claude Code Skills 2.0)

**Priority:** SPIKE
**Depends on:** none
**Created:** 2026-04-20
**Source:** https://pub.towardsai.net/claude-code-agent-skills-2-0-from-custom-instructions-to-programmable-agents-ab6e4563c176

## Summary

Claude Code's skill system has evolved from static markdown-with-frontmatter into something closer to "programmable agents" — skills can now spawn isolated subagents, inject live data via shell commands at invocation time, restrict tool access, override the model, hook into lifecycle events, and fork execution contexts (including parallel worktrees). SweetClaude's current skills are almost entirely prose instructions with the Skill tool loader doing the heavy lifting through the main-agent context. A subset of SweetClaude skills already use subagent isolation (TDD test-writer vs. implementer) and hooks (test-guardian, auto-test-runner, git-checkpoint), but we have not systematically explored whether the newer agentic-skill primitives would let us simplify, harden, or extend the framework.

This spike determines whether and where SweetClaude should adopt agentic-skill patterns — not whether to rewrite everything.

## Initial Thinking

**What the article actually claims (skimmed — it is thin on specifics):**
- Skills as programs, not instructions
- Isolated subagent spawning with independent context windows
- Dynamic context injection via shell at invocation
- Tool access restrictions per skill
- Model override per skill
- Lifecycle hooks
- Forked/parallel execution, one example uses separate git worktrees

**Where this maps to current SweetClaude pain:**
- TDD Level 3 already needs test-writer/implementer isolation — the skill achieves this by spawning subagents inside the main skill body. An agentic-skill-native form might be cleaner.
- QA Caucus (3 perspectives) is a natural fit for parallel subagents — currently run sequentially.
- Hooks (test-guardian, auto-test-runner, git-checkpoint) are already lifecycle-ish but live in `settings.json`, not co-located with skills. Skill-scoped lifecycle hooks might reduce scatter.
- Tool restriction could be valuable for the test-writer subagent (no ability to edit source files) and the implementer (no ability to edit tests) — we enforce this via hooks today; declarative restriction would be more robust.
- Dynamic context injection could replace the repeated "read phase.yaml, read improvement-register" ritual at session start with a skill-scoped pre-hook.

**Key technical decisions to resolve in the spike:**
1. What is the actual current spec for agentic skills? The article is marketing. The truth lives in Anthropic's Claude Code docs — find the canonical reference before designing anything.
2. Are agentic skills a superset of current skills (frontmatter-compatible) or a new format? Migration cost depends.
3. Do they work with the SweetClaude global-install model (`~/.claude/skills/sweetclaude/...` with symlink-on-install), or do they require project-local?
4. Can hooks currently in `hooks/*.sh` be migrated to skill-scoped hooks without losing the cross-project enforcement they provide?

**Risks and open questions:**
- Adopting too eagerly could fracture the framework into a mix of legacy-skill and agentic-skill patterns, increasing maintenance burden.
- If agentic skills require a newer Claude Code version than some users have, adoption gates on user upgrade.
- The "programmable" framing implies more complexity. Not every skill benefits — `sweetclaude:status` does not need tool restrictions.

**Architecture implications:**
- Potential simplification of `rules/sweetclaude/` → inline into skill frontmatter
- Potential consolidation of `hooks/*.sh` into skill lifecycle hooks for hooks that are single-skill-scoped
- Potential parallelization of QA Caucus invocations

**Connection to other backlog items:**
- None yet. Likely spawns follow-up items for specific migrations.

## Spike Deliverable

A brief (1–2 pages) that answers:
1. What are agentic skills, precisely? (Cite Anthropic docs, not third-party articles.)
2. Which SweetClaude skills would materially benefit from migration? (Ranked.)
3. Which framework primitives (rules, hooks, subagent definitions) could be simplified or replaced?
4. Recommended adoption strategy: no-op, selective, or full migration — with rationale.
5. List of follow-up backlog items to create if we proceed.

## Open Questions

- Is "agentic skills" the official Anthropic name or a third-party label? Need canonical source.
- Does SweetClaude's current Skill tool loader still work with newer skill formats, or is there a break?
- How do agentic skills interact with the `.claude-plugin/plugin.json` distribution model SweetClaude uses?
