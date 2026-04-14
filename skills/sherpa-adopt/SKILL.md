---
description: "Start using SweetClaude on an existing project. Scans the codebase, understands what exists, sets up SweetClaude state, and figures out where you are in the development lifecycle. For projects with existing code, docs, or history."
---

# SweetClaude Sherpa — Adopt Existing Project

Set up SweetClaude on a project that already has code, docs, or history. This skill assesses what exists, configures SweetClaude, and determines where you are in the pipeline.

**Follow these steps in order. Do not skip. Do not fast-track.**

---

## Step 0: Check for SweetClaude

Is `.sweetclaude/state/phase.yaml` already present?

**If yes**: SweetClaude is already set up. Tell the user:

> "SweetClaude is already configured here. Run `/sweetclaude:status` to see progress, or `/sweetclaude:help` for commands."

Do not proceed.

**If no**: Continue.

---

## Step 1: Initialize SweetClaude

Run `/sweetclaude:init`. This will:
- Detect that code already exists (Scenario B or A)
- Ask about strategy documents to bring in
- Scan the codebase for language, framework, and toolchain
- Create `.sweetclaude/` (a folder inside the project that tracks progress, decisions, and configuration)
- Generate or update CLAUDE.md

Wait for init to complete.

---

## Step 2: Assess what exists

Spawn a subagent to survey the project:

> Scan the project and report what exists. Check for:
>
> **Code:**
> - Source code: languages, frameworks, approximate size (file count)
> - Tests: do they exist? What coverage (rough)? What test framework?
> - CI/CD: any GitHub Actions, deployment scripts?
> - Dependencies: package count, any known vulnerabilities?
>
> **Documentation:**
> - README: does it exist? Is it substantive?
> - CLAUDE.md: already exists or just generated?
> - docs/ directory: what's in it?
> - ADRs or decision records?
> - API docs, specs, architecture docs?
>
> **Project management:**
> - Issues: check `gh issue list` for open issues
> - PRs: check `gh pr list` for open PRs
> - Backlog: any backlog files?
> - User stories or specs?
>
> **Strategy:**
> - strategy/ directory: what's in it?
> - Any positioning, competitive analysis, or research docs?
>
> Report findings organized by category. Be factual — count files, list what exists. Do not editorialize. Do nothing else.

Present the survey to the user.

---

## Step 3: Understand the current state

Ask the user these questions one at a time:

1. **"Where is the project right now — early (mostly planning), mid-build (actively coding), or mature (maintaining/iterating)?"**

2. **"What needs to happen next?"**

3. **"What is the biggest problem or frustration with the project right now?"**

4. **"Is anything about the codebase messy, undocumented, or worrying you?"**

---

## Step 4: Determine pipeline position

Based on the survey (Step 2) and user answers (Step 3), propose where this project sits in the SweetClaude pipeline:

| Project State | Recommended Phase | Rationale |
|---|---|---|
| Just an idea, no code | DISCOVER | Start from the beginning |
| Has specs/PRD but no code | PLAN or DESIGN | Specs exist, may need stories or architecture |
| Actively building features | IMPLEMENT | Code is being written |
| Code exists but untested | IMPLEMENT | Lock behavior with tests |
| Feature-complete, needs polish | VERIFY | Code review, security, PR prep |
| Shipping/maintaining | SHIP or new task cycle | Use `/sweetclaude:new-task` for each piece of work |

Present your assessment:

> "This project is in the {phase} phase. Reason: {reasoning}. Does that match?"

Let the user confirm or adjust.

---

## Step 5: Set phase and orient

Update `.sweetclaude/state/phase.yaml` with the agreed phase:
```yaml
phase: {agreed phase}
work_type: {adoption}
deference_level: null
project_type: code+strategy
```

Then ask the deference level. Use AskUserQuestion with these options:
- "Collaborative" — stop after every sub-step
- "Guided" — stop at major decisions
- "Autonomous" — stop only at phase gates

---

## Step 6: Address immediate concerns

If the user mentioned problems in Step 3 (messy code, no tests, missing docs), propose a first action:

> "You mentioned {concern}. First step: {specific action using a specific SweetClaude command}. Start there?"

If no concerns:

> "Setup complete. Run `/sweetclaude:status` to see the full picture, `/sweetclaude:auto-flow` to work through the pipeline, or `/sweetclaude:help` for all commands."

---

## Principles for adoption

- **Do not judge the existing code.** You are an archaeologist, not a demolition crew.
- **Do not propose rewriting anything** unless the user brings it up.
- **Lock behavior before changing it.** If the user wants to refactor, tests come first.
- **Respect existing decisions.** Read docs, ADRs, and specs before proposing anything that might contradict them.
- **The user knows their project better than you.** Your job is to understand it, not to critique it.
