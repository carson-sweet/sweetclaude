# SweetClaude Glossary

**Version:** 1.3
**Date:** 2026-10-21

Quick definitions for SweetClaude-specific terms. When you see one of these in the docs and want to know what it means, this is the lookup.

---

**Caucus**
A multi-agent review pattern where three specialist subagents (service, component, integration) review the same input independently — they never see each other's outputs. Isolation preserves diversity of findings. Used in the TDD Level 3 pipeline to review test plans before implementation begins.

**Deference level**
How much SweetClaude stops and waits for your approval. Three levels: *Collaborative* (stops at every sub-step), *Guided* (stops at major decisions), *Autonomous* (stops only at phase gates). Set at session start; changeable mid-session.

**Phase dwelling**
SweetClaude's commitment to not pushing you forward. It never asks "ready to move on?" or "shall we proceed?" — you decide when a phase is done. Iteration is the work; advancement happens when you say so.

**Phase gate**
A quality checkpoint between phases. SweetClaude will not advance to the next phase until the exit criteria for the current one are met. *Soft gates* can be bypassed with "I've addressed this informally — proceed." *Hard gates* require explicit risk acceptance logged to the decision log. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.)

**Subagent**
A separate Claude instance spawned for a specific task — test writing, implementation, code review, QA, security review. Subagents have isolated context windows: the implementer is dispatched with the failing tests, not the spec. This prevents rationalization across contexts.

**Subagent isolation**
The design principle that test writers and implementers do not share context. Prevents the implementer from knowing what the tests are supposed to prove, which would allow it to write code that passes tests without satisfying the underlying intent. At Level 2 only the implementer is a subagent and the tests are written in the main context; at Level 3 the test writer is also a subagent. Level 1 uses a single context.

**TDD Level**
The degree of test-driven development enforcement. Four levels: *Level 0* (hotfix — regression test written in same session), *Level 1* (light — test-first, single context), *Level 2* (standard — tests written in the main context, implementer as a subagent, test-guardian hook active once `code-tdd` marks `tdd_phase` implementing), *Level 3* (full — Gherkin specs, QA caucus, maximum isolation). See [TDD Levels](tdd.md) for full details.

**Test-guardian hook**
A Claude Code hook that physically blocks edits to test files during the IMPLEMENT phase. It applies only after `code-tdd` marks `tdd_phase` implementing with `scripts/tdd_phase.py`. Prevents the implementer from modifying tests to make them pass. Once `tdd_phase` is implementing, the hook denies edits to test files; to override, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tdd_phase.py release --file <path> --approval "<text>"`, which is logged.

**Auto-test-runner hook**
A Claude Code hook that runs the test suite automatically after source file edits while `tdd_phase` is implementing, using the configured test command or one detected from the project, and reports failures back. Gives instant feedback on whether the change moved the tests from RED to GREEN.

**Version stage**
Where the project is in its lifecycle: IDEA → ALPHA → BETA → GA → SCALED → MAINTAINED. During onboarding, setup writes IDEA for new projects and early prototypes, and maps the stage you report for an existing project to IDEA, ALPHA, BETA or GA. You declare the stage; the system never advances it.

**Betting table**
A Shape Up concept (does not exist in Kanban or Agile modes). A decision artifact produced during the DEFINE phase that records: the core outcome if this ships, the rabbit holes (likely scope explosions), and what is explicitly out of scope. Implementation is hard-blocked until the betting table is approved. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.)

**Agile mode**
SweetClaude's most structured mode. Uses the full hierarchy: milestones, epics, sprints, and stories. Epics are first-class. Implementation is hard-blocked without an active sprint. Best for teams with stakeholder delivery commitments. See [Planning Concepts](planning-concepts.md). (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.)

**Backlog**
A flat, priority-ranked list of stories that have not yet been scheduled for work. The default landing zone for all new ideas. The backlog is a completely separate structure from the roadmap — backlog stories have no epic and no milestone assignment. Triage moves a story from the backlog to `roadmap/issues/` and its ID does not change; linking it to an epic or a milestone is a separate step. See [Planning Concepts](planning-concepts.md).

**Backlog-driven development**
A development approach where the only planning structure is a priority-ranked backlog. Triage the list a couple of times a week, work the top item. No milestones, no epics, no sprints. The natural next step up from vibe coding. See [Planning Concepts](planning-concepts.md).

**Epic**
A named bundle of stories grouped by feature area or functional domain. A story carries an `epic` field, and an epic can be linked to a milestone. Stories within an epic are worked closely together because they are feature-related or technically interdependent. See [Planning Concepts](planning-concepts.md).

**Milestone**
A named strategic outcome — a meaningful product state the project is driving toward. Milestones are not releases and not dated. A milestone is marked achieved when its success criteria are met and you confirm it. See [Planning Concepts](planning-concepts.md).

**Flow mode**
SweetClaude's lightest mode. No phase gates, no required artifacts. Backlog and milestones are optional. TDD Level 1. SweetClaude observes quietly and builds what you ask. Best for exploration, prototypes, and personal projects. See [Planning Concepts](planning-concepts.md).

**Kanban mode**
A continuous-flow mode with a hard WIP limit of 3 in-progress stories; the WIP limit hook denies activating an issue beyond the limit. No sprints. Backlog is used. Best for solo developers or small teams who deliver continuously without sprint ceremonies. See [Planning Concepts](planning-concepts.md).

**Roadmap-driven development**
A development approach where stories are organized into milestones and epics, with optional sprint planning for time-boxed execution. Used by product teams delivering software commercially. See [Planning Concepts](planning-concepts.md).

**Shape Up mode**
A mode based on the Basecamp methodology. Work enters through shaped pitches, not a backlog. A betting table approves pitches before implementation begins (hard gate). 6-week cycles; fixed appetite, variable scope. No milestones, epics, or sprints. See [Planning Concepts](planning-concepts.md). (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.)

**Sprint**
A fixed-length time container for work (Agile). Groups stories by when they will be worked, not by what they are about. Optional in SweetClaude — solo developers often skip sprints and work directly from epics. See [Planning Concepts](planning-concepts.md).

**Story**
The atomic unit of work. Describes something a user or the system needs, with enough specificity to know when it is done. Every story has a status and a priority. Stories keep their ID when promoted from the backlog to the roadmap. See [Planning Concepts](planning-concepts.md).

**`.sweetclaude/` directory**
Where SweetClaude keeps all its own artifacts — state, product docs, design docs, plans. Intentionally separate from your distributable codebase so SweetClaude's work never mingles with the code you ship. Commit this directory to git except derived state: the guardian flag and recovery snapshots (`.sweetclaude/state/recovery-runs/`, which setup gitignores) stay out of source control. The rest is project history, not scratch.

## Doctor

The SweetClaude diagnostic and maintenance front door. `/sweetclaude:configure doctor` scans state, hooks, storage, migration, config, files, onboarding, and environment, then routes repair, recovery, or supported migration through safety checks.

## Recover

The safety flow for projects left in bad update, doctor, repair, or unsafe migration states. `/sweetclaude:configure recover` diagnoses first, plans, snapshots before mutation, asks before execution, verifies, and reports rollback instructions.

## Compatibility Mode

A maintenance state where recovery has accepted a legacy taxonomy layout without moving product artifacts. Doctor collapses accepted legacy taxonomy noise and does not present a migration prompt.

## Stable Channel

The recommended SweetClaude plugin channel for normal active project work. It is the 5.x line on `main`, installed with `carson-sweet/sweetclaude@main` and `sweetclaude@sweetclaude-stable`. The older 3.x line is the legacy channel, installed from `carson-sweet/sweetclaude@stable-3.x` as `sweetclaude@sweetclaude-legacy`.

## 4.x Beta Channel

The former opt-in beta channel for 4.x pre-release testing. Retired after the 4.x line was promoted to stable — it no longer receives updates and cannot be installed. Existing beta installs make a one-time switch to stable (see [Installing SweetClaude](install.md)).
