---
description: List all SweetClaude commands and check project configuration status. Use when the user types /sweetclaude:help or asks what SweetClaude can do.
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Help

Check project status. Show available commands.

## Step 1: Project Status

Check and report:

```
SweetClaude Status
══════════════════

Project:     {project name from git root}
Configured:  {Yes/No}
Phase:       {current phase from phase.yaml, or "not set"}
Deference:   {level from phase.yaml, or "not set"}
State dir:   {path if exists, or "none"}
```

## Step 2: Available Commands

```
Getting Started
  /sweetclaude:sherpa         New or existing project — detects context, walks you through setup

Orchestration
  /sweetclaude:master         Start session, pre-flight check, phase routing
  /sweetclaude:help           This list (you are here)
  /sweetclaude:status         See what is done, what is pending, what is next
  /sweetclaude:next-steps     Walk through pipeline step by step
  /sweetclaude:find-skill       Classify work and enter the pipeline
  /sweetclaude:fix-sweetclaude     Audit and repair SweetClaude configuration
  /sweetclaude:update-sweetclaude  Sync latest from GitHub — update all projects
  /sweetclaude:usage          Toggle and view local usage tracking
  /sweetclaude:hibernate      Freeze or thaw a project

Strategy
  /sweetclaude:strategy/concept              Articulate what this is and why it exists
  /sweetclaude:strategy/pain-thesis          Structured pain analysis
  /sweetclaude:strategy/ideal-customer-profile  Who has this pain and will pay
  /sweetclaude:strategy/competitive-analysis Strategic landscape and differentiation
  /sweetclaude:strategy/academic-research    Research paper development pipeline
  /sweetclaude:strategy/meeting-prep         Stakeholder meeting deliverables
  /sweetclaude:strategy/narrative-arc        Knowledge graph of strategic claims
  /sweetclaude:product/market-messaging     External communications

Product
  /sweetclaude:product/discovery             Persona interviews, feature brainstorming
  /sweetclaude:product/positioning-statement Product positioning
  /sweetclaude:product/product-brief         11-section product brief
  /sweetclaude:product/prd                   Full PRD with FRs, NFRs, epics
  /sweetclaude:product/user-story            User stories with acceptance criteria
  /sweetclaude:product/user-tdd-tests        Stories to Gherkin .feature files
  /sweetclaude:product/user-success-criteria Measurable success per persona
  /sweetclaude:product/user-workflows        Stories to UX/UI flows
  /sweetclaude:product/manage-scope          Track scope changes with rationale
  /sweetclaude:product/backlog               Manage deferred work
  /sweetclaude:product/sprint-plan           Plan sprints from backlog
  /sweetclaude:product/research              Market or technical research
  /sweetclaude:product/feature-competitive   Product-level feature comparison

Design
  /sweetclaude:design/architecture           System architecture
  /sweetclaude:design/tech-spec              Technical specification
  /sweetclaude:design/ux                     UX design and wireframes
  /sweetclaude:design/solutioning-gate       Validate design before implementation
  /sweetclaude:design/change-impact-analysis Trace blast radius before changes
  /sweetclaude:design/update-docs            Keep docs in sync after changes
  /sweetclaude:design/data-model             Schema, entities, migrations
  /sweetclaude:design/api-design             Endpoints, contracts, versioning
  /sweetclaude:design/services-design        Service boundaries and communication
  /sweetclaude:design/infra-design           Infrastructure and deployment
  /sweetclaude:design/manage-decisions       Record decisions with rationale

Documents
  /sweetclaude:document-corpus     Corpus pipeline + RAG — consolidate, triage, reconcile, promote, search

Code
  /sweetclaude:code/tdd              TDD at 4 levels (hotfix through full from Gherkin)
  /sweetclaude:code/work-issue       Implement a GitHub issue end-to-end
  /sweetclaude:code/work-debt        Tech debt cleanup (lock behavior first)
  /sweetclaude:code/testing          Run tests, mutation, security review, and/or PR pre-check
  /sweetclaude:code/code-review      Adversarial code review
```

## Step 3: Quick Start

If the project is not configured:
> "Run `/sweetclaude:sherpa` to set up this project."

If configured:
> "You are in the {phase} phase. Run `/sweetclaude:status` to see the full picture, `/sweetclaude:next-steps` to keep working, or any command above."
