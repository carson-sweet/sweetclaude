# Walkthroughs

**Version:** 1.0
**Date:** 2026-05-01

Six concrete scenarios end-to-end. Each one shows what you run, what comes back, and what you have when you are done. The interactions are simulated but representative — actual prompts vary slightly with the model and your project state.

---

## 1. From Napkin Sketch to Shipped Feature

You have a vague idea: a tool to help freelance designers collect feedback from clients on visual mockups. No code, no spec, no folder. You want to take it from concept to a shipped MVP feature.

### Setup

```bash
mkdir feedback-tool && cd feedback-tool && claude
```

```
/sweetclaude:on
```

SweetClaude detects the empty folder. It asks if you want a git repo (yes), what deference level (collaborative for the first run), and then asks you to describe the idea.

You type a paragraph. SweetClaude does not start drafting. Instead it pushes back:

> You said "freelance designers" — but the friction in client feedback exists across roles. Agencies, in-house teams, and indie product designers all face it. What makes you confident the freelance segment specifically? Or is "freelance designers" a stand-in for a broader pattern?

You think about it and refine: it is freelance designers because they have no design ops infrastructure and clients are non-designers. SweetClaude accepts the framing, records it as a decision, and offers product discovery at three depths. You pick L2 (problem and success) — this is more than a hobby project but you do not want a 90-minute interview.

### Discovery and Definition

SweetClaude conducts the L2 discovery interview, one section at a time. After each section it probes — never batches multiple questions into one message. By the end you have:

- `strategy/discovery.md` — problem framing, target user, success criteria
- `strategy/personas/` — at least one persona with a real scenario
- `.sweetclaude/state/decision-log.md` — three decisions captured

Then you run `/sweetclaude:product-brief`. SweetClaude reads the discovery output, presents an outline first, lets you approve or restructure, then writes the brief. You iterate twice. You commit.

Then `/sweetclaude:product-prd` — full PRD with functional requirements, NFRs, and epics. About 90 minutes of work. You commit.

### Design

`/sweetclaude:design-architecture`. SweetClaude conducts an architecture interview — language, framework, data store, deployment target. Always offers a recommendation before asking you to decide. Records architectural decisions as ADRs.

You also run `/sweetclaude:design-data-model` for the schema and `/sweetclaude:design-api-design` for endpoint contracts. Both feed off the architecture state.

### Plan

`/sweetclaude:product-user-stories` produces stories with acceptance criteria for the first epic. `/sweetclaude:product-user-tdd-tests` converts them to Gherkin `.feature` files.

### Implement

```
/sweetclaude:code-feature first feedback-thread feature
```

SweetClaude finds the Gherkin specs for that feature. It runs **TDD Level 3**:

1. The test-writer agent (separate context, no knowledge of planned implementation) writes failing tests.
2. The QA Caucus — three specialist agents — reviews the test plan from three angles: service/API, component/UI, integration/cross-cutting.
3. You see the QA findings and approve the test plan.
4. The implementer agent (separate context, sees only the tests) makes them pass with minimal code. The test-guardian hook physically blocks any test file edits while it works.
5. The auto-test-runner hook fires after every source edit. Tests run automatically.

When all tests pass, SweetClaude runs `/sweetclaude:code-review` and `/sweetclaude:code-testing` (PR pre-check), then opens a PR.

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
/sweetclaude:on
```

The first thing SweetClaude does is create a `pre-sweetclaude` git branch from your current state. That branch is your insurance — if you ever want to undo every byte SweetClaude added to your repo, `git checkout pre-sweetclaude` gets you back. SweetClaude refuses to proceed without this branch.

Then it scans your project read-only:

```
✓ Detected: TypeScript + Node.js
✓ Test runner: jest (47 tests, last run passing)
✓ Build: npm run build
✓ Docs: README.md, no CLAUDE.md, no architecture doc
✓ Git: 4 open branches, 12 open issues, 2 open PRs
```

Then the four-question interview, one at a time. The fourth question is the important one:

> Is there anything messy, undocumented, or worrying?

Most onboarding flows skip this. SweetClaude treats your answer here as load-bearing.

If you say "the auth code was written under deadline and I am not sure it is right," SweetClaude positions you in the IMPLEMENT phase with a specific first action: `/sweetclaude:code-debt` to lock the existing auth behavior in tests before any refactor.

If you say "everything is fine, I just want SweetClaude to be available," SweetClaude positions you wherever you want and shows you the menu.

### What you have at the end

Your codebase, untouched except for the addition of `.sweetclaude/` (which you commit). A `pre-sweetclaude` branch you can roll back to. A phase state that reflects where you actually are. A first action proposed if you flagged a concern, or a clean slate if you did not.

The tone of this onboarding is deliberate. SweetClaude treats existing codebases like an archaeologist treats a dig site — understanding before changing, respecting what is there.

---

## 3. A Hotfix at 2 AM

Production is broken. You need to ship a fix now. SweetClaude has a workflow for this and it skips most of the ceremony.

```
/sweetclaude:find-skill production is down, the OAuth callback is throwing 500s
```

SweetClaude classifies this as a `hotfix` — work type, not bug fix. The difference matters: hotfix runs the **compressed** workflow shape (DIAGNOSE → IMPLEMENT → SHIP → POST-MORTEM), skips most prerequisite checks, and accepts that the POST-MORTEM is a follow-on work item, not a step you can skip.

It asks you three triage questions:
1. Is the impact confirmed (which users, what severity)?
2. Is there a temporary mitigation that can reduce exposure while you patch?
3. Is rollback faster than patching?

If rollback is faster, SweetClaude routes you to `rollback-revert` instead. If a patch is right, you stay in `hotfix`.

### DIAGNOSE

The hotfix workflow is not "skip the test." It is "minimal test, in this session." SweetClaude asks you to identify the broken code and write a regression test that fails on the bug. Then it implements the fix. The test and fix get committed together.

Test-guardian and auto-test-runner hooks are still active. The hotfix shortcut applies to ceremony, not to discipline.

### SHIP

SweetClaude asks for an async notification to a stakeholder (a Slack message, an issue update — anything) or a logged self-review. It deploys (or hands off to your deploy command). It confirms the fix in production.

### POST-MORTEM

Spawned automatically as a follow-on work item. Not optional. The post-mortem fires as a separate skill that asks for the timeline of events, the root cause analysis, contributing factors, and action items. Action items go to your backlog.

If the hotfix was a workaround rather than a real fix, SweetClaude creates a follow-on tech-debt work item to do the real fix later. It will not let you forget.

### What you have at the end

Production restored. A regression test that was missing before. A POST-MORTEM document. Action items in the backlog. A tech-debt item if you patched around the real problem.

---

## 4. Organizing a Pile of Documents

You have thirty strategy documents, fifteen Claude.ai session exports, eight meeting notes, and a Google Drive folder of research PDFs. Some are duplicates. Some are drafts of drafts. You need a clean canonical set of go-forward documents that you can search.

```
/sweetclaude:document-corpus
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

You cannot skip steps. The state machine refuses and explains why if you try. Skipping consolidate creates duplicate canonical documents. Skipping triage feeds discards into reconcile. Skipping reconcile and indexing raw files into RAG produces a knowledge base that cannot tell drafts from authoritative documents.

### What you have at the end

A `corpus/canonical/` directory with the documents you actually want to keep. Provenance sidecars that explain every canonical document's source. An archive of the originals (never deleted). An optional local RAG index (`corpus/rag/`) that lets you ask "what did we decide about authentication?" and get the right passages back.

Full reference: [Corpus and RAG](corpus-system.md).

---

## 5. Course Correction Mid-Project

You have been building. New information arrived — a customer interview, a competitive shift, a regulatory ruling — and the direction is wrong. You need to pivot without throwing away the work that still applies.

```
/sweetclaude:find-skill we need to change direction, the target user is not who we thought
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
/sweetclaude:code-feature thread reply feature
```

SweetClaude looks for existing specs in this order: Gherkin `.feature` files, user stories in `.sweetclaude/stories/`, PRD in `docs/`. It finds Gherkin files for "thread reply" and skips the spec-writing step.

Now the **TDD Level 3** pipeline:

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

It writes implementation code. The auto-test-runner hook runs the tests after every edit. The test-guardian hook prevents any change to test files.

The implementer iterates until all tests pass. If tests cannot be made to pass without modifying them, the implementer surfaces the conflict to you — it cannot rationalize a poor test by reasoning about what the spec "really meant," because it has not seen the spec.

### Step 4 — Optional mutation testing

```
/sweetclaude:code-testing mutation
```

Mutation testing introduces deliberate faults into the implementation and re-runs the test suite. Every mutation that the tests fail to catch is a coverage gap. You decide whether to add a test or accept the gap.

### Step 5 — Code review and PR pre-check

```
/sweetclaude:code-review
/sweetclaude:code-testing pr-precheck
```

Adversarial review by the code-reviewer agent — logic errors, edge cases, missing error handling. Then PR pre-check — coverage, changelog, doc updates. PR opens.

### What you have at the end

A feature that does what the spec says, verified by tests that were written before the implementation, reviewed by a second context that could not see those tests' rationale, and reviewed adversarially. A traceability map from user story to test to commit. Mutation-tested if you ran step 4.

This is the most rigorous version of the SweetClaude code workflow. It is appropriate for net-new features in a project that has reached BETA or beyond. For earlier-stage work, TDD Levels 1 or 2 are usually enough — see [tdd.md](tdd.md).

---

## What to Read Next

- The mental model behind these workflows → [How It Works](how-it-works.md)
- Reference for all skills used in these walkthroughs → [Skills Reference](skills-reference.md)
- Reference for phase exit criteria → [Phases and Workflows](phases-and-workflows.md)
- Honest tradeoffs and when not to use SweetClaude → [FAQ](faq.md)
