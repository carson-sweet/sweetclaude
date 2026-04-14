---
name: sherpa-start
description: "The ultimate starting point for a brand new project. Empty folder, fresh idea. Walks you through everything from 'I have an idea' to a configured project with strategy, product definition, and a path to code. Chains init → concept → pain-thesis → ICP → discovery → auto-flow."
---

# SweetClaude Sherpa — New Project

You're starting from scratch. This skill walks you through the entire early process, one step at a time.

**Follow these steps in order. Do not skip. Do not fast-track. Complete each step before moving to the next.**

---

## Step 0: Check for existing project

Before anything else, check the current directory:
- Is there a `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Makefile`, or `src/` directory?
- Is there a `.git` directory with commits?
- Is there a `.sweetclaude/` directory?

**If any of these exist**, stop immediately:

> "This folder already has a project in it. `/sweetclaude:sherpa-start` is for brand new projects starting from an empty folder. If you want to start using SweetClaude on this existing project, run `/sweetclaude:sherpa-adopt` instead."

Do not proceed. Wait for the user to decide.

**If the folder is empty or nearly empty** (just a README or .gitignore is fine), continue.

---

## Step 1: What's the idea?

Ask the user one question:

> "What do you want to build? Don't worry about being precise — just tell me the idea in whatever words come naturally."

Listen. Don't correct. Don't structure. Let them talk. Ask one follow-up if the answer is very short:

> "Tell me more — what problem does this solve, and for whom?"

---

## Step 2: Initialize the project

Run `/sweetclaude:init` to set up the project. This creates the repo, `.sweetclaude/` state directory, `strategy/` structure, and CLAUDE.md.

The user's answer from Step 1 provides the project description for CLAUDE.md.

Wait for init to complete before proceeding.

---

## Step 3: Articulate the concept

Run `/sweetclaude:strategy/concept` using the user's idea from Step 1 as the starting input.

This produces `strategy/concept.md` — a sharpened statement of what the project is, the problem it solves, why it matters, key assumptions, and what it's NOT.

Wait for the user to be satisfied with the concept before proceeding.

---

## Step 4: Build the pain thesis

Run `/sweetclaude:strategy/pain-thesis`.

This walks through 11 sections: industry background, pain ownership, pain detail, existing failures, solution requirements, strategic wedge, buyer success criteria, ICP, solution mapping, validation plan.

This is the longest step. The user may want to do it across multiple sessions. That's fine — `.sweetclaude/state/` tracks progress.

Wait for completion before proceeding.

---

## Step 5: Define the ideal customer

Run `/sweetclaude:strategy/ideal-customer-profile`.

This sharpens the "who" from the pain thesis into a targetable profile: demographics, behaviors, triggers, deal-breakers, anti-profile.

Wait for completion.

---

## Step 6: Product discovery

Run `/sweetclaude:product/discovery`.

This walks through persona interviews (one at a time), feature brainstorming (one at a time, include/exclude), and optional competitive analysis.

Wait for completion.

---

## Step 7: Hand off to auto-flow

At this point the project has:
- A concept statement
- A pain thesis
- An ideal customer profile
- Personas and feature set from discovery

Tell the user:

> "The strategic foundation is set. From here, the next steps are product definition (product brief, PRD), then design, then implementation. Run `/sweetclaude:auto-flow` to continue step by step, or pick any specific command from `/sweetclaude:help`."

Do not auto-invoke auto-flow. The user decides when to continue.

---

## Session continuity

If a session ends mid-process, `.sweetclaude/state/phase.yaml` tracks where you are. The next session can resume with `/sweetclaude:status` to see what's done and what's next, then continue with the appropriate step.
