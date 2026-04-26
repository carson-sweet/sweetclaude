---
description: "The ultimate starting point for a brand new project. Empty folder, fresh idea. Walks you through everything from 'I have an idea' to a configured project with strategy, product definition, and a path to code. Chains init → product-discovery → product-user-personas → auto-flow."
---

# SweetClaude Sherpa — New Project

Starting from scratch. This skill walks through the entire early process, one step at a time.

**Follow these steps in order. Do not skip. Do not fast-track. Complete each step before moving to the next.**

---

## Step 0: Check for existing project

Before anything else, check the current directory:
- Is there a `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Makefile`, or `src/` directory?
- Is there a `.git` directory with commits?
- Is there a `.sweetclaude/` directory?

**If any of these exist**, stop immediately:

> "This folder already has a project in it. `/sweetclaude:sherpa-start` is for empty folders. Run `/sweetclaude:sherpa-adopt` to set up SweetClaude on an existing project."

Do not proceed. Wait for the user to decide.

**If the folder is empty or nearly empty** (just a README or .gitignore is fine), continue.

---

## Step 1: What is the idea?

Ask the user one question:

> "What do you want to build?"

Listen. Do not correct. Do not structure. Let them talk. Ask one follow-up if the answer is very short:

> "What problem does this solve, and for whom?"

---

## Step 2: Initialize the project

Run `/sweetclaude:init` to set up the project. This creates the repo, `.sweetclaude/` state directory (a folder inside the project that tracks progress, decisions, and configuration), `strategy/` structure, and CLAUDE.md.

The user's answer from Step 1 provides the project description for CLAUDE.md.

Wait for init to complete before proceeding.

---

## Step 3: Product discovery

Run `/sweetclaude:product-discovery` using the user's idea from Step 1 as the starting input.

Offer the three depth levels before starting:
- **L1 — Intent and boundaries:** Quick orientation — what you're building, for whom, and what's out of scope. Good for utilities and hobby projects.
- **L2 — Problem and success:** Adds concrete problem definition, audience refinement, success framing, and a challenge of the framing. Good for internal tools and significant projects.
- **L3 — Full pain thesis:** Adds pain measurement, market context, accountability analysis, escalation chains, and a validation rubric. Appropriate for commercial products.

Let the user choose depth or ask for a recommendation. L3 is the most thorough and produces the richest foundation for everything that follows.

Discovery writes `.sweetclaude/state/discovery.yaml`. Wait for the user to be satisfied before proceeding.

---

## Step 4: Define users and personas

Run `/sweetclaude:product-user-personas`.

This defines who uses the product: role, context, trigger (what makes them go looking for a solution), deal-breakers, and the tasks they need to accomplish — with observable success criteria for each task.

At the end, offer an anti-profile: who is explicitly NOT a target user.

Wait for completion.

---

## Step 5: Competitive landscape (optional)

Offer:
> "Want to map the competitive landscape before moving to product definition? I can run a survey (L1), comparison matrix (L2), or feature-deep analysis (L3) via `/sweetclaude:product-competition`."

If the user wants it, run `product-competition`. If not, proceed.

---

## Step 6: Hand off to auto-flow

At this point the project has:
- Discovery artifacts (intent, problem framing, and optionally full pain thesis)
- User personas with tasks and success criteria
- Optionally: competitive landscape

Tell the user:

> "The strategic foundation is set. Next steps: product definition (product brief, PRD), then design, then implementation. Run `/sweetclaude:auto-flow` to continue step by step, or pick a command from `/sweetclaude:help`."

Do not auto-invoke auto-flow. The user decides when to continue.

---

## Session continuity

If a session ends mid-process, `.sweetclaude/state/` tracks progress (discovery.yaml, personas.yaml, etc.). The next session can resume with `/sweetclaude:status` to see what is done and what is next.
