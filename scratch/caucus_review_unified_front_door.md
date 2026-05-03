# Caucus Review: /sweetclaude Unified Front Door Design
**Date:** 2026-05-03
**Proctor:** SweetClaude Framework
**Topic:** Review the proposed `/sweetclaude` unified front door — schema, decision tree, skill consolidations, and feature offer loop
**Turns:** 3
**Committee:** 5 SweetClaude users + 5 Claude Skill 2.0 developers

---

## The Design Under Review

### What's proposed

**Two visible skills (down from 73+):**
- `/sweetclaude [optional: natural language]` — everything
- `/sweetclaude:help` — progressive onboarding chat

**Consolidated internals:**
- `on` + `adopt` → `sweetclaude:setup` (3 branches: new / clean existing / messy inherited)
- `go`, `find-skill`, `next-steps`, `status` → absorbed into `/sweetclaude` routing
- `phase.yaml` + `skills.yaml` → single `sweetclaude.yaml`

### `sweetclaude.yaml` schema
```yaml
schema_version: 1
project:
  name: sweetclaude
  type: existing-code
  version_stage: BETA
  safety_snapshot: pre-sweetclaude
framework:
  installed_version: '2.40.0'
  setup_complete: true
  migrated_at: '2026-05-03T19:00:00Z'
  migrated_from: '2.40.0'
  consistency:
    last_checked: '2026-05-03T19:00:00Z'
    status: ok
    drift: []
  update:
    available: null
    last_checked: '2026-05-03T19:00:00Z'
    declined: false
session:
  deference_level: collaborative
work:
  last_item_id: null
  active:
    id: null
    type: null
    workflow: []
    phase: null
    title: null
    started: null
    entry_category: null
features:
  product_milestones:    { status: active,      offered_at: '2026-05-01', decided_at: '2026-05-01' }
  product_backlog:       { status: active,      offered_at: '2026-05-01', decided_at: '2026-05-01' }
  product_personas:      { status: not_offered, offered_at: null,         decided_at: null }
  product_stories:       { status: not_offered, offered_at: null,         decided_at: null }
  document_corpus:       { status: not_offered, offered_at: null,         decided_at: null }
  usage_tracking:        { status: not_offered, offered_at: null,         decided_at: null }
  behavioral_regression: { status: not_offered, offered_at: null,         decided_at: null }
health:
  last_checked: '2026-05-03T19:00:00Z'
  artifacts:
    milestones:  ok
    backlog:     ok
    personas:    missing
    stories:     missing
    corpus:      not_configured
work_history:               # rolling 20, oldest dropped
  - { id: BL-047, title: "Hide internal skills from slash command picker", type: enhancement, completed_at: '2026-05-03', outcome: shipped }
learnings:                  # top 15, full audit in improvement-register.jsonl
  - "After editing framework files, copy to ~/.claude/ to keep both in sync"
  - "Push to origin main immediately after every commit"
```

### Decision tree
```
READ sweetclaude.yaml  (one read, always)

sweetclaude.yaml missing?
  + old state files present  →  MIGRATION: consolidate → write → archive
  + no state files            →  sweetclaude:setup (new project)

setup_complete = false?  →  sweetclaude:setup (new / clean / messy branch)

now - consistency.last_checked > 24h?  →  scan + write status + drift + timestamp
now - update.last_checked > 24h?       →  check remote + write available + timestamp

consistency.status = drift_detected?   →  offer fix
update.available AND NOT declined?     →  offer update

args present?
  incident / broken     →  sweetclaude:something-broke
  status / where are we →  surface from file (no extra reads)
  help / how do I       →  sweetclaude:help
  work description      →  sweetclaude:find-skill $ARGUMENTS

no args — feature offer loop (one per session):
  product_milestones → product_backlog → product_personas →
  product_stories → document_corpus → usage_tracking → behavioral_regression
  first not_offered → offer it

all clear:
  show project · version_stage · active work · what's next
  ask: "Work on something, or review the plan?"
```

---

## Committee Profiles

### Users

**Amara Osei** — Solo founder, non-technical. Uses SweetClaude via a contractor who set it up; she runs it herself day-to-day to manage product pipeline. Has no interest in framework internals.
*Bias:* "Just make it work without me thinking about it." Deeply uncomfortable when tools surface technical state she doesn't understand. Prioritizes zero cognitive load over any capability.
*Blind spot:* Assumes all users want the same invisible experience she does. Underweights the needs of people who want to understand what's happening.

**Tom Hargreaves** — Senior full-stack engineer, 15 years. Uses Claude Code as a pair programmer, treats SweetClaude as a structured co-pilot. Has opinions about everything.
*Bias:* "Show me what you're doing and why." Suspicious of any "magic" routing that obscures which skill fired and why. Will debug his way to the truth regardless.
*Blind spot:* Assumes all users are power users. His tolerance for complexity is far above average.

**Priya Malhotra** — Product manager at a 20-person startup. Uses SweetClaude for discovery, PRDs, and sprint planning. Not a developer. Relies on guided workflows to not miss steps.
*Bias:* Structured process over speed. Gets anxious when tools skip steps silently. Needs confidence that the offer loop will surface the right features in the right order.
*Blind spot:* Doesn't appreciate that developers find guided workflows patronizing. Over-indexes on completeness, under-indexes on flow.

**Marcus Webb** — Indie developer, 3 active SweetClaude projects, daily user for 6 months. Has every skill name memorized. Considered writing his own fork.
*Bias:* "I know exactly what I want and I want to say it in two words." Resents any UX that treats him like a beginner. Will bypass the front door if he can find a way to.
*Blind spot:* He's in the 5%. Most users haven't memorized skill names and never will. His ideal UX is unusable for the other 95%.

**Zoe Chen** — Junior developer, 1 year experience, first AI workflow tool. Discovered SweetClaude via a YouTube tutorial. Has never typed a skill name directly.
*Bias:* Loves guided UX. Terrified of doing the wrong thing. Will read every word of the help text. The proposed design was clearly designed for her.
*Blind spot:* Doesn't anticipate edge cases. Won't notice missing power-user affordances until she's no longer a junior.

---

### Developers

**Dr. Raj Patel** — Framework architect who contributed to the Claude Code skill system spec. Believes in composability above all else.
*Bias:* "Skills should be small, single-purpose, composable units." The moment `/sweetclaude` starts doing six things, it's a god-skill and a maintenance nightmare. Will push hard for thin orchestration and delegation to focused sub-skills.
*Blind spot:* Sometimes architectural purity produces more files and complexity than the "messy" monolith it replaced. A 500-line orchestrator that works is better than 20 perfectly composed skills that nobody can follow.

**Yuki Tanaka** — Developer experience engineer, wrote the Claude Code hooks documentation. Expert in the hook lifecycle and its limits.
*Bias:* "The hook layer is the right place for automation." Thinks several things in this design belong in hooks rather than skill logic. Will note that the 24h check should be a SessionStart hook, not inline skill logic.
*Blind spot:* Hooks have real limitations — they can't inspect message content, can't invoke skills, can't produce user-facing output in the conversation. Sometimes the skill layer is the only option.

**Fatima Al-Hassan** — Reliability engineer, has seen Claude skills fail in production at scale. Thinks in failure modes.
*Bias:* "What happens when this breaks?" Will stress-test every assumption: corrupted YAML, network unavailable for version check, migration that runs twice, race condition between hook write and skill read.
*Blind spot:* Production reliability concerns can paralyze design. Not every failure mode needs a designed recovery path — some can just fail loudly.

**Ben Kowalski** — Performance engineer. Counts tokens. Has profiled dozens of skill files and knows exactly how context window cost scales with skill size.
*Bias:* "The skill file is loaded into every relevant context. Every line costs tokens." Will challenge anything that makes the skill file larger without proportional user value. The decision tree, the schema, the migration logic — all of it is token cost.
*Blind spot:* Token cost is real but not always the binding constraint. A skill that saves users 20 minutes of confusion is worth 500 extra tokens per invocation.

**Sasha Oduya** — Product owner for the Claude Skill ecosystem. Thinks in roadmaps and upgrade paths.
*Bias:* "Schema version 1 becomes schema version 2 in six months." Will push for extensibility in `sweetclaude.yaml` — versioning, unknown-field tolerance, migration hooks for future schema changes. Worried this design paints itself into a corner.
*Blind spot:* Over-engineering for version 3 sometimes prevents shipping version 1. Future-proofing has carrying costs.

---

## Turn 1: First Reactions

**Proctor's question:** Read the full design. What's your strongest reaction — positive or negative? What's the most important thing the committee should examine in this review?

---

### Amara Osei

I've been waiting for this since the day I started using SweetClaude.

The thing that made me nervous about SweetClaude when I first saw it was the list of slash commands. There were so many. My contractor set it up and showed me maybe five commands I'd actually use, but every time I opened the picker I felt like I was doing it wrong because I didn't know what half of them meant.

Two visible skills. That's it. I would have started using SweetClaude six months earlier if this had existed.

My one concern: the feature offer loop. "One offer per session max" — I love this rule. What I need to know is: what does the offer *look like*? Is it technical? "You haven't initialized product_personas" means nothing to me. If it says "Want me to help you define who your users are?" I say yes immediately. The language of the offer matters as much as the logic.

What I want the committee to examine: the user-facing copy of every offer in that loop. Not the schema field names — the actual words.

---

### Tom Hargreaves

The design is directionally right and I'll support it. But I want to register one concern loudly before it gets buried: **what happens when the natural language classifier routes wrong?**

I type `/sweetclaude let's refactor the auth middleware` and it routes to `sweetclaude:code-debt` because "refactor" is a debt signal. But I actually wanted `sweetclaude:code-feature` because I'm replacing it, not cleaning it up. The skill fires, I'm in the wrong workflow, and now I'm spending three minutes backing out of something I didn't intend to start.

The design doesn't address misclassification recovery. There's no "that's not what I meant" path. In the current system, if I know I want `code-feature`, I type it and it's unambiguous. In this system, I describe my intent and hope the classifier agrees with me.

I want the committee to examine: **what's the misclassification recovery path?** And is there a way for power users to be explicit about routing without losing the natural language option?

---

### Priya Malhotra

The feature offer loop is the heart of this design and I want to examine the ordering carefully.

The proposed order is: product_milestones → product_backlog → product_personas → product_stories → document_corpus → usage_tracking → behavioral_regression.

I understand the dependency logic (you need milestones before backlog, backlog before personas, etc.). But I'm worried about users getting stuck at a "not_offered" feature they're not ready for yet. If I decline product_personas today because I'm not ready to define my users yet, the loop skips to document_corpus next session. But document_corpus requires personas to be useful. The offer loop doesn't know I declined because I wasn't ready — it treats "not ready" the same as "not interested."

There's a difference between `declined` and `not_yet`. The schema only has `not_offered | offered | active | declined`. I'd want `deferred` — "offer me again in a few sessions."

The committee should examine: **is the feature registry's four-state model sufficient?**

---

### Marcus Webb

I'll be the contrarian voice.

The design solves a real problem — the picker was overwhelming for new users. But it creates a new problem for users like me: **I can no longer be precise.**

Right now I type `/sweetclaude:code-feature` and I know exactly what's about to happen. In the new world, I type `/sweetclaude build a new feature for user authentication` and I'm trusting a classifier to get it right. Sometimes I don't want to describe my work — I just want to invoke the right tool.

I'm not asking for the old picker back. I'm asking: is there an advanced mode, a power user mode, or even just a documented way to be explicit? Something like `/sweetclaude --skill code-feature` or even just telling the skill "use code-feature workflow" in the text. If the skill can interpret natural language, it can interpret "use X workflow" as an explicit override.

My ask for the committee: **design the explicit override path alongside the natural language path.** Don't make me file a support ticket when the classifier misroutes me.

---

### Zoe Chen

I love this design. But I want to make sure I'm not missing something obvious as a new user.

When I type `/sweetclaude` for the first time on a new project, the decision tree says it routes to `sweetclaude:setup`. What does that experience actually look like? Does it ask me questions? Does it tell me what it's doing? How long does it take?

I'm also curious about the `learnings` section. It says SweetClaude applies learnings from previous sessions. What kind of learnings? If I make a mistake early on and SweetClaude "learns" something wrong about how I work, does it keep applying that wrong thing forever? Can I see the learnings? Can I delete one?

For the committee: **the first-run experience needs more definition.** The schema has `setup_complete: false` as a signal, but what the user actually sees during setup isn't specified in this design.

---

### Dr. Raj Patel

The design has a structural problem I want to name clearly: **`/sweetclaude` is doing too many things.**

Read the decision tree. It bootstraps, migrates, runs health checks, checks for updates, offers features, classifies natural language, routes to sub-skills, AND surfaces status. That's six distinct responsibilities in one skill. By the time this is implemented, the skill file will be 800+ lines and impossible to maintain.

The right architecture is thin orchestration: `/sweetclaude` reads the file, makes one decision, and delegates to a focused sub-skill. The sub-skill owns its domain. Right now the design has the migration logic, the health check logic, the offer loop logic, and the routing logic all living inline.

I want the committee to examine: **where are the sub-skill boundaries?** What should be delegated and what should stay in the orchestrator?

---

### Yuki Tanaka

Raj is right about complexity, and I want to add a specific point: **the 24-hour checks belong in the hook layer, not the skill layer.**

The consistency check and the version check are periodic background operations. They should fire at `SessionStart` — before the user even types `/sweetclaude` — and write their results to `sweetclaude.yaml`. Then when `/sweetclaude` runs, it just reads the cached result. The skill file doesn't need check logic at all.

This is exactly what hooks are for. The `session-preflight.sh` hook already runs at session start. Extend it. Don't put time-comparison logic in a skill that fires on every invocation.

The token cost argument alone makes this worth doing: every invocation of `/sweetclaude` currently has to run the 24h timestamp comparison. That's inline logic in the skill file. Move it to the hook and the skill gets simpler, cheaper, and faster.

For the committee: **the 24h check logic should move to SessionStart hook.** The skill should only read results, not run checks.

---

### Fatima Al-Hassan

I have three failure modes I want the committee to examine.

**1. Corrupted `sweetclaude.yaml`.** The single-file design means one corruption event takes down everything. Currently, if `phase.yaml` corrupts, `skills.yaml` still works. Now there's one file. What does the skill do if the YAML fails to parse? The decision tree has no error branch.

**2. Migration that runs twice.** The migration triggers when `sweetclaude.yaml` is missing and old state files are present. What if the migration writes `sweetclaude.yaml` but fails halfway? Next invocation: old files still present, `sweetclaude.yaml` exists but is incomplete. Does it re-migrate? Does it detect partial writes? The design doesn't say.

**3. Network unavailable during version check.** The version check hits a remote endpoint every 24 hours. What if there's no network? Does it fail silently and skip? Does it set `update.available = error`? Does it retry? The design doesn't specify.

These aren't edge cases — they're common scenarios. Every laptop goes offline. Every YAML gets hand-edited by an impatient developer.

For the committee: **the error handling model needs to be specified.** Not just the happy path.

---

### Ben Kowalski

I'm going to put a number on the token cost of this design.

The proposed `sweetclaude.yaml` schema as written is approximately 40 lines. At session start, the `!` shell command reads it and injects it into the skill context — call it 600 tokens. The decision tree logic in the skill file itself — the migration check, the 24h comparisons, the feature offer loop, the NL classifier instructions — will be another 400-600 tokens easily. Total: ~1,000-1,200 tokens **per invocation** of `/sweetclaude`.

Compare that to the current `go` skill which reads session state (~200 tokens) and has a routing table (~300 tokens). We're looking at a 2-3x token cost increase for the most-invoked skill in the framework.

This isn't a dealbreaker. But it means we need to be disciplined: every line in the skill and every field in the schema should earn its token cost. The `work_history` section (20 items × ~5 fields = 100+ tokens) is suspect. The `learnings` section (15 entries × ~1 line = 30 tokens) is probably fine.

For the committee: **`work_history` in the schema needs to justify its token cost.** Does the skill actually use work_history to make better decisions, or is it just nice to have?

---

### Sasha Oduya

The schema says `schema_version: 1`. That's the right instinct. But I want to see the migration story for `schema_version: 2`.

In six months, someone adds a new feature to the `features` registry. Or the `work` section needs a new field for a new work type. Or the `health` section gains new artifact types. Every one of these changes requires either a schema version bump with migration logic, or tolerating unknown fields.

The current design doesn't specify:
- How an old `sweetclaude.yaml` (schema v1) is detected by a skill expecting schema v2
- Whether unknown fields are tolerated or cause errors
- Where the migration-between-schema-versions logic lives

The migration FROM `phase.yaml`/`skills.yaml` TO `sweetclaude.yaml` is designed. The migration FROM `sweetclaude.yaml v1` TO `sweetclaude.yaml v2` is not.

For the committee: **`sweetclaude.yaml` needs a forward migration story before v1 ships.** Not the full implementation — just the pattern. Otherwise v2 will be a crisis.

---

### Proctor Synthesis — Turn 1

**What emerged:**

Ten panelists, ten distinct concerns. They cluster into five tension areas:

| Tension | Raised by | Stakes |
|---------|-----------|--------|
| **Natural language misclassification** | Tom, Marcus | Users can end up in wrong workflows with no recovery path |
| **God-skill / complexity** | Raj, Ben | `/sweetclaude` owns too many responsibilities; token cost is real |
| **Hook vs skill layer** | Yuki | 24h checks belong in SessionStart hook, not inline logic |
| **Error handling gaps** | Fatima | Corrupted file, partial migration, no network — all unaddressed |
| **Schema evolution** | Sasha, Priya | Four-state feature registry is insufficient; v2 migration unspecified |

**Strong positives:** Amara, Zoe, and Priya all validated the core direction. The two-skill visible menu and natural language routing solve the right problem. No one argued the design is directionally wrong.

**Open questions entering Turn 2:**
1. What is the misclassification recovery path? Can power users be explicit?
2. Should the 24h checks move to the SessionStart hook?
3. Should `features` have a fifth state: `deferred`?
4. What's the error handling model for corrupted file / partial migration / no network?
5. Does `work_history` earn its token cost in the schema?

---

## Turn 2: Deep Dive on Key Tensions

**Proctor's question:** Focus on the five tensions. Where do you stand? Which concerns are blockers vs. acceptable risks? And where is there genuine disagreement worth resolving now?

---

### Amara Osei

On misclassification: I want to push back gently on Tom and Marcus's concern. As a non-technical user, I get misrouted all the time — by every tool I use. What matters is not that misrouting never happens but that recovery is easy. If SweetClaude starts the wrong workflow and I say "wait, that's not what I wanted," does it stop and ask what I meant? That's all I need.

On the feature offer language: I want to keep pressing this. Raj is talking about sub-skill boundaries and Yuki is talking about hooks. That's the right conversation for developers. For users, what matters is: when the offer fires, does it sound like a human or a system? "product_personas has status not_offered" is a system. "Want to spend 20 minutes defining who your users are? It'll make everything that comes after sharper." That's a human. The schema design is invisible to me — the copy is not.

---

### Tom Hargreaves

On the recovery path: I've thought about this more and Marcus is right that the solution is an explicit override, not just better recovery after misrouting. If the user can say `/sweetclaude use code-feature` and the skill recognizes "use [skill-name]" as an explicit routing instruction, we get the best of both worlds: natural language for new users, explicit routing for power users. The classifier just needs one extra pattern: if the message starts with "use [known-workflow-name]", bypass classification and route directly.

On the hook vs skill layer debate: Yuki is right in principle but I want to see evidence it's worth the architectural split. If moving the 24h checks to a hook saves 200 tokens per invocation and removes check logic from the skill file, that's a clean win. If it requires a complex hook-to-skill communication protocol that's hard to maintain, the token savings don't justify it.

---

### Priya Malhotra

I want to go deeper on the `deferred` state.

Here's the scenario: I'm three weeks into a project. SweetClaude offers me product_personas. I know I need to define personas eventually, but right now I'm in the middle of a sprint and I don't want to stop. "Decline" means never offer again. "Accept" means we stop what I'm doing and start a personas session. Neither is right. I want "ask me again next week."

`deferred` doesn't have to be calendar-based. It could be invocation-count-based: "offer this again after N more invocations." Or it could be event-based: "offer when active work item is complete." The simplest version is just a `deferred_until_invocation: 10` field that the offer loop checks before surfacing.

On the god-skill concern: I agree with Raj that the skill shouldn't own migration logic inline. But I disagree that this is a priority-1 issue. Ship the working monolith, extract sub-skills in v1.1. The user experience is the priority.

---

### Marcus Webb

Tom's "use [skill-name]" explicit override is exactly what I was asking for and it's elegant. I want to add one more pattern: if I type `/sweetclaude --raw` or `/sweetclaude --advanced`, it drops into a mode that shows me the skill list and lets me pick directly. Not the full 73-skill picker — just the top 20 most-used skills for my project (derivable from work_history and feature statuses). Power user mode, accessible on demand.

On work_history token cost: Ben is right to scrutinize it. But I'll defend it from the user side. The single most useful thing SweetClaude can do at the start of a session is tell me "last time you were working on X, you left off at Y." That context is worth the tokens. The question is whether 20 items is the right number. I'd say 10 is sufficient for day-to-day, 20 is overkill.

---

### Zoe Chen

I want to add one thing to Amara's point about offer language: the offer should tell me WHY before asking if I want to do it. Not just "Want to define your users?" but "Knowing who your users are makes every product decision easier. Want to spend 20 minutes setting that up?" The why is motivating. Without it, the offer feels like a bureaucratic checkbox.

On error handling: Fatima's concern about corrupted YAML is real for me too. I've accidentally broken config files before just by copying text into the wrong place. If SweetClaude breaks because I edited the wrong file, I'll think I broke something serious and abandon the session. The error message needs to be: "Looks like sweetclaude.yaml got scrambled. Here's how to fix it in 30 seconds." Not a stack trace.

---

### Dr. Raj Patel

I want to respond to Priya's "ship the monolith" argument directly.

The problem isn't aesthetic. It's operational. When `/sweetclaude` is 800 lines of inline logic, debugging a misclassification means reading 800 lines. Extending the feature offer loop means touching the same file that owns the migration logic. A bug in the migration path can corrupt the routing logic. These are real maintenance costs that compound over time.

My proposed sub-skill boundaries — and I'll commit to a specific proposal now:

1. `sweetclaude:_migrate` — runs once, triggered by orchestrator when yaml is missing
2. `sweetclaude:_health` — runs the consistency + update checks, writes results
3. `sweetclaude:_offer` — manages the feature offer loop
4. `sweetclaude:_route` — classifies natural language and delegates to the right skill
5. `/sweetclaude` — reads the file, runs pre-checks, delegates to the above

The orchestrator stays thin. Each sub-skill is under 200 lines. Underscored naming signals internal-only. This isn't over-engineering — it's the same pattern as any well-structured codebase.

---

### Yuki Tanaka

I want to make a concrete case for the hook migration.

The current `session-preflight.sh` hook already runs at session start and writes to `session-state.yaml`. The change is minimal: add two checks to the script.

```bash
# In session-preflight.sh, add:
last_consistency=$(yq '.framework.consistency.last_checked' sweetclaude.yaml)
if [[ $(hours_since $last_consistency) -gt 24 ]]; then
  run_consistency_check
  yq -i '.framework.consistency = ...' sweetclaude.yaml
fi

last_update=$(yq '.framework.update.last_checked' sweetclaude.yaml)
if [[ $(hours_since $last_update) -gt 24 ]]; then
  check_remote_version
  yq -i '.framework.update = ...' sweetclaude.yaml
fi
```

The skill file then has zero time-comparison logic. It reads `consistency.status` and `update.available` and acts on the cached results. Cleaner skill, no token cost for check logic, checks run before the user even types anything.

The one limitation: if the session starts and the hook runs but the checks fail silently, the skill has no way to know they failed. We need a `consistency.check_error` field in the schema to handle this.

---

### Fatima Al-Hassan

I want to propose a minimal error handling model that covers the three failure modes without over-engineering.

**Corrupted `sweetclaude.yaml`:** The skill tries to parse the file. On parse failure, it does not crash — it routes to `sweetclaude:fix-sweetclaude` with a clear message. `fix-sweetclaude` already exists and handles configuration repair. We just need to ensure it handles YAML parse failures specifically.

**Partial migration:** Add a `migration_status` field to the schema:
```yaml
framework:
  migration_status: complete  # in_progress | complete | failed
```
If the migration writes this field last, a partial write leaves it as `in_progress`. Next invocation detects `in_progress` and re-runs migration from scratch. Safe because migration is idempotent if we archive (not delete) old files.

**No network for version check:** The hook (per Yuki's proposal) catches the error and writes:
```yaml
update:
  available: null
  last_checked: '2026-05-03T19:00:00Z'
  check_error: "network_unavailable"
```
The skill reads `check_error`, skips the offer, and tries again next session. Silent, graceful.

Three failure modes, three targeted fixes. None require a major architectural change.

---

### Ben Kowalski

Marcus convinced me on `work_history`. The day-start context ("last time you worked on X") is worth the tokens. I'm changing my ask: cap it at 10 items, not 20. The tail items (items 11-20) are rarely relevant — most users work on one project continuously and the last 3 sessions are all that matter for context. 10 items at ~5 fields each = ~50 tokens. Acceptable.

On Raj's sub-skill proposal: I support it on token-cost grounds. Each sub-skill is only loaded when needed. If the migration sub-skill is only invoked once per installation, its token cost is effectively zero amortized. If the health sub-skill only runs once per 24 hours (via the hook), its cost is similarly amortized. The orchestrator stays lean.

One specific ask: the `learnings` section. 15 entries at ~80 chars each ≈ 300 tokens. Is this used by `/sweetclaude` itself, or only by `sweetclaude:master`/`go`? If only the latter, it shouldn't be in the file that `/sweetclaude` reads every invocation. Move it to a separate section that's only loaded by the skills that need it.

---

### Sasha Oduya

I want to propose the forward migration pattern before we lose the thread.

The pattern is dead simple: add a `schema_version` check at the top of every skill that reads `sweetclaude.yaml`. If the version doesn't match what the skill expects, route to a migration sub-skill before proceeding. The migration sub-skill knows how to upgrade v1 → v2 (and eventually v2 → v3).

```yaml
# In /sweetclaude decision tree, before everything else:
if schema_version != expected_version:
  → sweetclaude:_migrate --schema-upgrade
```

For unknown fields: YAML parsers ignore unknown fields by default. We don't need to do anything special — new fields added in v2 are simply invisible to v1 skills. Old fields removed in v2 are handled by the migration. This is the standard YAML schema evolution pattern.

On Priya's `deferred` state: strongly agree. Four states is insufficient. My version: `not_offered | offered | active | declined | deferred`. Add a `defer_until` timestamp field. The offer loop skips features where `now < defer_until`. Simple, powerful, doesn't require event-based logic.

---

### Proctor Synthesis — Turn 2

**What changed:**

| Issue | T1 Status | T2 Resolution |
|-------|-----------|---------------|
| Misclassification recovery | Open | **Resolved:** "use [skill-name]" explicit override + `--advanced` power user mode |
| 24h checks in skill vs hook | Open | **Consensus: move to SessionStart hook.** Yuki's concrete proposal endorsed by Tom, Ben. |
| `deferred` feature state | Priya raised | **Consensus:** Add 5th state. Sasha's `defer_until` timestamp is the cleanest implementation. |
| Error handling model | Fatima raised | **Consensus:** Fatima's three targeted fixes cover the space. `migration_status` field added. |
| Sub-skill architecture | Raj raised | **Near-consensus:** 5 sub-skills proposed. Ben endorses on token-cost grounds. Priya defers ("ship first, extract later"). |
| `work_history` token cost | Ben raised | **Resolved:** Cap at 10 items (not 20). Marcus agreed. |
| `learnings` in /sweetclaude | Ben raised | **Open:** Should learnings move to a sub-section not loaded by `/sweetclaude`? |
| Forward migration story | Sasha raised | **Resolved:** schema_version check at top of skill → route to `_migrate` if mismatch. |

**One unresolved item entering Turn 3:** Should `learnings` be inline in `sweetclaude.yaml` (loaded on every `/sweetclaude` invocation) or in a separate section only loaded by skills that apply learnings?

---

## Turn 3: Final Verdicts

**Proctor's question:** Lock your positions. What changes to the design are mandatory before implementation? What's acceptable as future work? Register any remaining dissents.

---

### Amara Osei

My mandatory asks are user-facing and I'll be brief:

1. **Offer copy must be human-language.** Schema field names never appear in user-facing output. Every offer is a sentence that explains why the feature matters before asking if they want it.

2. **Error messages must be actionable.** "sweetclaude.yaml parse error" → "Something got corrupted. Type `/sweetclaude:help` and I'll walk you through fixing it in 30 seconds."

3. **Setup experience must be described.** The design specifies the trigger (`setup_complete = false`) but not the experience. Even a paragraph.

Everything else — hooks, sub-skills, token counts — I'll trust the developers on.

---

### Tom Hargreaves

**Mandatory:** The explicit override path. `/sweetclaude use code-feature` or `/sweetclaude --skill code-feature` bypasses the classifier and routes directly. This is the safety valve that makes the natural language classifier acceptable to power users.

**Acceptable future work:** The `--advanced` mode Marcus proposed (show top-N skill list). Useful but not critical for v1.

**My dissent on moving checks to hooks:** I'm not blocking it, but I want it documented clearly that if the hook fails silently, the skill needs a fallback. "Checks ran at hook time" can't be an invisible assumption — the skill file should note explicitly that it trusts hook-written results.

---

### Priya Malhotra

**Mandatory:** `deferred` as a fifth feature state with `defer_until` timestamp. Without it, users who aren't ready for a feature are permanently opted out the moment they decline. This is a user experience defect, not a nice-to-have.

**Mandatory:** The offer loop needs a "not yet" option that defers for a reasonable default period (I'd say 5 sessions / ~1 week of typical use).

**Acceptable future work:** Fine-grained deferral control (user-set duration). V1 can use a fixed default.

---

### Marcus Webb

**Mandatory:** Explicit routing override. Tom said it, I agree.

**Strongly recommended but not blocking:** `--advanced` mode. I'll live without it in v1 if the override exists.

**A new ask I haven't raised yet:** The decision tree's "all clear" path shows status and asks "work on something or review the plan?" — this should remember my last answer. If I always say "work on something," stop asking. Track `session.default_action` in the schema and skip the question after 3 consecutive same answers.

---

### Zoe Chen

**Mandatory:** First-run experience described. Even bullet points. "When you first run `/sweetclaude` on a new project, here's what happens step by step."

**Mandatory:** `learnings` must be visible and editable by the user. Not buried in a YAML file — surfaced via `/sweetclaude:help` with an option to "review my SweetClaude preferences." If the system is learning about me, I want to know what it learned.

**Nice to have:** Inline help hints on offers. When an offer fires, a "(explain more)" option that tells me what the feature does before I decide.

---

### Dr. Raj Patel

**Mandatory:** The five sub-skill boundaries I proposed. This is an implementation requirement, not a future-work item. Shipping a monolith and planning to extract sub-skills later is how frameworks accrue technical debt that never gets paid. The extraction cost is much lower before habits and edge cases accumulate.

**My revised position on Priya's "ship first" argument:** I understand the impulse. But the sub-skill architecture is not complex — it's five files with clear ownership. This is not gold-plating. It's the minimum structure that makes the system maintainable.

**Acceptable future work:** The `--advanced` mode, `session.default_action` (Marcus's suggestion), expanded `defer_until` options.

---

### Yuki Tanaka

**Mandatory:** 24h checks move to `session-preflight.sh` hook. The skill file should contain zero time-comparison logic. The `check_error` field should be added to handle silent hook failures.

**Mandatory:** The hook must handle the case where `sweetclaude.yaml` doesn't exist yet (first run, pre-migration). The hook should gracefully no-op rather than error.

**Strong recommendation:** Add a `hook_last_ran` timestamp to the schema so the skill can detect if the hook hasn't fired recently (e.g., someone invoked the skill outside a normal session).

---

### Fatima Al-Hassan

**Mandatory:** The three error handling additions:
1. Parse failure → route to `fix-sweetclaude` with human-readable message
2. `migration_status: in_progress | complete | failed` field for idempotent migration
3. `check_error` field for silent hook failures

**Mandatory:** Migration must archive, not delete, old files. `phase.yaml` → `.sweetclaude/state/archive/phase.yaml.2026-05-03`. Users who had important data in those files deserve a recovery path.

**Nice to have:** A schema checksum or last-written-by field to help diagnose corruption. Not critical for v1.

---

### Ben Kowalski

**Mandatory:** Work history capped at 10 items, not 20. The token math doesn't support 20.

**Mandatory:** `learnings` section should be conditionally loaded. Proposal: move it to a sub-key `extended` that's only injected when the skill explicitly requests it. The `/sweetclaude` orchestrator doesn't need learnings — `sweetclaude:_route` and individual workflow skills do.

```yaml
# sweetclaude.yaml
learnings:                    # loaded by workflow skills, not orchestrator
  - "..."
```

The orchestrator skill reads everything above `learnings` and stops. Workflow skills load the full file. This saves ~300 tokens on every `/sweetclaude` invocation.

**Acceptable future work:** `session.default_action`, fine-grained deferral.

---

### Sasha Oduya

**Mandatory:** Schema version check at top of decision tree. One line:
```
if schema_version != 1 → sweetclaude:_migrate --schema-upgrade
```
This is literally two lines of skill logic and it future-proofs every schema evolution for the lifetime of the framework.

**Mandatory:** Unknown fields must be tolerated without error. Document this explicitly so developers adding fields in sub-skills don't fear breaking existing users.

**My final position on `learnings` placement:** Ben's conditional loading proposal is clever but adds complexity. Simpler approach: keep `learnings` in the file, but the orchestrator skill explicitly skips that section. YAML parsers don't care — the section is read but the orchestrator ignores it. Saves the complexity of a two-tier loading scheme.

---

### Proctor — Final Synthesis

---

## Final Synthesis

### Position Trajectory

| Panelist | T1 Focus | T3 Position |
|----------|----------|-------------|
| Amara | Copy quality | Unchanged — mandatory human-language offers |
| Tom | Misclassification recovery | Resolved — explicit override path is mandatory |
| Priya | Feature offer loop states | Stronger — `deferred` is mandatory, not nice-to-have |
| Marcus | Power user access | Partially resolved — override mandatory, `--advanced` v2 |
| Zoe | First-run + learnings visibility | Both mandatory |
| Raj | Sub-skill architecture | Mandatory — no monolith compromise |
| Yuki | Hook layer for checks | Mandatory — zero time-logic in skill |
| Fatima | Error handling | Three targeted fixes, all mandatory |
| Ben | Token cost | Work history cap (10) + conditional learnings, mandatory |
| Sasha | Schema evolution | Schema version check mandatory, unknown-field tolerance mandatory |

---

### Consensus Findings

**The design is directionally correct.** Ten panelists, zero objections to the core concept. Two visible skills, natural language routing, single-file state — all validated.

**Changes that are mandatory before implementation:**

| # | Change | Raised by |
|---|--------|-----------|
| 1 | Explicit routing override: `/sweetclaude use [workflow]` bypasses classifier | Tom, Marcus |
| 2 | 5th feature state: `deferred` with `defer_until` timestamp | Priya, Sasha |
| 3 | 24h checks move to `session-preflight.sh` SessionStart hook | Yuki |
| 4 | `check_error` field for silent hook failures | Fatima, Yuki |
| 5 | `migration_status: in_progress\|complete\|failed` field | Fatima |
| 6 | Migration archives old files (does not delete) | Fatima |
| 7 | Parse failure routes to `fix-sweetclaude` with human message | Fatima, Amara |
| 8 | Schema version check at top of decision tree | Sasha |
| 9 | Work history capped at 10 items (not 20) | Ben, Marcus |
| 10 | Sub-skill architecture: 5 internal sub-skills, orchestrator stays thin | Raj |
| 11 | Offer copy is human-language — no schema field names in user output | Amara |
| 12 | First-run experience described in design doc | Zoe, Amara |
| 13 | `learnings` visible and editable via `/sweetclaude:help` | Zoe |
| 14 | `hook_last_ran` timestamp so skill detects stale hook | Yuki |

**Acceptable as future work (v2):**
- `--advanced` mode showing top-N skill list (Marcus)
- `session.default_action` remembering last answer (Marcus)
- Fine-grained user-controlled deferral durations (Priya)
- Schema checksum for corruption diagnosis (Fatima)

---

### Unresolved Disagreements

**`learnings` loading strategy (Ben vs Sasha):**
- Ben: conditionally load — orchestrator reads partial file, workflow skills read full file
- Sasha: keep simple — full file always loaded, orchestrator just ignores learnings section
- Both are technically valid. Ben's saves ~300 tokens per invocation. Sasha's is simpler to implement and maintain. **Recommendation: Sasha's approach for v1, Ben's optimization for v2 if token cost proves to be a real constraint in practice.**

**Sub-skill extraction timing (Raj vs Priya):**
- Raj: extract sub-skills before shipping v1
- Priya: ship working monolith, extract in v1.1
- **Recommendation: Raj. The boundaries are clearly defined and the extraction cost is lower now than after implementation habits form. Five focused files beats one 800-line file.**

---

### Minority Reports

**Marcus Webb on `--advanced` mode:**
> "The explicit override solves the immediate problem. But there's a class of power user — someone mid-session who knows exactly what they want and doesn't want to describe it in natural language — who benefits from a clean 'show me the options' escape hatch. `/sweetclaude --advanced` as a v1 feature costs nothing to implement and prevents frustration that the natural language path will inevitably cause. I'll accept v2 if I must, but I'd push the team to include it."

**Priya Malhotra on sub-skill extraction timing:**
> "I've seen frameworks that extracted sub-skills early and the result was five files that nobody could follow because the context was split. If the sub-skill boundaries are truly clean, they'll be easy to extract later. Ship the working whole, learn where the seams actually are from real use, then extract. Premature modularization is as real a problem as monolithic bloat."

---

*Caucus complete. 10 experts. 3 turns. 14 mandatory changes. 2 dissents on record.*
