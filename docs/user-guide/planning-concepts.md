# Planning Concepts

**Version:** 1.1
**Date:** 2026-05-10

This page explains the building blocks SweetClaude uses to plan and track software work — what they are, how they relate to each other, and the four development modes that use them differently.

---

## A Note on Opinions

There are many valid ways to structure a project: what  backlogs, epics, milestones, sprints, etc. actually are and how they relate to each other, what constraints are enforced, etc. Every experienced product owner / developer earns their own scars, wisdom, and preferences. That diversity of ideas and experiences is one of the things that makes software development a rich domain.

SweetClaude is opinionated, because many people just want to develop their project, not dwell on the internal processes. The structure described in this document reflects how the authors of SweetClaude actually build software. It is not intended to be a synthesis of industry best practices or a neutral survey of methodologies. It is one coherent approach that has worked in practice, built into the tool so it does not have to be re-negotiated every session.

That said, SweetClaude will work the way you tell it to. If you or your team has a different vocabulary, a different hierarchy, or a different opinion about what a backlog is for, etc. then SweetClaude is happy to work from your own set of hard-won lessons. The easiest path is to tell SweetClaude what you prefer at the start of a session and it will work within your model. You can describe your preferred structure in plain language and it will adapt. For deeper changes, the skills are designed to be readable and forkable. You can fork the framework and modify the skills directly. 

As always, YMMV and the SweetClaude maintainers love feedback.

---

## The Building Blocks

### Story / Issue

This is the atomic unit of development work. The term "story" ties well to user-centricity, while "issue" is often used in developer-centric tools like GitHub. In some larger-team processes, a "story" is what lives in the product manager's world, and that story is eventually broken down into multiple development issues as units of actual code work. To keep it relatively simple, SweetClaude considers the terms "story" and "issue" to be interchangeable, and is not here to debate the finer points. If you want something different, fork and tweak to your heart's content.

For the rest of this doc, we define a story as something describing something a user or the system needs to do, with enough specificity to know what success looks like when it has been implemented, that a developer (human or agent) actually implements. Stories are what you actually work on and ship. If a story is too big to be done as one task, SweetClaude can help you break it down into smaller stories. This is how epics often get created: a big story that needs to be broken down becomes an epic with new, smaller stories that make up the epic.

In SweetClaude, every story should have:
- A **status**: new → ready → active → blocked → deferred → done → abandoned
- A **priority**: next · sooner · soon · later · someday
- An optional **tag** for the system or component it touches (see [Tags](#tags) below)

Stories can have more or less detail depending on the discipline level being implemented. For example, Test Driven Development (TDD) demands that before a line of code is written for a story, a test is written in advance to make sure that code does what's expected; in that case, the developer (human or agent) uses the test to determine how to implement code.

The workflow around creating and implementing stories can be managed in many ways — as a simple force-ranked list, a release-oriented roadmap, moved through a Kanban flow, etc. The options implemented in SweetClaude are described in detail below.

### Backlog

A backlog is a flat list of stories. The backlog is where ideas go when they are captured but not yet scheduled for work. It is intentionally structureless — no milestones, no epics, no sprints. The only organizing force is priority: you force-rank the list so the most important things float to the top. 

The backlog needs to be managed, otherwise it gets unwieldy quickly. This management involves prioritizing stories in the backlog, moving items from the backlog into a roadmap, or both. If you're just vibe-coding or developing an internal structure, just letting SweetClaude look through the backlog to decide what's next can work just fine. For something like a product with milestones and release targets, you probably want a structured roadmap to drive the timeline, with milestones and epics to contain related phases of work.

You can ask SweetClaude to help you think through this process anytime.

The backlog is a completely separate structure from the roadmap. Backlog stories do not require epics or milestone assignments. When a story moves from the backlog to the roadmap, it is physically moved and assigned to an epic. A story ID never appears in both the backlog and the roadmap at the same time.

### Epic

A named bundle of stories that are related by feature area or functional domain. An epic groups stories that belong together conceptually — all the stories for a given feature, subsystem, or capability. Epics typically live inside milestones on a roadmap. In the full hierarchy, an epic belongs to exactly one milestone. Stories within an epic are worked closely together because they share context, touch the same code, or have technical dependencies on each other.

Epics are a product-level concept — they answer "what are we building?" A sprint is the execution-level complement that answers "when are we building it?"

### Milestone

A named strategic outcome — a meaningful product state the project is driving toward. Examples: "Platform Foundation Complete," "Web UI Shipped," "Auth Alpha-Ready."

They are checkpoints that define what "done enough to move on" means for a significant phase of work. A milestone is complete when all its stories (which are usually in epics or sprints) are complete.

### Sprint

A fixed-length time container for work, used in Agile. A sprint groups stories by when they will be worked, not by what they are about. Where an epic bundles stories because they are feature-related, a sprint bundles stories because they fit within a constrained block of time — typically one to four weeks.

Sprints are most useful for teams coordinating parallel work, tracking velocity, and managing delivery commitments. Solo developers often skip sprints entirely and work directly from epics or the backlog.

---

## The Hierarchy

When you use the full structure, work organizes into the less-structured backlog and the strictly-structured roadmap. You perform triage regularly to move things from the backlog to the roadmap.

```
Backlog (stands alone)
	└── Story

Roadmap
  └── Milestone
  			└── Epic
        			└── Sprint (optional)
              			└── Story
              
```

In SweetClaude's default opinionated structure, a story belongs to one epic. An epic belongs to one milestone. A sprint is optional and can be attached to either a milestone or an epic — it provides a time-slice view of whichever level it is attached to. If you are not using sprints, stories live directly under their epic.

The **backlog** sits completely outside this hierarchy — it has no milestone and no epic. Promoting a story from the backlog means physically moving it to an epic (which implies a milestone). The story ID does not change on promotion.

---

## Development Modes

SweetClaude supports four modes. Each one uses the building blocks above differently — some use all of them, some skip most of them. The right mode depends on where you are in the project, who you are building with, and how much structure is actually earning its weight.

### Flow Mode (Backlog-Driven)

The simplest structured mode, and the natural next step up from vibe coding.

You keep a flat backlog. When you have an idea, you put it in. A couple of times a week you do a pass through the list to bring the most important things to the top — this is called **triage** or **grooming**. When you sit down to work, you take the next thing off the top of the list and work it.

No milestones. No epics. No sprints. No roadmap. Just: what matters most right now, and work it.

This approach works well when:
- You are early-stage and do not yet know enough to plan quarters ahead
- You are solo and the coordination overhead of a roadmap is not worth it
- The work is exploratory and priorities shift frequently
- You want to keep overhead near zero and just ship things

The limitation is visibility. A backlog tells you what exists and what is prioritized, but it does not tell you where you are going or when you will get there. As soon as someone outside the project (a customer, a co-founder, an investor) starts asking "what does the next six months look like?", you need a roadmap.

### Kanban

Kanban keeps a backlog and works stories continuously — no sprints, no cycles, no ceremony around what gets started when. The defining constraint is a **WIP limit**: SweetClaude hard-enforces a maximum of three stories in active status at any time. You cannot start new work until something finishes.

The WIP limit is not advisory. It is the entire mechanism. By capping work-in-progress, it forces completion over accumulation — the most common failure mode in solo development is a graveyard of half-done work. The limit keeps the flow moving.

Kanban works well with or without a roadmap. You can run a pure backlog (triage and pull from the top) or organize the backlog behind milestones and epics and still work Kanban-style through execution. The mode governs how you execute, not necessarily how you plan.

This mode works well when:
- You are solo or a small team and sprint ceremonies would be pure overhead
- You deliver continuously rather than in scheduled batches
- You want more discipline than Flow but not the full Agile apparatus
- You have been in Flow Mode and are starting to notice too many things half-done

### Shape Up

Shape Up is a methodology from Basecamp built around a fundamentally different premise: instead of estimating how long work will take, you decide in advance how much time a piece of work is worth — the **appetite** — and then cut scope to fit. Time is fixed; scope is variable.

The workflow has two phases that alternate:

**Shaping.** Before work can be scheduled, it must be shaped — described with enough specificity to bet on it, but not so much detail that it precludes good decisions by the team building it. The output is a **pitch**: what the problem is, what the solution boundaries are, and what is explicitly out of scope. Unshapen ideas do not enter the cycle.

**Betting.** At the start of each 6-week cycle, a betting table decides which shaped pitches get worked. Pitches that are not bet on do not carry forward automatically — they go back to a pool and must be re-pitched if they are still worth doing. There is no accumulating backlog of promised work.

SweetClaude enforces a hard gate: implementation is blocked until the betting table approves the pitch. This prevents the most common Shape Up failure mode, which is treating pitches as a formality and building before the appetite is agreed.

Shape Up has no epics, no sprints, and no milestones in the SweetClaude sense. The cycle is the container. Stories exist but they emerge from pitches rather than from a roadmap.

This mode works well when:
- You want real scope control, not just deadline pressure
- You are a product team that has experienced the failure mode of a backlog that never shrinks
- You want to make deliberate bets on work rather than commit to an infinite roadmap
- Unpredictable scope has caused missed milestones in the past

### Agile (Roadmap-Driven)

The structured mode used by product teams delivering software commercially with full team coordination.

A product manager or owner works the pipeline in two directions at once. They pull ideas from the backlog into the roadmap — assigning each story to a milestone and an epic, which answers the question "what are we actually targeting?" They also group closely related stories into epics, which answers "what belongs together and should be worked closely?"

The dev lead or tech lead then looks at each epic's stories and:
- Identifies technical dependencies between stories (which stories block which)
- Decides the order in which stories should be worked within the epic
- Organizes stories into sprints, fitting them into time windows and matching available capacity

The result is a roadmap: a structured view of what ships with what, organized around meaningful product outcomes (milestones), with feature-related work bundled together (epics), and specific delivery windows defined (sprints). SweetClaude enforces a hard gate: implementation is blocked unless there is an active sprint.

Epics are first-class in Agile mode — they appear in status views, Kanban boards, and big-picture renders. In all other modes, epics are available but not surfaced by default.

This mode works well when:
- You are past early stage and need to communicate a delivery plan to stakeholders
- You have a team and need to coordinate who works on what, and in what order
- You are managing scope and want to defer work explicitly rather than just not doing it
- You need to reason about technical dependencies across a large body of work

---

## Choosing a Mode

If you are not sure which mode fits your situation, this table shows exactly what each mode uses and enforces.

| | **Flow** | **Kanban** | **Shape Up** | **Agile** |
|---|---|---|---|---|
| **Stories** | Yes | Yes | Yes (from pitches) | Yes |
| **Backlog** | Optional | Yes | No — pitches instead | Yes |
| **Milestones** | Optional | Optional | No — cycles instead | Yes (required) |
| **Epics** | Optional, not surfaced | Optional, not surfaced | No | Yes, first-class |
| **Sprints** | No | No | No — 6-week cycles | Yes (required to implement) |
| **Structured roadmap** | No | Optional | No | Yes |
| **WIP limit** | None | 3 active (hard block) | Appetite per pitch | Sprint capacity |
| **Kanban board columns** | No | Yes (statuses as columns) | No | Yes |
| **TDD enforcement** | Level 1 | Level 1 | Level 2 | Level 2 |
| **Hard gate to implement** | None | WIP limit | Betting table approval | Active sprint required |
| **Best for** | Solo, exploration, prototypes | Solo or small team, continuous delivery | Product teams, fixed appetite, scope control | Teams, structured iteration, stakeholder delivery |

**How to read the table:**
- "Optional" means the artifact exists and you can use it, but SweetClaude does not require it or surface it prominently.
- "Not surfaced" means epics are available in the data model but do not appear in status views or big-picture renders.
- "Hard block" means SweetClaude will not let you proceed until the condition is met.

You can switch modes at any time — work already done stays as-is. When switching to a more structured mode, SweetClaude will flag what artifacts are missing and offer to catch up.

---

## Tags

Tags are labels attached to stories that identify the system or component the story touches — for example: `auth`, `vivarium`, `telemetry`, `web-ui`, `platform-db`.

Tags are orthogonal to the milestone/epic hierarchy. A story in the auth epic might touch the `platform-db` component; a story in the observability epic might also touch `platform-db`. Tags make that cross-cutting connection visible.

The primary use of tags is **dependency analysis**: before deciding what to work on next, you can look at which tags appear most in your active stories and identify which components have the most in-flight work. Stories that touch the same component often have implicit dependencies — working them in sequence rather than in parallel reduces merge conflicts and context-switching cost.

Tags are also useful for sprint planning: if two stories both touch `auth`, there is usually a good reason to put them in the same sprint even if they are in different epics.

---

## Status and Priority Reference

**Status values** — what is happening with a story right now:

| Status | Meaning |
|---|---|
| new | Captured, not yet reviewed or scheduled |
| ready | Reviewed, well-specified, ready to be worked |
| active | Being worked right now |
| blocked | Cannot proceed — waiting on something external |
| deferred | Consciously postponed — will come back to it |
| done | Complete and accepted |
| abandoned | Will not do — closed without completion |

When using Kanban, these statuses map directly to board columns.

**Priority values** — how urgently a story should be worked relative to others:

| Priority | Meaning |
|---|---|
| next | Work this before anything else |
| sooner | Work this soon, ahead of the general queue |
| soon | Work this in the near term |
| later | Work this eventually, but not urgently |
| someday | Good idea, no current urgency — backlog hold |

Priority is how you force-rank the backlog. In a roadmap, priority within an epic or sprint determines sequencing when there is more work than capacity.
