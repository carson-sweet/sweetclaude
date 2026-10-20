# Operating Modes — content for sweetclaude:help Option 2

## Option 2 — Operating Modes (top-level)

SweetClaude doesn't lock you into a single methodology. Think of it as a dial, not a switch. There are four named modes on that dial — each one enforcing a different level of structure:

**Flow Mode** — the lightweight end. No phase gates, no required artifacts, no ceremony. SweetClaude observes quietly and builds what you ask. Right for exploration, prototypes, and personal projects where speed matters more than auditability.

**Kanban** — adds a WIP limit (3 in-progress items, hard enforced). Keeps work flowing without piling up. Right for continuous delivery without sprints.

**Shape Up** — 6-week cycles with pitches and a betting table. No backlog — all work enters through approved pitches. A hard gate prevents implementation until the betting table approves the pitch. Right for product teams that want fixed appetite and variable scope.

**Agile** — sprint-based execution. You must have an active sprint to implement. Right for teams running structured iteration cycles.

Most solo developers start in Flow Mode and dial up as the project matures. You can change mode at any time — even mid-project.

There's also **John Wick mode** — an experimental, fully autonomous SDLC pipeline that runs discovery through PR with minimal human intervention. It uses TDD Level 3, subagent isolation, QA caucus review, and a full phase sequence. Not for everyday use — but powerful for teams that want maximum automation and discipline. Invoke with `/sweetclaude:build john-wick`.

## Option 2b — What actually changes at each level

Here's what each mode actually enforces:

**Flow Mode**
- Conversational routing — describe what you want, SweetClaude figures out what to run
- TDD Level 1 — tests written before implementation, single context
- No phase gates, no required artifacts
- Quietly accumulates thin versions of key artifacts in the background (mini brief, architecture sketch, decision log entries) — so if you decide to switch modes later, there's something to build from
- Right for: exploration, prototypes, personal projects

**Kanban**
- TDD Level 1
- WIP limit of 3 enforced as a hard block — can't start new work until something finishes
- Sprint skills disabled — continuous flow only
- Right for: solo or small teams doing continuous delivery without sprint ceremonies

**Shape Up**
- TDD Level 2 — subagent isolation between test writer and implementer
- Betting table required before any implementation begins (hard gate)
- 6-week cycles, no backlog — all work enters through approved pitches
- Ship/no-ship decision required at end of each cycle
- Right for: product teams who want fixed appetite and real scope control

**Agile**
- TDD Level 2
- Active sprint required to implement (hard gate)
- Sprint close required before ship
- Right for: teams running structured iteration with sprint ceremonies

**John Wick** *(experimental)*
- TDD Level 3 — full subagent isolation, QA caucus, mutation testing available
- Fully autonomous — runs discovery through PR with minimal human intervention
- Hard gates at key decisions (PRD approval, design review, final PR)
- Right for: when you want maximum automation and discipline end-to-end

You can switch modes at any time — even mid-feature.

## Option 2c — How to change levels mid-project

Changing modes is a conversation, not a config file. Just tell SweetClaude what you want:

> "Let's dial this up — I want full TDD from here on."
> "We're just exploring right now, let's switch to Flow Mode."
> "We're getting close to production — switch to Agile."

SweetClaude updates your project state and applies the new mode from that point forward. Work already done stays as-is — nothing gets undone or invalidated.

**When switching to a more structured mode**, you may have gaps. If you've been in Flow Mode and want to move to Shape Up or Agile, you won't have a product brief, architecture doc, or decision log yet. SweetClaude will flag what's missing and offer to catch up — either in a dedicated session or as you go. You don't have to fill everything in at once.

**When switching to a lighter mode**, nothing gets removed. Your existing artifacts stay and SweetClaude keeps referencing them. You're just turning off the guardrails for new work — useful when you want to move fast on a known problem without ceremony.

You can also set mode per-task rather than globally: "just do this one thing in Flow Mode" works fine even if your project is otherwise running Agile.
