# How It Works

**Version:** 1.0
**Date:** 2026-05-01

This page is the mental model. It will not teach you any commands. It will explain why SweetClaude is shaped the way it is, so the rest of the docs make sense.

---

## The Core Bet

SweetClaude is built on one bet: AI coding tools generate convincing-looking output much faster than humans can verify it, and the gap between speed and verification is where bad software comes from.

The response cannot be "slow down." Slowing down forfeits the productivity gain that justifies the tool. Instead, the response is *structure* — phases that prevent skipping, hooks that prevent test/implementation drift, separate AI contexts that prevent rationalization, and persistent state that prevents the system from forgetting what it decided yesterday.

Everything else in this document is a consequence of that bet.

---

## Two Kinds of State

Most workflow tools track one thing: what step are you on? SweetClaude tracks two, because they move at different speeds.

**`version_stage`** is where your *project* is in its release lifecycle. It moves slowly. Values: `PROTOTYPE → ALPHA → BETA → GA → SCALED → MAINTAINED`. A v2 rewrite resets it. You declare it; the system never advances it on you.

**`active_work_item`** is the *specific work* in flight right now. It moves fast. A bug fix work item lives for an hour or two. A net-new feature work item might span weeks. Each work item has a type (one of 19), a workflow (a sequence of phases), and a current phase.

Both live in `.sweetclaude/state/phase.yaml`:

```yaml
version_stage: BETA
deference_level: collaborative

active_work_item:
  id: WI-014
  type: net-new-feature
  workflow: [DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP]
  phase: IMPLEMENT
  title: "OAuth login flow"
  started: 2026-04-29
  entry_category: mid-project-planned
```

The two-dimension model matters because it lets the framework do **progressive disclosure**. A PROTOTYPE-stage project does not see compliance work types — those are noise at that stage. A MAINTAINED project gets feature work de-emphasized in favor of operations and security patches. The pipeline you see is appropriate to where the project actually is, not a feature dump.

---

## Phases as Quality Gates

The 7-phase pipeline (DISCOVER → DEFINE → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP) looks like the standard SDLC, but it is not used the standard way.

In a typical SDLC, phases are time-boxed: "we are in design this sprint." In SweetClaude, phases are **quality gates**. A phase is done when its exit criteria are met. Not when the calendar says so. Not when you feel like it.

This is why SweetClaude refuses to give time estimates. The right question is not "how long will design take?" — it is "have we covered the architecture, the data model, the API contracts, and recorded the key decisions?" When the answer is yes, design is done.

There are two kinds of gates. **Soft gates** are advisory — you can override with "I've addressed this informally — proceed." **Hard gates** (⚠️) cannot be soft-bypassed. They apply to high-blast-radius work at GA+ stages: data migration integrity checks, security patch reviews, infrastructure change rollback plans, technology migration cutover decisions. Hard gate overrides require explicit risk acceptance, logged to the decision log.

The list of soft and hard gates is in [`phases-and-workflows.md`](phases-and-workflows.md).

---

## Phase Dwelling

This is the part most workflow tools get wrong, and SweetClaude treats it as load-bearing.

SweetClaude **never pushes you to advance**. It will not say "ready to move on?" or "shall we proceed to the next phase?" or any variant. After presenting work, it sits available for iteration. You decide when a phase is done.

The reason is that iteration is the work. Most strategy and design problems are not solved on the first pass — they are sharpened. The framework that asks "ready to move on?" every five minutes is fighting the user, not helping them.

If you want to advance, you say so. If you want to dwell, you do nothing — SweetClaude waits.

The cost of this is that some users feel adrift, especially in early phases where it is unclear what "done" looks like. The mitigation is the [phase gates reference](phases-and-workflows.md): each phase has explicit exit criteria. When the criteria are met, you know.

---

## Workflow Shapes

A bug fix does not need discovery. A data migration does not need user stories. SweetClaude has six workflow shapes that cover all 19 work types:

| Shape | Phases | Used for |
|---|---|---|
| `full-pipeline` | DISCOVER → DEFINE → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP | Net-new features, external integrations |
| `abbreviated` | DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP | Enhancements, infrastructure changes |
| `extended-abbreviated` | ASSESS → DEFINE → DESIGN → IMPLEMENT → VERIFY → SHIP | Compliance work |
| `diagnostic` | DIAGNOSE → IMPLEMENT → VERIFY → SHIP | Bug fixes, security patches, performance |
| `migration` | ASSESS → DESIGN → PLAN → IMPLEMENT → VERIFY → CUTOVER → CLEANUP | Tech migrations, API deprecations |
| `compressed` | DIAGNOSE → IMPLEMENT → SHIP → POST-MORTEM | Hotfixes |

The work type determines the shape. You do not pick. When you describe the work to `/sweetclaude:find-skill` ("there is a bug in the auth flow"), the framework classifies it (`bug-fix`), reads the shape from config (`diagnostic`), and starts at DIAGNOSE. The diagnostic shape exists because you cannot fix what you cannot reproduce.

---

## TDD by Hook, Not by Prompt

Most TDD documentation is advisory: "write the test first." SweetClaude does not believe in advisory TDD because advisory TDD fails. The implementer (human or AI) ends up touching the test to make it pass, or writes the test after the code so the test rationalizes the implementation rather than specifying behavior.

SweetClaude substantially raises the cost of this at higher levels:

- **Test-guardian hook** (PreToolUse) blocks edits to test files during the IMPLEMENT phase. Not "warns" — blocks.
- **Auto-test-runner hook** (PostToolUse) runs tests automatically after every source edit. Not "reminds" — runs.
- **Subagent isolation** at TDD Level 2-3 means the test writer and implementer are different agents in different contexts. The implementer never sees the spec or the test writer's reasoning. Only the tests.

This sounds extreme until you watch what happens without it: a test passes, you ship, and three weeks later production breaks because the test was passing for the wrong reason. The hooks remove that failure mode.

The four TDD levels (0 through 3) calibrate the discipline to the work. A hotfix does not get the full pipeline. A net-new feature with Gherkin specs does. See [tdd.md](tdd.md) for the full breakdown.

---

## Why Subagents Are Isolated

When the test writer agent reads the user story, writes failing tests, and the implementer reads only those tests, the implementer cannot rationalize a poor test by reasoning about what the spec "really meant." It has to make the tests pass with code, not with arguments.

This is the same principle that produced double-blind clinical trials. Information that flows backward from outcome to design corrupts the design. SweetClaude prevents the flow.

---

## Deference Levels

Three levels: collaborative, guided, autonomous.

The honest framing: **deference levels are about how much you trust the framework today**, not about how complex the work is. Your first session should be collaborative because you are still building a model of what SweetClaude does. Your tenth feature in the same project might be autonomous because you have seen the rhythm and you are tired of confirming sub-steps.

Autonomous does not mean unsupervised. The framework still pauses at phase gates. It still respects hard gates. It still saves state. It just stops asking "okay to proceed?" between every micro-step.

The level is changeable mid-session by saying "switch to guided" or "go autonomous." SweetClaude immediately respects the change and updates `.sweetclaude/state/phase.yaml`.

---

## Persistence Across Sessions

Claude Code sessions die. Context windows fill. Networks drop. SweetClaude is designed to survive this.

The structured state files in `.sweetclaude/state/` are the source of truth — not conversation history. Skills re-read state files at every step rather than relying on what was said earlier. Decisions go to `decision-log.md`. Assumptions go to `assumption-register.md`. Scope changes go to `scope-changes.md`. Improvement feedback goes to `improvement-register.md`.

When you resume a session, `/sweetclaude:go` reads state and re-orients. You do not have to remember what you were doing.

This is also why `.sweetclaude/` is committed to git. The state is project history, not scratch. If you switch machines or someone else picks up the work, the context travels with the repo.

---

## What Lives Where

```
~/.claude/                          ← Global SweetClaude install
├── skills/sweetclaude/             ← 52 skills
├── agents/sweetclaude/             ← 8 isolated subagents
├── hooks/sweetclaude/              ← TDD enforcement hooks
├── rules/sweetclaude/              ← Phase gates, TDD levels, interaction model
└── config/sweetclaude/             ← Phase-skill mapping, workflow templates

your-project/.sweetclaude/          ← Per-project state
├── state/
│   ├── phase.yaml                  ← Two-dimension state
│   ├── project.yaml                ← Language, framework, commands
│   ├── decision-log.md
│   ├── assumption-register.md
│   ├── improvement-register.md
│   └── scope-changes.md
├── traceability/                   ← Story → requirement → test → code
└── version-bump.yaml               ← Optional: auto-bump on commit
```

The split is intentional. Global install is the framework. Per-project state is your work. They are committed separately. The framework can update without disturbing your project history.

---

## What SweetClaude Will Not Do

This is the part most documentation skips. SweetClaude has explicit non-goals:

**It will not give time estimates.** AI-assisted solo development does not run on calendar time. If you ask "how long will this take?", SweetClaude redirects: "I'm your implementation partner — I build with you at AI speed, not calendar speed. Let's focus on what needs to be done."

**It will not push you forward.** Phase advancement is the user's call. Always.

**It will not modify tests during implementation.** Hooks block this physically.

**It will not silently skip steps in the corpus pipeline.** The state machine refuses out-of-order operations and explains why if you try.

**It will not assume your stack.** Codebase discovery drives all configuration. Templates, not constants. SweetClaude works on Python, Go, TypeScript, Rust, or anything else because the workflow is the product.

**It will not replace Superpowers.** SweetClaude orchestrates Superpowers (when present); it does not fork or override it. Plans, worktrees, parallel agents, systematic debugging — those are Superpowers skills SweetClaude calls into.

---

## Enforcement Tiers

Not all behavioral properties in SweetClaude are guaranteed equally. Some are enforced deterministically — hooks that fire regardless of what the model does. Others are instruction-guided — rules that Claude is directed to follow, but which are probabilistic by nature.

This distinction matters because deterministic properties are version-stable (a hook doesn't degrade when the underlying model changes) and instruction-guided properties are not.

**Deterministic (hook-enforced):**

| Property | Mechanism | What it guarantees |
|---|---|---|
| Test files cannot be edited during IMPLEMENT | `test-guardian.sh` (PreToolUse) | Edits to test directories are blocked at the tool call level |
| Tests run after every source edit | `auto-test-runner.sh` (PostToolUse) | Test suite runs without requiring the user to trigger it |
| TDD Level 2-3 context isolation | Subagent architecture | Implementer agent never receives the spec or test writer's reasoning |
| Phase advancement phrases removed from responses | `phase-dwelling-guard.sh` (Stop hook) | When Protocol Guardian is active, responses containing "ready to move on?" are blocked before reaching the user |

**Instruction-guided (probabilistic):**

| Property | Mechanism | What it means |
|---|---|---|
| Phase dwelling — never asks "ready to move on?" | `interaction-model.md` rule | Claude is directed to dwell; Protocol Guardian enforces it when active |
| Deference level respect | `interaction-model.md` rule | Claude adjusts how frequently it stops based on the configured level |
| Improvement register capture triggers | `interaction-model.md` rule | Claude is directed to capture feedback at defined trigger points |
| Propose-not-ask interaction mode | `interaction-model.md` rule | Claude defaults to making proposals with reasoning rather than asking open-ended questions |
| Adaptive language matching | `interaction-model.md` rule | Claude matches the user's vocabulary and domain language |

The practical implication: instruction-guided properties are the right implementation choice for behavioral nuance that cannot be mechanically verified. They work well most of the time and degrade gracefully. Deterministic properties are the right choice for correctness guarantees that the framework's value depends on. If a property is described as "load-bearing" in this document and it is instruction-guided, enabling the Protocol Guardian (`/sweetclaude:guardian-on`) upgrades it to deterministic enforcement for that session.

---

## What to Read Next

- Concrete walkthroughs of specific scenarios → [Walkthroughs](walkthroughs.md)
- Reference for all phases and work types → [Phases and Workflows](phases-and-workflows.md)
- Reference for all skills → [Skills Reference](skills-reference.md)
- Honest tradeoffs and when not to use → [FAQ](faq.md)
