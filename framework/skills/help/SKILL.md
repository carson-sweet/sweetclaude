---
name: sweetclaude:help
description: List all SweetClaude commands and check project configuration status. Use when the user types /sweetclaude:help or asks what SweetClaude can do.
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Help

Check project status, then show available commands.

## Step 1: Project Status

Check and report:

```
SweetClaude Status
  Project:     {project name from git root}
  Configured:  {Yes/No}
  Phase:       {current phase from phase.yaml, or "not set"}
  Deference:   {level from phase.yaml, or "not set"}
  State dir: {path if exists, or "none"}
```

## Step 2: Available Commands

```
Orchestration
  /sweetclaude:master         Start session, pre-flight check, phase routing
  /sweetclaude:help           This help (you are here)
  /sweetclaude:status         Orient to project: what's done, what's pending, what's next
  /sweetclaude:auto-flow      Walk through pipeline step by step
  /sweetclaude:init           Set up SweetClaude for this project
  /sweetclaude:new-task       Classify work and enter the pipeline
  /sweetclaude:hibernate      Freeze or thaw a project mid-phase

Strategy
  /sweetclaude:strategy/concept              Articulate what this is and why it exists
  /sweetclaude:strategy/pain-thesis          Structured pain analysis
  /sweetclaude:strategy/ideal-customer-profile  Who has this pain and will pay
  /sweetclaude:strategy/competitive-analysis Strategic landscape and differentiation
  /sweetclaude:strategy/academic-research    Research paper development pipeline
  /sweetclaude:strategy/meeting-prep         Stakeholder meeting deliverables
  /sweetclaude:strategy/narrative-arc        Knowledge graph of strategic claims
  /sweetclaude:strategy/market-messaging     External communications

Product
  /sweetclaude:product/discovery             Persona interviews, feature brainstorming
  /sweetclaude:product/positioning-statement Product positioning
  /sweetclaude:product/product-brief         11-section product brief
  /sweetclaude:product/prd                   Full PRD with FRs, NFRs, epics
  /sweetclaude:product/user-story            User stories with acceptance criteria
  /sweetclaude:product/user-tdd-tests        Stories → Gherkin .feature files
  /sweetclaude:product/user-success-criteria Measurable success per persona
  /sweetclaude:product/user-workflows        Stories → UX/UI flows
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

Code
  /sweetclaude:code/tdd              TDD at 4 levels (hotfix → full from Gherkin)
  /sweetclaude:code/work-issue       Implement a GitHub issue end-to-end
  /sweetclaude:code/work-debt        Tech debt cleanup (lock behavior first)
  /sweetclaude:code/pr-precheck      Pre-PR quality gate
  /sweetclaude:code/qa-testing       Run tests, report failures concisely
  /sweetclaude:code/mutation-testing  Verify tests catch real faults
  /sweetclaude:code/security-testing Security review of code changes
  /sweetclaude:code/code-review      Adversarial code review
```

## Step 3: Quick Start

If the project is not configured:
> "Run `/sweetclaude:init` to set up this project, or `/sweetclaude` to start the pre-flight check."

If configured:
> "You're in the {phase} phase. Run `/sweetclaude:status` to orient, `/sweetclaude:auto-flow` to keep moving, or any command above."
