# Walkthroughs

**Version:** 1.4
**Date:** 2026-10-21

Seven concrete scenarios end-to-end. Each one shows what you run, what comes back, and what you have when you are done. The interactions are simulated but representative — actual prompts vary slightly with the model and your project state.

---

## 1. From Napkin Sketch to Shipped Feature

You have a vague idea: a tool to help freelance designers collect feedback from clients on visual mockups. No code, no spec, no folder. You want to take it from concept to a shipped MVP feature.

### Setup

```bash
mkdir feedback-tool && cd feedback-tool && claude
```

```
/sweetclaude:configure init
```

Init runs setup, which detects the empty folder and asks for the project name, a one-sentence description, where issues should live, and a working mode. Setup then offers optional features. You start discovery yourself with `/sweetclaude:plan product-discovery` and describe the idea.

You type a paragraph. SweetClaude does not start drafting. Instead it pushes back:

> You said "freelance designers" — but the friction in client feedback exists across roles. Agencies, in-house teams, and indie product designers all face it. What makes you confident the freelance segment specifically? Or is "freelance designers" a stand-in for a broader pattern?

You think about it and refine: it is freelance designers because they have no design ops infrastructure and clients are non-designers. SweetClaude accepts the framing, records it as a decision, and offers product discovery at three depths: L1 (intent and boundaries), L2 (problem and success), and L3 (full pain thesis). You pick L2 (problem and success) — this is more than a hobby project but you do not want a 90-minute interview.

### Discovery and Definition

SweetClaude conducts the L2 discovery interview, one section at a time. After each section it probes — never batches multiple questions into one message. By the end you have:

- `.sweetclaude/state/discovery.yaml` — problem framing, target user, success criteria
- `.sweetclaude/state/personas.yaml` — at least one persona with a real scenario
- `.sweetclaude/state/decision-log.md` — three decisions captured

Then you run `/sweetclaude:plan product-brief`. SweetClaude reads the discovery output, presents an outline first, lets you approve or restructure, then writes the brief. You iterate twice. You commit.

Then `/sweetclaude:plan product-prd` — full PRD with functional requirements, NFRs, and epics. About 90 minutes of work. You commit.

### Design

`/sweetclaude:design design-architecture`. SweetClaude conducts an architecture interview — language, framework, data store, deployment target. Always offers a recommendation before asking you to decide. Records architectural decisions as ADRs.

You also run `/sweetclaude:design design-data-model` for the schema and `/sweetclaude:design design-api-design` for endpoint contracts. Both feed off the architecture state.

### Plan

`/sweetclaude:plan product-user-stories` produces stories with acceptance criteria for the first epic. `/sweetclaude:build product-user-tdd-tests` converts them to Gherkin `.feature` files.

### Implement

```
/sweetclaude:build code-feature first feedback-thread feature
```

SweetClaude finds the Gherkin specs for that feature. It runs **TDD Level 3**:

0. A story branch (`{ID}/{slug}`) is created. All work for this feature lands there.
1. The test-writer agent (separate context, no knowledge of planned implementation) writes failing tests.
2. The QA Caucus — three specialist agents — reviews the test plan from three angles: service/API, component/UI, integration/cross-cutting.
3. You see the QA findings and approve the test plan.
4. The implementer agent (separate context, sees only the tests) makes them pass with minimal code. The test-guardian hook denies edits to test files while it works (override: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tdd_phase.py release --file <path> --approval "<text>"`, logged).
5. The auto-test-runner hook runs the configured or detected test command after every source edit and reports failures back.

When all tests pass, SweetClaude runs `/sweetclaude:build code-review` and `/sweetclaude:build code-testing` (PR pre-check), then opens a PR.

### What you have at the end

A working feature. Tests that specify behavior, not just confirm code. A decision log explaining every architectural choice. A traceability map from user story to requirement to test to commit. A PR that is ready for review because the review already happened.

This is the canonical SweetClaude flow. Other walkthroughs are variations.

---

## 2. Adopting an Existing Codebase

You have a codebase. It might be polished. It might be a mess. You want to start using SweetClaude on it without disrupting anything.

```bash
cd ~/work/legacy-project
claude
```

```
/sweetclaude:configure init
```

Init runs setup. The first thing setup does is create a `pre-sweetclaude` git branch from your current state. That branch is your insurance — if you ever want to undo every byte SweetClaude added to your repo, `git checkout pre-sweetclaude` gets you back. If the branch cannot be created, setup stops and writes nothing.

Setup then takes a quick read-only look at the project: a file listing, the top of your README, and the last ten commits.

For a codebase that looks organized, it asks three questions, one at a time:

1. What is the project name?
2. What stage is it at: early prototype, active development, approaching launch, or in production?
3. Which issue tracker should hold project issues: this repository or GitHub Issues?

It then asks which working mode fits. Your stage answer sets `version_stage` (IDEA, ALPHA, BETA, or GA) in `.sweetclaude/state/sweetclaude.yaml`.

If the codebase looks inherited or disorganized, setup takes a different path. It runs a full assessment — assess, diagnose, plan, scaffold — shows you the scaffolding plan before touching anything, and ends by suggesting what to tackle first. If the assessment flags auth code written under deadline, for example, a sensible first move is `/sweetclaude:maintain code-debt` to lock the existing behavior in tests before any refactor.

Either way, setup finishes by offering optional features.

### What you have at the end

Your codebase, untouched except for the addition of `.sweetclaude/` (which you commit). A `pre-sweetclaude` branch you can roll back to. A recorded `version_stage` that reflects where the project is. A suggested first move if the assessment path ran, or a clean slate if it did not.

The tone of this onboarding is deliberate. SweetClaude treats existing codebases like an archaeologist treats a dig site — understanding before changing, respecting what is there.

---

## 3. A Hotfix at 2 AM

Production is broken. You need to ship a fix now. SweetClaude has a workflow for this and it skips most of the ceremony.

```
/sweetclaude:go production is down, the OAuth callback is throwing 500s
```

SweetClaude classifies this as a `hotfix` — work type, not bug fix. The difference matters: hotfix runs the **compressed** workflow shape (DIAGNOSE → IMPLEMENT → SHIP → POST-MORTEM), skips most prerequisite checks, and and treats the POST-MORTEM as a required follow-on.

It asks you three triage questions:
1. What is the specific failure — the error message, broken behavior, or degraded state?
2. What is the severity: P0 (service down, data loss, or security), P1 (core workflow broken, no workaround), or P2 (degraded, workaround exists)?
3. What is the scope: all users or a subset?

After the fix ships, SweetClaude checks that the broken behavior is resolved, error rates are back to baseline, and there are no side effects. If the fix does not resolve the problem, it reassesses and suggests `rollback-revert` or a different fix approach.

### DIAGNOSE

The hotfix workflow is not "skip the test." It is "minimal test, in this session." SweetClaude asks you to identify the broken code and write a regression test that fails on the bug. Then it implements the fix. The test and fix get committed together.

Test-guardian and auto-test-runner hooks are still active. The hotfix shortcut applies to ceremony, not to discipline.

### SHIP

SweetClaude asks for an async notification to a stakeholder (a Slack message, an issue update — anything) or a logged self-review. It deploys (or hands off to your deploy command). It confirms the fix in production.

### POST-MORTEM

The post-mortem is logged as required. SweetClaude offers two choices: create a POST-MORTEM backlog item now, or skip and create it later. A skip is recorded in the decision log so the obligation stays visible. The backlog item's body points to `/sweetclaude:maintain postmortem`, which asks for the timeline of events, the root cause analysis, contributing factors, and action items.

If the hotfix was a workaround rather than a real fix, the post-mortem item reminds you to create a tech-debt follow-up for the real fix.

### What you have at the end

Production restored. A regression test that was missing before. A POST-MORTEM backlog item or a logged decision to create it later. A reminder in the post-mortem item to create a tech-debt follow-up if you patched around the real problem.

---

## 4. Organizing a Pile of Documents

You have thirty strategy documents, fifteen Claude.ai session exports, eight meeting notes, and a Google Drive folder of research PDFs. Some are duplicates. Some are drafts of drafts. You need a clean canonical set of go-forward documents that you can search.

```
/sweetclaude:utils document-corpus
```

SweetClaude shows the menu with current pipeline state next to each step:

```
  1. Status        — see where the pipeline is
  2. Consolidate   — scan directories, deduplicate, ingest into raw/inbox/
  3. Triage        — classify each file (keep/reconcile/discard/defer)
  4. Reconcile     — draft canonical documents from related files
  5. Promote       — finalize with provenance, archive sources, RAG index
  6. Set up RAG    — local semantic search over canonical docs
  7. Reindex RAG   — rebuild embeddings
```

You pick **2** (Consolidate). Point it at three directories. It scans every file, computes hashes, collapses duplicates, copies unique files into `corpus/raw/inbox/`. Originals are never touched. You see a plan before anything moves.

Then **3** (Triage). Each file gets classified — keep, reconcile, discard, or defer. You can do this in batch, by group, or one at a time. Discarded files go to archive with a sidecar explaining why.

Then **4** (Reconcile). Pick a cluster of related staged files. An AI subagent reads each file and proposes an action against existing canonical documents (merge, supersede, copy, discard). You review the proposals, then collaborate on a draft canonical document. Iterate until you approve. Approved drafts land in `corpus/working/`.

Then **5** (Promote). The mechanical step. Takes approved drafts, writes provenance sidecars tracing every canonical document back to its source files, archives the sources, moves canonical to `corpus/canonical/`, and git commits. If you have RAG set up, this step also re-indexes.

Each step checks that the previous one is complete and explains why it matters if it is not. Skipping consolidate creates duplicate canonical documents. Skipping triage feeds discards into reconcile. Skipping reconcile and indexing raw files into RAG produces a knowledge base that cannot tell drafts from authoritative documents. If you still want to skip ahead, you can override by typing `I accept the risk of corpus corruption`.

### What you have at the end

A `corpus/canonical/` directory with the documents you actually want to keep. Provenance sidecars that explain every canonical document's source. An archive of the originals (never deleted). An optional local RAG index (`.rag-index/`) that lets you ask "what did we decide about authentication?" and get the right passages back.

Full reference: [Corpus and RAG](corpus-system.md).

---

## 5. Course Correction Mid-Project

You have been building. New information arrived — a customer interview, a competitive shift, a regulatory ruling — and the direction is wrong. You need to pivot without throwing away the work that still applies.

```
/sweetclaude:go we need to change direction, the target user is not who we thought
```

SweetClaude classifies this as `course-correction`. The workflow is `full-pipeline` but with a TRIAGE phase between DEFINE and SHIP. That phase exists for exactly this situation.

### DISCOVER (revised)

You document the signal that triggered the correction. Not just the ruling/interview/data — the *aggregation* of signals. SweetClaude pushes here: is this a pattern, or a single data point that might be noise? Course corrections are expensive; the framework wants confirmation before you commit.

### DEFINE (revised)

The new direction is articulated. The old direction is also articulated, side by side, so the diff is explicit. Updated personas if the target user is changing. New scope. Old scope formally retired.

### TRIAGE

Every in-flight work item gets reviewed and tagged: **keep**, **drop**, **repurpose**, or **defer**. SweetClaude walks through them one by one. Repurposed items become new backlog items with rationale. Dropped items get closed with documented justification. Nothing gets silently abandoned.

### SHIP

The correction is committed to project state. The decision log records the correction. Backlog is clean. New follow-on work items exist for whatever the new direction needs.

### What you have at the end

A clean break from the old direction. Decision log entry explaining the correction. Backlog free of zombie items from the abandoned direction. Whatever you decided to keep is intact, with explicit justification.

The reason this exists as its own work type is that pivots without TRIAGE leave debris everywhere — half-finished features, stale assumptions, contradictory specs. Six months later the codebase still reflects two directions. The TRIAGE phase prevents that.

---

## 6. Building One Feature With Full TDD

You have a planned feature. Specs exist. You want to run the rigorous version end-to-end.

```
/sweetclaude:build code-feature thread reply feature
```

SweetClaude looks for existing specs in this order: Gherkin `.feature` files in `.sweetclaude/` or `features/`, user stories and issue artifacts in the configured product base (`.sweetclaude/product/` by default), and a PRD or product brief in `docs/`. It finds Gherkin files for "thread reply" and skips the spec-writing step.

Now the **TDD Level 3** pipeline:

### Step 0 — Story branch

`code-feature` recommends creating a story branch before any test or implementation work begins: `{ID}/{slug}` — e.g. `ISSUE-046/thread-reply-feature`. The ID comes from the backlog ID in your request or the active work item. You can accept the recommended branch, stay on your current branch, or choose something else. If you take the branch, all commits for this feature land on it. At completion you choose how to close out: open a PR (recommended), commit, merge to main, and push, commit only, or leave the changes as they are.

### Step 1 — Test writer agent

A separate AI agent runs in an isolated context. It can read the Gherkin specs, the existing codebase, and the test framework configuration. It cannot read this conversation. It writes failing tests and commits them.

You see the diff. The tests are committed before any implementation begins.

### Step 2 — QA Caucus review

Three specialist agents review the test plan in parallel. Each returns findings:

- **Service/API expert** — coverage of tenant isolation, state transitions, concurrency, inter-service interactions
- **Component/UI expert** — accessibility, loading states, user interaction edge cases
- **Integration expert** — gaps between layers, optimistic UI vs server state, multi-tab scenarios, security bypasses

The findings are presented to you. You can accept the test plan, request additions, or override specific findings with rationale. Nothing proceeds until you approve.

### Step 3 — Implementer agent

A separate AI agent runs in an isolated context. It can read the tests, the codebase, and the framework. It cannot read the Gherkin specs, the QA findings, or the test writer's reasoning. It only sees the tests as a black-box specification of behavior.

It writes implementation code. The auto-test-runner hook runs the tests after each edit and reports failures back. The test-guardian hook denies edits to test files.

The implementer iterates until all tests pass. If tests cannot be made to pass without modifying them, the implementer surfaces the conflict to you — it cannot rationalize a poor test by reasoning about what the spec "really meant," because it has not seen the spec.

### Step 4 — Optional mutation testing

```
/sweetclaude:build code-testing mutation
```

Mutation testing introduces deliberate faults into the implementation and re-runs the test suite. Every mutation that the tests fail to catch is a coverage gap. You decide whether to add a test or accept the gap.

### Step 5 — Code review and PR pre-check

```
/sweetclaude:build code-review
/sweetclaude:build code-testing pr-precheck
```

Adversarial review by the code-reviewer agent — logic errors, edge cases, missing error handling. Then PR pre-check — coverage, changelog, doc updates. PR opens.

### What you have at the end

A feature that does what the spec says, verified by tests that were written before the implementation, reviewed by a second context that could not see those tests' rationale, and reviewed adversarially. A traceability map from user story to test to commit. Mutation-tested if you ran step 4.

This is the most rigorous version of the SweetClaude code workflow. It is appropriate for net-new features in a project that has reached BETA or beyond. For earlier-stage work, TDD Levels 1 or 2 are usually enough — see [tdd.md](tdd.md).

---

## 7. A Big Feature Through the Large-Story Workflow

### Setup

You describe a substantial, risky piece of work to `/sweetclaude:go` — something
too big for a single bounded pass. SweetClaude classifies it as high-rigor and
routes into the internal **large-story** workflow. You don't invoke it directly;
you just notice the work now moves one gated step at a time.

### Define — lock the criteria

Before any design or code, you and SweetClaude agree the objective, outcomes, and
non-goals, then it writes and **freezes** a success-criteria contract. Each
criterion is binary and measurable — vague ones ("looks good", "production-ready")
are rejected and routed to backlog. Freezing computes a hash; from here, every
downstream artifact is bound to it.

### Design and Plan — bound to the contract

Design and plan artifacts are written and bound to the frozen contract. The
controller won't let Plan start until the design is bound, or Implement start
until the plan is bound. Try to jump ahead and you get a block with the reason.

### Enforcement check

Right before Implement, the controller arms a probe to confirm the evidence gate
is actually live — it allows one expected write and blocks one forbidden one. If
enforcement can't be verified, the workflow stops rather than run unprotected.

### Implement — evidence is recorded, not claimed

Only now can project files change. As you work, an evidence hook records the files
touched and commands run — automatically, from observed activity. You can't
fabricate it, and you can't skip it.

### Verify — fails closed

The controller regenerates the implementation record and writes the canonical
ledger. If any criterion lacks evidence — or no implementation evidence was
observed at all — verify **does not pass**. "It works on my screen" is not
completion; the ledger is.

### What you have at the end

A feature whose completion is provable: a frozen contract, an evidence trail the
harness observed, and a ledger that evaluated every criterion. "Done" was granted
by the controller against evidence, not asserted from how the output looked. For
the full mechanics see [Large-Story and Small-Story Workflows](large-story-workflow.md)
and [Evidence and Success-Criteria Contracts](evidence-and-contracts.md).

---

## What to Read Next

- The mental model behind these workflows → [How It Works](how-it-works.md)
- Reference for all skills used in these walkthroughs → [Skills Reference](skills-reference.md)
- Reference for phase exit criteria → [Phases and Workflows](phases-and-workflows.md)
- Honest tradeoffs and when not to use SweetClaude → [FAQ](faq.md)
