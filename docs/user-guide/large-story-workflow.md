# Large-Story and Small-Story Workflows

**Version:** 1.1
**Date:** 2026-10-21

These are SweetClaude's two controller-gated, evidence-based work item workflows. They run a work item through the full sequence — DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP/closeout — with phase progression enforced by a controller and a set of hooks rather than by Claude's own judgment. The point is that a story cannot be declared done on the basis of how the output looks. It is done only when the controller has recorded evidence against the criteria that were locked in up front.

---

## You Don't Invoke These Directly

Both workflows are internal. You do not call `/sweetclaude:build large-story` or `/sweetclaude:build small-story` yourself. You start work the normal way — describe what you want in natural language to `/sweetclaude:go`. SweetClaude classifies the request and, when the work warrants it, routes into one of these workflows.

From your seat, the experience is the same as any other SweetClaude work: you talk through what the story is, you approve the success criteria, you do the implementation work together, and at the end SweetClaude reports completion. What is different is underneath — the controller is recording state, gating each phase, and refusing to let the story close until the evidence is in place. You feel that mostly as a sequence that cannot be rushed, not as extra ceremony.

---

## The Phase Sequence and Its Gates

Both workflows run the same phases in the same order:

```text
DEFINE → DESIGN → PLAN → [ENFORCEMENT CHECK] → IMPLEMENT → VERIFY → SHIP
```

Each transition goes through the controller. The controller is the single writer of workflow state — Claude never edits the state files directly. The gate hook denies direct writes to the controller-protected paths, which are exactly `.sweetclaude/state/workflows/`, `.sweetclaude/state/phase.yaml`, `.sweetclaude/reports/` and `.sweetclaude/contracts/`. Other files under `.sweetclaude/` are ordinary project state and stay writable, so the only way forward through a phase is a controller command that returns success.

What each gate enforces:

- **DEFINE** — The story objective, expected outcomes, and non-goals are agreed with you, and a success-criteria contract is created and frozen. Criteria must be binary and machine- or test-measurable; open-ended, human-judged criteria are rejected here and routed to backlog instead. Once the contract is frozen and the workflow is initialized, direct edits to the contract are blocked: the gate hook denies them outright in every permission mode, because an approval question is not reliably shown in auto mode. Amending a frozen contract is a human action. You run the contract commands yourself, re-freeze the contract, and re-run init so the workflow binds to the new hash.
- **DESIGN** and **PLAN** — Durable design and plan artifacts are written, each bound to the frozen contract. PLAN will not enter if the design artifact is not bound to the contract; IMPLEMENT will not enter if the plan artifact is not bound to the contract.
- **ENFORCEMENT CHECK** — Before IMPLEMENT, the controller confirms the gate hook is actually loaded. It arms a probe, allows one expected write, blocks one forbidden write, then checks the result. If enforcement is not verified live, the workflow stops here and refuses to enter IMPLEMENT — it will not run unprotected where the evidence gate cannot be trusted.
- **IMPLEMENT** — Only after IMPLEMENT is entered can project files be created or modified. In every other phase the gate hook denies project writes. As you work, an evidence hook automatically records the files touched and commands run. That evidence cannot be fabricated; it comes from observed activity.
- **VERIFY** — The controller regenerates the implementation record from observed evidence and writes the canonical ledger. It **fails closed**: if any criterion lacks evidence, or if no hook-observed file changes were recorded, verification does not pass.
- **SHIP** — Closeout is written by the controller only after completion validation passes. Terminal "done" state is written by the controller, never by Claude.

You cannot skip ahead. If you try to move to a phase whose gate is not satisfied, the controller returns a block, Claude reports the reason, and the workflow stays where it is. There is no working around a block by retrying with different arguments — the SKILL explicitly forbids that.

See [Phases and Workflows](phases-and-workflows.md) for how phases and gates work across all of SweetClaude.

---

## Success-Criteria Contracts and Evidence

The contract is the spine of both workflows. During DEFINE, SweetClaude generates a schema-valid contract skeleton, fills it in with the agreed objective, outcomes, non-goals, and the binary pass/fail conditions for each criterion, then freezes it. Freezing computes a contract hash. From that point on, every downstream phase artifact is bound to that hash, and any edit to the frozen contract is detected as stale.

Completion is not a judgment call. It requires a `success-criteria-ledger.json` that evaluates every frozen criterion against accepted evidence and reports a single binary outcome: `all_success_criteria_passed == true` or `false`. No review, caucus, verification, or release step may add new completion criteria after the contract is frozen. If a reviewer finds a real issue outside the frozen criteria, it routes to backlog, a contract-amendment request, a split story, or human escalation — it does not silently become a new blocker.

Because the ledger is written by the controller from recorded evidence, and because VERIFY fails closed without that evidence, SweetClaude cannot claim a story is complete on the strength of how the result looks. Screenshots and app behavior do not count as completion evidence unless the controller has entered them into the ledger.

For the full mechanics of contracts, freezing, and ledgers, see [Evidence and Success-Criteria Contracts](evidence-and-contracts.md).

---

## How the Controller Stops You From Skipping Ahead

The controllers (`large_story_controller.py` and `small_story_controller.py`) and their hooks are the enforcement layer — not the skill text. Three behaviors are worth knowing as a user:

- **The gate hook** denies project writes outside a controller-entered IMPLEMENT phase, and denies direct writes to the controller-protected paths (`state/workflows/`, `state/phase.yaml`, `reports/` and `contracts/` under `.sweetclaude/`). So you literally cannot start changing code before the workflow has reached IMPLEMENT through the gates.
- **The evidence hook** records implementation evidence (touched files, commands) automatically during IMPLEMENT. This is what VERIFY reads.
- **The stop guard hook** blocks the first attempt to end the session while the workflow is non-terminal and shows a one-line status checkpoint, so the open workflow is not silently abandoned. If you try to stop a second time (the second stop), the guard records an intentional pause and lets the session end. Later turns stop silently until the story makes progress, at which point the guard re-arms and gives one reminder again. A workflow that has reached a terminal state is never blocked.

The user-visible effect is simple: the workflow advances one gated step at a time, the order is fixed, and "done" is something the controller grants, not something Claude asserts.

---

## Large vs Small

Both workflows run the identical controller-gated sequence, freeze a contract, bind downstream artifacts to its hash, record evidence, and fail closed at VERIFY. The difference is what kind of work each is meant for:

- **Large story** is for a work item that is too large or high-risk for a single bounded `/sweetclaude:build code-feature`, `/sweetclaude:build code-issue`, or `/sweetclaude:build code-tdd` pass. This is the high-rigor path. SweetClaude's process controls anchor the frozen, hash-bound success-criteria contract requirement to large/high-rigor work specifically — large-story is where that contract discipline is mandatory before any downstream planning, design, implementation, review, or release begins.
- **Small story** is for bounded work items that benefit from controller-enforced phase gates and evidence recording but are lighter in rigor — the kind of contained, single-session work where you still want the gate, the evidence trail, and the fail-closed VERIFY, without treating the item as a high-risk initiative.

Both keep their own workflow state. The primary state path for each workflow is `.sweetclaude/state/workflows/{workflow_id}.yaml`, which init writes. `.sweetclaude/state/large-story.yaml` and `.sweetclaude/state/small-story.yaml` are legacy pointers that the controllers read only if they are present. See [State and Memory](state-and-memory.md) for how SweetClaude persists work across sessions.

---

## When SweetClaude Uses Each

You don't choose between them directly — you describe the work and SweetClaude routes. As a rough mental model:

- A substantial or risky feature, or anything you'd otherwise break into multiple passes, lands in **large story** — the high-rigor, contract-anchored path.
- A contained piece of work that fits in a single bounded session, but that you still want gated and evidenced, lands in **small story**.

Either way, the contract is agreed with you up front, the phases are gated, the evidence is recorded as you go, and completion is granted by the controller against that evidence — not asserted from how the output looks.
