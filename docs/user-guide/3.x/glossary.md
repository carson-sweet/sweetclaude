# SweetClaude Glossary

**Version:** 1.0
**Date:** 2026-05-06

Quick definitions for SweetClaude-specific terms. When you see one of these in the docs and want to know what it means, this is the lookup.

---

**Caucus**
A multi-agent review pattern where three specialist subagents (service, component, integration) review the same input independently — they never see each other's outputs. Isolation preserves diversity of findings. Used in the TDD Level 3 pipeline to review test plans before implementation begins.

**Deference level**
How much SweetClaude stops and waits for your approval. Three levels: *Collaborative* (stops at every sub-step), *Guided* (stops at major decisions), *Autonomous* (stops only at phase gates). Set at session start; changeable mid-session.

**Phase dwelling**
SweetClaude's commitment to not pushing you forward. It never asks "ready to move on?" or "shall we proceed?" — you decide when a phase is done. Iteration is the work; advancement happens when you say so.

**Phase gate**
A quality checkpoint between phases. SweetClaude will not advance to the next phase until the exit criteria for the current one are met. *Soft gates* can be bypassed with "I've addressed this informally — proceed." *Hard gates* (marked ⚠️) require explicit risk acceptance logged to the decision log.

**Subagent**
A separate Claude instance spawned for a specific task — test writing, implementation, code review, QA, security review. Subagents have isolated context windows: the implementer never sees the spec, only the failing tests. This prevents rationalization across contexts.

**Subagent isolation**
The design principle that test writers and implementers must never share context. Prevents the implementer from knowing what the tests are supposed to prove, which would allow it to write code that passes tests without satisfying the underlying intent. Applies at TDD Levels 2 and 3; Level 1 uses a single context.

**TDD Level**
The degree of test-driven development enforcement. Four levels: *Level 0* (hotfix — regression test written in same session), *Level 1* (light — test-first, single context), *Level 2* (standard — subagent separation, test-guardian hook active), *Level 3* (full — Gherkin specs, QA caucus, maximum isolation). See [TDD Levels](tdd.md) for full details.

**Test-guardian hook**
A Claude Code hook that physically blocks edits to test files during the IMPLEMENT phase. Prevents the implementer from modifying tests to make them pass. Active at TDD Levels 1–3.

**Auto-test-runner hook**
A Claude Code hook that runs the test suite automatically after every source file edit during IMPLEMENT. Gives instant feedback on whether the change moved the tests from RED to GREEN.

**Version stage**
Where the project is in its lifecycle: IDEA → PRE-ALPHA → PROTOTYPE → ALPHA → BETA → GA → SCALED → MAINTAINED. Controls which work types and phase gates are visible. A PROTOTYPE-stage project doesn't see compliance work types; a GA project gets them surfaced automatically. New projects start at IDEA or PRE-ALPHA depending on how they were initialized.

**Betting table**
A Shape Up concept (does not exist in Kanban or Agile modes). A decision artifact produced during the DEFINE phase that records: the core outcome if this ships, the rabbit holes (likely scope explosions), and what is explicitly out of scope. Implementation is hard-blocked until the betting table is approved.

**`.sweetclaude/` directory**
Where SweetClaude keeps all its own artifacts — state, product docs, design docs, plans. Intentionally separate from your distributable codebase so SweetClaude's work never mingles with the code you ship. Commit this directory to git — it's project history, not scratch.
