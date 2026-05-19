---
id: STORY-307
type: story
title: Spike — enforce collaborative deference checkpoints via prompt engineering and/or subagent isolation
status: new
priority: soon
effort: m
epic: null
milestone: null
sprint: null
tags: [spike, deference, prompt-engineering, subagents, safety, self-hosting]
origin: manual
created: 2026-05-19
updated: 2026-05-19
closed_date: null
---

## Description

As a SweetClaude developer working in collaborative deference mode, I want the framework to structurally enforce checkpoint stops between sub-steps so that context compression, autonomy drift, and efficiency reasoning cannot cause Claude to charge ahead past explicit stop boundaries.

The current enforcement is purely behavioral — a rule in the interaction model that Claude is supposed to follow. In practice, it fails when context is compressed ("resume directly" gets misread as license to run autonomously) and when Claude decides a remaining step is "small enough" to batch. Both failure modes are documented in the improvement register and have recurred across sessions. The rule needs structural backing, not just a stronger rule.

## Spike Questions

1. **Prompt engineering:** Can the deference level be encoded in a way that survives context compression? Candidates: a persistent SYSTEM-level reminder injected per tool call, a structured checkpoint marker embedded in each sub-step output that Claude must emit before the next step can begin, or a required acknowledgment token the user must echo back. What survives compression and what doesn't?

2. **Subagent isolation:** Can collaborative deference checkpoints be enforced by having each sub-step run in a separate subagent invocation that terminates after producing its output — forcing a return to the main context where the user must explicitly trigger the next agent? What is the overhead (latency, cost, context loss between steps)?

3. **Hybrid:** Can the two approaches be combined — prompt engineering to make the stop boundary explicit in each step's output, subagent isolation to make it impossible to continue without user action? What does the authoring overhead look like for skill writers?

4. **Failure modes:** What are the failure modes of each approach? Can a subagent be prompted in a way that causes it to chain into the next subagent without user intervention? Can prompt engineering be overridden by a sufficiently strong system instruction (like "resume directly")?

5. **Skill authoring impact:** How much does each approach change what it costs to write a SweetClaude skill? Subagent isolation in particular may require significant scaffolding for state handoff between steps.

6. **Scope:** Should this apply only to collaborative deference, or should guided deference also get checkpoint enforcement at phase gates?

## Acceptance Criteria

- [ ] Spike findings documented in `docs/internal/` covering all six questions above
- [ ] At least one working proof-of-concept for each viable approach (prompt engineering, subagent isolation, or hybrid) demonstrated on a real skill with multiple sub-steps
- [ ] Each PoC tested against the specific failure mode: context compression followed by "resume directly"
- [ ] Decision recorded: which approach (if any) to adopt, why, and at what deference level(s)
- [ ] If proceeding: follow-on stories created for implementation

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
