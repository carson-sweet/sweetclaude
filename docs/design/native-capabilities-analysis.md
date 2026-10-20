# Deep Analysis: Can native Claude Code plugin capabilities carry SweetClaude's burden?

**Date:** 2026-06-27
**Subject repo:** `/home/user/sweetclaude` (sweetclaude v4.1.12-beta)
**Question:** Could native Claude Code plugin-developer capabilities — Plan Mode, subagents/agent-teams, and **dynamic Workflows** — natively carry some of the burden SweetClaude currently implements with custom machinery (23 bash hooks, ~38 Python scripts, an `orchestrator_loop.py`, 113 prose skills, custom YAML state, and shell-preprocessing state injection)?

> **Implementation status (2026-06-28):** Addendum improvements #1 (the `execute_step` yield — model-as-runtime executor), #2 (structured-output contract), #3 (parallel/fan-out step groups), #4 (per-workflow budget), and #5 (adversarial-verify step shape) have all landed in `scripts/orchestrator_loop.py` and `skill-library/build/orchestrator/SKILL.md`, each with tests and Gherkin scenarios. The two smaller cleanups have also landed: the artifact pointer is now dropped when exit checks fail on a missing file (exit checks read `state["artifacts"]`, so the pointer must still be set *before* validation — it cannot simply be reordered), and `_save_state` now stages every temp file before swapping any in, narrowing the dual-write half-fail window.

---

## Context — why this matters

SweetClaude is *already* a Claude Code plugin. It ships `.claude-plugin/plugin.json`, a `hooks/hooks.json` registering 14 hook entries, an `agents/` directory of 11 subagents, and 113 skills. So this is **not** "could a plugin do this" — it provably can, because it does. The real question is sharper and more useful for the roadmap:

> Of the burden SweetClaude carries through its **own custom code** — the Python orchestrator, the bash enforcement hooks, the hand-rolled state schema, the shell-preprocessing trick — how much can be **shifted onto native primitives that did not exist (or were weaker) when SweetClaude was built**, specifically Plan Mode, native subagents/agent-teams, dynamic Workflows, and auto-memory?

The payoff is reduced maintenance surface and fewer places where SweetClaude reimplements something the harness now does natively (and more robustly, cross-platform). The risk is trading deterministic, owned code for harness behavior SweetClaude can't version or guarantee.

This document is a **feasibility analysis with a layered migration roadmap**. It does not change any code.

---

## The core lens: enforced vs. discretionary

Everything below turns on one distinction, which SweetClaude's own architecture already respects:

| Mechanism | Who guarantees it | SweetClaude uses it for |
|---|---|---|
| **Hooks** (Pre/PostToolUse, SessionStart, UserPromptSubmit) | Harness — runs deterministically, can `deny` a tool call | TDD test-immutability, bootstrap gating, drift gating, auto-test, WIP limits |
| **Workflows** (dynamic JS orchestration) | Runtime — script controls fan-out, results in script vars | *(not used yet)* |
| **Subagents / agent-teams** | Spawned on demand; isolated context | TDD test-writer/implementer split, review caucus |
| **Skills / CLAUDE.md** | **Model discretion** — guidance, not enforcement | Phase workflows, interaction model, all 113 procedures |
| **Plan Mode** | Harness — blocks writes until plan approved | *(not used as a primitive; SweetClaude has its own `ultraplan`/`go`)* |

**The headline finding:** SweetClaude's *enforcement* layer is already native (hooks). Its *orchestration* layer is the part still carried by custom code (`orchestrator_loop.py`, prose multi-agent choreography in skills) and is the **biggest candidate to move onto native dynamic Workflows + agent-teams**. Its *guidance* layer (phase gates, interaction model) is inherently discretionary and cannot be made native-deterministic without hooks — which it already partially is.

---

## Capability-by-capability verdict

### 1. Dynamic Workflows ← `orchestrator_loop.py` + prose multi-agent choreography  **(STRONGEST FIT)**

**What SweetClaude does today:** `scripts/orchestrator_loop.py` is a hand-written workflow loop engine that tracks step state, yields gates/failures/escalations, and routes decisions. The TDD pipeline (test-writer → implementer → reviewers) is choreographed by **prose instructions** inside `skill-library/build/code-tdd/SKILL.md` and the `agents/*.md` files — i.e., the model is *told* to spawn agents in order and is trusted to do it correctly.

**What native Workflows offer:** Deterministic JS orchestration. The script — not the model — decides which agents run, in what order, with what inputs, and how results aggregate. `pipeline()`/`parallel()` give real fan-out (up to 16 concurrent, 1000 total). Structured output schemas force agents to return validated data. This is *exactly* the TDD pipeline and the review caucus: `test-writer → verify RED → implementer → [code-review ∥ security-review ∥ perf-review]`, with adversarial verification of findings.

**Verdict: HIGH-VALUE MIGRATION.** The multi-agent pipelines (TDD Levels 2–3, the QA/review caucus, John Wick autonomous mode) are the single best fit for native Workflows. Moving them off prose-choreography removes the largest correctness risk in SweetClaude: *the model silently not following the multi-agent protocol*. A Workflow script makes "spawn test-writer, confirm RED, then spawn implementer who cannot see the stories" a **structural guarantee**, not a hope.

**Caveats:**
- Workflows require explicit user opt-in per invocation (the `ultracode`/"use a workflow" gate). SweetClaude would invoke them from inside a skill — confirm a skill *can* trigger `Workflow` non-interactively, or whether the opt-in friction breaks the conversational flow. **This is the #1 thing to verify before committing.**
- Workflow scripts can't touch the filesystem directly or use `Date.now()/Math.random()`. State writes (`.sweetclaude/`) must happen via agents or after the workflow returns. SweetClaude's Python writes state freely today; this is a real porting constraint.
- Test-immutability enforcement still needs the `test-guardian` hook even inside a Workflow — the worktree-isolation option helps with parallel mutation but doesn't replace the lock.

### 2. Subagents / agent-teams ← `agents/*.md` + prose spawning  **(ALREADY NATIVE; TIGHTEN)**

**Today:** 11 agent definitions exist as Markdown with role prompts and tool restrictions. They are spawned by the model following skill prose. The test-writer/implementer context split (implementer can't see stories; tests are read-only) is the crown jewel.

**Native:** This *is* the native subagent model — `agents/*.md` with `tools:`/`description:` frontmatter is exactly the supported format. The gap is **invocation determinism**, which Workflows (above) close. Agent-teams (peer messaging, shared task list) could model the QA caucus more naturally than independent subagents.

**Verdict: KEEP, but drive invocation from Workflows rather than prose.** No need to replace the agent definitions; they're already native. The win is *how they're orchestrated* (see §1).

### 3. Hooks ← bash enforcement hooks  **(ALREADY NATIVE; MINOR MODERNIZATION)**

**Today:** 23 bash/Python hooks do the real enforcement — `test-guardian.sh` (blocks test writes during IMPLEMENT), `master-preflight.sh` (bootstrap/drift gating), `tdd-prewrite-guardian.sh`, `wip-limit.sh`, `auto-test-runner.sh`, `state-regenerator.sh`. These are genuinely deterministic and **cannot be replaced by anything more native — they already are the native enforcement primitive.**

**Modernization opportunities (not replacements):**
- The hooks emit `{"ok": false, "reason": ...}`. Current docs describe a richer `hookSpecificOutput` with `permissionDecision: deny|ask` and `additionalContext` injection. If SweetClaude is on the older output contract, migrating to the structured form gives better UX (ask vs hard-deny) and lets hooks **inject context** rather than only block — potentially replacing some shell-preprocessing (see §6).
- Newer hook events (`SubagentStart/Stop`, `FileChanged`, `PreCompact`, `SessionEnd`) could replace polling/manual steps — e.g., `PreCompact` to force a state commit (SweetClaude's CLAUDE.md already *asks* the model to "save before compression"; a `PreCompact` hook makes it guaranteed).

**Verdict: KEEP. Modernize output contract; adopt `PreCompact`/`SessionEnd` for state durability.**

### 4. Plan Mode ← `ultraplan` skill + plan-file tracking  **(PARTIAL FIT)**

**Today:** SweetClaude has its own planning skills (`ultraplan`, `go`) and a `plan-tracker.sh` PostToolUse hook on `ExitPlanMode` that records the active plan file. So it already *integrates with* native Plan Mode rather than replacing it.

**Native Plan Mode** gives a harness-enforced read-only research phase ending in an approved plan — which maps cleanly onto SweetClaude's DISCOVER/DEFINE/DESIGN "think before you build" ethos and its phase-gate approval ritual. But Plan Mode is a *single* gate, whereas SweetClaude's value is the *multi-phase* gate sequence with persisted artifacts. Native Plan Mode can't model "7 phases each with exit criteria and a decision log."

**Verdict: COMPLEMENT, don't replace.** Lean on native Plan Mode for the per-work-item "plan this change" step (and keep the `plan-tracker` hook). Keep SweetClaude's phase pipeline as the higher-level structure native Plan Mode doesn't provide.

### 5. Phase gates + interaction model ← prose rules  **(CANNOT GO NATIVE; the irreducible core)**

`rules/phase-gates.md` (688 lines), `rules/interaction-model.md` (157 lines), and the 113 skill procedures are **discretionary guidance**. There is no native primitive that makes "challenge the framing at L2+" or "never push phase advancement" deterministic. The *only* native lever is hooks, and you can hook-enforce *artifacts* (does `product-brief.md` exist before DEFINE exit?) but not *quality* (is the brief actually good?).

**Verdict: STAYS AS PROSE.** This is SweetClaude's actual product and its irreducible non-native core. The most you can do natively is convert *checkable* gate criteria (artifact existence, test pass, file presence) into PostToolUse/Stop hooks — partially already done by `artifact-guardian.sh`.

### 6. State management ← custom YAML + shell-preprocessing injection  **(MIXED)**

**Today:** Source of truth is `.sweetclaude/state/*.yaml`, queried/written by `sc-artifact-impl.py` (~30KB) and injected into skills via the `!`cat .sweetclaude/state/session-state.yaml`` shell-preprocessing trick in SKILL.md frontmatter.

**Native options:**
- **Auto-memory** (`MEMORY.md` + topic files, model-written, 30-day retention) overlaps with `improvement-register.md` (learnings across sessions) — a plausible partial replacement for the *learnings* slice, but **not** for structured phase/work state, which must stay explicit YAML (auto-memory is model-curated and lossy; SweetClaude's state is project-critical and committed to git). **Do not move structured state to auto-memory.**
- The **shell-preprocessing injection** could partly move to a **SessionStart hook returning `additionalContext`** (native context injection), which is cleaner and less dependent on the `!`...`` SKILL.md feature. Worth prototyping.

**Verdict: KEEP structured YAML state and `sc-artifact-impl.py`.** Consider (a) SessionStart-hook context injection to replace shell-preprocessing, (b) evaluate whether `improvement-register` *learnings* duplicate auto-memory.

---

## Summary scorecard

| SweetClaude burden | Native target | Verdict | Effort |
|---|---|---|---|
| `orchestrator_loop.py` + prose TDD/review choreography | **Dynamic Workflows** + agent-teams | **Migrate — highest value** | High |
| `agents/*.md` definitions | Native subagents | Already native; orchestrate via Workflows | Low |
| Bash enforcement hooks | Native hooks | Already native; modernize output contract | Low–Med |
| Per-change planning | Native Plan Mode | Complement, keep `plan-tracker` hook | Low |
| Phase gates + interaction model | (none) | **Stays prose** — irreducible core | — |
| Structured YAML state | (none) | **Stays custom** | — |
| `improvement-register` learnings | Auto-memory | Evaluate overlap only | Low |
| Shell-preprocessing state injection | SessionStart-hook `additionalContext` | Prototype replacement | Med |

**One-line answer to the question:** Yes for **orchestration** (dynamic Workflows are a strong, high-value replacement for `orchestrator_loop.py` and the prose multi-agent choreography); **no** for the phase-gate/interaction-model core (irreducibly discretionary) and structured state (must stay owned). The enforcement layer is *already* native. Plan Mode complements rather than replaces.

---

## Recommended approach (layered roadmap)

**Phase A — De-risk the orchestration migration (read-only spikes first):**
1. Verify the **#1 blocker**: can a SweetClaude skill invoke the `Workflow` tool without breaking the conversational opt-in flow? Test with a throwaway skill that runs a 2-agent pipeline. If opt-in friction is unacceptable, the whole orchestration migration is gated on it — find out before anything else.
2. Confirm Workflow constraints against the TDD pipeline's needs: no-filesystem-in-script, structured-output schemas for RED/GREEN signals, worktree isolation for parallel implementers, and that `test-guardian` still fires inside Workflow-spawned agents.

**Phase B — Pilot one pipeline on native Workflows:**
3. Port the **review caucus** first (lower risk than TDD — it's read-only analysis): `parallel([code-review, security-review, perf-review])` → adversarial verify → synthesize. Keep the existing `agents/*.md` as the agent definitions. Compare against the current prose-choreographed version for reliability and cost.
4. If the caucus pilot succeeds, port **TDD Level 2** (test-writer → RED gate → implementer → auto-test), keeping `test-guardian`/`tdd-prewrite-guardian` hooks as the immutability backstop.

**Phase C — Modernize the native layer already in place:**
5. Migrate hook output to the structured `hookSpecificOutput` contract (`permissionDecision`, `additionalContext`); adopt `PreCompact`/`SessionEnd` hooks for guaranteed state-commit (replacing the prose "save before compression" ask in CLAUDE.md).
6. Prototype replacing the `!`cat session-state.yaml`` shell-preprocessing with a SessionStart hook returning `additionalContext`.

**Phase D — Leave alone (explicitly):**
7. Phase gates, interaction model, the 113 skill procedures, and structured YAML state remain custom. Document *why* (irreducibly discretionary / project-critical / git-committed) so future contributors don't try to "nativize" them.

---

## Critical files (for whoever executes)

- Orchestration to migrate: `/home/user/sweetclaude/scripts/orchestrator_loop.py`, `/home/user/sweetclaude/skill-library/build/code-tdd/SKILL.md`, `/home/user/sweetclaude/agents/{test-writer,implementer,code-reviewer,security-reviewer,performance-reviewer}.md`
- Enforcement to keep/modernize: `/home/user/sweetclaude/hooks/hooks.json`, `/home/user/sweetclaude/hooks/test-guardian.sh`, `/home/user/sweetclaude/hooks/master-preflight.sh`
- State to keep: `/home/user/sweetclaude/scripts/sc-artifact-impl.py`, `/home/user/sweetclaude/skills/master/SKILL.md` (shell-preprocessing line 9)
- Irreducible core: `/home/user/sweetclaude/rules/phase-gates.md`, `/home/user/sweetclaude/rules/interaction-model.md`

## Verification (for any migration, since this analysis ships no code)

- **Workflow opt-in spike:** invoke a trivial Workflow from inside a test skill; confirm it runs and returns structured output without breaking the chat turn.
- **Caucus parity test:** run the same diff through (a) current prose review and (b) Workflow-orchestrated review; compare findings, false-positive rate, wall-clock, token cost.
- **TDD backstop test:** inside a Workflow-spawned implementer, attempt to edit a test file; confirm `test-guardian.sh` still denies it.
- **Regression:** use `/sweetclaude:configure` to run the 15-contract behavioral regression before and after any change, confirming no behavioral drift.

---

## Honesty notes / things I did not fully verify

- The native-capability details (Workflow opt-in semantics from inside a skill, exact current hook-output contract, agent-team availability) come from current docs and my own tool surface, **not** from running them against this repo. Phase A spikes exist precisely to confirm them before committing.
- I interpreted "plan, plan, and dynamic workflows" as **Plan Mode + subagents/agent-teams + dynamic Workflows** (the phrase appears to have a typo). The analysis covers the full plugin-dev surface anyway, so the interpretation doesn't narrow the conclusions.

---

# Addendum (2026-06-28): orchestrator deep-dive + correction

After the initial analysis I verified two things against the live code and current docs. Both change the picture, so they're recorded here rather than silently edited into the text above.

## Correction to the roadmap's "#1 blocker"

The original Phase A framed the blocker as *"can a skill invoke the `Workflow` tool without breaking the opt-in flow?"* — implying it might work with friction. **Confirmed against docs: it does not.** There is no documented way for a plugin, skill, hook, or agent to trigger a native Workflow non-interactively, and no plugin manifest field to bundle workflows. Native Workflows are **user-gated only** ("ultracode" / "use a workflow" / `/saved-workflow`). The most SweetClaude can do is *suggest* a workflow or ship a saved one into `.claude/workflows/` for the user to run.

**Implication:** native dynamic Workflows **cannot be wired into SweetClaude's autonomous flow as an internal engine.** They remain a cooperative, user-invoked tool. This kills the "port the orchestrator onto native Workflows" idea as originally implied.

What *is* native and plugin-callable for background work:
- **MCP server** (`.mcp.json`) — a persistent subprocess (any language) that starts with the plugin and exposes tools. The real native home for the orchestrator's **state + deterministic logic**. **But an MCP server cannot spawn Claude subagents** — it exposes tools the model calls; it doesn't drive the model. So it carries compute/state, not multi-agent fan-out.
- **Background monitors** (`monitors.json`, v2.1.105+, personal-scope/interactive only) — watch + notify, not orchestrate.
- **Async hooks** (`async`/`asyncRewake`) — event-triggered, non-blocking; not persistent daemons.

**Net platform wall:** no plugin-callable runtime can spawn Claude subagents. The dynamic-Workflow `agent()/parallel()/pipeline()` runtime is reachable **only** when the model invokes the Workflow tool. Therefore the only executor SweetClaude can reach from inside its own flow is **the conversational model itself** (via the Task tool).

## The central finding: the orchestrator's executor seam is empty

`scripts/orchestrator_loop.py` is a well-built **deterministic workflow state machine** — routing DSL, iteration counters with backward-edge detection, gate replay-prevention, atomic dual-write persistence, exit checks. But its execution call site is hollow:

```python
# orchestrator_loop.py:306
def _invoke_agent(*args, **kwargs):
    pass
```

Every test in `tests/test-orchestrator-loop.py` **monkeypatches** `_invoke_agent` to actually write an artifact and return a signal (e.g. `lambda **kw: {"status":"success","signal":"done"}`). In production it does nothing, and nothing else fills the gap — `skill-library/build/orchestrator/SKILL.md` only runs the loop and routes user gates; it never spawns subagents. A Python subprocess can't spawn Claude subagents anyway (the platform wall above).

**Consequence — traced for an artifact step** (`spec`: `output_artifact`, `exit_checks:[file_exists, file_non_empty]`):
1. gate yields → approve → `resume` re-enters `run_loop`
2. `_invoke_agent(...)` → no-op, **nothing written**
3. line 507 records `artifacts[spec_file] = output_path` even though the file is absent
4. `_extract_signal_from_path` → file missing → `None`
5. `validate_exit_checks` → `file_exists` fails → yields `reason: "failure"`

So **in production the loop stalls at the first artifact-producing step.** This — not architecture — is the deepest difference from native Workflow: native Workflow's whole point is that `agent()` executes and returns data into script variables; here that exact call site is empty.

**Honesty note:** I confirmed this across the three places execution could live (the script, the skill, the tests). I read the contract of `orchestrator.py` helpers (`assemble_context_envelope`, `extract_output_signal`, `validate_exit_checks`) but not the module in full. Conclusion: the autonomous executor is **unimplemented / WIP in this beta**, not wired elsewhere.

## Improvements to make it native-Workflow-like (highest leverage first)

### 1. Make the model the runtime — add an `execute_step` yield (the big one)
Invert the design: the loop should **yield steps to be executed**, not try to execute them. Before the `_invoke_agent` site, when the step's output isn't ready, return a new reason:

```python
state["status"] = "waiting_for_agent"
_save_state(...)
return {
  "reason": "execute_step",
  "step_id": step["id"],
  "payload": {
    "agent": step.get("agent"),
    "subagent_type": step.get("subagent_type"),
    "model": step.get("model", "sonnet"),
    "input_paths": input_paths,
    "output_path": output_path,
    "output_schema": step.get("output_schema"),   # see #2
    "prompt": prompt,
  },
}
```

`orchestrator/SKILL.md` gains a handler: on `reason: execute_step`, the model spawns the real subagent (Task tool, honoring `subagent_type`/`model`/inputs), confirms the artifact, then calls `resume {"action":"accept"}`. The loop re-enters, finds the artifact, extracts the signal, runs exit-checks, advances. **`_invoke_agent` is then deleted** — its job is now the model's. This is native Workflow's loop with the model as runtime instead of the JS sandbox, and it's the one change that makes the orchestrator actually run in production.

### 2. Structured-output contract instead of regex signal-scraping
`extract_output_signal` scrapes the signal from a markdown file — brittle; the source of the "no signal produced" failures (loop lines 532–543). Add an optional per-step `output_schema`; have the executing subagent return validated JSON (native `agent({schema})`-style) and read the signal from that object, keeping file-scraping as fallback.

### 3. Fan-out / parallel step groups in the template DSL
Today `current_step_id` is a single scalar — strictly sequential. Model the review caucus / reviewer bank as native `parallel()`:

```yaml
- id: review-caucus
  parallel:
    - { agent: code-reviewer,     output_artifact: code_review }
    - { agent: security-reviewer, output_artifact: sec_review }
    - { agent: perf-reviewer,     output_artifact: perf_review }
  join: all   # advance when all children have artifacts + pass exit-checks
```

`execute_step` yields the whole group; the model spawns all children in one turn; a join-gate validates each before advancing.

### 4. Budget alongside `iteration_limits`
Native Workflow has `budget.remaining()`; you have only `default_max: 3`. Add an optional per-workflow token/turn budget to `orchestrator-defaults.yaml`, track spend in state, and yield `reason: "budget_exhausted"` (reset/abort) reusing the existing counter machinery.

### 5. Adversarial-verify as a reusable step shape
Promote native Workflow's verify-each-finding pattern to a `verify:` block that fans out K skeptics and routes on majority vote. Your gated, durable design can **exceed** native Workflow here because verdicts persist across sessions.

### Smaller cleanups
- **Bug:** loop line 507 sets `artifacts[output_artifact] = output_path` before confirming the file exists; on later exit-check failure, state points at a non-existent artifact. Set it only after `validate_exit_checks` passes.
- The canonical + output-dir **dual write** (`_save_state`, lines 75–87) doubles every write and can half-fail. Prefer one canonical file + a pointer, or a single rollback-wrapped write.

## What to keep — already better than native Workflow
- **Cross-session durability** (`os.replace` atomic state + `completed_steps`/`gates_passed`/`sessions`) — native Workflow runs are session-scoped; this survives process death and weeks.
- **Human gates as first-class** (`user_approval`/`user_approval_hard` + deference) — native Workflow runs to completion; this is the point of SweetClaude.
- **Declarative template DSL** (`workflow-templates.yaml` steps + routing) — native Workflow's orchestration is imperative JS; this separation is cleaner.

## Revised recommendation
The orchestrator's architecture is sound — it's a stronger state machine than native Workflow for a lifecycle tool. It fails in production only because the executor seam is empty, and the platform makes the conversational model the only reachable executor. So the path is **not** "port to native Workflows" (impossible from inside the flow) but **"finish the orchestrator with the model as runtime"**: implement #1 (the `execute_step` yield + skill handler, delete `_invoke_agent`), then tighten the contract with #2–#3. Optionally relocate the orchestrator's pure state/logic into a bundled **MCP server** for cleaner persistence — but that's orthogonal and doesn't change the executor story.

### Suggested execution order
1. **#1 `execute_step` yield + skill handler** (makes workflows actually run; delete `_invoke_agent`). Update `tests/test-orchestrator-loop.py` to assert the new yield instead of monkeypatching the hollow seam.
2. **Fix the two cleanups** (artifact-set ordering, dual-write) — small, ride along with #1.
3. **#2 structured-output contract** — removes the brittlest failure mode.
4. **#3 parallel step groups** — unlocks the review caucus / TDD reviewer bank.
5. **#4 budget, #5 adversarial-verify** — quality layers, lower priority.

### Verification for the orchestrator work
- Unit: extend `tests/test-orchestrator-loop.py` to cover the `execute_step` yield, the accept-after-execute re-entry, and join-gate validation for parallel groups. Keep the existing routing/iteration/gate coverage green.
- End-to-end: run a real `net-new-feature` workflow via `/sweetclaude:go` → orchestrator, confirm it advances past an artifact step in production (the current stall point) without monkeypatching.
- Regression: `/sweetclaude:configure` runs the 15-contract behavioral regression before and after.
