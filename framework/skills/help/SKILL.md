---
name: sweetclaude-help
description: List all SweetClaude commands and check project configuration status. Use when the user types /sweetclaude:help or asks what SweetClaude can do.
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Help

Check project status, then show available commands.

## Step 1: Project Status

Check and report:

```
SweetClaude Status
  Project:     {project name from git root}
  Configured:  {Yes/No — does state/phase.yaml exist?}
  Phase:       {current phase from phase.yaml, or "not set"}
  Track:       {code/strategy from phase.yaml, or "not set"}
  Deference:   {level from phase.yaml, or "not set"}
  Working repo: {path if exists, or "none"}
```

## Step 2: Available Commands

```
Orchestration
  /sweetclaude              Session entry point, phase router, pre-flight check
  /sweetclaude:init         Set up SweetClaude for this project
  /sweetclaude:help         This help (you are here)
  /sweetclaude:hibernate    Freeze or thaw a project mid-phase
  /sweetclaude:discover  Structured persona/feature/competitive discovery
  /sweetclaude:work-router  Classify work type and enter pipeline

Code Track
  /sweetclaude:code/tdd             TDD enforcement (4 levels: hotfix, light, standard, full)
  /sweetclaude:code/fix-issue       End-to-end GitHub issue implementation
  /sweetclaude:code/pr-ready        Pre-PR quality gate checklist
  /sweetclaude:code/ripple          Ripple-effect analysis before changes
  /sweetclaude:code/auto-docs       Update docs when behavior changes
  /sweetclaude:code/gherkin-bridge  Convert user stories to .feature files
  /sweetclaude:code/mutation-testing Verify test quality via mutation testing
  /sweetclaude:code/scope-tracker   Track scope changes with rationale

Strategy Track
  /sweetclaude:strategy/reconciliation  Onboard and organize unstructured files
  /sweetclaude:strategy/academic        Research paper development pipeline
```

## Step 3: Quick Start

If the project is not configured:
> "Run `/sweetclaude:init` to set up this project, or `/sweetclaude` to start the pre-flight check."

If configured:
> "You're in the {phase} phase on the {track} track. Run `/sweetclaude` to continue, or any command above."
