# Platform Dependencies

**Version:** 1.0
**Date:** 2026-05-01

SweetClaude depends on three external systems. This document states what each dependency does, what fails if it goes away, whether a contingency plan exists, and what would trigger a reconsideration of the architecture.

This is transparency, not alarm. These are known and accepted tradeoffs — but a project that depends on commercial platforms owes its users a written answer to "what happens if the platform changes?"

---

## Dependency 1: Claude Code (Anthropic)

**What it is:** Claude Code is the runtime SweetClaude runs inside. SweetClaude skills are slash commands that Claude Code loads and executes. The hook system, CLAUDE.md rules, and subagent architecture all depend on Claude Code's extension API.

**What fails if it changes:** Everything. If Anthropic changes the slash-command interface, deprecates CLAUDE.md-based customization, or stops supporting PostToolUse/PreToolUse hooks, SweetClaude's architecture would need to be rebuilt. This is not a partial failure — it is an existential dependency.

**Contingency plan:** None that pre-empts the problem. The mitigation is: (1) SweetClaude follows Anthropic's changelog closely and flags breaking changes before they ship to users; (2) state files are plain YAML and markdown, so the strategic and product artifacts survive any platform change; (3) the behavioral framework (phases, gates, interaction model) is documented and could be ported to a different execution environment if necessary.

**What would trigger reconsideration:** Anthropic deprecating the plugin API without a migration path. If that happened, the options would be: rebuild as a Claude.ai Project instruction set, rebuild as a standalone LLM-agnostic CLI, or deprecate the project.

**Risk assessment:** High dependency, accepted tradeoff. The VSCode extension ecosystem has the same structure. The risk is real; the mitigation is watchfulness and the portability of state files.

---

## Dependency 2: Superpowers (obra/superpowers)

**What it is:** Superpowers is a Claude Code plugin that provides implementation primitives: plans, git worktrees, parallel agent dispatch, systematic debugging. SweetClaude code skills (`code-feature`, `code-issue`, `code-debt`) call into Superpowers skills.

**License:** MIT

**What fails if it goes unmaintained:** Code-phase skills degrade. Strategy, product, design, corpus, and orchestration skills are unaffected — they have no Superpowers dependency. The `--strategy-skills-only` install path works without Superpowers.

**Contingency plan:** The Superpowers dependency is wrapped at the skill call boundary. If Superpowers becomes unavailable, the affected skills (`code-feature`, `code-issue`, `code-debt`) can be rewritten to implement their functionality directly. This would be multi-week work, not multi-month.

**What would trigger reconsideration:** Superpowers becoming unmaintained and incompatible with current Claude Code versions, with no active fork. At that point, internalizing the functionality is the likely path.

**Risk assessment:** Moderate dependency, contained blast radius. The isolation of the `--strategy-skills-only` install means the majority of SweetClaude's value surface is unaffected by Superpowers availability.

---

## Dependency 3: mcp-local-rag (npm)

**What it is:** mcp-local-rag provides local vector search for the corpus management RAG features. It runs a per-project vector database on your machine with no external services.

**License:** MIT

**What fails if it goes unmaintained:** The corpus pipeline's promote step stops auto-indexing. The `/sweetclaude:document-corpus rag` mode fails. Everything else in SweetClaude is unaffected — corpus management through the promote step still works, just without the RAG index.

**Contingency plan:** RAG is explicitly optional. If mcp-local-rag becomes unavailable, the behavior reverts to manual semantic search. The canonical documents (produced by the corpus pipeline) still exist and are still organized — they just aren't automatically indexed.

**What would trigger reconsideration:** mcp-local-rag becoming incompatible with current Node.js versions and unforkable under its license. At that point, a swap to a different local vector search library would be straightforward — the dependency is cleanly isolated to the rag/reindex modes of `document-corpus`.

**Risk assessment:** Low dependency, cleanly isolated, explicitly optional.

---

## What This Document Is Not

This is not a promise that these dependencies will remain stable, or that SweetClaude will survive if they change. It is a statement that these risks are known, acknowledged, and tracked.

If you are evaluating SweetClaude for a context where commercial AI platform dependency is unacceptable, the honest answer is: this project is not right for that context. The strategic and product artifacts it produces (discovery docs, PRDs, decision logs, assumption registers) are portable. The workflow execution layer is not.

---

## Changelog

| Date | Change |
|---|---|
| 2026-05-01 | Initial version |
